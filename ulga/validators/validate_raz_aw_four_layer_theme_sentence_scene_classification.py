#!/usr/bin/env python3
"""Validate the RAZ A-W four-layer Theme/Sentence/Scene package."""
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
from ulga.builders import build_raz_aw_four_layer_theme_sentence_scene_classification as builder  # noqa: E402

SCHEMA_PATH = REPO_ROOT / "ulga/schemas/raz_aw_four_layer_theme_sentence_scene_classification.schema.json"
DEFAULT_OUTPUT = REPO_ROOT / ".local/raz_aw/four_layer_classification/validation.safe.json"
PASS_STATUS = "PASS_RAZ_AW_FOUR_LAYER_THEME_SENTENCE_SCENE_CLASSIFICATION_VALIDATION"


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
    if package.get("schema_version") != builder.SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
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
    links = package.get("four_layer_cross_links", [])
    gate = package.get("classification_gate", {})
    record_count = scope.get("record_count")

    count_fields = (
        "derived_record_count",
        "review_candidate_count",
        "bridge_candidate_count",
        "linkage_page_unit_count",
    )
    for field in count_fields:
        if scope.get(field) != record_count:
            errors.append(f"{field}_mismatch")
    if scope.get("linkage_record_count") != record_count * 2:
        errors.append("linkage_record_count_mismatch")
    if len(links) != record_count:
        errors.append("four_layer_cross_link_count_mismatch")
    if summary.get("four_layer_cross_link_count") != record_count:
        errors.append("summary_four_layer_cross_link_count_mismatch")
    if summary.get("sentence_seed_candidate_count") != record_count:
        errors.append("sentence_seed_count_mismatch")
    if summary.get("scene_seed_candidate_count") != record_count:
        errors.append("scene_seed_count_mismatch")
    if package.get("errors") != []:
        errors.append("builder_errors_not_empty")
    if gate.get("decision") != "FOUR_LAYER_CLASSIFICATION_READY_FOR_REVIEW":
        errors.append("gate_decision_mismatch")
    if gate.get("ready_for_human_review") is not True:
        errors.append("review_ready_flag_mismatch")
    if gate.get("ready_for_canonical_promotion") is not False:
        errors.append("canonical_promotion_must_remain_false")
    if gate.get("ready_for_learning_unit_population") is not False:
        errors.append("unit_population_must_remain_false")
    if not all(gate.get("source_checks", {}).values()):
        errors.append("source_checks_not_all_true")

    refs = [row.get("source_unit_ref") for row in links]
    if len(refs) != len(set(refs)):
        errors.append("duplicate_four_layer_source_ref")
    for row in links:
        ref = row.get("source_unit_ref")
        if row.get("authority_status") != "candidate_only":
            errors.append(f"authority_status_mismatch:{ref}")
        if row.get("promotion_status") != "promotion_blocked":
            errors.append(f"promotion_status_mismatch:{ref}")
        if row.get("review_status") != "pending":
            errors.append(f"review_status_mismatch:{ref}")
        if row.get("normalized_trace_confidence") != "high":
            errors.append(f"normalized_trace_confidence_mismatch:{ref}")
        if row.get("enriched_trace_confidence") != "medium":
            errors.append(f"enriched_trace_confidence_mismatch:{ref}")

    if rebuilt is not None and package != rebuilt:
        errors.append("deterministic_rebuild_mismatch")

    return {
        "task_id": builder.TASK_ID,
        "validation_status": PASS_STATUS if not errors else "FAIL",
        "error_count": len(errors),
        "errors": sorted(set(errors)),
        "decision": gate.get("decision"),
        "record_count": record_count,
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
        rebuilt = None if args.skip_rebuild else builder.build_from_source(
            args.source_root, args.manifest
        )
        result = validate_package(package, rebuilt=rebuilt)
        deep.write_json_atomic(args.output, result)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["error_count"] == 0 else 1
    except (
        builder.FourLayerClassificationError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
