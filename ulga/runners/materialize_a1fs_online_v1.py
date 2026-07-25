#!/usr/bin/env python3
"""Materialize A1FS Online V1 through one shared artifact authority."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ulga.artifacts.a1fs_artifact_authority import (
    A1FS_CONTENT_POLICY_EXEMPTION,
    A1FS_CONTENT_POLICY_MODE,
    ArtifactAuthorityError,
    DEFAULT_MANIFEST,
    failure_report,
    load_manifest,
    materialize,
    resolve_artifact_root,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--through", default="S02_SAFE")
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--recover-from", type=Path, action="append", default=[])
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        manifest = load_manifest(args.manifest)
        artifact_root = resolve_artifact_root(REPO_ROOT, args.artifact_root)
        report = materialize(
            manifest,
            args.through,
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
