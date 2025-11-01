import json
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
from gymnasium import spaces
from poke_env.environment import DoublesEnv
from src.mcts import MCTS
from src.simulator import Simulator
from stable_baselines3 import PPO
from stable_baselines3.common.buffers import RolloutBuffer
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.utils import obs_as_tensor
from stable_baselines3.common.vec_env import VecEnv


class MCTS_PPO(PPO):
    def __init__(
        self,
        *args: Any,
        mcts_simulations: int = 64,
        mcts_exploration: float = math.sqrt(2.0),
        mcts_rollout_depth: int = 12,
        mcts_rollout_policy: Optional[Any] = None,
        showdown_path: str = "pokemon-showdown/pokemon-showdown",
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.mcts_simulations = mcts_simulations
        self.mcts_exploration = mcts_exploration
        self.mcts_rollout_depth = mcts_rollout_depth
        self.mcts_rollout_policy = mcts_rollout_policy
        self.mcts_showdown_path = showdown_path
        self._simulators: List[Optional[Simulator]] = []
        self._simulator_configs: List[Optional[Tuple[str, str, str]]] = []
        self._last_infos: List[Dict[str, Any]] = []

    def _ensure_simulators(self, env: VecEnv) -> None:
        if len(self._simulators) != env.num_envs:
            self._close_simulators()
            self._simulators = [None] * env.num_envs
            self._simulator_configs = [None] * env.num_envs

    def _get_simulator(self, index: int, payload: Dict[str, Any]) -> Simulator:
        format_id = payload["format_id"]
        role = payload["player_role"]
        opponent = payload["opponent_role"]
        config = (format_id, role, opponent)
        simulator = self._simulators[index]
        if simulator is not None and self._simulator_configs[index] != config:
            simulator.close()
            simulator = None
        if simulator is None:
            simulator = Simulator(
                format_id=format_id,
                player_role=role,
                opponent_role=opponent,
                showdown_path=self.mcts_showdown_path,
            )
            self._simulators[index] = simulator
        self._simulator_configs[index] = config
        return simulator

    def _select_actions(self, simulator: Simulator, payload: Dict[str, Any]) -> np.ndarray:
        tree = MCTS(
            simulator=simulator,
            player_role=payload["player_role"],
            opponent_role=payload["opponent_role"],
            root_state=payload["state"],
            exploration=self.mcts_exploration,
            rollout_depth=self.mcts_rollout_depth,
            rollout_policy=self.mcts_rollout_policy,
        )
        decision = tree.run(self.mcts_simulations)
        if decision is None:
            return np.full(2, -2, dtype=np.int64)
        # Recreate the battle snapshot so we can translate the chosen order back to action ids.
        battle = tree._state_to_battle(payload["state"])
        if battle is None:
            return np.full(2, -2, dtype=np.int64)
        actions = DoublesEnv.order_to_action(decision, battle)
        return np.array(actions, dtype=np.int64)

    def _flatten_info_entries(self, infos: Sequence[Any], expected: int) -> List[Dict[str, Any]]:
        flattened: List[Dict[str, Any]] = []
        for entry in infos:
            if isinstance(entry, dict):
                flattened.append(entry)
                continue
            if isinstance(entry, (list, tuple)):
                for sub in entry:
                    if isinstance(sub, dict):
                        flattened.append(sub)
                    elif isinstance(sub, tuple) and len(sub) == 2 and isinstance(sub[1], dict):
                        flattened.append(sub[1])
            # Ignore anything else
            if len(flattened) >= expected:
                break
        return flattened

    def _normalize_info_entry(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(entry, dict):
            return None
        payload = dict(entry)
        state = payload.get("state")
        if state is None:
            state = payload.get("battle_state")
        if isinstance(state, str):
            try:
                state = json.loads(state)
            except json.JSONDecodeError:
                return None
        if not isinstance(state, dict):
            return None
        payload["state"] = state

        format_id = payload.get("format_id") or state.get("formatid") or ""
        payload["format_id"] = format_id or "gen9vgc2024regg"

        player_role = payload.get("player_role")
        opponent_role = payload.get("opponent_role")

        if player_role is None or opponent_role is None:
            roles: List[str] = []
            sides = state.get("sides")
            if isinstance(sides, list):
                for side in sides:
                    if isinstance(side, dict):
                        ident = side.get("id")
                        if isinstance(ident, str):
                            roles.append(ident)
            if player_role is None and roles:
                player_role = roles[0]
            if opponent_role is None and len(roles) > 1:
                opponent_role = roles[1]

        if player_role is None:
            player_role = "p1"
        if opponent_role is None:
            opponent_role = "p2" if player_role != "p2" else "p1"

        payload["player_role"] = player_role
        payload["opponent_role"] = opponent_role
        return payload

    def _prepare_mcts_payloads(self, expected: int) -> Optional[List[Dict[str, Any]]]:
        if not self._last_infos:
            return None
        flattened = self._flatten_info_entries(self._last_infos, expected)
        if len(flattened) < expected:
            return None
        payloads: List[Dict[str, Any]] = []
        for entry in flattened[:expected]:
            normalized = self._normalize_info_entry(entry)
            if normalized is None:
                return None
            payloads.append(normalized)
        return payloads

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

        self._ensure_simulators(env)

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

            obs_tensor = obs_as_tensor(self._last_obs, self.device)  # type: ignore
            payloads = self._prepare_mcts_payloads(env.num_envs)
            use_mcts = payloads is not None

            if use_mcts:
                assert payloads is not None
                actions_list: List[np.ndarray] = []
                for idx, payload in enumerate(payloads):
                    try:
                        simulator = self._get_simulator(idx, payload)
                        action_array = self._select_actions(simulator, payload)
                    except Exception:
                        use_mcts = False
                        break
                    actions_list.append(action_array)
                if use_mcts and len(actions_list) == env.num_envs:
                    actions_np = np.stack(actions_list, axis=0)
                    actions_tensor = torch.as_tensor(actions_np, device=self.device)
                    with torch.no_grad():
                        values, log_probs, _ = self.policy.evaluate_actions(
                            obs_tensor, actions_tensor
                        )
                else:
                    use_mcts = False

            if not use_mcts:
                with torch.no_grad():
                    actions_tensor, values, log_probs = self.policy(obs_tensor)

            # Rescale and perform action
            actions = actions_tensor.cpu().numpy()  # type: ignore
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
                        clipped_actions, self.action_space.low, self.action_space.high
                    )

            new_obs, rewards, dones, infos = env.step(clipped_actions)

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
                values,  # type: ignore
                log_probs,  # type: ignore
            )
            self._last_obs = new_obs  # type: ignore[assignment]
            self._last_infos = self._flatten_info_entries(infos, env.num_envs)
            self._last_episode_starts = dones

        with torch.no_grad():
            # Compute value for the last timestep
            values = self.policy.predict_values(obs_as_tensor(new_obs, self.device))  # type: ignore[arg-type]

        rollout_buffer.compute_returns_and_advantage(last_values=values, dones=dones)  # type: ignore

        callback.update_locals(locals())

        callback.on_rollout_end()

        return True

    def _close_simulators(self) -> None:
        for simulator in self._simulators:
            if simulator is not None:
                simulator.close()
        self._simulators = []
        self._simulator_configs = []
