#!/usr/bin/env python3
"""Discover cross-worktree RAZ inputs, then delegate to the governed M4D1 runner.

This compatibility entrypoint changes only input discovery.  The existing M4D1
stage order, validators, isolated learner-state database, planner authority, and
claim boundaries remain authoritative.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from ulga.builders import build_ket99_pku_m4d_private_chain_materialization as base

REGISTRY_FILENAME = base.raz_registry.DEFAULT_OUTPUT.name
DEDUP_FILENAME = base.raz_dedup.DEFAULT_OUTPUT.name


def auxiliary_roots(private_root: Path | None) -> list[Path]:
    roots: list[Path] = []
    if private_root is not None:
        roots.append(private_root.resolve() / ".local")
    roots.append(base.ROOT / ".local")
    unique: list[Path] = []
    for root in roots:
        resolved = root.resolve()
        if resolved not in unique:
            unique.append(resolved)
    return unique


def resolve_auxiliary_inputs(
    *,
    private_root: Path | None,
    raz_registry: Path | None,
    semantic_dedup: Path | None,
) -> tuple[Path, Path]:
    roots = auxiliary_roots(private_root)
    registry = base.discover_artifact(
        explicit=raz_registry,
        filename=REGISTRY_FILENAME,
        roots=roots,
        preferred_relatives=(
            "raz_ai/acl_v1_s05_material_registry/a1_a1plus_material_registry.safe.json",
        ),
    )
    dedup = base.discover_artifact(
        explicit=semantic_dedup,
        filename=DEDUP_FILENAME,
        roots=roots,
        preferred_relatives=(
            "raz_ai/acl_v1_s02_semantic_dedup/semantic_dedup_representative_selection.safe.json",
        ),
    )
    return registry, dedup


def forwarded_arguments(args: argparse.Namespace, passthrough: Sequence[str]) -> list[str]:
    forwarded: list[str] = []
    if args.private_root is not None:
        forwarded.extend(("--private-root", str(args.private_root.resolve())))
    forwarded.extend(passthrough)
    return forwarded


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, add_help=True)
    parser.add_argument("--private-root", type=Path)
    parser.add_argument("--raz-registry", type=Path)
    parser.add_argument("--semantic-dedup", type=Path)
    args, passthrough = parser.parse_known_args(argv)

    registry, dedup = resolve_auxiliary_inputs(
        private_root=args.private_root,
        raz_registry=args.raz_registry,
        semantic_dedup=args.semantic_dedup,
    )

    previous_registry = base.raz_registry.DEFAULT_OUTPUT
    previous_dedup = base.raz_dedup.DEFAULT_OUTPUT
    base.raz_registry.DEFAULT_OUTPUT = registry
    base.raz_dedup.DEFAULT_OUTPUT = dedup
    try:
        return base.main(forwarded_arguments(args, passthrough))
    finally:
        base.raz_registry.DEFAULT_OUTPUT = previous_registry
        base.raz_dedup.DEFAULT_OUTPUT = previous_dedup


if __name__ == "__main__":
    raise SystemExit(main())
