"""
Training module for VGC-Bench.

Implements reinforcement learning training for Pokemon VGC agents using PPO.
Supports multiple training paradigms including self-play, fictitious play,
double oracle, and exploiter training, optionally initialized with behavior
cloning.
"""

import argparse
from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv

from vgc_bench.src.callback import Callback
from vgc_bench.src.env import ShowdownEnv
from vgc_bench.src.policy import MaskedActorCriticPolicy
from vgc_bench.src.utils import LearningStyle, format_map, set_global_seed


def train(
    battle_format: str,
    run_id: int,
    num_teams: int,
    num_envs: int,
    num_eval_workers: int,
    log_level: int,
    port: int,
    device: str,
    learning_style: LearningStyle,
    behavior_clone: bool,
    num_frames: int,
    allow_mirror_match: bool,
    chooses_on_teampreview: bool,
    team1: str | None,
    team2: str | None,
    results_suffix: str,
):
    """
    Train a Pokemon VGC policy using reinforcement learning.

    Creates the training environment, initializes PPO with the appropriate
    policy architecture, and runs training with periodic evaluation and
    checkpointing.

    Args:
        battle_format: Pokemon Showdown battle format string.
        run_id: Training run identifier for saving/loading.
        num_teams: Number of teams to train with.
        num_envs: Number of parallel environments.
        num_eval_workers: Number of workers for evaluation battles.
        log_level: Logging verbosity for Showdown clients.
        port: Port for the Pokemon Showdown server.
        device: CUDA device for training.
        learning_style: Training paradigm (self-play, fictitious play, etc.).
        behavior_clone: Whether to initialize from a BC-pretrained policy.
        num_frames: Number of frames for frame stacking.
        allow_mirror_match: Whether to allow same-team matchups.
        chooses_on_teampreview: Whether policy makes teampreview decisions.
        team1: Optional team string for matchup solving (requires team2).
        team2: Optional team string for matchup solving (requires team1).
        results_suffix: Suffix appended to results<run_id> for output paths.
    """
    save_interval = 98_304
    env = (
        ShowdownEnv.create_env(
            battle_format,
            run_id,
            num_teams,
            num_envs,
            log_level,
            port,
            learning_style,
            num_frames,
            allow_mirror_match,
            chooses_on_teampreview,
            team1,
            team2,
        )
        if learning_style == LearningStyle.PURE_SELF_PLAY
        else SubprocVecEnv(
            [
                lambda: ShowdownEnv.create_env(
                    battle_format,
                    run_id,
                    1 if learning_style == LearningStyle.EXPLOITER else num_teams,
                    num_envs,
                    log_level,
                    port,
                    learning_style,
                    num_frames,
                    allow_mirror_match,
                    chooses_on_teampreview,
                    team1,
                    team2,
                )
                for _ in range(num_envs)
            ]
        )
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
    suffix = f"-{results_suffix}" if results_suffix else ""
    output_dir = Path(f"results{run_id}{suffix}")
    save_dir = output_dir / f"saves-{run_ident}" / f"{num_teams}-teams"
    ppo = PPO(
        MaskedActorCriticPolicy,
        env,
        learning_rate=1e-5,
        n_steps=(
            3072 // (2 * num_envs)
            if learning_style == LearningStyle.PURE_SELF_PLAY
            else 3072 // num_envs
        ),
        batch_size=64,
        gamma=1,
        ent_coef=0.01,
        tensorboard_log=str(output_dir / f"logs-{run_ident}"),
        policy_kwargs={
            "d_model": 256,
            "num_frames": num_frames,
            "chooses_on_teampreview": chooses_on_teampreview,
        },
        device=device,
    )
    num_saved_timesteps = 0
    if save_dir.exists() and any(save_dir.iterdir()):
        saved_policy_timesteps = [
            int(file.stem) for file in save_dir.iterdir() if int(file.stem) >= 0
        ]
        if saved_policy_timesteps:
            num_saved_timesteps = max(saved_policy_timesteps)
            ppo.set_parameters(
                str(save_dir / f"{num_saved_timesteps}.zip"), device=ppo.device
            )
            if num_saved_timesteps < save_interval:
                num_saved_timesteps = 0
            ppo.num_timesteps = num_saved_timesteps
    ppo.learn(
        51 * save_interval - num_saved_timesteps,
        callback=Callback(
            run_id,
            num_teams,
            battle_format,
            num_eval_workers,
            log_level,
            port,
            learning_style,
            behavior_clone,
            num_frames,
            allow_mirror_match,
            chooses_on_teampreview,
            save_interval,
            team1,
            team2,
            results_suffix,
        ),
        tb_log_name=f"{num_teams}-teams",
        reset_num_timesteps=False,
    )
    env.close()


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
        help="use bc model as initial policy; if save folder has no checkpoint, downloads default BC checkpoint from Hugging Face",
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
    parser.add_argument(
        "--reg", type=str, required=True, help="VGC regulation to train on, i.e. G"
    )
    parser.add_argument(
        "--run_id", type=int, default=1, help="run ID for the training session"
    )
    parser.add_argument(
        "--team1", type=str, default="", help="team 1 string for matchup solving"
    )
    parser.add_argument(
        "--team2", type=str, default="", help="team 2 string for matchup solving"
    )
    parser.add_argument(
        "--results_suffix",
        type=str,
        default="",
        help="suffix appended to results<run_id> for output paths",
    )
    parser.add_argument(
        "--num_teams", type=int, default=2, help="number of teams to train with"
    )
    parser.add_argument(
        "--num_envs", type=int, default=1, help="number of parallel envs to run"
    )
    parser.add_argument(
        "--num_eval_workers", type=int, default=1, help="number of eval workers to run"
    )
    parser.add_argument(
        "--log_level", type=int, default=25, help="log level for showdown clients"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="port to run showdown server on"
    )
    parser.add_argument(
        "--device", type=str, default="cuda:0", help="device to use for training"
    )
    args = parser.parse_args()
    set_global_seed(args.run_id)
    battle_format = format_map[args.reg.lower()]
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
    if style == LearningStyle.EXPLOITER:
        assert (
            not args.no_mirror_match
        ), "--no_mirror_match is incompatible with --exploiter (exploiter uses a single team)"
    assert (args.team1 == "") == (
        args.team2 == ""
    ), "must provide both or neither of --team1 and --team2"
    if args.team1 != "":
        assert (
            args.results_suffix != ""
        ), "--results_suffix is required when using --team1 and --team2"
    train(
        battle_format,
        args.run_id,
        args.num_teams,
        args.num_envs,
        args.num_eval_workers,
        args.log_level,
        args.port,
        args.device,
        style,
        args.behavior_clone,
        args.num_frames,
        not args.no_mirror_match,
        not args.no_teampreview,
        args.team1 or None,
        args.team2 or None,
        args.results_suffix,
    )
