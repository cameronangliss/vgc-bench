"""Tests for vgc_bench.pretrain (offline-only, no Showdown server)."""

import os
import pickle

from vgc_bench.pretrain import TrajectoryDataset


class TestTrajectoryDataset:
    def test_loads_files(self, trajs_dir, monkeypatch):
        monkeypatch.chdir(trajs_dir.parent)
        ds = TrajectoryDataset()
        assert len(ds) == 1

    def test_getitem_returns_trajectory(self, trajs_dir, monkeypatch):
        monkeypatch.chdir(trajs_dir.parent)
        ds = TrajectoryDataset()
        traj = ds[0]
        assert hasattr(traj, "obs")
        assert hasattr(traj, "acts")
        assert traj.terminal is True

    def test_empty_directory(self, tmp_path, monkeypatch):
        (tmp_path / "trajs").mkdir()
        monkeypatch.chdir(tmp_path)
        ds = TrajectoryDataset()
        assert len(ds) == 0
