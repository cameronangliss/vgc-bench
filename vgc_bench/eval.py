"""
Evaluation module for VGC-Bench.

Provides functions for cross-evaluating trained agents against each other and
baseline players, computing payoff matrices, and analyzing team statistics
using Alpha-Rank for meta-game analysis.
"""

import argparse
import asyncio
import random
from pathlib import Path
from statistics import mean, median

import numpy as np
from open_spiel.python.egt import alpharank
from poke_env import cross_evaluate
from poke_env.player import MaxBasePowerPlayer, RandomPlayer, SimpleHeuristicsPlayer
from poke_env.ps_client import AccountConfiguration, ServerConfiguration
from stable_baselines3 import PPO
from tensorboard.backend.event_processing import event_accumulator

from vgc_bench.src.llm import LLMPlayer
from vgc_bench.src.policy_player import BatchPolicyPlayer
from vgc_bench.src.teams import (
    RandomTeamBuilder,
    calc_team_similarity_score,
    get_team_paths,
)
from vgc_bench.src.utils import format_map


def cross_eval_all_agents(
    battle_format: str,
    num_teams: int,
    port: int,
    device: str,
    num_battles: int,
    num_llm_battles: int,
):
    """
    Run cross-evaluation of all agent types and compute average payoff matrix.

    Evaluates Random, MaxBasePower, SimpleHeuristics, LLM, and various RL-trained
    agents (SP, FP, DO, BC variants) against each other across multiple runs,
    then uses Alpha-Rank to analyze the meta-game.

    Args:
        battle_format: Pokemon Showdown battle format string.
        num_teams: Number of teams to use in evaluation.
        port: Port for the Pokemon Showdown server.
        device: CUDA device for model inference.
        num_battles: Total number of battles for non-LLM matchups.
        num_llm_battles: Total number of battles involving the LLM player.
    """
    num_runs = 5
    avg_payoff_matrix = np.zeros((11, 11))
    labels = ["R", "MBP", "SH", "LLM", "SP", "FP", "DO", "BC", "BCSP", "BCFP", "BCDO"]
    for run_id in range(1, num_runs + 1):
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
                team=RandomTeamBuilder(run_id, num_teams, battle_format),
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
            team=RandomTeamBuilder(run_id, num_teams, battle_format),
        )
        best_checkpoints = asyncio.run(
            get_best_checkpoints(
                battle_format, run_id, num_teams, port, device, num_battles
            )
        )
        for method, checkpoint in best_checkpoints.items():
            agent = BatchPolicyPlayer(
                account_configuration=AccountConfiguration(
                    f"{run_id}/{method}/{checkpoint}", None
                ),
                server_configuration=ServerConfiguration(
                    f"ws://localhost:{port}/showdown/websocket",
                    "https://play.pokemonshowdown.com/action.php?",
                ),
                battle_format=battle_format,
                log_level=25,
                max_concurrent_battles=10,
                accept_open_team_sheet=True,
                open_timeout=None,
                team=RandomTeamBuilder(run_id, num_teams, battle_format),
            )
            policy_path = f"results{run_id}/saves-{method}"
            if method != "bc":
                policy_path += f"/{num_teams}-teams"
            agent.policy = PPO.load(f"{policy_path}/{checkpoint}", device=device).policy
            players += [agent]
        results = asyncio.run(
            cross_evaluate(players, n_challenges=num_battles // num_runs)
        )
        asyncio.run(
            llm_player.battle_against(*players, n_battles=num_llm_battles // num_runs)
        )
        del llm_player.model
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
        print(f"Cross-agent comparison of run {run_id} with {num_teams} teams:")
        print(payoff_matrix.tolist())
        pi = alpharank.compute([payoff_matrix], use_inf_alpha=True)[2]
        alpharank.utils.print_rankings_table(
            [avg_payoff_matrix],
            pi,
            strat_labels=labels,
            num_top_strats_to_print=len(pi),
        )
        avg_payoff_matrix += payoff_matrix / num_runs
    avg_payoff_matrix = avg_payoff_matrix.round(decimals=3)
    print(f"Average cross-agent comparison across all runs with {num_teams} teams:")
    print(avg_payoff_matrix.tolist())
    pi = alpharank.compute([avg_payoff_matrix], use_inf_alpha=True)[2]
    alpharank.utils.print_rankings_table(
        [avg_payoff_matrix], pi, strat_labels=labels, num_top_strats_to_print=len(pi)
    )


async def get_best_checkpoints(
    battle_format: str,
    run_id: int,
    num_teams: int,
    port: int,
    device: str,
    num_battles: int,
    eval_pool_size: int = 50,
    cutoff: int = 5,
) -> dict[str, int]:
    """
    Find the best checkpoint for each training method based on evaluation performance.

    For each method, selects checkpoints with top-10% evaluation scores from TensorBoard
    logs, then battles them against a random pool of other checkpoints to determine
    which performs best in head-to-head matchups.

    Args:
        battle_format: Pokemon Showdown battle format string.
        run_id: Training run identifier.
        num_teams: Number of teams used during training.
        port: Port for the Pokemon Showdown server.
        device: CUDA device for model inference.
        num_battles: Number of battles to run for each checkpoint evaluation.
        eval_pool_size: Size of the random opponent pool for evaluation.
        cutoff: Number of initial checkpoints to skip.

    Returns:
        Dictionary mapping method names to their best checkpoint timesteps.
    """
    best_checkpoints = {}
    save_policy = BatchPolicyPlayer(
        server_configuration=ServerConfiguration(
            f"ws://localhost:{port}/showdown/websocket",
            "https://play.pokemonshowdown.com/action.php?",
        ),
        battle_format=battle_format,
        log_level=25,
        max_concurrent_battles=10,
        accept_open_team_sheet=True,
        open_timeout=None,
        team=RandomTeamBuilder(run_id, num_teams, battle_format),
    )
    opponent = BatchPolicyPlayer(
        server_configuration=ServerConfiguration(
            f"ws://localhost:{port}/showdown/websocket",
            "https://play.pokemonshowdown.com/action.php?",
        ),
        battle_format=battle_format,
        log_level=25,
        max_concurrent_battles=10,
        accept_open_team_sheet=True,
        open_timeout=None,
        team=RandomTeamBuilder(run_id, num_teams, battle_format),
    )
    filess = [
        sorted(
            Path(f"results{run_id}/saves-{method}/{num_teams}-teams").iterdir(),
            key=lambda p: int(p.stem),
        )[cutoff:]
        for method in ["sp", "fp", "do", "bc-sp", "bc-fp", "bc-do"]
    ]
    files = [file for files in filess for file in files]
    eval_pool_files = random.sample(files, eval_pool_size)
    for method in ["sp", "fp", "do", "bc", "bc-sp", "bc-fp", "bc-do"]:
        if method == "bc":
            best_checkpoints["bc"] = 100
            continue
        data = extract_tb(
            f"results{run_id}/logs-{method}/{num_teams}-teams_0", "train/eval"
        )
        eval_scores = [d[1] for d in data]
        min_score = np.percentile(eval_scores, 90)
        best_indices = np.where(eval_scores >= min_score)[0][::-1]
        checkpoints = np.array([d[0] for d in data])[best_indices]
        win_rates = {}
        for checkpoint in checkpoints:
            save_dir = Path(f"results{run_id}/saves-{method}/{num_teams}-teams")
            save_policy.policy = PPO.load(
                save_dir / f"{checkpoint}", device=device
            ).policy
            for f in eval_pool_files:
                opponent.policy = PPO.load(f, device=device).policy
                await save_policy.battle_against(
                    opponent, n_battles=num_battles // eval_pool_size
                )
            win_rates[checkpoint.item()] = save_policy.win_rate
            save_policy.reset_battles()
            opponent.reset_battles()
        print(
            f"comparison of agents with top-10% eval score from {method}: {win_rates}",
            flush=True,
        )
        best_checkpoints[method] = max(list(win_rates.items()), key=lambda tup: tup[1])[
            0
        ]
    print(f"best of run #{run_id}:", best_checkpoints, flush=True)
    return best_checkpoints


def extract_tb(event_file: str, tag_prefix: str) -> list[tuple[int, float]]:
    """
    Extract (x, y) pairs from TensorBoard event file's `tag_prefix` data,
    keeping only the most recent recording for each step (last occurrence)
    """
    ea = event_accumulator.EventAccumulator(event_file)
    ea.Reload()
    for tag in ea.Tags()["scalars"]:
        if tag.startswith(tag_prefix):
            scalars = ea.Scalars(tag)
            last_per_step: dict[int, float] = {}
            for s in scalars:
                last_per_step[int(s.step)] = round(s.value, ndigits=5)
            return sorted(last_per_step.items(), key=lambda kv: kv[0])
    raise FileNotFoundError()


def cross_eval_over_team_sizes(
    battle_format: str,
    team_counts: list[int],
    methods: list[tuple[str, list[int]]],
    port: int,
    device: str,
    num_battles: int,
    is_performance_test: bool,
):
    """
    Cross-evaluate agents trained with different team counts.

    Tests whether agents trained with more teams perform better (performance test)
    or generalize better to unseen teams (generalization test).

    Args:
        battle_format: Pokemon Showdown battle format string.
        team_counts: List of team counts corresponding to each method.
        methods: List of (method_name, checkpoint_list) tuples for each team count.
        port: Port for the Pokemon Showdown server.
        device: CUDA device for model inference.
        num_battles: Total number of battles across all runs.
        is_performance_test: If True, tests on minimum team count; if False,
            tests generalization on maximum team count (out-of-distribution).
    """
    # if is_performance_test is False, then this becomes the generalization test
    num_runs = 5
    avg_payoff_matrix = np.zeros((4, 4))
    for run_id in range(1, num_runs + 1):
        agents = []
        for num_teams, (method, checkpoints) in zip(team_counts, methods):
            agent = BatchPolicyPlayer(
                account_configuration=AccountConfiguration.generate(
                    f"{run_id}/{method}/{num_teams}-teams"
                ),
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
                    run_id,
                    min(team_counts) if is_performance_test else max(team_counts),
                    battle_format,
                    take_from_end=not is_performance_test,
                ),
            )
            agent.policy = PPO.load(
                f"results{run_id}/saves-{method}/{num_teams}-teams/{checkpoints[run_id - 1]}",
                device=device,
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
    avg_payoff_matrix = avg_payoff_matrix.round(decimals=3)
    print("Performance" if is_performance_test else "Generalization", "test results:")
    print(avg_payoff_matrix.tolist())
    pi = alpharank.compute([avg_payoff_matrix], use_inf_alpha=True)[2]
    alpharank.utils.print_rankings_table(
        [avg_payoff_matrix],
        pi,
        strat_labels=[f"{n}-teams" for n in team_counts],
        num_top_strats_to_print=len(pi),
    )


def print_team_statistics(battle_format: str, num_teams: int):
    """
    Print similarity statistics between teams in the dataset.

    Computes and displays worst-case similarity scores between each team and
    its most similar neighbor, both globally and for out-of-distribution teams
    relative to the in-distribution training set for each run.

    Args:
        battle_format: Pokemon Showdown battle format string.
        num_teams: Number of teams in the in-distribution training set.
    """
    num_runs = 5
    all_teams = [path.read_text() for path in get_team_paths(battle_format)]
    sim_scores = [
        max(
            [
                calc_team_similarity_score(all_teams[i], all_teams[j])
                for i in range(len(all_teams))
                if i != j
            ]
        )
        for j in range(len(all_teams))
    ]
    print(
        "worst-case team similarities for each team across all teams:",
        f"mean = {round(mean(sim_scores), ndigits=3)},",
        f"median = {round(median(sim_scores), ndigits=4)},",
        f"min = {min(sim_scores)},",
        f"max = {max(sim_scores)}",
    )
    print(
        "worst-case team similarities of out-of-distribution teams",
        f"across in-distribution {num_teams} team set in...",
    )
    for run_id in range(1, num_runs + 1):
        teams = list(range(len(all_teams)))
        random.Random(run_id).shuffle(teams)
        sim_scores = [
            max(
                [
                    calc_team_similarity_score(all_teams[i], all_teams[j])
                    for i in teams[:num_teams]
                ]
            )
            for j in teams[num_teams:]
        ]
        print(
            f"run #{run_id}:",
            f"mean = {round(mean(sim_scores), ndigits=3)},",
            f"median = {round(median(sim_scores), ndigits=4)},",
            f"min = {min(sim_scores)},",
            f"max = {max(sim_scores)}",
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate a Pokémon AI model")
    parser.add_argument(
        "--reg", type=str, required=True, help="VGC regulation to eval on, i.e. G"
    )
    parser.add_argument(
        "--num_teams", type=int, required=True, help="Number of teams to eval with"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to run showdown server on"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda:0",
        choices=["cuda:0", "cuda:1", "cuda:2", "cuda:3"],
        help="CUDA device to use for eval",
    )
    args = parser.parse_args()
    battle_format = format_map[args.reg.lower()]
    print_team_statistics(battle_format, args.num_teams)
    cross_eval_all_agents(
        battle_format, args.num_teams, args.port, args.device, 1000, 100
    )
    team_counts = [1, 4, 16, 64]
    methods = [
        ("bc-sp", [4915200, 1474560, 4816896, 1179648, 786432]),
        ("bc-sp", [589824, 3047424, 4128768, 983040, 3538944]),
        ("bc-do", [3833856, 1671168, 5013504, 2654208, 4030464]),
        ("bc-sp", [1769472, 2064384, 4227072, 983040, 5013504]),
    ]
    # cross_eval_over_team_sizes(team_counts, methods, args.port, args.device, 1000, True)
    # cross_eval_over_team_sizes(team_counts, methods, args.port, args.device, 1000, False)
