import base64
import json
import math
import subprocess
from copy import deepcopy
from enum import Enum
from typing import Any

from poke_env.battle import DoubleBattle, Move, Pokemon, PokemonGender, SideCondition, Status
from poke_env.data import GenData
from poke_env.player import Player


class Simulator:
    def __init__(self, battle: DoubleBattle, verbose: bool = False):
        self.battle = battle
        self.verbose = verbose
        self.opp_battle = self._derive_opp_battle(battle)
        self.process = subprocess.Popen(
            ["pokemon-showdown/pokemon-showdown", "simulate-battle", "--skip-build"],
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
        assert battle._packed_team is not None
        assert battle._opponent_packed_team is not None
        p1_packed_team, p2_packed_team = (
            (battle._packed_team, battle._opponent_packed_team)
            if battle.player_role == "p1"
            else (battle._opponent_packed_team, battle._packed_team)
        )
        p1_username, p2_username = (
            (battle.player_username, battle.opponent_username)
            if battle.player_role == "p1"
            else (battle.opponent_username, battle.player_username)
        )
        self.stdin.write(
            f"""
>start {{"formatid":"{battle.format}"}}
>player p1 {{"name":"{p1_username}","team":"{p1_packed_team}"}}
>player p2 {{"name":"{p2_username}","team":"{p2_packed_team}"}}
"""
        )
        num_requests_seen = 0
        for msg in self.stdout:
            if "|request|" in msg:
                num_requests_seen += 1
                if num_requests_seen == 2:
                    break
        self.write_state(self.serialize_battle(battle))

    @staticmethod
    def _derive_opp_battle(battle: DoubleBattle) -> DoubleBattle:
        opp_battle = deepcopy(battle)
        opp_battle.logger = None
        assert battle.opponent_username is not None
        opp_battle._player_username = battle.opponent_username
        opp_battle._opponent_username = battle.player_username
        opp_battle._player_role = battle.opponent_role
        team = opp_battle.team
        opp_battle._team = opp_battle.opponent_team
        opp_battle._opponent_team = team
        active_pokemon = battle._active_pokemon
        opp_battle._active_pokemon = battle._opponent_active_pokemon
        opp_battle._opponent_active_pokemon = active_pokemon
        side_conditions = battle.side_conditions
        opp_battle._side_conditions = battle.opponent_side_conditions
        opp_battle._opponent_side_conditions = side_conditions
        return opp_battle

    def write_state(self, state: dict[str, Any]):
        state_str = json.dumps(state, separators=(",", ":"))
        payload = base64.b64encode(state_str.encode()).decode()
        self.stdin.write(
            (
                ">eval ("
                "    () => {"
                '        const State = require("./state").State;'
                f'       const restored = State.deserializeBattle(JSON.parse(Buffer.from("{payload}", "base64").toString()));'
                "        restored.send = battle.send;"
                "        this.battle = restored;"
                "        restored.sentRequests = false;"
                "        restored.makeRequest();"
                "    }"
                ")()\n"
            )
        )
        num_requests_seen = 0
        for msg in self.stdout:
            if self.verbose:
                print(msg, flush=True)
            split_msg = msg.strip().split("|")
            if not split_msg or len(split_msg) <= 2:
                continue
            if split_msg[1] == "request" and len(split_msg) > 2:
                request = json.loads(split_msg[2])
                battle = (
                    self.battle
                    if self.battle.player_role == request["side"]["id"]
                    else self.opp_battle
                )
                battle.parse_request(request)
                if "teamPreview" in request and request["teamPreview"]:
                    for p in request["side"]["pokemon"]:
                        p["active"] = False
                num_requests_seen += 1
                if num_requests_seen == 2:
                    break

    def step(self, player_command: str | None, opponent_command: str | None):
        if self.verbose:
            print(f"{player_command}, {opponent_command}", flush=True)
        if player_command:
            player_command = player_command.replace("/choose ", "")
            self.stdin.write(f">{self.battle.player_role} {player_command}\n")
        if opponent_command:
            opponent_command = opponent_command.replace("/choose ", "")
            self.stdin.write(f">{self.battle.opponent_role} {opponent_command}\n")
        num_requests_seen = 0
        last_msg = None
        for msg in self.stdout:
            if msg == last_msg:
                continue
            if self.verbose:
                print(msg, flush=True)
            split_msg = msg.strip().split("|")
            # copy of a bunch of logic from Player._handle_battle_message()
            if not split_msg or len(split_msg) < 2:
                continue
            elif split_msg[1] == "":
                self.battle.parse_message(split_msg)
            elif split_msg[1] in Player.MESSAGES_TO_IGNORE:
                pass
            elif split_msg[1] == "request":
                if split_msg[2]:
                    request = json.loads(split_msg[2])
                    battle = (
                        self.battle
                        if self.battle.player_role == request["side"]["id"]
                        else self.opp_battle
                    )
                    battle.parse_request(request)
                    num_requests_seen += 1
                    if num_requests_seen == 2:
                        break
            elif split_msg[1] == "showteam":
                pass
            elif split_msg[1] == "win" or split_msg[1] == "tie":
                if split_msg[1] == "win":
                    self.battle.won_by(split_msg[2])
                else:
                    self.battle.tied()
                break
            elif split_msg[1] == "error":
                raise RuntimeError(f"Simulator error: {'|'.join(split_msg[2:])}")
            elif split_msg[1] == "bigerror":
                raise RuntimeError(f"Simulator bigerror: {'|'.join(split_msg[2:])}")
            else:
                self.battle.parse_message(split_msg)
            last_msg = msg

    def __del__(self):
        self.process.terminate()
        self.process.wait()

    @staticmethod
    def serialize_battle(battle: DoubleBattle) -> dict[str, Any]:
        role = battle.player_role or "p1"
        opponent_role = battle.opponent_role or ("p2" if role == "p1" else "p1")
        last_request = battle.last_request or {}
        if last_request.get("teamPreview"):
            request_state = "teampreview"
        elif battle.turn == 0:
            request_state = "teampreview"
        elif last_request.get("forceSwitch"):
            request_state = "switch"
        elif last_request:
            request_state = "move"
        elif getattr(battle, "in_team_preview", False):
            request_state = "teampreview"
        else:
            request_state = "move" if battle.turn else "teampreview"
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
            "requestState": request_state,
            "turn": battle.turn,
            "midTurn": False,
            "started": True,
            "ended": battle.finished,
            "effect": {"id": ""},
            "effectState": Simulator._effect_state(""),
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
            "field": Simulator._serialize_field(battle),
        }
        player_side = Simulator._serialize_side(
            battle, role, battle.team, getattr(battle, "_active_pokemon", {}), True
        )
        opponent_side = Simulator._serialize_side(
            battle,
            opponent_role,
            battle.opponent_team,
            getattr(battle, "_opponent_active_pokemon", {}),
            False,
        )
        sides_by_id = {role: player_side, opponent_role: opponent_side}
        state["sides"] = [sides_by_id.get("p1"), sides_by_id.get("p2")]
        if any(side is None for side in state["sides"]):
            raise ValueError(
                f"Unable to serialize battle sides: player_role={role!r} opponent_role={opponent_role!r}"
            )
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
        data = GenData.from_gen(gen).pokedex.get(species_id, {})
        ability = pokemon.ability or data.get("abilities", {}).get("0", "")
        item = pokemon.item or ""
        # Important: in Showdown's Pokemon constructor, if `set.name === set.species`,
        # it rewrites `set.name` to the base species (e.g., "Ogerpon" for
        # "Ogerpon-Cornerstone"). To preserve poke-env's identifier naming (and avoid
        # get_pokemon() trying to "add" an extra mon mid-battle), ensure these strings
        # are never identical by using an ID-ish string for `species`.
        display_species = data.get("name", pokemon.species or pokemon.base_species)
        set_entry = {
            "name": pokemon.name or display_species,
            "species": species_id,
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
            "maxhp": pokemon.max_hp or stored_stats.get("hp", 0) or base_stats.get("hp", 0),
            "baseMaxhp": pokemon.max_hp or stored_stats.get("hp", 0) or base_stats.get("hp", 0),
            "hp": (
                pokemon.current_hp
                if pokemon.current_hp
                else stored_stats.get("hp", 0) or base_stats.get("hp", 0)
            ),
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
        # Pokemon Showdown stores "active" mons at positions 0/1 in `side.pokemon`
        # (and uses those positions to generate refs like `[Pokemon:p1a]`/`[Pokemon:p1b]`).
        # Our input `team` dict has no such ordering guarantee, so we must reorder
        # the list to put current actives first or we will restore a battle where
        # the wrong mons are active (leading to invalid choice errors).
        team_list = list(team.values())

        # Find which Pokemon are active
        active_mons: list[Pokemon] = []
        if active_map:
            for slot_suffix in ("a", "b"):
                slot = f"{role}{slot_suffix}"
                mon = active_map.get(slot)
                if mon is not None:
                    # Find this mon in team_list by identity or species
                    for team_mon in team_list:
                        if team_mon is mon or team_mon.species == mon.species:
                            if team_mon not in active_mons:
                                active_mons.append(team_mon)
                            break
        else:
            active_mons = [mon for mon in team_list if getattr(mon, "active", False)]

        # REORDER the team: active Pokemon must be at positions 0 and 1
        # This is required because Showdown's active slots always reference positions 0/1
        ordered_team_list = active_mons[:2] + [mon for mon in team_list if mon not in active_mons]
        # Pad if we don't have 2 actives
        while len(ordered_team_list) < len(team_list):
            for mon in team_list:
                if mon not in ordered_team_list:
                    ordered_team_list.append(mon)
                    break

        pokemon = [
            cls._serialize_pokemon(mon, idx, gen) for idx, mon in enumerate(ordered_team_list)
        ]
        team_str = "".join(str(i + 1) for i in range(len(team_list)))
        foe = "[Side:p2]" if role == "p1" else "[Side:p1]"

        # Active slots MUST reference positions 0 and 1 (slots a and b)
        active_slots: list[Any] = [None, None]
        for idx in range(min(2, len(active_mons))):
            slot_id = f"{role}{chr(ord('a') + idx)}"  # p1a/p1b or p2a/p2b
            active_slots[idx] = f"[Pokemon:{slot_id}]"

        # Mark positions 0 and 1 as active
        for idx, mon in enumerate(pokemon):
            mon["isActive"] = idx < len(active_mons) and idx < 2
            if mon["isActive"]:
                mon["activeTurns"] = mon.get("activeTurns", 0) or 1
                mon["newlySwitched"] = False
                mon["isStarted"] = True
        return {
            "foe": foe,
            "allySide": None,
            "lastSelectedMove": "",
            "id": role,
            "n": 0 if role == "p1" else 1,
            "name": battle.player_username if is_player else (battle.opponent_username or ""),
            "avatar": "",
            "pokemonLeft": sum(0 if mon.fainted else 1 for mon in team.values()),
            "active": active_slots,
            "faintedLastTurn": None,
            "faintedThisTurn": None,
            "totalFainted": sum(1 for mon in team.values() if mon.fainted),
            "zMoveUsed": battle.used_z_move if is_player else battle.opponent_used_z_move,
            "dynamaxUsed": battle.used_dynamax if is_player else battle.opponent_used_dynamax,
            "sideConditions": cls._serialize_side_conditions(
                battle.side_conditions if is_player else battle.opponent_side_conditions
            ),
            "slotConditions": [{} for _ in range(len(active_slots) or 2)],
            "lastMove": None,
            "pokemon": pokemon,
            "team": team_str,
            "choice": {
                "cantUndo": False,
                "error": "",
                "actions": [],
                "forcedSwitchesLeft": 0,
                "forcedPassesLeft": 0,
                "switchIns": [],
                "zMove": False,
                "mega": False,
                "ultra": False,
                "dynamax": False,
                "terastallize": False,
            },
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
