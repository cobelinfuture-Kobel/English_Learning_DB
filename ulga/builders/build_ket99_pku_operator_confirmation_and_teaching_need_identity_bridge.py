#!/usr/bin/env python3
"""Materialize the confirmed KET99 PKU teaching-need identity bridge.

This milestone confirms the operator-reviewed five-transcript pilot without
promoting transcript evidence to canonical authority or mutating the M1 hard
graph. Exact grammar joins retain their existing authority references; the
remaining admitted PKUs receive deterministic soft teaching-need identities
for a later exact lesson-eligibility pass.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.validators import validate_ket99_pku_five_transcript_manual_pilot as m1_validator

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Operator-decision and metadata-only teaching-need identity bridge over the "
    "non-authoritative KET99 PKU pilot; no learner content, canonical promotion, "
    "hard graph mutation, production lesson mapping, mastery, media, or A2 payload is produced."
)

TASK_ID = "KET99-PK-M2_OperatorConfirmationAndTeachingNeedIdentityBridge"
SCHEMA_VERSION = "ket99.pedagogical_knowledge_unit.operator_confirmation_bridge.v1"
PASS_STATUS = "PASS_KET99_PK_M2_OPERATOR_CONFIRMED_TEACHING_NEED_IDENTITIES_READY"
NEXT_SHORT_STEP = "KET99-PK-M3_ExactLessonEligibilityAndPilotOverlayAdmission"

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_M1_JSON = REPO_ROOT / "ulga/reports/ket99_pku_pilot/ket99_pedagogical_knowledge_units.pilot.json"
DEFAULT_M1_CSV = REPO_ROOT / "ulga/reports/ket99_pku_pilot/ket99_pku_pilot_review.csv"
DEFAULT_DECISION = REPO_ROOT / "ulga/reports/ket99_pku_pilot/ket99_pku_m2_operator_decision.json"
DEFAULT_OUTPUT = REPO_ROOT / ".local/a1fs_v1/ket99_pku_m2/ket99_pku_operator_confirmation_bridge.safe.json"


class BridgeBuildError(ValueError):
    """Fail-closed bridge construction error."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise BridgeBuildError(f"json_object_required:{path}")
    return value


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    if not rows:
        raise BridgeBuildError(f"csv_rows_required:{path}")
    return rows


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
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


def _index_records(artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    fields = artifact.get("pku_index_field_order")
    rows = artifact.get("pku_index")
    if not isinstance(fields, list) or not isinstance(rows, list):
        raise BridgeBuildError("m1_pku_index_invalid")
    records: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, list) or len(row) != len(fields):
            raise BridgeBuildError("m1_pku_index_row_invalid")
        records.append(dict(zip(fields, row, strict=True)))
    return records


def _split_pipe(value: str) -> list[str]:
    return [part for part in value.split("|") if part]


def _level_scope(decision: str) -> list[str]:
    mapping = {
        "ADMITTED_A1": ["A1"],
        "ADMITTED_A1_PLUS": ["A1_PLUS"],
        "ADMITTED_A1_AND_A1_PLUS": ["A1", "A1_PLUS"],
    }
    if decision not in mapping:
        raise BridgeBuildError(f"admitted_cefr_decision_invalid:{decision}")
    return mapping[decision]


def _validate_decision(decision: Mapping[str, Any]) -> None:
    if decision.get("decision_id") != "KET99-PK-M2-OPERATOR-20260724-01":
        raise BridgeBuildError("operator_decision_id_invalid")
    if decision.get("decision_status") != "APPROVED_FOR_M2_METADATA_BRIDGE":
        raise BridgeBuildError("operator_decision_status_invalid")
    if decision.get("authorization_command") != "續跑任務":
        raise BridgeBuildError("operator_authorization_command_invalid")
    expected = [
        "CONFIRM_32_PILOT_ADMISSIONS",
        "CONFIRM_3_EXAM_PROCEDURE_REJECTIONS",
        "CREATE_22_SOFT_TEACHING_NEED_IDENTITIES",
    ]
    if decision.get("approved_actions") != expected:
        raise BridgeBuildError("operator_approved_actions_invalid")
    boundaries = decision.get("boundaries", {})
    for key in (
        "canonical_promotion_allowed",
        "hard_graph_mutation_allowed",
        "production_lesson_mapping_allowed",
        "a2_unlock_allowed",
    ):
        if boundaries.get(key) is not False:
            raise BridgeBuildError(f"operator_boundary_invalid:{key}")


def build_bridge(
    *,
    m1_artifact: Mapping[str, Any],
    m1_rows: Sequence[Mapping[str, str]],
    decision: Mapping[str, Any],
    m1_json_sha256: str,
    m1_csv_sha256: str,
    decision_sha256: str,
) -> dict[str, Any]:
    m1_report = m1_validator.validate_artifact(m1_artifact, m1_rows)
    if m1_report.get("validation_status") != m1_validator.PASS_STATUS:
        raise BridgeBuildError(f"m1_pilot_not_passed:{m1_report.get('errors')}")
    _validate_decision(decision)

    csv_by_id = {str(row.get("pku_id") or ""): row for row in m1_rows}
    bridge_records: list[dict[str, Any]] = []
    rejected_records: list[dict[str, Any]] = []

    for record in _index_records(m1_artifact):
        pku_id = str(record.get("pku_id") or "")
        row = csv_by_id.get(pku_id)
        if row is None:
            raise BridgeBuildError(f"m1_csv_row_missing:{pku_id}")
        concept_id = str(record.get("pedagogical_concept_id") or "")
        transcript_id = str(record.get("source_transcript_id") or "")
        disposition = str(record.get("disposition") or "")
        authority_refs = list(record.get("authority_ids") or [])
        source_lineage = {
            "pku_id": pku_id,
            "source_transcript_id": transcript_id,
            "pedagogical_concept_id": concept_id,
            "evidence_anchor_sha256": hashlib.sha256(
                str(row.get("evidence_anchor") or "").encode("utf-8")
            ).hexdigest(),
        }

        if disposition == "REJECTED_EXAM_PROCEDURE_ONLY":
            rejected_records.append({
                **source_lineage,
                "operator_confirmation": "CONFIRMED_REJECTED",
                "final_disposition": "REJECTED_EXAM_PROCEDURE_ONLY",
                "teaching_need_identity_id": None,
                "lesson_mapping_allowed": False,
                "rejection_reason": "EXAM_PROCEDURE_OUTSIDE_A1_A1PLUS_LEARNING_SCOPE",
            })
            continue
        if disposition != "PILOT_ADMITTED_PENDING_OPERATOR":
            raise BridgeBuildError(f"m1_disposition_unexpected:{pku_id}:{disposition}")

        identity_id = f"TN:KET99:{concept_id}"
        bridge_kind = "EXISTING_AUTHORITY_JOIN" if authority_refs else "SOFT_TEACHING_NEED_IDENTITY"
        bridge_status = (
            "CONFIRMED_EXISTING_AUTHORITY_JOIN_READY"
            if authority_refs
            else "CONFIRMED_SOFT_TEACHING_NEED_IDENTITY_READY"
        )
        bridge_records.append({
            **source_lineage,
            "operator_confirmation": "CONFIRMED_APPROVED",
            "final_disposition": "CONFIRMED_PILOT_ADMISSION",
            "teaching_need_identity_id": identity_id,
            "identity_class": str(row.get("knowledge_type") or ""),
            "knowledge_mode": str(row.get("knowledge_mode") or ""),
            "bridge_kind": bridge_kind,
            "bridge_status": bridge_status,
            "canonical_authority_refs": authority_refs,
            "level_scope": _level_scope(str(row.get("cefr_decision") or "")),
            "skill_scope": _split_pipe(str(row.get("skill_scope") or "")),
            "teaching_roles": _split_pipe(str(row.get("teaching_roles") or "")),
            "lesson_eligibility_contract": {
                "catalog_authority": "A1FS_V1_M2_LESSON_CATALOG",
                "matching_fields": ["skill_scope", "level_scope"],
                "matching_mode": "EXACT_CLOSED_ENUM_ONLY",
                "soft_overlay_only": True,
                "hard_lesson_selection_allowed": False,
                "production_lesson_mapping_allowed": False,
                "exact_lesson_ids": [],
            },
        })

    bridge_records.sort(key=lambda item: item["pku_id"])
    rejected_records.sort(key=lambda item: item["pku_id"])
    exact_join_count = sum(bool(row["canonical_authority_refs"]) for row in bridge_records)
    soft_identity_count = sum(not row["canonical_authority_refs"] for row in bridge_records)
    result = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "scope": {
            "level_scope": ["A1", "A1_PLUS"],
            "a2_status": "LOCKED",
            "source_transcript_ids": list(m1_validator.EXPECTED_TRANSCRIPTS),
        },
        "source_identity": {
            "m1_task_id": m1_validator.TASK_ID,
            "m1_json_sha256": m1_json_sha256,
            "m1_csv_sha256": m1_csv_sha256,
            "operator_decision_sha256": decision_sha256,
        },
        "operator_confirmation": {
            "decision_id": decision["decision_id"],
            "decision_status": decision["decision_status"],
            "authorization_command": decision["authorization_command"],
            "confirmed_record_count": len(bridge_records) + len(rejected_records),
        },
        "authority_contract": {
            "source_role": "third_party_teacher_delivery_reference",
            "authority_status": "non_authoritative",
            "canonical_promotion_allowed": False,
            "keyword_only_mapping_allowed": False,
            "free_form_fuzzy_matching_allowed": False,
            "hard_graph_mutation_allowed": False,
            "hard_prerequisite_creation_allowed": False,
            "hard_lesson_selection_allowed": False,
            "production_lesson_mapping_allowed": False,
            "a2_unlock_allowed": False,
        },
        "bridge_records": bridge_records,
        "rejected_records": rejected_records,
        "counts": {
            "source_transcript_count": len(m1_validator.EXPECTED_TRANSCRIPTS),
            "source_pku_count": len(bridge_records) + len(rejected_records),
            "confirmed_pilot_admission_count": len(bridge_records),
            "confirmed_exam_procedure_rejection_count": len(rejected_records),
            "existing_authority_join_count": exact_join_count,
            "soft_teaching_need_identity_count": soft_identity_count,
            "teaching_need_identity_count": len(bridge_records),
            "production_lesson_mapping_count": 0,
            "hard_graph_mutation_count": 0,
        },
        "claim_boundaries": {
            "lesson_eligibility_evaluated": False,
            "production_lesson_mapping_claimed": False,
            "canonical_authority_promoted": False,
            "hard_graph_modified": False,
            "learner_content_created": False,
            "mastery_claimed": False,
            "a2_unlocked": False,
        },
        "errors": [],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    result["artifact_sha256"] = _digest(result)
    return result


def build_from_paths(*, m1_json: Path, m1_csv: Path, decision_path: Path) -> dict[str, Any]:
    return build_bridge(
        m1_artifact=_load_json(m1_json),
        m1_rows=_load_csv(m1_csv),
        decision=_load_json(decision_path),
        m1_json_sha256=_file_digest(m1_json),
        m1_csv_sha256=_file_digest(m1_csv),
        decision_sha256=_file_digest(decision_path),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m1-json", type=Path, default=DEFAULT_M1_JSON)
    parser.add_argument("--m1-csv", type=Path, default=DEFAULT_M1_CSV)
    parser.add_argument("--decision", type=Path, default=DEFAULT_DECISION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    artifact = build_from_paths(m1_json=args.m1_json, m1_csv=args.m1_csv, decision_path=args.decision)
    _atomic_json(args.output, artifact)
    print(json.dumps({"validation_status": artifact["validation_status"], "counts": artifact["counts"], "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
