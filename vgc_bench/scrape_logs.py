import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import requests
from poke_env.battle import Pokemon
from poke_env.data import to_id_str
from src.utils import all_formats


def scrape_logs(increment: int, battle_format: str) -> bool:
    if os.path.exists(f"data/logs-{battle_format}.json"):
        with open(f"data/logs-{battle_format}.json", "r") as f:
            old_logs = json.load(f)
    else:
        old_logs = {}
    log_times = [int(time) for f, (time, _) in old_logs.items() if f.startswith(battle_format)]
    oldest = min(log_times) if log_times else 2_000_000_000
    newest = max(log_times) if log_times else None
    battle_idents = get_battle_idents(increment, battle_format, oldest, newest)
    battle_idents = [ident for ident in battle_idents if ident not in old_logs.keys()]
    with ThreadPoolExecutor(max_workers=8) as executor:
        log_jsons = list(executor.map(get_log_json, battle_idents))
    new_logs = {
        lj["id"]: (lj["uploadtime"], lj["log"])
        for lj in log_jsons
        if lj is not None
        and lj["log"].count("|poke|p1|") == 6
        and lj["log"].count("|poke|p2|") == 6
        and "|turn|1" in lj["log"]
        and "|showteam|" in lj["log"].split("\n|\n")[0]
        and can_distinguish_team_members(lj["log"].split("\n|\n")[0], "p1")
        and can_distinguish_team_members(lj["log"].split("\n|\n")[0], "p2")
        and "Zoroark" not in lj["log"]
        and "Zorua" not in lj["log"]
        and "|-mega|" not in lj["log"]
    }
    logs = {**old_logs, **new_logs}
    print(f"{battle_format}:", len(logs))
    with open(f"data/logs-{battle_format}.json", "w") as f:
        json.dump(logs, f)
    return len(logs) == len(old_logs)


def can_distinguish_team_members(log: str, player_role: str) -> bool:
    teampreview_mons = [
        Pokemon(9, details=dets)
        for dets in re.findall(r"\|poke\|" + player_role + r"\|([^,|]+)", log)
    ]
    showteam = [line for line in log.split("\n") if line.startswith(f"|showteam|{player_role}|")][0]
    showteam_names = [mon.split("|")[0] for mon in "|".join(showteam.split("|")[3:]).split("]")]
    for mon in teampreview_mons:
        matches = [
            name
            for name in showteam_names
            if mon.base_species == to_id_str(name)
            or mon.base_species in [to_id_str(substr) for substr in name.split("-")]
        ]
        if len(matches) != 1:
            return False
    return True


def get_battle_idents(
    num_battles: int, battle_format: str, oldest: int, newest: int | None
) -> set[str]:
    battle_idents = set()
    # Collecting games that happened after we first started collecting
    if newest is not None:
        oldest_ = 2_000_000_000
        while oldest_ >= newest:
            battle_idents, oldest_ = update_battle_idents(battle_idents, battle_format, oldest_)
    # Collecting games that are older than anything we've seen yet
    while len(battle_idents) < num_battles:
        o = oldest
        battle_idents, oldest = update_battle_idents(battle_idents, battle_format, oldest)
        if oldest == o:
            break
    return battle_idents


def update_battle_idents(
    battle_idents: set[str], battle_format: str, oldest: int
) -> tuple[set[str], int]:
    site = "https://replay.pokemonshowdown.com"
    response = requests.get(f"{site}/search.json?format={battle_format}&before={oldest + 1}")
    new_battle_jsons = json.loads(response.text)
    oldest = new_battle_jsons[-1]["uploadtime"]
    battle_idents |= {bj["id"] for bj in new_battle_jsons if bj["id"].startswith(battle_format)}
    return battle_idents, oldest


def get_log_json(ident: str) -> dict[str, Any] | None:
    site = "https://replay.pokemonshowdown.com"
    response = requests.get(f"{site}/{ident}.json")
    if response:
        return json.loads(response.text)


def get_rating(log: str, role: str) -> int | None:
    start_index = log.index(f"|player|{role}|")
    rating_str = log[start_index : log.index("\n", start_index)].split("|")[5]
    rating = int(rating_str) if rating_str else None
    return rating


if __name__ == "__main__":

    def run(f: str):
        done = False
        while not done:
            done = scrape_logs(4000, f)
        with open(f"data/logs-{f}.json", "r") as file:
            log_dict = json.load(file)
            logs = [log for _, log in log_dict.values()]
        players_in_range = lambda logs, low, high: len(
            [log for log in logs if low <= (get_rating(log, "p1") or 0) <= high]
        ) + len([log for log in logs if low <= (get_rating(log, "p2") or 0) <= high])
        print(
            f"""
{f} stats:
most recent log date = {max([t for t, _ in log_dict.values()])}
total logs = {len(logs)}
# of players w/ rating...
    unrated:   {len([log for log in logs if get_rating(log, "p1") is None]) + len([log for log in logs if get_rating(log, "p2") is None])}
    1000-1099: {players_in_range(logs, 1000, 1099)}
    1100-1199: {players_in_range(logs, 1100, 1199)}
    1200-1299: {players_in_range(logs, 1200, 1299)}
    1300-1399: {players_in_range(logs, 1300, 1399)}
    1400-1499: {players_in_range(logs, 1400, 1499)}
    1500-1599: {players_in_range(logs, 1500, 1599)}
    1600-1699: {players_in_range(logs, 1600, 1699)}
    1700-1799: {players_in_range(logs, 1700, 1799)}
    1800+:     {players_in_range(logs, 1800, 3000)}
""",
            flush=True,
        )

    with ThreadPoolExecutor(max_workers=len(all_formats)) as executor:
        executor.map(run, all_formats)
