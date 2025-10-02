import random
from typing import Any

import numpy as np
import numpy.typing as npt
from gymnasium.spaces import Box, Discrete
from pettingzoo import ParallelEnv
from poke_env.battle import AbstractBattle
from poke_env.environment import DoublesEnv
from poke_env.ps_client import ServerConfiguration
from ray.rllib.env import ParallelPettingZooEnv
from src.policy_player import PolicyPlayer
from src.teams import TEAMS, RandomTeamBuilder, TeamToggle
from src.utils import LearningStyle, act_len, battle_format, chunk_obs_len, moves


class ShowdownEnv(DoublesEnv[npt.NDArray[np.float32]]):
    _teampreview_draft1: list[int]
    _teampreview_draft2: list[int]
    _learning_style: LearningStyle

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.metadata = {"name": "showdown_v1", "render_modes": ["human"]}
        self.render_mode: str | None = None
        self.observation_spaces = {
            agent: Box(
                -1, len(moves), shape=(2 * act_len + 12 * chunk_obs_len + 1,), dtype=np.float32
            )
            for agent in self.possible_agents
        }
        self._teampreview_draft1 = []
        self._teampreview_draft2 = []

    async def async_random_teampreview1(self, battle: AbstractBattle) -> str:
        message = self.agent1.random_teampreview(battle)
        self._teampreview_draft1 = [int(i) for i in message[6:-2]]
        return message

    async def async_random_teampreview2(self, battle: AbstractBattle) -> str:
        message = self.agent2.random_teampreview(battle)
        self._teampreview_draft2 = [int(i) for i in message[6:-2]]
        return message

    def step(
        self, actions: dict[str, npt.NDArray[np.int64]]
    ) -> tuple[
        dict[str, npt.NDArray[np.float32]],
        dict[str, float],
        dict[str, bool],
        dict[str, bool],
        dict[str, dict[str, Any]],
    ]:
        if len(self._teampreview_draft1) < 4:
            self._teampreview_draft1 += actions[self.agents[0]].tolist()
        if len(self._teampreview_draft2) < 4:
            self._teampreview_draft2 += actions[self.agents[1]].tolist()
        return super().step(actions)

    def reset(
        self, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[dict[str, npt.NDArray[np.float32]], dict[str, dict[str, Any]]]:
        self._teampreview_draft1 = []
        self._teampreview_draft2 = []
        return super().reset(seed=seed, options=options)

    def close(self, force: bool = True, wait: bool = False):
        super().close(force=force, wait=wait)

    def calc_reward(self, battle: AbstractBattle) -> float:
        if not battle.finished:
            return 0
        elif battle.won:
            return 1
        elif battle.lost:
            return -1
        else:
            return 0

    def embed_battle(self, battle: AbstractBattle) -> npt.NDArray[np.float32]:
        teampreview_draft = (
            self._teampreview_draft1 if battle.player_role == "p1" else self._teampreview_draft2
        )
        return PolicyPlayer.embed_battle(battle, teampreview_draft, fake_rating=True)


class TwoStepShowdownEnv(ParallelEnv):
    def __init__(self, env: ShowdownEnv):
        self.env = env
        self.action1 = None
        self.action_spaces = {agent: Discrete(act_len) for agent in env.possible_agents}

    @classmethod
    def create_env(cls, config: dict[str, Any]) -> ParallelPettingZooEnv:
        teams = list(range(len(TEAMS[battle_format[-4:]])))
        random.Random(config["run_id"]).shuffle(teams)
        toggle = None if config["allow_mirror_match"] else TeamToggle(config["num_teams"])
        env = cls(
            ShowdownEnv(
                server_configuration=ServerConfiguration(
                    f"ws://localhost:{config['port']}/showdown/websocket",
                    "https://play.pokemonshowdown.com/action.php?",
                ),
                battle_format=battle_format,
                log_level=25,
                accept_open_team_sheet=True,
                open_timeout=None,
                team=RandomTeamBuilder(teams[: config["num_teams"]], battle_format, toggle),
            )
        )
        if not config["chooses_on_teampreview"]:
            env.agent1.teampreview = env.async_random_teampreview1
            env.agent2.teampreview = env.async_random_teampreview2
        return ParallelPettingZooEnv(env)

    def __getattr__(self, name):
        if name in ["env", "action_spaces"]:
            raise AttributeError
        else:
            return getattr(self.env, name)

    def reset(
        self, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[dict[str, npt.NDArray[np.float32]], dict[str, dict[str, Any]]]:
        obs, info = self.env.reset(seed, options)
        obs = {
            self.env.agents[0]: np.append(obs[self.env.agents[0]], -1),
            self.env.agents[1]: np.append(obs[self.env.agents[1]], -1),
        }
        return obs, info

    def step(
        self, actions: dict[str, np.int64]
    ) -> tuple[
        dict[str, npt.NDArray[np.float32]],
        dict[str, float],
        dict[str, bool],
        dict[str, bool],
        dict[str, dict[str, Any]],
    ]:
        if self.action1 is None:
            assert self.env.agent1.battle is not None
            assert self.env.agent2.battle is not None
            obs = {
                self.env.agents[0]: np.append(
                    self.env.embed_battle(self.env.agent1.battle), np.float32(actions[self.env.agents[0]])
                ),
                self.env.agents[1]: np.append(
                    self.env.embed_battle(self.env.agent2.battle), np.float32(actions[self.env.agents[1]])
                ),
            }
            rewards = {agent: 0.0 for agent in self.env.agents}
            terms = {agent: False for agent in self.env.agents}
            truncs = {agent: False for agent in self.env.agents}
            infos = {agent: {} for agent in self.env.agents}
            self.action1 = actions
            return obs, rewards, terms, truncs, infos
        else:
            two_actions = {
                agent: np.array([self.action1[agent], actions[agent]]) for agent in actions
            }
            self.action1 = None
            obs, reward, term, trunc, info = self.env.step(two_actions)
            obs = {
                self.env.agents[0]: np.append(obs[self.env.agents[0]], -1),
                self.env.agents[1]: np.append(obs[self.env.agents[1]], -1),
            }
            return obs, reward, term, trunc, info

    def close(self):
        self.env.close()

    @property
    def unwrapped(self):
        return self.env
