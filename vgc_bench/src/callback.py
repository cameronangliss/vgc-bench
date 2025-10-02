import random

from ray.rllib.algorithms.callbacks import DefaultCallbacks
from src.teams import TEAMS, RandomTeamBuilder
from src.utils import battle_format


class Callback(DefaultCallbacks):
    def __init__(
        self, run_id: int, num_teams: int, policy_map: dict[str, list[str]], *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.run_id = run_id
        self.num_teams = num_teams
        self.policy_map = policy_map

    def on_episode_created(self, *, episode, env=None, env_index, **kwargs):
        assert env is not None
        assert episode.id_ not in self.policy_map
        policy_names = [f"p{i}" for i in range(self.num_teams)]
        players = random.sample(policy_names, 2)
        self.policy_map[episode.id_] = players
        teams = list(range(len(TEAMS[battle_format[-4:]])))
        random.Random(self.run_id).shuffle(teams)
        env.envs[env_index].unwrapped.get_sub_environments.agent1._team = RandomTeamBuilder(
            [teams[int(players[0][1:])]], battle_format, None
        )
        env.envs[env_index].unwrapped.get_sub_environments.agent2._team = RandomTeamBuilder(
            [teams[int(players[1][1:])]], battle_format, None
        )

    def on_episode_end(self, *, episode, **kwargs):
        self.policy_map.pop(episode.id_)
