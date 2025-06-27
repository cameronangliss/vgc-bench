import argparse
import asyncio

import numpy as np
import torch
from poke_env import cross_evaluate
from poke_env.player import MaxBasePowerPlayer, RandomPlayer, SimpleHeuristicsPlayer
from poke_env.ps_client import AccountConfiguration, ServerConfiguration
from src.agent import Agent
from src.llm import LLMPlayer
from src.teams import RandomTeamBuilder
from src.utils import battle_format
from stable_baselines3 import PPO


def eval(teams: list[int], port: int):
    players = []
    for cls_ in [RandomPlayer, MaxBasePowerPlayer, SimpleHeuristicsPlayer]:
        player = cls_(
            server_configuration=ServerConfiguration(
                f"ws://localhost:{port}/showdown/websocket",
                "https://play.pokemonshowdown.com/action.php?",
            ),
            battle_format=battle_format,
            log_level=25,
            max_concurrent_battles=10,
            accept_open_team_sheet=True,
            open_timeout=None,
            team=RandomTeamBuilder(teams, battle_format),
        )
        players += [player]
    llm_player = LLMPlayer(
        device="cuda:0",
        server_configuration=ServerConfiguration(
            f"ws://localhost:{port}/showdown/websocket",
            "https://play.pokemonshowdown.com/action.php?",
        ),
        battle_format=battle_format,
        log_level=25,
        accept_open_team_sheet=True,
        open_timeout=None,
        team=RandomTeamBuilder(teams, battle_format),
    )
    players += [llm_player]
    agent_files = {
        "bc1": f"results/saves-bc-fp/0-teams/98304",
        # "bc3": f"results/saves-bc-fp/0,1,2-teams/98304",
        # "bc10": f"results/saves-bc-fp/0,1,2,3,4,5,6,7,8,9-teams/98304",
        # "bc30": f"results/saves-bc-fp/0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29-teams/98304",
    }
    for name, f in agent_files.items():
        agent = Agent(
            num_frames=1,
            device=torch.device("cuda:0"),
            account_configuration=AccountConfiguration(name, None),
            server_configuration=ServerConfiguration(
                f"ws://localhost:{port}/showdown/websocket",
                "https://play.pokemonshowdown.com/action.php?",
            ),
            battle_format=battle_format,
            log_level=25,
            max_concurrent_battles=10,
            accept_open_team_sheet=True,
            open_timeout=None,
            team=RandomTeamBuilder(teams, battle_format),
        )
        agent.set_policy(PPO.load(f).policy)
        players += [agent]
    results = asyncio.run(cross_evaluate(players, 100))
    payoff_matrix = np.array(
        [[r if r is not None else 0 for r in result.values()] for result in results.values()]
    )
    elos = wins_to_elos(payoff_matrix)
    print(payoff_matrix)
    print(elos)


def wins_to_elos(win_rates, base_elo=1500, min_elo=1000, scale_std=200):
    """
    Convert a symmetric matrix of win rates into Elo ratings.

    Parameters
    ----------
    win_rates : (n,n) array
        win_rates[i,j] is fraction of games player i won vs j (out of 1).
        Diagonal entries are ignored (e.g., zero).
    base_elo : float
        The mean Elo to center the ratings on.
    min_elo : float
        The minimum Elo after shifting.
    scale_std : float or None
        If not None, rescale so that resulting std of elos equals this.

    Returns
    -------
    elos : (n,) array
        Computed Elo ratings.
    """
    n = win_rates.shape[0]

    # Build equations A x = b for differences
    rows = []
    b = []
    for i in range(n):
        for j in range(n):
            s = win_rates[i, j]
            # only if result is strictly between 0 and 1
            if i != j and 0 < s < 1:
                # implied diff: R_i - R_j = D_ij
                D_ij = -400 * np.log10((1 / s) - 1)
                row = np.zeros(n)
                row[i] = 1
                row[j] = -1
                rows.append(row)
                b.append(D_ij)
    A = np.vstack(rows)
    b = np.array(b)

    # Add constraint: sum(R_i) = n * base_elo
    constraint = np.ones((1, n))
    A = np.vstack([A, constraint])
    b = np.concatenate([b, [n * base_elo]])

    # Solve least squares
    R, *_ = np.linalg.lstsq(A, b, rcond=None)

    # Optionally rescale so min equals min_elo
    shift = min_elo - np.min(R)
    R = R + shift

    # Optionally set standard deviation
    if scale_std is not None:
        R = (R - np.mean(R)) * (scale_std / np.std(R)) + np.mean(R)

    return R


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate a Pokémon AI model")
    parser.add_argument("--teams", nargs="+", type=int, help="Indices of teams to train with")
    parser.add_argument("--num_teams", type=int, help="Number of teams to train with")
    parser.add_argument("--port", type=int, default=8000, help="Port to run showdown server on")
    args = parser.parse_args()
    assert (args.teams is None) != (
        args.num_teams is None
    ), "Only pass one of --teams and --num_teams in"
    teams = args.teams if args.teams is not None else list(range(args.num_teams))
    eval(teams, args.port)
