"""Integration tests for vgc_bench.src.teams filesystem-dependent operations.

These tests read real team files from the teams/ directory on disk and verify
deterministic shuffling, path discovery, and cross-team similarity scoring.
"""

from vgc_bench.src.teams import (
    calc_team_similarity_score,
    get_available_regs,
    get_team_ids,
    get_team_paths,
)


class TestGetTeamIds:
    def test_deterministic(self):
        ids1 = get_team_ids(1, 10, "g")
        ids2 = get_team_ids(1, 10, "g")
        assert ids1 == ids2

    def test_different_seeds(self):
        ids1 = get_team_ids(1, 10, "g")
        ids2 = get_team_ids(2, 10, "g")
        assert ids1 != ids2

    def test_correct_length(self):
        ids = get_team_ids(1, 5, "g")
        assert len(ids) == 5

    def test_take_from_end(self):
        ids_front = get_team_ids(1, 5, "g", take_from_end=False)
        ids_back = get_team_ids(1, 5, "g", take_from_end=True)
        assert ids_front != ids_back


class TestGetTeamPaths:
    def test_returns_paths(self):
        paths = get_team_paths("g")
        assert len(paths) > 0
        for p in paths:
            assert p.suffix == ".txt"
            assert p.exists()


class TestGetAvailableRegs:
    def test_returns_regs(self):
        regs = get_available_regs()
        assert len(regs) > 0
        for r in regs:
            assert len(r) == 1
            assert r.isalpha()

    def test_sorted(self):
        regs = get_available_regs()
        assert regs == sorted(regs)


class TestCalcTeamSimilarityScoreFromDisk:
    def test_different_teams(self):
        paths = get_team_paths("g")
        if len(paths) >= 2:
            t1 = paths[0].read_text()
            t2 = paths[-1].read_text()
            score = calc_team_similarity_score(t1, t2)
            assert 0.0 <= score <= 1.0
