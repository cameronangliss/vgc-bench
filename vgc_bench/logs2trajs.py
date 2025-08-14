import asyncio
import json
import os
import pickle
import random
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from itertools import islice
from threading import Thread

import numpy as np
import numpy.typing as npt
from imitation.data.types import Trajectory
from poke_env import to_id_str
from poke_env.battle import AbstractBattle, DoubleBattle, SPECIAL_MOVES, Move
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
from src.agent import Agent
from src.utils import act_len, all_formats, chunk_obs_len


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
        order1 = self.get_order(battle, self.next_msg, 0)
        order2 = self.get_order(battle, self.next_msg, 1)
        order = DoubleBattleOrder(order1, order2)
        action = DoublesEnv.order_to_action(order, battle, fake=True)
        if 0 not in action or not (
            np.all(action == 0) or f"|faint|{battle.player_role}" in self.next_msg
        ):
            self.states += [deepcopy(battle)]
            self.actions += [action]
        return order

    def teampreview(self, battle: AbstractBattle) -> str:
        assert self.next_msg is not None
        assert isinstance(battle, DoubleBattle)
        id1 = self.get_teampreview_order(battle, self.next_msg, 0)
        id2 = self.get_teampreview_order(battle, self.next_msg, 1)
        id3, id4 = random.sample([i for i in range(1, 7) if i not in [id1, id2]], k=2)
        order_str = f"/team {id1}{id2}{id3}{id4}"
        order1a = SingleBattleOrder(list(battle.team.values())[id1 - 1])
        order1b = SingleBattleOrder(list(battle.team.values())[id2 - 1])
        order1 = DoubleBattleOrder(order1a, order1b)
        action1 = DoublesEnv.order_to_action(order1, battle, fake=True)
        upd_battle = _EnvPlayer._simulate_teampreview_switchin(order1, battle)
        order2a = SingleBattleOrder(list(battle.team.values())[id3 - 1])
        order2b = SingleBattleOrder(list(battle.team.values())[id4 - 1])
        order2 = DoubleBattleOrder(order2a, order2b)
        action2 = DoublesEnv.order_to_action(order2, upd_battle, fake=True)
        self.states += [deepcopy(battle), upd_battle]
        self.actions += [action1, action2]
        return order_str

    @staticmethod
    def get_order(battle: DoubleBattle, msg: str, pos: int) -> SingleBattleOrder:
        slot = "a" if pos == 0 else "b"
        lines = msg.split("\n")
        order = PassBattleOrder()
        for line in lines:
            if line.startswith(f"|move|{battle.player_role}{slot}: ") and "[from]" not in line:
                [_, _, identifier, move_id, target_identifier, *_] = line.split("|")
                active = battle.active_pokemon[pos]
                assert active is not None, battle.player_role
                if to_id_str(move_id) in SPECIAL_MOVES:
                    move = Move(to_id_str(move_id), gen=battle.gen)
                else:
                    move = active.moves[to_id_str(move_id)]
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
            elif line.startswith(f"|switch|{battle.player_role}{slot}: ") or line.startswith(
                f"|drag|{battle.player_role}{slot}: "
            ):
                [_, _, identifier, details, *_] = line.split("|")
                mon = battle.get_pokemon(identifier, details=details)
                order = SingleBattleOrder(mon)
            elif line.startswith("|switch|") or line.startswith("|drag|"):
                [_, _, identifier, details, *_] = line.split("|")
                battle.get_pokemon(identifier, details=details)
        return order

    @staticmethod
    def get_teampreview_order(battle: AbstractBattle, msg: str, pos: int) -> int:
        slot = "a" if pos == 0 else "b"
        start = msg.index(f"|switch|{battle.player_role}{slot}: ")
        end = msg.index("\n", start)
        [_, _, identifier, details, *_] = msg[start:end].split("|")
        mon = battle.get_pokemon(identifier, details=details)
        index = list(battle.team.values()).index(mon)
        return index + 1

    async def follow_log(
        self, tag: str, log: str
    ) -> tuple[npt.NDArray[np.float32], npt.NDArray[np.int64]]:
        self.states = []
        self.actions = []
        tag = f"battle-{tag}"
        messages = [f">{tag}\n" + m for m in log.split("\n|\n")]
        battle = await self._create_battle(f">{tag}".split("-"))
        assert isinstance(battle, DoubleBattle)
        battle.logger = None
        split_messages = [m.split("|") for m in messages[0].split("\n")]
        await self._handle_battle_message(split_messages)
        for i in range(1, len(messages)):
            split_messages = [m.split("|") for m in messages[i].split("\n")]
            self.next_msg = messages[i]
            if i == 1:
                battle._teampreview = True
                self.teampreview(battle)
                battle._teampreview = False
            elif "|switch|" in self.next_msg or "|move|" in self.next_msg:
                self.choose_move(battle)
            await self._handle_battle_message(split_messages)
        self.states += [deepcopy(battle)]
        teampreview_draft = [
            i
            for i, p in enumerate(battle.team.values())
            if i + 1 not in self.actions[0] and p.revealed
        ]
        if teampreview_draft:
            rand = random.choice(range(len(teampreview_draft)))
            self.actions[1][0] = teampreview_draft.pop(rand) + 1
        if teampreview_draft:
            self.actions[1][1] = teampreview_draft[0] + 1
        elif self.actions[1][0] == self.actions[1][1]:
            self.actions[1][1] = random.choice(
                [i for i in range(1, 7) if i not in self.actions[0] and i not in self.actions[1]]
            )
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


def process_logs(
    log_jsons: dict[str, tuple[str, str]],
    executor: ProcessPoolExecutor,
    min_rating: int | None = None,
    strict: bool = False,
) -> list[Trajectory]:

    def chunked(iterable, size):
        it = iter(iterable)
        while chunk := list(islice(it, size)):
            yield chunk

    trajs = []
    task_params = [(tag, log, "p1", min_rating) for tag, (_, log) in log_jsons.items()] + [
        (tag, log, "p2", min_rating) for tag, (_, log) in log_jsons.items()
    ]
    num_empty = 0
    num_errors = 0
    for chunk in chunked(task_params, 10_000):
        tasks = [executor.submit(process_log, *params) for params in chunk]
        for task in as_completed(tasks):
            try:
                traj = task.result()
                if traj is None:
                    num_empty += 1
                else:
                    trajs += [traj]
            except KeyboardInterrupt:
                raise
            except SystemExit:
                raise
            except Exception as e:
                if strict:
                    raise e
                else:
                    num_errors += 1
    num_trans = sum([len(t.acts) for t in trajs])
    print(
        f"prepared {len(trajs)} trajectories with {num_trans} transitions "
        f"({num_empty} discarded trajs, {num_errors} failed traj reads)"
    )
    return trajs


def process_log(tag: str, log: str, role: str, min_rating: int | None) -> Trajectory | None:
    start_index = log.index(f"|player|{role}|")
    end_index = log.index("\n", start_index)
    _, _, _, username, _, rating = log[start_index:end_index].split("|")
    if min_rating is None or (rating and int(rating) >= min_rating):
        player = LogReader(
            account_configuration=AccountConfiguration(username, None),
            battle_format=tag.split("-")[0],
            log_level=51,
            accept_open_team_sheet=True,
            loop=_READER_LOOP,
        )
        results = asyncio.run_coroutine_threadsafe(
            player.follow_log(tag, log), _READER_LOOP
        ).result()
        if results is not None:
            states, actions = results
            traj = Trajectory(obs=states, acts=actions, infos=None, terminal=True)
            return traj


if __name__ == "__main__":

    def _init_worker_loop():
        global _READER_LOOP
        _READER_LOOP = asyncio.new_event_loop()
        Thread(target=_READER_LOOP.run_forever, daemon=True).start()

    executor = ProcessPoolExecutor(max_workers=64, initializer=_init_worker_loop)
    os.makedirs("data/trajs", exist_ok=True)
    total = 0
    for f in all_formats:
        with open(f"data/logs-{f}.json", "r") as file:
            logs = json.load(file)
        print(f"processing {len(logs)} {f} logs...")
        trajs = process_logs(logs, executor)
        for i, traj in enumerate(trajs, start=total):
            with open(f"data/trajs/{i:08d}.pkl", "wb") as f:
                pickle.dump(traj, f)
        total += len(trajs)
