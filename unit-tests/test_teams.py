"""Unit tests for vgc_bench.src.teams in-memory logic."""

from vgc_bench.src.teams import TeamToggle, calc_team_similarity_score


class TestTeamToggle:
    def test_alternates_values(self):
        toggle = TeamToggle()
        v1 = toggle.next(4)
        v2 = toggle.next(4)
        assert v1 != v2
        assert 0 <= v1 < 4
        assert 0 <= v2 < 4

    def test_many_calls_no_consecutive_duplicates(self):
        toggle = TeamToggle()
        values = [toggle.next(10) for _ in range(20)]
        for i in range(0, len(values) - 1, 2):
            assert values[i] != values[i + 1]

    def test_two_teams_always_alternates(self):
        toggle = TeamToggle()
        v1 = toggle.next(2)
        v2 = toggle.next(2)
        assert {v1, v2} == {0, 1}


class TestCalcTeamSimilarityScore:
    def test_identical_teams(self, sample_team_text):
        score = calc_team_similarity_score(sample_team_text, sample_team_text)
        assert score == 1.0

    def test_score_range(self, sample_team_text):
        score = calc_team_similarity_score(sample_team_text, sample_team_text)
        assert 0.0 <= score <= 1.0
