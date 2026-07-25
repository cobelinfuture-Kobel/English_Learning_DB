#!/usr/bin/env python3
"""Shared, worktree-independent artifact authority for A1FS Online V1."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Coordinates artifact paths, hashes, and existing builders; no learner content is authored."
)
TASK_ID = "A1FS-ARTIFACT-AUTHORITY-V1-S00_SharedArtifactRootManifestAndChainRunner"
SCHEMA_VERSION = "a1fs.artifact.authority.v1"
PASS_STATUS = "PASS_A1FS_SHARED_ARTIFACT_AUTHORITY_MATERIALIZED"
FAIL_STATUS = "FAIL_CLOSED_A1FS_SHARED_ARTIFACT_AUTHORITY"
ROOT_ENV = "ENGLISH_DB_ARTIFACT_ROOT"
DEFAULT_MANIFEST = Path(__file__).resolve().parent / "manifests/a1fs_online_v1_s02_artifact_manifest.json"


class ArtifactAuthorityError(RuntimeError):
    def __init__(self, code: str, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.details = dict(details or {})


def _json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactAuthorityError(code, {"path": str(path), "error": str(exc)}) from exc
    if not isinstance(value, dict):
        raise ArtifactAuthorityError(code, {"path": str(path), "reason": "not_object"})
    return value


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe(base: Path, relative: str, code: str) -> Path:
    path = (base / relative).resolve()
    try:
        path.relative_to(base.resolve())
    except ValueError as exc:
        raise ArtifactAuthorityError(code, {"relative_path": relative}) from exc
    return path


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    manifest = _json(path, "MANIFEST_UNREADABLE")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ArtifactAuthorityError("MANIFEST_SCHEMA_VERSION_MISMATCH")
    if not isinstance(manifest.get("artifacts"), dict) or not manifest["artifacts"]:
        raise ArtifactAuthorityError("MANIFEST_ARTIFACTS_INVALID")
    return manifest


def resolve_artifact_root(repo_root: Path, explicit: Path | None = None, env=None) -> Path:
    source = os.environ if env is None else env
    raw = str(explicit or source.get(ROOT_ENV, "")).strip()
    if not raw:
        raise ArtifactAuthorityError("ARTIFACT_ROOT_NOT_CONFIGURED", {"required_env": ROOT_ENV})
    root, repo = Path(raw).expanduser().resolve(), repo_root.resolve()
    try:
        root.relative_to(repo)
    except ValueError:
        pass
    else:
        raise ArtifactAuthorityError(
            "ARTIFACT_ROOT_MUST_BE_OUTSIDE_REPOSITORY",
            {"artifact_root": str(root), "repo_root": str(repo)},
        )
    root.mkdir(parents=True, exist_ok=True)
    return root


def _entry(manifest: Mapping[str, Any], artifact_id: str) -> Mapping[str, Any]:
    entry = manifest.get("artifacts", {}).get(artifact_id)
    if not isinstance(entry, Mapping):
        raise ArtifactAuthorityError("UNKNOWN_ARTIFACT_ID", {"artifact_id": artifact_id})
    return entry


def paths(manifest, artifact_id: str, repo_root: Path, artifact_root: Path) -> dict[str, Path | None]:
    entry, authority = _entry(manifest, artifact_id), _entry(manifest, artifact_id).get("authority")
    if authority == "repository":
        return {"primary": _safe(repo_root, entry["path"], "REPOSITORY_PATH_ESCAPE"), "report": None, "state": None}
    if authority not in {"shared", "shared_external"}:
        raise ArtifactAuthorityError("ARTIFACT_AUTHORITY_INVALID", {"artifact_id": artifact_id})
    report = entry.get("report_path")
    return {
        "primary": _safe(artifact_root, entry["path"], "ARTIFACT_PATH_ESCAPE"),
        "report": _safe(artifact_root, report, "ARTIFACT_REPORT_PATH_ESCAPE") if report else None,
        "state": _safe(artifact_root, f".authority/state/{artifact_id}.json", "ARTIFACT_STATE_PATH_ESCAPE"),
    }


def _matches(value: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    for dotted, wanted in expected.items():
        current: Any = value
        for part in dotted.split("."):
            if not isinstance(current, Mapping) or part not in current:
                return False
            current = current[part]
        if current != wanted:
            return False
    return True


def validate(manifest, artifact_id: str, repo_root: Path, artifact_root: Path, override: Path | None = None):
    entry = _entry(manifest, artifact_id)
    resolved = paths(manifest, artifact_id, repo_root, artifact_root)
    primary = override or resolved["primary"]
    report = None if override else resolved["report"]
    target = report or primary
    if not primary.is_file() or not target.is_file():
        raise ArtifactAuthorityError("ARTIFACT_MISSING", {"artifact_id": artifact_id, "path": str(target)})
    value = _json(target, "ARTIFACT_UNREADABLE")
    if not _matches(value, entry.get("expected", {})):
        raise ArtifactAuthorityError("ARTIFACT_CONTRACT_MISMATCH", {"artifact_id": artifact_id, "path": str(target)})
    return value


def dependency_order(manifest, through: str) -> list[str]:
    result, visiting, done = [], set(), set()

    def visit(artifact_id: str) -> None:
        if artifact_id in done:
            return
        if artifact_id in visiting:
            raise ArtifactAuthorityError("MANIFEST_DEPENDENCY_CYCLE", {"artifact_id": artifact_id})
        visiting.add(artifact_id)
        for dependency in _entry(manifest, artifact_id).get("dependencies", []):
            visit(str(dependency))
        visiting.remove(artifact_id)
        done.add(artifact_id)
        result.append(artifact_id)

    visit(through)
    return result


def _fingerprint(manifest, artifact_id: str, repo_root: Path, artifact_root: Path) -> str:
    entry = _entry(manifest, artifact_id)
    dependency_hashes = {}
    for dependency in entry.get("dependencies", []):
        validate(manifest, dependency, repo_root, artifact_root)
        dep = paths(manifest, dependency, repo_root, artifact_root)
        dependency_hashes[dependency] = _hash(dep["report"] or dep["primary"])
    source_hashes = {}
    for relative in entry.get("repository_inputs", []):
        source = _safe(repo_root, relative, "REPOSITORY_INPUT_PATH_ESCAPE")
        if not source.is_file():
            raise ArtifactAuthorityError("REPOSITORY_INPUT_MISSING", {"path": str(source)})
        source_hashes[relative] = _hash(source)
    payload = json.dumps(
        {"artifact_id": artifact_id, "command": entry.get("command"), "dependencies": dependency_hashes,
         "repository_inputs": source_hashes, "schema_version": SCHEMA_VERSION},
        sort_keys=True, separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _state_matches(state: Path | None, fingerprint: str) -> bool:
    if not state or not state.is_file():
        return False
    try:
        return _json(state, "STATE_UNREADABLE").get("fingerprint") == fingerprint
    except ArtifactAuthorityError:
        return False


def _write_state(resolved, artifact_id: str, fingerprint: str) -> None:
    state = resolved["state"]
    if not state:
        return
    state.parent.mkdir(parents=True, exist_ok=True)
    target = resolved["report"] or resolved["primary"]
    state.write_text(json.dumps({
        "schema_version": SCHEMA_VERSION,
        "artifact_id": artifact_id,
        "fingerprint": fingerprint,
        "primary_sha256": _hash(resolved["primary"]),
        "validation_sha256": _hash(target),
    }, indent=2) + "\n", encoding="utf-8")


def recover_external(manifest, artifact_id: str, repo_root: Path, artifact_root: Path,
                     search_roots: Iterable[Path]) -> Path:
    entry = _entry(manifest, artifact_id)
    if entry.get("authority") != "shared_external":
        raise ArtifactAuthorityError("RECOVERY_NOT_ALLOWED_FOR_ARTIFACT")
    target = paths(manifest, artifact_id, repo_root, artifact_root)["primary"]
    filename = entry.get("recovery_filename") or Path(entry["path"]).name
    candidates = []
    for root in map(Path, search_roots):
        if not root.exists():
            continue
        for candidate in root.rglob(filename):
            candidate = candidate.resolve()
            if candidate == target or not candidate.is_file():
                continue
            try:
                validate(manifest, artifact_id, repo_root, artifact_root, candidate)
            except ArtifactAuthorityError:
                continue
            candidates.append((candidate, _hash(candidate), candidate.stat().st_mtime))
    unique = {(str(path), digest): (path, digest, modified) for path, digest, modified in candidates}
    candidates = list(unique.values())
    if not candidates:
        raise ArtifactAuthorityError("EXTERNAL_ARTIFACT_RECOVERY_CANDIDATE_NOT_FOUND", {"artifact_id": artifact_id})
    if len({digest for _, digest, _ in candidates}) != 1:
        raise ArtifactAuthorityError("EXTERNAL_ARTIFACT_RECOVERY_AMBIGUOUS", {
            "artifact_id": artifact_id, "candidates": [str(row[0]) for row in sorted(candidates)]})
    selected = max(candidates, key=lambda row: (row[2], str(row[0])))[0]
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(selected, target)
    validate(manifest, artifact_id, repo_root, artifact_root)
    return selected


def preflight(manifest, order: Sequence[str], repo_root: Path, artifact_root: Path,
              recovery_roots: Iterable[Path] = ()) -> list[dict[str, str]]:
    failures, recovered = [], []
    for artifact_id in order:
        authority = _entry(manifest, artifact_id).get("authority")
        if authority not in {"repository", "shared_external"}:
            continue
        try:
            validate(manifest, artifact_id, repo_root, artifact_root)
        except ArtifactAuthorityError as exc:
            if authority == "shared_external" and recovery_roots:
                try:
                    source = recover_external(manifest, artifact_id, repo_root, artifact_root, recovery_roots)
                    recovered.append({"artifact_id": artifact_id, "source": str(source)})
                    continue
                except ArtifactAuthorityError as recovery_exc:
                    exc = recovery_exc
            failures.append({"artifact_id": artifact_id, "code": exc.code, **exc.details})
    if failures:
        raise ArtifactAuthorityError("ARTIFACT_PREFLIGHT_FAILED", {"failures": failures})
    return recovered


def plan(manifest, order: Sequence[str], repo_root: Path, artifact_root: Path, force=False):
    actions, rebuilt = [], set()
    for artifact_id in order:
        entry, authority = _entry(manifest, artifact_id), _entry(manifest, artifact_id).get("authority")
        if authority in {"repository", "shared_external"}:
            validate(manifest, artifact_id, repo_root, artifact_root)
            actions.append((artifact_id, "REUSED", "authoritative_input", None))
            continue
        fingerprint = _fingerprint(manifest, artifact_id, repo_root, artifact_root)
        dependency_rebuilt = any(dep in rebuilt for dep in entry.get("dependencies", []))
        resolved = paths(manifest, artifact_id, repo_root, artifact_root)
        reusable = False
        if not force and not dependency_rebuilt:
            try:
                validate(manifest, artifact_id, repo_root, artifact_root)
                reusable = _state_matches(resolved["state"], fingerprint)
            except ArtifactAuthorityError:
                pass
        if reusable:
            actions.append((artifact_id, "REUSED", "fingerprint_match", fingerprint))
        else:
            reason = "forced" if force else ("dependency_rebuilt" if dependency_rebuilt else "missing_or_stale")
            actions.append((artifact_id, "BUILD", reason, fingerprint))
            rebuilt.add(artifact_id)
    return actions


def _command(manifest, artifact_id: str, repo_root: Path, artifact_root: Path) -> list[str]:
    command = _entry(manifest, artifact_id).get("command")
    if not isinstance(command, list) or not command:
        raise ArtifactAuthorityError("ARTIFACT_PRODUCER_COMMAND_MISSING", {"artifact_id": artifact_id})
    rendered = []
    for token in map(str, command):
        token = token.replace("{python}", sys.executable)
        for candidate in manifest["artifacts"]:
            resolved = paths(manifest, candidate, repo_root, artifact_root)
            token = token.replace(f"{{artifact:{candidate}}}", str(resolved["primary"]))
            token = token.replace(f"{{report:{candidate}}}", str(resolved["report"] or resolved["primary"]))
        rendered.append(token)
    return rendered


def _run(argv: Sequence[str], cwd: Path) -> int:
    return subprocess.run(list(argv), cwd=cwd, check=False).returncode


def materialize(manifest, through: str, repo_root: Path, artifact_root: Path, *,
                recovery_roots: Iterable[Path] = (), force=False,
                runner: Callable[[Sequence[str], Path], int] = _run) -> dict[str, Any]:
    order = dependency_order(manifest, through)
    recovered = preflight(manifest, order, repo_root, artifact_root, recovery_roots)
    results = []
    for artifact_id, action, reason, fingerprint in plan(manifest, order, repo_root, artifact_root, force):
        resolved = paths(manifest, artifact_id, repo_root, artifact_root)
        if action == "BUILD":
            resolved["primary"].parent.mkdir(parents=True, exist_ok=True)
            if resolved["report"]:
                resolved["report"].parent.mkdir(parents=True, exist_ok=True)
            argv = _command(manifest, artifact_id, repo_root, artifact_root)
            code = runner(argv, repo_root)
            if code:
                raise ArtifactAuthorityError("ARTIFACT_BUILD_FAILED", {
                    "artifact_id": artifact_id, "exit_code": code, "command": argv})
            validate(manifest, artifact_id, repo_root, artifact_root)
            _write_state(resolved, artifact_id, fingerprint)
        results.append({"artifact_id": artifact_id, "action": action, "reason": reason,
                        "path": str(resolved["primary"])})
    final = paths(manifest, through, repo_root, artifact_root)
    summary = validate(manifest, through, repo_root, artifact_root)
    target = final["report"] or final["primary"]
    return {"task_id": TASK_ID, "schema_version": SCHEMA_VERSION, "validation_status": PASS_STATUS,
            "artifact_root": str(artifact_root), "through": through, "dependency_order": order,
            "recovered_external_artifacts": recovered, "actions": results,
            "final_artifact_path": str(target), "final_artifact_sha256": _hash(target),
            "final_artifact_summary": summary, "stop_reason": "NONE",
            "next_short_step": "A1FS-ONLINE-V1-S03_UnifiedLearnerRuntimeIntegration_NoAudio"}


def failure_report(exc: ArtifactAuthorityError) -> dict[str, Any]:
    return {"task_id": TASK_ID, "schema_version": SCHEMA_VERSION, "validation_status": FAIL_STATUS,
            "stop_reason": exc.code, "blocker_type": "SHARED_ARTIFACT_AUTHORITY_BLOCKER",
            "details": exc.details, "next_resume_task": TASK_ID}
