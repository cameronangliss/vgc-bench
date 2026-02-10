"""
Log-to-trajectory converter for VGC-Bench.

Parses Pokemon Showdown battle logs and converts them into trajectory data
suitable for imitation learning. Extracts state-action pairs from recorded
battles to create training data for behavior cloning.
"""

import argparse
import asyncio
import json
import pickle
import random
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from itertools import islice
from pathlib import Path
from threading import Thread

import numpy as np
import numpy.typing as npt
from imitation.data.types import Trajectory
from poke_env import to_id_str
from poke_env.battle import SPECIAL_MOVES, AbstractBattle, DoubleBattle, Move
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

from vgc_bench.src.policy_player import PolicyPlayer
from vgc_bench.src.utils import act_len, all_formats, chunk_obs_len


class LogReader(Player):
    """
    A player that reads and replays battle logs to extract state-action pairs.

    Parses Pokemon Showdown battle logs, simulating the battle progression
    to reconstruct game states and extract the actions taken at each turn.
    Used to convert recorded battles into trajectory data for training.

    Attributes:
        states: List of battle states encountered during log replay.
        actions: List of actions taken at each state.
        next_msg: The next message to process from the log.
    """

    states: list[DoubleBattle]
    actions: list[npt.NDArray[np.int64]]
    msg: str | None

    def __init__(self, *args, **kwargs):
        """Initialize the LogReader with empty state and action lists."""
        super().__init__(start_listening=False, *args, **kwargs)
        self.states = []
        self.actions = []
        self.next_msg = None

    async def _handle_battle_request(
        self, battle: AbstractBattle, maybe_default_order: bool = False
    ):
        """Override to do nothing; log replay handles battle progression."""
        pass

    def choose_move(self, battle: AbstractBattle) -> BattleOrder:
        """
        Extract the move choice from the log message and record the state-action pair.

        Args:
            battle: The current battle state.

        Returns:
            The battle order extracted from the log.
        """
        assert self.next_msg is not None
        assert isinstance(battle, DoubleBattle)
        order1 = self.get_order(battle, self.next_msg, 0)
        order2 = self.get_order(battle, self.next_msg, 1)
        order = DoubleBattleOrder(order1, order2)
        action = DoublesEnv.order_to_action(order, battle, fake=True)
        battle._available_moves = [[], []]
        if 0 not in action or not (
            np.all(action == 0) or f"|faint|{battle.player_role}" in self.next_msg
        ):
            self.states += [deepcopy(battle)]
            self.actions += [action]
        return order

    def teampreview(self, battle: AbstractBattle) -> str:
        """
        Extract teampreview choices from the log and record the state-action pairs.

        Args:
            battle: The current battle state during team preview.

        Returns:
            The team order string for Pokemon Showdown.
        """
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
        """
        Parse a battle log message to extract the order for a specific slot.

        Args:
            battle: The current battle state.
            msg: The log message containing move/switch information.
            pos: The active slot position (0 or 1).

        Returns:
            The parsed battle order for the specified slot.
        """
        slot = "a" if pos == 0 else "b"
        lines = msg.split("\n")
        order = PassBattleOrder()
        for line in lines:
            if (
                line.startswith(f"|move|{battle.player_role}{slot}: ")
                and "[from]" not in line
            ):
                [_, _, identifier, move_id, target_identifier, *_] = line.split("|")
                active = battle.active_pokemon[pos]
                assert active is not None, battle.player_role
                if to_id_str(move_id) in SPECIAL_MOVES:
                    move = Move(to_id_str(move_id), gen=battle.gen)
                    battle._available_moves[pos] += [move]
                else:
                    move = active.moves[to_id_str(move_id)]
                target_lines = [
                    l for l in msg.split("\n") if f"|switch|{target_identifier}" in l
                ]
                target_details = target_lines[0].split("|")[3] if target_lines else ""
                target = (
                    battle.get_pokemon(target_identifier, details=target_details)
                    if ": " in target_identifier
                    else None
                )
                did_tera = f"|-terastallize|{identifier}|" in msg
                order = SingleBattleOrder(
                    move,
                    terastallize=did_tera,
                    move_target=battle.to_showdown_target(move, target),
                )
            elif line.startswith(
                f"|switch|{battle.player_role}{slot}: "
            ) or line.startswith(f"|drag|{battle.player_role}{slot}: "):
                [_, _, identifier, details, *_] = line.split("|")
                mon = battle.get_pokemon(identifier, details=details)
                order = SingleBattleOrder(mon)
            elif line.startswith(f"|swap|{battle.player_role}{slot}: "):
                slot = "b" if slot == "a" else "a"
            elif line.startswith("|switch|") or line.startswith("|drag|"):
                [_, _, identifier, details, *_] = line.split("|")
                battle.get_pokemon(identifier, details=details)
        return order

    @staticmethod
    def get_teampreview_order(battle: AbstractBattle, msg: str, pos: int) -> int:
        """
        Parse a log message to determine which Pokemon was sent out at teampreview.

        Args:
            battle: The current battle state.
            msg: The log message containing switch information.
            pos: The active slot position (0 or 1).

        Returns:
            The 1-indexed position of the Pokemon in the team.
        """
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
        """
        Replay a battle log to extract embedded states and actions.

        Args:
            tag: The battle tag identifier.
            log: The full battle log string.

        Returns:
            Tuple of (embedded_states, actions) arrays for the trajectory.
        """
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
            for i, p in enumerate(battle.team.values(), start=1)
            if i not in self.actions[0] and p.revealed
        ]
        if teampreview_draft:
            rand = random.choice(range(len(teampreview_draft)))
            self.actions[1][0] = teampreview_draft.pop(rand)
        if teampreview_draft:
            self.actions[1][1] = teampreview_draft[0]
        elif self.actions[1][0] == self.actions[1][1]:
            self.actions[1][1] = random.choice(
                [
                    i
                    for i in range(1, 7)
                    if i not in self.actions[0] and i not in self.actions[1]
                ]
            )
        actions = np.stack(self.actions, axis=0)
        return self.embed_states(self.states, actions), actions

    @staticmethod
    def embed_states(
        states: list[DoubleBattle], actions: npt.NDArray[np.int64]
    ) -> npt.NDArray[np.float32]:
        """
        Convert a list of battle states to embedded observation arrays.

        Args:
            states: List of battle states to embed.
            actions: Actions taken at each state (used for teampreview tracking).

        Returns:
            Stacked array of embedded state observations.
        """
        embedded_states = []
        teampreview_draft = []
        for i, state in enumerate(states):
            if i in [1, 2]:
                teampreview_draft += actions[i - 1].tolist()
            embedded_state = PolicyPlayer.embed_battle(state, teampreview_draft)
            assert embedded_state.shape == (2 * act_len + 12 * chunk_obs_len,)
            embedded_states += [embedded_state]
        return np.stack(embedded_states, axis=0)


def process_logs(
    log_jsons: dict[str, tuple[str, str]],
    executor: ProcessPoolExecutor,
    min_rating: int | None,
    only_winner: bool,
    strict: bool,
) -> list[Trajectory]:
    """
    Process multiple battle logs in parallel to extract trajectories.

    Args:
        log_jsons: Dictionary mapping battle tags to (timestamp, log) tuples.
        executor: Process pool for parallel processing.
        min_rating: Minimum player rating to include (None for no filter).
        only_winner: If True, only extract trajectories from the winner's perspective.
        strict: If True, raise exceptions on parsing errors; otherwise skip.

    Returns:
        List of Trajectory objects extracted from the logs.
    """

    def chunked(iterable, size):
        it = iter(iterable)
        while chunk := list(islice(it, size)):
            yield chunk

    trajs = []
    task_params = [
        (tag, log, "p1", min_rating, only_winner) for tag, (_, log) in log_jsons.items()
    ] + [
        (tag, log, "p2", min_rating, only_winner) for tag, (_, log) in log_jsons.items()
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


def process_log(
    tag: str, log: str, role: str, min_rating: int | None, only_winner: bool
) -> Trajectory | None:
    """
    Process a single battle log to extract a trajectory for one player.

    Args:
        tag: The battle tag identifier.
        log: The full battle log string.
        role: The player role to extract ("p1" or "p2").
        min_rating: Minimum rating threshold (None to skip check).
        only_winner: If True, only return trajectory if this player won.

    Returns:
        Trajectory object if criteria met, None otherwise.
    """
    start_index = log.index(f"|player|{role}|")
    end_index = log.index("\n", start_index)
    _, _, _, username, _, rating = log[start_index:end_index].split("|")
    win_start_index = log.index("|win|")
    win_end_index = log.index("\n", win_start_index)
    _, _, winner = log[win_start_index:win_end_index].split("|")
    if (not only_winner or winner == username) and (
        min_rating is None or (rating and int(rating) >= min_rating)
    ):
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


def main(num_workers: int, min_rating: int | None, only_winner: bool, strict: bool):
    """
    Main entry point for converting logs to trajectories.

    Processes all battle logs in data/logs-*.json files and saves extracted
    trajectories as pickle files in data/trajs/.

    Args:
        num_workers: Number of parallel worker processes.
        min_rating: Minimum player rating to include.
        only_winner: If True, only extract winner trajectories.
        strict: If True, crash on parsing errors; otherwise skip problematic logs.
    """

    def _init_worker_loop():
        global _READER_LOOP
        _READER_LOOP = asyncio.new_event_loop()
        Thread(target=_READER_LOOP.run_forever, daemon=True).start()

    executor = ProcessPoolExecutor(
        max_workers=num_workers, initializer=_init_worker_loop
    )
    Path("trajs").mkdir(exist_ok=True)
    total = 0
    for f in all_formats:
        with open(f"battle-logs/logs-{f}.json", "r") as file:
            logs = json.load(file)
        print(f"processing {len(logs)} {f} logs...")
        trajs = process_logs(logs, executor, min_rating, only_winner, strict)
        for i, traj in enumerate(trajs, start=total):
            with open(f"trajs/{i:08d}.pkl", "wb") as f:
                pickle.dump(traj, f)
        total += len(trajs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parses logs in data/ folder into trajectories stored in data/trajs/"
    )
    parser.add_argument(
        "--num_workers", type=int, default=1, help="number of parallel log parsers"
    )
    parser.add_argument(
        "--min_rating",
        type=int,
        default=None,
        help="minimum Elo rating to parse in that player's perspective",
    )
    parser.add_argument(
        "--only_winner",
        action="store_true",
        help="skips parsing logs in the perspective of the player that lost",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="will crash program if a log fails to parse (WARNING: mostly useful for debugging; some logs, such as those with Ditto, are known to not parse)",
    )
    args = parser.parse_args()
    main(args.num_workers, args.min_rating, args.only_winner, args.strict)
