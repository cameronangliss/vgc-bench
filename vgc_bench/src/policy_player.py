"""
Policy-based player module for VGC-Bench.

Provides player implementations that use neural network policies to make
battle decisions, including synchronous and batched asynchronous variants.
Also implements battle state tokenization for policy observations.
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
    PokemonType,
    SideCondition,
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
    ENT,
    EVT,
    FIELDS_PER_EVENT,
    POS,
    get_reg_from_format,
    is_vgc_format,
    max_events,
)

_EMPTY_EVT = EVT["EMPTY"]


class PolicyPlayer(Player):
    """
    A Pokemon VGC player that uses a neural network policy for decisions.

    Handles battle state tokenization and action masking to ensure only
    legal moves are selected.

    Attributes:
        policy: The neural network policy used for action selection.
    """

    policy: BasePolicy | None

    def __init__(
        self,
        policy: BasePolicy | None = None,
        accept_all_formats: bool = False,
        deterministic: bool = False,
        invitee: str | None = None,
        *args: Any,
        **kwargs: Any,
    ):
        """
        Initialize the policy player.

        Args:
            policy: Neural network policy (can be set later via set_policy).
            accept_all_formats: If True, accept challenges in any recognized
                VGC format instead of only ``battle_format``. Requires the
                team builder to be in multi-reg mode (``reg=None``) so the
                correct regulation's teams are yielded.
            deterministic: If True, always pick the highest-probability action
                instead of sampling from the distribution.
            *args: Additional arguments for Player base class.
            **kwargs: Additional keyword arguments for Player base class.
        """
        super().__init__(*args, **kwargs)
        self.policy = policy
        self._accept_all_formats = accept_all_formats
        self.deterministic = deterministic
        self.invitee = invitee

    async def _handle_challenge_request(self, split_message: list[str]):
        """Accept challenge requests, optionally for any recognized format."""
        if not self._accept_all_formats:
            return await super()._handle_challenge_request(split_message)
        challenging_player = split_message[2].strip()
        if challenging_player != self.username:
            if len(split_message) >= 6:
                fmt = split_message[5]
                if is_vgc_format(fmt):
                    await self._challenge_queue.put((challenging_player, fmt))

    async def _update_challenges(self, split_message: list[str]):
        """Queue challenges, optionally accepting any recognized format."""
        if not self._accept_all_formats:
            return await super()._update_challenges(split_message)
        challenges = json.loads(split_message[2]).get("challengesFrom", {})
        for user, fmt in challenges.items():
            if is_vgc_format(fmt):
                await self._challenge_queue.put((user, fmt))

    async def _accept_challenges(
        self,
        opponent: str | list[str] | None,
        n_challenges: int,
        packed_team: str | None,
    ):
        """Accept challenges, setting format and team reg before each."""
        if not self._accept_all_formats:
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
                        self._team.current_reg = get_reg_from_format(fmt)
                    team = packed_team or self.next_team
                    await self.ps_client.accept_challenge(username, team)
                    await self._battle_semaphore.acquire()
                    break
        await self._battle_count_queue.join()

    async def _create_battle(self, split_message: list[str]):
        """Create a battle, accepting any recognized format if configured."""
        if not self._accept_all_formats:
            battle = await super()._create_battle(split_message)
        elif is_vgc_format(split_message[1]):
            saved = self.format
            self._format = split_message[1]
            try:
                battle = await super()._create_battle(split_message)
            finally:
                self._format = saved
        else:
            battle = await super()._create_battle(split_message)
        if self.invitee is not None and "bo3" not in self.format:
            await self.ps_client.send_message(
                f"/invite {self.invitee}", battle.battle_tag
            )
        return battle

    async def _handle_bestof_message(self, split_messages):
        """Handle best-of series messages, inviting spectator to the lobby."""
        if self.invitee is not None:
            game_tag = split_messages[0][0][1:]  # strip >
            for split_message in split_messages[1:]:
                if len(split_message) >= 2 and split_message[1] == "init":
                    await self.ps_client.send_message(
                        f"/invite {self.invitee}", room=game_tag
                    )
                    break
        await super()._handle_bestof_message(split_messages)

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
        obs = self.tokenize_battle(battle, fake_rating=2000)
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
            action, _, _ = self.policy.forward(
                obs_dict, deterministic=self.deterministic
            )
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

    # --- Tokenization ---

    @staticmethod
    def tokenize_battle(
        battle: AbstractBattle,
        fake_rating: int | None = None,
    ) -> npt.NDArray[np.float32]:
        """
        Tokenize a battle state into a fixed-size event sequence observation.

        Converts the battle's replay data (event log) into a structured sequence
        of tokenized events, including team information and teampreview actions.

        Args:
            battle: The battle state to tokenize.
            fake_rating: Optional raw rating override for the player side.
                If provided, opponent rating is masked to 0.

        Returns:
            Flat numpy array of shape (max_events * FIELDS_PER_EVENT,).
        """
        assert isinstance(battle, DoubleBattle)
        assert battle.player_role is not None
        rows: list[npt.NDArray[np.float32]] = [PolicyPlayer._row(evt=EVT["BOS"])]
        # Rating tokens
        for event in battle._replay_data:
            if len(event) >= 3 and event[1] == "player":
                is_ally = event[2] == battle.player_role
                if is_ally and fake_rating is not None:
                    rating = fake_rating / 2000
                elif len(event) >= 6 and event[5]:
                    rating = int(event[5]) / 2000
                else:
                    continue
                src = POS["ally_side"] if is_ally else POS["opp_side"]
                rows.append(PolicyPlayer._row(evt=EVT["RATING"], src=src, hp=rating))
        team_inserted = False
        for event in battle._replay_data:
            if (
                not team_inserted
                and len(event) > 1
                and event[1] in ("start", "turn", "switch")
            ):
                rows += PolicyPlayer.tokenize_team(battle)
                rows += PolicyPlayer.tokenize_teampreview_action(battle)
                team_inserted = True
            rows += PolicyPlayer.tokenize_event(event, battle.player_role)

        if not team_inserted and battle.team:
            rows += PolicyPlayer.tokenize_team(battle)
            rows += PolicyPlayer.tokenize_teampreview_action(battle)

        rows.append(PolicyPlayer._row(evt=EVT["REQUEST"]))

        # left-truncation: keep BOS at front, drop oldest
        if len(rows) > max_events:
            rows = [rows[0]] + rows[-(max_events - 1) :]

        result = np.zeros((max_events, FIELDS_PER_EVENT), dtype=np.float32)
        for i, row in enumerate(rows):
            result[i] = row
        return result.ravel()

    # --- Row constructor ---
    @staticmethod
    def _row(
        evt: int = 0,
        src: int = 0,
        tgt: int = 0,
        e1: int = 0,
        e2: int = 0,
        e3: int = 0,
        e4: int = 0,
        hp: float = 0.0,
        boost: float = 0.0,
        stat_hp: float = 0.0,
        stat_atk: float = 0.0,
        stat_def: float = 0.0,
        stat_spa: float = 0.0,
        stat_spd: float = 0.0,
        stat_spe: float = 0.0,
    ) -> npt.NDArray[np.float32]:
        return np.array(
            [
                evt,
                src,
                tgt,
                e1,
                e2,
                e3,
                e4,
                hp,
                boost,
                stat_hp,
                stat_atk,
                stat_def,
                stat_spa,
                stat_spd,
                stat_spe,
            ],
            dtype=np.float32,
        )

    # --- Helpers ---
    @staticmethod
    def _parse_pos(identifier: str, player_role: str) -> int:
        """Convert 'p1a: Nickname' or 'p1: Username' to position ID."""
        raw = identifier.split(":")[0].strip()
        is_ally = raw[:2] == player_role
        slot = raw[2:]
        if slot == "a":
            return POS["ally_a"] if is_ally else POS["opp_a"]
        elif slot == "b":
            return POS["ally_b"] if is_ally else POS["opp_b"]
        return POS["ally_side"] if is_ally else POS["opp_side"]

    @staticmethod
    def _parse_hp(hp_str: str) -> float:
        hp_str = hp_str.split()[0]
        if "/" in hp_str:
            cur, max_hp = hp_str.split("/")
            return int(cur) / int(max_hp)
        return 0.0 if hp_str == "0" else 1.0

    @staticmethod
    def _parse_species(details: str) -> int:
        return ENT[f"species:{to_id_str(details.split(',')[0])}"]

    @staticmethod
    def _strip_prefix(text: str) -> str:
        """Strip 'move:', 'ability:', 'item:' prefix if present."""
        return text.split(":", 1)[1].strip() if ":" in text else text

    @staticmethod
    def _parse_effect_arg(text: str) -> int:
        """Parse an effect/move/ability/item argument to entity ID."""
        text = text.strip()
        if text.startswith("ability:"):
            return ENT[f"ability:{to_id_str(PolicyPlayer._strip_prefix(text))}"]
        if text.startswith("item:"):
            return ENT[f"item:{to_id_str(PolicyPlayer._strip_prefix(text))}"]
        if text.startswith("move:"):
            return ENT[f"move:{to_id_str(PolicyPlayer._strip_prefix(text))}"]
        effect = Effect.from_showdown_message(text)
        if effect != Effect.UNKNOWN:
            return ENT[f"effect:{effect.name}"]
        mid = to_id_str(text)
        key = f"move:{mid}"
        if key in ENT._id_map:
            return ENT[key]
        return ENT[f"effect:{Effect.UNKNOWN.name}"]

    @staticmethod
    def tokenize_event(
        event: list[str], player_role: str
    ) -> list[npt.NDArray[np.float32]]:
        """Convert a single event to a list of rows (usually 0 or 1)."""
        if len(event) < 2:
            return []
        etype = event[1]
        if etype == "":
            return [PolicyPlayer._row(evt=_EMPTY_EVT)]
        if etype not in EVT:
            return []
        evt = EVT[etype]

        if etype in ("switch", "drag"):
            if len(event) < 5:
                return []
            return [
                PolicyPlayer._row(
                    evt=evt,
                    src=PolicyPlayer._parse_pos(event[2], player_role),
                    e1=PolicyPlayer._parse_species(event[3]),
                    hp=PolicyPlayer._parse_hp(event[4]),
                )
            ]
        elif etype == "move":
            if len(event) < 4:
                return []
            tgt = 0
            if len(event) >= 5 and ": " in event[4]:
                tgt = PolicyPlayer._parse_pos(event[4], player_role)
            return [
                PolicyPlayer._row(
                    evt=evt,
                    src=PolicyPlayer._parse_pos(event[2], player_role),
                    tgt=tgt,
                    e1=ENT[f"move:{to_id_str(event[3])}"],
                )
            ]
        elif etype in ("-damage", "-heal", "-sethp"):
            if len(event) < 4:
                return []
            return [
                PolicyPlayer._row(
                    evt=evt,
                    src=PolicyPlayer._parse_pos(event[2], player_role),
                    hp=PolicyPlayer._parse_hp(event[3]),
                )
            ]
        elif etype in ("-status", "-curestatus"):
            if len(event) < 4:
                return []
            name = event[3].strip().upper()
            return [
                PolicyPlayer._row(
                    evt=evt,
                    src=PolicyPlayer._parse_pos(event[2], player_role),
                    e1=ENT[f"status:{name}"],
                )
            ]
        elif etype in ("-boost", "-unboost", "-setboost"):
            if len(event) < 5:
                return []
            amount = int(event[4])
            if etype == "-unboost":
                amount = -amount
            return [
                PolicyPlayer._row(
                    evt=evt,
                    src=PolicyPlayer._parse_pos(event[2], player_role),
                    e1=ENT[f"stat:{event[3].strip().lower()}"],
                    boost=amount / 6.0,
                )
            ]
        elif etype == "-weather":
            if len(event) < 3 or event[2] == "none":
                return []
            w = Weather.from_showdown_message(event[2])
            return [PolicyPlayer._row(evt=evt, e1=ENT[f"weather:{w.name}"])]
        elif etype in ("-fieldstart", "-fieldend"):
            if len(event) < 3:
                return []
            f = Field.from_showdown_message(PolicyPlayer._strip_prefix(event[2]))
            return [PolicyPlayer._row(evt=evt, e1=ENT[f"field:{f.name}"])]
        elif etype in ("-sidestart", "-sideend"):
            if len(event) < 4:
                return []
            s = SideCondition.from_showdown_message(
                PolicyPlayer._strip_prefix(event[3])
            )
            return [
                PolicyPlayer._row(
                    evt=evt,
                    src=PolicyPlayer._parse_pos(event[2], player_role),
                    e1=ENT[f"side:{s.name}"],
                )
            ]
        elif etype in ("-start", "-end", "-singleturn", "-singlemove", "-activate"):
            if len(event) < 4:
                if len(event) >= 3:
                    return [
                        PolicyPlayer._row(
                            evt=evt, src=PolicyPlayer._parse_pos(event[2], player_role)
                        )
                    ]
                return [PolicyPlayer._row(evt=evt)]
            return [
                PolicyPlayer._row(
                    evt=evt,
                    src=PolicyPlayer._parse_pos(event[2], player_role),
                    e1=PolicyPlayer._parse_effect_arg(event[3]),
                )
            ]
        elif etype in ("-ability", "-endability"):
            if len(event) < 4:
                return []
            return [
                PolicyPlayer._row(
                    evt=evt,
                    src=PolicyPlayer._parse_pos(event[2], player_role),
                    e1=ENT[
                        f"ability:{to_id_str(PolicyPlayer._strip_prefix(event[3]))}"
                    ],
                )
            ]
        elif etype in ("-item", "-enditem"):
            if len(event) < 4:
                return []
            return [
                PolicyPlayer._row(
                    evt=evt,
                    src=PolicyPlayer._parse_pos(event[2], player_role),
                    e1=ENT[f"item:{to_id_str(PolicyPlayer._strip_prefix(event[3]))}"],
                )
            ]
        elif etype == "-terastallize":
            if len(event) < 4:
                return []
            t = next(
                (t for t in PokemonType if to_id_str(event[3]) == to_id_str(t.name)),
                PokemonType.NORMAL,
            )
            return [
                PolicyPlayer._row(
                    evt=evt,
                    src=PolicyPlayer._parse_pos(event[2], player_role),
                    e1=ENT[f"type:{t.name}"],
                )
            ]
        elif etype in ("-formechange", "detailschange"):
            if len(event) < 4:
                return []
            return [
                PolicyPlayer._row(
                    evt=evt,
                    src=PolicyPlayer._parse_pos(event[2], player_role),
                    e1=PolicyPlayer._parse_species(event[3]),
                )
            ]
        elif etype == "-prepare":
            if len(event) < 4:
                return []
            return [
                PolicyPlayer._row(
                    evt=evt,
                    src=PolicyPlayer._parse_pos(event[2], player_role),
                    e1=ENT[f"move:{to_id_str(event[3])}"],
                )
            ]
        elif etype in ("-copyboost", "-swapboost", "-transform"):
            if len(event) < 4:
                return []
            return [
                PolicyPlayer._row(
                    evt=evt,
                    src=PolicyPlayer._parse_pos(event[2], player_role),
                    tgt=PolicyPlayer._parse_pos(event[3], player_role),
                )
            ]
        elif etype == "turn":
            return [PolicyPlayer._row(evt=EVT["SEP"])]
        elif etype in ("-clearallboost", "-swapsideconditions", "start"):
            return [PolicyPlayer._row(evt=evt)]
        elif len(event) >= 3:
            return [
                PolicyPlayer._row(
                    evt=evt, src=PolicyPlayer._parse_pos(event[2], player_role)
                )
            ]
        return [PolicyPlayer._row(evt=evt)]

    @staticmethod
    def tokenize_team(battle: DoubleBattle) -> list[npt.NDArray[np.float32]]:
        """Emit team tokens with stats (ally) or base stats (opponent)."""
        rows: list[npt.NDArray[np.float32]] = []
        team_evt = EVT["TEAM"]
        moves_evt = EVT["TEAM_MOVES"]
        for side, team in [("ally", battle.team), ("opp", battle.opponent_team)]:
            side_pos = POS[f"{side}_side"]
            is_ally = side == "ally"
            for mon in team.values():
                species = ENT[f"species:{to_id_str(mon.species)}"]
                ability = ENT[f"ability:{mon.ability or 'null'}"]
                item = ENT[f"item:{mon.item or 'null'}"]
                if is_ally and mon.stats:
                    raw = mon.stats
                    s = [(raw[k] or 0) / 255 for k in ["hp", "atk", "def", "spa", "spd", "spe"]]
                else:
                    raw = mon.base_stats
                    s = [raw[k] / 255 for k in ["hp", "atk", "def", "spa", "spd", "spe"]]
                rows.append(
                    PolicyPlayer._row(
                        evt=team_evt,
                        src=side_pos,
                        e1=species,
                        e2=ability,
                        e3=item,
                        stat_hp=s[0],
                        stat_atk=s[1],
                        stat_def=s[2],
                        stat_spa=s[3],
                        stat_spd=s[4],
                        stat_spe=s[5],
                    )
                )
                move_ids = [ENT[f"move:{m}"] for m in mon.moves]
                move_ids += [ENT["move:null"]] * (4 - len(move_ids))
                rows.append(
                    PolicyPlayer._row(
                        evt=moves_evt,
                        src=side_pos,
                        e1=move_ids[0],
                        e2=move_ids[1],
                        e3=move_ids[2],
                        e4=move_ids[3],
                    )
                )
        return rows

    @staticmethod
    def tokenize_teampreview_action(
        battle: DoubleBattle,
    ) -> list[npt.NDArray[np.float32]]:
        """Emit tokens for mons the player selected in teampreview."""
        rows: list[npt.NDArray[np.float32]] = []
        tp_evt = EVT["TEAMPREVIEW_ACTION"]
        for mon in battle.team.values():
            if mon.selected_in_teampreview:
                species = ENT[f"species:{to_id_str(mon.species)}"]
                rows.append(PolicyPlayer._row(evt=tp_evt, e1=species))
        return rows


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
        obs = self.tokenize_battle(battle, fake_rating=2000)
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
                actions, _, _ = self.policy.forward(
                    obs_dict, deterministic=self.deterministic
                )
            actions = actions.cpu().numpy()

            # dispatch
            for req, act in zip(requests, actions):
                req.result = act
                req.event.set()
