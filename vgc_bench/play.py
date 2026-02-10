"""
Interactive play module for VGC-Bench.

Allows a trained policy to play games on Pokemon Showdown, either by
accepting challenges or playing on the ranked ladder.
"""

import argparse
import asyncio
from pathlib import Path

from poke_env import AccountConfiguration, ShowdownServerConfiguration
from stable_baselines3 import PPO

from vgc_bench.src.policy import MaskedActorCriticPolicy
from vgc_bench.src.policy_player import PolicyPlayer
from vgc_bench.src.teams import RandomTeamBuilder
from vgc_bench.src.utils import format_map


async def play(
    battle_format: str, run_id: int, num_teams: int, n_games: int, play_on_ladder: bool
):
    """
    Run the trained policy in interactive play mode.

    Loads a trained model and either enters the Pokemon Showdown ladder
    or waits to accept challenges from other players.

    Args:
        battle_format: Pokemon Showdown battle format string.
        run_id: Training run identifier for loading the model.
        num_teams: Number of teams the model was trained with.
        n_games: Number of games to play.
        play_on_ladder: If True, play on ladder; if False, accept challenges.
    """
    print("Setting up...")
    path = Path(f"results{run_id}/saves-sp/{num_teams}-teams")
    agent = PolicyPlayer(
        account_configuration=AccountConfiguration("", ""),  # fill in
        battle_format=battle_format,
        log_level=40,
        max_concurrent_battles=10,
        server_configuration=ShowdownServerConfiguration,
        accept_open_team_sheet=True,
        start_timer_on_battle_start=play_on_ladder,
        team=RandomTeamBuilder(run_id, num_teams, battle_format),
    )
    filepath = sorted(path.iterdir(), key=lambda p: int(p.stem))[-1]
    agent.policy = PPO.load(filepath, device="cuda:0").policy
    assert isinstance(agent.policy, MaskedActorCriticPolicy)
    agent.policy.debug = True
    print(f"Loaded model from {filepath}")
    if play_on_ladder:
        print("Entering ladder")
        await agent.ladder(n_games=n_games)
        print(f"{agent.n_won_battles}-{agent.n_lost_battles}-{agent.n_tied_battles}")
    else:
        print("Awaiting challenges")
        await agent.accept_challenges(opponent=None, n_challenges=n_games)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reg", type=str, required=True, help="VGC regulation to play in, i.e. G"
    )
    parser.add_argument(
        "--run_id", type=int, required=True, help="AI's ID from its training run"
    )
    parser.add_argument(
        "--num_teams", type=int, default=1, help="Number of teams AI was trained with"
    )
    parser.add_argument(
        "-n", type=int, default=1, help="Number of games to play. Default is 1."
    )
    parser.add_argument(
        "-l", action="store_true", help="Play ladder. Default accepts challenges."
    )
    args = parser.parse_args()
    battle_format = format_map[args.reg.lower()]
    asyncio.run(play(battle_format, args.run_id, args.num_teams, args.n, args.l))
