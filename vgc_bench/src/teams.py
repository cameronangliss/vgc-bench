import random
from functools import cache
from pathlib import Path

from poke_env.teambuilder import Teambuilder, TeambuilderPokemon


class TeamToggle:
    def __init__(self, num_teams: int):
        assert num_teams > 1
        self.num_teams = num_teams
        self._last_value = None

    def next(self) -> int:
        if self._last_value is None:
            self._last_value = random.choice(range(self.num_teams))
            return self._last_value
        else:
            value = random.choice(
                [t for t in range(self.num_teams) if t != self._last_value]
            )
            self._last_value = None
            return value


class RandomTeamBuilder(Teambuilder):
    teams: list[str]

    def __init__(
        self,
        run_id: int,
        num_teams: int,
        battle_format: str,
        toggle: TeamToggle | None = None,
        take_from_end: bool = False,
    ):
        self.teams = []
        self.toggle = toggle
        paths = get_team_paths(battle_format)
        teams = get_team_ids(run_id, num_teams, battle_format, take_from_end)
        for team_path in [paths[t] for t in teams]:
            parsed_team = self.parse_showdown_team(team_path.read_text())
            packed_team = self.join_team(parsed_team)
            self.teams.append(packed_team)

    def yield_team(self) -> str:
        if self.toggle:
            return self.teams[self.toggle.next()]
        else:
            return random.choice(self.teams)


def calc_team_similarity_score(team1: str, team2: str):
    """
    Roughly measures similarity between two teams on a scale of 0-1
    """
    mon_builders1 = Teambuilder.parse_showdown_team(team1)
    mon_builders2 = Teambuilder.parse_showdown_team(team2)
    match_pairs: list[tuple[TeambuilderPokemon, TeambuilderPokemon]] = []
    for mon_builder in mon_builders1:
        matches = [
            p
            for p in mon_builders2
            if (p.species or p.nickname)
            == (mon_builder.species or mon_builder.nickname)
        ]
        if matches:
            match_pairs += [(mon_builder, matches[0])]
    similarity_score = 0
    for mon1, mon2 in match_pairs:
        if mon1.item == mon2.item:
            similarity_score += 1
        if mon1.ability == mon2.ability:
            similarity_score += 1
        if mon1.tera_type == mon2.tera_type:
            similarity_score += 1
        ev_dist = sum([abs(ev1 - ev2) for ev1, ev2 in zip(mon1.evs, mon2.evs)]) / (
            2 * 508
        )
        similarity_score += 1 - ev_dist
        if mon1.nature == mon2.nature:
            similarity_score += 1
        iv_dist = sum([abs(iv1 - iv2) for iv1, iv2 in zip(mon1.ivs, mon2.ivs)]) / (
            6 * 31
        )
        similarity_score += 1 - iv_dist
        for move in mon1.moves:
            if move in mon2.moves:
                similarity_score += 1
    return round(similarity_score / 60, ndigits=3)


def find_run_id(team_ids: set[int], battle_format: str) -> int:
    """
    Finds lowest run_id > 0 that will have team_ids in the beginning of its team order
    """
    run_id = 1
    while set(get_team_ids(run_id, len(team_ids), battle_format, False)) != team_ids:
        run_id += 1
    return run_id


def get_team_ids(
    run_id: int, num_teams: int, battle_format: str, take_from_end: bool
) -> list[int]:
    paths = get_team_paths(battle_format)
    teams = list(range(len(paths)))
    random.Random(run_id).shuffle(teams)
    return teams[-num_teams:] if take_from_end else teams[:num_teams]


@cache
def get_team_paths(battle_format: str) -> list[Path]:
    reg_path = Path("data") / "teams" / battle_format[-4:]
    return list(reg_path.rglob("*.txt"))
