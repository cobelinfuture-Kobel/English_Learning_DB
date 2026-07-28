from __future__ import annotations

import sqlite3
from pathlib import Path

from ulga.builders import build_a1fs_online_v1_r01_self_contained_product_root_update_channel as r01
from ulga.runners import materialize_a1fs_online_v1_r01 as r01_runner
from ulga.runners import run_a1fs_r01_with_windows_safe_sqlite as compatibility_runtime


def _write_sqlite(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.execute("CREATE TABLE payload(value TEXT NOT NULL)")
        connection.execute("INSERT INTO payload(value) VALUES(?)", (value,))
        connection.commit()
    finally:
        connection.close()


def _read_sqlite(path: Path) -> str:
    connection = sqlite3.connect(path)
    try:
        return str(connection.execute("SELECT value FROM payload").fetchone()[0])
    finally:
        connection.close()


def test_authoritative_builder_uses_sqlite_backup_without_windows_atomic_replace(
    tmp_path: Path, monkeypatch,
) -> None:
    source = tmp_path / "source.sqlite3"
    target = tmp_path / "shared" / "database" / "learner_runtime.sqlite3"
    _write_sqlite(source, "copied")

    def forbidden_replace(*_args, **_kwargs) -> None:
        raise AssertionError("sqlite copy must not rely on os.replace")

    monkeypatch.setattr(r01.os, "replace", forbidden_replace)

    r01._copy_sqlite(source, target)

    assert _read_sqlite(target) == "copied"
    assert not target.with_suffix(target.suffix + ".tmp").exists()


def test_authoritative_builder_overwrites_existing_sqlite_with_reader_open(
    tmp_path: Path, monkeypatch,
) -> None:
    source = tmp_path / "source.sqlite3"
    target = tmp_path / "shared" / "database" / "learner_runtime.sqlite3"
    _write_sqlite(source, "new-value")
    _write_sqlite(target, "old-value")
    reader = sqlite3.connect(target)

    def forbidden_replace(*_args, **_kwargs) -> None:
        raise AssertionError("sqlite copy must not rely on os.replace")

    monkeypatch.setattr(r01.os, "replace", forbidden_replace)
    try:
        assert reader.execute("SELECT value FROM payload").fetchone()[0] == "old-value"
        r01._copy_sqlite(source, target)
    finally:
        reader.close()

    assert _read_sqlite(target) == "new-value"


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
