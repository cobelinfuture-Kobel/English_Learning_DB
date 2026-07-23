#!/usr/bin/env python3
"""Validate the CP07F-R3C KET Authority semantic bridge."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp07r3c_ket_authority_semantic_bridge as builder  # noqa: E402

VALIDATOR_ID = "validate_a1fs_v1_cp07r3c_ket_authority_semantic_bridge"
SCHEMA_VERSION = "a1fs.v1.cp07f.r3c.ket_authority_semantic_bridge_validation.v1"


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def _walk_forbidden(value: Any, path: str, errors: list[str]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in builder.FORBIDDEN_KEYS:
                errors.append(f"private_content_key_forbidden:{path}.{key}")
            _walk_forbidden(child, f"{path}.{key}", errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_forbidden(child, f"{path}[{index}]", errors)


def validate_artifact(
    artifact: Mapping[str, Any],
    *,
    m1_graph: Mapping[str, Any],
    m2_consumer: Mapping[str, Any],
    cp07b_overlay: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if artifact.get("task_id") != builder.TASK_ID:
        errors.append("task_id_invalid")
    if artifact.get("schema_version") != builder.SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if artifact.get("validation_status") != builder.PASS_STATUS:
        errors.append("validation_status_invalid")
    if artifact.get("scope") != "A1_A1_PLUS_ONLY":
        errors.append("scope_invalid")
    if artifact.get("stop_reason") != "NONE" or artifact.get("errors") != []:
        errors.append("artifact_not_passed")
    if artifact.get("next_short_step") != builder.NEXT_SHORT_STEP:
        errors.append("next_short_step_invalid")

    expected_source_identity = {
        "m1_hard_graph_sha256": builder._digest(m1_graph),
        "m2_consumer_sha256": builder._digest(m2_consumer),
        "cp07b_instructional_overlay_sha256": builder._digest(cp07b_overlay),
    }
    if artifact.get("source_identity") != expected_source_identity:
        errors.append("source_identity_mismatch")

    authority = artifact.get("authority_contract")
    if not isinstance(authority, Mapping):
        errors.append("authority_contract_required")
    else:
        if authority.get("identity_join") != "M1_COVERAGE_ASSET_ID_TO_M2_ASSET_PAYLOAD":
            errors.append("identity_join_invalid")
        if authority.get("semantic_match_mode") != "EXACT_NORMALIZED_AUTHORITY_TEXT_ONLY":
            errors.append("semantic_match_mode_invalid")
        if authority.get("fuzzy_matching_allowed") is not False:
            errors.append("fuzzy_matching_not_locked")
        if authority.get("manual_opaque_id_mapping_embedded") is not False:
            errors.append("manual_opaque_mapping_detected")
        if authority.get("root_lesson_policy") != "OWN_ASSET_BODY_AUTHORITY_TARGET_REQUIRED":
            errors.append("root_lesson_policy_invalid")
        if authority.get("hard_graph_mutation_allowed") is not False:
            errors.append("hard_graph_mutation_not_locked")
        if authority.get("a2_a2plus_status") != "LOCKED":
            errors.append("a2_lock_invalid")

    rows = artifact.get("lesson_semantic_bridges")
    if not isinstance(rows, list) or not rows:
        errors.append("lesson_semantic_bridge_list_required")
        rows = []
    identities: set[str] = set()
    resolved_count = 0
    root_count = 0
    requirement_count = 0
    for row in rows:
        if not isinstance(row, Mapping):
            errors.append("lesson_semantic_bridge_row_invalid")
            continue
        lesson_id = str(row.get("lesson_id") or "")
        if not lesson_id or lesson_id in identities:
            errors.append(f"lesson_identity_missing_or_duplicate:{lesson_id}")
        identities.add(lesson_id)
        if row.get("skill") not in builder.SKILLS or row.get("level") not in {"A1", "A1+"}:
            errors.append(f"lesson_scope_invalid:{lesson_id}")
        requirements = row.get("requirement_node_ids")
        matched = row.get("matched_requirement_node_ids")
        grammar = row.get("grammar_unit_ids")
        evidence = row.get("authority_evidence")
        if not isinstance(requirements, list) or not isinstance(matched, list):
            errors.append(f"requirement_identity_list_invalid:{lesson_id}")
            requirements, matched = [], []
        if not set(matched) <= set(requirements):
            errors.append(f"matched_requirement_not_subset:{lesson_id}")
        if not isinstance(grammar, list) or not isinstance(evidence, list):
            errors.append(f"semantic_target_or_evidence_list_invalid:{lesson_id}")
            grammar, evidence = [], []
        anchor_mode = row.get("anchor_mode")
        if requirements:
            requirement_count += 1
            if anchor_mode != "REQUIREMENT_ASSET_AUTHORITY":
                errors.append(f"requirement_anchor_mode_invalid:{lesson_id}")
        else:
            root_count += 1
            if anchor_mode != "ROOT_LESSON_ASSET_AUTHORITY":
                errors.append(f"root_anchor_mode_invalid:{lesson_id}")
        status = row.get("resolution_status")
        if status not in {"RESOLVED", "UNRESOLVED"}:
            errors.append(f"resolution_status_invalid:{lesson_id}")
        if status == "RESOLVED":
            resolved_count += 1
            if not grammar or not evidence:
                errors.append(f"resolved_lesson_without_semantic_evidence:{lesson_id}")
            if requirements and not matched:
                errors.append(f"resolved_requirement_lesson_without_matched_requirement:{lesson_id}")
            if row.get("unresolved_reason") is not None:
                errors.append(f"resolved_lesson_has_unresolved_reason:{lesson_id}")
        else:
            if grammar or evidence:
                errors.append(f"unresolved_lesson_has_semantic_target:{lesson_id}")
            if not str(row.get("unresolved_reason") or ""):
                errors.append(f"unresolved_reason_missing:{lesson_id}")
        for item in evidence:
            if not isinstance(item, Mapping):
                errors.append(f"authority_evidence_invalid:{lesson_id}")
                continue
            if item.get("match_mode") != "EXACT_NORMALIZED_AUTHORITY_TEXT":
                errors.append(f"authority_match_mode_invalid:{lesson_id}")
            if len(str(item.get("authority_scalar_sha256") or "")) != 64:
                errors.append(f"authority_scalar_digest_invalid:{lesson_id}")
            if not str(item.get("authority_asset_key") or "") or not str(item.get("authority_payload_path") or ""):
                errors.append(f"authority_asset_or_path_missing:{lesson_id}")
            if not item.get("grammar_unit_ids"):
                errors.append(f"authority_evidence_grammar_target_missing:{lesson_id}")

    summary = artifact.get("coverage_summary")
    if not isinstance(summary, Mapping):
        errors.append("coverage_summary_required")
        summary = {}
    expected_summary = {
        "learning_lesson_count": len(rows),
        "resolved_lesson_count": resolved_count,
        "unresolved_lesson_count": len(rows) - resolved_count,
        "root_lesson_count": root_count,
        "requirement_bound_lesson_count": requirement_count,
        "hard_graph_edge_count_before": int(m1_graph.get("counts", {}).get("edge_count", 0)),
        "hard_graph_edge_count_after": int(m1_graph.get("counts", {}).get("edge_count", 0)),
        "new_hard_prerequisite_edge_count": 0,
    }
    for key, value in expected_summary.items():
        if summary.get(key) != value:
            errors.append(f"coverage_summary_mismatch:{key}")

    boundaries = artifact.get("claim_boundaries")
    if not isinstance(boundaries, Mapping) or any(value is not False for value in boundaries.values()):
        errors.append("claim_boundaries_invalid")
    _walk_forbidden(artifact, "$", errors)

    deterministic = False
    try:
        rebuilt = builder.build_artifact(m1_graph, m2_consumer, cp07b_overlay)
        deterministic = builder._digest(rebuilt) == builder._digest(artifact)
        if not deterministic:
            errors.append("deterministic_rebuild_mismatch")
    except (builder.SemanticBridgeError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"deterministic_rebuild_failed:{exc}")

    return {
        "task_id": builder.TASK_ID,
        "validator_id": VALIDATOR_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": builder.PASS_STATUS if not errors else "FAIL_CP07F_R3C_KET_AUTHORITY_SEMANTIC_BRIDGE",
        "error_count": len(errors),
        "errors": errors,
        "deterministic_rebuild_matches": deterministic,
        "coverage_summary": dict(summary),
        "private_payload_text_absent": not any(error.startswith("private_content_key_forbidden") for error in errors),
        "hard_graph_unchanged": summary.get("new_hard_prerequisite_edge_count") == 0,
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILED",
        "next_short_step": builder.NEXT_SHORT_STEP,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--m1-graph", type=Path, required=True)
    parser.add_argument("--m2-consumer", type=Path, required=True)
    parser.add_argument("--cp07b-overlay", type=Path, required=True)
    args = parser.parse_args(argv)
    report = validate_artifact(
        _read(args.artifact),
        m1_graph=_read(args.m1_graph),
        m2_consumer=_read(args.m2_consumer),
        cp07b_overlay=_read(args.cp07b_overlay),
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["validation_status"] == builder.PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
