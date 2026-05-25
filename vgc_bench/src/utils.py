"""
Utility module for VGC-Bench.

Contains shared constants, enums, and helper functions used throughout the
codebase. Defines observation space dimensions, loads Pokemon game data,
and provides training configuration utilities.
"""

import json
import os
import random
import re
from enum import Enum, auto, unique

import numpy as np
import torch
from poke_env.battle import Effect, Field, PokemonType, SideCondition, Status, Weather
from poke_env.data import GenData


@unique
class LearningStyle(Enum):
    """
    Training paradigm options for reinforcement learning.

    Defines different self-play and opponent sampling strategies used
    during PPO training for Pokemon VGC agents.

    Values:
        EXPLOITER: Train against a fixed opponent policy.
        PURE_SELF_PLAY: Train against current policy (both players identical).
        FICTITIOUS_PLAY: Sample historical checkpoints uniformly as opponents.
        DOUBLE_ORACLE: Sample checkpoints based on Nash equilibrium distribution.
    """

    EXPLOITER = auto()
    PURE_SELF_PLAY = auto()
    FICTITIOUS_PLAY = auto()
    DOUBLE_ORACLE = auto()

    @property
    def is_self_play(self) -> bool:
        """Check if this style involves any form of self-play training."""
        return self in {
            LearningStyle.PURE_SELF_PLAY,
            LearningStyle.FICTITIOUS_PLAY,
            LearningStyle.DOUBLE_ORACLE,
        }

    @property
    def abbrev(self) -> str:
        """Get two-letter abbreviation for logging and file naming."""
        match self:
            case LearningStyle.EXPLOITER:
                return "ex"
            case LearningStyle.PURE_SELF_PLAY:
                return "sp"
            case LearningStyle.FICTITIOUS_PLAY:
                return "fp"
            case LearningStyle.DOUBLE_ORACLE:
                return "do"


def set_global_seed(seed: int) -> None:
    """
    Set random seeds for reproducibility across all libraries.

    Args:
        seed: Integer seed to use for all random number generators.
    """
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# game data
with open("data/abilities.json") as f:
    abilities: list[str] = json.load(f)
with open("data/items.json") as f:
    items: list[str] = json.load(f)
with open("data/moves.json") as f:
    moves: list[str] = json.load(f)

# observation length constants
act_len = 107

# event-token observation constants
max_events = 256
FIELDS_PER_EVENT = 15

# event types we tokenize (everything else is skipped)
EVENT_TYPES = [
    "switch",
    "drag",
    "move",
    "-damage",
    "-heal",
    "-sethp",
    "-status",
    "-curestatus",
    "-cureteam",
    "-boost",
    "-unboost",
    "-setboost",
    "-clearallboost",
    "-clearboost",
    "-clearnegativeboost",
    "-clearpositiveboost",
    "-copyboost",
    "-swapboost",
    "-invertboost",
    "-weather",
    "-fieldstart",
    "-fieldend",
    "-sidestart",
    "-sideend",
    "-swapsideconditions",
    "-start",
    "-end",
    "-activate",
    "-ability",
    "-endability",
    "-item",
    "-enditem",
    "-terastallize",
    "-formechange",
    "detailschange",
    "-mega",
    "-primal",
    "-mustrecharge",
    "-singleturn",
    "-singlemove",
    "-prepare",
    "-transform",
    "faint",
    "turn",
    "cant",
    "start",
    "-immune",
]

POSITIONS = ["ally_a", "ally_b", "opp_a", "opp_b", "ally_side", "opp_side"]

STATS = ["atk", "def", "spa", "spd", "spe", "accuracy", "evasion"]

# --- Event type IDs (index into event_type embedding) ---
_evt_list = [
    "PAD",
    "BOS",
    "SEP",
    "REQUEST",
    "TEAM",
    "TEAM_MOVES",
    "TEAMPREVIEW_ACTION",
    "RATING",
    "EMPTY",
] + EVENT_TYPES
EVT: dict[str, int] = {name: i for i, name in enumerate(_evt_list)}
NUM_EVENT_TYPES = len(_evt_list)

# --- Position IDs (index into position embedding) ---
_pos_list = ["NONE"] + POSITIONS
POS: dict[str, int] = {name: i for i, name in enumerate(_pos_list)}
NUM_POSITIONS = len(_pos_list)


# --- Unified entity vocab ---
class EntityVocab:
    """Maps entity strings to integer IDs for the unified entity embedding."""

    def __init__(self):
        self._id_map: dict[str, int] = {"PAD": 0}
        self._next = 1
        gd = GenData.from_gen(9)
        for species in sorted(gd.pokedex.keys()):
            self._add(f"species:{species}")
        for m in moves:
            self._add(f"move:{m}")
        self._add("move:null")
        for a in abilities:
            self._add(f"ability:{a}")
        self._add("ability:asone")
        self._add("ability:null")
        for i in items:
            self._add(f"item:{i}")
        self._add("item:null")
        for t in PokemonType:
            self._add(f"type:{t.name}")
        for w in Weather:
            self._add(f"weather:{w.name}")
        for f in Field:
            self._add(f"field:{f.name}")
        for s in SideCondition:
            self._add(f"side:{s.name}")
        for s in Status:
            self._add(f"status:{s.name}")
        for s in STATS:
            self._add(f"stat:{s}")
        for e in Effect:
            self._add(f"effect:{e.name}")

    def _add(self, key: str):
        if key not in self._id_map:
            self._id_map[key] = self._next
            self._next += 1

    def __getitem__(self, key: str) -> int:
        return self._id_map[key]

    @property
    def size(self) -> int:
        return self._next


ENT = EntityVocab()
NUM_ENTITIES = ENT.size

# format logic
format_map = {
    "a": "gen9vgc2022rega",
    "b": "gen9vgc2023regb",
    "c": "gen9vgc2023regc",
    "d": "gen9vgc2023regd",
    "e": "gen9vgc2024rege",
    "f": "gen9vgc2024regf",
    "g": "gen9vgc2024regg",
    "h": "gen9vgc2024regh",
    "i": "gen9vgc2025regi",
    "j": "gen9vgc2025regj",
    "ma": "gen9championsvgc2026regma",
}


def is_vgc_format(fmt: str) -> bool:
    """Check if a format string is a recognized VGC format."""
    return bool(re.match(r"gen9(?:champions)?vgc\d{4}reg(ma|[a-j])(?:bo\d+)?$", fmt))


def get_reg_from_format(fmt: str) -> str:
    """Extract the regulation identifier from a VGC format string"""
    m = re.match(r"gen9(?:champions)?vgc\d{4}reg(ma|[a-j])(?:bo\d+)?$", fmt)
    assert m is not None, f"not a valid VGC format: {fmt}"
    return m.group(1)


with open("data/abilities.json") as f:
    abilities: list[str] = json.load(f)
with open("data/items.json") as f:
    items: list[str] = json.load(f)
with open("data/moves.json") as f:
    moves: list[str] = json.load(f)
