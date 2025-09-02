import argparse
import os

from src.callback import Callback
from src.env import ShowdownEnv
from src.policy import MaskedActorCriticPolicy
from src.utils import LearningStyle, save_interval
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv


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
    env = (
        ShowdownEnv.create_env(
            run_id,
            num_teams,
            num_envs,
            port,
            learning_style,
            num_frames,
            allow_mirror_match,
            chooses_on_teampreview,
        )
        if learning_style == LearningStyle.PURE_SELF_PLAY
        else SubprocVecEnv(
            [
                lambda: ShowdownEnv.create_env(
                    run_id,
                    1 if learning_style == LearningStyle.EXPLOITER else num_teams,
                    num_envs,
                    port,
                    learning_style,
                    num_frames,
                    allow_mirror_match,
                    chooses_on_teampreview,
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
        ent_coef=1e-3,
        tensorboard_log=f"results{run_id}/logs-{run_ident}",
        policy_kwargs={"num_frames": num_frames, "chooses_on_teampreview": chooses_on_teampreview},
        device=device,
    )
    num_saved_timesteps = 0
    if (
        os.path.exists(f"results{run_id}/saves-{run_ident}/{num_teams}-teams")
        and len(os.listdir(f"results{run_id}/saves-{run_ident}/{num_teams}-teams")) > 0
    ):
        saved_policy_timesteps = [
            int(file[:-4])
            for file in os.listdir(f"results{run_id}/saves-{run_ident}/{num_teams}-teams")
            if int(file[:-4]) >= 0
        ]
        if saved_policy_timesteps:
            num_saved_timesteps = max(saved_policy_timesteps)
            ppo.set_parameters(
                f"results{run_id}/saves-{run_ident}/{num_teams}-teams/{num_saved_timesteps}.zip",
                device=ppo.device,
            )
            if num_saved_timesteps < save_interval:
                num_saved_timesteps = 0
            ppo.num_timesteps = num_saved_timesteps
    ppo.learn(
        5_013_504 - num_saved_timesteps,
        callback=Callback(
            run_id,
            num_teams,
            port,
            learning_style,
            behavior_clone,
            num_frames,
            allow_mirror_match,
            chooses_on_teampreview,
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
