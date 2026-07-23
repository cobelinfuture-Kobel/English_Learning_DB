from __future__ import annotations

from copy import deepcopy
import json

import pytest

from ulga.builders import cp07b_ket99_canonical_mapping_and_instructional_sequence_overlay_impl as builder
from ulga.builders import build_a1fs_v1_cp06_grammar_spiral_role_population_and_content_capacity as cp06
from ulga.builders import build_a1fs_v1_m1_prerequisite_graph_and_coverage as m1
from ulga.builders import build_ket_comp_transcript_final_consolidation as consolidation
from ulga.validators import validate_a1fs_v1_cp07b_ket99_canonical_mapping_and_instructional_sequence_overlay as validator


GRAMMAR_UNITS = (
    "GRAMMAR_ARTICLES_BASIC", "GRAMMAR_REGULAR_PLURAL_NOUNS", "GRAMMAR_SUBJECT_PRONOUNS",
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE", "GRAMMAR_BE_VERB_BASIC", "GRAMMAR_CAN_STATEMENT",
    "GRAMMAR_DEMONSTRATIVES_CONTRAST", "GRAMMAR_OBJECT_PRONOUNS_BASIC",
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC", "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS",
    "GRAMMAR_ADJECTIVE_PHRASES_A1", "GRAMMAR_ADVERB_PHRASES_A1",
    "GRAMMAR_BE_INTERROGATIVES_A1", "GRAMMAR_CAN_NEGATIVE_A1", "GRAMMAR_COORDINATION_A1",
    "GRAMMAR_DECLARATIVE_CLAUSE_FORMS_A1", "GRAMMAR_PAST_SIMPLE_A1",
    "GRAMMAR_PRESENT_SIMPLE_NEGATIVES", "GRAMMAR_THERE_IS",
    "GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1", "GRAMMAR_WILL_FUTURE_A1",
    "GRAMMAR_BECAUSE_REASON_CLAUSES_A1", "GRAMMAR_NOUN_PHRASES_A1",
    "GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS",
)


def _unit(number: int) -> dict:
    tid = f"P{number:03d}"
    evidence, roles, lesson_role = [f"topic_word_{number}"], ["vocabulary", "teacher_delivery"], "unit_core"
    if number == 4:
        evidence, roles = ["ask_name", "give_name"], ["speaking", "teacher_delivery"]
    elif number == 6:
        evidence = ["be_present_affirmative", "be_present_negative", "be_present_yes_no_question"]
        roles = ["grammar", "teacher_delivery"]
    elif number == 16:
        evidence, roles, lesson_role = ["present_simple", "frequency_adverbs"], ["grammar", "review"], "review"
    elif number == 20:
        evidence, roles = ["be_present_negative", "have_got_affirmative"], ["grammar", "error_diagnosis"]
    elif number == 93:
        evidence, roles = ["hope_will_false_correction"], ["grammar", "error_diagnosis"]
    return {
        "content_unit_id": f"KET_COMP_CU_{tid}_LESSON_BUNDLE",
        "transcript_id": tid,
        "textbook_page": number + 4,
        "unit_id": f"U{((number - 4) // 8) + 1:02d}",
        "lesson_role": lesson_role,
        "content_roles": roles,
        "evidence_items": evidence,
        "risk_flags": [],
        "source_span": {"evidence_sha256": f"{number:064x}"[-64:], "coverage_mode": "full_transcript_read"},
        "authority_status": consolidation.AUTHORITY,
        "canonical_promotion_allowed": False,
    }


def _content() -> list[dict]:
    return [_unit(number) for number in range(4, 103)]


def _admission() -> dict:
    rows = []
    for number in range(4, 103):
        tid = f"P{number:03d}"
        rows.append({
            "admission_id": f"KET_COMP_ADMISSION_{tid}", "subject_type": "content_unit",
            "subject_id": f"KET_COMP_CU_{tid}_LESSON_BUNDLE", "transcript_id": tid,
            "decisions": {"lesson_planner": "approved_with_constraints", "canonical_grammar_authority": "denied", "canonical_vocabulary_authority": "denied"},
            "requirements": ["map_language_items_to_canonical_authorities"],
        })
    rows += [
        {"admission_id": "DENY_1", "subject_type": "source_claim", "subject_id": "P093_FALSE_HOPE_WILL_CORRECTION", "transcript_id": "P093"},
        {"admission_id": "DENY_2", "subject_type": "source_claim", "subject_id": "P102_KET_ZHONGKAO_EQUIVALENCE", "transcript_id": "P102"},
    ]
    return {
        "task_id": consolidation.TASK_ID,
        "schema_version": "ket.comp.transcript_admission_decisions.v1",
        "global_policy": {"canonical_promotion_allowed": False},
        "decision_count": len(rows), "decisions": rows,
    }


def _graph() -> dict:
    nodes = [
        {"node_id": "REF:SPEAKING:be_present_affirmative", "node_type": "CAPABILITY", "skill": "SPEAKING", "level": "A1", "source_ref": "be_present_affirmative"},
        {"node_id": "GATE:A1FS:A2_LOCK", "node_type": "A2_LOCK", "skill": "FOUR_SKILL", "level": "A2", "source_ref": "A2_ENTRY"},
    ]
    edges = [{"from_node_id": nodes[0]["node_id"], "to_node_id": nodes[1]["node_id"], "edge_type": "UNLOCK_REQUIRES"}]
    return {
        "task_id": m1.TASK_ID, "schema_version": m1.SCHEMA_VERSION, "validation_status": m1.STATUS,
        "nodes": nodes, "edges": edges, "coverage": [],
        "counts": {"node_count": 2, "edge_count": 1},
        "a2_lock_contract": {"state": "LOCKED_BY_DESIGN"}, "errors": [],
    }


def _cp06() -> dict:
    units = [
        {"learning_unit_id": f"E4S_A1V1_UNIT:{grammar_id}", "grammar_unit_id": grammar_id, "sequence_index": index,
         "internal_stage": "A1" if index <= 12 else "A1_PLUS"}
        for index, grammar_id in enumerate(GRAMMAR_UNITS, start=1)
    ]
    return {
        "task_id": cp06.TASK_ID, "program_id": cp06.PROGRAM_ID, "schema_version": cp06.SCHEMA_VERSION,
        "scope": "A1_A1_PLUS_ONLY", "unit_content_capacity": units,
        "coverage_summary": {"existing_learning_unit_count": 24},
        "errors": [], "stop_reason": "NONE",
    }


def _inputs() -> tuple[list[dict], dict, dict, dict]:
    return _content(), _admission(), _graph(), _cp06()


def test_reconciles_99_and_disposes_all_evidence_without_graph_mutation() -> None:
    artifact = builder.build_artifact(*_inputs())
    summary = artifact["coverage_summary"]
    assert summary["transcript_count"] == 99
    assert sum(summary["evidence_disposition_counts"].values()) == summary["evidence_occurrence_count"]
    assert summary["new_hard_prerequisite_edge_count"] == 0
    assert "edges" not in artifact


def test_exact_mapping_focus_recycle_review_and_m1_match() -> None:
    artifact = builder.build_artifact(*_inputs())
    be_rows = builder.query_instructional_overlay(artifact, grammar_unit_id="GRAMMAR_BE_VERB_BASIC")["evidence_occurrences"]
    assert [row["transcript_id"] for row in be_rows] == ["P006", "P006", "P020"]
    first = next(row for row in be_rows if row["evidence_item"] == "be_present_affirmative")
    assert {target["target_type"] for target in first["canonical_targets"]} == {"GRAMMAR_UNIT", "M1_NODE"}
    assert "FOCUS" in first["instructional_roles"]
    assert "RECYCLE" in next(row for row in be_rows if row["transcript_id"] == "P020")["instructional_roles"]
    review = builder.query_instructional_overlay(artifact, grammar_unit_id="GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS", instructional_role="REVIEW")
    assert review["total_match_count"] == 1


def test_support_and_review_required_are_kept_separate() -> None:
    artifact = builder.build_artifact(*_inputs())
    support = builder.query_instructional_overlay(artifact, transcript_id="P004", disposition="INSTRUCTIONAL_SUPPORT_ONLY")
    assert support["total_match_count"] == 2
    review = builder.query_instructional_overlay(artifact, transcript_id="P020", disposition="REVIEW_REQUIRED")
    assert [row["evidence_item"] for row in review["evidence_occurrences"]] == ["have_got_affirmative"]


def test_denied_claims_and_a2_are_fail_closed() -> None:
    artifact = builder.build_artifact(*_inputs())
    assert {"P093_FALSE_HOPE_WILL_CORRECTION", "P102_KET_ZHONGKAO_EQUIVALENCE"} <= set(artifact["denied_source_claim_ids"])
    with pytest.raises(builder.CP07BBuildError, match="A2_OVERLAY_LOCKED"):
        builder.query_instructional_overlay(artifact, level="A2")


def test_validator_passes_and_rejects_mutation_claim() -> None:
    inputs = _inputs(); artifact = builder.build_artifact(*inputs)
    report = validator.validate_artifact(artifact, content_units=inputs[0], admission_artifact=inputs[1], m1_graph=inputs[2], cp06_artifact=inputs[3])
    assert report["validation_status"] == builder.PASS_STATUS, report["errors"]
    assert report["deterministic_rebuild_matches"] is True
    tampered = deepcopy(artifact); tampered["planner_overlay_gate"]["canonical_graph_mutation_performed"] = True
    failed = validator.validate_artifact(tampered, content_units=inputs[0], admission_artifact=inputs[1], m1_graph=inputs[2], cp06_artifact=inputs[3])
    assert "canonical_graph_mutation_claim_invalid" in failed["errors"]


def test_real_committed_99_transcript_corpus_smoke() -> None:
    content = [json.loads(line) for line in builder.DEFAULT_CONTENT_UNITS.read_text(encoding="utf-8").splitlines() if line.strip()]
    admission = json.loads(builder.DEFAULT_ADMISSION.read_text(encoding="utf-8"))
    artifact = builder.build_artifact(content, admission, _graph(), _cp06())
    assert artifact["coverage_summary"]["transcript_count"] == 99
    assert artifact["coverage_summary"]["evidence_disposition_counts"]["CANONICAL_MATCH"] > 0
    assert artifact["planner_overlay_gate"]["all_99_transcript_identities_reconciled"] is True
