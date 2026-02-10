"""
Data scraping module for VGC-Bench.

Downloads Pokemon data (abilities, items, moves) from Pokemon Showdown and
extracts compact name lists used for feature indexing.
"""

import json
import re
from pathlib import Path

import requests


def update_name_list(url: str, file: str, extras: tuple[str, ...] = ()):
    """
    Download Pokemon data and save a list of valid entry names.

    Fetches a data file from Pokemon Showdown and stores entry names.
    The resulting lists are used to map ability/item/move names to
    stable integer ids.

    Args:
        url: Base URL for the Pokemon Showdown data files.
        file: Filename to download (e.g., "abilities.js").
        extras: Additional names to prepend to the list.
    """
    response = requests.get(f"{url}/{file}")
    if ".json" in file:
        json_text = response.text
    else:
        js_text = response.text
        i = js_text.index("{")
        js_literal = js_text[i:-1]
        json_text = re.sub(r"([{,])([a-zA-Z0-9_]+)(:)", r'\1"\2"\3', js_literal)
        file += "on"
    dex = json.loads(json_text)
    names = list(dict.fromkeys([*extras, *dex.keys()]))
    with open(f"data/{file}", "w") as f:
        json.dump(names, f)


if __name__ == "__main__":
    Path("data").mkdir(exist_ok=True)
    update_name_list(
        "https://play.pokemonshowdown.com/data", "abilities.js", extras=("null", "")
    )
    update_name_list(
        "https://play.pokemonshowdown.com/data",
        "items.js",
        extras=("null", "", "unknown_item"),
    )
    update_name_list(
        "https://play.pokemonshowdown.com/data", "moves.js", extras=("no move",)
    )
