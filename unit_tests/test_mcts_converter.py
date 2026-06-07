"""Regression tests for the poke-env -> poke-engine state converter.

These guard the engine's volatile-status invariants that previously crashed
training with a Rust panic (e.g. "Taunt duration cannot be 3 when taunt
volatile is active"). They run offline -- no Showdown server needed -- by
feeding converter output straight into the engine and asserting it accepts the
state. Skipped automatically if poke-engine-doubles is not installed.
"""

import pytest

pytest.importorskip("poke_engine")

from poke_engine import (  # noqa: E402
    Move,
    Pokemon,
    PokemonIndex,
    Side,
    SideConditions,
    SideSlot,
    State,
    monte_carlo_tree_search,
)
from poke_env.battle import Effect, PokemonType, Status  # noqa: E402

import vgc_bench.src.mcts as mcts  # noqa: E402


class _FakePokemon:
    """Minimal stand-in exposing the attributes the slot converter reads."""

    def __init__(self, effects, last_move_id=None, protect_counter=0):
        self.effects = effects
        self.protect_counter = protect_counter
        self.must_recharge = False
        self.boosts = {}
        self.fainted = False
        if last_move_id:
            move = type("Mv", (), {"id": last_move_id})()
            self.last_move = move
            self.moves = {last_move_id: move}
        else:
            self.last_move = None
            self.moves = {}


def _engine_accepts(slot: SideSlot) -> None:
    """Run a tiny search; raises (incl. PanicException) if the state is invalid."""
    def fresh_side(slot_a):
        mons = [
            Pokemon(id="pikachu", moves=[Move(id="thunderbolt", pp=16)])
            for _ in range(6)
        ]
        return Side(
            pokemon=mons,
            slot_a=slot_a,
            slot_b=SideSlot(active_index=PokemonIndex.P1),
            side_conditions=SideConditions(),
        )

    state = State(
        side_one=fresh_side(slot),
        side_two=fresh_side(SideSlot(active_index=PokemonIndex.P0)),
    )
    monte_carlo_tree_search(state, duration_ms=4)


def _slot_for(pokemon: _FakePokemon) -> SideSlot:
    """Build a SideSlot the same way the converter's _slot_to_engine does."""
    vs = mcts._volatile_statuses(pokemon)
    last_used = mcts._last_used_move(pokemon)
    if last_used == "move:none":
        vs.discard("encore")
    return SideSlot(
        active_index=PokemonIndex.P0,
        volatile_status_durations=mcts._volatile_status_durations(pokemon),
        volatile_statuses=vs,
        last_used_move=last_used,
        substitute_health=1 if "substitute" in vs else 0,
    )


@pytest.mark.parametrize("elapsed", range(5))
def test_taunt_duration_never_exceeds_engine_cap(elapsed):
    # The original crash: poke-env taunt counter reaches 3, engine caps at 2.
    durations = mcts._volatile_status_durations(_FakePokemon({Effect.TAUNT: elapsed}))
    assert durations.taunt <= 2
    _engine_accepts(_slot_for(_FakePokemon({Effect.TAUNT: elapsed})))


@pytest.mark.parametrize("elapsed", range(4))
def test_yawn_duration_never_exceeds_engine_cap(elapsed):
    durations = mcts._volatile_status_durations(_FakePokemon({Effect.YAWN: elapsed}))
    assert durations.yawn <= 1
    _engine_accepts(_slot_for(_FakePokemon({Effect.YAWN: elapsed})))


def test_encore_dropped_without_real_last_move():
    # Engine: encore volatile may only be active with a real last_used_move.
    pokemon = _FakePokemon({Effect.ENCORE: 0}, last_move_id=None)
    assert "encore" not in _slot_for(pokemon).volatile_statuses
    _engine_accepts(_slot_for(pokemon))


def test_encore_kept_with_real_last_move():
    pokemon = _FakePokemon({Effect.ENCORE: 0}, last_move_id="thunderbolt")
    assert "encore" in _slot_for(pokemon).volatile_statuses
    _engine_accepts(_slot_for(pokemon))


class _Move:
    def __init__(self, id):
        self.id = id


class _FakeBattle:
    """Minimal battle exposing what _engine_choice_to_slot_action reads."""

    def __init__(self):
        move = _Move("gigadrain")
        self.active_pokemon = [type("P", (), {"moves": {"gigadrain": move}})(), None]
        self.available_moves = [[move], []]


def test_engine_move_choice_gimmick_blocks():
    # move 1 (index 0), target side-2 slot-a -> showdown target +1 -> (target+2)=3.
    # action_map blocks: base 7-26, mega 27-46, tera 87-106 (gimmick 0/1/4).
    battle = _FakeBattle()

    def idx(choice):
        return int(mcts._engine_choice_to_slot_action(choice, battle, slot_pos=0))

    assert idx("gigadrain,2,a") == 10           # base
    assert idx("gigadrain,2,a,mega") == 30       # 10 + 20*1
    assert idx("gigadrain,2,a,tera") == 90       # 10 + 20*4
    # mega must land in the mega block, never be dropped or collide with tera
    assert 27 <= idx("gigadrain,2,a,mega") <= 46


class _FakeMove:
    def __init__(self, id, pp=16):
        self.id = id
        self.current_pp = pp


class _FakeMon:
    """Rich enough stand-in for what _pokemon_to_engine reads."""

    def __init__(self, status, status_counter):
        self.evs = [85] * 6
        self.ivs = [31] * 6
        self.level = 50
        self.base_stats = {k: 100 for k in ("hp", "atk", "def", "spa", "spd", "spe")}
        self.max_hp = 120
        self.fainted = False
        self.current_hp = 120
        self.current_hp_fraction = 1.0
        self.stats = {k: 100 for k in ("atk", "def", "spa", "spd", "spe")}
        self.ability = "static"
        self.base_ability = "static"
        self.item = "none"
        self.species = "pikachu"
        self.base_species = "pikachu"
        self.name = "Pikachu"
        self.types = [PokemonType.ELECTRIC]
        self.base_types = [PokemonType.ELECTRIC]
        self.nature = "serious"
        self.status = status
        self.status_counter = status_counter
        self.weight = 6.0
        self.moves = {"thunderbolt": _FakeMove("thunderbolt")}
        self.is_terastallized = False
        self.tera_type = None


@pytest.mark.parametrize("counter,expected", [(0, 0), (1, 1), (2, 2), (3, 2), (5, 2)])
def test_sleep_turns_clamped_to_engine_cap(counter, expected):
    # The engine caps turns_asleep at 2; poke-env's status_counter can reach 3+.
    engine_mon = mcts._pokemon_to_engine(
        _FakeMon(Status.SLP, counter), from_opponent=False
    )
    assert engine_mon.sleep_turns == expected
    # and a state with this (asleep) mon active must search without panicking
    other = [
        Pokemon(id="pikachu", moves=[Move(id="thunderbolt", pp=16)]) for _ in range(6)
    ]
    side = Side(
        pokemon=[engine_mon] + other[:5],
        slot_a=SideSlot(active_index=PokemonIndex.P0),
        slot_b=SideSlot(active_index=PokemonIndex.P1),
        side_conditions=SideConditions(),
    )
    foe = Side(
        pokemon=other,
        slot_a=SideSlot(active_index=PokemonIndex.P0),
        slot_b=SideSlot(active_index=PokemonIndex.P1),
        side_conditions=SideConditions(),
    )
    monte_carlo_tree_search(State(side_one=side, side_two=foe), duration_ms=4)


def test_non_sleep_status_has_zero_sleep_turns():
    engine_mon = mcts._pokemon_to_engine(_FakeMon(Status.BRN, 5), from_opponent=False)
    assert engine_mon.sleep_turns == 0
