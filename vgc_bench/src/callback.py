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
import torch
from huggingface_hub import hf_hub_download
from nashpy import Game
from poke_env.player import Player, SimpleHeuristicsPlayer
from poke_env.ps_client import ServerConfiguration
from stable_baselines3.common.callbacks import BaseCallback

from vgc_bench.src.mcts import MCTSPlayer
from vgc_bench.src.policy import MaskedActorCriticPolicy
from vgc_bench.src.policy_player import BatchPolicyPlayer
from vgc_bench.src.teams import RandomTeamBuilder, TeamToggle, get_available_regs
from vgc_bench.src.utils import LearningStyle, format_map

warnings.filterwarnings("ignore", category=UserWarning)

HF_BC_MODEL_REPO = "cameronangliss/vgc-bench-models"
HF_BC_MODEL_FILE = "results/saves_bc/seed1/100.zip"
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
        num_teams: int | None,
        reg: str | None,
        num_eval_workers: int,
        log_level: int,
        port: int,
        learning_style: LearningStyle,
        behavior_clone: bool,
        allow_mirror_match: bool,
        choose_on_teampreview: bool,
        save_interval: int,
        team_paths: list[Path] | None,
        results_suffix: str,
        total_steps: int,
        evaluate: bool = True,
        alpha_zero: bool = False,
        az_mcts_threads: int = 1,
        az_policy_coef: float = 0.25,
        az_value_coef: float = 0.5,
        az_train_epochs: int = 1,
        az_batch_size: int = 512,
        az_replay_size: int = 8192,
        az_eval_mcts: bool = False,
        az_eval_mcts_ms: int = 50,
    ):
        """
        Initialize the training callback.

        Args:
            run_id: Training run identifier.
            num_teams: Number of teams to use.
            reg: VGC regulation letter (e.g. 'g', 'h', 'i'), or None for all.
            num_eval_workers: Number of parallel evaluation workers.
            log_level: Logging verbosity for Showdown clients.
            port: Port for the Pokemon Showdown server.
            learning_style: Training paradigm (self-play, fictitious play, etc.).
            behavior_clone: Whether initialized from behavior cloning.
            allow_mirror_match: Whether to allow same-team matchups.
            choose_on_teampreview: Whether policy makes teampreview decisions.
            save_interval: Timesteps between checkpoint saves.
            team_paths: Optional list of team file paths for matchup solving.
            results_suffix: Suffix appended to results<run_id> for output paths.
            total_steps: Total training timesteps for entropy coefficient decay.
            evaluate: Whether to run evaluations and save checkpoints.
        """
        super().__init__()
        self.evaluate = evaluate
        self.alpha_zero = alpha_zero
        self.az_mcts_threads = az_mcts_threads
        self.az_policy_coef = az_policy_coef
        self.az_value_coef = az_value_coef
        self.az_train_epochs = az_train_epochs
        self.az_batch_size = az_batch_size
        self.az_replay_size = az_replay_size
        self.az_eval_mcts = az_eval_mcts
        self.az_eval_mcts_ms = az_eval_mcts_ms
        self.az_obs_buffer: list[dict[str, npt.NDArray[np.float32]]] = []
        self.az_target_buffer: list[list[tuple[int, int, float]]] = []
        self.az_value_buffer: list[float] = []
        self.total_steps = total_steps
        self.learning_style = learning_style
        self.behavior_clone = behavior_clone
        self.save_interval = save_interval
        method_tags = [
            "bc" if behavior_clone else None,
            "az" if alpha_zero else None,
            learning_style.abbrev,
            "xm" if not allow_mirror_match else None,
            "xt" if not choose_on_teampreview else None,
        ]
        method = "_".join([p for p in method_tags if p is not None])
        suffix = f"_{results_suffix}" if results_suffix else ""
        output_dir = Path(f"results{suffix}")
        self.log_dir = output_dir / f"logs_{method}"
        if reg is None:
            battle_format = format_map[get_available_regs()[0]]
        else:
            battle_format = format_map[reg]
        method_dir = output_dir / f"saves_{method}"
        method_dir = method_dir / (f"reg_{reg}" if reg is not None else "reg_all")
        if num_teams is not None:
            method_dir = method_dir / f"{num_teams}_teams"
        self.save_dir = method_dir / f"seed{run_id}"
        self.save_label = str(self.save_dir.relative_to(output_dir / f"saves_{method}"))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.payoff_matrix: npt.NDArray[np.float32]
        self.prob_dist = None
        if self.learning_style == LearningStyle.DOUBLE_ORACLE:
            payoff_path = self.log_dir / f"{self.save_label}_payoff_matrix.json"
            if payoff_path.exists():
                with payoff_path.open() as f:
                    self.payoff_matrix = np.array(json.load(f))
            else:
                self.payoff_matrix = np.array([[0.5]])
            self.prob_dist = Game(self.payoff_matrix).linear_program()[0].tolist()
        toggle = None if allow_mirror_match else TeamToggle()
        if self.evaluate:
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
                team=RandomTeamBuilder(run_id, num_teams, reg, team_paths, toggle),
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
                team=RandomTeamBuilder(run_id, num_teams, reg, team_paths, toggle),
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
                team=RandomTeamBuilder(run_id, num_teams, reg, team_paths, toggle),
            )
            self.eval_opponent2 = BatchPolicyPlayer(
                deterministic=True,
                server_configuration=ServerConfiguration(
                    f"ws://localhost:{port}/showdown/websocket",
                    "https://play.pokemonshowdown.com/action.php?",
                ),
                battle_format=battle_format,
                log_level=log_level,
                max_concurrent_battles=num_eval_workers,
                accept_open_team_sheet=True,
                open_timeout=None,
                team=RandomTeamBuilder(run_id, num_teams, reg, team_paths, toggle),
            )
            self.eval_mcts_agent = (
                MCTSPlayer(
                    duration_ms=az_eval_mcts_ms,
                    threads=az_mcts_threads,
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
                        run_id, num_teams, reg, team_paths, toggle
                    ),
                )
                if az_eval_mcts
                else None
            )

    def _on_step(self) -> bool:
        """Called after each environment step. Returns True to continue training."""
        if self.alpha_zero:
            self.collect_alpha_zero_targets()
        return True

    def collect_alpha_zero_targets(self) -> None:
        """Collect sparse MCTS visit targets from vectorized env infos."""
        infos = self.locals.get("infos", [])
        algorithm = self.locals.get("self")
        last_obs = getattr(algorithm, "_last_obs", None)
        if not isinstance(last_obs, dict):
            return
        for env_idx, info in enumerate(infos):
            pairs = info.get("az_target_pairs")
            if not pairs:
                continue
            obs = {
                key: np.asarray(value[env_idx]).copy()
                for key, value in last_obs.items()
            }
            self.az_obs_buffer.append(obs)
            self.az_target_buffer.append(
                [
                    (int(first), int(second), float(prob))
                    for first, second, prob in pairs
                ]
            )
            self.az_value_buffer.append(float(info.get("az_value_target", 0.0)))
        if len(self.az_obs_buffer) > self.az_replay_size:
            excess = len(self.az_obs_buffer) - self.az_replay_size
            del self.az_obs_buffer[:excess]
            del self.az_target_buffer[:excess]
            del self.az_value_buffer[:excess]

    def _on_training_start(self):
        """Initialize evaluation agent and perform initial checkpoint if needed."""
        assert self.model.env is not None
        self.starting_timestep = self.model.num_timesteps
        if not self.evaluate:
            if self.behavior_clone:
                bc_policy_path = self.save_dir / f"{HF_BC_MODEL_TIMESTEP}.zip"
                saves = [
                    int(p.stem) for p in self.save_dir.iterdir() if int(p.stem) >= 0
                ]
                if len(saves) == 0:
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
                    shutil.copy2(downloaded_policy, bc_policy_path)
                    saves = [HF_BC_MODEL_TIMESTEP]
                    self.model.set_parameters(
                        str(self.save_dir / f"{max(saves)}.zip"),
                        device=self.model.device,
                    )
            return
        self.eval_agent.policy = self.model.policy
        bc_policy_path = self.save_dir / f"{HF_BC_MODEL_TIMESTEP}.zip"
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
                shutil.copy2(downloaded_policy, bc_policy_path)
                saves = [HF_BC_MODEL_TIMESTEP]
                self.model.set_parameters(
                    str(self.save_dir / f"{max(saves)}.zip"), device=self.model.device
                )
            heuristic_win_rates = self.compare(self.eval_agent, self.eval_opponent, 100)
            for label, wr in heuristic_win_rates.items():
                self.model.logger.record(f"eval/heuristic{label}", wr)
            if self.eval_mcts_agent is not None:
                mcts_win_rates = self.compare(
                    self.eval_mcts_agent, self.eval_opponent, 100
                )
                for label, wr in mcts_win_rates.items():
                    self.model.logger.record(f"eval/mcts_heuristic{label}", wr)
            if not self.behavior_clone:
                self.model.save(self.save_dir / f"{self.model.num_timesteps}")
        if bc_policy_path.exists():
            self.eval_opponent2.set_policy(bc_policy_path, self.model.device)
            if self.model.num_timesteps < self.save_interval:
                bc_win_rates = self.compare(self.eval_agent, self.eval_opponent2, 100)
                for label, wr in bc_win_rates.items():
                    self.model.logger.record(f"eval/bc{label}", wr)
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
        if self.alpha_zero:
            self.train_alpha_zero_targets()
        if (
            self.evaluate
            and self.model.num_timesteps % self.save_interval == 0
            and self.model.num_timesteps > self.starting_timestep
        ):
            self.record()
        self.model.logger.dump(self.model.num_timesteps)
        if self.behavior_clone:
            assert isinstance(self.model.policy, MaskedActorCriticPolicy)
            self.model.policy.actor_grad = self.model.num_timesteps >= 98_304
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

    def train_alpha_zero_targets(self) -> None:
        """Apply auxiliary MCTS visit-distribution and root-value losses."""
        if (
            (self.az_policy_coef <= 0 and self.az_value_coef <= 0)
            or not self.az_obs_buffer
            or not isinstance(self.model.policy, MaskedActorCriticPolicy)
        ):
            return
        policy = self.model.policy
        if not policy.actor_grad:
            return

        policy.set_training_mode(True)
        n_samples = len(self.az_obs_buffer)
        batch_size = min(self.az_batch_size, n_samples)
        total_policy_losses: list[float] = []
        total_value_losses: list[float] = []
        total_targets = 0

        for _ in range(self.az_train_epochs):
            indices = np.random.permutation(n_samples)
            for start in range(0, n_samples, batch_size):
                batch_indices = indices[start : start + batch_size]
                obs_np = {
                    key: np.stack([self.az_obs_buffer[i][key] for i in batch_indices])
                    for key in self.az_obs_buffer[0]
                }
                obs = {
                    key: torch.as_tensor(value, device=policy.device)
                    for key, value in obs_np.items()
                }
                losses = []
                if self.az_value_coef > 0:
                    # calc_reward is +1 win / -1 loss with gamma=1, so the critic's
                    # value scale is 2 * P(win) - 1; map the engine win-prob target.
                    value_targets = torch.as_tensor(
                        [2.0 * self.az_value_buffer[i] - 1.0 for i in batch_indices],
                        device=policy.device,
                        dtype=torch.float32,
                    )
                    value_loss = self.az_value_coef * policy.value_target_loss(
                        obs, value_targets
                    )
                    losses.append(value_loss)
                    total_value_losses.append(value_loss.item())

                sample_indices: list[int] = []
                first_actions: list[int] = []
                second_actions: list[int] = []
                probs: list[float] = []
                for sample_idx, buffer_idx in enumerate(batch_indices):
                    for first, second, prob in self.az_target_buffer[buffer_idx]:
                        sample_indices.append(sample_idx)
                        first_actions.append(first)
                        second_actions.append(second)
                        probs.append(prob)
                if probs and self.az_policy_coef > 0:
                    target_sample_indices = torch.as_tensor(
                        sample_indices, device=policy.device, dtype=torch.long
                    )
                    target_first_actions = torch.as_tensor(
                        first_actions, device=policy.device, dtype=torch.long
                    )
                    target_second_actions = torch.as_tensor(
                        second_actions, device=policy.device, dtype=torch.long
                    )
                    target_probs = torch.as_tensor(
                        probs, device=policy.device, dtype=torch.float32
                    )
                    policy_loss = self.az_policy_coef * policy.action_pair_target_loss(
                        obs,
                        target_sample_indices,
                        target_first_actions,
                        target_second_actions,
                        target_probs,
                    )
                    losses.append(policy_loss)
                    total_policy_losses.append(policy_loss.item())
                    total_targets += len(probs)

                if not losses:
                    continue
                loss = sum(losses)
                policy.optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(
                    policy.parameters(), self.model.max_grad_norm
                )
                policy.optimizer.step()

        if total_policy_losses:
            self.model.logger.record(
                "train/az_policy_loss", np.mean(total_policy_losses)
            )
            self.model.logger.record("train/az_targets", total_targets)
        if total_value_losses:
            self.model.logger.record("train/az_value_loss", np.mean(total_value_losses))
        if total_policy_losses or total_value_losses:
            self.model.logger.record("train/az_buffer_size", len(self.az_obs_buffer))

    def _on_training_end(self):
        """Record final checkpoint and flush logs."""
        if self.alpha_zero:
            self.train_alpha_zero_targets()
        if self.evaluate:
            self.record()
        self.model.logger.dump(self.model.num_timesteps)

    def record(self):
        """Evaluate current policy, update payoff matrix for DO, and save checkpoint."""
        heuristic_win_rates = self.compare(self.eval_agent, self.eval_opponent, 100)
        for label, wr in heuristic_win_rates.items():
            self.model.logger.record(f"eval/heuristic{label}", wr)
        if self.eval_mcts_agent is not None:
            mcts_win_rates = self.compare(self.eval_mcts_agent, self.eval_opponent, 100)
            for label, wr in mcts_win_rates.items():
                self.model.logger.record(f"eval/mcts_heuristic{label}", wr)
        if self.eval_opponent2.policy is not None:
            bc_win_rates = self.compare(self.eval_agent, self.eval_opponent2, 100)
            for label, wr in bc_win_rates.items():
                self.model.logger.record(f"eval/bc{label}", wr)
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
            wr = self.compare(self.eval_agent, self.eval_agent2, 100, per_reg=False)[""]
            win_rates = np.append(win_rates, wr)
        self.payoff_matrix = np.concat(
            [self.payoff_matrix, 1 - win_rates.reshape(-1, 1)], axis=1
        )
        win_rates = np.append(win_rates, 0.5)
        self.payoff_matrix = np.concat(
            [self.payoff_matrix, win_rates.reshape(1, -1)], axis=0
        )
        self.prob_dist = Game(self.payoff_matrix).linear_program()[0].tolist()
        payoff_path = self.log_dir / f"{self.save_label}_payoff_matrix.json"
        with payoff_path.open("w") as f:
            json.dump(
                [
                    [round(win_rate, 3) for win_rate in win_rates]
                    for win_rates in self.payoff_matrix.tolist()
                ],
                f,
            )

    @staticmethod
    def compare(
        player1: Player, player2: Player, n_battles: int, per_reg: bool = True
    ) -> dict[str, float]:
        """
        Run battles between two players and return player1's win rates.

        Args:
            player1: First player (whose win rate is returned).
            player2: Second player.
            n_battles: Number of battles to run (per regulation if multi-reg).
            per_reg: Whether to break down win rates by regulation in multi-reg
                mode. When False, only the aggregate is returned.

        Returns:
            Dict mapping suffix to win rate. Always contains "" (aggregate).
            When per_reg is True and in multi-reg mode, also contains
            per-regulation entries like "_reg_f".
        """
        assert isinstance(player1._team, RandomTeamBuilder)
        assert isinstance(player2._team, RandomTeamBuilder)
        available_regs = player1._team.available_regs
        if available_regs is None or not per_reg:
            asyncio.run(player1.battle_against(player2, n_battles=n_battles))
            win_rate = player1.win_rate
            player1.reset_battles()
            player2.reset_battles()
            return {"": win_rate}
        else:
            win_rates: dict[str, float] = {}
            total_wins = 0
            total_battles = 0
            for reg in available_regs:
                player1._team.current_reg = reg
                player2._team.current_reg = reg
                fmt = format_map[reg]
                player1._format = fmt
                player2._format = fmt
                asyncio.run(player1.battle_against(player2, n_battles=n_battles))
                win_rates[f"_reg_{reg}"] = player1.win_rate
                total_wins += player1.n_won_battles
                total_battles += player1.n_finished_battles
                player1.reset_battles()
                player2.reset_battles()
            win_rates[""] = total_wins / total_battles if total_battles > 0 else 0
            return win_rates
