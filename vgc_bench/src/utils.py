import json
import os
import random
from enum import Enum, auto, unique

import numpy as np
import numpy.typing as npt
import torch
from poke_env.battle import (
    Effect,
    Field,
    MoveCategory,
    PokemonGender,
    PokemonType,
    SideCondition,
    Status,
    Target,
    Weather,
)


@unique
class LearningStyle(Enum):
    EXPLOITER = auto()
    PURE_SELF_PLAY = auto()
    FICTITIOUS_PLAY = auto()
    DOUBLE_ORACLE = auto()

    @property
    def is_self_play(self) -> bool:
        return self in {
            LearningStyle.PURE_SELF_PLAY,
            LearningStyle.FICTITIOUS_PLAY,
            LearningStyle.DOUBLE_ORACLE,
        }

    @property
    def abbrev(self) -> str:
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
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# training params
battle_format = "gen9vgc2024regg"
save_interval = 98_304

# observation length constants
act_len = 107
glob_obs_len = len(Field) + len(Weather) + 2
side_obs_len = len(SideCondition) + 5
move_obs_len = len(MoveCategory) + len(Target) + len(PokemonType) + 12
pokemon_obs_len = (
    4 * move_obs_len + len(Effect) + len(PokemonGender) + 2 * len(PokemonType) + len(Status) + 39
)
chunk_obs_len = glob_obs_len + side_obs_len + pokemon_obs_len

# pokemon data
all_formats = [
    "gen9vgc2023regd",
    "gen9vgc2024regf",
    "gen9vgc2024regfbo3",
    "gen9vgc2024regg",
    "gen9vgc2024reggbo3",
    "gen9vgc2024regh",
    "gen9vgc2024reghbo3",
    "gen9vgc2025regg",
    "gen9vgc2025reggbo3",
    "gen9vgc2025regh",
    "gen9vgc2025reghbo3",
    "gen9vgc2025regi",
    "gen9vgc2025regibo3",
    "gen9vgc2025regjbo3",
    "gen9vgc2026regf",
    "gen9vgc2026regfbo3",
]
with open("data/abilities.json") as f:
    ability_descs: dict[str, npt.NDArray[np.float32]] = json.load(f)
    abilities = list(ability_descs.keys())
    ability_embeds = list(ability_descs.values())
with open("data/items.json") as f:
    item_descs: dict[str, npt.NDArray[np.float32]] = json.load(f)
    items = list(item_descs.keys())
    item_embeds = list(item_descs.values())
with open("data/moves.json") as f:
    move_descs: dict[str, npt.NDArray[np.float32]] = json.load(f)
    moves = list(move_descs.keys())
    move_embeds = list(move_descs.values())
