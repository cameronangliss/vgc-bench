import argparse

import numpy as np
from gymnasium.spaces import Box, MultiDiscrete
from ray.rllib.algorithms import PPOConfig
from ray.rllib.core.rl_module import RLModuleSpec
from ray.tune.registry import register_env
from src.env import ShowdownEnv
from ray.tune.logger import UnifiedLogger
from src.policy import ActorCriticModule
from src.utils import (
    LearningStyle,
    allow_mirror_match,
    chooses_on_teampreview,
    doubles_act_len,
    doubles_chunk_obs_len,
    moves,
    num_envs,
    steps,
)


def train(
    teams: list[int],
    port: int,
    device: str,
    learning_style: LearningStyle,
    behavior_clone: bool,
    num_frames: int,
):
    register_env("showdown", ShowdownEnv.create_env)
    config = PPOConfig()
    config.environment(
        "showdown",
        env_config={
            "teams": teams,
            "port": port,
            "device": device,
            "learning_style": learning_style,
            "num_frames": num_frames,
        },
        disable_env_checking=True,
    )
    config.multi_agent(
        policies={"p1", "p2"},
        policy_mapping_fn=lambda agent_id, _: ("p1" if agent_id.startswith("player_0") else "p2"),
        policies_to_train=["p1", "p2"],
    )
    config.rl_module(
        rl_module_spec=RLModuleSpec(
            module_class=ActorCriticModule,
            observation_space=Box(
                -1, len(moves), shape=(12 * doubles_chunk_obs_len,), dtype=np.float32
            ),
            action_space=MultiDiscrete([doubles_act_len, doubles_act_len]),
            model_config={
                "num_frames": num_frames,
                "chooses_on_teampreview": chooses_on_teampreview,
            },
        )
    )
    config.training(
        use_critic=True,
        use_gae=True,
        lr=1e-5,
        gamma=1.0,
        train_batch_size_per_learner=3072,
        minibatch_size=64,
        num_epochs=10,
    )
    config.learners(num_learners=1, num_gpus_per_learner=1, local_gpu_idx=int(device[-1]))
    config.env_runners(num_env_runners=num_envs)
    run_ident = "".join(
        [
            "-bc" if behavior_clone else "",
            f"-fs{num_frames}" if num_frames > 1 else "",
            "-" + learning_style.abbrev,
            "-xm" if not allow_mirror_match else "",
        ]
    )[1:]
    algo = config.build_algo(
        logger_creator=lambda config: UnifiedLogger(  # type: ignore
            config,
            f"results/logs-{run_ident}/{','.join([str(t) for t in teams])}-teams/",
            loggers=None,
        )
    )
    for _ in range(steps):
        algo.train()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train a Pokémon AI model")
    parser.add_argument("--teams", nargs="+", type=int, help="Indices of teams to train with")
    parser.add_argument("--num_teams", type=int, help="Number of teams to train with")
    parser.add_argument("--port", type=int, default=8000, help="Port to run showdown server on")
    parser.add_argument(
        "--device",
        type=str,
        default="cuda:0",
        choices=["cuda:0", "cuda:1", "cuda:2", "cuda:3"],
        help="CUDA device to use for training",
    )
    parser.add_argument("--exploiter", action="store_true", help="play against fixed bot")
    parser.add_argument("--self_play", action="store_true", help="do pure self-play")
    parser.add_argument("--last_self", action="store_true", help="do last-self play")
    parser.add_argument("--fictitious_play", action="store_true", help="do fictitious play")
    parser.add_argument("--double_oracle", action="store_true", help="do double oracle")
    parser.add_argument(
        "--behavior_clone", action="store_true", help="Warm up with behavior cloning"
    )
    parser.add_argument(
        "--num_frames",
        type=int,
        default=1,
        help="number of frames to use for frame stacking. default is 1",
    )
    args = parser.parse_args()
    assert (args.teams is None) != (
        args.num_teams is None
    ), "Only pass one of --teams and --num_teams in"
    assert (
        int(args.exploiter)
        + int(args.self_play)
        + int(args.last_self)
        + int(args.fictitious_play)
        + int(args.double_oracle)
        == 1
    )
    teams = args.teams if args.teams is not None else list(range(args.num_teams))
    if args.exploiter:
        style = LearningStyle.EXPLOITER
    elif args.self_play:
        style = LearningStyle.PURE_SELF_PLAY
    elif args.last_self:
        style = LearningStyle.LAST_SELF
    elif args.fictitious_play:
        style = LearningStyle.FICTITIOUS_PLAY
    elif args.double_oracle:
        style = LearningStyle.DOUBLE_ORACLE
    else:
        raise TypeError()
    train(teams, args.port, args.device, style, args.behavior_clone, args.num_frames)
