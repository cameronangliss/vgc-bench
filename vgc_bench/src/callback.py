import asyncio
import json
import os
import random
import warnings

import numpy as np
import numpy.typing as npt
import torch
from open_spiel.python.egt import alpharank
from poke_env.player import Player, SimpleHeuristicsPlayer
from poke_env.ps_client import ServerConfiguration
from src.agent import Agent
from src.policy import MaskedActorCriticPolicy
from src.teams import RandomTeamBuilder, TeamToggle
from src.utils import LearningStyle, allow_mirror_match, battle_format, steps
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback

warnings.filterwarnings("ignore", category=UserWarning)


class Callback(BaseCallback):
    def __init__(
        self,
        teams: list[int],
        port: int,
        device: str,
        learning_style: LearningStyle,
        behavior_clone: bool,
        num_frames: int,
    ):
        super().__init__()
        self.learning_style = learning_style
        self.behavior_clone = behavior_clone
        self.teams = teams
        self.run_ident = "".join(
            [
                "-bc" if behavior_clone else "",
                f"-fs{num_frames}" if num_frames > 1 else "",
                "-" + learning_style.abbrev,
                "-xm" if not allow_mirror_match else "",
            ]
        )[1:]
        if not os.path.exists(f"results/logs-{self.run_ident}"):
            os.mkdir(f"results/logs-{self.run_ident}")
        self.payoff_matrix: npt.NDArray[np.float32]
        self.prob_dist: list[float] | None = None
        if self.learning_style == LearningStyle.LAST_SELF:
            policy_files = os.listdir(
                f"results/saves-{self.run_ident}/{','.join([str(t) for t in self.teams])}-teams"
            )
            self.prob_dist = [0.0] * len(policy_files)
            self.prob_dist[-1] = 1
        elif self.learning_style == LearningStyle.DOUBLE_ORACLE:
            if os.path.exists(
                f"results/logs-{self.run_ident}/{','.join([str(t) for t in self.teams])}-teams-payoff-matrix.json"
            ):
                with open(
                    f"results/logs-{self.run_ident}/{','.join([str(t) for t in self.teams])}-teams-payoff-matrix.json"
                ) as f:
                    self.payoff_matrix = np.array(json.load(f))
            else:
                self.payoff_matrix = np.array([[0.5]])
            self.prob_dist = alpharank.compute(  # type: ignore
                [self.payoff_matrix], use_inf_alpha=True, inf_alpha_eps=0.1
            )[2]
        toggle = None if allow_mirror_match else TeamToggle(len(teams))
        self.eval_agent = Agent(
            num_frames,
            torch.device(device),
            server_configuration=ServerConfiguration(
                f"ws://localhost:{port}/showdown/websocket",
                "https://play.pokemonshowdown.com/action.php?",
            ),
            battle_format=battle_format,
            log_level=25,
            max_concurrent_battles=10,
            accept_open_team_sheet=True,
            open_timeout=None,
            team=RandomTeamBuilder(
                [0] if learning_style == LearningStyle.EXPLOITER else teams, battle_format, toggle
            ),
        )
        self.eval_agent2 = Agent(
            num_frames,
            torch.device(device),
            server_configuration=ServerConfiguration(
                f"ws://localhost:{port}/showdown/websocket",
                "https://play.pokemonshowdown.com/action.php?",
            ),
            battle_format=battle_format,
            log_level=25,
            max_concurrent_battles=10,
            accept_open_team_sheet=True,
            open_timeout=None,
            team=RandomTeamBuilder(
                [0] if learning_style == LearningStyle.EXPLOITER else teams, battle_format, toggle
            ),
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
            team=RandomTeamBuilder(
                [0] if learning_style == LearningStyle.EXPLOITER else teams, battle_format, toggle
            ),
        )

    def _on_step(self) -> bool:
        return True

    def _on_training_start(self):
        assert self.model.env is not None
        if self.model.num_timesteps < steps:
            self.evaluate()
        if not self.behavior_clone:
            self.model.save(
                f"results/saves-{self.run_ident}/{','.join([str(t) for t in self.teams])}-teams/{self.model.num_timesteps}"
            )
        else:
            try:
                saves = [
                    int(file[:-4])
                    for file in os.listdir(
                        f"results/saves-{self.run_ident}/{','.join([str(t) for t in self.teams])}-teams"
                    )
                    if int(file[:-4]) >= 0
                ]
            except FileNotFoundError:
                raise FileNotFoundError("behavior_clone on, but no model initialization found")
            assert len(saves) > 0
        if self.learning_style == LearningStyle.EXPLOITER:
            policy = PPO.load(
                f"results/saves-{self.run_ident}/{','.join([str(t) for t in self.teams])}-teams/-1",
                device=self.model.device,
            ).policy
            for i in range(self.model.env.num_envs):
                self.model.env.env_method("set_opp_policy", policy, indices=i)

    def _on_rollout_start(self):
        assert self.model.env is not None
        self.model.logger.dump(self.model.num_timesteps)
        if self.behavior_clone:
            self.model.policy.actor_grad = self.model.num_timesteps >= steps  # type: ignore
        if self.learning_style in [
            LearningStyle.LAST_SELF,
            LearningStyle.FICTITIOUS_PLAY,
            LearningStyle.DOUBLE_ORACLE,
        ]:
            policy_files = os.listdir(
                f"results/saves-{self.run_ident}/{','.join([str(t) for t in self.teams])}-teams"
            )
            policies = random.choices(
                policy_files, weights=self.prob_dist, k=self.model.env.num_envs
            )
            for i in range(self.model.env.num_envs):
                self.model.env.env_method("cleanup", indices=i)
                policy = PPO.load(
                    f"results/saves-{self.run_ident}/{','.join([str(t) for t in self.teams])}-teams/{policies[i]}",
                    device=self.model.device,
                ).policy
                self.model.env.env_method("set_opp_policy", policy, indices=i)

    def _on_training_end(self):
        self.evaluate()
        self.model.logger.dump(self.model.num_timesteps)
        if self.learning_style == LearningStyle.DOUBLE_ORACLE:
            self.update_payoff_matrix()
        self.model.save(
            f"results/saves-{self.run_ident}/{','.join([str(t) for t in self.teams])}-teams/{self.model.num_timesteps}"
        )

    def evaluate(self):
        policy = MaskedActorCriticPolicy.clone(self.model)
        self.eval_agent.set_policy(policy)
        win_rate = self.compare(self.eval_agent, self.eval_opponent, 100)
        self.model.logger.record("train/eval", win_rate)

    def update_payoff_matrix(self):
        policy = MaskedActorCriticPolicy.clone(self.model)
        self.eval_agent.set_policy(policy)
        policy_files = os.listdir(
            f"results/saves-{self.run_ident}/{','.join([str(t) for t in self.teams])}-teams"
        )
        win_rates = np.array([])
        for p in policy_files:
            policy2 = PPO.load(
                f"results/saves-{self.run_ident}/{','.join([str(t) for t in self.teams])}-teams/{p}",
                device=self.model.device,
            ).policy
            self.eval_agent2.set_policy(policy2)
            win_rate = self.compare(self.eval_agent, self.eval_agent2, 100)
            win_rates = np.append(win_rates, win_rate)
        self.payoff_matrix = np.concat([self.payoff_matrix, 1 - win_rates.reshape(-1, 1)], axis=1)
        win_rates = np.append(win_rates, 0.5)
        self.payoff_matrix = np.concat([self.payoff_matrix, win_rates.reshape(1, -1)], axis=0)
        with open(
            f"results/logs-{self.run_ident}/{','.join([str(t) for t in self.teams])}-teams-payoff-matrix.json",
            "w",
        ) as f:
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
