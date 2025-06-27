from __future__ import annotations

from typing import Any

import torch
import torch.nn as nn
from gymnasium.spaces import Space
from ray.rllib.core import Columns
from ray.rllib.core.rl_module.apis.value_function_api import ValueFunctionAPI
from ray.rllib.core.rl_module.torch import TorchRLModule
from ray.rllib.models.torch.torch_distributions import TorchCategorical, TorchMultiCategorical
from src.utils import (
    abilities,
    doubles_act_len,
    doubles_chunk_obs_len,
    doubles_glob_obs_len,
    items,
    moves,
    side_obs_len,
)


class NeuralNetwork(nn.Module):
    num_pokemon: int = 12
    embed_len: int = 32
    proj_len: int = 128
    embed_layers: int = 3

    def __init__(self, num_frames: int, chooses_on_teampreview: bool):
        super().__init__()
        self.num_frames = num_frames
        self.chooses_on_teampreview = chooses_on_teampreview
        self.ability_embed = nn.Embedding(len(abilities), self.embed_len)
        self.item_embed = nn.Embedding(len(items), self.embed_len)
        self.move_embed = nn.Embedding(len(moves), self.embed_len)
        self.feature_proj = nn.Linear(
            doubles_chunk_obs_len + 6 * (self.embed_len - 1), self.proj_len
        )
        self.cls_token = nn.Parameter(torch.randn(1, 1, self.proj_len))
        self.frame_encoder = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(
                d_model=self.proj_len,
                nhead=self.proj_len // 64,
                dim_feedforward=self.proj_len,
                dropout=0,
                batch_first=True,
                norm_first=True,
            ),
            num_layers=self.embed_layers,
        )
        self.frame_encoding: torch.Tensor
        if num_frames > 1:
            self.register_buffer("frame_encoding", torch.eye(num_frames).unsqueeze(0))
            self.frame_proj = nn.Linear(self.proj_len + num_frames, self.proj_len)
            self.mask: torch.Tensor
            self.register_buffer("mask", nn.Transformer.generate_square_subsequent_mask(num_frames))
            self.meta_encoder = nn.TransformerEncoder(
                nn.TransformerEncoderLayer(
                    d_model=self.proj_len,
                    nhead=self.proj_len // 64,
                    dim_feedforward=self.proj_len,
                    dropout=0,
                    batch_first=True,
                    norm_first=True,
                ),
                num_layers=self.embed_layers,
            )
        self.actor_proj = nn.Linear(self.proj_len, 2 * doubles_act_len)
        self.value_proj = nn.Linear(self.proj_len, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size = x.size(0)
        x = x.view(*x.size()[:-1], 12, -1)
        # embedding
        start = doubles_glob_obs_len + side_obs_len
        x = torch.cat(
            [
                x[..., :start],
                self.ability_embed(x[..., start].long()),
                self.item_embed(x[..., start + 1].long()),
                self.move_embed(x[..., start + 2].long()),
                self.move_embed(x[..., start + 3].long()),
                self.move_embed(x[..., start + 4].long()),
                self.move_embed(x[..., start + 5].long()),
                x[..., start + 6 :],
            ],
            dim=-1,
        )
        # frame encoder
        x = x.view(batch_size * self.num_frames, self.num_pokemon, -1)
        x = self.feature_proj(x)
        token = self.cls_token.expand(batch_size * self.num_frames, -1, -1)
        x = torch.cat([token, x], dim=1)
        x = self.frame_encoder(x)[:, 0, :]
        if self.num_frames == 1:
            return x
        # meta encoder
        x = x.view(batch_size, self.num_frames, -1)
        frame_encoding = self.frame_encoding.expand(batch_size, -1, -1)
        x = torch.cat([x, frame_encoding], dim=2)
        x = self.frame_proj(x)
        return self.meta_encoder(x, mask=self.mask, is_causal=True)[:, -1, :]


class TwoStepTorchMultiCategorical(TorchMultiCategorical):
    def sample(self) -> torch.Tensor:
        actions1 = self._cats[0].sample().unsqueeze(1)  # type: ignore
        mask = self._get_mask(actions1)
        dist = TorchCategorical(logits=self._cats[1].logits + mask)
        actions2 = dist.sample().unsqueeze(1)  # type: ignore
        actions = torch.cat([actions1, actions2], dim=1)
        return actions

    def logp(self, value: torch.Tensor) -> torch.Tensor:
        mask = self._get_mask(value[:, :1])
        dist2 = TorchCategorical(logits=self._cats[1].logits + mask)
        altered_dist = TorchMultiCategorical([self._cats[0], dist2])
        return altered_dist.logp(value)

    @staticmethod
    def _get_mask(ally_actions: torch.Tensor) -> torch.Tensor:
        indices = (
            torch.arange(doubles_act_len, device=ally_actions.device)
            .unsqueeze(0)
            .expand(len(ally_actions), -1)
        )
        ally_switched = (1 <= ally_actions) & (ally_actions <= 6)
        ally_terastallized = ally_actions >= 87
        mask = (
            ((27 <= indices) & (indices < 87))
            | ((indices == ally_actions) & ally_switched)
            | ((indices >= 87) & ally_terastallized)
        )
        mask = torch.where(mask == 1, float("-inf"), 0)
        return mask


class ActorCriticModule(TorchRLModule, ValueFunctionAPI):
    def __init__(
        self,
        observation_space: Space,
        action_space: Space,
        inference_only: bool,
        model_config: dict[str, Any],
        catalog_class: Any,
    ):
        super().__init__(
            observation_space=observation_space,
            action_space=action_space,
            inference_only=inference_only,
            model_config=model_config,
            catalog_class=catalog_class,
        )
        self.model = NeuralNetwork(
            model_config["num_frames"], model_config["chooses_on_teampreview"]
        )
        self.action_dist_cls = TwoStepTorchMultiCategorical.get_partial_dist_cls(input_lens=[doubles_act_len, doubles_act_len])  # type: ignore

    def _forward(self, batch: dict[str, Any], **kwargs) -> dict[str, Any]:
        obs = batch[Columns.OBS]
        embeddings = self.model(obs)
        logits = self.model.actor_proj(embeddings)
        mask = torch.where(obs[:, : 2 * doubles_act_len] == 1, float("-inf"), 0)
        return {Columns.EMBEDDINGS: embeddings, Columns.ACTION_DIST_INPUTS: logits + mask}

    def compute_values(
        self, batch: dict[str, Any], embeddings: torch.Tensor | None = None
    ) -> torch.Tensor:
        if embeddings is None:
            embeddings = self.model(batch[Columns.OBS])
        return self.model.value_proj(embeddings).squeeze(-1)
