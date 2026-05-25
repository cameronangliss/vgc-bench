"""Unit tests for vgc_bench.src.utils."""

import numpy as np
import torch

from vgc_bench.src.utils import (
    ENT,
    EVT,
    FIELDS_PER_EVENT,
    NUM_ENTITIES,
    NUM_EVENT_TYPES,
    NUM_POSITIONS,
    POS,
    LearningStyle,
    act_len,
    format_map,
    get_reg_from_format,
    is_vgc_format,
    max_events,
    set_global_seed,
)


class TestLearningStyle:
    def test_is_self_play(self):
        assert LearningStyle.PURE_SELF_PLAY.is_self_play is True
        assert LearningStyle.FICTITIOUS_PLAY.is_self_play is True
        assert LearningStyle.DOUBLE_ORACLE.is_self_play is True
        assert LearningStyle.EXPLOITER.is_self_play is False

    def test_abbrev(self):
        assert LearningStyle.EXPLOITER.abbrev == "ex"
        assert LearningStyle.PURE_SELF_PLAY.abbrev == "sp"
        assert LearningStyle.FICTITIOUS_PLAY.abbrev == "fp"
        assert LearningStyle.DOUBLE_ORACLE.abbrev == "do"

    def test_all_members_have_abbrev(self):
        for style in LearningStyle:
            assert isinstance(style.abbrev, str)
            assert len(style.abbrev) == 2


class TestConstants:
    def test_act_len(self):
        assert act_len == 107

    def test_event_token_constants(self):
        assert max_events == 256
        assert FIELDS_PER_EVENT == 15
        assert NUM_EVENT_TYPES > 0
        assert NUM_POSITIONS > 0
        assert NUM_ENTITIES > 0

    def test_evt_has_required_keys(self):
        for key in ["PAD", "BOS", "SEP", "REQUEST", "TEAM", "TEAM_MOVES"]:
            assert key in EVT

    def test_pos_has_required_keys(self):
        for key in ["NONE", "ally_a", "ally_b", "opp_a", "opp_b"]:
            assert key in POS

    def test_ent_vocab(self):
        assert ENT["PAD"] == 0
        assert ENT.size == NUM_ENTITIES

    def test_format_map_keys(self):
        for key in format_map:
            assert key.isalpha()
            assert format_map[key].startswith("gen9")
            assert "vgc" in format_map[key]
        assert format_map["ma"] == "gen9championsvgc2026regma"

    def test_vgc_format_detection(self):
        assert is_vgc_format("gen9vgc2025regj")
        assert is_vgc_format("gen9vgc2025regjbo3")
        assert is_vgc_format("gen9championsvgc2026regma")
        assert is_vgc_format("gen9championsvgc2026regmabo3")
        assert not is_vgc_format("gen9ou")

    def test_get_reg_from_format(self):
        assert get_reg_from_format("gen9vgc2025regj") == "j"
        assert get_reg_from_format("gen9vgc2025regjbo3") == "j"
        assert get_reg_from_format("gen9championsvgc2026regma") == "ma"
        assert get_reg_from_format("gen9championsvgc2026regmabo3") == "ma"


class TestSetGlobalSeed:
    def test_reproducibility(self):
        set_global_seed(42)
        a = np.random.rand(5)
        t = torch.rand(5)
        set_global_seed(42)
        b = np.random.rand(5)
        u = torch.rand(5)
        np.testing.assert_array_equal(a, b)
        assert torch.equal(t, u)
