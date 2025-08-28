import argparse
import asyncio
import random
from statistics import mean, median

import numpy as np
from open_spiel.python.egt import alpharank
from poke_env import cross_evaluate
from poke_env.player import MaxBasePowerPlayer, RandomPlayer, SimpleHeuristicsPlayer
from poke_env.ps_client import AccountConfiguration, ServerConfiguration
from src.llm import LLMPlayer
from src.policy_player import PolicyPlayer
from src.teams import TEAMS, RandomTeamBuilder, calc_team_similarity_score
from src.utils import battle_format
from stable_baselines3 import PPO


def cross_eval_all_agents(
    num_teams: int, port: int, device: str, num_battles: int, num_llm_battles: int
):
    num_runs = 5
    avg_payoff_matrix = np.zeros((11, 11))
    for run_id in range(1, num_runs + 1):
        teams = list(range(len(TEAMS[battle_format[-4:]])))
        random.Random(run_id).shuffle(teams)
        players = [
            cls_(
                server_configuration=ServerConfiguration(
                    f"ws://localhost:{port}/showdown/websocket",
                    "https://play.pokemonshowdown.com/action.php?",
                ),
                battle_format=battle_format,
                log_level=25,
                max_concurrent_battles=10,
                accept_open_team_sheet=True,
                open_timeout=None,
                team=RandomTeamBuilder(teams[:num_teams], battle_format),
            )
            for cls_ in [RandomPlayer, MaxBasePowerPlayer, SimpleHeuristicsPlayer]
        ]
        llm_player = LLMPlayer(
            device=device,
            server_configuration=ServerConfiguration(
                f"ws://localhost:{port}/showdown/websocket",
                "https://play.pokemonshowdown.com/action.php?",
            ),
            battle_format=battle_format,
            log_level=25,
            max_concurrent_battles=10,
            accept_open_team_sheet=True,
            open_timeout=None,
            team=RandomTeamBuilder(teams[:num_teams], battle_format),
        )
        for name in ["sp", "fp", "do", "bc", "bc-sp", "bc-fp", "bc-do"]:
            step = 100 if name == "bc" else 5013504
            agent = PolicyPlayer(
                account_configuration=AccountConfiguration(f"{name} {run_id}", None),
                server_configuration=ServerConfiguration(
                    f"ws://localhost:{port}/showdown/websocket",
                    "https://play.pokemonshowdown.com/action.php?",
                ),
                battle_format=battle_format,
                log_level=25,
                max_concurrent_battles=10,
                accept_open_team_sheet=True,
                open_timeout=None,
                team=RandomTeamBuilder(teams[:num_teams], battle_format),
            )
            teams_str = f"{num_teams}-teams/"
            if name == "bc":
                teams_str = ""
            agent.policy = PPO.load(
                f"results{run_id}/saves-{name}/{teams_str}{step}", device=device
            ).policy
            players += [agent]
        results = asyncio.run(cross_evaluate(players, n_challenges=num_battles // num_runs))
        asyncio.run(llm_player.battle_against(*players, n_battles=num_llm_battles // num_runs))
        llm_wins = [p.n_lost_battles / p.n_finished_battles for p in players]
        llm_losses = [p.n_won_battles / p.n_finished_battles for p in players]
        for p in players + [llm_player]:
            p.reset_battles()
        llm_losses.insert(3, np.nan)
        payoff_matrix = np.array(
            [
                [r if r is not None else np.nan for r in result.values()]
                for result in results.values()
            ]
        )
        payoff_matrix = np.insert(payoff_matrix, 3, llm_wins, axis=0)
        payoff_matrix = np.insert(payoff_matrix, 3, llm_losses, axis=1)
        avg_payoff_matrix += payoff_matrix / num_runs
    print(f"Cross-agent comparison for {num_teams} teams:")
    print(avg_payoff_matrix.tolist())
    ranking = alpharank.compute([avg_payoff_matrix], use_inf_alpha=True)[2]
    print("AlphaRank pi values:", ranking.tolist())
    sim_scores = [
        max(
            [
                calc_team_similarity_score(
                    TEAMS[battle_format[-4:]][i], TEAMS[battle_format[-4:]][j]
                )
                for i in range(len(TEAMS[battle_format[-4:]]))
                if i != j
            ]
        )
        for j in range(len(TEAMS[battle_format[-4:]]))
    ]
    print(f"Overall team similarity statistics:")
    print("mean =", round(mean(sim_scores), ndigits=2))
    print("median =", round(median(sim_scores), ndigits=3))
    print("min =", min(sim_scores))
    print("max =", max(sim_scores))


def cross_eval_over_team_sizes(
    team_counts: list[int],
    methods: list[str],
    port: int,
    device: str,
    num_battles: int,
    is_performance_test: bool,
):
    # if is_performance_test is False, then this becomes the generalization test
    num_runs = 5
    avg_payoff_matrix = np.zeros((4, 4))
    for run_id in range(1, num_runs + 1):
        teams = list(range(len(TEAMS[battle_format[-4:]])))
        random.Random(run_id).shuffle(teams)
        agents = []
        for num_teams, method in zip(team_counts, methods):
            agent = PolicyPlayer(
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
                    teams[: min(team_counts)] if is_performance_test else teams[max(team_counts) :],
                    battle_format,
                ),
            )
            agent.policy = PPO.load(
                f"results{run_id}/saves-{method}/{num_teams}-teams/5013504", device=device
            ).policy
            agents += [agent]
        results = asyncio.run(cross_evaluate(agents, num_battles // num_runs))
        payoff_matrix = np.array(
            [
                [r if r is not None else np.nan for r in result.values()]
                for result in results.values()
            ]
        )
        avg_payoff_matrix += payoff_matrix / num_runs
        if not is_performance_test:
            sim_scores = [
                max(
                    [
                        calc_team_similarity_score(
                            TEAMS[battle_format[-4:]][i], TEAMS[battle_format[-4:]][j]
                        )
                        for i in teams[: max(team_counts)]
                    ]
                )
                for j in teams[max(team_counts) :]
            ]
            print(f"team similarity statistics for run #{run_id}:")
            print("mean =", round(mean(sim_scores), ndigits=2))
            print("median =", round(median(sim_scores), ndigits=3))
            print("min =", min(sim_scores))
            print("max =", max(sim_scores))
    print("Performance" if is_performance_test else "Generalization", "test results:")
    print(avg_payoff_matrix.tolist())
    ranking = alpharank.compute([avg_payoff_matrix], use_inf_alpha=True)[2]
    print("AlphaRank pi values:", ranking.tolist())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate a Pokémon AI model")
    parser.add_argument(
        "--num_teams", type=int, required=True, help="Number of teams to train with"
    )
    parser.add_argument("--port", type=int, default=8000, help="Port to run showdown server on")
    parser.add_argument(
        "--device",
        type=str,
        default="cuda:0",
        choices=["cuda:0", "cuda:1", "cuda:2", "cuda:3"],
        help="CUDA device to use for training",
    )
    args = parser.parse_args()
    cross_eval_all_agents(args.num_teams, args.port, args.device, 1000, 100)
    team_counts = [1, 4, 16, 64]
    methods = ["bc-sp", "bc-sp", "bc-do", "bc-fp"]
    # cross_eval_over_team_sizes(team_counts, methods, args.port, args.device, 1000, True)
    # cross_eval_over_team_sizes(team_counts, methods, args.port, args.device, 1000, False)
