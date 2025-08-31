# teams from https://docs.google.com/spreadsheets/d/1axlwmzPA49rYkqXh7zHvAtSP-TKbM0ijGYBPRflLSWw/edit?gid=736919171#gid=736919171

import random

from poke_env.teambuilder import Teambuilder, TeambuilderPokemon


class TeamToggle:
    def __init__(self, num_teams: int):
        assert num_teams > 1
        self.num_teams = num_teams
        self._last_value = None

    def next(self) -> int:
        if self._last_value is None:
            self._last_value = random.choice(range(self.num_teams))
            return self._last_value
        else:
            value = random.choice([t for t in range(self.num_teams) if t != self._last_value])
            self._last_value = None
            return value


class RandomTeamBuilder(Teambuilder):
    teams: list[str]

    def __init__(self, teams: list[int], battle_format: str, toggle: TeamToggle | None = None):
        self.teams = []
        self.toggle = toggle
        for team in [TEAMS[battle_format[-4:]][t] for t in teams]:
            parsed_team = self.parse_showdown_team(team)
            packed_team = self.join_team(parsed_team)
            self.teams.append(packed_team)

    def yield_team(self) -> str:
        if self.toggle:
            return self.teams[self.toggle.next()]
        else:
            return random.choice(self.teams)


def calc_team_similarity_score(team1: str, team2: str):
    """
    Roughly measures similarity between two teams on a scale of 0-100
    """
    mon_builders1 = Teambuilder.parse_showdown_team(team1)
    mon_builders2 = Teambuilder.parse_showdown_team(team2)
    match_pairs: list[tuple[TeambuilderPokemon, TeambuilderPokemon]] = []
    for mon_builder in mon_builders1:
        matches = [
            p
            for p in mon_builders2
            if (p.species or p.nickname) == (mon_builder.species or mon_builder.nickname)
        ]
        if matches:
            match_pairs += [(mon_builder, matches[0])]
    similarity_score = 0
    for mon1, mon2 in match_pairs:
        if mon1.item == mon2.item:
            similarity_score += 1
        if mon1.ability == mon2.ability:
            similarity_score += 1
        if mon1.tera_type == mon2.tera_type:
            similarity_score += 1
        ev_dist = sum([abs(ev1 - ev2) for ev1, ev2 in zip(mon1.evs, mon2.evs)]) / (2 * 508)
        similarity_score += 1 - ev_dist
        if mon1.nature == mon2.nature:
            similarity_score += 1
        iv_dist = sum([abs(iv1 - iv2) for iv1, iv2 in zip(mon1.ivs, mon2.ivs)]) / (6 * 31)
        similarity_score += 1 - iv_dist
        for move in mon1.moves:
            if move in mon2.moves:
                similarity_score += 1
    return round(100 * similarity_score / 60, ndigits=2)


def find_run_id(team_ids: set[int], battle_format: str) -> int:
    """
    Finds lowest run_id > 0 that will have team_ids in the beginning of its team order
    """
    run_id = 1
    while True:
        teams = list(range(len(TEAMS[battle_format[-4:]])))
        random.Random(run_id).shuffle(teams)
        if set(teams[: len(team_ids)]) == team_ids:
            return run_id
        run_id += 1


TEAMS = {
    "regi": [
        ### ATLANTA REGIONALS APRIL 2025 (14 teams) ###
        """
Koraidon @ Clear Amulet
Ability: Orichalcum Pulse
Level: 50
Tera Type: Fire
EVs: 100 HP / 196 Atk / 4 Def / 4 SpD / 204 Spe
Adamant Nature
- Flare Blitz
- Collision Course
- Flame Charge
- Protect

Iron Crown @ Booster Energy
Ability: Quark Drive
Level: 50
Tera Type: Water
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 20 Atk
- Expanding Force
- Tachyon Cutter
- Calm Mind
- Protect

Indeedee-F @ Psychic Seed
Ability: Psychic Surge
Level: 50
Tera Type: Fairy
EVs: 252 HP / 252 Def / 4 SpD
Bold Nature
IVs: 0 Atk / 29 Spe
- Psychic
- Follow Me
- Helping Hand
- Trick Room

Brute Bonnet @ Covert Cloak
Ability: Protosynthesis
Level: 50
Tera Type: Water
EVs: 252 HP / 132 Def / 124 Spe
Impish Nature
- Seed Bomb
- Sucker Punch
- Spore
- Rage Powder

Flutter Mane @ Focus Sash
Ability: Protosynthesis
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Shadow Ball
- Icy Wind
- Protect

Chi-Yu @ Choice Scarf
Ability: Beads of Ruin
Level: 50
Tera Type: Fire
EVs: 132 HP / 4 Def / 116 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Heat Wave
- Dark Pulse
- Overheat
- Snarl
""",
        """
Calyrex-Shadow @ Life Orb
Ability: As One (Spectrier)
Level: 50
Tera Type: Normal
EVs: 28 HP / 84 Def / 140 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Psyshock
- Nasty Plot
- Protect

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 4 Atk / 188 Def / 68 SpD / 4 Spe
Impish Nature
- Fake Out
- Knock Off
- Will-O-Wisp
- Parting Shot

Ogerpon-Hearthflame @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 252 HP / 76 Atk / 164 Def / 12 SpD / 4 Spe
Adamant Nature
- Ivy Cudgel
- Grassy Glide
- Follow Me
- Spiky Shield

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 252 HP / 36 Atk / 204 Def / 12 SpD / 4 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- U-turn
- Fake Out

Urshifu-Rapid-Strike @ Mystic Water
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 28 HP / 236 Atk / 4 Def / 140 SpD / 100 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Detect

Raging Bolt @ Leftovers
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 156 HP / 164 Def / 180 SpA / 4 SpD / 4 Spe
Modest Nature
IVs: 20 Atk
- Thunderclap
- Dragon Pulse
- Calm Mind
- Protect
""",
        """
Calyrex-Shadow @ Life Orb
Ability: As One (Spectrier)
Level: 50
Tera Type: Grass
EVs: 28 HP / 4 Def / 220 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Astral Barrage
- Giga Drain
- Nasty Plot
- Protect

Smeargle @ Focus Sash
Ability: Moody
Level: 50
Tera Type: Ghost
EVs: 12 HP / 244 Def / 252 Spe
Jolly Nature
- Fake Out
- Spore
- Wide Guard
- Follow Me

Clefairy @ Eviolite
Ability: Friend Guard
Level: 50
Tera Type: Grass
EVs: 252 HP / 212 Def / 44 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Follow Me
- After You
- Helping Hand
- Protect

Tornadus @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 148 HP / 76 Def / 4 SpA / 28 SpD / 252 Spe
Timid Nature
- Tailwind
- Bleakwind Storm
- Rain Dance
- Taunt

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 252 HP / 140 Atk / 84 Def / 28 SpD / 4 Spe
Adamant Nature
- Fake Out
- Grassy Glide
- Wood Hammer
- U-turn

Urshifu-Rapid-Strike @ Mystic Water
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 44 HP / 188 Atk / 4 Def / 76 SpD / 196 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Detect
""",
        """
Calyrex-Shadow @ Life Orb
Ability: As One (Spectrier)
Level: 50
Tera Type: Normal
EVs: 108 HP / 12 Def / 132 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Astral Barrage
- Psychic
- Nasty Plot

Dc+GB (Mienshao) (F) @ Focus Sash
Ability: Inner Focus
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Close Combat
- Feint
- Wide Guard
- Fake Out

Urshifu-Rapid-Strike @ Mystic Water
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 140 HP / 156 Atk / 4 Def / 20 SpD / 188 Spe
Adamant Nature
- Protect
- Surging Strikes
- Aqua Jet
- Taunt

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fairy
EVs: 252 HP / 68 Atk / 4 Def / 108 SpD / 76 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- U-turn
- Fake Out

Clefairy @ Eviolite
Ability: Friend Guard
Level: 50
Tera Type: Grass
EVs: 252 HP / 140 Def / 116 SpD
Sassy Nature
IVs: 0 Atk / 0 Spe
- Protect
- Follow Me
- After You
- Helping Hand

LMK (Roaring Moon) @ Booster Energy
Ability: Protosynthesis
Level: 50
Shiny: Yes
Tera Type: Flying
EVs: 148 HP / 84 Atk / 76 Def / 4 SpD / 196 Spe
Jolly Nature
- Knock Off
- Acrobatics
- Protect
- Tailwind
""",
        """
Ehrmantraut (Calyrex-Ice) @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Poison
EVs: 252 HP / 116 Atk / 4 Def / 116 SpD / 20 Spe
Adamant Nature
- Protect
- Glacial Lance
- High Horsepower
- Trick Room

Ichiban (Urshifu-Rapid-Strike) @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 12 HP / 236 Atk / 4 Def / 4 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Coaching
- U-turn

Chitose (Ogerpon-Cornerstone) @ Cornerstone Mask
Ability: Sturdy
Level: 50
Tera Type: Rock
EVs: 140 HP / 84 Atk / 52 Def / 4 SpD / 228 Spe
Adamant Nature
- Spiky Shield
- Ivy Cudgel
- Power Whip
- Follow Me

Tomizawa (Raging Bolt) @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 100 HP / 4 Def / 252 SpA / 52 SpD / 100 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Draco Meteor
- Thunderclap
- Volt Switch

Nanba (Landorus) @ Life Orb
Ability: Sheer Force
Level: 50
Tera Type: Water
EVs: 132 HP / 4 Def / 116 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Protect
- Earth Power
- Sludge Bomb
- Sandsear Storm

Patrick’s Pel (Pelipper) (M) @ Focus Sash
Ability: Drizzle
Tera Type: Grass
EVs: 252 HP / 4 Def / 212 SpA / 4 SpD / 36 Spe
Modest Nature
IVs: 0 Atk
- Protect
- Weather Ball
- Hurricane
- Wide Guard
""",
        """
Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 236 HP / 4 Def / 220 SpA / 4 SpD / 44 Spe
Modest Nature
- Electro Drift
- Dazzling Gleam
- Draco Meteor
- Volt Switch

Whimsicott @ Covert Cloak
Ability: Prankster
Level: 50
Shiny: Yes
Tera Type: Dark
EVs: 196 HP / 252 SpD / 60 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Tailwind
- Encore
- Light Screen

Urshifu-Rapid-Strike @ Splash Plate
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 76 HP / 220 Atk / 20 Def / 100 SpD / 92 Spe
Adamant Nature
- Surging Strikes
- Aqua Jet
- Taunt
- Detect

Ogerpon-Hearthflame @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 252 HP / 116 Atk / 52 Def / 84 SpD / 4 Spe
Adamant Nature
IVs: 20 SpA
- Ivy Cudgel
- Focus Energy
- Follow Me
- Spiky Shield

Farigiraf @ Electric Seed
Ability: Armor Tail
Level: 50
Tera Type: Water
EVs: 228 HP / 164 Def / 4 SpA / 68 SpD / 44 Spe
Bold Nature
IVs: 0 Atk
- Helping Hand
- Foul Play
- Psychic
- Trick Room

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 50
Tera Type: Water
EVs: 84 HP / 180 Atk / 84 Def / 156 SpD / 4 Spe
Adamant Nature
IVs: 27 Spe
- Drain Punch
- Heavy Slam
- Low Kick
- Fake Out
""",
        """
Indeedee-F @ Rocky Helmet
Ability: Psychic Surge
Level: 50
Tera Type: Water
EVs: 252 HP / 244 Def / 12 SpD
Bold Nature
IVs: 0 Atk / 28 Spe
- Trick Room
- Follow Me
- Helping Hand
- Psychic

Calyrex-Shadow @ Life Orb
Ability: As One (Spectrier)
Level: 50
Tera Type: Dark
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Nasty Plot
- Expanding Force
- Astral Barrage

Whimsicott @ Focus Sash
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 HP / 0 Atk
- Protect
- Tailwind
- Endeavor
- Moonblast

Urshifu-Rapid-Strike @ Mystic Water
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 60 HP / 188 Atk / 4 Def / 4 SpD / 252 Spe
Adamant Nature
- Detect
- Surging Strikes
- Close Combat
- Aqua Jet

Ogerpon-Cornerstone @ Cornerstone Mask
Ability: Sturdy
Level: 50
Tera Type: Rock
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Spiky Shield
- Follow Me
- Ivy Cudgel
- Power Whip

Incineroar @ Assault Vest
Ability: Intimidate
Level: 50
Tera Type: Water
EVs: 244 HP / 188 Def / 76 SpD
Impish Nature
- Fake Out
- Flare Blitz
- Knock Off
- U-turn
""",
        """
Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Fairy
EVs: 124 HP / 132 Atk / 252 Spe
Jolly Nature
- Glacial Lance
- High Horsepower
- Trick Room
- Protect

Whimsicott (F) @ Focus Sash
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Tailwind
- Moonblast
- Encore
- Endeavor

Landorus @ Choice Scarf
Ability: Sheer Force
Level: 50
Tera Type: Water
EVs: 172 HP / 4 Def / 196 SpA / 4 SpD / 132 Spe
Modest Nature
- Earth Power
- Sludge Bomb
- Sandsear Storm
- U-turn

Raging Bolt @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 4 HP / 4 Def / 252 SpA / 68 SpD / 180 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Thunderclap
- Draco Meteor
- Protect

Chi-Yu @ Covert Cloak
Ability: Beads of Ruin
Level: 50
Tera Type: Dragon
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 0 Atk
- Taunt
- Heat Wave
- Snarl
- Overheat

Ogerpon-Cornerstone @ Cornerstone Mask
Ability: Sturdy
Level: 50
Tera Type: Rock
EVs: 92 HP / 252 Atk / 164 Spe
Adamant Nature
- Ivy Cudgel
- Power Whip
- Follow Me
- Spiky Shield
""",
        """
Calyrex-Shadow @ Life Orb
Ability: As One (Spectrier)
Level: 50
Tera Type: Grass
EVs: 28 HP / 228 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Giga Drain
- Nasty Plot
- Protect

Clefairy @ Eviolite
Ability: Friend Guard
Level: 50
Tera Type: Grass
EVs: 252 HP / 252 Def / 4 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Follow Me
- Helping Hand
- After You
- Protect

Tornadus @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 220 HP / 60 Def / 44 SpA / 4 SpD / 180 Spe
Modest Nature
IVs: 0 Atk
- Bleakwind Storm
- Tailwind
- Rain Dance
- Taunt

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 188 HP / 116 Atk / 4 Def / 92 SpD / 108 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- U-turn
- Fake Out

Smeargle @ Focus Sash
Ability: Moody
Level: 50
Tera Type: Ghost
EVs: 252 HP / 4 Def / 252 Spe
Jolly Nature
- Follow Me
- Spore
- Wide Guard
- Fake Out

Urshifu-Rapid-Strike @ Mystic Water
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 28 HP / 244 Atk / 4 Def / 28 SpD / 204 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Protect
""",
        """
Calyrex-Shadow @ Life Orb
Ability: As One (Spectrier)
Level: 50
Tera Type: Dark
EVs: 28 HP / 84 Def / 228 SpA / 4 SpD / 164 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Psychic
- Nasty Plot
- Protect

Ogerpon-Hearthflame @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 252 HP / 84 Atk / 52 Def / 60 SpD / 60 Spe
Adamant Nature
- Ivy Cudgel
- Horn Leech
- Follow Me
- Spiky Shield

Raging Bolt @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 116 HP / 12 Def / 212 SpA / 12 SpD / 156 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Thunderclap
- Dragon Pulse
- Protect

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Surging Strikes
- Aqua Jet
- Protect
- Close Combat

Whimsicott @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 132 HP / 4 Def / 44 SpA / 164 SpD / 164 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Tailwind
- Encore
- Light Screen

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Water
EVs: 244 HP / 4 Atk / 76 Def / 92 SpD / 92 Spe
Impish Nature
- Fake Out
- Knock Off
- Will-O-Wisp
- Parting Shot
""",
        """
Indeedee-F @ Rocky Helmet
Ability: Psychic Surge
Level: 50
Tera Type: Water
EVs: 252 HP / 244 Def / 4 SpA / 4 SpD / 4 Spe
Bold Nature
IVs: 1 Atk
- Psychic
- Follow Me
- Imprison
- Trick Room

Calyrex-Shadow @ Life Orb
Ability: As One (Spectrier)
Level: 50
Tera Type: Dark
EVs: 28 HP / 84 Def / 228 SpA / 4 SpD / 164 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Psychic
- Nasty Plot
- Astral Barrage

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 4 HP / 244 Atk / 20 Def / 28 SpD / 212 Spe
Adamant Nature
- Detect
- Taunt
- Close Combat
- Surging Strikes

Chi-Yu @ Choice Specs
Ability: Beads of Ruin
Level: 50
Tera Type: Water
EVs: 148 HP / 44 Def / 148 SpA / 4 SpD / 164 Spe
Timid Nature
IVs: 2 Atk
- Dark Pulse
- Heat Wave
- Snarl
- Overheat

Whimsicott @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 244 HP / 52 Def / 44 SpA / 116 SpD / 52 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Light Screen
- Tailwind
- Helping Hand

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Water
EVs: 252 HP / 68 Atk / 4 Def / 124 SpD / 60 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- U-turn
- Fake Out
""",
        """
Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 244 HP / 156 Def / 108 SpD
Relaxed Nature
IVs: 22 Spe
- Will-O-Wisp
- Fake Out
- Knock Off
- U-turn

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Shiny: Yes
Tera Type: Fire
EVs: 252 HP / 116 Atk / 36 Def / 84 SpD / 20 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- Fake Out
- U-turn

Kyogre @ Mystic Water
Ability: Drizzle
Level: 50
Shiny: Yes
Tera Type: Grass
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 0 Atk
- Water Spout
- Origin Pulse
- Ice Beam
- Protect

Tornadus @ Covert Cloak
Ability: Prankster
Level: 50
Shiny: Yes
Tera Type: Steel
EVs: 92 HP / 52 Def / 84 SpA / 28 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Bleakwind Storm
- Tailwind
- Rain Dance
- Scary Face

Landorus @ Life Orb
Ability: Sheer Force
Level: 50
Shiny: Yes
Tera Type: Poison
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 0 Atk
- Earth Power
- Sandsear Storm
- Sludge Bomb
- Protect

Urshifu @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Dark
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Wicked Blow
- Close Combat
- Sucker Punch
- Detect
""",
        """
Calyrex-Shadow @ Life Orb
Ability: As One (Spectrier)
Level: 50
Tera Type: Dark
EVs: 28 HP / 84 Def / 236 SpA / 4 SpD / 156 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Psychic
- Nasty Plot
- Protect

Chi-Yu @ Choice Scarf
Ability: Beads of Ruin
Level: 50
Tera Type: Ghost
EVs: 20 HP / 52 Def / 180 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 14 Atk
- Heat Wave
- Dark Pulse
- Snarl
- Overheat

Flutter Mane @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Grass
EVs: 116 HP / 44 Def / 92 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 14 Atk
- Moonblast
- Icy Wind
- Thunder Wave
- Protect

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Fire
EVs: 236 HP / 228 Def / 44 SpD
Relaxed Nature
- Rage Powder
- Sludge Bomb
- Spore
- Protect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Water
EVs: 172 HP / 84 Atk / 4 Def / 244 SpD / 4 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- U-turn
- Fake Out

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Protect
""",
        """
GROUN (Groudon) @ Assault Vest
Ability: Drought
Tera Type: Fire
EVs: 188 HP / 76 Atk / 12 Def / 84 SpD / 148 Spe
Adamant Nature
- Precipice Blades
- Heat Crash
- Thunder Punch
- High Horsepower

Rengoku (Gouging Fire) @ Clear Amulet
Ability: Protosynthesis
Tera Type: Fairy
EVs: 164 HP / 84 Atk / 4 Def / 4 SpD / 252 Spe
Jolly Nature
- Flare Blitz
- Howl
- Protect
- Breaking Swipe

Kirin (Raging Bolt) @ Life Orb
Ability: Protosynthesis
Tera Type: Electric
EVs: 68 HP / 124 Def / 212 SpA / 44 SpD / 60 Spe
Modest Nature
- Thunderbolt
- Thunderclap
- Draco Meteor
- Protect

Volcaruba (Volcarona) @ Rocky Helmet
Ability: Flame Body
Tera Type: Water
EVs: 252 HP / 212 Def / 44 SpD
Bold Nature
IVs: 20 Atk
- Heat Wave
- Rage Powder
- Will-O-Wisp
- Tailwind

Asgard (Chien-Pao) @ Focus Sash
Ability: Sword of Ruin
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Icicle Crash
- Crunch
- Sucker Punch
- Protect

Megumi (Iron Valiant) @ Booster Energy
Ability: Quark Drive
Tera Type: Dark
EVs: 100 HP / 4 Atk / 4 Def / 196 SpD / 204 Spe
Jolly Nature
- Spirit Break
- Wide Guard
- Coaching
- Icy Wind
""",
        ### BRISBANE REGIONALS MARCH 2025 (4 teams) ###
        """
Terapagos @ Leftovers
Ability: Tera Shift
Level: 50
Tera Type: Stellar
EVs: 172 HP / 164 Def / 164 SpA / 4 SpD / 4 Spe
Bold Nature
IVs: 15 Atk
- Tera Starstorm
- Substitute
- Calm Mind
- Protect

Incineroar @ Rocky Helmet
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 188 Def / 76 SpD
Impish Nature
- Knock Off
- Will-O-Wisp
- Parting Shot
- Fake Out

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Grass
EVs: 252 HP / 116 Def / 140 SpD
Adamant Nature
- Wood Hammer
- Grassy Glide
- U-turn
- Fake Out

Scream Tail @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Grass
EVs: 252 HP / 132 Def / 4 SpA / 4 SpD / 116 Spe
Timid Nature
IVs: 0 Atk
- Dazzling Gleam
- Encore
- Disable
- Protect

Ogerpon-Cornerstone (F) @ Cornerstone Mask
Ability: Sturdy
Level: 50
Tera Type: Rock
EVs: 4 HP / 196 Atk / 52 Def / 4 SpD / 252 Spe
Jolly Nature
- Ivy Cudgel
- Power Whip
- Follow Me
- Spiky Shield

Heatran @ Sitrus Berry
Ability: Flash Fire
Level: 50
Tera Type: Fairy
EVs: 252 HP / 4 Atk / 100 Def / 76 SpA / 76 SpD
Quiet Nature
- Magma Storm
- Heavy Slam
- Tera Blast
- Protect
""",
        """
Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Tera Type: Stellar
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Ice Spinner
- Crunch
- Sucker Punch
- Protect

Zamazenta @ Rusted Shield
Ability: Dauntless Shield
Level: 70
Tera Type: Dragon
EVs: 92 HP / 4 Atk / 244 Def / 4 SpD / 164 Spe
Impish Nature
- Body Press
- Heavy Slam
- Wide Guard
- Protect

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 252 HP / 236 Def / 20 SpD
Bold Nature
IVs: 0 Atk / 26 Spe
- Sludge Bomb
- Spore
- Rage Powder
- Pollen Puff

Mesprit @ Leftovers
Ability: Levitate
Level: 50
Tera Type: Water
EVs: 204 HP / 76 Def / 52 SpA / 20 SpD / 156 Spe
Bold Nature
IVs: 0 Atk
- Mystical Power
- Dazzling Gleam
- Thunder Wave
- Protect

Flutter Mane @ Booster Energy
Ability: Protosynthesis
Tera Type: Water
EVs: 244 HP / 108 Def / 4 SpA / 4 SpD / 148 Spe
Timid Nature
IVs: 4 Atk
- Moonblast
- Shadow Ball
- Icy Wind
- Protect

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 75
Tera Type: Grass
EVs: 196 HP / 164 Def / 100 SpA / 4 SpD / 44 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Draco Meteor
- Thunderclap
- Electroweb
""",
        """
Rabsca @ Mental Herb
Ability: Telepathy
Level: 50
Shiny: Yes
Tera Type: Water
EVs: 252 HP / 252 Def / 4 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Bug Buzz
- Speed Swap
- Trick Room
- Revival Blessing

Ursaluna @ Flame Orb
Ability: Guts
Level: 56
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
IVs: 24 SpA
- Headlong Rush
- Facade
- Earthquake
- Protect

Miraidon @ Life Orb
Ability: Hadron Engine
Tera Type: Fairy
EVs: 4 Def / 252 SpA / 252 Spe
Modest Nature
- Discharge
- Dazzling Gleam
- Electro Drift
- Protect

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 61
Tera Type: Grass
EVs: 108 HP / 252 Atk / 4 Def / 124 SpD / 20 Spe
Adamant Nature
- Fake Out
- Drain Punch
- Heavy Slam
- Low Kick

Zapdos-Galar @ Covert Cloak
Ability: Defiant
Level: 50
Tera Type: Dark
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Close Combat
- Brave Bird
- Detect
- Tailwind

Volcarona @ Rocky Helmet
Ability: Flame Body
Level: 80
Shiny: Yes
Tera Type: Fairy
EVs: 212 HP / 212 Def / 36 SpA / 4 SpD / 44 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Heat Wave
- Struggle Bug
- Rage Powder
""",
        """
Calyrex-Shadow @ Choice Specs
Ability: As One (Spectrier)
Tera Type: Ghost
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 1 Atk
- Astral Barrage
- Expanding Force
- Shadow Ball
- Pollen Puff

Indeedee-F @ Rocky Helmet
Ability: Psychic Surge
Shiny: Yes
Tera Type: Fairy
EVs: 252 HP / 252 Def / 4 SpD
Relaxed Nature
IVs: 0 Atk / 21 SpA / 11 Spe
- Imprison
- Helping Hand
- Follow Me
- Trick Room

Chi-Yu @ Assault Vest
Ability: Beads of Ruin
Tera Type: Steel
EVs: 84 HP / 4 Def / 180 SpA / 4 SpD / 236 Spe
Modest Nature
IVs: 18 Atk
- Heat Wave
- Dark Pulse
- Overheat
- Snarl

Whimsicott @ Covert Cloak
Ability: Prankster
Tera Type: Dark
EVs: 252 HP / 4 Def / 60 SpA / 188 SpD / 4 Spe
Calm Nature
IVs: 6 Atk
- Tailwind
- Light Screen
- Sunny Day
- Moonblast

Ogerpon-Wellspring @ Wellspring Mask
Ability: Water Absorb
Tera Type: Water
EVs: 252 HP / 36 Atk / 124 Def / 92 SpD / 4 Spe
Impish Nature
IVs: 20 SpA
- Follow Me
- Ivy Cudgel
- Wood Hammer
- Spiky Shield

Urshifu-Rapid-Strike (F) @ Choice Band
Ability: Unseen Fist
Tera Type: Water
EVs: 68 HP / 252 Atk / 4 Def / 4 SpD / 180 Spe
Jolly Nature
IVs: 18 SpA
- Surging Strikes
- Close Combat
- U-turn
- Aqua Jet
""",
        ### STOCKHOLM REGIONALS MARCH 2025 (7 teams) ###
        """
Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Fire
EVs: 252 HP / 196 Atk / 60 SpD
Brave Nature
IVs: 27 SpA / 0 Spe
- Glacial Lance
- Close Combat
- Trick Room
- Protect

Indeedee-F @ Rocky Helmet
Ability: Psychic Surge
Level: 50
Tera Type: Fairy
EVs: 252 HP / 244 Def / 12 SpD
Bold Nature
IVs: 0 Atk / 13 Spe
- Psychic
- Follow Me
- Helping Hand
- Trick Room

Smeargle @ Focus Sash
Ability: Technician
Level: 50
Tera Type: Grass
EVs: 12 HP / 244 Def / 252 Spe
Jolly Nature
IVs: 30 SpA
- Fake Out
- Spore
- Follow Me
- Decorate

Raging Bolt @ Safety Goggles
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 196 HP / 60 Def / 252 SpA
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Draco Meteor
- Thunderclap
- Protect

Urshifu @ Choice Band
Ability: Unseen Fist
Level: 50
Tera Type: Grass
EVs: 220 HP / 252 Atk / 36 SpD
Brave Nature
IVs: 2 Spe
- Wicked Blow
- Close Combat
- Sucker Punch
- Iron Head

Torkoal @ Choice Specs
Ability: Drought
Level: 50
Tera Type: Fire
EVs: 252 HP / 4 Def / 252 SpA
Quiet Nature
IVs: 0 Atk / 0 Spe
- Eruption
- Heat Wave
- Earth Power
- Weather Ball
""",
        """
Koraidon @ Life Orb
Ability: Orichalcum Pulse
Level: 50
Tera Type: Fire
EVs: 4 HP / 244 Atk / 4 Def / 4 SpD / 252 Spe
Adamant Nature
- Close Combat
- Breaking Swipe
- Flare Blitz
- Protect

Brute Bonnet @ Covert Cloak
Ability: Protosynthesis
Level: 50
Tera Type: Water
EVs: 252 HP / 4 Atk / 132 Def / 116 SpD / 4 Spe
Impish Nature
- Seed Bomb
- Sucker Punch
- Spore
- Rage Powder

Chi-Yu @ Choice Scarf
Ability: Beads of Ruin
Level: 50
Tera Type: Fire
EVs: 4 HP / 4 Def / 244 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Overheat
- Dark Pulse
- Heat Wave
- Flamethrower

Flutter Mane @ Fairy Feather
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 100 HP / 204 Def / 52 SpA / 4 SpD / 148 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Dazzling Gleam
- Icy Wind
- Protect

Heatran @ Zoom Lens
Ability: Flash Fire
Level: 50
Tera Type: Fairy
EVs: 244 HP / 244 Def / 20 SpA
Bold Nature
IVs: 21 Atk
- Magma Storm
- Tera Blast
- Substitute
- Protect

Walking Wake @ Choice Specs
Ability: Protosynthesis
Level: 50
Tera Type: Water
EVs: 36 HP / 4 Def / 252 SpA / 4 SpD / 212 Spe
Timid Nature
IVs: 11 Atk
- Hydro Steam
- Draco Meteor
- Dragon Pulse
- Snarl
""",
        """
Calyrex-Shadow @ Sitrus Berry
Ability: As One (Spectrier)
Level: 50
Tera Type: Fairy
EVs: 84 HP / 12 Def / 156 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Draining Kiss
- Nasty Plot
- Protect

Mienshao @ Focus Sash
Ability: Inner Focus
Level: 50
Tera Type: Fighting
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Close Combat
- Fake Out
- Feint
- Wide Guard

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 236 HP / 116 Atk / 4 Def / 76 SpD / 76 Spe
Adamant Nature
- Grassy Glide
- Wood Hammer
- Fake Out
- U-turn

Flutter Mane @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 244 HP / 172 Def / 84 SpA / 4 SpD / 4 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Shadow Ball
- Icy Wind
- Protect

Chi-Yu @ Covert Cloak
Ability: Beads of Ruin
Level: 50
Tera Type: Water
EVs: 244 HP / 140 Def / 36 SpA / 4 SpD / 84 Spe
Modest Nature
IVs: 0 Atk
- Heat Wave
- Snarl
- Overheat
- Taunt

Clefairy @ Eviolite
Ability: Friend Guard
Level: 50
Tera Type: Grass
EVs: 252 HP / 252 Def / 4 SpD
Bold Nature
IVs: 0 Atk / 16 Spe
- Follow Me
- Helping Hand
- Sing
- Protect
""",
        """
Calyrex-Shadow @ Spooky Plate
Ability: As One (Spectrier)
Level: 50
Tera Type: Fairy
EVs: 140 HP / 180 Def / 36 SpA / 4 SpD / 148 Spe
Modest Nature
IVs: 0 Atk
- Astral Barrage
- Draining Kiss
- Nasty Plot
- Protect

Whimsicott @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 212 HP / 244 SpD / 52 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Tailwind
- Encore
- Light Screen

Incineroar @ Rocky Helmet
Ability: Intimidate
Level: 50
Tera Type: Poison
EVs: 244 HP / 4 Atk / 84 Def / 132 SpD / 44 Spe
Impish Nature
- Fake Out
- Knock Off
- Taunt
- Parting Shot

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Detect

Ogerpon-Hearthflame @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 236 HP / 76 Atk / 180 Def / 4 SpD / 12 Spe
Adamant Nature
- Ivy Cudgel
- Wood Hammer
- Follow Me
- Spiky Shield

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 50
Tera Type: Water
EVs: 92 HP / 196 Atk / 12 Def / 164 SpD / 44 Spe
Adamant Nature
- Fake Out
- Drain Punch
- Low Kick
- Heavy Slam
""",
        """
Lunala @ Power Herb
Ability: Shadow Shield
Level: 50
Tera Type: Grass
EVs: 156 HP / 4 Def / 252 SpA / 4 SpD / 92 Spe
Modest Nature
IVs: 0 Atk
- Moongeist Beam
- Meteor Beam
- Expanding Force
- Trick Room

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Surging Strikes
- Detect
- U-turn
- Close Combat

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 252 HP / 172 Def / 84 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Rage Powder
- Spore
- Pollen Puff
- Clear Smog

Indeedee-F @ Psychic Seed
Ability: Psychic Surge
Level: 50
Tera Type: Fairy
EVs: 252 HP / 252 Def / 4 SpD
Bold Nature
IVs: 0 Atk / 27 Spe
- Follow Me
- Helping Hand
- Alluring Voice
- Trick Room

Tornadus @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 252 HP / 164 Def / 4 SpA / 36 SpD / 52 Spe
Timid Nature
IVs: 0 Atk
- Bleakwind Storm
- Rain Dance
- Tailwind
- Taunt

Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Ghost
EVs: 252 HP / 252 Atk / 4 SpD
Brave Nature
IVs: 0 Spe
- Facade
- Headlong Rush
- Substitute
- Protect
""",
        """
Calyrex-Shadow @ Life Orb
Ability: As One (Spectrier)
Tera Type: Normal
EVs: 108 HP / 4 Def / 132 SpA / 12 SpD / 252 Spe
Timid Nature
IVs: 2 Atk
- Astral Barrage
- Psychic
- Nasty Plot
- Protect

Incineroar @ Rocky Helmet
Ability: Intimidate
Tera Type: Water
EVs: 244 HP / 188 Def / 76 SpD
Relaxed Nature
IVs: 0 Spe
- Knock Off
- Parting Shot
- Flare Blitz
- Fake Out

Rillaboom @ Assault Vest
Ability: Grassy Surge
Tera Type: Fire
EVs: 244 HP / 116 Atk / 4 Def / 84 SpD / 60 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- U-turn
- Fake Out

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Detect

Clefairy @ Eviolite
Ability: Friend Guard
Tera Type: Grass
EVs: 252 HP / 180 Def / 76 SpD
Bold Nature
IVs: 0 Atk
- Helping Hand
- Protect
- Sing
- Follow Me

Raging Bolt @ Booster Energy
Ability: Protosynthesis
Tera Type: Electric
EVs: 196 HP / 4 Def / 212 SpA / 4 SpD / 92 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Dragon Pulse
- Thunderclap
- Protect
""",
        """
Eternatus @ Choice Specs
Ability: Pressure
Level: 50
Tera Type: Poison
EVs: 28 HP / 28 Def / 196 SpA / 20 SpD / 236 Spe
Modest Nature
IVs: 0 Atk
- Sludge Bomb
- Dynamax Cannon
- Sludge Wave
- Fire Blast

Tinkaton @ Assault Vest
Ability: Mold Breaker
Level: 50
Tera Type: Dragon
EVs: 252 HP / 68 Atk / 164 Def / 4 SpD / 20 Spe
Jolly Nature
- Gigaton Hammer
- Play Rough
- Feint
- Fake Out

Ogerpon-Hearthflame (F) @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 252 HP / 44 Atk / 100 Def / 12 SpD / 100 Spe
Jolly Nature
- Ivy Cudgel
- Wood Hammer
- Follow Me
- Spiky Shield

Urshifu @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Dark
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Wicked Blow
- Close Combat
- Sucker Punch
- Protect

Araquanid @ Safety Goggles
Ability: Water Bubble
Level: 50
Tera Type: Water
EVs: 252 HP / 204 Atk / 52 Def
Adamant Nature
- Liquidation
- Wide Guard
- Sticky Web
- Protect

Flutter Mane @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Steel
EVs: 228 HP / 132 Def / 4 SpA / 12 SpD / 132 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Shadow Ball
- Icy Wind
- Protect
""",
        ### VANCOUVER REGIONALS MARCH 2025 (9 teams) ###
        """
Lunala @ Power Herb
Ability: Shadow Shield
Level: 50
Tera Type: Water
EVs: 116 HP / 108 Def / 252 SpA / 28 SpD / 4 Spe
Modest Nature
IVs: 0 Atk
- Moongeist Beam
- Meteor Beam
- Expanding Force
- Trick Room

Landorus @ Life Orb
Ability: Sheer Force
Level: 50
Tera Type: Poison
EVs: 164 HP / 140 SpA / 204 SpD
Modest Nature
IVs: 0 Atk
- Earth Power
- Sludge Bomb
- Sandsear Storm
- Protect

Indeedee-F @ Rocky Helmet
Ability: Psychic Surge
Level: 50
Tera Type: Fairy
EVs: 252 HP / 252 Def
Bold Nature
IVs: 0 Atk / 28 Spe
- Follow Me
- Alluring Voice
- Trick Room
- Helping Hand

Ogerpon-Hearthflame (F) @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 220 HP / 12 Atk / 252 Def / 4 SpD / 20 Spe
Jolly Nature
- Ivy Cudgel
- Wood Hammer
- Follow Me
- Spiky Shield

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Taunt
- Detect

Roaring Moon @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Flying
EVs: 44 HP / 196 Atk / 4 Def / 12 SpD / 252 Spe
Jolly Nature
- Acrobatics
- Knock Off
- Tailwind
- Protect
""",
        """
Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 44 HP / 4 Def / 244 SpA / 4 SpD / 212 Spe
Modest Nature
- Electro Drift
- Draco Meteor
- Volt Switch
- Dazzling Gleam

Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Poison
EVs: 76 HP / 236 Atk / 4 Def / 4 SpD / 188 Spe
Adamant Nature
- Facade
- Headlong Rush
- Earthquake
- Protect

Whimsicott @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 236 HP / 116 SpD / 156 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Tailwind
- Light Screen
- Encore

Incineroar @ Assault Vest
Ability: Intimidate
Level: 50
Tera Type: Dragon
EVs: 220 HP / 196 Atk / 4 Def / 4 SpD / 84 Spe
Adamant Nature
- Fake Out
- Flare Blitz
- Knock Off
- U-turn

Farigiraf @ Electric Seed
Ability: Armor Tail
Level: 50
Tera Type: Water
EVs: 204 HP / 196 Def / 108 SpD
Bold Nature
IVs: 0 Atk
- Foul Play
- Psychic
- Trick Room
- Helping Hand

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Protect
""",
        """
Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 236 HP / 236 Def / 36 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Spore
- Rage Powder
- Pollen Puff
- Protect

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 252 HP / 36 Atk / 84 Def / 84 SpD / 52 Spe
Adamant Nature
- Parting Shot
- Flare Blitz
- Knock Off
- Fake Out

Urshifu-Rapid-Strike @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 44 HP / 156 Atk / 4 Def / 52 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- U-turn

Raging Bolt @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 252 HP / 252 SpA / 4 SpD
Modest Nature
IVs: 20 Atk
- Thunderclap
- Draco Meteor
- Thunderbolt
- Protect

Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Water
EVs: 252 HP / 116 Atk / 4 Def / 132 SpD / 4 Spe
Adamant Nature
- Glacial Lance
- High Horsepower
- Trick Room
- Protect

Ogerpon-Cornerstone @ Cornerstone Mask
Ability: Sturdy
Level: 50
Tera Type: Rock
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Ivy Cudgel
- Taunt
- Follow Me
- Spiky Shield
""",
        """
Gru (Kyogre) @ Leftovers
Ability: Drizzle
Level: 50
Tera Type: Grass
EVs: 140 HP / 148 Def / 92 SpA / 12 SpD / 116 Spe
Modest Nature
IVs: 0 Atk
- Origin Pulse
- Ice Beam
- Calm Mind
- Protect

Kevin (Incineroar) @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 4 Atk / 188 Def / 60 SpD / 12 Spe
Impish Nature
- Knock Off
- Will-O-Wisp
- Parting Shot
- Fake Out

Stuart (Rillaboom) @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 132 HP / 92 Atk / 4 Def / 28 SpD / 252 Spe
Jolly Nature
- Drum Beating
- Grassy Glide
- U-turn
- Fake Out

Bob (Amoonguss) @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Fairy
EVs: 236 HP / 228 Def / 44 SpD
Bold Nature
IVs: 0 Atk / 27 Spe
- Sludge Bomb
- Spore
- Rage Powder
- Protect

Nefario (Urshifu-Rapid-Strike) @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Ghost
EVs: 4 HP / 236 Atk / 4 Def / 12 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- U-turn

The Moon (Roaring Moon) @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Flying
EVs: 116 HP / 36 Atk / 156 Def / 4 SpD / 196 Spe
Jolly Nature
- Knock Off
- Acrobatics
- Tailwind
- Protect
""",
        """
Zacian-Crowned @ Rusted Sword
Ability: Intrepid Sword
Level: 50
Tera Type: Water
EVs: 92 HP / 252 Atk / 4 Def / 4 SpD / 156 Spe
Jolly Nature
- Behemoth Blade
- Play Rough
- Sacred Sword
- Protect

Tornadus @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 252 HP / 180 Def / 76 SpD
Calm Nature
IVs: 0 Atk
- Bleakwind Storm
- Rain Dance
- Tailwind
- Taunt

Landorus @ Life Orb
Ability: Sheer Force
Level: 50
Tera Type: Water
EVs: 4 HP / 28 Def / 156 SpA / 68 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Protect
- Sandsear Storm
- Earth Power
- Sludge Bomb

Urshifu-Rapid-Strike @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Grass
EVs: 252 Atk / 252 Spe
Adamant Nature
- Surging Strikes
- Aqua Jet
- Close Combat
- U-turn

Okidogi @ Assault Vest
Ability: Guard Dog
Level: 50
Tera Type: Grass
EVs: 156 HP / 252 Atk / 4 Def / 4 SpD / 92 Spe
Adamant Nature
- Knock Off
- Drain Punch
- Upper Hand
- Gunk Shot

Rotom-Wash @ Safety Goggles
Ability: Levitate
Level: 50
Tera Type: Steel
EVs: 244 HP / 100 Def / 44 SpA / 76 SpD / 44 Spe
Bold Nature
IVs: 0 Atk
- Thunderbolt
- Hydro Pump
- Foul Play
- Will-O-Wisp
""",
        """
Regidrago @ Life Orb
Ability: Dragon's Maw
Level: 50
Tera Type: Ghost
EVs: 28 HP / 4 Def / 252 SpA / 4 SpD / 220 Spe
Modest Nature
IVs: 0 Atk
- Draco Meteor
- Dragon Energy
- Tera Blast
- Protect

Zacian-Crowned @ Rusted Sword
Ability: Intrepid Sword
Level: 50
Tera Type: Fairy
EVs: 68 HP / 252 Atk / 4 Def / 4 SpD / 180 Spe
Jolly Nature
- Behemoth Blade
- Play Rough
- Swords Dance
- Protect

Tornadus @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 140 HP / 20 Def / 4 SpA / 92 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Taunt
- Rain Dance
- Tailwind
- Bleakwind Storm

Ogerpon-Hearthflame @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 220 HP / 12 Atk / 156 Def / 12 SpD / 108 Spe
Jolly Nature
- Ivy Cudgel
- Follow Me
- Wood Hammer
- Spiky Shield

Urshifu-Rapid-Strike @ Choice Band
Ability: Unseen Fist
Level: 50
Tera Type: Grass
EVs: 60 HP / 92 Atk / 12 Def / 124 SpD / 220 Spe
Adamant Nature
- U-turn
- Surging Strikes
- Close Combat
- Aqua Jet

Farigiraf @ Safety Goggles
Ability: Armor Tail
Level: 50
Tera Type: Water
EVs: 228 HP / 140 Def / 4 SpA / 124 SpD / 12 Spe
Bold Nature
IVs: 0 Atk
- Foul Play
- Trick Room
- Helping Hand
- Psychic
""",
        """
Calyrex-Shadow @ Focus Sash
Ability: As One (Spectrier)
Level: 50
Tera Type: Ghost
EVs: 4 HP / 4 Def / 244 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Psychic
- Nasty Plot
- Protect

Tornadus @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 244 HP / 236 Def / 28 SpD
Bold Nature
IVs: 0 Atk
- Bleakwind Storm
- Tailwind
- Rain Dance
- Taunt

Tinkaton @ Assault Vest
Ability: Mold Breaker
Level: 50
Tera Type: Grass
EVs: 252 HP / 196 Atk / 44 Def / 4 SpD / 12 Spe
Adamant Nature
- Fake Out
- Gigaton Hammer
- Play Rough
- Feint

Urshifu-Rapid-Strike @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 44 HP / 204 Atk / 4 Def / 4 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- U-turn

Amoonguss @ Mental Herb
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 236 HP / 156 Def / 116 SpD
Bold Nature
IVs: 0 Atk / 26 Spe
- Rage Powder
- Spore
- Sludge Bomb
- Protect

Landorus @ Life Orb
Ability: Sheer Force
Level: 50
Tera Type: Poison
EVs: 28 HP / 100 Def / 124 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Earth Power
- Sludge Bomb
- Sandsear Storm
- Protect
""",
        """
Incineroar (M) @ Safety Goggles
Ability: Intimidate
Shiny: Yes
Tera Type: Bug
EVs: 244 HP / 4 Atk / 188 Def / 12 SpD / 60 Spe
Impish Nature
IVs: 0 SpA
- Flare Blitz
- Fake Out
- Knock Off
- Parting Shot

Urshifu-Rapid-Strike (M) @ Choice Scarf
Ability: Unseen Fist
Tera Type: Water
EVs: 92 HP / 76 Atk / 4 Def / 84 SpD / 252 Spe
Adamant Nature
IVs: 20 SpA
- Surging Strikes
- Close Combat
- U-turn
- Aqua Jet

Rillaboom (M) @ Assault Vest
Ability: Grassy Surge
Shiny: Yes
Tera Type: Fire
EVs: 252 HP / 4 SpD / 252 Spe
Jolly Nature
IVs: 29 SpA
- Drum Beating
- Fake Out
- Grassy Glide
- U-turn

Lunala @ Grassy Seed
Ability: Shadow Shield
Shiny: Yes
Tera Type: Fairy
EVs: 116 HP / 4 Def / 132 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 8 Atk
- Protect
- Calm Mind
- Dazzling Gleam
- Moongeist Beam

Pelipper (F) @ Covert Cloak
Ability: Drizzle
Tera Type: Dark
EVs: 252 HP / 76 Def / 4 SpA / 132 SpD / 44 Spe
Bold Nature
IVs: 0 Atk
- Protect
- Wide Guard
- Weather Ball
- Hurricane

Goodra-Hisui (M) @ Leftovers
Ability: Sap Sipper
Shiny: Yes
Tera Type: Water
EVs: 236 HP / 244 Def / 28 Spe
Impish Nature
- Life Dew
- Shelter
- Body Press
- Heavy Slam
""",
        """
Garganacl @ Leftovers
Ability: Purifying Salt
Level: 50
Shiny: Yes
Tera Type: Water
EVs: 252 HP / 60 Def / 196 SpD
Sassy Nature
- Salt Cure
- Recover
- Wide Guard
- Protect

Chi-Yu @ Choice Scarf
Ability: Beads of Ruin
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 0 Atk
- Snarl
- Heat Wave
- Dark Pulse
- Overheat

Flutter Mane @ Focus Sash
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Icy Wind
- Shadow Ball
- Moonblast
- Protect

Groudon @ Clear Amulet
Ability: Drought
Level: 50
Tera Type: Fire
EVs: 180 HP / 252 Atk / 76 Spe
Adamant Nature
- Heat Crash
- Precipice Blades
- Stomping Tantrum
- Protect

Whimsicott @ Covert Cloak
Ability: Prankster
Level: 50
Shiny: Yes
Tera Type: Dark
EVs: 76 HP / 4 Def / 156 SpA / 52 SpD / 220 Spe
Timid Nature
IVs: 0 Atk
- Tailwind
- Sunny Day
- Moonblast
- Misty Terrain

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 188 HP / 140 Def / 100 SpA / 12 SpD / 68 Spe
Modest Nature
IVs: 20 Atk
- Thunderclap
- Volt Switch
- Draco Meteor
- Snarl
""",
        ### FORTALEZA REGIONALS MARCH 2025 (1 team) ###
        """
Koraidon @ Clear Amulet
Ability: Orichalcum Pulse
Level: 50
Tera Type: Fire
EVs: 236 HP / 196 Atk / 4 Def / 4 SpD / 68 Spe
Adamant Nature
- Collision Course
- Flare Blitz
- Flame Charge
- Protect

Raging Bolt @ Life Orb
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 148 HP / 164 Def / 100 SpA / 4 SpD / 92 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Thunderclap
- Draco Meteor
- Protect

Flutter Mane @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Normal
EVs: 244 HP / 132 Def / 4 SpA / 4 SpD / 124 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Icy Wind
- Thunder Wave
- Protect

Ogerpon-Cornerstone @ Cornerstone Mask
Ability: Sturdy
Level: 50
Tera Type: Rock
EVs: 36 HP / 204 Atk / 12 Def / 4 SpD / 252 Spe
Jolly Nature
- Ivy Cudgel
- Power Whip
- Follow Me
- Spiky Shield

Chi-Yu @ Covert Cloak
Ability: Beads of Ruin
Level: 50
Tera Type: Water
EVs: 172 HP / 44 Def / 36 SpA / 12 SpD / 244 Spe
Modest Nature
IVs: 0 Atk
- Heat Wave
- Snarl
- Overheat
- Taunt

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 4 Atk / 196 Def / 52 SpD / 12 Spe
Impish Nature
- Knock Off
- Fake Out
- Will-O-Wisp
- Parting Shot
""",
        ### EUIC FEBRUARY 2025 (20 teams) ###
        """
Flutter Mane @ Focus Sash
Ability: Protosynthesis
Level: 50
Tera Type: Normal
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Icy Wind
- Moonblast
- Shadow Ball

Koraidon @ Life Orb
Ability: Orichalcum Pulse
Level: 50
Tera Type: Fire
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Protect
- Flame Charge
- Close Combat
- Flare Blitz

Amoonguss @ Mental Herb
Ability: Regenerator
Level: 50
Tera Type: Dark
EVs: 236 HP / 76 Def / 196 SpD
Sassy Nature
IVs: 0 Atk / 0 Spe
- Protect
- Rage Powder
- Sludge Bomb
- Spore

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Bug
EVs: 252 HP / 124 Def / 132 SpD
Careful Nature
IVs: 29 Spe
- Protect
- Flare Blitz
- Fake Out
- Parting Shot

Gothitelle @ Leftovers
Ability: Shadow Tag
Level: 50
Tera Type: Water
EVs: 252 HP / 196 Def / 4 SpA / 52 SpD / 4 Spe
Bold Nature
IVs: 0 Atk
- Protect
- Psychic
- Fake Out
- Taunt

Scream Tail @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Dark
EVs: 252 HP / 84 Def / 68 SpD / 100 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Encore
- Disable
- Perish Song""",
        """
megabeast:3 (Miraidon) @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 172 HP / 4 Def / 124 SpA / 4 SpD / 204 Spe
Modest Nature
- Electro Drift
- Volt Switch
- Draco Meteor
- Dazzling Gleam

hellofreak (Incineroar) (F) @ Rocky Helmet
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 252 HP / 140 Def / 116 SpD
Careful Nature
IVs: 11 Spe
- Flare Blitz
- Knock Off
- U-turn
- Fake Out

radicalqueen (Urshifu) (F) @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Dark
EVs: 4 HP / 236 Atk / 20 Def / 4 SpD / 244 Spe
Adamant Nature
- Wicked Blow
- Sucker Punch
- Close Combat
- Detect

partypirate (Iron Hands) @ Assault Vest
Ability: Quark Drive
Level: 50
Tera Type: Poison
EVs: 76 HP / 164 Atk / 12 Def / 252 SpD
Brave Nature
IVs: 0 Spe
- Drain Punch
- Low Kick
- Heavy Slam
- Fake Out

crimsonracer (Iron Treads) @ Choice Band
Ability: Quark Drive
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 252 Atk / 36 SpD / 220 Spe
Jolly Nature
- High Horsepower
- Iron Head
- Steel Roller
- Rock Slide

mythicdreamr (Farigiraf) (M) @ Electric Seed
Ability: Armor Tail
Level: 50
Shiny: Yes
Tera Type: Water
EVs: 228 HP / 164 Def / 116 SpD
Bold Nature
IVs: 20 Atk / 13 Spe
- Psychic
- Roar
- Trick Room
- Helping Hand
""",
        """
Tornadus @ Covert Cloak
Ability: Prankster
Level: 78
Tera Type: Dark
EVs: 68 HP / 196 Def / 92 SpA / 4 SpD / 148 Spe
Bold Nature
IVs: 20 Atk
- Bleakwind Storm
- Rain Dance
- Tailwind
- Taunt

Kyogre @ Mystic Water
Ability: Drizzle
Tera Type: Grass
EVs: 92 HP / 4 Def / 236 SpA / 4 SpD / 172 Spe
Modest Nature
- Water Spout
- Origin Pulse
- Protect
- Ice Beam

Urshifu-Rapid-Strike @ Choice Scarf
Ability: Unseen Fist
Level: 52
Tera Type: Water
EVs: 28 HP / 196 Atk / 28 Def / 4 SpD / 252 Spe
Adamant Nature
IVs: 3 SpA
- Surging Strikes
- Close Combat
- Aqua Jet
- U-turn

Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
IVs: 3 SpA
- Icicle Crash
- Sucker Punch
- Sacred Sword
- Protect

Amoonguss (F) @ Rocky Helmet
Ability: Regenerator
Level: 59
Tera Type: Dark
EVs: 220 HP / 228 Def / 60 SpD
Bold Nature
IVs: 12 Atk / 16 Spe
- Spore
- Rage Powder
- Clear Smog
- Pollen Puff

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 59
Tera Type: Grass
EVs: 12 HP / 244 Atk / 4 Def / 188 SpD / 60 Spe
Adamant Nature
IVs: 26 SpA
- Fake Out
- Drain Punch
- Wild Charge
- Low Kick
""",
        """
Cartman (Incineroar) @ Rocky Helmet
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 188 Def / 76 SpD
Relaxed Nature
IVs: 25 Spe
- Fake Out
- Helping Hand
- Knock Off
- Parting Shot

Trunkey (Rillaboom) @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 236 HP / 116 Atk / 4 Def / 140 SpD / 12 Spe
Adamant Nature
- Fake Out
- Wood Hammer
- Grassy Glide
- U-turn

Shido (Urshifu-Rapid-Strike) @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Protect

King Olly (Calyrex-Shadow) @ Life Orb
Ability: As One (Spectrier)
Level: 50
Tera Type: Normal
EVs: 108 HP / 36 Def / 100 SpA / 12 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Protect
- Nasty Plot
- Psychic

Odin’sWrath (Raging Bolt) @ Booster Energy
Ability: Protosynthesis
Tera Type: Fairy
EVs: 188 HP / 36 Def / 180 SpA / 4 SpD / 100 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Dragon Pulse
- Thunderclap
- Protect

Mio (Ogerpon-Hearthflame) (F) @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 188 HP / 76 Atk / 52 Def / 4 SpD / 188 Spe
Adamant Nature
- Ivy Cudgel
- Grassy Glide
- Follow Me
- Spiky Shield
""",
        """
Kyogre @ Leftovers
Ability: Drizzle
Level: 50
Tera Type: Grass
EVs: 244 HP / 172 Def / 4 SpA / 4 SpD / 84 Spe
Modest Nature
IVs: 0 Atk
- Origin Pulse
- Ice Beam
- Calm Mind
- Protect

Roaring Moon @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Flying
EVs: 148 HP / 84 Atk / 108 Def / 4 SpD / 164 Spe
Jolly Nature
- Acrobatics
- Knock Off
- Tailwind
- Protect

Archaludon @ Assault Vest
Ability: Stamina
Level: 50
Tera Type: Bug
EVs: 252 HP / 12 Def / 44 SpA / 116 SpD / 84 Spe
Modest Nature
IVs: 0 Atk
- Draco Meteor
- Flash Cannon
- Electro Shot
- Snarl

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Fairy
EVs: 244 HP / 188 Def / 76 SpD
Sassy Nature
IVs: 0 Atk
- Spore
- Rage Powder
- Sludge Bomb
- Protect

Basculegion @ Choice Band
Ability: Swift Swim
Level: 50
Tera Type: Water
EVs: 44 HP / 252 Atk / 36 Def / 4 SpD / 172 Spe
Adamant Nature
- Wave Crash
- Last Respects
- Flip Turn
- Aqua Jet

Rillaboom @ Miracle Seed
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 212 HP / 36 Atk / 12 Def / 236 SpD / 12 Spe
Careful Nature
- Grassy Glide
- Wood Hammer
- U-turn
- Fake Out
""",
        """
Incineroar @ Rocky Helmet
Ability: Intimidate
Level: 50
Tera Type: Poison
EVs: 252 HP / 4 Atk / 84 Def / 132 SpD / 36 Spe
Impish Nature
- Taunt
- Knock Off
- Parting Shot
- Fake Out

Calyrex-Shadow @ Spell Tag
Ability: As One (Spectrier)
Level: 50
Tera Type: Fairy
EVs: 188 HP / 132 Def / 36 SpA / 4 SpD / 148 Spe
Modest Nature
IVs: 0 Atk
- Astral Barrage
- Nasty Plot
- Protect
- Draining Kiss

Whimsicott @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 212 HP / 244 SpD / 52 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Tailwind
- Encore
- Light Screen

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Detect

Ogerpon-Hearthflame @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 252 HP / 44 Atk / 212 Def
Adamant Nature
- Ivy Cudgel
- Helping Hand
- Follow Me
- Spiky Shield

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 50
Tera Type: Fairy
EVs: 92 HP / 204 Atk / 12 Def / 156 SpD / 44 Spe
Adamant Nature
- Drain Punch
- Low Kick
- Fake Out
- Heavy Slam
""",
        """
Kyogre @ Mystic Water
Ability: Drizzle
Level: 50
Tera Type: Grass
EVs: 100 HP / 132 Def / 116 SpA / 4 SpD / 156 Spe
Modest Nature
- Water Spout
- Origin Pulse
- Ice Beam
- Protect

Tsareena @ Loaded Dice
Ability: Queenly Majesty
Level: 50
Tera Type: Ice
EVs: 36 HP / 236 Atk / 12 Def / 4 SpD / 220 Spe
Jolly Nature
- Bullet Seed
- Triple Axel
- Taunt
- Protect

Roaring Moon @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Flying
EVs: 68 HP / 76 Atk / 108 Def / 4 SpD / 252 Spe
Jolly Nature
- Knock Off
- Acrobatics
- Tailwind
- Protect

Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Ice Spinner
- Sacred Sword
- Sucker Punch
- Protect

Urshifu-Rapid-Strike @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 44 HP / 156 Atk / 4 Def / 52 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- U-turn

Raging Bolt @ Safety Goggles
Ability: Protosynthesis
Level: 50
Tera Type: Poison
EVs: 164 HP / 100 Def / 180 SpA / 4 SpD / 60 Spe
Modest Nature
- Thunderbolt
- Thunderclap
- Draco Meteor
- Protect
""",
        """
Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Fairy
EVs: 236 HP / 132 Atk / 4 Def / 100 SpD / 36 Spe
Adamant Nature
- Glacial Lance
- High Horsepower
- Trick Room
- Protect

Raging Bolt @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 196 HP / 108 Def / 196 SpA / 4 SpD / 4 Spe
Modest Nature
IVs: 20 Atk
- Dragon Pulse
- Thunderclap
- Thunderbolt
- Protect

Urshifu @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Sucker Punch
- Close Combat
- Wicked Blow
- Protect

Amoonguss @ Covert Cloak
Ability: Regenerator
Level: 50
Tera Type: Fire
EVs: 244 HP / 156 Def / 108 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Pollen Puff
- Spore
- Sludge Bomb
- Rage Powder

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Water
EVs: 204 HP / 4 Atk / 156 Def / 44 SpD / 100 Spe
Impish Nature
- Fake Out
- Knock Off
- Taunt
- Parting Shot

Landorus @ Choice Scarf
Ability: Sheer Force
Tera Type: Ghost
EVs: 4 HP / 4 Def / 244 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Sandsear Storm
- Sludge Bomb
- Earth Power
- Psychic
""",
        """
Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Tera Type: Fairy
EVs: 204 HP / 116 Atk / 4 Def / 28 SpD / 156 Spe
Adamant Nature
- Glacial Lance
- High Horsepower
- Protect
- Trick Room

Landorus @ Life Orb
Ability: Sheer Force
Tera Type: Water
EVs: 212 HP / 4 Def / 124 SpA / 4 SpD / 164 Spe
Modest Nature
IVs: 0 Atk
- Earth Power
- Sludge Bomb
- Sandsear Storm
- Protect

Amoonguss (F) @ Covert Cloak
Ability: Regenerator
Level: 50
Tera Type: Fairy
EVs: 244 HP / 156 Def / 108 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Pollen Puff
- Spore
- Protect
- Rage Powder

Urshifu-Rapid-Strike (M) @ Mystic Water
Ability: Unseen Fist
Tera Type: Water
EVs: 140 HP / 196 Atk / 20 Def / 44 SpD / 108 Spe
Adamant Nature
- Surging Strikes
- Aqua Jet
- Taunt
- Detect

Roaring Moon @ Booster Energy
Ability: Protosynthesis
Tera Type: Flying
EVs: 148 HP / 84 Atk / 76 Def / 4 SpD / 196 Spe
Jolly Nature
- Knock Off
- Acrobatics
- Protect
- Tailwind

Ogerpon-Hearthflame @ Hearthflame Mask
Ability: Mold Breaker
Tera Type: Fire
EVs: 220 HP / 12 Atk / 252 Def / 4 SpD / 20 Spe
Impish Nature
- Ivy Cudgel
- Horn Leech
- Follow Me
- Spiky Shield
""",
        """
Ehrmantraut (Calyrex-Ice) @ Clear Amulet
Ability: As One (Glastrier)
Tera Type: Poison
EVs: 252 HP / 116 Atk / 4 Def / 116 SpD / 20 Spe
Adamant Nature
- Protect
- Glacial Lance
- High Horsepower
- Trick Room

El Girafo (Raging Bolt) @ Booster Energy
Ability: Protosynthesis
Tera Type: Electric
EVs: 188 HP / 44 Def / 252 SpA / 4 SpD / 20 Spe
Modest Nature
IVs: 20 Atk
- Protect
- Thunderbolt
- Draco Meteor
- Thunderclap

Ichiban (Urshifu-Rapid-Strike) @ Choice Scarf
Ability: Unseen Fist
Tera Type: Water
EVs: 4 HP / 236 Atk / 4 Def / 12 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Coaching
- U-turn

Adachi (Amoonguss) @ Rocky Helmet
Ability: Regenerator
Tera Type: Fairy
EVs: 236 HP / 156 Def / 116 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Protect
- Pollen Puff
- Rage Powder
- Spore

Nanba (Landorus) @ Life Orb
Ability: Sheer Force
Tera Type: Poison
EVs: 44 HP / 4 Def / 204 SpA / 4 SpD / 252 Spe
Timid Nature
- Protect
- Earth Power
- Sludge Bomb
- Sandsear Storm

Pat’s Pelipper (Pelipper) @ Covert Cloak
Ability: Drizzle
Shiny: Yes
Tera Type: Grass
EVs: 252 HP / 4 Def / 196 SpA / 36 SpD / 20 Spe
Modest Nature
IVs: 8 Atk
- Protect
- Weather Ball
- Hurricane
- Wide Guard
""",
        """
Clefairy @ Eviolite
Ability: Friend Guard
Level: 50
Tera Type: Grass
EVs: 252 HP / 252 Def / 4 SpD
Bold Nature
IVs: 0 Atk / 17 Spe
- Follow Me
- Sing
- Helping Hand
- Protect

Mienshao @ Focus Sash
Ability: Inner Focus
Level: 50
Tera Type: Fighting
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Close Combat
- Taunt
- Wide Guard
- Fake Out

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 188 Def / 76 SpD
Impish Nature
IVs: 21 Spe
- Knock Off
- Will-O-Wisp
- Parting Shot
- Fake Out

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 244 HP / 12 Atk / 36 Def / 212 SpD / 4 Spe
Careful Nature
- Wood Hammer
- Grassy Glide
- U-turn
- Fake Out

Urshifu-Rapid-Strike @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 4 HP / 236 Atk / 4 Def / 12 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- U-turn
- Rain Dance

Calyrex-Shadow @ Covert Cloak
Ability: As One (Spectrier)
Level: 50
Tera Type: Fairy
EVs: 148 HP / 84 Def / 20 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Draining Kiss
- Calm Mind
- Protect
""",
        """
Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- U-turn
- Protect

Lunala @ Power Herb
Ability: Shadow Shield
Level: 50
Tera Type: Grass
EVs: 156 HP / 4 Def / 252 SpA / 4 SpD / 92 Spe
Modest Nature
IVs: 0 Atk
- Moongeist Beam
- Expanding Force
- Meteor Beam
- Trick Room

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 236 HP / 180 Def / 92 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Pollen Puff
- Spore
- Rage Powder
- Protect

Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Ghost
EVs: 252 HP / 252 Atk / 4 SpD
Brave Nature
IVs: 0 Spe
- Facade
- Headlong Rush
- Earthquake
- Protect

Indeedee-F @ Psychic Seed
Ability: Psychic Surge
Level: 50
Tera Type: Fairy
EVs: 252 HP / 252 Def / 4 SpD
Bold Nature
IVs: 0 Atk / 28 Spe
- Alluring Voice
- Follow Me
- Helping Hand
- Trick Room

Tornadus @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 244 HP / 196 Def / 4 SpA / 12 SpD / 52 Spe
Timid Nature
IVs: 0 Atk
- Bleakwind Storm
- Taunt
- Tailwind
- Rain Dance
""",
        """
Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Icicle Crash
- Crunch
- Sucker Punch
- Protect

Zamazenta-Crowned @ Rusted Shield
Ability: Dauntless Shield
Level: 50
Tera Type: Dragon
EVs: 92 HP / 4 Atk / 244 Def / 4 SpD / 164 Spe
Impish Nature
- Body Press
- Heavy Slam
- Wide Guard
- Protect

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 252 HP / 236 Def / 20 SpD
Bold Nature
IVs: 0 Atk / 26 Spe
- Sludge Bomb
- Spore
- Rage Powder
- Protect

Chi-Yu @ Choice Scarf
Ability: Beads of Ruin
Level: 50
Tera Type: Ghost
EVs: 124 HP / 4 Def / 124 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Heat Wave
- Overheat
- Dark Pulse
- Snarl

Flutter Mane @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Grass
EVs: 244 HP / 108 Def / 4 SpA / 4 SpD / 148 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Shadow Ball
- Icy Wind
- Protect

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Grass
EVs: 196 HP / 164 Def / 100 SpA / 4 SpD / 44 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Draco Meteor
- Thunderclap
- Electroweb
""",
        """
Blast (Chi-Yu) @ Choice Scarf
Ability: Beads of Ruin
Level: 50
Tera Type: Ghost
EVs: 132 HP / 4 Def / 116 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Heat Wave
- Dark Pulse
- Overheat
- Snarl

Beam (Amoonguss) @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 236 HP / 236 Def / 36 SpD
Bold Nature
IVs: 0 Atk / 27 Spe
- Sludge Bomb
- Spore
- Rage Powder
- Protect

Punch (Urshifu-Rapid-Strike) @ Safety Goggles
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 204 HP / 76 Atk / 4 Def / 36 SpD / 188 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Protect

Slam (Zamazenta-Crowned) @ Rusted Shield
Ability: Dauntless Shield
Level: 50
Tera Type: Dragon
EVs: 12 HP / 244 Def / 252 Spe
Impish Nature
- Body Press
- Heavy Slam
- Wide Guard
- Protect

Voice (Flutter Mane) @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Grass
EVs: 148 HP / 204 Def / 4 SpA / 4 SpD / 148 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Shadow Ball
- Icy Wind
- Protect

Pulse (Chien-Pao) @ Focus Sash
Ability: Sword of Ruin
Level: 50
Tera Type: Ghost
EVs: 4 HP / 156 Atk / 92 Def / 4 SpD / 252 Spe
Adamant Nature
- Ice Spinner
- Crunch
- Sucker Punch
- Protect
""",
        """
Calyrex-Shadow @ Life Orb
Ability: As One (Spectrier)
Level: 50
Tera Type: Normal
EVs: 188 HP / 36 Def / 12 SpA / 20 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Psychic
- Nasty Plot
- Protect

Ogerpon-Cornerstone (F) @ Cornerstone Mask
Ability: Sturdy
Level: 50
Tera Type: Rock
EVs: 28 HP / 172 Atk / 52 Def / 4 SpD / 252 Spe
Jolly Nature
- Ivy Cudgel
- Power Whip
- Follow Me
- Spiky Shield

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 188 HP / 4 Atk / 4 Def / 236 SpD / 76 Spe
Careful Nature
- Wood Hammer
- Grassy Glide
- Fake Out
- U-turn

Whimsicott @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Fire
EVs: 132 HP / 28 Def / 12 SpA / 116 SpD / 220 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Tailwind
- Encore
- Light Screen

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Detect

Incineroar @ Rocky Helmet
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 188 Def / 76 SpD
Impish Nature
IVs: 29 Spe
- Knock Off
- Will-O-Wisp
- Fake Out
- Parting Shot
""",
        """
Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 82
Tera Type: Dragon
EVs: 140 HP / 196 Atk / 4 Def / 20 SpD / 148 Spe
Adamant Nature
- Trick Room
- Imprison
- Glacial Lance
- High Horsepower

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Shiny: Yes
Tera Type: Water
EVs: 236 HP / 188 Def / 84 SpD
Relaxed Nature
IVs: 8 Spe
- Spore
- Pollen Puff
- Rage Powder
- Clear Smog

Landorus @ Choice Scarf
Ability: Sheer Force
Tera Type: Water
EVs: 52 HP / 4 Def / 196 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 12 Atk
- Earth Power
- Sandsear Storm
- Sludge Bomb
- U-turn

Indeedee-F @ Safety Goggles
Ability: Psychic Surge
Level: 50
Tera Type: Fairy
EVs: 252 HP / 252 Def / 4 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Follow Me
- Trick Room
- Alluring Voice
- Helping Hand

Regieleki @ Focus Sash
Ability: Transistor
Level: 70
Tera Type: Electric
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
- Protect
- Electroweb
- Volt Switch
- Thunderbolt

Urshifu @ Choice Band
Ability: Unseen Fist
Level: 50
Tera Type: Poison
EVs: 124 HP / 236 Atk / 148 SpD
Brave Nature
IVs: 29 Spe
- Wicked Blow
- U-turn
- Close Combat
- Poison Jab
""",
        """
Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 252 HP / 188 Def / 68 SpD
Bold Nature
IVs: 0 Atk
- Sludge Bomb
- Protect
- Rage Powder
- Spore

Flutter Mane @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Grass
EVs: 220 HP / 132 Def / 12 SpA / 4 SpD / 140 Spe
Timid Nature
IVs: 0 Atk
- Icy Wind
- Taunt
- Moonblast
- Thunder Wave

Zamazenta-Crowned @ Rusted Shield
Ability: Dauntless Shield
Level: 50
Tera Type: Dragon
EVs: 4 HP / 4 Atk / 244 Def / 4 SpD / 252 Spe
Impish Nature
- Protect
- Behemoth Bash
- Wide Guard
- Body Press

Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Sucker Punch
- Throat Chop
- Protect
- Ice Spinner

Entei @ Choice Band
Ability: Inner Focus
Level: 50
Tera Type: Normal
EVs: 12 HP / 244 Atk / 4 Def / 4 SpD / 244 Spe
Adamant Nature
- Stone Edge
- Sacred Fire
- Extreme Speed
- Flare Blitz

Urshifu @ Safety Goggles
Ability: Unseen Fist
Level: 50
Tera Type: Poison
EVs: 108 HP / 156 Atk / 4 Def / 60 SpD / 180 Spe
Adamant Nature
- Wicked Blow
- Close Combat
- Taunt
- Detect
""",
        """
Dondozo @ Leftovers
Ability: Unaware
Level: 50
Tera Type: Poison
EVs: 244 HP / 52 Def / 212 SpD
Impish Nature
- Wave Crash
- Yawn
- Fissure
- Protect

Ting-Lu @ Rocky Helmet
Ability: Vessel of Ruin
Level: 50
Tera Type: Fairy
EVs: 212 HP / 116 Def / 180 SpD
Impish Nature
- Sand Tomb
- Ruination
- Taunt
- Protect

Zamazenta-Crowned @ Rusted Shield
Ability: Dauntless Shield
Level: 50
Tera Type: Dragon
EVs: 4 HP / 4 Atk / 244 Def / 4 SpD / 252 Spe
Impish Nature
- Body Press
- Heavy Slam
- Wide Guard
- Protect

Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Ice Spinner
- Sucker Punch
- Throat Chop
- Protect

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 148 HP / 68 Def / 180 SpA / 28 SpD / 84 Spe
Modest Nature
IVs: 20 Atk
- Thunderclap
- Snarl
- Draco Meteor
- Electroweb

Ogerpon-Hearthflame @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 228 HP / 36 Atk / 52 Def / 4 SpD / 188 Spe
Adamant Nature
- Ivy Cudgel
- Wood Hammer
- Follow Me
- Spiky Shield
""",
        """
Miraidon @ Electric Seed
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 252 HP / 124 Def / 116 SpA / 4 SpD / 12 Spe
Modest Nature
- Parabolic Charge
- Dragon Pulse
- Calm Mind
- Protect

Incineroar @ Sitrus Berry
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 252 HP / 4 Atk / 244 Def / 4 SpD / 4 Spe
Impish Nature
- Fake Out
- Will-O-Wisp
- Knock Off
- Parting Shot

Thundurus @ Safety Goggles
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 252 HP / 84 Def / 172 SpD
Calm Nature
IVs: 0 Atk
- Eerie Impulse
- Thunder Wave
- Electric Terrain
- Sludge Bomb

Ogerpon-Cornerstone (F) @ Cornerstone Mask
Ability: Sturdy
Level: 50
Tera Type: Rock
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Ivy Cudgel
- Power Whip
- Follow Me
- Spiky Shield

Oranguru @ Covert Cloak
Ability: Symbiosis
Level: 50
Tera Type: Ground
EVs: 220 HP / 36 SpD / 252 Spe
Timid Nature
- Instruct
- Scary Face
- Bulldoze
- Taunt

Tinkaton @ Assault Vest
Ability: Mold Breaker
Level: 50
Tera Type: Water
EVs: 236 HP / 100 Atk / 52 Def / 44 SpD / 76 Spe
Careful Nature
- Fake Out
- Gigaton Hammer
- Play Rough
- Feint
""",
        """
Trixie (Whimsicott) @ Covert Cloak
Ability: Prankster
Level: 50
Shiny: Yes
Tera Type: Dark
EVs: 252 HP / 4 Def / 4 SpA / 172 SpD / 76 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Tailwind
- Encore
- Cotton Spore

Fig (Farigiraf) @ Rocky Helmet
Ability: Armor Tail
Level: 50
Shiny: Yes
Tera Type: Water
EVs: 180 HP / 156 Def / 4 SpA / 132 SpD / 36 Spe
Bold Nature
IVs: 0 Atk
- Psychic Noise
- Foul Play
- Helping Hand
- Trick Room

Wan (Chi-Yu) @ Choice Scarf
Ability: Beads of Ruin
Level: 50
Tera Type: Ground
EVs: 4 HP / 4 Def / 244 SpA / 4 SpD / 252 Spe
Modest Nature
- Heat Wave
- Dark Pulse
- Tera Blast
- Overheat

Scrapper the Great (Iron Hands) @ Assault Vest
Ability: Quark Drive
Level: 50
Shiny: Yes
Tera Type: Fire
EVs: 20 HP / 252 Atk / 12 Def / 4 SpA / 220 SpD
Brave Nature
IVs: 0 Spe
- Drain Punch
- Wild Charge
- Low Kick
- Fake Out

Shamone Rider (Calyrex-Shadow) @ Life Orb
Ability: As One (Spectrier)
Level: 50
Tera Type: Water
EVs: 252 HP / 36 Def / 44 SpA / 4 SpD / 172 Spe
Modest Nature
- Astral Barrage
- Psyshock
- Tera Blast
- Protect

Wicked Shades (Urshifu) @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Wicked Blow
- Close Combat
- Sucker Punch
- Detect
""",
        ### SAN ANTONIO REGIONALS JANUARY 2025 (7 teams) ###
        """
Calyrex-Shadow @ Life Orb
Ability: As One (Spectrier)
Level: 50
Tera Type: Dark
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Substitute
- Psychic
- Protect

Ting-Lu @ Rocky Helmet
Ability: Vessel of Ruin
Level: 50
Tera Type: Fairy
EVs: 228 HP / 4 Atk / 36 Def / 236 SpD / 4 Spe
Impish Nature
- Stealth Rock
- Sand Tomb
- Protect
- Ruination

Dondozo @ Leftovers
Ability: Oblivious
Level: 50
Tera Type: Dragon
EVs: 244 HP / 12 Atk / 252 SpD
Relaxed Nature
IVs: 27 Spe
- Yawn
- Wave Crash
- Fissure
- Protect

Urshifu @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Dark
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Detect
- Wicked Blow
- Close Combat
- Sucker Punch

Ogerpon-Hearthflame (F) @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 252 HP / 20 Atk / 76 Def / 4 SpD / 156 Spe
Adamant Nature
- Horn Leech
- Ivy Cudgel
- Follow Me
- Spiky Shield

Whimsicott @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Normal
EVs: 148 HP / 4 Def / 4 SpA / 132 SpD / 220 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Helping Hand
- Encore
- Tailwind
""",
        """
Koraidon @ Loaded Dice
Ability: Orichalcum Pulse
Level: 50
Tera Type: Fire
EVs: 116 HP / 196 Atk / 196 Spe
Adamant Nature
- Collision Course
- Flare Blitz
- Scale Shot
- Protect

Flutter Mane @ Focus Sash
Ability: Protosynthesis
Level: 50
Shiny: Yes
Tera Type: Fairy
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Dazzling Gleam
- Icy Wind
- Protect

Entei @ Choice Band
Ability: Inner Focus
Level: 50
Shiny: Yes
Tera Type: Normal
EVs: 4 HP / 196 Atk / 4 Def / 68 SpD / 236 Spe
Adamant Nature
- Sacred Fire
- Extreme Speed
- Stomping Tantrum
- Stone Edge

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 188 HP / 4 Def / 180 SpA / 4 SpD / 132 Spe
Modest Nature
IVs: 20 Atk
- Thunderclap
- Thunderbolt
- Draco Meteor
- Volt Switch

Umbreon @ Safety Goggles
Ability: Inner Focus
Level: 50
Shiny: Yes
Tera Type: Poison
EVs: 252 HP / 156 Def / 100 SpD
Bold Nature
IVs: 0 Atk
- Foul Play
- Taunt
- Yawn
- Moonlight

Ogerpon-Cornerstone @ Cornerstone Mask
Ability: Sturdy
Level: 50
Tera Type: Rock
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Ivy Cudgel
- Power Whip
- Follow Me
- Spiky Shield
""",
        """
Kyogre @ Choice Specs
Ability: Drizzle
Level: 50
Tera Type: Grass
EVs: 156 HP / 252 Def / 76 SpA / 4 SpD / 20 Spe
Modest Nature
IVs: 0 Atk
- Water Spout
- Origin Pulse
- Hydro Pump
- Ice Beam

Tornadus (M) @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Flying
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Bleakwind Storm
- Hurricane
- Tailwind
- Rain Dance

Kingambit @ Safety Goggles
Ability: Defiant
Level: 50
Tera Type: Dark
EVs: 252 HP / 252 Atk / 4 SpD
Brave Nature
IVs: 0 Spe
- Kowtow Cleave
- Iron Head
- Sucker Punch
- Protect

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Protect

Indeedee-F @ Psychic Seed
Ability: Psychic Surge
Level: 50
Tera Type: Fairy
EVs: 252 HP / 252 Def / 4 SpD
Bold Nature
IVs: 0 Atk
- Dazzling Gleam
- Follow Me
- Helping Hand
- Trick Room

Landorus @ Choice Scarf
Ability: Sand Force
Level: 50
Tera Type: Ground
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
- Sandsear Storm
- Earth Power
- Sludge Bomb
- U-turn
""",
        """
斷崖老師 (Groudon) @ Assault Vest
Ability: Drought
Shiny: Yes
Tera Type: Fire
EVs: 188 HP / 76 Atk / 12 Def / 84 SpD / 148 Spe
Adamant Nature
- Precipice Blades
- Heat Crash
- Thunder Punch
- High Horsepower

紧急授课 (Gouging Fire) @ Clear Amulet
Ability: Protosynthesis
Tera Type: Fairy
EVs: 164 HP / 84 Atk / 4 Def / 4 SpD / 252 Spe
Jolly Nature
- Flare Blitz
- Howl
- Protect
- Breaking Swipe

朝谒 (Raging Bolt) @ Life Orb
Ability: Protosynthesis
Tera Type: Electric
EVs: 68 HP / 124 Def / 212 SpA / 44 SpD / 60 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Thunderclap
- Draco Meteor
- Protect

圣城 (Volcarona) @ Rocky Helmet
Ability: Flame Body
Shiny: Yes
Tera Type: Water
EVs: 252 HP / 212 Def / 44 SpD
Bold Nature
IVs: 9 Atk
- Heat Wave
- Rage Powder
- Will-O-Wisp
- Tailwind

授法 (Chien-Pao) @ Focus Sash
Ability: Sword of Ruin
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Icicle Crash
- Sucker Punch
- Sacred Sword
- Protect

梅柳齐娜 (Iron Valiant) @ Booster Energy
Ability: Quark Drive
Shiny: Yes
Tera Type: Ghost
EVs: 140 HP / 4 Atk / 100 Def / 60 SpD / 204 Spe
Jolly Nature
- Spirit Break
- Wide Guard
- Coaching
- Encore
""",
        """
Koraidon @ Clear Amulet
Ability: Orichalcum Pulse
Level: 50
Tera Type: Fire
EVs: 84 HP / 252 Atk / 4 Def / 4 SpD / 164 Spe
Jolly Nature
- Collision Course
- Flare Blitz
- Flame Charge
- Protect

Venusaur @ Focus Sash
Ability: Chlorophyll
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Grass Knot
- Sludge Bomb
- Sleep Powder
- Protect

Indeedee-F @ Psychic Seed
Ability: Psychic Surge
Level: 50
Tera Type: Water
EVs: 252 HP / 252 Def / 4 SpD
Bold Nature
IVs: 0 Atk / 29 Spe
- Psychic
- Follow Me
- Helping Hand
- Trick Room

Chi-Yu @ Choice Scarf
Ability: Beads of Ruin
Level: 50
Tera Type: Fire
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 0 Atk
- Heat Wave
- Dark Pulse
- Flamethrower
- Snarl

Raging Bolt @ Life Orb
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 20 Atk
- Draco Meteor
- Thunderbolt
- Thunderclap
- Protect

Iron Crown @ Booster Energy
Ability: Quark Drive
Level: 50
Tera Type: Ground
EVs: 164 HP / 4 Def / 252 SpA / 4 SpD / 84 Spe
Modest Nature
- Tachyon Cutter
- Expanding Force
- Tera Blast
- Protect
""",
        """
Frosmoth @ Safety Goggles
Ability: Ice Scales
Level: 50
Tera Type: Dragon
EVs: 212 HP / 252 Def / 36 SpA / 4 SpD / 4 Spe
Modest Nature
- Ice Beam
- Bug Buzz
- Wide Guard
- Protect

Urshifu @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
IVs: 22 SpA
- Wicked Blow
- Close Combat
- Sucker Punch
- Detect

Landorus @ Life Orb
Ability: Sheer Force
Level: 50
Tera Type: Steel
EVs: 12 HP / 4 Def / 204 SpA / 36 SpD / 252 Spe
Timid Nature
- Earth Power
- Sludge Bomb
- Sandsear Storm
- Protect

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 108 HP / 180 Def / 180 SpA / 4 SpD / 36 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Thunderclap
- Electroweb
- Draco Meteor

Ogerpon-Hearthflame @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 188 HP / 76 Atk / 76 Def / 4 SpD / 164 Spe
Adamant Nature
IVs: 20 SpA
- Ivy Cudgel
- Wood Hammer
- Follow Me
- Spiky Shield

Necrozma-Dusk-Mane @ Clear Amulet
Ability: Prism Armor
Level: 50
Tera Type: Normal
EVs: 252 HP / 20 Atk / 60 Def / 148 SpD / 28 Spe
Adamant Nature
- Sunsteel Strike
- Photon Geyser
- Trick Room
- Protect
""",
        """
Bastiodon (M) @ Covert Cloak
Ability: Sturdy
Level: 50
Tera Type: Grass
EVs: 252 HP / 76 Def / 180 SpD
Sassy Nature
IVs: 0 Atk / 2 Spe
- Body Press
- Iron Defense
- Foul Play
- Wide Guard

Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 108 HP / 4 Def / 228 SpA / 4 SpD / 164 Spe
Timid Nature
- Electro Drift
- Dazzling Gleam
- Volt Switch
- Draco Meteor

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 50
Tera Type: Water
EVs: 84 HP / 172 Atk / 12 Def / 172 SpD / 68 Spe
Adamant Nature
- Drain Punch
- Heavy Slam
- Fake Out
- Low Kick

Ogerpon-Hearthflame @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 188 HP / 76 Atk / 52 Def / 4 SpD / 188 Spe
Adamant Nature
- Ivy Cudgel
- Wood Hammer
- Spiky Shield
- Follow Me

Grimmsnarl @ Light Clay
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 244 HP / 4 Atk / 132 Def / 116 SpD / 12 Spe
Impish Nature
- Reflect
- Light Screen
- Spirit Break
- Thunder Wave

Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Icicle Crash
- Throat Chop
- Sucker Punch
- Protect
""",
        ### BIRMINGHAM REGIONALS JANUARY 2025 (3 teams) ###
        """
Shamone Rider (Calyrex-Shadow) @ Spooky Plate
Ability: As One (Spectrier)
Level: 50
Tera Type: Water
EVs: 252 HP / 36 Def / 44 SpA / 4 SpD / 172 Spe
Modest Nature
IVs: 3 Atk
- Astral Barrage
- Tera Blast
- Nasty Plot
- Protect

Larry (Whimsicott) @ Covert Cloak
Ability: Prankster
Level: 50
Shiny: Yes
Tera Type: Dark
EVs: 252 HP / 4 Def / 4 SpA / 172 SpD / 76 Spe
Timid Nature
IVs: 30 Atk
- Moonblast
- Tailwind
- Encore
- Cotton Spore

Wicked Shades (Urshifu) @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
IVs: 2 SpA
- Wicked Blow
- Close Combat
- Sucker Punch
- Detect

Fisto (Iron Hands) @ Assault Vest
Ability: Quark Drive
Level: 50
Shiny: Yes
Tera Type: Fire
EVs: 20 HP / 236 Atk / 12 Def / 188 SpD / 52 Spe
Adamant Nature
- Low Kick
- Wild Charge
- Drain Punch
- Fake Out

Piepi (Clefairy) (F) @ Eviolite
Ability: Friend Guard
Level: 50
Shiny: Yes
Tera Type: Dragon
EVs: 252 HP / 252 Def / 4 SpD
Relaxed Nature
IVs: 0 Atk / 2 SpA / 0 Spe
- Helping Hand
- Follow Me
- After You
- Protect

Elizabeth (Ogerpon-Hearthflame) @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 124 HP / 76 Atk / 92 Def / 4 SpD / 212 Spe
Adamant Nature
- Ivy Cudgel
- Wood Hammer
- Follow Me
- Spiky Shield
""",
        """
Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 4 Atk / 188 Def / 44 SpD / 28 Spe
Impish Nature
- Fake Out
- Knock Off
- Will-O-Wisp
- Parting Shot

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 244 HP / 36 Atk / 4 Def / 124 SpD / 100 Spe
Adamant Nature
- Fake Out
- Wood Hammer
- Grassy Glide
- U-turn

Urshifu-Rapid-Strike @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Ghost
EVs: 4 HP / 156 Atk / 4 Def / 92 SpD / 252 Spe
Adamant Nature
- Close Combat
- Surging Strikes
- Aqua Jet
- U-turn

Kyogre @ Leftovers
Ability: Drizzle
Level: 50
Tera Type: Grass
EVs: 132 HP / 140 Def / 76 SpA / 12 SpD / 148 Spe
Modest Nature
IVs: 6 Atk
- Ice Beam
- Protect
- Origin Pulse
- Calm Mind

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Fairy
EVs: 236 HP / 236 Def / 36 SpD
Bold Nature
IVs: 0 Atk / 26 Spe
- Spore
- Protect
- Sludge Bomb
- Rage Powder

Roaring Moon @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Flying
EVs: 28 HP / 220 Atk / 4 Def / 4 SpD / 252 Spe
Jolly Nature
- Knock Off
- Protect
- Acrobatics
- Tailwind
""",
        """
Raging Bolt @ Life Orb
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 52 HP / 4 Def / 252 SpA / 4 SpD / 196 Spe
Modest Nature
IVs: 20 Atk
- Protect
- Thunderclap
- Draco Meteor
- Thunderbolt

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Fire
EVs: 244 HP / 188 Def / 76 SpD
Sassy Nature
IVs: 0 Atk / 0 Spe
- Protect
- Rage Powder
- Spore
- Sludge Bomb

Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Protect
- Ice Spinner
- Sucker Punch
- Throat Chop

Zamazenta-Crowned @ Rusted Shield
Ability: Dauntless Shield
Level: 50
Tera Type: Fairy
EVs: 92 HP / 4 Atk / 156 Def / 12 SpD / 244 Spe
Impish Nature
- Protect
- Wide Guard
- Body Press
- Heavy Slam

Flutter Mane @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Grass
EVs: 204 HP / 132 Def / 28 SpA / 4 SpD / 140 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Shadow Ball
- Icy Wind
- Taunt

Chi-Yu @ Choice Scarf
Ability: Beads of Ruin
Level: 50
Tera Type: Ghost
EVs: 100 HP / 252 SpA / 156 Spe
Timid Nature
IVs: 0 Atk
- Overheat
- Dark Pulse
- Heat Wave
- Snarl
""",
        ### RIO DE JANEIRO REGIONALS JANUARY 2025 (1 team) ###
        """
Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 252 HP / 4 Def / 196 SpA / 44 SpD / 12 Spe
Modest Nature
- Electro Drift
- Volt Switch
- Dazzling Gleam
- Draco Meteor

Farigiraf @ Electric Seed
Ability: Armor Tail
Level: 50
Tera Type: Water
EVs: 236 HP / 164 Def / 108 SpD
Bold Nature
IVs: 6 Atk
- Psychic Noise
- Foul Play
- Helping Hand
- Trick Room

Whimsicott @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 252 HP / 60 Def / 196 SpD
Calm Nature
IVs: 14 Atk
- Moonblast
- Encore
- Tailwind
- Light Screen

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 50
Tera Type: Bug
EVs: 76 HP / 180 Atk / 12 Def / 236 SpD
Brave Nature
IVs: 6 SpA / 2 Spe
- Fake Out
- Drain Punch
- Wild Charge
- Low Kick

Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Icicle Crash
- Sucker Punch
- Sacred Sword
- Protect

Ogerpon-Cornerstone @ Cornerstone Mask
Ability: Sturdy
Level: 50
Tera Type: Rock
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
IVs: 20 SpA
- Ivy Cudgel
- Power Whip
- Spiky Shield
- Follow Me
""",
        ### WORLDS HONOLULU AUGUST 2024 (25 teams) ###
        """
Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 44 HP / 4 Def / 244 SpA / 12 SpD / 204 Spe
Modest Nature
- Electro Drift
- Draco Meteor
- Volt Switch
- Dazzling Gleam

Whimsicott @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 236 HP / 164 SpD / 108 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Tailwind
- Light Screen
- Encore

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Protect

Ogerpon-Hearthflame (F) @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 188 HP / 76 Atk / 52 Def / 4 SpD / 188 Spe
Adamant Nature
- Ivy Cudgel
- Wood Hammer
- Follow Me
- Spiky Shield

Farigiraf @ Electric Seed
Ability: Armor Tail
Level: 50
Tera Type: Water
EVs: 204 HP / 164 Def / 4 SpA / 108 SpD / 28 Spe
Bold Nature
IVs: 6 Atk
- Foul Play
- Psychic Noise
- Trick Room
- Helping Hand

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 50
Tera Type: Bug
EVs: 76 HP / 180 Atk / 12 Def / 236 SpD
Brave Nature
IVs: 0 Spe
- Drain Punch
- Low Kick
- Wild Charge
- Fake Out
""",
        """
Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Grass
EVs: 252 HP / 172 Atk / 84 SpD
Brave Nature
IVs: 1 Spe
- Glacial Lance
- High Horsepower
- Protect
- Trick Room

Urshifu-Rapid-Strike (M) @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Detect

Pelipper @ Life Orb
Ability: Drizzle
Level: 50
Tera Type: Grass
EVs: 252 HP / 252 SpA / 4 SpD
Modest Nature
IVs: 0 Atk
- Weather Ball
- Hurricane
- Helping Hand
- Wide Guard

Amoonguss (M) @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Fire
EVs: 236 HP / 228 Def / 44 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Spore
- Rage Powder
- Clear Smog
- Pollen Puff

Iron Valiant @ Booster Energy
Ability: Quark Drive
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 204 HP / 4 Atk / 100 Def / 28 SpD / 172 Spe
Jolly Nature
- Spirit Break
- Coaching
- Wide Guard
- Encore

Landorus @ Choice Scarf
Ability: Sheer Force
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
- Earth Power
- Sandsear Storm
- Sludge Bomb
- U-turn
""",
        """
Zamazenta-Crowned @ Rusted Shield
Ability: Dauntless Shield
Level: 50
Tera Type: Dragon
EVs: 92 HP / 4 Atk / 156 Def / 4 SpD / 252 Spe
Impish Nature
- Body Press
- Heavy Slam
- Wide Guard
- Protect

Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Icicle Crash
- Throat Chop
- Sucker Punch
- Protect

Entei @ Choice Band
Ability: Inner Focus
Level: 50
Tera Type: Normal
EVs: 12 HP / 244 Atk / 252 Spe
Adamant Nature
- Sacred Fire
- Extreme Speed
- Stone Edge
- Flare Blitz

Urshifu-Rapid-Strike @ Safety Goggles
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 92 HP / 156 Atk / 4 Def / 4 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Aqua Jet
- Substitute
- Protect

Flutter Mane @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Grass
EVs: 196 HP / 140 Def / 28 SpA / 4 SpD / 140 Spe
Timid Nature
- Moonblast
- Shadow Ball
- Icy Wind
- Protect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 188 HP / 196 Atk / 4 Def / 60 SpD / 60 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- U-turn
- Fake Out
""",
        """
Whimsicott @ Covert Cloak
Ability: Prankster
Level: 50
Shiny: Yes
Tera Type: Water
EVs: 236 HP / 4 Def / 4 SpA / 236 SpD / 28 Spe
Timid Nature
IVs: 0 Atk
- Tailwind
- Moonblast
- Encore
- Light Screen

Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 44 HP / 4 Def / 252 SpA / 4 SpD / 204 Spe
Modest Nature
- Electro Drift
- Draco Meteor
- Dazzling Gleam
- Volt Switch

Farigiraf @ Electric Seed
Ability: Armor Tail
Level: 50
Shiny: Yes
Tera Type: Water
EVs: 228 HP / 196 Def / 84 SpD
Bold Nature
IVs: 0 Atk
- Trick Room
- Psychic
- Foul Play
- Helping Hand

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 50
Shiny: Yes
Tera Type: Grass
EVs: 76 HP / 244 Atk / 108 Def / 76 SpD
Adamant Nature
IVs: 29 Spe
- Fake Out
- Drain Punch
- Low Kick
- Heavy Slam

Ogerpon-Hearthflame @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 252 HP / 100 Atk / 52 Def / 44 SpD / 60 Spe
Adamant Nature
- Ivy Cudgel
- Horn Leech
- Follow Me
- Spiky Shield

Urshifu @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Dark
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Wicked Blow
- Close Combat
- Sucker Punch
- Protect
""",
        """
Farigiraf @ Safety Goggles
Ability: Armor Tail
Level: 50
Tera Type: Steel
EVs: 116 HP / 156 Def / 156 SpA / 76 SpD / 4 Spe
Modest Nature
IVs: 0 Atk
- Foul Play
- Helping Hand
- Trick Room
- Psychic

Regieleki @ Focus Sash
Ability: Transistor
Level: 50
Tera Type: Electric
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 0 Atk
- Protect
- Electroweb
- Thunderbolt
- Volt Switch

Landorus @ Life Orb
Ability: Sheer Force
Level: 50
Tera Type: Poison
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Sludge Bomb
- Earth Power
- Sandsear Storm

Ogerpon-Cornerstone (F) @ Cornerstone Mask
Ability: Sturdy
Level: 50
Tera Type: Rock
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Ivy Cudgel
- Follow Me
- Power Whip
- Spiky Shield

Urshifu-Rapid-Strike @ Mystic Water
Ability: Unseen Fist
Level: 50
Tera Type: Normal
EVs: 44 HP / 156 Atk / 4 Def / 116 SpD / 188 Spe
Adamant Nature
- Detect
- Close Combat
- Surging Strikes
- Aqua Jet

Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Water
EVs: 204 HP / 116 Atk / 4 Def / 44 SpD / 140 Spe
Adamant Nature
- Trick Room
- Glacial Lance
- Protect
- High Horsepower
""",
        """
Terapagos @ Leftovers
Ability: Tera Shift
Level: 50
Tera Type: Stellar
EVs: 172 HP / 4 Def / 204 SpA / 12 SpD / 116 Spe
Modest Nature
IVs: 15 Atk
- Tera Starstorm
- Calm Mind
- Substitute
- Protect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Grass
EVs: 252 HP / 132 Atk / 20 Def / 28 SpD / 76 Spe
Adamant Nature
- Fake Out
- Wood Hammer
- Grassy Glide
- U-turn

Incineroar @ Rocky Helmet
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 4 Atk / 156 Def / 84 SpD / 20 Spe
Impish Nature
- Fake Out
- Knock Off
- Parting Shot
- Will-O-Wisp

Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Icicle Crash
- Sucker Punch
- Sacred Sword
- Protect

Urshifu-Rapid-Strike @ Splash Plate
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 20 HP / 140 Atk / 52 Def / 44 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Detect

Flutter Mane @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 212 HP / 132 Def / 4 SpA / 4 SpD / 156 Spe
Timid Nature
IVs: 28 Atk
- Moonblast
- Icy Wind
- Thunder Wave
- Protect
""",
        """
Zamazenta-Crowned @ Rusted Shield
Ability: Dauntless Shield
Level: 70
Tera Type: Dragon
EVs: 68 HP / 244 Def / 196 Spe
Impish Nature
- Body Press
- Heavy Slam
- Wide Guard
- Protect

Flutter Mane @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Grass
EVs: 220 HP / 132 Def / 12 SpA / 20 SpD / 124 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Shadow Ball
- Thunder Wave
- Protect

Rillaboom @ Miracle Seed
Ability: Grassy Surge
Level: 65
Tera Type: Grass
EVs: 60 HP / 252 Atk / 196 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- Fake Out
- Protect

Latios @ Soul Dew
Ability: Levitate
Level: 71
Tera Type: Steel
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 10 Atk
- Luster Purge
- Draco Meteor
- Tailwind
- Protect

Tyranitar @ Focus Sash
Ability: Sand Stream
Tera Type: Ghost
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Rock Slide
- Knock Off
- Taunt
- Protect

Landorus @ Life Orb
Ability: Sheer Force
Tera Type: Poison
EVs: 116 HP / 12 Def / 116 SpA / 12 SpD / 252 Spe
Modest Nature
- Earth Power
- Sludge Bomb
- Substitute
- Protect
""",
        """
Calyrex-Shadow @ Covert Cloak
Ability: As One (Spectrier)
Level: 50
Tera Type: Water
EVs: 140 HP / 4 Def / 100 SpA / 12 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Astral Barrage
- Nasty Plot
- Psyshock

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 252 HP / 180 Def / 76 SpD
Sassy Nature
IVs: 0 Spe
- Knock Off
- Parting Shot
- Helping Hand
- Fake Out

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Detect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 244 HP / 36 Atk / 4 Def / 220 SpD / 4 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- U-turn
- Fake Out

Farigiraf @ Throat Spray
Ability: Armor Tail
Level: 50
Tera Type: Grass
EVs: 228 HP / 12 Def / 156 SpA / 108 SpD
Modest Nature
IVs: 0 Atk
- Protect
- Psychic
- Hyper Voice
- Trick Room

Raging Bolt @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 196 HP / 108 Def / 196 SpA / 4 SpD / 4 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Dragon Pulse
- Thunderclap
- Protect
""",
        """
Calyrex-Ice @ Never-Melt Ice
Ability: As One (Glastrier)
Level: 50
Tera Type: Poison
EVs: 252 HP / 4 Atk / 108 Def / 140 SpD
Brave Nature
IVs: 0 Spe
- Protect
- Glacial Lance
- High Horsepower
- Trick Room

Raging Bolt @ Life Orb
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 228 HP / 28 Def / 252 SpA
Modest Nature
IVs: 20 Atk
- Protect
- Draco Meteor
- Thunderbolt
- Thunderclap

Flutter Mane @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Normal
EVs: 252 HP / 196 Def / 60 SpA
Timid Nature
IVs: 0 Atk
- Protect
- Dazzling Gleam
- Icy Wind
- Moonblast

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Detect
- Aqua Jet

Chi-Yu @ Covert Cloak
Ability: Beads of Ruin
Level: 50
Tera Type: Grass
EVs: 116 HP / 4 Def / 140 SpA / 4 SpD / 244 Spe
Modest Nature
IVs: 0 Atk
- Protect
- Snarl
- Heat Wave
- Overheat

Ogerpon-Cornerstone @ Cornerstone Mask
Ability: Sturdy
Level: 50
Tera Type: Rock
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
IVs: 20 SpA
- Spiky Shield
- Follow Me
- Power Whip
- Ivy Cudgel
""",
        """
Calyrex-Shadow @ Spell Tag
Ability: As One (Spectrier)
Level: 50
Tera Type: Normal
EVs: 28 HP / 4 Def / 220 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Expanding Force
- Nasty Plot
- Protect

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Protect

Raging Bolt @ Life Orb
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Dragon Pulse
- Thunderclap
- Protect

Rillaboom (M) @ Assault Vest
Ability: Grassy Surge
Level: 50
Shiny: Yes
Tera Type: Fire
EVs: 252 HP / 148 Atk / 108 SpD
Adamant Nature
- Fake Out
- Grassy Glide
- Wood Hammer
- U-turn

Incineroar (M) @ Covert Cloak
Ability: Intimidate
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 252 HP / 124 Def / 132 SpD
Impish Nature
- Fake Out
- Knock Off
- Taunt
- Parting Shot

Amoonguss (M) @ Rocky Helmet
Ability: Regenerator
Level: 50
Shiny: Yes
Tera Type: Fairy
EVs: 252 HP / 156 Def / 100 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Spore
- Sludge Bomb
- Rage Powder
- Protect
""",
        """
Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Normal
EVs: 252 HP / 116 Atk / 4 Def / 132 SpD / 4 Spe
Adamant Nature
- Glacial Lance
- High Horsepower
- Protect
- Trick Room

Landorus @ Choice Scarf
Ability: Sheer Force
Level: 50
Tera Type: Ghost
EVs: 4 HP / 12 Def / 236 SpA / 4 SpD / 252 Spe
Modest Nature
- Earth Power
- U-turn
- Sandsear Storm
- Sludge Bomb

Incineroar @ Rocky Helmet
Ability: Intimidate
Level: 50
Tera Type: Grass
EVs: 252 HP / 4 Atk / 188 Def / 44 SpD / 20 Spe
Impish Nature
- Fake Out
- Parting Shot
- Will-O-Wisp
- Knock Off

Pelipper @ Safety Goggles
Ability: Drizzle
Level: 50
Tera Type: Grass
EVs: 252 HP / 44 Def / 36 SpA / 140 SpD / 36 Spe
Modest Nature
IVs: 0 Atk
- Hurricane
- Wide Guard
- Weather Ball
- Helping Hand

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Detect

Ogerpon (F) @ Loaded Dice
Ability: Defiant
Level: 50
Tera Type: Grass
EVs: 76 HP / 156 Atk / 44 Def / 20 SpD / 212 Spe
Adamant Nature
- Bullet Seed
- Encore
- Spiky Shield
- Follow Me
""",
        """
Calyrex-Shadow @ Life Orb
Ability: As One (Spectrier)
Level: 50
Tera Type: Dark
EVs: 108 HP / 180 Def / 44 SpA / 4 SpD / 172 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Psychic
- Nasty Plot
- Protect

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Protect

Incineroar @ Rocky Helmet
Ability: Intimidate
Level: 50
Tera Type: Water
EVs: 252 HP / 4 Atk / 132 Def / 76 SpD / 44 Spe
Careful Nature
- Parting Shot
- Knock Off
- Helping Hand
- Fake Out

Rillaboom @ Clear Amulet
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 172 HP / 52 Atk / 4 Def / 252 SpD / 28 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- U-turn
- Fake Out

Amoonguss @ Mental Herb
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 252 HP / 164 Def / 4 SpA / 76 SpD / 12 Spe
Calm Nature
IVs: 0 Atk
- Spore
- Sludge Bomb
- Rage Powder
- Protect

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 188 HP / 4 Def / 244 SpA / 4 SpD / 68 Spe
Modest Nature
IVs: 20 Atk
- Electroweb
- Volt Switch
- Thunderclap
- Draco Meteor
""",
        """
Kyogre @ Assault Vest
Ability: Drizzle
Level: 50
Tera Type: Grass
EVs: 44 HP / 68 Def / 236 SpA / 4 SpD / 156 Spe
Modest Nature
IVs: 0 Atk
- Water Spout
- Origin Pulse
- Ice Beam
- Thunder

Tornadus @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 252 HP / 4 Def / 36 SpA / 4 SpD / 212 Spe
Modest Nature
IVs: 0 Atk
- Bleakwind Storm
- Tailwind
- Rain Dance
- Taunt

Urshifu-Rapid-Strike @ Choice Band
Ability: Unseen Fist
Level: 50
Tera Type: Grass
EVs: 4 HP / 252 Atk / 4 Def / 44 SpD / 204 Spe
Jolly Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- U-turn

Basculegion @ Life Orb
Ability: Swift Swim
Level: 50
Tera Type: Grass
EVs: 28 HP / 252 Atk / 68 Def / 4 SpD / 156 Spe
Adamant Nature
- Wave Crash
- Last Respects
- Aqua Jet
- Protect

Tsareena @ Wide Lens
Ability: Queenly Majesty
Level: 50
Tera Type: Ice
EVs: 60 HP / 236 Atk / 4 Def / 4 SpD / 204 Spe
Jolly Nature
- Triple Axel
- Taunt
- Protect
- Power Whip

Landorus @ Choice Scarf
Ability: Sheer Force
Level: 50
Tera Type: Ghost
EVs: 4 HP / 12 Def / 236 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 3 Atk
- Earth Power
- Sandsear Storm
- Sludge Bomb
- Taunt
""",
        """
Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 100 HP / 4 Def / 148 SpA / 4 SpD / 252 Spe
Timid Nature
- Electro Drift
- Volt Switch
- Dazzling Gleam
- Draco Meteor

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Detect

Ogerpon-Hearthflame @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 236 HP / 60 Atk / 52 Def / 4 SpD / 156 Spe
Adamant Nature
IVs: 20 SpA
- Ivy Cudgel
- Wood Hammer
- Spiky Shield
- Taunt

Farigiraf @ Electric Seed
Ability: Armor Tail
Level: 50
Tera Type: Water
EVs: 252 HP / 164 Def / 92 SpD
Bold Nature
IVs: 0 Atk
- Foul Play
- Psychic Noise
- Trick Room
- Helping Hand

Whimsicott @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Fire
EVs: 124 HP / 4 Def / 4 SpA / 220 SpD / 156 Spe
Timid Nature
IVs: 24 Atk
- Encore
- Light Screen
- Moonblast
- Tailwind

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 50
Tera Type: Bug
EVs: 60 HP / 172 Atk / 12 Def / 172 SpD / 92 Spe
Adamant Nature
- Low Kick
- Drain Punch
- Fake Out
- Wild Charge
""",
        """
Calyrex-Shadow @ Covert Cloak
Ability: As One (Spectrier)
Level: 50
Tera Type: Fairy
EVs: 148 HP / 84 Def / 20 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Astral Barrage
- Draining Kiss
- Calm Mind

Mienshao @ Focus Sash
Ability: Inner Focus
Level: 50
Tera Type: Fighting
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Close Combat
- Taunt
- Wide Guard
- Fake Out

Clefairy @ Eviolite
Ability: Friend Guard
Level: 50
Tera Type: Grass
EVs: 252 HP / 212 Def / 44 SpD
Impish Nature
IVs: 10 SpA / 16 Spe
- Protect
- Follow Me
- Helping Hand
- Sing

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 252 HP / 36 Atk / 4 Def / 204 SpD / 12 Spe
Adamant Nature
- Wood Hammer
- U-turn
- Grassy Glide
- Fake Out

Urshifu-Rapid-Strike @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 28 HP / 252 Atk / 4 Def / 4 SpD / 220 Spe
Jolly Nature
- Surging Strikes
- Close Combat
- U-turn
- Rock Tomb

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Water
EVs: 252 HP / 4 Atk / 108 Def / 84 SpD / 60 Spe
Impish Nature
- Knock Off
- Will-O-Wisp
- Parting Shot
- Fake Out
""",
        """
Slowking @ Life Orb
Ability: Regenerator
Level: 50
Tera Type: Grass
EVs: 52 HP / 68 Def / 252 SpA / 132 SpD
Quiet Nature
IVs: 0 Atk / 0 Spe
- Expanding Force
- Scald
- Grass Knot
- Trick Room

Weezing-Galar @ Assault Vest
Ability: Neutralizing Gas
Level: 50
Tera Type: Normal
EVs: 68 HP / 252 Atk / 4 Def / 172 SpD / 12 Spe
Adamant Nature
- Play Rough
- Gunk Shot
- Assurance
- Explosion

Baxcalibur @ Loaded Dice
Ability: Thermal Exchange
Level: 50
Tera Type: Poison
EVs: 12 HP / 228 Atk / 4 Def / 12 SpD / 252 Spe
Jolly Nature
- Protect
- Swords Dance
- Scale Shot
- Icicle Spear

Kyogre @ Choice Scarf
Ability: Drizzle
Level: 50
Tera Type: Water
EVs: 4 HP / 4 Def / 244 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Water Spout
- Hydro Pump
- Thunder
- Origin Pulse

Indeedee-F @ Rocky Helmet
Ability: Psychic Surge
Level: 50
Tera Type: Grass
EVs: 188 HP / 212 Def / 108 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Trick Room
- Follow Me
- Helping Hand
- Dazzling Gleam

Smeargle @ Focus Sash
Ability: Moody
Level: 50
Tera Type: Ghost
EVs: 252 HP / 4 Def / 252 Spe
Jolly Nature
- Fake Out
- Follow Me
- Shed Tail
- Spore
""",
        """
Calyrex-Shadow @ Covert Cloak
Ability: As One (Spectrier)
Level: 50
Tera Type: Normal
EVs: 140 HP / 52 Def / 60 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 28 Atk
- Astral Barrage
- Expanding Force
- Nasty Plot
- Protect

Indeedee-F @ Psychic Seed
Ability: Psychic Surge
Level: 50
Tera Type: Fairy
EVs: 252 HP / 204 Def / 52 SpD
Bold Nature
IVs: 4 Atk
- Alluring Voice
- Trick Room
- Helping Hand
- Follow Me

Incineroar @ Rocky Helmet
Ability: Intimidate
Level: 50
Tera Type: Water
EVs: 252 HP / 4 Atk / 164 Def / 76 SpD / 12 Spe
Impish Nature
- Fake Out
- Parting Shot
- Flare Blitz
- Knock Off

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 140 HP / 172 Atk / 4 Def / 188 SpD / 4 Spe
Adamant Nature
- Fake Out
- Wood Hammer
- Grassy Glide
- U-turn

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Taunt
- Detect

Ogerpon-Wellspring @ Wellspring Mask
Ability: Water Absorb
Level: 50
Tera Type: Water
EVs: 252 HP / 76 SpD / 180 Spe
Jolly Nature
IVs: 20 SpA
- Ivy Cudgel
- Encore
- Follow Me
- Spiky Shield
""",
        """
Calyrex-Shadow @ Focus Sash
Ability: As One (Spectrier)
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 28 Atk
- Astral Barrage
- Psyshock
- Taunt
- Protect

Raging Bolt @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 188 HP / 140 Def / 100 SpA / 4 SpD / 76 Spe
Modest Nature
IVs: 20 Atk
- Thunderclap
- Draco Meteor
- Electroweb
- Protect

Ting-Lu @ Rocky Helmet
Ability: Vessel of Ruin
Level: 50
Tera Type: Fairy
EVs: 252 HP / 76 Def / 180 SpD
Impish Nature
- Ruination
- Sand Tomb
- Protect
- Stealth Rock

Ogerpon-Hearthflame @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 252 HP / 124 Atk / 52 Def / 4 SpD / 76 Spe
Adamant Nature
IVs: 20 SpA
- Ivy Cudgel
- Power Whip
- Follow Me
- Spiky Shield

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 252 HP / 116 Atk / 4 Def / 108 SpD / 28 Spe
Adamant Nature
IVs: 22 SpA
- Wood Hammer
- High Horsepower
- U-turn
- Fake Out

Dondozo @ Leftovers
Ability: Oblivious
Level: 50
Tera Type: Dragon
EVs: 244 HP / 68 Def / 196 SpD
Careful Nature
- Fissure
- Wave Crash
- Yawn
- Protect
""",
        """
Whimsicott @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Fire
EVs: 252 HP / 68 Def / 4 SpA / 148 SpD / 36 Spe
Timid Nature
IVs: 16 Atk
- Tailwind
- Encore
- Light Screen
- Moonblast

Urshifu @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Dark
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Wicked Blow
- Detect
- Close Combat
- Sucker Punch

Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
- Draco Meteor
- Volt Switch
- Electro Drift
- Dazzling Gleam

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 50
Tera Type: Poison
EVs: 116 HP / 244 Atk / 68 Def / 28 SpD / 52 Spe
Adamant Nature
IVs: 4 SpA
- Fake Out
- Drain Punch
- Wild Charge
- Heavy Slam

Landorus @ Life Orb
Ability: Sheer Force
Level: 50
Tera Type: Fire
EVs: 212 HP / 4 Def / 252 SpA / 4 SpD / 36 Spe
Modest Nature
- Earth Power
- Protect
- Sandsear Storm
- Sludge Bomb

Gholdengo @ Iron Plate
Ability: Good as Gold
Level: 50
Tera Type: Steel
EVs: 156 HP / 4 Def / 252 SpA / 4 SpD / 92 Spe
Modest Nature
IVs: 10 Atk
- Make It Rain
- Shadow Ball
- Protect
- Nasty Plot
""",
        """
Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Dragon
EVs: 252 HP / 164 Atk / 92 SpD
Brave Nature
IVs: 0 Spe
- Glacial Lance
- High Horsepower
- Trick Room
- Protect

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Detect

Torkoal @ Charcoal
Ability: Drought
Level: 50
Tera Type: Fire
EVs: 252 HP / 252 SpA / 4 SpD
Quiet Nature
IVs: 0 Atk / 0 Spe
- Eruption
- Heat Wave
- Helping Hand
- Protect

Ogerpon-Cornerstone @ Cornerstone Mask
Ability: Sturdy
Level: 50
Tera Type: Rock
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Ivy Cudgel
- Power Whip
- Follow Me
- Spiky Shield

Flutter Mane @ Life Orb
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 12 HP / 244 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Dazzling Gleam
- Shadow Ball
- Moonblast
- Protect

Farigiraf @ Rocky Helmet
Ability: Armor Tail
Level: 50
Tera Type: Dark
EVs: 244 HP / 172 Def / 92 SpD
Bold Nature
IVs: 0 Atk / 26 Spe
- Psychic
- Foul Play
- Helping Hand
- Trick Room
""",
        """
Koraidon @ Assault Vest
Ability: Orichalcum Pulse
Level: 50
Tera Type: Fire
EVs: 140 HP / 44 Atk / 4 Def / 252 SpD / 68 Spe
Jolly Nature
- Collision Course
- Dragon Claw
- Flare Blitz
- Flame Charge

Chi-Yu @ Choice Scarf
Ability: Beads of Ruin
Level: 50
Tera Type: Ghost
EVs: 132 HP / 4 Def / 116 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Heat Wave
- Overheat
- Dark Pulse
- Snarl

Flutter Mane @ Focus Sash
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Dazzling Gleam
- Icy Wind
- Protect

Raging Bolt @ Life Orb
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 20 Atk
- Thunderclap
- Draco Meteor
- Thunderbolt
- Protect

Glastrier @ Leftovers
Ability: Chilling Neigh
Level: 50
Tera Type: Water
EVs: 252 HP / 188 Def / 68 SpD
Relaxed Nature
IVs: 0 Spe
- Icicle Crash
- Body Press
- Iron Defense
- Protect

Rillaboom @ Miracle Seed
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 220 HP / 228 Def / 60 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- Taunt
- Fake Out
""",
        """
Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Grass
EVs: 252 HP / 196 Atk / 4 Def / 52 SpD / 4 Spe
Adamant Nature
- Glacial Lance
- High Horsepower
- Trick Room
- Protect

Urshifu-Rapid-Strike @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Coaching
- U-turn

Raging Bolt @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 244 HP / 20 Def / 164 SpA / 4 SpD / 76 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Thunderclap
- Draco Meteor
- Protect

Incineroar @ Rocky Helmet
Ability: Intimidate
Level: 50
Tera Type: Water
EVs: 252 HP / 4 Atk / 12 Def / 36 SpD / 204 Spe
Careful Nature
- Knock Off
- Parting Shot
- Taunt
- Fake Out

Amoonguss @ Covert Cloak
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 252 HP / 132 Def / 124 SpD
Sassy Nature
IVs: 0 Atk / 0 Spe
- Spore
- Rage Powder
- Pollen Puff
- Clear Smog

Pelipper @ Focus Sash
Ability: Drizzle
Level: 50
Tera Type: Ghost
EVs: 12 HP / 4 Def / 236 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Hurricane
- Weather Ball
- Wide Guard
- Helping Hand
""",
        """
Calyrex-Shadow @ Sitrus Berry
Ability: As One (Spectrier)
Level: 50
Tera Type: Fighting
EVs: 100 HP / 28 Def / 124 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Tera Blast
- Nasty Plot
- Protect

Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Icicle Crash
- Throat Chop
- Sucker Punch
- Protect

Urshifu-Rapid-Strike @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Ghost
EVs: 108 HP / 76 Atk / 4 Def / 68 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- U-turn
- Coaching

Ogerpon-Hearthflame @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 252 HP / 4 Atk / 52 Def / 4 SpD / 196 Spe
Jolly Nature
IVs: 20 SpA
- Ivy Cudgel
- Horn Leech
- Follow Me
- Spiky Shield

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 50
Tera Type: Grass
EVs: 76 HP / 132 Atk / 4 Def / 124 SpD / 172 Spe
Adamant Nature
- Drain Punch
- Wild Charge
- Volt Switch
- Fake Out

Clefairy @ Eviolite
Ability: Friend Guard
Level: 50
Tera Type: Grass
EVs: 252 HP / 172 Def / 84 SpD
Relaxed Nature
IVs: 0 Atk / 24 SpA / 0 Spe
- Follow Me
- Helping Hand
- After You
- Protect
""",
        """
Groudon @ Life Orb
Ability: Drought
Level: 50
Tera Type: Fire
EVs: 12 HP / 252 Atk / 4 Def / 4 SpD / 236 Spe
Adamant Nature
- Precipice Blades
- Heat Crash
- Substitute
- Protect

Flutter Mane @ Choice Specs
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 100 HP / 236 Def / 140 SpA / 4 SpD / 28 Spe
Timid Nature
IVs: 10 Atk
- Moonblast
- Hex
- Dazzling Gleam
- Icy Wind

Chi-Yu @ Choice Scarf
Ability: Beads of Ruin
Level: 50
Tera Type: Fire
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
- Heat Wave
- Dark Pulse
- Fire Blast
- Snarl

Indeedee-F @ Psychic Seed
Ability: Psychic Surge
Level: 50
Tera Type: Fire
EVs: 252 HP / 252 Def / 4 SpD
Bold Nature
IVs: 14 Atk
- Follow Me
- Trick Room
- Helping Hand
- Psychic

Sableye @ Focus Sash
Ability: Prankster
Level: 50
Tera Type: Normal
EVs: 12 HP / 244 Def / 252 Spe
Jolly Nature
- Foul Play
- Fake Out
- Gravity
- Skill Swap

Altaria @ Mental Herb
Ability: Cloud Nine
Level: 50
Tera Type: Water
EVs: 252 HP / 12 Def / 4 SpA / 116 SpD / 124 Spe
Calm Nature
IVs: 16 Atk
- Hurricane
- Sing
- Tailwind
- Roost
""",
        """
Terapagos @ Leftovers
Ability: Tera Shift
Level: 85
Tera Type: Stellar
EVs: 172 HP / 4 Def / 156 SpA / 4 SpD / 172 Spe
Modest Nature
IVs: 15 Atk
- Tera Starstorm
- Substitute
- Calm Mind
- Protect

Amoonguss @ Mental Herb
Ability: Regenerator
Level: 64
Tera Type: Water
EVs: 236 HP / 132 Def / 140 SpD
Calm Nature
IVs: 0 Atk
- Pollen Puff
- Spore
- Protect
- Rage Powder

Incineroar (M) @ Safety Goggles
Ability: Intimidate
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 244 HP / 4 Atk / 188 Def / 44 SpD / 28 Spe
Impish Nature
- Knock Off
- Will-O-Wisp
- Parting Shot
- Fake Out

Flutter Mane @ Booster Energy
Ability: Protosynthesis
Tera Type: Fairy
EVs: 108 HP / 204 Def / 52 SpA / 4 SpD / 140 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Taunt
- Thunder Wave
- Protect

Urshifu @ Focus Sash
Ability: Unseen Fist
Tera Type: Dark
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Wicked Blow
- Sucker Punch
- Close Combat
- Detect

Landorus @ Choice Scarf
Ability: Sheer Force
Level: 80
Tera Type: Fairy
EVs: 84 HP / 196 SpA / 228 Spe
Modest Nature
IVs: 0 Atk
- Sandsear Storm
- Earth Power
- Sludge Bomb
- Psychic
""",
        ### NAIC JUNE 2024 (10 teams) ###
        """
Incineroar (M) @ Safety Goggles
Ability: Intimidate
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 252 HP / 44 Atk / 68 Def / 108 SpD / 36 Spe
Adamant Nature
- Knock Off
- Will-O-Wisp
- Parting Shot
- Fake Out

Rillaboom (F) @ Assault Vest
Ability: Grassy Surge
Level: 50
Shiny: Yes
Tera Type: Normal
EVs: 236 HP / 148 Atk / 4 Def / 44 SpD / 76 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- U-turn
- Fake Out

Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Water
EVs: 252 HP / 132 Atk / 4 Def / 116 SpD / 4 Spe
Adamant Nature
- Protect
- Glacial Lance
- High Horsepower
- Trick Room

Urshifu-Rapid-Strike (M) @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 4 HP / 236 Atk / 4 Def / 12 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Coaching
- U-turn

Pelipper @ Focus Sash
Ability: Drizzle
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 12 HP / 4 Def / 236 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Protect
- Hurricane
- Weather Ball
- Wide Guard

Raging Bolt @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 188 HP / 4 Def / 252 SpA / 4 SpD / 60 Spe
Modest Nature
IVs: 20 Atk
- Protect
- Thunderbolt
- Draco Meteor
- Thunderclap
""",
        """
Kyogre @ Assault Vest
Ability: Drizzle
Level: 50
Tera Type: Grass
EVs: 252 HP / 132 Def / 92 SpA / 12 SpD / 20 Spe
Modest Nature
IVs: 0 Atk
- Water Spout
- Origin Pulse
- Thunder
- Ice Beam

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 4 Atk / 4 Def / 4 SpD / 252 Spe
Jolly Nature
- Fake Out
- Parting Shot
- Will-O-Wisp
- Knock Off

Wo-Chien @ Leftovers
Ability: Tablets of Ruin
Level: 50
Tera Type: Poison
EVs: 252 HP / 44 Def / 4 SpA / 20 SpD / 188 Spe
Bold Nature
IVs: 0 Atk
- Ruination
- Leech Seed
- Pollen Puff
- Protect

Grimmsnarl @ Light Clay
Ability: Prankster
Level: 50
Tera Type: Grass
EVs: 228 HP / 204 Def / 76 SpD
Careful Nature
- Reflect
- Light Screen
- Thunder Wave
- Spirit Break

Urshifu-Rapid-Strike @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- U-turn
- Aqua Jet

Iron Jugulis @ Booster Energy
Ability: Quark Drive
Level: 50
Tera Type: Water
EVs: 252 HP / 36 Def / 68 SpA / 36 SpD / 116 Spe
Timid Nature
IVs: 0 Atk
- Tailwind
- Hurricane
- Protect
- Snarl
""",
        """
Kyogre @ Mystic Water
Ability: Drizzle
Level: 50
Tera Type: Ghost
EVs: 244 HP / 156 SpA / 108 Spe
Modest Nature
IVs: 0 Atk
- Water Spout
- Hydro Pump
- Ice Beam
- Protect

Tornadus @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 212 HP / 164 Def / 116 SpA / 4 SpD / 12 Spe
Modest Nature
IVs: 0 Atk
- Bleakwind Storm
- Tailwind
- Rain Dance
- Taunt

Volcarona @ Safety Goggles
Ability: Flame Body
Level: 50
Tera Type: Water
EVs: 252 HP / 196 Def / 60 Spe
Timid Nature
IVs: 0 Atk
- Bug Buzz
- Protect
- Rage Powder
- Will-O-Wisp

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 220 HP / 36 Atk / 4 Def / 140 SpD / 108 Spe
Adamant Nature
- Grassy Glide
- U-turn
- Wood Hammer
- Fake Out

Overqwil @ Life Orb
Ability: Swift Swim
Level: 50
Tera Type: Poison
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Gunk Shot
- Crunch
- Acid Spray
- Protect

Landorus (M) @ Choice Scarf
Ability: Sheer Force
Level: 50
Tera Type: Ground
EVs: 252 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Sandsear Storm
- Earth Power
- Sludge Bomb
- Grass Knot
""",
        """
Maziodyne (Miraidon) @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Electric
EVs: 100 HP / 4 Def / 252 SpA / 4 SpD / 148 Spe
Timid Nature
- Volt Switch
- Electro Drift
- Draco Meteor
- Discharge

Bufudyne (Chien-Pao) @ Focus Sash
Ability: Sword of Ruin
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
IVs: 27 SpA
- Icicle Crash
- Sacred Sword
- Sucker Punch
- Protect

God's Hand (Iron Hands) @ Assault Vest
Ability: Quark Drive
Tera Type: Grass
EVs: 4 HP / 180 Atk / 44 Def / 236 SpD / 44 Spe
Adamant Nature
- Fake Out
- Close Combat
- Drain Punch
- Heavy Slam

Garudyne (Talonflame) @ Life Orb
Ability: Gale Wings
Tera Type: Ground
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
IVs: 1 SpA
- Brave Bird
- Tailwind
- Will-O-Wisp
- Protect

Megidolaon (Ursaluna-Bloodmoon) @ Silk Scarf
Ability: Mind's Eye
Tera Type: Normal
EVs: 196 HP / 4 Def / 252 SpA / 4 SpD / 52 Spe
Modest Nature
IVs: 4 Atk
- Hyper Voice
- Blood Moon
- Calm Mind
- Protect

Psiodyne (Farigiraf) @ Electric Seed
Ability: Armor Tail
Level: 56
Tera Type: Ground
EVs: 252 HP / 52 Def / 84 SpA / 116 SpD
Modest Nature
IVs: 3 Atk / 22 Spe
- Foul Play
- Twin Beam
- Trick Room
- Helping Hand
""",
        """
Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Fire
EVs: 212 HP / 252 Atk / 4 Def / 4 SpD / 36 Spe
Adamant Nature
- Glacial Lance
- Trick Room
- Protect
- Close Combat

Ursaluna-Bloodmoon @ Life Orb
Ability: Mind's Eye
Level: 50
Tera Type: Normal
EVs: 244 HP / 252 SpA / 12 Spe
Modest Nature
IVs: 0 Atk
- Hyper Voice
- Earth Power
- Blood Moon
- Protect

Smeargle (M) @ Focus Sash
Ability: Own Tempo
Level: 50
Tera Type: Grass
EVs: 252 HP / 252 Def / 4 SpD
Relaxed Nature
IVs: 0 Spe
- Fake Out
- Follow Me
- Decorate
- Spore

Farigiraf @ Mental Herb
Ability: Armor Tail
Level: 50
Tera Type: Ground
EVs: 132 HP / 236 Def / 140 SpD
Bold Nature
IVs: 0 Atk / 17 Spe
- Psychic Noise
- Trick Room
- Helping Hand
- Tera Blast

Annihilape @ Choice Scarf
Ability: Defiant
Level: 50
Tera Type: Grass
EVs: 252 HP / 4 Atk / 252 Spe
Jolly Nature
- Final Gambit
- Close Combat
- Shadow Claw
- Coaching

Electabuzz (M) @ Eviolite
Ability: Vital Spirit
Level: 50
Tera Type: Ghost
EVs: 252 HP / 180 Def / 76 SpD
Bold Nature
- Follow Me
- Taunt
- Feint
- Volt Switch
""",
        """
Ting-Lu @ Rocky Helmet
Ability: Vessel of Ruin
Level: 50
Tera Type: Water
EVs: 228 HP / 4 Atk / 36 Def / 236 SpD / 4 Spe
Impish Nature
IVs: 12 SpA
- Stealth Rock
- Taunt
- Throat Chop
- Ruination

Calyrex-Shadow @ Focus Sash
Ability: As One (Spectrier)
Level: 50
Tera Type: Ghost
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 4 Atk
- Astral Barrage
- Pollen Puff
- Psyshock
- Protect

Dondozo @ Leftovers
Ability: Oblivious
Level: 50
Tera Type: Dragon
EVs: 244 HP / 12 Atk / 252 SpD
Relaxed Nature
IVs: 20 Spe
- Yawn
- Wave Crash
- Body Press
- Protect

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 244 HP / 68 Def / 100 SpA / 20 SpD / 76 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Electroweb
- Thunderclap
- Dragon Pulse

Scream Tail @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Normal
EVs: 244 HP / 76 Atk / 12 Def / 108 SpD / 68 Spe
Jolly Nature
- Encore
- Disable
- Protect
- Play Rough

Ogerpon-Hearthflame @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 252 HP / 76 Atk / 76 Def / 4 SpD / 100 Spe
Adamant Nature
- Horn Leech
- Ivy Cudgel
- Follow Me
- Spiky Shield
""",
        """
hot wheels (Koraidon) @ Clear Amulet
Ability: Orichalcum Pulse
Level: 50
Tera Type: Fire
EVs: 204 HP / 68 Atk / 20 Def / 68 SpD / 148 Spe
Adamant Nature
- Collision Course
- Flare Blitz
- Flame Charge
- Protect

fushigi (Sandy Shocks) @ Life Orb
Ability: Protosynthesis
Level: 50
Tera Type: Water
EVs: 36 HP / 12 Def / 204 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Thunderbolt
- Earth Power
- Volt Switch

floam (Flutter Mane) @ Focus Sash
Ability: Protosynthesis
Level: 50
Tera Type: Stellar
EVs: 12 HP / 28 Def / 212 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Shadow Ball
- Icy Wind
- Protect

bop it (Rillaboom) @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 252 HP / 36 Atk / 204 Def / 12 SpD / 4 Spe
Adamant Nature
- Grassy Glide
- Wood Hammer
- U-turn
- Fake Out

pillow pets (Umbreon) @ Safety Goggles
Ability: Inner Focus
Level: 50
Tera Type: Poison
EVs: 212 HP / 140 Def / 156 SpD
Calm Nature
IVs: 0 Atk
- Foul Play
- Moonlight
- Snarl
- Yawn

silly bands (Gholdengo) @ Grassy Seed
Ability: Good as Gold
Level: 50
Tera Type: Water
EVs: 236 HP / 84 Def / 68 SpA / 12 SpD / 108 Spe
Modest Nature
IVs: 0 Atk
- Protect
- Make It Rain
- Shadow Ball
- Nasty Plot
""",
        """
Flutter Mane @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 116 HP / 204 Def / 52 SpA / 4 SpD / 132 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Icy Wind
- Taunt
- Protect

Landorus @ Life Orb
Ability: Sheer Force
Level: 50
Tera Type: Poison
EVs: 4 HP / 4 Def / 244 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 8 Atk
- Earth Power
- Sludge Bomb
- Substitute
- Protect

Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Normal
EVs: 236 HP / 44 Atk / 4 Def / 172 SpD / 52 Spe
Adamant Nature
- Glacial Lance
- Protect
- Trick Room
- High Horsepower

Ogerpon-Cornerstone @ Cornerstone Mask
Ability: Sturdy
Level: 50
Tera Type: Rock
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
IVs: 20 SpA
- Ivy Cudgel
- Power Whip
- Spiky Shield
- Follow Me

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 228 HP / 188 Def / 92 Spe
Impish Nature
- Fake Out
- Knock Off
- Parting Shot
- Taunt

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 196 HP / 60 Def / 20 SpA / 4 SpD / 228 Spe
Modest Nature
IVs: 20 Atk
- Thunderclap
- Electroweb
- Draco Meteor
- Volt Switch
""",
        """
Calyrex-Shadow @ Choice Specs
Ability: As One (Spectrier)
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Psyshock
- Pollen Puff
- Trick

Urshifu @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Wicked Blow
- Sucker Punch
- Close Combat
- Detect

Talonflame @ Sharp Beak
Ability: Gale Wings
Level: 50
Tera Type: Flying
EVs: 60 HP / 252 Atk / 196 Spe
Jolly Nature
- Brave Bird
- Tailwind
- Feint
- Quick Guard

Sylveon @ Fairy Feather
Ability: Pixilate
Level: 50
Tera Type: Fairy
EVs: 60 HP / 4 Def / 252 SpA / 4 SpD / 188 Spe
Modest Nature
- Hyper Voice
- Hyper Beam
- Quick Attack
- Detect

Gothitelle @ Sitrus Berry
Ability: Shadow Tag
Level: 50
Tera Type: Dark
EVs: 244 HP / 4 Atk / 36 Def / 4 SpD / 220 Spe
Jolly Nature
- Foul Play
- Taunt
- Helping Hand
- Fake Out

Ogerpon-Wellspring (F) @ Wellspring Mask
Ability: Water Absorb
Level: 50
Tera Type: Water
EVs: 252 HP / 76 Atk / 52 Def / 68 SpD / 60 Spe
Adamant Nature
- Ivy Cudgel
- Horn Leech
- Follow Me
- Spiky Shield
""",
        """
Miraidon @ Choice Specs
Ability: Hadron Engine
Tera Type: Electric
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
- Electro Drift
- Draco Meteor
- Discharge
- Volt Switch

Whimsicott @ Focus Sash
Ability: Prankster
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Encore
- Protect
- Tailwind

Iron Hands @ Assault Vest
Ability: Quark Drive
Tera Type: Water
EVs: 68 HP / 164 Atk / 4 Def / 220 SpD / 52 Spe
Adamant Nature
IVs: 29 SpA
- Fake Out
- Wild Charge
- Drain Punch
- Volt Switch

Farigiraf @ Electric Seed
Ability: Armor Tail
Tera Type: Fire
EVs: 228 HP / 164 Def / 116 SpD
Bold Nature
IVs: 0 Atk
- Helping Hand
- Psychic Noise
- Trick Room
- Foul Play

Volcarona @ Leftovers
Ability: Flame Body
Tera Type: Dragon
EVs: 252 HP / 76 Def / 36 SpA / 4 SpD / 140 Spe
Modest Nature
IVs: 0 Atk
- Flamethrower
- Bug Buzz
- Quiver Dance
- Protect

Ursaluna-Bloodmoon @ Life Orb
Ability: Mind's Eye
Tera Type: Normal
EVs: 4 HP / 12 Def / 132 SpA / 116 SpD / 244 Spe
Modest Nature
IVs: 2 Atk
- Hyper Voice
- Earth Power
- Blood Moon
- Protect
""",
        ### TAIWAN NATIONAL JUNE 2024 (2 teams) ###
        """
Zamazenta-Crowned @ Rusted Shield
Ability: Dauntless Shield
Level: 50
Tera Type: Dragon
EVs: 100 HP / 4 Atk / 236 Def / 4 SpD / 164 Spe
Impish Nature
- Body Press
- Wide Guard
- Protect
- Heavy Slam

Rillaboom @ Choice Band
Ability: Grassy Surge
Level: 50
Tera Type: Grass
EVs: 108 HP / 252 Atk / 148 Spe
Adamant Nature
- Grassy Glide
- Wood Hammer
- U-turn
- High Horsepower

Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Icicle Crash
- Protect
- Sucker Punch
- Sacred Sword

Flutter Mane @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Normal
EVs: 212 HP / 140 Def / 20 SpA / 4 SpD / 132 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Moonblast
- Thunder Wave
- Icy Wind

Chandelure @ Life Orb
Ability: Flash Fire
Level: 50
Tera Type: Grass
EVs: 188 HP / 4 Def / 196 SpA / 100 SpD / 20 Spe
Modest Nature
IVs: 14 Atk
- Protect
- Heat Wave
- Trick Room
- Shadow Ball

Moltres-Galar @ Black Glasses
Ability: Berserk
Level: 50
Tera Type: Dark
EVs: 252 HP / 236 Def / 4 SpA / 4 SpD / 12 Spe
Bold Nature
IVs: 20 Atk
- Protect
- Taunt
- Foul Play
- Fiery Wrath
""",
        """
Calyrex-Shadow @ Covert Cloak
Ability: As One (Spectrier)
Level: 50
Tera Type: Fairy
EVs: 180 HP / 84 Def / 84 SpA / 4 SpD / 156 Spe
Modest Nature
IVs: 0 Atk
- Astral Barrage
- Draining Kiss
- Calm Mind
- Protect

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 148 HP / 4 Def / 100 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 20 Atk
- Draco Meteor
- Thunderbolt
- Thunderclap
- Electroweb

Clefairy @ Eviolite
Ability: Friend Guard
Level: 50
Tera Type: Grass
EVs: 252 HP / 252 Def / 4 SpD
Bold Nature
IVs: 0 Atk / 17 Spe
- Follow Me
- Helping Hand
- Sing
- Protect

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Surging Strikes
- Close Combat
- Taunt
- Detect

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 4 Atk / 60 Def / 156 SpD / 44 Spe
Careful Nature
- Knock Off
- Will-O-Wisp
- Parting Shot
- Fake Out

Rillaboom @ Choice Band
Ability: Grassy Surge
Level: 50
Tera Type: Grass
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- High Horsepower
- U-turn
""",
        ### HONG KONG NATIONAL JUNE 2024 (2 teams) ###
        """
Koraidon @ Clear Amulet
Ability: Orichalcum Pulse
Level: 50
Tera Type: Fire
EVs: 140 HP / 188 Atk / 4 Def / 44 SpD / 132 Spe
Jolly Nature
- Collision Course
- Flare Blitz
- Dragon Claw
- Protect

Grimmsnarl @ Light Clay
Ability: Prankster
Level: 50
Tera Type: Ground
EVs: 252 HP / 4 Atk / 164 Def / 76 SpD / 12 Spe
Careful Nature
IVs: 0 Atk
- Light Screen
- Reflect
- Thunder Wave
- Foul Play

Flutter Mane @ Focus Sash
Ability: Protosynthesis
Level: 50
Tera Type: Grass
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Icy Wind
- Taunt
- Shadow Ball

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 140 HP / 164 Def / 100 SpA / 4 SpD / 100 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Thunderclap
- Weather Ball
- Draco Meteor

Ogerpon-Cornerstone (F) @ Cornerstone Mask
Ability: Sturdy
Level: 50
Tera Type: Rock
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Ivy Cudgel
- Power Whip
- Follow Me
- Spiky Shield

Gholdengo @ Life Orb
Ability: Good as Gold
Level: 50
Tera Type: Normal
EVs: 212 HP / 52 Def / 52 SpA / 100 SpD / 92 Spe
Modest Nature
IVs: 0 Atk
- Make It Rain
- Power Gem
- Nasty Plot
- Protect
""",
        """
Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Electric
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
- Electro Drift
- Draco Meteor
- Volt Switch
- Discharge

Whimsicott @ Focus Sash
Ability: Prankster
Level: 50
Tera Type: Ground
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Tailwind
- Encore
- Protect

Volcarona @ Leftovers
Ability: Flame Body
Level: 50
Tera Type: Water
EVs: 252 HP / 116 SpA / 140 Spe
Modest Nature
IVs: 0 Atk
- Flamethrower
- Giga Drain
- Quiver Dance
- Protect

Farigiraf @ Electric Seed
Ability: Armor Tail
Level: 50
Tera Type: Ground
EVs: 244 HP / 12 Def / 4 SpA / 236 SpD / 12 Spe
Calm Nature
IVs: 0 Atk
- Psychic Noise
- Foul Play
- Trick Room
- Helping Hand

Grimmsnarl @ Light Clay
Ability: Prankster
Level: 50
Tera Type: Ground
EVs: 244 HP / 4 Atk / 68 Def / 188 SpD / 4 Spe
Careful Nature
- Spirit Break
- Reflect
- Light Screen
- Thunder Wave

Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Fairy
EVs: 252 HP / 252 Atk / 4 Def
Brave Nature
IVs: 0 Spe
- Facade
- Headlong Rush
- Swords Dance
- Protect
""",
        ### JAPAN NATIONAL CHAMPIONSHIPS JUNE 2024 (15 teams) ###
        """
Terapagos @ Power Herb
Ability: Tera Shift
Level: 50
Tera Type: Stellar
EVs: 92 HP / 252 SpA / 164 Spe
Modest Nature
- Tera Starstorm
- Meteor Beam
- Rock Polish
- Protect

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Grass
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Detect

Ogerpon-Hearthflame (F) @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 252 HP / 100 Atk / 52 Def / 4 SpD / 100 Spe
Jolly Nature
- Ivy Cudgel
- Wood Hammer
- Follow Me
- Spiky Shield

Flutter Mane @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 148 HP / 236 Def / 116 SpA / 4 SpD / 4 Spe
Timid Nature
- Moonblast
- Icy Wind
- Trick Room
- Taunt

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 236 HP / 196 Def / 76 SpD
Calm Nature
IVs: 16 Spe
- Pollen Puff
- Spore
- Rage Powder
- Protect

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 50
Tera Type: Water
EVs: 172 HP / 156 Atk / 4 Def / 172 SpD / 4 Spe
Adamant Nature
- Wild Charge
- Drain Punch
- Heavy Slam
- Fake Out
""",
        """
Raging Bolt @ Life Orb
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Draco Meteor
- Thunderclap
- Protect

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Grass
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
IVs: 2 SpA
- Close Combat
- Surging Strikes
- Aqua Jet
- Detect

Ogerpon-Cornerstone (F) @ Cornerstone Mask
Ability: Sturdy
Level: 50
Tera Type: Rock
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
IVs: 20 SpA
- Ivy Cudgel
- Power Whip
- Follow Me
- Spiky Shield

Calyrex-Ice @ Assault Vest
Ability: As One (Glastrier)
Level: 50
Tera Type: Fire
EVs: 132 HP / 116 Atk / 4 Def / 12 SpD / 244 Spe
Adamant Nature
- Glacial Lance
- High Horsepower
- Seed Bomb
- Crunch

Iron Valiant @ Booster Energy
Ability: Quark Drive
Level: 50
Tera Type: Steel
EVs: 252 HP / 84 Def / 4 SpA / 52 SpD / 116 Spe
Timid Nature
IVs: 4 Atk
- Moonblast
- Icy Wind
- Disable
- Protect

Pelipper @ Covert Cloak
Ability: Drizzle
Level: 50
Tera Type: Steel
EVs: 244 HP / 4 Def / 60 SpA / 60 SpD / 140 Spe
Modest Nature
IVs: 0 Atk
- Weather Ball
- Hurricane
- Tailwind
- Wide Guard
""",
        """
Kyogre @ Covert Cloak
Ability: Drizzle
Level: 50
Tera Type: Ice
EVs: 212 HP / 4 Def / 244 SpA / 4 SpD / 44 Spe
Modest Nature
- Blizzard
- Hydro Pump
- Thunder
- Water Spout

Chien-Pao @ Life Orb
Ability: Sword of Ruin
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Ice Shard
- Protect
- Sucker Punch
- Throat Chop

Tornadus @ Focus Sash
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 8 Atk
- Tailwind
- Protect
- Snowscape
- Bleakwind Storm

Rillaboom @ Miracle Seed
Ability: Grassy Surge
Level: 50
Tera Type: Normal
EVs: 188 HP / 196 Atk / 20 Def / 60 SpD / 44 Spe
Adamant Nature
- Grassy Glide
- Wood Hammer
- Protect
- Swords Dance

Urshifu-Rapid-Strike @ Mystic Water
Ability: Unseen Fist
Level: 50
Tera Type: Steel
EVs: 124 HP / 252 Atk / 4 Def / 44 SpD / 84 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Detect
- Aqua Jet

Entei @ Assault Vest
Ability: Inner Focus
Level: 50
Tera Type: Grass
EVs: 116 HP / 196 Atk / 12 Def / 116 SpD / 68 Spe
Adamant Nature
- Sacred Fire
- Extreme Speed
- Trailblaze
- Stomping Tantrum
""",
        """
Lunala @ Leftovers
Ability: Shadow Shield
Level: 50
Tera Type: Fairy
EVs: 228 HP / 52 Def / 180 SpA / 4 SpD / 44 Spe
Modest Nature
IVs: 0 Atk
- Moongeist Beam
- Moonblast
- Calm Mind
- Protect

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
IVs: 4 SpA
- Close Combat
- Surging Strikes
- Aqua Jet
- Detect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Water
EVs: 172 HP / 252 Atk / 4 Def / 4 SpD / 76 Spe
Adamant Nature
- Grassy Glide
- Wood Hammer
- U-turn
- Fake Out

Iron Jugulis @ Booster Energy
Ability: Quark Drive
Level: 50
Tera Type: Ghost
EVs: 252 HP / 12 Def / 4 SpA / 116 SpD / 124 Spe
Timid Nature
IVs: 0 Atk
- Snarl
- Air Slash
- Tailwind
- Rain Dance

Umbreon @ Sitrus Berry
Ability: Inner Focus
Level: 50
Tera Type: Poison
EVs: 244 HP / 188 Def / 76 SpD
Calm Nature
IVs: 0 Atk
- Foul Play
- Toxic
- Taunt
- Reflect

Chi-Yu @ Choice Scarf
Ability: Beads of Ruin
Level: 50
Tera Type: Ghost
EVs: 148 HP / 4 Def / 100 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Heat Wave
- Snarl
- Overheat
- Will-O-Wisp
""",
        """
Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Grass
EVs: 252 HP / 252 Atk / 4 Def
Brave Nature
IVs: 0 Spe
- Protect
- Glacial Lance
- High Horsepower
- Trick Room

Mienshao @ Focus Sash
Ability: Inner Focus
Level: 50
Tera Type: Grass
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Close Combat
- Wide Guard
- Coaching
- Fake Out

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 68 HP / 124 Def / 228 SpA / 84 SpD / 4 Spe
Modest Nature
- Thunderclap
- Dragon Pulse
- Snarl
- Thunderbolt

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 252 HP / 252 Def / 4 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Spore
- Rage Powder
- Pollen Puff
- Clear Smog

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Water
EVs: 252 HP / 20 Atk / 180 Def / 44 SpD / 12 Spe
Impish Nature
- Fake Out
- Will-O-Wisp
- Knock Off
- Parting Shot

Ting-Lu @ Lum Berry
Ability: Vessel of Ruin
Level: 50
Tera Type: Fairy
EVs: 252 HP / 252 Atk / 4 Def
Brave Nature
IVs: 4 Spe
- Stomping Tantrum
- Ruination
- Tera Blast
- Protect
""",
        """
Grimmsnarl @ Lagging Tail
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 252 HP / 60 Def / 196 SpD
Careful Nature
IVs: 24 SpA
- Spirit Break
- Trick
- Light Screen
- Thunder Wave

Landorus @ Life Orb
Ability: Sheer Force
Level: 50
Tera Type: Water
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 8 Atk
- Earth Power
- Sandsear Storm
- Sludge Bomb
- Protect

Calyrex-Ice @ Assault Vest
Ability: As One (Glastrier)
Level: 50
Tera Type: Water
EVs: 252 HP / 116 Atk / 4 Def / 12 SpD / 124 Spe
Adamant Nature
- Glacial Lance
- Crunch
- Seed Bomb
- High Horsepower

Pelipper @ Focus Sash
Ability: Drizzle
Level: 50
Tera Type: Dark
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Hurricane
- Weather Ball
- Tailwind
- Wide Guard

Urshifu-Rapid-Strike @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Ghost
EVs: 244 Atk / 12 SpD / 252 Spe
Adamant Nature
IVs: 24 SpA
- Surging Strikes
- Close Combat
- U-turn
- Coaching

Rillaboom @ Sitrus Berry
Ability: Grassy Surge
Level: 50
Tera Type: Grass
EVs: 172 HP / 36 Atk / 4 Def / 108 SpD / 188 Spe
Adamant Nature
- Grassy Glide
- Drum Beating
- U-turn
- Fake Out
""",
        """
Calyrex-Shadow @ Focus Sash
Ability: As One (Spectrier)
Level: 50
Tera Type: Ghost
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Disable
- Encore
- Protect

Cobalion @ Grassy Seed
Ability: Justified
Level: 50
Tera Type: Ground
EVs: 252 HP / 156 Def / 4 SpD / 92 Spe
Bold Nature
IVs: 0 Atk
- Body Press
- Quick Guard
- Taunt
- Protect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 220 HP / 116 Atk / 4 Def / 12 SpD / 156 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- U-turn
- Fake Out

Raging Bolt @ Life Orb
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 20 Atk
- Thunderclap
- Draco Meteor
- Volt Switch
- Protect

Tornadus @ Mental Herb
Ability: Prankster
Level: 50
Tera Type: Normal
EVs: 252 HP / 100 Def / 156 SpD
Modest Nature
IVs: 24 Spe
- Bleakwind Storm
- Tailwind
- Sunny Day
- Taunt

Urshifu-Rapid-Strike @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Grass
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Iron Head
- U-turn
""",
        """
Tornadus @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 252 HP / 156 Def / 100 SpD
Bold Nature
IVs: 20 Atk
- Tailwind
- Bleakwind Storm
- Scary Face
- Protect

Urshifu @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Wicked Blow
- Detect
- Close Combat
- Sucker Punch

Dragonite @ Silk Scarf
Ability: Multiscale
Level: 50
Tera Type: Normal
EVs: 140 HP / 252 Atk / 4 Def / 4 SpD / 108 Spe
Adamant Nature
IVs: 10 SpA
- Extreme Speed
- Haze
- Low Kick
- Ice Spinner

Incineroar @ Room Service
Ability: Intimidate
Level: 50
Tera Type: Water
EVs: 252 HP / 36 Atk / 76 Def / 140 SpD
Relaxed Nature
- Flare Blitz
- Knock Off
- Taunt
- Fake Out

Landorus-Therian @ Assault Vest
Ability: Intimidate
Level: 50
Tera Type: Fairy
EVs: 236 HP / 252 Atk / 4 Def / 4 SpD / 12 Spe
Adamant Nature
- Earthquake
- Rock Slide
- U-turn
- Stomping Tantrum

Calyrex-Shadow @ Choice Specs
Ability: As One (Spectrier)
Level: 50
Tera Type: Normal
EVs: 116 HP / 4 Def / 132 SpA / 4 SpD / 252 Spe
Timid Nature
- Astral Barrage
- Psychic
- Pollen Puff
- Shadow Ball
""",
        """
Lunala @ Power Herb
Ability: Shadow Shield
Level: 50
Tera Type: Fairy
EVs: 164 HP / 4 Def / 252 SpA / 4 SpD / 84 Spe
Modest Nature
IVs: 2 Atk
- Expanding Force
- Moonblast
- Meteor Beam
- Trick Room

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 204 HP / 204 Atk / 100 SpD
Adamant Nature
IVs: 16 SpA
- Wood Hammer
- Grassy Glide
- High Horsepower
- Fake Out

Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Ghost
EVs: 204 HP / 236 Atk / 68 SpD
Brave Nature
IVs: 4 SpA / 0 Spe
- Headlong Rush
- Facade
- Rock Slide
- Protect

Indeedee-F @ Safety Goggles
Ability: Psychic Surge
Level: 50
Tera Type: Fairy
EVs: 252 HP / 252 Def / 4 SpD
Relaxed Nature
- Follow Me
- Dazzling Gleam
- Trick Room
- Helping Hand

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Detect

Torkoal @ Choice Specs
Ability: Drought
Level: 50
Tera Type: Fire
EVs: 252 HP / 252 SpA / 4 SpD
Quiet Nature
IVs: 0 Atk / 0 Spe
- Eruption
- Heat Wave
- Weather Ball
- Overheat
""",
        """
Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Fire
EVs: 252 HP / 252 Atk / 4 SpD
Brave Nature
IVs: 0 Spe
- Glacial Lance
- High Horsepower
- Trick Room
- Encore

Iron Valiant @ Booster Energy
Ability: Quark Drive
Level: 50
Tera Type: Ghost
EVs: 76 HP / 28 Atk / 4 Def / 228 SpA / 172 Spe
Naive Nature
- Moonblast
- Knock Off
- Encore
- Coaching

Amoonguss @ Covert Cloak
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 236 HP / 76 Def / 196 SpD
Sassy Nature
IVs: 0 Atk / 0 Spe
- Spore
- Pollen Puff
- Rage Powder
- Clear Smog

Pelipper @ Choice Specs
Ability: Drizzle
Level: 50
Tera Type: Ground
EVs: 252 HP / 252 SpA / 4 SpD
Quiet Nature
IVs: 0 Spe
- Weather Ball
- Hurricane
- Tera Blast
- Wide Guard

Thundurus @ Mental Herb
Ability: Prankster
Level: 50
Tera Type: Steel
EVs: 212 HP / 92 Def / 204 SpD
Calm Nature
- Thunderbolt
- Taunt
- Eerie Impulse
- Sunny Day

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Water
EVs: 252 HP / 36 Atk / 4 Def / 68 SpD / 148 Spe
Adamant Nature
- Wood Hammer
- High Horsepower
- U-turn
- Fake Out
""",
        """
Grimmsnarl @ Lagging Tail
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 228 HP / 164 Def / 116 SpD
Careful Nature
- Fake Out
- Light Screen
- Spirit Break
- Trick

Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Water
EVs: 252 HP / 116 Atk / 4 Def / 100 SpD / 36 Spe
Adamant Nature
- Glacial Lance
- High Horsepower
- Trick Room
- Protect

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 156 Def / 76 SpD / 28 Spe
Impish Nature
- Fake Out
- Knock Off
- Will-O-Wisp
- Parting Shot

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 252 HP / 236 Def / 20 SpD
Relaxed Nature
IVs: 28 Atk / 22 Spe
- Pollen Puff
- Spore
- Rage Powder
- Clear Smog

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 196 HP / 124 Def / 180 SpA / 4 SpD / 4 Spe
Modest Nature
IVs: 20 Atk
- Thunderclap
- Draco Meteor
- Thunderbolt
- Volt Switch

Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Water
EVs: 236 HP / 236 Atk / 36 Def
Brave Nature
IVs: 6 SpA / 0 Spe
- Headlong Rush
- Facade
- Earthquake
- Protect
""",
        """
Whimsicott @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Rock
EVs: 140 HP / 116 SpD / 252 Spe
Timid Nature
IVs: 6 Atk
- Moonblast
- Beat Up
- Encore
- Tailwind

Terrakion @ Sitrus Berry
Ability: Justified
Level: 50
Tera Type: Grass
EVs: 140 HP / 76 Atk / 4 Def / 60 SpD / 228 Spe
Adamant Nature
IVs: 4 SpA
- Rock Slide
- Close Combat
- Quick Attack
- Protect

Archaludon @ Power Herb
Ability: Sturdy
Level: 50
Tera Type: Normal
EVs: 252 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Steel Beam
- Draco Meteor
- Electro Shot
- Protect

Kyogre @ Choice Scarf
Ability: Drizzle
Level: 50
Tera Type: Water
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 2 Atk
- Water Spout
- Origin Pulse
- Ice Beam
- Thunder

Urshifu @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Dark
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Wicked Blow
- Sucker Punch
- Close Combat
- Detect

Tsareena @ Wide Lens
Ability: Queenly Majesty
Level: 50
Tera Type: Ice
EVs: 12 HP / 236 Atk / 4 Def / 4 SpD / 252 Spe
Adamant Nature
IVs: 22 SpA
- Power Whip
- Triple Axel
- High Jump Kick
- Helping Hand
""",
        """
Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Normal
EVs: 220 HP / 116 Atk / 4 Def / 4 SpD / 164 Spe
Adamant Nature
IVs: 10 SpA
- Glacial Lance
- High Horsepower
- Swords Dance
- Protect

Urshifu-Rapid-Strike @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Close Combat
- Surging Strikes
- U-turn
- Aqua Jet

Pelipper @ Focus Sash
Ability: Drizzle
Level: 50
Tera Type: Ghost
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Hurricane
- Weather Ball
- Tailwind
- Wide Guard

Incineroar @ Assault Vest
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 4 Atk / 188 Def / 68 SpD / 4 Spe
Impish Nature
IVs: 14 SpA
- Flare Blitz
- Knock Off
- U-turn
- Fake Out

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Fairy
EVs: 252 HP / 244 Def / 12 SpD
Bold Nature
IVs: 0 Atk / 26 Spe
- Pollen Puff
- Rage Powder
- Spore
- Protect

Indeedee-F @ Psychic Seed
Ability: Psychic Surge
Level: 50
Tera Type: Dragon
EVs: 252 HP / 220 Def / 36 SpD
Calm Nature
IVs: 0 Atk / 28 Spe
- Psychic
- Follow Me
- Trick Room
- Helping Hand
""",
        """
Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 140 HP / 4 Def / 124 SpA / 4 SpD / 236 Spe
Modest Nature
- Electro Drift
- Draco Meteor
- Dazzling Gleam
- Volt Switch

Chi-Yu @ Choice Scarf
Ability: Beads of Ruin
Level: 50
Tera Type: Fire
EVs: 124 HP / 4 Def / 140 SpA / 4 SpD / 236 Spe
Modest Nature
IVs: 0 Atk
- Snarl
- Dark Pulse
- Heat Wave
- Overheat

Iron Treads @ Life Orb
Ability: Quark Drive
Level: 50
Tera Type: Dragon
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Earthquake
- Steel Roller
- High Horsepower
- Protect

Farigiraf @ Electric Seed
Ability: Armor Tail
Level: 50
Tera Type: Water
EVs: 252 HP / 92 Def / 164 SpD
Calm Nature
IVs: 4 Atk / 20 Spe
- Trick Room
- Foul Play
- Helping Hand
- Psychic

Tornadus (M) @ Focus Sash
Ability: Prankster
Level: 50
Tera Type: Flying
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Bleakwind Storm
- Protect
- Tailwind
- Rain Dance

Urshifu-Rapid-Strike @ Choice Band
Ability: Unseen Fist
Level: 50
Tera Type: Poison
EVs: 156 HP / 252 Atk / 4 Def / 4 SpD / 92 Spe
Adamant Nature
- Surging Strikes
- U-turn
- Close Combat
- Aqua Jet
""",
        """
Zamazenta-Crowned @ Rusted Shield
Ability: Dauntless Shield
Level: 50
Tera Type: Dragon
EVs: 252 HP / 4 Atk / 44 Def / 44 SpD / 164 Spe
Impish Nature
- Behemoth Bash
- Body Press
- Protect
- Iron Defense

Cresselia @ Safety Goggles
Ability: Levitate
Level: 50
Tera Type: Electric
EVs: 252 HP / 236 Def / 20 SpD
Bold Nature
- Psychic
- Lunar Blessing
- Ally Switch
- Trick Room

Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 252 Spe
Jolly Nature
IVs: 10 SpA
- Icicle Crash
- Sucker Punch
- Throat Chop
- Protect

Rillaboom @ Choice Band
Ability: Grassy Surge
Level: 50
Tera Type: Grass
EVs: 228 HP / 252 Atk / 4 SpD / 20 Spe
Adamant Nature
IVs: 10 SpA
- Grassy Glide
- Wood Hammer
- High Horsepower
- U-turn

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 220 HP / 12 Def / 244 SpA / 28 SpD / 4 Spe
Modest Nature
- Thunderclap
- Electroweb
- Dragon Pulse
- Snarl

Moltres-Galar @ Sitrus Berry
Ability: Berserk
Level: 50
Tera Type: Fire
EVs: 236 HP / 4 Def / 204 SpA / 36 SpD / 12 Spe
Calm Nature
IVs: 4 Atk
- Fiery Wrath
- Air Slash
- Tailwind
- Protect
""",
        ### LOS ANGELES REGIONALS MAY 2024 (7 teams) ###
        """
Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Electric
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
- Electro Drift
- Discharge
- Volt Switch
- Draco Meteor

Iron Bundle @ Focus Sash
Ability: Quark Drive
Level: 50
Tera Type: Ground
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
- Freeze-Dry
- Icy Wind
- Tera Blast
- Protect

Farigiraf @ Electric Seed
Ability: Armor Tail
Level: 50
Tera Type: Ground
EVs: 244 HP / 60 Def / 204 SpD
Sassy Nature
IVs: 0 Atk
- Helping Hand
- Psychic Noise
- Foul Play
- Trick Room

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 50
Tera Type: Bug
EVs: 92 HP / 172 Atk / 4 Def / 220 SpD / 20 Spe
Adamant Nature
- Fake Out
- Wild Charge
- Drain Punch
- Heavy Slam

Landorus @ Life Orb
Ability: Sheer Force
Level: 50
Tera Type: Poison
EVs: 44 HP / 4 Def / 204 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 10 Atk
- Earth Power
- Sludge Bomb
- Sandsear Storm
- Protect

Grimmsnarl @ Light Clay
Ability: Prankster
Level: 50
Tera Type: Ground
EVs: 252 HP / 140 Def / 116 SpD
Careful Nature
- Reflect
- Light Screen
- Thunder Wave
- Foul Play
""",
        """
Whimsicott @ Focus Sash
Ability: Prankster
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Cotton Spore
- Tailwind
- Protect

Regidrago @ Life Orb
Ability: Dragon's Maw
Tera Type: Ghost
EVs: 4 HP / 20 Def / 252 SpA / 4 SpD / 228 Spe
Modest Nature
IVs: 0 Atk
- Dragon Energy
- Draco Meteor
- Tera Blast
- Protect

Chi-Yu @ Choice Scarf
Ability: Beads of Ruin
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 0 Atk
- Heat Wave
- Flamethrower
- Dark Pulse
- Snarl

Zacian @ Rusted Sword
Ability: Intrepid Sword
Tera Type: Ground
EVs: 4 HP / 252 Atk / 4 Def / 68 SpD / 180 Spe
Jolly Nature
- Iron Head
- Sacred Sword
- Tera Blast
- Protect

Ogerpon-Wellspring (F) @ Wellspring Mask
Ability: Water Absorb
Tera Type: Water
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Ivy Cudgel
- Horn Leech
- Follow Me
- Spiky Shield

Amoonguss @ Sitrus Berry
Ability: Regenerator
Tera Type: Water
EVs: 244 HP / 220 Def / 44 SpD
Bold Nature
IVs: 0 Atk / 27 Spe
- Spore
- Sludge Bomb
- Rage Powder
- Protect
""",
        """
Time's Arrow (Calyrex-Ice) @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Water
EVs: 236 HP / 236 Atk / 36 Spe
Adamant Nature
- Glacial Lance
- High Horsepower
- Trick Room
- Protect

Free Churro (Incineroar) (M) @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 188 Def / 76 Spe
Impish Nature
- Knock Off
- Fake Out
- Taunt
- Parting Shot

TooMuch,Man (Amoonguss) (F) @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 244 HP / 180 Def / 84 SpD
Bold Nature
IVs: 0 Atk / 26 Spe
- Spore
- Rage Powder
- Pollen Puff
- Protect

EscapeFromLA (Raging Bolt) @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 196 HP / 132 Def / 108 SpA / 20 SpD / 52 Spe
Modest Nature
IVs: 20 Atk
- Electroweb
- Thunderclap
- Draco Meteor
- Volt Switch

Showstopper (Urshifu) (M) @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Dark
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Wicked Blow
- Sucker Punch
- Close Combat
- Protect

DownerEnding (Landorus) @ Life Orb
Ability: Sheer Force
Level: 50
Tera Type: Poison
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Earth Power
- Sludge Bomb
- Substitute
- Protect
""",
        """
Lunala @ Power Herb
Ability: Shadow Shield
Level: 50
Tera Type: Grass
EVs: 252 HP / 4 Def / 244 SpA / 4 SpD / 4 Spe
Modest Nature
IVs: 0 Atk
- Moongeist Beam
- Meteor Beam
- Trick Room
- Wide Guard

Urshifu-Rapid-Strike @ Life Orb
Ability: Unseen Fist
Level: 50
Tera Type: Steel
EVs: 100 HP / 236 Atk / 4 Def / 4 SpD / 164 Spe
Adamant Nature
- Surging Strikes
- Aqua Jet
- Close Combat
- Detect

Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Ghost
EVs: 252 HP / 252 Atk / 4 SpD
Brave Nature
IVs: 0 SpA / 0 Spe
- Facade
- Earthquake
- Headlong Rush
- Protect

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 4 Atk / 4 Def / 4 SpD / 252 Spe
Jolly Nature
- Knock Off
- Fake Out
- Will-O-Wisp
- Parting Shot

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Fairy
EVs: 220 HP / 220 Def / 68 SpD
Relaxed Nature
IVs: 2 Atk / 20 Spe
- Spore
- Rage Powder
- Pollen Puff
- Protect

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 196 HP / 124 Def / 180 SpA / 4 SpD / 4 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Thunderclap
- Draco Meteor
- Snarl
""",
        """
Lust (Flutter Mane) @ Choice Specs
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 108 HP / 148 SpA / 252 Spe
Timid Nature
IVs: 15 Atk
- Dazzling Gleam
- Moonblast
- Power Gem
- Shadow Ball

Sloth (Groudon) @ Clear Amulet
Ability: Drought
Level: 50
Tera Type: Fire
EVs: 4 HP / 244 Atk / 4 Def / 4 SpD / 252 Spe
Jolly Nature
- Precipice Blades
- Heat Crash
- Thunder Punch
- Protect

Pride (Incineroar) @ Sitrus Berry
Ability: Intimidate
Level: 50
Tera Type: Grass
EVs: 252 HP / 4 Atk / 108 Def / 60 SpD / 84 Spe
Impish Nature
- Fake Out
- Flare Blitz
- Knock Off
- Will-O-Wisp

Wrath (Chi-Yu) @ Focus Sash
Ability: Beads of Ruin
Level: 50
Tera Type: Ghost
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Overheat
- Dark Pulse
- Burning Jealousy
- Protect

Gluttony (Rillaboom) (M) @ Assault Vest
Ability: Grassy Surge
Level: 50
Shiny: Yes
Tera Type: Steel
EVs: 252 HP / 4 Atk / 108 Def / 4 SpD / 140 Spe
Impish Nature
- Fake Out
- Wood Hammer
- Grassy Glide
- U-turn

Greed (Tornadus) @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 244 HP / 204 SpD / 60 Spe
Calm Nature
IVs: 25 Atk
- Bleakwind Storm
- Tailwind
- Sunny Day
- Protect
""",
        """
Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Icicle Crash
- Sucker Punch
- Sacred Sword
- Protect

Zacian-Crowned @ Rusted Sword
Ability: Intrepid Sword
Tera Type: Stellar
EVs: 100 HP / 252 Atk / 156 Spe
Jolly Nature
- Play Rough
- Behemoth Blade
- Close Combat
- Protect

Landorus @ Choice Scarf
Ability: Sheer Force
Level: 50
Tera Type: Ground
EVs: 252 SpA / 252 Spe
Modest Nature
- Earth Power
- U-turn
- Sandsear Storm
- Sludge Bomb

Suicune @ Rocky Helmet
Ability: Inner Focus
Shiny: Yes
Tera Type: Dark
EVs: 252 HP / 52 Def / 100 SpA / 52 SpD / 52 Spe
Bold Nature
IVs: 0 Atk
- Scald
- Snarl
- Calm Mind
- Mist

Incineroar @ Assault Vest
Ability: Intimidate
Level: 50
Tera Type: Grass
EVs: 252 HP / 196 Def / 60 SpD
Impish Nature
IVs: 29 Spe
- Flare Blitz
- Knock Off
- Fake Out
- U-turn

Whimsicott @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Tailwind
- Moonblast
- Encore
""",
        """
Lugia @ Covert Cloak
Ability: Multiscale
Level: 50
Tera Type: Fairy
EVs: 252 HP / 60 Def / 140 SpA / 52 SpD / 4 Spe
Bold Nature
- Aeroblast
- Earth Power
- Calm Mind
- Protect

Comfey @ Sitrus Berry
Ability: Triage
Level: 50
Tera Type: Water
EVs: 236 HP / 236 Def / 28 SpA / 4 SpD / 4 Spe
Calm Nature
IVs: 0 Atk
- Draining Kiss
- Floral Healing
- Trick Room
- Protect

Sableye @ Light Clay
Ability: Prankster
Level: 50
Tera Type: Steel
EVs: 212 HP / 140 Def / 156 SpD
Calm Nature
IVs: 0 Atk / 0 SpA
- Reflect
- Light Screen
- Will-O-Wisp
- Taunt

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 252 HP / 228 Atk / 4 Def / 20 SpD / 4 Spe
Adamant Nature
IVs: 8 SpA
- Fake Out
- Wood Hammer
- Grassy Glide
- U-turn

Ogerpon-Cornerstone (F) @ Cornerstone Mask
Ability: Sturdy
Level: 50
Tera Type: Rock
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
IVs: 20 SpA
- Follow Me
- Ivy Cudgel
- Power Whip
- Spiky Shield

Pelipper @ Focus Sash
Ability: Drizzle
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 0 Atk
- Weather Ball
- Hurricane
- Wide Guard
- Protect
""",
        ### STOCKHOLM REGIONALS MAY 2024 (3 teams) ###
        """
Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 50
Tera Type: Water
EVs: 12 HP / 156 Atk / 76 Def / 252 SpD / 12 Spe
Adamant Nature
- Drain Punch
- Ice Punch
- Volt Switch
- Fake Out

Whimsicott @ Focus Sash
Ability: Prankster
Level: 50
Tera Type: Ground
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Tailwind
- Encore
- Protect

Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Electric
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
- Electro Drift
- Draco Meteor
- Volt Switch
- Discharge

Ogerpon-Wellspring @ Wellspring Mask
Ability: Water Absorb
Level: 50
Tera Type: Water
EVs: 156 HP / 156 Atk / 4 Def / 4 SpD / 188 Spe
Jolly Nature
- Ivy Cudgel
- Wood Hammer
- Follow Me
- Spiky Shield

Farigiraf @ Electric Seed
Ability: Armor Tail
Level: 50
Tera Type: Ground
EVs: 140 HP / 156 Def / 212 SpD
Bold Nature
IVs: 0 Atk
- Psychic
- Foul Play
- Helping Hand
- Trick Room

Ursaluna-Bloodmoon @ Life Orb
Ability: Mind’s Eye
Level: 50
Tera Type: Normal
EVs: 164 HP / 4 Def / 252 SpA / 36 SpD / 52 Spe
Modest Nature
IVs: 0 Atk
- Blood Moon
- Hyper Voice
- Earth Power
- Protect
""",
        """
Chi-Yu @ Choice Scarf
Ability: Beads of Ruin
Level: 50
Tera Type: Ground
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 28 Atk
- Heat Wave
- Overheat
- Tera Blast
- Snarl

Tornadus @ Focus Sash
Ability: Prankster
Level: 50
Tera Type: Ground
EVs: 4 Def / 252 SpA / 252 Spe
Modest Nature
- Tailwind
- Bleakwind Storm
- Taunt
- Protect

Ursaluna-Bloodmoon @ Life Orb
Ability: Mind’s Eye
Level: 50
Tera Type: Normal
EVs: 4 HP / 4 Def / 252 SpA / 4 SpD / 244 Spe
Modest Nature
- Blood Moon
- Earth Power
- Protect
- Hyper Voice

Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Electric
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
- Discharge
- Electro Drift
- Draco Meteor
- Volt Switch

Farigiraf @ Electric Seed
Ability: Armor Tail
Level: 50
Tera Type: Fairy
EVs: 244 HP / 12 Def / 4 SpA / 236 SpD / 12 Spe
Calm Nature
IVs: 10 Atk
- Helping Hand
- Psyshock
- Trick Room
- Foul Play

Iron Hands @ Clear Amulet
Ability: Quark Drive
Level: 50
Tera Type: Fire
EVs: 164 HP / 252 Atk / 92 SpD
Brave Nature
IVs: 8 SpA / 0 Spe
- Ice Punch
- Close Combat
- Fake Out
- Wild Charge
""",
        """
Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 244 HP / 60 Def / 100 SpA / 20 SpD / 84 Spe
Modest Nature
- Thunderclap
- Snarl
- Draco Meteor
- Electroweb

Flutter Mane @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 100 HP / 60 Def / 92 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 6 Atk
- Taunt
- Protect
- Thunder Wave
- Moonblast

Gastrodon-East @ Leftovers
Ability: Storm Drain
Level: 50
Tera Type: Fire
EVs: 180 HP / 92 Def / 92 SpA / 140 SpD
Calm Nature
IVs: 0 Atk / 0 Spe
- Protect
- Earth Power
- Yawn
- Icy Wind

Urshifu @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Dark
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Wicked Blow
- Close Combat
- Sucker Punch
- Detect

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 4 Atk / 68 Def / 156 SpD / 36 Spe
Careful Nature
- Fake Out
- Flare Blitz
- Will-O-Wisp
- Parting Shot

Calyrex-Shadow @ Covert Cloak
Ability: As One (Spectrier)
Level: 50
Tera Type: Fairy
EVs: 132 HP / 84 Def / 36 SpA / 4 SpD / 252 Spe
Timid Nature
- Protect
- Draining Kiss
- Astral Barrage
- Calm Mind
""",
        ### INDIANAPOLIS REGIONALS MAY 2024 (6 teams) ###
        """
Whimsicott @ Focus Sash
Ability: Prankster
Tera Type: Ghost
EVs: 4 HP / 44 Def / 204 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Tailwind
- Encore
- Protect

Ogerpon-Cornerstone @ Cornerstone Mask
Ability: Sturdy
Tera Type: Rock
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Ivy Cudgel
- Power Whip
- Follow Me
- Spiky Shield

Incineroar @ Assault Vest
Ability: Intimidate
Tera Type: Grass
EVs: 252 HP / 196 Def / 60 SpD
Impish Nature
IVs: 29 Spe
- Flare Blitz
- Knock Off
- Fake Out
- U-turn

Miraidon @ Choice Specs
Ability: Hadron Engine
Tera Type: Electric
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
- Electro Drift
- Draco Meteor
- Volt Switch
- Discharge

Ursaluna-Bloodmoon @ Life Orb
Ability: Mind's Eye
Tera Type: Normal
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Hyper Voice
- Blood Moon
- Earth Power
- Protect

Farigiraf @ Electric Seed
Ability: Armor Tail
Tera Type: Ground
EVs: 180 HP / 236 Def / 92 SpD
Bold Nature
IVs: 0 Atk
- Tera Blast
- Foul Play
- Trick Room
- Helping Hand
""",
        """
Koraidon @ Clear Amulet
Ability: Orichalcum Pulse
Level: 50
Tera Type: Fire
EVs: 116 HP / 156 Atk / 4 Def / 4 SpD / 228 Spe
Adamant Nature
- Collision Course
- Flare Blitz
- Bulk Up
- Protect

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 4 Atk / 100 Def / 100 SpD / 60 Spe
Adamant Nature
IVs: 0 SpA
- Flare Blitz
- Fake Out
- Parting Shot
- Will-O-Wisp

Ogerpon-Wellspring (F) @ Wellspring Mask
Ability: Water Absorb
Level: 50
Tera Type: Water
EVs: 252 HP / 4 Atk / 252 Def
Impish Nature
- Ivy Cudgel
- Horn Leech
- Follow Me
- Spiky Shield

Flutter Mane @ Choice Specs
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 244 HP / 108 Def / 76 SpA / 12 SpD / 68 Spe
Timid Nature
IVs: 0 Atk
- Shadow Ball
- Dazzling Gleam
- Moonblast
- Icy Wind

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 196 HP / 116 Def / 156 SpA / 4 SpD / 36 Spe
Modest Nature
IVs: 20 Atk
- Thunderclap
- Draco Meteor
- Electroweb
- Thunderbolt

Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
IVs: 22 SpA
- Ice Spinner
- Sucker Punch
- Sacred Sword
- Protect
""",
        """
Gouging Fire @ Covert Cloak
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 172 HP / 52 Atk / 44 Def / 12 SpD / 228 Spe
Jolly Nature
- Flare Blitz
- Snarl
- Breaking Swipe
- Howl

Groudon @ Clear Amulet
Ability: Drought
Level: 50
Tera Type: Fire
EVs: 204 HP / 92 Atk / 4 Def / 148 SpD / 60 Spe
Adamant Nature
- Precipice Blades
- Heat Crash
- Thunder Punch
- Protect

Flutter Mane @ Choice Specs
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 100 HP / 92 Def / 140 SpA / 4 SpD / 172 Spe
Timid Nature
IVs: 8 Atk
- Dazzling Gleam
- Moonblast
- Shadow Ball
- Icy Wind

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 252 HP / 116 Atk / 4 Def / 76 SpD / 60 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- Fake Out
- U-turn

Urshifu (F) @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Dark
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Wicked Blow
- Sucker Punch
- Close Combat
- Detect

Raging Bolt @ Safety Goggles
Ability: Protosynthesis
Level: 50
Tera Type: Water
EVs: 252 HP / 100 Def / 108 SpA / 44 SpD / 4 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Draco Meteor
- Thunderclap
- Protect
""",
        """
Kyurem-White @ Assault Vest
Ability: Turboblaze
Level: 50
Shiny: Yes
Tera Type: Fairy
EVs: 100 HP / 44 Def / 252 SpA / 100 SpD / 12 Spe
Modest Nature
IVs: 0 Atk
- Blizzard
- Freeze-Dry
- Earth Power
- Fusion Flare

Ninetales-Alola @ Focus Sash
Ability: Snow Warning
Level: 50
Shiny: Yes
Tera Type: Fire
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Blizzard
- Moonblast
- Aurora Veil
- Fake Tears

Milotic @ Leftovers
Ability: Competitive
Level: 50
Shiny: Yes
Tera Type: Grass
EVs: 252 HP / 44 Def / 4 SpA / 172 SpD / 36 Spe
Calm Nature
IVs: 0 Atk
- Hypnosis
- Coil
- Scald
- Life Dew

Urshifu-Rapid-Strike @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Surging Strikes
- Aqua Jet
- Close Combat
- U-turn

Ursaluna-Bloodmoon @ Life Orb
Ability: Mind's Eye
Level: 50
Tera Type: Normal
EVs: 252 HP / 252 SpA / 4 SpD
Quiet Nature
IVs: 0 Atk / 0 Spe
- Hyper Voice
- Earth Power
- Blood Moon
- Protect

Indeedee-F @ Sitrus Berry
Ability: Psychic Surge
Level: 50
Shiny: Yes
Tera Type: Grass
EVs: 252 HP / 252 Def / 4 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Trick Room
- Follow Me
- Helping Hand
- Shadow Ball
""",
        """
Lunala @ Power Herb
Ability: Shadow Shield
Level: 50
Tera Type: Fairy
EVs: 244 HP / 4 Def / 252 SpA / 4 SpD / 4 Spe
Modest Nature
IVs: 14 Atk
- Moongeist Beam
- Meteor Beam
- Trick Room
- Wide Guard

Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Ghost
EVs: 252 HP / 252 Atk / 4 SpD
Brave Nature
IVs: 22 SpA / 0 Spe
- Facade
- Headlong Rush
- Earthquake
- Protect

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 236 HP / 156 Def / 116 SpD
Bold Nature
IVs: 0 Atk / 26 Spe
- Pollen Puff
- Spore
- Rage Powder
- Protect

Urshifu-Rapid-Strike @ Life Orb
Ability: Unseen Fist
Level: 50
Tera Type: Fire
EVs: 108 HP / 252 Atk / 4 Def / 132 SpD / 12 Spe
Adamant Nature
IVs: 8 SpA
- Surging Strikes
- Close Combat
- Aqua Jet
- Detect

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 4 Atk / 156 Def / 100 SpD / 4 Spe
Impish Nature
- Flare Blitz
- Knock Off
- Fake Out
- Parting Shot

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 196 HP / 124 Def / 180 SpA / 4 SpD / 4 Spe
Modest Nature
IVs: 20 Atk
- Thunderclap
- Snarl
- Thunderbolt
- Dragon Pulse
""",
        """
Koraidon @ Clear Amulet
Ability: Orichalcum Pulse
Level: 50
Tera Type: Fire
EVs: 236 HP / 140 Atk / 4 Def / 4 SpD / 124 Spe
Jolly Nature
- Protect
- Collision Course
- Flame Charge
- Flare Blitz

Chi-Yu @ Choice Specs
Ability: Beads of Ruin
Level: 50
Tera Type: Ghost
EVs: 252 HP / 4 Def / 12 SpA / 4 SpD / 236 Spe
Modest Nature
IVs: 0 Atk
- Heat Wave
- Dark Pulse
- Overheat
- Snarl

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 236 HP / 156 Def / 116 SpD
Calm Nature
IVs: 0 Atk / 26 Spe
- Protect
- Sludge Bomb
- Spore
- Rage Powder

Tornadus @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 236 HP / 220 Def / 44 SpA / 4 SpD / 4 Spe
Modest Nature
IVs: 0 Atk
- Bleakwind Storm
- Icy Wind
- Sunny Day
- Tailwind

Flutter Mane @ Focus Sash
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 252 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Protect
- Moonblast
- Dazzling Gleam
- Taunt

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Water
EVs: 148 HP / 76 Def / 100 SpA / 44 SpD / 140 Spe
Modest Nature
IVs: 20 Atk
- Draco Meteor
- Thunderclap
- Weather Ball
- Electroweb
""",
    ],
    "regh": [
        ### BALTIMORE REGIONALS SEPTEMBER 2024 (11 teams) ###
        """
Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 188 HP / 164 Atk / 4 Def / 108 SpD / 44 Spe
Adamant Nature
- Fake Out
- Flare Blitz
- Knock Off
- Parting Shot

Pelipper @ Focus Sash
Ability: Drizzle
Level: 50
Tera Type: Ghost
EVs: 252 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Hurricane
- Weather Ball
- Tailwind
- Protect

Basculegion (M) @ Mystic Water
Ability: Swift Swim
Level: 50
Tera Type: Water
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Protect
- Wave Crash
- Aqua Jet
- Last Respects

Amoonguss @ Sitrus Berry
Ability: Regenerator
Tera Type: Water
EVs: 248 HP / 68 Def / 192 SpD
Sassy Nature
IVs: 0 Atk / 0 Spe
- Spore
- Rage Powder
- Pollen Puff
- Clear Smog

Maushold-Four @ Wide Lens
Ability: Technician
Level: 50
Tera Type: Grass
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Population Bomb
- Follow Me
- Taunt
- Protect

Archaludon @ Assault Vest
Ability: Stamina
Level: 50
Tera Type: Grass
EVs: 252 HP / 4 Def / 36 SpA / 196 SpD / 20 Spe
Modest Nature
IVs: 0 Atk
- Electro Shot
- Dragon Pulse
- Flash Cannon
- Body Press
""",
        """
Porygon2 @ Eviolite
Ability: Trace
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 252 HP / 140 Def / 36 SpA / 76 SpD / 4 Spe
Modest Nature
IVs: 0 Atk
- Tri Attack
- Shadow Ball
- Recover
- Trick Room

Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Fairy
EVs: 252 HP / 236 Atk / 20 SpD
Brave Nature
IVs: 2 Spe
- Facade
- Earthquake
- Headlong Rush
- Protect

Volcarona @ Covert Cloak
Ability: Flame Body
Level: 50
Tera Type: Dragon
EVs: 188 HP / 52 Def / 12 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Overheat
- Struggle Bug
- Rage Powder
- Will-O-Wisp

Grimmsnarl @ Light Clay
Ability: Prankster
Level: 50
Tera Type: Steel
EVs: 252 HP / 180 Def / 76 SpD
Careful Nature
- Spirit Break
- Reflect
- Light Screen
- Taunt

Annihilape @ Safety Goggles
Ability: Defiant
Level: 50
Tera Type: Fire
EVs: 140 HP / 68 Atk / 12 Def / 60 SpD / 228 Spe
Jolly Nature
- Rage Fist
- Drain Punch
- Protect
- Bulk Up

Gholdengo @ Choice Specs
Ability: Good as Gold
Level: 50
Tera Type: Dragon
EVs: 164 HP / 4 Def / 132 SpA / 4 SpD / 204 Spe
Modest Nature
IVs: 0 Atk
- Shadow Ball
- Make It Rain
- Power Gem
- Trick
""",
        """
Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Shiny: Yes
Tera Type: Grass
EVs: 172 HP / 116 Atk / 28 Def / 60 SpD / 132 Spe
Adamant Nature
IVs: 18 SpA
- Knock Off
- Flare Blitz
- Parting Shot
- Fake Out

Porygon2 @ Eviolite
Ability: Download
Level: 50
Shiny: Yes
Tera Type: Fighting
EVs: 252 HP / 220 Def / 4 SpA / 28 SpD / 4 Spe
Modest Nature
- Tera Blast
- Ice Beam
- Recover
- Trick Room

Amoonguss @ Mental Herb
Ability: Regenerator
Shiny: Yes
Tera Type: Water
EVs: 236 HP / 164 Def / 108 SpD
Bold Nature
IVs: 21 Atk
- Spore
- Rage Powder
- Pollen Puff
- Sludge Bomb

Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Shiny: Yes
Tera Type: Normal
EVs: 140 HP / 180 Atk / 100 Def / 84 SpD / 4 Spe
Brave Nature
IVs: 6 Spe
- Facade
- Headlong Rush
- Earthquake
- Protect

Gholdengo @ Life Orb
Ability: Good as Gold
Shiny: Yes
Tera Type: Dragon
EVs: 44 HP / 4 Def / 196 SpA / 12 SpD / 252 Spe
Timid Nature
IVs: 5 Atk
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect

Flamigo @ Focus Sash
Ability: Scrappy
Level: 70
Shiny: Yes
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
IVs: 0 SpA
- Close Combat
- Brave Bird
- Wide Guard
- Protect
""",
        """
Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 52
Tera Type: Water
EVs: 236 HP / 156 Def / 116 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Spore
- Rage Powder
- Pollen Puff
- Protect

Gholdengo @ Life Orb
Ability: Good as Gold
Level: 63
Tera Type: Dragon
EVs: 20 HP / 4 Def / 228 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect

Porygon2 @ Eviolite
Ability: Download
Level: 71
Tera Type: Fighting
EVs: 252 HP / 4 Atk / 76 Def / 4 SpA / 172 SpD
Sassy Nature
- Tera Blast
- Trick Room
- Recover
- Ice Beam

Incineroar @ Safety Goggles
Ability: Intimidate
Tera Type: Ghost
EVs: 236 HP / 44 Atk / 12 Def / 20 SpD / 196 Spe
Impish Nature
- Parting Shot
- Knock Off
- Flare Blitz
- Fake Out

Ursaluna @ Flame Orb
Ability: Guts
Level: 51
Tera Type: Ghost
EVs: 252 HP / 132 Atk / 4 Def / 92 SpD / 28 Spe
Adamant Nature
- Facade
- Headlong Rush
- Substitute
- Protect

Tyranitar @ Assault Vest
Ability: Sand Stream
Level: 55
Tera Type: Fairy
EVs: 252 HP / 156 Atk / 4 Def / 28 SpD / 68 Spe
Adamant Nature
- Low Kick
- Tera Blast
- Rock Slide
- Knock Off
""",
        """
Salamence @ Choice Specs
Ability: Intimidate
Level: 50
Tera Type: Fire
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Draco Meteor
- Air Slash
- Heat Wave
- Dragon Pulse

Electabuzz @ Eviolite
Ability: Vital Spirit
Level: 50
Tera Type: Dragon
EVs: 244 HP / 196 Def / 4 SpA / 36 SpD / 28 Spe
Calm Nature
IVs: 0 Atk
- Electroweb
- Protect
- Follow Me
- Helping Hand

Kingambit @ Black Glasses
Ability: Defiant
Level: 50
Tera Type: Dark
EVs: 252 HP / 196 Atk / 4 Def / 4 SpD / 52 Spe
Adamant Nature
- Kowtow Cleave
- Swords Dance
- Sucker Punch
- Protect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 252 HP / 116 Atk / 4 Def / 60 SpD / 76 Spe
Adamant Nature
- Fake Out
- U-turn
- Grassy Glide
- Wood Hammer

Primarina @ Life Orb
Ability: Liquid Voice
Level: 50
Tera Type: Poison
EVs: 108 HP / 68 Def / 108 SpA / 20 SpD / 204 Spe
Modest Nature
IVs: 0 Atk
- Hyper Voice
- Moonblast
- Haze
- Protect

Sneasler @ Focus Sash
Ability: Poison Touch
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Fake Out
- Close Combat
- Dire Claw
- Protect
""",
        """
Grimmsnarl @ Light Clay
Ability: Prankster
Level: 50
Tera Type: Steel
EVs: 252 HP / 116 Def / 140 SpD
Careful Nature
- Reflect
- Light Screen
- Thunder Wave
- Spirit Break

Annihilape @ Spell Tag
Ability: Defiant
Level: 50
Tera Type: Dragon
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Bulk Up
- Protect
- Drain Punch
- Rage Fist

Maushold @ Safety Goggles
Ability: Friend Guard
Level: 50
Tera Type: Ghost
EVs: 252 HP / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Beat Up
- Taunt
- Follow Me
- Protect

Pelipper @ Life Orb
Ability: Drizzle
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 0 Atk
- Hurricane
- Weather Ball
- Tailwind
- Protect

Archaludon @ Assault Vest
Ability: Stamina
Level: 50
Tera Type: Grass
EVs: 252 HP / 12 Def / 36 SpA / 196 SpD / 12 Spe
Modest Nature
IVs: 0 Atk
- Electro Shot
- Draco Meteor
- Snarl
- Body Press

Sinistcha @ Sitrus Berry
Ability: Hospitality
Level: 50
Tera Type: Water
EVs: 252 HP / 60 Def / 4 SpA / 188 SpD / 4 Spe
Calm Nature
IVs: 0 Atk
- Life Dew
- Trick Room
- Strength Sap
- Matcha Gotcha
""",
        """
Volbeat @ Coba Berry
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 252 HP / 60 Def / 196 SpD
Calm Nature
IVs: 0 Atk
- Encore
- Sunny Day
- Tailwind
- Rain Dance

Primarina @ Choice Specs
Ability: Liquid Voice
Level: 50
Tera Type: Steel
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Hyper Voice
- Weather Ball
- Dazzling Gleam
- Moonblast

Espathra @ Focus Sash
Ability: Speed Boost
Level: 50
Tera Type: Psychic
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Lumina Crash
- Expanding Force
- Dazzling Gleam

Typhlosion-Hisui @ Charcoal
Ability: Blaze
Level: 50
Tera Type: Fire
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Eruption
- Protect
- Shadow Ball
- Flamethrower

Indeedee-F @ Safety Goggles
Ability: Psychic Surge
Level: 50
Tera Type: Fairy
EVs: 252 HP / 116 Def / 4 SpA / 60 SpD / 76 Spe
Bold Nature
IVs: 0 Atk
- Follow Me
- Hyper Voice
- Trick Room
- Imprison

Archaludon @ Power Herb
Ability: Stamina
Level: 50
Tera Type: Grass
EVs: 132 SpA / 124 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Protect
- Electro Shot
- Aura Sphere
- Dragon Pulse
""",
        """
Talonflame @ Life Orb
Ability: Gale Wings
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
IVs: 18 SpA
- Tailwind
- Flare Blitz
- Protect
- Brave Bird

Annihilape @ Leftovers
Ability: Defiant
Level: 50
Tera Type: Fire
EVs: 180 HP / 116 Atk / 60 Def / 4 SpD / 148 Spe
Adamant Nature
- Rage Fist
- Drain Punch
- Bulk Up
- Protect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Grass
EVs: 252 HP / 116 Atk / 4 Def / 60 SpD / 76 Spe
Adamant Nature
- Fake Out
- Grassy Glide
- U-turn
- Wood Hammer

Primarina @ Choice Specs
Ability: Liquid Voice
Level: 50
Tera Type: Water
EVs: 164 HP / 4 Def / 196 SpA / 68 SpD / 76 Spe
Modest Nature
IVs: 14 Atk
- Moonblast
- Dazzling Gleam
- Hyper Voice
- Haze

Gholdengo @ Metal Coat
Ability: Good as Gold
Level: 50
Tera Type: Dragon
EVs: 236 HP / 28 Def / 132 SpA / 4 SpD / 108 Spe
Modest Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect

Maushold @ Safety Goggles
Ability: Friend Guard
Level: 50
Tera Type: Ghost
EVs: 212 HP / 100 Def / 196 SpD
Careful Nature
- Beat Up
- Follow Me
- Super Fang
- Protect
""",
        """
Cutter (Kingambit) @ Assault Vest
Ability: Defiant
Level: 50
Tera Type: Fire
EVs: 204 HP / 212 Atk / 4 Def / 52 SpD / 36 Spe
Adamant Nature
- Kowtow Cleave
- Iron Head
- Sucker Punch
- Low Kick

Curveball (Rillaboom) @ Miracle Seed
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 4 HP / 156 Atk / 20 Def / 124 SpD / 204 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- U-turn
- Fake Out

Knuckleball (Electabuzz) @ Eviolite
Ability: Vital Spirit
Level: 50
Tera Type: Dark
EVs: 236 HP / 196 Def / 4 SpA / 4 SpD / 68 Spe
Bold Nature
IVs: 0 Atk
- Thunderbolt
- Follow Me
- Taunt
- Protect

Fastball (Blaziken) @ Focus Sash
Ability: Speed Boost
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Close Combat
- Flare Blitz
- Coaching
- Protect

Splitter (Dragapult) @ Choice Band
Ability: Clear Body
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Dragon Darts
- Phantom Force
- Tera Blast
- U-turn

Slider (Primarina) @ Sitrus Berry
Ability: Liquid Voice
Level: 50
Tera Type: Steel
EVs: 164 HP / 108 Def / 188 SpA / 4 SpD / 44 Spe
Modest Nature
IVs: 0 Atk
- Hyper Voice
- Moonblast
- Haze
- Protect
""",
        """
Lilligant-Hisui @ Focus Sash
Ability: Chlorophyll
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Triple Axel
- After You
- Close Combat
- Sleep Powder

Hatterene @ Covert Cloak
Ability: Magic Bounce
Level: 50
Tera Type: Fire
EVs: 252 HP / 252 SpA / 4 SpD
Quiet Nature
IVs: 0 Spe
- Dazzling Gleam
- Expanding Force
- Trick Room
- Mystical Fire

Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Ghost
EVs: 252 HP / 252 Atk / 4 SpD
Brave Nature
IVs: 4 Spe
- Facade
- Headlong Rush
- Earthquake
- Protect

Indeedee-F @ Psychic Seed
Ability: Psychic Surge
Level: 50
Tera Type: Dragon
EVs: 252 HP / 252 Def / 4 SpD
Relaxed Nature
- Psychic
- Trick Room
- Helping Hand
- Follow Me

Torkoal @ Flame Plate
Ability: Drought
Level: 50
Tera Type: Fire
EVs: 252 HP / 252 SpA / 4 SpD
Quiet Nature
IVs: 0 Spe
- Eruption
- Weather Ball
- Heat Wave
- Protect

Gallade @ Clear Amulet
Ability: Sharpness
Level: 50
Tera Type: Grass
EVs: 180 HP / 252 Atk / 36 Def / 36 Spe
Adamant Nature
- Psycho Cut
- Sacred Sword
- Trick Room
- Wide Guard
""",
        """
Torkoal @ Charcoal
Ability: Drought
Level: 50
Tera Type: Fire
EVs: 252 HP / 252 SpA / 4 SpD
Quiet Nature
IVs: 0 Atk / 0 Spe
- Eruption
- Body Press
- Weather Ball
- Protect

Indeedee-F @ Psychic Seed
Ability: Psychic Surge
Level: 50
Tera Type: Grass
EVs: 252 HP / 252 Def / 4 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Psychic
- Follow Me
- Helping Hand
- Trick Room

Delphox @ Life Orb
Ability: Blaze
Level: 50
Tera Type: Fighting
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Expanding Force
- Heat Wave
- Tera Blast
- Protect

Gallade @ Clear Amulet
Ability: Sharpness
Level: 50
Tera Type: Grass
EVs: 252 HP / 252 Atk / 4 Def
Adamant Nature
IVs: 28 SpA
- Psycho Cut
- Sacred Sword
- Wide Guard
- Trick Room

Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Ghost
EVs: 252 HP / 252 Atk / 4 Def
Brave Nature
IVs: 14 SpA / 0 Spe
- Facade
- Earthquake
- Headlong Rush
- Protect

Lilligant-Hisui @ Focus Sash
Ability: Chlorophyll
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Leaf Blade
- Close Combat
- After You
- Sleep Powder
""",
        ### JOINVILLE REGIONALS SEPTEMBER 2024 (1 team) ###
        """
Garchomp @ Choice Band
Ability: Rough Skin
Level: 50
Tera Type: Steel
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Rock Slide
- Stomping Tantrum
- Dragon Claw
- Earthquake

Dragonite @ Lum Berry
Ability: Multiscale
Level: 50
Tera Type: Flying
EVs: 188 HP / 252 Atk / 4 Def / 4 SpD / 60 Spe
Adamant Nature
- Protect
- Extreme Speed
- Low Kick
- Tera Blast

Kingambit @ Assault Vest
Ability: Defiant
Level: 50
Tera Type: Dark
EVs: 188 HP / 196 Atk / 4 Def / 4 SpD / 116 Spe
Adamant Nature
- Kowtow Cleave
- Iron Head
- Sucker Punch
- Low Kick

Ninetales-Alola @ Choice Specs
Ability: Snow Warning
Level: 50
Tera Type: Ice
EVs: 100 HP / 132 Def / 164 SpA / 4 SpD / 108 Spe
Timid Nature
IVs: 0 Atk
- Blizzard
- Moonblast
- Freeze-Dry
- Ice Beam

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 252 HP / 68 Atk / 188 SpD
Adamant Nature
IVs: 13 Spe
- Parting Shot
- Flare Blitz
- Knock Off
- Fake Out

Amoonguss @ Sitrus Berry
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 244 HP / 156 Def / 108 SpD
Bold Nature
IVs: 0 Atk / 27 Spe
- Spore
- Rage Powder
- Pollen Puff
- Clear Smog
""",
        ### DORTMUND REGIONALS SEPTEMBER 2024 (2 teams) ###
        """
Indeedee @ Focus Sash
Ability: Psychic Surge
Level: 50
Tera Type: Ground
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Expanding Force
- Tera Blast
- Imprison
- Trick Room

Drifblim (M) @ Psychic Seed
Ability: Unburden
Level: 50
Tera Type: Grass
EVs: 180 Def / 172 SpD / 156 Spe
Jolly Nature
IVs: 30 SpA
- Acrobatics
- Will-O-Wisp
- Strength Sap
- Tailwind

Volcarona (F) @ Life Orb
Ability: Flame Body
Level: 50
Tera Type: Fairy
EVs: 132 HP / 4 Def / 116 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Bug Buzz
- Heat Wave
- Tera Blast
- Protect

Kommo-o (M) @ Leftovers
Ability: Soundproof
Level: 50
Tera Type: Fire
EVs: 252 HP / 116 Def / 4 SpA / 92 SpD / 44 Spe
Bold Nature
- Body Press
- Flamethrower
- Iron Defense
- Protect

Toxtricity (M) @ Choice Specs
Ability: Punk Rock
Level: 50
Tera Type: Normal
EVs: 44 HP / 4 Def / 252 SpA / 4 SpD / 204 Spe
Timid Nature
- Overdrive
- Sludge Bomb
- Boomburst
- Volt Switch

Hydreigon (M) @ Assault Vest
Ability: Levitate
Level: 50
Tera Type: Ghost
EVs: 124 HP / 4 Def / 116 SpA / 12 SpD / 252 Spe
Modest Nature
- Dark Pulse
- Draco Meteor
- Earth Power
- Snarl
""",
        """
Magmar @ Eviolite
Ability: Vital Spirit
Level: 50
Tera Type: Ghost
EVs: 244 HP / 252 Def / 4 SpA / 4 SpD / 4 Spe
Bold Nature
IVs: 24 Atk
- Will-O-Wisp
- Overheat
- Follow Me
- Protect

Salamence @ Choice Specs
Ability: Intimidate
Level: 50
Tera Type: Fire
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 6 Atk
- Dragon Pulse
- Draco Meteor
- Heat Wave
- Air Slash

Primarina @ Sitrus Berry
Ability: Liquid Voice
Level: 50
Tera Type: Poison
EVs: 180 HP / 76 Def / 188 SpA / 4 SpD / 60 Spe
Modest Nature
IVs: 20 Atk
- Moonblast
- Hyper Voice
- Haze
- Protect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 220 HP / 196 Atk / 4 Def / 12 SpD / 76 Spe
Adamant Nature
- Wood Hammer
- U-turn
- Grassy Glide
- Fake Out

Sneasler @ Focus Sash
Ability: Poison Touch
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Close Combat
- Protect
- Fake Out
- Dire Claw

Kingambit @ Black Glasses
Ability: Defiant
Level: 50
Tera Type: Dark
EVs: 220 HP / 212 Atk / 4 Def / 4 SpD / 68 Spe
Adamant Nature
- Kowtow Cleave
- Swords Dance
- Sucker Punch
- Protect
""",
        ### LOUISVILLE REGIONALS OCTOBER 2024 (14 teams) ###
        """
Porygon2 @ Eviolite
Ability: Download
Level: 50
Tera Type: Ground
EVs: 252 HP / 4 Atk / 100 Def / 116 SpA / 36 SpD
Quiet Nature
- Tera Blast
- Ice Beam
- Recover
- Trick Room

Sneasler @ Focus Sash
Ability: Poison Touch
Level: 50
Tera Type: Flying
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Close Combat
- Dire Claw
- Coaching
- Protect

Gholdengo @ Life Orb
Ability: Good as Gold
Level: 50
Tera Type: Water
EVs: 212 HP / 148 Def / 132 SpA / 12 SpD
Modest Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect

Amoonguss @ Sitrus Berry
Ability: Regenerator
Level: 50
Tera Type: Fairy
EVs: 244 HP / 156 Def / 108 SpD
Bold Nature
IVs: 0 Atk
- Pollen Puff
- Spore
- Rage Powder
- Protect

Garchomp @ Clear Amulet
Ability: Rough Skin
Level: 50
Tera Type: Fire
EVs: 44 HP / 204 Atk / 4 Def / 4 SpD / 252 Spe
Jolly Nature
- Earthquake
- Stomping Tantrum
- Dragon Claw
- Protect

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 252 HP / 36 Atk / 76 Def / 140 SpD
Brave Nature
IVs: 29 Spe
- Flare Blitz
- Knock Off
- Fake Out
- Parting Shot
""",
        """
Rillaboom (F) @ Miracle Seed
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 236 HP / 196 Atk / 4 Def / 52 SpD / 20 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- Fake Out
- High Horsepower

Kingambit (M) @ Assault Vest
Ability: Defiant
Level: 50
Tera Type: Flying
EVs: 252 HP / 244 Atk / 4 Def / 4 SpD / 4 Spe
Adamant Nature
- Kowtow Cleave
- Sucker Punch
- Tera Blast
- Iron Head

Sneasler (F) @ Focus Sash
Ability: Unburden
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Dire Claw
- Close Combat
- Coaching
- Fake Out

Dragonite @ Loaded Dice
Ability: Multiscale
Level: 50
Tera Type: Fairy
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Extreme Speed
- Scale Shot
- Low Kick
- Protect

Gastrodon @ Sitrus Berry
Ability: Storm Drain
Level: 50
Tera Type: Poison
EVs: 252 HP / 116 Def / 60 SpA / 76 SpD / 4 Spe
Modest Nature
IVs: 0 Atk
- Earth Power
- Ice Beam
- Clear Smog
- Protect

Ceruledge @ Leftovers
Ability: Flash Fire
Level: 50
Tera Type: Grass
EVs: 252 HP / 116 Atk / 52 Def / 76 SpD / 12 Spe
Adamant Nature
- Bitter Blade
- Shadow Sneak
- Bulk Up
- Protect
""",
        """
WrathofKhan (Kingambit) (F) @ Black Glasses
Ability: Defiant
Level: 50
Shiny: Yes
Tera Type: Dark
EVs: 252 HP / 196 Atk / 4 Def / 20 SpD / 36 Spe
Adamant Nature
- Protect
- Kowtow Cleave
- Sucker Punch
- Swords Dance

Trunkmeister (Rillaboom) (F) @ Assault Vest
Ability: Grassy Surge
Level: 50
Shiny: Yes
Tera Type: Fire
EVs: 252 HP / 140 Atk / 4 Def / 52 SpD / 60 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- U-turn
- Fake Out

Litofsky (Electabuzz) (M) @ Eviolite
Ability: Vital Spirit
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 244 HP / 228 Def / 4 SpA / 4 SpD / 28 Spe
Bold Nature
IVs: 0 Atk
- Protect
- Thunderbolt
- Helping Hand
- Follow Me

Pultimore (Dragapult) (M) @ Choice Specs
Ability: Clear Body
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
- Draco Meteor
- Shadow Ball
- Fire Blast
- U-turn

Heimlich (Volcarona) (M) @ Covert Cloak
Ability: Flame Body
Level: 50
Shiny: Yes
Tera Type: Dragon
EVs: 252 HP / 60 Def / 52 SpA / 4 SpD / 140 Spe
Modest Nature
IVs: 0 Atk
- Protect
- Heat Wave
- Giga Drain
- Quiver Dance

Bull CRIT!! (Tauros-Paldea-Aqua) @ Mirror Herb
Ability: Intimidate
Level: 50
Tera Type: Water
EVs: 92 HP / 156 Atk / 4 Def / 4 SpD / 252 Spe
Adamant Nature
- Protect
- Wave Crash
- Close Combat
- Aqua Jet
""",
        """
Ninetales-Alola @ Choice Specs
Ability: Snow Warning
Level: 50
Tera Type: Ice
EVs: 4 HP / 76 Def / 196 SpA / 4 SpD / 228 Spe
Timid Nature
- Moonblast
- Aurora Veil
- Freeze-Dry
- Blizzard

Volcarona @ Sitrus Berry
Ability: Flame Body
Level: 50
Tera Type: Fairy
EVs: 252 HP / 140 Def / 36 SpA / 4 SpD / 76 Spe
Modest Nature
IVs: 10 Atk
- Heat Wave
- Will-O-Wisp
- Rage Powder
- Tailwind

Kingambit @ Safety Goggles
Ability: Defiant
Level: 50
Tera Type: Dark
EVs: 252 HP / 196 Atk / 4 Def / 4 SpD / 52 Spe
Adamant Nature
- Sucker Punch
- Kowtow Cleave
- Swords Dance
- Protect

Sneasler @ Focus Sash
Ability: Poison Touch
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Dire Claw
- Close Combat
- Fake Out
- Protect

Kommo-o @ Throat Spray
Ability: Soundproof
Level: 50
Tera Type: Fire
EVs: 204 HP / 4 Def / 92 SpA / 4 SpD / 204 Spe
Timid Nature
IVs: 24 Atk
- Clanging Scales
- Flamethrower
- Clangorous Soul
- Protect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 172 HP / 116 Atk / 4 Def / 12 SpD / 204 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- Fake Out
- High Horsepower
""",
        """
Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Ghost
EVs: 140 HP / 252 Atk / 4 Def / 92 SpD / 20 Spe
Adamant Nature
- Headlong Rush
- Facade
- Helping Hand
- Protect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Electric
EVs: 204 HP / 116 Atk / 4 Def / 108 SpD / 76 Spe
Adamant Nature
- Wood Hammer
- Fake Out
- Grassy Glide
- Grass Pledge

Dragapult @ Choice Band
Ability: Clear Body
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Dragon Darts
- Phantom Force
- U-turn
- Tera Blast

Empoleon @ Leftovers
Ability: Competitive
Level: 50
Tera Type: Grass
EVs: 236 HP / 4 Def / 148 SpA / 84 SpD / 36 Spe
Modest Nature
IVs: 0 Atk
- Water Pledge
- Ice Beam
- Yawn
- Protect

Porygon2 @ Eviolite
Ability: Download
Level: 50
Tera Type: Fighting
EVs: 252 HP / 12 Atk / 140 Def / 68 SpA / 36 SpD
Quiet Nature
- Tera Blast
- Ice Beam
- Recover
- Trick Room

Blaziken @ Focus Sash
Ability: Speed Boost
Tera Type: Fighting
EVs: 252 Atk / 4 SpA / 252 Spe
Lonely Nature
- Close Combat
- Fire Pledge
- Upper Hand
- Detect
""",
        """
Amoonguss @ Sitrus Berry
Ability: Regenerator
Shiny: Yes
Tera Type: Fairy
EVs: 244 HP / 92 Def / 4 SpA / 156 SpD / 12 Spe
Calm Nature
IVs: 0 Atk
- Protect
- Pollen Puff
- Spore
- Rage Powder

Incineroar @ Rocky Helmet
Ability: Intimidate
Tera Type: Grass
EVs: 236 HP / 36 Atk / 60 Def / 172 SpD / 4 Spe
Adamant Nature
- Fake Out
- Flare Blitz
- Knock Off
- Parting Shot

Kingambit @ Safety Goggles
Ability: Defiant
Shiny: Yes
Tera Type: Dark
EVs: 204 HP / 196 Atk / 12 Def / 4 SpD / 92 Spe
Adamant Nature
- Kowtow Cleave
- Sucker Punch
- Swords Dance
- Protect

Ninetales-Alola @ Choice Specs
Ability: Snow Warning
Shiny: Yes
Tera Type: Ice
EVs: 100 HP / 76 Def / 76 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Blizzard
- Dazzling Gleam
- Freeze-Dry
- Moonblast

Garchomp @ Choice Band
Ability: Rough Skin
Shiny: Yes
Tera Type: Steel
EVs: 100 HP / 124 Atk / 28 Def / 4 SpD / 252 Spe
Jolly Nature
- Dragon Claw
- Earthquake
- Stomping Tantrum
- Rock Slide

Dragonite @ Assault Vest
Ability: Multiscale
Tera Type: Flying
EVs: 220 HP / 132 Atk / 36 Def / 4 SpD / 116 Spe
Adamant Nature
- Tera Blast
- Extreme Speed
- Ice Spinner
- Low Kick
""",
        """
Basculegion @ Choice Scarf
Ability: Adaptability
Level: 50
Tera Type: Grass
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Wave Crash
- Aqua Jet
- Flip Turn
- Last Respects

Pelipper @ Focus Sash
Ability: Drizzle
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 8 Atk
- Weather Ball
- Hurricane
- Tailwind
- Protect

Archaludon @ Assault Vest
Ability: Stamina
Level: 50
Tera Type: Grass
EVs: 244 HP / 12 Def / 52 SpA / 140 SpD
Modest Nature
IVs: 0 Atk
- Flash Cannon
- Body Press
- Electro Shot
- Dragon Pulse

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Fairy
EVs: 236 HP / 156 Def / 116 SpD
Bold Nature
IVs: 24 Spe
- Spore
- Rage Powder
- Pollen Puff
- Protect

Gholdengo @ Life Orb
Ability: Good as Gold
Level: 50
Tera Type: Flying
EVs: 52 HP / 20 Def / 180 SpA / 4 SpD / 252 Spe
Timid Nature
- Make It Rain
- Shadow Ball
- Protect
- Nasty Plot

Ninetales-Alola @ Light Clay
Ability: Snow Warning
Level: 50
Tera Type: Water
EVs: 84 HP / 12 Def / 156 SpA / 252 Spe
Timid Nature
- Icy Wind
- Blizzard
- Aurora Veil
- Protect
""",
        """
Whimsicott @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Water
EVs: 204 HP / 4 Def / 148 SpA / 4 SpD / 148 Spe
Timid Nature
- Tailwind
- Encore
- Sunny Day
- Moonblast

Primarina @ Sitrus Berry
Ability: Liquid Voice
Level: 50
Tera Type: Poison
EVs: 244 HP / 92 Def / 108 SpA / 4 SpD / 60 Spe
Modest Nature
IVs: 18 Atk
- Hyper Voice
- Moonblast
- Haze
- Protect

Sneasler @ Psychic Seed
Ability: Unburden
Level: 50
Tera Type: Dark
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Dire Claw
- Close Combat
- Throat Chop
- Protect

Indeedee @ Focus Sash
Ability: Psychic Surge
Level: 50
Tera Type: Fighting
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Expanding Force
- Tera Blast
- Protect
- Trick Room

Ursaluna-Bloodmoon @ Life Orb
Ability: Mind's Eye
Level: 50
Tera Type: Normal
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 14 Atk
- Blood Moon
- Earth Power
- Hyper Voice
- Protect

Arcanine-Hisui @ Choice Band
Ability: Intimidate
Level: 50
Tera Type: Grass
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
IVs: 20 SpA
- Flare Blitz
- Extreme Speed
- Close Combat
- Rock Slide
""",
        """
Archaludon @ Power Herb
Ability: Sturdy
Level: 50
Tera Type: Stellar
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 28 Atk
- Draco Meteor
- Flash Cannon
- Electro Shot
- Protect

Glimmora @ Focus Sash
Ability: Toxic Debris
Level: 50
Tera Type: Grass
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 12 Atk
- Power Gem
- Sludge Wave
- Earth Power
- Spiky Shield

Dondozo @ Leftovers
Ability: Unaware
Level: 50
Tera Type: Fire
EVs: 244 HP / 4 Atk / 68 Def / 188 SpD / 4 Spe
Impish Nature
IVs: 0 SpA
- Wave Crash
- Fissure
- Yawn
- Protect

Kingambit @ Safety Goggles
Ability: Defiant
Level: 50
Tera Type: Dark
EVs: 204 HP / 196 Atk / 4 Def / 52 SpD / 52 Spe
Adamant Nature
IVs: 28 SpA
- Assurance
- Sucker Punch
- Low Kick
- Protect

Dragonite @ Assault Vest
Ability: Multiscale
Level: 50
Tera Type: Flying
EVs: 92 HP / 252 Atk / 4 Def / 4 SpD / 156 Spe
Adamant Nature
IVs: 8 SpA
- Tera Blast
- Extreme Speed
- Ice Spinner
- Stomping Tantrum

Annihilape @ Choice Scarf
Ability: Defiant
Level: 50
Tera Type: Grass
EVs: 172 HP / 76 Atk / 4 Def / 4 SpD / 252 Spe
Jolly Nature
- Final Gambit
- Close Combat
- Coaching
- Shadow Claw
""",
        """
FASTLANE (Drifblim) @ Psychic Seed
Ability: Unburden
Level: 50
Tera Type: Grass
EVs: 4 HP / 244 Atk / 68 Def / 28 SpD / 164 Spe
Jolly Nature
- Acrobatics
- Will-O-Wisp
- Sunny Day
- Tailwind

GEEDORAH (Hydreigon) @ Assault Vest
Ability: Levitate
Level: 50
Tera Type: Poison
EVs: 112 HP / 40 Def / 196 SpA / 12 SpD / 148 Spe
Modest Nature
IVs: 0 Atk
- Dark Pulse
- Draco Meteor
- Earth Power
- Snarl

CROSSHAIRS (Indeedee) @ Focus Sash
Ability: Psychic Surge
Level: 50
Tera Type: Fighting
EVs: 252 SpA / 4 SpD / 252 Spe
Modest Nature
- Expanding Force
- Tera Blast
- Imprison
- Trick Room

CZARFACE (Sneasler) @ White Herb
Ability: Unburden
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Dire Claw
- Close Combat
- Throat Chop
- Protect

FAZERS (Dragapult) @ Choice Band
Ability: Clear Body
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Dragon Darts
- Phantom Force
- Tera Blast
- U-turn

VENOMOUS (Volcarona) @ Rocky Helmet
Ability: Flame Body
Level: 50
Tera Type: Fairy
EVs: 148 HP / 252 Def / 36 SpA / 4 SpD / 68 Spe
Bold Nature
IVs: 0 Atk
- Overheat
- Rage Powder
- Protect
- Bug Buzz
""",
        """
Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 236 HP / 196 Atk / 4 Def / 12 SpD / 60 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- High Horsepower
- Fake Out

Primarina @ Life Orb
Ability: Liquid Voice
Level: 50
Tera Type: Water
EVs: 108 HP / 68 Def / 108 SpA / 20 SpD / 204 Spe
Modest Nature
IVs: 14 Atk
- Haze
- Hyper Voice
- Moonblast
- Protect

Electabuzz @ Eviolite
Ability: Vital Spirit
Level: 50
Tera Type: Fairy
EVs: 252 HP / 116 Def / 4 SpA / 20 SpD / 116 Spe
Timid Nature
IVs: 14 Atk
- Electroweb
- Taunt
- Protect
- Follow Me

Dragonite @ Loaded Dice
Ability: Multiscale
Level: 50
Tera Type: Flying
EVs: 20 HP / 252 Atk / 236 Spe
Adamant Nature
- Scale Shot
- Tera Blast
- Extreme Speed
- Protect

Kingambit @ Black Glasses
Ability: Defiant
Level: 50
Tera Type: Dark
EVs: 252 HP / 196 Atk / 4 Def / 4 SpD / 52 Spe
Adamant Nature
IVs: 22 SpA
- Kowtow Cleave
- Protect
- Swords Dance
- Sucker Punch

Sneasler @ Focus Sash
Ability: Poison Touch
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
IVs: 10 SpA
- Dire Claw
- Close Combat
- Coaching
- Fake Out
""",
        """
Sneasler @ Covert Cloak
Ability: Poison Touch
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Dire Claw
- Close Combat
- Fake Out
- Protect

Primarina @ Throat Spray
Ability: Liquid Voice
Level: 50
Tera Type: Steel
EVs: 252 HP / 84 Def / 164 SpA / 4 SpD / 4 Spe
Modest Nature
IVs: 0 Atk
- Protect
- Moonblast
- Hyper Voice
- Haze

Garchomp @ Life Orb
Ability: Rough Skin
Level: 50
Tera Type: Fire
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Protect
- Stomping Tantrum
- Dragon Claw
- Earthquake

Vivillon @ Focus Sash
Ability: Compound Eyes
Level: 50
Tera Type: Ghost
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
- Protect
- Hurricane
- Rage Powder
- Sleep Powder

Porygon2 @ Eviolite
Ability: Download
Level: 50
Tera Type: Fighting
EVs: 252 HP / 196 Def / 60 SpD
Modest Nature
- Tera Blast
- Ice Beam
- Recover
- Trick Room

Gholdengo @ Metal Coat
Ability: Good as Gold
Level: 50
Tera Type: Dragon
EVs: 100 HP / 4 Def / 252 SpA / 4 SpD / 148 Spe
Modest Nature
- Protect
- Make It Rain
- Shadow Ball
- Nasty Plot
""",
        """
Cold Brew (Ninetales-Alola) @ Choice Specs
Ability: Snow Warning
Level: 50
Tera Type: Ice
EVs: 68 HP / 76 Def / 108 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Blizzard
- Moonblast
- Freeze-Dry
- Icy Wind

Mocha (Garchomp) @ Life Orb
Ability: Rough Skin
Level: 50
Tera Type: Steel
EVs: 4 HP / 236 Atk / 4 Def / 12 SpD / 252 Spe
Jolly Nature
- Stomping Tantrum
- Earthquake
- Dragon Claw
- Protect

Latte (Dragonite) @ Lum Berry
Ability: Multiscale
Level: 50
Tera Type: Flying
EVs: 60 HP / 204 Atk / 4 Def / 4 SpD / 236 Spe
Adamant Nature
- Tera Blast
- Extreme Speed
- Low Kick
- Protect

Cappuccino (Sneasler) @ Focus Sash
Ability: Poison Touch
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Dire Claw
- Close Combat
- Coaching
- Fake Out

Macchiato (Kingambit) @ Assault Vest
Ability: Defiant
Level: 50
Tera Type: Water
EVs: 188 HP / 204 Atk / 4 Def / 36 SpD / 76 Spe
Adamant Nature
- Kowtow Cleave
- Iron Head
- Sucker Punch
- Low Kick

Espresso (Amoonguss) @ Covert Cloak
Ability: Regenerator
Level: 50
Tera Type: Fairy
EVs: 228 HP / 220 Def / 60 SpD
Bold Nature
IVs: 0 Atk / 27 Spe
- Pollen Puff
- Clear Smog
- Rage Powder
- Spore
""",
        """
Porygon2 @ Eviolite
Ability: Download
Level: 50
Tera Type: Fighting
EVs: 252 HP / 20 Def / 196 SpA / 4 SpD / 36 Spe
Modest Nature
- Trick Room
- Recover
- Tera Blast
- Ice Beam

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Water
EVs: 244 HP / 36 Atk / 156 Def / 60 SpD / 12 Spe
Adamant Nature
- Fake Out
- Flare Blitz
- Knock Off
- Parting Shot

Amoonguss @ Sitrus Berry
Ability: Regenerator
Level: 50
Tera Type: Fairy
EVs: 236 HP / 180 Def / 92 SpD
Bold Nature
IVs: 0 Atk
- Protect
- Spore
- Rage Powder
- Pollen Puff

Ninetales-Alola @ Choice Specs
Ability: Snow Warning
Level: 50
Tera Type: Fire
EVs: 20 HP / 4 Def / 252 SpA / 4 SpD / 228 Spe
Timid Nature
IVs: 0 Atk
- Blizzard
- Freeze-Dry
- Moonblast
- Tera Blast

Vivillon @ Focus Sash
Ability: Compound Eyes
Level: 50
Tera Type: Ghost
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
- Protect
- Sleep Powder
- Tailwind
- Hurricane

Garchomp @ Life Orb
Ability: Rough Skin
Level: 50
Tera Type: Steel
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
IVs: 6 SpA
- Protect
- Earthquake
- Stomping Tantrum
- Dragon Claw
""",
        ### THAILAND PREMIER BALL LEAGUE OCTOBER 2024 (1 team) ###
        """
Annihilape (M) @ Safety Goggles
Ability: Defiant
Level: 50
Shiny: Yes
Tera Type: Water
EVs: 252 HP / 4 Atk / 252 Spe
Jolly Nature
- Rage Fist
- Drain Punch
- Bulk Up
- Protect

Ninetales-Alola (F) @ Covert Cloak
Ability: Snow Warning
Level: 50
Shiny: Yes
Tera Type: Ice
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
- Blizzard
- Freeze-Dry
- Aurora Veil
- Protect

Talonflame @ Sharp Beak
Ability: Gale Wings
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Dual Wingbeat
- Tailwind
- Will-O-Wisp
- Protect

Garchomp (M) @ Life Orb
Ability: Rough Skin
Level: 50
Tera Type: Steel
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Earthquake
- Stomping Tantrum
- Dragon Claw
- Protect

Vivillon-Ocean (F) @ Focus Sash
Ability: Compound Eyes
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
- Sleep Powder
- Hurricane
- Rage Powder
- Protect

Gholdengo @ Iron Plate
Ability: Good as Gold
Level: 50
Tera Type: Steel
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect
""",
        ### LILLE REGIONALS OCTOBER 2024 (4 teams) ###
        """
Baxcalibur (F) @ Loaded Dice
Ability: Thermal Exchange
Level: 50
Tera Type: Ghost
EVs: 12 HP / 252 Atk / 12 Def / 28 SpD / 204 Spe
Adamant Nature
- Protect
- Icicle Spear
- Scale Shot
- Ice Shard

Dondozo (M) @ Leftovers
Ability: Unaware
Level: 52
Tera Type: Bug
EVs: 244 HP / 64 Def / 196 SpD / 4 Spe
Careful Nature
- Protect
- Liquidation
- Yawn
- Fissure

Kingambit (M) @ Safety Goggles
Ability: Defiant
Level: 64
Tera Type: Dark
EVs: 132 HP / 212 Atk / 12 Def / 36 SpD / 116 Spe
Adamant Nature
- Protect
- Kowtow Cleave
- Sucker Punch
- Swords Dance

Rillaboom (M) @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Water
EVs: 196 HP / 116 Atk / 12 Def / 156 SpD / 28 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- Fake Out
- High Horsepower

Sneasler (F) @ Focus Sash
Ability: Unburden
Level: 60
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
IVs: 29 SpA
- Protect
- Close Combat
- Dire Claw
- Coaching

Volcarona (M) @ Covert Cloak
Ability: Flame Body
Level: 50
Tera Type: Fairy
EVs: 252 HP / 108 Def / 36 SpA / 4 SpD / 108 Spe
Modest Nature
IVs: 5 Atk
- Heat Wave
- Tera Blast
- Quiver Dance
- Rage Powder
""",
        """
Dragonite (M) @ Loaded Dice
Ability: Multiscale
Level: 50
Tera Type: Fairy
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
IVs: 0 SpA
- Scale Shot
- Extreme Speed
- Haze
- Protect

Volcarona (F) @ Covert Cloak
Ability: Flame Body
Level: 50
Tera Type: Fairy
EVs: 132 HP / 20 Def / 164 SpA / 4 SpD / 188 Spe
Timid Nature
- Heat Wave
- Tera Blast
- Quiver Dance
- Protect

Sneasler (M) @ Focus Sash
Ability: Unburden
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Close Combat
- Dire Claw
- Coaching
- Protect

Rillaboom (M) @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Water
EVs: 204 HP / 196 Atk / 4 Def / 4 SpD / 100 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- High Horsepower
- Fake Out

Electabuzz (M) @ Eviolite
Ability: Vital Spirit
Level: 50
Tera Type: Ghost
EVs: 244 HP / 180 Def / 4 SpA / 20 SpD / 60 Spe
Bold Nature
IVs: 0 Atk
- Thunderbolt
- Follow Me
- Taunt
- Protect

Kingambit (M) @ Black Glasses
Ability: Defiant
Level: 50
Shiny: Yes
Tera Type: Dark
EVs: 252 HP / 220 Atk / 4 Def / 4 SpD / 28 Spe
Adamant Nature
- Kowtow Cleave
- Sucker Punch
- Swords Dance
- Protect
""",
        """
Clefable @ Sitrus Berry
Ability: Unaware
Level: 50
Tera Type: Water
EVs: 252 HP / 172 Def / 4 SpA / 36 SpD / 44 Spe
Bold Nature
IVs: 10 Atk
- Follow Me
- Moonblast
- Misty Terrain
- Protect

Garchomp @ Life Orb
Ability: Rough Skin
Level: 50
Tera Type: Ground
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
IVs: 28 SpA
- Stomping Tantrum
- Dragon Claw
- Earthquake
- Protect

Whimsicott @ Focus Sash
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Encore
- Tailwind
- Sunny Day

Hydreigon @ Choice Specs
Ability: Levitate
Level: 50
Tera Type: Fire
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Dark Pulse
- Draco Meteor
- Snarl
- Heat Wave

Annihilape @ Leftovers
Ability: Defiant
Level: 50
Tera Type: Water
EVs: 180 HP / 84 Atk / 4 Def / 20 SpD / 220 Spe
Adamant Nature
IVs: 2 SpA
- Rage Fist
- Drain Punch
- Bulk Up
- Protect

Gholdengo @ Iron Plate
Ability: Good as Gold
Level: 50
Tera Type: Steel
EVs: 116 HP / 4 Def / 132 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect
""",
        """
Gothitelle @ Sitrus Berry
Ability: Shadow Tag
Level: 50
Tera Type: Water
EVs: 244 HP / 92 Def / 4 SpA / 156 SpD / 12 Spe
Calm Nature
- Psychic Noise
- Protect
- Trick Room
- Fake Out

Primarina @ Throat Spray
Ability: Liquid Voice
Level: 50
Tera Type: Dragon
EVs: 212 HP / 68 Def / 188 SpA / 4 SpD / 36 Spe
Modest Nature
IVs: 0 Atk
- Hyper Voice
- Moonblast
- Protect
- Perish Song

Ursaluna-Bloodmoon @ Life Orb
Ability: Mind's Eye
Level: 50
Tera Type: Normal
EVs: 36 HP / 4 Def / 252 SpA / 196 SpD / 20 Spe
Modest Nature
IVs: 28 Atk
- Hyper Voice
- Earth Power
- Blood Moon
- Protect

Gholdengo @ Choice Specs
Ability: Good as Gold
Level: 50
Tera Type: Steel
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 2 Atk
- Make It Rain
- Shadow Ball
- Thunderbolt
- Power Gem

Talonflame @ Covert Cloak
Ability: Gale Wings
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
IVs: 6 SpA
- Dual Wingbeat
- Flare Blitz
- Tailwind
- Taunt

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 204 HP / 116 Atk / 52 Def / 20 SpD / 116 Spe
Adamant Nature
IVs: 0 SpA
- Grassy Glide
- Wood Hammer
- Fake Out
- High Horsepower
""",
        ### PHILIPPINES PREMIER BALL LEAGUE OCTOBER 2024 (1 team) ###
        """
Primarina @ Life Orb
Ability: Liquid Voice
Level: 50
Shiny: Yes
Tera Type: Steel
EVs: 108 HP / 52 Def / 188 SpA / 20 SpD / 140 Spe
Modest Nature
IVs: 0 Atk
- Water Pledge
- Hyper Voice
- Moonblast
- Protect

Sylveon @ Choice Specs
Ability: Pixilate
Level: 50
Tera Type: Ghost
EVs: 4 HP / 116 Def / 252 SpA / 4 SpD / 132 Spe
Modest Nature
IVs: 0 Atk
- Hyper Voice
- Shadow Ball
- Hyper Beam
- Psychic

Indeedee @ Safety Goggles
Ability: Psychic Surge
Level: 50
Shiny: Yes
Tera Type: Fire
EVs: 156 HP / 124 Def / 116 SpA / 4 SpD / 108 Spe
Modest Nature
IVs: 0 Atk
- Expanding Force
- Tera Blast
- Trick Room
- Imprison

Meowscarada @ Focus Sash
Ability: Overgrow
Level: 50
Shiny: Yes
Tera Type: Fairy
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Knock Off
- Flower Trick
- Protect
- Grass Pledge

Sneasler @ Psychic Seed
Ability: Unburden
Level: 50
Shiny: Yes
Tera Type: Grass
EVs: 60 HP / 252 Atk / 4 Def / 4 SpD / 188 Spe
Jolly Nature
- Dire Claw
- Acrobatics
- Close Combat
- Protect

Decidueye-Hisui @ Razor Claw
Ability: Scrappy
Level: 50
Shiny: Yes
Tera Type: Fire
EVs: 60 HP / 212 Atk / 236 Spe
Jolly Nature
- Triple Arrows
- Haze
- Leaf Blade
- Protect
""",
        ### SINGAPORE PREMIER BALL LEAGUE NOVEMBER 2024 (1 team) ###
        """
Sneasler @ Focus Sash
Ability: Poison Touch
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
IVs: 6 SpA
- Dire Claw
- Coaching
- Protect
- Close Combat

Electabuzz @ Eviolite
Ability: Vital Spirit
Level: 50
Tera Type: Ghost
EVs: 252 HP / 228 Def / 28 Spe
Bold Nature
IVs: 22 Atk
- Follow Me
- Thunderbolt
- Taunt
- Protect

Kingambit @ Black Glasses
Ability: Defiant
Level: 50
Tera Type: Dark
EVs: 252 HP / 220 Atk / 4 Def / 4 SpD / 28 Spe
Adamant Nature
- Kowtow Cleave
- Swords Dance
- Sucker Punch
- Protect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Water
EVs: 204 HP / 196 Atk / 4 Def / 4 SpD / 100 Spe
Adamant Nature
IVs: 4 SpA
- Wood Hammer
- U-turn
- Grassy Glide
- Fake Out

Volcarona @ Covert Cloak
Ability: Flame Body
Level: 50
Tera Type: Fairy
EVs: 252 HP / 132 Def / 36 SpA / 4 SpD / 84 Spe
Modest Nature
IVs: 2 Atk
- Fiery Dance
- Tera Blast
- Quiver Dance
- Protect

Incineroar @ Rocky Helmet
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 4 Atk / 140 Def / 76 SpD / 44 Spe
Careful Nature
- Knock Off
- Will-O-Wisp
- Fake Out
- Parting Shot
""",
        ### GDAŃSK REGIONALS NOVEMBER 2024 (4 teams) ###
        """
Annihilape (F) @ Leftovers
Ability: Defiant
Level: 50
Shiny: Yes
Tera Type: Fire
EVs: 180 HP / 36 Atk / 4 Def / 36 SpD / 252 Spe
Jolly Nature
- Protect
- Bulk Up
- Drain Punch
- Rage Fist

Sinistcha @ Sitrus Berry
Ability: Hospitality
Level: 50
Tera Type: Water
EVs: 252 HP / 108 Def / 148 SpD
Bold Nature
IVs: 0 Atk
- Matcha Gotcha
- Trick Room
- Life Dew
- Rage Powder

Maushold-Four @ Safety Goggles
Ability: Friend Guard
Level: 50
Tera Type: Ghost
EVs: 108 HP / 172 Def / 36 SpD / 188 Spe
Timid Nature
IVs: 26 Atk
- Follow Me
- Taunt
- Beat Up
- Protect

Klefki @ Light Clay
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 252 HP / 76 Def / 180 SpD
Calm Nature
IVs: 24 Atk
- Reflect
- Light Screen
- Misty Terrain
- Dazzling Gleam

Ursaluna-Bloodmoon @ Assault Vest
Ability: Mind's Eye
Level: 50
Tera Type: Water
EVs: 252 HP / 4 Def / 116 SpA / 132 SpD / 4 Spe
Modest Nature
- Blood Moon
- Hyper Voice
- Earth Power
- Vacuum Wave

Ninetales-Alola (F) @ Focus Sash
Ability: Snow Warning
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 4 HP / 36 Def / 212 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 20 Atk
- Protect
- Encore
- Freeze-Dry
- Blizzard
""",
        """
Ninetales-Alola @ Never-Melt Ice
Ability: Snow Warning
Level: 50
Tera Type: Ghost
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Blizzard
- Freeze-Dry
- Encore
- Protect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Ghost
EVs: 220 HP / 116 Atk / 4 Def / 68 SpD / 100 Spe
Adamant Nature
- Wood Hammer
- Fake Out
- U-turn
- Grassy Glide

Magmar @ Eviolite
Ability: Vital Spirit
Level: 50
Tera Type: Ghost
EVs: 236 HP / 220 Def / 4 SpA / 4 SpD / 44 Spe
Bold Nature
IVs: 0 Atk
- Protect
- Heat Wave
- Will-O-Wisp
- Follow Me

Sneasler @ Focus Sash
Ability: Poison Touch
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Fake Out
- Dire Claw
- Close Combat
- Protect

Kingambit @ Black Glasses
Ability: Defiant
Level: 50
Tera Type: Fire
EVs: 92 HP / 252 Atk / 4 Def / 4 SpD / 156 Spe
Adamant Nature
- Kowtow Cleave
- Swords Dance
- Sucker Punch
- Protect

Basculegion @ Choice Scarf
Ability: Adaptability
Level: 50
Tera Type: Fighting
EVs: 4 HP / 220 Atk / 28 Def / 4 SpD / 252 Spe
Adamant Nature
- Wave Crash
- Flip Turn
- Tera Blast
- Last Respects
""",
        """
Archaludon @ Assault Vest
Ability: Stamina
Shiny: Yes
Tera Type: Grass
EVs: 180 HP / 12 Def / 44 SpA / 164 SpD / 108 Spe
Modest Nature
IVs: 0 Atk
- Draco Meteor
- Flash Cannon
- Electro Shot
- Body Press

Pelipper @ Focus Sash
Ability: Drizzle
Shiny: Yes
Tera Type: Stellar
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 0 Atk
- Protect
- Weather Ball
- Hurricane
- Tailwind

Gholdengo @ Life Orb
Ability: Good as Gold
Tera Type: Water
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Make It Rain
- Shadow Ball
- Nasty Plot

Basculegion @ Choice Band
Ability: Swift Swim
Shiny: Yes
Tera Type: Grass
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Flip Turn
- Wave Crash
- Aqua Jet
- Last Respects

Amoonguss @ Sitrus Berry
Ability: Regenerator
Shiny: Yes
Tera Type: Water
EVs: 244 HP / 180 Def / 84 SpD
Bold Nature
IVs: 0 Atk / 27 Spe
- Spore
- Rage Powder
- Pollen Puff
- Protect

Incineroar @ Safety Goggles
Ability: Intimidate
Tera Type: Ghost
EVs: 252 HP / 116 Atk / 68 Def / 28 SpD / 44 Spe
Adamant Nature
- Flare Blitz
- Knock Off
- Parting Shot
- Fake Out
""",
        """
Ninetales-Alola @ Choice Specs
Ability: Snow Warning
Level: 50
Tera Type: Ghost
EVs: 20 Def / 236 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Blizzard
- Freeze-Dry
- Icy Wind
- Moonblast

Delphox @ Life Orb
Ability: Blaze
Level: 50
Tera Type: Fighting
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 18 Atk
- Protect
- Tera Blast
- Expanding Force
- Heat Wave

Indeedee (M) @ Focus Sash
Ability: Psychic Surge
Level: 50
Tera Type: Psychic
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 12 Atk
- Tera Blast
- Expanding Force
- Trick Room
- Imprison

Kingambit @ Assault Vest
Ability: Defiant
Level: 50
Tera Type: Flying
EVs: 252 HP / 252 Atk / 4 Spe
Adamant Nature
IVs: 16 SpA
- Stone Edge
- Kowtow Cleave
- Sucker Punch
- Low Kick

Sneasler @ Psychic Seed
Ability: Unburden
Level: 50
Tera Type: Dark
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
IVs: 18 SpA
- Protect
- Throat Chop
- Close Combat
- Dire Claw

Prinplup @ Eviolite
Ability: Competitive
Level: 50
Tera Type: Fairy
EVs: 252 HP / 52 Def / 36 SpA / 4 SpD / 164 Spe
Bold Nature
IVs: 18 Atk
- Tera Blast
- Helping Hand
- Haze
- Water Pledge
""",
        ### LAIC NOVEMBER 2024 (10 teams) ###
        """
Charizard @ Choice Specs
Ability: Solar Power
Level: 50
Tera Type: Ghost
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
- Heat Wave
- Overheat
- Weather Ball
- Air Slash

Torkoal @ Eject Pack
Ability: Drought
Level: 50
Tera Type: Fire
EVs: 252 HP / 4 Def / 252 SpA
Modest Nature
IVs: 0 Atk / 9 Spe
- Eruption
- Overheat
- Helping Hand
- Protect

Porygon2 @ Eviolite
Ability: Download
Level: 50
Tera Type: Fighting
EVs: 252 HP / 28 Def / 204 SpA / 20 SpD / 4 Spe
Modest Nature
- Ice Beam
- Tera Blast
- Trick Room
- Recover

Incineroar @ Sitrus Berry
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 252 HP / 36 Atk / 4 Def / 12 SpD / 204 Spe
Adamant Nature
- Flare Blitz
- Knock Off
- Fake Out
- Parting Shot

Jumpluff @ Covert Cloak
Ability: Chlorophyll
Level: 50
Tera Type: Water
EVs: 164 HP / 148 Def / 196 Spe
Timid Nature
IVs: 0 Atk
- Sleep Powder
- Sunny Day
- Rage Powder
- Tailwind

Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Ghost
EVs: 140 HP / 252 Atk / 116 Spe
Adamant Nature
- Headlong Rush
- Facade
- Earthquake
- Protect
""",
        """
Kommo-o @ Throat Spray
Ability: Soundproof
Level: 50
Tera Type: Fire
EVs: 196 HP / 12 Def / 76 SpA / 4 SpD / 220 Spe
Timid Nature
IVs: 10 Atk
- Clangorous Soul
- Clanging Scales
- Flamethrower
- Protect

Dondozo @ Leftovers
Ability: Unaware
Level: 50
Tera Type: Flying
EVs: 252 HP / 4 Def / 252 SpD
Impish Nature
- Wave Crash
- Fissure
- Yawn
- Protect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 252 HP / 252 Atk / 4 SpD
Adamant Nature
- Fake Out
- Wood Hammer
- Grassy Glide
- High Horsepower

Sneasler @ Focus Sash
Ability: Unburden
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Fake Out
- Dire Claw
- Close Combat
- Protect

Electabuzz @ Eviolite
Ability: Vital Spirit
Level: 50
Tera Type: Grass
EVs: 220 HP / 124 Def / 4 SpA / 44 SpD / 116 Spe
Timid Nature
IVs: 0 Atk
- Electroweb
- Follow Me
- Helping Hand
- Protect

Gholdengo @ Choice Specs
Ability: Good as Gold
Level: 50
Tera Type: Fairy
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Dazzling Gleam
- Power Gem
""",
        """
Annihilape @ Safety Goggles
Ability: Defiant
Tera Type: Water
EVs: 188 HP / 68 Atk / 252 Spe
Jolly Nature
- Coaching
- Close Combat
- Rage Fist
- Final Gambit

Archaludon @ Power Herb
Ability: Stalwart
Tera Type: Electric
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Electro Shot
- Thunderbolt
- Dragon Pulse
- Protect

Dragonite @ Loaded Dice
Ability: Multiscale
Tera Type: Steel
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Scale Shot
- Extreme Speed
- Haze
- Protect

Incineroar @ Sitrus Berry
Ability: Intimidate
Level: 50
Tera Type: Grass
EVs: 236 HP / 4 Atk / 4 Def / 52 SpD / 212 Spe
Adamant Nature
- Fake Out
- Flare Blitz
- Knock Off
- Parting Shot

Ursaluna-Bloodmoon @ Assault Vest
Ability: Mind's Eye
Tera Type: Poison
EVs: 172 HP / 4 Def / 116 SpA / 148 SpD / 68 Spe
Modest Nature
- Blood Moon
- Hyper Voice
- Earth Power
- Vacuum Wave

Whimsicott @ Focus Sash
Ability: Prankster
Tera Type: Ghost
EVs: 44 Def / 212 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Fake Tears
- Encore
- Tailwind
""",
        """
Gholdengo @ Life Orb
Ability: Good as Gold
Level: 50
Tera Type: Steel
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect

Sneasler @ Focus Sash
Ability: Poison Touch
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
IVs: 24 SpA
- Fake Out
- Close Combat
- Dire Claw
- Protect

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 4 Atk / 4 Def / 252 SpD / 4 Spe
Careful Nature
IVs: 22 SpA
- Fake Out
- Flare Blitz
- Knock Off
- Parting Shot

Dragonite @ Loaded Dice
Ability: Multiscale
Level: 50
Tera Type: Fairy
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Scale Shot
- Extreme Speed
- Haze
- Tailwind

Amoonguss @ Sitrus Berry
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 244 HP / 156 Def / 108 SpD
Bold Nature
- Spore
- Rage Powder
- Sludge Bomb
- Protect

Ursaluna-Bloodmoon @ Assault Vest
Ability: Mind's Eye
Level: 50
Tera Type: Normal
EVs: 20 HP / 4 Def / 196 SpA / 108 SpD / 180 Spe
Modest Nature
IVs: 10 Atk
- Hyper Voice
- Blood Moon
- Earth Power
- Vacuum Wave
""",
        """
Ninetales-Alola (M) @ Focus Sash
Ability: Snow Warning
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Aurora Veil
- Encore
- Blizzard
- Icy Wind

Annihilape @ Safety Goggles
Ability: Defiant
Level: 50
Tera Type: Water
EVs: 180 HP / 20 Atk / 44 Def / 12 SpD / 252 Spe
Jolly Nature
- Drain Punch
- Rage Fist
- Bulk Up
- Protect

Gholdengo @ Leftovers
Ability: Good as Gold
Level: 50
Tera Type: Water
EVs: 236 HP / 4 Def / 52 SpA / 4 SpD / 212 Spe
Modest Nature
- Make It Rain
- Nasty Plot
- Shadow Ball
- Protect

Dragonite (F) @ Loaded Dice
Ability: Multiscale
Level: 50
Tera Type: Steel
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Scale Shot
- Tailwind
- Extreme Speed
- Protect

Primarina @ Choice Specs
Ability: Liquid Voice
Level: 50
Tera Type: Poison
EVs: 132 HP / 116 Def / 36 SpA / 4 SpD / 220 Spe
Modest Nature
IVs: 0 Atk
- Hyper Voice
- Moonblast
- Dazzling Gleam
- Haze

Arcanine @ Mirror Herb
Ability: Intimidate
Level: 50
Tera Type: Normal
EVs: 4 HP / 236 Atk / 4 Def / 44 SpD / 220 Spe
Jolly Nature
- Extreme Speed
- Flare Blitz
- Protect
- Will-O-Wisp
""",
        """
Sneasler @ Focus Sash
Ability: Poison Touch
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Close Combat
- Dire Claw
- Fake Out
- Protect

Dragapult @ Choice Band
Ability: Clear Body
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Dragon Darts
- Tera Blast
- Phantom Force
- U-turn

Primarina @ Sitrus Berry
Ability: Liquid Voice
Level: 50
Tera Type: Water
EVs: 228 HP / 172 Def / 28 SpA / 4 SpD / 76 Spe
Modest Nature
IVs: 0 Atk
- Hyper Voice
- Moonblast
- Haze
- Protect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 172 HP / 196 Atk / 4 Def / 28 SpD / 108 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- High Horsepower
- Fake Out

Kingambit @ Black Glasses
Ability: Defiant
Level: 50
Tera Type: Ghost
EVs: 172 HP / 196 Atk / 4 Def / 124 SpD / 12 Spe
Adamant Nature
- Kowtow Cleave
- Sucker Punch
- Swords Dance
- Protect

Magmar @ Eviolite
Ability: Vital Spirit
Level: 50
Tera Type: Ghost
EVs: 252 HP / 196 Def / 4 SpA / 4 SpD / 52 Spe
Modest Nature
IVs: 0 Atk
- Overheat
- Will-O-Wisp
- Follow Me
- Protect
""",
        """
Archaludon @ Assault Vest
Ability: Stamina
Level: 50
Tera Type: Fairy
EVs: 220 HP / 4 Def / 52 SpA / 116 SpD / 116 Spe
Bold Nature
IVs: 26 Atk
- Electro Shot
- Draco Meteor
- Flash Cannon
- Body Press

Rillaboom @ Loaded Dice
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 204 HP / 116 Atk / 4 Def / 60 SpD / 124 Spe
Adamant Nature
- Bullet Seed
- Grassy Glide
- Fake Out
- High Horsepower

Basculegion @ Choice Band
Ability: Swift Swim
Level: 50
Tera Type: Grass
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Wave Crash
- Last Respects
- Flip Turn
- Aqua Jet

Kingambit @ Black Glasses
Ability: Defiant
Level: 50
Tera Type: Dark
EVs: 236 HP / 228 Atk / 4 Def / 4 SpD / 36 Spe
Adamant Nature
- Kowtow Cleave
- Sucker Punch
- Swords Dance
- Protect

Pelipper @ Focus Sash
Ability: Drizzle
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
- Weather Ball
- Hurricane
- Tailwind
- Protect

Electabuzz @ Eviolite
Ability: Vital Spirit
Level: 50
Tera Type: Ghost
EVs: 244 HP / 180 Def / 4 SpA / 20 SpD / 60 Spe
Bold Nature
IVs: 20 Atk
- Electroweb
- Taunt
- Follow Me
- Protect
""",
        """
Farigiraf @ Air Balloon
Ability: Armor Tail
Level: 50
Tera Type: Dragon
EVs: 244 HP / 156 Def / 108 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Psychic
- Dazzling Gleam
- Calm Mind
- Trick Room

Indeedee-F @ Safety Goggles
Ability: Psychic Surge
Level: 50
Tera Type: Water
EVs: 252 HP / 252 Def / 4 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Psychic
- Follow Me
- Helping Hand
- Trick Room

Annihilape @ Choice Scarf
Ability: Defiant
Level: 50
Tera Type: Ground
EVs: 252 HP / 100 Atk / 156 Spe
Jolly Nature
IVs: 24 SpA
- U-turn
- Close Combat
- Earthquake
- Final Gambit

Snorlax @ Custap Berry
Ability: Gluttony
Level: 50
Tera Type: Rock
EVs: 244 HP / 252 Atk / 12 Def
Brave Nature
IVs: 0 Spe
- Body Slam
- Rock Slide
- Earthquake
- Belly Drum

Torkoal @ Choice Specs
Ability: Drought
Level: 50
Tera Type: Fire
EVs: 252 HP / 252 SpA / 4 SpD
Quiet Nature
IVs: 0 Atk / 0 Spe
- Eruption
- Heat Wave
- Weather Ball
- Earth Power

Armarouge @ Weakness Policy
Ability: Weak Armor
Level: 50
Tera Type: Psychic
EVs: 4 HP / 124 Def / 132 SpA / 4 SpD / 244 Spe
Modest Nature
IVs: 0 Atk
- Expanding Force
- Heat Wave
- Stored Power
- Endure
""",
        """
Gholdengo @ Life Orb
Ability: Good as Gold
Level: 66
Tera Type: Water
EVs: 164 HP / 36 Def / 68 SpA / 4 SpD / 236 Spe
Modest Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Protect
- Nasty Plot

Incineroar @ Assault Vest
Ability: Intimidate
Level: 50
Tera Type: Grass
EVs: 236 HP / 4 Atk / 180 Def / 28 SpD / 60 Spe
Impish Nature
- Flare Blitz
- Knock Off
- Fake Out
- U-turn

Amoonguss @ Covert Cloak
Ability: Regenerator
Level: 50
Tera Type: Fire
EVs: 236 HP / 164 Def / 108 SpD
Bold Nature
IVs: 0 Atk
- Pollen Puff
- Clear Smog
- Rage Powder
- Spore

Ursaluna @ Flame Orb
Ability: Guts
Level: 80
Tera Type: Ghost
EVs: 140 HP / 244 Atk / 44 Def / 76 SpD / 4 Spe
Adamant Nature
- Facade
- Headlong Rush
- Earthquake
- Ice Punch

Porygon2 @ Eviolite
Ability: Download
Level: 50
Tera Type: Fighting
EVs: 244 HP / 4 Atk / 100 Def / 92 SpA / 68 SpD
Quiet Nature
- Tera Blast
- Ice Beam
- Trick Room
- Recover

Hydreigon @ Choice Specs
Ability: Levitate
Level: 50
Tera Type: Fire
EVs: 28 HP / 20 Def / 196 SpA / 12 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Draco Meteor
- Dark Pulse
- Snarl
- Heat Wave
""",
        """
Grimmsnarl @ Light Clay
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 252 HP / 140 Def / 116 SpD
Careful Nature
- Thunder Wave
- Light Screen
- Reflect
- Spirit Break

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 252 HP / 116 Atk / 12 Def / 124 SpD / 4 Spe
Adamant Nature
- Fake Out
- Knock Off
- Flare Blitz
- Parting Shot

Gliscor @ Toxic Orb
Ability: Poison Heal
Level: 50
Tera Type: Water
EVs: 252 HP / 36 Atk / 4 Def / 196 SpD / 20 Spe
Adamant Nature
- Dual Wingbeat
- Swords Dance
- Protect
- High Horsepower

Archaludon @ Power Herb
Ability: Stalwart
Level: 50
Tera Type: Electric
EVs: 244 HP / 4 Def / 124 SpA / 116 SpD / 20 Spe
Modest Nature
IVs: 0 Atk
- Electro Shot
- Draco Meteor
- Thunderbolt
- Protect

Sinistcha @ Assault Vest
Ability: Hospitality
Level: 50
Tera Type: Water
EVs: 236 HP / 4 Def / 68 SpA / 156 SpD / 44 Spe
Modest Nature
IVs: 0 Atk
- Matcha Gotcha
- Shadow Ball
- Scald
- Leaf Storm

Pelipper @ Focus Sash
Ability: Drizzle
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Weather Ball
- Hurricane
- Tailwind
- Protect
""",
        ### SACRAMENTO REGIONALS NOVEMBER 2024 (5 teams) ###
        """
Sneasler @ Psychic Seed
Ability: Unburden
Level: 50
Tera Type: Dark
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Close Combat
- Dire Claw
- Throat Chop
- Protect

Indeedee (M) @ Focus Sash
Ability: Psychic Surge
Level: 50
Tera Type: Psychic
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Expanding Force
- Trick Room
- Helping Hand
- Protect

Ursaluna-Bloodmoon @ Life Orb
Ability: Mind's Eye
Level: 50
Tera Type: Normal
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 0 Atk
- Blood Moon
- Hyper Voice
- Earth Power
- Protect

Electabuzz @ Eviolite
Ability: Vital Spirit
Level: 50
Tera Type: Dragon
EVs: 148 HP / 100 Def / 4 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Electroweb
- Follow Me
- Taunt
- Protect

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 204 HP / 36 Atk / 4 Def / 12 SpD / 252 Spe
Adamant Nature
- Flare Blitz
- Knock Off
- Parting Shot
- Fake Out

Talonflame @ Covert Cloak
Ability: Gale Wings
Level: 50
Tera Type: Fairy
EVs: 244 Atk / 12 SpD / 252 Spe
Jolly Nature
- Flare Blitz
- Dual Wingbeat
- Will-O-Wisp
- Tailwind
""",
        """
Incineroar @ Assault Vest
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 220 HP / 36 Atk / 4 Def / 84 SpD / 164 Spe
Adamant Nature
- Knock Off
- Flare Blitz
- Fake Out
- U-turn

Sneasler @ Focus Sash
Ability: Poison Touch
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Dire Claw
- Close Combat
- Fake Out
- Coaching

Archaludon @ Power Herb
Ability: Stamina
Level: 50
Tera Type: Dragon
EVs: 12 HP / 4 Def / 212 SpA / 28 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Draco Meteor
- Flash Cannon
- Electro Shot

Garchomp @ Life Orb
Ability: Rough Skin
Level: 50
Tera Type: Ground
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Protect
- Earthquake
- Dragon Claw
- Stomping Tantrum

Corviknight @ Sitrus Berry
Ability: Mirror Armor
Level: 50
Tera Type: Fire
EVs: 244 HP / 4 Atk / 4 Def / 156 SpD / 100 Spe
Careful Nature
- Brave Bird
- Tailwind
- Roost
- Taunt

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Shiny: Yes
Tera Type: Water
EVs: 236 HP / 164 Def / 4 SpA / 100 SpD / 4 Spe
Bold Nature
IVs: 0 Atk
- Protect
- Rage Powder
- Spore
- Sludge Bomb
""",
        """
Porygon2 @ Eviolite
Ability: Download
Level: 50
Shiny: Yes
Tera Type: Fighting
EVs: 252 HP / 28 Def / 172 SpA / 52 SpD / 4 Spe
Modest Nature
- Tera Blast
- Ice Beam
- Trick Room
- Recover

Hydreigon @ Safety Goggles
Ability: Levitate
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 76 HP / 4 Def / 180 SpA / 12 SpD / 236 Spe
Timid Nature
IVs: 8 Atk
- Snarl
- Draco Meteor
- Tailwind
- Protect

Incineroar @ Sitrus Berry
Ability: Intimidate
Level: 50
Shiny: Yes
Tera Type: Grass
EVs: 236 HP / 36 Atk / 4 Def / 4 SpD / 228 Spe
Adamant Nature
- Flare Blitz
- Knock Off
- Parting Shot
- Fake Out

Garchomp @ Loaded Dice
Ability: Rough Skin
Level: 50
Shiny: Yes
Tera Type: Fire
EVs: 4 HP / 244 Atk / 4 Def / 4 SpD / 252 Spe
Adamant Nature
- Scale Shot
- Earthquake
- Stomping Tantrum
- Protect

Amoonguss @ Covert Cloak
Ability: Regenerator
Level: 50
Shiny: Yes
Tera Type: Fire
EVs: 236 HP / 116 Def / 156 SpD
Calm Nature
IVs: 27 Atk / 27 Spe
- Pollen Puff
- Spore
- Rage Powder
- Protect

Gholdengo @ Metal Coat
Ability: Good as Gold
Level: 50
Shiny: Yes
Tera Type: Flying
EVs: 228 HP / 44 Def / 212 SpA / 4 SpD / 20 Spe
Modest Nature
IVs: 5 Atk
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect
""",
        """
Whimsicott @ Focus Sash
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Tailwind
- Taunt
- Encore

Ursaluna-Bloodmoon @ Assault Vest
Ability: Mind's Eye
Level: 50
Tera Type: Water
EVs: 156 HP / 4 Def / 148 SpA / 68 SpD / 132 Spe
Modest Nature
IVs: 0 Atk
- Blood Moon
- Hyper Voice
- Earth Power
- Vacuum Wave

Dragonite @ Loaded Dice
Ability: Multiscale
Level: 50
Tera Type: Fairy
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Scale Shot
- Extreme Speed
- Haze
- Protect

Archaludon @ Power Herb
Ability: Stalwart
Level: 50
Tera Type: Electric
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Electro Shot
- Dragon Pulse
- Thunderbolt
- Protect

Annihilape @ Safety Goggles
Ability: Defiant
Level: 50
Tera Type: Water
EVs: 180 HP / 76 Atk / 252 Spe
Jolly Nature
- Rage Fist
- Close Combat
- Coaching
- Final Gambit

Incineroar @ Sitrus Berry
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 236 HP / 20 Atk / 4 Def / 12 SpD / 236 Spe
Jolly Nature
- Fake Out
- Flare Blitz
- Knock Off
- Parting Shot
""",
        """
Pelipper @ Focus Sash
Ability: Drizzle
Level: 50
Tera Type: Stellar
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
- Wide Guard
- Hurricane
- Weather Ball
- Protect

Archaludon @ Assault Vest
Ability: Stamina
Level: 50
Tera Type: Bug
EVs: 116 HP / 84 Def / 116 SpA / 172 SpD / 20 Spe
Modest Nature
IVs: 20 Atk
- Body Press
- Dragon Pulse
- Flash Cannon
- Electro Shot

Murkrow @ Eviolite
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 252 HP / 4 Def / 252 Spe
Timid Nature
IVs: 0 Atk
- Foul Play
- Tailwind
- Haze
- Rain Dance

Basculegion @ Choice Band
Ability: Swift Swim
Level: 50
Tera Type: Grass
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Wave Crash
- Aqua Jet
- Flip Turn
- Last Respects

Rillaboom @ Miracle Seed
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 244 HP / 140 Atk / 28 Def / 36 SpD / 60 Spe
Adamant Nature
- Taunt
- Wood Hammer
- Grassy Glide
- Fake Out

Ursaluna-Bloodmoon @ Life Orb
Ability: Mind's Eye
Level: 50
Tera Type: Normal
EVs: 52 HP / 252 SpA / 204 Spe
Modest Nature
IVs: 20 Atk
- Blood Moon
- Earth Power
- Protect
- Hyper Voice
""",
        ### TAIWAN PREMIER BALL LEAGUE DECEMBER 2024 (11 teams) ###
        """
紫竽超可愛 (Indeedee-F) @ Psychic Seed
Ability: Psychic Surge
Level: 50
Shiny: Yes
Tera Type: Fire
EVs: 252 HP / 252 Def / 4 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Trick Room
- Follow Me
- Helping Hand
- Dazzling Gleam

紫竽敲可愛 (Hatterene) @ Life Orb
Ability: Magic Bounce
Level: 50
Shiny: Yes
Tera Type: Psychic
EVs: 212 HP / 44 Def / 252 SpA
Quiet Nature
IVs: 0 Atk / 0 Spe
- Expanding Force
- Trick Room
- Dazzling Gleam
- Protect

紫竽親衛隊 (Gallade) @ Clear Amulet
Ability: Sharpness
Level: 50
Shiny: Yes
Tera Type: Grass
EVs: 212 HP / 252 Atk / 44 Spe
Adamant Nature
- Psycho Cut
- Trick Room
- Sacred Sword
- Wide Guard

一拳月月熊 (Ursaluna) (M) @ Flame Orb
Ability: Guts
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 252 HP / 252 Atk / 4 SpD
Brave Nature
IVs: 0 Spe
- Headlong Rush
- Facade
- Swords Dance
- Protect

紫竽好可愛 (Lilligant-Hisui) @ Focus Sash
Ability: Chlorophyll
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Solar Blade
- Sleep Powder
- Close Combat
- After You

太樂巴戈斯 (Torkoal) (M) @ Choice Specs
Ability: Drought
Level: 50
Shiny: Yes
Tera Type: Fire
EVs: 252 HP / 4 Def / 252 SpA
Quiet Nature
IVs: 0 Atk / 0 Spe
- Eruption
- Heat Wave
- Weather Ball
- Earth Power
""",
        """
Grimmsnarl @ Light Clay
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 236 HP / 196 Def / 76 SpD
Impish Nature
- Spirit Break
- Parting Shot
- Reflect
- Light Screen

Annihilape @ Leftovers
Ability: Defiant
Level: 50
Tera Type: Fire
EVs: 180 HP / 36 Atk / 20 Def / 20 SpD / 252 Spe
Jolly Nature
- Drain Punch
- Rage Fist
- Bulk Up
- Protect

Ursaluna-Bloodmoon @ Assault Vest
Ability: Mind's Eye
Level: 50
Tera Type: Water
EVs: 148 HP / 4 Def / 252 SpA / 4 SpD / 100 Spe
Modest Nature
IVs: 0 Atk
- Blood Moon
- Hyper Voice
- Earth Power
- Vacuum Wave

Volcarona @ Sitrus Berry
Ability: Flame Body
Level: 50
Tera Type: Grass
EVs: 252 HP / 28 Def / 36 SpA / 4 SpD / 188 Spe
Modest Nature
IVs: 0 Atk
- Giga Drain
- Heat Wave
- Quiver Dance
- Protect

Gholdengo @ Metal Alloy
Ability: Good as Gold
Level: 50
Tera Type: Dragon
EVs: 244 HP / 108 Def / 52 SpA / 76 Spe
Modest Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect

Dragonite @ Loaded Dice
Ability: Multiscale
Level: 50
Tera Type: Steel
EVs: 164 HP / 204 Atk / 12 Def / 12 SpD / 116 Spe
Adamant Nature
- Scale Shot
- Stomping Tantrum
- Extreme Speed
- Protect
""",
        """
Ursaluna-Bloodmoon @ Assault Vest
Ability: Mind's Eye
Level: 50
Tera Type: Water
EVs: 156 HP / 44 Def / 116 SpA / 4 SpD / 188 Spe
Modest Nature
IVs: 4 Atk
- Hyper Voice
- Blood Moon
- Vacuum Wave
- Earth Power

Ninetales-Alola (M) @ Light Clay
Ability: Snow Warning
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 220 HP / 36 Def / 252 Spe
Timid Nature
- Blizzard
- Aurora Veil
- Encore
- Icy Wind

Gholdengo @ Life Orb
Ability: Good as Gold
Level: 50
Tera Type: Dragon
EVs: 212 HP / 4 Def / 20 SpA / 20 SpD / 252 Spe
Timid Nature
IVs: 18 Atk
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect

Magmar (F) @ Eviolite
Ability: Vital Spirit
Level: 50
Shiny: Yes
Tera Type: Grass
EVs: 252 HP / 100 Def / 12 SpA / 4 SpD / 140 Spe
Modest Nature
IVs: 21 Atk
- Overheat
- Follow Me
- Clear Smog
- Protect

Dragonite (F) @ Loaded Dice
Ability: Multiscale
Level: 50
Shiny: Yes
Tera Type: Dark
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
IVs: 8 SpA
- Scale Shot
- Extreme Speed
- Ice Spinner
- Protect

Annihilape (F) @ Safety Goggles
Ability: Defiant
Level: 50
Shiny: Yes
Tera Type: Water
EVs: 180 HP / 36 Atk / 12 Def / 60 SpD / 220 Spe
Adamant Nature
IVs: 23 SpA
- Rage Fist
- Drain Punch
- Bulk Up
- Protect
""",
        """
Dragonite (F) @ Loaded Dice
Ability: Multiscale
Level: 50
Shiny: Yes
Tera Type: Fairy
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
IVs: 22 SpA
- Scale Shot
- Haze
- Extreme Speed
- Protect

Annihilape (F) @ Focus Sash
Ability: Defiant
Level: 50
Shiny: Yes
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
IVs: 14 SpA
- Rage Fist
- Close Combat
- Coaching
- Taunt

Electabuzz (M) @ Eviolite
Ability: Vital Spirit
Level: 50
Shiny: Yes
Tera Type: Dragon
EVs: 164 HP / 116 Def / 4 SpA / 4 SpD / 220 Spe
Timid Nature
IVs: 22 Atk
- Thunderbolt
- Electroweb
- Follow Me
- Protect

Rillaboom (M) @ Assault Vest
Ability: Grassy Surge
Level: 50
Shiny: Yes
Tera Type: Fire
EVs: 204 HP / 116 Atk / 12 Def / 76 SpD / 100 Spe
Adamant Nature
IVs: 0 SpA
- Wood Hammer
- Grassy Glide
- High Horsepower
- Fake Out

Incineroar (F) @ Mirror Herb
Ability: Intimidate
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 244 HP / 36 Atk / 116 Def / 4 SpD / 108 Spe
Adamant Nature
IVs: 2 SpA
- Flare Blitz
- Knock Off
- Parting Shot
- Fake Out

Gholdengo @ Sitrus Berry
Ability: Good as Gold
Level: 50
Tera Type: Water
EVs: 108 HP / 4 Def / 140 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect
""",
        """
Excadrill @ Focus Sash
Ability: Sand Rush
Level: 50
Tera Type: Ground
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Protect
- Iron Head
- High Horsepower
- Earthquake

Tyranitar @ Assault Vest
Ability: Sand Stream
Level: 50
Tera Type: Flying
EVs: 252 HP / 252 Atk / 4 Def
Adamant Nature
- Knock Off
- Rock Slide
- Low Kick
- Tera Blast

Corviknight @ Wacan Berry
Ability: Mirror Armor
Level: 50
Tera Type: Dragon
EVs: 252 HP / 36 Def / 220 SpD
Impish Nature
- Brave Bird
- U-turn
- Taunt
- Tailwind

Rotom-Wash @ Safety Goggles
Ability: Levitate
Level: 50
Tera Type: Electric
EVs: 252 HP / 252 SpA / 4 SpD
Modest Nature
IVs: 16 Atk
- Thunderbolt
- Hydro Pump
- Will-O-Wisp
- Protect

Amoonguss @ Sitrus Berry
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 244 HP / 156 Def / 108 SpD
Bold Nature
IVs: 15 Atk / 26 Spe
- Clear Smog
- Pollen Puff
- Rage Powder
- Spore

Flamigo @ Covert Cloak
Ability: Scrappy
Level: 50
Tera Type: Steel
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Brave Bird
- Wide Guard
- Close Combat
- Detect
""",
        """
Porygon2 @ Eviolite
Ability: Download
Level: 50
Tera Type: Fighting
EVs: 252 HP / 4 Atk / 124 Def / 92 SpA / 36 SpD
Quiet Nature
IVs: 0 Spe
- Tera Blast
- Ice Beam
- Trick Room
- Recover

Incineroar @ Sitrus Berry
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 204 Atk / 28 Def / 4 SpD / 28 Spe
Adamant Nature
- Fake Out
- Knock Off
- Flare Blitz
- Parting Shot

Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Ghost
EVs: 148 HP / 252 Atk / 108 Spe
Adamant Nature
- Headlong Rush
- Facade
- Earthquake
- Protect

Jumpluff @ Covert Cloak
Ability: Leaf Guard
Level: 50
Tera Type: Water
EVs: 252 HP / 76 SpD / 180 Spe
Timid Nature
IVs: 0 Atk
- Rage Powder
- Sunny Day
- Tailwind
- Sleep Powder

Charizard @ Choice Specs
Ability: Solar Power
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Heat Wave
- Overheat
- Weather Ball
- Dragon Pulse

Torkoal @ Eject Pack
Ability: Drought
Tera Type: Fire
EVs: 252 HP / 252 SpA / 4 SpD
Quiet Nature
- Overheat
- Eruption
- Helping Hand
- Protect
""",
        """
Volcarona @ Rocky Helmet
Ability: Flame Body
Level: 50
Tera Type: Grass
EVs: 252 HP / 252 Def / 4 Spe
Bold Nature
IVs: 0 Atk
- Rage Powder
- Quiver Dance
- Heat Wave
- Giga Drain

Gholdengo @ Leftovers
Ability: Good as Gold
Level: 50
Tera Type: Water
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Make It Rain
- Nasty Plot
- Shadow Ball
- Protect

Basculegion @ Clear Amulet
Ability: Swift Swim
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Last Respects
- Wave Crash
- Aqua Jet
- Flip Turn

Murkrow @ Eviolite
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 252 HP / 4 Def / 252 SpD
Calm Nature
IVs: 0 Atk
- Tailwind
- Haze
- Taunt
- Foul Play

Sneasler @ Focus Sash
Ability: Poison Touch
Level: 50
Tera Type: Dark
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Fake Out
- Close Combat
- Dire Claw
- Protect

Archaludon @ Power Herb
Ability: Stamina
Level: 50
Tera Type: Fairy
EVs: 4 HP / 252 SpA / 252 SpD
Calm Nature
IVs: 0 Atk
- Electro Shot
- Draco Meteor
- Body Press
- Protect
""",
        """
Charizard (M) @ Choice Specs
Ability: Solar Power
Level: 50
Tera Type: Fire
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Heat Wave
- Air Slash
- Scorching Sands
- Overheat

Lilligant-Hisui @ Focus Sash
Ability: Chlorophyll
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Leaf Blade
- Close Combat
- After You
- Sleep Powder

Torkoal (M) @ Eject Pack
Ability: Drought
Level: 50
Tera Type: Fire
EVs: 244 HP / 252 SpA / 12 SpD
Modest Nature
IVs: 0 Atk / 0 Spe
- Eruption
- Overheat
- Clear Smog
- Protect

Rillaboom (M) @ Miracle Seed
Ability: Grassy Surge
Level: 50
Shiny: Yes
Tera Type: Grass
EVs: 252 HP / 156 Atk / 20 Def / 20 SpD / 60 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- Fake Out
- High Horsepower

Sneasler (M) @ Grassy Seed
Ability: Unburden
Level: 50
Shiny: Yes
Tera Type: Flying
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Acrobatics
- Dire Claw
- Close Combat
- Protect

Porygon2 @ Eviolite
Ability: Download
Level: 50
Shiny: Yes
Tera Type: Electric
EVs: 252 HP / 4 Atk / 36 Def / 52 SpA / 164 SpD
Relaxed Nature
- Tera Blast
- Ice Beam
- Trick Room
- Recover
""",
        """
Kingambit (M) @ Black Glasses
Ability: Defiant
Level: 50
Shiny: Yes
Tera Type: Dark
EVs: 252 HP / 196 Atk / 4 Def / 36 SpD / 20 Spe
Adamant Nature
IVs: 27 SpA
- Kowtow Cleave
- Iron Head
- Protect
- Sucker Punch

Rillaboom (M) @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 132 HP / 196 Atk / 108 Def / 60 SpD / 12 Spe
Adamant Nature
IVs: 0 SpA
- Wood Hammer
- Grassy Glide
- High Horsepower
- Fake Out

Ursaluna-Bloodmoon @ Life Orb
Ability: Mind's Eye
Level: 50
Tera Type: Normal
EVs: 164 HP / 196 SpA / 148 Spe
Modest Nature
IVs: 26 Atk
- Earth Power
- Blood Moon
- Protect
- Hyper Voice

Sneasler (M) @ Focus Sash
Ability: Unburden
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
IVs: 0 SpA
- Close Combat
- Dire Claw
- Protect
- Fake Out

Pelipper (M) @ Covert Cloak
Ability: Drizzle
Level: 50
Shiny: Yes
Tera Type: Grass
EVs: 148 HP / 4 Def / 116 SpA / 68 SpD / 172 Spe
Bold Nature
IVs: 8 Atk
- Weather Ball
- Hurricane
- Protect
- Tailwind

Dondozo (M) @ Mystic Water
Ability: Unaware
Level: 50
Tera Type: Grass
EVs: 244 HP / 236 Atk / 28 Spe
Adamant Nature
IVs: 12 SpA
- Wave Crash
- Stomping Tantrum
- Protect
- Yawn
""",
        """
Goodra (Goodra-Hisui) (F) @ Assault Vest
Ability: Sap Sipper
Shiny: Yes
Tera Type: Water
EVs: 252 HP / 76 Def / 156 SpA / 12 SpD / 12 Spe
Modest Nature
IVs: 0 Atk
- Dragon Pulse
- Ice Beam
- Muddy Water
- Thunderbolt

Rillaboom (F) @ Life Orb
Ability: Grassy Surge
Shiny: Yes
Tera Type: Fire
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- High Horsepower
- Fake Out

Sneasler (F) @ Focus Sash
Ability: Unburden
Tera Type: Stellar
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Close Combat
- Dire Claw
- Coaching
- Protect

Incineroar (M) @ Safety Goggles
Ability: Intimidate
Shiny: Yes
Tera Type: Ghost
EVs: 236 HP / 4 Atk / 76 Def / 116 SpD / 76 Spe
Impish Nature
- Fake Out
- Knock Off
- Flare Blitz
- Parting Shot

Gholdengo @ Leftovers
Ability: Good as Gold
Tera Type: Dragon
EVs: 108 HP / 4 Def / 132 SpA / 12 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect

Amoonguss (F) @ Sitrus Berry
Ability: Regenerator
Level: 50
Shiny: Yes
Tera Type: Water
EVs: 244 HP / 156 Def / 108 SpD
Bold Nature
IVs: 0 Atk
- Spore
- Rage Powder
- Pollen Puff
- Clear Smog
""",
        """
Gholdengo @ Choice Scarf
Ability: Good as Gold
Level: 50
Shiny: Yes
Tera Type: Flying
EVs: 12 HP / 4 Def / 252 SpA / 4 SpD / 236 Spe
Modest Nature
- Make It Rain
- Shadow Ball
- Trick
- Protect

Pelipper (F) @ Focus Sash
Ability: Drizzle
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
- Weather Ball
- Hurricane
- Tailwind
- Protect

Archaludon (F) @ Assault Vest
Ability: Stamina
Level: 50
Shiny: Yes
Tera Type: Fighting
EVs: 252 HP / 76 Def / 4 SpA / 164 SpD / 12 Spe
Bold Nature
- Electro Shot
- Flash Cannon
- Body Press
- Snarl

Sinistcha @ Sitrus Berry
Ability: Hospitality
Level: 50
Shiny: Yes
Tera Type: Dark
EVs: 252 HP / 68 Def / 4 SpA / 180 SpD
Relaxed Nature
IVs: 0 Spe
- Matcha Gotcha
- Life Dew
- Rage Powder
- Trick Room

Ursaluna (F) @ Flame Orb
Ability: Guts
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 12 HP / 252 Atk / 20 Def / 20 SpD / 204 Spe
Adamant Nature
- Headlong Rush
- Earthquake
- Facade
- Protect

Dragonite (F) @ Loaded Dice
Ability: Multiscale
Level: 50
Shiny: Yes
Tera Type: Fairy
EVs: 4 HP / 248 Atk / 4 Def / 252 Spe
Adamant Nature
- Scale Shot
- Haze
- Tailwind
- Protect
""",
        ### STUTTGART REGIONALS DECEMBER 2024 (6 teams) ###
        """
Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 252 HP / 4 Atk / 76 Def / 140 SpD / 36 Spe
Adamant Nature
- Flare Blitz
- Knock Off
- Parting Shot
- Fake Out

Amoonguss @ Sitrus Berry
Ability: Regenerator
Level: 50
Tera Type: Psychic
EVs: 244 HP / 164 Def / 4 SpA / 76 SpD / 20 Spe
Calm Nature
IVs: 0 Atk
- Spore
- Rage Powder
- Pollen Puff
- Protect

Ursaluna-Bloodmoon @ Assault Vest
Ability: Mind's Eye
Level: 50
Tera Type: Water
EVs: 148 HP / 12 Def / 116 SpA / 180 SpD / 52 Spe
Modest Nature
IVs: 0 Atk
- Hyper Voice
- Blood Moon
- Earth Power
- Vacuum Wave

Sneasler @ Focus Sash
Ability: Unburden
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Close Combat
- Dire Claw
- Throat Chop
- Protect

Gholdengo @ Life Orb
Ability: Good as Gold
Level: 50
Tera Type: Water
EVs: 116 HP / 4 Def / 132 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect

Dragonite @ Loaded Dice
Ability: Multiscale
Level: 50
Tera Type: Fairy
EVs: 12 HP / 236 Atk / 4 Def / 4 SpD / 252 Spe
Adamant Nature
- Scale Shot
- Tailwind
- Haze
- Protect
""",
        """
Volcarona @ Leftovers
Ability: Flame Body
Level: 50
Tera Type: Fairy
EVs: 132 HP / 180 Def / 36 SpA / 4 SpD / 156 Spe
Modest Nature
- Heat Wave
- Tera Blast
- Quiver Dance
- Protect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 204 HP / 116 Atk / 4 Def / 76 SpD / 108 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- High Horsepower
- Fake Out

Electabuzz @ Eviolite
Ability: Vital Spirit
Level: 50
Tera Type: Ghost
EVs: 252 HP / 212 Def / 4 SpA / 4 SpD / 36 Spe
Timid Nature
IVs: 0 Atk
- Thunderbolt
- Follow Me
- Taunt
- Protect

Dragonite @ Loaded Dice
Ability: Multiscale
Level: 50
Tera Type: Steel
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Scale Shot
- Extreme Speed
- Haze
- Protect

Kingambit @ Black Glasses
Ability: Defiant
Level: 50
Tera Type: Dark
EVs: 252 HP / 244 Atk / 12 Def
Adamant Nature
- Kowtow Cleave
- Sucker Punch
- Swords Dance
- Protect

Sneasler @ Focus Sash
Ability: Unburden
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Close Combat
- Dire Claw
- Coaching
- Protect
""",
        """
Dragonite @ Loaded Dice
Ability: Multiscale
Level: 50
Tera Type: Fairy
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Scale Shot
- Extreme Speed
- Haze
- Protect

Pelipper @ Focus Sash
Ability: Drizzle
Level: 50
Tera Type: Dark
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 0 Atk
- Muddy Water
- Hurricane
- Tailwind
- Protect

Archaludon @ Assault Vest
Ability: Stamina
Level: 50
Tera Type: Fighting
EVs: 252 HP / 28 Def / 4 SpA / 100 SpD / 124 Spe
Modest Nature
IVs: 0 Atk
- Electro Shot
- Draco Meteor
- Flash Cannon
- Body Press

Basculegion (M) @ Life Orb
Ability: Swift Swim
Level: 50
Tera Type: Water
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Wave Crash
- Last Respects
- Aqua Jet
- Protect

Sinistcha-Masterpiece @ Sitrus Berry
Ability: Hospitality
Level: 50
Tera Type: Water
EVs: 252 HP / 108 Def / 148 SpD
Bold Nature
IVs: 0 Atk
- Matcha Gotcha
- Rage Powder
- Trick Room
- Life Dew

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 236 HP / 4 Atk / 44 Def / 100 SpD / 124 Spe
Impish Nature
- Knock Off
- Taunt
- Fake Out
- Parting Shot
""",
        """
Annihilape @ Safety Goggles
Ability: Defiant
Level: 50
Tera Type: Water
EVs: 180 HP / 52 Atk / 12 Def / 12 SpD / 252 Spe
Jolly Nature
- Drain Punch
- Rage Fist
- Bulk Up
- Protect

Gholdengo @ Metal Coat
Ability: Good as Gold
Level: 50
Tera Type: Dragon
EVs: 196 HP / 4 Def / 52 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect

Dragonite @ Loaded Dice
Ability: Multiscale
Level: 50
Tera Type: Steel
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Scale Shot
- Extreme Speed
- Ice Spinner
- Protect

Ninetales-Alola @ Light Clay
Ability: Snow Warning
Level: 50
Tera Type: Ghost
EVs: 100 HP / 132 Def / 12 SpA / 12 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Blizzard
- Encore
- Icy Wind
- Aurora Veil

Magmar @ Eviolite
Ability: Flame Body
Level: 50
Tera Type: Ghost
EVs: 244 HP / 220 Def / 4 SpA / 4 SpD / 36 Spe
Bold Nature
IVs: 0 Atk
- Overheat
- Follow Me
- Protect
- Clear Smog

Ursaluna-Bloodmoon @ Assault Vest
Ability: Mind's Eye
Level: 50
Tera Type: Water
EVs: 100 HP / 12 Def / 116 SpA / 196 SpD / 84 Spe
Modest Nature
IVs: 0 Atk
- Blood Moon
- Earth Power
- Hyper Voice
- Vacuum Wave
""",
        """
Sneasler @ Grassy Seed
Ability: Unburden
Level: 50
Tera Type: Dark
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Dire Claw
- Close Combat
- Throat Chop
- Protect

Volcarona @ Leftovers
Ability: Flame Body
Level: 50
Tera Type: Fairy
EVs: 252 HP / 76 Def / 36 SpA / 4 SpD / 140 Spe
Modest Nature
- Heat Wave
- Quiver Dance
- Protect
- Tera Blast

Dragonite @ Loaded Dice
Ability: Multiscale
Level: 50
Tera Type: Steel
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Scale Shot
- Extreme Speed
- Haze
- Protect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 132 HP / 212 Atk / 28 Def / 28 SpD / 108 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- High Horsepower
- Fake Out

Maushold-Four @ Focus Sash
Ability: Friend Guard
Tera Type: Ghost
EVs: 156 HP / 100 Def / 252 Spe
Timid Nature
IVs: 0 Atk
- Follow Me
- Taunt
- Protect
- Super Fang

Gholdengo @ Sitrus Berry
Ability: Good as Gold
Level: 50
Tera Type: Water
EVs: 172 HP / 12 Def / 84 SpA / 4 SpD / 236 Spe
Modest Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect
""",
        """
Anti-Hero (Yanmega) @ Focus Sash
Ability: Speed Boost
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 0 Atk
- Bug Buzz
- Air Slash
- Tailwind
- Protect

YOYOK (Ursaluna) @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Ghost
EVs: 28 HP / 252 Atk / 4 Def / 4 SpD / 220 Spe
Adamant Nature
- Facade
- Earthquake
- Headlong Rush
- Protect

Maroon (Porygon2) @ Eviolite
Ability: Download
Level: 50
Tera Type: Fighting
EVs: 252 HP / 52 Def / 116 SpA / 84 SpD / 4 Spe
Modest Nature
- Tera Blast
- Ice Beam
- Recover
- Trick Room

Karma (Incineroar) @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 236 HP / 36 Atk / 4 Def / 4 SpD / 228 Spe
Adamant Nature
- Knock Off
- Parting Shot
- Flare Blitz
- Fake Out

Labyrinth (Amoonguss) @ Mental Herb
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 252 HP / 156 Def / 100 SpD
Bold Nature
IVs: 0 Atk
- Pollen Puff
- Clear Smog
- Rage Powder
- Spore

Bejeweled (Gholdengo) @ Life Orb
Ability: Good as Gold
Level: 50
Tera Type: Water
EVs: 52 HP / 204 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect
""",
        ### MALAYSIA PREMIER BALL LEAGUE DECEMBER 2024 (2 teams) ###
        """
Indeedee (M) @ Choice Scarf
Ability: Psychic Surge
Level: 50
Tera Type: Psychic
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 10 Atk
- Protect
- Expanding Force
- Dazzling Gleam
- Trick

Torkoal @ Eject Pack
Ability: Drought
Level: 50
Tera Type: Fire
EVs: 252 HP / 252 SpA / 4 SpD
Quiet Nature
IVs: 0 Atk / 14 Spe
- Eruption
- Overheat
- Earth Power
- Protect

Dragonite @ Loaded Dice
Ability: Multiscale
Level: 50
Tera Type: Steel
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Scale Shot
- Haze
- Stomping Tantrum
- Protect

Delphox @ Focus Sash
Ability: Magician
Level: 50
Tera Type: Fairy
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 0 Atk
- Expanding Force
- Dazzling Gleam
- Burning Jealousy
- Trick Room

Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Ghost
EVs: 252 HP / 252 Atk / 4 Def
Brave Nature
IVs: 6 Spe
- Headlong Rush
- Facade
- Earthquake
- Protect

Porygon2 @ Eviolite
Ability: Download
Level: 50
Tera Type: Fighting
EVs: 252 HP / 140 Def / 68 SpA / 44 SpD
Quiet Nature
IVs: 22 Spe
- Recover
- Ice Beam
- Tera Blast
- Trick Room
""",
        """
Archaludon @ Power Herb
Ability: Sturdy
Level: 50
Tera Type: Stellar
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Electro Shot
- Protect
- Flash Cannon
- Draco Meteor

Sneasler @ Focus Sash
Ability: Unburden
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Close Combat
- Dire Claw
- Coaching
- Protect

Rillaboom @ Miracle Seed
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 252 HP / 116 Atk / 4 Def / 100 SpD / 36 Spe
Adamant Nature
- Fake Out
- Grassy Glide
- Wood Hammer
- Protect

Incineroar @ Assault Vest
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 252 HP / 116 Atk / 100 Def / 12 SpD / 28 Spe
Adamant Nature
IVs: 8 SpA
- Fake Out
- Flare Blitz
- Knock Off
- U-turn

Primarina @ Leftovers
Ability: Liquid Voice
Level: 50
Tera Type: Poison
EVs: 252 HP / 100 Def / 108 SpA / 12 SpD / 36 Spe
Modest Nature
IVs: 0 Atk
- Hyper Voice
- Moonblast
- Calm Mind
- Protect

Dragonite @ Loaded Dice
Ability: Multiscale
Level: 50
Tera Type: Steel
EVs: 252 HP / 44 Atk / 36 Def / 20 SpD / 156 Spe
Adamant Nature
IVs: 8 SpA
- Scale Shot
- Protect
- Tailwind
- Haze
""",
        ### PERTH REGIONALS DECEMBER 2024 (5 teams) ###
        """
Dinko (Ursaluna) @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Fairy
EVs: 12 HP / 244 Atk / 252 Spe
Adamant Nature
- Facade
- Headlong Rush
- Earthquake
- Protect

Big Bird (Kilowattrel) (F) @ Focus Sash
Ability: Competitive
Level: 50
Tera Type: Ghost
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Thunderbolt
- Air Slash
- Tailwind
- Protect

Mr Worldwide (Gholdengo) @ Life Orb
Ability: Good as Gold
Level: 50
Tera Type: Flying
EVs: 52 HP / 84 Def / 116 SpA / 4 SpD / 252 Spe
Timid Nature
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect

Pumpy the Grumpy (Incineroar) @ Assault Vest
Ability: Intimidate
Level: 50
Shiny: Yes
Tera Type: Grass
EVs: 196 HP / 92 Atk / 4 Def / 20 SpD / 196 Spe
Adamant Nature
- Knock Off
- Flare Blitz
- U-turn
- Fake Out

뽀록나 (Amoonguss) @ Sitrus Berry
Ability: Regenerator
Level: 50
Shiny: Yes
Tera Type: Water
EVs: 228 HP / 204 Def / 76 SpD
Calm Nature
IVs: 0 Atk
- Spore
- Rage Powder
- Sludge Bomb
- Protect

Nokia Brick (Porygon2) @ Eviolite
Ability: Download
Level: 50
Shiny: Yes
Tera Type: Fighting
EVs: 244 HP / 108 Def / 4 SpA / 148 SpD / 4 Spe
Calm Nature
- Tera Blast
- Ice Beam
- Recover
- Trick Room
""",
        """
Porygon2 @ Eviolite
Ability: Download
Level: 50
Tera Type: Fighting
EVs: 252 HP / 28 Def / 148 SpA / 68 SpD / 12 Spe
Modest Nature
- Tera Blast
- Ice Beam
- Recover
- Trick Room

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 4 Atk / 44 Def / 4 SpD / 212 Spe
Careful Nature
- Fake Out
- Knock Off
- Flare Blitz
- Parting Shot

Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Ghost
EVs: 140 HP / 236 Atk / 132 Spe
Adamant Nature
IVs: 14 SpA
- Headlong Rush
- Facade
- Earthquake
- Protect

Amoonguss @ Sitrus Berry
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 228 HP / 156 Def / 124 SpD
Bold Nature
IVs: 0 Atk / 26 Spe
- Pollen Puff
- Spore
- Rage Powder
- Protect

Gholdengo @ Life Orb
Ability: Good as Gold
Level: 50
Tera Type: Water
EVs: 20 HP / 4 Def / 228 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect

Dragonite @ Loaded Dice
Ability: Multiscale
Level: 50
Tera Type: Steel
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Scale Shot
- Haze
- Tailwind
- Protect
""",
        """
Amoonguss @ Sitrus Berry
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 244 HP / 156 Def / 108 SpD
Bold Nature
IVs: 0 Atk
- Rage Powder
- Spore
- Sludge Bomb
- Protect

Dragonite @ Loaded Dice
Ability: Inner Focus
Level: 50
Tera Type: Fairy
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
IVs: 10 SpA
- Scale Shot
- Low Kick
- Tailwind
- Haze

Excadrill @ Focus Sash
Ability: Sand Rush
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
IVs: 8 SpA
- Protect
- High Horsepower
- Earthquake
- Iron Head

Gholdengo @ Life Orb
Ability: Good as Gold
Level: 50
Tera Type: Dragon
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Make It Rain
- Nasty Plot
- Protect
- Shadow Ball

Gyarados @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Steel
EVs: 244 HP / 36 Atk / 4 Def / 44 SpD / 180 Spe
Adamant Nature
- Waterfall
- Thunder Wave
- Taunt
- Protect

Tyranitar @ Assault Vest
Ability: Sand Stream
Level: 50
Tera Type: Flying
EVs: 188 HP / 204 Atk / 116 Spe
Adamant Nature
IVs: 28 SpA
- Rock Slide
- Knock Off
- Low Kick
- Tera Blast
""",
        """
Gholdengo @ Life Orb
Ability: Good as Gold
Tera Type: Water
EVs: 52 HP / 4 Def / 196 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect

Amoonguss @ Sitrus Berry
Ability: Regenerator
Level: 75
Tera Type: Psychic
EVs: 244 HP / 164 Def / 100 SpD
Bold Nature
IVs: 0 Atk
- Spore
- Rage Powder
- Pollen Puff
- Protect

Basculegion @ Choice Band
Ability: Swift Swim
Level: 80
Tera Type: Water
EVs: 4 HP / 252 Atk / 52 Def / 4 SpD / 196 Spe
Adamant Nature
- Wave Crash
- Flip Turn
- Last Respects
- Aqua Jet

Pelipper @ Focus Sash
Ability: Drizzle
Level: 69
Tera Type: Ground
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 0 Atk
- Weather Ball
- Hurricane
- Tailwind
- Protect

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 85
Tera Type: Ghost
EVs: 252 HP / 36 Atk / 124 Def / 92 SpD / 4 Spe
Adamant Nature
IVs: 28 SpA
- Flare Blitz
- Knock Off
- Parting Shot
- Fake Out

Archaludon @ Assault Vest
Ability: Stamina
Level: 69
Tera Type: Bug
EVs: 252 HP / 4 Def / 36 SpA / 92 SpD / 124 Spe
Modest Nature
IVs: 0 Atk
- Electro Shot
- Flash Cannon
- Draco Meteor
- Body Press
""",
        """
Excadrill @ Focus Sash
Ability: Sand Rush
Level: 50
Tera Type: Ground
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Protect
- Earthquake
- High Horsepower
- Iron Head

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 252 HP / 116 Atk / 20 Def / 108 SpD / 12 Spe
Adamant Nature
IVs: 22 SpA
- Fake Out
- Knock Off
- Flare Blitz
- Parting Shot

Tyranitar @ Assault Vest
Ability: Sand Stream
Level: 50
Tera Type: Flying
EVs: 244 HP / 204 Atk / 4 Def / 12 SpD / 44 Spe
Adamant Nature
- Rock Slide
- Knock Off
- Low Kick
- Tera Blast

Amoonguss @ Sitrus Berry
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 212 HP / 156 Def / 140 SpD
Bold Nature
IVs: 4 Atk / 6 Spe
- Pollen Puff
- Rage Powder
- Clear Smog
- Spore

Kommo-o @ Throat Spray
Ability: Overcoat
Level: 50
Tera Type: Steel
EVs: 124 HP / 12 Def / 124 SpA / 4 SpD / 228 Spe
Timid Nature
- Protect
- Clanging Scales
- Clangorous Soul
- Aura Sphere

Reuniclus @ Life Orb
Ability: Magic Guard
Level: 50
Tera Type: Dark
EVs: 252 HP / 60 Def / 196 SpA
Modest Nature
- Protect
- Trick Room
- Expanding Force
- Flash Cannon
""",
        ### TORONTO REGIONALS DECEMBER 2024 (13 teams) ###
        """
Sneasler @ Psychic Seed
Ability: Unburden
Level: 50
Tera Type: Dark
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Close Combat
- Dire Claw
- Throat Chop
- Protect

Indeedee (M) @ Choice Scarf
Ability: Psychic Surge
Level: 50
Tera Type: Psychic
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
- Expanding Force
- Tera Blast
- Trick
- Protect

Volcarona @ Sitrus Berry
Ability: Flame Body
Level: 50
Tera Type: Grass
EVs: 156 HP / 84 Def / 12 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Overheat
- Struggle Bug
- Rage Powder
- Tailwind

Ursaluna-Bloodmoon @ Life Orb
Ability: Mind's Eye
Level: 50
Tera Type: Normal
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 0 Atk
- Blood Moon
- Hyper Voice
- Earth Power
- Protect

Annihilape @ Safety Goggles
Ability: Defiant
Level: 50
Tera Type: Fairy
EVs: 188 HP / 68 Atk / 252 Spe
Jolly Nature
- Close Combat
- Rage Fist
- Taunt
- Final Gambit

Tyranitar (M) @ Assault Vest
Ability: Sand Stream
Level: 50
Tera Type: Flying
EVs: 116 HP / 204 Atk / 188 Spe
Adamant Nature
- Rock Slide
- Knock Off
- Tera Blast
- Low Kick
""",
        """
Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Ghost
EVs: 252 HP / 236 Atk / 20 SpD
Brave Nature
IVs: 3 Spe
- Protect
- Facade
- Headlong Rush
- Substitute

Amoonguss @ Covert Cloak
Ability: Regenerator
Level: 50
Tera Type: Electric
EVs: 236 HP / 180 Def / 4 SpA / 84 SpD / 4 Spe
Bold Nature
IVs: 0 Atk
- Rage Powder
- Clear Smog
- Pollen Puff
- Spore

Porygon2 @ Eviolite
Ability: Download
Level: 50
Shiny: Yes
Tera Type: Fighting
EVs: 252 HP / 4 Atk / 124 Def / 44 SpA / 84 SpD
Quiet Nature
IVs: 0 Spe
- Recover
- Tera Blast
- Ice Beam
- Trick Room

Incineroar @ Assault Vest
Ability: Intimidate
Level: 50
Tera Type: Grass
EVs: 180 HP / 60 Atk / 4 Def / 12 SpD / 252 Spe
Jolly Nature
- U-turn
- Flare Blitz
- Knock Off
- Fake Out

Gholdengo @ Life Orb
Ability: Good as Gold
Level: 50
Tera Type: Water
EVs: 132 HP / 4 Def / 228 SpA / 4 SpD / 140 Spe
Modest Nature
IVs: 0 Atk
- Protect
- Make It Rain
- Shadow Ball
- Nasty Plot

Mienshao @ Focus Sash
Ability: Inner Focus
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Close Combat
- Knock Off
- Ice Spinner
- Wide Guard
""",
        """
Gholdengo @ Grassy Seed
Ability: Good as Gold
Level: 79
Tera Type: Water
EVs: 236 HP / 4 Def / 36 SpA / 4 SpD / 228 Spe
Modest Nature
IVs: 0 Atk
- Nasty Plot
- Make It Rain
- Shadow Ball
- Protect

Sneasler (M) @ White Herb
Ability: Unburden
Level: 50
Tera Type: Ghost
EVs: 172 HP / 92 Atk / 108 Def / 4 SpD / 132 Spe
Adamant Nature
- Close Combat
- Dire Claw
- Coaching
- Protect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 60
Tera Type: Fire
EVs: 108 HP / 140 Atk / 4 Def / 4 SpD / 252 Spe
Jolly Nature
- Fake Out
- Grassy Glide
- Drum Beating
- High Horsepower

Dragonite @ Loaded Dice
Ability: Multiscale
Level: 55
Tera Type: Ground
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Scale Shot
- Stomping Tantrum
- Tailwind
- Protect

Ninetales-Alola @ Focus Sash
Ability: Snow Warning
Level: 76
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Blizzard
- Icy Wind
- Encore
- Aurora Veil

Arcanine-Hisui @ Clear Amulet
Ability: Intimidate
Tera Type: Water
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Rock Slide
- Flare Blitz
- Extreme Speed
- Protect
""",
        """
WrathofKhan (Kingambit) (F) @ Black Glasses
Ability: Defiant
Level: 50
Shiny: Yes
Tera Type: Dark
EVs: 252 HP / 196 Atk / 4 Def / 20 SpD / 36 Spe
Adamant Nature
- Protect
- Kowtow Cleave
- Sucker Punch
- Swords Dance

Trunkmeister (Rillaboom) (F) @ Assault Vest
Ability: Grassy Surge
Level: 50
Shiny: Yes
Tera Type: Fire
EVs: 252 HP / 116 Atk / 4 Def / 60 SpD / 76 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- High Horsepower
- Fake Out

Litofsky (Electabuzz) (M) @ Eviolite
Ability: Vital Spirit
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 228 HP / 180 Def / 4 SpA / 4 SpD / 92 Spe
Bold Nature
IVs: 0 Atk
- Protect
- Thunderbolt
- Helping Hand
- Follow Me

Heimlich (Volcarona) (M) @ Covert Cloak
Ability: Flame Body
Level: 50
Shiny: Yes
Tera Type: Fairy
EVs: 252 HP / 76 Def / 52 SpA / 4 SpD / 124 Spe
Modest Nature
- Protect
- Heat Wave
- Tera Blast
- Quiver Dance

Shigaraki (Sneasler) @ Focus Sash
Ability: Unburden
Level: 50
Tera Type: Stellar
EVs: 4 HP / 244 Atk / 4 Def / 4 SpD / 252 Spe
Jolly Nature
- Close Combat
- Dire Claw
- Coaching
- Fake Out

All for One (Dragonite) @ Loaded Dice
Ability: Multiscale
Level: 50
Tera Type: Fairy
EVs: 12 HP / 236 Atk / 4 Def / 4 SpD / 252 Spe
Adamant Nature
- Scale Shot
- Haze
- Extreme Speed
- Protect
""",
        """
Hatterene @ Covert Cloak
Ability: Magic Bounce
Tera Type: Fire
EVs: 252 HP / 4 Def / 252 SpA
Quiet Nature
IVs: 0 Atk / 0 Spe
- Expanding Force
- Dazzling Gleam
- Tera Blast
- Trick Room

Indeedee-F @ Psychic Seed
Ability: Psychic Surge
Tera Type: Water
EVs: 236 HP / 252 Def / 20 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Psychic
- Follow Me
- Helping Hand
- Trick Room

Torkoal @ Choice Specs
Ability: Drought
Level: 50
Tera Type: Fire
EVs: 252 HP / 252 SpA / 4 SpD
Quiet Nature
IVs: 0 Atk / 0 Spe
- Eruption
- Heat Wave
- Earth Power
- Weather Ball

Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Ghost
EVs: 252 HP / 252 Atk / 4 Def
Brave Nature
IVs: 0 Spe
- Facade
- Earthquake
- Headlong Rush
- Protect

Gallade @ Clear Amulet
Ability: Sharpness
Level: 50
Tera Type: Grass
EVs: 220 HP / 252 Atk / 36 SpD
Brave Nature
IVs: 0 Spe
- Sacred Sword
- Psycho Cut
- Wide Guard
- Trick Room

Maushold @ Wide Lens
Ability: Technician
Level: 50
Tera Type: Poison
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Population Bomb
- Follow Me
- Taunt
- Protect
""",
        """
Dragonite (M) @ Loaded Dice
Ability: Multiscale
Level: 50
Tera Type: Steel
EVs: 36 HP / 212 Atk / 4 Def / 4 SpD / 252 Spe
Adamant Nature
- Scale Shot
- Low Kick
- Protect
- Haze

Electabuzz (M) @ Eviolite
Ability: Vital Spirit
Level: 50
Tera Type: Fairy
EVs: 164 HP / 100 Def / 244 Spe
Timid Nature
IVs: 0 Atk
- Thunderbolt
- Taunt
- Protect
- Follow Me

Kingambit (M) @ Safety Goggles
Ability: Defiant
Level: 50
Tera Type: Flying
EVs: 252 HP / 196 Atk / 28 Def / 28 SpD / 4 Spe
Adamant Nature
- Kowtow Cleave
- Sucker Punch
- Protect
- Tera Blast

Rillaboom (M) @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 236 HP / 116 Atk / 4 Def / 44 SpD / 108 Spe
Adamant Nature
- Grassy Glide
- Wood Hammer
- Fake Out
- High Horsepower

Sneasler (F) @ Focus Sash
Ability: Poison Touch
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
IVs: 0 Def
- Dire Claw
- Close Combat
- Fake Out
- Coaching

Volcarona (F) @ Leftovers
Ability: Flame Body
Level: 50
Tera Type: Fairy
EVs: 252 HP / 60 Def / 36 SpA / 4 SpD / 156 Spe
Modest Nature
IVs: 0 Atk
- Heat Wave
- Tera Blast
- Protect
- Quiver Dance
""",
        """
Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 244 HP / 116 Atk / 4 Def / 60 SpD / 84 Spe
Adamant Nature
IVs: 18 SpA
- Fake Out
- High Horsepower
- Wood Hammer
- Grassy Glide

Dragonite @ Loaded Dice
Ability: Multiscale
Level: 50
Tera Type: Steel
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
IVs: 26 SpA
- Extreme Speed
- Scale Shot
- Protect
- Haze

Sneasler @ Focus Sash
Ability: Poison Touch
Level: 50
Tera Type: Stellar
EVs: 204 Atk / 52 Def / 252 Spe
Jolly Nature
IVs: 16 SpA
- Dire Claw
- Close Combat
- Fake Out
- Coaching

Kingambit @ Black Glasses
Ability: Defiant
Level: 50
Tera Type: Dark
EVs: 220 HP / 244 Atk / 28 Def / 4 SpD / 12 Spe
Adamant Nature
IVs: 6 SpA
- Kowtow Cleave
- Sucker Punch
- Swords Dance
- Protect

Electabuzz @ Eviolite
Ability: Vital Spirit
Level: 50
Tera Type: Ghost
EVs: 228 HP / 212 Def / 4 SpA / 4 SpD / 60 Spe
Bold Nature
IVs: 4 Atk
- Thunderbolt
- Taunt
- Follow Me
- Protect

Volcarona @ Leftovers
Ability: Flame Body
Level: 50
Tera Type: Fairy
EVs: 124 HP / 164 Def / 12 SpA / 4 SpD / 204 Spe
Modest Nature
IVs: 16 Atk
- Heat Wave
- Tera Blast
- Quiver Dance
- Protect
""",
        """
Ceruledge @ Assault Vest
Ability: Flash Fire
Level: 50
Tera Type: Grass
EVs: 252 HP / 116 Atk / 12 Def / 124 SpD / 4 Spe
Adamant Nature
- Bitter Blade
- Close Combat
- Poltergeist
- Shadow Sneak

Kingambit @ Safety Goggles
Ability: Defiant
Level: 50
Tera Type: Dark
EVs: 252 HP / 196 Atk / 28 Def / 12 SpD / 20 Spe
Adamant Nature
- Kowtow Cleave
- Protect
- Swords Dance
- Sucker Punch

Sneasler @ Focus Sash
Ability: Unburden
Level: 50
Tera Type: Flying
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Dire Claw
- Close Combat
- Coaching
- Protect

Gyarados @ Sitrus Berry
Ability: Intimidate
Level: 50
Tera Type: Fire
EVs: 140 HP / 196 Atk / 20 Def / 12 SpD / 140 Spe
Adamant Nature
- Waterfall
- Temper Flare
- Protect
- Dragon Dance

Abomasnow @ Life Orb
Ability: Snow Warning
Level: 50
Tera Type: Ice
EVs: 180 HP / 20 Def / 252 SpA / 4 SpD / 52 Spe
Modest Nature
IVs: 0 Atk
- Protect
- Aurora Veil
- Blizzard
- Leaf Storm

Garchomp @ Loaded Dice
Ability: Rough Skin
Level: 50
Tera Type: Fairy
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Stomping Tantrum
- Scale Shot
- Earthquake
- Protect
""",
        """
Sinistcha @ Mental Herb
Ability: Heatproof
Level: 50
Tera Type: Dark
EVs: 252 HP / 28 Def / 228 SpD
Bold Nature
IVs: 0 Atk
- Matcha Gotcha
- Calm Mind
- Strength Sap
- Trick Room

Kingambit @ Lum Berry
Ability: Defiant
Level: 50
Tera Type: Ghost
EVs: 236 HP / 196 Atk / 4 Def / 68 SpD / 4 Spe
Adamant Nature
- Kowtow Cleave
- Iron Head
- Sucker Punch
- Swords Dance

Garchomp @ Loaded Dice
Ability: Rough Skin
Level: 50
Tera Type: Steel
EVs: 36 HP / 252 Atk / 4 Def / 4 SpD / 212 Spe
Jolly Nature
- Stomping Tantrum
- Scale Shot
- Swords Dance
- Protect

Primarina @ Choice Specs
Ability: Liquid Voice
Level: 50
Tera Type: Grass
EVs: 252 HP / 36 Def / 188 SpA / 4 SpD / 28 Spe
Modest Nature
IVs: 0 Atk
- Hyper Voice
- Moonblast
- Dazzling Gleam
- Hydro Cannon

Volcarona @ Safety Goggles
Ability: Flame Body
Level: 50
Tera Type: Water
EVs: 188 HP / 60 Def / 4 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Struggle Bug
- Flamethrower
- Rage Powder
- Tailwind

Hariyama @ Assault Vest
Ability: Thick Fat
Level: 50
Tera Type: Steel
EVs: 156 HP / 76 Atk / 52 Def / 220 SpD
Brave Nature
IVs: 0 Spe
- Drain Punch
- Knock Off
- Headlong Rush
- Fake Out
""",
        """
Kilowattrel @ Focus Sash
Ability: Competitive
Level: 50
Tera Type: Ghost
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Thunderbolt
- Air Slash
- Tailwind
- Protect

Amoonguss @ Sitrus Berry
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 244 HP / 156 Def / 108 SpD
Bold Nature
IVs: 0 Atk / 27 Spe
- Pollen Puff
- Spore
- Rage Powder
- Protect

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 252 HP / 36 Atk / 4 Def / 20 SpD / 196 Spe
Adamant Nature
- Fake Out
- Flare Blitz
- Knock Off
- Parting Shot

Porygon2 @ Eviolite
Ability: Download
Level: 50
Tera Type: Fighting
EVs: 252 HP / 108 Def / 44 SpA / 100 SpD / 4 Spe
Modest Nature
- Tera Blast
- Ice Beam
- Recover
- Trick Room

Gholdengo @ Metal Coat
Ability: Good as Gold
Level: 50
Tera Type: Flying
EVs: 60 HP / 4 Def / 212 SpA / 4 SpD / 228 Spe
Modest Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect

Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Ghost
EVs: 36 HP / 244 Atk / 4 Def / 4 SpD / 220 Spe
Adamant Nature
- Facade
- Headlong Rush
- Earthquake
- Protect
""",
        """
Baxcalibur @ Loaded Dice
Ability: Thermal Exchange
Level: 75
Tera Type: Ghost
EVs: 28 HP / 236 Atk / 4 Def / 4 SpD / 236 Spe
Adamant Nature
- Scale Shot
- Icicle Spear
- High Horsepower
- Protect

Annihilape @ Focus Sash
Ability: Defiant
Level: 50
Shiny: Yes
Tera Type: Grass
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Rage Fist
- Close Combat
- Coaching
- Protect

Incineroar @ Safety Goggles
Ability: Intimidate
Tera Type: Ghost
EVs: 244 HP / 36 Atk / 100 Def / 116 SpD / 12 Spe
Careful Nature
- Flare Blitz
- Knock Off
- Fake Out
- Parting Shot

Primarina @ Leftovers
Ability: Liquid Voice
Level: 75
Shiny: Yes
Tera Type: Poison
EVs: 164 HP / 148 Def / 108 SpA / 4 SpD / 84 Spe
Modest Nature
IVs: 0 Atk
- Hyper Voice
- Moonblast
- Calm Mind
- Protect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 75
Tera Type: Fire
EVs: 244 HP / 116 Atk / 4 Def / 28 SpD / 116 Spe
Adamant Nature
- Grassy Glide
- Wood Hammer
- Fake Out
- High Horsepower

Gholdengo @ Choice Scarf
Ability: Good as Gold
Shiny: Yes
Tera Type: Steel
EVs: 60 HP / 20 Def / 212 SpA / 4 SpD / 212 Spe
Modest Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Power Gem
- Trick
""",
        """
Dragonite @ Loaded Dice
Ability: Multiscale
Level: 50
Tera Type: Fairy
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Scale Shot
- Extreme Speed
- Haze
- Protect

Ninetales-Alola @ Light Clay
Ability: Snow Warning
Level: 50
Tera Type: Ghost
EVs: 164 HP / 76 Def / 12 SpA / 4 SpD / 252 Spe
Timid Nature
- Icicle Spear
- Aurora Veil
- Blizzard
- Icy Wind

Annihilape @ Safety Goggles
Ability: Defiant
Level: 50
Tera Type: Fire
EVs: 180 HP / 68 Atk / 4 Def / 4 SpD / 252 Spe
Jolly Nature
- Rage Fist
- Drain Punch
- Bulk Up
- Protect

Rillaboom @ Miracle Seed
Ability: Grassy Surge
Level: 50
Tera Type: Grass
EVs: 132 HP / 244 Atk / 12 Def / 4 SpD / 116 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- Fake Out
- Protect

Gholdengo @ Life Orb
Ability: Good as Gold
Level: 50
Tera Type: Water
EVs: 52 HP / 4 Def / 196 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect

Ursaluna-Bloodmoon @ Assault Vest
Ability: Mind's Eye
Level: 50
Tera Type: Ghost
EVs: 148 HP / 12 Def / 116 SpA / 180 SpD / 52 Spe
Modest Nature
IVs: 0 Atk
- Blood Moon
- Hyper Voice
- Earth Power
- Vacuum Wave
""",
        """
Incineroar @ Safety Goggles
Ability: Intimidate
Tera Type: Ghost
EVs: 252 HP / 20 Atk / 4 Def / 20 SpD / 212 Spe
Impish Nature
- Flare Blitz
- Knock Off
- Fake Out
- Parting Shot

Gholdengo @ Life Orb
Ability: Good as Gold
Tera Type: Water
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect

Dragonite @ Loaded Dice
Ability: Multiscale
Tera Type: Steel
EVs: 20 HP / 212 Atk / 20 Def / 4 SpD / 252 Spe
Adamant Nature
- Scale Shot
- Haze
- Tailwind
- Protect

Ursaluna @ Flame Orb
Ability: Guts
Tera Type: Ghost
EVs: 12 HP / 236 Atk / 4 Def / 52 SpD / 204 Spe
Adamant Nature
- Headlong Rush
- Facade
- Earthquake
- Protect

Annihilape @ Focus Sash
Ability: Defiant
Tera Type: Stellar
EVs: 100 HP / 156 Atk / 252 Spe
Jolly Nature
- Close Combat
- Rage Fist
- Coaching
- Final Gambit

Indeedee-F @ Psychic Seed
Ability: Psychic Surge
Tera Type: Fairy
EVs: 236 HP / 196 Def / 4 SpA / 68 SpD / 4 Spe
Bold Nature
IVs: 0 Atk
- Psychic
- Follow Me
- Trick Room
- Protect
""",
        ### HONG KONG PREMIER BALL LEAGUE DECEMBER 2024 (2 teams) ###
        """
Whimsicott @ Focus Sash
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
- Tailwind
- Taunt
- Moonblast
- Beat Up

Annihilape @ Assault Vest
Ability: Defiant
Level: 50
Tera Type: Fire
EVs: 164 HP / 252 Atk / 4 Def / 4 SpD / 84 Spe
Adamant Nature
- Rage Fist
- Close Combat
- Rock Slide
- Drain Punch

Pelipper @ Covert Cloak
Ability: Drizzle
Level: 50
Tera Type: Ground
EVs: 124 HP / 4 Def / 220 SpA / 4 SpD / 156 Spe
Modest Nature
- Tailwind
- Hurricane
- Weather Ball
- Protect

Archaludon @ Life Orb
Ability: Stamina
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
- Electro Shot
- Protect
- Draco Meteor
- Body Press

Sneasler @ Psychic Seed
Ability: Unburden
Level: 50
Tera Type: Dark
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Acrobatics
- Close Combat
- Dire Claw
- Throat Chop

Indeedee (M) @ Choice Specs
Ability: Psychic Surge
Level: 50
Tera Type: Psychic
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 0 Atk
- Expanding Force
- Imprison
- Trick Room
- Trick
""",
        """
Incineroar (M) @ Chople Berry
Ability: Intimidate
Level: 50
Tera Type: Grass
EVs: 204 HP / 36 Atk / 4 Def / 12 SpD / 252 Spe
Adamant Nature
- Flare Blitz
- Knock Off
- Fake Out
- Parting Shot

Dragonite @ Loaded Dice
Ability: Multiscale
Level: 50
Tera Type: Steel
EVs: 12 HP / 236 Atk / 4 Def / 4 SpD / 252 Spe
Adamant Nature
- Scale Shot
- Tailwind
- Haze
- Protect

Porygon2 @ Eviolite
Ability: Download
Level: 50
Tera Type: Fighting
EVs: 252 HP / 28 Def / 148 SpA / 36 SpD / 44 Spe
Modest Nature
- Tera Blast
- Ice Beam
- Recover
- Trick Room

Ursaluna-Bloodmoon @ Assault Vest
Ability: Mind's Eye
Level: 50
Tera Type: Water
EVs: 156 HP / 44 Def / 116 SpA / 4 SpD / 188 Spe
Modest Nature
IVs: 4 Atk
- Hyper Voice
- Blood Moon
- Vacuum Wave
- Earth Power

Ninetales-Alola @ Light Clay
Ability: Snow Warning
Level: 50
Tera Type: Ghost
EVs: 100 HP / 132 Def / 12 SpA / 12 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Icicle Spear
- Encore
- Icy Wind
- Aurora Veil

Annihilape @ Safety Goggles
Ability: Defiant
Level: 50
Tera Type: Fire
EVs: 180 HP / 52 Atk / 12 Def / 12 SpD / 252 Spe
Jolly Nature
- Drain Punch
- Rage Fist
- Bulk Up
- Protect
""",
    ],
    "regiactual": [
        """
Koraidon @ Life Orb
Ability: Orichalcum Pulse
Level: 50
Tera Type: Fire
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Flare Blitz
- Close Combat
- Flame Charge
- Protect

Terapagos @ Leftovers
Ability: Tera Shift
Level: 50
Tera Type: Stellar
EVs: 172 HP / 236 Def / 76 SpA / 12 SpD / 12 Spe
Bold Nature
IVs: 15 Atk
- Tera Starstorm
- Earth Power
- Calm Mind
- Protect

Flutter Mane @ Focus Sash
Ability: Protosynthesis
Level: 50
Tera Type: Stellar
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Shadow Ball
- Icy Wind
- Protect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Poison
EVs: 252 HP / 60 Atk / 4 Def / 172 SpD / 20 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- Fake Out
- U-turn

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 236 Def / 28 Spe
Impish Nature
- Knock Off
- Fake Out
- Taunt
- U-turn

Volcarona @ Rocky Helmet
Ability: Flame Body
Level: 50
Tera Type: Grass
EVs: 252 HP / 212 Def / 4 SpA / 4 SpD / 36 Spe
Bold Nature
IVs: 0 Atk
- Morning Sun
- Overheat
- Struggle Bug
- Rage Powder
""",
        """
Calyrex-Shadow @ Life Orb
Ability: As One (Spectrier)
Level: 50
Tera Type: Dark
EVs: 172 HP / 4 Def / 180 SpA / 12 SpD / 140 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Psychic
- Nasty Plot
- Protect

Zamazenta-Crowned @ Rusted Shield
Ability: Dauntless Shield
Level: 50
Tera Type: Grass
EVs: 204 HP / 4 Atk / 180 Def / 28 SpD / 92 Spe
Impish Nature
- Body Press
- Heavy Slam
- Wide Guard
- Protect

Raging Bolt @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 196 HP / 4 Def / 252 SpA / 36 SpD / 20 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Draco Meteor
- Thunderclap
- Protect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 252 HP / 36 Atk / 76 Def / 124 SpD / 20 Spe
Adamant Nature
- Wood Hammer
- U-turn
- Grassy Glide
- Fake Out

Tornadus @ Sharp Beak
Ability: Prankster
Level: 50
Tera Type: Dragon
EVs: 244 HP / 116 Def / 44 SpA / 92 SpD / 12 Spe
Modest Nature
IVs: 0 Atk
- Bleakwind Storm
- Taunt
- Tailwind
- Protect

Smeargle @ Focus Sash
Ability: Moody
Level: 50
Tera Type: Grass
EVs: 12 HP / 244 Def / 252 Spe
Jolly Nature
- Spore
- Decorate
- Follow Me
- Fake Out
""",
        """
Miraidon @ Assault Vest
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 124 HP / 68 Def / 196 SpA / 4 SpD / 116 Spe
Modest Nature
- Draco Meteor
- Dazzling Gleam
- Electro Drift
- Volt Switch

Whimsicott (M) @ Covert Cloak
Ability: Prankster
Level: 50
Shiny: Yes
Tera Type: Fire
EVs: 252 HP / 164 Def / 4 SpA / 68 SpD / 20 Spe
Bold Nature
IVs: 0 Atk
- Tailwind
- Moonblast
- Light Screen
- Tickle

Incineroar (F) @ Rocky Helmet
Ability: Intimidate
Level: 50
Tera Type: Grass
EVs: 244 HP / 4 Atk / 84 Def / 156 SpD / 20 Spe
Careful Nature
- Fake Out
- Parting Shot
- Knock Off
- Helping Hand

Calyrex-Ice @ Icicle Plate
Ability: As One (Glastrier)
Level: 50
Tera Type: Water
EVs: 252 HP / 68 Atk / 4 Def / 172 SpD / 12 Spe
Adamant Nature
- Glacial Lance
- Trick Room
- Protect
- Leech Seed

Urshifu-Rapid-Strike (M) @ Mystic Water
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 84 HP / 236 Atk / 12 Def / 84 SpD / 92 Spe
Adamant Nature
- Surging Strikes
- Aqua Jet
- Protect
- Taunt

Landorus @ Life Orb
Ability: Sheer Force
Level: 50
Tera Type: Poison
EVs: 172 HP / 4 Def / 196 SpA / 4 SpD / 132 Spe
Modest Nature
- Earth Power
- Sludge Bomb
- Protect
- Crunch
""",
        """
Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Fire
EVs: 252 HP / 196 Atk / 60 SpD
Brave Nature
IVs: 1 Spe
- Glacial Lance
- High Horsepower
- Trick Room
- Protect

Lunala @ Power Herb
Ability: Shadow Shield
Level: 50
Tera Type: Grass
EVs: 220 HP / 20 Def / 196 SpA / 4 SpD / 68 Spe
Modest Nature
IVs: 0 Atk
- Expanding Force
- Trick Room
- Moongeist Beam
- Meteor Beam

Smeargle (M) @ Focus Sash
Ability: Technician
Level: 50
Shiny: Yes
Tera Type: Grass
EVs: 236 HP / 20 Def / 252 Spe
Jolly Nature
- Follow Me
- Fake Out
- Decorate
- Spore

Urshifu (M) @ Choice Band
Ability: Unseen Fist
Level: 50
Tera Type: Grass
EVs: 252 HP / 252 Atk / 4 Def
Brave Nature
IVs: 0 Spe
- Wicked Blow
- Sucker Punch
- Close Combat
- U-turn

Torkoal (M) @ Choice Specs
Ability: Drought
Level: 50
Shiny: Yes
Tera Type: Fire
EVs: 252 HP / 4 Def / 252 SpA
Quiet Nature
IVs: 0 Atk / 0 Spe
- Eruption
- Heat Wave
- Weather Ball
- Earth Power

Indeedee-F @ Safety Goggles
Ability: Psychic Surge
Level: 50
Shiny: Yes
Tera Type: Fairy
EVs: 252 HP / 252 Def / 4 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Alluring Voice
- Trick Room
- Follow Me
- Helping Hand
""",
        """
Kyogre @ Choice Scarf
Ability: Drizzle
Level: 50
Tera Type: Ghost
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Water Spout
- Origin Pulse
- Hydro Pump
- Thunder

Calyrex-Ice @ Loaded Dice
Ability: As One (Glastrier)
Level: 50
Tera Type: Grass
EVs: 252 HP / 252 Atk / 4 SpD
Brave Nature
IVs: 0 Spe
- Icicle Spear
- Bullet Seed
- Trick Room
- Protect

Incineroar @ Eject Button
Ability: Intimidate
Level: 50
Tera Type: Flying
EVs: 252 HP / 4 SpD / 252 Spe
Jolly Nature
- Knock Off
- Helping Hand
- Parting Shot
- Fake Out

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 252 HP / 180 Def / 76 SpD
Sassy Nature
IVs: 0 Atk / 0 Spe
- Pollen Puff
- Spore
- Rage Powder
- Protect

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 244 HP / 4 Def / 116 SpA / 132 SpD / 12 Spe
Modest Nature
IVs: 20 Atk
- Volt Switch
- Draco Meteor
- Snarl
- Thunderclap

Iron Treads @ Life Orb
Ability: Quark Drive
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- High Horsepower
- Steel Roller
- Knock Off
- Protect
""",
        """
Miraidon @ Choice Specs
Ability: Hadron Engine
Tera Type: Fairy
EVs: 28 HP / 28 Def / 196 SpA / 4 SpD / 252 Spe
Timid Nature
- Volt Switch
- Electro Drift
- Draco Meteor
- Dazzling Gleam

Zamazenta @ Rusted Shield
Ability: Dauntless Shield
Tera Type: Ghost
EVs: 236 HP / 4 Atk / 244 Def / 4 SpD / 20 Spe
Impish Nature
IVs: 30 SpA
- Protect
- Body Press
- Iron Head
- Wide Guard

Grimmsnarl @ Light Clay
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 244 HP / 196 Def / 68 SpD
Careful Nature
- Spirit Break
- Reflect
- Light Screen
- Thunder Wave

Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Level: 60
Tera Type: Stellar
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Protect
- Icicle Crash
- Crunch
- Sucker Punch

Volcarona @ Leftovers
Ability: Flame Body
Level: 59
Tera Type: Dragon
EVs: 252 HP / 100 Def / 20 SpA / 4 SpD / 132 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Flamethrower
- Struggle Bug
- Quiver Dance

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 58
Tera Type: Water
EVs: 76 HP / 156 Atk / 12 Def / 140 SpD / 124 Spe
Adamant Nature
- Wild Charge
- Drain Punch
- Fake Out
- Low Kick
""",
        """
Amoonguss (F) @ Rocky Helmet
Ability: Regenerator
Level: 59
Tera Type: Dark
EVs: 244 HP / 188 Def / 76 SpD
Calm Nature
IVs: 0 Atk / 16 Spe
- Spore
- Rage Powder
- Pollen Puff
- Protect

Calyrex-Ice @ Leftovers
Ability: As One (Glastrier)
Level: 80
Tera Type: Fairy
EVs: 252 HP / 100 Def / 156 SpD
Relaxed Nature
IVs: 16 Spe
- Glacial Lance
- Leech Seed
- Trick Room
- Protect

Kyogre @ Mystic Water
Ability: Drizzle
Tera Type: Grass
EVs: 52 HP / 4 Def / 236 SpA / 4 SpD / 212 Spe
Modest Nature
IVs: 0 Atk
- Water Spout
- Origin Pulse
- Hydro Pump
- Protect

Grimmsnarl @ Light Clay
Ability: Prankster
Level: 57
Tera Type: Ghost
EVs: 252 HP / 4 Atk / 108 Def / 116 SpD / 28 Spe
Careful Nature
- Spirit Break
- Sucker Punch
- Reflect
- Light Screen

Flutter Mane @ Focus Sash
Ability: Protosynthesis
Level: 86
Tera Type: Fairy
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Icy Wind
- Shadow Ball
- Moonblast
- Taunt

Basculegion @ Life Orb
Ability: Swift Swim
Tera Type: Ghost
EVs: 100 HP / 252 Atk / 28 Def / 20 SpD / 108 Spe
Adamant Nature
- Wave Crash
- Last Respects
- Aqua Jet
- Protect
""",
        """
Calyrex-Ice @ Leftovers
Ability: As One (Glastrier)
Level: 50
Tera Type: Water
EVs: 252 HP / 36 Atk / 4 Def / 196 SpD / 20 Spe
Adamant Nature
- Glacial Lance
- Leech Seed
- Trick Room
- Protect

Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 236 HP / 36 Def / 36 SpA / 132 SpD / 68 Spe
Modest Nature
- Electro Drift
- Volt Switch
- Draco Meteor
- Dazzling Gleam

Grimmsnarl @ Light Clay
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 252 HP / 4 Atk / 124 Def / 116 SpD / 12 Spe
Careful Nature
- Spirit Break
- Thunder Wave
- Reflect
- Light Screen

Urshifu-Rapid-Strike @ Choice Band
Ability: Unseen Fist
Level: 50
Tera Type: Ghost
EVs: 108 HP / 196 Atk / 4 Def / 180 SpD / 20 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- U-turn
- Aqua Jet

Incineroar @ Assault Vest
Ability: Intimidate
Level: 50
Tera Type: Grass
EVs: 180 HP / 4 Atk / 60 Def / 12 SpD / 252 Spe
Jolly Nature
- Flare Blitz
- Knock Off
- U-turn
- Fake Out

Landorus @ Life Orb
Ability: Sheer Force
Level: 50
Tera Type: Poison
EVs: 252 HP / 4 Def / 116 SpA / 132 SpD / 4 Spe
Modest Nature
IVs: 0 Atk
- Earth Power
- Sludge Bomb
- Taunt
- Protect
""",
        """
Weezing-Galar @ Covert Cloak
Ability: Neutralizing Gas
Level: 50
Tera Type: Water
EVs: 252 HP / 220 SpD / 36 Spe
Careful Nature
- Play Rough
- Taunt
- Will-O-Wisp
- Protect

Koraidon @ Ability Shield
Ability: Orichalcum Pulse
Level: 50
Tera Type: Fire
EVs: 252 HP / 156 Atk / 4 Def / 60 SpD / 36 Spe
Adamant Nature
- Flare Blitz
- Flame Charge
- Collision Course
- Protect

Walking Wake @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Water
EVs: 108 HP / 164 SpA / 236 Spe
Timid Nature
- Hydro Steam
- Draco Meteor
- Snarl
- Aqua Jet

Calyrex-Shadow @ Focus Sash
Ability: As One (Spectrier)
Level: 50
Tera Type: Ghost
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Psychic
- Encore
- Protect

Chi-Yu @ Choice Scarf
Ability: Beads of Ruin
Level: 50
Tera Type: Ghost
EVs: 52 HP / 4 Def / 196 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Heat Wave
- Flamethrower
- Dark Pulse
- Snarl

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Bug
EVs: 244 HP / 196 Def / 68 SpD
Careful Nature
- Knock Off
- Fake Out
- Parting Shot
- Protect
""",
        """
Calyrex-Ice @ Leftovers
Ability: As One (Glastrier)
Level: 50
Tera Type: Water
EVs: 236 HP / 36 Atk / 236 SpD
Adamant Nature
- Glacial Lance
- Leech Seed
- Trick Room
- Protect

Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 236 HP / 52 Def / 124 SpA / 68 SpD / 28 Spe
Modest Nature
- Volt Switch
- Dazzling Gleam
- Electro Drift
- Draco Meteor

Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Ghost
EVs: 108 HP / 156 Atk / 4 Def / 116 SpD / 124 Spe
Adamant Nature
- Facade
- Crunch
- Headlong Rush
- Protect

Volcarona @ Rocky Helmet
Ability: Flame Body
Level: 50
Tera Type: Water
EVs: 252 HP / 196 Def / 60 SpD
Bold Nature
- Struggle Bug
- Overheat
- Rage Powder
- Tailwind

Grimmsnarl @ Light Clay
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 236 HP / 4 Atk / 140 Def / 116 SpD / 12 Spe
Careful Nature
- Spirit Break
- Thunder Wave
- Reflect
- Light Screen

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 50
Tera Type: Bug
EVs: 236 Atk / 236 SpD / 36 Spe
Adamant Nature
- Fake Out
- Heavy Slam
- Low Kick
- Wild Charge
""",
        """
Lunala @ Electric Seed
Ability: Shadow Shield
Level: 50
Tera Type: Fairy
EVs: 132 HP / 172 Def / 180 SpA / 12 SpD / 12 Spe
Modest Nature
IVs: 0 Atk
- Moongeist Beam
- Moonblast
- Trick Room
- Wide Guard

Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Ghost
EVs: 140 HP / 252 Atk / 44 Def / 4 SpA / 68 SpD
Brave Nature
IVs: 0 Spe
- Headlong Rush
- Facade
- Earthquake
- Protect

Urshifu-Rapid-Strike @ Choice Band
Ability: Unseen Fist
Level: 50
Tera Type: Ghost
EVs: 84 HP / 212 Atk / 4 Def / 4 SpD / 204 Spe
Adamant Nature
- Surging Strikes
- U-turn
- Aqua Jet
- Close Combat

Miraidon @ Assault Vest
Ability: Hadron Engine
Level: 50
Tera Type: Electric
EVs: 252 HP / 20 Def / 212 SpA / 4 SpD / 20 Spe
Modest Nature
- Electro Drift
- Volt Switch
- Draco Meteor
- Snarl

Grimmsnarl @ Light Clay
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 228 HP / 4 Atk / 156 Def / 116 SpD / 4 Spe
Careful Nature
- Reflect
- Spirit Break
- Light Screen
- Thunder Wave

Incineroar @ Rocky Helmet
Ability: Intimidate
Level: 50
Tera Type: Bug
EVs: 252 HP / 252 Def / 4 SpD
Impish Nature
IVs: 29 Spe
- Fake Out
- Parting Shot
- Will-O-Wisp
- Knock Off
""",
        """
Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 252 HP / 52 Def / 116 SpA / 76 SpD / 12 Spe
Modest Nature
- Electro Drift
- Draco Meteor
- Dazzling Gleam
- Volt Switch

Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Normal
EVs: 236 HP / 196 Atk / 4 Def / 12 SpD / 60 Spe
Adamant Nature
- Glacial Lance
- High Horsepower
- Trick Room
- Protect

Volcarona @ Sitrus Berry
Ability: Flame Body
Level: 50
Tera Type: Dragon
EVs: 252 HP / 220 Def / 36 Spe
Modest Nature
IVs: 0 Atk
- Overheat
- Struggle Bug
- Rage Powder
- Protect

Urshifu-Rapid-Strike @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Detect

Archaludon @ Power Herb
Ability: Sturdy
Level: 50
Tera Type: Stellar
EVs: 252 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Meteor Beam
- Draco Meteor
- Flash Cannon
- Protect

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 50
Tera Type: Water
EVs: 76 HP / 156 Atk / 4 Def / 236 SpD / 28 Spe
Adamant Nature
- Wild Charge
- Low Kick
- Drain Punch
- Fake Out
""",
        """
ゆいな (Miraidon) @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 252 HP / 76 Def / 36 SpA / 116 SpD / 28 Spe
Modest Nature
- Electro Drift
- Draco Meteor
- Dazzling Gleam
- Volt Switch

ゆつき (Lunala) @ Leftovers
Ability: Shadow Shield
Level: 50
Tera Type: Fairy
EVs: 156 HP / 164 Def / 180 SpA / 4 SpD / 4 Spe
Modest Nature
IVs: 0 Atk / 27 Spe
- Moongeist Beam
- Moonblast
- Trick Room
- Protect

なぎちゃん (Rillaboom) @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 204 HP / 36 Atk / 4 Def / 252 SpD / 12 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- U-turn
- Fake Out

すーじー (Incineroar) @ Rocky Helmet
Ability: Intimidate
Level: 50
Tera Type: Bug
EVs: 252 HP / 252 Def / 4 SpD
Impish Nature
IVs: 25 Spe
- Fake Out
- Parting Shot
- Taunt
- Knock Off

Kanemiku (Urshifu-Rapid-Strike) @ Choice Band
Ability: Unseen Fist
Level: 50
Tera Type: Ghost
EVs: 108 HP / 212 Atk / 4 Def / 180 SpD / 4 Spe
Adamant Nature
- Surging Strikes
- U-turn
- Aqua Jet
- Close Combat

むらやま (Grimmsnarl) @ Light Clay
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 252 HP / 4 Atk / 116 Def / 124 SpD / 12 Spe
Careful Nature
- Spirit Break
- Reflect
- Light Screen
- Thunder Wave
""",
        """
Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 236 HP / 4 Def / 124 SpA / 68 SpD / 76 Spe
Modest Nature
IVs: 20 Atk
- Thunderclap
- Dragon Pulse
- Electroweb
- Volt Switch

Groudon @ Clear Amulet
Ability: Drought
Level: 50
Tera Type: Fire
EVs: 172 HP / 180 Atk / 156 Spe
Adamant Nature
- Precipice Blades
- Heat Crash
- High Horsepower
- Protect

Jumpluff @ Wide Lens
Ability: Chlorophyll
Level: 50
Tera Type: Dark
EVs: 252 HP / 4 Def / 252 Spe
Timid Nature
IVs: 0 Atk
- Tailwind
- Encore
- Sleep Powder
- Rage Powder

Calyrex-Shadow @ Focus Sash
Ability: As One (Spectrier)
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Psychic
- Protect
- Nasty Plot

Chi-Yu @ Choice Scarf
Ability: Beads of Ruin
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Heat Wave
- Dark Pulse
- Overheat
- Snarl

Flutter Mane @ Choice Specs
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 100 HP / 68 Def / 84 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Dazzling Gleam
- Moonblast
- Shadow Ball
- Trick Room
""",
        """
Ducktile's sheep (Cresselia) @ Electric Seed
Ability: Levitate
Level: 50
Tera Type: Fairy
EVs: 228 HP / 76 Def / 36 SpA / 156 SpD / 12 Spe
Modest Nature
IVs: 0 Atk
- Psychic
- Lunar Blessing
- Helping Hand
- Trick Room

Duckhand (Iron Hands) @ Assault Vest
Ability: Quark Drive
Level: 50
Tera Type: Water
EVs: 92 HP / 172 Atk / 4 Def / 236 SpD / 4 Spe
Adamant Nature
- Drain Punch
- Wild Charge
- Low Kick
- Fake Out

Ducktile's horse (Calyrex-Shadow) @ Life Orb
Ability: As One (Spectrier)
Level: 50
Tera Type: Dark
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Psychic
- Encore
- Protect

Ducktile's bike (Miraidon) @ Choice Scarf
Ability: Hadron Engine
Level: 50
Tera Type: Electric
EVs: 100 HP / 20 Def / 252 SpA / 4 SpD / 132 Spe
Timid Nature
- Electro Drift
- Volt Switch
- Draco Meteor
- Snarl

Ducktile (Ursaluna) @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Ghost
EVs: 156 HP / 156 Atk / 196 SpD
Brave Nature
IVs: 0 Spe
- Facade
- Headlong Rush
- Earthquake
- Protect

Faketile (Sneasler) @ Focus Sash
Ability: Unburden
Level: 50
Tera Type: Fighting
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Close Combat
- Fake Out
- Feint
- Dire Claw
""",
        """
Kyogre @ Splash Plate
Ability: Drizzle
Level: 50
Tera Type: Grass
EVs: 52 HP / 4 Def / 196 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Water Spout
- Hydro Pump
- Thunder
- Protect

Calyrex-Ice @ Never-Melt Ice
Ability: As One (Glastrier)
Level: 50
Tera Type: Grass
EVs: 252 HP / 116 Atk / 4 Def / 100 SpD / 36 Spe
Adamant Nature
- Glacial Lance
- Seed Bomb
- Trick Room
- Protect

Urshifu-Rapid-Strike @ Life Orb
Ability: Unseen Fist
Level: 50
Tera Type: Grass
EVs: 108 HP / 156 Atk / 4 Def / 156 SpD / 84 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Protect

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 236 HP / 164 Def / 108 SpD
Bold Nature
IVs: 0 Atk / 12 Spe
- Pollen Puff
- Spore
- Rage Powder
- Protect

Iron Jugulis @ Booster Energy
Ability: Quark Drive
Level: 50
Tera Type: Steel
EVs: 236 HP / 28 Def / 4 SpA / 20 SpD / 220 Spe
Timid Nature
IVs: 0 Atk
- Hurricane
- Snarl
- Tailwind
- Taunt

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 244 HP / 116 Atk / 4 Def / 124 SpD / 20 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- Fake Out
- U-turn
""",
        """
Terapagos-Terastal @ Leftovers
Ability: Tera Shell
Level: 50
Tera Type: Stellar
EVs: 172 HP / 100 Def / 76 SpA / 12 SpD / 148 Spe
Modest Nature
IVs: 15 Atk
- Tera Starstorm
- Dark Pulse
- Calm Mind
- Protect

Zamazenta-Crowned @ Rusted Shield
Ability: Dauntless Shield
Level: 50
Tera Type: Dragon
EVs: 204 HP / 124 Def / 180 Spe
Jolly Nature
IVs: 0 Atk
- Body Press
- Wide Guard
- Imprison
- Protect

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Water
EVs: 244 HP / 4 Atk / 188 Def / 68 SpD / 4 Spe
Impish Nature
- Knock Off
- Parting Shot
- Will-O-Wisp
- Fake Out

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Water
EVs: 252 HP / 116 Atk / 28 Def / 60 SpD / 52 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- U-turn
- Fake Out

Smeargle @ Focus Sash
Ability: Moody
Level: 50
Tera Type: Ghost
EVs: 252 HP / 4 Def / 252 Spe
Timid Nature
IVs: 0 Atk
- Spore
- Lunar Blessing
- Follow Me
- Topsy-Turvy

Tornadus @ Ability Shield
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 228 HP / 52 Def / 36 SpA / 4 SpD / 188 Spe
Modest Nature
IVs: 0 Atk
- Bleakwind Storm
- Rain Dance
- Tailwind
- Protect
""",
        """
Zacian-Crowned @ Rusted Sword
Ability: Intrepid Sword
Level: 50
Tera Type: Fairy
EVs: 244 HP / 92 Atk / 4 Def / 4 SpD / 164 Spe
Adamant Nature
- Behemoth Blade
- Play Rough
- Substitute
- Protect

Kyogre @ Mystic Water
Ability: Drizzle
Level: 50
Tera Type: Grass
EVs: 244 HP / 4 Def / 156 SpA / 4 SpD / 100 Spe
Modest Nature
IVs: 0 Atk
- Water Spout
- Origin Pulse
- Ice Beam
- Protect

Tornadus @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 252 HP / 172 Def / 4 SpA / 76 SpD / 4 Spe
Bold Nature
IVs: 0 Atk
- Bleakwind Storm
- Tailwind
- Rain Dance
- Taunt

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Steel
EVs: 252 HP / 156 Def / 100 SpD
Bold Nature
IVs: 0 Atk / 27 Spe
- Pollen Puff
- Spore
- Rage Powder
- Protect

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Water
EVs: 236 HP / 4 Atk / 76 Def / 108 SpD / 84 Spe
Impish Nature
- Knock Off
- Fake Out
- Will-O-Wisp
- Parting Shot

Urshifu-Rapid-Strike @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- U-turn
- Coaching
""",
        """
Whimsicott (F) @ Covert Cloak
Ability: Prankster
Level: 50
Shiny: Yes
Tera Type: Water
EVs: 116 HP / 4 Def / 4 SpA / 132 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Fake Tears
- Moonblast
- Tailwind
- Encore

Calyrex-Shadow @ Focus Sash
Ability: As One (Spectrier)
Level: 50
Tera Type: Ghost
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Psychic
- Disable
- Protect

Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 132 HP / 4 Def / 116 SpA / 4 SpD / 252 Spe
Timid Nature
- Volt Switch
- Electro Drift
- Draco Meteor
- Dazzling Gleam

Incineroar @ Rocky Helmet
Ability: Intimidate
Level: 50
Tera Type: Water
EVs: 172 HP / 156 SpD / 180 Spe
Careful Nature
- Knock Off
- Will-O-Wisp
- Parting Shot
- Fake Out

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 50
Shiny: Yes
Tera Type: Bug
EVs: 124 HP / 244 Atk / 140 SpD
Brave Nature
IVs: 0 Spe
- Drain Punch
- Low Kick
- Wild Charge
- Fake Out

Chi-Yu @ Choice Scarf
Ability: Beads of Ruin
Level: 50
Tera Type: Ghost
EVs: 4 Def / 252 SpA / 252 Spe
Modest Nature
IVs: 0 Atk
- Heat Wave
- Flamethrower
- Snarl
- Ruination
""",
        """
Farigiraf @ Electric Seed
Ability: Armor Tail
Level: 50
Tera Type: Water
EVs: 180 HP / 236 Def / 4 SpA / 76 SpD / 12 Spe
Bold Nature
IVs: 0 Atk
- Foul Play
- Psychic Noise
- Trick Room
- Helping Hand

RAOOOOOOOW (Miraidon) @ Choice Scarf
Ability: Hadron Engine
Level: 50
Tera Type: Electric
EVs: 204 HP / 28 Def / 252 SpA / 12 SpD / 12 Spe
Modest Nature
- Snarl
- Electro Drift
- Draco Meteor
- Volt Switch

good against sun (Rayquaza) @ Clear Amulet
Ability: Air Lock
Level: 50
Tera Type: Normal
EVs: 140 HP / 252 Atk / 4 Def / 28 SpD / 84 Spe
Adamant Nature
- Protect
- Dragon Ascent
- Extreme Speed
- Swords Dance

Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Protect
- Throat Chop
- Icicle Crash
- Sucker Punch

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 50
Tera Type: Bug
EVs: 108 HP / 204 Atk / 60 Def / 132 SpD
Brave Nature
IVs: 0 Spe
- Drain Punch
- Wild Charge
- Low Kick
- Fake Out

Volcarona @ Rocky Helmet
Ability: Flame Body
Level: 50
Tera Type: Dragon
EVs: 228 HP / 244 Def / 4 SpA / 28 SpD / 4 Spe
Bold Nature
IVs: 0 Atk
- Rage Powder
- Flamethrower
- Protect
- Struggle Bug
""",
        """
Glimmora @ Power Herb
Ability: Toxic Debris
Level: 50
Shiny: Yes
Tera Type: Water
EVs: 172 HP / 156 SpA / 180 Spe
Modest Nature
- Mortal Spin
- Spiky Shield
- Meteor Beam
- Earth Power

Calyrex-Ice @ Leftovers
Ability: As One (Glastrier)
Level: 50
Tera Type: Water
EVs: 244 HP / 116 Atk / 68 Def / 76 SpD
Brave Nature
IVs: 0 Spe
- Leech Seed
- Glacial Lance
- Protect
- Trick Room

Zamazenta-Crowned @ Rusted Shield
Ability: Dauntless Shield
Level: 50
Tera Type: Dragon
EVs: 204 HP / 236 Def / 68 Spe
Impish Nature
- Wide Guard
- Heavy Slam
- Body Press
- Protect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Shiny: Yes
Tera Type: Fire
EVs: 204 HP / 116 Atk / 4 Def / 76 SpD / 108 Spe
Adamant Nature
- Fake Out
- Wood Hammer
- Grassy Glide
- High Horsepower

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Shiny: Yes
Tera Type: Fire
EVs: 252 HP / 180 Def / 76 SpD
Sassy Nature
IVs: 0 Atk / 0 Spe
- Rage Powder
- Spore
- Clear Smog
- Pollen Puff

Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Ghost
EVs: 252 HP / 252 Atk / 4 SpD
Brave Nature
IVs: 2 Spe
- Facade
- Headlong Rush
- Close Combat
- Protect
""",
        """
Miraidon @ Choice Specs
Ability: Hadron Engine
Tera Type: Electric
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
- Electro Drift
- Discharge
- Volt Switch
- Draco Meteor

Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Ground
EVs: 252 HP / 252 Atk / 4 SpD
Brave Nature
IVs: 0 Spe
- Glacial Lance
- High Horsepower
- Trick Room
- Protect

Farigiraf (F) @ Electric Seed
Ability: Armor Tail
Shiny: Yes
Tera Type: Ground
EVs: 180 HP / 236 Def / 92 SpD
Bold Nature
IVs: 0 Atk
- Psychic Noise
- Foul Play
- Helping Hand
- Trick Room

Chi-Yu @ Choice Scarf
Ability: Beads of Ruin
Tera Type: Ground
EVs: 252 SpA / 4 SpD / 252 Spe
Modest Nature
- Dark Pulse
- Overheat
- Snarl
- Tera Blast

Ursaluna (F) @ Flame Orb
Ability: Guts
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 252 HP / 252 Atk / 4 SpD
Adamant Nature
- Headlong Rush
- Earthquake
- Facade
- Protect

Gardevoir (F) @ Focus Sash
Ability: Telepathy
Shiny: Yes
Tera Type: Normal
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Psychic
- Moonblast
- Dazzling Gleam
- Protect
""",
        """
Zacian-Crowned @ Rusted Sword
Ability: Intrepid Sword
Level: 50
Tera Type: Normal
EVs: 76 HP / 252 Atk / 4 Def / 4 SpD / 172 Spe
Jolly Nature
- Behemoth Blade
- Play Rough
- Substitute
- Protect

Koraidon @ Clear Amulet
Ability: Orichalcum Pulse
Level: 50
Tera Type: Fire
EVs: 252 HP / 196 Atk / 4 Def / 44 SpD / 12 Spe
Adamant Nature
- Flare Blitz
- Scale Shot
- Collision Course
- Protect

Walking Wake @ Life Orb
Ability: Protosynthesis
Level: 50
Tera Type: Water
EVs: 4 HP / 4 Def / 244 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Hydro Steam
- Draco Meteor
- Snarl
- Protect

Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Icicle Crash
- Crunch
- Sucker Punch
- Protect

Ogerpon-Cornerstone (F) @ Cornerstone Mask
Ability: Sturdy
Level: 50
Tera Type: Rock
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Ivy Cudgel
- Power Whip
- Follow Me
- Spiky Shield

Thundurus @ Sitrus Berry
Ability: Prankster
Level: 50
Tera Type: Steel
EVs: 252 HP / 100 Def / 156 SpD
Calm Nature
IVs: 0 Atk
- Wildbolt Storm
- Thunder Wave
- Eerie Impulse
- Leer
""",
        """
Zamazenta-Crowned @ Rusted Shield
Ability: Dauntless Shield
Level: 50
Tera Type: Dragon
EVs: 252 HP / 124 Def / 132 Spe
Jolly Nature
- Body Press
- Imprison
- Protect
- Wide Guard

Koraidon @ Clear Amulet
Ability: Orichalcum Pulse
Level: 50
Tera Type: Fire
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Close Combat
- Flare Blitz
- Protect
- Flame Charge

Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Ice Spinner
- Crunch
- Protect
- Sucker Punch

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 252 HP / 236 Def / 20 SpD
Relaxed Nature
IVs: 0 Atk
- Pollen Puff
- Spore
- Protect
- Rage Powder

Flutter Mane @ Choice Specs
Ability: Protosynthesis
Level: 50
Tera Type: Normal
EVs: 116 HP / 76 Def / 116 SpA / 4 SpD / 196 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Shadow Ball
- Dazzling Gleam
- Icy Wind

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Water
EVs: 196 HP / 108 Def / 196 SpA / 4 SpD / 4 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Draco Meteor
- Thunderclap
- Electroweb
""",
        """
Koraidon @ Ability Shield
Ability: Orichalcum Pulse
Tera Type: Fire
EVs: 236 HP / 116 Atk / 4 Def / 68 SpD / 84 Spe
Adamant Nature
- Protect
- Flare Blitz
- Collision Course
- Flame Charge

Calyrex-Shadow @ Focus Sash
Ability: As One (Spectrier)
Level: 80
Tera Type: Ghost
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Psychic
- Encore
- Protect

Weezing-Galar (M) @ Covert Cloak
Ability: Neutralizing Gas
Shiny: Yes
Tera Type: Water
EVs: 252 HP / 4 Atk / 12 Def / 212 SpD / 28 Spe
Impish Nature
- Protect
- Poison Gas
- Play Rough
- Taunt

Chi-Yu @ Choice Scarf
Ability: Beads of Ruin
Level: 60
Tera Type: Ghost
EVs: 52 HP / 4 Def / 196 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Heat Wave
- Snarl
- Flamethrower
- Ruination

Walking Wake @ Assault Vest
Ability: Protosynthesis
Level: 75
Tera Type: Water
EVs: 52 HP / 4 Def / 196 SpA / 4 SpD / 252 Spe
Timid Nature
- Hydro Steam
- Draco Meteor
- Snarl
- Aqua Jet

Brute Bonnet @ Rocky Helmet
Ability: Protosynthesis
Shiny: Yes
Tera Type: Fire
EVs: 252 HP / 4 Atk / 188 Def / 64 SpD
Relaxed Nature
- Sucker Punch
- Spore
- Rage Powder
- Seed Bomb
""",
        """
Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 108 HP / 52 Def / 212 SpA / 4 SpD / 132 Spe
Timid Nature
- Electro Drift
- Volt Switch
- Draco Meteor
- Dazzling Gleam

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 236 HP / 4 Atk / 236 Def / 28 SpD / 4 Spe
Adamant Nature
- Fake Out
- U-turn
- Wood Hammer
- Grassy Glide

Incineroar @ Rocky Helmet
Ability: Intimidate
Level: 50
Tera Type: Bug
EVs: 244 HP / 4 Atk / 236 Def / 12 SpD / 12 Spe
Impish Nature
- Fake Out
- Will-O-Wisp
- Knock Off
- Parting Shot

Calyrex-Ice @ Leftovers
Ability: As One (Glastrier)
Level: 50
Tera Type: Fairy
EVs: 244 HP / 4 Atk / 68 Def / 180 SpD / 12 Spe
Adamant Nature
- Leech Seed
- Protect
- Glacial Lance
- Trick Room

Annihilape @ Choice Scarf
Ability: Defiant
Level: 50
Tera Type: Grass
EVs: 220 HP / 52 Atk / 4 Def / 4 SpD / 220 Spe
Jolly Nature
- Coaching
- Rage Fist
- Close Combat
- Final Gambit

Urshifu @ Covert Cloak
Ability: Unseen Fist
Level: 50
Tera Type: Stellar
EVs: 132 HP / 236 Atk / 4 Def / 76 SpD / 60 Spe
Adamant Nature
- Wicked Blow
- Close Combat
- Detect
- Sucker Punch
""",
        """
Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Fire
EVs: 252 HP / 196 Atk / 60 SpD
Brave Nature
IVs: 0 Spe
- Glacial Lance
- High Horsepower
- Trick Room
- Protect

Scraggy @ Eviolite
Ability: Intimidate
Level: 50
Tera Type: Poison
EVs: 4 HP / 252 Def / 252 SpD
Sassy Nature
IVs: 0 Spe
- Foul Play
- Endeavor
- Coaching
- Fake Out

Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 236 HP / 4 Def / 252 SpA / 4 SpD / 12 Spe
Modest Nature
- Volt Switch
- Dazzling Gleam
- Electro Drift
- Draco Meteor

Farigiraf @ Electric Seed
Ability: Armor Tail
Level: 50
Tera Type: Water
EVs: 228 HP / 164 Def / 116 SpD
Bold Nature
IVs: 0 Atk
- Psychic
- Helping Hand
- Trick Room
- Foul Play

Iron Treads @ Life Orb
Ability: Quark Drive
Level: 50
Tera Type: Ground
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- High Horsepower
- Iron Head
- Knock Off
- Protect

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 50
Tera Type: Water
EVs: 76 HP / 180 Atk / 12 Def / 236 SpD
Brave Nature
IVs: 0 Spe
- Low Kick
- Fake Out
- Drain Punch
- Wild Charge
""",
        """
Éclipse (Lunala) @ Power Herb
Ability: Shadow Shield
Level: 50
Shiny: Yes
Tera Type: Water
EVs: 108 HP / 108 Def / 212 SpA / 28 SpD / 52 Spe
Modest Nature
IVs: 0 Atk
- Moongeist Beam
- Meteor Beam
- Wide Guard
- Trick Room

Mánagarmr (Zacian-Crowned) @ Rusted Sword
Ability: Intrepid Sword
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 68 HP / 252 Atk / 4 Def / 4 SpD / 180 Spe
Jolly Nature
- Behemoth Blade
- Play Rough
- Sacred Sword
- Protect

Luna Obscura (Roaring Moon) @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Flying
EVs: 44 HP / 196 Atk / 4 Def / 12 SpD / 252 Spe
Jolly Nature
- Knock Off
- Acrobatics
- Tailwind
- Protect

Blue Moon (Ogerpon-Wellspring) (F) @ Wellspring Mask
Ability: Water Absorb
Level: 50
Tera Type: Water
EVs: 252 HP / 76 Atk / 36 Def / 132 SpD / 12 Spe
Adamant Nature
- Ivy Cudgel
- Wood Hammer
- Follow Me
- Spiky Shield

Harvest Moon (Landorus) @ Life Orb
Ability: Sheer Force
Level: 50
Tera Type: Water
EVs: 68 HP / 44 Def / 140 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Earth Power
- Sandsear Storm
- Sludge Bomb
- Protect

Sailor Moon (Pelipper) (F) @ Focus Sash
Ability: Drizzle
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 28 HP / 4 Def / 252 SpA / 4 SpD / 220 Spe
Modest Nature
IVs: 0 Atk
- Hurricane
- Muddy Water
- Wide Guard
- Protect
""",
        """
Tornadus @ Mental Herb
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 196 HP / 244 Def / 4 SpA / 20 SpD / 44 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Tailwind
- Bleakwind Storm
- Rain Dance

Zacian-Crowned @ Rusted Sword
Ability: Intrepid Sword
Level: 50
Tera Type: Normal
EVs: 188 HP / 156 Atk / 4 Def / 4 SpD / 156 Spe
Adamant Nature
- Protect
- Behemoth Blade
- Play Rough
- Substitute

Kyogre @ Assault Vest
Ability: Drizzle
Level: 50
Tera Type: Electric
EVs: 252 HP / 36 Def / 76 SpA / 4 SpD / 140 Spe
Modest Nature
IVs: 0 Atk
- Water Spout
- Origin Pulse
- Hydro Pump
- Ice Beam

Urshifu-Rapid-Strike @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 4 HP / 236 Atk / 4 Def / 12 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Coaching
- U-turn

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 228 HP / 204 Def / 76 SpD
Calm Nature
IVs: 0 Atk / 21 Spe
- Protect
- Rage Powder
- Spore
- Pollen Puff

Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Protect
- Ice Spinner
- Throat Chop
- Sucker Punch
""",
        """
Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 108 HP / 52 Def / 212 SpA / 4 SpD / 132 Spe
Timid Nature
- Electro Drift
- Dazzling Gleam
- Volt Switch
- Draco Meteor

Calyrex-Ice @ Leftovers
Ability: As One (Glastrier)
Level: 50
Tera Type: Water
EVs: 252 HP / 36 Atk / 4 Def / 180 SpD / 36 Spe
Adamant Nature
- Glacial Lance
- Leech Seed
- Trick Room
- Protect

Incineroar @ Assault Vest
Ability: Intimidate
Level: 50
Tera Type: Bug
EVs: 252 HP / 116 Atk / 36 Def / 28 SpD / 76 Spe
Adamant Nature
- Flare Blitz
- Knock Off
- U-turn
- Fake Out

Landorus @ Life Orb
Ability: Sheer Force
Level: 50
Tera Type: Poison
EVs: 220 HP / 4 Def / 252 SpA / 4 SpD / 28 Spe
Modest Nature
IVs: 0 Atk
- Sandsear Storm
- Earth Power
- Sludge Bomb
- Protect

Urshifu-Rapid-Strike @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- U-turn

Farigiraf @ Electric Seed
Ability: Armor Tail
Level: 50
Tera Type: Ground
EVs: 116 HP / 156 Def / 156 SpA / 76 SpD / 4 Spe
Modest Nature
IVs: 0 Atk
- Psychic
- Trick Room
- Helping Hand
- Foul Play
""",
    ],
}
