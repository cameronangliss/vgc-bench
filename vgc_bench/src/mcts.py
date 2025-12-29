from __future__ import annotations

from copy import deepcopy

from mcts.base.base import BaseState
from mcts.searcher.mcts import MCTS
from poke_env.battle import DoubleBattle
from poke_env.player import Player
from poke_env.player.battle_order import DoubleBattleOrder
from src.simulator import Simulator


class HashableAction:
    """Hashable wrapper around DoubleBattleOrder for use with MCTS library."""

    __slots__ = ("order",)

    def __init__(self, order: DoubleBattleOrder):
        self.order = order

    def __hash__(self) -> int:
        return hash(self.order.message)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HashableAction):
            return False
        return self.order.message == other.order.message

    def __repr__(self) -> str:
        return f"HashableAction({self.order.message})"


class BattleState(BaseState):
    """
    Wrapper around DoubleBattle that implements the BaseState interface
    for the monte-carlo-tree-search library.
    """

    def __init__(self, battle: DoubleBattle, max_rollout_depth: int = 50):
        self.battle = battle
        self.max_rollout_depth = max_rollout_depth

    def get_current_player(self) -> int:
        return 1  # Always maximizer (player 1's perspective)

    def get_possible_actions(self) -> list[HashableAction]:
        if self.battle._wait or self.battle.finished:
            return []
        orders = DoubleBattleOrder.join_orders(*self.battle.valid_orders)
        return [HashableAction(o) for o in orders]

    def take_action(self, action: HashableAction) -> BattleState:
        """Execute action, sample random opponent move, return new state."""
        battle_copy = deepcopy(self.battle)
        sim = Simulator(battle_copy, verbose=False)
        opp_action = (
            Player.choose_random_move(sim.opp_battle).message if not sim.opp_battle._wait else None
        )
        sim.step(action.order.message, opp_action)
        return BattleState(sim.battle, self.max_rollout_depth)

    def is_terminal(self) -> bool:
        return self.battle.finished

    def get_reward(self) -> float:
        if self.battle.won:
            return 1.0
        elif self.battle.lost:
            return -1.0
        return 0.0


def rollout_policy(state: BattleState) -> float:
    """Random rollout until terminal or max depth."""
    battle_copy = deepcopy(state.battle)
    sim = Simulator(battle_copy, verbose=False)
    depth = 0
    while not sim.battle.finished and depth < state.max_rollout_depth:
        p1 = Player.choose_random_move(sim.battle).message if not sim.battle._wait else None
        p2 = Player.choose_random_move(sim.opp_battle).message if not sim.opp_battle._wait else None
        sim.step(p1, p2)
        depth += 1
    if sim.battle.won:
        return 1.0
    elif sim.battle.lost:
        return -1.0
    return 0.0


def run_mcts_for_battle(
    battle: DoubleBattle,
    num_simulations: int = 100,
    time_limit_ms: int | None = None,
    exploration_constant: float = 1.41,
    max_rollout_depth: int = 50,
) -> DoubleBattleOrder:
    """
    Run MCTS search and return the best action.

    Args:
        battle: Current battle state (must not be in teampreview)
        num_simulations: Number of iterations (ignored if time_limit_ms set)
        time_limit_ms: Optional time limit in milliseconds
        exploration_constant: UCB1 exploration parameter
        max_rollout_depth: Max depth for random rollouts

    Returns:
        The best DoubleBattleOrder
    """
    assert not battle.teampreview, "MCTS should not be called during teampreview"

    state = BattleState(battle, max_rollout_depth)

    if not state.get_possible_actions():
        return Player.choose_random_doubles_move(battle)

    if time_limit_ms is not None:
        searcher = MCTS(
            time_limit=time_limit_ms,
            exploration_constant=exploration_constant,
            rollout_policy=rollout_policy,
        )
    else:
        searcher = MCTS(
            iteration_limit=num_simulations,
            exploration_constant=exploration_constant,
            rollout_policy=rollout_policy,
        )

    action = searcher.search(initial_state=state)

    if action is None:
        return Player.choose_random_doubles_move(battle)

    # Unwrap HashableAction to DoubleBattleOrder
    if isinstance(action, HashableAction):
        return action.order
    return Player.choose_random_doubles_move(battle)
