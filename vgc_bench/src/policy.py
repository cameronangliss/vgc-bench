"""
Neural network policy module for VGC-Bench.

Implements the actor-critic policy architecture with sequence-based feature
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
    FIELDS_PER_EVENT,
    NUM_ENTITIES,
    NUM_EVENT_TYPES,
    NUM_POSITIONS,
    act_len,
    max_events,
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
    moves and uses a sequence-based feature extractor for processing
    tokenized battle event observations.

    Attributes:
        choose_on_teampreview: Whether policy controls teampreview decisions.
        actor_grad: Whether to compute gradients for actor during evaluation.
        debug: Whether to print debug information during forward pass.
    """

    def __init__(self, *args: Any, choose_on_teampreview: bool = True, **kwargs: Any):
        """
        Initialize the masked actor-critic policy.

        Args:
            choose_on_teampreview: Whether policy controls teampreview.
            *args: Additional arguments for ActorCriticPolicy.
            **kwargs: Additional keyword arguments for ActorCriticPolicy.
        """
        self.choose_on_teampreview = choose_on_teampreview
        self.actor_grad = True
        self.debug = False
        super().__init__(
            *args,
            **kwargs,
            net_arch=[],
            activation_fn=torch.nn.ReLU,
            features_extractor_class=SequenceExtractor,
            share_features_extractor=False,
        )

    def forward(self, obs: PyTorchObs, deterministic=False):
        assert isinstance(obs, dict)
        action_logits, value_logits = self.get_logits(obs, actor_grad=True)
        distribution = self.get_dist_from_logits(action_logits, obs["action_mask"])
        actions = distribution.get_actions(deterministic=deterministic)
        distribution2 = self.get_dist_from_logits(
            action_logits, obs["action_mask"], actions[:, :1]
        )
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

    def evaluate_actions(self, obs, actions):
        assert isinstance(obs, dict)
        action_logits, value_logits = self.get_logits(obs, self.actor_grad)
        distribution = self.get_dist_from_logits(action_logits, obs["action_mask"])
        distribution2 = self.get_dist_from_logits(
            action_logits, obs["action_mask"], actions[:, :1]
        )
        distribution.distribution[1] = distribution2.distribution[1]
        log_prob = distribution.log_prob(actions)
        entropy = distribution.entropy()
        return value_logits, log_prob, entropy

    def get_logits(
        self, obs: dict[str, torch.Tensor], actor_grad: bool
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
        action_logits: torch.Tensor,
        mask: torch.Tensor,
        action: torch.Tensor | None = None,
    ) -> MultiCategoricalDistribution:
        """Create masked action distribution from logits."""
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
        ally_mega_evolved = (26 < ally_actions) & (ally_actions <= 46)
        ally_z_moved = (46 < ally_actions) & (ally_actions <= 66)
        ally_dynamaxed = (66 < ally_actions) & (ally_actions <= 86)
        ally_terastallized = (86 < ally_actions) & (ally_actions <= 106)
        updated_half = mask[:, act_len:] * ~(
            ((indices == 0) & ally_passed & ~ally_force_passed)
            | ((indices == ally_actions) & ally_switched)
            | ((26 < indices) & (indices <= 46) & ally_mega_evolved)
            | ((46 < indices) & (indices <= 66) & ally_z_moved)
            | ((66 < indices) & (indices <= 86) & ally_dynamaxed)
            | ((86 < indices) & (indices <= 106) & ally_terastallized)
        )
        return torch.cat([mask[:, :act_len], updated_half], dim=1)


class SequenceExtractor(BaseFeaturesExtractor):
    """
    Feature extractor that processes structured battle event sequences.

    Each event is a fixed-width row of IDs and continuous values. Discrete fields
    are embedded into small vectors, concatenated with continuous features, and
    projected to d_model.

    Class Attributes:
        embed_len: Dimension of embedding vectors for discrete fields.
        num_heads: Number of attention heads in transformer layers.
        embed_layers: Number of transformer encoder layers.
    """

    embed_len: int = 32
    d_model: int = 256
    num_heads: int = 4
    dim_feedforward: int = 1024
    embed_layers: int = 3

    def __init__(self, observation_space: Space[Any]):
        super().__init__(observation_space, features_dim=self.d_model)
        self.event_embed = nn.Embedding(NUM_EVENT_TYPES, self.embed_len)
        self.src_pos_embed = nn.Embedding(NUM_POSITIONS, self.embed_len)
        self.tgt_pos_embed = nn.Embedding(NUM_POSITIONS, self.embed_len)
        self.entity_embed = nn.Embedding(NUM_ENTITIES, self.embed_len, padding_idx=0)
        self.event_proj = nn.Linear(7 * self.embed_len + 8, self.d_model)
        self.seq_pos_embed = nn.Embedding(max_events, self.d_model)
        self.event_encoder = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(
                d_model=self.d_model,
                nhead=self.num_heads,
                dim_feedforward=self.dim_feedforward,
                dropout=0,
                batch_first=True,
                norm_first=True,
            ),
            num_layers=self.embed_layers,
        )
        self.norm = nn.LayerNorm(self.d_model)

    def forward(self, obs_dict: dict[str, torch.Tensor]) -> torch.Tensor:
        """Extract features from structured event observation."""
        x = obs_dict["observation"]
        batch_size = x.size(0)
        data = x.view(batch_size, max_events, FIELDS_PER_EVENT)
        # embedding
        evt_ids = data[:, :, 0].long()
        src_ids = data[:, :, 1].long()
        tgt_ids = data[:, :, 2].long()
        ent_ids = data[:, :, 3:7].long()
        ent_flat = self.entity_embed(ent_ids).view(
            batch_size, max_events, 4 * self.embed_len
        )
        event_obs = torch.cat(
            [
                self.event_embed(evt_ids),
                self.src_pos_embed(src_ids),
                self.tgt_pos_embed(tgt_ids),
                ent_flat,
                data[:, :, 7:],
            ],
            dim=-1,
        )
        # event encoder
        event_tokens = self.event_proj(event_obs)
        positions = torch.arange(max_events, device=x.device).unsqueeze(0)
        event_tokens = event_tokens + self.seq_pos_embed(positions)
        is_pad = evt_ids == 0
        causal_mask = nn.Transformer.generate_square_subsequent_mask(
            max_events, device=x.device
        )
        pad_mask = torch.where(is_pad, float("-inf"), 0.0)
        z = self.event_encoder(
            event_tokens,
            mask=causal_mask,
            src_key_padding_mask=pad_mask,
            is_causal=True,
        )
        seq_lens = (~is_pad).sum(dim=1) - 1
        return self.norm(z[torch.arange(batch_size, device=x.device), seq_lens])
