import argparse
import os
import pickle

import numpy as np
import torch
from imitation.algorithms.bc import BC
from imitation.data.types import Trajectory
from imitation.util.logger import configure
from poke_env.environment import SingleAgentWrapper
from poke_env.player import MaxBasePowerPlayer, RandomPlayer
from poke_env.ps_client import ServerConfiguration
from src.agent import Agent
from src.callback import Callback
from src.env import ShowdownEnv
from src.policy import MaskedActorCriticPolicy
from src.teams import RandomTeamBuilder
from src.utils import LearningStyle, battle_format
from stable_baselines3 import PPO
from torch.utils.data import DataLoader, Dataset


class TrajectoryDataset(Dataset):
    def __init__(self, num_frames: int):
        self.num_frames = num_frames
        directory = "data/trajs"
        self.files = [
            os.path.join(directory, file) for file in os.listdir(directory) if file.endswith(".pkl")
        ]

    def __len__(self):
        return len(self.files)

    def __getitem__(self, idx):
        file_path = self.files[idx]
        with open(file_path, "rb") as f:
            traj = pickle.load(f)
        if self.num_frames > 1:
            traj = self._frame_stack_traj(traj)
        return traj

    def _frame_stack_traj(self, traj: Trajectory) -> Trajectory:
        traj_len, *obs_shape = traj.obs.shape
        stacked_obs = np.empty((traj_len, self.num_frames, *obs_shape), dtype=traj.obs.dtype)
        zero_obs = np.zeros(obs_shape, dtype=traj.obs[0].dtype)
        for i in range(traj_len):
            for j in range(self.num_frames):
                idx = i - j
                if idx >= 0:
                    stacked_obs[i, self.num_frames - 1 - j] = traj.obs[idx]
                else:
                    stacked_obs[i, self.num_frames - 1 - j] = zero_obs
        return Trajectory(obs=stacked_obs, acts=traj.acts, infos=None, terminal=True)


def pretrain(num_teams: int, port: int, device: str, num_frames: int):
    env = ShowdownEnv(
        learning_style=LearningStyle.PURE_SELF_PLAY,
        battle_format=battle_format,
        log_level=40,
        accept_open_team_sheet=True,
        start_listening=False,
    )
    opponent = RandomPlayer(
        battle_format=battle_format,
        log_level=40,
        accept_open_team_sheet=True,
        start_listening=False,
    )
    single_agent_env = SingleAgentWrapper(env, opponent)
    ppo = PPO(
        MaskedActorCriticPolicy,
        single_agent_env,
        policy_kwargs={"num_frames": num_frames, "chooses_on_teampreview": True},
        device=device,
    )
    dataset = TrajectoryDataset(num_frames)
    div_count = 10
    dataloader = DataLoader(
        dataset,
        batch_size=len(dataset) // div_count,
        shuffle=True,
        num_workers=1,
        collate_fn=lambda batch: batch,
    )
    bc = BC(
        observation_space=ppo.observation_space,  # type: ignore
        action_space=ppo.action_space,  # type: ignore
        rng=np.random.default_rng(0),
        policy=ppo.policy,
        batch_size=1024,
        device=device,
        custom_logger=configure(
            f"results/logs-bc{f'-fs{num_frames}' if num_frames > 1 else ''}", ["tensorboard"]
        ),
    )
    eval_agent = Agent(
        num_frames,
        torch.device(device),
        server_configuration=ServerConfiguration(
            f"ws://localhost:{port}/showdown/websocket",
            "https://play.pokemonshowdown.com/action.php?",
        ),
        battle_format=battle_format,
        log_level=40,
        accept_open_team_sheet=True,
        team=RandomTeamBuilder(list(range(num_teams)), battle_format),
    )
    eval_opponent = MaxBasePowerPlayer(
        server_configuration=ServerConfiguration(
            f"ws://localhost:{port}/showdown/websocket",
            "https://play.pokemonshowdown.com/action.php?",
        ),
        battle_format=battle_format,
        log_level=40,
        accept_open_team_sheet=True,
        team=RandomTeamBuilder(list(range(num_teams)), battle_format),
    )
    policy = MaskedActorCriticPolicy.clone(ppo)
    eval_agent.set_policy(policy)
    win_rate = Callback.compare(eval_agent, eval_opponent, 100)
    bc.logger.record("bc/eval", win_rate)
    ppo.save(f"results/saves-bc{f'-fs{num_frames}' if num_frames > 1 else ''}/0")
    for i in range(100):
        data = iter(dataloader)
        for _ in range(div_count):
            demos = next(data)
            bc.set_demonstrations(demos)
            bc.train(n_epochs=1)
        policy = MaskedActorCriticPolicy.clone(ppo)
        eval_agent.set_policy(policy)
        win_rate = Callback.compare(eval_agent, eval_opponent, 100)
        bc.logger.record("bc/eval", win_rate)
        ppo.save(f"results/saves-bc{f'-fs{num_frames}' if num_frames > 1 else ''}/{i + 1}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pretrain a Pokémon AI model")
    parser.add_argument("--num_teams", type=int, default=1, help="Number of teams to train with")
    parser.add_argument("--port", type=int, default=8000, help="Port to run showdown server on")
    parser.add_argument(
        "--device",
        type=str,
        default="cuda:0",
        choices=["cuda:0", "cuda:1", "cuda:2", "cuda:3"],
        help="CUDA device to use for training",
    )
    parser.add_argument(
        "--num_frames",
        type=int,
        default=1,
        help="number of frames to use for frame stacking. default is 1",
    )
    args = parser.parse_args()
    pretrain(args.num_teams, args.port, args.device, args.num_frames)
