"""
Team management module for VGC-Bench.

Provides team building utilities including random team selection, team toggling
to prevent mirror matches, and team similarity scoring for analysis.
"""

import random
from functools import cache
from pathlib import Path

from poke_env.teambuilder import Teambuilder, TeambuilderPokemon


class TeamToggle:
    """
    Alternating team selector to prevent mirror matches.

    Ensures consecutive team selections are always different, which is useful
    in self-play training to prevent agents from facing identical teams.

    Attributes:
        num_teams: Total number of teams available for selection.
    """

    def __init__(self, num_teams: int):
        """
        Initialize the team toggle.

        Args:
            num_teams: Number of teams to toggle between (must be > 1).
        """
        assert num_teams > 1
        self.num_teams = num_teams
        self._last_value = None

    def next(self) -> int:
        """
        Get the next team index, guaranteed different from the previous call.

        Returns:
            Team index between 0 and num_teams-1.
        """
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
    """
    Team builder that randomly selects from a pool of pre-built teams.

    Loads teams from the data directory based on the battle format and
    provides random team selection for battles. Optionally uses TeamToggle
    to prevent mirror matches.

    Attributes:
        teams: List of packed team strings ready for battle.
        toggle: Optional TeamToggle for preventing mirror matches.
    """

    teams: list[str]

    def __init__(
        self,
        run_id: int,
        num_teams: int,
        battle_format: str,
        team1: str | None = None,
        team2: str | None = None,
        toggle: TeamToggle | None = None,
        take_from_end: bool = False,
    ):
        """
        Initialize the random team builder.

        Args:
            run_id: Training run identifier for deterministic team selection.
            num_teams: Number of teams to include in the pool.
            battle_format: Pokemon Showdown format string (e.g., 'gen9vgc2024regh').
            team1: Optional team string for matchup solving (requires team2).
            team2: Optional team string for matchup solving (requires team1).
            toggle: Optional TeamToggle to prevent consecutive identical teams.
            take_from_end: If True, take teams from end of shuffled list.
        """
        self.teams = []
        self.toggle = toggle
        paths = get_team_paths(battle_format)
        if team1 is not None and team2 is not None:
            parsed_team1 = self.parse_showdown_team(team1)
            packed_team1 = self.join_team(parsed_team1)
            self.teams.append(packed_team1)
            parsed_team2 = self.parse_showdown_team(team2)
            packed_team2 = self.join_team(parsed_team2)
            self.teams.append(packed_team2)
            return
        teams = get_team_ids(run_id, num_teams, battle_format, take_from_end)
        for team_path in [paths[t] for t in teams]:
            parsed_team = self.parse_showdown_team(team_path.read_text())
            packed_team = self.join_team(parsed_team)
            self.teams.append(packed_team)

    def yield_team(self) -> str:
        """
        Get a team for the next battle.

        Returns:
            Packed team string, either toggled or randomly selected.
        """
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
    """
    Get deterministically shuffled team indices for a given run.

    Args:
        run_id: Seed for deterministic shuffling.
        num_teams: Number of team indices to return.
        battle_format: Pokemon Showdown format string.
        take_from_end: If True, take teams from end of shuffled list.

    Returns:
        List of team indices.
    """
    paths = get_team_paths(battle_format)
    teams = list(range(len(paths)))
    random.Random(run_id).shuffle(teams)
    return teams[-num_teams:] if take_from_end else teams[:num_teams]


@cache
def get_team_paths(battle_format: str) -> list[Path]:
    """
    Get all team file paths for a given battle format.

    Args:
        battle_format: Pokemon Showdown format string (extracts last 4 chars
            as regulation identifier, e.g., 'regh' from 'gen9vgc2024regh').

    Returns:
        List of Path objects pointing to team .txt files.
    """
    reg_path = Path("teams") / battle_format[-4:]
    return sorted(reg_path.rglob("*.txt"))
