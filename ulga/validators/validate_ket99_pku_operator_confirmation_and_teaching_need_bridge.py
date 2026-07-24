#!/usr/bin/env python3
"""Validate the KET99-PK-M2 operator decision and teaching-need bridge."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "KET99-PK-M2_OperatorConfirmationAndTeachingNeedIdentityBridge"
SCHEMA_VERSION = "ket99.pku.operator_confirmation_teaching_need_bridge.v1"
PASS_STATUS = "PASS_KET99_PK_M2_OPERATOR_CONFIRMATION_AND_TEACHING_NEED_IDENTITY_BRIDGE_READY"
FAIL_STATUS = "FAIL_KET99_PK_M2_OPERATOR_CONFIRMATION_AND_TEACHING_NEED_IDENTITY_BRIDGE"
NEXT_SHORT_STEP = "KET99-PK-M3_ControlledLessonCandidateMappingAndValidation"
PILOT = ROOT / "ulga/reports/ket99_pku_pilot/ket99_pedagogical_knowledge_units.pilot.json"
BRIDGE = ROOT / "ulga/reports/ket99_pku_pilot/ket99_pku_operator_confirmation_teaching_need_bridge.v1.json"
REPORT = ROOT / ".local/a1fs_v1/ket99_pku_m2/operator_confirmation_teaching_need_bridge.validation.json"
LEVELS = {"A1", "A1+"}
SKILLS = {"LISTENING", "SPEAKING", "READING", "WRITING"}
FALSE_AUTHORITY_KEYS = {
    "canonical_promotion_allowed", "hard_graph_mutation_allowed",
    "hard_prerequisite_creation_allowed", "hard_lesson_selection_allowed",
    "production_lesson_mapping_allowed", "a2_mapping_allowed",
}
EXPECTED_COUNTS = {
    "operator_confirmed_pku_count": 35,
    "confirmed_pilot_admission_count": 32,
    "confirmed_exact_authority_join_count": 10,
    "confirmed_teaching_need_bridge_count": 22,
    "confirmed_exam_only_reject_count": 3,
    "production_admission_count": 0,
    "production_lesson_mapping_count": 0,
}


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


def rows(value: Mapping[str, Any], field_key: str, row_key: str) -> list[dict[str, Any]]:
    fields, raw_rows = value.get(field_key), value.get(row_key)
    if not isinstance(fields, list) or not isinstance(raw_rows, list):
        raise ValueError(f"row_bundle_missing:{row_key}")
    result = []
    for raw in raw_rows:
        if not isinstance(raw, list) or len(raw) != len(fields):
            raise ValueError(f"row_bundle_invalid:{row_key}")
        result.append(dict(zip(fields, raw)))
    return result


def index(rows_: list[dict[str, Any]], key: str, code: str) -> dict[str, dict[str, Any]]:
    result = {}
    for row in rows_:
        identity = str(row.get(key) or "")
        if not identity or identity in result:
            raise ValueError(f"{code}:{identity}")
        result[identity] = row
    return result


def validate_bridge(bridge: Mapping[str, Any], pilot: Mapping[str, Any], *, pilot_blob_sha: str | None = None) -> dict[str, Any]:
    errors: list[str] = []

    def require(ok: bool, code: str) -> None:
        if not ok:
            errors.append(code)

    require(bridge.get("task_id") == TASK_ID, "task_id_invalid")
    require(bridge.get("schema_version") == SCHEMA_VERSION, "schema_version_invalid")
    require(bridge.get("validation_status") == PASS_STATUS, "validation_status_invalid")
    require(bridge.get("errors") == [], "committed_errors_not_empty")
    require(bridge.get("stop_reason") == "NONE", "stop_reason_invalid")
    require(bridge.get("next_short_step") == NEXT_SHORT_STEP, "next_short_step_invalid")

    scope = bridge.get("scope", {})
    require(isinstance(scope, Mapping), "scope_missing")
    if isinstance(scope, Mapping):
        require(scope.get("source_pilot_task_id") == pilot.get("task_id"), "pilot_task_binding_invalid")
        require(scope.get("pilot_transcript_ids") == ["P005", "P006", "P008", "P023", "P026"], "transcript_scope_invalid")
        require(scope.get("level_scope") == ["A1", "A1+"], "level_scope_invalid")
        require(scope.get("a2_status") == "LOCKED", "a2_not_locked")

    confirmation = bridge.get("operator_confirmation", {})
    require(isinstance(confirmation, Mapping), "operator_confirmation_missing")
    if isinstance(confirmation, Mapping):
        require(confirmation.get("status") == "CONFIRMED", "operator_confirmation_invalid")
        require(confirmation.get("confirmation_scope") == "CONFIRM_M1_RECOMMENDED_DISPOSITIONS_ONLY", "confirmation_scope_invalid")
        require(confirmation.get("confirmed_pku_count") == 35, "confirmed_pku_count_invalid")
        require(bool(str(confirmation.get("operator_instruction_ref") or "")), "operator_instruction_ref_missing")

    authority = bridge.get("authority_contract", {})
    require(isinstance(authority, Mapping), "authority_contract_missing")
    if isinstance(authority, Mapping):
        require(authority.get("source_role") == "third_party_teacher_delivery_reference", "source_role_invalid")
        require(authority.get("authority_status") == "non_authoritative", "authority_status_invalid")
        for key in FALSE_AUTHORITY_KEYS:
            require(authority.get(key) is False, f"authority_boundary_true:{key}")

    source = bridge.get("source_identity", {})
    require(isinstance(source, Mapping), "source_identity_missing")
    if isinstance(source, Mapping) and pilot_blob_sha:
        require(source.get("pilot_manifest_git_blob_sha") == pilot_blob_sha, "pilot_blob_sha_mismatch")

    try:
        pilot_index = index(rows(pilot, "pku_index_field_order", "pku_index"), "pku_id", "pilot_identity_invalid")
        decisions = index(rows(bridge, "operator_decision_field_order", "operator_decisions"), "pku_id", "decision_identity_invalid")
        registry = index(rows(bridge, "teaching_need_field_order", "teaching_need_registry"), "source_pku_id", "teaching_need_source_invalid")
    except ValueError as exc:
        errors.append(str(exc))
        pilot_index, decisions, registry = {}, {}, {}

    require(set(decisions) == set(pilot_index), "decision_coverage_invalid")
    registry_ids: set[str] = set()
    for pku_id, row in registry.items():
        need_id = str(row.get("teaching_need_id") or "")
        concept = str(row.get("pedagogical_concept_id") or "")
        require(need_id == f"TEACHING_NEED:{concept}", f"teaching_need_identity_invalid:{pku_id}")
        require(need_id not in registry_ids, f"teaching_need_duplicate:{need_id}")
        registry_ids.add(need_id)
        require(isinstance(row.get("level_scope"), list) and bool(row["level_scope"]) and set(row["level_scope"]) <= LEVELS, f"teaching_need_level_invalid:{pku_id}")
        require(isinstance(row.get("skill_scope"), list) and bool(row["skill_scope"]) and set(row["skill_scope"]) <= SKILLS, f"teaching_need_skill_invalid:{pku_id}")

    exact = bridged = rejected = admitted = 0
    for pku_id, source_row in pilot_index.items():
        decision = decisions.get(pku_id, {})
        require(decision.get("production_admission_allowed") is False, f"production_admission_true:{pku_id}")
        require(decision.get("production_lesson_mapping_allowed") is False, f"production_mapping_true:{pku_id}")
        disposition = source_row.get("disposition")
        mapping = source_row.get("lesson_mapping_status")
        concept = str(source_row.get("pedagogical_concept_id") or "")
        authority_ids = source_row.get("authority_ids") or []

        if disposition == "REJECTED_EXAM_PROCEDURE_ONLY":
            rejected += 1
            require(decision.get("operator_decision") == "CONFIRM_REJECT_EXAM_PROCEDURE_ONLY", f"exam_decision_invalid:{pku_id}")
            require(decision.get("confirmed_disposition") == disposition, f"exam_disposition_invalid:{pku_id}")
            require(decision.get("teaching_need_id") is None and pku_id not in registry, f"exam_bridge_forbidden:{pku_id}")
            continue

        admitted += 1
        require(decision.get("confirmed_disposition") == "PILOT_ADMITTED", f"admission_disposition_invalid:{pku_id}")
        if mapping == "EXACT_AUTHORITY_JOIN_READY":
            exact += 1
            require(decision.get("operator_decision") == "CONFIRM_EXACT_AUTHORITY_JOIN", f"exact_decision_invalid:{pku_id}")
            require(decision.get("authority_ids") == authority_ids, f"exact_authority_drift:{pku_id}")
            require(decision.get("teaching_need_id") is None and pku_id not in registry, f"exact_bridge_forbidden:{pku_id}")
        elif mapping == "BLOCKED_MISSING_LESSON_TEACHING_NEED_IDENTITY":
            bridged += 1
            expected = f"TEACHING_NEED:{concept}"
            require(decision.get("operator_decision") == "CONFIRM_TEACHING_NEED_BRIDGE", f"bridge_decision_invalid:{pku_id}")
            require(decision.get("teaching_need_id") == expected, f"bridge_identity_invalid:{pku_id}")
            require(pku_id in registry and registry[pku_id].get("teaching_need_id") == expected, f"registry_binding_invalid:{pku_id}")
        else:
            errors.append(f"unsupported_mapping_status:{pku_id}:{mapping}")

    derived = {
        "operator_confirmed_pku_count": len(pilot_index),
        "confirmed_pilot_admission_count": admitted,
        "confirmed_exact_authority_join_count": exact,
        "confirmed_teaching_need_bridge_count": bridged,
        "confirmed_exam_only_reject_count": rejected,
        "production_admission_count": 0,
        "production_lesson_mapping_count": 0,
    }
    counts = bridge.get("counts", {})
    require(isinstance(counts, Mapping), "counts_missing")
    if isinstance(counts, Mapping):
        for key, value in EXPECTED_COUNTS.items():
            require(counts.get(key) == value, f"committed_count_invalid:{key}")
        for key, value in derived.items():
            require(counts.get(key) == value, f"derived_count_invalid:{key}")
    require(len(registry) == 22, "teaching_need_count_invalid")

    boundaries = bridge.get("claim_boundaries", {})
    require(isinstance(boundaries, Mapping), "claim_boundaries_missing")
    if isinstance(boundaries, Mapping):
        for key, value in boundaries.items():
            require(value is False, f"claim_boundary_true:{key}")

    return {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS if not errors else FAIL_STATUS,
        "source_pku_count": len(pilot_index),
        "operator_decision_count": len(decisions),
        "teaching_need_identity_count": len(registry),
        "exact_authority_join_count": exact,
        "exam_only_reject_count": rejected,
        "production_lesson_mapping_count": 0,
        "a2_unlocked": False,
        "errors": errors,
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILURE",
        "next_short_step": NEXT_SHORT_STEP if not errors else TASK_ID,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", type=Path, default=PILOT)
    parser.add_argument("--bridge", type=Path, default=BRIDGE)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    try:
        report = validate_bridge(read_json(args.bridge), read_json(args.pilot), pilot_blob_sha=_git_blob_sha(args.pilot))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report = {"task_id": TASK_ID, "validation_status": FAIL_STATUS, "errors": [str(exc)], "stop_reason": "VALIDATION_FAILURE", "next_short_step": TASK_ID}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("validation_status") == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
