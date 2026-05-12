"""
Gymnasium environment module for VGC-Bench.

Provides a custom Gymnasium environment wrapping poke-env's DoublesEnv for
training reinforcement learning agents on Pokemon VGC battles.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import numpy.typing as npt
import supersuit as ss
from gymnasium import Env
from gymnasium.spaces import Box
from poke_env.battle import AbstractBattle
from poke_env.environment import DoublesEnv, SingleAgentWrapper
from poke_env.ps_client import ServerConfiguration
from stable_baselines3.common.monitor import Monitor

from vgc_bench.src.policy_player import PolicyPlayer
from vgc_bench.src.teams import RandomTeamBuilder, TeamToggle, get_available_regs
from vgc_bench.src.utils import LearningStyle, chunk_obs_len, format_map, moves


class ShowdownEnv(DoublesEnv):
    """
    Gymnasium environment for Pokemon VGC doubles battles.

    Extends poke-env's DoublesEnv with custom observation embedding,
    reward calculation, and support for various training paradigms.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        """
        Initialize the ShowdownEnv.
        """
        super().__init__(*args, **kwargs)
        self.observation_spaces = {
            agent: Box(-1, len(moves), shape=(12 * chunk_obs_len,), dtype=np.float32)
            for agent in self.possible_agents
        }

    @classmethod
    def create_env(
        cls,
        reg: str | None,
        run_id: int,
        num_teams: int | None,
        num_envs: int,
        log_level: int,
        port: int,
        learning_style: LearningStyle,
        allow_mirror_match: bool,
        choose_on_teampreview: bool,
        team_paths: list[Path] | None = None,
    ) -> Env:
        """
        Factory method to create a properly wrapped training environment.

        Creates the base ShowdownEnv and applies appropriate wrappers based
        on the learning style (vectorization for self-play, single-agent
        wrapper for other paradigms).

        Args:
            reg: VGC regulation letter (e.g. 'g', 'h', 'i'), or None for all.
            run_id: Training run identifier.
            num_teams: Number of teams to train with, or None for all.
            num_envs: Number of parallel environments.
            log_level: Logging verbosity for Showdown clients.
            port: Port for the Pokemon Showdown server.
            learning_style: Training paradigm to use.
            allow_mirror_match: Whether to allow same-team matchups.
            choose_on_teampreview: Whether policy controls teampreview.
            team_paths: Optional list of team file paths for matchup solving.

        Returns:
            Wrapped Gymnasium environment ready for training.
        """
        toggle = None if allow_mirror_match else TeamToggle()
        if reg is None:
            battle_format = format_map[get_available_regs()[0]]
        else:
            battle_format = format_map[reg]
        env = cls(
            server_configuration=ServerConfiguration(
                f"ws://localhost:{port}/showdown/websocket",
                "https://play.pokemonshowdown.com/action.php?",
            ),
            battle_format=battle_format,
            log_level=log_level,
            accept_open_team_sheet=True,
            open_timeout=None,
            team=RandomTeamBuilder(run_id, num_teams, reg, team_paths, toggle),
            choose_on_teampreview=choose_on_teampreview,
        )
        if learning_style == LearningStyle.PURE_SELF_PLAY:
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
            env = Monitor(env)
            return env

    def reset(
        self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        """Reset the environment, updating battle format if multi-reg."""
        assert isinstance(self._team, RandomTeamBuilder)
        if self._team.available_regs is not None:
            assert self._team.current_reg is not None
            self._team.pick_reg()
            fmt = format_map[self._team.current_reg]
            self.agent1._format = fmt
            self.agent2._format = fmt
        return super().reset(seed=seed, options=options)

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
        return PolicyPlayer.embed_battle(battle, fake_rating=2000)
