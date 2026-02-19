"""
Gymnasium environment module for VGC-Bench.

Provides a custom Gymnasium environment wrapping poke-env's DoublesEnv for
training reinforcement learning agents on Pokemon VGC battles.
"""

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
from stable_baselines3.common.monitor import Monitor

from vgc_bench.src.policy_player import PolicyPlayer
from vgc_bench.src.teams import RandomTeamBuilder, TeamToggle
from vgc_bench.src.utils import LearningStyle, act_len, chunk_obs_len, moves


class ShowdownEnv(DoublesEnv[npt.NDArray[np.float32]]):
    """
    Gymnasium environment for Pokemon VGC doubles battles.

    Extends poke-env's DoublesEnv with custom observation embedding,
    reward calculation, and support for various training paradigms.

    Attributes:
        _learning_style: Training paradigm being used.
        _chooses_on_teampreview: Whether the policy controls teampreview.
        _teampreview_draft1: Player 1's teampreview selections.
        _teampreview_draft2: Player 2's teampreview selections.
    """

    _learning_style: LearningStyle
    _chooses_on_teampreview: bool
    _teampreview_draft1: list[int] = []
    _teampreview_draft2: list[int] = []

    def __init__(
        self,
        learning_style: LearningStyle,
        chooses_on_teampreview: bool,
        *args: Any,
        **kwargs: Any,
    ):
        """
        Initialize the ShowdownEnv.

        Args:
            learning_style: Training paradigm to use.
            chooses_on_teampreview: Whether policy controls teampreview decisions.
            *args: Additional arguments for DoublesEnv.
            **kwargs: Additional keyword arguments for DoublesEnv.
        """
        super().__init__(*args, **kwargs)
        self.metadata = {"name": "showdown_v1", "render_modes": ["human"]}
        self.render_mode: str | None = None
        self.observation_spaces = {
            agent: Box(
                -1,
                len(moves),
                shape=(2 * act_len + 12 * chunk_obs_len,),
                dtype=np.float32,
            )
            for agent in self.possible_agents
        }
        self._learning_style = learning_style
        self._chooses_on_teampreview = chooses_on_teampreview

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Restore environment state from pickle, including teampreview handlers."""
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
        log_level: int,
        port: int,
        learning_style: LearningStyle,
        num_frames: int,
        allow_mirror_match: bool,
        chooses_on_teampreview: bool,
        team1: str | None,
        team2: str | None,
    ) -> Env:
        """
        Factory method to create a properly wrapped training environment.

        Creates the base ShowdownEnv and applies appropriate wrappers based
        on the learning style (vectorization for self-play, single-agent
        wrapper for other paradigms).

        Args:
            battle_format: Pokemon Showdown battle format string.
            run_id: Training run identifier.
            num_teams: Number of teams to train with.
            num_envs: Number of parallel environments.
            log_level: Logging verbosity for Showdown clients.
            port: Port for the Pokemon Showdown server.
            learning_style: Training paradigm to use.
            num_frames: Number of frames for frame stacking.
            allow_mirror_match: Whether to allow same-team matchups.
            chooses_on_teampreview: Whether policy controls teampreview.
            team1: Optional team string for matchup solving (requires team2).
            team2: Optional team string for matchup solving (requires team1).

        Returns:
            Wrapped Gymnasium environment ready for training.
        """
        toggle = None if allow_mirror_match else TeamToggle(num_teams)
        env = cls(
            learning_style,
            chooses_on_teampreview,
            server_configuration=ServerConfiguration(
                f"ws://localhost:{port}/showdown/websocket",
                "https://play.pokemonshowdown.com/action.php?",
            ),
            battle_format=battle_format,
            log_level=log_level,
            accept_open_team_sheet=True,
            open_timeout=None,
            team=RandomTeamBuilder(
                run_id, num_teams, battle_format, team1, team2, toggle
            ),
        )
        if not chooses_on_teampreview:
            env.agent1.teampreview = env.async_random_teampreview1
            env.agent2.teampreview = env.async_random_teampreview2
        if learning_style == LearningStyle.PURE_SELF_PLAY:
            if num_frames > 1:
                env = ss.frame_stack_v1(env, stack_size=num_frames, stack_dim=0)
            env = ss.pettingzoo_env_to_vec_env_v1(env)
            env = ss.concat_vec_envs_v1(
                env,
                num_vec_envs=num_envs,
                num_cpus=num_envs,
                base_class="stable_baselines3",
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
        """Generate random teampreview for player 1 and record the selection."""
        message = self.agent1.random_teampreview(battle)
        self._teampreview_draft1 = [int(i) for i in message[6:-2]]
        return message

    async def async_random_teampreview2(self, battle: AbstractBattle) -> str:
        """Generate random teampreview for player 2 and record the selection."""
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
        """Execute actions and return new observations, rewards, and done flags."""
        if len(self._teampreview_draft1) < 4:
            self._teampreview_draft1 += actions[self.agents[0]].tolist()
        if len(self._teampreview_draft2) < 4:
            self._teampreview_draft2 += actions[self.agents[1]].tolist()
        return super().step(actions)

    def reset(
        self, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[dict[str, npt.NDArray[np.float32]], dict[str, dict[str, Any]]]:
        """Reset the environment for a new episode, clearing teampreview state."""
        self._teampreview_draft1 = []
        self._teampreview_draft2 = []
        return super().reset(seed=seed, options=options)

    def close(self, force: bool = True, wait: bool = False):
        """Close the environment and clean up resources."""
        super().close(force=force, wait=wait)

    def calc_reward(self, battle: AbstractBattle) -> float:
        """
        Calculate reward for the current battle state.

        Returns:
            1 if won, -1 if lost, 0 otherwise.
        """
        if not battle.finished:
            return 0
        elif battle.won:
            return 1
        elif battle.lost:
            return -1
        else:
            return 0

    def embed_battle(self, battle: AbstractBattle) -> npt.NDArray[np.float32]:
        """
        Convert the battle state to a feature vector observation.

        Args:
            battle: Current battle state.

        Returns:
            Numpy array observation for the policy network.
        """
        teampreview_draft = (
            self._teampreview_draft1
            if battle.player_role == "p1"
            else self._teampreview_draft2
        )
        return PolicyPlayer.embed_battle(battle, teampreview_draft, fake_rating=True)
