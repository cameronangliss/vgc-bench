"""
Neural network policy module for VGC-Bench.

Implements the actor-critic policy architecture with attention-based feature
extraction for Pokemon VGC battles. Uses action masking to ensure only legal
moves are selected.
"""

from typing import Any

import torch
from gymnasium import Space
from stable_baselines3.common.distributions import MultiCategoricalDistribution
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from stable_baselines3.common.type_aliases import PyTorchObs
from torch import nn

from vgc_bench.src.utils import (
    abilities,
    act_len,
    chunk_obs_len,
    glob_obs_len,
    items,
    moves,
    side_obs_len,
)

action_map = (
    ["pass", "switch 1", "switch 2", "switch 3", "switch 4", "switch 5", "switch 6"]
    + [f"move {i} target {j}" for i in range(1, 5) for j in range(-2, 3)]
    + [f"move {i} target {j} mega" for i in range(1, 5) for j in range(-2, 3)]
    + [f"move {i} target {j} zmove" for i in range(1, 5) for j in range(-2, 3)]
    + [f"move {i} target {j} dynamax" for i in range(1, 5) for j in range(-2, 3)]
    + [f"move {i} target {j} tera" for i in range(1, 5) for j in range(-2, 3)]
)


class MaskedActorCriticPolicy(ActorCriticPolicy):
    """
    Actor-critic policy with action masking for Pokemon VGC.

    Extends SB3's ActorCriticPolicy with action masking to enforce legal
    moves and uses an attention-based feature extractor for processing
    Pokemon battle observations.

    Attributes:
        num_frames: Number of stacked frames for temporal context.
        choose_on_teampreview: Whether policy controls teampreview decisions.
        actor_grad: Whether to compute gradients for actor during evaluation.
        debug: Whether to print debug information during forward pass.
    """

    def __init__(
        self,
        *args: Any,
        d_model: int,
        num_frames: int,
        choose_on_teampreview: bool,
        **kwargs: Any,
    ):
        """
        Initialize the masked actor-critic policy.

        Args:
            d_model: Hidden size for policy/value networks and attention extractor.
            num_frames: Number of frames to stack for temporal context.
            choose_on_teampreview: Whether policy controls teampreview.
            *args: Additional arguments for ActorCriticPolicy.
            **kwargs: Additional keyword arguments for ActorCriticPolicy.
        """
        self.num_frames = num_frames
        self.choose_on_teampreview = choose_on_teampreview
        self.actor_grad = True
        self.debug = False
        super().__init__(
            *args,
            **kwargs,
            net_arch=[],
            activation_fn=torch.nn.ReLU,
            features_extractor_class=AttentionExtractor,
            features_extractor_kwargs={
                "d_model": d_model,
                "num_frames": num_frames,
                "choose_on_teampreview": choose_on_teampreview,
            },
            share_features_extractor=False,
        )

    def forward(
        self, obs: torch.Tensor, deterministic: bool = False
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Compute actions, values, and log probabilities from observations.

        Args:
            obs: Batch of observations.
            deterministic: If True, select the most likely action.

        Returns:
            Tuple of (actions, values, log_probs).
        """
        action_logits, value_logits = self.get_logits(obs, actor_grad=True)
        distribution = self.get_dist_from_logits(obs, action_logits)
        actions = distribution.get_actions(deterministic=deterministic)
        distribution2 = self.get_dist_from_logits(obs, action_logits, actions[:, :1])
        actions2 = distribution2.get_actions(deterministic=deterministic)
        distribution.distribution[1] = distribution2.distribution[1]
        actions[:, 1] = actions2[:, 1]
        if self.debug:
            print("value:", value_logits[0][0].item())
            action_dist1 = {
                action_map[i]: f"{p.item():.3e}"
                for i, p in enumerate(distribution.distribution[0].probs[0])
                if p > 0
            }
            action_dist1 = dict(
                sorted(action_dist1.items(), key=lambda x: float(x[1]), reverse=True)
            )
            print("action1 dist:", action_dist1)
            action_dist2 = {
                action_map[i]: f"{p.item():.3e}"
                for i, p in enumerate(distribution.distribution[1].probs[0])
                if p > 0
            }
            action_dist2 = dict(
                sorted(action_dist2.items(), key=lambda x: float(x[1]), reverse=True)
            )
            print("action2 dist:", action_dist2)
        log_prob = distribution.log_prob(actions)
        actions = actions.reshape((-1, *self.action_space.shape))  # type: ignore[misc]
        return actions, value_logits, log_prob

    def evaluate_actions(
        self, obs: PyTorchObs, actions: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor | None]:
        """Evaluate given actions and return values, log probs, and entropy."""
        assert isinstance(obs, torch.Tensor)
        action_logits, value_logits = self.get_logits(obs, self.actor_grad)
        distribution = self.get_dist_from_logits(obs, action_logits)
        distribution2 = self.get_dist_from_logits(obs, action_logits, actions[:, :1])
        distribution.distribution[1] = distribution2.distribution[1]
        log_prob = distribution.log_prob(actions)
        entropy = distribution.entropy()
        return value_logits, log_prob, entropy

    def get_logits(
        self, obs: torch.Tensor, actor_grad: bool
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Extract features and compute action/value logits."""
        actor_context = torch.enable_grad() if actor_grad else torch.no_grad()
        features = self.extract_features(obs)
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
        self,
        obs: torch.Tensor,
        action_logits: torch.Tensor,
        action: torch.Tensor | None = None,
    ) -> MultiCategoricalDistribution:
        """Create masked action distribution from logits."""
        batch_size = obs.size(0)
        mask = obs.view(batch_size, self.num_frames, -1)
        mask = mask[:, -1, : 2 * act_len]
        if action is not None:
            mask = self._update_mask(mask, action)
        mask = torch.where(mask == 1, 0, float("-inf"))
        distribution = self.action_dist.proba_distribution(action_logits + mask)
        assert isinstance(distribution, MultiCategoricalDistribution)
        return distribution

    @staticmethod
    def _update_mask(mask: torch.Tensor, ally_actions: torch.Tensor) -> torch.Tensor:
        """
        Update action mask based on ally's already-chosen action.

        Prevents illegal combinations like both Pokemon switching to the same
        slot, both passing when not forced, or both terastallizing.

        Args:
            mask: Current action mask tensor of shape (batch, 2*act_len).
            ally_actions: Ally's chosen actions of shape (batch, 1).

        Returns:
            Updated mask tensor with illegal actions disabled.
        """
        indices = (
            torch.arange(act_len, device=ally_actions.device)
            .unsqueeze(0)
            .expand(len(ally_actions), -1)
        )
        ally_passed = ally_actions == 0
        ally_force_passed = (
            (mask[:, 0] == 1) & (mask[:, :act_len].sum(1) == 1)
        ).unsqueeze(1)
        ally_switched = (1 <= ally_actions) & (ally_actions <= 6)
        ally_terastallized = (86 < ally_actions) & (ally_actions <= 106)
        updated_half = mask[:, act_len:] * ~(
            ((indices == 0) & ally_passed & ~ally_force_passed)
            | ((indices == ally_actions) & ally_switched)
            | ((86 < indices) & (indices <= 106) & ally_terastallized)
        )
        return torch.cat([mask[:, :act_len], updated_half], dim=1)


class AttentionExtractor(BaseFeaturesExtractor):
    """
    Attention-based feature extractor for Pokemon battle observations.

    Processes Pokemon observations using embeddings for abilities, items, and
    moves, then applies transformer attention to produce a fixed-size feature
    vector. Supports optional temporal frame stacking with causal attention.

    Class Attributes:
        embed_len: Dimension of embedding vectors for abilities/items/moves.
        num_heads: Number of attention heads in transformer layers.
        embed_layers: Number of transformer encoder layers.
    """

    embed_len: int = 32
    num_heads: int = 4
    embed_layers: int = 3

    def __init__(
        self,
        observation_space: Space[Any],
        d_model: int,
        num_frames: int,
        choose_on_teampreview: bool,
    ):
        """
        Initialize the attention-based feature extractor.

        Args:
            observation_space: Gymnasium observation space specification.
            d_model: Hidden size for token projection and transformer layers.
            num_frames: Number of stacked frames for temporal context.
            choose_on_teampreview: Whether policy controls teampreview decisions.
        """
        super().__init__(observation_space, features_dim=d_model)
        self.num_frames = num_frames
        self.choose_on_teampreview = choose_on_teampreview
        self.ability_embed = nn.Embedding(
            len(abilities), self.embed_len, max_norm=self.embed_len**0.5
        )
        self.item_embed = nn.Embedding(
            len(items), self.embed_len, max_norm=self.embed_len**0.5
        )
        self.move_embed = nn.Embedding(
            len(moves), self.embed_len, max_norm=self.embed_len**0.5
        )
        self.pokemon_proj = nn.Linear(chunk_obs_len + 6 * (self.embed_len - 1), d_model)
        self.cls_token = nn.Parameter(torch.randn(1, 1, d_model))
        self.pokemon_encoder = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(
                d_model=d_model,
                nhead=self.num_heads,
                dim_feedforward=d_model,
                dropout=0,
                batch_first=True,
                norm_first=True,
            ),
            num_layers=self.embed_layers,
            enable_nested_tensor=False,
        )
        if num_frames > 1:
            self.frame_encoding: torch.Tensor
            self.register_buffer("frame_encoding", torch.eye(num_frames).unsqueeze(0))
            self.frame_proj = nn.Linear(d_model + num_frames, d_model)
            self.mask: torch.Tensor
            self.register_buffer(
                "mask", nn.Transformer.generate_square_subsequent_mask(num_frames)
            )
            self.frame_encoder = nn.TransformerEncoder(
                nn.TransformerEncoderLayer(
                    d_model=d_model,
                    nhead=self.num_heads,
                    dim_feedforward=d_model,
                    dropout=0,
                    batch_first=True,
                    norm_first=True,
                ),
                num_layers=self.embed_layers,
                enable_nested_tensor=False,
            )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Extract features from battle observation tensor.

        Embeds Pokemon attributes, applies transformer attention across all 12
        Pokemon (6 per side), and optionally applies temporal attention across
        stacked frames.

        Args:
            x: Observation tensor of shape (batch, obs_dim) or
               (batch, num_frames * obs_dim) if frame stacking.

        Returns:
            Feature tensor of shape (batch, d_model).
        """
        batch_size = x.size(0)
        x = x.view(batch_size, self.num_frames, -1)
        x = x[:, :, 2 * act_len :]
        pokemon_obs = x.view(batch_size * self.num_frames, 12, -1)
        # embedding
        start = glob_obs_len + side_obs_len
        pokemon_obs = torch.cat(
            [
                pokemon_obs[:, :, :start],
                self.ability_embed(pokemon_obs[:, :, start].long()),
                self.item_embed(pokemon_obs[:, :, start + 1].long()),
                self.move_embed(pokemon_obs[:, :, start + 2].long()),
                self.move_embed(pokemon_obs[:, :, start + 3].long()),
                self.move_embed(pokemon_obs[:, :, start + 4].long()),
                self.move_embed(pokemon_obs[:, :, start + 5].long()),
                pokemon_obs[:, :, start + 6 :],
            ],
            dim=-1,
        )
        # pokemon encoder
        pokemon_tokens = self.pokemon_proj(pokemon_obs)
        cls_token = self.cls_token.expand(batch_size * self.num_frames, -1, -1)
        tokens = torch.cat([cls_token, pokemon_tokens], dim=1)
        z = self.pokemon_encoder(tokens)[:, 0, :]
        if self.num_frames == 1:
            return z
        # frame encoder
        frame_tokens = z.view(batch_size, self.num_frames, -1)
        frame_encoding = self.frame_encoding.expand(batch_size, -1, -1)
        frame_tokens = torch.cat([frame_tokens, frame_encoding], dim=2)
        frame_tokens = self.frame_proj(frame_tokens)
        return self.frame_encoder(frame_tokens, mask=self.mask, is_causal=True)[
            :, -1, :
        ]
