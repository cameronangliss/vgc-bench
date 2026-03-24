"""Integration tests for vgc_bench.logs2trajs using a real battle log fixture.

These tests exercise the full log-replay pipeline: LogReader + poke-env battle
simulation + PolicyPlayer embedding, using a real scraped battle log and an
async event loop.
"""

import asyncio
import json
from pathlib import Path
from threading import Thread
from unittest.mock import patch

import numpy as np
import pytest
from poke_env.ps_client import AccountConfiguration

from vgc_bench.logs2trajs import LogReader, process_log
from vgc_bench.src.utils import act_len, chunk_obs_len

FIXTURE_PATH = Path(__file__).parent / "fixture_battle_log.json"


@pytest.fixture(scope="module")
def battle_log_fixture():
    """Load the real battle log fixture."""
    with FIXTURE_PATH.open() as f:
        logs = json.load(f)
    tag = next(iter(logs))
    _, log = logs[tag]
    return tag, log


@pytest.fixture(scope="module")
def reader_loop():
    """Create and start an event loop for LogReader (mimics _init_worker_loop)."""
    loop = asyncio.new_event_loop()
    thread = Thread(target=loop.run_forever, daemon=True)
    thread.start()
    yield loop
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=5)


def _run_process_log(tag, log, role, reader_loop, **kwargs):
    """Run process_log with the _READER_LOOP patched and battle_locks pre-seeded."""
    orig_follow = LogReader.follow_log

    async def patched_follow(self, tag, log):
        battle_tag = f"battle-{tag}"
        if battle_tag not in self.ps_client._battle_locks:
            self.ps_client._battle_locks[battle_tag] = asyncio.Lock()
        return await orig_follow(self, tag, log)

    with patch.object(LogReader, "follow_log", patched_follow):
        import vgc_bench.logs2trajs as mod

        mod._READER_LOOP = reader_loop
        try:
            return process_log(tag, log, role, **kwargs)
        finally:
            del mod._READER_LOOP


class TestProcessLog:
    def test_process_log_p1(self, battle_log_fixture, reader_loop):
        tag, log = battle_log_fixture
        traj = _run_process_log(
            tag, log, "p1", reader_loop, min_rating=None, only_winner=False
        )
        assert traj is not None
        assert traj.terminal is True
        obs_dim = 12 * chunk_obs_len
        assert traj.obs.shape[1] == obs_dim
        assert traj.acts.shape[1] == 2
        assert traj.obs.shape[0] == traj.acts.shape[0] + 1
        assert not np.any(np.isnan(traj.obs))
        assert np.all(traj.acts >= 0)
        assert np.all(traj.acts < act_len)

    def test_process_log_p2(self, battle_log_fixture, reader_loop):
        tag, log = battle_log_fixture
        traj = _run_process_log(
            tag, log, "p2", reader_loop, min_rating=None, only_winner=False
        )
        assert traj is not None
        assert traj.obs.ndim == 2
        assert traj.acts.ndim == 2

    def test_min_rating_filter(self, battle_log_fixture, reader_loop):
        tag, log = battle_log_fixture
        traj = _run_process_log(
            tag, log, "p1", reader_loop, min_rating=99999, only_winner=False
        )
        assert traj is None

    def test_winner_filter(self, battle_log_fixture, reader_loop):
        tag, log = battle_log_fixture
        win_start = log.index("|win|")
        win_end = log.index("\n", win_start)
        _, _, winner = log[win_start:win_end].split("|")
        for role in ["p1", "p2"]:
            start = log.index(f"|player|{role}|")
            end = log.index("\n", start)
            username = log[start:end].split("|")[3]
            if username != winner:
                loser_role = role
                break
        traj = _run_process_log(
            tag, log, loser_role, reader_loop, min_rating=None, only_winner=True
        )
        assert traj is None


class TestLogParsingHelpers:
    def test_rating_extraction_from_real_log(self, battle_log_fixture):
        _, log = battle_log_fixture
        from vgc_bench.scrape_logs import get_rating

        r1 = get_rating(log, "p1")
        r2 = get_rating(log, "p2")
        assert r1 is None or isinstance(r1, int)
        assert r2 is None or isinstance(r2, int)

    def test_winner_extraction(self, battle_log_fixture):
        _, log = battle_log_fixture
        win_start = log.index("|win|")
        win_end = log.index("\n", win_start)
        _, _, winner = log[win_start:win_end].split("|")
        assert len(winner) > 0
