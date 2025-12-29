from typing import Any

import numpy as np
import torch
from gymnasium import spaces
from poke_env.battle import DoubleBattle
from src.mcts import run_mcts_for_battle
from stable_baselines3 import PPO
from stable_baselines3.common.buffers import RolloutBuffer
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.utils import obs_as_tensor
from stable_baselines3.common.vec_env import VecEnv


class MCTS_PPO(PPO):
    def __init__(
        self, *args: Any, use_mcts: bool = False, mcts_simulations: int = 100, **kwargs: Any
    ):
        super().__init__(*args, **kwargs)
        self.use_mcts = use_mcts
        self.mcts_simulations = mcts_simulations
        # Store battle states from previous step for MCTS
        self._cached_battles: list[DoubleBattle | None] = []

    def _get_mcts_actions(
        self, battles: list[DoubleBattle | None], policy_actions: np.ndarray
    ) -> np.ndarray:
        """Run MCTS on battle states and return improved actions."""
        if not self.use_mcts:
            return policy_actions

        mcts_actions = policy_actions.copy()
        for i, battle in enumerate(battles):
            if battle is None or battle.finished:
                continue
            if battle._wait:
                continue
            # Skip MCTS during teampreview - use policy action
            if battle.teampreview:
                continue

            try:
                # Run MCTS to get best action
                action_order = run_mcts_for_battle(battle, num_simulations=self.mcts_simulations)

                # Parse the action string back to action indices
                parsed_action = self._parse_action_string(action_order.message, battle)
                if parsed_action is not None:
                    mcts_actions[i] = parsed_action
            except Exception:
                # Fall back to policy action on any error
                pass

        return mcts_actions

    def _extract_battles_from_infos(
        self, infos: list[dict[str, Any]], num_envs: int
    ) -> list[DoubleBattle | None]:
        """Extract battle states from the info dicts returned by env.step()."""
        battles: list[DoubleBattle | None] = []
        for i in range(num_envs):
            battle = None
            if i < len(infos):
                info = infos[i]
                # Try different possible keys for battle state
                if "battle" in info:
                    battle = info["battle"]
                elif "p1" in info and "battle" in info["p1"]:
                    battle = info["p1"]["battle"]
                elif "p2" in info and "battle" in info["p2"]:
                    battle = info["p2"]["battle"]
            battles.append(battle)
        return battles

    def _parse_action_string(self, action_str: str, _battle: DoubleBattle) -> np.ndarray | None:
        """Parse an action string back to action indices."""
        if not action_str:
            return None

        try:
            # Handle teampreview format: "/team 1234"
            if action_str.startswith("/team "):
                indices_str = action_str[6:]
                # Return first two as the action (for the two active slots)
                if len(indices_str) >= 2:
                    return np.array([int(indices_str[0]), int(indices_str[1])])
                return None

            # Handle battle action format: "/choose move1 +2, switch 3"
            if action_str.startswith("/choose "):
                action_str = action_str[8:]

            parts = action_str.split(", ")
            actions = []

            for part in parts:
                part = part.strip()
                if part.startswith("move"):
                    # Parse move action: "move1 +2" or "move2 -1" etc.
                    move_part = part.split()[0]
                    move_idx = int(move_part[4:]) - 1  # "move1" -> 0

                    # Check for target
                    target = 0
                    if " " in part:
                        target_str = part.split()[1]
                        if target_str.startswith("+") or target_str.startswith("-"):
                            target = int(target_str)

                    # Convert to action index (simplified mapping)
                    # Base move actions start at 7, each move has 5 target options
                    base_action = 7 + move_idx * 5
                    target_offset = target + 2  # -2 -> 0, -1 -> 1, 0 -> 2, +1 -> 3, +2 -> 4
                    actions.append(base_action + target_offset)

                elif part.startswith("switch"):
                    # Parse switch action: "switch 3"
                    switch_idx = int(part.split()[1])
                    actions.append(switch_idx)

                elif part == "pass":
                    actions.append(0)

                elif part.startswith("tera"):
                    # Handle terastallize moves
                    # Format: "tera move1 +2"
                    rest = part[5:]  # Remove "tera "
                    if rest.startswith("move"):
                        move_part = rest.split()[0]
                        move_idx = int(move_part[4:]) - 1
                        target = 0
                        if " " in rest:
                            target_str = rest.split()[1]
                            if target_str.startswith("+") or target_str.startswith("-"):
                                target = int(target_str)
                        base_action = 87 + move_idx * 5  # Tera moves start at 87
                        target_offset = target + 2
                        actions.append(base_action + target_offset)

            if len(actions) >= 2:
                return np.array(actions[:2])
            elif len(actions) == 1:
                return np.array([actions[0], 0])
            return None
        except Exception:
            return None

    def collect_rollouts(
        self,
        env: VecEnv,
        callback: BaseCallback,
        rollout_buffer: RolloutBuffer,
        n_rollout_steps: int,
    ) -> bool:
        """
        Collect experiences using the current policy and fill a ``RolloutBuffer``.
        The term rollout here refers to the model-free notion and should not
        be used with the concept of rollout used in model-based RL or planning.

        :param env: The training environment
        :param callback: Callback that will be called at each step
            (and at the beginning and end of the rollout)
        :param rollout_buffer: Buffer to fill with rollouts
        :param n_rollout_steps: Number of experiences to collect per environment
        :return: True if function returned with at least `n_rollout_steps`
            collected, False if callback terminated rollout prematurely.
        """
        assert self._last_obs is not None, "No previous observation was provided"
        # Switch to eval mode (this affects batch norm / dropout)
        self.policy.set_training_mode(False)

        n_steps = 0
        rollout_buffer.reset()
        # Sample new weights for the state dependent exploration
        if self.use_sde:
            self.policy.reset_noise(env.num_envs)

        callback.on_rollout_start()

        while n_steps < n_rollout_steps:
            if self.use_sde and self.sde_sample_freq > 0 and n_steps % self.sde_sample_freq == 0:
                # Sample a new noise matrix
                self.policy.reset_noise(env.num_envs)

            with torch.no_grad():
                # Convert to pytorch tensor or to TensorDict
                obs_tensor = obs_as_tensor(self._last_obs, self.device)  # type: ignore
                actions, values, log_probs = self.policy(obs_tensor)
            actions = actions.cpu().numpy()

            # Apply MCTS if enabled and we have cached battle states
            if self.use_mcts and self._cached_battles:
                actions = self._get_mcts_actions(self._cached_battles, actions)

            # Rescale and perform action
            clipped_actions = actions

            if isinstance(self.action_space, spaces.Box):
                if self.policy.squash_output:
                    # Unscale the actions to match env bounds
                    # if they were previously squashed (scaled in [-1, 1])
                    clipped_actions = self.policy.unscale_action(clipped_actions)
                else:
                    # Otherwise, clip the actions to avoid out of bound error
                    # as we are sampling from an unbounded Gaussian distribution
                    clipped_actions = np.clip(
                        actions, self.action_space.low, self.action_space.high
                    )

            new_obs, rewards, dones, infos = env.step(clipped_actions)

            # Extract battle states from infos for MCTS in next iteration
            if self.use_mcts:
                self._cached_battles = self._extract_battles_from_infos(infos, env.num_envs)

            self.num_timesteps += env.num_envs

            # Give access to local variables
            callback.update_locals(locals())
            if not callback.on_step():
                return False

            self._update_info_buffer(infos, dones)
            n_steps += 1

            if isinstance(self.action_space, spaces.Discrete):
                # Reshape in case of discrete action
                actions = actions.reshape(-1, 1)

            # Handle timeout by bootstrapping with value function
            # see GitHub issue #633
            for idx, done in enumerate(dones):
                if (
                    done
                    and infos[idx].get("terminal_observation") is not None
                    and infos[idx].get("TimeLimit.truncated", False)
                ):
                    terminal_obs = self.policy.obs_to_tensor(infos[idx]["terminal_observation"])[0]
                    with torch.no_grad():
                        terminal_value = self.policy.predict_values(terminal_obs)[0]  # type: ignore[arg-type]
                    rewards[idx] += self.gamma * terminal_value

            rollout_buffer.add(
                self._last_obs,  # type: ignore[arg-type]
                actions,
                rewards,
                self._last_episode_starts,  # type: ignore[arg-type]
                values,
                log_probs,
            )
            self._last_obs = new_obs  # type: ignore[assignment]
            self._last_episode_starts = dones

        with torch.no_grad():
            # Compute value for the last timestep
            values = self.policy.predict_values(obs_as_tensor(new_obs, self.device))  # type: ignore[arg-type]

        rollout_buffer.compute_returns_and_advantage(last_values=values, dones=dones)  # type: ignore

        callback.update_locals(locals())

        callback.on_rollout_end()

        return True
