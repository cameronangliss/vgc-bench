import asyncio
import json
import os
import pickle
from copy import deepcopy

import numpy as np
import numpy.typing as npt
from imitation.data.types import Trajectory
from poke_env import to_id_str
from poke_env.battle import AbstractBattle, DoubleBattle
from poke_env.environment import DoublesEnv
from poke_env.environment.env import _EnvPlayer
from poke_env.player import (
    BattleOrder,
    DoubleBattleOrder,
    PassBattleOrder,
    Player,
    SingleBattleOrder,
)
from poke_env.ps_client import AccountConfiguration
from scrape_logs import battle_formats
from src.agent import Agent
from src.utils import act_len, chunk_obs_len

MIN_RATING: int | None = 1200


class LogReader(Player):
    states: list[DoubleBattle]
    actions: list[npt.NDArray[np.int64]]
    msg: str | None

    def __init__(self, *args, **kwargs):
        super().__init__(start_listening=False, *args, **kwargs)
        self.states = []
        self.actions = []
        self.next_msg = None
        self.teampreview_draft = []

    async def _handle_battle_request(
        self, battle: AbstractBattle, maybe_default_order: bool = False
    ):
        pass

    def choose_move(self, battle: AbstractBattle) -> BattleOrder:
        assert self.next_msg is not None
        assert isinstance(battle, DoubleBattle)
        order1 = self.get_order(battle, self.next_msg, False)
        order2 = self.get_order(battle, self.next_msg, True)
        order = DoubleBattleOrder(order1, order2)
        action = DoublesEnv.order_to_action(order, battle, fake=True)
        if action[0] != 0 and action[1] != 0:
            self.states += [deepcopy(battle)]
            self.actions += [action]
        return order

    def teampreview(self, battle: AbstractBattle) -> str:
        assert self.next_msg is not None
        assert isinstance(battle, DoubleBattle)
        id1 = self.get_teampreview_order(battle, self.next_msg, False)
        id2 = self.get_teampreview_order(battle, self.next_msg, True)
        all_choices = [i for i in range(1, 7)]
        all_choices.remove(id1)
        all_choices.remove(id2)
        order_str = f"/team {id1}{id2}{all_choices[0]}{all_choices[1]}"
        order1a = SingleBattleOrder(list(battle.team.values())[id1 - 1])
        order1b = SingleBattleOrder(list(battle.team.values())[id2 - 1])
        order1 = DoubleBattleOrder(order1a, order1b)
        action1 = DoublesEnv.order_to_action(order1, battle, fake=True)
        upd_battle = _EnvPlayer._simulate_teampreview_switchin(order1, battle)
        order2a = SingleBattleOrder(list(battle.team.values())[all_choices[0] - 1])
        order2b = SingleBattleOrder(list(battle.team.values())[all_choices[1] - 1])
        order2 = DoubleBattleOrder(order2a, order2b)
        action2 = DoublesEnv.order_to_action(order2, upd_battle, fake=True)
        self.states += [deepcopy(battle), upd_battle]
        self.actions += [action1, action2]
        return order_str

    @staticmethod
    def get_order(battle: DoubleBattle, msg: str, is_right: bool) -> SingleBattleOrder:
        pos = "b" if is_right else "a"
        lines = msg.split("\n")
        order = PassBattleOrder()
        for line in lines:
            if line.startswith(f"|move|{battle.player_role}{pos}: ") and "[from]" not in line:
                [_, _, identifier, move, target_identifier, *_] = line.split("|")
                active = battle.active_pokemon[int(is_right)]
                assert active is not None, battle.active_pokemon
                if to_id_str(move) in active.moves:
                    move = active.moves[to_id_str(move)]
                elif to_id_str(move) == "struggle":
                    move = list(active.moves.values())[0]
                else:
                    continue
                target_lines = [l for l in msg.split("\n") if f"|switch|{target_identifier}" in l]
                target_details = target_lines[0].split("|")[3] if target_lines else ""
                target = (
                    battle.get_pokemon(target_identifier, details=target_details)
                    if ": " in target_identifier
                    else None
                )
                did_tera = f"|-terastallize|{identifier}|" in msg
                order = SingleBattleOrder(
                    move, terastallize=did_tera, move_target=battle.to_showdown_target(move, target)
                )
            elif line.startswith(f"|switch|{battle.player_role}{pos}: ") or line.startswith(
                f"|drag|{battle.player_role}{pos}: "
            ):
                [_, _, identifier, details, *_] = line.split("|")
                mon = battle.get_pokemon(identifier, details=details, request=battle.last_request)
                order = SingleBattleOrder(mon)
            elif line.startswith("|switch|") or line.startswith("|drag|"):
                [_, _, identifier, details, *_] = line.split("|")
                battle.get_pokemon(identifier, details=details)
        return order

    @staticmethod
    def get_teampreview_order(battle: AbstractBattle, msg: str, is_right: bool) -> int:
        pos = "b" if is_right else "a"
        start = msg.index(f"|switch|{battle.player_role}{pos}: ")
        end = msg.index("\n", start)
        [_, _, identifier, details, *_] = msg[start:end].split("|")
        mon = battle.get_pokemon(identifier, details=details, request=battle.last_request)
        index = list(battle.team.values()).index(mon)
        return index + 1

    async def follow_log(
        self, tag: str, log: str
    ) -> tuple[npt.NDArray[np.float32], npt.NDArray[np.int64]]:
        self.states = []
        self.actions = []
        tag = f"battle-{tag}"
        messages = [f">{tag}\n" + m for m in log.split("\n|\n")]
        assert "|win|" not in messages[1]
        for i in range(len(messages) - 1):
            split_messages = [m.split("|") for m in messages[i].split("\n")]
            self.next_msg = messages[i + 1]
            if i == 0:
                battle = await self._create_battle(f">{tag}".split("-"))
                battle.logger = None
                battle._teampreview = True
                await self._handle_battle_message(split_messages)
                self.teampreview(battle)
            else:
                battle = self.battles[tag]
                battle._teampreview = False
                await self._handle_battle_message(split_messages)
                if "|switch|" in messages[i + 1] or "|move|" in messages[i + 1]:
                    self.choose_move(battle)
        split_messages = [m.split("|") for m in messages[-1].split("\n")]
        await self._handle_battle_message(split_messages)
        last_state = self.battles[tag]
        assert isinstance(last_state, DoubleBattle)
        self.states += [deepcopy(last_state)]
        teampreview_draft = [
            i
            for i, p in enumerate(last_state.team.values())
            if i not in self.actions[0] and p.revealed
        ]
        if teampreview_draft:
            self.actions[1][0] = teampreview_draft[0] + 1
        if len(teampreview_draft) > 1:
            self.actions[1][1] = teampreview_draft[1] + 1
        actions = np.stack(self.actions, axis=0)
        return self.embed_states(self.states, actions), actions

    @staticmethod
    def embed_states(
        states: list[DoubleBattle], actions: npt.NDArray[np.int64]
    ) -> npt.NDArray[np.float32]:
        embedded_states = []
        teampreview_draft = []
        for i, state in enumerate(states):
            if i in [1, 2]:
                teampreview_draft += [a - 1 for a in actions[i - 1].tolist()]
            embedded_state = Agent.embed_battle(state, teampreview_draft)
            assert embedded_state.shape == (2 * act_len + 12 * chunk_obs_len,)
            embedded_states += [embedded_state]
        return np.stack(embedded_states, axis=0)


def process_logs(log_jsons: dict[str, tuple[str, str]], strict: bool = False) -> list[Trajectory]:
    trajs = []
    total = 0
    num_errors = 0
    for i, (tag, (_, log)) in enumerate(log_jsons.items()):
        print(f"Progress: {i}/{len(log_jsons)}", end="\r")
        try:
            start_index1 = log.index(f"|player|p1|")
            _, _, _, username1, _, rating1 = log[
                start_index1 : log.index("\n", start_index1)
            ].split("|")
            if MIN_RATING is None or (rating1 and int(rating1) >= MIN_RATING):
                player1 = LogReader(
                    account_configuration=AccountConfiguration(username1, None),
                    battle_format=tag.split("-")[0],
                    log_level=51,
                    accept_open_team_sheet=True,
                )
                states1, actions1 = asyncio.run(player1.follow_log(tag, log))
                total += len(states1)
                trajs += [Trajectory(obs=states1, acts=actions1, infos=None, terminal=True)]
            start_index2 = log.index(f"|player|p2|")
            _, _, _, username2, _, rating2 = log[
                start_index2 : log.index("\n", start_index2)
            ].split("|")
            if MIN_RATING is None or (rating2 and int(rating2) >= MIN_RATING):
                player2 = LogReader(
                    account_configuration=AccountConfiguration(username2, None),
                    battle_format=tag.split("-")[0],
                    log_level=51,
                    accept_open_team_sheet=True,
                )
                states2, actions2 = asyncio.run(player2.follow_log(tag, log))
                total += len(states2)
                trajs += [Trajectory(obs=states2, acts=actions2, infos=None, terminal=True)]
        except KeyboardInterrupt:
            raise
        except SystemExit:
            raise
        except Exception as e:
            if strict:
                raise e
            else:
                num_errors += 1
    print(
        f"prepared {len(trajs)} trajectories "
        f"with {total} total state-action pairs "
        f"(and {num_errors} games thrown away)"
    )
    return trajs


if __name__ == "__main__":
    os.makedirs("data/trajs", exist_ok=True)
    total = 0
    for f in battle_formats:
        with open(f"data/logs-{f}.json", "r") as file:
            logs = json.load(file)
        trajs = process_logs(logs, strict=False)
        for i, traj in enumerate(trajs, start=total):
            width = len(str(len(trajs)))
            with open(f"data/trajs/{i:0{width}d}.pkl", "wb") as f:
                pickle.dump(traj, f)
        total += len(trajs)
