import argparse
import os

import numpy as np
import torch
from gymnasium.spaces import Box, MultiDiscrete
from poke_env.player import MaxBasePowerPlayer
from poke_env.ps_client import ServerConfiguration
from ray.rllib.algorithms import PPOConfig
from ray.rllib.core.rl_module import RLModuleSpec
from ray.tune.logger import TBXLogger, UnifiedLogger
from ray.tune.registry import register_env
from src.agent import Agent
from src.env import ShowdownEnv
from src.policy import ActorCriticModule
from src.teams import RandomTeamBuilder, TeamToggle
from src.utils import (
    LearningStyle,
    allow_mirror_match,
    battle_format,
    chooses_on_teampreview,
    compare,
    doubles_act_len,
    doubles_chunk_obs_len,
    moves,
)


class FilteredTBXLogger(TBXLogger):
    def on_result(self, result):
        result.get("env_runners", {}).pop("agent_episode_returns_mean", None)
        result.get("env_runners", {}).pop("agent_steps", None)
        result.get("env_runners", {}).pop("num_agent_steps_sampled", None)
        result.get("env_runners", {}).pop("num_agent_steps_sampled_lifetime", None)
        super().on_result(result)


def train(
    teams: list[int],
    port: int,
    device: str,
    learning_style: LearningStyle,
    behavior_clone: bool,
    num_frames: int,
):
    register_env("showdown", ShowdownEnv.create_env)
    gather_period = 10_000
    save_period = 100_000
    config = PPOConfig()
    config = config.environment(
        "showdown",
        env_config={
            "teams": teams,
            "port": port,
            "learning_style": learning_style,
            "num_frames": num_frames,
        },
        disable_env_checking=True,
    )
    config = config.env_runners(num_env_runners=24)
    config = config.learners(num_learners=1, num_gpus_per_learner=1, local_gpu_idx=int(device[-1]))
    config = config.multi_agent(
        policies={"p1"}, policy_mapping_fn=lambda agent_id, ep_type: "p1", policies_to_train=["p1"]
    )
    config = config.rl_module(
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
    config = config.training(
        gamma=1, lr=1e-5, train_batch_size=gather_period, num_epochs=10, minibatch_size=200
    )
    run_ident = "".join(
        [
            "-bc" if behavior_clone else "",
            f"-fs{num_frames}" if num_frames > 1 else "",
            "-" + learning_style.abbrev,
            "-xm" if not allow_mirror_match else "",
        ]
    )[1:]
    log_dir = f"results/logs-{run_ident}/{','.join([str(t) for t in teams])}-teams/"
    save_dir = f"results/saves-{run_ident}/{','.join([str(t) for t in teams])}-teams"
    os.makedirs(save_dir, exist_ok=True)
    algo = config.build_algo(
        logger_creator=lambda config: UnifiedLogger(  # type: ignore
            config, log_dir, loggers=[FilteredTBXLogger]
        )
    )
    toggle = None if allow_mirror_match else TeamToggle(len(teams))
    eval_agent1 = Agent(
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
    num_saved_steps = 0
    if os.path.exists(save_dir) and len(os.listdir(save_dir)) > 0:
        saved_steps_list = [int(file[:-3]) for file in os.listdir(save_dir) if int(file[:-3]) >= 0]
        if saved_steps_list:
            num_saved_steps = max(saved_steps_list)
            module = algo.get_module("p1")
            assert isinstance(module, ActorCriticModule)
            state = torch.load(f"{save_dir}/{num_saved_steps}.pt")
            module.model.load_state_dict(state)
            if num_saved_steps < save_period:
                num_saved_steps = 0
            algo._iteration = num_saved_steps // gather_period
    if gather_period * algo.training_iteration < save_period:
        policy = algo.get_module("p1")
        assert isinstance(policy, ActorCriticModule)
        eval_agent1.set_policy(policy)
        win_rate = compare(eval_agent1, eval_agent2, n_battles=100)
    if not behavior_clone:
        module = algo.get_module("p1")
        assert isinstance(module, ActorCriticModule)
        torch.save(
            module.model.state_dict(), f"{save_dir}/{gather_period * algo.training_iteration}.pt"
        )
    else:
        try:
            saves = [int(file[:-3]) for file in os.listdir(save_dir) if int(file[:-3]) >= 0]
        except FileNotFoundError:
            raise FileNotFoundError("behavior_clone on, but no model initialization found")
        assert len(saves) > 0
    if learning_style == LearningStyle.EXPLOITER:
        algo.add_module(
            "target",
            RLModuleSpec(
                module_class=ActorCriticModule,
                observation_space=Box(
                    -1, len(moves), shape=(12 * doubles_chunk_obs_len,), dtype=np.float32
                ),
                action_space=MultiDiscrete([doubles_act_len, doubles_act_len]),
                model_config={
                    "num_frames": num_frames,
                    "chooses_on_teampreview": chooses_on_teampreview,
                },
            ),
        )
        module = algo.get_module("target")
        assert isinstance(module, ActorCriticModule)
        state = torch.load(f"{save_dir}/-1.pt")
        module.model.load_state_dict(state)
    for _ in range(10):
        algo.train()
    policy = algo.get_module("p1")
    assert isinstance(policy, ActorCriticModule)
    eval_agent1.set_policy(policy)
    win_rate = compare(eval_agent1, eval_agent2, n_battles=100)
    module = algo.get_module("p1")
    assert isinstance(module, ActorCriticModule)
    torch.save(
        module.model.state_dict(), f"{save_dir}/{gather_period * algo.training_iteration}.pt"
    )


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
