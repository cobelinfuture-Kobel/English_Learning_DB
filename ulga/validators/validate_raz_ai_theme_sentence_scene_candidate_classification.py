#!/usr/bin/env python3
"""Validate the RAZ A-I Theme/Sentence/Scene candidate classification package."""
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

from ulga.builders import build_raz_ai_theme_sentence_scene_candidate_classification as builder  # noqa: E402
from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep  # noqa: E402
from ulga.builders import build_raz_gi_targeted_gap_source_expansion as gi  # noqa: E402

SCHEMA_PATH = REPO_ROOT / "ulga/schemas/raz_ai_theme_sentence_scene_candidate_classification.schema.json"
DEFAULT_OUTPUT = REPO_ROOT / ".local/raz_ai/theme_sentence_scene_classification/validation.safe.json"
PASS_STATUS = "PASS_RAZ_AI_THEME_SENTENCE_SCENE_CANDIDATE_CLASSIFICATION_VALIDATION"


def validate_package(
    package: Mapping[str, Any],
    *,
    rebuilt: Mapping[str, Any] | None = None,
    schema_path: Path = SCHEMA_PATH,
) -> dict[str, Any]:
    schema = deep.read_json(schema_path)
    errors = [
        f"schema:{'.'.join(map(str, error.absolute_path)) or '$'}:{error.message}"
        for error in sorted(
            Draft202012Validator(schema).iter_errors(package),
            key=lambda item: list(item.absolute_path),
        )
    ]
    if package.get("task_id") != builder.TASK_ID:
        errors.append("task_id_mismatch")
    if package.get("validation_status") != builder.PASS_STATUS:
        errors.append("builder_status_mismatch")
    if package.get("claim_boundaries") != builder.CLAIM_BOUNDARIES:
        errors.append("claim_boundaries_mismatch")
    errors.extend(builder.scan_forbidden_safe_keys(package))

    supplied = package.get("package_sha256")
    expected = deep.sha256_value({
        key: value for key, value in package.items() if key != "package_sha256"
    })
    if supplied != expected:
        errors.append("package_sha256_mismatch")

    scope = package.get("source_scope", {})
    summary = package.get("classification_summary", {})
    gate = package.get("classification_gate", {})
    record_count = scope.get("record_count")
    if summary.get("sentence_seed_candidate_count") != record_count:
        errors.append("sentence_seed_count_mismatch")
    if summary.get("scene_seed_candidate_count") != record_count:
        errors.append("scene_seed_count_mismatch")
    if summary.get("cross_link_count") != record_count:
        errors.append("cross_link_count_mismatch")
    if gate.get("ready_for_canonical_promotion") is not False:
        errors.append("canonical_promotion_must_remain_false")
    if gate.get("ready_for_learning_unit_population") is not False:
        errors.append("unit_population_must_remain_false")
    if gate.get("decision") == "CLASSIFICATION_READY_FOR_REVIEW":
        if not gate.get("ready_for_human_review"):
            errors.append("review_ready_flag_mismatch")
        if not all(gate.get("source_checks", {}).values()):
            errors.append("classification_ready_without_all_source_checks")

    if rebuilt is not None and package != rebuilt:
        errors.append("deterministic_rebuild_mismatch")

    return {
        "task_id": builder.TASK_ID,
        "validation_status": PASS_STATUS if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "decision": gate.get("decision"),
        "j_w_read_performed": scope.get("j_w_read_performed"),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, nargs="?", default=builder.DEFAULT_OUTPUT)
    parser.add_argument("--source-root", type=Path, default=builder.DEFAULT_SOURCE_ROOT)
    parser.add_argument("--manifest", type=Path, default=builder.DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-rebuild", action="store_true")
    args = parser.parse_args(argv)
    try:
        package = deep.read_json(args.package)
        rebuilt = None
        if not args.skip_rebuild:
            af_records, af_index = gi.load_levels(args.source_root, gi.AF_LEVELS)
            gi_records, gi_index = gi.load_levels(args.source_root, gi.GI_LEVELS)
            rebuilt = builder.build_package(
                [*af_records, *gi_records],
                [*af_index, *gi_index],
                deep.load_authorities(),
                deep.load_manifest_grammar_tags(args.manifest),
            )
        result = validate_package(package, rebuilt=rebuilt)
        deep.write_json_atomic(args.output, result)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["error_count"] == 0 else 1
    except (
        builder.ClassificationError,
        gi.TargetedGapError,
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
