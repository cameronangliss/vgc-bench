import argparse
import asyncio
import random

import numpy as np
import torch
from open_spiel.python.egt import alpharank
from poke_env.player import MaxBasePowerPlayer, Player, RandomPlayer, SimpleHeuristicsPlayer
from poke_env.ps_client import AccountConfiguration, ServerConfiguration
from src.agent import Agent
from src.llm import LLMPlayer
from src.teams import RandomTeamBuilder
from src.utils import battle_format
from stable_baselines3 import PPO


def eval(teams: list[int], port: int, device: str):
    player_groups = []
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
        player_groups += [[player]]
    llm_player = LLMPlayer(
        device=device,
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
    bcs = [41, 20, 22, 12, 14]
    for name in ["sp", "fp", "do", "bc", "bc-sp", "bc-fp", "bc-do"]:
        agents = []
        for i in range(5):
            step = bcs[i] if name == "bc" else 5013504
            agent = Agent(
                num_frames=1,
                device=torch.device(device),
                account_configuration=AccountConfiguration(f"{name} {i + 1}", None),
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
            teams_str = ",".join([str(t) for t in teams]) + "-teams/"
            if name == "bc":
                teams_str = ""
            agent.set_policy(
                PPO.load(f"results-final{i + 1}/saves-{name}/{teams_str}{step}").policy
            )
            agents += [agent]
        player_groups += [agents]
    results = asyncio.run(mixed_policy_cross_evaluate(player_groups, 1000))
    llm_results = asyncio.run(mixed_policy_battle_against([llm_player], player_groups, 100))
    llm_wins = [r[0] for r in llm_results.values()]
    llm_losses = [r[1] for r in llm_results.values()]
    llm_losses = llm_losses[:3] + [0] + llm_losses[3:]
    payoff_matrix = np.array(
        [[r if r is not None else 0.5 for r in result.values()] for result in results.values()]
    )
    payoff_matrix = np.insert(payoff_matrix, 3, llm_wins, axis=0)
    payoff_matrix = np.insert(payoff_matrix, 3, llm_losses, axis=1)
    print(payoff_matrix)
    ranking = alpharank.compute([payoff_matrix], use_inf_alpha=True)[2]
    print(ranking)


async def mixed_policy_cross_evaluate(
    player_groups: list[list[Player]], num_battles: int
) -> dict[str, dict[str, float | None]]:
    results: dict[str, dict[str, float | None]] = {
        players1[0].username[:-2]: {players2[0].username[:-2]: None for players2 in player_groups}
        for players1 in player_groups
    }
    for i, players1 in enumerate(player_groups):
        p1_name = players1[0].username[:-2]
        r = await mixed_policy_battle_against(players1, player_groups[i + 1 :], num_battles)
        for p2_name, (p1_num_wins, p2_num_wins) in r.items():
            results[p1_name][p2_name] = p1_num_wins
            results[p2_name][p1_name] = p2_num_wins
    return results


async def mixed_policy_battle_against(
    players: list[Player], player_groups: list[list[Player]], num_battles: int
) -> dict[str, tuple[float, float]]:
    results = {}
    for players2 in player_groups:
        p2_name = players2[0].username[:-2]
        p1_num_wins = 0
        p2_num_wins = 0
        for _ in range(num_battles):
            player1 = random.choice(players)
            player2 = random.choice(players2)
            await player1.battle_against(player2)
            p1_num_wins += player1.n_won_battles
            p2_num_wins += player2.n_won_battles
            player1.reset_battles()
            player2.reset_battles()
        results[p2_name] = (p1_num_wins / num_battles, p2_num_wins / num_battles)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate a Pokémon AI model")
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
    args = parser.parse_args()
    assert (args.teams is None) != (
        args.num_teams is None
    ), "Only pass one of --teams and --num_teams in"
    teams = args.teams if args.teams is not None else list(range(args.num_teams))
    eval(teams, args.port, args.device)
