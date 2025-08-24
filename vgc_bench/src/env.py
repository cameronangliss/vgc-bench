import random
from typing import Any

import numpy as np
import numpy.typing as npt
import supersuit as ss
import torch
from gymnasium import Env
from gymnasium.spaces import Box
from gymnasium.wrappers import FrameStackObservation
from poke_env.battle import AbstractBattle
from poke_env.environment import DoublesEnv, SingleAgentWrapper
from poke_env.ps_client import ServerConfiguration
from src.agent import Agent
from src.teams import TEAMS, RandomTeamBuilder, TeamToggle
from src.utils import (
    LearningStyle,
    act_len,
    allow_mirror_match,
    battle_format,
    chooses_on_teampreview,
    chunk_obs_len,
    moves,
    num_envs,
)
from stable_baselines3.common.monitor import Monitor


class ShowdownEnv(DoublesEnv[npt.NDArray[np.float32]]):
    _teampreview_draft1: list[int]
    _teampreview_draft2: list[int]
    _learning_style: LearningStyle

    def __init__(self, learning_style: LearningStyle, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.metadata = {"name": "showdown_v1", "render_modes": ["human"]}
        self.render_mode: str | None = None
        self.observation_spaces = {
            agent: Box(-1, len(moves), shape=(2 * act_len + 12 * chunk_obs_len,), dtype=np.float32)
            for agent in self.possible_agents
        }
        self._teampreview_draft1 = []
        self._teampreview_draft2 = []
        self._learning_style = learning_style

    @classmethod
    def create_env(
        cls,
        run_id: int,
        num_teams: int,
        port: int,
        device: str,
        learning_style: LearningStyle,
        num_frames: int,
    ) -> Env:
        teams = list(range(len(TEAMS[battle_format[-4:]])))
        random.Random(run_id).shuffle(teams)
        toggle = None if allow_mirror_match else TeamToggle(num_teams)
        env = cls(
            learning_style,
            server_configuration=ServerConfiguration(
                f"ws://localhost:{port}/showdown/websocket",
                "https://play.pokemonshowdown.com/action.php?",
            ),
            battle_format=battle_format,
            log_level=25,
            accept_open_team_sheet=True,
            open_timeout=None,
            team=RandomTeamBuilder(teams[:num_teams], battle_format, toggle),
        )
        if not chooses_on_teampreview:
            env.agent1.teampreview = env.async_random_teampreview1
            env.agent2.teampreview = env.async_random_teampreview2
        if learning_style == LearningStyle.PURE_SELF_PLAY:
            if num_frames > 1:
                env = ss.frame_stack_v2(env, stack_size=num_frames, stack_dim=0)
            env = ss.pettingzoo_env_to_vec_env_v1(env)
            env = ss.concat_vec_envs_v1(
                env, num_vec_envs=num_envs, num_cpus=num_envs, base_class="stable_baselines3"
            )
            return env  # type: ignore
        else:
            opponent = Agent(num_frames, torch.device(device), start_listening=False)
            env = SingleAgentWrapper(env, opponent)
            if num_frames > 1:
                env = FrameStackObservation(env, num_frames, padding_type="zeros")
            env = Monitor(env)
            return env

    async def async_random_teampreview1(self, battle: AbstractBattle) -> str:
        message = self.agent1.random_teampreview(battle)
        self._teampreview_draft1 = [int(i) - 1 for i in message[6:-2]]
        return message

    async def async_random_teampreview2(self, battle: AbstractBattle) -> str:
        message = self.agent2.random_teampreview(battle)
        self._teampreview_draft2 = [int(i) - 1 for i in message[6:-2]]
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
            self._teampreview_draft1 += [a - 1 for a in actions[self.agents[0]]]
        if len(self._teampreview_draft2) < 4:
            self._teampreview_draft2 += [a - 1 for a in actions[self.agents[1]]]
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
        return Agent.embed_battle(battle, teampreview_draft, fake_rating=True)
