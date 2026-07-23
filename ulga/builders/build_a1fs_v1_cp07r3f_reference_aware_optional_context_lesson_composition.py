#!/usr/bin/env python3
"""Compose one M4-selected lesson with optional KET99 and contextual support.

KET Asset Body remains the required lesson body. KET99 teacher transcripts are
optional instructional references. RAZ and M11B context is attached only when
an exact GRAMMAR_UNIT target is present in those references and a matching
CP07A runtime activity exists. Missing references or context never blocks the
selected A1/A1+ KET lesson.
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

from ulga.builders import build_a1fs_v1_cp07r3e_ket99_lesson_instructional_reference_overlay as r3e  # noqa: E402
from ulga.builders import build_a1fs_v1_m4_lesson_planner_selection_a2_lock as m4  # noqa: E402
from ulga.builders import cp07c_unified_m4_lesson_composition_impl as cp07c  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Metadata-only M4 lesson composition over governed KET assets, optional KET99 reference identities, and optional CP07A context identities; no private payload, transcript text, prompt, score, learner response, hard graph mutation, mastery, retention, or A2 payload is produced."

TASK_ID = "A1FS-V1-CP07F-R3F_ReferenceAwareOptionalContextLessonComposition"
SCHEMA_VERSION = "a1fs.v1.cp07f.r3f.reference_aware_optional_context_lesson_composition.v1"
PASS_STATUS = "PASS_CP07F_R3F_REFERENCE_AWARE_OPTIONAL_CONTEXT_LESSON_COMPOSITION_READY"
NEXT_SHORT_STEP = "A1FS-V1-CP07F-R4_FourSkillCP07DPrivateDeliveryConsumerBuild"

DEFAULT_M4_PLAN = cp07c.DEFAULT_M4_PLAN
DEFAULT_M2 = cp07c.DEFAULT_M2
DEFAULT_M1 = cp07c.DEFAULT_M1
DEFAULT_CP07A = cp07c.DEFAULT_CP07A
DEFAULT_R3E = r3e.DEFAULT_OUTPUT
DEFAULT_OUTPUT = REPO_ROOT / ".local/a1fs_v1/cp07r3f/reference_aware_optional_context_lesson_composition.safe.json"
DEFAULT_REPORT = REPO_ROOT / ".local/a1fs_v1/cp07r3f/reference_aware_optional_context_lesson_composition.validation.json"

SUPPORTED_PLAN_STATUSES = cp07c.SUPPORTED_PLAN_STATUSES
SKILLS = cp07c.SKILLS
CONTEXT_ROLES = cp07c.CONTEXT_ROLES
MAX_BRIDGED_GRAMMAR_UNITS = cp07c.MAX_BRIDGED_GRAMMAR_UNITS


class ReferenceAwareCompositionError(ValueError):
    """Fail-closed source, identity, or composition contract error."""


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReferenceAwareCompositionError(f"json_object_required:{path}")
    return value


def _verify_plan(plan: Mapping[str, Any]) -> Mapping[str, Any]:
    if plan.get("task_id") != m4.TASK_ID or plan.get("validation_status") != m4.STATUS:
        raise ReferenceAwareCompositionError("m4_plan_contract_invalid")
    if plan.get("plan_status") not in SUPPORTED_PLAN_STATUSES:
        raise ReferenceAwareCompositionError("m4_plan_not_composable")
    if plan.get("a2_payload_included") is not False or plan.get("a2_session_started") is not False:
        raise ReferenceAwareCompositionError("m4_a2_boundary_invalid")
    lock = plan.get("a2_lock")
    if not isinstance(lock, Mapping):
        raise ReferenceAwareCompositionError("m4_a2_lock_missing")
    if lock.get("a2_payload_access_granted") is not False or lock.get("a2_session_start_granted") is not False:
        raise ReferenceAwareCompositionError("m4_a2_lock_contract_invalid")
    lesson = plan.get("selected_lesson")
    if not isinstance(lesson, Mapping):
        raise ReferenceAwareCompositionError("m4_selected_lesson_required")
    if lesson.get("skill") not in SKILLS:
        raise ReferenceAwareCompositionError("m4_selected_skill_invalid")
    cp07c._normalize_level(lesson.get("level"))
    if not str(lesson.get("lesson_id") or "") or not str(lesson.get("lesson_node_id") or ""):
        raise ReferenceAwareCompositionError("m4_selected_lesson_identity_missing")
    if not isinstance(lesson.get("requirement_node_ids"), list):
        raise ReferenceAwareCompositionError("m4_selected_lesson_requirement_nodes_not_list")
    return lesson


def _verify_reference_overlay(
    overlay: Mapping[str, Any],
    *,
    m1_graph: Mapping[str, Any],
    m2_consumer: Mapping[str, Any],
    lesson: Mapping[str, Any],
) -> Mapping[str, Any]:
    if overlay.get("task_id") != r3e.TASK_ID or overlay.get("schema_version") != r3e.SCHEMA_VERSION:
        raise ReferenceAwareCompositionError("r3e_contract_invalid")
    if overlay.get("validation_status") != r3e.PASS_STATUS or overlay.get("stop_reason") != "NONE" or overlay.get("errors") != []:
        raise ReferenceAwareCompositionError("r3e_not_passed")
    source_identity = overlay.get("source_identity")
    if not isinstance(source_identity, Mapping):
        raise ReferenceAwareCompositionError("r3e_source_identity_missing")
    if source_identity.get("m1_hard_graph_sha256") != cp07c._digest(m1_graph):
        raise ReferenceAwareCompositionError("r3e_m1_binding_invalid")
    if source_identity.get("m2_consumer_sha256") != cp07c._digest(m2_consumer):
        raise ReferenceAwareCompositionError("r3e_m2_binding_invalid")
    authority = overlay.get("authority_contract")
    if not isinstance(authority, Mapping):
        raise ReferenceAwareCompositionError("r3e_authority_contract_missing")
    if authority.get("delivery_block_on_missing_reference_allowed") is not False:
        raise ReferenceAwareCompositionError("r3e_missing_reference_boundary_invalid")
    if authority.get("hard_graph_mutation_allowed") is not False or authority.get("hard_lesson_selection_allowed") is not False:
        raise ReferenceAwareCompositionError("r3e_hard_authority_boundary_invalid")
    if authority.get("fuzzy_matching_allowed") is not False or authority.get("a2_a2plus_status") != "LOCKED":
        raise ReferenceAwareCompositionError("r3e_mapping_or_a2_boundary_invalid")
    matches = [
        row for row in overlay.get("lesson_instructional_references", [])
        if isinstance(row, Mapping) and row.get("lesson_id") == lesson.get("lesson_id")
    ]
    if len(matches) != 1:
        raise ReferenceAwareCompositionError("r3e_selected_lesson_reference_not_unique")
    row = matches[0]
    for key in ("lesson_node_id", "skill", "level", "requirement_node_ids"):
        expected = list(lesson.get(key, [])) if key == "requirement_node_ids" else lesson.get(key)
        actual = list(row.get(key, [])) if key == "requirement_node_ids" else row.get(key)
        if actual != expected:
            raise ReferenceAwareCompositionError(f"r3e_selected_lesson_drift:{key}")
    references = row.get("instructional_references")
    if not isinstance(references, list):
        raise ReferenceAwareCompositionError("r3e_instructional_reference_list_required")
    expected_status = "REFERENCED" if references else "NO_EXACT_KET99_REFERENCE"
    if row.get("reference_status") != expected_status:
        raise ReferenceAwareCompositionError("r3e_reference_status_invalid")
    if row.get("delivery_blocked_by_missing_reference") is not False or row.get("hard_lesson_selection_changed") is not False:
        raise ReferenceAwareCompositionError("r3e_reference_row_hard_effect_invalid")
    return row


def _ket_items(
    *,
    activity_rows: Sequence[Mapping[str, Any]],
    catalog: Mapping[str, Any],
    lesson_id: str,
    skill: str,
) -> list[dict[str, Any]]:
    rows = [
        row for row in activity_rows
        if isinstance(row, Mapping)
        and row.get("source_kind") == "KET_ASSET_BODY"
        and row.get("curriculum_binding", {}).get("ket_lesson_id") == lesson_id
    ]
    rows.sort(key=lambda row: str(row.get("source_lineage", {}).get("m2_asset_key") or ""))
    asset_keys = [str(row.get("source_lineage", {}).get("m2_asset_key") or "") for row in rows]
    if set(asset_keys) != set(catalog.get("asset_keys", [])) or len(asset_keys) != len(set(asset_keys)):
        raise ReferenceAwareCompositionError("KET_ASSET_BUNDLE_NOT_RECONCILED")
    items = [
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
        for row in rows
    ]
    if not items:
        raise ReferenceAwareCompositionError("KET_STRUCTURED_ASSET_REQUIRED")
    return items


def _grammar_targets(reference_row: Mapping[str, Any]) -> list[str]:
    grammar_ids = {
        str(target.get("target_id") or "")
        for reference in reference_row.get("instructional_references", [])
        if isinstance(reference, Mapping)
        for target in reference.get("canonical_target_refs", [])
        if isinstance(target, Mapping)
        and target.get("target_type") == "GRAMMAR_UNIT"
        and str(target.get("target_id") or "")
    }
    return sorted(grammar_ids)[:MAX_BRIDGED_GRAMMAR_UNITS]


def _optional_context_items(
    *,
    activity_rows: Sequence[Mapping[str, Any]],
    skill: str,
    grammar_ids: Sequence[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    if not grammar_ids:
        return [], list(CONTEXT_ROLES)
    grammar_set = set(grammar_ids)
    rank = {grammar_id: index for index, grammar_id in enumerate(grammar_ids)}
    readiness_order = {
        "QUERYABLE_TEXT_RUNTIME_CONTRACT": 0,
        "BLOCKED_AUDIO_GENERATION": 1,
        "BLOCKED_RECORDING_CAPTURE": 1,
    }
    candidates = [
        row for row in activity_rows
        if isinstance(row, Mapping)
        and row.get("source_kind") == "RAZ_ACTIVITY_BINDING"
        and row.get("skill") == skill
        and row.get("curriculum_binding", {}).get("grammar_unit_id") in grammar_set
    ]
    candidates.sort(key=lambda row: (
        rank.get(str(row.get("curriculum_binding", {}).get("grammar_unit_id") or ""), 10**9),
        readiness_order.get(str(row.get("runtime_readiness") or ""), 9),
        cp07c._material_identity(row),
        str(row.get("runtime_activity_id") or ""),
    ))
    selected: list[dict[str, Any]] = []
    selected_materials: set[str] = set()
    gaps: list[str] = []
    for role in CONTEXT_ROLES:
        role_candidates = [row for row in candidates if role in row.get("instructional_roles", [])]
        if not role_candidates:
            gaps.append(role)
            continue
        unused = [row for row in role_candidates if cp07c._material_identity(row) not in selected_materials]
        chosen = (unused or role_candidates)[0]
        selected_materials.add(cp07c._material_identity(chosen))
        selected.append({
            "composition_item_id": str(chosen["runtime_activity_id"]),
            "source_kind": "RAZ_ACTIVITY_BINDING",
            "skill": skill,
            "instructional_role": role,
            "grammar_unit_id": str(chosen["curriculum_binding"]["grammar_unit_id"]),
            "learning_unit_id": str(chosen["curriculum_binding"]["learning_unit_id"]),
            "runtime_readiness": str(chosen["runtime_readiness"]),
            "delivery_allowed_now": chosen["runtime_readiness"] == "QUERYABLE_TEXT_RUNTIME_CONTRACT",
            "source_lineage": copy.deepcopy(chosen["source_lineage"]),
            "response_contract_ref": copy.deepcopy(chosen["response_contract_ref"]),
        })
    return selected, gaps


def _optional_m11b_item(
    *,
    activity_rows: Sequence[Mapping[str, Any]],
    skill: str,
    grammar_ids: Sequence[str],
) -> tuple[dict[str, Any] | None, str | None]:
    if not grammar_ids:
        return None, "NO_EXACT_GRAMMAR_TARGET_FROM_KET99_REFERENCE"
    rank = {grammar_id: index for index, grammar_id in enumerate(grammar_ids)}
    return cp07c._select_m11b_checkpoint(
        rows=activity_rows,
        skill=skill,
        grammar_ids=grammar_ids,
        rank_by_grammar=rank,
    )


def build_composition(
    m4_plan: Mapping[str, Any],
    m2_consumer: Mapping[str, Any],
    m1_graph: Mapping[str, Any],
    cp07a_index: Mapping[str, Any],
    r3e_overlay: Mapping[str, Any],
) -> dict[str, Any]:
    lesson = _verify_plan(m4_plan)
    catalog = cp07c._verify_m2(m2_consumer, lesson)
    cp07c._verify_m1(m1_graph, lesson)
    activity_rows = cp07c._verify_cp07a(cp07a_index, m2_consumer)
    reference_row = _verify_reference_overlay(
        r3e_overlay,
        m1_graph=m1_graph,
        m2_consumer=m2_consumer,
        lesson=lesson,
    )

    lesson_id = str(lesson["lesson_id"])
    skill = str(lesson["skill"])
    ket_items = _ket_items(activity_rows=activity_rows, catalog=catalog, lesson_id=lesson_id, skill=skill)
    grammar_ids = _grammar_targets(reference_row)
    raz_items, missing_context_roles = _optional_context_items(
        activity_rows=activity_rows,
        skill=skill,
        grammar_ids=grammar_ids,
    )
    m11b_item, m11b_gap = _optional_m11b_item(
        activity_rows=activity_rows,
        skill=skill,
        grammar_ids=grammar_ids,
    )
    references = copy.deepcopy(list(reference_row.get("instructional_references", [])))
    if not references:
        composition_mode = "KET_ONLY_NO_EXACT_KET99_REFERENCE"
    elif raz_items:
        composition_mode = "KET_WITH_KET99_REFERENCE_AND_OPTIONAL_CONTEXT"
    elif grammar_ids:
        composition_mode = "KET_WITH_KET99_REFERENCE_CONTEXT_UNAVAILABLE"
    else:
        composition_mode = "KET_WITH_KET99_REFERENCE_NO_GRAMMAR_CONTEXT"

    composition_items = ket_items + raz_items + ([m11b_item] if m11b_item else [])
    delivery_allowed_count = sum(bool(row["delivery_allowed_now"]) for row in composition_items)
    source_counts = Counter(str(row["source_kind"]) for row in composition_items)
    role_counts = Counter(str(row["instructional_role"]) for row in composition_items)

    enriched = copy.deepcopy(dict(m4_plan))
    enriched["cp07r3f_task_id"] = TASK_ID
    enriched["cp07r3f_schema_version"] = SCHEMA_VERSION
    enriched["cp07r3f_validation_status"] = PASS_STATUS
    enriched["source_m4_next_short_step"] = m4_plan.get("next_short_step")
    enriched["source_identity"] = {
        "m4_plan_sha256": cp07c._digest(m4_plan),
        "m2_consumer_sha256": cp07c._digest(m2_consumer),
        "m1_hard_graph_sha256": cp07c._digest(m1_graph),
        "cp07a_runtime_index_sha256": cp07c._digest(cp07a_index),
        "r3e_reference_overlay_sha256": cp07c._digest(r3e_overlay),
    }
    enriched["unified_lesson_composition"] = {
        "composition_id": f"A1FS_CP07R3F:{m4_plan['plan_id']}",
        "selected_lesson_id": lesson_id,
        "selected_skill": skill,
        "selected_level": cp07c._normalize_level(lesson["level"]),
        "hard_selection_preserved": True,
        "requirement_node_ids": list(lesson["requirement_node_ids"]),
        "composition_mode": composition_mode,
        "instructional_reference_status": str(reference_row["reference_status"]),
        "instructional_references": references,
        "bridged_grammar_unit_ids": grammar_ids,
        "composition_items": composition_items,
        "composition_gaps": {
            "missing_exact_ket99_reference": not references,
            "no_exact_grammar_target_from_reference": bool(references) and not grammar_ids,
            "missing_context_roles": missing_context_roles,
            "m11b_checkpoint_gap": m11b_gap,
        },
        "coverage_summary": {
            "composition_item_count": len(composition_items),
            "source_kind_counts": dict(sorted(source_counts.items())),
            "instructional_role_counts": dict(sorted(role_counts.items())),
            "ket_asset_count": len(ket_items),
            "instructional_reference_count": len(references),
            "raz_contextual_activity_count": len(raz_items),
            "m11b_checkpoint_count": 1 if m11b_item else 0,
            "bridged_grammar_unit_count": len(grammar_ids),
            "delivery_allowed_now_count": delivery_allowed_count,
            "blocked_dependency_count": len(composition_items) - delivery_allowed_count,
        },
        "consumer_gate": {
            "m4_selected_lesson_unchanged": True,
            "m1_hard_prerequisite_graph_unchanged": True,
            "ket_asset_body_required": True,
            "ket99_reference_optional": True,
            "raz_context_optional": True,
            "m11b_checkpoint_optional": True,
            "missing_reference_blocks_delivery": False,
            "r4_cp07d_optional_context_consumer_completed": False,
            "a2_payload_included": False,
        },
    }
    enriched["claim_boundaries"] = {
        "private_content_included": False,
        "transcript_text_included": False,
        "hard_lesson_selection_changed": False,
        "hard_prerequisite_changed": False,
        "missing_reference_blocks_delivery": False,
        "r4_cp07d_runtime_claimed": False,
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
    parser.add_argument("--r3e-overlay", type=Path, default=DEFAULT_R3E)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        inputs = (
            _read(args.m4_plan),
            _read(args.m2_consumer),
            _read(args.m1_graph),
            _read(args.cp07a_index),
            _read(args.r3e_overlay),
        )
        artifact = build_composition(*inputs)
        from ulga.validators import validate_a1fs_v1_cp07r3f_reference_aware_optional_context_lesson_composition as validator
        report = validator.validate_artifact(
            artifact,
            m4_plan=inputs[0],
            m2_consumer=inputs[1],
            m1_graph=inputs[2],
            cp07a_index=inputs[3],
            r3e_overlay=inputs[4],
        )
        cp07c._write_atomic(args.output, artifact)
        cp07c._write_atomic(args.report, report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["validation_status"] == PASS_STATUS else 1
    except (ReferenceAwareCompositionError, cp07c.CP07CBuildError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
