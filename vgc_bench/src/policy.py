from typing import Any

import torch
import torch.nn as nn
from gymnasium.spaces import Space
from ray.rllib.core import Columns
from ray.rllib.core.rl_module.apis.value_function_api import ValueFunctionAPI
from ray.rllib.core.rl_module.torch import TorchRLModule
from ray.rllib.models.torch.torch_distributions import TorchCategorical, TorchMultiCategorical
from src.utils import abilities, act_len, chunk_obs_len, glob_obs_len, items, moves, side_obs_len

action_map = (
    ["pass", "switch 1", "switch 2", "switch 3", "switch 4", "switch 5", "switch 6"]
    + [f"move {i} target {j}" for i in range(1, 5) for j in range(-2, 3)]
    + [f"move {i} target {j} mega" for i in range(1, 5) for j in range(-2, 3)]
    + [f"move {i} target {j} zmove" for i in range(1, 5) for j in range(-2, 3)]
    + [f"move {i} target {j} dynamax" for i in range(1, 5) for j in range(-2, 3)]
    + [f"move {i} target {j} tera" for i in range(1, 5) for j in range(-2, 3)]
)


class NeuralNetwork(nn.Module):
    num_pokemon: int = 12
    embed_len: int = 25
    proj_len: int = 200
    num_heads: int = 4
    embed_layers: int = 3

    def __init__(self, num_frames: int, chooses_on_teampreview: bool):
        super().__init__()
        self.num_frames = num_frames
        self.chooses_on_teampreview = chooses_on_teampreview
        self.ability_embed = nn.Embedding(
            len(abilities), self.embed_len, max_norm=self.embed_len**0.5
        )
        self.item_embed = nn.Embedding(len(items), self.embed_len, max_norm=self.embed_len**0.5)
        self.move_embed = nn.Embedding(len(moves), self.embed_len, max_norm=self.embed_len**0.5)
        self.feature_proj = nn.Linear(chunk_obs_len + 6 * (self.embed_len - 1), self.proj_len)
        self.cls_token = nn.Parameter(torch.randn(1, 1, self.proj_len))
        self.frame_encoder = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(
                d_model=self.proj_len,
                nhead=self.num_heads,
                dim_feedforward=self.proj_len,
                dropout=0,
                batch_first=True,
                norm_first=True,
            ),
            num_layers=self.embed_layers,
            enable_nested_tensor=False,
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
                    nhead=self.num_heads,
                    dim_feedforward=self.proj_len,
                    dropout=0,
                    batch_first=True,
                    norm_first=True,
                ),
                num_layers=self.embed_layers,
                enable_nested_tensor=False,
            )
        self.actor_proj = nn.Linear(self.proj_len, 2 * act_len)
        self.value_proj = nn.Linear(self.proj_len, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size = x.size(0)
        x = x.view(batch_size, self.num_frames, -1)
        x = x[:, :, 2 * act_len :]
        x = x.view(batch_size * self.num_frames, 12, -1)
        # embedding
        start = glob_obs_len + side_obs_len
        x = torch.cat(
            [
                x[:, :, :start],
                self.ability_embed(x[:, :, start].long()),
                self.item_embed(x[:, :, start + 1].long()),
                self.move_embed(x[:, :, start + 2].long()),
                self.move_embed(x[:, :, start + 3].long()),
                self.move_embed(x[:, :, start + 4].long()),
                self.move_embed(x[:, :, start + 5].long()),
                x[:, :, start + 6 :],
            ],
            dim=-1,
        )
        # frame encoder
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
        logits = torch.cat([self._cats[0].logits, self._cats[1].logits], dim=1)
        mask = torch.where(logits == float("-inf"), 0, 1)
        actions1 = self._cats[0].sample().unsqueeze(1)  # type: ignore
        mask = self._update_mask(mask, actions1)
        mask = torch.where(mask.bool(), 0, float("-inf"))
        dist = TorchCategorical(logits=self._cats[1].logits + mask[:, act_len:])
        actions2 = dist.sample().unsqueeze(1)  # type: ignore
        actions = torch.cat([actions1, actions2], dim=1)
        return actions

    def logp(self, value: torch.Tensor) -> torch.Tensor:
        logits = torch.cat([self._cats[0].logits, self._cats[1].logits], dim=1)
        mask = torch.where(logits == float("-inf"), 0, 1)
        mask = self._update_mask(mask, value[:, :1])
        mask = torch.where(mask.bool(), 0, float("-inf"))
        dist2 = TorchCategorical(logits=self._cats[1].logits + mask[:, act_len:])
        altered_dist = TorchMultiCategorical([self._cats[0], dist2])
        return altered_dist.logp(value)

    @staticmethod
    def _update_mask(mask: torch.Tensor, ally_actions: torch.Tensor) -> torch.Tensor:
        indices = (
            torch.arange(act_len, device=ally_actions.device)
            .unsqueeze(0)
            .expand(len(ally_actions), -1)
        )
        ally_passed = ally_actions == 0
        ally_force_passed = ((mask[:, 0] == 1) & (mask[:, :act_len].sum(1) == 1)).unsqueeze(1)
        ally_switched = (1 <= ally_actions) & (ally_actions <= 6)
        ally_terastallized = (86 < ally_actions) & (ally_actions <= 106)
        updated_half = mask[:, act_len:] * ~(
            ((indices == 0) & ally_passed & ~ally_force_passed)
            | ((indices == ally_actions) & ally_switched)
            | ((86 < indices) & (indices <= 106) & ally_terastallized)
        )
        return torch.cat([mask[:, :act_len], updated_half], dim=1)


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
        self.action_dist_cls = TwoStepTorchMultiCategorical.get_partial_dist_cls(input_lens=[act_len, act_len])  # type: ignore

    def _forward(self, batch: dict[str, Any], **kwargs) -> dict[str, Any]:
        obs = batch[Columns.OBS]
        embeddings = self.model(obs)
        logits = self.model.actor_proj(embeddings)
        mask = torch.where(obs[:, : 2 * act_len].bool(), 0, float("-inf"))
        return {Columns.EMBEDDINGS: embeddings, Columns.ACTION_DIST_INPUTS: logits + mask}

    def compute_values(
        self, batch: dict[str, Any], embeddings: torch.Tensor | None = None
    ) -> torch.Tensor:
        if embeddings is None:
            embeddings = self.model(batch[Columns.OBS])
        return self.model.value_proj(embeddings).squeeze(-1)
