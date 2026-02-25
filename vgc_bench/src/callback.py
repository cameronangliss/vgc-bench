"""
Training callback module for VGC-Bench.

Provides a custom Stable-Baselines3 callback for periodic evaluation,
checkpointing, and opponent sampling during reinforcement learning training.
"""

import asyncio
import json
import random
import shutil
import warnings
from pathlib import Path

import numpy as np
import numpy.typing as npt
from huggingface_hub import hf_hub_download
from nashpy import Game
from poke_env.player import Player, SimpleHeuristicsPlayer
from poke_env.ps_client import ServerConfiguration
from stable_baselines3.common.callbacks import BaseCallback

from vgc_bench.src.policy import MaskedActorCriticPolicy
from vgc_bench.src.policy_player import BatchPolicyPlayer
from vgc_bench.src.teams import RandomTeamBuilder, TeamToggle
from vgc_bench.src.utils import LearningStyle

warnings.filterwarnings("ignore", category=UserWarning)

HF_BC_MODEL_REPO = "cameronangliss/vgc-bench-models"
HF_BC_MODEL_FILE = "results1/saves-bc/100.zip"
HF_BC_MODEL_TIMESTEP = 100


class Callback(BaseCallback):
    """
    Training callback for PPO-based Pokemon VGC training.

    Handles periodic evaluation against SimpleHeuristics, checkpoint saving,
    and opponent sampling for self-play variants. For double oracle training,
    maintains a payoff matrix and computes Nash equilibrium distributions.

    Attributes:
        num_teams: Number of teams used in training.
        learning_style: Training paradigm being used.
        behavior_clone: Whether training was initialized from BC.
        save_interval: Timesteps between checkpoint saves.
        eval_agent: Agent used for evaluation battles.
        payoff_matrix: Win rate matrix for double oracle (if applicable).
        prob_dist: Nash equilibrium opponent sampling distribution.
    """

    def __init__(
        self,
        run_id: int,
        num_teams: int,
        battle_format: str,
        num_eval_workers: int,
        log_level: int,
        port: int,
        learning_style: LearningStyle,
        behavior_clone: bool,
        num_frames: int,
        allow_mirror_match: bool,
        choose_on_teampreview: bool,
        save_interval: int,
        team1: str | None,
        team2: str | None,
        results_suffix: str,
    ):
        """
        Initialize the training callback.

        Args:
            run_id: Training run identifier.
            num_teams: Number of teams to use.
            battle_format: Pokemon Showdown battle format string.
            num_eval_workers: Number of parallel evaluation workers.
            log_level: Logging verbosity for Showdown clients.
            port: Port for the Pokemon Showdown server.
            learning_style: Training paradigm (self-play, fictitious play, etc.).
            behavior_clone: Whether initialized from behavior cloning.
            num_frames: Number of frames for frame stacking.
            allow_mirror_match: Whether to allow same-team matchups.
            choose_on_teampreview: Whether policy makes teampreview decisions.
            save_interval: Timesteps between checkpoint saves.
            team1: Optional team string for matchup solving (requires team2).
            team2: Optional team string for matchup solving (requires team1).
            results_suffix: Suffix appended to results<run_id> for output paths.
        """
        super().__init__()
        self.num_teams = num_teams
        self.learning_style = learning_style
        self.behavior_clone = behavior_clone
        self.save_interval = save_interval
        method = "".join(
            [
                "-bc" if behavior_clone else "",
                "-" + learning_style.abbrev,
                f"-fs{num_frames}" if num_frames > 1 else "",
                "-xm" if not allow_mirror_match else "",
                "-xt" if not choose_on_teampreview else "",
            ]
        )[1:]
        suffix = f"-{results_suffix}" if results_suffix else ""
        output_dir = Path(f"results{run_id}{suffix}")
        self.log_dir = output_dir / f"logs-{method}"
        self.save_dir = output_dir / f"saves-{method}" / f"{self.num_teams}-teams"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.payoff_matrix: npt.NDArray[np.float32]
        self.prob_dist = None
        if self.learning_style == LearningStyle.DOUBLE_ORACLE:
            payoff_path = self.log_dir / f"{self.num_teams}-teams-payoff-matrix.json"
            if payoff_path.exists():
                with payoff_path.open() as f:
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
            log_level=log_level,
            max_concurrent_battles=num_eval_workers,
            accept_open_team_sheet=True,
            open_timeout=None,
            team=RandomTeamBuilder(
                run_id, num_teams, battle_format, team1, team2, toggle
            ),
        )
        self.eval_agent2 = BatchPolicyPlayer(
            server_configuration=ServerConfiguration(
                f"ws://localhost:{port}/showdown/websocket",
                "https://play.pokemonshowdown.com/action.php?",
            ),
            battle_format=battle_format,
            log_level=log_level,
            max_concurrent_battles=num_eval_workers,
            accept_open_team_sheet=True,
            open_timeout=None,
            team=RandomTeamBuilder(
                run_id, num_teams, battle_format, team1, team2, toggle
            ),
        )
        self.eval_opponent = SimpleHeuristicsPlayer(
            server_configuration=ServerConfiguration(
                f"ws://localhost:{port}/showdown/websocket",
                "https://play.pokemonshowdown.com/action.php?",
            ),
            battle_format=battle_format,
            log_level=log_level,
            max_concurrent_battles=num_eval_workers,
            accept_open_team_sheet=True,
            open_timeout=None,
            team=RandomTeamBuilder(
                run_id, num_teams, battle_format, team1, team2, toggle
            ),
        )

    def _on_step(self) -> bool:
        """Called after each environment step. Returns True to continue training."""
        return True

    def _on_training_start(self):
        """Initialize evaluation agent and perform initial checkpoint if needed."""
        assert self.model.env is not None
        self.eval_agent.policy = self.model.policy
        self.starting_timestep = self.model.num_timesteps
        if self.model.num_timesteps < self.save_interval:
            saves = [int(p.stem) for p in self.save_dir.iterdir() if int(p.stem) >= 0]
            if self.behavior_clone and len(saves) == 0:
                print(
                    "behavior_clone on, but no save file found. Downloading "
                    f"{HF_BC_MODEL_FILE} from {HF_BC_MODEL_REPO}...",
                    flush=True,
                )
                downloaded_policy = Path(
                    hf_hub_download(
                        repo_id=HF_BC_MODEL_REPO,
                        filename=HF_BC_MODEL_FILE,
                        repo_type="model",
                    )
                )
                shutil.copy2(
                    downloaded_policy, self.save_dir / f"{HF_BC_MODEL_TIMESTEP}.zip"
                )
                saves = [HF_BC_MODEL_TIMESTEP]
                self.model.set_parameters(
                    str(self.save_dir / f"{max(saves)}.zip"), device=self.model.device
                )
            win_rate = self.compare(self.eval_agent, self.eval_opponent, 1000)
            self.model.logger.record("train/eval", win_rate)
            if not self.behavior_clone:
                self.model.save(self.save_dir / f"{self.model.num_timesteps}")
        if self.learning_style == LearningStyle.EXPLOITER:
            for i in range(self.model.env.num_envs):
                self.model.env.env_method(
                    "set_opp_policy",
                    str(self.save_dir / "-1"),
                    self.model.device,
                    indices=i,
                )

    def _on_rollout_start(self):
        """Sample opponents for self-play and record checkpoints at intervals."""
        assert self.model.env is not None
        if (
            self.model.num_timesteps % self.save_interval == 0
            and self.model.num_timesteps > self.starting_timestep
        ):
            self.record()
        self.model.logger.dump(self.model.num_timesteps)
        if self.behavior_clone:
            assert isinstance(self.model.policy, MaskedActorCriticPolicy)
            self.model.policy.actor_grad = (
                self.model.num_timesteps >= self.save_interval
            )
        if self.learning_style in [
            LearningStyle.FICTITIOUS_PLAY,
            LearningStyle.DOUBLE_ORACLE,
        ]:
            policy_files = sorted(self.save_dir.iterdir(), key=lambda p: int(p.stem))
            selected_files = random.choices(
                policy_files, weights=self.prob_dist, k=self.model.env.num_envs
            )
            for i in range(self.model.env.num_envs):
                self.model.env.env_method(
                    "set_opp_policy", selected_files[i], self.model.device, indices=i
                )

    def _on_training_end(self):
        """Record final checkpoint and flush logs."""
        self.record()
        self.model.logger.dump(self.model.num_timesteps)

    def record(self):
        """Evaluate current policy, update payoff matrix for DO, and save checkpoint."""
        win_rate = self.compare(self.eval_agent, self.eval_opponent, 1000)
        self.model.logger.record("train/eval", win_rate)
        if self.learning_style == LearningStyle.DOUBLE_ORACLE:
            policy_files = list(self.save_dir.iterdir())
            self.update_payoff_matrix(policy_files)
        self.model.save(self.save_dir / f"{self.model.num_timesteps}")

    def update_payoff_matrix(self, policy_files: list[Path]):
        """
        Expand and persist the double-oracle payoff matrix with a new policy.

        Evaluates the current training policy (`self.eval_agent`) against each
        policy in `policy_files`, appends the resulting payoffs to both axes of
        the square matrix, recomputes the Nash opponent distribution, and writes
        the rounded matrix to disk.

        Args:
            policy_files: Existing checkpoint files.
        """
        ordered_policy_files = sorted(policy_files, key=lambda p: int(p.stem))
        win_rates = np.array([])
        for p in ordered_policy_files:
            self.eval_agent2.set_policy(p, self.model.device)
            win_rate = self.compare(self.eval_agent, self.eval_agent2, 100)
            win_rates = np.append(win_rates, win_rate)
        self.payoff_matrix = np.concat(
            [self.payoff_matrix, 1 - win_rates.reshape(-1, 1)], axis=1
        )
        win_rates = np.append(win_rates, 0.5)
        self.payoff_matrix = np.concat(
            [self.payoff_matrix, win_rates.reshape(1, -1)], axis=0
        )
        self.prob_dist = Game(self.payoff_matrix).linear_program()[0].tolist()
        payoff_path = self.log_dir / f"{self.num_teams}-teams-payoff-matrix.json"
        with payoff_path.open("w") as f:
            json.dump(
                [
                    [round(win_rate, 3) for win_rate in win_rates]
                    for win_rates in self.payoff_matrix.tolist()
                ],
                f,
            )

    @staticmethod
    def compare(player1: Player, player2: Player, n_battles: int) -> float:
        """
        Run battles between two players and return player1's win rate.

        Args:
            player1: First player (whose win rate is returned).
            player2: Second player.
            n_battles: Number of battles to run.

        Returns:
            Win rate of player1 as a float between 0 and 1.
        """
        asyncio.run(player1.battle_against(player2, n_battles=n_battles))
        win_rate = player1.win_rate
        player1.reset_battles()
        player2.reset_battles()
        return win_rate
