from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_online_v1_s07_multiunit_runtime_expansion as s07
from ulga.runners import materialize_a1fs_online_v1 as authority_runner
from ulga.runners import run_a1fs_s07_with_explicit_sqlite_close as closing_entrypoint


def test_context_managed_sqlite_connection_releases_handle(tmp_path: Path) -> None:
    database = tmp_path / "handle-release.sqlite3"

    with closing_entrypoint.explicit_sqlite_context_close():
        with sqlite3.connect(database) as connection:
            connection.execute("CREATE TABLE proof(value TEXT NOT NULL)")
            connection.execute("INSERT INTO proof VALUES('PASS')")

        assert isinstance(connection, closing_entrypoint.ClosingConnection)
        assert connection.context_exit_closed is True
        with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
            connection.execute("SELECT 1")

    replacement = tmp_path / "replacement.sqlite3"
    with sqlite3.connect(replacement) as candidate:
        candidate.execute("CREATE TABLE replacement(value TEXT NOT NULL)")
        candidate.execute("INSERT INTO replacement VALUES('REPLACED')")

    replacement.replace(database)
    with sqlite3.connect(database) as verification:
        assert verification.execute("SELECT value FROM replacement").fetchone()[0] == "REPLACED"


def test_entrypoint_restores_global_connect_after_s07_main(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_connect = sqlite3.connect
    database = tmp_path / "entrypoint.sqlite3"

    def fake_main(argv: list[str] | None = None) -> int:
        assert argv == ["materialize"]
        with sqlite3.connect(database) as connection:
            connection.execute("CREATE TABLE proof(value INTEGER NOT NULL)")
        assert isinstance(connection, closing_entrypoint.ClosingConnection)
        assert connection.context_exit_closed is True
        return 0

    monkeypatch.setattr(s07, "main", fake_main)
    assert closing_entrypoint.main(["materialize"]) == 0
    assert sqlite3.connect is original_connect


def test_authority_routes_only_exact_s07_builder_module() -> None:
    source = [
        "python",
        "-m",
        authority_runner.S07_BUILDER_MODULE,
        "materialize",
        "--output",
        "artifact.json",
    ]
    effective = authority_runner._effective_command(source)

    assert source[2] == authority_runner.S07_BUILDER_MODULE
    assert effective[2] == authority_runner.S07_CLOSING_ENTRYPOINT_MODULE
    assert effective[3:] == source[3:]

    other = ["python", "-m", "ulga.builders.some_other_builder", "--output", "artifact.json"]
    assert authority_runner._effective_command(other) == other


def test_s07_runtime_route_is_part_of_artifact_fingerprint_inputs() -> None:
    manifest = {
        "artifacts": {
            authority_runner.S07_ARTIFACT_ID: {
                "repository_inputs": [
                    "ulga/builders/build_a1fs_online_v1_s07_multiunit_runtime_expansion.py"
                ]
            }
        }
    }

    authority_runner._prepare_runtime_fingerprint_inputs(manifest)
    repository_inputs = manifest["artifacts"][authority_runner.S07_ARTIFACT_ID]["repository_inputs"]

    for path in authority_runner.S07_RUNTIME_FINGERPRINT_INPUTS:
        assert path in repository_inputs

    authority_runner._prepare_runtime_fingerprint_inputs(manifest)
    assert len(repository_inputs) == len(set(repository_inputs))
