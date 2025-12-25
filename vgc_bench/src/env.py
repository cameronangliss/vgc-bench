from typing import Any

import numpy as np
import numpy.typing as npt
import supersuit as ss
from gymnasium import Env
from gymnasium.spaces import Box
from gymnasium.wrappers import FrameStackObservation
from poke_env.battle import AbstractBattle
from poke_env.environment import DoublesEnv, SingleAgentWrapper
from poke_env.ps_client import ServerConfiguration
from src.policy_player import PolicyPlayer
from src.teams import RandomTeamBuilder, TeamToggle
from src.utils import LearningStyle, act_len, chunk_obs_len, moves
from stable_baselines3.common.monitor import Monitor


class ShowdownEnv(DoublesEnv[npt.NDArray[np.float32]]):
    _learning_style: LearningStyle
    _chooses_on_teampreview: bool
    _teampreview_draft1: list[int] = []
    _teampreview_draft2: list[int] = []

    def __init__(
        self, learning_style: LearningStyle, chooses_on_teampreview: bool, *args: Any, **kwargs: Any
    ):
        super().__init__(*args, **kwargs)
        self.metadata = {"name": "showdown_v1", "render_modes": ["human"]}
        self.render_mode: str | None = None
        self.observation_spaces = {
            agent: Box(-1, len(moves), shape=(2 * act_len + 12 * chunk_obs_len,), dtype=np.float32)
            for agent in self.possible_agents
        }
        self._learning_style = learning_style
        self._chooses_on_teampreview = chooses_on_teampreview

    def __setstate__(self, state: dict[str, Any]) -> None:
        super().__setstate__(state)
        self._learning_style = state["_learning_style"]
        self._chooses_on_teampreview = state["_chooses_on_teampreview"]
        if not self._chooses_on_teampreview:
            self.agent1.teampreview = self.async_random_teampreview1
            self.agent2.teampreview = self.async_random_teampreview2

    @classmethod
    def create_env(
        cls,
        battle_format: str,
        run_id: int,
        num_teams: int,
        num_envs: int,
        port: int,
        learning_style: LearningStyle,
        num_frames: int,
        allow_mirror_match: bool,
        chooses_on_teampreview: bool,
    ) -> Env:
        toggle = None if allow_mirror_match else TeamToggle(num_teams)
        env = cls(
            learning_style,
            chooses_on_teampreview,
            server_configuration=ServerConfiguration(
                f"ws://localhost:{port}/showdown/websocket",
                "https://play.pokemonshowdown.com/action.php?",
            ),
            battle_format=battle_format,
            log_level=25,
            accept_open_team_sheet=True,
            open_timeout=None,
            team=RandomTeamBuilder(run_id, num_teams, battle_format, toggle),
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
            return env
        else:
            opponent = PolicyPlayer(start_listening=False)
            env = SingleAgentWrapper(env, opponent)
            if num_frames > 1:
                env = FrameStackObservation(env, num_frames, padding_type="zero")
            env = Monitor(env)
            return env

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

    def get_additional_info(self) -> dict[str, dict[str, Any]]:
        return {self.agents[0]: {"battle": self.battle1}, self.agents[1]: {"battle": self.battle2}}

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
