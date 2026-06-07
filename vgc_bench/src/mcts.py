"""MCTS guidance utilities backed by poke-engine-doubles.

This module is an adapter: VGC-Bench keeps using poke-env and Showdown for the
real rollouts, while poke-engine-doubles searches the *current* decision and
produces AlphaZero-style policy targets (during training) or move choices (for
evaluation).

The hard part is converting poke-env's partially-observed, "turns-elapsed"
battle view into poke-engine's fully-specified, "turns-remaining" state without
violating any of the engine's internal invariants. The engine is reliable when
fed a valid state; when it is fed an invalid one it panics (a Rust panic that
surfaces in Python as ``pyo3_runtime.PanicException``). We therefore build state
that satisfies the engine's invariants and run in *strict* mode so that any
remaining conversion gap surfaces loudly rather than corrupting training.

Known engine invariants enforced here (discovered empirically against
poke-engine-doubles 0.0.7):

* ``VolatileStatusDurations`` fields are *turns remaining*, not turns elapsed.
* ``taunt`` remaining must be <= 2 while the ``taunt`` volatile is active.
* ``yawn`` remaining must be <= 1 while the ``yawn`` volatile is active.
* the ``encore`` volatile may only be active when ``last_used_move`` is a real
  move (``move:0``..``move:3``), never ``move:none``.
* the ``substitute`` volatile may only be active when ``substitute_health`` > 0.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt
from poke_env.battle import (
    AbstractBattle,
    DoubleBattle,
    Effect,
    Field,
    Pokemon,
    PokemonType,
    SideCondition,
    Status,
    Weather,
)
from poke_env.data import to_id_str
from poke_env.environment import DoublesEnv
from poke_env.player import BattleOrder, DefaultBattleOrder, Player

try:
    from poke_engine import Move as EngineMove  # type: ignore[import-untyped]
    from poke_engine import Pokemon as EnginePokemon
    from poke_engine import (
        PokemonIndex,
        Side,
        SideConditions,
        SideSlot,
        State,
        VolatileStatusDurations,
        monte_carlo_tree_search,
    )

    POKE_ENGINE_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - exercised when optional dep is absent
    EngineMove = None  # type: ignore[assignment]
    EnginePokemon = None  # type: ignore[assignment]
    PokemonIndex = None  # type: ignore[assignment]
    Side = None  # type: ignore[assignment]
    SideConditions = None  # type: ignore[assignment]
    SideSlot = None  # type: ignore[assignment]
    State = None  # type: ignore[assignment]
    VolatileStatusDurations = None  # type: ignore[assignment]
    monte_carlo_tree_search = None  # type: ignore[assignment]
    POKE_ENGINE_IMPORT_ERROR = exc


# Per-volatile (total_duration, max_turns_remaining_while_active). ``total`` is
# used to turn poke-env's elapsed counter into a remaining count; the cap is the
# largest value the engine accepts while the volatile is active.
_VOLATILE_DURATIONS: dict[Effect, tuple[int, int]] = {
    Effect.CONFUSION: (4, 4),
    Effect.ENCORE: (3, 3),
    Effect.LOCKED_MOVE: (3, 3),
    Effect.SLOW_START: (5, 5),
    Effect.TAUNT: (3, 2),
    Effect.YAWN: (2, 1),
}


@dataclass(frozen=True)
class MCTSGuidanceConfig:
    """Configuration for collecting MCTS policy targets during training."""

    duration_ms: int = 50
    threads: int = 1
    sample_rate: float = 1.0
    target_temperature: float = 1.0
    max_targets: int = 16
    strict: bool = True


class MCTSGuidance:
    """Run MCTS and return sparse pair-action visit targets."""

    def __init__(self, config: MCTSGuidanceConfig):
        ensure_poke_engine_available()
        self.config = config

    def search_policy_target(self, battle: DoubleBattle) -> dict[str, Any]:
        """Return an info dict containing sparse AlphaZero target pairs."""
        # The engine's MCTS does not support team preview (it panics in
        # root_get_all_options, which wants generate_team_preview_options). We
        # only guide in-battle move decisions, so skip team-preview states.
        if battle.finished or battle.wait or battle.teampreview:
            return {}
        if random.random() > self.config.sample_rate:
            return {}
        state_str = "<state construction failed>"
        try:
            state = battle_to_engine_state(battle)
            # Capture the engine state BEFORE searching so a panic inside the
            # search is deterministically reproducible via State.from_string.
            state_str = state.to_string()
            result = monte_carlo_tree_search(
                state, duration_ms=self.config.duration_ms, threads=self.config.threads
            )
            return mcts_result_to_policy_target(
                result,
                battle,
                temperature=self.config.target_temperature,
                max_targets=self.config.max_targets,
            )
        except BaseException as exc:
            # poke-engine raises pyo3_runtime.PanicException (a BaseException,
            # not an Exception) on an invalid state. In strict mode we re-raise
            # as a plain, picklable RuntimeError so the failure crosses the
            # SubprocVecEnv boundary cleanly with a debuggable message instead
            # of the opaque "can't pickle PanicException" / EOFError cascade.
            # The engine state string is included so the failure can be
            # reproduced offline with State.from_string(...).
            detail = f"{type(exc).__name__}: {exc}"
            if self.config.strict:
                # Also dump the reproducing state to a standalone file so it is
                # easy to grab out of an otherwise noisy training log.
                dump_path = _dump_invalid_state(state_str, detail)
                raise RuntimeError(
                    f"MCTS conversion produced an invalid state: {detail}\n"
                    f"reproduce with State.from_string(...); state dumped to "
                    f"{dump_path}\nengine_state={state_str}"
                ) from None
            return {"az_mcts_error": detail[:300]}


class MCTSPlayer(Player):
    """A poke-env player that chooses moves with poke-engine-doubles MCTS."""

    def __init__(
        self, *args: Any, duration_ms: int = 50, threads: int = 1, **kwargs: Any
    ):
        ensure_poke_engine_available()
        self.duration_ms = duration_ms
        self.threads = threads
        super().__init__(*args, **kwargs)

    def choose_move(self, battle: AbstractBattle) -> BattleOrder:
        """Search the current battle state and play the highest-visit action.

        Evaluation should never crash a battle, so any engine/conversion failure
        (including a Rust panic) falls back to a random legal move.
        """
        assert isinstance(battle, DoubleBattle)
        if battle.wait:
            return DefaultBattleOrder()
        try:
            state = battle_to_engine_state(battle)
            result = monte_carlo_tree_search(
                state, duration_ms=self.duration_ms, threads=self.threads
            )
            sorted_results = sorted(
                result.side_one,
                key=lambda side_result: side_result.visits,
                reverse=True,
            )
            for side_result in sorted_results:
                try:
                    action = engine_choice_to_action(side_result.move_choice, battle)
                    return DoublesEnv.action_to_order(action, battle, strict=True)
                except Exception:
                    continue
        except BaseException:
            pass
        return Player.choose_random_doubles_move(battle)


def _dump_invalid_state(state_str: str, detail: str) -> str:
    """Write a reproducing engine state to a uniquely-named file; return path."""
    import os

    path = f"az_invalid_state_{os.getpid()}_{int(time.time())}.txt"
    try:
        with open(path, "w") as f:
            f.write(f"# {detail}\n{state_str}\n")
    except OSError:
        return "<dump failed>"
    return path


def ensure_poke_engine_available() -> None:
    """Raise a helpful error if poke-engine-doubles is not importable."""
    if POKE_ENGINE_IMPORT_ERROR is None:
        return
    raise ImportError(
        "AlphaZero MCTS guidance requires poke-engine-doubles. Install it with "
        "`pip install poke-engine-doubles==0.0.7` after sourcing Cargo's env."
    ) from POKE_ENGINE_IMPORT_ERROR


def battle_to_engine_state(battle: DoubleBattle) -> Any:
    """Convert the current poke-env doubles battle view to poke-engine state."""
    ensure_poke_engine_available()
    return State(
        side_one=_side_to_engine(battle, opp=False),
        side_two=_side_to_engine(battle, opp=True),
        weather=_weather_to_engine(battle),
        weather_turns_remaining=_weather_turns_remaining(battle),
        terrain=_terrain_to_engine(battle),
        terrain_turns_remaining=_terrain_turns_remaining(battle),
        trick_room=Field.TRICK_ROOM in battle.fields,
        trick_room_turns_remaining=_field_turns_remaining(
            battle, Field.TRICK_ROOM, default_duration=5
        ),
        team_preview=battle.teampreview,
    )


def mcts_result_to_policy_target(
    result: Any,
    battle: DoubleBattle,
    *,
    temperature: float,
    max_targets: int,
) -> dict[str, Any]:
    """Convert poke-engine MCTS visits into sparse pair-action probabilities."""
    visits_by_pair: dict[tuple[int, int], int] = {}
    for side_result in getattr(result, "side_one", []):
        visits = int(getattr(side_result, "visits", 0))
        if visits <= 0:
            continue
        try:
            action = engine_choice_to_action(side_result.move_choice, battle)
        except Exception:
            continue
        key = (int(action[0]), int(action[1]))
        visits_by_pair[key] = visits_by_pair.get(key, 0) + visits

    if not visits_by_pair:
        return {}

    sorted_items = sorted(visits_by_pair.items(), key=lambda kv: kv[1], reverse=True)
    sorted_items = sorted_items[:max_targets]
    if temperature <= 0:
        weights = np.zeros(len(sorted_items), dtype=np.float64)
        weights[0] = 1.0
    else:
        visits = np.array([v for _, v in sorted_items], dtype=np.float64)
        weights = visits ** (1.0 / temperature)
        weights /= weights.sum()

    target_pairs = [
        (first, second, float(prob))
        for ((first, second), _), prob in zip(sorted_items, weights)
        if prob > 0
    ]
    total_visits = int(getattr(result, "total_visits", 0))
    # poke-engine scores are win-probability in [0, 1] from side_one's (our)
    # perspective; the root value is their visit-weighted average.
    root_score = sum(
        float(getattr(sr, "total_score", 0.0)) for sr in getattr(result, "side_one", [])
    )
    root_value = root_score / total_visits if total_visits > 0 else 0.5
    return {
        "az_target_pairs": target_pairs,
        "az_value_target": root_value,
    }


def engine_choice_to_action(
    move_choice: tuple[str, str], battle: DoubleBattle
) -> npt.NDArray[np.int64]:
    """Convert a poke-engine doubles move choice into VGC-Bench's action pair."""
    action = np.array(
        [
            _engine_choice_to_slot_action(move_choice[0], battle, slot_pos=0),
            _engine_choice_to_slot_action(move_choice[1], battle, slot_pos=1),
        ],
        dtype=np.int64,
    )
    DoublesEnv.action_to_order(action, battle, strict=True)
    return action


def _engine_choice_to_slot_action(
    choice: str, battle: DoubleBattle, *, slot_pos: int
) -> np.int64:
    choice = choice.strip().lower()
    if choice.startswith("no move") or choice.startswith("none"):
        return np.int64(0)

    if choice.startswith("switch "):
        species = to_id_str(choice.removeprefix("switch "))
        for i, pokemon in enumerate(battle.team.values(), start=1):
            names = {pokemon.species, pokemon.base_species, pokemon.name}
            if species in {to_id_str(name) for name in names if name}:
                return np.int64(i)
        raise ValueError(f"Could not map engine switch choice {choice!r}")

    parts = choice.split(",")
    # Trailing gimmick suffix, e.g. "gigadrain,2,a,mega" or "tackle,2,a,tera". The
    # gimmick index matches action_map's blocks (base=0, mega=1, tera=4); Champions
    # VGC 2026 uses Mega Evolution, so dropping ",mega" choices would discard a core
    # decision from the MCTS targets.
    gimmick = 0
    if parts[-1] == "tera":
        gimmick = 4
        parts = parts[:-1]
    elif parts[-1] == "mega":
        gimmick = 1
        parts = parts[:-1]
    if len(parts) == 1:
        move_id = to_id_str(parts[0])
        target = 0
    elif len(parts) == 3:
        move_id = to_id_str(parts[0])
        target = _engine_target_to_showdown(parts[1], parts[2])
    else:
        raise ValueError(f"Could not parse engine move choice {choice!r}")

    active_mon = battle.active_pokemon[slot_pos]
    if active_mon is None:
        raise ValueError(f"Engine chose move {choice!r} for an empty active slot")
    known_moves = list(active_mon.moves.values())[:4]
    known_ids = [move.id for move in known_moves]
    if move_id in known_ids:
        move_index = known_ids.index(move_id)
    else:
        available_ids = [move.id for move in battle.available_moves[slot_pos]]
        if move_id in available_ids:
            move_index = available_ids.index(move_id)
        else:
            raise ValueError(f"Could not map engine move choice {choice!r}")

    return np.int64(7 + 5 * move_index + (target + 2) + 20 * gimmick)


def _engine_target_to_showdown(side_ref: str, slot_ref: str) -> int:
    if side_ref == "1" and slot_ref == "a":
        return -1
    if side_ref == "1" and slot_ref == "b":
        return -2
    if side_ref == "2" and slot_ref == "a":
        return 1
    if side_ref == "2" and slot_ref == "b":
        return 2
    raise ValueError(f"Unknown engine target {side_ref},{slot_ref}")


def _side_to_engine(battle: DoubleBattle, *, opp: bool) -> Any:
    team = list((battle.opponent_team if opp else battle.team).values())
    active = battle.opponent_active_pokemon if opp else battle.active_pokemon
    pokemon = [_pokemon_to_engine(mon, from_opponent=opp) for mon in team[:6]]
    while len(pokemon) < 6:
        pokemon.append(EnginePokemon.create_fainted())

    slot_a_index = _active_index(team, active[0], fallback=0)
    slot_b_index = _active_index(team, active[1], fallback=1)
    side_conditions = battle.opponent_side_conditions if opp else battle.side_conditions
    return Side(
        pokemon=pokemon,
        slot_a=_slot_to_engine(battle, active[0], slot_a_index, opp=opp, slot_pos=0),
        slot_b=_slot_to_engine(battle, active[1], slot_b_index, opp=opp, slot_pos=1),
        side_conditions=_side_conditions_to_engine(battle, side_conditions),
    )


def _pokemon_to_engine(pokemon: Pokemon, *, from_opponent: bool) -> Any:
    estimated_stats = _estimated_stats(pokemon)
    maxhp = estimated_stats["hp"] if from_opponent else pokemon.max_hp
    maxhp = maxhp or estimated_stats["hp"] or 100
    if pokemon.fainted:
        hp = 0
    elif from_opponent:
        hp_fraction = pokemon.current_hp_fraction or 1.0
        hp = max(1, round(hp_fraction * maxhp))
    else:
        hp = pokemon.current_hp or maxhp

    stats = pokemon.stats
    attack = stats.get("atk") or estimated_stats["atk"]
    defense = stats.get("def") or estimated_stats["def"]
    special_attack = stats.get("spa") or estimated_stats["spa"]
    special_defense = stats.get("spd") or estimated_stats["spd"]
    speed = stats.get("spe") or estimated_stats["spe"]
    ability = _known_id(pokemon.ability)
    base_ability = _known_id(pokemon.base_ability) or ability

    return EnginePokemon(
        id=to_id_str(pokemon.species or pokemon.base_species or pokemon.name),
        level=pokemon.level or 50,
        types=_type_tuple(pokemon.types),
        base_types=_type_tuple(pokemon.base_types),
        hp=hp,
        maxhp=maxhp,
        ability=ability or "none",
        base_ability=base_ability or "none",
        item=_known_id(pokemon.item) or "none",
        nature=(pokemon.nature or "serious").lower(),
        evs=_ev_tuple(pokemon),
        attack=attack,
        defense=defense,
        special_attack=special_attack,
        special_defense=special_defense,
        speed=speed,
        status=_status_to_engine(pokemon.status),
        rest_turns=0,
        # Engine caps turns_asleep at 2 (a mon wakes by turn 3), but poke-env's
        # status_counter keeps climbing and can reach 3+, so clamp it.
        sleep_turns=(
            min(pokemon.status_counter, 2) if pokemon.status == Status.SLP else 0
        ),
        weight_kg=float(pokemon.weight or 0.0),
        moves=_moves_to_engine(pokemon),
        terastallized=pokemon.is_terastallized,
        tera_type=_type_to_engine(pokemon.tera_type),
        # NOTE: engine `mega_evolved` is left False. poke-env's mega_evolve() updates
        # stats/types in place without exposing a persistent flag, so we can't reliably
        # detect an already-mega mon. Worst case the engine offers a stale mega action,
        # which then fails to map to a legal VGC action and is dropped.
    )


def _moves_to_engine(pokemon: Pokemon) -> list[Any]:
    engine_moves = [
        EngineMove(id=move.id, pp=max(0, move.current_pp), disabled=False)
        for move in list(pokemon.moves.values())[:4]
    ]
    while len(engine_moves) < 4:
        engine_moves.append(EngineMove(id="none", pp=0, disabled=True))
    return engine_moves


def _slot_to_engine(
    battle: DoubleBattle,
    pokemon: Pokemon | None,
    active_index: int,
    *,
    opp: bool,
    slot_pos: int,
) -> Any:
    boosts = pokemon.boosts if pokemon is not None else {}
    has_substitute = pokemon is not None and Effect.SUBSTITUTE in pokemon.effects
    last_used_move = _last_used_move(pokemon)
    volatile_statuses = _volatile_statuses(pokemon)
    # Enforce engine cross-field invariants on the volatile set.
    if last_used_move == "move:none":
        volatile_statuses.discard("encore")
    if not has_substitute:
        volatile_statuses.discard("substitute")
    force_switch = (
        (not opp and bool(battle.force_switch[slot_pos]))
        or pokemon is None
        or bool(pokemon.fainted)
    )
    force_trapped = not opp and bool(battle.trapped[slot_pos])
    return SideSlot(
        active_index=_pokemon_index(active_index),
        volatile_status_durations=_volatile_status_durations(pokemon),
        force_switch=force_switch,
        force_trapped=force_trapped,
        volatile_statuses=volatile_statuses,
        substitute_health=1 if has_substitute else 0,
        attack_boost=boosts.get("atk", 0),
        defense_boost=boosts.get("def", 0),
        special_attack_boost=boosts.get("spa", 0),
        special_defense_boost=boosts.get("spd", 0),
        speed_boost=boosts.get("spe", 0),
        accuracy_boost=boosts.get("accuracy", 0),
        evasion_boost=boosts.get("evasion", 0),
        last_used_move=last_used_move,
    )


def _side_conditions_to_engine(
    battle: DoubleBattle, side_conditions: dict[SideCondition, int]
) -> Any:
    def remaining(condition: SideCondition, default: int) -> int:
        if condition not in side_conditions:
            return 0
        return max(1, default - max(0, battle.turn - side_conditions[condition]))

    return SideConditions(
        spikes=side_conditions.get(SideCondition.SPIKES, 0),
        toxic_spikes=side_conditions.get(SideCondition.TOXIC_SPIKES, 0),
        stealth_rock=int(SideCondition.STEALTH_ROCK in side_conditions),
        sticky_web=int(SideCondition.STICKY_WEB in side_conditions),
        tailwind=remaining(SideCondition.TAILWIND, 4),
        lucky_chant=remaining(SideCondition.LUCKY_CHANT, 5),
        reflect=remaining(SideCondition.REFLECT, 5),
        light_screen=remaining(SideCondition.LIGHT_SCREEN, 5),
        aurora_veil=remaining(SideCondition.AURORA_VEIL, 5),
        crafty_shield=remaining(SideCondition.CRAFTY_SHIELD, 1),
        safeguard=remaining(SideCondition.SAFEGUARD, 5),
        mist=remaining(SideCondition.MIST, 5),
        mat_block=remaining(SideCondition.MATBLOCK, 1),
        quick_guard=remaining(SideCondition.QUICK_GUARD, 1),
        wide_guard=remaining(SideCondition.WIDE_GUARD, 1),
    )


def _active_index(team: list[Pokemon], active: Pokemon | None, *, fallback: int) -> int:
    if active is None:
        return fallback
    for i, pokemon in enumerate(team):
        if pokemon is active or pokemon.name == active.name:
            return i
    for i, pokemon in enumerate(team):
        if pokemon.base_species == active.base_species:
            return i
    return fallback


def _pokemon_index(index: int) -> Any:
    return [
        PokemonIndex.P0,
        PokemonIndex.P1,
        PokemonIndex.P2,
        PokemonIndex.P3,
        PokemonIndex.P4,
        PokemonIndex.P5,
    ][max(0, min(index, 5))]


def _estimated_stats(pokemon: Pokemon) -> dict[str, int]:
    evs = _ev_tuple(pokemon)
    ivs = tuple(pokemon.ivs or [31, 31, 31, 31, 31, 31])
    level = pokemon.level or 50
    base = pokemon.base_stats
    hp = ((2 * base.get("hp", 100) + ivs[0] + evs[0] // 4) * level) // 100
    hp += level + 10
    return {
        "hp": hp,
        "atk": _estimate_non_hp_stat(base.get("atk", 100), ivs[1], evs[1], level),
        "def": _estimate_non_hp_stat(base.get("def", 100), ivs[2], evs[2], level),
        "spa": _estimate_non_hp_stat(base.get("spa", 100), ivs[3], evs[3], level),
        "spd": _estimate_non_hp_stat(base.get("spd", 100), ivs[4], evs[4], level),
        "spe": _estimate_non_hp_stat(base.get("spe", 100), ivs[5], evs[5], level),
    }


def _estimate_non_hp_stat(base: int, iv: int, ev: int, level: int) -> int:
    return ((2 * base + iv + ev // 4) * level) // 100 + 5


def _ev_tuple(pokemon: Pokemon) -> tuple[int, int, int, int, int, int]:
    evs = pokemon.evs or [85, 85, 85, 85, 85, 85]
    return tuple(int(ev) for ev in evs[:6])  # type: ignore[return-value]


def _type_tuple(types: list[PokemonType]) -> tuple[str, str]:
    engine_types = [_type_to_engine(t) for t in types[:2]]
    while len(engine_types) < 2:
        engine_types.append("typeless")
    return engine_types[0], engine_types[1]


def _type_to_engine(pokemon_type: PokemonType | None) -> str:
    if pokemon_type is None:
        return "typeless"
    if pokemon_type == PokemonType.THREE_QUESTION_MARKS:
        return "typeless"
    return pokemon_type.name.lower()


def _status_to_engine(status: Status | None) -> str:
    return {
        None: "none",
        Status.BRN: "burn",
        Status.FNT: "none",
        Status.FRZ: "freeze",
        Status.PAR: "paralyze",
        Status.PSN: "poison",
        Status.SLP: "sleep",
        Status.TOX: "toxic",
    }[status]


def _known_id(value: str | None) -> str | None:
    if value is None:
        return None
    value = to_id_str(value)
    return None if value in {"", "unknown", "unknownitem"} else value


def _last_used_move(pokemon: Pokemon | None) -> str:
    if pokemon is None or pokemon.last_move is None:
        return "move:none"
    move_ids = [move.id for move in list(pokemon.moves.values())[:4]]
    if pokemon.last_move.id not in move_ids:
        return "move:none"
    return f"move:{move_ids.index(pokemon.last_move.id)}"


def _volatile_statuses(pokemon: Pokemon | None) -> set[str]:
    if pokemon is None:
        return set()
    statuses: set[str] = set()
    effect_map = {
        Effect.AQUA_RING: "aquaring",
        Effect.ATTRACT: "attract",
        Effect.BANEFUL_BUNKER: "banefulbunker",
        Effect.BURNING_BULWARK: "burningbulwark",
        Effect.CHARGE: "charge",
        Effect.COMMANDER: "commanding",
        Effect.CONFUSION: "confusion",
        Effect.CURSE: "curse",
        Effect.DESTINY_BOND: "destinybond",
        Effect.DISABLE: "disable",
        Effect.ELECTRIFY: "electrify",
        Effect.ENCORE: "encore",
        Effect.ENDURE: "endure",
        Effect.FLINCH: "flinch",
        Effect.FOLLOW_ME: "followme",
        Effect.HELPING_HAND: "helpinghand",
        Effect.INGRAIN: "ingrain",
        Effect.LEECH_SEED: "leechseed",
        Effect.LOCKED_MOVE: "lockedmove",
        Effect.MUST_RECHARGE: "mustrecharge",
        Effect.PROTECT: "protect",
        Effect.RAGE_POWDER: "ragepowder",
        Effect.SLOW_START: "slowstart",
        Effect.SUBSTITUTE: "substitute",
        Effect.TAUNT: "taunt",
        Effect.YAWN: "yawn",
    }
    for effect, name in effect_map.items():
        if effect in pokemon.effects:
            statuses.add(name)
    if pokemon.must_recharge:
        statuses.add("mustrecharge")
    return statuses


def _volatile_status_durations(pokemon: Pokemon | None) -> Any:
    """Map poke-env's elapsed-turn counters to the engine's remaining counts.

    poke-env stores ``effects[e]`` as the number of turns the effect has been
    active, counting up from 0. The engine wants *turns remaining*, and rejects
    values above each volatile's cap while the volatile is active (see
    ``_VOLATILE_DURATIONS``).
    """
    if pokemon is None:
        return VolatileStatusDurations()
    return VolatileStatusDurations(
        confusion=_remaining(pokemon, Effect.CONFUSION),
        encore=_remaining(pokemon, Effect.ENCORE),
        lockedmove=_remaining(pokemon, Effect.LOCKED_MOVE),
        protect=min(pokemon.protect_counter, 4),
        slowstart=_remaining(pokemon, Effect.SLOW_START),
        taunt=_remaining(pokemon, Effect.TAUNT),
        yawn=_remaining(pokemon, Effect.YAWN),
    )


def _remaining(pokemon: Pokemon, effect: Effect) -> int:
    """Turns remaining for ``effect``, clamped to the engine's accepted range."""
    if effect not in pokemon.effects:
        return 0
    total, cap = _VOLATILE_DURATIONS[effect]
    elapsed = int(pokemon.effects[effect])
    return max(0, min(total - elapsed, cap))


def _weather_to_engine(battle: DoubleBattle) -> str:
    for weather in battle.weather:
        return {
            Weather.DESOLATELAND: "harshsun",
            Weather.HAIL: "hail",
            Weather.PRIMORDIALSEA: "heavyrain",
            Weather.RAINDANCE: "rain",
            Weather.SANDSTORM: "sand",
            Weather.SNOWSCAPE: "snow",
            Weather.SUNNYDAY: "sun",
        }.get(weather, "none")
    return "none"


def _weather_turns_remaining(battle: DoubleBattle) -> int:
    for weather in battle.weather:
        return max(1, 5 - max(0, battle.turn - battle.weather[weather]))
    return 0


def _terrain_to_engine(battle: DoubleBattle) -> str:
    terrain_map = {
        Field.ELECTRIC_TERRAIN: "electricterrain",
        Field.GRASSY_TERRAIN: "grassyterrain",
        Field.MISTY_TERRAIN: "mistyterrain",
        Field.PSYCHIC_TERRAIN: "psychicterrain",
    }
    for field, terrain in terrain_map.items():
        if field in battle.fields:
            return terrain
    return "none"


def _terrain_turns_remaining(battle: DoubleBattle) -> int:
    for field in (
        Field.ELECTRIC_TERRAIN,
        Field.GRASSY_TERRAIN,
        Field.MISTY_TERRAIN,
        Field.PSYCHIC_TERRAIN,
    ):
        if field in battle.fields:
            return _field_turns_remaining(battle, field, default_duration=5)
    return 0


def _field_turns_remaining(
    battle: DoubleBattle, field: Field, *, default_duration: int
) -> int:
    if field not in battle.fields:
        return 0
    return max(1, default_duration - max(0, battle.turn - battle.fields[field]))
