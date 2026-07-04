#!/usr/bin/env python3
"""Build a small static/offline E4S-P6 tagged-record smoke output.

This builder is intentionally non-runtime and non-ingestive. It uses a tiny
approved static seed embedded in this file to prove that P6-S2-compatible
records can be emitted and validated by the existing P6 static validator.

Blocked by design:
- no source crawling or PDF extraction
- no runtime learner answer capture
- no learner-state mutation
- no UI output
- no weak-point aggregation
- no generated remediation exercises
- no adaptive recommendation
"""
from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUT_PATH = BASE_DIR / "ulga" / "graph" / "e4s_p6_error_tagging_records.json"
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "e4s_p6_error_tagging_records_validation_report.json"

BUILDER_ID = "E4S_P6_I5_STATIC_RECORD_BUILDER"
BUILDER_SCHEMA_VERSION = "p6_i5_static_record_builder_v1"
TAXONOMY_VERSION = "p6_s1_v1"
RECORD_SCHEMA_VERSION = "p6_s2_v1"

APPROVED_STATIC_QUESTION_PACKAGES: list[dict[str, Any]] = [
    {
        "question_id": "Q_RV1_BUILDER_001",
        "source_type": "operator_reviewed_seed",
        "source_unit_id": "SRC_RV1_BUILDER_SMOKE_001",
        "level": "pre_a1",
        "question_type": "literal_what",
        "skill_area": "reading",
        "concept_tags": ["literal_comprehension", "detail_finding", "what_reference"],
        "cognitive_skill": "locate_information",
        "correct_answer": {"type": "normalized_text", "value_ref": "ANSWER_RV1_BUILDER_001"},
        "source_evidence_ref": "SRC_RV1_BUILDER_SMOKE_001:SENT_002",
        "taxonomy_version": TAXONOMY_VERSION,
        "schema_version": RECORD_SCHEMA_VERSION,
        "diagnosis_policy": {
            "when_wrong": {
                "error_type": "reading_detail_error",
                "error_detail": "wrong_what_reference",
                "diagnosis_confidence": "high",
                "diagnosis_basis": [
                    "tagged_question_taxonomy",
                    "learner_answer_mismatch",
                    "source_evidence_mismatch"
                ],
                "remediation_tag": "practice_literal_what_questions",
                "remediation_priority": "normal",
                "remediation_basis": ["error_detail_mapping"]
            }
        }
    },
    {
        "question_id": "Q_RV1_BUILDER_002",
        "source_type": "operator_reviewed_seed",
        "source_unit_id": "SRC_RV1_BUILDER_SMOKE_002",
        "level": "pre_a1",
        "question_type": "cloze_vocabulary",
        "skill_area": "vocabulary",
        "concept_tags": ["food_words"],
        "cognitive_skill": "produce_word",
        "correct_answer": {"type": "normalized_text", "value_ref": "ANSWER_RV1_BUILDER_002"},
        "source_evidence_ref": "SRC_RV1_BUILDER_SMOKE_002:SENT_004",
        "taxonomy_version": TAXONOMY_VERSION,
        "schema_version": RECORD_SCHEMA_VERSION,
        "diagnosis_policy": {
            "when_wrong": {
                "error_type": "vocabulary_gap",
                "error_detail": "unknown_word",
                "diagnosis_confidence": "medium",
                "diagnosis_basis": [
                    "tagged_question_taxonomy",
                    "learner_answer_mismatch"
                ],
                "remediation_tag": "vocabulary_food_words_review",
                "remediation_priority": "normal",
                "remediation_basis": ["error_detail_mapping", "concept_tag_mapping"],
                "expected_warning": "warn_single_answer_vocabulary_gap"
            }
        }
    }
]

APPROVED_STATIC_ANSWER_EVENTS: list[dict[str, Any]] = [
    {
        "question_id": "Q_RV1_BUILDER_001",
        "learner_ref": "LNR_PSEUDO_BUILDER_001",
        "attempt_id": "ATT_RV1_BUILDER_001",
        "attempt_index": 1,
        "learner_answer": "placeholder_wrong_what",
        "answer_format": "normalized_text",
        "is_correct": False,
        "scoring_method": "normalized_match",
        "answered_at": "2026-07-04T12:00:00+08:00"
    },
    {
        "question_id": "Q_RV1_BUILDER_002",
        "learner_ref": "LNR_PSEUDO_BUILDER_001",
        "attempt_id": "ATT_RV1_BUILDER_002",
        "attempt_index": 1,
        "learner_answer": "placeholder_unknown_food_word",
        "answer_format": "normalized_text",
        "is_correct": False,
        "scoring_method": "normalized_match",
        "answered_at": "2026-07-04T12:01:00+08:00"
    }
]


def stable_suffix(index: int) -> str:
    return f"{index:06d}"


def build_tagged_question_record(question: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "tagged_question_id": f"TQ_RV1_BUILDER_{stable_suffix(index)}",
        "question_id": question["question_id"],
        "source_type": question["source_type"],
        "source_unit_id": question["source_unit_id"],
        "level": question["level"],
        "question_type": question["question_type"],
        "skill_area": question["skill_area"],
        "concept_tags": deepcopy(question["concept_tags"]),
        "cognitive_skill": question["cognitive_skill"],
        "correct_answer": deepcopy(question["correct_answer"]),
        "source_evidence_ref": question["source_evidence_ref"],
        "taxonomy_version": TAXONOMY_VERSION,
        "schema_version": RECORD_SCHEMA_VERSION,
        "answer_format": "normalized_text",
        "notes": ["built_from_approved_static_smoke_seed"]
    }


def build_learner_answer_record(
    answer_event: dict[str, Any], tagged_question_id: str, index: int
) -> dict[str, Any]:
    return {
        "learner_answer_id": f"LA_RV1_BUILDER_{stable_suffix(index)}",
        "tagged_question_id": tagged_question_id,
        "question_id": answer_event["question_id"],
        "learner_ref": answer_event["learner_ref"],
        "attempt_id": answer_event["attempt_id"],
        "attempt_index": answer_event["attempt_index"],
        "learner_answer": answer_event["learner_answer"],
        "answer_format": answer_event["answer_format"],
        "is_correct": answer_event["is_correct"],
        "scoring_method": answer_event["scoring_method"],
        "answered_at": answer_event["answered_at"],
        "schema_version": RECORD_SCHEMA_VERSION
    }


def build_error_diagnosis_record(
    question: dict[str, Any],
    tagged_question: dict[str, Any],
    learner_answer: dict[str, Any],
    index: int,
) -> dict[str, Any] | None:
    if learner_answer["is_correct"] is True:
        return None
    policy = question["diagnosis_policy"]["when_wrong"]
    return {
        "error_diagnosis_id": f"ED_RV1_BUILDER_{stable_suffix(index)}",
        "learner_answer_id": learner_answer["learner_answer_id"],
        "tagged_question_id": tagged_question["tagged_question_id"],
        "question_id": learner_answer["question_id"],
        "is_correct": learner_answer["is_correct"],
        "error_type": policy["error_type"],
        "error_detail": policy["error_detail"],
        "diagnosis_confidence": policy["diagnosis_confidence"],
        "diagnosis_basis": deepcopy(policy["diagnosis_basis"]),
        "source_evidence_ref": tagged_question["source_evidence_ref"],
        "taxonomy_version": TAXONOMY_VERSION,
        "schema_version": RECORD_SCHEMA_VERSION
    }


def build_remediation_link_record(
    question: dict[str, Any],
    learner_answer: dict[str, Any],
    tagged_question: dict[str, Any],
    error_diagnosis: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    policy = question["diagnosis_policy"]["when_wrong"]
    return {
        "remediation_link_id": f"RL_RV1_BUILDER_{stable_suffix(index)}",
        "error_diagnosis_id": error_diagnosis["error_diagnosis_id"],
        "learner_answer_id": learner_answer["learner_answer_id"],
        "tagged_question_id": tagged_question["tagged_question_id"],
        "remediation_tag": policy["remediation_tag"],
        "remediation_priority": policy["remediation_priority"],
        "remediation_basis": deepcopy(policy["remediation_basis"]),
        "schema_version": RECORD_SCHEMA_VERSION
    }


def expected_case_result(question: dict[str, Any]) -> tuple[str, list[str]]:
    policy = question["diagnosis_policy"]["when_wrong"]
    warning = policy.get("expected_warning")
    if warning:
        return "PASS_WITH_WARNINGS", [warning]
    return "PASS", []


def build_records() -> dict[str, Any]:
    question_by_id = {question["question_id"]: question for question in APPROVED_STATIC_QUESTION_PACKAGES}
    tagged_question_records: list[dict[str, Any]] = []
    learner_answer_records: list[dict[str, Any]] = []
    error_diagnosis_records: list[dict[str, Any]] = []
    remediation_link_records: list[dict[str, Any]] = []
    sample_cases: list[dict[str, Any]] = []

    for index, answer_event in enumerate(APPROVED_STATIC_ANSWER_EVENTS, start=1):
        question = question_by_id[answer_event["question_id"]]
        tagged_question = build_tagged_question_record(question, index)
        learner_answer = build_learner_answer_record(answer_event, tagged_question["tagged_question_id"], index)
        error_diagnosis = build_error_diagnosis_record(question, tagged_question, learner_answer, index)

        tagged_question_records.append(tagged_question)
        learner_answer_records.append(learner_answer)

        records_under_test: dict[str, Any] = {
            "tagged_question_record": tagged_question,
            "learner_answer_record": learner_answer,
        }
        if error_diagnosis is not None:
            error_diagnosis_records.append(error_diagnosis)
            remediation_link = build_remediation_link_record(
                question, learner_answer, tagged_question, error_diagnosis, index
            )
            remediation_link_records.append(remediation_link)
            records_under_test["error_diagnosis_record"] = error_diagnosis
            records_under_test["remediation_link_record"] = remediation_link

        expected_result, expected_issue_codes = expected_case_result(question)
        sample_cases.append(
            {
                "sample_case_id": f"I5_BUILDER_SMOKE_{stable_suffix(index)}",
                "category": "builder_output_smoke_case",
                "expected_result": expected_result,
                "description": "Static builder output smoke case from approved non-runtime seed input.",
                "records_under_test": records_under_test,
                "expected_gate_outcomes": {},
                "expected_issue_codes": expected_issue_codes,
                "manual_review_note": None,
            }
        )

    return {
        "metadata": {
            "builder_id": BUILDER_ID,
            "schema_version": BUILDER_SCHEMA_VERSION,
            "source_task": "E4S-P6-I5_StaticRecordBuilderImplementation_OperatorApprovedStart",
            "run_mode": "static_offline_smoke_pilot",
            "taxonomy_version": TAXONOMY_VERSION,
            "record_schema_version": RECORD_SCHEMA_VERSION,
            "input_source": "embedded_approved_static_smoke_seed",
            "scope_limits": [
                "no_source_ingestion",
                "no_runtime_answer_capture",
                "no_learner_state_mutation",
                "no_ui_output",
                "no_weak_point_aggregation",
                "no_generated_remediation_exercises",
                "no_adaptive_recommendation"
            ]
        },
        "input_summary": {
            "question_package_count": len(APPROVED_STATIC_QUESTION_PACKAGES),
            "answer_event_count": len(APPROVED_STATIC_ANSWER_EVENTS),
            "approved_static_input": True,
            "source_evidence_ref_preserved": True,
            "learner_ref_pseudonymous": True
        },
        "generated_records": {
            "tagged_question_records": tagged_question_records,
            "learner_answer_records": learner_answer_records,
            "error_diagnosis_records": error_diagnosis_records,
            "remediation_link_records": remediation_link_records
        },
        "sample_cases": sample_cases,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def validate_output(payload: dict[str, Any]) -> dict[str, Any]:
    sys.path.insert(0, str(BASE_DIR))
    from ulga.validators.validate_e4s_p6_error_tagging import build_report

    return build_report(payload, OUTPUT_PATH)


def build() -> dict[str, Any]:
    output = build_records()
    write_json(OUTPUT_PATH, output)
    report = validate_output(output)
    write_json(REPORT_PATH, report)
    return report


def main() -> int:
    report = build()
    print(f"E4S P6 tagged-record builder validation result: {report['result']}")
    print(f"Output written to: {OUTPUT_PATH}")
    print(f"Validation report written to: {REPORT_PATH}")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
