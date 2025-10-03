import argparse
import asyncio
import os
import random

import numpy as np
import torch
from gymnasium.spaces import Box, MultiDiscrete
from poke_env.ps_client import AccountConfiguration, ShowdownServerConfiguration
from src.policy import ActorCriticModule
from src.policy_player import PolicyPlayer
from src.teams import TEAMS, RandomTeamBuilder
from src.utils import act_len, battle_format, chunk_obs_len, moves


async def play(run_id: int, num_teams: int, n_games: int, play_on_ladder: bool):
    print("Setting up...")
    path = f"results{run_id}/saves-sp/{num_teams}-teams"
    team_ids = list(range(len(TEAMS[battle_format[-4:]])))
    random.Random(run_id).shuffle(team_ids)
    agent = PolicyPlayer(
        "cuda:0",
        account_configuration=AccountConfiguration("", ""),  # fill in
        battle_format=battle_format,
        log_level=40,
        max_concurrent_battles=10,
        server_configuration=ShowdownServerConfiguration,
        accept_open_team_sheet=True,
        start_timer_on_battle_start=play_on_ladder,
        team=RandomTeamBuilder(team_ids[:num_teams], battle_format),
    )
    policy = ActorCriticModule(
        observation_space=Box(-1, len(moves), shape=(12 * chunk_obs_len,), dtype=np.float32),
        action_space=MultiDiscrete([act_len, act_len]),
        inference_only=True,
        model_config={"num_frames": 1, "chooses_on_teampreview": True},
        catalog_class=None,
    )
    file = os.listdir(path)[-1]
    state = torch.load(f"{path}/{file}")
    policy.model.load_state_dict(state)
    agent.policy = policy.to("cuda:0")
    if play_on_ladder:
        print("Entering ladder")
        await agent.ladder(n_games=n_games)
        print(f"{agent.n_won_battles}-{agent.n_lost_battles}-{agent.n_tied_battles}")
    else:
        print("Awaiting challenges")
        print(TEAMS[battle_format[-4:]][random.choice(team_ids[:num_teams])])
        await agent.accept_challenges(opponent=None, n_challenges=n_games)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", type=int, required=True, help="AI's ID from its training run")
    parser.add_argument(
        "--num_teams", type=int, default=1, help="Number of teams AI was trained with"
    )
    parser.add_argument("-n", type=int, default=1, help="Number of games to play. Default is 1.")
    parser.add_argument("-l", action="store_true", help="Play ladder. Default accepts challenges.")
    args = parser.parse_args()
    asyncio.run(play(args.run_id, args.num_teams, args.n, args.l))
