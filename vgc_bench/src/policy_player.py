"""
Policy-based player module for VGC-Bench.

Provides player implementations that use neural network policies to make
battle decisions, including synchronous and batched asynchronous variants.
Also implements the battle state embedding used for policy observations.
"""

import asyncio
import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable

import numpy as np
import numpy.typing as npt
import torch
from poke_env.battle import (
    AbstractBattle,
    DoubleBattle,
    Effect,
    Field,
    Move,
    MoveCategory,
    Pokemon,
    PokemonGender,
    PokemonType,
    SideCondition,
    Status,
    Target,
    Weather,
)
from poke_env.data import to_id_str
from poke_env.environment import DoublesEnv
from poke_env.player import BattleOrder, DefaultBattleOrder, Player
from stable_baselines3 import PPO
from stable_baselines3.common.policies import BasePolicy

from vgc_bench.src.policy import MaskedActorCriticPolicy
from vgc_bench.src.teams import RandomTeamBuilder
from vgc_bench.src.utils import (
    abilities,
    items,
    move_obs_len,
    moves,
    normalize_format,
    pokemon_obs_len,
)


class PolicyPlayer(Player):
    """
    A Pokemon VGC player that uses a neural network policy for decisions.

    Handles battle state embedding and action masking to ensure only legal
    moves are selected.

    Attributes:
        policy: The neural network policy used for action selection.
    """

    policy: BasePolicy | None

    def __init__(
        self,
        policy: BasePolicy | None = None,
        accepted_formats: set[str] | None = None,
        *args: Any,
        **kwargs: Any,
    ):
        """
        Initialize the policy player.

        Args:
            policy: Neural network policy (can be set later via set_policy).
            accepted_formats: If set, accept challenges of any of these formats
                instead of only ``battle_format``. Requires the team builder to
                be in multi-reg mode (``reg=None``) so the correct
                regulation's teams are yielded.
            *args: Additional arguments for Player base class.
            **kwargs: Additional keyword arguments for Player base class.
        """
        super().__init__(*args, **kwargs)
        self.policy = policy
        self._accepted_formats = accepted_formats

    async def _handle_challenge_request(self, split_message: list[str]):
        """Accept challenge requests, optionally for any recognized format."""
        if self._accepted_formats is None:
            return await super()._handle_challenge_request(split_message)
        challenging_player = split_message[2].strip()
        if challenging_player != self.username:
            if len(split_message) >= 6:
                canonical = normalize_format(split_message[5])
                if canonical and canonical in self._accepted_formats:
                    await self._challenge_queue.put((challenging_player, canonical))

    async def _update_challenges(self, split_message: list[str]):
        """Queue challenges, optionally accepting any recognized format."""
        if self._accepted_formats is None:
            return await super()._update_challenges(split_message)
        challenges = json.loads(split_message[2]).get("challengesFrom", {})
        for user, fmt in challenges.items():
            canonical = normalize_format(fmt)
            if canonical and canonical in self._accepted_formats:
                await self._challenge_queue.put((user, canonical))

    async def _accept_challenges(
        self,
        opponent: str | list[str] | None,
        n_challenges: int,
        packed_team: str | None,
    ):
        """Accept challenges, setting format and team reg before each."""
        if self._accepted_formats is None:
            return await super()._accept_challenges(opponent, n_challenges, packed_team)
        if opponent:
            if isinstance(opponent, list):
                opponent = [to_id_str(o) for o in opponent]
            else:
                opponent = to_id_str(opponent)
        await self.ps_client.logged_in.wait()

        for _ in range(n_challenges):
            while True:
                username, fmt = await self._challenge_queue.get()
                username = to_id_str(username)
                if (
                    (opponent is None)
                    or (opponent == username)
                    or (isinstance(opponent, list) and (username in opponent))
                ):
                    self._format = fmt
                    if (
                        isinstance(self._team, RandomTeamBuilder)
                        and self._team.available_regs is not None
                    ):
                        self._team.current_reg = fmt[-1]
                    team = packed_team or self.next_team
                    await self.ps_client.accept_challenge(username, team)
                    await self._battle_semaphore.acquire()
                    break
        await self._battle_count_queue.join()

    async def _create_battle(self, split_message: list[str]):
        """Create a battle, accepting any recognized format if configured."""
        if self._accepted_formats is None:
            return await super()._create_battle(split_message)
        canonical = normalize_format(split_message[1])
        if canonical and canonical in self._accepted_formats:
            saved = self._format
            self._format = canonical
            try:
                return await super()._create_battle(split_message)
            finally:
                self._format = saved
        return await super()._create_battle(split_message)

    def set_policy(self, policy_file: str | Path, device: torch.device):
        """
        Load or update the policy from a checkpoint file.

        Args:
            policy_file: Path to the saved PPO checkpoint.
            device: PyTorch device for model placement.
        """
        if self.policy is None:
            self.policy = PPO.load(policy_file, device=device).policy
        else:
            # Bypass SB3's leaky set_parameters - load state dict directly from zip
            with zipfile.ZipFile(policy_file, "r") as zf:
                with zf.open("policy.pth") as f:
                    state_dict = torch.load(
                        io.BytesIO(f.read()), map_location=device, weights_only=True
                    )
            self.policy.load_state_dict(state_dict)

    def choose_move(
        self, battle: AbstractBattle
    ) -> BattleOrder | Awaitable[BattleOrder]:
        """
        Choose the next move using the neural network policy.

        Args:
            battle: Current battle state.

        Returns:
            The chosen battle order.
        """
        assert isinstance(battle, DoubleBattle)
        assert isinstance(self.policy, MaskedActorCriticPolicy)
        if battle._wait:
            return DefaultBattleOrder()
        obs = self.embed_battle(battle, fake_rating=2000)
        mask = np.array(DoublesEnv.get_action_mask(battle))
        with torch.no_grad():
            obs_dict = {
                "observation": torch.as_tensor(
                    obs, device=self.policy.device
                ).unsqueeze(0),
                "action_mask": torch.as_tensor(
                    mask, device=self.policy.device
                ).unsqueeze(0),
            }
            action, _, _ = self.policy.forward(obs_dict)  # type: ignore
        action = action.cpu().numpy()[0]
        return DoublesEnv.action_to_order(action, battle)

    def teampreview(self, battle: AbstractBattle) -> str | Awaitable[str]:
        """
        Select Pokemon for teampreview.

        Uses random teampreview when policy-controlled teampreview is disabled.

        Args:
            battle: Current battle state during team preview.

        Returns:
            Team order string for Pokemon Showdown.
        """
        assert isinstance(self.policy, MaskedActorCriticPolicy)
        if not self.policy.choose_on_teampreview:
            return self.random_teampreview(battle)
        assert isinstance(battle, DoubleBattle)
        order1 = self.choose_move(battle)
        assert not isinstance(order1, Awaitable)
        action1 = DoublesEnv.order_to_action(order1, battle)
        list(battle.team.values())[action1[0] - 1]._selected_in_teampreview = True
        list(battle.team.values())[action1[1] - 1]._selected_in_teampreview = True
        order2 = self.choose_move(battle)
        assert not isinstance(order2, Awaitable)
        action2 = DoublesEnv.order_to_action(order2, battle)
        list(battle.team.values())[action2[0] - 1]._selected_in_teampreview = True
        list(battle.team.values())[action2[1] - 1]._selected_in_teampreview = True
        return f"/team {action1[0]}{action1[1]}{action2[0]}{action2[1]}"

    @staticmethod
    def embed_battle(
        battle: AbstractBattle, fake_rating: int | None = None
    ) -> npt.NDArray[np.float32]:
        """
        Convert a battle state to a feature vector observation.

        Creates a fixed-size numpy array encoding the full battle state including
        action masks, global effects, side conditions, and all Pokemon information.

        Args:
            battle: The battle state to embed.
            fake_rating: Optional raw rating override for the player side.
                If provided, opponent rating is masked to 0.

        Returns:
            Numpy array observation for the policy network.
        """
        assert isinstance(battle, DoubleBattle)
        glob = PolicyPlayer.embed_global(battle)
        side = PolicyPlayer.embed_side(battle, fake_rating)
        opp_fake_rating = None if fake_rating is None else 0
        opp_side = PolicyPlayer.embed_side(battle, opp_fake_rating, opp=True)
        a1, a2 = battle.active_pokemon
        o1, o2 = battle.opponent_active_pokemon
        assert battle.teampreview == (
            len([p for p in battle.team.values() if p.selected_in_teampreview]) < 4
        )
        pokemons = [
            PolicyPlayer.embed_pokemon(
                p,
                i,
                from_opponent=False,
                active_a=a1 is not None and p.name == a1.name,
                active_b=a2 is not None and p.name == a2.name,
            )
            for i, p in enumerate(battle.team.values())
        ]
        pokemons += [np.zeros(pokemon_obs_len, dtype=np.float32)] * (6 - len(pokemons))
        opp_pokemons = [
            PolicyPlayer.embed_pokemon(
                p,
                i,
                from_opponent=True,
                active_a=o1 is not None and p.name == o1.name,
                active_b=o2 is not None and p.name == o2.name,
            )
            for i, p in enumerate(battle.opponent_team.values())
        ]
        opp_pokemons += [np.zeros(pokemon_obs_len, dtype=np.float32)] * (
            6 - len(opp_pokemons)
        )
        return np.concatenate(
            [np.concatenate([glob, side, p]) for p in pokemons]
            + [np.concatenate([glob, opp_side, p]) for p in opp_pokemons],
            dtype=np.float32,
        )

    @staticmethod
    def embed_global(battle: DoubleBattle) -> npt.NDArray[np.float32]:
        """Embed global battle state (weather, fields, etc)."""
        weather = [
            (min(battle.turn - battle.weather[w], 8) / 8 if w in battle.weather else 0)
            for w in Weather
        ]
        fields = [
            min(battle.turn - battle.fields[f], 8) / 8 if f in battle.fields else 0
            for f in Field
        ]
        teampreview = float(battle.teampreview)
        reviving = float(battle.reviving)
        commanding = float(battle.commanding)
        return np.array(
            [*weather, *fields, teampreview, reviving, commanding], dtype=np.float32
        )

    @staticmethod
    def embed_side(
        battle: DoubleBattle, fake_rating: int | None, opp: bool = False
    ) -> npt.NDArray[np.float32]:
        """
        Embed side-specific state (side conditions, gimmick availability, rating).

        Args:
            battle: Current doubles battle state.
            fake_rating: Optional raw rating override for this side.
                If None, read rating from battle player metadata.
            opp: Whether to embed the opponent side.
        """
        gims = [
            battle.can_mega_evolve[0],
            battle.can_z_move[0],
            battle.can_dynamax[0],
            battle.can_tera[0],
        ]
        opp_gims = [
            battle.opponent_used_mega_evolve,
            battle.opponent_used_z_move,
            battle.opponent_used_dynamax,
            battle._opponent_used_tera,
        ]
        side_conds = battle.opponent_side_conditions if opp else battle.side_conditions
        side_conditions = [
            (
                0
                if s not in side_conds
                else (
                    1
                    if s == SideCondition.STEALTH_ROCK
                    else (
                        side_conds[s] / 2
                        if s == SideCondition.TOXIC_SPIKES
                        else (
                            side_conds[s] / 3
                            if s == SideCondition.SPIKES
                            else min(battle.turn - side_conds[s], 8) / 8
                        )
                    )
                )
            )
            for s in SideCondition
        ]
        gims = opp_gims if opp else gims
        gimmicks = [float(g) for g in gims]
        if fake_rating is not None:
            rating = fake_rating / 2000
        else:
            player = battle.opponent_role if opp else battle.player_role
            rat = [p for p in battle._players if p["player"] == player][0].get(
                "rating", "0"
            )
            rating = int(rat or "0") / 2000
        return np.array([*side_conditions, *gimmicks, rating], dtype=np.float32)

    @staticmethod
    def embed_pokemon(
        pokemon: Pokemon, pos: int, from_opponent: bool, active_a: bool, active_b: bool
    ) -> npt.NDArray[np.float32]:
        """Embed a Pokemon's stats, moves, status, and effects."""
        assert from_opponent or not pokemon.revealed or pokemon.selected_in_teampreview
        # (mostly) stable fields
        ability_id = abilities.index(
            "null" if pokemon.ability is None else pokemon.ability
        )
        item_id = items.index("null" if pokemon.item is None else pokemon.item)
        move_list = list(pokemon.moves.values())[-4:]
        move_ids = [moves.index(move.id) for move in move_list]
        move_ids += [0] * (4 - len(move_ids))
        move_embeds = [PolicyPlayer.embed_move(move) for move in move_list]
        move_embeds += [np.zeros(move_obs_len, dtype=np.float32)] * (
            4 - len(move_embeds)
        )
        move_embeds = np.concatenate(move_embeds)
        types = [float(t in pokemon.base_types) for t in PokemonType]
        tera_type = [float(t == pokemon.tera_type) for t in PokemonType]
        if from_opponent:
            stats = [s / 255 for s in pokemon.base_stats.values()]
        else:
            stats = [(0 if s is None else s / 255) for s in pokemon.stats.values()]
        gender = [float(g == pokemon.gender) for g in PokemonGender]
        weight = pokemon.weight / 1000
        # volatile fields
        hp_frac = pokemon.current_hp_fraction
        revealed = float(pokemon.revealed)
        in_draft = float(pokemon.selected_in_teampreview)
        status = [float(s == pokemon.status) for s in Status]
        status_counter = pokemon.status_counter / 16
        boosts = [b / 6 for b in pokemon.boosts.values()]
        effects = [
            (min(pokemon.effects[e], 8) / 8 if e in pokemon.effects else 0)
            for e in Effect
        ]
        first_turn = float(pokemon.first_turn)
        protect_counter = pokemon.protect_counter / 5
        must_recharge = float(pokemon.must_recharge)
        preparing = float(pokemon.preparing)
        gimmicks = [float(s) for s in [pokemon.is_dynamaxed, pokemon.is_terastallized]]
        pos_onehot = [float(pos == i) for i in range(6)]
        return np.array(
            [
                ability_id,
                item_id,
                *move_ids,
                *move_embeds,
                *types,
                *tera_type,
                *stats,
                *gender,
                weight,
                hp_frac,
                revealed,
                in_draft,
                *status,
                status_counter,
                *boosts,
                *effects,
                first_turn,
                protect_counter,
                must_recharge,
                preparing,
                *gimmicks,
                float(active_a),
                float(active_b),
                *pos_onehot,
                float(from_opponent),
            ],
            dtype=np.float32,
        )

    @staticmethod
    def embed_move(move: Move) -> npt.NDArray[np.float32]:
        """Embed a move's power, accuracy, type, and special properties."""
        power = move.base_power / 250
        acc = move.accuracy / 100
        category = [float(c == move.category) for c in MoveCategory]
        target = [float(t == move.target) for t in Target]
        priority = (move.priority + 7) / 12
        crit_ratio = move.crit_ratio
        drain = move.drain
        force_switch = float(move.force_switch)
        recoil = move.recoil
        self_destruct = float(move.self_destruct is not None)
        self_switch = float(move.self_switch is not False)
        pp = move.max_pp / 64
        pp_frac = move.current_pp / move.max_pp
        is_last_used = float(move.is_last_used)
        move_type = [float(t == move.type) for t in PokemonType]
        return np.array(
            [
                power,
                acc,
                *category,
                *target,
                priority,
                crit_ratio,
                drain,
                force_switch,
                recoil,
                self_destruct,
                self_switch,
                pp,
                pp_frac,
                is_last_used,
                *move_type,
            ]
        )


@dataclass
class _BatchReq:
    """Internal request object for batched inference."""

    obs: npt.NDArray[np.float32]
    mask: npt.NDArray[np.int64]
    event: asyncio.Event
    result: npt.NDArray[np.int64] | None = None


class BatchPolicyPlayer(PolicyPlayer):
    """
    A policy player that batches inference requests for efficiency.

    Collects multiple battle observations and runs them through the policy
    network together, improving GPU utilization when managing many concurrent
    battles.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize the batch policy player with an inference queue."""
        super().__init__(*args, **kwargs)
        self._q: asyncio.Queue[_BatchReq] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None

    def choose_move(self, battle: AbstractBattle) -> Awaitable[BattleOrder]:
        """Return an awaitable that resolves to the chosen battle order."""
        return self._choose_move(battle)

    async def _choose_move(self, battle: AbstractBattle) -> BattleOrder:
        """Queue an observation for batched inference and await the result."""
        assert isinstance(battle, DoubleBattle)
        if battle._wait:
            return DefaultBattleOrder()
        obs = self.embed_battle(battle, fake_rating=2000)
        mask = np.array(DoublesEnv.get_action_mask(battle))
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._inference_loop())
        req = _BatchReq(obs=obs, mask=mask, event=asyncio.Event())
        await self._q.put(req)
        await req.event.wait()
        assert req.result is not None
        action = req.result
        return DoublesEnv.action_to_order(action, battle)

    def teampreview(self, battle: AbstractBattle) -> Awaitable[str]:
        """Return an awaitable that resolves to the team order string."""
        return self._teampreview(battle)

    async def _teampreview(self, battle: AbstractBattle) -> str:
        """Async teampreview implementation with random fallback when disabled."""
        assert isinstance(self.policy, MaskedActorCriticPolicy)
        if not self.policy.choose_on_teampreview:
            return self.random_teampreview(battle)
        assert isinstance(battle, DoubleBattle)
        order1 = await self.choose_move(battle)
        action1 = DoublesEnv.order_to_action(order1, battle)
        list(battle.team.values())[action1[0] - 1]._selected_in_teampreview = True
        list(battle.team.values())[action1[1] - 1]._selected_in_teampreview = True
        order2 = await self.choose_move(battle)
        action2 = DoublesEnv.order_to_action(order2, battle)
        list(battle.team.values())[action2[0] - 1]._selected_in_teampreview = True
        list(battle.team.values())[action2[1] - 1]._selected_in_teampreview = True
        return f"/team {action1[0]}{action1[1]}{action2[0]}{action2[1]}"

    async def _inference_loop(self) -> None:
        """Background task that batches and processes inference requests."""
        assert isinstance(self.policy, MaskedActorCriticPolicy)
        while True:
            # gather requests
            requests = [await self._q.get()]
            just_slept = False
            while len(requests) < self._max_concurrent_battles:
                try:
                    req = self._q.get_nowait()
                    requests.append(req)
                    just_slept = False
                except asyncio.QueueEmpty:
                    if just_slept:
                        break
                    await asyncio.sleep(0.005)
                    just_slept = True

            # run inference
            obs = np.stack([r.obs for r in requests], axis=0)
            masks = np.stack([r.mask for r in requests], axis=0)
            with torch.no_grad():
                obs_dict = {
                    "observation": torch.as_tensor(obs, device=self.policy.device),
                    "action_mask": torch.as_tensor(masks, device=self.policy.device),
                }
                actions, _, _ = self.policy.forward(obs_dict)  # type: ignore
            actions = actions.cpu().numpy()

            # dispatch
            for req, act in zip(requests, actions):
                req.result = act
                req.event.set()
