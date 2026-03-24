"""Integration test for the full scrape -> logs2trajs -> pretrain -> train pipeline.

Scrapes a small batch of Reg D battle logs, converts them to trajectories,
runs a short behavior cloning pretrain, then runs RL training initialized
from a BC checkpoint downloaded from the model repo.
"""

import asyncio
import pickle
import socket
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

from vgc_bench.logs2trajs import process_log
from vgc_bench.pretrain import TrajectoryDataset
from vgc_bench.scrape_logs import (
    can_distinguish_team_members,
    get_log_json,
    update_battle_idents,
)
from vgc_bench.src.env import ShowdownEnv
from vgc_bench.src.policy import MaskedActorCriticPolicy
from vgc_bench.src.utils import LearningStyle, act_len, chunk_obs_len, format_map
from vgc_bench.train import train

BATTLE_FORMAT = "gen9vgc2023regd"


def _server_available() -> bool:
    try:
        with socket.create_connection(("localhost", 8100), timeout=1):
            return True
    except OSError:
        return False


requires_server = pytest.mark.skipif(
    not _server_available(), reason="Pokemon Showdown server not running on port 8100"
)


def _scrape_valid_logs(n: int) -> dict[str, tuple[str, str]]:
    """Scrape up to *n* valid Reg D logs from the Showdown replay API.

    Returns:
        Dict mapping battle tag to (uploadtime, log) tuples.
    """
    battle_idents: set[str] = set()
    oldest = 2_000_000_000
    # Fetch pages until we have enough candidates
    while len(battle_idents) < n * 5:
        prev_len = len(battle_idents)
        battle_idents, oldest = update_battle_idents(
            battle_idents, BATTLE_FORMAT, oldest
        )
        if len(battle_idents) == prev_len:
            break

    valid_logs: dict[str, tuple[str, str]] = {}
    for ident in battle_idents:
        if len(valid_logs) >= n:
            break
        lj = get_log_json(ident)
        if lj is None:
            continue
        log = lj["log"]
        if (
            log.count("|poke|p1|") == 6
            and log.count("|poke|p2|") == 6
            and "|turn|1" in log
            and "|showteam|" in log.split("\n|\n")[0]
            and can_distinguish_team_members(log.split("\n|\n")[0], "p1")
            and can_distinguish_team_members(log.split("\n|\n")[0], "p2")
            and "Zoroark" not in log
            and "Zorua" not in log
            and "|-mega|" not in log
        ):
            valid_logs[lj["id"]] = (str(lj["uploadtime"]), log)
    return valid_logs


@pytest.fixture(scope="module")
def scraped_logs():
    """Scrape a small batch of valid Reg D logs."""
    logs = _scrape_valid_logs(5)
    if not logs:
        pytest.skip("Could not scrape any valid Reg D logs")
    return logs


@pytest.fixture(scope="module")
def reader_loop():
    """Event loop for LogReader."""
    loop = asyncio.new_event_loop()
    thread = Thread(target=loop.run_forever, daemon=True)
    thread.start()
    yield loop
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=5)


@pytest.fixture(scope="module")
def trajectories(scraped_logs, reader_loop):
    """Convert scraped logs to trajectories via process_log."""
    from unittest.mock import patch

    from vgc_bench.logs2trajs import LogReader

    orig_follow = LogReader.follow_log

    async def patched_follow(self, tag, log):
        battle_tag = f"battle-{tag}"
        if battle_tag not in self.ps_client._battle_locks:
            self.ps_client._battle_locks[battle_tag] = asyncio.Lock()
        return await orig_follow(self, tag, log)

    trajs = []
    with patch.object(LogReader, "follow_log", patched_follow):
        import vgc_bench.logs2trajs as mod

        mod._READER_LOOP = reader_loop
        try:
            for tag, (_, log) in scraped_logs.items():
                for role in ["p1", "p2"]:
                    try:
                        traj = process_log(
                            tag, log, role, min_rating=None, only_winner=False
                        )
                        if traj is not None:
                            trajs.append(traj)
                    except Exception:
                        pass
        finally:
            del mod._READER_LOOP
    assert len(trajs) > 0, "No trajectories produced from scraped logs"
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

    def test_scrape_produces_logs(self, scraped_logs):
        assert len(scraped_logs) > 0
        for tag, (uploadtime, log) in scraped_logs.items():
            assert tag.startswith(BATTLE_FORMAT)
            assert "|win|" in log

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
            batch_size=32,
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
        train(
            reg="g",
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
            total_timesteps=3072,
        )
        save_dir = tmp_path / "results-test" / "saves-bc-sp" / "regg" / "seed1"
        assert save_dir.exists()
        saves = list(save_dir.glob("*.zip"))
        assert len(saves) > 0
