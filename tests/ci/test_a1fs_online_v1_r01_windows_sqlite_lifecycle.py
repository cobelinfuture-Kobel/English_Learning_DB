from __future__ import annotations

import os
from pathlib import Path

from ulga.builders import build_a1fs_online_v1_r01_self_contained_product_root_update_channel as r01
from ulga.runners import materialize_a1fs_online_v1_r01 as r01_runner
from ulga.runners import run_a1fs_r01_with_windows_safe_sqlite as windows_runtime


class _FakeConnection:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.closed = False
        self.committed = False

    def backup(self, destination: "_FakeConnection") -> None:
        assert destination.path is not None
        destination.path.write_bytes(b"sqlite-backup")

    def commit(self) -> None:
        self.committed = True

    def close(self) -> None:
        self.closed = True


def test_sqlite_connections_close_before_windows_atomic_replace(
    tmp_path: Path, monkeypatch,
) -> None:
    source = tmp_path / "source.sqlite3"
    target = tmp_path / "shared" / "learner_runtime.sqlite3"
    source.write_bytes(b"source")
    connections: list[_FakeConnection] = []

    def fake_connect(value, *args, **kwargs):
        path = None if str(value).startswith("file:") else Path(value)
        connection = _FakeConnection(path)
        connections.append(connection)
        return connection

    real_replace = os.replace

    def guarded_replace(source_path, target_path) -> None:
        assert len(connections) == 2
        assert all(connection.closed for connection in connections)
        assert connections[1].committed is True
        real_replace(source_path, target_path)

    monkeypatch.setattr(windows_runtime.sqlite3, "connect", fake_connect)
    monkeypatch.setattr(windows_runtime.os, "replace", guarded_replace)

    windows_runtime.copy_sqlite_closed(source, target)

    assert target.read_bytes() == b"sqlite-backup"
    assert not target.with_suffix(target.suffix + ".tmp").exists()


def test_windows_runtime_becomes_packaged_v1_entrypoint() -> None:
    original_copy = r01._copy_sqlite
    original_module = r01.MODULE
    try:
        windows_runtime.activate_windows_safe_runtime()
        assert r01._copy_sqlite is windows_runtime.copy_sqlite_closed
        assert r01.MODULE == windows_runtime.MODULE
    finally:
        r01._copy_sqlite = original_copy
        r01.MODULE = original_module


def test_r01_authority_fingerprints_windows_runtime() -> None:
    manifest = r01_runner.load_r01_manifest()
    inputs = manifest["artifacts"]["R01_SAFE"]["repository_inputs"]
    assert "ulga/runners/run_a1fs_r01_with_windows_safe_sqlite.py" in inputs


def test_windows_runtime_declares_non_content_producer_governance() -> None:
    assert windows_runtime.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert windows_runtime.A1FS_CONTENT_POLICY_EXEMPTION
