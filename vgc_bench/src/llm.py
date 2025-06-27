import json
import re
from typing import Any

import numpy as np
import torch
import transformers
from poke_env.battle import AbstractBattle, DoubleBattle, Move, Pokemon
from poke_env.environment import DoublesEnv
from poke_env.player import BattleOrder, DefaultBattleOrder, Player
from src.agent import Agent


class LLMPlayer(Player):
    def __init__(self, device: str, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.__teampreview_draft = []
        tokenizer = transformers.AutoTokenizer.from_pretrained(
            "meta-llama/Meta-Llama-3.1-8B-Instruct", use_auth_token=True
        )
        model = transformers.AutoModelForCausalLM.from_pretrained(
            "meta-llama/Meta-Llama-3.1-8B-Instruct",
            torch_dtype=torch.bfloat16,
            device_map=device,
            use_auth_token=True,
        )
        tokenizer.pad_token = tokenizer.eos_token
        model.config.pad_token_id = tokenizer.eos_token_id
        self.model = transformers.pipeline("text-generation", model=model, tokenizer=tokenizer)  # type: ignore

    def choose_move(self, battle: AbstractBattle) -> BattleOrder:
        assert isinstance(battle, DoubleBattle)
        prompt = self.explain_battle(battle, self.__teampreview_draft)
        try:
            input_dict = [
                {
                    "role": "system",
                    "content": f"You are an expert Pokemon VGC competitor playing a Pokemon battle in the {battle.format} format.",
                },
                {"role": "user", "content": prompt},
            ]
            response: str = self.model(input_dict)[0]["generated_text"][-1]["content"]  # type: ignore
            action = np.array(json.loads(response))
        except ValueError:
            action = np.array([-2, -2])
        order = DoublesEnv.action_to_order(action, battle, strict=False)
        if isinstance(order, DefaultBattleOrder):
            return self.choose_random_move(battle)
        return order

    def teampreview(self, battle: AbstractBattle) -> str:
        assert isinstance(battle, DoubleBattle)
        team_pokemon = list(battle.team.values())
        opponent_pokemon = list(battle.opponent_team.values())
        prompt = f"""
Here is the following observation:

Your Pokemon:
    1. {team_pokemon[0].base_species}
{LLMPlayer.explain_pokemon(team_pokemon[0])}
    2. {team_pokemon[1].base_species}
{LLMPlayer.explain_pokemon(team_pokemon[1])}
    3. {team_pokemon[2].base_species}
{LLMPlayer.explain_pokemon(team_pokemon[2])}
    4. {team_pokemon[3].base_species}
{LLMPlayer.explain_pokemon(team_pokemon[3])}
    5. {team_pokemon[4].base_species}
{LLMPlayer.explain_pokemon(team_pokemon[4])}
    6. {team_pokemon[5].base_species}
{LLMPlayer.explain_pokemon(team_pokemon[5])}
Opponent Pokemon:
    1. {opponent_pokemon[0].base_species}
{LLMPlayer.explain_pokemon(opponent_pokemon[0])}
    2. {opponent_pokemon[1].base_species}
{LLMPlayer.explain_pokemon(opponent_pokemon[1])}
    3. {opponent_pokemon[2].base_species}
{LLMPlayer.explain_pokemon(opponent_pokemon[2])}
    4. {opponent_pokemon[3].base_species}
{LLMPlayer.explain_pokemon(opponent_pokemon[3])}
    5. {opponent_pokemon[4].base_species}
{LLMPlayer.explain_pokemon(opponent_pokemon[4])}
    6. {opponent_pokemon[5].base_species}
{LLMPlayer.explain_pokemon(opponent_pokemon[5])}

You must respond with the indices of which Pokemon you wish to bring to the battle from teampreview. You can only select from your Pokemon, NOT the opponent's Pokemon.
Please respond with the format /team <action1><action2><action3><action4>. The order that you set the numbers determines the order that they come in. So, if you send /turn 1246, 1 and 2 will lead and 4 and 6 will be on the bench, whereas if you do /turn 4162, then 4 and 1 will lead and 6 and 2 will be on the bench. You need not limit yourself to the set of numbers 1, 2, 4, and 6; any number from 1-6 is acceptable, and each can only be used once.
Do **not** include any extra text, punctuation, or explanation.
"""
        input_dict = [
            {
                "role": "system",
                "content": f"You are an expert Pokemon VGC competitor playing a Pokemon battle in the {battle.format} format. You are currently in teampreview.",
            },
            {"role": "user", "content": prompt},
        ]
        response: str = self.model(input_dict)[0]["generated_text"][-1]["content"]  # type: ignore
        if re.match(r"^/team (?!.*([1-6]).*\1)[1-6]{4}$", response) is None:
            response = self.random_teampreview(battle)[:-2]
        self.__teampreview_draft = [int(i) for i in response[6:]]
        return response

    @staticmethod
    def explain_battle(battle: DoubleBattle, teampreview_draft: list[int]) -> str:
        glob = LLMPlayer.explain_global(battle)
        side = LLMPlayer.explain_side(battle)
        opp_side = LLMPlayer.explain_side(battle, opp=True)
        [a1, a2] = battle.active_pokemon
        [o1, o2] = battle.opponent_active_pokemon
        benched_pokemon = [
            p
            for i, p in enumerate(battle.team.values())
            if i + 1 in teampreview_draft and p not in [a1, a2]
        ]
        opp_benched_pokemon = [p for p in battle.opponent_team.values() if p not in [o1, o2]]
        action_space1 = Agent.get_action_space(battle, 0)
        action_space2 = Agent.get_action_space(battle, 1)
        return f"""
The following is what you are currently observing:

Global Conditions in Battle:
{glob}
Side Conditions:
{side}
Active Pokemon:
    1. {a1.base_species if a1 is not None else ""}
{LLMPlayer.explain_pokemon(a1) if a1 is not None else ""}
    2. {a2.base_species if a2 is not None else ""}
{LLMPlayer.explain_pokemon(a2) if a2 is not None else ""}
Benched Pokemon:
    1. {benched_pokemon[0].base_species}
{LLMPlayer.explain_pokemon(benched_pokemon[0])}
    2. {benched_pokemon[1].base_species}
{LLMPlayer.explain_pokemon(benched_pokemon[1])}
    3. {benched_pokemon[2].base_species if len(benched_pokemon) > 2 else ""}
{LLMPlayer.explain_pokemon(benched_pokemon[2]) if len(benched_pokemon) > 2 else ""}
Opponent Side Conditions:
{opp_side}
Opponent Active Pokemon:
    1. {o1.base_species if o1 is not None else ""}
{LLMPlayer.explain_pokemon(o1) if o1 is not None else ""}
    2. {o2.base_species if o2 is not None else ""}
{LLMPlayer.explain_pokemon(o2) if o2 is not None else ""}
Opponent Benched Pokemon:
    1. {opp_benched_pokemon[0].base_species}
{LLMPlayer.explain_pokemon(opp_benched_pokemon[0])}
    2. {opp_benched_pokemon[1].base_species}
{LLMPlayer.explain_pokemon(opp_benched_pokemon[1])}
    3. {opp_benched_pokemon[2].base_species}
{LLMPlayer.explain_pokemon(opp_benched_pokemon[2])}
    4. {opp_benched_pokemon[3].base_species}
{LLMPlayer.explain_pokemon(opp_benched_pokemon[3])}
    5. {opp_benched_pokemon[4].base_species if len(opp_benched_pokemon) > 4 else ""}
{LLMPlayer.explain_pokemon(opp_benched_pokemon[4]) if len(opp_benched_pokemon) > 4 else ""}

Please select the optimal move given this observation. Your response must be of the form [<action1>, <action2>], where action1 and action2 are integers with the following meanings:

action = -2: default
action = -1: forfeit
action = 0: pass
1 <= action <= 6: switch to pokemon <action
7 <= action <= 11: move 1
12 <= action <= 16: move 2
17 <= action <= 21: move 3
22 <= action <= 26: move 4
27 <= action <= 31: move 1 and mega evolve
32 <= action <= 36: move 2 and mega evolve
37 <= action <= 41: move 3 and mega evolve
42 <= action <= 46: move 4 and mega evolve
47 <= action <= 51: move 1 and z-move
52 <= action <= 56: move 2 and z-move
57 <= action <= 61: move 3 and z-move
62 <= action <= 66: move 4 and z-move
67 <= action <= 71: move 1 and dynamax
72 <= action <= 76: move 2 and dynamax
77 <= action <= 81: move 3 and dynamax
82 <= action <= 86: move 4 and dynamax
87 <= action <= 91: move 1 and terastallize
92 <= action <= 96: move 2 and terastallize
97 <= action <= 101: move 3 and terastallize
102 <= action <= 106: move 4 and terastallize

For all move actions, notice that there are 5 allowed values for each slot. This is because the target is also encoded into the action. The target encoding is:
+0: Your Active Pokemon #2
+1: Your Active Pokemon #1
+2: No target (move doesn't target anything)
+3: Opponent's Active Pokemon #1
+4: Opponent's Active Pokemon #2
For example, if I want to use my first Pokemon's first attack on the opponent's second Pokemon and terastallize, and use my second Pokemon's third move on the opponent's first Pokemon, this is how we would derive the action:
1. Our first Pokemon wants to use its first move, which is in the range 7 <= action <= 11, but it wants to terastallize, so the range would be 87 <= action <= 91. We want to target the opponent's second Pokemon, so we take the +4 index of that range, which yields 91.
2. Our second Pokemon wants to use its third move, which is in the range 17 <= action <= 21. We want to target the opponent's first Pokemon, so we take the +3 index of that range, which yields 20.
Therefore, our final answer is [91, 20].

To aid you in making your decision, we provide you action spaces to make sure that your actions are valid. The actions you pick MUST BE INCLUDED in the corresponding list.

The following is the action space of your first Pokemon (the action space for action1):
{action_space1}

The following is the action space of your second Pokemon (the action space for action2):
{action_space2}

NOTE: if both Pokemon are switching, they cannot switch into the same Pokemon. Also, you cannot terastallize with both Pokemon, even if the option is available to both. Only one Pokemon can terastallize.
Therefore, the following example actions are invalid, no matter what the action spaces are:
1. [4, 4] (because that is switching in the same Pokemon for both options)
2. [91, 102] (because that is terastallizing both Pokemon simultaneously)

Please remember, your only allowed response MUST BE of the format [<action1>, <action2>]. PLEASE GIVE NO FURTHER RESPONSE THAN THAT!
"""

    @staticmethod
    def explain_global(battle: DoubleBattle) -> str:
        return f"""
    Current Turn: {battle.turn}
    Your Pokemon 1 is being forced to switch: {battle.force_switch[0]}
    Your Pokemon 2 is being forced to switch: {battle.force_switch[1]}
    The active weather in the game (as a dictionary, mapping to its starting turn): {battle.weather}
    The active fields in the game (as a dictionary, mapping to its starting turn): {battle.fields}
"""

    @staticmethod
    def explain_side(battle: DoubleBattle, opp: bool = False) -> str:
        gims = [
            battle.can_mega_evolve[0],
            battle.can_z_move[0],
            battle.can_dynamax[0],
            battle.can_tera[0] is not False,
        ]
        opp_gims = [
            battle.opponent_used_mega_evolve,
            battle.opponent_used_z_move,
            battle.opponent_used_dynamax,
            battle._opponent_used_tera,
        ]
        side_conds = battle.opponent_side_conditions if opp else battle.side_conditions
        gims = opp_gims if opp else gims
        rat = battle.opponent_rating if opp else battle.rating
        return f"""
Player Rating: {rat}
Player can still mega evolve: {gims[0]}
Player can still z-move: {gims[1]}
Player can still dynamax/gigantamax: {gims[2]}
Player can still terastallize: {gims[3]}
Side conditions on this player's side (the number of layers of the SideCondition if the side condition is stackable, or the turn where the SideCondition was setup otherwise): {side_conds}
"""

    @staticmethod
    def explain_pokemon(pokemon: Pokemon) -> str:
        move_names = list(pokemon.moves.keys())
        moves = list(pokemon.moves.values())
        return f"""
        Ability: {pokemon.ability}
        Item: {pokemon.item}
        Moves:
            1. {move_names[0] if move_names[0] else ""}
        {LLMPlayer.explain_move(moves[0]) if moves[0] else ""}
            2. {move_names[1] if move_names[1] else ""}
        {LLMPlayer.explain_move(moves[1]) if moves[1] else ""}
            3. {move_names[2] if move_names[2] else ""}
        {LLMPlayer.explain_move(moves[2]) if moves[2] else ""}
            4. {move_names[3] if move_names[3] else ""}
        {LLMPlayer.explain_move(moves[3]) if moves[3] else ""}
        Types: {pokemon.types[0]}, {pokemon.types[1] if len(pokemon.types) == 2 else ""}
        Tera Type: {pokemon.tera_type}
        Stats: {pokemon.stats["hp"]} HP, {pokemon.stats["atk"]} Attack, {pokemon.stats["def"]} Defense, {pokemon.stats["spa"]} Special Attack, {pokemon.stats["spd"]} Special Defense, {pokemon.stats["spe"]} Speed
        Gender: {pokemon.gender}
        Weight: {pokemon.weight}
        Current HP Fraction: {pokemon.current_hp_fraction}
        Has been revealed in battle: {pokemon.revealed}
        Status effect: {pokemon.status}
        Number of turns with that status effect (only for toxic and sleep): {pokemon.status_counter}
        Boosts: {pokemon.boosts["accuracy"]} Accuracy, {pokemon.boosts["atk"]} Attack, {pokemon.boosts["def"]} Defense, {pokemon.boosts["evasion"]} Evasion, {pokemon.boosts["spa"]} Special Attack, {pokemon.boosts["spd"]} Special Defense, {pokemon.boosts["spe"]} Speed
        Effects (mapping effect name to number of turns left for the effect): {pokemon.effects}
        Is first turn being in (effects moves like fake out): {pokemon.first_turn}
        Number of turns protect has been used in a row: {pokemon.protect_counter}
        Currently recharging (from a move like hyper beam): {pokemon.must_recharge}
        Is currently preparing a move (like solar beam): {pokemon.preparing}
        Is dynamaxed: {pokemon.is_dynamaxed}
        Is terastallized: {pokemon.is_terastallized}
"""

    @staticmethod
    def explain_move(move: Move) -> str:
        return f"""
                Power: {move.base_power}
                Accuracy: {move.accuracy}
                Type: {move.type}
                Category: {move.category}
                Target: {move.target}
                Priority: {move.priority}
                Critical-hit Ratio: {move.crit_ratio}
                Drain ratio: {move.drain}
                Forces switch: {move.force_switch}
                Has recoil damage: {move.recoil}
                Switches self out: {move.self_switch}
                Current PP: {move.current_pp}
                Max PP: {move.max_pp}
"""
