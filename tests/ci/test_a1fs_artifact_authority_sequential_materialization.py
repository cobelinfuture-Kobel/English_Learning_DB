from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from ulga.artifacts.a1fs_artifact_authority import SCHEMA_VERSION
from ulga.runners.materialize_a1fs_online_v1 import materialize_sequentially


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_missing_upstream_is_built_before_downstream_fingerprint(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    root = tmp_path / "authority"
    repo.mkdir()
    root.mkdir()
    _write(repo / "repo.json", {"status": "PASS"})
    (repo / "producer_a.py").write_text("# producer a\n", encoding="utf-8")
    (repo / "producer_b.py").write_text("# producer b\n", encoding="utf-8")

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifacts": {
            "REPO": {
                "authority": "repository",
                "path": "repo.json",
                "dependencies": [],
                "expected": {"status": "PASS"},
            },
            "A": {
                "authority": "shared",
                "path": "a/a.json",
                "dependencies": ["REPO"],
                "repository_inputs": ["producer_a.py"],
                "command": ["builder_a", "{artifact:A}"],
                "expected": {"status": "PASS_A"},
            },
            "B": {
                "authority": "shared",
                "path": "b/b.private.json",
                "report_path": "b/b.safe.json",
                "dependencies": ["A"],
                "repository_inputs": ["producer_b.py"],
                "command": ["builder_b", "{artifact:B}", "{report:B}"],
                "expected": {"status": "PASS_B"},
            },
        },
    }

    calls: list[str] = []

    def command_runner(argv: Sequence[str], cwd: Path) -> int:
        assert cwd == repo
        calls.append(argv[0])
        if argv[0] == "builder_a":
            _write(Path(argv[1]), {"status": "PASS_A"})
            return 0
        if argv[0] == "builder_b":
            _write(Path(argv[1]), {"private": True})
            _write(Path(argv[2]), {"status": "PASS_B"})
            return 0
        raise AssertionError(f"unexpected command: {argv}")

    report = materialize_sequentially(
        manifest,
        "B",
        repo,
        root,
        command_runner=command_runner,
    )

    assert calls == ["builder_a", "builder_b"]
    assert report["validation_status"] == "PASS_A1FS_SHARED_ARTIFACT_AUTHORITY_MATERIALIZED"
    assert report["stop_reason"] == "NONE"
    assert [(row["artifact_id"], row["action"]) for row in report["actions"]] == [
        ("REPO", "REUSED"),
        ("A", "BUILD"),
        ("B", "BUILD"),
    ]


def test_second_run_reuses_materialized_chain(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    root = tmp_path / "authority"
    repo.mkdir()
    root.mkdir()
    _write(repo / "repo.json", {"status": "PASS"})
    (repo / "producer_a.py").write_text("# producer a\n", encoding="utf-8")

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifacts": {
            "REPO": {
                "authority": "repository",
                "path": "repo.json",
                "dependencies": [],
                "expected": {"status": "PASS"},
            },
            "A": {
                "authority": "shared",
                "path": "a/a.json",
                "dependencies": ["REPO"],
                "repository_inputs": ["producer_a.py"],
                "command": ["builder_a", "{artifact:A}"],
                "expected": {"status": "PASS_A"},
            },
        },
    }

    calls = 0

    def command_runner(argv: Sequence[str], cwd: Path) -> int:
        nonlocal calls
        calls += 1
        _write(Path(argv[1]), {"status": "PASS_A"})
        return 0

    first = materialize_sequentially(manifest, "A", repo, root, command_runner=command_runner)
    second = materialize_sequentially(manifest, "A", repo, root, command_runner=command_runner)

    assert first["actions"][-1]["action"] == "BUILD"
    assert second["actions"][-1]["action"] == "REUSED"
    assert calls == 1
