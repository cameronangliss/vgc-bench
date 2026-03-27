"""Integration test for the logs2trajs -> pretrain -> train pipeline.

Loads pre-scraped Reg G Bo3 battle logs from a fixture file, converts them
to trajectories, runs a short behavior cloning pretrain, then runs RL
training initialized from a BC checkpoint downloaded from the model repo.
"""

import asyncio
import json
import pickle
import socket
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from threading import Thread

import numpy as np
import pytest
from imitation.algorithms.bc import BC
from imitation.data.types import DictObs, Trajectory
from imitation.util.logger import configure
from poke_env.environment import SingleAgentWrapper
from poke_env.player import RandomPlayer
from stable_baselines3 import PPO

from vgc_bench.logs2trajs import process_logs
from vgc_bench.pretrain import TrajectoryDataset
from vgc_bench.src.env import ShowdownEnv
from vgc_bench.src.policy import MaskedActorCriticPolicy
from vgc_bench.src.utils import LearningStyle, act_len, chunk_obs_len, format_map
from vgc_bench.train import train


def _server_available() -> bool:
    try:
        with socket.create_connection(("localhost", 8100), timeout=1):
            return True
    except OSError:
        return False


requires_server = pytest.mark.skipif(
    not _server_available(), reason="Pokemon Showdown server not running on port 8100"
)


@pytest.fixture(scope="module")
def trajectories():
    """Load fixture logs and convert to trajectories via process_logs."""
    fixture_path = Path(__file__).parent / "fixture_logs.json"
    with fixture_path.open() as f:
        logs = json.load(f)

    def _init_worker_loop():
        import vgc_bench.logs2trajs as mod

        mod._READER_LOOP = asyncio.new_event_loop()
        Thread(target=mod._READER_LOOP.run_forever, daemon=True).start()

    with ProcessPoolExecutor(max_workers=4, initializer=_init_worker_loop) as executor:
        trajs = process_logs(
            logs, executor, min_rating=None, only_winner=False, strict=False
        )
    assert len(trajs) > 0, "No trajectories produced from fixture logs"
    return trajs


@pytest.fixture(scope="module")
def trajs_on_disk(trajectories, tmp_path_factory):
    """Write trajectories to a temp directory as pickle files."""
    trajs_dir = tmp_path_factory.mktemp("trajs")
    for i, traj in enumerate(trajectories):
        with (trajs_dir / f"{i:08d}.pkl").open("wb") as f:
            pickle.dump(traj, f)
    return trajs_dir


class TestPipeline:
    """Test the full scrape -> logs2trajs -> pretrain pipeline."""

    def test_logs2trajs_produces_trajectories(self, trajectories):
        assert len(trajectories) > 0
        for traj in trajectories:
            assert isinstance(traj, Trajectory)
            assert traj.obs.shape[1] == 12 * chunk_obs_len
            assert traj.acts.shape[1] == 2
            assert traj.obs.shape[0] == traj.acts.shape[0] + 1

    def test_pretrain_on_trajectories(self, trajs_on_disk, monkeypatch):
        """Run a minimal BC training loop on the scraped trajectory data."""
        monkeypatch.chdir(trajs_on_disk.parent)
        # Rename directory to "trajs" so TrajectoryDataset finds it
        target = trajs_on_disk.parent / "trajs"
        if not target.exists():
            trajs_on_disk.rename(target)

        dataset = TrajectoryDataset()
        assert len(dataset) > 0

        # Verify DictObs wrapping works
        sample = dataset[0]
        assert isinstance(sample, Trajectory)
        assert isinstance(sample.obs, DictObs)
        assert "observation" in sample.obs._d
        assert "action_mask" in sample.obs._d
        assert sample.obs._d["action_mask"].shape[1] == 2 * act_len
        assert np.all(sample.obs._d["action_mask"] == 1)

        # Create a minimal PPO + BC setup and train 1 epoch
        env = ShowdownEnv(
            battle_format=format_map["g"],
            log_level=40,
            accept_open_team_sheet=True,
            start_listening=False,
            choose_on_teampreview=True,
        )
        opponent = RandomPlayer(start_listening=False)
        single_env = SingleAgentWrapper(env, opponent)
        ppo = PPO(
            MaskedActorCriticPolicy,
            single_env,
            policy_kwargs={"d_model": 64, "choose_on_teampreview": True},
            device="cpu",
        )
        bc = BC(
            observation_space=ppo.observation_space,
            action_space=ppo.action_space,
            rng=np.random.default_rng(42),
            policy=ppo.policy,
            batch_size=4,
            device="cpu",
            custom_logger=configure(str(trajs_on_disk.parent / "logs"), ["stdout"]),
        )
        demos = [dataset[i] for i in range(len(dataset))]
        bc.set_demonstrations(demos)
        bc.train(n_epochs=1)

    @requires_server
    def test_train_with_bc(self, tmp_path, monkeypatch):
        """Run RL training initialized from BC checkpoint downloaded from HuggingFace.

        Uses self-play with a tiny number of timesteps to verify the full
        train() pipeline works end-to-end, including BC model download.
        """
        monkeypatch.chdir(tmp_path)
        project_root = Path(__file__).resolve().parent.parent
        (tmp_path / "teams").symlink_to(project_root / "teams")
        (tmp_path / "data").symlink_to(project_root / "data")
        train(
            reg=None,
            run_id=1,
            num_teams=None,
            num_envs=1,
            num_eval_workers=1,
            log_level=40,
            port=8100,
            device="cpu",
            learning_style=LearningStyle.PURE_SELF_PLAY,
            behavior_clone=True,
            allow_mirror_match=True,
            choose_on_teampreview=True,
            team1=None,
            team2=None,
            results_suffix="test",
            total_steps=3072,
            evaluate=False,
        )
