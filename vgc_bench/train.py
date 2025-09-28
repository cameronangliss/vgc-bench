import argparse
import os
import random

import numpy as np
import torch
from gymnasium.spaces import Box, MultiDiscrete
from poke_env.player import MaxBasePowerPlayer
from poke_env.ps_client import ServerConfiguration
from ray.rllib.algorithms import PPOConfig
from ray.rllib.core.rl_module import RLModuleSpec
from ray.tune.logger import UnifiedLogger
from ray.tune.registry import register_env
from src.env import ShowdownEnv
from src.policy import ActorCriticModule
from src.policy_player import PolicyPlayer
from src.teams import TEAMS, RandomTeamBuilder, TeamToggle
from src.utils import (
    LearningStyle,
    act_len,
    battle_format,
    chunk_obs_len,
    compare,
    moves,
    set_global_seed,
)


def train(
    run_id: int,
    num_teams: int,
    num_envs: int,
    port: int,
    device: str,
    learning_style: LearningStyle,
    behavior_clone: bool,
    num_frames: int,
    allow_mirror_match: bool,
    chooses_on_teampreview: bool,
):
    register_env("showdown", ShowdownEnv.create_env)
    gather_period = 10_000
    save_period = 100_000
    config = PPOConfig()
    teams = list(range(len(TEAMS[battle_format[-4:]])))
    random.Random(run_id).shuffle(teams)
    config = config.environment(
        "showdown",
        env_config={
            "run_id": run_id,
            "num_teams": num_teams,
            "port": port,
            "num_frames": num_frames,
            "allow_mirror_match": allow_mirror_match,
            "chooses_on_teampreview": chooses_on_teampreview,
        },
        disable_env_checking=True,
    )
    config = config.env_runners(num_env_runners=num_envs)
    config = config.learners(num_learners=1, num_gpus_per_learner=1, local_gpu_idx=int(device[-1]))
    num_policies = 2
    policy_names = [f"p{i}" for i in range(num_policies)]
    config = config.multi_agent(
        policies=policy_names,
        policy_mapping_fn=lambda agent_id, ep_type: policy_names[int(agent_id[-1])],
        policies_to_train=policy_names,
    )
    config = config.rl_module(
        rl_module_spec=RLModuleSpec(
            module_class=ActorCriticModule,
            observation_space=Box(-1, len(moves), shape=(12 * chunk_obs_len,), dtype=np.float32),
            action_space=MultiDiscrete([act_len, act_len]),
            model_config={
                "num_frames": num_frames,
                "chooses_on_teampreview": chooses_on_teampreview,
            },
        )
    )
    config = config.training(
        gamma=1, lr=1e-5, train_batch_size=gather_period, num_epochs=10, minibatch_size=200
    )
    run_ident = "".join(
        [
            "-bc" if behavior_clone else "",
            "-" + learning_style.abbrev,
            f"-fs{num_frames}" if num_frames > 1 else "",
            "-xm" if not allow_mirror_match else "",
            "-xt" if not chooses_on_teampreview else "",
        ]
    )[1:]
    log_dir = f"results/logs-{run_ident}/{num_teams}-teams/"
    save_dir = f"results/saves-{run_ident}/{num_teams}-teams"
    os.makedirs(save_dir, exist_ok=True)
    algo = config.build_algo(logger_creator=lambda config: UnifiedLogger(config, log_dir))  # type: ignore
    toggle = None if allow_mirror_match else TeamToggle(num_teams)
    eval_agent1 = PolicyPlayer(
        device,
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
    eval_agent2 = MaxBasePowerPlayer(
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
    # num_saved_steps = 0
    # if os.path.exists(save_dir) and len(os.listdir(save_dir)) > 0:
    #     saved_steps_list = [int(file[:-3]) for file in os.listdir(save_dir) if int(file[:-3]) >= 0]
    #     if saved_steps_list:
    #         num_saved_steps = max(saved_steps_list)
    #         module = algo.get_module("p1")
    #         assert isinstance(module, ActorCriticModule)
    #         state = torch.load(f"{save_dir}/{num_saved_steps}.pt")
    #         module.model.load_state_dict(state)
    #         if num_saved_steps < save_period:
    #             num_saved_steps = 0
    #         algo._iteration = num_saved_steps // gather_period
    # if gather_period * algo.training_iteration < save_period:
    #     policy = algo.get_module("p1")
    #     assert isinstance(policy, ActorCriticModule)
    #     eval_agent1.set_policy(policy)
    #     win_rate = compare(eval_agent1, eval_agent2, n_battles=100)
    # if not behavior_clone:
    #     module = algo.get_module("p1")
    #     assert isinstance(module, ActorCriticModule)
    #     torch.save(
    #         module.model.state_dict(), f"{save_dir}/{gather_period * algo.training_iteration}.pt"
    #     )
    # else:
    #     try:
    #         saves = [int(file[:-3]) for file in os.listdir(save_dir) if int(file[:-3]) >= 0]
    #     except FileNotFoundError:
    #         raise FileNotFoundError("behavior_clone on, but no model initialization found")
    #     assert len(saves) > 0
    # if learning_style == LearningStyle.EXPLOITER:
    #     algo.add_module(
    #         "target",
    #         RLModuleSpec(
    #             module_class=ActorCriticModule,
    #             observation_space=Box(
    #                 -1, len(moves), shape=(12 * chunk_obs_len,), dtype=np.float32
    #             ),
    #             action_space=MultiDiscrete([act_len, act_len]),
    #             model_config={
    #                 "num_frames": num_frames,
    #                 "chooses_on_teampreview": chooses_on_teampreview,
    #             },
    #         ),
    #     )
    #     module = algo.get_module("target")
    #     assert isinstance(module, ActorCriticModule)
    #     state = torch.load(f"{save_dir}/-1.pt")
    #     module.model.load_state_dict(state)
    while True:
        for _ in range(10):
            algo.train()
        win_rates = []
        for name in policy_names:
            policy = algo.get_module(name)
            assert isinstance(policy, ActorCriticModule)
            eval_agent1.policy = policy
            win_rate = compare(eval_agent1, eval_agent2, n_battles=100)
            win_rates += [win_rate]
        print(win_rates, flush=True)
        module = algo.get_module("p1")
        assert isinstance(module, ActorCriticModule)
        torch.save(
            module.model.state_dict(), f"{save_dir}/{gather_period * algo.training_iteration}.pt"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train a policy using population-based reinforcement learning. Must choose EXACTLY ONE of exploiter, self_play, fictitious_play, or double_oracle options."
    )
    parser.add_argument(
        "--exploiter",
        action="store_true",
        help="train against fixed policy, requires fixed policy file to be placed in save folder as -1.zip prior to training",
    )
    parser.add_argument(
        "--self_play",
        action="store_true",
        help="p1 and p2 are both controlled by same learning policy",
    )
    parser.add_argument(
        "--fictitious_play",
        action="store_true",
        help="p1 controlled by learning policy, p2 controlled by a past saved policy",
    )
    parser.add_argument(
        "--double_oracle",
        action="store_true",
        help="p1 controlled by learning policy, p2 controlled by past saved policy with selection weighted based on computed Nash equilibrium",
    )
    parser.add_argument(
        "--behavior_clone",
        action="store_true",
        help="use bc model as initial policy, requires bc model to be placed in save folder prior to training",
    )
    parser.add_argument(
        "--num_frames",
        type=int,
        default=1,
        help="number of frames to use for frame stacking, default is 1 (no frame stacking)",
    )
    parser.add_argument(
        "--no_mirror_match",
        action="store_true",
        help="disables same-team matchups during training, requires num_teams > 1",
    )
    parser.add_argument(
        "--no_teampreview",
        action="store_true",
        help="training agents will effectively start games after teampreview, with teampreview decision selected randomly",
    )
    parser.add_argument("--run_id", type=int, default=1, help="run ID for the training session")
    parser.add_argument("--num_teams", type=int, default=2, help="number of teams to train with")
    parser.add_argument("--num_envs", type=int, default=1, help="number of parallel envs to run")
    parser.add_argument("--port", type=int, default=8000, help="port to run showdown server on")
    parser.add_argument("--device", type=str, default="cuda:0", help="device to use for training")
    args = parser.parse_args()
    set_global_seed(args.run_id)
    assert (
        int(args.exploiter)
        + int(args.self_play)
        + int(args.fictitious_play)
        + int(args.double_oracle)
        == 1
    )
    if args.exploiter:
        style = LearningStyle.EXPLOITER
    elif args.self_play:
        style = LearningStyle.PURE_SELF_PLAY
    elif args.fictitious_play:
        style = LearningStyle.FICTITIOUS_PLAY
    elif args.double_oracle:
        style = LearningStyle.DOUBLE_ORACLE
    else:
        raise TypeError()
    train(
        args.run_id,
        args.num_teams,
        args.num_envs,
        args.port,
        args.device,
        style,
        args.behavior_clone,
        args.num_frames,
        not args.no_mirror_match,
        not args.no_teampreview,
    )
