import base64
import json
import math
import select
import subprocess
from enum import Enum
from typing import Any

from poke_env.battle import DoubleBattle, Move, Pokemon, PokemonGender, SideCondition, Status
from poke_env.data import GenData
from poke_env.player import Player


class Simulator:
    def __init__(self, battle: DoubleBattle, packed_team: str):
        self.battle = battle
        self.process = subprocess.Popen(
            ["pokemon-showdown/pokemon-showdown", "simulate-battle"],
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
        self.stdin.write(
            f"""
>start {{"formatid":"{battle.format}"}}
>player p1 {{"name":"Player 1","team":"{packed_team}"}}
>player p2 {{"name":"Player 2","team":"{packed_team}"}}
"""
        )
        self.stdin.flush()
        msg = self.stdout.readline()
        print("reading dead msg:", msg)
        while True:
            ready, _, _ = select.select([self.stdout.fileno()], [], [], 0.1)
            if not ready:
                break
            msg = self.stdout.readline()
            print("reading dead msg:", msg)
        print("FIRST:", self.read_state())
        self.write_state(self.serialize_battle(battle))
        print("SECOND:", self.read_state())

    def read_state(self) -> dict[str, Any]:
        self.stdin.write(">eval JSON.stringify(battle && battle.toJSON())\n")
        self.stdin.flush()
        for msg in self.stdout:
            if not msg.startswith("||<<< "):
                continue
            if "||<<< error" in msg:
                raise RuntimeError(msg)
            return json.loads(msg.strip()[7:-1])
        raise LookupError("unable to read battle state from showdown")

    def write_state(self, state: dict[str, Any]):
        state_str = json.dumps(state, separators=(",", ":"))
        payload = base64.b64encode(state_str.encode()).decode()
        self.stdin.write(
            (
                ">eval (() => { "
                'const State = require("./state").State; '
                f'const restored = State.deserializeBattle(JSON.parse(Buffer.from("{payload}", "base64").toString())); '
                "restored.send = battle.send; "
                "this.battle = restored; "
                "})()\n"
            )
        )
        self.stdin.flush()
        print(self.battle.player_role, "SUCCESSFULLY WROTE STATE")

    def step(self, player_command: str | None, opponent_command: str | None):
        print(f"Stepping with commands: {player_command} | {opponent_command}", flush=True)
        if player_command:
            self.stdin.write(f">{self.battle.player_role} {player_command}\n")
        if opponent_command:
            self.stdin.write(f">{self.battle.opponent_role} {opponent_command}\n")
        for msg in self.stdout:
            print(msg, flush=True)
            split_msg = msg.strip().split("|")
            if not split_msg:
                continue
            elif len(split_msg) == 1:
                pass
            elif split_msg[1] == "":
                self.battle.parse_message(split_msg)
            elif split_msg[1] in Player.MESSAGES_TO_IGNORE:
                pass
            elif split_msg[1] == "request":
                if split_msg[2]:
                    request = json.loads(split_msg[2])
                    if "teamPreview" in request and request["teamPreview"]:
                        for p in request["side"]["pokemon"]:
                            p["active"] = False
                    self.battle.parse_request(request)
            elif split_msg[1] == "showteam":
                pass
            elif split_msg[1] == "win" or split_msg[1] == "tie":
                if split_msg[1] == "win":
                    self.battle.won_by(split_msg[2])
                else:
                    self.battle.tied()
            elif split_msg[1] == "error":
                pass
            elif split_msg[1] == "bigerror":
                pass
            else:
                self.battle.parse_message(split_msg)

    def __del__(self):
        self.process.terminate()
        self.process.wait()

    @classmethod
    def serialize_battle(cls, battle: DoubleBattle) -> dict[str, Any]:
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
            "log": [],
            "sentLogPos": -1,
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

    @classmethod
    def _serialize_field(cls, battle: DoubleBattle) -> dict[str, Any]:
        weather = ""
        weather_state = cls._effect_state("")
        if battle.weather:
            weather_enum, start_turn = next(iter(battle.weather.items()))
            weather = cls._enum_to_showdown_id(weather_enum)
            weather_state = {"id": weather, "effectOrder": 0, "turn": start_turn}
        terrain = ""
        terrain_state = cls._effect_state("")
        pseudo: dict[str, Any] = {}
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

    @classmethod
    def _serialize_pokemon(cls, pokemon: Pokemon, position: int, gen: int) -> dict[str, Any]:
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
        tera_rep = cls._enum_to_showdown_id(
            getattr(pokemon, "_tera_type", None)
        ) or cls._enum_to_showdown_id(tera_type)
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

    @staticmethod
    def _serialize_move(move: Move) -> dict[str, Any]:
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
    def _pokemon_types(cls, pokemon: Pokemon) -> list[str]:
        types = pokemon.types
        pretty: list[str] = []
        for pokemon_type in types:
            pretty.append(cls._enum_to_showdown_id(pokemon_type))
        return pretty

    @staticmethod
    def _gender_to_str(gender: PokemonGender | None) -> str:
        if gender is None:
            return ""
        if gender == PokemonGender.MALE:
            return "M"
        if gender == PokemonGender.FEMALE:
            return "F"
        return ""

    @staticmethod
    def _status_to_str(status: Status | None) -> str:
        return "" if status is None else status.name.lower()

    @staticmethod
    def _effect_state(effect_id: str) -> dict[str, Any]:
        return {"id": effect_id, "effectOrder": 0}

    @classmethod
    def _serialize_side(
        cls,
        battle: DoubleBattle,
        role: str,
        team: dict[str, Pokemon],
        active_map: dict[str, Pokemon],
        is_player: bool,
    ) -> dict[str, Any]:
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
            "sideConditions": cls._serialize_side_conditions(
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
    def _serialize_side_conditions(cls, conditions: dict[SideCondition, int]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for condition, counter in conditions.items():
            key = cls._enum_to_showdown_id(condition)
            result[key] = {"id": key, "effectOrder": 0, "layers": counter}
        return result

    @staticmethod
    def _enum_to_showdown_id(value: Enum | None) -> str:
        if value is None:
            return ""
        name = value.name.lower()
        parts = name.split("_")
        return "".join(part.capitalize() for part in parts)
