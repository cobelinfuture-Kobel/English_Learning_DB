#!/usr/bin/env python3
"""Validate the CP07F-R3F reference-aware optional-context composition."""
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

from ulga.builders import build_a1fs_v1_cp07r3f_reference_aware_optional_context_lesson_composition as builder  # noqa: E402
from ulga.builders import build_a1fs_v1_m4_lesson_planner_selection_a2_lock as m4  # noqa: E402
from ulga.builders import cp07c_unified_m4_lesson_composition_impl as cp07c  # noqa: E402

VALIDATOR_ID = "validate_a1fs_v1_cp07r3f_reference_aware_optional_context_lesson_composition"
SCHEMA_VERSION = "a1fs.v1.cp07f.r3f.reference_aware_optional_context_lesson_composition_validation.v1"


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
    r3e_overlay: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if artifact.get("task_id") != m4.TASK_ID or artifact.get("validation_status") != m4.STATUS:
        errors.append("m4_backward_compatible_identity_invalid")
    if artifact.get("cp07r3f_task_id") != builder.TASK_ID:
        errors.append("cp07r3f_task_id_invalid")
    if artifact.get("cp07r3f_schema_version") != builder.SCHEMA_VERSION:
        errors.append("cp07r3f_schema_version_invalid")
    if artifact.get("cp07r3f_validation_status") != builder.PASS_STATUS:
        errors.append("cp07r3f_validation_status_invalid")
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
        "r3e_reference_overlay_sha256": cp07c._digest(r3e_overlay),
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

    reference_rows = [
        row for row in r3e_overlay.get("lesson_instructional_references", [])
        if isinstance(row, Mapping) and row.get("lesson_id") == selected.get("lesson_id")
    ]
    if len(reference_rows) != 1:
        errors.append("r3e_selected_lesson_reference_not_unique")
        reference_row: Mapping[str, Any] = {}
    else:
        reference_row = reference_rows[0]
    references = composition.get("instructional_references")
    if references != reference_row.get("instructional_references"):
        errors.append("instructional_reference_drift")
        references = []
    if composition.get("instructional_reference_status") != reference_row.get("reference_status"):
        errors.append("instructional_reference_status_drift")
    expected_grammar_ids = builder._grammar_targets(reference_row)
    grammar_ids = composition.get("bridged_grammar_unit_ids")
    if grammar_ids != expected_grammar_ids:
        errors.append("reference_grammar_target_drift")
        grammar_ids = []

    items = composition.get("composition_items")
    if not isinstance(items, list) or not items:
        errors.append("composition_item_list_required")
        items = []
    identities: set[str] = set()
    source_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    allowed_count = 0
    raz_roles: set[str] = set()
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
            if role not in builder.CONTEXT_ROLES:
                errors.append(f"raz_composition_role_invalid:{identity}")
            if role in raz_roles:
                errors.append(f"raz_composition_role_duplicate:{role}")
            raz_roles.add(role)
            if row.get("grammar_unit_id") not in grammar_ids:
                errors.append(f"raz_composition_grammar_bridge_invalid:{identity}")
        elif source_kind == "M11B_REVIEWED_ACTIVITY":
            if role != "CHECKPOINT" or row.get("grammar_unit_id") not in grammar_ids:
                errors.append(f"m11b_composition_contract_invalid:{identity}")
        if row.get("delivery_allowed_now") is True:
            allowed_count += 1
        source_counts[source_kind] += 1
        role_counts[role] += 1

    try:
        lesson = builder._verify_plan(m4_plan)
        catalog = cp07c._verify_m2(m2_consumer, lesson)
        cp07c._verify_m1(m1_graph, lesson)
        activity_rows = cp07c._verify_cp07a(cp07a_index, m2_consumer)
        expected_ket = builder._ket_items(
            activity_rows=activity_rows,
            catalog=catalog,
            lesson_id=str(lesson["lesson_id"]),
            skill=str(lesson["skill"]),
        )
        expected_ket_ids = {row["composition_item_id"] for row in expected_ket}
        actual_ket_ids = {
            str(row.get("composition_item_id") or "")
            for row in items
            if isinstance(row, Mapping) and row.get("source_kind") == "KET_ASSET_BODY"
        }
        if actual_ket_ids != expected_ket_ids:
            errors.append("ket_asset_bundle_identity_mismatch")
    except (builder.ReferenceAwareCompositionError, cp07c.CP07CBuildError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"ket_asset_bundle_validation_failed:{exc}")

    reference_count = len(references) if isinstance(references, list) else 0
    raz_count = source_counts["RAZ_ACTIVITY_BINDING"]
    m11b_count = source_counts["M11B_REVIEWED_ACTIVITY"]
    if source_counts["KET_ASSET_BODY"] < 1:
        errors.append("ket_structured_asset_missing")
    if reference_count == 0:
        if grammar_ids or raz_count or m11b_count:
            errors.append("unreferenced_lesson_has_reference_dependent_context")
        expected_mode = "KET_ONLY_NO_EXACT_KET99_REFERENCE"
    elif raz_count:
        expected_mode = "KET_WITH_KET99_REFERENCE_AND_OPTIONAL_CONTEXT"
    elif grammar_ids:
        expected_mode = "KET_WITH_KET99_REFERENCE_CONTEXT_UNAVAILABLE"
    else:
        if raz_count or m11b_count:
            errors.append("reference_without_grammar_has_context")
        expected_mode = "KET_WITH_KET99_REFERENCE_NO_GRAMMAR_CONTEXT"
    if composition.get("composition_mode") != expected_mode:
        errors.append("composition_mode_invalid")

    gaps = composition.get("composition_gaps")
    if not isinstance(gaps, Mapping):
        errors.append("composition_gap_contract_missing")
        gaps = {}
    if gaps.get("missing_exact_ket99_reference") is not (reference_count == 0):
        errors.append("missing_reference_gap_invalid")
    if gaps.get("no_exact_grammar_target_from_reference") is not (reference_count > 0 and not grammar_ids):
        errors.append("grammar_reference_gap_invalid")
    missing_roles = gaps.get("missing_context_roles")
    expected_missing_roles = [role for role in builder.CONTEXT_ROLES if role not in raz_roles]
    if missing_roles != expected_missing_roles:
        errors.append("missing_context_roles_invalid")

    summary = composition.get("coverage_summary")
    if not isinstance(summary, Mapping):
        errors.append("composition_coverage_summary_required")
        summary = {}
    expected_summary = {
        "composition_item_count": len(items),
        "source_kind_counts": dict(sorted(source_counts.items())),
        "instructional_role_counts": dict(sorted(role_counts.items())),
        "ket_asset_count": source_counts["KET_ASSET_BODY"],
        "instructional_reference_count": reference_count,
        "raz_contextual_activity_count": raz_count,
        "m11b_checkpoint_count": m11b_count,
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
        required_true = (
            "m4_selected_lesson_unchanged",
            "m1_hard_prerequisite_graph_unchanged",
            "ket_asset_body_required",
            "ket99_reference_optional",
            "raz_context_optional",
            "m11b_checkpoint_optional",
        )
        for key in required_true:
            if gate.get(key) is not True:
                errors.append(f"consumer_gate_true_flag_invalid:{key}")
        if gate.get("missing_reference_blocks_delivery") is not False:
            errors.append("missing_reference_blocks_delivery")
        if gate.get("r4_cp07d_optional_context_consumer_completed") is not False:
            errors.append("premature_r4_cp07d_claim")
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
        rebuilt = builder.build_composition(m4_plan, m2_consumer, m1_graph, cp07a_index, r3e_overlay)
        deterministic = cp07c._digest(rebuilt) == cp07c._digest(artifact)
        if not deterministic:
            errors.append("deterministic_rebuild_mismatch")
    except (builder.ReferenceAwareCompositionError, cp07c.CP07CBuildError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"deterministic_rebuild_failed:{exc}")

    return {
        "task_id": builder.TASK_ID,
        "validator_id": VALIDATOR_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": builder.PASS_STATUS if not errors else "FAIL_CP07F_R3F_REFERENCE_AWARE_OPTIONAL_CONTEXT_LESSON_COMPOSITION",
        "error_count": len(errors),
        "errors": errors,
        "deterministic_rebuild_matches": deterministic,
        "m4_selected_lesson_unchanged": artifact.get("selected_lesson") == m4_plan.get("selected_lesson"),
        "instructional_reference_count": reference_count,
        "ket_asset_count": source_counts["KET_ASSET_BODY"],
        "raz_contextual_activity_count": raz_count,
        "m11b_checkpoint_count": m11b_count,
        "missing_reference_blocks_delivery": False,
        "a2_status": "LOCKED",
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
    parser.add_argument("--r3e-overlay", type=Path, required=True)
    args = parser.parse_args(argv)
    report = validate_artifact(
        _read(args.artifact),
        m4_plan=_read(args.m4_plan),
        m2_consumer=_read(args.m2_consumer),
        m1_graph=_read(args.m1_graph),
        cp07a_index=_read(args.cp07a_index),
        r3e_overlay=_read(args.r3e_overlay),
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["validation_status"] == builder.PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
