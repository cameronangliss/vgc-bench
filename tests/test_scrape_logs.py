"""Tests for vgc_bench.scrape_logs (offline-only, no network calls)."""

from vgc_bench.scrape_logs import get_rating


class TestGetRating:
    def test_extracts_p1_rating(self, sample_battle_log):
        rating = get_rating(sample_battle_log, "p1")
        assert rating == 1500

    def test_extracts_p2_rating(self, sample_battle_log):
        rating = get_rating(sample_battle_log, "p2")
        assert rating == 1200

    def test_empty_rating(self):
        log = "|player|p1|Alice|102|\n|win|Alice\n"
        rating = get_rating(log, "p1")
        assert rating is None
