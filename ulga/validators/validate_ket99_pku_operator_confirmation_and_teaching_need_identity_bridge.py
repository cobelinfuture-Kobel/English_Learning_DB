#!/usr/bin/env python3
"""Validate the KET99 PKU operator confirmation and teaching-need bridge."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_ket99_pku_operator_confirmation_and_teaching_need_identity_bridge as builder

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validation-only enforcement for the non-authoritative KET99 PKU M2 metadata bridge; "
    "no learner content, canonical promotion, hard graph mutation, production lesson mapping, mastery, media, or A2 payload is produced."
)

FAIL_STATUS = "FAIL_KET99_PK_M2_OPERATOR_CONFIRMATION_BRIDGE_VALIDATION"


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def validate_artifact(artifact: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    require(artifact.get("task_id") == builder.TASK_ID, "task_id_invalid")
    require(artifact.get("schema_version") == builder.SCHEMA_VERSION, "schema_version_invalid")
    require(artifact.get("validation_status") == builder.PASS_STATUS, "validation_status_invalid")
    require(artifact.get("stop_reason") == "NONE", "stop_reason_invalid")
    require(artifact.get("next_short_step") == builder.NEXT_SHORT_STEP, "next_short_step_invalid")
    require(artifact.get("errors") == [], "artifact_errors_not_empty")

    scope = artifact.get("scope", {})
    require(scope.get("level_scope") == ["A1", "A1_PLUS"], "level_scope_invalid")
    require(scope.get("a2_status") == "LOCKED", "a2_status_invalid")
    require(scope.get("source_transcript_ids") == list(builder.m1_validator.EXPECTED_TRANSCRIPTS), "transcript_scope_invalid")

    authority = artifact.get("authority_contract", {})
    for key in (
        "canonical_promotion_allowed",
        "keyword_only_mapping_allowed",
        "free_form_fuzzy_matching_allowed",
        "hard_graph_mutation_allowed",
        "hard_prerequisite_creation_allowed",
        "hard_lesson_selection_allowed",
        "production_lesson_mapping_allowed",
        "a2_unlock_allowed",
    ):
        require(authority.get(key) is False, f"authority_boundary_invalid:{key}")
    require(authority.get("authority_status") == "non_authoritative", "authority_status_invalid")

    confirmation = artifact.get("operator_confirmation", {})
    require(confirmation.get("decision_id") == "KET99-PK-M2-OPERATOR-20260724-01", "decision_id_invalid")
    require(confirmation.get("decision_status") == "APPROVED_FOR_M2_METADATA_BRIDGE", "decision_status_invalid")
    require(confirmation.get("authorization_command") == "續跑任務", "authorization_command_invalid")
    require(confirmation.get("confirmed_record_count") == 35, "confirmed_record_count_invalid")

    bridge_records = artifact.get("bridge_records")
    rejected_records = artifact.get("rejected_records")
    require(isinstance(bridge_records, list), "bridge_records_invalid")
    require(isinstance(rejected_records, list), "rejected_records_invalid")
    if not isinstance(bridge_records, list):
        bridge_records = []
    if not isinstance(rejected_records, list):
        rejected_records = []

    seen_pku: set[str] = set()
    seen_identity: set[str] = set()
    exact_join_count = 0
    soft_identity_count = 0
    for row in bridge_records:
        require(isinstance(row, Mapping), "bridge_record_not_object")
        if not isinstance(row, Mapping):
            continue
        pku_id = str(row.get("pku_id") or "")
        identity_id = str(row.get("teaching_need_identity_id") or "")
        concept_id = str(row.get("pedagogical_concept_id") or "")
        require(bool(pku_id), "bridge_pku_id_missing")
        require(pku_id not in seen_pku, f"duplicate_pku_id:{pku_id}")
        seen_pku.add(pku_id)
        require(row.get("operator_confirmation") == "CONFIRMED_APPROVED", f"operator_confirmation_invalid:{pku_id}")
        require(row.get("final_disposition") == "CONFIRMED_PILOT_ADMISSION", f"final_disposition_invalid:{pku_id}")
        require(identity_id == f"TN:KET99:{concept_id}", f"teaching_need_identity_invalid:{pku_id}")
        require(identity_id not in seen_identity, f"duplicate_teaching_need_identity:{identity_id}")
        seen_identity.add(identity_id)
        require(row.get("level_scope") in (["A1"], ["A1_PLUS"], ["A1", "A1_PLUS"]), f"level_scope_invalid:{pku_id}")
        require(bool(row.get("skill_scope")), f"skill_scope_missing:{pku_id}")
        require(bool(row.get("teaching_roles")), f"teaching_roles_missing:{pku_id}")
        contract = row.get("lesson_eligibility_contract", {})
        require(contract.get("catalog_authority") == "A1FS_V1_M2_LESSON_CATALOG", f"catalog_authority_invalid:{pku_id}")
        require(contract.get("matching_mode") == "EXACT_CLOSED_ENUM_ONLY", f"matching_mode_invalid:{pku_id}")
        require(contract.get("soft_overlay_only") is True, f"soft_overlay_invalid:{pku_id}")
        require(contract.get("hard_lesson_selection_allowed") is False, f"hard_lesson_selection_invalid:{pku_id}")
        require(contract.get("production_lesson_mapping_allowed") is False, f"production_mapping_invalid:{pku_id}")
        require(contract.get("exact_lesson_ids") == [], f"exact_lesson_ids_not_empty:{pku_id}")
        refs = row.get("canonical_authority_refs")
        require(isinstance(refs, list), f"authority_refs_invalid:{pku_id}")
        if refs:
            exact_join_count += 1
            require(row.get("bridge_kind") == "EXISTING_AUTHORITY_JOIN", f"bridge_kind_invalid:{pku_id}")
            require(row.get("bridge_status") == "CONFIRMED_EXISTING_AUTHORITY_JOIN_READY", f"bridge_status_invalid:{pku_id}")
        else:
            soft_identity_count += 1
            require(row.get("bridge_kind") == "SOFT_TEACHING_NEED_IDENTITY", f"bridge_kind_invalid:{pku_id}")
            require(row.get("bridge_status") == "CONFIRMED_SOFT_TEACHING_NEED_IDENTITY_READY", f"bridge_status_invalid:{pku_id}")

    for row in rejected_records:
        require(isinstance(row, Mapping), "rejected_record_not_object")
        if not isinstance(row, Mapping):
            continue
        pku_id = str(row.get("pku_id") or "")
        require(pku_id not in seen_pku, f"duplicate_pku_id:{pku_id}")
        seen_pku.add(pku_id)
        require(row.get("operator_confirmation") == "CONFIRMED_REJECTED", f"rejected_confirmation_invalid:{pku_id}")
        require(row.get("final_disposition") == "REJECTED_EXAM_PROCEDURE_ONLY", f"rejected_disposition_invalid:{pku_id}")
        require(row.get("teaching_need_identity_id") is None, f"rejected_identity_present:{pku_id}")
        require(row.get("lesson_mapping_allowed") is False, f"rejected_lesson_mapping_allowed:{pku_id}")

    counts = artifact.get("counts", {})
    expected_counts = {
        "source_transcript_count": 5,
        "source_pku_count": 35,
        "confirmed_pilot_admission_count": 32,
        "confirmed_exam_procedure_rejection_count": 3,
        "existing_authority_join_count": 10,
        "soft_teaching_need_identity_count": 22,
        "teaching_need_identity_count": 32,
        "production_lesson_mapping_count": 0,
        "hard_graph_mutation_count": 0,
    }
    for key, expected in expected_counts.items():
        require(counts.get(key) == expected, f"count_invalid:{key}")
    require(len(bridge_records) == 32, "bridge_record_count_invalid")
    require(len(rejected_records) == 3, "rejected_record_count_invalid")
    require(exact_join_count == 10, "computed_exact_join_count_invalid")
    require(soft_identity_count == 22, "computed_soft_identity_count_invalid")
    require(len(seen_pku) == 35, "computed_pku_count_invalid")
    require(len(seen_identity) == 32, "computed_identity_count_invalid")

    claims = artifact.get("claim_boundaries", {})
    for key in (
        "lesson_eligibility_evaluated",
        "production_lesson_mapping_claimed",
        "canonical_authority_promoted",
        "hard_graph_modified",
        "learner_content_created",
        "mastery_claimed",
        "a2_unlocked",
    ):
        require(claims.get(key) is False, f"claim_boundary_invalid:{key}")

    stored_digest = artifact.get("artifact_sha256")
    unsigned = dict(artifact)
    unsigned.pop("artifact_sha256", None)
    require(stored_digest == builder._digest(unsigned), "artifact_sha256_invalid")

    return {
        "task_id": builder.TASK_ID,
        "validation_status": builder.PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        "counts": counts,
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILED",
        "next_short_step": builder.NEXT_SHORT_STEP if not errors else builder.TASK_ID,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    report = validate_artifact(_load_json(args.artifact))
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
