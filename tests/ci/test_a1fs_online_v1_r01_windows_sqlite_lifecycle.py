from __future__ import annotations

import os
from pathlib import Path

from ulga.builders import build_a1fs_online_v1_r01_self_contained_product_root_update_channel as r01
from ulga.runners import materialize_a1fs_online_v1_r01 as r01_runner
from ulga.runners import run_a1fs_r01_with_windows_safe_sqlite as compatibility_runtime


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


def test_authoritative_builder_closes_sqlite_before_windows_atomic_replace(
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

    monkeypatch.setattr(r01.sqlite3, "connect", fake_connect)
    monkeypatch.setattr(r01.os, "replace", guarded_replace)

    r01._copy_sqlite(source, target)

    assert target.read_bytes() == b"sqlite-backup"
    assert not target.with_suffix(target.suffix + ".tmp").exists()


def test_compatibility_runtime_does_not_monkeypatch_builder() -> None:
    authoritative_copy = r01._copy_sqlite
    authoritative_module = r01.MODULE

    compatibility_runtime.activate_windows_safe_runtime()

    assert r01._copy_sqlite is authoritative_copy
    assert r01.MODULE == authoritative_module
    assert compatibility_runtime.MODULE == authoritative_module


def test_r01_authority_fingerprints_builder_not_compatibility_facade() -> None:
    manifest = r01_runner.load_r01_manifest()
    inputs = manifest["artifacts"]["R01_SAFE"]["repository_inputs"]
    assert "ulga/builders/build_a1fs_online_v1_r01_self_contained_product_root_update_channel.py" in inputs
    assert "ulga/runners/run_a1fs_r01_with_windows_safe_sqlite.py" not in inputs


def test_compatibility_runtime_declares_non_content_producer_governance() -> None:
    assert compatibility_runtime.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert compatibility_runtime.A1FS_CONTENT_POLICY_EXEMPTION
