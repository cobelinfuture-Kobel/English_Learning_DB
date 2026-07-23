#!/usr/bin/env python3
"""Compose a CP07C-compatible lesson through the R3C semantic bridge.

M4 remains the sole hard lesson selector.  This adapter accepts root lessons
with no prerequisite nodes only when the selected lesson's own Asset Body
Authority has an exact semantic target in the R3C bridge.  Requirement-bound
lessons must have at least one exact M1-coverage/M2-payload semantic bridge.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp07c_unified_m4_lesson_composition as cp07c  # noqa: E402
from ulga.builders import build_a1fs_v1_cp07r3c_ket_authority_semantic_bridge as semantic_bridge  # noqa: E402
from ulga.builders import build_a1fs_v1_m4_lesson_planner_selection_a2_lock as m4  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Metadata-only CP07C-compatible lesson composition using an exact M1-coverage/M2-Authority/CP07B semantic bridge; no private payload, prompt, answer, learner response, hard graph mutation, mastery, retention, or A2 payload is produced."

TASK_ID = "A1FS-V1-CP07F-R3C_SemanticLessonComposition"
SCHEMA_VERSION = "a1fs.v1.cp07f.r3c.semantic_lesson_composition.v1"
PASS_STATUS = "PASS_CP07F_R3C_SEMANTIC_LESSON_COMPOSITION_READY"
NEXT_SHORT_STEP = "A1FS-V1-CP07F-R4_FourSkillCP07DPrivateDeliveryConsumerBuild"

DEFAULT_M4_PLAN = cp07c.DEFAULT_M4_PLAN
DEFAULT_M2 = cp07c.DEFAULT_M2
DEFAULT_M1 = cp07c.DEFAULT_M1
DEFAULT_CP07A = cp07c.DEFAULT_CP07A
DEFAULT_CP07B = cp07c.DEFAULT_CP07B
DEFAULT_SEMANTIC_BRIDGE = semantic_bridge.DEFAULT_OUTPUT
DEFAULT_OUTPUT = REPO_ROOT / ".local/a1fs_v1/cp07r3c/semantic_lesson_composition.safe.json"
DEFAULT_REPORT = REPO_ROOT / ".local/a1fs_v1/cp07r3c/semantic_lesson_composition.validation.json"

SKILLS = cp07c.SKILLS
SUPPORTED_PLAN_STATUSES = cp07c.SUPPORTED_PLAN_STATUSES


class SemanticCompositionError(ValueError):
    """Fail-closed semantic bridge or CP07C-compatible composition error."""


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SemanticCompositionError(f"json_object_required:{path}")
    return value


def _verify_plan(plan: Mapping[str, Any]) -> Mapping[str, Any]:
    if plan.get("task_id") != m4.TASK_ID or plan.get("validation_status") != m4.STATUS:
        raise SemanticCompositionError("m4_plan_contract_invalid")
    if plan.get("plan_status") not in SUPPORTED_PLAN_STATUSES:
        raise SemanticCompositionError("m4_plan_not_composable")
    if plan.get("a2_payload_included") is not False or plan.get("a2_session_started") is not False:
        raise SemanticCompositionError("m4_a2_boundary_invalid")
    lock = plan.get("a2_lock")
    if not isinstance(lock, Mapping) or lock.get("a2_payload_access_granted") is not False or lock.get("a2_session_start_granted") is not False:
        raise SemanticCompositionError("m4_a2_lock_contract_invalid")
    lesson = plan.get("selected_lesson")
    if not isinstance(lesson, Mapping):
        raise SemanticCompositionError("m4_selected_lesson_required")
    if lesson.get("skill") not in SKILLS:
        raise SemanticCompositionError("m4_selected_skill_invalid")
    cp07c._normalize_level(lesson.get("level"))
    if not str(lesson.get("lesson_id") or "") or not str(lesson.get("lesson_node_id") or ""):
        raise SemanticCompositionError("m4_selected_lesson_identity_missing")
    requirements = lesson.get("requirement_node_ids")
    if not isinstance(requirements, list):
        raise SemanticCompositionError("m4_selected_lesson_requirement_nodes_not_list")
    return lesson


def _verify_semantic_bridge(
    bridge: Mapping[str, Any],
    *,
    m1_graph: Mapping[str, Any],
    m2_consumer: Mapping[str, Any],
    cp07b_overlay: Mapping[str, Any],
    lesson: Mapping[str, Any],
) -> Mapping[str, Any]:
    if bridge.get("task_id") != semantic_bridge.TASK_ID or bridge.get("schema_version") != semantic_bridge.SCHEMA_VERSION:
        raise SemanticCompositionError("semantic_bridge_contract_invalid")
    if bridge.get("validation_status") != semantic_bridge.PASS_STATUS or bridge.get("stop_reason") != "NONE" or bridge.get("errors") != []:
        raise SemanticCompositionError("semantic_bridge_not_passed")
    expected_identity = {
        "m1_hard_graph_sha256": semantic_bridge._digest(m1_graph),
        "m2_consumer_sha256": semantic_bridge._digest(m2_consumer),
        "cp07b_instructional_overlay_sha256": semantic_bridge._digest(cp07b_overlay),
    }
    if bridge.get("source_identity") != expected_identity:
        raise SemanticCompositionError("semantic_bridge_source_identity_mismatch")
    authority = bridge.get("authority_contract")
    if not isinstance(authority, Mapping):
        raise SemanticCompositionError("semantic_bridge_authority_contract_missing")
    if authority.get("fuzzy_matching_allowed") is not False or authority.get("hard_graph_mutation_allowed") is not False:
        raise SemanticCompositionError("semantic_bridge_authority_boundary_invalid")
    if authority.get("a2_a2plus_status") != "LOCKED":
        raise SemanticCompositionError("semantic_bridge_a2_lock_invalid")

    matches = [
        row for row in bridge.get("lesson_semantic_bridges", [])
        if isinstance(row, Mapping) and row.get("lesson_id") == lesson.get("lesson_id")
    ]
    if len(matches) != 1:
        raise SemanticCompositionError("semantic_bridge_selected_lesson_not_unique")
    row = matches[0]
    for key in ("lesson_node_id", "skill", "level", "requirement_node_ids"):
        if row.get(key) != lesson.get(key):
            raise SemanticCompositionError(f"semantic_bridge_m4_lesson_drift:{key}")
    if row.get("resolution_status") != "RESOLVED" or not row.get("grammar_unit_ids") or not row.get("authority_evidence"):
        raise SemanticCompositionError("semantic_bridge_selected_lesson_unresolved")
    requirements = list(lesson.get("requirement_node_ids", []))
    if requirements:
        if row.get("anchor_mode") != "REQUIREMENT_ASSET_AUTHORITY":
            raise SemanticCompositionError("semantic_bridge_requirement_anchor_invalid")
        matched = set(row.get("matched_requirement_node_ids", []))
        if not matched or not matched <= set(requirements):
            raise SemanticCompositionError("semantic_bridge_requirement_match_invalid")
    else:
        if row.get("anchor_mode") != "ROOT_LESSON_ASSET_AUTHORITY":
            raise SemanticCompositionError("semantic_bridge_root_anchor_invalid")
        if row.get("matched_requirement_node_ids") != []:
            raise SemanticCompositionError("semantic_bridge_root_requirement_match_invalid")
    return row


def build_composition(
    m4_plan: Mapping[str, Any],
    m2_consumer: Mapping[str, Any],
    m1_graph: Mapping[str, Any],
    cp07a_index: Mapping[str, Any],
    cp07b_overlay: Mapping[str, Any],
    bridge: Mapping[str, Any],
) -> dict[str, Any]:
    lesson = _verify_plan(m4_plan)
    catalog = cp07c._verify_m2(m2_consumer, lesson)
    cp07c._verify_m1(m1_graph, lesson)
    activity_rows = cp07c._verify_cp07a(cp07a_index, m2_consumer)
    cp07c._verify_cp07b(cp07b_overlay, m1_graph)
    bridge_row = _verify_semantic_bridge(
        bridge,
        m1_graph=m1_graph,
        m2_consumer=m2_consumer,
        cp07b_overlay=cp07b_overlay,
        lesson=lesson,
    )

    lesson_id = str(lesson["lesson_id"])
    skill = str(lesson["skill"])
    ket_rows = [
        row for row in activity_rows
        if isinstance(row, Mapping)
        and row.get("source_kind") == "KET_ASSET_BODY"
        and row.get("curriculum_binding", {}).get("ket_lesson_id") == lesson_id
    ]
    ket_rows.sort(key=lambda row: str(row.get("source_lineage", {}).get("m2_asset_key") or ""))
    ket_asset_keys = [str(row.get("source_lineage", {}).get("m2_asset_key") or "") for row in ket_rows]
    if set(ket_asset_keys) != set(catalog.get("asset_keys", [])) or len(ket_asset_keys) != len(set(ket_asset_keys)):
        raise SemanticCompositionError("KET_ASSET_BUNDLE_NOT_RECONCILED")
    ket_items = [
        {
            "composition_item_id": str(row["runtime_activity_id"]),
            "source_kind": "KET_ASSET_BODY",
            "skill": skill,
            "instructional_role": "STRUCTURED_KET_ASSET",
            "ket_role_refs": [role for role in row.get("instructional_roles", []) if role != "FOCUS"],
            "runtime_readiness": str(row["runtime_readiness"]),
            "delivery_allowed_now": row["runtime_readiness"] == "QUERYABLE_PRIVATE_KET_ASSET",
            "source_lineage": copy.deepcopy(row["source_lineage"]),
            "response_contract_ref": copy.deepcopy(row["response_contract_ref"]),
        }
        for row in ket_rows
    ]
    if not ket_items:
        raise SemanticCompositionError("KET_STRUCTURED_ASSET_REQUIRED")

    grammar_ids = list(bridge_row["grammar_unit_ids"])[: cp07c.MAX_BRIDGED_GRAMMAR_UNITS]
    rank_by_grammar = {
        str(row.get("target_id") or ""): int(row.get("soft_order_rank") or 10**9)
        for row in cp07b_overlay.get("canonical_target_sequences", [])
        if isinstance(row, Mapping) and row.get("target_type") == "GRAMMAR_UNIT"
    }
    grammar_ids.sort(key=lambda grammar_id: (rank_by_grammar.get(grammar_id, 10**9), grammar_id))
    bridge_evidence = [
        {
            "grammar_unit_id": grammar_id,
            "soft_order_rank": rank_by_grammar.get(grammar_id),
            "anchor_mode": str(bridge_row["anchor_mode"]),
            "matched_requirement_node_ids": list(bridge_row.get("matched_requirement_node_ids", [])),
            "authority_evidence": [
                copy.deepcopy(item)
                for item in bridge_row.get("authority_evidence", [])
                if grammar_id in item.get("grammar_unit_ids", [])
            ],
        }
        for grammar_id in grammar_ids
    ]

    raz_items, missing_context_roles = cp07c._select_contextual_items(
        rows=activity_rows, skill=skill, grammar_ids=grammar_ids, rank_by_grammar=rank_by_grammar
    )
    m11b_item, m11b_gap = cp07c._select_m11b_checkpoint(
        rows=activity_rows, skill=skill, grammar_ids=grammar_ids, rank_by_grammar=rank_by_grammar
    )
    composition_items = ket_items + raz_items + ([m11b_item] if m11b_item else [])
    delivery_allowed_count = sum(bool(row["delivery_allowed_now"]) for row in composition_items)
    blocked_dependency_count = len(composition_items) - delivery_allowed_count
    source_counts = Counter(row["source_kind"] for row in composition_items)
    role_counts = Counter(row["instructional_role"] for row in composition_items)

    enriched = copy.deepcopy(dict(m4_plan))
    enriched["cp07c_task_id"] = cp07c.TASK_ID
    enriched["cp07c_schema_version"] = cp07c.SCHEMA_VERSION
    enriched["cp07c_validation_status"] = cp07c.PASS_STATUS
    enriched["cp07r3c_task_id"] = TASK_ID
    enriched["cp07r3c_schema_version"] = SCHEMA_VERSION
    enriched["cp07r3c_validation_status"] = PASS_STATUS
    enriched["source_m4_next_short_step"] = m4_plan.get("next_short_step")
    enriched["source_identity"] = {
        "m4_plan_sha256": cp07c._digest(m4_plan),
        "m2_consumer_sha256": cp07c._digest(m2_consumer),
        "m1_hard_graph_sha256": cp07c._digest(m1_graph),
        "cp07a_runtime_index_sha256": cp07c._digest(cp07a_index),
        "cp07b_instructional_overlay_sha256": cp07c._digest(cp07b_overlay),
        "cp07r3c_semantic_bridge_sha256": cp07c._digest(bridge),
    }
    enriched["unified_lesson_composition"] = {
        "composition_id": f"A1FS_CP07C:{m4_plan['plan_id']}",
        "selected_lesson_id": lesson_id,
        "selected_skill": skill,
        "selected_level": cp07c._normalize_level(lesson["level"]),
        "hard_selection_preserved": True,
        "requirement_node_ids": list(lesson["requirement_node_ids"]),
        "semantic_anchor_mode": str(bridge_row["anchor_mode"]),
        "bridged_grammar_unit_ids": grammar_ids,
        "canonical_bridge_evidence": bridge_evidence,
        "composition_items": composition_items,
        "composition_gaps": {
            "missing_context_roles": missing_context_roles,
            "m11b_checkpoint_gap": m11b_gap,
        },
        "coverage_summary": {
            "composition_item_count": len(composition_items),
            "source_kind_counts": dict(sorted(source_counts.items())),
            "instructional_role_counts": dict(sorted(role_counts.items())),
            "ket_asset_count": len(ket_items),
            "raz_contextual_activity_count": len(raz_items),
            "m11b_checkpoint_count": 1 if m11b_item else 0,
            "bridged_grammar_unit_count": len(grammar_ids),
            "delivery_allowed_now_count": delivery_allowed_count,
            "blocked_dependency_count": blocked_dependency_count,
        },
        "consumer_gate": {
            "m4_selected_lesson_unchanged": True,
            "m1_hard_prerequisite_graph_unchanged": True,
            "m5_existing_ket_renderer_backward_compatible": True,
            "m5_contextual_activity_rendering_completed": False,
            "m6_response_capture_completed": False,
            "a2_payload_included": False,
        },
    }
    enriched["claim_boundaries"] = {
        "private_content_included": False,
        "manual_opaque_id_mapping_included": False,
        "m4_hard_selection_changed": False,
        "m1_hard_graph_changed": False,
        "m5_contextual_rendering_claimed": False,
        "m6_attempt_claimed": False,
        "mastery_or_retention_claimed": False,
        "a2_a2plus_in_scope": False,
    }
    enriched["errors"] = []
    enriched["stop_reason"] = "NONE"
    enriched["next_short_step"] = NEXT_SHORT_STEP
    cp07c._walk_forbidden(enriched)
    return enriched


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m4-plan", type=Path, default=DEFAULT_M4_PLAN)
    parser.add_argument("--m2-consumer", type=Path, default=DEFAULT_M2)
    parser.add_argument("--m1-graph", type=Path, default=DEFAULT_M1)
    parser.add_argument("--cp07a-index", type=Path, default=DEFAULT_CP07A)
    parser.add_argument("--cp07b-overlay", type=Path, default=DEFAULT_CP07B)
    parser.add_argument("--semantic-bridge", type=Path, default=DEFAULT_SEMANTIC_BRIDGE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        inputs = (
            _read(args.m4_plan), _read(args.m2_consumer), _read(args.m1_graph),
            _read(args.cp07a_index), _read(args.cp07b_overlay), _read(args.semantic_bridge),
        )
        artifact = build_composition(*inputs)
        from ulga.validators import validate_a1fs_v1_cp07r3c_semantic_lesson_composition as validator
        report = validator.validate_artifact(
            artifact,
            m4_plan=inputs[0], m2_consumer=inputs[1], m1_graph=inputs[2],
            cp07a_index=inputs[3], cp07b_overlay=inputs[4], semantic_bridge=inputs[5],
        )
        cp07c._write_atomic(args.output, artifact)
        cp07c._write_atomic(args.report, report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["validation_status"] == PASS_STATUS else 1
    except (SemanticCompositionError, cp07c.CP07CBuildError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
