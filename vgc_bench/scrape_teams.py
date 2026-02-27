"""
Scrapes competitive VGC team data from the VGCPastes Google Sheets database.
"""

import argparse
import csv
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import requests
from poke_env.teambuilder import Teambuilder

from vgc_bench.src.teams import calc_team_similarity_score

SHEET_ID = "1axlwmzPA49rYkqXh7zHvAtSP-TKbM0ijGYBPRflLSWw"
SHEET_EDIT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"
SHEET_GVIZ_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq"

ALLOWED_EVENTS = ("regional", "euic", "laic", "naic", "worlds")
BANNED_ABILITIES = ("illusion", "commander")


def slugify(text: str) -> str:
    """Convert text to a URL/filename-safe slug."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def normalize_event_name(name: str) -> str:
    """Remove common suffixes like 'Regional Championships'."""
    name = re.sub(r"\bregional\s+championships?\b", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\bregionals?\b", "", name, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", name).strip()


def extract_year(event_name: str, date_str: str) -> str | None:
    """Extract year from event name, falling back to date string."""
    match = re.search(r"\b(20\d{2})\b", event_name)
    if match:
        return match.group(1)
    date_str = date_str.strip().replace("Sept", "Sep")
    for fmt in ("%d %b %Y", "%d %B %Y", "%d %b, %Y", "%d %B, %Y", "%b %Y", "%B %Y"):
        try:
            return str(datetime.strptime(date_str, fmt).year)
        except ValueError:
            pass
    return None


def event_slug(event_name: str, date_str: str) -> str:
    """Generate slugified event identifier with year."""
    normalized = re.sub(r"\b\d{4}\b", "", normalize_event_name(event_name)).strip()
    base = slugify(normalized) or slugify(normalize_event_name(event_name)) or "event"
    year = extract_year(event_name, date_str)
    return f"{base}_{year}" if year else base


def placement_to_filename(placement: str) -> str:
    """Convert placement to filename (e.g., 'Champion' -> '1st')."""
    normalized = slugify(placement)
    if normalized in {"champion", "winner"}:
        return "1st"
    if normalized == "runner_up":
        return "2nd"
    return normalized or "unknown"


def fetch_sheet_names(session: requests.Session) -> list[str]:
    """Fetch sheet names from the VGCPastes spreadsheet."""
    resp = session.get(SHEET_EDIT_URL, timeout=30)
    resp.raise_for_status()
    names = re.findall(r"docs-sheet-tab-caption\">([^<]+)<", resp.text)
    return list(dict.fromkeys(names))  # dedupe preserving order


def get_regulation_sheets(all_sheets: list[str], regulation: str) -> list[str]:
    """Find featured team sheets for a regulation."""
    reg = regulation.lower()
    sheets = [
        name
        for name in all_sheets
        if "featured" in name.lower()
        and "presentable" not in name.lower()
        and (f"reg {reg}" in name.lower() or f"regulation {reg}" in name.lower())
    ]
    return sheets or [f"Reg {regulation.upper()} Featured Teams"]


def fetch_csv(session: requests.Session, sheet_name: str) -> list[list[str]]:
    """Fetch sheet data as CSV rows."""
    url = f"{SHEET_GVIZ_URL}?tqx=out:csv&sheet={quote_plus(sheet_name)}"
    resp = session.get(url, timeout=60)
    resp.raise_for_status()
    return list(csv.reader(resp.text.splitlines()))


def fetch_team(session: requests.Session, pokepaste_url: str) -> str:
    """Fetch and normalize team text from Pokepaste."""
    paste_id = pokepaste_url.rstrip("/").split("/")[-1]
    resp = session.get(f"https://pokepast.es/{paste_id}/raw", timeout=30)
    resp.raise_for_status()
    return normalize_team_text(resp.text)


def normalize_team_text(text: str) -> str:
    """Normalize team formatting and fix As One ability disambiguation."""
    lines = [line.rstrip() for line in text.strip().splitlines()]
    blocks, block = [], []
    for line in lines:
        if line:
            block.append(line)
        elif block:
            blocks.append(block)
            block = []
    if block:
        blocks.append(block)
    normalized = []
    for block in blocks:
        header = block[0]
        asone = (
            "As One (Glastrier)"
            if "calyrex-ice" in header.lower()
            else "As One (Spectrier)"
        )
        new_lines = []
        for line in block:
            m = re.match(r"^(\s*Ability:\s*)(.*?)\s*$", line, re.IGNORECASE)
            if m and re.sub(r"[^a-z0-9]", "", m.group(2).lower()) == "asone":
                line = f"{m.group(1)}{asone}"
            new_lines.append(line)
        normalized.append("\n".join(new_lines))
    return "\n\n".join(normalized) + "\n"


def has_banned_ability(team_text: str) -> bool:
    """Check if team has Illusion or Commander ability."""
    return any(
        re.search(
            rf"^\s*Ability:\s*{ability}\s*$", team_text, re.IGNORECASE | re.MULTILINE
        )
        for ability in BANNED_ABILITIES
    )


def is_valid_event(event_name: str) -> bool:
    """Check if event should be included."""
    lower = event_name.lower()
    if not any(kw in lower for kw in ALLOWED_EVENTS):
        return False
    if "seniors" in lower or "juniors" in lower or "&" in event_name:
        return False
    return True


def is_valid_placement(placement: str) -> bool:
    """Check if placement is top 64 and not juniors/seniors."""
    lower = placement.lower()
    if "juniors" in lower or "seniors" in lower:
        return False
    filename = placement_to_filename(placement)
    if not filename[0].isdigit():
        return False
    return True


def scrape_regulation(regulation: str) -> None:
    """Scrape featured teams for a VGC regulation."""
    reg_dir = Path("teams") / f"reg{regulation.lower()}"
    reg_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    sheets = get_regulation_sheets(fetch_sheet_names(session), regulation)
    seen_teams: list[str] = []
    event_dirs: dict[str, Path] = {}
    stats = {"saved": 0, "duplicates": 0, "banned": 0, "existing": 0}
    for sheet in sheets:
        rows = fetch_csv(session, sheet)
        header_idx = next(
            i
            for i, r in enumerate(rows)
            if r and r[0].strip() == "Team ID" and "Pokepaste" in r
        )
        header = rows[header_idx]
        col = {
            name: header.index(name)
            for name in ["Category", "EVs", "Pokepaste", "Tournament / Event", "Rank"]
        }
        col["Date"] = (
            header.index("Date") if "Date" in header else col["Tournament / Event"] - 1
        )
        for row in rows[header_idx + 1 :]:
            if len(row) <= max(col.values()):
                continue
            # Filter by category and EVs
            if row[col["Category"]].strip().lower() != "in person event":
                continue
            if row[col["EVs"]].strip().lower() != "yes":
                continue
            # Fetch and validate team
            pokepaste = row[col["Pokepaste"]].strip()
            if not pokepaste.startswith("https://pokepast.es/"):
                continue
            team_text = fetch_team(session, pokepaste)
            if has_banned_ability(team_text):
                stats["banned"] += 1
                continue
            try:
                Teambuilder.parse_showdown_team(team_text)
            except KeyError:
                continue
            if any(
                calc_team_similarity_score(team_text, prev) == 1.0
                for prev in seen_teams
            ):
                stats["duplicates"] += 1
                continue
            seen_teams.append(team_text)
            # Filter by event and placement
            event_name = row[col["Tournament / Event"]].strip()
            if not is_valid_event(event_name):
                continue
            placement = row[col["Rank"]].strip()
            if not is_valid_placement(placement):
                continue
            # Save team
            date_str = row[col["Date"]].strip()
            key = event_slug(event_name, date_str)
            if key not in event_dirs:
                event_dirs[key] = reg_dir / key
                event_dirs[key].mkdir(parents=True, exist_ok=True)
            out_path = event_dirs[key] / f"{placement_to_filename(placement)}.txt"
            if out_path.exists():
                stats["existing"] += 1
                continue
            out_path.write_text(team_text)
            stats["saved"] += 1
    print(f"Saved {stats['saved']} teams to {reg_dir}")
    print(
        f"Skipped {stats['existing']} existing, {stats['banned']} banned, {stats['duplicates']} duplicates"
    )


def main():
    parser = argparse.ArgumentParser(description="Scrape VGCPastes Featured Teams")
    parser.add_argument("--reg", "-r", required=True, help="Regulation letter (e.g. G)")
    args = parser.parse_args()
    reg = args.reg.strip().upper()
    if len(reg) != 1 or not reg.isalpha():
        raise ValueError("--reg must be a single letter")
    Path("teams").mkdir(exist_ok=True)
    scrape_regulation(reg)


if __name__ == "__main__":
    main()
