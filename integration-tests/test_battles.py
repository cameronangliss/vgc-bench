"""
Integration tests for actual Pokemon VGC battles.

Runs real battles on a local Pokemon Showdown server to verify that
PolicyPlayer and LLMPlayer can complete games end-to-end.
"""

import asyncio
import random

import pytest
from poke_env.environment import SingleAgentWrapper
from poke_env.player import RandomPlayer, SimpleHeuristicsPlayer
from poke_env.ps_client import ServerConfiguration
from stable_baselines3 import PPO

from vgc_bench.src.env import ShowdownEnv
from vgc_bench.src.llm import LLMPlayer
from vgc_bench.src.policy import MaskedActorCriticPolicy
from vgc_bench.src.policy_player import PolicyPlayer
from vgc_bench.src.teams import RandomTeamBuilder
from vgc_bench.src.utils import format_map

SERVER_CONFIG = ServerConfiguration(
    "ws://localhost:8100/showdown/websocket",
    "https://play.pokemonshowdown.com/action.php?",
)
BATTLE_FORMAT = format_map["g"]
N_BATTLES = 3


def server_available() -> bool:
    """Check if a Pokemon Showdown server is running on the test port."""
    import socket

    try:
        with socket.create_connection(("localhost", 8100), timeout=1):
            return True
    except OSError:
        return False


requires_server = pytest.mark.skipif(
    not server_available(), reason="Pokemon Showdown server not running on port 8100"
)


class MockLLMPlayer(LLMPlayer):
    """LLMPlayer with mocked LLM that returns random valid action indices."""

    def setup_llm(self):
        """Skip LLM loading entirely."""
        pass

    def get_response(self, prompt: str) -> str:
        """Return a random valid action index from the prompt.

        Parses only the final numbered action list (after the last
        "available" header) to determine how many options exist.
        """
        # Only count numbered items after the final action/choice section
        sections = prompt.split("JUST THE NUMBER")
        action_section = sections[0].rsplit("available", 1)[-1] if sections else prompt
        max_idx = 0
        for line in action_section.split("\n"):
            stripped = line.strip()
            if stripped and stripped[0].isdigit() and ". " in stripped:
                try:
                    idx = int(stripped.split(".")[0])
                    max_idx = max(max_idx, idx)
                except ValueError:
                    pass
        if max_idx == 0:
            return "1"
        return str(random.randint(1, max_idx))


@requires_server
class TestPolicyPlayerBattles:
    """Test that PolicyPlayer can complete real battles."""

    def test_policy_vs_random(self):
        """PolicyPlayer with random weights completes battles against RandomPlayer."""
        env = ShowdownEnv(
            battle_format=BATTLE_FORMAT,
            log_level=40,
            accept_open_team_sheet=True,
            start_listening=False,
            choose_on_teampreview=True,
        )
        opponent = RandomPlayer(start_listening=False)
        single_env = SingleAgentWrapper(env, opponent)
        ppo = PPO(
            MaskedActorCriticPolicy,
            single_env,
            policy_kwargs={"d_model": 64, "choose_on_teampreview": True},
            device="cpu",
        )
        player = PolicyPlayer(
            policy=ppo.policy,
            server_configuration=SERVER_CONFIG,
            battle_format=BATTLE_FORMAT,
            log_level=40,
            max_concurrent_battles=1,
            accept_open_team_sheet=True,
            team=RandomTeamBuilder(1, None, "g"),
        )
        opponent = SimpleHeuristicsPlayer(
            server_configuration=SERVER_CONFIG,
            battle_format=BATTLE_FORMAT,
            log_level=40,
            max_concurrent_battles=1,
            accept_open_team_sheet=True,
            team=RandomTeamBuilder(1, None, "g"),
        )
        asyncio.run(player.battle_against(opponent, n_battles=N_BATTLES))
        assert player.n_finished_battles == N_BATTLES
        assert opponent.n_finished_battles == N_BATTLES

    def test_policy_vs_heuristics(self):
        """PolicyPlayer with random weights completes battles against SimpleHeuristics."""
        env = ShowdownEnv(
            battle_format=BATTLE_FORMAT,
            log_level=40,
            accept_open_team_sheet=True,
            start_listening=False,
            choose_on_teampreview=True,
        )
        opponent = RandomPlayer(start_listening=False)
        single_env = SingleAgentWrapper(env, opponent)
        ppo = PPO(
            MaskedActorCriticPolicy,
            single_env,
            policy_kwargs={"d_model": 64, "choose_on_teampreview": True},
            device="cpu",
        )
        player = PolicyPlayer(
            policy=ppo.policy,
            server_configuration=SERVER_CONFIG,
            battle_format=BATTLE_FORMAT,
            log_level=40,
            max_concurrent_battles=1,
            accept_open_team_sheet=True,
            team=RandomTeamBuilder(2, None, "g"),
        )
        opponent = SimpleHeuristicsPlayer(
            server_configuration=SERVER_CONFIG,
            battle_format=BATTLE_FORMAT,
            log_level=40,
            max_concurrent_battles=1,
            accept_open_team_sheet=True,
            team=RandomTeamBuilder(2, None, "g"),
        )
        asyncio.run(player.battle_against(opponent, n_battles=N_BATTLES))
        assert player.n_finished_battles == N_BATTLES
        assert opponent.n_finished_battles == N_BATTLES


@requires_server
class TestMockLLMPlayerBattles:
    """Test that LLMPlayer (with mocked LLM) can complete real battles."""

    def test_llm_vs_random(self):
        """MockLLMPlayer completes battles against RandomPlayer."""
        player = MockLLMPlayer(
            device="cpu",
            server_configuration=SERVER_CONFIG,
            battle_format=BATTLE_FORMAT,
            log_level=40,
            max_concurrent_battles=1,
            accept_open_team_sheet=True,
            team=RandomTeamBuilder(3, None, "g"),
        )
        opponent = RandomPlayer(
            server_configuration=SERVER_CONFIG,
            battle_format=BATTLE_FORMAT,
            log_level=40,
            max_concurrent_battles=1,
            accept_open_team_sheet=True,
            team=RandomTeamBuilder(3, None, "g"),
        )
        asyncio.run(player.battle_against(opponent, n_battles=N_BATTLES))
        assert player.n_finished_battles == N_BATTLES
        assert opponent.n_finished_battles == N_BATTLES

    def test_llm_vs_heuristics(self):
        """MockLLMPlayer completes battles against SimpleHeuristicsPlayer."""
        player = MockLLMPlayer(
            device="cpu",
            server_configuration=SERVER_CONFIG,
            battle_format=BATTLE_FORMAT,
            log_level=40,
            max_concurrent_battles=1,
            accept_open_team_sheet=True,
            team=RandomTeamBuilder(4, None, "g"),
        )
        opponent = SimpleHeuristicsPlayer(
            server_configuration=SERVER_CONFIG,
            battle_format=BATTLE_FORMAT,
            log_level=40,
            max_concurrent_battles=1,
            accept_open_team_sheet=True,
            team=RandomTeamBuilder(4, None, "g"),
        )
        asyncio.run(player.battle_against(opponent, n_battles=N_BATTLES))
        assert player.n_finished_battles == N_BATTLES
        assert opponent.n_finished_battles == N_BATTLES
