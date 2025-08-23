import argparse
import asyncio
import os
import random

import torch
from poke_env import AccountConfiguration, ShowdownServerConfiguration
from src.agent import Agent
from src.teams import TEAMS, RandomTeamBuilder
from src.utils import battle_format
from stable_baselines3 import PPO


async def play(run_id: int, num_teams: int, n_games: int, play_on_ladder: bool):
    print("Setting up...")
    path = f"results{run_id}/saves-sp/{num_teams}-teams"
    team_ids = list(range(len(TEAMS[battle_format[-4:]])))
    random.Random(run_id).shuffle(team_ids)
    agent = Agent(
        num_frames=1,
        device=torch.device("cuda:0"),
        account_configuration=AccountConfiguration("", ""),  # fill in
        battle_format=battle_format,
        log_level=40,
        max_concurrent_battles=10,
        server_configuration=ShowdownServerConfiguration,
        accept_open_team_sheet=True,
        start_timer_on_battle_start=play_on_ladder,
        team=RandomTeamBuilder(team_ids[:num_teams], battle_format),
    )
    agent.set_policy(PPO.load(f"{path}/{os.listdir(path)[-1]}").policy)
    if play_on_ladder:
        print("Entering ladder")
        await agent.ladder(n_games=n_games)
        print(f"{agent.n_won_battles}-{agent.n_lost_battles}-{agent.n_tied_battles}")
    else:
        print("AI is ready")
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
