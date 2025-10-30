import atexit
import itertools
import json
import math
import random
import subprocess
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Sequence, cast

from poke_env.battle import DoubleBattle
from poke_env.player import DoubleBattleOrder, PassBattleOrder, SingleBattleOrder

from vgc_bench.simulate import read_state, serializePokeEnvBattle, write_state


@dataclass
class StepResult:
    state: dict[str, Any]
    state_json: str
    reward: float
    terminated: bool


class ShowdownSimulator:
    def __init__(
        self,
        format_id: str,
        player_role: str,
        opponent_role: str,
        showdown_path: str = "pokemon-showdown/pokemon-showdown",
    ):
        self.format_id = format_id or "gen9vgc2024regg"
        self.player_role = player_role
        self.opponent_role = opponent_role
        self.process = subprocess.Popen(
            [showdown_path, "simulate-battle"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        stdin = self.process.stdin
        stdout = self.process.stdout
        assert stdin is not None
        assert stdout is not None
        self.stdin = stdin
        self.stdout = stdout
        if self.stdin is None or self.stdout is None:
            raise RuntimeError("failed to start showdown simulate-battle sub-process")
        self._bootstrap()
        atexit.register(self.close)

    def _bootstrap(self) -> None:
        self.stdin.write(f'>start {{"formatid":"{self.format_id}"}}\n')
        self.stdin.write(f'>player {self.player_role} {{"name":"MCTS"}}\n')
        self.stdin.write(f'>player {self.opponent_role} {{"name":"Rollout"}}\n')
        self.stdin.flush()
        # Prime the channel so later requests are immediate.
        self.peek_state()

    def peek_state(self) -> dict[str, Any]:
        snapshot = read_state(self.stdin, self.stdout)
        state = cast(dict[str, Any], json.loads(snapshot))
        return state

    def close(self) -> None:
        if self.stdin:
            try:
                self.stdin.close()
            except Exception:
                pass
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except Exception:
                self.process.kill()

    def _normalize(self, state: dict[str, Any]) -> str:
        return json.dumps(state, sort_keys=True, separators=(",", ":"))

    def normalize(self, state: dict[str, Any]) -> str:
        return self._normalize(state)

    def _player_side(self, state: dict[str, Any], role: str) -> dict[str, Any]:
        sides = cast(list[dict[str, Any]], state.get("sides", []))
        for side in sides:
            if side.get("id") == role:
                return side
        raise KeyError(f"could not locate side {role}")

    def reward(self, state: dict[str, Any]) -> float:
        if not state.get("ended"):
            return 0.0
        player = self._player_side(state, self.player_role)
        opponent = self._player_side(state, self.opponent_role)
        player_left = cast(int, player.get("pokemonLeft", 0))
        opponent_left = cast(int, opponent.get("pokemonLeft", 0))
        if player_left > opponent_left:
            return 1.0
        if opponent_left > player_left:
            return -1.0
        return 0.0

    def step(
        self, state_json: str, player_command: str, opponent_command: str = "default"
    ) -> StepResult:
        write_state(self.stdin, state_json)
        self.stdin.flush()
        if opponent_command:
            self.stdin.write(f">{self.opponent_role} {opponent_command}\n")
        if player_command:
            self.stdin.write(f">{self.player_role} {player_command}\n")
        self.stdin.flush()
        snapshot = read_state(self.stdin, self.stdout)
        state = cast(dict[str, Any], json.loads(snapshot))
        return StepResult(
            state=state,
            state_json=self._normalize(state),
            reward=self.reward(state),
            terminated=bool(state.get("ended")),
        )


@dataclass
class MCTSNode:
    state: dict[str, Any]
    state_json: str
    parent: Optional["MCTSNode"]
    incoming_order: Optional[DoubleBattleOrder]
    unexpanded_orders: list[DoubleBattleOrder] = field(default_factory=list)
    children: dict[str, "MCTSNode"] = field(default_factory=dict)
    order_lookup: dict[str, DoubleBattleOrder] = field(default_factory=dict)
    visits: int = 0
    total_value: float = 0.0
    is_terminal: bool = False

    def best_child_key(self, exploration: float) -> str:
        log_parent = math.log(self.visits + 1)
        best_key: Optional[str] = None
        best_value = float("-inf")
        for key, node in self.children.items():
            if node.visits == 0:
                score = float("inf")
            else:
                mean = node.total_value / node.visits
                bonus = exploration * math.sqrt(log_parent / node.visits)
                score = mean + bonus
            if score > best_value:
                best_key = key
                best_value = score
        if best_key is None:
            raise ValueError("best_child_key called on a node with no children")
        return best_key

    def add_child(
        self, order: DoubleBattleOrder, state: dict[str, Any], state_json: str, terminal: bool
    ) -> "MCTSNode":
        child = MCTSNode(
            state=state,
            state_json=state_json,
            parent=self,
            incoming_order=order,
            unexpanded_orders=[],
            children={},
            visits=0,
            total_value=0.0,
            is_terminal=terminal,
        )
        command = _double_order_command(order)
        self.children[command] = child
        self.order_lookup[command] = order
        return child

    def update(self, value: float) -> None:
        self.visits += 1
        self.total_value += value


def _find_side(state: dict[str, Any], role: str) -> dict[str, Any]:
    sides = cast(list[dict[str, Any]], state.get("sides", []))
    for side in sides:
        if side.get("id") == role:
            return side
    raise KeyError(f"side {role} missing from state")


def _default_target(target: Optional[str], slot: int) -> Optional[str]:
    if target is None:
        return None
    lowered = target.lower()
    if lowered in {"normal", "adjacentfoe", "adjacent"}:
        return "1" if slot == 0 else "2"
    if lowered in {"any", "randomnormal"}:
        return "1"
    return None


def _switch_orders(
    side: dict[str, Any], slot: int
) -> list[tuple[SingleBattleOrder, Optional[int]]]:
    options: list[tuple[SingleBattleOrder, Optional[int]]] = []
    pokemon_entries = cast(list[dict[str, Any]], side.get("pokemon", []))
    for idx, pokemon in enumerate(pokemon_entries, start=1):
        if pokemon.get("isActive") or pokemon.get("fainted"):
            continue
        order = SingleBattleOrder(order=f"/choose switch {idx}")
        options.append((order, idx))
    return options


def _move_orders(
    active_info: dict[str, Any], slot: int
) -> list[tuple[SingleBattleOrder, Optional[int]]]:
    decisions: list[tuple[SingleBattleOrder, Optional[int]]] = []
    move_entries = cast(list[dict[str, Any]], active_info.get("moves", []))
    for idx, move in enumerate(move_entries, start=1):
        if move.get("disabled"):
            continue
        target = _default_target(cast(Optional[str], move.get("target")), slot)
        command = f"/choose move {idx}"
        if target is not None:
            command += f" {target}"
        decisions.append((SingleBattleOrder(order=command), None))
    return decisions


def _valid_combo(options: Sequence[tuple[SingleBattleOrder, Optional[int]]]) -> bool:
    switches = [switch for _, switch in options if switch is not None]
    return len(switches) == len(set(switches))


def extract_orders(state: dict[str, Any], role: str) -> list[DoubleBattleOrder]:
    side = _find_side(state, role)
    request = cast(Optional[dict[str, Any]], side.get("activeRequest"))
    if not request:
        return []
    active = cast(list[dict[str, Any]], request.get("active", []))
    force_switch = cast(list[bool], request.get("forceSwitch", [False] * len(active)))
    per_slot: list[list[tuple[SingleBattleOrder, Optional[int]]]] = []
    for slot, info in enumerate(active):
        options: list[tuple[SingleBattleOrder, Optional[int]]] = []
        if slot < len(force_switch) and force_switch[slot]:
            options.extend(_switch_orders(side, slot))
        else:
            options.extend(_move_orders(info, slot))
            trapped = info.get("trapped") or info.get("maybeTrapped")
            if not trapped:
                options.extend(_switch_orders(side, slot))
        if not options:
            options.append((SingleBattleOrder(order="/choose move 1"), None))
        per_slot.append(options)
    if not per_slot:
        return []
    orders: list[DoubleBattleOrder] = []
    for combo in itertools.product(*per_slot):
        if not _valid_combo(combo):
            continue
        single_orders = [choice[0] for choice in combo]
        while len(single_orders) < 2:
            single_orders.append(PassBattleOrder())
        orders.append(
            DoubleBattleOrder(first_order=single_orders[0], second_order=single_orders[1])
        )
    return orders


def _double_order_command(order: DoubleBattleOrder) -> str:
    message = order.message
    return message[8:] if message.startswith("/choose ") else message


class ShowdownMCTS:
    def __init__(
        self,
        simulator: ShowdownSimulator,
        player_role: str,
        opponent_role: str,
        root_state: dict[str, Any],
        exploration: float = math.sqrt(2),
        rollout_depth: int = 12,
        rollout_policy: Optional[Callable[[Sequence[DoubleBattleOrder]], DoubleBattleOrder]] = None,
    ):
        self.simulator = simulator
        self.player_role = player_role
        self.opponent_role = opponent_role
        self.exploration = exploration
        self.rollout_depth = rollout_depth
        self.rollout_policy = rollout_policy
        self._last_order: Optional[DoubleBattleOrder] = None
        root_json = simulator.normalize(root_state)
        orders = extract_orders(root_state, player_role)
        self.root = MCTSNode(
            state=root_state,
            state_json=root_json,
            parent=None,
            incoming_order=None,
            unexpanded_orders=list(orders),
            children={},
            order_lookup={},
            visits=0,
            total_value=0.0,
            is_terminal=bool(root_state.get("ended")),
        )

    @classmethod
    def from_battle(
        cls,
        battle: DoubleBattle,
        showdown_path: str = "pokemon-showdown/pokemon-showdown",
        exploration: float = math.sqrt(2),
        rollout_depth: int = 12,
    ) -> "ShowdownMCTS":
        role = battle.player_role or "p1"
        opponent = battle.opponent_role or ("p2" if role == "p1" else "p1")
        state = cast(dict[str, Any], serializePokeEnvBattle(battle))
        format_id = cast(Optional[str], state.get("formatid")) or battle.format or "gen9vgc2024regg"
        simulator = ShowdownSimulator(
            format_id=format_id,
            player_role=role,
            opponent_role=opponent,
            showdown_path=showdown_path,
        )
        return cls(
            simulator=simulator,
            player_role=role,
            opponent_role=opponent,
            root_state=state,
            exploration=exploration,
            rollout_depth=rollout_depth,
            rollout_policy=None,
        )

    @property
    def last_order(self) -> Optional[DoubleBattleOrder]:
        return self._last_order

    def run(self, simulations: int) -> Optional[DoubleBattleOrder]:
        if not self.root.unexpanded_orders and not self.root.children:
            return None
        for _ in range(simulations):
            node = self._select(self.root)
            expanded = self._expand(node)
            leaf = expanded or node
            reward = self._rollout(leaf)
            self._backpropagate(leaf, reward)
        if not self.root.children:
            return None
        best_key = max(self.root.children.items(), key=lambda item: item[1].visits)[0]
        best_order = self.root.order_lookup[best_key]
        self._last_order = best_order
        return best_order

    def _select(self, node: MCTSNode) -> MCTSNode:
        current = node
        while not current.is_terminal:
            if current.unexpanded_orders:
                return current
            if not current.children:
                return current
            key = current.best_child_key(self.exploration)
            current = current.children[key]
        return current

    def _expand(self, node: MCTSNode) -> Optional[MCTSNode]:
        if node.is_terminal or not node.unexpanded_orders:
            return None
        order = node.unexpanded_orders.pop()
        command = _double_order_command(order)
        result = self.simulator.step(node.state_json, command)
        child_orders = extract_orders(result.state, self.player_role)
        child = node.add_child(
            order=order,
            state=result.state,
            state_json=result.state_json,
            terminal=result.terminated,
        )
        child.unexpanded_orders.extend(child_orders)
        return child

    def _rollout(self, node: MCTSNode) -> float:
        if node.is_terminal:
            return self.simulator.reward(node.state)
        state = node.state
        state_json = node.state_json
        depth = 0
        if self.rollout_policy is not None:
            policy = self.rollout_policy
        else:
            policy = cast(Callable[[Sequence[DoubleBattleOrder]], DoubleBattleOrder], random.choice)
        while depth < self.rollout_depth:
            orders = extract_orders(state, self.player_role)
            if not orders:
                break
            order = policy(orders)
            command = _double_order_command(order)
            result = self.simulator.step(state_json, command)
            if result.terminated:
                return result.reward
            state = result.state
            state_json = result.state_json
            depth += 1
        return self.simulator.reward(state)

    def _backpropagate(self, node: MCTSNode, reward: float) -> None:
        current = node
        while current:
            current.update(reward)
            current = current.parent
