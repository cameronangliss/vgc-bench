import asyncio
import json
import os

import numpy as np
import numpy.typing as npt
import pandas as pd
from poke_env import to_id_str
from poke_env.environment import AbstractBattle, DoubleBattle
from poke_env.player import BattleOrder, DoubleBattleOrder, DoublesEnv, Player
from poke_env.ps_client import AccountConfiguration
from ray.rllib.core import Columns
from ray.rllib.env.single_agent_episode import SingleAgentEpisode
from scrape_logs import battle_formats
from src.agent import Agent
from src.utils import doubles_chunk_obs_len

MIN_RATING = 1200


class LogReader(Player):
    states: list[npt.NDArray[np.float32]]
    actions: list[npt.NDArray[np.int64]]
    msg: str | None
    teampreview_draft: list[int]

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
        state = Agent.embed_battle(battle, self.teampreview_draft)
        action = DoublesEnv.order_to_action(order, battle, fake=True)
        if action[0] != 0 and action[1] != 0:
            self.states += [state]
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
        order1 = BattleOrder(list(battle.team.values())[id1 - 1])
        order2 = BattleOrder(list(battle.team.values())[id2 - 1])
        order = DoubleBattleOrder(order1, order2)
        state = Agent.embed_battle(battle, self.teampreview_draft)
        assert state.shape == (12 * doubles_chunk_obs_len,)
        action = DoublesEnv.order_to_action(order, battle, fake=True)
        self.states += [state]
        self.actions += [action]
        self.teampreview_draft = [id1 - 1, id2 - 1, all_choices[0] - 1, all_choices[1] - 1]
        return order_str

    @staticmethod
    def get_order(battle: DoubleBattle, msg: str, is_right: bool) -> BattleOrder | None:
        pos = "b" if is_right else "a"
        lines = msg.split("\n")
        order = None
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
                order = BattleOrder(
                    move, terastallize=did_tera, move_target=battle.to_showdown_target(move, target)
                )
            elif line.startswith(f"|switch|{battle.player_role}{pos}: ") or line.startswith(
                f"|drag|{battle.player_role}{pos}: "
            ):
                [_, _, identifier, details, *_] = line.split("|")
                mon = battle.get_pokemon(identifier, details=details, request=battle.last_request)
                order = BattleOrder(mon)
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

    async def follow_log(self, tag: str, log: str) -> SingleAgentEpisode:
        self.states = []
        self.actions = []
        self.teampreview_draft = []
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
        episode = SingleAgentEpisode()
        episode.add_env_reset(self.states[0])
        for state, action in zip(self.states[1:], self.actions[:-1]):
            episode.add_env_step(state, action, 0)
        split_messages = [m.split("|") for m in messages[-1].split("\n")]
        await self._handle_battle_message(split_messages)
        last_state = Agent.embed_battle(self.battles[tag], self.teampreview_draft)
        reward = 1 if f"|win|{self.username}" in log else -1
        episode.add_env_step(last_state, self.actions[-1], reward)
        return episode


def process_logs(
    log_jsons: dict[str, tuple[str, str]], strict: bool = False
) -> list[SingleAgentEpisode]:
    episodes = []
    total = 0
    num_errors = 0
    for i, (tag, (_, log)) in enumerate(log_jsons.items()):
        print(f"Progress: {i}/{len(log_jsons)}", end="\r")
        try:
            start_index1 = log.index(f"|player|p1|")
            _, _, _, username1, _, rating1 = log[
                start_index1 : log.index("\n", start_index1)
            ].split("|")
            if rating1 and int(rating1) >= MIN_RATING:
                player1 = LogReader(
                    account_configuration=AccountConfiguration(username1, None),
                    battle_format=tag.split("-")[0],
                    log_level=51,
                    accept_open_team_sheet=True,
                )
                episode = asyncio.run(player1.follow_log(tag, log))
                total += len(episode.observations)
                episodes += [episode]
            start_index2 = log.index(f"|player|p2|")
            _, _, _, username2, _, rating2 = log[
                start_index2 : log.index("\n", start_index2)
            ].split("|")
            if rating2 and int(rating2) >= MIN_RATING:
                player2 = LogReader(
                    account_configuration=AccountConfiguration(username2, None),
                    battle_format=tag.split("-")[0],
                    log_level=51,
                    accept_open_team_sheet=True,
                )
                episode = asyncio.run(player2.follow_log(tag, log))
                total += len(episode.observations)
                episodes += [episode]
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
        f"prepared {len(episodes)} trajectories "
        f"with {total} total state-action pairs "
        f"(and {num_errors} games thrown away)"
    )
    return episodes


if __name__ == "__main__":
    logs = {}
    for f in battle_formats:
        with open(f"data/logs-{f}.json", "r") as file:
            logs = {**logs, **json.load(file)}
    episodes = process_logs(logs, strict=False)
    os.makedirs("data/episodes", exist_ok=True)
    width = len(str(len(episodes)))
    for i, ep in enumerate(episodes):
        states = ep.get_observations()
        actions = ep.get_actions()
        rewards = ep.get_rewards()
        rows = []
        for j in range(len(actions)):
            rows.append(
                {
                    Columns.OBS: states[j],
                    Columns.ACTIONS: actions[j],
                    Columns.REWARDS: rewards[j],
                    Columns.TERMINATEDS: int(j == len(actions) - 1),
                    Columns.NEXT_OBS: states[j + 1],
                }
            )
        df = pd.DataFrame(rows)
        df.to_parquet(f"data/episodes/{i:0{width}d}.parquet", index=False)
