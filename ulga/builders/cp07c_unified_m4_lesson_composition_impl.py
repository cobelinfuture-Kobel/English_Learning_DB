#!/usr/bin/env python3
"""Compose one evidence-bound KET + RAZ + M11B A1/A1+ lesson plan.

The existing M4 planner remains the sole hard lesson selector.  This adapter
keeps the selected KET lesson unchanged and enriches that plan with a bounded,
metadata-only activity composition.  Contextual activities are admitted only
when the selected lesson's existing M1 requirement nodes have exact CP07B
transcript evidence that connects to an existing CP06 Grammar Unit.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp07a_unified_runtime_activity_contract_and_lineage_adapter as cp07a  # noqa: E402
from ulga.builders import build_a1fs_v1_cp07b_ket99_canonical_mapping_and_instructional_sequence_overlay as cp07b  # noqa: E402
from ulga.builders import build_a1fs_v1_m1_prerequisite_graph_and_coverage as m1  # noqa: E402
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2  # noqa: E402
from ulga.builders import build_a1fs_v1_m4_lesson_planner_selection_a2_lock as m4  # noqa: E402

TASK_ID = "A1FS-V1-CP07C_UnifiedM4PlannerSelectionAndLessonComposition"
PROGRAM_ID = cp07a.PROGRAM_ID
SCHEMA_VERSION = "a1fs.v1.cp07c.unified_m4_lesson_composition.v1"
PASS_STATUS = "PASS_CP07C_UNIFIED_M4_LESSON_COMPOSITION_READY"
NEXT_SHORT_STEP = "A1FS-V1-CP07D_FourSkillDeliveryResponseAndMediaCanaryIntegration"

DEFAULT_M4_PLAN = REPO_ROOT / ".local/a1fs_v1/m4/lesson_plan.private.json"
DEFAULT_M2 = REPO_ROOT / ".local/a1fs_v1/m2/four_skill_asset_body_consumer.private.json"
DEFAULT_M1 = REPO_ROOT / ".local/a1fs_v1/m1/a1a1plus_prerequisite_graph_and_coverage.private.json"
DEFAULT_CP07A = cp07a.DEFAULT_OUTPUT
DEFAULT_CP07B = cp07b.DEFAULT_OUTPUT
DEFAULT_OUTPUT = REPO_ROOT / ".local/a1fs_v1/cp07c/unified_m4_lesson_composition.safe.json"
DEFAULT_REPORT = REPO_ROOT / ".local/a1fs_v1/cp07c/unified_m4_lesson_composition.validation.json"

SUPPORTED_PLAN_STATUSES = {"PLAN_LEARNING_LESSON", "RESUME_ACTIVE_SESSION"}
SKILLS = ("LISTENING", "SPEAKING", "READING", "WRITING")
LEVELS = ("A1", "A1_PLUS")
CONTEXT_ROLES = ("FOCUS", "CONTRAST", "RECYCLE", "TRANSFER")
MAX_BRIDGED_GRAMMAR_UNITS = 3
FORBIDDEN_KEYS = {
    "payload", "source_content", "text", "prompt", "scoring_contract",
    "correct_answer", "answer_key", "learner_response", "audio_bytes",
    "recording", "transcript_text", "speaker_turns",
}


class CP07CBuildError(ValueError):
    """Fail-closed composition or lineage error."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CP07CBuildError(f"json_object_required:{path}")
    return value


def _write_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def _normalize_level(value: Any) -> str:
    normalized = str(value or "").upper().replace("+", "_PLUS")
    if normalized not in LEVELS:
        raise CP07CBuildError(f"level_outside_a1_a1plus:{value}")
    return normalized


def _walk_forbidden(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in FORBIDDEN_KEYS:
                raise CP07CBuildError(f"private_content_key_forbidden:{path}.{key}")
            _walk_forbidden(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_forbidden(child, f"{path}[{index}]")


def _verify_plan(plan: Mapping[str, Any]) -> Mapping[str, Any]:
    if plan.get("task_id") != m4.TASK_ID or plan.get("validation_status") != m4.STATUS:
        raise CP07CBuildError("m4_plan_contract_invalid")
    if plan.get("plan_status") not in SUPPORTED_PLAN_STATUSES:
        raise CP07CBuildError("m4_plan_not_composable")
    if plan.get("a2_payload_included") is not False or plan.get("a2_session_started") is not False:
        raise CP07CBuildError("m4_a2_boundary_invalid")
    lock = plan.get("a2_lock")
    if not isinstance(lock, Mapping) or lock.get("a2_payload_access_granted") is not False or lock.get("a2_session_start_granted") is not False:
        raise CP07CBuildError("m4_a2_lock_contract_invalid")
    lesson = plan.get("selected_lesson")
    if not isinstance(lesson, Mapping):
        raise CP07CBuildError("m4_selected_lesson_required")
    if lesson.get("skill") not in SKILLS:
        raise CP07CBuildError("m4_selected_skill_invalid")
    _normalize_level(lesson.get("level"))
    if not str(lesson.get("lesson_id") or "") or not str(lesson.get("lesson_node_id") or ""):
        raise CP07CBuildError("m4_selected_lesson_identity_missing")
    if not isinstance(lesson.get("requirement_node_ids"), list) or not lesson.get("requirement_node_ids"):
        raise CP07CBuildError("m4_selected_lesson_requirement_nodes_missing")
    return lesson


def _verify_m2(consumer: Mapping[str, Any], lesson: Mapping[str, Any]) -> Mapping[str, Any]:
    if consumer.get("task_id") != m2.TASK_ID or consumer.get("schema_version") != m2.SCHEMA_VERSION:
        raise CP07CBuildError("m2_contract_invalid")
    if consumer.get("validation_status") != m2.STATUS or consumer.get("errors") != []:
        raise CP07CBuildError("m2_not_passed")
    if consumer.get("access_contract", {}).get("a2_payload_query_allowed") is not False:
        raise CP07CBuildError("m2_a2_lock_invalid")
    catalogs = [row for row in consumer.get("lesson_catalog", []) if isinstance(row, Mapping) and row.get("lesson_id") == lesson["lesson_id"]]
    if len(catalogs) != 1:
        raise CP07CBuildError("m2_selected_lesson_not_unique")
    catalog = catalogs[0]
    for key in ("lesson_node_id", "skill", "level", "requirement_node_ids"):
        if catalog.get(key) != lesson.get(key):
            raise CP07CBuildError(f"m2_m4_selected_lesson_drift:{key}")
    if catalog.get("level") not in {"A1", "A1+"}:
        raise CP07CBuildError("m2_selected_lesson_a2_locked")
    return catalog


def _verify_m1(graph: Mapping[str, Any], lesson: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if graph.get("task_id") != m1.TASK_ID or graph.get("schema_version") != m1.SCHEMA_VERSION:
        raise CP07CBuildError("m1_contract_invalid")
    if graph.get("validation_status") != m1.STATUS or graph.get("errors") != []:
        raise CP07CBuildError("m1_not_passed")
    if graph.get("a2_lock_contract", {}).get("state") != "LOCKED_BY_DESIGN":
        raise CP07CBuildError("m1_a2_lock_invalid")
    node_index = {
        str(row.get("node_id") or ""): row
        for row in graph.get("nodes", [])
        if isinstance(row, Mapping) and str(row.get("node_id") or "")
    }
    lesson_node = node_index.get(str(lesson["lesson_node_id"]))
    if lesson_node is None or lesson_node.get("node_type") != "LESSON" or lesson_node.get("source_ref") != lesson["lesson_id"]:
        raise CP07CBuildError("m1_selected_lesson_node_invalid")
    for requirement_id in lesson["requirement_node_ids"]:
        node = node_index.get(str(requirement_id))
        if node is None or node.get("node_type") not in {"CAPABILITY", "SUPPORT_RESOURCE"} or node.get("level") not in {"A1", "A1+"}:
            raise CP07CBuildError(f"m1_requirement_node_invalid:{requirement_id}")
    return node_index


def _verify_cp07a(index: Mapping[str, Any], consumer: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if index.get("task_id") != cp07a.TASK_ID or index.get("schema_version") != cp07a.SCHEMA_VERSION:
        raise CP07CBuildError("cp07a_contract_invalid")
    if index.get("stop_reason") != "NONE" or index.get("errors") != []:
        raise CP07CBuildError("cp07a_not_passed")
    if index.get("scope") != "A1_A1_PLUS_ONLY":
        raise CP07CBuildError("cp07a_scope_invalid")
    if index.get("source_identity", {}).get("m2_consumer_sha256") != _digest(consumer):
        raise CP07CBuildError("cp07a_m2_binding_invalid")
    rows = index.get("runtime_activities")
    if not isinstance(rows, list) or not rows:
        raise CP07CBuildError("cp07a_runtime_activity_list_required")
    return rows


def _verify_cp07b(overlay: Mapping[str, Any], graph: Mapping[str, Any]) -> None:
    if overlay.get("task_id") != cp07b.TASK_ID or overlay.get("schema_version") != cp07b.SCHEMA_VERSION:
        raise CP07CBuildError("cp07b_contract_invalid")
    if overlay.get("stop_reason") != "NONE" or overlay.get("errors") != []:
        raise CP07CBuildError("cp07b_not_passed")
    authority = overlay.get("authority_contract")
    if not isinstance(authority, Mapping) or authority.get("hard_graph_mutation_allowed") is not False:
        raise CP07CBuildError("cp07b_hard_graph_boundary_invalid")
    if authority.get("a2_a2plus_status") != "LOCKED":
        raise CP07CBuildError("cp07b_a2_lock_invalid")
    if overlay.get("source_identity", {}).get("m1_hard_graph_sha256") != _digest(graph):
        raise CP07CBuildError("cp07b_m1_binding_invalid")
    if overlay.get("planner_overlay_gate", {}).get("m4_planner_integration_completed") is not False:
        raise CP07CBuildError("cp07b_premature_m4_claim_invalid")


def _bridge_selected_lesson(
    *, lesson: Mapping[str, Any], overlay: Mapping[str, Any]
) -> tuple[list[str], list[dict[str, Any]], dict[str, int]]:
    requirement_ids = {str(value) for value in lesson["requirement_node_ids"]}
    transcript_matches: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    transcript_rows: dict[str, Mapping[str, Any]] = {}
    for transcript in overlay.get("transcript_overlays", []):
        if not isinstance(transcript, Mapping):
            continue
        transcript_id = str(transcript.get("transcript_id") or "")
        transcript_rows[transcript_id] = transcript
        for occurrence in transcript.get("evidence_occurrences", []):
            if not isinstance(occurrence, Mapping):
                continue
            matching = [
                target for target in occurrence.get("canonical_targets", [])
                if isinstance(target, Mapping)
                and target.get("target_type") == "M1_NODE"
                and str(target.get("target_id") or "") in requirement_ids
            ]
            if matching:
                transcript_matches[transcript_id].append({
                    "evidence_occurrence_id": str(occurrence.get("evidence_occurrence_id") or ""),
                    "matched_requirement_node_ids": sorted(str(target["target_id"]) for target in matching),
                    "source_evidence_sha256": str(transcript.get("source_lineage", {}).get("source_evidence_sha256") or ""),
                })
    if not transcript_matches:
        raise CP07CBuildError("NO_EXACT_KET_REQUIREMENT_TO_TRANSCRIPT_BRIDGE")

    grammar_evidence: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for transcript_id in sorted(transcript_matches):
        transcript = transcript_rows[transcript_id]
        for occurrence in transcript.get("evidence_occurrences", []):
            if not isinstance(occurrence, Mapping):
                continue
            for target in occurrence.get("canonical_targets", []):
                if not isinstance(target, Mapping) or target.get("target_type") != "GRAMMAR_UNIT":
                    continue
                grammar_id = str(target.get("target_id") or "")
                if not grammar_id:
                    continue
                grammar_evidence[grammar_id].append({
                    "transcript_id": transcript_id,
                    "evidence_occurrence_id": str(occurrence.get("evidence_occurrence_id") or ""),
                    "matched_requirement_node_ids": sorted({
                        node_id
                        for match in transcript_matches[transcript_id]
                        for node_id in match["matched_requirement_node_ids"]
                    }),
                    "mapping_basis": str(target.get("mapping_basis") or ""),
                    "mapping_confidence": str(target.get("mapping_confidence") or ""),
                    "source_evidence_sha256": str(transcript.get("source_lineage", {}).get("source_evidence_sha256") or ""),
                })
    if not grammar_evidence:
        raise CP07CBuildError("NO_TRANSCRIPT_CONTEXT_TO_GRAMMAR_UNIT_BRIDGE")

    rank_by_grammar: dict[str, int] = {}
    for row in overlay.get("canonical_target_sequences", []):
        if isinstance(row, Mapping) and row.get("target_type") == "GRAMMAR_UNIT":
            rank_by_grammar[str(row.get("target_id") or "")] = int(row.get("soft_order_rank") or 10**9)
    grammar_ids = sorted(
        grammar_evidence,
        key=lambda grammar_id: (
            rank_by_grammar.get(grammar_id, 10**9),
            min(int(item["transcript_id"][1:]) for item in grammar_evidence[grammar_id]),
            grammar_id,
        ),
    )[:MAX_BRIDGED_GRAMMAR_UNITS]
    bridge_rows = [
        {
            "grammar_unit_id": grammar_id,
            "soft_order_rank": rank_by_grammar.get(grammar_id),
            "evidence": grammar_evidence[grammar_id],
        }
        for grammar_id in grammar_ids
    ]
    return grammar_ids, bridge_rows, rank_by_grammar


def _material_identity(row: Mapping[str, Any]) -> str:
    lineage = row.get("source_lineage", {})
    if not isinstance(lineage, Mapping):
        return str(row.get("runtime_activity_id") or "")
    return str(lineage.get("cp05_material_id") or lineage.get("cp05_m11b_activity_id") or row.get("runtime_activity_id") or "")


def _select_contextual_items(
    *, rows: Sequence[Mapping[str, Any]], skill: str, grammar_ids: Sequence[str], rank_by_grammar: Mapping[str, int]
) -> tuple[list[dict[str, Any]], list[str]]:
    grammar_set = set(grammar_ids)
    candidates = [
        row for row in rows
        if isinstance(row, Mapping)
        and row.get("source_kind") == "RAZ_ACTIVITY_BINDING"
        and row.get("skill") == skill
        and row.get("curriculum_binding", {}).get("grammar_unit_id") in grammar_set
    ]
    if not candidates:
        raise CP07CBuildError("NO_RAZ_CONTEXTUAL_ACTIVITY_FOR_BRIDGED_GRAMMAR")
    readiness_order = {
        "QUERYABLE_TEXT_RUNTIME_CONTRACT": 0,
        "BLOCKED_AUDIO_GENERATION": 1,
        "BLOCKED_RECORDING_CAPTURE": 1,
    }
    candidates.sort(key=lambda row: (
        rank_by_grammar.get(str(row.get("curriculum_binding", {}).get("grammar_unit_id") or ""), 10**9),
        readiness_order.get(str(row.get("runtime_readiness") or ""), 9),
        _material_identity(row),
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
        unused = [row for row in role_candidates if _material_identity(row) not in selected_materials]
        chosen = (unused or role_candidates)[0]
        selected_materials.add(_material_identity(chosen))
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
    if not any(row["instructional_role"] == "FOCUS" for row in selected):
        raise CP07CBuildError("RAZ_FOCUS_ACTIVITY_REQUIRED")
    return selected, gaps


def _select_m11b_checkpoint(
    *, rows: Sequence[Mapping[str, Any]], skill: str, grammar_ids: Sequence[str], rank_by_grammar: Mapping[str, int]
) -> tuple[dict[str, Any] | None, str | None]:
    grammar_set = set(grammar_ids)
    candidates = [
        row for row in rows
        if isinstance(row, Mapping)
        and row.get("source_kind") == "M11B_REVIEWED_ACTIVITY"
        and row.get("skill") == skill
        and row.get("curriculum_binding", {}).get("grammar_unit_id") in grammar_set
    ]
    candidates.sort(key=lambda row: (
        rank_by_grammar.get(str(row.get("curriculum_binding", {}).get("grammar_unit_id") or ""), 10**9),
        str(row.get("runtime_activity_id") or ""),
    ))
    if not candidates:
        return None, "NO_M11B_CHECKPOINT_FOR_BRIDGED_GRAMMAR_AND_SKILL"
    chosen = candidates[0]
    return {
        "composition_item_id": str(chosen["runtime_activity_id"]),
        "source_kind": "M11B_REVIEWED_ACTIVITY",
        "skill": skill,
        "instructional_role": "CHECKPOINT",
        "grammar_unit_id": str(chosen["curriculum_binding"]["grammar_unit_id"]),
        "learning_unit_id": str(chosen["curriculum_binding"]["learning_unit_id"]),
        "runtime_readiness": str(chosen["runtime_readiness"]),
        "delivery_allowed_now": False,
        "source_lineage": copy.deepcopy(chosen["source_lineage"]),
        "response_contract_ref": copy.deepcopy(chosen["response_contract_ref"]),
    }, None


def build_composition(
    m4_plan: Mapping[str, Any],
    m2_consumer: Mapping[str, Any],
    m1_graph: Mapping[str, Any],
    cp07a_index: Mapping[str, Any],
    cp07b_overlay: Mapping[str, Any],
) -> dict[str, Any]:
    lesson = _verify_plan(m4_plan)
    catalog = _verify_m2(m2_consumer, lesson)
    _verify_m1(m1_graph, lesson)
    activity_rows = _verify_cp07a(cp07a_index, m2_consumer)
    _verify_cp07b(cp07b_overlay, m1_graph)

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
        raise CP07CBuildError("KET_ASSET_BUNDLE_NOT_RECONCILED")
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
        raise CP07CBuildError("KET_STRUCTURED_ASSET_REQUIRED")

    grammar_ids, bridge_evidence, rank_by_grammar = _bridge_selected_lesson(
        lesson=lesson, overlay=cp07b_overlay
    )
    raz_items, missing_context_roles = _select_contextual_items(
        rows=activity_rows, skill=skill, grammar_ids=grammar_ids, rank_by_grammar=rank_by_grammar
    )
    m11b_item, m11b_gap = _select_m11b_checkpoint(
        rows=activity_rows, skill=skill, grammar_ids=grammar_ids, rank_by_grammar=rank_by_grammar
    )

    composition_items = ket_items + raz_items + ([m11b_item] if m11b_item else [])
    delivery_allowed_count = sum(bool(row["delivery_allowed_now"]) for row in composition_items)
    blocked_dependency_count = len(composition_items) - delivery_allowed_count
    source_counts = Counter(row["source_kind"] for row in composition_items)
    role_counts = Counter(row["instructional_role"] for row in composition_items)

    enriched = copy.deepcopy(dict(m4_plan))
    enriched["cp07c_task_id"] = TASK_ID
    enriched["cp07c_schema_version"] = SCHEMA_VERSION
    enriched["cp07c_validation_status"] = PASS_STATUS
    enriched["source_m4_next_short_step"] = m4_plan.get("next_short_step")
    enriched["source_identity"] = {
        "m4_plan_sha256": _digest(m4_plan),
        "m2_consumer_sha256": _digest(m2_consumer),
        "m1_hard_graph_sha256": _digest(m1_graph),
        "cp07a_runtime_index_sha256": _digest(cp07a_index),
        "cp07b_instructional_overlay_sha256": _digest(cp07b_overlay),
    }
    enriched["unified_lesson_composition"] = {
        "composition_id": f"A1FS_CP07C:{m4_plan['plan_id']}",
        "selected_lesson_id": lesson_id,
        "selected_skill": skill,
        "selected_level": _normalize_level(lesson["level"]),
        "hard_selection_preserved": True,
        "requirement_node_ids": list(lesson["requirement_node_ids"]),
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
    _walk_forbidden(enriched)
    return enriched


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m4-plan", type=Path, default=DEFAULT_M4_PLAN)
    parser.add_argument("--m2-consumer", type=Path, default=DEFAULT_M2)
    parser.add_argument("--m1-graph", type=Path, default=DEFAULT_M1)
    parser.add_argument("--cp07a-index", type=Path, default=DEFAULT_CP07A)
    parser.add_argument("--cp07b-overlay", type=Path, default=DEFAULT_CP07B)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        inputs = (
            _read(args.m4_plan), _read(args.m2_consumer), _read(args.m1_graph),
            _read(args.cp07a_index), _read(args.cp07b_overlay),
        )
        artifact = build_composition(*inputs)
        from ulga.validators import validate_a1fs_v1_cp07c_unified_m4_lesson_composition as validator
        report = validator.validate_artifact(
            artifact,
            m4_plan=inputs[0], m2_consumer=inputs[1], m1_graph=inputs[2],
            cp07a_index=inputs[3], cp07b_overlay=inputs[4],
        )
        _write_atomic(args.output, artifact)
        _write_atomic(args.report, report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["validation_status"] == PASS_STATUS else 1
    except (CP07CBuildError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
