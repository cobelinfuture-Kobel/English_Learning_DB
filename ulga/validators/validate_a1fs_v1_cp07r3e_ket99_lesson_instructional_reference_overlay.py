#!/usr/bin/env python3
"""Validate the CP07F-R3E KET99 lesson instructional reference overlay."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp07r3e_ket99_lesson_instructional_reference_overlay as builder  # noqa: E402

VALIDATOR_ID = "validate_a1fs_v1_cp07r3e_ket99_lesson_instructional_reference_overlay"
SCHEMA_VERSION = "a1fs.v1.cp07f.r3e.ket99_lesson_instructional_reference_overlay_validation.v1"


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def validate_artifact(
    artifact: Mapping[str, Any],
    *,
    m1_graph: Mapping[str, Any],
    m2_consumer: Mapping[str, Any],
    cp07b_overlay: Mapping[str, Any],
    r3c_bridge: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if artifact.get("task_id") != builder.TASK_ID:
        errors.append("task_id_invalid")
    if artifact.get("schema_version") != builder.SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if artifact.get("validation_status") != builder.PASS_STATUS:
        errors.append("validation_status_invalid")
    if artifact.get("stop_reason") != "NONE" or artifact.get("errors") != []:
        errors.append("artifact_not_passed")
    if artifact.get("next_short_step") != builder.NEXT_SHORT_STEP:
        errors.append("next_short_step_invalid")

    expected_identity = {
        "m1_hard_graph_sha256": builder._digest(m1_graph),
        "m2_consumer_sha256": builder._digest(m2_consumer),
        "cp07b_instructional_overlay_sha256": builder._digest(cp07b_overlay),
        "r3c_semantic_bridge_sha256": builder._digest(r3c_bridge),
    }
    if artifact.get("source_identity") != expected_identity:
        errors.append("source_identity_mismatch")

    authority = artifact.get("authority_contract")
    if not isinstance(authority, Mapping):
        errors.append("authority_contract_missing")
        authority = {}
    if authority.get("source_role") != "NON_AUTHORITATIVE_KET_TEACHER_DELIVERY_REFERENCE":
        errors.append("source_role_invalid")
    for key in (
        "hard_graph_mutation_allowed",
        "hard_lesson_selection_allowed",
        "mastery_gate_creation_allowed",
        "delivery_block_on_missing_reference_allowed",
        "fuzzy_matching_allowed",
    ):
        if authority.get(key) is not False:
            errors.append(f"authority_boundary_invalid:{key}")
    if authority.get("a2_a2plus_status") != "LOCKED":
        errors.append("a2_lock_invalid")

    expected_lessons = {
        str(row.get("lesson_id") or ""): row
        for row in m2_consumer.get("lesson_catalog", [])
        if isinstance(row, Mapping) and str(row.get("level") or "") in builder.LEVELS
    }
    rows = artifact.get("lesson_instructional_references")
    if not isinstance(rows, list):
        errors.append("lesson_reference_list_required")
        rows = []
    row_index = {
        str(row.get("lesson_id") or ""): row
        for row in rows
        if isinstance(row, Mapping) and str(row.get("lesson_id") or "")
    }
    if len(row_index) != len(rows):
        errors.append("lesson_reference_identity_missing_or_duplicate")
    if set(row_index) != set(expected_lessons):
        errors.append("lesson_reference_identity_set_mismatch")

    referenced_count = 0
    unreferenced_count = 0
    reference_count = 0
    referenced_transcripts: set[str] = set()
    for lesson_id, row in row_index.items():
        lesson = expected_lessons[lesson_id]
        for key in ("lesson_node_id", "skill", "level"):
            if row.get(key) != lesson.get(key):
                errors.append(f"lesson_identity_drift:{lesson_id}:{key}")
        expected_requirements = sorted({str(value) for value in lesson.get("requirement_node_ids", []) if str(value)})
        if row.get("requirement_node_ids") != expected_requirements:
            errors.append(f"requirement_identity_drift:{lesson_id}")
        if row.get("delivery_blocked_by_missing_reference") is not False:
            errors.append(f"missing_reference_blocks_delivery:{lesson_id}")
        if row.get("hard_lesson_selection_changed") is not False:
            errors.append(f"hard_lesson_selection_changed:{lesson_id}")
        references = row.get("instructional_references")
        if not isinstance(references, list):
            errors.append(f"instructional_reference_list_invalid:{lesson_id}")
            references = []
        status = row.get("reference_status")
        if references:
            referenced_count += 1
            if status != "REFERENCED":
                errors.append(f"referenced_status_invalid:{lesson_id}")
        else:
            unreferenced_count += 1
            if status != "NO_EXACT_KET99_REFERENCE":
                errors.append(f"unreferenced_status_invalid:{lesson_id}")
        seen_occurrences: set[str] = set()
        for reference in references:
            if not isinstance(reference, Mapping):
                errors.append(f"instructional_reference_invalid:{lesson_id}")
                continue
            occurrence_id = str(reference.get("evidence_occurrence_id") or "")
            if not occurrence_id or occurrence_id in seen_occurrences:
                errors.append(f"instructional_reference_identity_invalid:{lesson_id}:{occurrence_id}")
            seen_occurrences.add(occurrence_id)
            if reference.get("runtime_effect") != "OPTIONAL_TEACHING_REFERENCE_ONLY":
                errors.append(f"instructional_reference_runtime_effect_invalid:{lesson_id}:{occurrence_id}")
            basis = reference.get("mapping_basis")
            if not isinstance(basis, list) or not basis or any(not str(value).startswith("EXACT_") for value in basis):
                errors.append(f"instructional_reference_mapping_basis_invalid:{lesson_id}:{occurrence_id}")
            transcript_id = str(reference.get("transcript_id") or "")
            if not transcript_id:
                errors.append(f"instructional_reference_transcript_missing:{lesson_id}:{occurrence_id}")
            referenced_transcripts.add(transcript_id)
            reference_count += 1

    transcript_ids = {
        str(row.get("transcript_id") or "")
        for row in cp07b_overlay.get("transcript_overlays", [])
        if isinstance(row, Mapping) and str(row.get("transcript_id") or "")
    }
    summary = artifact.get("coverage_summary")
    if not isinstance(summary, Mapping):
        errors.append("coverage_summary_missing")
        summary = {}
    expected_summary = {
        "learning_lesson_count": len(rows),
        "referenced_lesson_count": referenced_count,
        "unreferenced_lesson_count": unreferenced_count,
        "instructional_reference_count": reference_count,
        "transcript_count": len(transcript_ids),
        "referenced_transcript_count": len(referenced_transcripts),
        "unused_transcript_count": len(transcript_ids - referenced_transcripts),
        "hard_graph_edge_delta": 0,
        "blocked_lesson_count": 0,
    }
    for key, value in expected_summary.items():
        if summary.get(key) != value:
            errors.append(f"coverage_summary_mismatch:{key}")

    boundaries = artifact.get("claim_boundaries")
    if not isinstance(boundaries, Mapping) or any(value is not False for value in boundaries.values()):
        errors.append("claim_boundaries_invalid")
    try:
        builder._walk_forbidden(artifact)
    except builder.ReferenceOverlayError as exc:
        errors.append(str(exc))

    deterministic = False
    try:
        rebuilt = builder.build_artifact(m1_graph, m2_consumer, cp07b_overlay, r3c_bridge)
        deterministic = builder._digest(rebuilt) == builder._digest(artifact)
        if not deterministic:
            errors.append("deterministic_rebuild_mismatch")
    except (builder.ReferenceOverlayError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"deterministic_rebuild_failed:{exc}")

    return {
        "task_id": builder.TASK_ID,
        "validator_id": VALIDATOR_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": builder.PASS_STATUS if not errors else "FAIL_CP07F_R3E_KET99_LESSON_INSTRUCTIONAL_REFERENCE_OVERLAY",
        "error_count": len(errors),
        "errors": errors,
        "deterministic_rebuild_matches": deterministic,
        "learning_lesson_count": len(rows),
        "referenced_lesson_count": referenced_count,
        "unreferenced_lesson_count": unreferenced_count,
        "instructional_reference_count": reference_count,
        "blocked_lesson_count": int(summary.get("blocked_lesson_count") or 0),
        "hard_graph_unchanged": summary.get("hard_graph_edge_delta") == 0,
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILED",
        "next_short_step": builder.NEXT_SHORT_STEP,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--m1-graph", type=Path, required=True)
    parser.add_argument("--m2-consumer", type=Path, required=True)
    parser.add_argument("--cp07b-overlay", type=Path, required=True)
    parser.add_argument("--r3c-bridge", type=Path, required=True)
    args = parser.parse_args(argv)
    report = validate_artifact(
        _read(args.artifact),
        m1_graph=_read(args.m1_graph),
        m2_consumer=_read(args.m2_consumer),
        cp07b_overlay=_read(args.cp07b_overlay),
        r3c_bridge=_read(args.r3c_bridge),
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["validation_status"] == builder.PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
