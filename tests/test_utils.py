"""Tests for vgc_bench.src.utils."""

import numpy as np
import torch

from vgc_bench.src.utils import (
    LearningStyle,
    act_len,
    chunk_obs_len,
    format_map,
    glob_obs_len,
    move_obs_len,
    pokemon_obs_len,
    set_global_seed,
    side_obs_len,
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

    def test_obs_len_positive(self):
        assert glob_obs_len > 0
        assert side_obs_len > 0
        assert move_obs_len > 0
        assert pokemon_obs_len > 0
        assert chunk_obs_len > 0

    def test_chunk_obs_len_composition(self):
        assert chunk_obs_len == glob_obs_len + side_obs_len + pokemon_obs_len

    def test_format_map_keys(self):
        for key in format_map:
            assert len(key) == 1
            assert key.isalpha()
            assert format_map[key].startswith("gen9vgc")


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
