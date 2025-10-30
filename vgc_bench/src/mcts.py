import atexit
import base64
import itertools
import json
import math
import random
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import IO, Any, Callable, Dict, List, Optional, Sequence, cast

from poke_env.battle import DoubleBattle, Move, Pokemon, PokemonGender, SideCondition, Status
from poke_env.data import GenData
from poke_env.player import DoubleBattleOrder, PassBattleOrder, SingleBattleOrder


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
        snapshot = self._read_state_from_stream(self.stdin, self.stdout)
        state = cast(dict[str, Any], json.loads(snapshot))
        return state

    @staticmethod
    def _read_state_from_stream(stdin: IO[str], stdout: IO[str]) -> str:
        stdin.write(">eval JSON.stringify(battle.toJSON())\n")
        stdin.flush()
        for msg in stdout:
            if not msg.startswith("||<<< "):
                continue
            return msg.strip()[7:-1]
        raise LookupError("unable to read battle state from showdown")

    @staticmethod
    def _write_state_to_stream(stdin: IO[str], state: str) -> None:
        payload = base64.b64encode(state.encode()).decode()
        stdin.write(
            (
                ">eval (() => { "
                'const State = require("./state").State; '
                f'const restored = State.deserializeBattle(JSON.parse(Buffer.from("{payload}", "base64").toString())); '
                "restored.send = battle.send; "
                "this.battle = restored; "
                "restored.sendUpdates(); "
                "})()\n"
            )
        )
        stdin.flush()

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
        self._write_state_to_stream(self.stdin, state_json)
        if opponent_command:
            self.stdin.write(f">{self.opponent_role} {opponent_command}\n")
        if player_command:
            self.stdin.write(f">{self.player_role} {player_command}\n")
        self.stdin.flush()
        snapshot = self._read_state_from_stream(self.stdin, self.stdout)
        state = cast(dict[str, Any], json.loads(snapshot))
        return StepResult(
            state=state,
            state_json=json.dumps(state, sort_keys=True, separators=(",", ":")),
            reward=self.reward(state),
            terminated=bool(state.get("ended")),
        )

    @classmethod
    def serialize_battle(cls, battle: DoubleBattle) -> Dict[str, Any]:
        role = battle.player_role or "p1"
        opponent_role = battle.opponent_role or ("p2" if role == "p1" else "p1")
        state = {
            "sentRequests": False,
            "debugMode": False,
            "forceRandomChance": None,
            "strictChoices": False,
            "formatData": {"id": battle.format or "", "effectOrder": 0},
            "formatid": battle.format or "",
            "gameType": "doubles",
            "activePerHalf": 2,
            "prngSeed": "sodium,0,0,0,0",
            "prng": [0, 0, 0, 1],
            "rated": battle.rating is not None,
            "reportExactHP": True,
            "reportPercentages": False,
            "supportCancel": False,
            "faintQueue": [],
            "inputLog": [],
            "messageLog": [],
            "sentLogPos": 0,
            "sentEnd": False,
            "requestState": "move" if battle.last_request else "team",
            "turn": battle.turn,
            "midTurn": False,
            "started": battle.turn > 0 or any(mon.revealed for mon in battle.team.values()),
            "ended": battle.finished,
            "effect": {"id": ""},
            "effectState": cls._effect_state(""),
            "event": {"id": ""},
            "events": None,
            "eventDepth": 0,
            "activeMove": None,
            "activePokemon": None,
            "activeTarget": None,
            "lastMove": None,
            "lastMoveLine": -1,
            "lastSuccessfulMoveThisTurn": None,
            "lastDamage": 0,
            "effectOrder": 0,
            "quickClawRoll": False,
            "speedOrder": [],
            "field": cls._serialize_field(battle),
        }
        state["sides"] = [
            cls._serialize_side(
                battle, role, battle.team, getattr(battle, "_active_pokemon", {}), True
            ),
            cls._serialize_side(
                battle,
                opponent_role,
                battle.opponent_team,
                getattr(battle, "_opponent_active_pokemon", {}),
                False,
            ),
        ]
        state["hints"] = []
        state["queue"] = []
        return state

    @staticmethod
    def _enum_to_showdown_id(value: Optional[Enum]) -> str:
        if value is None:
            return ""
        name = value.name.lower()
        parts = name.split("_")
        return "".join(part.capitalize() for part in parts)

    @classmethod
    def _pokemon_types(cls, pokemon: Pokemon) -> List[str]:
        types = pokemon.types
        pretty: List[str] = []
        for pokemon_type in types:
            pretty.append(cls._enum_to_showdown_id(pokemon_type))
        return pretty

    @staticmethod
    def _gender_to_str(gender: Optional[PokemonGender]) -> str:
        if gender is None:
            return ""
        if gender == PokemonGender.MALE:
            return "M"
        if gender == PokemonGender.FEMALE:
            return "F"
        return ""

    @staticmethod
    def _status_to_str(status: Optional[Status]) -> str:
        return "" if status is None else status.name.lower()

    @staticmethod
    def _effect_state(effect_id: str) -> Dict[str, Any]:
        return {"id": effect_id, "effectOrder": 0}

    @staticmethod
    def _serialize_move(move: Move) -> Dict[str, Any]:
        entry = move.entry
        return {
            "move": entry.get("name", move.id.title()),
            "id": move.id,
            "pp": move.current_pp,
            "maxpp": move.max_pp,
            "target": entry.get("target", "normal"),
            "disabled": False,
            "disabledSource": "",
            "used": getattr(move, "_is_last_used", False),
        }

    @classmethod
    def _serialize_pokemon(cls, pokemon: Pokemon, position: int, gen: int) -> Dict[str, Any]:
        species_id = pokemon.species or pokemon.base_species
        tera_type = pokemon.tera_type
        base_stats = pokemon.base_stats
        stored_stats = {
            stat: (pokemon.stats.get(stat) or 0) if pokemon.stats else 0
            for stat in ["hp", "atk", "def", "spa", "spd", "spe"]
        }
        boost_stats = pokemon.boosts or {}
        boosts = {
            "atk": boost_stats.get("atk", 0),
            "def": boost_stats.get("def", 0),
            "spa": boost_stats.get("spa", 0),
            "spd": boost_stats.get("spd", 0),
            "spe": boost_stats.get("spe", 0),
            "accuracy": boost_stats.get("accuracy", 0),
            "evasion": boost_stats.get("evasion", 0),
        }
        moveslots = [cls._serialize_move(move) for move in pokemon.moves.values()]
        while len(moveslots) < 4:
            moveslots.append(
                {
                    "move": "",
                    "id": "",
                    "pp": 0,
                    "maxpp": 0,
                    "target": "normal",
                    "disabled": True,
                    "disabledSource": "",
                    "used": False,
                }
            )
        data = GenData.from_gen(gen).pokedex.get(pokemon.species or pokemon.base_species, {})
        ability = pokemon.ability or data.get("abilities", {}).get("0", "")
        item = pokemon.item or ""
        set_entry = {
            "name": pokemon.name,
            "species": data.get("name", pokemon.species or pokemon.base_species),
            "gender": cls._gender_to_str(pokemon.gender),
            "shiny": pokemon.shiny,
            "level": pokemon.level,
            "moves": list(pokemon.moves.keys()),
            "ability": ability.title() if ability else "",
            "evs": {stat: 0 for stat in ["hp", "atk", "def", "spa", "spd", "spe"]},
            "ivs": {stat: 31 for stat in ["hp", "atk", "def", "spa", "spd", "spe"]},
            "item": item.title() if item else "",
            "teraType": cls._enum_to_showdown_id(tera_type),
        }
        pokemon_types = cls._pokemon_types(pokemon)
        tera_rep = cls._enum_to_showdown_id(getattr(pokemon, "_tera_type", None)) or cls._enum_to_showdown_id(
            tera_type
        )
        return {
            "m": {},
            "baseSpecies": f"[Species:{pokemon.base_species}]",
            "species": f"[Species:{species_id}]",
            "speciesState": cls._effect_state(species_id),
            "gender": cls._gender_to_str(pokemon.gender),
            "dynamaxLevel": 10,
            "gigantamax": False,
            "moveSlots": moveslots,
            "position": position,
            "details": pokemon._last_details if getattr(pokemon, "_last_details", "") else "",
            "status": cls._status_to_str(pokemon.status),
            "statusState": cls._effect_state(cls._status_to_str(pokemon.status)),
            "volatiles": {
                effect.name.lower(): {"id": effect.name.lower(), "effectOrder": 0, "turn": counter}
                for effect, counter in pokemon.effects.items()
            },
            "hpType": "",
            "hpPower": 60,
            "baseHpType": "",
            "baseHpPower": 60,
            "baseStoredStats": base_stats,
            "storedStats": stored_stats,
            "boosts": boosts,
            "baseAbility": ability,
            "ability": ability,
            "abilityState": cls._effect_state(ability),
            "item": item,
            "itemState": cls._effect_state(item),
            "lastItem": "",
            "usedItemThisTurn": False,
            "ateBerry": False,
            "trapped": False,
            "maybeTrapped": False,
            "maybeDisabled": False,
            "maybeLocked": False,
            "illusion": None,
            "transformed": False,
            "fainted": pokemon.fainted,
            "faintQueued": False,
            "subFainted": None,
            "formeRegression": False,
            "types": pokemon_types,
            "baseTypes": pokemon_types,
            "addedType": "",
            "knownType": True,
            "apparentType": "/".join(pokemon_types),
            "teraType": cls._enum_to_showdown_id(tera_type),
            "switchFlag": False,
            "forceSwitchFlag": False,
            "skipBeforeSwitchOutEventFlag": False,
            "draggedIn": None,
            "newlySwitched": False,
            "beingCalledBack": False,
            "lastMove": None,
            "lastMoveUsed": None,
            "moveThisTurn": "",
            "statsRaisedThisTurn": False,
            "statsLoweredThisTurn": False,
            "hurtThisTurn": None,
            "lastDamage": 0,
            "attackedBy": [],
            "timesAttacked": 0,
            "isActive": bool(pokemon.active),
            "activeTurns": getattr(pokemon, "_active_turns", 0),
            "activeMoveActions": 0,
            "previouslySwitchedIn": getattr(pokemon, "_previously_switched_in", 0),
            "truantTurn": False,
            "bondTriggered": False,
            "swordBoost": False,
            "shieldBoost": False,
            "syrupTriggered": False,
            "stellarBoostedTypes": [],
            "isStarted": pokemon.revealed,
            "duringMove": False,
            "weighthg": int(math.floor(pokemon.weight * 10)),
            "speed": stored_stats.get("spe", 0) or base_stats.get("spe", 0),
            "canMegaEvo": None,
            "canUltraBurst": None,
            "canGigantamax": None,
            "canTerastallize": tera_rep,
            "maxhp": pokemon.max_hp,
            "baseMaxhp": pokemon.max_hp,
            "hp": pokemon.current_hp,
            "set": set_entry,
        }

    @classmethod
    def _side_conditions_to_state(cls, conditions: Dict[SideCondition, int]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for condition, counter in conditions.items():
            key = cls._enum_to_showdown_id(condition)
            result[key] = {"id": key, "effectOrder": 0, "layers": counter}
        return result

    @classmethod
    def _serialize_side(
        cls,
        battle: DoubleBattle,
        role: str,
        team: Dict[str, Pokemon],
        active_map: Dict[str, Pokemon],
        is_player: bool,
    ) -> Dict[str, Any]:
        gen = battle.gen
        team_list = list(team.values())
        pokemon = [cls._serialize_pokemon(mon, idx, gen) for idx, mon in enumerate(team_list)]
        team_str = "".join(str(i + 1) for i in range(len(team_list)))
        foe = "[Side:p2]" if role == "p1" else "[Side:p1]"
        return {
            "foe": foe,
            "allySide": None,
            "lastSelectedMove": "",
            "id": role,
            "n": 0 if role == "p1" else 1,
            "name": battle.player_username if is_player else (battle.opponent_username or ""),
            "avatar": "",
            "pokemonLeft": sum(0 if mon.fainted else 1 for mon in team.values()),
            "active": [
                f"[Pokemon:{slot}]" for slot, mon in active_map.items() if slot.startswith(role)
            ],
            "faintedLastTurn": None,
            "faintedThisTurn": None,
            "totalFainted": sum(1 for mon in team.values() if mon.fainted),
            "zMoveUsed": battle.used_z_move if is_player else battle.opponent_used_z_move,
            "dynamaxUsed": battle.used_dynamax if is_player else battle.opponent_used_dynamax,
            "sideConditions": cls._side_conditions_to_state(
                battle.side_conditions if is_player else battle.opponent_side_conditions
            ),
            "slotConditions": [{} for _ in range(2)],
            "lastMove": None,
            "pokemon": pokemon,
            "team": team_str,
            "choice": {},
            "activeRequest": battle.last_request if is_player else None,
        }

    @classmethod
    def _serialize_field(cls, battle: DoubleBattle) -> Dict[str, Any]:
        weather = ""
        weather_state = cls._effect_state("")
        if battle.weather:
            weather_enum, start_turn = next(iter(battle.weather.items()))
            weather = cls._enum_to_showdown_id(weather_enum)
            weather_state = {"id": weather, "effectOrder": 0, "turn": start_turn}
        terrain = ""
        terrain_state = cls._effect_state("")
        pseudo: Dict[str, Any] = {}
        for field_effect, start_turn in battle.fields.items():
            key = cls._enum_to_showdown_id(field_effect)
            if field_effect.is_terrain:
                terrain = key
                terrain_state = {"id": key, "effectOrder": 0, "turn": start_turn}
            else:
                pseudo[key] = {"id": key, "effectOrder": 0, "turn": start_turn}
        return {
            "weather": weather,
            "weatherState": weather_state,
            "terrain": terrain,
            "terrainState": terrain_state,
            "pseudoWeather": pseudo,
        }


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
        command = self.command_from_order(order)
        self.children[command] = child
        self.order_lookup[command] = order
        return child

    def update(self, value: float) -> None:
        self.visits += 1
        self.total_value += value


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
        root_json = json.dumps(root_state, sort_keys=True, separators=(",", ":"))
        orders = self._extract_orders(root_state)
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
        state = ShowdownSimulator.serialize_battle(battle)
        format_id = cast(Optional[str], state.get("formatid")) or battle.format or "gen9vgc2024regg"
        simulator = ShowdownSimulator(format_id=format_id, player_role=role, opponent_role=opponent)
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
        command = MCTSNode.command_from_order(order)
        result = self.simulator.step(node.state_json, command)
        child_orders = self._extract_orders(result.state)
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
            orders = self._extract_orders(state)
            if not orders:
                break
            order = policy(orders)
            command = MCTSNode.command_from_order(order)
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

    def _extract_orders(self, state: dict[str, Any]) -> list[DoubleBattleOrder]:
        side = self._find_side(state, self.player_role)
        request = cast(Optional[dict[str, Any]], side.get("activeRequest"))
        if not request:
            return []
        active = cast(list[dict[str, Any]], request.get("active", []))
        force_switch = cast(list[bool], request.get("forceSwitch", [False] * len(active)))
        per_slot: list[list[tuple[SingleBattleOrder, Optional[int]]]] = []
        for slot, info in enumerate(active):
            options: list[tuple[SingleBattleOrder, Optional[int]]] = []
            if slot < len(force_switch) and force_switch[slot]:
                options.extend(self._switch_orders(side, slot))
            else:
                options.extend(self._move_orders(info, slot))
                trapped = info.get("trapped") or info.get("maybeTrapped")
                if not trapped:
                    options.extend(self._switch_orders(side, slot))
            if not options:
                options.append((SingleBattleOrder(order="/choose move 1"), None))
            per_slot.append(options)
        if not per_slot:
            return []
        orders: list[DoubleBattleOrder] = []
        for combo in itertools.product(*per_slot):
            if not self._valid_combo(combo):
                continue
            single_orders = [choice[0] for choice in combo]
            while len(single_orders) < 2:
                single_orders.append(PassBattleOrder())
            orders.append(
                DoubleBattleOrder(first_order=single_orders[0], second_order=single_orders[1])
            )
        return orders

    @staticmethod
    def _find_side(state: dict[str, Any], role: str) -> dict[str, Any]:
        sides = cast(list[dict[str, Any]], state.get("sides", []))
        for side in sides:
            if side.get("id") == role:
                return side
        raise KeyError(f"side {role} missing from state")

    @staticmethod
    def _default_target(target: Optional[str], slot: int) -> Optional[str]:
        if target is None:
            return None
        lowered = target.lower()
        if lowered in {"normal", "adjacentfoe", "adjacent"}:
            return "1" if slot == 0 else "2"
        if lowered in {"any", "randomnormal"}:
            return "1"
        return None

    @staticmethod
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

    @classmethod
    def _move_orders(
        cls, active_info: dict[str, Any], slot: int
    ) -> list[tuple[SingleBattleOrder, Optional[int]]]:
        decisions: list[tuple[SingleBattleOrder, Optional[int]]] = []
        move_entries = cast(list[dict[str, Any]], active_info.get("moves", []))
        for idx, move in enumerate(move_entries, start=1):
            if move.get("disabled"):
                continue
            target = cls._default_target(cast(Optional[str], move.get("target")), slot)
            command = f"/choose move {idx}"
            if target is not None:
                command += f" {target}"
            decisions.append((SingleBattleOrder(order=command), None))
        return decisions

    @staticmethod
    def _valid_combo(options: Sequence[tuple[SingleBattleOrder, Optional[int]]]) -> bool:
        switches = [switch for _, switch in options if switch is not None]
        return len(switches) == len(set(switches))
