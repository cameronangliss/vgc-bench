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
        self.opp_battle = self._derive_opp_battle(battle)
        # Tracks whether we've already submitted a choice for a side that hasn't been
        # consumed by the simulator yet. This prevents us from repeatedly re-sending
        # the opponent's choice after the other side makes an invalid choice, which
        # can trigger Showdown's "Can't undo" errors.
        self._pending_choices: dict[str, bool] = {"p1": False, "p2": False}
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
        self._request_sync()

    def _derive_opp_battle(self, battle: DoubleBattle) -> DoubleBattle:
        role = battle.opponent_role or ("p2" if (battle.player_role or "p1") == "p1" else "p1")
        opp_battle = DoubleBattle(
            f"{battle.battle_tag}-opp",
            battle.opponent_username or "opponent",
            None,  # type: ignore
            self.battle.gen,
            save_replays=False,
        )
        opp_battle._player_role = role
        assert battle.opponent_username is not None
        opp_battle.player_username = battle.opponent_username
        opp_battle.opponent_username = battle.player_username
        opp_battle._team = dict(battle.opponent_team)
        opp_battle._opponent_team = dict(battle.team)
        opp_battle._active_pokemon = dict(getattr(battle, "_opponent_active_pokemon", {}))
        opp_battle._opponent_active_pokemon = dict(getattr(battle, "_active_pokemon", {}))
        opp_battle._side_conditions = dict(battle.opponent_side_conditions)
        opp_battle._opponent_side_conditions = dict(battle.side_conditions)
        opp_battle._weather = dict(battle.weather)
        opp_battle._fields = dict(battle.fields)
        opp_battle.turn = battle.turn
        opp_battle.in_team_preview = getattr(battle, "in_team_preview", False)
        return opp_battle

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

    def _request_sync(self):
        # Ensure Showdown emits fresh requests after we restore state, then drain
        # them from stdout so the next `step` starts from a clean boundary.
        self.stdin.write(">eval (() => { battle.sentRequests = false; battle.makeRequest(); })()\n")
        self.stdin.flush()
        # Drain output until we reach the request messages. We intentionally do NOT
        # apply them to poke-env battle objects here: at initialization time, the
        # caller's battle already represents the desired state, and parsing another
        # request can mutate/corrupt it.
        needed_requests: set[str] = set()
        if self.battle.player_role:
            needed_requests.add(self.battle.player_role)
        if self.battle.opponent_role:
            needed_requests.add(self.battle.opponent_role)
        if not needed_requests:
            needed_requests.update({"p1", "p2"})

        seen_requests: set[str] = set()
        for msg in self.stdout:
            split_msg = msg.strip().split("|")
            if not split_msg or len(split_msg) < 2:
                continue
            if split_msg[1] == "request" and len(split_msg) > 2 and split_msg[2]:
                request = json.loads(split_msg[2])
                target_side = request.get("side", {}).get("id")
                if target_side:
                    seen_requests.add(str(target_side))
                if seen_requests >= needed_requests:
                    break

    def step(self, player_command: str | None, opponent_command: str | None):
        print(f"Stepping with commands: {player_command} | {opponent_command}", flush=True)
        if player_command:
            cleaned = player_command
            if cleaned.startswith("/choose "):
                cleaned = cleaned[len("/choose ") :]
            side = self.battle.player_role or "p1"
            if cleaned == "undo" or not self._pending_choices.get(side, False):
                self.stdin.write(f">{side} {cleaned}\n")
                self._pending_choices[side] = cleaned != "undo"
        if opponent_command:
            cleaned = opponent_command
            if cleaned.startswith("/choose "):
                cleaned = cleaned[len("/choose ") :]
            side = self.battle.opponent_role or (
                "p2" if (self.battle.player_role or "p1") == "p1" else "p1"
            )
            if cleaned == "undo" or not self._pending_choices.get(side, False):
                self.stdin.write(f">{side} {cleaned}\n")
                self._pending_choices[side] = cleaned != "undo"
        # Track which sides have received their newest request so both battle
        # objects stay in sync before returning control to the caller.
        needed_requests: set[str] = set()
        seen_requests: set[str] = set()
        if self.battle.player_role:
            needed_requests.add(self.battle.player_role)
        if self.battle.opponent_role:
            needed_requests.add(self.battle.opponent_role)
        if not needed_requests:
            needed_requests.add("p1")
        current_sideupdate: str | None = None
        awaiting_side_id = False
        for msg in self.stdout:
            print(msg, flush=True)
            raw = msg.strip()
            if raw == "sideupdate":
                awaiting_side_id = True
                current_sideupdate = None
                continue
            if raw == "update":
                awaiting_side_id = False
                current_sideupdate = None
                continue
            if awaiting_side_id and raw in {"p1", "p2", "p3", "p4"}:
                current_sideupdate = raw
                awaiting_side_id = False
                continue

            split_msg = raw.split("|")
            if not split_msg or len(split_msg) < 2:
                continue
            elif split_msg[1] == "":
                self.battle.parse_message(split_msg)
            elif split_msg[1] in Player.MESSAGES_TO_IGNORE:
                pass
            elif split_msg[1] == "request":
                if split_msg[2]:
                    request = json.loads(split_msg[2])
                    target_side = request.get("side", {}).get("id")
                    for b in (self.battle, self.opp_battle):
                        if not b or target_side != b.player_role:
                            continue
                        if request.get("active"):
                            b._active_pokemon = {}
                        if "teamPreview" in request and request["teamPreview"]:
                            for p in request["side"]["pokemon"]:
                                p["active"] = False
                        b.parse_request(request)
                        seen_requests.add(target_side)
                    if target_side:
                        self._pending_choices[target_side] = bool(request.get("wait"))

                    if seen_requests >= needed_requests:
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
                if current_sideupdate:
                    self._pending_choices[current_sideupdate] = False
                # Stop so caller can recompute a legal choice.
                break
            elif split_msg[1] == "bigerror":
                break
            else:
                self.battle.parse_message(split_msg)

    def __del__(self):
        self.process.terminate()
        self.process.wait()

    def choose_opponent_order(self) -> str | None:
        opp = self.opp_battle
        if not opp:
            return None
        req = getattr(opp, "last_request", {}) or {}
        if req.get("teamPreview"):
            team_size = req.get("maxChosenTeamSize", 2)
            picks = ",".join(str(i + 1) for i in range(team_size))
            return f"team {picks}"
        if opp._wait:
            return None
        return Player.choose_random_move(opp).message

    @classmethod
    def serialize_battle(cls, battle: DoubleBattle) -> dict[str, Any]:
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
        player_side = cls._serialize_side(
            battle, role, battle.team, getattr(battle, "_active_pokemon", {}), True
        )
        opponent_side = cls._serialize_side(
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
        active_mons: list[Pokemon] = []
        if active_map:
            for slot_suffix in ("a", "b"):
                slot = f"{role}{slot_suffix}"
                mon = active_map.get(slot)
                if mon is not None and mon not in active_mons:
                    active_mons.append(mon)
            # Include any additional actives we might have (shouldn't happen in doubles,
            # but keeps this resilient to edge cases).
            for slot, mon in active_map.items():
                if not slot.startswith(role):
                    continue
                if mon not in active_mons:
                    active_mons.append(mon)
        else:
            active_mons = [mon for mon in team_list if getattr(mon, "active", False)]

        ordered_team_list = active_mons + [mon for mon in team_list if mon not in active_mons]

        pokemon = [
            cls._serialize_pokemon(mon, idx, gen) for idx, mon in enumerate(ordered_team_list)
        ]
        team_str = "".join(str(i + 1) for i in range(len(team_list)))
        foe = "[Side:p2]" if role == "p1" else "[Side:p1]"
        # Side.active should be length-2 (doubles) with refs for current actives.
        active_slots: list[Any] = [None, None]
        for idx in range(min(2, len(active_mons))):
            slot_id = f"{role}{chr(ord('a') + idx)}"
            active_slots[idx] = f"[Pokemon:{slot_id}]"

        # Mark which mons are active in their serialized entries
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
