#!/usr/bin/env python3
"""Validate the RAZ A-W linkage integrity and page-unit lineage package."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep  # noqa: E402
from ulga.builders import build_raz_aw_linkage_integrity_and_page_unit_lineage as builder  # noqa: E402

SCHEMA_PATH = REPO_ROOT / "ulga/schemas/raz_aw_linkage_integrity_and_page_unit_lineage.schema.json"
DEFAULT_OUTPUT = REPO_ROOT / ".local/raz_aw/linkage_integrity/validation.safe.json"
PASS_STATUS = "PASS_RAZ_AW_LINKAGE_INTEGRITY_AND_PAGE_UNIT_LINEAGE_VALIDATION"


def validate_direct_tree(source_root: Path) -> list[str]:
    """Require exactly Level_A..Level_W as direct linkage children.

    This catches the former failure where bridge folders were nested under
    linkage/Level_R and linkage/Level_S while direct linkage files were absent.
    """
    linkage_root = source_root / "linkage" if (source_root / "linkage").is_dir() else source_root
    errors: list[str] = []
    if not linkage_root.is_dir():
        return [f"linkage_root_missing:{linkage_root}"]
    expected_names = {f"Level_{level}" for level in builder.LEVELS}
    actual_dirs = {path.name for path in linkage_root.iterdir() if path.is_dir()}
    missing = sorted(expected_names - actual_dirs)
    unexpected = sorted(actual_dirs - expected_names)
    errors.extend(f"missing_direct_level_folder:{name}" for name in missing)
    errors.extend(f"unexpected_direct_linkage_folder:{name}" for name in unexpected)
    for level in builder.LEVELS:
        folder = linkage_root / f"Level_{level}"
        expected_file = folder / f"raz_{level}_authority_linkage_view.json"
        if not expected_file.is_file():
            errors.append(f"missing_direct_linkage_file:{level}:{expected_file.name}")
            continue
        nested_dirs = sorted(path.name for path in folder.iterdir() if path.is_dir())
        errors.extend(
            f"nested_linkage_folder_forbidden:{level}:{name}" for name in nested_dirs
        )
        json_files = sorted(path.name for path in folder.glob("*.json"))
        if json_files != [expected_file.name]:
            errors.append(
                f"direct_linkage_file_set_mismatch:{level}:{json_files}"
            )
    return errors


def validate_package(
    package: Mapping[str, Any],
    *,
    rebuilt: Mapping[str, Any] | None = None,
    schema_path: Path = SCHEMA_PATH,
    tree_errors: Sequence[str] = (),
) -> dict[str, Any]:
    schema = deep.read_json(schema_path)
    errors = [
        f"schema:{'.'.join(map(str, error.absolute_path)) or '$'}:{error.message}"
        for error in sorted(
            Draft202012Validator(schema).iter_errors(package),
            key=lambda item: list(item.absolute_path),
        )
    ]
    errors.extend(tree_errors)
    if package.get("task_id") != builder.TASK_ID:
        errors.append("task_id_mismatch")
    if package.get("schema_version") != builder.SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if package.get("validation_status") != builder.PASS_STATUS:
        errors.append("builder_status_mismatch")
    if package.get("claim_boundaries") != builder.CLAIM_BOUNDARIES:
        errors.append("claim_boundaries_mismatch")
    errors.extend(builder.scan_forbidden_keys(package))

    supplied = package.get("package_sha256")
    expected = deep.sha256_value({
        key: value for key, value in package.items() if key != "package_sha256"
    })
    if supplied != expected:
        errors.append("package_sha256_mismatch")

    scope = package.get("source_scope", {})
    lineage = package.get("page_unit_lineage", [])
    gate = package.get("integrity_gate", {})
    page_count = scope.get("page_unit_count")
    if page_count != len(lineage):
        errors.append("page_unit_lineage_count_mismatch")
    if not isinstance(page_count, int) or scope.get("page_unit_linkage_record_count") != page_count * 2:
        errors.append("page_unit_linkage_record_count_mismatch")
    if scope.get("source_file_count") != len(builder.LEVELS):
        errors.append("source_file_count_mismatch")
    if scope.get("levels") != list(builder.LEVELS):
        errors.append("levels_mismatch")
    if package.get("errors") != []:
        errors.append("builder_errors_not_empty")
    if gate.get("decision") != "LINKAGE_READY_FOR_CLASSIFICATION_LINEAGE":
        errors.append("gate_decision_mismatch")
    if gate.get("ready_for_classification_lineage") is not True:
        errors.append("classification_lineage_ready_flag_mismatch")
    if gate.get("ready_for_canonical_promotion") is not False:
        errors.append("canonical_promotion_must_remain_false")
    if gate.get("ready_for_learning_unit_population") is not False:
        errors.append("unit_population_must_remain_false")
    if not all(gate.get("source_checks", {}).values()):
        errors.append("source_checks_not_all_true")

    refs = [row.get("source_unit_ref") for row in lineage]
    if len(refs) != len(set(refs)):
        errors.append("duplicate_page_unit_lineage_ref")
    for row in lineage:
        ref = row.get("source_unit_ref")
        if row.get("authority_status") != "candidate_only":
            errors.append(f"lineage_authority_status_mismatch:{ref}")
        if row.get("promotion_status") != "promotion_blocked":
            errors.append(f"lineage_promotion_status_mismatch:{ref}")
        if row.get("review_status") != "pending":
            errors.append(f"lineage_review_status_mismatch:{ref}")
        if set(row.get("allowed_authority_targets") or []) < builder.EXPECTED_ALLOWED_TARGETS:
            errors.append(f"lineage_allowed_targets_missing:{ref}")
        if set(row.get("blocked_authority_targets") or []) < builder.EXPECTED_BLOCKED_TARGETS:
            errors.append(f"lineage_blocked_targets_missing:{ref}")

    if rebuilt is not None and package != rebuilt:
        errors.append("deterministic_rebuild_mismatch")

    unique_errors = sorted(set(errors))
    return {
        "task_id": builder.TASK_ID,
        "validation_status": PASS_STATUS if not unique_errors else "FAIL",
        "error_count": len(unique_errors),
        "errors": unique_errors,
        "decision": gate.get("decision"),
        "page_unit_count": page_count,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, nargs="?", default=builder.DEFAULT_OUTPUT)
    parser.add_argument("--source-root", type=Path, default=builder.DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-rebuild", action="store_true")
    args = parser.parse_args(argv)
    try:
        package = deep.read_json(args.package)
        tree_errors = validate_direct_tree(args.source_root)
        rebuilt = None if args.skip_rebuild else builder.load_and_build(args.source_root)
        result = validate_package(
            package,
            rebuilt=rebuilt,
            tree_errors=tree_errors,
        )
        deep.write_json_atomic(args.output, result)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["error_count"] == 0 else 1
    except (
        builder.LinkageIntegrityError,
        deep.AlignmentError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
