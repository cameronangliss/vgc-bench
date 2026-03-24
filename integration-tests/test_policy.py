"""Integration tests for vgc_bench.src.policy AttentionExtractor.

These tests instantiate the full transformer-based feature extractor and run
forward/backward passes, verifying the architecture produces correct output
shapes and supports gradient flow.
"""

import gymnasium as gym
import numpy as np
import torch

from vgc_bench.src.policy import AttentionExtractor, act_len
from vgc_bench.src.utils import chunk_obs_len


class TestAttentionExtractor:
    def test_forward_shape(self):
        d_model = 64
        obs_dim = 12 * chunk_obs_len
        obs_space = gym.spaces.Dict(
            {
                "observation": gym.spaces.Box(
                    low=-1, high=1000, shape=(obs_dim,), dtype=np.float32
                ),
                "action_mask": gym.spaces.MultiBinary(2 * act_len),
            }
        )
        extractor = AttentionExtractor(obs_space, d_model, choose_on_teampreview=True)
        batch_size = 2
        obs = torch.zeros(batch_size, obs_dim)
        obs_dict = {
            "observation": obs,
            "action_mask": torch.ones(batch_size, 2 * act_len),
        }
        out = extractor(obs_dict)
        assert out.shape == (batch_size, d_model)

    def test_output_is_differentiable(self):
        d_model = 64
        obs_dim = 12 * chunk_obs_len
        obs_space = gym.spaces.Dict(
            {
                "observation": gym.spaces.Box(
                    low=-1, high=1000, shape=(obs_dim,), dtype=np.float32
                ),
                "action_mask": gym.spaces.MultiBinary(2 * act_len),
            }
        )
        extractor = AttentionExtractor(obs_space, d_model, choose_on_teampreview=True)
        obs = torch.zeros(1, obs_dim, requires_grad=True)
        obs_dict = {
            "observation": obs,
            "action_mask": torch.ones(1, 2 * act_len),
        }
        out = extractor(obs_dict)
        loss = out.sum()
        loss.backward()
        assert obs.grad is not None
