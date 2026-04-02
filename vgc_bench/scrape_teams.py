"""
Scrapes competitive VGC team data from the VGCPastes Google Sheets database.
"""

import argparse
import csv
import re
from pathlib import Path
from urllib.parse import quote_plus

import requests
from poke_env.teambuilder import Teambuilder


SHEET_ID = "1axlwmzPA49rYkqXh7zHvAtSP-TKbM0ijGYBPRflLSWw"
SHEET_EDIT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"
SHEET_GVIZ_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq"


def fetch_sheet_names(session: requests.Session) -> list[str]:
    """Fetch sheet names from the VGCPastes spreadsheet."""
    resp = session.get(SHEET_EDIT_URL, timeout=30)
    resp.raise_for_status()
    names = re.findall(r"docs-sheet-tab-caption\">([^<]+)<", resp.text)
    return list(dict.fromkeys(names))  # dedupe preserving order


def get_regulation_sheets(
    all_sheets: list[str], regulation: str
) -> tuple[list[str], list[str]]:
    """Find featured and regular team sheets for a regulation."""
    reg = regulation.lower()
    featured = [
        name
        for name in all_sheets
        if "featured" in name.lower()
        and "presentable" not in name.lower()
        and (f"reg {reg}" in name.lower() or f"regulation {reg}" in name.lower())
    ]
    regular = [
        name
        for name in all_sheets
        if "featured" not in name.lower()
        and f"regulation {reg}" in name.lower()
    ]
    if not regular:
        regular = [f"SV Regulation {regulation.upper()}"]
    return featured, regular


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
    """Normalize team formatting, fix legality issues, and disambiguate abilities."""
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
        # Join everything before "Ability:" into one line (fixes multi-byte
        # Unicode nicknames split across lines), then strip the nickname.
        header = ""
        while block and not re.match(r"\s*Ability:", block[0]):
            header += block.pop(0)
        nick_match = re.match(r"^.+?\(([^)]{2,})\)\s*(.*)$", header)
        if nick_match:
            header = f"{nick_match.group(1)} {nick_match.group(2)}".strip()
        block.insert(0, header)
        asone = (
            "As One (Glastrier)"
            if "calyrex-ice" in header.lower()
            else "As One (Spectrier)"
        )
        # Fix Urshifu form based on moves
        has_surging = any("Surging Strikes" in line for line in block)
        if has_surging and "urshifu-rapid-strike" not in header.lower():
            header = re.sub(r"\bUrshifu\b", "Urshifu-Rapid-Strike", header)
            block[0] = header
        # Fix Ogerpon locked Tera types
        OGERPON_TERA = {
            "ogerpon-cornerstone": "Rock",
            "ogerpon-hearthflame": "Fire",
            "ogerpon-wellspring": "Water",
        }
        header_lower = header.lower()
        locked_tera = next(
            (t for form, t in OGERPON_TERA.items() if form in header_lower), None
        )
        is_raging_bolt = "raging bolt" in header_lower
        has_correct_atk_iv = any(
            re.search(r"IVs:.*\b20\s*Atk\b", line) for line in block
        )
        new_lines = []
        for line in block:
            if locked_tera and re.match(r"\s*Tera Type:", line):
                line = f"Tera Type: {locked_tera}"
            if is_raging_bolt and re.match(r"\s*Shiny:\s*Yes\s*$", line, re.IGNORECASE):
                continue
            if is_raging_bolt and re.match(r"\s*IVs:", line) and not has_correct_atk_iv:
                # Fix Atk IV to 20 in existing IVs line
                if re.search(r"\d+\s*Atk", line):
                    line = re.sub(r"\d+(\s*Atk)", r"20\1", line)
                else:
                    line = re.sub(r"(IVs:\s*)", r"\g<1>20 Atk / ", line)
                has_correct_atk_iv = True
            m = re.match(r"^(\s*Ability:\s*)(.*?)\s*$", line, re.IGNORECASE)
            if m and re.sub(r"[^a-z0-9]", "", m.group(2).lower()) == "asone":
                line = f"{m.group(1)}{asone}"
            if re.match(r"\s*Level:", line):
                line = "Level: 50"
            new_lines.append(line)
        if is_raging_bolt and not has_correct_atk_iv:
            # No IVs line at all; insert after Nature line
            insert_idx = next(
                (i + 1 for i, line in enumerate(new_lines) if line.endswith("Nature")),
                len(new_lines),
            )
            new_lines.insert(insert_idx, "IVs: 20 Atk")
        if not any(re.match(r"\s*Level:", line) for line in new_lines):
            # Insert Level: 50 after Ability line
            insert_idx = next(
                (
                    i + 1
                    for i, line in enumerate(new_lines)
                    if re.match(r"\s*Ability:", line)
                ),
                1,
            )
            new_lines.insert(insert_idx, "Level: 50")
        normalized.append("\n".join(new_lines))
    return "\n\n".join(normalized) + "\n"


def has_duplicate_items(team_text: str) -> bool:
    """Check if any item appears more than once on a team."""
    items = re.findall(r"@\s*(.+)$", team_text, re.MULTILINE)
    items = [i.strip() for i in items]
    return len(items) != len(set(items))


def all_pokemon_have_evs(team_text: str) -> bool:
    """Check that every Pokemon block in the team has an EVs line."""
    blocks = re.split(r"\n\n+", team_text.strip())
    return all(
        any(re.match(r"\s*EVs:", line) for line in block.splitlines())
        for block in blocks
        if block.strip()
    )


def scrape_regulation(regulation: str) -> None:
    """Scrape teams for a VGC regulation from featured and regular sheets."""
    reg_dir = Path("teams") / f"reg_{regulation.lower()}"
    reg_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    featured_sheets, regular_sheets = get_regulation_sheets(
        fetch_sheet_names(session), regulation
    )
    featured_dir = reg_dir / "featured"
    if featured_sheets:
        featured_dir.mkdir(parents=True, exist_ok=True)
    seen_ids = {p.stem for p in reg_dir.rglob("*.txt")}
    existing = len(seen_ids)
    stats = {"saved": 0, "invalid": 0}
    for is_featured, sheets in [(True, featured_sheets), (False, regular_sheets)]:
        out_dir = featured_dir if is_featured else reg_dir
        for sheet in sheets:
            rows = fetch_csv(session, sheet)
            header_idx = next(
                (
                    i
                    for i, r in enumerate(rows)
                    if r and "Pokepaste" in r
                ),
                None,
            )
            if header_idx is None:
                continue
            header = rows[header_idx]
            evs_col = header.index("EVs")
            paste_col = header.index("Pokepaste")
            for row in rows[header_idx + 1 :]:
                if len(row) <= max(evs_col, paste_col):
                    continue
                team_id = row[0].strip()
                if not team_id or team_id in seen_ids:
                    continue
                if row[evs_col].strip().lower() != "yes":
                    continue
                pokepaste = row[paste_col].strip()
                if not pokepaste.startswith("https://pokepast.es/"):
                    continue
                team_text = fetch_team(session, pokepaste)
                if not all_pokemon_have_evs(team_text) or has_duplicate_items(
                    team_text
                ):
                    continue
                if re.search(r"@\s*Electric Gem\s*$", team_text, re.MULTILINE):
                    stats["invalid"] += 1
                    continue
                try:
                    Teambuilder.parse_showdown_team(team_text)
                except KeyError:
                    continue
                seen_ids.add(team_id)
                (out_dir / f"{team_id}.txt").write_text(team_text)
                stats["saved"] += 1
    total = existing + stats["saved"]
    print(f"Saved {stats['saved']} new teams to {reg_dir} ({total} total)")
    print(
        f"Skipped {stats['invalid']} invalid"
    )


def discover_regulations(sheet_names: list[str]) -> list[str]:
    """Extract available regulation letters from sheet names."""
    regs = set()
    for name in sheet_names:
        m = re.search(r"regulation\s+([a-z])", name, re.IGNORECASE)
        if m:
            regs.add(m.group(1).upper())
    return sorted(regs)


def main():
    parser = argparse.ArgumentParser(description="Scrape VGCPastes Teams")
    parser.add_argument("--reg", "-r", help="Regulation letter (e.g. G). Omit for all.")
    args = parser.parse_args()
    Path("teams").mkdir(exist_ok=True)
    if args.reg:
        reg = args.reg.strip().upper()
        if len(reg) != 1 or not reg.isalpha():
            raise ValueError("--reg must be a single letter")
        scrape_regulation(reg)
    else:
        session = requests.Session()
        regs = discover_regulations(fetch_sheet_names(session))
        print(f"Found regulations: {', '.join(regs)}")
        for reg in regs:
            print(f"\n--- Regulation {reg} ---")
            scrape_regulation(reg)


if __name__ == "__main__":
    main()
