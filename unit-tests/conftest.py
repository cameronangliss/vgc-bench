"""Shared fixtures for VGC-Bench unit tests."""

import textwrap

import pytest


@pytest.fixture
def sample_team_text():
    """A valid 6-Pokemon VGC team in Showdown format."""
    return textwrap.dedent("""\
        Reshiram @ Scope Lens
        Ability: Turboblaze
        Level: 50
        Tera Type: Fairy
        EVs: 252 HP / 12 Def / 156 SpA / 60 SpD / 28 Spe
        Modest Nature
        IVs: 0 Atk
        - Protect
        - Heat Wave
        - Draco Meteor
        - Blue Flare

        Urshifu @ Focus Sash
        Ability: Unseen Fist
        Level: 50
        Tera Type: Dark
        EVs: 4 HP / 252 Atk / 252 Spe
        Adamant Nature
        - Detect
        - Wicked Blow
        - Close Combat
        - Sucker Punch

        Ogerpon-Wellspring (F) @ Wellspring Mask
        Ability: Water Absorb
        Level: 50
        Tera Type: Water
        EVs: 252 HP / 4 SpD / 252 Spe
        Jolly Nature
        - Spiky Shield
        - Ivy Cudgel
        - Follow Me
        - Horn Leech

        Iron Jugulis @ Booster Energy
        Ability: Quark Drive
        Level: 50
        Tera Type: Steel
        EVs: 188 HP / 68 SpD / 252 Spe
        Timid Nature
        - Tailwind
        - Air Slash
        - Snarl
        - Protect

        Rillaboom @ Assault Vest
        Ability: Grassy Surge
        Level: 50
        Tera Type: Fire
        EVs: 252 HP / 164 Atk / 4 Def / 60 SpD / 28 Spe
        Adamant Nature
        - Fake Out
        - Grassy Glide
        - Wood Hammer
        - U-turn

        Landorus-Therian @ Life Orb
        Ability: Intimidate
        Level: 50
        Tera Type: Flying
        EVs: 4 HP / 252 SpA / 252 Spe
        Timid Nature
        - Earth Power
        - Sludge Bomb
        - Protect
        - Psychic
    """)


@pytest.fixture
def sample_battle_log():
    """A minimal snippet of a battle log for testing log parsing helpers."""
    return (
        "|player|p1|Alice|102|1500\n"
        "|player|p2|Bob|103|1200\n"
        "|win|Alice\n"
    )
