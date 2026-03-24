"""Tests for vgc_bench.src.llm (offline-only, no model downloads)."""

from vgc_bench.src.llm import LLMPlayer


class TestExplainBoost:
    def test_zero_boost(self):
        assert LLMPlayer.explain_boost(0) == 1.0

    def test_positive_boost(self):
        assert LLMPlayer.explain_boost(1) == 1.5
        assert LLMPlayer.explain_boost(2) == 2.0
        assert LLMPlayer.explain_boost(6) == 4.0

    def test_negative_boost(self):
        assert LLMPlayer.explain_boost(-1) == 0.67
        assert LLMPlayer.explain_boost(-2) == 0.5
        assert LLMPlayer.explain_boost(-6) == 0.25


class TestExplainBoosts:
    def test_no_boosts(self):
        boosts = {
            "atk": 0,
            "def": 0,
            "spa": 0,
            "spd": 0,
            "spe": 0,
            "accuracy": 0,
            "evasion": 0,
        }
        result = LLMPlayer.explain_boosts(boosts)
        assert "None" in result

    def test_with_boosts(self):
        boosts = {
            "atk": 2,
            "def": -1,
            "spa": 0,
            "spd": 0,
            "spe": 0,
            "accuracy": 0,
            "evasion": 0,
        }
        result = LLMPlayer.explain_boosts(boosts)
        assert "Attack" in result
        assert "Defense" in result
        assert "Special Attack" not in result
