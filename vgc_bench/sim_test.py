import asyncio
import random

from poke_env.battle import DoubleBattle
from poke_env.concurrency import POKE_LOOP
from poke_env.player import Player
from poke_env.ps_client import AccountConfiguration
from src.simulator import Simulator
from src.teams import RandomTeamBuilder


class ManualPlayer(Player):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._pending = asyncio.Queue()

    async def choose_move(self, battle):
        fut = asyncio.get_running_loop().create_future()
        await self._pending.put((battle, fut))
        return await fut


async def main():
    p1 = ManualPlayer(
        account_configuration=AccountConfiguration(f"p{random.randint(0, 999999)}", None),
        battle_format="gen9vgc2024regg",
        accept_open_team_sheet=True,
        team=RandomTeamBuilder(1, 1, "gen9vgc2024regg"),
    )
    p2 = ManualPlayer(
        account_configuration=AccountConfiguration(f"p{random.randint(0, 999999)}", None),
        battle_format="gen9vgc2024regg",
        accept_open_team_sheet=True,
        team=RandomTeamBuilder(1, 1, "gen9vgc2024regg"),
    )
    asyncio.run_coroutine_threadsafe(p1.battle_against(p2), loop=POKE_LOOP)
    while not p1.battles:
        await asyncio.sleep(0.1)
    battle_tag = list(p1._battles.keys())[0]
    battle1 = p1._battles[battle_tag]
    assert isinstance(battle1, DoubleBattle)
    sim = Simulator(battle1, verbose=True)
    while not sim.battle.finished:
        print("p1a:", [str(o) for o in sim.battle.valid_orders[0]], flush=True)
        print("p1b:", [str(o) for o in sim.battle.valid_orders[1]], flush=True)
        order1 = Player.choose_random_move(sim.battle).message if not sim.battle._wait else None
        print("p2a:", [str(o) for o in sim.opp_battle.valid_orders[0]], flush=True)
        print("p2b:", [str(o) for o in sim.opp_battle.valid_orders[1]], flush=True)
        order2 = (
            Player.choose_random_move(sim.opp_battle).message if not sim.opp_battle._wait else None
        )
        sim.step(order1, order2)


if __name__ == "__main__":
    asyncio.run(main())
