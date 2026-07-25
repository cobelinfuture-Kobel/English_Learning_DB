from __future__ import annotations

import json
from pathlib import Path

import pytest

from ulga.artifacts.a1fs_artifact_authority import (
    ArtifactAuthorityError,
    SCHEMA_VERSION,
    _write_state,
    paths,
    _fingerprint,
    plan,
    dependency_order,
    preflight,
    recover_external,
    resolve_artifact_root,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _manifest() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifacts": {
            "REPO": {
                "authority": "repository",
                "path": "repo.json",
                "dependencies": [],
                "expected": {"status": "PASS"},
            },
            "EXTERNAL": {
                "authority": "shared_external",
                "path": "external/external.safe.json",
                "recovery_filename": "external.safe.json",
                "dependencies": [],
                "expected": {"status": "PASS", "errors": []},
            },
            "A": {
                "authority": "shared",
                "path": "generated/a.json",
                "dependencies": ["REPO", "EXTERNAL"],
                "repository_inputs": ["producer_a.py"],
                "command": ["{python}", "producer_a.py", "{artifact:A}"],
                "expected": {"status": "PASS"},
            },
            "B": {
                "authority": "shared",
                "path": "generated/b.private.json",
                "report_path": "generated/b.safe.json",
                "dependencies": ["A"],
                "repository_inputs": ["producer_b.py"],
                "command": ["{python}", "producer_b.py", "{artifact:A}", "{artifact:B}", "{report:B}"],
                "expected": {"status": "PASS"},
            },
        },
    }


def _seed_repo_and_external(tmp_path: Path, manifest: dict) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    root = tmp_path / "authority"
    repo.mkdir()
    root.mkdir()
    _write(repo / "repo.json", {"status": "PASS"})
    (repo / "producer_a.py").write_text("# a\n", encoding="utf-8")
    (repo / "producer_b.py").write_text("# b\n", encoding="utf-8")
    _write(root / "external/external.safe.json", {"status": "PASS", "errors": []})
    return repo, root


def test_artifact_root_must_be_external(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(ArtifactAuthorityError) as exc:
        resolve_artifact_root(repo, repo / ".local")
    assert exc.value.code == "ARTIFACT_ROOT_MUST_BE_OUTSIDE_REPOSITORY"


def test_dependency_order_is_deterministic_and_directed() -> None:
    assert dependency_order(_manifest(), "B") == ["REPO", "EXTERNAL", "A", "B"]


def test_external_recovery_accepts_same_hash_candidates(tmp_path: Path) -> None:
    manifest = _manifest()
    repo, root = _seed_repo_and_external(tmp_path, manifest)
    target = root / "external/external.safe.json"
    target.unlink()
    payload = {"status": "PASS", "errors": []}
    _write(tmp_path / "recovery1/external.safe.json", payload)
    _write(tmp_path / "recovery2/external.safe.json", payload)
    selected = recover_external(
        manifest, "EXTERNAL", repo, root, [tmp_path / "recovery1", tmp_path / "recovery2"]
    )
    assert selected.name == "external.safe.json"
    assert json.loads(target.read_text(encoding="utf-8")) == payload


def test_external_recovery_rejects_divergent_valid_candidates(tmp_path: Path) -> None:
    manifest = _manifest()
    repo, root = _seed_repo_and_external(tmp_path, manifest)
    (root / "external/external.safe.json").unlink()
    _write(tmp_path / "recovery1/external.safe.json", {"status": "PASS", "errors": [], "v": 1})
    _write(tmp_path / "recovery2/external.safe.json", {"status": "PASS", "errors": [], "v": 2})
    with pytest.raises(ArtifactAuthorityError) as exc:
        recover_external(
            manifest, "EXTERNAL", repo, root, [tmp_path / "recovery1", tmp_path / "recovery2"]
        )
    assert exc.value.code == "EXTERNAL_ARTIFACT_RECOVERY_AMBIGUOUS"
    assert len(exc.value.details["candidates"]) == 2


def test_preflight_returns_one_aggregate_blocker(tmp_path: Path) -> None:
    manifest = _manifest()
    repo, root = _seed_repo_and_external(tmp_path, manifest)
    (repo / "repo.json").unlink()
    (root / "external/external.safe.json").unlink()
    with pytest.raises(ArtifactAuthorityError) as exc:
        preflight(manifest, dependency_order(manifest, "B"), repo, root)
    assert exc.value.code == "ARTIFACT_PREFLIGHT_FAILED"
    assert len(exc.value.details["failures"]) == 2


def test_matching_fingerprints_reuse_without_rebuild(tmp_path: Path) -> None:
    manifest = _manifest()
    repo, root = _seed_repo_and_external(tmp_path, manifest)
    _write(root / "generated/a.json", {"status": "PASS"})
    _write(root / "generated/b.private.json", {"private": True})
    _write(root / "generated/b.safe.json", {"status": "PASS"})
    for artifact_id in ("A", "B"):
        resolved = paths(manifest, artifact_id, repo, root)
        fingerprint = _fingerprint(manifest, artifact_id, repo, root)
        _write_state(resolved, artifact_id, fingerprint)
    rows = plan(manifest, dependency_order(manifest, "B"), repo, root)
    assert [(row[0], row[1]) for row in rows] == [
        ("REPO", "REUSED"),
        ("EXTERNAL", "REUSED"),
        ("A", "REUSED"),
        ("B", "REUSED"),
    ]


def test_stale_dependency_rebuilds_only_downstream_chain(tmp_path: Path) -> None:
    manifest = _manifest()
    repo, root = _seed_repo_and_external(tmp_path, manifest)
    _write(root / "generated/a.json", {"status": "PASS"})
    _write(root / "generated/b.private.json", {"private": True})
    _write(root / "generated/b.safe.json", {"status": "PASS"})
    for artifact_id in ("A", "B"):
        resolved = paths(manifest, artifact_id, repo, root)
        _write_state(resolved, artifact_id, _fingerprint(manifest, artifact_id, repo, root))
    (repo / "producer_a.py").write_text("# changed\n", encoding="utf-8")
    rows = plan(manifest, dependency_order(manifest, "B"), repo, root)
    actions = {row[0]: (row[1], row[2]) for row in rows}
    assert actions["A"] == ("BUILD", "missing_or_stale")
    assert actions["B"] == ("BUILD", "dependency_rebuilt")
