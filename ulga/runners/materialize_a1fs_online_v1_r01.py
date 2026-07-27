#!/usr/bin/env python3
'''Materialize the approved R01 product root through the existing shared authority.'''
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ulga.artifacts.a1fs_artifact_authority import (
    DEFAULT_MANIFEST,
    ArtifactAuthorityError,
    failure_report,
    resolve_artifact_root,
)
from ulga.runners import materialize_a1fs_online_v1 as base

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Extends the existing S19 shared artifact chain with the approved R01 packaging/update "
    "artifact only; it creates no curriculum, learner content, scoring, mastery, dashboard, "
    "audio, A2, Cloudflare route, deployment, or parallel authority."
)
REPO_ROOT = Path(__file__).resolve().parents[2]
R01_EXTENSION = REPO_ROOT / "ulga/artifacts/manifests/a1fs_online_v1_r01_artifact_extension.json"
DEFAULT_THROUGH = "R01_SAFE"


def load_r01_manifest() -> dict:
    manifest = base._load_effective_manifest(DEFAULT_MANIFEST)
    base._merge_manifest_extension(manifest, R01_EXTENSION)
    if manifest.get("default_through") != DEFAULT_THROUGH:
        raise ArtifactAuthorityError("R01_DEFAULT_THROUGH_INVALID")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--recover-from", type=Path, action="append", default=[])
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = load_r01_manifest()
        artifact_root = resolve_artifact_root(REPO_ROOT, args.artifact_root)
        report = base.materialize_sequentially(
            manifest, DEFAULT_THROUGH, REPO_ROOT, artifact_root,
            recovery_roots=args.recover_from, force=args.force,
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
