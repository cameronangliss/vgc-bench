import argparse

import numpy as np
import torch
from gymnasium.spaces import Box, MultiDiscrete
from poke_env.player import MaxBasePowerPlayer
from poke_env.ps_client import ServerConfiguration
from ray.rllib.algorithms.bc import BCConfig
from ray.rllib.core.rl_module import RLModuleSpec
from ray.tune.registry import register_env
from src.env import ShowdownEnv
from src.policy import ActorCriticModule
from src.policy_player import PolicyPlayer
from src.teams import RandomTeamBuilder
from src.utils import LearningStyle, act_len, battle_format, chunk_obs_len, moves, set_global_seed

# class TrajectoryDataset(Dataset):
#     def __init__(self, num_frames: int):
#         self.num_frames = num_frames
#         directory = "data/trajs"
#         self.files = [
#             os.path.join(directory, file) for file in os.listdir(directory) if file.endswith(".pkl")
#         ]

#     def __len__(self):
#         return len(self.files)

#     def __getitem__(self, idx):
#         file_path = self.files[idx]
#         with open(file_path, "rb") as f:
#             traj = pickle.load(f)
#         if self.num_frames > 1:
#             traj = self._frame_stack_traj(traj)
#         return traj

#     def _frame_stack_traj(self, traj: Trajectory) -> Trajectory:
#         traj_len, *obs_shape = traj.obs.shape
#         stacked_obs = np.empty((traj_len, self.num_frames, *obs_shape), dtype=traj.obs.dtype)
#         zero_obs = np.zeros(obs_shape, dtype=traj.obs[0].dtype)
#         for i in range(traj_len):
#             for j in range(self.num_frames):
#                 idx = i - j
#                 if idx >= 0:
#                     stacked_obs[i, self.num_frames - 1 - j] = traj.obs[idx]
#                 else:
#                     stacked_obs[i, self.num_frames - 1 - j] = zero_obs
#         return Trajectory(obs=stacked_obs, acts=traj.acts, infos=None, terminal=True)


def pretrain(run_id: int, num_teams: int, port: int, device: str, num_frames: int, div_frac: float):
    register_env("showdown", ShowdownEnv.create_env)
    # dataset = TrajectoryDataset(num_frames)
    # div_count = 10
    # dataloader = DataLoader(
    #     dataset,
    #     batch_size=len(dataset) // div_count,
    #     shuffle=True,
    #     num_workers=1,
    #     collate_fn=lambda batch: batch,
    # )
    config = BCConfig()
    config.environment(
        "showdown",
        env_config={
            "teams": [0],
            "port": port,
            "learning_style": LearningStyle.PURE_SELF_PLAY,
            "num_frames": num_frames,
        },
        observation_space=Box(-1, len(moves), shape=(12 * chunk_obs_len,), dtype=np.float32),
        action_space=MultiDiscrete([act_len, act_len]),
        disable_env_checking=True,
    )
    config.evaluation(evaluation_interval=None)
    config.offline_data(input_="data/episodes", dataset_num_iters_per_learner=1)
    config.rl_module(
        rl_module_spec=RLModuleSpec(
            module_class=ActorCriticModule,
            observation_space=Box(-1, len(moves), shape=(12 * chunk_obs_len,), dtype=np.float32),
            action_space=MultiDiscrete([act_len, act_len]),
            model_config={"num_frames": num_frames, "chooses_on_teampreview": True},
        )
    )
    algo = config.build_algo()
    eval_agent = PolicyPlayer(
        device,
        server_configuration=ServerConfiguration(
            f"ws://localhost:{port}/showdown/websocket",
            "https://play.pokemonshowdown.com/action.php?",
        ),
        battle_format=battle_format,
        log_level=40,
        max_concurrent_battles=10,
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
        max_concurrent_battles=10,
        accept_open_team_sheet=True,
        team=RandomTeamBuilder(list(range(num_teams)), battle_format),
    )
    for i in range(1000):
        # policy = algo.get_module("p1")
        # assert isinstance(policy, TorchRLModule)
        # eval_agent.set_policy(policy)
        # win_rate = compare(eval_agent, eval_opponent, 100)
        # algo.logger.record("bc/eval", win_rate)
        # algo.save(
        #     os.path.abspath(f"results/saves-bc{f'-fs{num_frames}' if num_frames > 1 else ''}/{i}")
        # )
        for _ in range(10):
            algo.train()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pretrain a policy using behavior cloning")
    parser.add_argument(
        "--num_frames",
        type=int,
        default=1,
        help="number of frames to use for frame stacking, default is 1 (no frame stacking)",
    )
    parser.add_argument(
        "--div_frac",
        type=float,
        default=0.01,
        help="fraction of total dataset to load at a given time during training (must be <1 when dataset is large)",
    )
    parser.add_argument("--run_id", type=int, default=1, help="run ID for the training session")
    parser.add_argument("--num_teams", type=int, default=2, help="number of teams to train with")
    parser.add_argument("--port", type=int, default=8000, help="port to run showdown server on")
    parser.add_argument("--device", type=str, default="cuda:0", help="device to use for training")
    args = parser.parse_args()
    set_global_seed(args.run_id)
    pretrain(args.run_id, args.num_teams, args.port, args.device, args.num_frames, args.div_frac)
