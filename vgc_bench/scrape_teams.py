"""
Scrapes competitive VGC team data from the VGCPastes Google Sheets database.
"""

import argparse
import csv
import re
import subprocess
from pathlib import Path
from urllib.parse import quote_plus

import requests

from vgc_bench.src.utils import format_map

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
        if "featured" not in name.lower() and f"regulation {reg}" in name.lower()
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
    resp.encoding = "utf-8"
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
        header = block[0]
        # Strip nicknames: "Nickname (Species) ..." -> "Species ..."
        header = re.sub(r"^.+\(([^()]{2,})\)", r"\1", header, count=1).strip()
        block[0] = header
        asone = (
            "As One (Glastrier)"
            if "calyrex-ice" in header.lower()
            else "As One (Spectrier)"
        )
        # Fix Tauros-Paldea-Water -> Tauros-Paldea-Aqua (pokepaste alias)
        header = header.replace("Tauros-Paldea-Water", "Tauros-Paldea-Aqua")
        block[0] = header
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
        # Event Pokemon with required IVs: {species_substring: {stat: value}}
        # Only applied when an IVs line already exists with a conflicting value.
        EVENT_IVS = {
            "raging bolt": {"Atk": 20},
            "iron crown": {"Atk": 20},
            "iron boulder": {"Atk": 20},
            "terapagos": {"Atk": 15},
            "ogerpon-hearthflame": {"SpA": 20},
            "ogerpon-wellspring": {"SpA": 20},
            "ogerpon-cornerstone": {"SpA": 20},
            "magearna": {"Atk": 30},
        }
        required_ivs: dict[str, int] = {}
        for species, ivs in EVENT_IVS.items():
            if species in header_lower:
                required_ivs = ivs
                break
        SHINY_LOCKED = [
            "enamorus",
            "ursaluna-bloodmoon",
            "ogerpon",
            "terapagos",
            "walking wake",
            "iron leaves",
            "iron boulder",
            "iron crown",
            "gouging fire",
            "raging bolt",
        ]
        # Valid Showdown team format fields (applied to non-header lines)
        FIELD_PATTERN = re.compile(
            r"^\s*("
            r"Ability:|Level:|EVs:|IVs:|Tera Type:|Shiny:|Happiness:|"
            r"Gigantamax:|Hidden Power:|"
            r"- |.+Nature$"
            r")"
        )
        new_lines = []
        for i, line in enumerate(block):
            if re.match(
                r"\s*ivs:", line, re.IGNORECASE
            ) and not line.lstrip().startswith("IVs:"):
                line = re.sub(r"(?i)^(\s*)ivs:", r"\1IVs:", line)
            # Space out EV/IV slash separators
            if re.match(r"\s*(EVs|IVs):", line):
                line = re.sub(r"\s*/\s*", " / ", line)
                # Normalize long-form stat names to short forms
                line = re.sub(r"Sp\.\s*Atk", "SpA", line)
                line = re.sub(r"Sp\.\s*Def", "SpD", line)
            # Drop non-header lines that aren't valid fields
            # (e.g. damage calc notes, comments left in pokepaste)
            if i > 0 and not FIELD_PATTERN.match(line):
                continue
            if locked_tera and re.match(r"\s*Tera Type:", line):
                line = f"Tera Type: {locked_tera}"
            if re.match(r"\s*Shiny:", line, re.IGNORECASE) and any(
                s in header_lower for s in SHINY_LOCKED
            ):
                continue
            if required_ivs and re.match(r"\s*IVs:", line):
                for stat, val in required_ivs.items():
                    if re.search(rf"\d+\s*{stat}\b", line):
                        line = re.sub(rf"\d+(\s*{stat}\b)", rf"{val}\1", line)
            m = re.match(r"^(\s*Ability:\s*)(.*?)\s*$", line, re.IGNORECASE)
            if m and re.sub(r"[^a-z0-9]", "", m.group(2).lower()) == "asone":
                line = f"{m.group(1)}{asone}"
            if re.match(r"\s*Level:", line):
                line = "Level: 50"
            new_lines.append(line)
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


class TeamValidator:
    """Persistent Showdown team validator using a long-running Node subprocess."""

    def __init__(self):
        proc = subprocess.Popen(
            ["node", "validate-teams-batch.js"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            cwd="pokemon-showdown",
        )
        assert proc.stdin is not None and proc.stdout is not None
        self._proc = proc
        self._stdin = proc.stdin
        self._stdout = proc.stdout

    def validate(self, team_text: str, regulation: str) -> str | None:
        """Validate a team. Returns None if valid, or an error string."""
        import json

        fmt = format_map[regulation.lower()]
        line = json.dumps({"format": fmt, "team": team_text})
        self._stdin.write(line + "\n")
        self._stdin.flush()
        result = json.loads(self._stdout.readline())
        if result["valid"]:
            return None
        return "\n".join(result["errors"])

    def close(self):
        self._stdin.close()
        self._proc.wait()


def scrape_regulation(regulation: str, validator: TeamValidator) -> None:
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
                (i for i, r in enumerate(rows) if r and "Pokepaste" in r), None
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
                num_pokemon = team_text.strip().split("\n\n")
                if len(num_pokemon) != 6:
                    stats["invalid"] += 1
                    continue
                error = validator.validate(team_text, regulation)
                if error:
                    stats["invalid"] += 1
                    continue
                seen_ids.add(team_id)
                (out_dir / f"{team_id}.txt").write_text(team_text)
                stats["saved"] += 1
    total = existing + stats["saved"]
    print(f"Saved {stats['saved']} new teams to {reg_dir} ({total} total)")
    print(f"Skipped {stats['invalid']} invalid")


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
    validator = TeamValidator()
    try:
        if args.reg:
            reg = args.reg.strip().upper()
            if len(reg) != 1 or not reg.isalpha():
                raise ValueError("--reg must be a single letter")
            scrape_regulation(reg, validator)
        else:
            session = requests.Session()
            regs = discover_regulations(fetch_sheet_names(session))
            print(f"Found regulations: {', '.join(regs)}")
            for reg in regs:
                print(f"\n--- Regulation {reg} ---")
                scrape_regulation(reg, validator)
    finally:
        validator.close()


if __name__ == "__main__":
    main()
