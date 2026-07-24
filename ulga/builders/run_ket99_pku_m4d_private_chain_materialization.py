#!/usr/bin/env python3
"""Resolve or rebuild RAZ inputs, then delegate to the governed M4D1 runner.

This compatibility entrypoint changes only prerequisite materialization and input
resolution. The existing M4D1 stage order, isolated learner-state database,
planner authority, validators, and claim boundaries remain authoritative.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Mapping, Sequence

from ulga.builders import build_ket99_pku_m4d_private_chain_materialization as base
from ulga.builders import build_raz_ai_acl_v1_s01_material_admission as s01
from ulga.builders import build_raz_ai_acl_v1_s02_semantic_dedup as s02
from ulga.builders import build_raz_ai_acl_v1_s03_authority_linkage as s03
from ulga.builders import build_raz_ai_acl_v1_s04_admission_resolution as s04
from ulga.builders import build_raz_ai_acl_v1_s05_material_registry as s05

REGISTRY_FILENAME = s05.DEFAULT_OUTPUT.name
DEDUP_FILENAME = s02.DEFAULT_OUTPUT.name
MATERIAL_FILENAME = s01.DEFAULT_MATERIAL.name
COVERAGE_FILENAME = s01.DEFAULT_COVERAGE.name
AUXILIARY_STAGE_ORDER = ("S01", "S02", "S03", "S04", "S05")


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


def optional_discover(
    *,
    explicit: Path | None,
    filename: str,
    roots: Sequence[Path],
    preferred_relatives: Sequence[str],
) -> Path | None:
    try:
        return base.discover_artifact(
            explicit=explicit,
            filename=filename,
            roots=roots,
            preferred_relatives=preferred_relatives,
        )
    except base.ChainMaterializationError as exc:
        if explicit is None and str(exc).startswith("artifact_not_found:"):
            return None
        raise


def auxiliary_output_paths() -> dict[str, Path]:
    return {
        "S01": s01.DEFAULT_OUTPUT.resolve(),
        "S02": s02.DEFAULT_OUTPUT.resolve(),
        "S03": s03.DEFAULT_OUTPUT.resolve(),
        "S04": s04.DEFAULT_OUTPUT.resolve(),
        "S05": s05.DEFAULT_OUTPUT.resolve(),
    }


def build_auxiliary_command_plan(
    *,
    material_package: Path,
    coverage_package: Path,
    outputs: Mapping[str, Path] | None = None,
) -> list[tuple[str, list[str]]]:
    paths = dict(outputs or auxiliary_output_paths())
    return [
        (
            "S01",
            base.module_command(
                "ulga.builders.build_raz_ai_acl_v1_s01_material_admission",
                "--material-package",
                material_package,
                "--coverage-package",
                coverage_package,
                "--output",
                paths["S01"],
            ),
        ),
        (
            "S02",
            base.module_command(
                "ulga.builders.build_raz_ai_acl_v1_s02_semantic_dedup",
                "--admission-package",
                paths["S01"],
                "--output",
                paths["S02"],
            ),
        ),
        (
            "S03",
            base.module_command(
                "ulga.builders.build_raz_ai_acl_v1_s03_authority_linkage",
                "--dedup-package",
                paths["S02"],
                "--output",
                paths["S03"],
            ),
        ),
        (
            "S04",
            base.module_command(
                "ulga.builders.build_raz_ai_acl_v1_s04_admission_resolution",
                "--authority-linkage-package",
                paths["S03"],
                "--output",
                paths["S04"],
            ),
        ),
        (
            "S05",
            base.module_command(
                "ulga.builders.build_raz_ai_acl_v1_s05_material_registry",
                "--admission-resolution-package",
                paths["S04"],
                "--output",
                paths["S05"],
            ),
        ),
    ]


def materialize_auxiliary_chain(
    *,
    material_package: Path,
    coverage_package: Path,
) -> tuple[Path, Path]:
    outputs = auxiliary_output_paths()
    for stage, command in build_auxiliary_command_plan(
        material_package=material_package,
        coverage_package=coverage_package,
        outputs=outputs,
    ):
        base.run_command(command)
        artifact = outputs[stage]
        if not artifact.is_file():
            raise base.ChainMaterializationError(
                f"auxiliary_stage_artifact_missing:{stage}:{artifact}"
            )
    return outputs["S05"], outputs["S02"]


def resolve_auxiliary_inputs(
    *,
    private_root: Path | None,
    raz_registry: Path | None,
    semantic_dedup: Path | None,
    material_package: Path | None = None,
    coverage_package: Path | None = None,
) -> tuple[Path, Path]:
    if (raz_registry is None) != (semantic_dedup is None):
        raise base.ChainMaterializationError("explicit_auxiliary_pair_required")

    roots = auxiliary_roots(private_root)
    registry = optional_discover(
        explicit=raz_registry,
        filename=REGISTRY_FILENAME,
        roots=roots,
        preferred_relatives=(
            "raz_ai/acl_v1_s05_material_registry/a1_a1plus_material_registry.safe.json",
        ),
    )
    dedup = optional_discover(
        explicit=semantic_dedup,
        filename=DEDUP_FILENAME,
        roots=roots,
        preferred_relatives=(
            "raz_ai/acl_v1_s02_semantic_dedup/semantic_dedup_representative_selection.safe.json",
        ),
    )
    if registry is not None and dedup is not None:
        return registry, dedup

    material = base.discover_artifact(
        explicit=material_package,
        filename=MATERIAL_FILENAME,
        roots=roots,
        preferred_relatives=(
            "raz_aw/derived_material_extraction_minimal/derived_material_extraction_minimal.safe.json",
        ),
    )
    coverage = base.discover_artifact(
        explicit=coverage_package,
        filename=COVERAGE_FILENAME,
        roots=roots,
        preferred_relatives=(
            "raz_ai/a1_a1plus_coverage_recheck/a1_a1plus_coverage_recheck.safe.json",
        ),
    )
    return materialize_auxiliary_chain(
        material_package=material,
        coverage_package=coverage,
    )


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
    parser.add_argument("--material-package", type=Path)
    parser.add_argument("--coverage-package", type=Path)
    args, passthrough = parser.parse_known_args(argv)

    try:
        registry, dedup = resolve_auxiliary_inputs(
            private_root=args.private_root,
            raz_registry=args.raz_registry,
            semantic_dedup=args.semantic_dedup,
            material_package=args.material_package,
            coverage_package=args.coverage_package,
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
    except (
        base.ChainMaterializationError,
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
