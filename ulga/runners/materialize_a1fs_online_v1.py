#!/usr/bin/env python3
"""Materialize A1FS Online V1 through one shared artifact authority."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from ulga.artifacts.a1fs_artifact_authority import (
    A1FS_CONTENT_POLICY_EXEMPTION,
    A1FS_CONTENT_POLICY_MODE,
    PASS_STATUS,
    SCHEMA_VERSION,
    TASK_ID,
    ArtifactAuthorityError,
    DEFAULT_MANIFEST,
    _command,
    _entry,
    _fingerprint,
    _hash,
    _state_matches,
    _write_state,
    dependency_order,
    failure_report,
    load_manifest,
    paths,
    preflight,
    resolve_artifact_root,
    validate,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(argv: Sequence[str], cwd: Path) -> int:
    return subprocess.run(list(argv), cwd=cwd, check=False).returncode


def materialize_sequentially(
    manifest: dict[str, Any],
    through: str,
    repo_root: Path,
    artifact_root: Path,
    *,
    recovery_roots: Iterable[Path] = (),
    force: bool = False,
    command_runner: Callable[[Sequence[str], Path], int] = _run,
) -> dict[str, Any]:
    """Build each dependency before fingerprinting or validating its consumer."""
    order = dependency_order(manifest, through)
    recovered = preflight(manifest, order, repo_root, artifact_root, recovery_roots)
    results: list[dict[str, str]] = []
    rebuilt: set[str] = set()

    for artifact_id in order:
        entry = _entry(manifest, artifact_id)
        authority = entry.get("authority")
        resolved = paths(manifest, artifact_id, repo_root, artifact_root)

        if authority in {"repository", "shared_external"}:
            validate(manifest, artifact_id, repo_root, artifact_root)
            results.append(
                {
                    "artifact_id": artifact_id,
                    "action": "REUSED",
                    "reason": "authoritative_input",
                    "path": str(resolved["primary"]),
                }
            )
            continue

        # All dependencies are already validated/materialized because order is topological.
        fingerprint = _fingerprint(manifest, artifact_id, repo_root, artifact_root)
        dependency_rebuilt = any(
            dependency in rebuilt for dependency in entry.get("dependencies", [])
        )
        reusable = False
        if not force and not dependency_rebuilt:
            try:
                validate(manifest, artifact_id, repo_root, artifact_root)
                reusable = _state_matches(resolved["state"], fingerprint)
            except ArtifactAuthorityError:
                reusable = False

        if reusable:
            action = "REUSED"
            reason = "fingerprint_match"
        else:
            action = "BUILD"
            reason = (
                "forced"
                if force
                else "dependency_rebuilt"
                if dependency_rebuilt
                else "missing_or_stale"
            )
            resolved["primary"].parent.mkdir(parents=True, exist_ok=True)
            if resolved["report"]:
                resolved["report"].parent.mkdir(parents=True, exist_ok=True)
            argv = _command(manifest, artifact_id, repo_root, artifact_root)
            exit_code = command_runner(argv, repo_root)
            if exit_code:
                raise ArtifactAuthorityError(
                    "ARTIFACT_BUILD_FAILED",
                    {
                        "artifact_id": artifact_id,
                        "exit_code": exit_code,
                        "command": list(argv),
                    },
                )
            validate(manifest, artifact_id, repo_root, artifact_root)
            _write_state(resolved, artifact_id, fingerprint)
            rebuilt.add(artifact_id)

        results.append(
            {
                "artifact_id": artifact_id,
                "action": action,
                "reason": reason,
                "path": str(resolved["primary"]),
            }
        )

    final = paths(manifest, through, repo_root, artifact_root)
    summary = validate(manifest, through, repo_root, artifact_root)
    target = final["report"] or final["primary"]
    next_short_step = str(summary.get("next_short_step") or through)
    return {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "artifact_root": str(artifact_root),
        "through": through,
        "dependency_order": order,
        "recovered_external_artifacts": recovered,
        "actions": results,
        "final_artifact_path": str(target),
        "final_artifact_sha256": _hash(target),
        "final_artifact_summary": summary,
        "stop_reason": "NONE",
        "next_short_step": next_short_step,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--through")
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--recover-from", type=Path, action="append", default=[])
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        manifest = load_manifest(args.manifest)
        through = str(args.through or manifest.get("default_through") or "").strip()
        if not through:
            raise ArtifactAuthorityError("MANIFEST_DEFAULT_THROUGH_MISSING")
        artifact_root = resolve_artifact_root(REPO_ROOT, args.artifact_root)
        report = materialize_sequentially(
            manifest,
            through,
            REPO_ROOT,
            artifact_root,
            recovery_roots=args.recover_from,
            force=args.force,
        )
        exit_code = 0
    except ArtifactAuthorityError as exc:
        report = failure_report(exc)
        exit_code = 1

    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
