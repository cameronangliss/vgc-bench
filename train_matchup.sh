#!/bin/bash

reg=G
port=8000
num_env_workers=1
num_eval_workers=1

# sample teams
# finals matchup of World Championships 2024 in Honolulu
# Luca Ceribelli vs. Yuta Ishigaki
TEAM1="""
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
"""
TEAM2="""
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
"""

start_showdown() {
    local port=$1
    (
        cd pokemon-showdown
        node pokemon-showdown start "$port" --no-security > /dev/null 2>&1 &
        echo $!
    )
}

echo "Starting Showdown server..."
showdown_pid=$(start_showdown "$port")
sleep 5  # give server time to start
echo "Starting training..."
python -m vgc_bench.train \
    --reg "$reg" \
    --port "$port" \
    --num_envs "$num_env_workers" \
    --num_eval_workers "$num_eval_workers" \
    --behavior_clone \
    --self_play \
    --no_mirror_match \
    --team1 "$TEAM1" \
    --team2 "$TEAM2" \
    > "debug$port.log" 2>&1
exit_status=$?
if [ $exit_status -ne 0 ]; then
    echo "Training process died with exit status $exit_status"
else
    echo "Training process finished!"
fi
kill $showdown_pid
