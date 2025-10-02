import random
from typing import Any, Awaitable, Deque

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
from poke_env.environment import DoublesEnv
from poke_env.player import BattleOrder, DefaultBattleOrder, Player
from ray.rllib.core import Columns
from ray.rllib.models.torch.torch_distributions import TorchCategorical
from src.policy import ActorCriticModule
from src.utils import abilities, act_len, chunk_obs_len, items, move_obs_len, moves, pokemon_obs_len


class PolicyPlayer(Player):
    policy: ActorCriticModule | None
    _frames: dict[str, Deque[npt.NDArray[np.float32]]] = {}
    _teampreview_drafts: dict[str, list[int]] = {}

    def __init__(
        self, device: str, policy: ActorCriticModule | None = None, *args: Any, **kwargs: Any
    ):
        super().__init__(*args, **kwargs)
        self.device = device
        self.policy = policy

    def choose_move(self, battle: AbstractBattle) -> BattleOrder | Awaitable[BattleOrder]:
        assert isinstance(battle, DoubleBattle)
        assert isinstance(self.policy, ActorCriticModule)
        if battle._wait:
            return DefaultBattleOrder()
        obs1 = self.get_observation(battle, np.int64(-1))
        with torch.no_grad():
            obs_tensor1 = torch.as_tensor(obs1, device=self.device).unsqueeze(0)
            output1 = self.policy.forward({Columns.OBS: obs_tensor1})
            dist1 = TorchCategorical(logits=output1[Columns.ACTION_DIST_INPUTS])
            action1 = dist1.sample()[0].cpu().numpy()
        obs2 = self.get_observation(battle, np.int64(action1))
        with torch.no_grad():
            obs_tensor2 = torch.as_tensor(obs2, device=self.device).unsqueeze(0)
            output2 = self.policy.forward({Columns.OBS: obs_tensor2})
            dist2 = TorchCategorical(logits=output2[Columns.ACTION_DIST_INPUTS])
            action2 = dist2.sample()[0].cpu().numpy()
        return self.get_order(battle, np.array([action1, action2]))

    def get_observation(
        self, battle: DoubleBattle, last_action: np.int64
    ) -> npt.NDArray[np.float32]:
        assert isinstance(self.policy, ActorCriticModule)
        # remove finished battles
        self._teampreview_drafts = {
            tag: preview
            for tag, preview in self._teampreview_drafts.items()
            if tag in self.battles and not self.battles[tag].finished
        }
        self._frames = {
            tag: frame
            for tag, frame in self._frames.items()
            if tag in self.battles and not self.battles[tag].finished
        }
        # initialize tracking for new battles
        if battle.battle_tag not in self._teampreview_drafts:
            self._teampreview_drafts[battle.battle_tag] = []
        if battle.battle_tag not in self._frames and self.policy.model.num_frames > 1:
            self._frames[battle.battle_tag] = Deque(maxlen=self.policy.model.num_frames)
            for _ in range(self.policy.model.num_frames):
                self._frames[battle.battle_tag].append(
                    np.zeros((2 * act_len + 12 * chunk_obs_len + 1,), dtype=np.float32)
                )
        # embed battle into observation
        obs = self.embed_battle(
            battle, self._teampreview_drafts[battle.battle_tag], fake_rating=True
        )
        obs = np.append(obs, np.float32(last_action))
        if self.policy.model.num_frames > 1:
            self._frames[battle.battle_tag].append(obs)
            obs = np.concatenate(self._frames[battle.battle_tag])
        return obs

    def get_order(self, battle: DoubleBattle, action: npt.NDArray[np.int64]) -> BattleOrder:
        assert isinstance(self.policy, ActorCriticModule)
        if battle.teampreview:
            if not self.policy.model.chooses_on_teampreview:
                available_actions = [
                    i for i in range(1, 7) if i not in self._teampreview_drafts[battle.battle_tag]
                ]
                action = np.array(random.sample(available_actions, k=2))
            self._teampreview_drafts[battle.battle_tag] += action.tolist()
        return DoublesEnv.action_to_order(action, battle)

    def teampreview(self, battle: AbstractBattle) -> str | Awaitable[str]:
        assert isinstance(battle, DoubleBattle)
        assert isinstance(self.policy, ActorCriticModule)
        if not self.policy.model.chooses_on_teampreview:
            message = self.random_teampreview(battle)
            self._teampreview_drafts[battle.battle_tag] = [int(i) for i in message[6:-2]]
            return message
        order1 = self.choose_move(battle)
        assert not isinstance(order1, Awaitable)
        action1 = DoublesEnv.order_to_action(order1, battle)
        order2 = self.choose_move(battle)
        assert not isinstance(order2, Awaitable)
        action2 = DoublesEnv.order_to_action(order2, battle)
        return f"/team {action1[0]}{action1[1]}{action2[0]}{action2[1]}"

    @staticmethod
    def embed_battle(
        battle: AbstractBattle, teampreview_draft: list[int], fake_rating: bool = False
    ) -> npt.NDArray[np.float32]:
        assert isinstance(battle, DoubleBattle)
        if not battle._last_request:
            mask = np.ones(2 * act_len, dtype=np.float32)
        else:
            mask1 = PolicyPlayer.get_action_mask(battle, 0, teampreview_draft)
            mask2 = PolicyPlayer.get_action_mask(battle, 1, teampreview_draft)
            mask = np.array(mask1 + mask2)
        glob = PolicyPlayer.embed_global(battle)
        side = PolicyPlayer.embed_side(battle, fake_rating)
        opp_side = PolicyPlayer.embed_side(battle, False, opp=True)
        [a1, a2, *_] = battle.active_pokemon
        [o1, o2, *_] = battle.opponent_active_pokemon
        assert battle.teampreview == (len(teampreview_draft) < 4)
        assert all(
            [
                i in teampreview_draft
                for i, p in enumerate(battle.team.values(), start=1)
                if p.active
            ]
        )
        pokemons = [
            PolicyPlayer.embed_pokemon(
                p,
                i,
                from_opponent=False,
                active_a=a1 is not None and p.name == a1.name,
                active_b=a2 is not None and p.name == a2.name,
                in_draft=i + 1 in teampreview_draft,
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
        opp_pokemons += [np.zeros(pokemon_obs_len, dtype=np.float32)] * (6 - len(opp_pokemons))
        return np.concatenate(
            [mask]
            + [np.concatenate([glob, side, p]) for p in pokemons]
            + [np.concatenate([glob, opp_side, p]) for p in opp_pokemons],
            dtype=np.float32,
        )

    @staticmethod
    def embed_global(battle: DoubleBattle) -> npt.NDArray[np.float32]:
        weather = [
            (min(battle.turn - battle.weather[w], 8) / 8 if w in battle.weather else 0)
            for w in Weather
        ]
        fields = [
            min(battle.turn - battle.fields[f], 8) / 8 if f in battle.fields else 0 for f in Field
        ]
        teampreview = float(battle.teampreview)
        reviving = float(battle.reviving)
        return np.array([*weather, *fields, reviving, teampreview], dtype=np.float32)

    @staticmethod
    def embed_side(
        battle: DoubleBattle, fake_rating: bool, opp: bool = False
    ) -> npt.NDArray[np.float32]:
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
        player = battle.opponent_role if opp else battle.player_role
        rat = [p for p in battle._players if p["player"] == player][0].get("rating", "0")
        rating = 1 if fake_rating else int(rat or "0") / 2000
        return np.array([*side_conditions, *gimmicks, rating], dtype=np.float32)

    @staticmethod
    def embed_pokemon(
        pokemon: Pokemon,
        pos: int,
        from_opponent: bool,
        active_a: bool,
        active_b: bool,
        in_draft: bool = False,
    ) -> npt.NDArray[np.float32]:
        # (mostly) stable fields
        ability_id = abilities.index("null" if pokemon.ability is None else pokemon.ability)
        item_id = items.index("null" if pokemon.item is None else pokemon.item)
        move_ids = [
            moves.index("hiddenpower" if move.id.startswith("hiddenpower") else move.id)
            for move in pokemon.moves.values()
        ]
        move_ids += [0] * (4 - len(move_ids))
        move_embeds = [PolicyPlayer.embed_move(move) for move in pokemon.moves.values()]
        move_embeds += [np.zeros(move_obs_len, dtype=np.float32)] * (4 - len(move_embeds))
        move_embeds = np.concatenate(move_embeds)
        types = [float(t in pokemon.types) for t in PokemonType]
        tera_type = [float(t == pokemon.tera_type) for t in PokemonType]
        stats = [(s or 0) / 1000 for s in pokemon.stats.values()]
        gender = [float(g == pokemon.gender) for g in PokemonGender]
        weight = pokemon.weight / 1000
        # volatile fields
        hp_frac = pokemon.current_hp_fraction
        revealed = float(pokemon.revealed)
        status = [float(s == pokemon.status) for s in Status]
        status_counter = pokemon.status_counter / 16
        boosts = [b / 6 for b in pokemon.boosts.values()]
        effects = [(min(pokemon.effects[e], 8) / 8 if e in pokemon.effects else 0) for e in Effect]
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
                float(in_draft),
            ],
            dtype=np.float32,
        )

    @staticmethod
    def embed_move(move: Move) -> npt.NDArray[np.float32]:
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
            ],
            dtype=np.float32,
        )

    @staticmethod
    def get_action_mask(battle: DoubleBattle, pos: int, teampreview_draft: list[int]) -> list[int]:
        switch_space = [
            i + 1
            for i, pokemon in enumerate(battle.team.values())
            if not battle.trapped[pos]
            and pokemon.base_species in [p.base_species for p in battle.available_switches[pos]]
        ]
        active_mon = battle.active_pokemon[pos]
        if battle._wait or (any(battle.force_switch) and not battle.force_switch[pos]):
            actions = [0]
        elif all(battle.force_switch) and len(battle.available_switches[0]) == 1:
            actions = switch_space + [0]
        elif battle.teampreview:
            assert teampreview_draft is not None
            actions = [s for s in switch_space if s not in teampreview_draft]
        elif active_mon is None:
            actions = switch_space
        else:
            move_spaces = [
                [7 + 5 * i + j + 2 for j in battle.get_possible_showdown_targets(move, active_mon)]
                for i, move in enumerate(active_mon.moves.values())
                if move.id in [m.id for m in battle.available_moves[pos]]
            ]
            move_space = [i for s in move_spaces for i in s]
            tera_space = [i + 80 for i in move_space if battle.can_tera[pos]]
            if (
                not move_space
                and len(battle.available_moves[pos]) == 1
                and battle.available_moves[pos][0].id in ["struggle", "recharge"]
            ):
                move_space = [9]
            actions = switch_space + move_space + tera_space
        actions = actions or [0]
        action_mask = [int(i in actions) for i in range(act_len)]
        return action_mask


# @dataclass
# class _BatchReq:
#     obs: npt.NDArray[np.float32]
#     event: asyncio.Event
#     result: npt.NDArray[np.int64] | None = None


# class BatchPolicyPlayer(PolicyPlayer):
#     def __init__(self, *args: Any, **kwargs: Any):
#         super().__init__(*args, **kwargs)
#         self._q: asyncio.Queue[_BatchReq] = asyncio.Queue()
#         self._worker_task: asyncio.Task | None = None

#     def choose_move(self, battle: AbstractBattle) -> Awaitable[BattleOrder]:
#         return self._choose_move(battle)

#     async def _choose_move(self, battle: AbstractBattle) -> BattleOrder:
#         assert isinstance(battle, DoubleBattle)
#         if battle._wait:
#             return DefaultBattleOrder()
#         obs = self.get_observation(battle)
#         if self._worker_task is None:
#             self._worker_task = asyncio.create_task(self._inference_loop())
#         req = _BatchReq(obs=obs, event=asyncio.Event())
#         await self._q.put(req)
#         await req.event.wait()
#         assert req.result is not None
#         action = req.result
#         return self.get_order(battle, action)

#     def teampreview(self, battle: AbstractBattle) -> Awaitable[str]:
#         return self._teampreview(battle)

#     async def _teampreview(self, battle: AbstractBattle) -> str:
#         assert isinstance(battle, DoubleBattle)
#         assert isinstance(self.policy, ActorCriticModule)
#         order1 = await self.choose_move(battle)
#         upd_battle = _EnvPlayer._simulate_teampreview_switchin(order1, battle)
#         order2 = await self.choose_move(upd_battle)
#         action1 = DoublesEnv.order_to_action(order1, battle)
#         action2 = DoublesEnv.order_to_action(order2, upd_battle)
#         if self.policy.model.chooses_on_teampreview:
#             return f"/team {action1[0]}{action1[1]}{action2[0]}{action2[1]}"
#         else:
#             message = self.random_teampreview(battle)
#             self._teampreview_drafts[battle.battle_tag] = [int(i) for i in message[6:-2]]
#             return message

#     async def _inference_loop(self) -> None:
#         assert isinstance(self.policy, ActorCriticModule)
#         while True:
#             # gather requests
#             requests = [await self._q.get()]
#             just_slept = False
#             while len(requests) < self._max_concurrent_battles:
#                 try:
#                     req = self._q.get_nowait()
#                     requests.append(req)
#                     just_slept = False
#                 except asyncio.QueueEmpty:
#                     if just_slept:
#                         break
#                     await asyncio.sleep(0.005)
#                     just_slept = True

#             # run inference
#             obs = np.stack([r.obs for r in requests], axis=0)
#             with torch.no_grad():
#                 obs_tensor = torch.as_tensor(obs, device=self.device)
#                 actions, _, _ = self.policy.forward(obs_tensor)
#             actions = actions.cpu().numpy()

#             # dispatch
#             for req, act in zip(requests, actions):
#                 req.result = act
#                 req.event.set()
