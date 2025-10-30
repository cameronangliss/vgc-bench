import base64
import json
import math
import subprocess
from enum import Enum
from typing import IO, Any, Dict, List, Optional

from poke_env.battle import DoubleBattle, Move, Pokemon, PokemonGender, SideCondition, Status
from poke_env.data import GenData


def _enum_to_showdown_id(value: Optional[Enum]) -> str:
    if value is None:
        return ""
    name = value.name.lower()
    parts = name.split("_")
    return "".join(part.capitalize() for part in parts)


def _pokemon_types(pokemon: Pokemon) -> List[str]:
    types = pokemon.types
    pretty: List[str] = []
    for t in types:
        pretty.append(_enum_to_showdown_id(t))
    return pretty


def _gender_to_str(gender: Optional[PokemonGender]) -> str:
    if gender is None:
        return ""
    if gender == PokemonGender.MALE:
        return "M"
    if gender == PokemonGender.FEMALE:
        return "F"
    return ""


def _status_to_str(status: Optional[Status]) -> str:
    return "" if status is None else status.name.lower()


def _effect_state(effect_id: str) -> Dict[str, Any]:
    return {"id": effect_id, "effectOrder": 0}


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


def _serialize_pokemon(pokemon: Pokemon, position: int, side_id: str, gen: int) -> Dict[str, Any]:
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
    moveslots = [_serialize_move(move) for move in pokemon.moves.values()]
    # Guarantee 4 entries for compatibility with Showdown
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
        "gender": _gender_to_str(pokemon.gender),
        "shiny": pokemon.shiny,
        "level": pokemon.level,
        "moves": list(pokemon.moves.keys()),
        "ability": ability.title() if ability else "",
        "evs": {stat: 0 for stat in ["hp", "atk", "def", "spa", "spd", "spe"]},
        "ivs": {stat: 31 for stat in ["hp", "atk", "def", "spa", "spd", "spe"]},
        "item": item.title() if item else "",
        "teraType": _enum_to_showdown_id(tera_type),
    }
    return {
        "m": {},
        "baseSpecies": f"[Species:{pokemon.base_species}]",
        "species": f"[Species:{species_id}]",
        "speciesState": _effect_state(species_id),
        "gender": _gender_to_str(pokemon.gender),
        "dynamaxLevel": 10,
        "gigantamax": False,
        "moveSlots": moveslots,
        "position": position,
        "details": pokemon._last_details if getattr(pokemon, "_last_details", "") else "",
        "status": _status_to_str(pokemon.status),
        "statusState": _effect_state(_status_to_str(pokemon.status)),
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
        "abilityState": _effect_state(ability),
        "item": item,
        "itemState": _effect_state(item),
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
        "types": _pokemon_types(pokemon),
        "baseTypes": _pokemon_types(pokemon),
        "addedType": "",
        "knownType": True,
        "apparentType": "/".join(_pokemon_types(pokemon)),
        "teraType": _enum_to_showdown_id(tera_type),
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
        "canTerastallize": _enum_to_showdown_id(getattr(pokemon, "_tera_type", None))
        or _enum_to_showdown_id(tera_type),
        "maxhp": pokemon.max_hp,
        "baseMaxhp": pokemon.max_hp,
        "hp": pokemon.current_hp,
        "set": set_entry,
    }


def _side_conditions_to_state(conditions: Dict[SideCondition, int]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for condition, counter in conditions.items():
        key = _enum_to_showdown_id(condition)
        result[key] = {"id": key, "effectOrder": 0, "layers": counter}
    return result


def _serialize_side(
    battle: DoubleBattle,
    role: str,
    team: Dict[str, Pokemon],
    active_map: Dict[str, Pokemon],
    is_player: bool,
) -> Dict[str, Any]:
    gen = battle.gen
    team_list = list(team.values())
    pokemon = [_serialize_pokemon(mon, idx, role, gen) for idx, mon in enumerate(team_list)]
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
        "sideConditions": _side_conditions_to_state(
            battle.side_conditions if is_player else battle.opponent_side_conditions
        ),
        "slotConditions": [{} for _ in range(2)],
        "lastMove": None,
        "pokemon": pokemon,
        "team": team_str,
        "choice": {},
        "activeRequest": battle.last_request if is_player else None,
    }


def _serialize_field(battle: DoubleBattle) -> Dict[str, Any]:
    weather = ""
    weather_state = _effect_state("")
    if battle.weather:
        weather_enum, start_turn = next(iter(battle.weather.items()))
        weather = _enum_to_showdown_id(weather_enum)
        weather_state = {"id": weather, "effectOrder": 0, "turn": start_turn}
    terrain = ""
    terrain_state = _effect_state("")
    pseudo: Dict[str, Any] = {}
    for field_effect, start_turn in battle.fields.items():
        key = _enum_to_showdown_id(field_effect)
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


def serializePokeEnvBattle(battle: DoubleBattle) -> Dict[str, Any]:
    """Approximate Pokemon Showdown `State.serializeBattle` output for a poke-env DoubleBattle."""
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
        "effectState": _effect_state(""),
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
        "field": _serialize_field(battle),
    }

    state["sides"] = [
        _serialize_side(battle, role, battle.team, getattr(battle, "_active_pokemon", {}), True),
        _serialize_side(
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


def read_state(stdin: IO[str], stdout: IO[str]) -> str:
    stdin.write(">eval JSON.stringify(battle.toJSON())\n")
    for msg in stdout:
        if not msg.startswith("||<<< "):
            continue
        return msg.strip()[7:-1]
    raise LookupError()


def write_state(stdin: IO[str], state: str):
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


def main():
    process = subprocess.Popen(
        ["pokemon-showdown/pokemon-showdown", "simulate-battle"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    stdin = process.stdin
    stdout = process.stdout
    assert stdin is not None
    assert stdout is not None
    stdin.write(
        """
>start {"formatid":"gen9randomdoublebattle"}
>player p1 {"name":"Player 1"}
>player p2 {"name":"Player 2"}
"""
    )
    state = read_state(stdin, stdout)
    print("STATE:", state)
    write_state(stdin, state)
    for msg in stdout:
        print(msg)
        if "|request|" in msg:
            _, _, request_msg = msg.split("|")
            request = json.loads(request_msg)
            player_id = request["side"]["id"]
            if "wait" not in request:
                response = f">{player_id} default\n"
                stdin.write(response)
                print(response)
        elif msg.startswith('{"winner":'):
            break
    stdin.close()
    process.terminate()
    process.wait()


if __name__ == "__main__":
    main()
