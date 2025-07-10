# teams from https://docs.google.com/spreadsheets/d/1axlwmzPA49rYkqXh7zHvAtSP-TKbM0ijGYBPRflLSWw/edit?gid=1168048410#gid=1168048410

import random

from poke_env.teambuilder import Teambuilder


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
        for team in [TEAMS[battle_format][t] for t in teams]:
            parsed_team = self.parse_showdown_team(team)
            packed_team = self.join_team(parsed_team)
            self.teams.append(packed_team)

    def yield_team(self) -> str:
        if self.toggle:
            return self.teams[self.toggle.next()]
        else:
            return random.choice(self.teams)


TEAMS = {
    "gen9vgc2025regiactual": [
        """
Urshifu-Rapid-Strike @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Ghost
EVs: 4 HP / 236 Atk / 4 Def / 12 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Coaching
- U-turn

Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Fire
EVs: 252 HP / 116 Atk / 4 Def / 92 SpD / 44 Spe
Adamant Nature
- Protect
- Glacial Lance
- High Horsepower
- Trick Room

Ogerpon-Cornerstone (F) @ Cornerstone Mask
Ability: Sturdy
Level: 50
Tera Type: Rock
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Spiky Shield
- Ivy Cudgel
- Follow Me
- Power Whip

Pelipper @ Focus Sash
Ability: Rain Dish
Level: 50
Tera Type: Ghost
EVs: 252 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Protect
- Weather Ball
- Hurricane
- Wide Guard

Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 12 HP / 44 Def / 196 SpA / 4 SpD / 252 Spe
Modest Nature
- Electro Drift
- Draco Meteor
- Dazzling Gleam
- Volt Switch

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 50
Tera Type: Bug
EVs: 92 HP / 156 Atk / 20 Def / 4 SpA / 236 SpD
Brave Nature
IVs: 0 Spe
- Drain Punch
- Low Kick
- Wild Charge
- Fake Out
""",
        """
Koraidon @ Life Orb
Ability: Orichalcum Pulse
Level: 50
Tera Type: Fire
EVs: 108 HP / 252 Atk / 4 Def / 12 SpD / 132 Spe
Jolly Nature
- Close Combat
- Flare Blitz
- Flame Charge
- Protect

Lunala @ Power Herb
Ability: Shadow Shield
Level: 50
Tera Type: Fairy
EVs: 220 HP / 12 Def / 180 SpA / 4 SpD / 92 Spe
Modest Nature
IVs: 0 Atk
- Moongeist Beam
- Meteor Beam
- Wide Guard
- Trick Room

Grimmsnarl @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Water
EVs: 252 HP / 164 Def / 36 SpD / 52 Spe
Calm Nature
IVs: 0 Atk
- Foul Play
- Reflect
- Light Screen
- Scary Face

Chi-Yu @ Choice Scarf
Ability: Beads of Ruin
Level: 50
Tera Type: Ghost
EVs: 68 HP / 4 Def / 252 SpA / 4 SpD / 180 Spe
Timid Nature
IVs: 0 Atk
- Heat Wave
- Dark Pulse
- Overheat
- Snarl

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

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 244 HP / 92 Def / 100 SpA / 4 SpD / 68 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Dragon Pulse
- Snarl
- Thunderclap""",
        """
Lunala @ Power Herb
Ability: Shadow Shield
Level: 50
Tera Type: Fairy
EVs: 244 HP / 44 Def / 180 SpA / 4 SpD / 36 Spe
Modest Nature
IVs: 0 Atk
- Moongeist Beam
- Meteor Beam
- Wide Guard
- Protect

Terapagos-Stellar @ Leftovers
Ability: Teraform Zero
Level: 50
Tera Type: Stellar
EVs: 172 HP / 156 Def / 100 SpA / 4 SpD / 76 Spe
Modest Nature
IVs: 15 Atk
- Calm Mind
- Tera Starstorm
- Substitute
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

Incineroar @ Rocky Helmet
Ability: Intimidate
Level: 50
Tera Type: Bug
EVs: 252 HP / 188 Def / 68 SpD
Impish Nature
- Fake Out
- Knock Off
- Will-O-Wisp
- Parting Shot

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 244 HP / 148 Atk / 4 Def / 108 SpD / 4 Spe
Adamant Nature
- Fake Out
- Wood Hammer
- Grassy Glide
- U-turn

Scream Tail @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Dark
EVs: 228 HP / 148 Def / 4 SpA / 20 SpD / 108 Spe
Timid Nature
IVs: 0 Atk
- Encore
- Disable
- Dazzling Gleam
- Protect""",
        """
Groudon @ Clear Amulet
Ability: Drought
Tera Type: Fire
EVs: 252 HP / 76 Atk / 44 Def / 108 SpD / 28 Spe
Adamant Nature
- Precipice Blades
- Heat Crash
- Protect
- High Horsepower

Lunala @ Power Herb
Ability: Shadow Shield
Shiny: Yes
Tera Type: Water
EVs: 228 HP / 12 Def / 100 SpA / 116 SpD / 52 Spe
Modest Nature
IVs: 0 Atk
- Moongeist Beam
- Meteor Beam
- Wide Guard
- Trick Room

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Tera Type: Fairy
EVs: 148 HP / 148 Def / 100 SpA / 52 SpD / 60 Spe
Modest Nature
IVs: 20 Atk
- Volt Switch
- Thunderclap
- Draco Meteor
- Electroweb

Incineroar @ Rocky Helmet
Ability: Intimidate
Tera Type: Bug
EVs: 252 HP / 188 Def / 68 SpD
Relaxed Nature
IVs: 24 Spe
- Fake Out
- Knock Off
- Will-O-Wisp
- U-turn

Iron Valiant @ Booster Energy
Ability: Quark Drive
Shiny: Yes
Tera Type: Ground
EVs: 124 HP / 4 Atk / 4 Def / 204 SpD / 172 Spe
Jolly Nature
- Spirit Break
- Wide Guard
- Coaching
- Icy Wind

Ogerpon-Hearthflame @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 228 HP / 12 Atk / 244 Def / 4 SpD / 20 Spe
Impish Nature
- Ivy Cudgel
- Horn Leech
- Follow Me
- Spiky Shield""",
        """
Indeedee-F @ Rocky Helmet
Ability: Psychic Surge
Level: 50
Shiny: Yes
Tera Type: Fairy
EVs: 252 HP / 252 Def / 4 SpD
Bold Nature
IVs: 0 Atk
- Psychic
- Trick Room
- Follow Me
- Helping Hand

Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Fire
EVs: 252 HP / 196 Atk / 4 Def / 28 SpD / 28 Spe
Adamant Nature
- Glacial Lance
- High Horsepower
- Trick Room
- Protect

Ursaluna-Bloodmoon @ Life Orb
Ability: Mind's Eye
Level: 50
Tera Type: Normal
EVs: 244 HP / 4 Def / 252 SpA / 4 SpD / 4 Spe
Modest Nature
IVs: 0 Atk
- Earth Power
- Hyper Voice
- Blood Moon
- Protect

Smeargle (M) @ Focus Sash
Ability: Own Tempo
Level: 50
Shiny: Yes
Tera Type: Grass
EVs: 236 HP / 196 Def / 76 SpD
Relaxed Nature
IVs: 0 Spe
- Follow Me
- Fake Out
- Decorate
- Spore

Urshifu @ Choice Band
Ability: Unseen Fist
Level: 50
Tera Type: Grass
EVs: 252 HP / 252 Atk / 4 Def
Brave Nature
IVs: 0 Spe
- Wicked Blow
- Sucker Punch
- Close Combat
- Iron Head

Lunala @ Power Herb
Ability: Shadow Shield
Level: 50
Tera Type: Grass
EVs: 220 HP / 236 SpA / 52 Spe
Modest Nature
IVs: 0 Atk
- Expanding Force
- Trick Room
- Moongeist Beam
- Meteor Beam""",
        """
Duke (Zamazenta-Crowned) @ Rusted Shield
Ability: Dauntless Shield
Level: 50
Tera Type: Dragon
EVs: 12 HP / 4 Atk / 236 Def / 4 SpD / 252 Spe
Impish Nature
- Body Press
- Heavy Slam
- Wide Guard
- Protect

Numb (Kyogre) @ Mystic Water
Ability: Drizzle
Level: 50
Shiny: Yes
Tera Type: Grass
EVs: 252 HP / 4 Def / 236 SpA / 4 SpD / 12 Spe
Modest Nature
IVs: 0 Atk
- Origin Pulse
- Ice Beam
- Water Spout
- Protect

Tree (Amoonguss) (M) @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 244 HP / 124 Def / 140 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Spore
- Rage Powder
- Pollen Puff
- Protect

Sugar (Chien-Pao) @ Focus Sash
Ability: Sword of Ruin
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Ice Spinner
- Sucker Punch
- Throat Chop
- Protect

Lauren (Urshifu-Rapid-Strike) (F) @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 132 HP / 76 Atk / 12 Def / 36 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- U-turn
- Rain Dance

Mudman (Tornadus) @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Steel
EVs: 252 HP / 236 Def / 4 SpA / 4 SpD / 12 Spe
Bold Nature
IVs: 0 Atk
- Bleakwind Storm
- Tailwind
- Taunt
- Rain Dance""",
        """
Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 44 HP / 12 Def / 196 SpA / 4 SpD / 252 Spe
Modest Nature
- Electro Drift
- Draco Meteor
- Volt Switch
- Dazzling Gleam

Whimsicott @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 236 HP / 20 Def / 4 SpA / 116 SpD / 132 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Tailwind
- Light Screen
- Encore

Ogerpon-Hearthflame (F) @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 188 HP / 76 Atk / 12 Def / 44 SpD / 188 Spe
Adamant Nature
- Ivy Cudgel
- Wood Hammer
- Follow Me
- Spiky Shield

Farigiraf @ Electric Seed
Ability: Armor Tail
Level: 50
Tera Type: Water
EVs: 236 HP / 108 Def / 4 SpA / 132 SpD / 28 Spe
Bold Nature
IVs: 0 Atk
- Foul Play
- Psychic Noise
- Trick Room
- Helping Hand

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 50
Tera Type: Water
EVs: 92 HP / 156 Atk / 20 Def / 4 SpA / 236 SpD
Brave Nature
IVs: 0 Spe
- Drain Punch
- Low Kick
- Wild Charge
- Fake Out

Calyrex-Ice @ Icicle Plate
Ability: As One (Glastrier)
Level: 50
Tera Type: Water
EVs: 252 HP / 44 Atk / 4 Def / 12 SpD / 196 Spe
Adamant Nature
- Protect
- Glacial Lance
- High Horsepower
- Trick Room""",
        """
Miraidon @ Choice Specs
Ability: Hadron Engine
Level: 50
Tera Type: Fairy
EVs: 196 HP / 4 Def / 196 SpA / 4 SpD / 108 Spe
Modest Nature
- Electro Drift
- Draco Meteor
- Volt Switch
- Dazzling Gleam

Calyrex-Shadow @ Focus Sash
Ability: As One (Spectrier)
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Psychic
- Encore
- Protect

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 50
Tera Type: Bug
EVs: 180 HP / 76 Atk / 252 SpD
Adamant Nature
- Low Kick
- Drain Punch
- Fake Out
- Heavy Slam

Whimsicott @ Covert Cloak
Ability: Prankster
Tera Type: Dark
EVs: 236 HP / 164 SpD / 108 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Tailwind
- Light Screen
- Encore

Chi-Yu @ Choice Scarf
Ability: Beads of Ruin
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
IVs: 0 Atk
- Heat Wave
- Dark Pulse
- Snarl
- Overheat

Farigiraf @ Electric Seed
Ability: Armor Tail
Level: 50
Tera Type: Water
EVs: 252 HP / 156 Def / 100 SpD
Bold Nature
IVs: 0 Atk
- Foul Play
- Psychic
- Trick Room
- Helping Hand""",
        """
Charizard @ Choice Specs
Ability: Solar Power
Level: 50
Tera Type: Ghost
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Overheat
- Dragon Pulse
- Solar Beam
- Heat Wave

Koraidon @ Clear Amulet
Ability: Orichalcum Pulse
Level: 50
Tera Type: Fire
EVs: 236 HP / 196 Atk / 4 Def / 4 SpD / 68 Spe
Jolly Nature
- Collision Course
- Flare Blitz
- Flame Charge
- Protect

Incineroar @ Sitrus Berry
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 252 HP / 196 Atk / 28 Def / 4 SpD / 28 Spe
Adamant Nature
- Parting Shot
- Fake Out
- Flare Blitz
- Knock Off

Jumpluff @ Covert Cloak
Ability: Chlorophyll
Level: 50
Tera Type: Fire
EVs: 252 HP / 60 Def / 196 Spe
Timid Nature
IVs: 0 Atk
- Sunny Day
- Tailwind
- Sleep Powder
- Rage Powder

Zamazenta-Crowned @ Rusted Shield
Ability: Dauntless Shield
Level: 50
Tera Type: Grass
EVs: 4 HP / 4 Atk / 244 Def / 4 SpD / 252 Spe
Impish Nature
- Heavy Slam
- Body Press
- Wide Guard
- Protect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Grass
EVs: 172 HP / 244 Atk / 4 Def / 12 SpD / 76 Spe
Adamant Nature
- Grassy Glide
- Wood Hammer
- Fake Out
- Drain Punch""",
        """
Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 236 HP / 4 Atk / 84 Def / 76 SpD / 108 Spe
Careful Nature
- Knock Off
- Fake Out
- Will-O-Wisp
- Parting Shot

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 236 HP / 156 Def / 116 SpD
Bold Nature
IVs: 0 Atk / 27 Spe
- Pollen Puff
- Spore
- Rage Powder
- Protect

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 252 HP / 92 Def / 20 SpA / 4 SpD / 140 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Thunderclap
- Draco Meteor
- Electroweb

Lunala @ Power Herb
Ability: Shadow Shield
Level: 50
Tera Type: Fairy
EVs: 252 HP / 4 Def / 180 SpA / 4 SpD / 68 Spe
Modest Nature
IVs: 0 Atk
- Moongeist Beam
- Meteor Beam
- Wide Guard
- Trick Room

Groudon @ Clear Amulet
Ability: Drought
Level: 50
Tera Type: Fire
EVs: 228 HP / 156 Atk / 4 Def / 4 SpD / 116 Spe
Adamant Nature
- Precipice Blades
- Heat Crash
- Swords Dance
- Protect

Ogerpon-Hearthflame @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 236 HP / 76 Atk / 4 Def / 4 SpD / 188 Spe
Adamant Nature
- Ivy Cudgel
- Wood Hammer
- Follow Me
- Spiky Shield""",
    ],
    "gen9vgc2025regi": [
        """
Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Fairy
EVs: 252 HP / 116 Atk / 4 Def / 20 SpD / 116 Spe
Adamant Nature
- Glacial Lance
- High Horsepower
- Protect
- Trick Room

Landorus @ Life Orb
Ability: Sheer Force
Level: 50
Tera Type: Water
EVs: 244 HP / 4 Def / 124 SpA / 4 SpD / 132 Spe
Modest Nature
IVs: 0 Atk
- Earth Power
- Sludge Bomb
- Sandsear Storm
- Protect

Amoonguss @ Covert Cloak
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

Urshifu-Rapid-Strike @ Mystic Water
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 204 HP / 188 Atk / 20 Def / 4 SpD / 92 Spe
Adamant Nature
- Surging Strikes
- Taunt
- Close Combat
- Detect

Roaring Moon @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Flying
EVs: 148 HP / 84 Atk / 116 Def / 4 SpD / 156 Spe
Jolly Nature
- Knock Off
- Acrobatics
- Protect
- Tailwind

Ogerpon-Hearthflame @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 220 HP / 12 Atk / 252 Def / 4 SpD / 20 Spe
Impish Nature
- Ivy Cudgel
- Horn Leech
- Follow Me
- Spiky Shield
""",
        """
Calyrex-Ice @ Life Orb
Ability: As One (Glastrier)
Level: 50
Tera Type: Dark
EVs: 252 HP / 252 Atk / 4 SpD
Brave Nature
IVs: 0 Spe
- Glacial Lance
- Trick Room
- Close Combat
- Protect

Zapdos-Galar @ Power Bracer
Ability: Defiant
Level: 50
Tera Type: Steel
EVs: 252 HP / 252 Atk / 4 Def
Brave Nature
IVs: 0 Spe
- Thunderous Kick
- Quick Guard
- Coaching
- Brave Bird

Girafarig @ Eviolite
Ability: Inner Focus
Level: 50
Tera Type: Water
EVs: 116 HP / 44 Def / 252 SpA / 92 SpD / 4 Spe
Modest Nature
IVs: 0 Atk
- Twin Beam
- Helping Hand
- Foul Play
- Trick Room

Grimmsnarl @ Rocky Helmet
Ability: Prankster
Level: 50
Tera Type: Steel
EVs: 252 HP / 252 Def / 4 SpD
Impish Nature
- Fake Out
- Foul Play
- Body Press
- Imprison

Ting-Lu @ Leftovers
Ability: Vessel of Ruin
Level: 50
Tera Type: Fairy
EVs: 212 HP / 44 Def / 252 SpD
Relaxed Nature
IVs: 0 Spe
- Sand Tomb
- Dig
- Fissure
- Protect

Ogerpon (F) @ Choice Band
Ability: Defiant
Level: 50
Tera Type: Grass
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Wood Hammer
- U-turn
- Giga Impact
- Bullet Seed
""",
        """
Lunala @ Power Herb
Ability: Shadow Shield
Level: 50
Tera Type: Grass
EVs: 156 HP / 4 Def / 252 SpA / 4 SpD / 92 Spe
Modest Nature
- Moongeist Beam
- Expanding Force
- Meteor Beam
- Trick Room

Indeedee-F @ Safety Goggles
Ability: Psychic Surge
Level: 50
Tera Type: Water
EVs: 252 HP / 252 Def / 4 SpD
Bold Nature
IVs: 0 Atk
- Alluring Voice
- Follow Me
- Helping Hand
- Trick Room

Tornadus @ Focus Sash
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 10 Atk
- Bleakwind Storm
- Tailwind
- Rain Dance
- Protect

Urshifu-Rapid-Strike @ Choice Band
Ability: Unseen Fist
Level: 50
Tera Type: Water
EVs: 60 HP / 196 Atk / 4 Def / 68 SpD / 180 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- U-turn

Ursaluna @ Flame Orb
Ability: Guts
Level: 50
Tera Type: Ghost
EVs: 252 HP / 252 Atk / 4 SpD
Brave Nature
IVs: 14 SpA / 0 Spe
- Facade
- Headlong Rush
- Earthquake
- Protect

Ogerpon (F) @ Covert Cloak
Ability: Defiant
Level: 50
Tera Type: Grass
EVs: 20 HP / 236 Atk / 252 Spe
Adamant Nature
IVs: 20 SpA
- Ivy Cudgel
- Superpower
- Follow Me
- Taunt
""",
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
Groudon @ Clear Amulet
Ability: Drought
Level: 50
Tera Type: Fire
EVs: 252 HP / 76 Atk / 36 SpD / 140 Spe
Adamant Nature
- Precipice Blades
- Thunder Punch
- Heat Crash
- Protect

Tornadus @ Focus Sash
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
- Air Slash
- Tailwind
- Heat Wave
- Protect

Flutter Mane @ Choice Specs
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 148 HP / 252 SpA / 108 Spe
Modest Nature
IVs: 18 Atk
- Dazzling Gleam
- Moonblast
- Shadow Ball
- Perish Song

Chi-Yu @ Choice Scarf
Ability: Beads of Ruin
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
- Heat Wave
- Dark Pulse
- Snarl
- Overheat

Grimmsnarl @ Light Clay
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 252 HP / 4 Atk / 180 Def / 36 SpD / 36 Spe
Careful Nature
IVs: 18 SpA
- Foul Play
- Thunder Wave
- Reflect
- Light Screen

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Fire
EVs: 60 HP / 4 Def / 196 SpA / 180 SpD / 68 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Thunderclap
- Dragon Pulse
- Weather Ball
""",
        """
Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Fairy
EVs: 220 HP / 196 Atk / 4 Def / 68 SpD / 20 Spe
Adamant Nature
- Protect
- Glacial Lance
- High Horsepower
- Trick Room

Regieleki @ Light Clay
Ability: Transistor
Level: 50
Tera Type: Electric
EVs: 204 HP / 140 Def / 12 SpA / 76 SpD / 76 Spe
Timid Nature
IVs: 0 Atk
- Electroweb
- Reflect
- Light Screen
- Thunder

Landorus @ Life Orb
Ability: Sheer Force
Level: 50
Tera Type: Water
EVs: 100 HP / 12 Def / 132 SpA / 12 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Earth Power
- Sludge Bomb
- Substitute

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

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 252 HP / 124 Atk / 4 Def / 124 SpD / 4 Spe
Adamant Nature
- Fake Out
- Grassy Glide
- Wood Hammer
- U-turn

Farigiraf @ Mental Herb
Ability: Armor Tail
Level: 50
Tera Type: Water
EVs: 212 HP / 156 Def / 140 SpD
Bold Nature
IVs: 0 Atk
- Psychic Noise
- Foul Play
- Helping Hand
- Trick Room
""",
        """
Whimsicott @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Water
EVs: 252 HP / 4 Def / 4 SpA / 212 SpD / 36 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Tailwind
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
EVs: 252 HP / 116 Atk / 52 Def / 84 SpD / 4 Spe
Adamant Nature
- Ivy Cudgel
- Wood Hammer
- Follow Me
- Spiky Shield

Farigiraf @ Electric Seed
Ability: Armor Tail
Level: 50
Tera Type: Water
EVs: 236 HP / 164 Def / 108 SpD
Bold Nature
IVs: 0 Atk
- Psychic
- Foul Play
- Helping Hand
- Trick Room

Iron Hands @ Assault Vest
Ability: Quark Drive
Level: 50
Tera Type: Grass
EVs: 140 HP / 244 Atk / 124 SpD
Adamant Nature
IVs: 29 Spe
- Drain Punch
- Low Kick
- Wild Charge
- Fake Out
""",
        """
Koraidon @ Clear Amulet
Ability: Orichalcum Pulse
Level: 50
Tera Type: Fire
EVs: 52 HP / 116 Atk / 132 SpD / 204 Spe
Adamant Nature
- Collision Course
- Flare Blitz
- Flame Charge
- Protect

Gholdengo @ Leftovers
Ability: Good as Gold
Level: 50
Tera Type: Fairy
EVs: 164 HP / 20 Def / 52 SpA / 188 SpD / 76 Spe
Modest Nature
IVs: 6 Atk
- Make It Rain
- Shadow Ball
- Nasty Plot
- Protect

Walking Wake @ Life Orb
Ability: Protosynthesis
Level: 50
Tera Type: Water
EVs: 44 HP / 212 SpA / 252 Spe
Timid Nature
- Hydro Steam
- Draco Meteor
- Flamethrower
- Protect

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Water
EVs: 252 HP / 4 Atk / 76 Def / 132 SpD / 36 Spe
Impish Nature
IVs: 28 SpA
- Fake Out
- Knock Off
- Will-O-Wisp
- Parting Shot

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 204 HP / 4 Atk / 252 Def / 20 SpD / 20 Spe
Adamant Nature
IVs: 18 SpA
- Fake Out
- Wood Hammer
- Grassy Glide
- High Horsepower

Tornadus @ Focus Sash
Ability: Prankster
Level: 50
Tera Type: Steel
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 24 Atk
- Bleakwind Storm
- Tailwind
- Sunny Day
- Protect
""",
        """
Calyrex-Shadow @ Life Orb
Ability: As One (Spectrier)
Level: 50
Tera Type: Normal
EVs: 244 HP / 36 Def / 84 SpA / 4 SpD / 140 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Psyshock
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
- Detect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 244 HP / 116 Atk / 4 Def / 140 SpD / 4 Spe
Adamant Nature
- Wood Hammer
- Fake Out
- Grassy Glide
- U-turn

Incineroar @ Rocky Helmet
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 4 Atk / 236 Def / 20 SpD / 4 Spe
Impish Nature
- Will-O-Wisp
- Fake Out
- Parting Shot
- Knock Off

Tornadus @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 252 HP / 180 Def / 4 SpA / 4 SpD / 68 Spe
Timid Nature
IVs: 0 Atk
- Bleakwind Storm
- Tailwind
- Rain Dance
- Protect

Ogerpon-Cornerstone (F) @ Cornerstone Mask
Ability: Sturdy
Level: 50
Tera Type: Rock
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Ivy Cudgel
- Wood Hammer
- Follow Me
- Spiky Shield
""",
        """
Sonic (Zacian-Crowned) @ Rusted Sword
Ability: Intrepid Sword
Level: 50
Tera Type: Dragon
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Protect
- Behemoth Blade
- Sacred Sword
- Play Rough

Badnik (Weezing) @ Sitrus Berry
Ability: Neutralizing Gas
Level: 50
Tera Type: Dark
EVs: 252 HP / 236 SpD / 20 Spe
Calm Nature
IVs: 0 Atk
- Protect
- Sludge Bomb
- Taunt
- Will-O-Wisp

Dr. Eggman (Regigigas) @ Life Orb
Ability: Slow Start
Level: 50
Tera Type: Ghost
EVs: 28 HP / 244 Atk / 236 Spe
Adamant Nature
- Protect
- Crush Grip
- Knock Off
- Wide Guard

Tails (Tornadus) @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Steel
EVs: 220 HP / 28 Def / 4 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Bleakwind Storm
- Tailwind
- Rain Dance

Knuckles (Chien-Pao) @ Focus Sash
Ability: Sword of Ruin
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Protect
- Ice Spinner
- Sacred Sword
- Sucker Punch

Amy Rose (Ogerpon-Wellspring) (F) @ Wellspring Mask
Ability: Water Absorb
Level: 50
Tera Type: Water
EVs: 196 HP / 108 Atk / 4 Def / 12 SpD / 188 Spe
Jolly Nature
- Spiky Shield
- Ivy Cudgel
- Horn Leech
- Follow Me
""",
        """
Raging Bolt @ Life Orb
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 100 HP / 92 Def / 252 SpA / 4 SpD / 60 Spe
Modest Nature
IVs: 20 Atk
- Thunderclap
- Thunderbolt
- Draco Meteor
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
- Detect

Ogerpon-Cornerstone (F) @ Cornerstone Mask
Ability: Sturdy
Level: 50
Tera Type: Rock
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
IVs: 20 SpA
- Ivy Cudgel
- Power Whip
- Follow Me
- Spiky Shield

Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Normal
EVs: 252 HP / 252 Atk / 4 SpD
Brave Nature
IVs: 0 Spe
- Glacial Lance
- High Horsepower
- Trick Room
- Protect

Iron Valiant @ Booster Energy
Ability: Quark Drive
Level: 50
Tera Type: Steel
EVs: 252 HP / 84 Def / 4 SpA / 52 SpD / 116 Spe
Timid Nature
IVs: 6 Atk
- Moonblast
- Coaching
- Disable
- Encore

Clefairy @ Eviolite
Ability: Friend Guard
Level: 50
Tera Type: Ground
EVs: 252 HP / 220 Def / 36 SpD
Sassy Nature
IVs: 0 Atk / 26 SpA / 0 Spe
- Follow Me
- Heal Pulse
- Helping Hand
- Protect
""",
        """
Rayquaza @ Clear Amulet
Ability: Air Lock
Level: 50
Tera Type: Normal
EVs: 220 HP / 92 Atk / 4 Def / 12 SpD / 180 Spe
Adamant Nature
- Dragon Ascent
- Extreme Speed
- Protect
- Dragon Dance

Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Ice Spinner
- Sacred Sword
- Protect
- Sucker Punch

Urshifu-Rapid-Strike @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Grass
EVs: 4 HP / 236 Atk / 4 Def / 12 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- U-turn
- Aqua Jet

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 188 Def / 76 SpD
Impish Nature
- Knock Off
- Will-O-Wisp
- Fake Out
- Parting Shot

Amoonguss @ Covert Cloak
Ability: Regenerator
Level: 50
Tera Type: Fairy
EVs: 244 HP / 156 Def / 108 SpD
Relaxed Nature
IVs: 0 Atk
- Pollen Puff
- Spore
- Protect
- Rage Powder

Moltres-Galar @ Sitrus Berry
Ability: Berserk
Level: 50
Tera Type: Dark
EVs: 244 HP / 44 Def / 12 SpA / 44 SpD / 164 Spe
Calm Nature
IVs: 0 Atk
- Fiery Wrath
- Foul Play
- Protect
- Taunt
""",
        """
Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Tera Type: Water
EVs: 252 HP / 252 Atk / 4 SpD
Brave Nature
IVs: 0 Spe
- Glacial Lance
- Trick Room
- Protect
- High Horsepower

Weezing-Galar (M) @ Wise Glasses
Ability: Misty Surge
Level: 50
Shiny: Yes
Tera Type: Flying
EVs: 252 HP / 252 SpA / 4 SpD
Quiet Nature
IVs: 0 Atk / 0 Spe
- Protect
- Thunderbolt
- Sludge Bomb
- Flamethrower

Ursaluna-Bloodmoon @ Life Orb
Ability: Mind's Eye
Tera Type: Normal
EVs: 244 HP / 252 SpA / 12 SpD
Quiet Nature
IVs: 0 Atk / 0 Spe
- Blood Moon
- Earth Power
- Hyper Voice
- Protect

Indeedee-F @ Psychic Seed
Ability: Psychic Surge
Tera Type: Water
EVs: 252 HP / 252 Def / 4 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Psychic
- Follow Me
- Trick Room
- Helping Hand

Farigiraf (M) @ Throat Spray
Ability: Armor Tail
Shiny: Yes
Tera Type: Fairy
EVs: 252 HP / 252 SpA / 4 SpD
Quiet Nature
IVs: 0 Atk / 0 Spe
- Trick Room
- Hyper Voice
- Protect
- Psychic Noise

Urshifu (M) @ Dread Plate
Ability: Unseen Fist
Level: 50
Tera Type: Poison
EVs: 252 HP / 252 Atk / 4 SpD
Brave Nature
IVs: 0 Spe
- Wicked Blow
- Sucker Punch
- Close Combat
- Protect
""",
        """
Miraidon @ Choice Scarf
Ability: Hadron Engine
Level: 50
Tera Type: Electric
EVs: 44 HP / 12 Def / 252 SpA / 28 SpD / 172 Spe
Modest Nature
- Electro Drift
- Discharge
- Draco Meteor
- Volt Switch

Whimsicott @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 252 HP / 4 SpA / 252 Spe
Timid Nature
IVs: 16 Atk
- Tailwind
- Moonblast
- Helping Hand
- Encore

Urshifu @ Focus Sash
Ability: Unseen Fist
Level: 50
Tera Type: Dark
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Wicked Blow
- Sucker Punch
- Close Combat
- Detect

Ogerpon-Hearthflame (F) @ Hearthflame Mask
Ability: Mold Breaker
Level: 50
Tera Type: Fire
EVs: 44 HP / 156 Atk / 12 Def / 36 SpD / 252 Spe
Jolly Nature
IVs: 20 SpA
- Ivy Cudgel
- Encore
- Follow Me
- Spiky Shield

Farigiraf @ Electric Seed
Ability: Armor Tail
Level: 50
Tera Type: Ground
EVs: 124 HP / 196 Def / 164 SpA / 20 SpD / 4 Spe
Calm Nature
IVs: 10 Atk
- Psychic Noise
- Helping Hand
- Trick Room
- Ally Switch

Glimmora @ Power Herb
Ability: Toxic Debris
Level: 50
Tera Type: Grass
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 4 Atk
- Spiky Shield
- Meteor Beam
- Sludge Bomb
- Mortal Spin
""",
        """
Miraidon @ Choice Specs
Ability: Hadron Engine
Tera Type: Electric
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
- Electro Drift
- Draco Meteor
- Overheat
- Volt Switch

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

Volcarona (M) @ Leftovers
Ability: Flame Body
Level: 50
Tera Type: Dragon
EVs: 252 HP / 76 Def / 36 SpA / 4 SpD / 140 Spe
Modest Nature
IVs: 0 Atk
- Heat Wave
- Giga Drain
- Quiver Dance
- Protect

Grimmsnarl @ Light Clay
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 244 HP / 4 Atk / 68 Def / 188 SpD / 4 Spe
Careful Nature
- Spirit Break
- Reflect
- Light Screen
- Thunder Wave

Urshifu-Rapid-Strike (M) @ Mystic Water
Ability: Unseen Fist
Level: 70
Tera Type: Water
EVs: 188 HP / 76 Atk / 4 Def / 68 SpD / 172 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Protect

Tornadus @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 204 HP / 36 Def / 4 SpA / 12 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Bleakwind Storm
- Taunt
- Rain Dance
- Tailwind
""",
        """
Giratina-Origin @ Griseous Core
Ability: Levitate
Level: 50
Tera Type: Normal
EVs: 188 HP / 252 Atk / 68 SpD
Adamant Nature
IVs: 22 SpA
- Poltergeist
- Breaking Swipe
- Shadow Sneak
- Protect

Tornadus @ Focus Sash
Ability: Prankster
Level: 50
Tera Type: Fire
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 24 Atk
- Bleakwind Storm
- Heat Wave
- Tailwind
- Protect

Iron Treads @ Choice Band
Ability: Quark Drive
Level: 50
Tera Type: Ground
EVs: 28 HP / 252 Atk / 4 Def / 4 SpD / 220 Spe
Jolly Nature
- Earthquake
- Iron Head
- Rock Slide
- High Horsepower

Farigiraf @ Choice Specs
Ability: Armor Tail
Level: 50
Tera Type: Normal
EVs: 124 Def / 252 SpA / 132 Spe
Modest Nature
IVs: 0 Atk
- Psychic
- Hyper Voice
- Shadow Ball
- Trick

Brute Bonnet @ Sitrus Berry
Ability: Protosynthesis
Level: 50
Tera Type: Dark
EVs: 244 HP / 4 Atk / 180 Def / 20 SpD / 60 Spe
Impish Nature
IVs: 22 SpA
- Spore
- Crunch
- Seed Bomb
- Sucker Punch

Comfey @ Life Orb
Ability: Triage
Level: 50
Tera Type: Fairy
EVs: 252 HP / 4 Def / 252 SpA
Modest Nature
IVs: 0 Atk
- Draining Kiss
- Stored Power
- Calm Mind
- Protect
""",
        """
Calyrex-Shadow @ Life Orb
Ability: As One (Spectrier)
Tera Type: Fairy
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Psychic
- Disable
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

Urshifu-Rapid-Strike (F) @ Mystic Water
Ability: Unseen Fist
Level: 50
Tera Type: Grass
EVs: 60 HP / 156 Atk / 4 Def / 124 SpD / 164 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Detect

Tornadus @ Rocky Helmet
Ability: Prankster
Level: 50
Tera Type: Steel
EVs: 204 HP / 244 Def / 4 SpA / 12 SpD / 44 Spe
Timid Nature
IVs: 0 Atk
- Tailwind
- Bleakwind Storm
- Rain Dance
- Protect

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 236 HP / 4 Atk / 108 Def / 156 SpD / 4 Spe
Careful Nature
- Fake Out
- Parting Shot
- Will-O-Wisp
- Knock Off

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Shiny: Yes
Tera Type: Fire
EVs: 244 HP / 116 Atk / 4 Def / 92 SpD / 52 Spe
Adamant Nature
- Fake Out
- Wood Hammer
- Grassy Glide
- U-turn
""",
        """
Zacon (Zacian) @ Clear Amulet
Ability: Intrepid Sword
Level: 50
Tera Type: Ground
EVs: 12 HP / 252 Atk / 4 Def / 4 SpD / 236 Spe
Jolly Nature
- Play Rough
- Sacred Sword
- Tera Blast
- Protect

Scream Tail @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Grass
EVs: 252 HP / 124 Def / 4 SpA / 84 SpD / 44 Spe
Timid Nature
IVs: 0 Atk
- Dazzling Gleam
- Encore
- Howl
- Protect

Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Sucker Punch
- Icicle Crash
- Sacred Sword
- Protect

Talonflame @ Life Orb
Ability: Gale Wings
Tera Type: Ghost
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Brave Bird
- Tailwind
- Flare Blitz
- Protect

Rillaboom @ Miracle Seed
Ability: Grassy Surge
Level: 50
Tera Type: Grass
EVs: 244 HP / 204 Atk / 4 Def / 4 SpD / 52 Spe
Adamant Nature
- Fake Out
- Wood Hammer
- Grassy Glide
- Protect

Pelipper @ Covert Cloak
Ability: Drizzle
Level: 50
Tera Type: Ghost
EVs: 252 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Wide Guard
- Weather Ball
- Hurricane
- Protect
""",
        """
Calyrex-Shadow @ Covert Cloak
Ability: As One (Spectrier)
Level: 50
Tera Type: Fairy
EVs: 132 HP / 4 Def / 116 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Astral Barrage
- Calm Mind
- Draining Kiss

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 252 HP / 4 Atk / 84 Def / 76 SpD / 92 Spe
Careful Nature
- Knock Off
- Parting Shot
- Taunt
- Fake Out

Pelipper @ Rocky Helmet
Ability: Drizzle
Level: 50
Tera Type: Grass
EVs: 252 HP / 4 Def / 20 SpA / 156 SpD / 76 Spe
Calm Nature
- Weather Ball
- Hurricane
- Wide Guard
- Protect

Urshifu-Rapid-Strike @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Grass
EVs: 4 HP / 236 Atk / 4 Def / 4 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- U-turn
- Aqua Jet
- Close Combat

Rillaboom @ Clear Amulet
Ability: Grassy Surge
Level: 50
Tera Type: Water
EVs: 196 HP / 52 Atk / 4 Def / 252 SpD / 4 Spe
Adamant Nature
- Grassy Glide
- High Horsepower
- U-turn
- Fake Out

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 140 HP / 52 Def / 180 SpA / 36 SpD / 100 Spe
Modest Nature
- Electroweb
- Thunderclap
- Volt Switch
- Draco Meteor
""",
        """
Calyrex-Ice @ Clear Amulet
Ability: As One (Glastrier)
Level: 50
Tera Type: Grass
EVs: 252 HP / 116 Atk / 4 Def / 108 SpD / 28 Spe
Adamant Nature
- Glacial Lance
- High Horsepower
- Trick Room
- Protect

Urshifu-Rapid-Strike @ Choice Scarf
Ability: Unseen Fist
Level: 50
Tera Type: Ghost
EVs: 4 HP / 156 Atk / 4 Def / 92 SpD / 252 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- U-turn
- Coaching

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

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 4 Atk / 4 Def / 4 SpD / 252 Spe
Jolly Nature
- Knock Off
- Parting Shot
- Taunt
- Fake Out

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Fairy
EVs: 252 HP / 156 Def / 100 SpD
Relaxed Nature
IVs: 0 Atk
- Spore
- Rage Powder
- Pollen Puff
- Protect

Raging Bolt @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 252 HP / 108 Def / 124 SpA / 4 SpD / 20 Spe
Modest Nature
IVs: 20 Atk
- Thunderbolt
- Draco Meteor
- Thunderclap
- Protect
""",
        """
Kommo-o better (Zamazenta-Crowned) @ Rusted Shield
Ability: Dauntless Shield
Level: 50
Tera Type: Water
EVs: 252 HP / 4 Atk / 196 Def / 4 SpD / 52 Spe
Jolly Nature
- Wide Guard
- Body Press
- Behemoth Bash
- Protect

Chien-Pao @ Focus Sash
Ability: Sword of Ruin
Tera Type: Ghost
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Sucker Punch
- Ice Spinner
- Sacred Sword
- Protect

Entei @ Assault Vest
Ability: Inner Focus
Level: 50
Tera Type: Normal
EVs: 140 HP / 116 Atk / 52 Def / 196 SpD / 4 Spe
Adamant Nature
- Sacred Fire
- Extreme Speed
- Stomping Tantrum
- Snarl

Ogerpon-Wellspring (F) @ Wellspring Mask
Ability: Water Absorb
Level: 50
Tera Type: Water
EVs: 252 HP / 76 Atk / 68 Def / 108 SpD / 4 Spe
Adamant Nature
- Follow Me
- Ivy Cudgel
- Horn Leech
- Spiky Shield

Flutter Mane @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 196 HP / 92 Def / 4 SpA / 4 SpD / 212 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Shadow Ball
- Taunt
- Protect

Latias @ Rocky Helmet
Ability: Levitate
Level: 50
Tera Type: Poison
EVs: 252 HP / 84 Def / 4 SpA / 4 SpD / 164 Spe
Timid Nature
IVs: 0 Atk
- Tailwind
- Mist Ball
- Ice Beam
- Recover
""",
        """
Calyrex-Shadow @ Life Orb
Ability: As One (Spectrier)
Level: 50
Tera Type: Fairy
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Astral Barrage
- Draining Kiss
- Psychic
- Protect

Incineroar @ Sitrus Berry
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 252 HP / 36 Atk / 100 Def / 76 SpD / 44 Spe
Careful Nature
- Flare Blitz
- Knock Off
- Will-O-Wisp
- Fake Out

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Ghost
EVs: 212 HP / 252 Atk / 44 Spe
Adamant Nature
- Grassy Glide
- High Horsepower
- Wood Hammer
- Fake Out

Urshifu-Rapid-Strike @ Mystic Water
Ability: Unseen Fist
Level: 50
Tera Type: Grass
EVs: 76 HP / 252 Atk / 180 Spe
Adamant Nature
- Surging Strikes
- Close Combat
- Aqua Jet
- Protect

Tornadus @ Focus Sash
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Tailwind
- Rain Dance
- Taunt
- Bleakwind Storm

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 244 HP / 156 Def / 108 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Rage Powder
- Spore
- Pollen Puff
- Protect
""",
        """
Tommy (Tornadus) @ Focus Sash
Ability: Prankster
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 26 Atk
- Bleakwind Storm
- Tailwind
- Rain Dance
- Protect

Flutter Mane @ Booster Energy
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 188 HP / 164 Def / 4 SpA / 4 SpD / 148 Spe
Timid Nature
IVs: 26 Atk
- Moonblast
- Icy Wind
- Fake Tears
- Protect

Kyogre @ Mystic Water
Ability: Drizzle
Level: 50
Tera Type: Water
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Water Spout
- Ice Beam
- Origin Pulse
- Protect

Tsareena @ Wide Lens
Ability: Queenly Majesty
Level: 50
Tera Type: Steel
EVs: 236 HP / 76 Atk / 196 Spe
Adamant Nature
- Power Whip
- Triple Axel
- Helping Hand
- Taunt

Landorus @ Life Orb
Ability: Sheer Force
Level: 50
Tera Type: Poison
EVs: 116 HP / 4 Def / 132 SpA / 4 SpD / 252 Spe
Modest Nature
- Earth Power
- Sludge Bomb
- Sandsear Storm
- Protect

Incineroar @ Assault Vest
Ability: Intimidate
Level: 50
Tera Type: Grass
EVs: 252 HP / 4 Atk / 100 Def / 132 SpD / 20 Spe
Impish Nature
- Fake Out
- Flare Blitz
- Knock Off
- U-turn
""",
        """
Miraidon @ Magnet
Ability: Hadron Engine
Tera Type: Electric
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
- Electro Drift
- Draco Meteor
- Dazzling Gleam
- Protect

Incineroar (M) @ Sitrus Berry
Ability: Intimidate
Level: 68
Tera Type: Water
EVs: 236 HP / 4 Atk / 188 Def / 76 SpD / 4 Spe
Impish Nature
- Flare Blitz
- Knock Off
- Fake Out
- Parting Shot

Ogerpon-Wellspring @ Wellspring Mask
Ability: Water Absorb
Tera Type: Water
EVs: 252 HP / 4 Atk / 12 Def / 52 SpD / 188 Spe
Jolly Nature
- Ivy Cudgel
- Spiky Shield
- Horn Leech
- Follow Me

Iron Bundle @ Covert Cloak
Ability: Quark Drive
Level: 58
Tera Type: Ice
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Freeze-Dry
- Icy Wind
- Protect
- Encore

Iron Valiant @ Focus Sash
Ability: Quark Drive
Tera Type: Ghost
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Close Combat
- Spirit Break
- Wide Guard
- Taunt

Landorus @ Life Orb
Ability: Sheer Force
Level: 94
Shiny: Yes
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
Koraidon @ Scope Lens
Ability: Orichalcum Pulse
Level: 50
Tera Type: Fire
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Flare Blitz
- Drain Punch
- Flame Charge
- Protect

Amoonguss @ Yache Berry
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 252 HP / 252 Def / 4 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Spore
- Rage Powder
- Pollen Puff
- Foul Play

Gouging Fire @ Covert Cloak
Ability: Protosynthesis
Level: 50
Tera Type: Fire
EVs: 244 HP / 4 Atk / 4 Def / 4 SpD / 252 Spe
Jolly Nature
- Breaking Swipe
- Snarl
- Burning Bulwark
- Dragon Cheer

Raging Bolt @ Assault Vest
Ability: Protosynthesis
Level: 50
Tera Type: Electric
EVs: 252 HP / 60 SpA / 196 SpD
Quiet Nature
IVs: 20 Atk / 20 Spe
- Thunderclap
- Volt Switch
- Draco Meteor
- Snarl

Roaring Moon @ Razor Claw
Ability: Protosynthesis
Level: 50
Tera Type: Steel
EVs: 28 HP / 220 Atk / 4 Def / 4 SpD / 252 Spe
Jolly Nature
- Knock Off
- Iron Head
- Dragon Cheer
- Tailwind

Flutter Mane @ Focus Sash
Ability: Protosynthesis
Level: 50
Tera Type: Fairy
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Taunt
- Sunny Day
- Icy Wind
""",
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
- Fake Out""",
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
- U-turn""",
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
- Helping Hand""",
    ],
    "gen9vgc2024regh": [
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
- Trick""",
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
- Protect""",
        """
Hydrapple @ Leftovers
Ability: Supersweet Syrup
Level: 50
Tera Type: Steel
EVs: 212 HP / 156 SpA / 140 SpD
Quiet Nature
IVs: 0 Atk / 0 Spe
- Syrup Bomb
- Fickle Beam
- Yawn
- Protect

Maushold-Four @ King's Rock
Ability: Technician
Level: 50
Shiny: Yes
Tera Type: Ghost
EVs: 172 HP / 196 Atk / 4 Def / 4 SpD / 132 Spe
Jolly Nature
- Population Bomb
- Taunt
- Follow Me
- Protect

Volcarona @ Safety Goggles
Ability: Flame Body
Level: 50
Shiny: Yes
Tera Type: Dragon
EVs: 252 HP / 68 Def / 36 SpA / 4 SpD / 148 Spe
Modest Nature
IVs: 0 Atk
- Heat Wave
- Giga Drain
- Quiver Dance
- Protect

Tauros-Paldea-Aqua @ Mirror Herb
Ability: Intimidate
Level: 50
Tera Type: Grass
EVs: 204 HP / 156 Atk / 4 Def / 4 SpD / 140 Spe
Adamant Nature
- Wave Crash
- Aqua Jet
- Close Combat
- Protect

Ursaluna-Bloodmoon @ Assault Vest
Ability: Mind's Eye
Level: 50
Tera Type: Normal
EVs: 148 HP / 4 Def / 196 SpA / 4 SpD / 156 Spe
Modest Nature
IVs: 0 Atk
- Hyper Voice
- Blood Moon
- Earth Power
- Vacuum Wave

Gothitelle @ Sitrus Berry
Ability: Shadow Tag
Level: 50
Tera Type: Steel
EVs: 244 HP / 36 Def / 4 SpA / 4 SpD / 220 Spe
Timid Nature
- Psychic
- Helping Hand
- Fake Out
- Trick Room""",
        """
Vivillon @ Focus Sash
Ability: Compound Eyes
Level: 50
Tera Type: Ghost
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Sleep Powder
- Rage Powder
- Hurricane

Garchomp @ Life Orb
Ability: Rough Skin
Level: 50
Tera Type: Fire
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Protect
- Earthquake
- Stomping Tantrum
- Dragon Claw

Primarina @ Sitrus Berry
Ability: Liquid Voice
Level: 50
Tera Type: Poison
EVs: 252 HP / 132 Def / 108 SpA / 4 SpD / 12 Spe
Modest Nature
IVs: 0 Atk
- Protect
- Haze
- Hyper Voice
- Moonblast

Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 164 HP / 4 Atk / 36 Def / 68 SpD / 236 Spe
Jolly Nature
- Fake Out
- Flare Blitz
- Knock Off
- Parting Shot

Porygon2 @ Eviolite
Ability: Download
Level: 50
Tera Type: Fighting
EVs: 252 HP / 196 SpA / 60 SpD
Quiet Nature
IVs: 0 Spe
- Trick Room
- Recover
- Tera Blast
- Ice Beam

Gholdengo @ Metal Coat
Ability: Good as Gold
Level: 50
Tera Type: Dragon
EVs: 252 HP / 108 Def / 132 SpA / 4 SpD / 12 Spe
Modest Nature
IVs: 0 Atk
- Protect
- Nasty Plot
- Make It Rain
- Shadow Ball""",
        """
Incineroar @ Safety Goggles
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 244 HP / 4 Atk / 4 Def / 4 SpD / 252 Spe
Jolly Nature
- Knock Off
- Snarl
- Fake Out
- Parting Shot

Amoonguss @ Sitrus Berry
Ability: Regenerator
Level: 50
Tera Type: Water
EVs: 236 HP / 196 Def / 76 SpD
Calm Nature
IVs: 0 Atk / 26 Spe
- Pollen Puff
- Rage Powder
- Spore
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
- Substitute
- Protect

Porygon2 @ Eviolite
Ability: Download
Level: 50
Tera Type: Ghost
EVs: 244 HP / 4 Atk / 36 Def / 92 SpA / 132 SpD
Quiet Nature
IVs: 24 Spe
- Tera Blast
- Ice Beam
- Recover
- Trick Room

Gholdengo @ Metal Coat
Ability: Good as Gold
Level: 50
Tera Type: Steel
EVs: 108 HP / 12 Def / 212 SpA / 4 SpD / 172 Spe
Modest Nature
IVs: 0 Atk
- Protect
- Nasty Plot
- Make It Rain
- Shadow Ball

Primarina @ Mystic Water
Ability: Liquid Voice
Level: 50
Tera Type: Poison
EVs: 244 HP / 4 Def / 188 SpA / 4 SpD / 68 Spe
Modest Nature
IVs: 0 Atk
- Hyper Voice
- Moonblast
- Haze
- Protect""",
        """
Decidueye-Hisui @ Scope Lens
Ability: Scrappy
Level: 50
Tera Type: Flying
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Leaf Blade
- Protect
- Brave Bird
- Triple Arrows

Basculegion (M) @ Mystic Water
Ability: Swift Swim
Level: 50
Tera Type: Water
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
IVs: 10 SpA
- Wave Crash
- Aqua Jet
- Protect
- Last Respects

Archaludon @ Assault Vest
Ability: Stamina
Level: 50
Tera Type: Fairy
EVs: 200 HP / 232 SpA / 76 Spe
Modest Nature
IVs: 24 Atk
- Draco Meteor
- Flash Cannon
- Body Press
- Electro Shot

Pelipper @ Focus Sash
Ability: Drizzle
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Tailwind
- Weather Ball
- Hurricane
- Protect

Clefairy @ Eviolite
Ability: Friend Guard
Level: 50
Tera Type: Grass
EVs: 252 HP / 252 Def / 4 SpD
Calm Nature
IVs: 0 Atk / 0 Spe
- Follow Me
- Helping Hand
- After You
- Protect

Ursaluna-Bloodmoon @ Life Orb
Ability: Mind's Eye
Level: 50
Tera Type: Normal
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Blood Moon
- Hyper Voice
- Earth Power
- Protect""",
        """
Ribombee (F) @ Focus Sash
Ability: Shield Dust
Level: 50
Shiny: Yes
Tera Type: Dark
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 5 Atk
- Moonblast
- Pollen Puff
- Tailwind
- Fake Tears

Primarina (F) @ Throat Spray
Ability: Liquid Voice
Level: 50
Shiny: Yes
Tera Type: Dragon
EVs: 212 HP / 68 Def / 188 SpA / 4 SpD / 36 Spe
Modest Nature
IVs: 16 Atk
- Protect
- Hyper Voice
- Moonblast
- Perish Song

Gothitelle (F) @ Mental Herb
Ability: Shadow Tag
Level: 50
Shiny: Yes
Tera Type: Water
EVs: 244 HP / 92 Def / 4 SpA / 156 SpD / 12 Spe
Calm Nature
IVs: 14 Atk
- Protect
- Fake Out
- Psychic
- Trick Room

Ursaluna-Bloodmoon @ Life Orb
Ability: Mind's Eye
Level: 50
Tera Type: Normal
EVs: 4 HP / 4 Def / 252 SpA / 108 SpD / 140 Spe
Modest Nature
IVs: 0 Atk
- Protect
- Hyper Voice
- Earth Power
- Blood Moon

Incineroar (M) @ Sitrus Berry
Ability: Intimidate
Level: 50
Shiny: Yes
Tera Type: Grass
EVs: 204 HP / 252 Atk / 4 Def / 4 SpD / 44 Spe
Adamant Nature
- Protect
- Fake Out
- Knock Off
- Flare Blitz

Gholdengo @ Choice Specs
Ability: Good as Gold
Level: 50
Shiny: Yes
Tera Type: Steel
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
- Make It Rain
- Shadow Ball
- Thunderbolt
- Power Gem""",
        """
Whimsicott @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Fire
EVs: 252 HP / 36 Def / 4 SpA / 212 SpD / 4 Spe
Bold Nature
IVs: 0 Atk
- Tailwind
- Moonblast
- Sunny Day
- Encore

Ursaluna-Bloodmoon @ Life Orb
Ability: Mind's Eye
Level: 50
Tera Type: Normal
EVs: 4 HP / 4 Def / 212 SpA / 60 SpD / 228 Spe
Modest Nature
IVs: 0 Atk
- Earth Power
- Blood Moon
- Hyper Voice
- Protect

Archaludon @ Assault Vest
Ability: Stamina
Level: 50
Tera Type: Grass
EVs: 252 HP / 76 Def / 68 SpA / 4 SpD / 108 Spe
Modest Nature
IVs: 0 Atk
- Electro Shot
- Flash Cannon
- Body Press
- Draco Meteor

Politoed @ Sitrus Berry
Ability: Drizzle
Level: 50
Shiny: Yes
Tera Type: Grass
EVs: 252 HP / 164 Def / 12 SpA / 76 SpD / 4 Spe
Bold Nature
IVs: 0 Atk
- Perish Song
- Haze
- Weather Ball
- Protect

Typhlosion-Hisui @ Choice Specs
Ability: Blaze
Level: 50
Shiny: Yes
Tera Type: Fire
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Eruption
- Heat Wave
- Infernal Parade
- Solar Beam

Indeedee-F @ Psychic Seed
Ability: Psychic Surge
Level: 50
Tera Type: Fairy
EVs: 252 HP / 244 Def / 4 SpA / 4 SpD / 4 Spe
Bold Nature
IVs: 0 Atk
- Trick Room
- Follow Me
- Imprison
- Psychic""",
        """
Hydreigon @ Choice Specs
Ability: Levitate
Level: 50
Tera Type: Fire
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Draco Meteor
- Dark Pulse
- Heat Wave
- Snarl

Indeedee-F @ Safety Goggles
Ability: Psychic Surge
Level: 50
Tera Type: Ghost
EVs: 252 HP / 132 Def / 4 SpA / 100 SpD / 20 Spe
Bold Nature
IVs: 0 Atk
- Hyper Voice
- Imprison
- Trick Room
- Follow Me

Gholdengo @ Life Orb
Ability: Good as Gold
Level: 86
Tera Type: Dragon
EVs: 52 HP / 4 Def / 212 SpA / 60 SpD / 180 Spe
Modest Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Protect
- Nasty Plot

Murkrow @ Eviolite
Ability: Prankster
Level: 52
Tera Type: Ghost
EVs: 252 HP / 220 SpD / 36 Spe
Calm Nature
IVs: 0 Atk
- Foul Play
- Protect
- Haze
- Tailwind

Sneasler @ Psychic Seed
Ability: Unburden
Level: 50
Tera Type: Dark
EVs: 236 HP / 252 Atk / 4 Def / 4 SpD / 12 Spe
Adamant Nature
- Close Combat
- Dire Claw
- Throat Chop
- Swords Dance

Basculegion @ Choice Scarf
Ability: Adaptability
Level: 50
Tera Type: Grass
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Wave Crash
- Last Respects
- Tera Blast
- Aqua Jet""",
        """
Garchomp @ Clear Amulet
Ability: Sand Veil
Level: 50
Tera Type: Ground
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Protect
- Earthquake
- Dragon Claw
- Swords Dance

Talonflame (F) @ Covert Cloak
Ability: Gale Wings
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Brave Bird
- Tailwind
- Will-O-Wisp
- Taunt

Tyranitar (M) @ Assault Vest
Ability: Sand Stream
Level: 50
Tera Type: Flying
EVs: 252 HP / 244 Atk / 12 SpD
Adamant Nature
- Rock Slide
- Assurance
- Stone Edge
- Low Kick

Gholdengo @ Choice Specs
Ability: Good as Gold
Level: 50
Tera Type: Steel
EVs: 252 HP / 228 SpA / 28 Spe
Modest Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Thunderbolt
- Trick

Brambleghast (F) @ Focus Sash
Ability: Wind Rider
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Poltergeist
- Power Whip
- Strength Sap
- Shadow Sneak

Glimmora (F) @ Power Herb
Ability: Toxic Debris
Level: 50
Tera Type: Grass
EVs: 4 HP / 252 SpA / 252 Spe
Modest Nature
- Meteor Beam
- Spiky Shield
- Earth Power
- Sludge Bomb""",
        """
Kingambit @ Black Glasses
Ability: Defiant
Level: 50
Tera Type: Dark
EVs: 252 HP / 252 Atk / 4 SpD
Adamant Nature
- Kowtow Cleave
- Sucker Punch
- Swords Dance
- Protect

Rillaboom @ Assault Vest
Ability: Grassy Surge
Level: 50
Tera Type: Fire
EVs: 252 HP / 116 Atk / 4 Def / 124 SpD / 12 Spe
Adamant Nature
- Wood Hammer
- Grassy Glide
- U-turn
- Fake Out

Clefable @ Safety Goggles
Ability: Unaware
Level: 50
Tera Type: Steel
EVs: 252 HP / 212 Def / 4 SpA / 36 SpD / 4 Spe
Bold Nature
IVs: 0 Atk
- Follow Me
- Helping Hand
- Moonblast
- Protect

Volcarona @ Leftovers
Ability: Flame Body
Level: 50
Tera Type: Dragon
EVs: 252 HP / 132 Def / 36 SpA / 4 SpD / 84 Spe
Modest Nature
IVs: 0 Atk
- Heat Wave
- Giga Drain
- Quiver Dance
- Protect

Sneasler (F) @ Grassy Seed
Ability: Unburden
Level: 50
Tera Type: Stellar
EVs: 164 HP / 76 Atk / 12 Def / 4 SpD / 252 Spe
Adamant Nature
- Protect
- Fake Out
- Close Combat
- Dire Claw

Dondozo @ Covert Cloak
Ability: Unaware
Level: 50
Tera Type: Steel
EVs: 244 HP / 12 Atk / 4 Def / 244 SpD / 4 Spe
Careful Nature
- Liquidation
- Fissure
- Yawn
- Curse""",
        """
Indeedee-F @ Psychic Seed
Ability: Psychic Surge
Level: 50
Tera Type: Fairy
EVs: 252 HP / 252 Def / 4 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Follow Me
- Helping Hand
- Psychic
- Trick Room

Hatterene @ Life Orb
Ability: Magic Bounce
Level: 50
Tera Type: Fire
EVs: 212 HP / 212 SpA / 84 SpD
Quiet Nature
IVs: 0 Atk / 0 Spe
- Expanding Force
- Dazzling Gleam
- Trick Room
- Mystical Fire

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

Araquanid @ Clear Amulet
Ability: Water Bubble
Level: 50
Tera Type: Grass
EVs: 252 HP / 252 Atk / 4 SpD
Brave Nature
IVs: 0 Spe
- Liquidation
- Leech Life
- Wide Guard
- Protect

Gallade @ Scope Lens
Ability: Sharpness
Level: 50
Tera Type: Grass
EVs: 252 HP / 252 Atk / 4 SpD
Adamant Nature
- Wide Guard
- Sacred Sword
- Psycho Cut
- Trick Room

Lilligant-Hisui @ Focus Sash
Ability: Chlorophyll
Level: 50
Tera Type: Ghost
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- After You
- Triple Axel
- Close Combat
- Sleep Powder""",
        """
Lokix @ Safety Goggles
Ability: Tinted Lens
Level: 50
Tera Type: Stellar
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- X-Scissor
- Swords Dance
- Throat Chop
- Protect

Venonat @ Eviolite
Ability: Compound Eyes
Level: 50
Tera Type: Grass
EVs: 252 HP / 164 Def / 92 SpD
Bold Nature
IVs: 0 Atk / 0 Spe
- Sleep Powder
- Rage Powder
- Toxic
- Morning Sun

Araquanid @ Mystic Water
Ability: Water Bubble
Level: 50
Tera Type: Water
EVs: 252 HP / 236 Atk / 20 Def
Adamant Nature
- Liquidation
- Leech Life
- Wide Guard
- Protect

Ribombee @ Focus Sash
Ability: Shield Dust
Level: 50
Tera Type: Ghost
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Sunny Day
- Tailwind
- Moonblast
- Fake Tears

Volcarona @ Choice Specs
Ability: Flame Body
Level: 50
Tera Type: Fire
EVs: 20 HP / 252 SpA / 236 Spe
Modest Nature
IVs: 0 Atk
- Fiery Dance
- Heat Wave
- Overheat
- Bug Buzz

Kleavor @ Assault Vest
Ability: Sharpness
Level: 50
Tera Type: Water
EVs: 68 HP / 252 Atk / 188 Spe
Adamant Nature
- Stone Axe
- X-Scissor
- Rock Blast
- Aerial Ace""",
        """
Sneasler @ Psychic Seed
Ability: Unburden
Level: 50
Tera Type: Dark
EVs: 4 HP / 236 Atk / 28 Def / 4 SpD / 236 Spe
Adamant Nature
- Protect
- Close Combat
- Dire Claw
- Throat Chop

Kleavor @ Focus Sash
Ability: Sharpness
Level: 50
Tera Type: Stellar
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Protect
- Stone Axe
- Night Slash
- Close Combat

Typhlosion-Hisui @ Charcoal
Ability: Frisk
Level: 50
Tera Type: Fire
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Eruption
- Shadow Ball
- Heat Wave

Hydreigon @ Razor Claw
Ability: Levitate
Level: 50
Tera Type: Fire
EVs: 4 HP / 4 Def / 244 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Protect
- Draco Meteor
- Heat Wave
- Focus Energy

Indeedee-F @ Rocky Helmet
Ability: Psychic Surge
Level: 50
Tera Type: Grass
EVs: 252 HP / 220 Def / 36 SpD
Calm Nature
IVs: 0 Atk / 27 Spe
- Helping Hand
- Follow Me
- Trick Room
- Imprison

Whimsicott @ Covert Cloak
Ability: Prankster
Level: 50
Tera Type: Dark
EVs: 252 HP / 4 Def / 4 SpA / 116 SpD / 132 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Encore
- Tailwind
- Sunny Day""",
        """
Archaludon @ Assault Vest
Ability: Stamina
Level: 50
Tera Type: Grass
EVs: 212 HP / 4 Def / 36 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Draco Meteor
- Electro Shot
- Flash Cannon
- Body Press

Pelipper @ Focus Sash
Ability: Drizzle
Level: 50
Tera Type: Ghost
EVs: 252 SpA / 4 SpD / 252 Spe
Modest Nature
IVs: 0 Atk
- Hurricane
- Weather Ball
- Helping Hand
- Tailwind

Basculegion @ Life Orb
Ability: Swift Swim
Level: 50
Tera Type: Grass
EVs: 220 Atk / 36 Def / 252 Spe
Adamant Nature
- Protect
- Wave Crash
- Aqua Jet
- Last Respects

Amoonguss @ Rocky Helmet
Ability: Regenerator
Level: 50
Tera Type: Dark
EVs: 252 HP / 100 Def / 156 SpD
Calm Nature
IVs: 0 Atk / 27 Spe
- Spore
- Pollen Puff
- Rage Powder
- Clear Smog

Kingambit @ Black Glasses
Ability: Defiant
Level: 50
Tera Type: Dark
EVs: 252 HP / 116 Atk / 4 Def / 20 SpD / 116 Spe
Adamant Nature
- Protect
- Kowtow Cleave
- Sucker Punch
- Swords Dance

Ludicolo @ Mystic Water
Ability: Swift Swim
Level: 50
Tera Type: Water
EVs: 12 HP / 36 Def / 236 SpA / 4 SpD / 220 Spe
Modest Nature
IVs: 0 Atk
- Protect
- Muddy Water
- Giga Drain
- Ice Beam""",
    ],
    "gen9ou": [
        """
Whiscash @ Leftovers
Ability: Oblivious
Tera Type: Poison
EVs: 252 HP / 252 SpA / 4 Spe
Modest Nature
IVs: 0 Atk
- Stealth Rock
- Spikes
- Hydro Pump
- Earth Power

Duraludon @ Eviolite
Ability: Heavy Metal
Tera Type: Ghost
EVs: 200 HP / 252 Def / 4 SpA / 52 Spe
Bold Nature
- Iron Defense
- Body Press
- Flash Cannon
- Dragon Tail

Zamazenta @ Light Clay
Ability: Dauntless Shield
Tera Type: Steel
EVs: 252 HP / 152 SpD / 104 Spe
Timid Nature
IVs: 0 Atk
- Reflect
- Light Screen
- Body Press
- Roar

Moltres @ Heavy-Duty Boots
Ability: Flame Body
Tera Type: Flying
EVs: 88 HP / 188 SpA / 232 Spe
Timid Nature
- Hurricane
- Flamethrower
- U-turn
- Roost

Great Tusk @ Lum Berry
Ability: Protosynthesis
Tera Type: Ice
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Bulk Up
- Earthquake
- Ice Spinner
- Rapid Spin

Ogerpon (F) @ Heavy-Duty Boots
Ability: Defiant
Tera Type: Grass
EVs: 4 HP / 252 Atk / 252 Spe
Jolly Nature
- Swords Dance
- Ivy Cudgel
- Knock Off
- Rock Tomb""",
        """
Landorus-Therian @ Leftovers
Ability: Intimidate
Shiny: Yes
Tera Type: Fire
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Earthquake
- Smack Down
- Substitute
- Swords Dance

Ribombee @ Focus Sash
Ability: Shield Dust
Shiny: Yes
Tera Type: Ghost
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Moonblast
- Stun Spore
- Skill Swap
- Sticky Web

Gholdengo @ Air Balloon
Ability: Good as Gold
Tera Type: Fairy
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Make It Rain
- Shadow Ball
- Dazzling Gleam
- Nasty Plot

Ogerpon-Wellspring @ Wellspring Mask
Ability: Water Absorb
Tera Type: Water
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Power Whip
- Ivy Cudgel
- Encore
- Swords Dance

Iron Treads @ Booster Energy
Ability: Quark Drive
Tera Type: Ghost
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
- Earth Power
- Steel Beam
- Rapid Spin
- Stealth Rock

Darkrai @ Expert Belt
Ability: Bad Dreams
Shiny: Yes
Tera Type: Poison
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Dark Pulse
- Sludge Bomb
- Ice Beam
- Focus Blast""",
        """
Cinderace @ Focus Sash
Ability: Blaze
Tera Type: Fighting
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Swords Dance
- Pyro Ball
- Reversal
- Sucker Punch

Landorus-Therian @ Rocky Helmet
Ability: Intimidate
Tera Type: Grass
EVs: 232 HP / 20 Def / 252 Spe
Timid Nature
- Stealth Rock
- Earth Power
- Taunt
- U-turn

Hatterene @ Rocky Helmet
Ability: Magic Bounce
Tera Type: Steel
EVs: 248 HP / 200 Def / 60 Spe
Bold Nature
- Psychic Noise
- Draining Kiss
- Nuzzle
- Healing Wish

Darkrai @ Roseli Berry
Ability: Bad Dreams
Tera Type: Poison
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Nasty Plot
- Dark Pulse
- Focus Blast
- Sludge Bomb

Kyurem @ Loaded Dice
Ability: Pressure
Tera Type: Electric
EVs: 56 HP / 252 Atk / 4 Def / 196 Spe
Jolly Nature
- Dragon Dance
- Substitute
- Icicle Spear
- Tera Blast

Iron Valiant @ Booster Energy
Ability: Quark Drive
Tera Type: Dark
EVs: 96 Atk / 160 SpA / 252 Spe
Naive Nature
- Destiny Bond
- Moonblast
- Knock Off
- Close Combat""",
        """
Weezing-Galar @ Terrain Extender
Ability: Misty Surge
Tera Type: Grass
EVs: 76 HP / 252 SpA / 180 Spe
Modest Nature
IVs: 0 Atk
- Strange Steam
- Sludge Wave
- Fire Blast
- Taunt

Ogerpon-Wellspring (F) @ Wellspring Mask
Ability: Water Absorb
Tera Type: Water
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Swords Dance
- Ivy Cudgel
- Power Whip
- Play Rough

Gholdengo @ Air Balloon
Ability: Good as Gold
Tera Type: Fairy
EVs: 252 HP / 72 Def / 184 Spe
Bold Nature
IVs: 0 Atk
- Nasty Plot
- Shadow Ball
- Dazzling Gleam
- Recover

Great Tusk @ Booster Energy
Ability: Protosynthesis
Tera Type: Steel
EVs: 252 HP / 4 Atk / 252 Spe
Jolly Nature
- Bulk Up
- Headlong Rush
- Ice Spinner
- Rapid Spin

Roaring Moon @ Booster Energy
Ability: Protosynthesis
Shiny: Yes
Tera Type: Ground
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Dragon Dance
- Knock Off
- Acrobatics
- Earthquake

Glimmora @ Red Card
Ability: Toxic Debris
Tera Type: Ghost
EVs: 4 Def / 252 SpA / 252 Spe
Timid Nature
- Stealth Rock
- Mortal Spin
- Power Gem
- Earth Power""",
        """
Rillaboom @ Terrain Extender
Ability: Grassy Surge
Tera Type: Steel
EVs: 200 HP / 252 Atk / 56 Spe
Adamant Nature
- Grassy Glide
- Knock Off
- Low Kick
- U-turn

Bellossom (F) @ Grassy Seed
Ability: Chlorophyll
Shiny: Yes
Tera Type: Fire
EVs: 80 HP / 4 Def / 232 SpA / 192 Spe
Timid Nature
- Giga Drain
- Tera Blast
- Quiver Dance
- Strength Sap

Glimmora @ Focus Sash
Ability: Toxic Debris
Tera Type: Ghost
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
- Mortal Spin
- Dazzling Gleam
- Mud Shot
- Stealth Rock

Hawlucha @ Grassy Seed
Ability: Unburden
Tera Type: Ground
EVs: 72 HP / 252 Atk / 60 SpD / 124 Spe
Adamant Nature
- Swords Dance
- Close Combat
- Acrobatics
- Encore

Hatterene @ Grassy Seed
Ability: Magic Bounce
Tera Type: Steel
EVs: 252 HP / 192 Def / 64 Spe
Bold Nature
- Calm Mind
- Draining Kiss
- Stored Power
- Nuzzle

Roaring Moon @ Booster Energy
Ability: Protosynthesis
Tera Type: Flying
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Dragon Dance
- Knock Off
- Acrobatics
- Brick Break""",
    ],
}
