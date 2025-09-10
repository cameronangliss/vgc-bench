import random
from typing import Any

import numpy as np
import torch
import transformers
from poke_env.battle import AbstractBattle, DoubleBattle, Move, Pokemon
from poke_env.environment import DoublesEnv
from poke_env.player import BattleOrder, DefaultBattleOrder, Player
from src.policy import MaskedActorCriticPolicy
from src.policy_player import PolicyPlayer
from src.utils import act_len


class LLMPlayer(Player):
    def __init__(self, device: str, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.device = device
        self._teampreview_drafts = {}
        self.setup_llm()

    def setup_llm(self):
        tokenizer = transformers.AutoTokenizer.from_pretrained(
            "meta-llama/Meta-Llama-3.1-8B-Instruct"
        )
        model = transformers.AutoModelForCausalLM.from_pretrained(
            "meta-llama/Meta-Llama-3.1-8B-Instruct", torch_dtype="auto", device_map=self.device
        )
        tokenizer.pad_token = tokenizer.eos_token
        model.config.pad_token_id = tokenizer.eos_token_id
        self.model = transformers.pipelines.pipeline(
            "text-generation", model=model, tokenizer=tokenizer
        )

    def get_response(self, prompt: str) -> str:
        input_dict = [
            {
                "role": "system",
                "content": (
                    "You are the strongest player of all time in competitive Pokemon VGC, "
                    "the official competitive format for the core Pokemon video game series. "
                    "You will do everything in your power to win this current battle, "
                    "since this is the finals of the biggest tournament ever."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        response = self.model(input_dict)[0]["generated_text"][-1]["content"]
        return response

    def choose_move(self, battle: AbstractBattle) -> BattleOrder:
        assert isinstance(battle, DoubleBattle)
        action1 = self.choose_move_individual(battle, 0, None)
        if action1 < 0:
            return DefaultBattleOrder()
        action2 = self.choose_move_individual(battle, 1, action1)
        action = np.array([action1, action2])
        order = DoublesEnv.action_to_order(action, battle)
        return order

    def choose_move_individual(
        self, battle: DoubleBattle, pos: int, ally_action: np.int64 | None
    ) -> np.int64:
        if pos == 0:
            mask = torch.tensor(PolicyPlayer.get_action_mask(battle, 0))
            ally_order = None
        else:
            assert ally_action is not None
            mask = torch.tensor(
                [PolicyPlayer.get_action_mask(battle, 0) + PolicyPlayer.get_action_mask(battle, 1)]
            )
            ally_action_tensor = torch.tensor([[ally_action]])
            mask = MaskedActorCriticPolicy._update_mask(mask, ally_action_tensor)[0, act_len:]
            ally_order = DoublesEnv._action_to_order_individual(ally_action, battle, False, 0)
        action_space = [i for i, m in enumerate(mask.tolist()) if m == 1]
        if not action_space:
            return np.int64(0)
        elif len(action_space) == 1:
            return np.int64(action_space[0])
        order_space = [
            DoublesEnv._action_to_order_individual(np.int64(a), battle, False, pos)
            for a in action_space
        ]
        action_names = [
            self.explain_battle_order(battle, o, pos) for o in order_space if o is not None
        ]
        prompt = self.explain_battle(
            battle, self._teampreview_drafts[battle.battle_tag], action_names, ally_order, pos
        )
        response = self.get_response(prompt)
        try:
            action_index = int(response) - 1
            action = action_space[action_index]
        except IndexError:
            print(f"INDEX OUT OF BOUNDS: {response}", flush=True)
            action = -2
        except ValueError:
            print(f"INVALID RESPONSE: {response}", flush=True)
            action = -2
        return np.int64(action)

    def teampreview(self, battle: AbstractBattle) -> str:
        assert isinstance(battle, DoubleBattle)
        self._teampreview_drafts = {
            tag: preview
            for tag, preview in self._teampreview_drafts.items()
            if tag in self.battles and not self.battles[tag].finished
        }
        actives = []
        bench = []
        self._teampreview_drafts[battle.battle_tag] = []
        for _ in range(2):
            actives += [self.teampreview_individual(battle, actives, bench)]
            self._teampreview_drafts[battle.battle_tag] += [
                i for i, p in enumerate(battle.team.values(), start=1) if p == actives[-1]
            ]
        for _ in range(2):
            bench += [self.teampreview_individual(battle, actives, bench)]
            self._teampreview_drafts[battle.battle_tag] += [
                i for i, p in enumerate(battle.team.values(), start=1) if p == bench[-1]
            ]
        return f"/team {','.join([str(i) for i in self._teampreview_drafts[battle.battle_tag]])}"

    def teampreview_individual(
        self, battle: DoubleBattle, actives: list[Pokemon], bench: list[Pokemon]
    ) -> Pokemon:
        remaining_pokemon = [p for p in battle.team.values() if p not in actives and p not in bench]
        prompt = self.explain_battle_teampreview(battle, actives, bench)
        response = self.get_response(prompt)
        try:
            action_index = int(response) - 1
            mon = remaining_pokemon[action_index]
        except IndexError:
            print(f"INDEX OUT OF BOUNDS (teampreview): {response}", flush=True)
            mon = random.choice(remaining_pokemon)
        except ValueError:
            print(f"INVALID RESPONSE (teampreview): {response}", flush=True)
            mon = random.choice(remaining_pokemon)
        return mon

    @staticmethod
    def explain_battle(
        battle: DoubleBattle,
        teampreview_draft: list[int],
        action_names: list[str],
        last_order: BattleOrder | None,
        pos: int,
    ) -> str:
        active_mon = battle.active_pokemon[pos]
        a1 = battle._active_pokemon[f"{battle.player_role}a"]
        a2 = battle._active_pokemon[f"{battle.player_role}b"]
        o1 = battle._opponent_active_pokemon[f"{battle.opponent_role}a"]
        o2 = battle._opponent_active_pokemon[f"{battle.opponent_role}b"]
        benched_pokemon = [
            p
            for i, p in enumerate(battle.team.values(), start=1)
            if i in teampreview_draft and p not in [a1, a2]
        ]
        opp_benched_pokemon = [p for p in battle.opponent_team.values() if p not in [o1, o2]]
        listed_action_space = "\n".join(f"{i + 1}. {name}" for i, name in enumerate(action_names))
        return f"""The following is what you are currently observing:

########## GLOBAL EFFECTS ##########

Active weather: {", ".join([f"{w.name.lower()} (active for {battle.turn - turn} turns)" for w, turn in battle.weather.items()]) or "None"}
Active fields: {", ".join([f"{f.name.lower()} (active for {battle.turn - turn} turns)" for f, turn in battle.fields.items()]) or "None"}

########## YOUR SIDE ##########

{"Tera used." if battle.used_tera else "Tera available."}
Active side conditions: {", ".join([s.name.lower() for s in battle.side_conditions.keys()]) or None}

### Active Pokemon ###

Slot 1: {LLMPlayer.explain_pokemon(a1)}

Slot 2: {LLMPlayer.explain_pokemon(a2)}

### Benched Pokemon ###

1. {LLMPlayer.explain_pokemon(benched_pokemon[0])}

2. {LLMPlayer.explain_pokemon(benched_pokemon[1])}

########## OPPONENT SIDE ##########

Rating: {battle.opponent_rating}
{"Opponent's tera already used." if battle.opponent_used_tera else "Tera available for opponent!"}
Active side conditions: {", ".join([s.name.lower() for s in battle.opponent_side_conditions.keys()]) or "None"}

### Active Pokemon ###

1. {LLMPlayer.explain_pokemon(o1)}

2. {LLMPlayer.explain_pokemon(o2)}

### Benched Pokemon ###

1. {LLMPlayer.explain_pokemon(opp_benched_pokemon[0])}

2. {LLMPlayer.explain_pokemon(opp_benched_pokemon[1])}

3. {LLMPlayer.explain_pokemon(opp_benched_pokemon[2])}

4. {LLMPlayer.explain_pokemon(opp_benched_pokemon[3])}

########## MAKE YOUR DECISION ##########

Please select the optimal action for slot {pos + 1}{f" (your {active_mon.base_species})" if active_mon is not None else ""}. {f"The action you already chose for your first slot was {last_order}." if pos == 1 else ""}

Here are your available actions:
{listed_action_space}

Respond with the number corresponding to your chosen action. PLEASE GIVE NO FURTHER RESPONSE THAN THAT, JUST THE NUMBER WITH NO PUNCTUATION!"""

    @staticmethod
    def explain_battle_teampreview(
        battle: DoubleBattle, actives: list[Pokemon], bench: list[Pokemon]
    ) -> str:
        remaining_pokemon = [p for p in battle.team.values() if p not in actives and p not in bench]
        opponent_pokemon = list(battle.opponent_team.values())
        return f"""The following is what you are currently observing in teampreview:

########## YOUR SIDE ##########

### Your already-made active choices ###

1. {LLMPlayer.explain_inactive_pokemon(actives[0]) if actives else "empty"}

2. {LLMPlayer.explain_inactive_pokemon(actives[1]) if len(actives) > 1 else "empty"}

### Your already-made bench choices ###

1. {LLMPlayer.explain_inactive_pokemon(bench[0]) if bench else "empty"}

2. {LLMPlayer.explain_inactive_pokemon(bench[1]) if len(bench) > 1 else "empty"}

### Your still-unchosen Pokemon ###

{LLMPlayer.explain_remaining_pokemon(remaining_pokemon)}

########## OPPONENT SIDE ##########

1. {LLMPlayer.explain_inactive_pokemon(opponent_pokemon[0])}

2. {LLMPlayer.explain_inactive_pokemon(opponent_pokemon[1])}

3. {LLMPlayer.explain_inactive_pokemon(opponent_pokemon[2])}

4. {LLMPlayer.explain_inactive_pokemon(opponent_pokemon[3])}

5. {LLMPlayer.explain_inactive_pokemon(opponent_pokemon[4])}

6. {LLMPlayer.explain_inactive_pokemon(opponent_pokemon[5])}

########## MAKE YOUR DECISION ##########

Please select a Pokemon from the "Your still-unchosen Pokemon" section to be put in position {len(actives) + 1 if len(actives) < 2 else len(bench) + 1} of the "Your already-made {"active" if len(actives) < 2 else "bench"} choices" section.

Just to recap, your available responses in the "Your still-unchosen Pokemon" section are:
{LLMPlayer.explain_remaining_pokemon_short(remaining_pokemon)}

Respond with the number corresponding to your choice. PLEASE GIVE NO FURTHER RESPONSE THAN THAT, JUST THE NUMBER WITH NO PUNCTUATION!"""

    @staticmethod
    def explain_battle_order(battle: DoubleBattle, order: BattleOrder, pos: int) -> str:
        order_str = str(order).removeprefix("/choose ")
        if order_str.endswith(" 1"):
            target = (
                battle.opponent_active_pokemon[0].base_species
                if battle.opponent_active_pokemon[0] is not None
                else "empty slot"
            )
            order_str = f"{order_str[:-2]} targeting foe's {target}"
        elif order_str.endswith(" 2"):
            target = (
                battle.opponent_active_pokemon[1].base_species
                if battle.opponent_active_pokemon[1] is not None
                else "empty slot"
            )
            order_str = f"{order_str[:-2]} targeting foe's {target}"
        elif order_str.endswith(" -1"):
            target = (
                battle.active_pokemon[0].base_species
                if battle.active_pokemon[0] is not None
                else "empty slot"
            )
            order_str = f"{order_str[:-3]} targeting your {target}"
        elif order_str.endswith(" -2"):
            target = (
                battle.active_pokemon[1].base_species
                if battle.active_pokemon[1] is not None
                else "empty slot"
            )
            order_str = f"{order_str[:-3]} targeting your {target}"
        if "terastallize" in order_str:
            active_mon = battle.active_pokemon[pos]
            assert active_mon is not None
            assert active_mon.tera_type is not None
            order_str = order_str.replace(
                "terastallize", f"activating {active_mon.tera_type.name.lower()} tera type"
            )
        return order_str

    @staticmethod
    def explain_remaining_pokemon(remaining_pokemon: list[Pokemon]) -> str:
        remain_str = f"1. {LLMPlayer.explain_inactive_pokemon(remaining_pokemon[0])}"
        remain_str += f"\n\n2. {LLMPlayer.explain_inactive_pokemon(remaining_pokemon[1])}"
        remain_str += f"\n\n3. {LLMPlayer.explain_inactive_pokemon(remaining_pokemon[2])}"
        if len(remaining_pokemon) > 3:
            remain_str += f"\n\n4. {LLMPlayer.explain_inactive_pokemon(remaining_pokemon[3])}"
        if len(remaining_pokemon) > 4:
            remain_str += f"\n\n5. {LLMPlayer.explain_inactive_pokemon(remaining_pokemon[4])}"
        if len(remaining_pokemon) > 5:
            remain_str += f"\n\n6. {LLMPlayer.explain_inactive_pokemon(remaining_pokemon[5])}"
        return remain_str

    @staticmethod
    def explain_remaining_pokemon_short(remaining_pokemon: list[Pokemon]) -> str:
        remain_str = f"1. {remaining_pokemon[0].base_species}"
        remain_str += f"\n2. {remaining_pokemon[1].base_species}"
        remain_str += f"\n3. {remaining_pokemon[2].base_species}"
        if len(remaining_pokemon) > 3:
            remain_str += f"\n4. {remaining_pokemon[3].base_species}"
        if len(remaining_pokemon) > 4:
            remain_str += f"\n5. {remaining_pokemon[4].base_species}"
        if len(remaining_pokemon) > 5:
            remain_str += f"\n6. {remaining_pokemon[5].base_species}"
        return remain_str

    @staticmethod
    def explain_pokemon(pokemon: Pokemon) -> str:
        if pokemon.fainted:
            return f"{pokemon.base_species} | fainted"
        elif not pokemon.active:
            return LLMPlayer.explain_inactive_pokemon(pokemon)
        else:
            return (
                LLMPlayer.explain_inactive_pokemon(pokemon)
                + f"""
{LLMPlayer.explain_boosts(pokemon.boosts)}
Effects: {", ".join([f"{e.name.lower()} (active for {counter} turns)" for e, counter in pokemon.effects.items()]) or "None"}
Is in first active turn (effects moves like fake out): {pokemon.first_turn}
Number of turns user has protected in a row: {pokemon.protect_counter}"""
            )

    @staticmethod
    def explain_inactive_pokemon(pokemon: Pokemon) -> str:
        moves = list(pokemon.moves.values())
        reveal_str = "revealed in battle" if pokemon.revealed else "unrevealed in battle"
        type_str = "/".join([t.name.lower() for t in pokemon.types])
        tera_type_str = (
            str(pokemon.tera_type.name.lower()) if pokemon.tera_type is not None else "None"
        )
        if pokemon.tera_type is not None and not pokemon.is_terastallized:
            tera_type_str += f" (unused)"
        hp_str = f"{round(100 * pokemon.current_hp_fraction)}%" if pokemon.max_hp > 0 else "unknown"
        if pokemon.fainted:
            return f"{pokemon.base_species} | fainted"
        return f"""{pokemon.base_species} | HP: {hp_str} | type: {type_str} | tera-type: {tera_type_str} | {reveal_str}
Ability: {pokemon.ability}
Item: {pokemon.item}
Status Effect: {pokemon.status.name.lower() if pokemon.status is not None else "None"}
Moves:
    - {LLMPlayer.explain_move(moves[0]) if len(moves) > 0 else "None"}
    - {LLMPlayer.explain_move(moves[1]) if len(moves) > 1 else "None"}
    - {LLMPlayer.explain_move(moves[2]) if len(moves) > 2 else "None"}
    - {LLMPlayer.explain_move(moves[3]) if len(moves) > 3 else "None"}
Base stats:
    {pokemon.base_stats["hp"]} HP
    {pokemon.base_stats["atk"]} Attack
    {pokemon.base_stats["def"]} Defense
    {pokemon.base_stats["spa"]} Special Attack
    {pokemon.base_stats["spd"]} Special Defense
    {pokemon.base_stats["spe"]} Speed"""

    @staticmethod
    def explain_move(move: Move) -> str:
        return f"{move.id} | pp: {move.current_pp}/{move.max_pp} | type: {move.type.name.lower()} | power: {move.base_power} | acc: {int(100 * move.accuracy)}% | category: {move.category.name.lower()}"

    @staticmethod
    def explain_boosts(boosts: dict[str, int]) -> str:
        boost_str = "Stat Modifiers:"
        if boosts["atk"] != 0:
            boost_str += f"\n    Attack: x{LLMPlayer.explain_boost(boosts['atk'])}"
        if boosts["def"] != 0:
            boost_str += f"\n    Defense: x{LLMPlayer.explain_boost(boosts['def'])}"
        if boosts["spa"] != 0:
            boost_str += f"\n    Special Attack: x{LLMPlayer.explain_boost(boosts['spa'])}"
        if boosts["spd"] != 0:
            boost_str += f"\n    Special Defense: x{LLMPlayer.explain_boost(boosts['spd'])}"
        if boosts["spe"] != 0:
            boost_str += f"\n    Speed: x{LLMPlayer.explain_boost(boosts['spe'])}"
        if boosts["accuracy"] != 0:
            boost_str += f"\n    Accuracy: x{LLMPlayer.explain_boost(boosts['accuracy'])}"
        if boosts["evasion"] != 0:
            boost_str += f"\n    Evasion: x{LLMPlayer.explain_boost(boosts['evasion'])}"
        if boost_str == "Stat Modifiers:":
            boost_str += " None"
        return boost_str

    @staticmethod
    def explain_boost(boost: int) -> float:
        if boost >= 0:
            modifier = (2 + boost) / 2
        else:
            modifier = 2 / (2 - boost)
        return round(modifier, ndigits=2)
