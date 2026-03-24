"""
Team management module for VGC-Bench.

Provides team building utilities including random team selection, team toggling
to prevent mirror matches, multi-regulation support, and team similarity
scoring for analysis.
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

    def __init__(self):
        """Initialize the team toggle."""
        self._last_value = None

    def next(self, num_teams: int) -> int:
        """
        Get the next team index, guaranteed different from the previous call.

        Args:
            num_teams: Number of teams to choose from (must be > 1).

        Returns:
            Team index between 0 and num_teams-1.
        """
        assert num_teams > 1
        if self._last_value is None:
            self._last_value = random.choice(range(num_teams))
            return self._last_value
        else:
            value = random.choice(
                [t for t in range(num_teams) if t != self._last_value]
            )
            self._last_value = None
            return value


class RandomTeamBuilder(Teambuilder):
    """
    Team builder that randomly selects from a pool of pre-built teams.

    Loads teams from the data directory based on the battle format and
    provides random team selection for battles. Optionally uses TeamToggle
    to prevent mirror matches. When ``reg`` is None, loads teams for all
    available regulations and exposes ``available_regs`` / ``current_reg``
    for callers to control which regulation's teams are yielded.

    Attributes:
        teams: List of packed team strings ready for battle (single-reg mode).
        available_regs: List of regulation letters when in multi-reg mode.
        current_reg: The regulation whose teams will be yielded next.
        toggle: Optional TeamToggle for preventing mirror matches.
    """

    teams: list[str]

    def __init__(
        self,
        run_id: int,
        num_teams: int | None,
        reg: str | None,
        team1: str | None = None,
        team2: str | None = None,
        toggle: TeamToggle | None = None,
    ):
        """
        Initialize the random team builder.

        When ``reg`` is None, teams are loaded for every available regulation.

        Args:
            run_id: Training run identifier for deterministic team selection.
            num_teams: Number of teams to include in the pool, or None for all.
            reg: VGC regulation letter (e.g. 'g', 'h', 'i'), or None for all.
            team1: Optional team string for matchup solving (requires team2).
            team2: Optional team string for matchup solving (requires team1).
            toggle: Optional TeamToggle to prevent consecutive identical teams.
        """
        self.teams = []
        self._reg_teams: dict[str, list[str]] = {}
        self.available_regs: list[str] | None = None
        self.current_reg: str | None = None
        self.toggle = toggle
        if team1 is not None and team2 is not None:
            parsed_team1 = self.parse_showdown_team(team1)
            packed_team1 = self.join_team(parsed_team1)
            self.teams.append(packed_team1)
            parsed_team2 = self.parse_showdown_team(team2)
            packed_team2 = self.join_team(parsed_team2)
            self.teams.append(packed_team2)
            return
        if reg is None:
            self.available_regs = get_available_regs()
            self.current_reg = random.choice(self.available_regs)
            for r in self.available_regs:
                self._reg_teams[r] = self._load_teams(run_id, num_teams, r)
        else:
            self.teams = self._load_teams(run_id, num_teams, reg)

    def pick_reg(self) -> None:
        """Select a random regulation for the next battle."""
        assert self.available_regs is not None
        self.current_reg = random.choice(self.available_regs)

    def _load_teams(self, run_id: int, num_teams: int | None, reg: str) -> list[str]:
        """
        Load and pack teams for a given regulation.

        Args:
            run_id: Training run identifier for deterministic team selection.
            num_teams: Number of teams to include, or None for all.
            reg: VGC regulation letter.

        Returns:
            List of packed team strings.
        """
        paths = get_team_paths(reg)
        effective_num_teams = len(paths) if num_teams is None else num_teams
        team_ids = get_team_ids(run_id, effective_num_teams, reg)
        teams = []
        for team_path in [paths[t] for t in team_ids]:
            parsed_team = self.parse_showdown_team(team_path.read_text())
            packed_team = self.join_team(parsed_team)
            teams.append(packed_team)
        return teams

    def yield_team(self) -> str:
        """
        Get a team for the next battle.

        Returns:
            Packed team string, either toggled or randomly selected.
        """
        if self.available_regs is not None:
            assert self.current_reg is not None
            teams = self._reg_teams[self.current_reg]
        else:
            teams = self.teams
        if self.toggle:
            return teams[self.toggle.next(len(teams))]
        else:
            return random.choice(teams)


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


def find_run_id(team_ids: set[int], reg: str) -> int:
    """
    Finds lowest run_id > 0 that will have team_ids in the beginning of its team order
    """
    run_id = 1
    while set(get_team_ids(run_id, len(team_ids), reg, False)) != team_ids:
        run_id += 1
    return run_id


def get_team_ids(
    run_id: int, num_teams: int, reg: str, take_from_end: bool = False
) -> list[int]:
    """
    Get deterministically shuffled team indices for a given run.

    Args:
        run_id: Seed for deterministic shuffling.
        num_teams: Number of team indices to return.
        reg: VGC regulation letter (e.g. 'g', 'h', 'i').
        take_from_end: If True, take teams from end of shuffled list.

    Returns:
        List of team indices.
    """
    paths = get_team_paths(reg)
    teams = list(range(len(paths)))
    random.Random(run_id).shuffle(teams)
    return teams[-num_teams:] if take_from_end else teams[:num_teams]


@cache
def get_team_paths(reg: str) -> list[Path]:
    """
    Get all team file paths for a given regulation.

    Args:
        reg: VGC regulation letter (e.g. 'g', 'h', 'i').

    Returns:
        List of Path objects pointing to team .txt files.
    """
    reg_path = Path("teams") / f"reg{reg}"
    return sorted(reg_path.rglob("*.txt"))


def get_available_regs() -> list[str]:
    """
    Discover available regulations from the teams directory.

    Returns:
        Sorted list of regulation letters that have team directories.
    """
    teams_dir = Path("teams")
    return sorted(
        d.name.removeprefix("reg")
        for d in teams_dir.iterdir()
        if d.is_dir() and d.name.startswith("reg")
    )
