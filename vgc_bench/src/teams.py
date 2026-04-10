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

    def __init__(
        self,
        run_id: int,
        num_teams: int | None,
        reg: str | None,
        custom_team_paths: list[Path] | None = None,
        toggle: TeamToggle | None = None,
        take_from_end: bool = False,
        featured_only: bool = False,
    ):
        """
        Initialize the random team builder.

        When ``reg`` is None, teams are loaded for every available regulation.
        Teams are stored as file paths and loaded on demand in yield_team().

        Args:
            run_id: Training run identifier for deterministic team selection.
            num_teams: Number of teams to include in the pool, or None for all.
            reg: VGC regulation letter (e.g. 'g', 'h', 'i'), or None for all.
            custom_team_paths: Optional explicit list of team file paths (e.g. for
                matchup solving). Overrides reg/num_teams selection.
            toggle: Optional TeamToggle to prevent consecutive identical teams.
            take_from_end: If True, take teams from end of shuffled list.
            featured_only: If True, only pick teams from the featured/ subdirectory.
        """
        self._team_paths: list[Path] = []
        self._reg_paths: dict[str, list[Path]] = {}
        self.available_regs: list[str] | None = None
        self.current_reg: str | None = None
        self.toggle = toggle
        if custom_team_paths is not None:
            self._team_paths = custom_team_paths
        elif reg is None:
            self.available_regs = get_available_regs()
            if num_teams is not None:
                n = len(self.available_regs)
                base, remainder = divmod(num_teams, n)
                for i, r in enumerate(self.available_regs):
                    paths = self._select_paths(
                        run_id,
                        base + (1 if i < remainder else 0),
                        r,
                        take_from_end,
                        featured_only,
                    )
                    if paths:
                        self._reg_paths[r] = paths
                self.available_regs = list(self._reg_paths.keys())
            else:
                for r in self.available_regs:
                    self._reg_paths[r] = self._select_paths(
                        run_id, None, r, take_from_end, featured_only
                    )
            self.pick_reg()
        else:
            self._team_paths = self._select_paths(
                run_id, num_teams, reg, take_from_end, featured_only
            )

    def pick_reg(self) -> None:
        """Select a regulation uniformly at random for the next battle."""
        assert self.available_regs is not None
        self.current_reg = random.choice(self.available_regs)

    @staticmethod
    def _select_paths(
        run_id: int,
        num_teams: int | None,
        reg: str,
        take_from_end: bool,
        featured_only: bool = False,
    ) -> list[Path]:
        """
        Select team file paths for a given regulation.

        Args:
            run_id: Training run identifier for deterministic team selection.
            num_teams: Number of teams to include, or None for all.
            reg: VGC regulation letter.
            take_from_end: If True, take teams from end of shuffled list.
            featured_only: If True, only pick teams from the featured/ subdirectory.

        Returns:
            List of Path objects for the selected teams.
        """
        paths = RandomTeamBuilder.get_team_paths(reg, featured_only)
        effective_num_teams = len(paths) if num_teams is None else num_teams
        teams = list(range(len(paths)))
        random.Random(run_id).shuffle(teams)
        team_ids = (
            teams[-effective_num_teams:]
            if take_from_end
            else teams[:effective_num_teams]
        )
        return [paths[t] for t in team_ids]

    def _load_team(self, path: Path) -> str:
        """Read a team file and return a packed team string."""
        return self.join_team(self.parse_showdown_team(path.read_text()))

    def yield_team(self) -> str:
        """
        Get a team for the next battle, loading from file on demand.

        Returns:
            Packed team string, either toggled or randomly selected.
        """
        if self.available_regs is not None:
            assert self.current_reg is not None
            paths = self._reg_paths[self.current_reg]
        else:
            paths = self._team_paths
        if self.toggle:
            return self._load_team(paths[self.toggle.next(len(paths))])
        else:
            return self._load_team(random.choice(paths))

    @staticmethod
    @cache
    def get_team_paths(reg: str, featured_only: bool = False) -> list[Path]:
        """
        Get all team file paths for a given regulation.

        Args:
            reg: VGC regulation letter (e.g. 'g', 'h', 'i').
            featured_only: If True, only return teams from the featured/ subdirectory.

        Returns:
            List of Path objects pointing to team .txt files.
        """
        reg_path = Path("teams") / f"reg_{reg}"
        if featured_only:
            featured_path = reg_path / "featured"
            if not featured_path.is_dir():
                raise FileNotFoundError(
                    f"No featured/ directory found for regulation {reg} "
                    f"(expected {featured_path})"
                )
            return sorted(featured_path.rglob("*.txt"))
        return sorted(reg_path.rglob("*.txt"))


def get_available_regs() -> list[str]:
    """
    Discover available regulations from the teams directory.

    Returns:
        Sorted list of regulation letters that have team directories.
    """
    teams_dir = Path("teams")
    return sorted(
        d.name.removeprefix("reg_")
        for d in teams_dir.iterdir()
        if d.is_dir() and d.name.startswith("reg_")
    )


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
