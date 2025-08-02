from __future__ import annotations

from typing import Any

import torch
from gymnasium import Space
from src.utils import abilities, act_len, chunk_obs_len, glob_obs_len, items, moves, side_obs_len
from stable_baselines3.common.base_class import BaseAlgorithm
from stable_baselines3.common.distributions import MultiCategoricalDistribution
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from stable_baselines3.common.type_aliases import PyTorchObs
from torch import nn


class MaskedActorCriticPolicy(ActorCriticPolicy):
    def __init__(self, *args: Any, num_frames: int, chooses_on_teampreview: bool, **kwargs: Any):
        self.num_frames = num_frames
        self.chooses_on_teampreview = chooses_on_teampreview
        self.actor_grad = True
        super().__init__(
            *args,
            **kwargs,
            net_arch=[],
            activation_fn=torch.nn.ReLU,
            features_extractor_class=AttentionExtractor,
            features_extractor_kwargs={
                "num_frames": num_frames,
                "chooses_on_teampreview": chooses_on_teampreview,
            },
            share_features_extractor=False,
        )

    @classmethod
    def clone(cls, model: BaseAlgorithm) -> MaskedActorCriticPolicy:
        assert isinstance(model.policy, MaskedActorCriticPolicy)
        new_policy = cls(
            model.observation_space,
            model.action_space,
            model.lr_schedule,
            num_frames=model.policy.num_frames,
            chooses_on_teampreview=model.policy.chooses_on_teampreview,
        )
        new_policy.load_state_dict(model.policy.state_dict())
        return new_policy

    def forward(
        self, obs: torch.Tensor, deterministic: bool = False
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        action_logits, value_logits = self.get_logits(obs, actor_grad=True)
        distribution = self.get_dist_from_logits(obs, action_logits)
        actions = distribution.get_actions(deterministic=deterministic)
        distribution2 = self.get_dist_from_logits(obs, action_logits, actions[:, :1])
        actions2 = distribution2.get_actions(deterministic=deterministic)
        distribution.distribution[1] = distribution2.distribution[1]
        actions[:, 1] = actions2[:, 1]
        log_prob = distribution.log_prob(actions)
        actions = actions.reshape((-1, *self.action_space.shape))  # type: ignore[misc]
        return actions, value_logits, log_prob

    def evaluate_actions(
        self, obs: PyTorchObs, actions: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor | None]:
        assert isinstance(obs, torch.Tensor)
        action_logits, value_logits = self.get_logits(obs, self.actor_grad)
        distribution = self.get_dist_from_logits(obs, action_logits)
        distribution2 = self.get_dist_from_logits(obs, action_logits, actions[:, :1])
        distribution.distribution[1] = distribution2.distribution[1]
        log_prob = distribution.log_prob(actions)
        entropy = distribution.entropy()
        return value_logits, log_prob, entropy

    def get_logits(self, obs: torch.Tensor, actor_grad: bool) -> tuple[torch.Tensor, torch.Tensor]:
        actor_context = torch.enable_grad() if actor_grad else torch.no_grad()
        features = self.extract_features(obs)  # type: ignore
        if self.share_features_extractor:
            latent_pi, latent_vf = self.mlp_extractor(features)
        else:
            pi_features, vf_features = features
            with actor_context:
                latent_pi = self.mlp_extractor.forward_actor(pi_features)
            latent_vf = self.mlp_extractor.forward_critic(vf_features)
        with actor_context:
            action_logits = self.action_net(latent_pi)
        value_logits = self.value_net(latent_vf)
        return action_logits, value_logits

    def get_dist_from_logits(
        self, obs: torch.Tensor, action_logits: torch.Tensor, action: torch.Tensor | None = None
    ) -> MultiCategoricalDistribution:
        mask = obs[:, : 2 * act_len]
        if action is not None:
            mask = self._update_mask(mask, action)
        mask = torch.where(mask == 1, 0, float("-inf"))
        distribution = self.action_dist.proba_distribution(action_logits + mask)
        assert isinstance(distribution, MultiCategoricalDistribution)
        return distribution

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
        mask[:, act_len:] *= ~(
            ((indices == 0) & ally_passed & ~ally_force_passed)
            | ((indices == ally_actions) & ally_switched)
            | ((86 < indices) & (indices <= 106) & ally_terastallized)
        )
        return mask


class AttentionExtractor(BaseFeaturesExtractor):
    embed_len: int = 32
    proj_len: int = 128
    embed_layers: int = 3

    def __init__(
        self, observation_space: Space[Any], num_frames: int, chooses_on_teampreview: bool
    ):
        super().__init__(observation_space, features_dim=self.proj_len)
        self.num_frames = num_frames
        self.chooses_on_teampreview = chooses_on_teampreview
        self.ability_embed = nn.Embedding(len(abilities), self.embed_len)
        self.item_embed = nn.Embedding(len(items), self.embed_len)
        self.move_embed = nn.Embedding(len(moves), self.embed_len)
        self.feature_proj = nn.Linear(chunk_obs_len + 6 * (self.embed_len - 1), self.proj_len)
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

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size = x.size(0)
        x = x[:, 2 * act_len :]
        x = x.view(*x.size()[:-1], 12, -1)
        # embedding
        start = glob_obs_len + side_obs_len
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
        x = x.view(batch_size * self.num_frames, 12, -1)
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
