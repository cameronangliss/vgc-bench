import asyncio
import json
import os
import random
import warnings

import numpy as np
import numpy.typing as npt
from nashpy import Game
from poke_env.player import Player, SimpleHeuristicsPlayer
from poke_env.ps_client import ServerConfiguration
from src.policy import MaskedActorCriticPolicy
from src.policy_player import BatchPolicyPlayer
from src.teams import RandomTeamBuilder, TeamToggle
from src.utils import LearningStyle
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback

warnings.filterwarnings("ignore", category=UserWarning)


class Callback(BaseCallback):
    def __init__(
        self,
        run_id: int,
        num_teams: int,
        battle_format: str,
        port: int,
        learning_style: LearningStyle,
        behavior_clone: bool,
        num_frames: int,
        allow_mirror_match: bool,
        chooses_on_teampreview: bool,
        save_interval: int,
    ):
        super().__init__()
        self.num_teams = num_teams
        self.learning_style = learning_style
        self.behavior_clone = behavior_clone
        self.save_interval = save_interval
        self.run_ident = "".join(
            [
                "-bc" if behavior_clone else "",
                "-" + learning_style.abbrev,
                f"-fs{num_frames}" if num_frames > 1 else "",
                "-xm" if not allow_mirror_match else "",
                "-xt" if not chooses_on_teampreview else "",
            ]
        )[1:]
        self.log_dir = f"results{run_id}/logs-{self.run_ident}"
        self.save_dir = f"results{run_id}/saves-{self.run_ident}/{self.num_teams}-teams"
        if not os.path.exists(self.log_dir):
            os.mkdir(self.log_dir)
        self.payoff_matrix: npt.NDArray[np.float32]
        self.prob_dist = None
        if self.learning_style == LearningStyle.DOUBLE_ORACLE:
            if os.path.exists(f"{self.log_dir}/{self.num_teams}-teams-payoff-matrix.json"):
                with open(f"{self.log_dir}/{self.num_teams}-teams-payoff-matrix.json") as f:
                    self.payoff_matrix = np.array(json.load(f))
            else:
                self.payoff_matrix = np.array([[0.5]])
            self.prob_dist = Game(self.payoff_matrix).linear_program()[0].tolist()
        if learning_style == LearningStyle.EXPLOITER:
            num_teams = 1
        toggle = None if allow_mirror_match else TeamToggle(num_teams)
        self.eval_agent = BatchPolicyPlayer(
            server_configuration=ServerConfiguration(
                f"ws://localhost:{port}/showdown/websocket",
                "https://play.pokemonshowdown.com/action.php?",
            ),
            battle_format=battle_format,
            log_level=25,
            max_concurrent_battles=10,
            accept_open_team_sheet=True,
            open_timeout=None,
            team=RandomTeamBuilder(run_id, num_teams, battle_format, toggle),
        )
        self.eval_agent2 = BatchPolicyPlayer(
            server_configuration=ServerConfiguration(
                f"ws://localhost:{port}/showdown/websocket",
                "https://play.pokemonshowdown.com/action.php?",
            ),
            battle_format=battle_format,
            log_level=25,
            max_concurrent_battles=10,
            accept_open_team_sheet=True,
            open_timeout=None,
            team=RandomTeamBuilder(run_id, num_teams, battle_format, toggle),
        )
        self.eval_opponent = SimpleHeuristicsPlayer(
            server_configuration=ServerConfiguration(
                f"ws://localhost:{port}/showdown/websocket",
                "https://play.pokemonshowdown.com/action.php?",
            ),
            battle_format=battle_format,
            log_level=25,
            max_concurrent_battles=10,
            accept_open_team_sheet=True,
            open_timeout=None,
            team=RandomTeamBuilder(run_id, num_teams, battle_format, toggle),
        )

    def _on_step(self) -> bool:
        return True

    def _on_training_start(self):
        assert self.model.env is not None
        self.eval_agent.policy = self.model.policy
        if self.model.num_timesteps < self.save_interval:
            win_rate = self.compare(self.eval_agent, self.eval_opponent, 1000)
            self.model.logger.record("train/eval", win_rate)
        if not self.behavior_clone:
            self.model.save(f"{self.save_dir}/{self.model.num_timesteps}")
        else:
            try:
                saves = [int(f[:-4]) for f in os.listdir(self.save_dir) if int(f[:-4]) >= 0]
            except FileNotFoundError:
                raise FileNotFoundError("behavior_clone on, but no model initialization found")
            assert len(saves) > 0
        if self.learning_style == LearningStyle.EXPLOITER:
            policy = PPO.load(f"{self.save_dir}/-1", device=self.model.device).policy
            for i in range(self.model.env.num_envs):
                self.model.env.env_method("set_opp_policy", policy, indices=i)

    def _on_rollout_start(self):
        assert self.model.env is not None
        self.model.logger.dump(self.model.num_timesteps)
        if self.behavior_clone:
            assert isinstance(self.model.policy, MaskedActorCriticPolicy)
            self.model.policy.actor_grad = self.model.num_timesteps >= self.save_interval
        if self.learning_style in [LearningStyle.FICTITIOUS_PLAY, LearningStyle.DOUBLE_ORACLE]:
            policy_files = os.listdir(self.save_dir)
            policies = random.choices(
                policy_files, weights=self.prob_dist, k=self.model.env.num_envs
            )
            for i in range(self.model.env.num_envs):
                policy = PPO.load(f"{self.save_dir}/{policies[i]}", device=self.model.device).policy
                self.model.env.env_method("set_opp_policy", policy, indices=i)

    def _on_rollout_end(self):
        if self.model.num_timesteps % self.save_interval == 0:
            win_rate = self.compare(self.eval_agent, self.eval_opponent, 1000)
            self.model.logger.record("train/eval", win_rate)
            if self.learning_style == LearningStyle.DOUBLE_ORACLE:
                self.update_payoff_matrix()
            self.model.save(f"{self.save_dir}/{self.model.num_timesteps}")

    def _on_training_end(self):
        self.model.logger.dump(self.model.num_timesteps)

    def update_payoff_matrix(self):
        policy_files = os.listdir(self.save_dir)
        win_rates = np.array([])
        for p in policy_files:
            self.eval_agent2.policy = PPO.load(
                f"{self.save_dir}/{p}", device=self.model.device
            ).policy
            win_rate = self.compare(self.eval_agent, self.eval_agent2, 1000)
            win_rates = np.append(win_rates, win_rate)
        self.payoff_matrix = np.concat([self.payoff_matrix, 1 - win_rates.reshape(-1, 1)], axis=1)
        win_rates = np.append(win_rates, 0.5)
        self.payoff_matrix = np.concat([self.payoff_matrix, win_rates.reshape(1, -1)], axis=0)
        self.prob_dist = Game(self.payoff_matrix).linear_program()[0].tolist()
        with open(f"{self.log_dir}/{self.num_teams}-teams-payoff-matrix.json", "w") as f:
            json.dump(
                [
                    [round(win_rate, 2) for win_rate in win_rates]
                    for win_rates in self.payoff_matrix.tolist()
                ],
                f,
            )

    @staticmethod
    def compare(player1: Player, player2: Player, n_battles: int) -> float:
        asyncio.run(player1.battle_against(player2, n_battles=n_battles))
        win_rate = player1.win_rate
        player1.reset_battles()
        player2.reset_battles()
        return win_rate
