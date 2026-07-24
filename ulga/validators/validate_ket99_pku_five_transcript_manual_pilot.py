#!/usr/bin/env python3
"""Validate the five-transcript KET99 pedagogical knowledge-unit manual pilot."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validation-only enforcement for a non-authoritative five-transcript KET99 PKU pilot; "
    "no canonical content, hard graph edge, production lesson mapping, mastery, media, or A2 payload is produced."
)

TASK_ID = "KET99-PK-M1_FiveTranscriptPedagogicalKnowledgeUnitManualPilot"
SCHEMA_VERSION = "ket99.pedagogical_knowledge_unit.manual_pilot.manifest.v3"
PASS_STATUS = "PASS_KET99_PK_M1_PILOT_CANDIDATES_READY_FOR_OPERATOR_CONFIRMATION"
NEXT_SHORT_STEP = "KET99-PK-M2_OperatorConfirmationAndTeachingNeedIdentityBridge"
EXPECTED_TRANSCRIPTS = ("P005", "P006", "P008", "P023", "P026")
EXPECTED_SOURCE_SHA = {
    "P005": "79f56223fee93e5368c8b2aee34730c8acbb21e9eb841bd2722fcfd2a9b74e98",
    "P006": "68d1e277fd05024fd4044eab46f1d6090bd1e1409d822fd5905e6967e4eddb63",
    "P008": "bc867aa016de7f211620849b58f7a93a2c9dc44a21ef015a3b7704043f519369",
    "P023": "87db5c17cbef6e1be5333cc800b9945c82660fc528affdd948c383ef60c9c557",
    "P026": "023b09a568cbfdc1ba03d21f2400c669d77ce3e882bdb518d7e423dbfe67e20c",
}
EXPECTED_INDEX_FIELDS = (
    "pku_id",
    "source_transcript_id",
    "pedagogical_concept_id",
    "authority_ids",
    "lesson_mapping_status",
    "required_teaching_need_id",
    "disposition",
)
ALLOWED_MODES = {
    "LEARNER_LANGUAGE",
    "LEARNER_SKILL",
    "TEACHER_METHOD",
    "ERROR_REPAIR",
    "PRONUNCIATION_SUPPORT",
    "EXAM_PROCEDURE",
}
ALLOWED_TYPES = {
    "GRAMMAR_FORM",
    "LEXICAL_CONCEPT",
    "COMMUNICATIVE_FUNCTION",
    "LISTENING_SKILL",
    "SPEAKING_SKILL",
    "READING_STRATEGY",
    "WRITING_SKILL",
    "PRONUNCIATION_PATTERN",
    "ERROR_PATTERN",
    "TEACHING_ROUTINE",
    "EXAM_TASK_PROCEDURE",
}
ALLOWED_AUTHORITIES = {
    "GRAMMAR_BE_VERB_BASIC",
    "GRAMMAR_BE_INTERROGATIVES_A1",
    "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS",
    "GRAMMAR_ADVERB_PHRASES_A1",
    "GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS",
    "GRAMMAR_BECAUSE_REASON_CLAUSES_A1",
    "GRAMMAR_ADJECTIVE_PHRASES_A1",
}
CSV_COLUMNS = [
    "pku_id",
    "source_transcript_id",
    "knowledge_mode",
    "knowledge_type",
    "concept_label",
    "pedagogical_concept_id",
    "cefr_decision",
    "skill_scope",
    "teaching_roles",
    "authority_refs",
    "lesson_mapping_status",
    "review_status",
    "operator_confirmation",
    "disposition",
    "risk_flags",
    "evidence_anchor",
    "operator_decision",
    "operator_notes",
]


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("json_object_required")
    return value


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != CSV_COLUMNS:
            raise ValueError("csv_columns_invalid")
        return [dict(row) for row in reader]


def _index_records(artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    fields = artifact.get("pku_index_field_order")
    rows = artifact.get("pku_index")
    if fields != list(EXPECTED_INDEX_FIELDS) or not isinstance(rows, list):
        return []
    result: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, list) or len(row) != len(EXPECTED_INDEX_FIELDS):
            return []
        result.append(dict(zip(EXPECTED_INDEX_FIELDS, row, strict=True)))
    return result


def _csv_bytes(rows: Sequence[Mapping[str, str]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def validate_artifact(
    artifact: Mapping[str, Any], csv_rows: Sequence[Mapping[str, str]]
) -> dict[str, Any]:
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    require(artifact.get("task_id") == TASK_ID, "task_id_invalid")
    require(artifact.get("schema_version") == SCHEMA_VERSION, "schema_invalid")
    require(artifact.get("validation_status") == PASS_STATUS, "status_invalid")
    require(artifact.get("stop_reason") == "OPERATOR_CONFIRMATION_REQUIRED", "stop_reason_invalid")
    require(artifact.get("next_short_step") == NEXT_SHORT_STEP, "next_short_step_invalid")
    require(artifact.get("errors") == [], "artifact_errors_not_empty")

    scope = artifact.get("scope", {})
    require(scope.get("pilot_transcript_ids") == list(EXPECTED_TRANSCRIPTS), "scope_ids_invalid")
    require(scope.get("source_read_mode") == "FULL_TRANSCRIPT_MANUAL_REVIEW", "source_read_mode_invalid")
    require(scope.get("a2_status") == "LOCKED", "a2_status_invalid")

    authority = artifact.get("authority_contract", {})
    require(authority.get("authority_status") == "non_authoritative", "authority_status_invalid")
    for key in (
        "canonical_promotion_allowed",
        "keyword_only_mapping_allowed",
        "free_form_fuzzy_matching_allowed",
        "hard_graph_mutation_allowed",
        "hard_lesson_selection_allowed",
        "production_admission_before_operator_confirmation_allowed",
    ):
        require(authority.get(key) is False, f"authority_lock_invalid:{key}")

    defaults = artifact.get("record_defaults", {})
    expected_defaults = {
        "source_read_status": "FULL_TRANSCRIPT_READ",
        "source_span_precision": "FULL_TRANSCRIPT_SHA_PLUS_NORMALIZED_ANCHOR",
        "reviewer_type": "AI_ASSISTANT_UNDER_OPERATOR_APPROVED_SCOPE",
        "review_status": "AI_ASSISTED_MANUAL_REVIEWED",
        "operator_confirmation": "PENDING",
        "authority_status": "NON_AUTHORITATIVE_PEDAGOGICAL_REFERENCE",
        "production_admission_allowed": False,
        "production_mapping_claimed": False,
        "keyword_only_mapping_used": False,
        "keyword_only_mapping_allowed": False,
        "free_form_fuzzy_matching_allowed": False,
        "hard_prerequisite_creation_allowed": False,
        "hard_lesson_selection_allowed": False,
        "a2_lesson_mapping_allowed": False,
    }
    for key, expected in expected_defaults.items():
        require(defaults.get(key) == expected, f"default_invalid:{key}")

    inventory = artifact.get("source_inventory", {})
    require(isinstance(inventory, dict), "source_inventory_invalid")
    require(list(inventory) == list(EXPECTED_TRANSCRIPTS), "source_inventory_order_invalid")
    for transcript_id in EXPECTED_TRANSCRIPTS:
        source = inventory.get(transcript_id, {})
        require(source.get("read_status") == "FULL_TRANSCRIPT_READ", f"source_not_full:{transcript_id}")
        require(source.get("sha256") == EXPECTED_SOURCE_SHA[transcript_id], f"source_sha_invalid:{transcript_id}")

    bundle = artifact.get("record_bundle", {})
    require(bundle.get("record_count") == 35, "bundle_record_count_invalid")
    require(bundle.get("operator_fields") == ["operator_decision", "operator_notes"], "bundle_operator_fields_invalid")
    require(bundle.get("csv_sha256") == hashlib.sha256(_csv_bytes(csv_rows)).hexdigest(), "csv_digest_invalid")

    index_records = _index_records(artifact)
    require(len(index_records) == 35, "pku_index_count_invalid")
    require(len(csv_rows) == 35, "csv_count_invalid")

    csv_by_id = {row.get("pku_id", ""): row for row in csv_rows}
    index_ids: list[str] = []
    per_transcript: Counter[str] = Counter()
    dispositions: Counter[str] = Counter()
    mappings: Counter[str] = Counter()
    modes: Counter[str] = Counter()
    types: Counter[str] = Counter()

    for record in index_records:
        pku_id = str(record.get("pku_id") or "")
        transcript_id = str(record.get("source_transcript_id") or "")
        index_ids.append(pku_id)
        per_transcript[transcript_id] += 1
        dispositions[str(record.get("disposition") or "")] += 1
        mappings[str(record.get("lesson_mapping_status") or "")] += 1

        row = csv_by_id.get(pku_id)
        if row is None:
            errors.append(f"csv_missing_pku:{pku_id}")
            continue

        require(transcript_id in EXPECTED_TRANSCRIPTS, f"transcript_invalid:{pku_id}")
        require(pku_id.startswith(f"KET99-{transcript_id}-PKU"), f"pku_id_invalid:{pku_id}")
        require(row.get("source_transcript_id") == transcript_id, f"csv_transcript_mismatch:{pku_id}")
        require(row.get("pedagogical_concept_id") == record.get("pedagogical_concept_id"), f"csv_concept_mismatch:{pku_id}")
        require(row.get("lesson_mapping_status") == record.get("lesson_mapping_status"), f"csv_mapping_mismatch:{pku_id}")
        require(row.get("disposition") == record.get("disposition"), f"csv_disposition_mismatch:{pku_id}")
        require(bool(row.get("concept_label")), f"concept_label_missing:{pku_id}")
        require(bool(row.get("evidence_anchor")), f"evidence_anchor_missing:{pku_id}")
        require(row.get("knowledge_mode") in ALLOWED_MODES, f"knowledge_mode_invalid:{pku_id}")
        require(row.get("knowledge_type") in ALLOWED_TYPES, f"knowledge_type_invalid:{pku_id}")
        require(row.get("review_status") == defaults.get("review_status"), f"review_status_invalid:{pku_id}")
        require(row.get("operator_confirmation") == "PENDING", f"operator_confirmation_invalid:{pku_id}")
        require(row.get("operator_decision") == "", f"csv_operator_decision_not_blank:{pku_id}")
        require(row.get("operator_notes") == "", f"csv_operator_notes_not_blank:{pku_id}")

        modes[row["knowledge_mode"]] += 1
        types[row["knowledge_type"]] += 1
        authority_ids = record.get("authority_ids", [])
        require(isinstance(authority_ids, list), f"authority_ids_invalid:{pku_id}")
        require(set(authority_ids).issubset(ALLOWED_AUTHORITIES), f"authority_unknown:{pku_id}")
        csv_authorities = row.get("authority_refs", "").split("|") if row.get("authority_refs") else []
        require(csv_authorities == authority_ids, f"csv_authority_mismatch:{pku_id}")

        rejected = str(record.get("disposition") or "").startswith("REJECTED")
        mapping_status = record.get("lesson_mapping_status")
        if rejected:
            require(mapping_status == "NOT_ELIGIBLE", f"rejected_mapping_invalid:{pku_id}")
            require(not authority_ids, f"rejected_authority_present:{pku_id}")
            require(row.get("cefr_decision") == "REJECTED_EXAM_PROCEDURE_ONLY", f"rejected_cefr_invalid:{pku_id}")
        elif authority_ids:
            require(mapping_status == "EXACT_AUTHORITY_JOIN_READY", f"exact_join_invalid:{pku_id}")
            require(record.get("required_teaching_need_id") is None, f"unexpected_need_id:{pku_id}")
        else:
            require(mapping_status == "BLOCKED_MISSING_LESSON_TEACHING_NEED_IDENTITY", f"teaching_need_status_invalid:{pku_id}")
            require(record.get("required_teaching_need_id") == record.get("pedagogical_concept_id"), f"teaching_need_identity_invalid:{pku_id}")

    require(index_ids == [row.get("pku_id") for row in csv_rows], "csv_index_order_invalid")
    require(len(index_ids) == len(set(index_ids)), "duplicate_pku_id")
    require(per_transcript == Counter({value: 7 for value in EXPECTED_TRANSCRIPTS}), "per_source_count_invalid")
    require(dispositions["PILOT_ADMITTED_PENDING_OPERATOR"] == 32, "admitted_count_invalid")
    require(dispositions["REJECTED_EXAM_PROCEDURE_ONLY"] == 3, "rejected_count_invalid")
    require(mappings["EXACT_AUTHORITY_JOIN_READY"] == 10, "exact_join_count_invalid")
    require(mappings["BLOCKED_MISSING_LESSON_TEACHING_NEED_IDENTITY"] == 22, "pending_need_count_invalid")
    require(mappings["NOT_ELIGIBLE"] == 3, "not_eligible_count_invalid")
    require(ALLOWED_MODES.issubset(modes), "knowledge_mode_coverage_invalid")

    findings = artifact.get("pilot_findings", {})
    require(findings.get("exact_authority_join_is_possible_for_grammar_pkus") is True, "finding_exact_join_invalid")
    require(findings.get("non_grammar_lesson_teaching_need_identity_present") is False, "finding_need_identity_invalid")
    require(findings.get("production_lesson_mapping_count") == 0, "finding_mapping_count_invalid")
    require(findings.get("keyword_mapping_rejected") is True, "finding_keyword_invalid")

    counts = artifact.get("counts", {})
    expected_counts = {
        "source_transcript_count": 5,
        "pku_count": 35,
        "pilot_admitted_pending_operator_count": 32,
        "rejected_exam_procedure_count": 3,
        "exact_authority_join_ready_count": 10,
        "pending_teaching_need_identity_count": 22,
        "not_eligible_count": 3,
        "operator_confirmation_pending_count": 35,
        "production_admission_count": 0,
        "production_lesson_mapping_count": 0,
    }
    for key, expected in expected_counts.items():
        require(counts.get(key) == expected, f"count_invalid:{key}")
    require(counts.get("knowledge_mode_counts") == dict(sorted(modes.items())), "mode_counts_invalid")
    require(counts.get("knowledge_type_counts") == dict(sorted(types.items())), "type_counts_invalid")

    return {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS if not errors else "FAIL_KET99_PK_M1_MANUAL_PILOT_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
        "source_transcript_count": len(inventory),
        "pku_count": len(index_records),
        "exact_authority_join_ready_count": mappings["EXACT_AUTHORITY_JOIN_READY"],
        "pending_teaching_need_identity_count": mappings["BLOCKED_MISSING_LESSON_TEACHING_NEED_IDENTITY"],
        "rejected_exam_procedure_count": dispositions["REJECTED_EXAM_PROCEDURE_ONLY"],
        "production_lesson_mapping_count": 0,
        "operator_confirmation_required": True,
        "a2_status": "LOCKED",
        "stop_reason": "OPERATOR_CONFIRMATION_REQUIRED" if not errors else "VALIDATION_FAILED",
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = validate_artifact(load_json(args.json), load_csv(args.csv))
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    print(text, end="")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
