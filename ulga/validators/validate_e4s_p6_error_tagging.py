#!/usr/bin/env python3
"""Offline/static validator for E4S-P6 error-tagging records.

Default input is the I1 golden sample fixture. This validator is static: it
reads JSON, computes case results, optionally writes a report, and does not
mutate learner state, runtime state, UI, weak-point summaries, or adaptive
recommendations.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_PATH = BASE_DIR / "ulga" / "fixtures" / "e4s_p6_error_tagging_golden_sample_v1.json"
DEFAULT_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "e4s_p6_error_tagging_validation_report.json"

VALIDATOR_ID = "E4S_P6_I2_STATIC_VALIDATOR"
SCHEMA_VERSION = "p6_i2_validator_report_v1"

GATES = [
    "record_shape_gate",
    "link_integrity_gate",
    "source_trace_gate",
    "taxonomy_gate",
    "compatibility_gate",
    "diagnosis_safety_gate",
    "non_generation_boundary_gate",
]

ACTIVE_READING_V1_QUESTION_TYPES = {
    "literal_who",
    "literal_what",
    "literal_where",
    "true_false",
    "sentence_ordering",
    "cloze_vocabulary",
}
DEFERRED_QUESTION_TYPES = {
    "multiple_choice",
    "fill_blank",
    "matching",
    "short_answer",
    "word_ordering",
    "error_correction",
    "reading_comprehension",
    "picture_description",
    "listening_choice",
    "dictation",
    "translation",
    "writing_prompt",
    "speaking_response",
}
ALLOWED_QUESTION_TYPES = ACTIVE_READING_V1_QUESTION_TYPES | DEFERRED_QUESTION_TYPES
ALLOWED_SKILL_AREAS = {
    "reading",
    "grammar",
    "vocabulary",
    "sentence_structure",
    "spelling",
    "phonics",
    "listening",
    "writing",
    "speaking",
    "comprehension",
    "inference",
}
ALLOWED_COGNITIVE_SKILLS = {
    "recognize",
    "recall",
    "locate_information",
    "match_information",
    "sequence_information",
    "apply_rule",
    "choose_answer",
    "produce_word",
    "produce_sentence",
    "correct_error",
    "infer_meaning",
    "summarize",
}
ALLOWED_CONCEPT_TAGS = {
    "literal_comprehension",
    "detail_finding",
    "explicit_detail",
    "who_reference",
    "what_reference",
    "where_reference",
    "sequence",
    "source_sentence_order",
    "picture_text_matching",
    "character_action",
    "setting",
    "main_idea",
    "cause_effect",
    "inference",
    "reference_word",
    "animal_words",
    "school_objects",
    "family_words",
    "food_words",
    "color_words",
    "number_words",
    "action_verbs",
    "place_words",
    "be_verb",
    "present_simple",
    "third_person_singular_s",
    "sentence_order",
    "word_order",
    "subject_verb_agreement",
    "simple_sentence",
    "svo_sentence",
    "sentence_fragment",
}
ALLOWED_ERROR_TYPES = {
    "concept_error",
    "rule_application_error",
    "vocabulary_gap",
    "question_misread",
    "careless_error",
    "spelling_error",
    "sentence_structure_error",
    "insufficient_output",
    "reading_detail_error",
    "source_evidence_error",
    "answer_format_error",
    "unknown_error",
}
ALLOWED_ERROR_DETAILS = {
    "missed_explicit_detail",
    "wrong_who_reference",
    "wrong_what_reference",
    "wrong_where_reference",
    "wrong_sequence_order",
    "source_sentence_mismatch",
    "picture_text_mismatch",
    "literal_question_misread",
    "unsupported_answer_from_source",
    "unknown_word",
    "wrong_word_meaning",
    "confused_similar_words",
    "wrong_topic_word",
    "color_word_confusion",
    "number_word_confusion",
    "place_word_confusion",
    "action_verb_confusion",
    "missing_third_person_s",
    "wrong_be_verb",
    "wrong_word_order",
    "spelling_blocks_answer",
    "sentence_fragment",
    "missing_subject",
    "missing_verb",
    "incomplete_answer",
    "answer_too_short",
    "wrong_answer_format",
    "not_enough_evidence",
    "needs_human_review",
}
ALLOWED_REMEDIATION_TAGS = {
    "practice_literal_who_questions",
    "practice_literal_what_questions",
    "practice_literal_where_questions",
    "practice_reading_detail_questions",
    "practice_sentence_ordering",
    "practice_source_evidence_lookup",
    "vocabulary_school_objects_review",
    "vocabulary_food_words_review",
    "vocabulary_animal_words_review",
    "vocabulary_color_words_review",
    "vocabulary_number_words_review",
    "vocabulary_home_words_review",
    "vocabulary_place_words_review",
    "vocabulary_action_verbs_review",
    "practice_third_person_s",
    "practice_present_simple_he_she_it",
    "practice_word_order",
    "rebuild_svo_sentence",
    "practice_complete_answer_sentence",
    "human_review_required",
    "no_remediation_assigned",
}

ERROR_DETAIL_BY_TYPE = {
    "reading_detail_error": {
        "missed_explicit_detail",
        "wrong_who_reference",
        "wrong_what_reference",
        "wrong_where_reference",
        "wrong_sequence_order",
        "source_sentence_mismatch",
        "picture_text_mismatch",
        "literal_question_misread",
        "unsupported_answer_from_source",
    },
    "source_evidence_error": {
        "source_sentence_mismatch",
        "unsupported_answer_from_source",
        "picture_text_mismatch",
    },
    "vocabulary_gap": {
        "unknown_word",
        "wrong_word_meaning",
        "confused_similar_words",
        "wrong_topic_word",
        "color_word_confusion",
        "number_word_confusion",
        "place_word_confusion",
        "action_verb_confusion",
    },
    "question_misread": {
        "literal_question_misread",
        "wrong_who_reference",
        "wrong_what_reference",
        "wrong_where_reference",
    },
    "rule_application_error": {
        "missing_third_person_s",
        "wrong_be_verb",
        "wrong_word_order",
    },
    "concept_error": {
        "missing_third_person_s",
        "wrong_be_verb",
        "wrong_word_order",
    },
    "spelling_error": {"spelling_blocks_answer"},
    "sentence_structure_error": {"wrong_word_order", "sentence_fragment", "missing_subject", "missing_verb"},
    "insufficient_output": {"incomplete_answer", "answer_too_short", "sentence_fragment"},
    "answer_format_error": {"wrong_answer_format", "incomplete_answer", "answer_too_short"},
    "unknown_error": {"not_enough_evidence", "needs_human_review"},
    "careless_error": {"not_enough_evidence", "needs_human_review"},
}
VOCAB_REMEDIATION_TAGS = {tag for tag in ALLOWED_REMEDIATION_TAGS if tag.startswith("vocabulary_")}
REMEDIATION_BY_DETAIL = {
    "wrong_who_reference": {"practice_literal_who_questions", "practice_source_evidence_lookup"},
    "wrong_what_reference": {"practice_literal_what_questions", "practice_reading_detail_questions"},
    "wrong_where_reference": {"practice_literal_where_questions", "practice_source_evidence_lookup"},
    "missed_explicit_detail": {"practice_reading_detail_questions", "practice_source_evidence_lookup"},
    "literal_question_misread": {"practice_reading_detail_questions", "human_review_required"},
    "missing_third_person_s": {"practice_third_person_s", "practice_present_simple_he_she_it"},
    "not_enough_evidence": {"human_review_required", "no_remediation_assigned"},
    "needs_human_review": {"human_review_required"},
}

RECORD_DEFINITIONS = {
    "tagged_question_record": (
        "tagged_question_id",
        "TQ_",
        {
            "tagged_question_id",
            "question_id",
            "question_type",
            "skill_area",
            "concept_tags",
            "cognitive_skill",
            "taxonomy_version",
            "schema_version",
        },
    ),
    "learner_answer_record": (
        "learner_answer_id",
        "LA_",
        {
            "learner_answer_id",
            "tagged_question_id",
            "question_id",
            "learner_ref",
            "learner_answer",
            "is_correct",
            "schema_version",
        },
    ),
    "error_diagnosis_record": (
        "error_diagnosis_id",
        "ED_",
        {
            "error_diagnosis_id",
            "learner_answer_id",
            "tagged_question_id",
            "question_id",
            "error_type",
            "error_detail",
            "diagnosis_confidence",
            "taxonomy_version",
            "schema_version",
        },
    ),
    "remediation_link_record": (
        "remediation_link_id",
        "RL_",
        {
            "remediation_link_id",
            "error_diagnosis_id",
            "learner_answer_id",
            "tagged_question_id",
            "remediation_tag",
            "remediation_priority",
            "remediation_basis",
            "schema_version",
        },
    ),
}


def issue(
    severity: str,
    code: str,
    gate: str,
    message: str,
    *,
    sample_case_id: str | None = None,
    record_type: str | None = None,
    record_id: str | None = None,
    field: str | None = None,
    expected: Any = None,
    actual: Any = None,
    source_ref: str | None = None,
) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "gate": gate,
        "sample_case_id": sample_case_id,
        "record_type": record_type,
        "record_id": record_id,
        "field": field,
        "message": message,
        "expected": expected,
        "actual": actual,
        "source_ref": source_ref,
    }


def rid(record_type: str, record: dict[str, Any]) -> str | None:
    id_field = RECORD_DEFINITIONS[record_type][0]
    value = record.get(id_field)
    return value if isinstance(value, str) else None


def records_in(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = case.get("records_under_test", {})
    if not isinstance(records, dict):
        return {}
    return {name: value for name, value in records.items() if name in RECORD_DEFINITIONS and isinstance(value, dict)}


def result_from_issues(items: list[dict[str, Any]]) -> str:
    severities = {item["severity"] for item in items}
    if "FAIL" in severities:
        return "FAIL"
    if "REVIEW" in severities:
        return "REVIEW_REQUIRED"
    if "WARN" in severities:
        return "PASS_WITH_WARNINGS"
    return "PASS"


def overall_gate(gates: dict[str, str]) -> str:
    values = [gates.get(gate, "NOT_RUN") for gate in GATES]
    if "FAIL" in values:
        return "FAIL"
    if "REVIEW_REQUIRED" in values:
        return "REVIEW_REQUIRED"
    if "PASS_WITH_WARNINGS" in values:
        return "PASS_WITH_WARNINGS"
    if values and all(value == "PASS" for value in values):
        return "PASS"
    return "NOT_RUN"


def gate_metrics(items: list[dict[str, Any]]) -> dict[str, str]:
    gates = {gate: result_from_issues([item for item in items if item["gate"] == gate]) for gate in GATES}
    gates["overall_gate"] = overall_gate(gates)
    return gates


def validate_shape(case: dict[str, Any]) -> list[dict[str, Any]]:
    sample_id = str(case.get("sample_case_id", "UNKNOWN_SAMPLE_CASE"))
    out: list[dict[str, Any]] = []
    required_case = {
        "sample_case_id",
        "category",
        "expected_result",
        "description",
        "records_under_test",
        "expected_gate_outcomes",
        "expected_issue_codes",
        "manual_review_note",
    }
    for field in sorted(required_case - set(case)):
        out.append(issue("FAIL", "missing_required_field", "record_shape_gate", "sample case missing required field", sample_case_id=sample_id, field=field))
    for record_type, record in records_in(case).items():
        id_field, prefix, required = RECORD_DEFINITIONS[record_type]
        record_id = rid(record_type, record)
        for field in sorted(required - set(record)):
            code = "missing_schema_version" if field == "schema_version" else "missing_taxonomy_version" if field == "taxonomy_version" else "missing_required_field"
            out.append(issue("FAIL", code, "record_shape_gate", f"{record_type} missing required field", sample_case_id=sample_id, record_type=record_type, record_id=record_id, field=field))
        value = record.get(id_field)
        if id_field in record and (not isinstance(value, str) or not value.startswith(prefix)):
            out.append(issue("FAIL", "invalid_record_id_prefix", "record_shape_gate", f"{id_field} has invalid prefix", sample_case_id=sample_id, record_type=record_type, record_id=value if isinstance(value, str) else None, field=id_field, expected=prefix, actual=value))
        if record_type == "tagged_question_record" and "concept_tags" in record:
            tags = record["concept_tags"]
            if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
                out.append(issue("FAIL", "invalid_field_type", "record_shape_gate", "concept_tags must be array[string]", sample_case_id=sample_id, record_type=record_type, record_id=record_id, field="concept_tags", actual=type(tags).__name__))
    return out


def validate_links(case: dict[str, Any]) -> list[dict[str, Any]]:
    sample_id = str(case.get("sample_case_id", "UNKNOWN_SAMPLE_CASE"))
    records = records_in(case)
    tq, la, ed, rl = (records.get(name) for name in ("tagged_question_record", "learner_answer_record", "error_diagnosis_record", "remediation_link_record"))
    out: list[dict[str, Any]] = []
    if tq and la and la.get("tagged_question_id") != tq.get("tagged_question_id"):
        out.append(issue("FAIL", "broken_tagged_question_link", "link_integrity_gate", "learner_answer_record tagged_question_id does not resolve", sample_case_id=sample_id, record_type="learner_answer_record", record_id=rid("learner_answer_record", la), field="tagged_question_id", expected=tq.get("tagged_question_id"), actual=la.get("tagged_question_id")))
    if la and ed and ed.get("learner_answer_id") != la.get("learner_answer_id"):
        out.append(issue("FAIL", "broken_learner_answer_link", "link_integrity_gate", "error_diagnosis_record learner_answer_id does not resolve", sample_case_id=sample_id, record_type="error_diagnosis_record", record_id=rid("error_diagnosis_record", ed), field="learner_answer_id", expected=la.get("learner_answer_id"), actual=ed.get("learner_answer_id")))
    if ed and rl and rl.get("error_diagnosis_id") != ed.get("error_diagnosis_id"):
        out.append(issue("FAIL", "broken_error_diagnosis_link", "link_integrity_gate", "remediation_link_record error_diagnosis_id does not resolve", sample_case_id=sample_id, record_type="remediation_link_record", record_id=rid("remediation_link_record", rl), field="error_diagnosis_id", expected=ed.get("error_diagnosis_id"), actual=rl.get("error_diagnosis_id")))
    question_ids = {record.get("question_id") for record in (tq, la, ed) if isinstance(record, dict) and "question_id" in record}
    if len(question_ids) > 1:
        out.append(issue("FAIL", "question_id_mismatch", "link_integrity_gate", "linked records disagree on question_id", sample_case_id=sample_id, field="question_id", actual=sorted(question_ids)))
    return out


def validate_source_trace(case: dict[str, Any]) -> list[dict[str, Any]]:
    sample_id = str(case.get("sample_case_id", "UNKNOWN_SAMPLE_CASE"))
    records = records_in(case)
    tq, ed = records.get("tagged_question_record"), records.get("error_diagnosis_record")
    if not tq or not ed:
        return []
    is_reading_v1 = tq.get("question_type") in ACTIVE_READING_V1_QUESTION_TYPES and tq.get("skill_area") in {"reading", "comprehension", "vocabulary", "sentence_structure"}
    source_grounded = ed.get("error_type") in {"reading_detail_error", "source_evidence_error", "question_misread"}
    if not (is_reading_v1 and source_grounded):
        return []
    out: list[dict[str, Any]] = []
    tagged_ref, diag_ref = tq.get("source_evidence_ref"), ed.get("source_evidence_ref")
    if not diag_ref:
        out.append(issue("FAIL", "missing_source_evidence_ref", "source_trace_gate", "source-grounded diagnosis missing source_evidence_ref", sample_case_id=sample_id, record_type="error_diagnosis_record", record_id=rid("error_diagnosis_record", ed), field="source_evidence_ref"))
        out.append(issue("FAIL", "source_grounded_diagnosis_without_evidence", "source_trace_gate", "source-grounded diagnosis has no evidence reference", sample_case_id=sample_id, record_type="error_diagnosis_record", record_id=rid("error_diagnosis_record", ed), field="source_evidence_ref"))
    elif tagged_ref and diag_ref != tagged_ref:
        out.append(issue("FAIL", "source_evidence_ref_mismatch", "source_trace_gate", "source_evidence_ref mismatch", sample_case_id=sample_id, record_type="error_diagnosis_record", record_id=rid("error_diagnosis_record", ed), field="source_evidence_ref", expected=tagged_ref, actual=diag_ref))
    return out


def validate_taxonomy(case: dict[str, Any]) -> list[dict[str, Any]]:
    sample_id = str(case.get("sample_case_id", "UNKNOWN_SAMPLE_CASE"))
    records = records_in(case)
    tq, ed, rl = records.get("tagged_question_record"), records.get("error_diagnosis_record"), records.get("remediation_link_record")
    out: list[dict[str, Any]] = []
    if tq:
        for field, allowed, code in [("question_type", ALLOWED_QUESTION_TYPES, "unknown_question_type"), ("skill_area", ALLOWED_SKILL_AREAS, "unknown_skill_area"), ("cognitive_skill", ALLOWED_COGNITIVE_SKILLS, "unknown_cognitive_skill")]:
            if field in tq and tq.get(field) not in allowed:
                out.append(issue("FAIL", code, "taxonomy_gate", f"{field} is not controlled", sample_case_id=sample_id, record_type="tagged_question_record", record_id=rid("tagged_question_record", tq), field=field, actual=tq.get(field)))
        for tag in tq.get("concept_tags", []) if isinstance(tq.get("concept_tags"), list) else []:
            if tag not in ALLOWED_CONCEPT_TAGS:
                out.append(issue("FAIL", "unknown_concept_tag", "taxonomy_gate", "concept tag is not controlled", sample_case_id=sample_id, record_type="tagged_question_record", record_id=rid("tagged_question_record", tq), field="concept_tags", actual=tag))
    if ed:
        if ed.get("error_type") not in ALLOWED_ERROR_TYPES:
            out.append(issue("FAIL", "unknown_error_type", "taxonomy_gate", "error_type is not controlled", sample_case_id=sample_id, record_type="error_diagnosis_record", record_id=rid("error_diagnosis_record", ed), field="error_type", actual=ed.get("error_type")))
        if ed.get("error_detail") not in ALLOWED_ERROR_DETAILS:
            out.append(issue("FAIL", "unknown_error_detail", "taxonomy_gate", "error_detail is not controlled", sample_case_id=sample_id, record_type="error_diagnosis_record", record_id=rid("error_diagnosis_record", ed), field="error_detail", actual=ed.get("error_detail")))
    if rl and rl.get("remediation_tag") not in ALLOWED_REMEDIATION_TAGS:
        out.append(issue("FAIL", "unknown_remediation_tag", "taxonomy_gate", "remediation_tag is not controlled", sample_case_id=sample_id, record_type="remediation_link_record", record_id=rid("remediation_link_record", rl), field="remediation_tag", actual=rl.get("remediation_tag")))
    return out


def validate_compatibility(case: dict[str, Any]) -> list[dict[str, Any]]:
    sample_id = str(case.get("sample_case_id", "UNKNOWN_SAMPLE_CASE"))
    records = records_in(case)
    tq, ed, rl = records.get("tagged_question_record"), records.get("error_diagnosis_record"), records.get("remediation_link_record")
    out: list[dict[str, Any]] = []
    if tq and tq.get("question_type") in DEFERRED_QUESTION_TYPES:
        out.append(issue("FAIL", "blocked_reading_v1_future_question_type", "compatibility_gate", "Reading V1 record uses deferred question_type", sample_case_id=sample_id, record_type="tagged_question_record", record_id=rid("tagged_question_record", tq), field="question_type", actual=tq.get("question_type")))
    if ed:
        allowed = ERROR_DETAIL_BY_TYPE.get(ed.get("error_type"))
        if allowed is not None and ed.get("error_detail") not in allowed:
            out.append(issue("FAIL", "blocked_error_type_error_detail", "compatibility_gate", "error_detail is incompatible with error_type", sample_case_id=sample_id, record_type="error_diagnosis_record", record_id=rid("error_diagnosis_record", ed), field="error_detail", expected=sorted(allowed), actual=ed.get("error_detail")))
    if tq and ed and rl:
        detail, tag = ed.get("error_detail"), rl.get("remediation_tag")
        allowed_tags = set(REMEDIATION_BY_DETAIL.get(detail, set()))
        if detail in {"unknown_word", "wrong_word_meaning", "confused_similar_words", "wrong_topic_word", "color_word_confusion", "number_word_confusion", "place_word_confusion", "action_verb_confusion"}:
            allowed_tags |= VOCAB_REMEDIATION_TAGS
        if allowed_tags and tag not in allowed_tags and tag not in {"human_review_required", "no_remediation_assigned"}:
            out.append(issue("FAIL", "blocked_error_detail_remediation_tag", "compatibility_gate", "remediation_tag is incompatible with error_detail", sample_case_id=sample_id, record_type="remediation_link_record", record_id=rid("remediation_link_record", rl), field="remediation_tag", expected=sorted(allowed_tags), actual=tag))
        if tq.get("question_type") == "literal_where" and detail == "missing_third_person_s":
            out.append(issue("FAIL", "blocked_error_detail_remediation_tag", "compatibility_gate", "literal_where cannot route to grammar-only remediation", sample_case_id=sample_id, record_type="remediation_link_record", record_id=rid("remediation_link_record", rl), field="remediation_tag", actual=tag))
        if rl.get("remediation_basis") == ["concept_tag_mapping"]:
            out.append(issue("WARN", "warn_remediation_from_concept_only", "compatibility_gate", "remediation selected from concept_tags only", sample_case_id=sample_id, record_type="remediation_link_record", record_id=rid("remediation_link_record", rl), field="remediation_basis", actual=rl.get("remediation_basis")))
    if ed and ed.get("error_type") == "vocabulary_gap" and ed.get("error_detail") == "unknown_word":
        out.append(issue("WARN", "warn_single_answer_vocabulary_gap", "diagnosis_safety_gate", "single-answer vocabulary_gap should remain warning-level evidence", sample_case_id=sample_id, record_type="error_diagnosis_record", record_id=rid("error_diagnosis_record", ed), field="error_type"))
    return out


def validate_diagnosis_safety(case: dict[str, Any]) -> list[dict[str, Any]]:
    sample_id = str(case.get("sample_case_id", "UNKNOWN_SAMPLE_CASE"))
    records = records_in(case)
    ed, rl = records.get("error_diagnosis_record"), records.get("remediation_link_record")
    if not ed:
        return []
    out: list[dict[str, Any]] = []
    basis = ed.get("diagnosis_basis", [])
    if ed.get("error_type") == "concept_error" and ed.get("diagnosis_confidence") == "high" and not {"repeated_same_error", "human_review_note", "human_confirmed"}.intersection(set(basis if isinstance(basis, list) else [])):
        out.append(issue("FAIL", "unsafe_concept_error_high_confidence", "diagnosis_safety_gate", "concept_error cannot be high confidence from one answer", sample_case_id=sample_id, record_type="error_diagnosis_record", record_id=rid("error_diagnosis_record", ed), field="diagnosis_confidence"))
    if ed.get("error_type") == "unknown_error" and ed.get("error_detail") not in {"not_enough_evidence", "needs_human_review"}:
        out.append(issue("FAIL", "unknown_error_with_specific_detail", "diagnosis_safety_gate", "unknown_error cannot carry specific detail", sample_case_id=sample_id, record_type="error_diagnosis_record", record_id=rid("error_diagnosis_record", ed), field="error_detail", actual=ed.get("error_detail")))
    remediation_tag = rl.get("remediation_tag") if rl else None
    if ed.get("error_type") == "unknown_error" and remediation_tag not in {None, "human_review_required", "no_remediation_assigned"}:
        out.append(issue("FAIL", "unknown_error_with_specific_remediation", "diagnosis_safety_gate", "unknown_error cannot route to specific remediation", sample_case_id=sample_id, record_type="remediation_link_record", record_id=rid("remediation_link_record", rl) if rl else None, field="remediation_tag", actual=remediation_tag))
    if ed.get("error_type") == "careless_error":
        out.append(issue("REVIEW", "careless_error_requires_review", "diagnosis_safety_gate", "careless_error requires human review", sample_case_id=sample_id, record_type="error_diagnosis_record", record_id=rid("error_diagnosis_record", ed), field="error_type"))
    if ed.get("error_type") == "question_misread" and ed.get("diagnosis_confidence") != "human_confirmed":
        out.append(issue("REVIEW", "question_misread_requires_review", "diagnosis_safety_gate", "question_misread without learner explanation requires review", sample_case_id=sample_id, record_type="error_diagnosis_record", record_id=rid("error_diagnosis_record", ed), field="error_type"))
    if ed.get("requires_human_review") is True and remediation_tag not in {None, "human_review_required"}:
        out.append(issue("FAIL", "missing_human_review_required_for_unsafe_diagnosis", "diagnosis_safety_gate", "unsafe diagnosis must route to human_review_required", sample_case_id=sample_id, record_type="remediation_link_record", record_id=rid("remediation_link_record", rl) if rl else None, field="remediation_tag", actual=remediation_tag))
    return out


def validate_boundary(case: dict[str, Any]) -> list[dict[str, Any]]:
    sample_id = str(case.get("sample_case_id", "UNKNOWN_SAMPLE_CASE"))
    rl = records_in(case).get("remediation_link_record")
    if not rl:
        return []
    generated_fields = sorted(field for field in rl if field.startswith("generated_") or field.endswith("_preview"))
    if generated_fields:
        return [issue("FAIL", "remediation_link_contains_generated_content", "non_generation_boundary_gate", "remediation_link_record contains generated content", sample_case_id=sample_id, record_type="remediation_link_record", record_id=rid("remediation_link_record", rl), field=",".join(generated_fields), actual=generated_fields)]
    return []


def validate_case(case: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for validator in (
        validate_shape,
        validate_links,
        validate_source_trace,
        validate_taxonomy,
        validate_compatibility,
        validate_diagnosis_safety,
        validate_boundary,
    ):
        items.extend(validator(case))
    gates = gate_metrics(items)
    actual_result = gates["overall_gate"]
    expected_codes = case.get("expected_issue_codes", [])
    actual_codes = [item["code"] for item in items]
    alignment = None
    if isinstance(case.get("expected_result"), str) and isinstance(expected_codes, list):
        alignment = {
            "expected_result": case["expected_result"],
            "actual_result": actual_result,
            "expected_issue_codes": expected_codes,
            "actual_issue_codes": actual_codes,
            "result_matches": case["expected_result"] == actual_result,
            "issue_codes_match": sorted(expected_codes) == sorted(actual_codes),
        }
        alignment["matches"] = alignment["result_matches"] and alignment["issue_codes_match"]
    return {
        "sample_case_id": case.get("sample_case_id"),
        "category": case.get("category"),
        "expected_result": case.get("expected_result"),
        "actual_result": actual_result,
        "gate_metrics": gates,
        "issues": items,
        "expected_alignment": alignment,
    }


def count_records(cases: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter()
    for case in cases:
        for record_type in records_in(case):
            counts[record_type] += 1
    return {
        "total_tagged_question_records": counts["tagged_question_record"],
        "total_learner_answer_records": counts["learner_answer_record"],
        "total_error_diagnosis_records": counts["error_diagnosis_record"],
        "total_remediation_link_records": counts["remediation_link_record"],
    }


def build_report(payload: Any, input_path: Path) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "validator_id": VALIDATOR_ID,
            "schema_version": SCHEMA_VERSION,
            "result": "NOT_RUN",
            "summary": {},
            "issues": [issue("FAIL", "invalid_field_type", "record_shape_gate", "input root must be an object")],
            "record_counts": {},
            "gate_metrics": {"overall_gate": "NOT_RUN"},
            "case_results": [],
            "input_path": str(input_path),
            "next_action_hint": "Fix input JSON root shape.",
        }
    cases = [case for case in payload.get("sample_cases", []) if isinstance(case, dict)]
    case_results = [validate_case(case) for case in cases]
    all_issues = [item for case in case_results for item in case["issues"]]
    result_counts = Counter(case["actual_result"] for case in case_results)
    issue_counts = Counter(item["code"] for item in all_issues)
    alignments = [case["expected_alignment"]["matches"] for case in case_results if case.get("expected_alignment") is not None]
    fixture_mode = bool(alignments)
    result = "PASS" if fixture_mode and all(alignments) else result_from_issues(all_issues)
    record_counts = count_records(cases)
    summary = {
        **record_counts,
        "pass_count": result_counts["PASS"],
        "warn_count": result_counts["PASS_WITH_WARNINGS"],
        "fail_count": result_counts["FAIL"],
        "review_count": result_counts["REVIEW_REQUIRED"],
        "missing_trace_count": issue_counts["missing_source_evidence_ref"] + issue_counts["source_grounded_diagnosis_without_evidence"],
        "blocked_compatibility_count": sum(count for code, count in issue_counts.items() if code.startswith("blocked_")),
        "unknown_error_count": issue_counts["unknown_error_with_specific_detail"] + issue_counts["unknown_error_with_specific_remediation"],
        "human_review_required_count": result_counts["REVIEW_REQUIRED"],
        "fixture_alignment_checked": fixture_mode,
        "fixture_alignment_pass": all(alignments) if fixture_mode else None,
        "issue_code_counts": dict(sorted(issue_counts.items())),
    }
    aggregate_gates = {gate: result_from_issues([item for item in all_issues if item["gate"] == gate]) for gate in GATES}
    aggregate_gates["fixture_alignment_gate"] = "PASS" if fixture_mode and all(alignments) else "FAIL" if fixture_mode else "NOT_RUN"
    aggregate_gates["overall_gate"] = "PASS" if result == "PASS" else overall_gate(aggregate_gates)
    return {
        "validator_id": VALIDATOR_ID,
        "schema_version": SCHEMA_VERSION,
        "result": result,
        "summary": summary,
        "issues": all_issues,
        "record_counts": record_counts,
        "gate_metrics": aggregate_gates,
        "case_results": case_results,
        "fixture_alignment_failures": [case for case in case_results if case.get("expected_alignment") and not case["expected_alignment"]["matches"]],
        "input_path": str(input_path),
        "next_action_hint": None if result == "PASS" else "Inspect issues and fixture_alignment_failures.",
    }


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def validate(input_path: Path = DEFAULT_INPUT_PATH, report_path: Path | None = DEFAULT_REPORT_PATH) -> bool:
    if not input_path.exists():
        report = {
            "validator_id": VALIDATOR_ID,
            "schema_version": SCHEMA_VERSION,
            "result": "NOT_RUN",
            "summary": {},
            "issues": [issue("FAIL", "missing_required_field", "record_shape_gate", "required input file does not exist", field="input_path", expected=str(input_path))],
            "record_counts": {},
            "gate_metrics": {"overall_gate": "NOT_RUN"},
            "case_results": [],
            "input_path": str(input_path),
            "next_action_hint": "Create the golden sample fixture or pass a valid input path.",
        }
    else:
        try:
            report = build_report(load_json(input_path), input_path)
        except Exception as exc:
            report = {
                "validator_id": VALIDATOR_ID,
                "schema_version": SCHEMA_VERSION,
                "result": "NOT_RUN",
                "summary": {},
                "issues": [issue("FAIL", "invalid_field_type", "record_shape_gate", "input cannot be parsed or validated", field="input_path", actual=str(exc))],
                "record_counts": {},
                "gate_metrics": {"overall_gate": "NOT_RUN"},
                "case_results": [],
                "input_path": str(input_path),
                "next_action_hint": "Fix JSON syntax or validator input shape.",
            }
    if report_path is not None:
        write_json(report_path, report)
    print(f"E4S P6 error-tagging validation result: {report['result']}")
    if report_path is not None:
        print(f"Report written to: {report_path}")
    return report["result"] == "PASS"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate E4S-P6 error-tagging records or the I1 golden sample fixture.")
    parser.add_argument("input_path", nargs="?", default=str(DEFAULT_INPUT_PATH))
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--no-report", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    return 0 if validate(Path(args.input_path), None if args.no_report else Path(args.report)) else 1


if __name__ == "__main__":
    sys.exit(main())
