from __future__ import annotations

import copy

import pytest

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_derived_material_extraction_minimal as material
from ulga.builders import build_raz_ai_a1_a1plus_coverage_recheck as coverage
from ulga.builders import build_raz_ai_acl_v1_s01_material_admission as admission


def _row(
    ref: str,
    level: str,
    group: str,
    *,
    vocabulary: list[str] | None = None,
    grammar: list[str] | None = None,
    chunks: list[str] | None = None,
    patterns: list[str] | None = None,
    skills: list[str] | None = None,
    theme: str = "Personal",
    maturity: str = "BROAD_CORE_SENTENCE_SEED",
    discourse: str = "simple_narrative_or_description",
    passage_supported: bool = False,
) -> dict[str, object]:
    return {
        "source_unit_ref": ref,
        "source_level": level,
        "source_book_id": f"BOOK_{level}",
        "source_macro_theme_labels": [theme],
        "source_subtheme_labels": [],
        "matched_vocabulary_refs": vocabulary or [],
        "matched_chunk_refs": chunks or [],
        "matched_pattern_refs": patterns or [],
        "matched_grammar_unit_refs": grammar or [],
        "sentence_seed_maturity": maturity,
        "semantic_duplicate_group_id": group,
        "discourse_shape": discourse,
        "passage_seed_status": "SUPPORTED" if passage_supported else "NOT_A_PASSAGE",
        "scene_structure": "GENERAL_CONTEXT_SCENE",
        "four_skill_affordances": skills or ["READING_SOURCE"],
        "promotion_status": "NOT_PROMOTED",
    }


def _material_package() -> dict[str, object]:
    rows = [
        _row(
            "A_001",
            "A",
            "G_SIMPLE",
            vocabulary=["vocabulary:cat"],
            grammar=["GRAMMAR_BE_VERB_BASIC"],
        ),
        _row(
            "B_001",
            "B",
            "G_PLUS",
            vocabulary=["vocabulary:go"],
            grammar=["GRAMMAR_PAST_SIMPLE_A1"],
            discourse="sequence",
        ),
        _row(
            "C_001",
            "C",
            "G_REWRITE",
            vocabulary=["vocabulary:book"],
        ),
        _row(
            "D_001",
            "D",
            "G_SUPPORT",
            chunks=["chunk:look_at"],
            skills=["READING_SOURCE", "SPEAKING_PROMPT"],
        ),
        _row("E_001", "E", "G_REJECT"),
        _row(
            "F_999",
            "F",
            "G_SIMPLE",
            vocabulary=["vocabulary:cat"],
            grammar=["GRAMMAR_BE_VERB_BASIC"],
        ),
        _row(
            "J_001",
            "J",
            "G_DEFER",
            vocabulary=["vocabulary:advanced"],
            grammar=["GRAMMAR_PAST_SIMPLE_A1"],
            theme="Animals",
        ),
    ]
    package: dict[str, object] = {
        "task_id": material.TASK_ID,
        "schema_version": material.SCHEMA_VERSION,
        "validation_status": material.PASS_STATUS,
        "source_scope": {
            "levels": ["A", "B", "C", "D", "E", "F", "J"],
            "page_unit_count": len(rows),
            "book_count": 7,
        },
        "page_unit_evidence": rows,
        "aggregate_summary": {},
        "errors": [],
    }
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _coverage_package(material_package: dict[str, object]) -> dict[str, object]:
    package: dict[str, object] = {
        "task_id": coverage.TASK_ID,
        "schema_version": coverage.SCHEMA_VERSION,
        "validation_status": coverage.PASS_STATUS,
        "input_identity": {
            "material_task_id": material.TASK_ID,
            "material_package_sha256": material_package["package_sha256"],
            "contextual_task_id": "fixture",
            "contextual_package_sha256": "f" * 64,
        },
        "approved_theme_decision_binding": {
            "decision_count": 4,
            "decisions": [dict(row) for row in coverage.APPROVED_THEME_ACTIONS],
            "decision_status": "OPERATOR_APPROVED_READY_FOR_CANONICAL_BINDING",
        },
        "a1_a1plus_observational_candidate_summary": {
            "page_unit_count": 6,
            "semantic_duplicate_group_count": 5,
        },
        "a1_a1plus_authority_matched_candidate_summary": {
            "final_promoted_page_unit_count": 0,
        },
        "coverage_gate": {
            "decision": "A1_A1PLUS_CANDIDATE_COUNTS_CONFIRMED_FINAL_PROMOTION_PENDING"
        },
        "errors": [],
    }
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _build() -> dict[str, object]:
    source = _material_package()
    return admission.build_package(
        source,
        _coverage_package(source),
        expected_total_page_unit_count=7,
        expected_scope_page_unit_count=6,
        expected_scope_duplicate_group_count=5,
        expected_deferred_page_unit_count=1,
    )


def test_material_admission_classifies_every_row_and_locks_a2() -> None:
    package = _build()
    assert package["validation_status"] == admission.PASS_STATUS
    assert package["admission_gate"]["decision"] == (
        "MATERIAL_ADMISSION_CLASSIFICATION_READY"
    )
    assert package["admission_gate"]["distance_after"] == "D5"

    summary = package["aggregate_summary"]
    assert summary["source_candidate_count"] == 7
    assert summary["a1_a1plus_scope_candidate_count"] == 6
    assert summary["semantic_duplicate_group_count"] == 5
    assert summary["admission_status_counts"] == {
        "A1PLUS_READY_CANDIDATE": 1,
        "A1_READY_CANDIDATE": 1,
        "DEFERRED_A2_A2PLUS": 1,
        "DUPLICATE_CANDIDATE": 1,
        "REJECTED_UNUSABLE": 1,
        "REWRITE_REQUIRED": 1,
        "SUPPORT_ONLY": 1,
    }
    assert summary["final_promoted_material_count"] == 0

    rows = {row["source_unit_ref"]: row for row in package["admission_rows"]}
    assert rows["A_001"]["admission_status"] == "A1_READY_CANDIDATE"
    assert rows["B_001"]["admission_status"] == "A1PLUS_READY_CANDIDATE"
    assert rows["C_001"]["admission_status"] == "REWRITE_REQUIRED"
    assert rows["D_001"]["admission_status"] == "SUPPORT_ONLY"
    assert rows["E_001"]["admission_status"] == "REJECTED_UNUSABLE"
    assert rows["F_999"]["admission_status"] == "DUPLICATE_CANDIDATE"
    assert rows["F_999"]["duplicate_representative_source_unit_ref"] == "A_001"
    assert rows["J_001"]["admission_status"] == "DEFERRED_A2_A2PLUS"
    assert rows["J_001"]["candidate_cefr_scope"] == "DEFERRED_A2_A2PLUS"
    assert "theme_candidate:a1_animals_and_habitats" in rows["J_001"][
        "candidate_theme_refs"
    ]


def test_a1plus_classification_uses_grammar_or_discourse_not_raz_level() -> None:
    package = _build()
    rows = {row["source_unit_ref"]: row for row in package["admission_rows"]}
    assert rows["A_001"]["candidate_cefr_scope"] == "A1"
    assert rows["B_001"]["candidate_cefr_scope"] == "A1_PLUS"
    assert "A1PLUS_GRAMMAR_SIGNAL" in rows["B_001"]["admission_reason_codes"]
    assert package["claim_boundaries"]["raz_level_used_as_cefr_equivalence"] is False


def test_material_or_coverage_hash_tampering_fails_closed() -> None:
    source = _material_package()
    coverage_package = _coverage_package(source)
    source["page_unit_evidence"][0]["source_book_id"] = "tampered"
    with pytest.raises(admission.MaterialAdmissionError, match="material_package_sha256_mismatch"):
        admission.build_package(
            source,
            coverage_package,
            expected_total_page_unit_count=7,
            expected_scope_page_unit_count=6,
            expected_scope_duplicate_group_count=5,
            expected_deferred_page_unit_count=1,
        )

    source = _material_package()
    coverage_package = _coverage_package(source)
    coverage_package["approved_theme_decision_binding"]["decision_count"] = 3
    with pytest.raises(admission.MaterialAdmissionError, match="coverage_package_sha256_mismatch"):
        admission.build_package(
            source,
            coverage_package,
            expected_total_page_unit_count=7,
            expected_scope_page_unit_count=6,
            expected_scope_duplicate_group_count=5,
            expected_deferred_page_unit_count=1,
        )


def test_unapproved_theme_candidate_fails_closed() -> None:
    source = _material_package()
    source["page_unit_evidence"][0]["source_macro_theme_labels"] = ["Unknown New Theme"]
    source.pop("package_sha256")
    source["package_sha256"] = deep.sha256_value(source)
    coverage_package = _coverage_package(source)
    with pytest.raises(
        admission.MaterialAdmissionError,
        match="source_macro_theme_label_unrecognized",
    ):
        admission.build_package(
            source,
            coverage_package,
            expected_total_page_unit_count=7,
            expected_scope_page_unit_count=6,
            expected_scope_duplicate_group_count=5,
            expected_deferred_page_unit_count=1,
        )


def test_safe_package_contains_no_source_text_or_title() -> None:
    package = _build()
    assert admission.matching.scan_forbidden_safe_keys(package) == []
    serialized = deep.canonical_json(package)
    assert "learner_facing_text" not in serialized
    assert '"text"' not in serialized
    assert '"title"' not in serialized
