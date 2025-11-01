import json
import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Sequence, cast

from poke_env.battle import DoubleBattle
from poke_env.player import DoubleBattleOrder
from src.simulator import Simulator


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

    @staticmethod
    def command_from_order(order: DoubleBattleOrder) -> str:
        message = order.message
        return message[8:] if message.startswith("/choose ") else message

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
        command = MCTSNode.command_from_order(order)
        self.children[command] = child
        self.order_lookup[command] = order
        return child

    def update(self, value: float) -> None:
        self.visits += 1
        self.total_value += value


class MCTS:
    def __init__(
        self,
        simulator: Simulator,
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
        self._last_decision: Optional[DoubleBattleOrder] = None
        root_json = json.dumps(root_state, sort_keys=True, separators=(",", ":"))
        orders = self._extract_orders(root_state, self.player_role)
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
        cls, battle: DoubleBattle, exploration: float = math.sqrt(2), rollout_depth: int = 12
    ):
        role = battle.player_role or "p1"
        opponent = battle.opponent_role or ("p2" if role == "p1" else "p1")
        state = Simulator.serialize_battle(battle)
        format_id = cast(Optional[str], state.get("formatid")) or battle.format or "gen9vgc2024regg"
        simulator = Simulator(format_id=format_id, player_role=role, opponent_role=opponent)
        return cls(
            simulator=simulator,
            player_role=role,
            opponent_role=opponent,
            root_state=state,
            exploration=exploration,
            rollout_depth=rollout_depth,
            rollout_policy=None,
        )

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
        best_decision = self.root.order_lookup[best_key]
        self._last_decision = best_decision
        return best_decision

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
        command = MCTSNode.command_from_order(order)
        opponent_command = self._command_for_role(node.state, self.opponent_role)
        result = self.simulator.step(
            node.state_json, command, opponent_command if opponent_command else "default"
        )
        child_orders = self._extract_orders(result.state, self.player_role)
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
        while depth < self.rollout_depth:
            player_orders = self._extract_orders(state, self.player_role)
            if not player_orders:
                break
            player_order = self._select_order(player_orders)
            if player_order is None:
                break
            command = MCTSNode.command_from_order(player_order)
            opponent_command = self._command_for_role(state, self.opponent_role)
            result = self.simulator.step(
                state_json, command, opponent_command if opponent_command else "default"
            )
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

    def _extract_orders(
        self, state: dict[str, Any], role: Optional[str] = None
    ) -> list[DoubleBattleOrder]:
        battle = self._state_to_battle(state, role)
        if battle is None:
            return []
        per_slot = battle.valid_orders
        if not per_slot:
            return []
        slot_one = per_slot[0] if per_slot else []
        slot_two = per_slot[1] if len(per_slot) > 1 else []
        combined = DoubleBattleOrder.join_orders(slot_one, slot_two)
        if not combined:
            return []
        return combined

    def _select_order(self, orders: Sequence[DoubleBattleOrder]) -> Optional[DoubleBattleOrder]:
        if not orders:
            return None
        if self.rollout_policy is None:
            return cast(DoubleBattleOrder, random.choice(orders))
        order_map = {MCTSNode.command_from_order(order): order for order in orders}
        selected = self.rollout_policy(orders)
        if selected is None:
            raise ValueError("Rollout policy returned None for available orders.")
        key = MCTSNode.command_from_order(selected)
        matched = order_map.get(key)
        if matched is None:
            raise ValueError(
                "Rollout policy returned an order not available from the current state."
            )
        return matched

    def _command_for_role(self, state: dict[str, Any], role: str) -> Optional[str]:
        orders = self._extract_orders(state, role)
        if not orders:
            return None
        order = self._select_order(orders)
        return MCTSNode.command_from_order(order) if order else None

    def _state_to_battle(
        self, state: dict[str, Any], role: Optional[str] = None
    ) -> Optional[DoubleBattle]:
        active_role = role or self.player_role
        side = self._find_side(state, active_role)
        request = cast(Optional[dict[str, Any]], side.get("activeRequest"))
        if not request:
            return None
        format_id = cast(Optional[str], state.get("formatid")) or self.simulator.format_id
        gen = self._format_to_gen(format_id)
        battle_tag = cast(str, state.get("id") or state.get("battle_tag") or "reconstructed")
        username = cast(str, side.get("name") or "player")
        battle = DoubleBattle(battle_tag=battle_tag, username=username, logger=None, gen=gen)  # type: ignore
        battle.player_role = active_role
        battle.player_username = username
        try:
            assert battle.opponent_role is not None
            opponent_side = self._find_side(state, battle.opponent_role)
            opponent_username = cast(str, opponent_side.get("name") or "opponent")
            battle.opponent_username = opponent_username  # type: ignore[attr-defined]
        except KeyError:
            pass
        battle.turn = cast(int, state.get("turn", 0))
        battle.parse_request(request)
        self._apply_opponent_state(battle, state)
        return battle

    @staticmethod
    def _find_side(state: dict[str, Any], role: str) -> dict[str, Any]:
        sides = cast(list[dict[str, Any]], state.get("sides", []))
        for side in sides:
            if side.get("id") == role:
                return side
        raise KeyError(f"side {role} missing from state")

    @staticmethod
    def _format_to_gen(format_id: str) -> int:
        lowered = (format_id or "").lower()
        if lowered.startswith("gen"):
            digits = ""
            for char in lowered[3:]:
                if char.isdigit():
                    digits += char
                else:
                    break
            if digits:
                try:
                    return int(digits)
                except ValueError:
                    pass
        return 9

    def _apply_opponent_state(self, battle: DoubleBattle, state: dict[str, Any]) -> None:
        opponent_role = battle.opponent_role
        if opponent_role is None:
            return
        try:
            opponent_side = self._find_side(state, opponent_role)
        except KeyError:
            return
        pokemon_entries = cast(list[dict[str, Any]], opponent_side.get("pokemon", []))
        identifiers: list[str] = []
        for idx, entry in enumerate(pokemon_entries):
            ident = self._opponent_identifier(entry, opponent_role, idx)
            details = self._opponent_details(entry, ident)
            pokemon = battle.get_pokemon(ident, details=details)
            hp_status = self._hp_status(entry)
            if hp_status:
                pokemon.set_hp_status(hp_status)
            if cast(bool, entry.get("fainted")):
                pokemon.faint()
                pokemon.clear_active()
            elif not cast(bool, entry.get("isActive")):
                pokemon.clear_active()
            identifiers.append(ident)

        battle._opponent_active_pokemon.clear()
        active_indices = [
            idx for idx, entry in enumerate(pokemon_entries) if cast(bool, entry.get("isActive"))
        ]
        slot_letters = ["a", "b"]
        for slot_idx, pokemon_idx in enumerate(active_indices):
            if slot_idx >= len(slot_letters):
                break
            ident = identifiers[pokemon_idx]
            pokemon = battle.get_pokemon(ident)
            details = self._opponent_details(pokemon_entries[pokemon_idx], ident)
            pokemon.switch_in(details=details or None)
            hp_status = self._hp_status(pokemon_entries[pokemon_idx])
            if hp_status:
                pokemon.set_hp_status(hp_status)
            battle._opponent_active_pokemon[f"{opponent_role}{slot_letters[slot_idx]}"] = pokemon

    @staticmethod
    def _opponent_identifier(entry: dict[str, Any], role: str, index: int) -> str:
        ident = cast(Optional[str], entry.get("ident"))
        if ident:
            return ident
        set_info = cast(dict[str, Any], entry.get("set") or {})
        species = cast(str, set_info.get("species") or MCTS._extract_species(entry))
        label = (species or f"Pokemon{index + 1}").strip()
        if not label:
            label = f"Pokemon{index + 1}"
        return f"{role}: {label}"

    @staticmethod
    def _opponent_details(entry: dict[str, Any], ident: str) -> str:
        details = cast(str, entry.get("details") or "")
        if details:
            return details
        set_info = cast(dict[str, Any], entry.get("set") or {})
        species = cast(str, set_info.get("species") or MCTS._extract_species(entry))
        level = set_info.get("level")
        gender = entry.get("gender")
        detail_parts = [species]
        if level:
            detail_parts.append(f"L{level}")
        if gender:
            detail_parts.append(gender)
        if cast(bool, entry.get("shiny")):
            detail_parts.append("shiny")
        return ", ".join(part for part in detail_parts if part)

    @staticmethod
    def _hp_status(entry: dict[str, Any]) -> Optional[str]:
        hp = entry.get("hp")
        max_hp = entry.get("maxhp")
        if hp is None or max_hp in (None, 0):
            return None
        status = entry.get("status")
        hp_status = f"{int(hp)}/{int(max_hp)}"
        if status:
            hp_status += f" {status}"
        return hp_status

    @staticmethod
    def _extract_species(entry: dict[str, Any]) -> str:
        raw = cast(str, entry.get("species") or entry.get("baseSpecies") or "")
        if raw.startswith("[Species:") and raw.endswith("]"):
            return raw[len("[Species:") : -1]
        return raw or "Ditto"
