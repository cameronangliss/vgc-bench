import argparse
import asyncio

import numpy as np
import torch
from gymnasium.spaces import Box, MultiDiscrete
from poke_env.ps_client import AccountConfiguration, ShowdownServerConfiguration
from src.agent import Agent
from src.policy import ActorCriticModule
from src.teams import RandomTeamBuilder
from src.utils import battle_format, doubles_act_len, doubles_chunk_obs_len, moves


async def play(filepath: str, n_games: int, play_on_ladder: bool):
    print("Setting up...")
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
        team=RandomTeamBuilder([0], battle_format),
    )
    policy = ActorCriticModule(
        observation_space=Box(
            -1, len(moves), shape=(12 * doubles_chunk_obs_len,), dtype=np.float32
        ),
        action_space=MultiDiscrete([doubles_act_len, doubles_act_len]),
        inference_only=True,
        model_config={"num_frames": 1, "chooses_on_teampreview": True},
        catalog_class=None,
    )
    state = torch.load(filepath)
    policy.model.load_state_dict(state)
    agent.set_policy(policy)
    if play_on_ladder:
        print("Entering ladder")
        await agent.ladder(n_games=n_games)
        print(f"{agent.n_won_battles}-{agent.n_lost_battles}-{agent.n_tied_battles}")
    else:
        print("AI is ready")
        await agent.accept_challenges(opponent=None, n_challenges=n_games)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--filepath", type=str, help="Filepath of save to play against")
    parser.add_argument("-n", type=int, default=1, help="Number of games to play. Default is 1.")
    parser.add_argument("-l", action="store_true", help="Play ladder. Default accepts challenges.")
    args = parser.parse_args()
    asyncio.run(play(args.filepath, args.n, args.l))
