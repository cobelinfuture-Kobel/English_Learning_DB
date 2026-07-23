#!/usr/bin/env python3
"""Validate the CP07F-R3C semantic lesson composition."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp07r3c_semantic_lesson_composition as builder  # noqa: E402
from ulga.builders import cp07c_unified_m4_lesson_composition_impl as cp07c  # noqa: E402
from ulga.builders import build_a1fs_v1_m4_lesson_planner_selection_a2_lock as m4  # noqa: E402

VALIDATOR_ID = "validate_a1fs_v1_cp07r3c_semantic_lesson_composition"
SCHEMA_VERSION = "a1fs.v1.cp07f.r3c.semantic_lesson_composition_validation.v1"


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def validate_artifact(
    artifact: Mapping[str, Any],
    *,
    m4_plan: Mapping[str, Any],
    m2_consumer: Mapping[str, Any],
    m1_graph: Mapping[str, Any],
    cp07a_index: Mapping[str, Any],
    cp07b_overlay: Mapping[str, Any],
    semantic_bridge: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if artifact.get("task_id") != m4.TASK_ID or artifact.get("validation_status") != m4.STATUS:
        errors.append("m4_backward_compatible_identity_invalid")
    if artifact.get("cp07c_task_id") != cp07c.TASK_ID or artifact.get("cp07c_validation_status") != cp07c.PASS_STATUS:
        errors.append("cp07c_backward_compatible_contract_invalid")
    if artifact.get("cp07r3c_task_id") != builder.TASK_ID:
        errors.append("cp07r3c_task_id_invalid")
    if artifact.get("cp07r3c_schema_version") != builder.SCHEMA_VERSION:
        errors.append("cp07r3c_schema_version_invalid")
    if artifact.get("cp07r3c_validation_status") != builder.PASS_STATUS:
        errors.append("cp07r3c_validation_status_invalid")
    if artifact.get("stop_reason") != "NONE" or artifact.get("errors") != []:
        errors.append("artifact_not_passed")
    if artifact.get("next_short_step") != builder.NEXT_SHORT_STEP:
        errors.append("next_short_step_invalid")
    if artifact.get("plan_id") != m4_plan.get("plan_id") or artifact.get("learner_id") != m4_plan.get("learner_id"):
        errors.append("m4_plan_identity_changed")
    if artifact.get("selected_lesson") != m4_plan.get("selected_lesson"):
        errors.append("m4_selected_lesson_changed")
    if artifact.get("plan_status") != m4_plan.get("plan_status"):
        errors.append("m4_plan_status_changed")
    if artifact.get("a2_payload_included") is not False or artifact.get("a2_session_started") is not False:
        errors.append("a2_payload_or_session_detected")

    expected_source_identity = {
        "m4_plan_sha256": cp07c._digest(m4_plan),
        "m2_consumer_sha256": cp07c._digest(m2_consumer),
        "m1_hard_graph_sha256": cp07c._digest(m1_graph),
        "cp07a_runtime_index_sha256": cp07c._digest(cp07a_index),
        "cp07b_instructional_overlay_sha256": cp07c._digest(cp07b_overlay),
        "cp07r3c_semantic_bridge_sha256": cp07c._digest(semantic_bridge),
    }
    if artifact.get("source_identity") != expected_source_identity:
        errors.append("source_identity_mismatch")

    selected = artifact.get("selected_lesson")
    composition = artifact.get("unified_lesson_composition")
    if not isinstance(selected, Mapping) or not isinstance(composition, Mapping):
        errors.append("selected_lesson_or_composition_missing")
        selected, composition = {}, {}
    if composition.get("selected_lesson_id") != selected.get("lesson_id"):
        errors.append("composition_selected_lesson_drift")
    if composition.get("selected_skill") != selected.get("skill"):
        errors.append("composition_selected_skill_drift")
    expected_level = str(selected.get("level") or "").upper().replace("+", "_PLUS")
    if composition.get("selected_level") != expected_level:
        errors.append("composition_selected_level_drift")
    if composition.get("hard_selection_preserved") is not True:
        errors.append("hard_selection_preservation_invalid")
    if composition.get("requirement_node_ids") != selected.get("requirement_node_ids"):
        errors.append("requirement_node_binding_drift")

    semantic_rows = [
        row for row in semantic_bridge.get("lesson_semantic_bridges", [])
        if isinstance(row, Mapping) and row.get("lesson_id") == selected.get("lesson_id")
    ]
    if len(semantic_rows) != 1:
        errors.append("semantic_bridge_selected_lesson_not_unique")
        semantic_row: Mapping[str, Any] = {}
    else:
        semantic_row = semantic_rows[0]
    if semantic_row.get("resolution_status") != "RESOLVED":
        errors.append("semantic_bridge_selected_lesson_unresolved")
    if composition.get("semantic_anchor_mode") != semantic_row.get("anchor_mode"):
        errors.append("semantic_anchor_mode_drift")
    grammar_ids = composition.get("bridged_grammar_unit_ids")
    if not isinstance(grammar_ids, list) or not grammar_ids or len(grammar_ids) > cp07c.MAX_BRIDGED_GRAMMAR_UNITS:
        errors.append("bridged_grammar_unit_count_invalid")
        grammar_ids = []
    if not set(grammar_ids) <= set(semantic_row.get("grammar_unit_ids", [])):
        errors.append("semantic_bridge_grammar_target_drift")
    bridge_rows = composition.get("canonical_bridge_evidence")
    if not isinstance(bridge_rows, list) or {row.get("grammar_unit_id") for row in bridge_rows if isinstance(row, Mapping)} != set(grammar_ids):
        errors.append("canonical_bridge_evidence_set_mismatch")
        bridge_rows = []
    for row in bridge_rows:
        if not row.get("authority_evidence"):
            errors.append(f"canonical_bridge_authority_evidence_missing:{row.get('grammar_unit_id')}")
        if row.get("anchor_mode") != semantic_row.get("anchor_mode"):
            errors.append(f"canonical_bridge_anchor_mode_drift:{row.get('grammar_unit_id')}")

    items = composition.get("composition_items")
    if not isinstance(items, list) or not items:
        errors.append("composition_item_list_required")
        items = []
    identities: set[str] = set()
    source_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    allowed_count = 0
    for row in items:
        if not isinstance(row, Mapping):
            errors.append("composition_item_invalid")
            continue
        identity = str(row.get("composition_item_id") or "")
        if not identity or identity in identities:
            errors.append(f"composition_item_identity_missing_or_duplicate:{identity}")
        identities.add(identity)
        source_kind = str(row.get("source_kind") or "")
        role = str(row.get("instructional_role") or "")
        if source_kind not in {"KET_ASSET_BODY", "RAZ_ACTIVITY_BINDING", "M11B_REVIEWED_ACTIVITY"}:
            errors.append(f"composition_source_kind_invalid:{identity}")
        if row.get("skill") != selected.get("skill"):
            errors.append(f"composition_skill_drift:{identity}")
        if not isinstance(row.get("source_lineage"), Mapping) or not isinstance(row.get("response_contract_ref"), Mapping):
            errors.append(f"composition_lineage_or_response_ref_missing:{identity}")
        if source_kind == "KET_ASSET_BODY":
            if role != "STRUCTURED_KET_ASSET" or row.get("runtime_readiness") != "QUERYABLE_PRIVATE_KET_ASSET":
                errors.append(f"ket_composition_contract_invalid:{identity}")
        elif source_kind == "RAZ_ACTIVITY_BINDING":
            if role not in cp07c.CONTEXT_ROLES:
                errors.append(f"raz_composition_role_invalid:{identity}")
            if row.get("grammar_unit_id") not in grammar_ids:
                errors.append(f"raz_composition_grammar_bridge_invalid:{identity}")
        else:
            if role != "CHECKPOINT" or row.get("grammar_unit_id") not in grammar_ids:
                errors.append(f"m11b_composition_contract_invalid:{identity}")
        if row.get("delivery_allowed_now") is True:
            allowed_count += 1
        source_counts[source_kind] += 1
        role_counts[role] += 1
    if source_counts["KET_ASSET_BODY"] < 1:
        errors.append("ket_structured_asset_missing")
    if source_counts["RAZ_ACTIVITY_BINDING"] < 1 or role_counts["FOCUS"] != 1:
        errors.append("raz_focus_context_missing_or_duplicate")
    if any(role_counts[role] > 1 for role in cp07c.CONTEXT_ROLES):
        errors.append("context_role_selected_more_than_once")

    summary = composition.get("coverage_summary")
    if not isinstance(summary, Mapping):
        errors.append("composition_coverage_summary_required")
        summary = {}
    expected_summary = {
        "composition_item_count": len(items),
        "source_kind_counts": dict(sorted(source_counts.items())),
        "instructional_role_counts": dict(sorted(role_counts.items())),
        "ket_asset_count": source_counts["KET_ASSET_BODY"],
        "raz_contextual_activity_count": source_counts["RAZ_ACTIVITY_BINDING"],
        "m11b_checkpoint_count": source_counts["M11B_REVIEWED_ACTIVITY"],
        "bridged_grammar_unit_count": len(grammar_ids),
        "delivery_allowed_now_count": allowed_count,
        "blocked_dependency_count": len(items) - allowed_count,
    }
    for key, value in expected_summary.items():
        if summary.get(key) != value:
            errors.append(f"composition_coverage_summary_mismatch:{key}")

    gate = composition.get("consumer_gate")
    if not isinstance(gate, Mapping):
        errors.append("consumer_gate_required")
    else:
        if gate.get("m4_selected_lesson_unchanged") is not True or gate.get("m1_hard_prerequisite_graph_unchanged") is not True:
            errors.append("hard_selection_or_graph_gate_invalid")
        if gate.get("m5_existing_ket_renderer_backward_compatible") is not True:
            errors.append("m5_backward_compatibility_gate_invalid")
        if gate.get("m5_contextual_activity_rendering_completed") is not False or gate.get("m6_response_capture_completed") is not False:
            errors.append("premature_runtime_claim")
        if gate.get("a2_payload_included") is not False:
            errors.append("consumer_gate_a2_boundary_invalid")

    boundaries = artifact.get("claim_boundaries")
    if not isinstance(boundaries, Mapping) or any(value is not False for value in boundaries.values()):
        errors.append("claim_boundaries_invalid")
    try:
        cp07c._walk_forbidden(artifact)
    except cp07c.CP07CBuildError as exc:
        errors.append(str(exc))

    deterministic = False
    try:
        rebuilt = builder.build_composition(
            m4_plan, m2_consumer, m1_graph, cp07a_index, cp07b_overlay, semantic_bridge
        )
        deterministic = cp07c._digest(rebuilt) == cp07c._digest(artifact)
        if not deterministic:
            errors.append("deterministic_rebuild_mismatch")
    except (builder.SemanticCompositionError, cp07c.CP07CBuildError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"deterministic_rebuild_failed:{exc}")

    return {
        "task_id": builder.TASK_ID,
        "validator_id": VALIDATOR_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": builder.PASS_STATUS if not errors else "FAIL_CP07F_R3C_SEMANTIC_LESSON_COMPOSITION",
        "error_count": len(errors),
        "errors": errors,
        "deterministic_rebuild_matches": deterministic,
        "m4_selected_lesson_unchanged": artifact.get("selected_lesson") == m4_plan.get("selected_lesson"),
        "cp07d_contract_compatible": (
            artifact.get("cp07c_task_id") == cp07c.TASK_ID
            and artifact.get("cp07c_validation_status") == cp07c.PASS_STATUS
            and source_counts["RAZ_ACTIVITY_BINDING"] > 0
        ),
        "coverage_summary": dict(summary),
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILED",
        "next_short_step": builder.NEXT_SHORT_STEP,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--m4-plan", type=Path, required=True)
    parser.add_argument("--m2-consumer", type=Path, required=True)
    parser.add_argument("--m1-graph", type=Path, required=True)
    parser.add_argument("--cp07a-index", type=Path, required=True)
    parser.add_argument("--cp07b-overlay", type=Path, required=True)
    parser.add_argument("--semantic-bridge", type=Path, required=True)
    args = parser.parse_args(argv)
    report = validate_artifact(
        _read(args.artifact),
        m4_plan=_read(args.m4_plan), m2_consumer=_read(args.m2_consumer),
        m1_graph=_read(args.m1_graph), cp07a_index=_read(args.cp07a_index),
        cp07b_overlay=_read(args.cp07b_overlay), semantic_bridge=_read(args.semantic_bridge),
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["validation_status"] == builder.PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
