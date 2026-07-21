from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_derived_material_extraction_minimal as material
from ulga.builders import build_raz_aw_theme_gap_evidence_topic_review as contextual
from ulga.builders import build_raz_ai_a1_a1plus_coverage_recheck as builder


def _with_hash(package: dict) -> dict:
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _material_package() -> dict:
    return _with_hash(
        {
            "task_id": material.TASK_ID,
            "schema_version": material.SCHEMA_VERSION,
            "validation_status": material.PASS_STATUS,
            "source_scope": {
                "levels": ["A", "B", "J"],
                "page_unit_count": 3,
                "book_count": 3,
            },
            "page_unit_evidence": [
                {
                    "source_unit_ref": "RAZ_A_1_P001",
                    "source_level": "A",
                    "source_book_id": "1",
                    "matched_vocabulary_refs": ["VOC_A", "VOC_SHARED"],
                    "matched_chunk_refs": ["CHUNK_A"],
                    "matched_pattern_refs": ["PATTERN_A"],
                    "matched_grammar_unit_refs": ["GRAMMAR_A"],
                    "sentence_seed_maturity": "STRICT_CORE_SENTENCE_SEED",
                    "semantic_duplicate_group_id": "DUP_1",
                    "passage_seed_status": "SUPPORTED",
                    "four_skill_affordances": ["READING_SOURCE", "WRITING_MODEL"],
                    "promotion_status": "NOT_PROMOTED",
                },
                {
                    "source_unit_ref": "RAZ_B_2_P001",
                    "source_level": "B",
                    "source_book_id": "2",
                    "matched_vocabulary_refs": ["VOC_B", "VOC_SHARED"],
                    "matched_chunk_refs": [],
                    "matched_pattern_refs": [],
                    "matched_grammar_unit_refs": ["GRAMMAR_A"],
                    "sentence_seed_maturity": "BROAD_CORE_SENTENCE_SEED",
                    "semantic_duplicate_group_id": "DUP_2",
                    "passage_seed_status": "NOT_A_PASSAGE",
                    "four_skill_affordances": ["READING_SOURCE"],
                    "promotion_status": "NOT_PROMOTED",
                },
                {
                    "source_unit_ref": "RAZ_J_3_P001",
                    "source_level": "J",
                    "source_book_id": "3",
                    "matched_vocabulary_refs": ["VOC_J"],
                    "matched_chunk_refs": ["CHUNK_J"],
                    "matched_pattern_refs": ["PATTERN_J"],
                    "matched_grammar_unit_refs": ["GRAMMAR_J"],
                    "sentence_seed_maturity": "STRICT_CORE_SENTENCE_SEED",
                    "semantic_duplicate_group_id": "DUP_3",
                    "passage_seed_status": "SUPPORTED",
                    "four_skill_affordances": ["READING_SOURCE"],
                    "promotion_status": "NOT_PROMOTED",
                },
            ],
            "aggregate_summary": {
                "matched_vocabulary_ref_count": 4,
                "matched_chunk_ref_count": 2,
                "matched_pattern_ref_count": 2,
                "matched_grammar_unit_ref_count": 2,
            },
            "errors": [],
        }
    )


def _contextual_package() -> dict:
    families = []
    for decision in builder.APPROVED_THEME_ACTIONS:
        families.append(
            {
                "source_macro_theme_family_id": decision[
                    "source_macro_theme_family_id"
                ],
                "source_unit_count": 1,
                "source_book_count": 1,
            }
        )
    return _with_hash(
        {
            "task_id": contextual.TASK_ID,
            "schema_version": contextual.SCHEMA_VERSION,
            "validation_status": contextual.PASS_STATUS,
            "contextual_theme_family_placements": families,
            "placement_gate": {
                "decision": "CONTEXTUAL_THEME_AND_TOPIC_PLACEMENTS_READY"
            },
            "errors": [],
        }
    )


def _inventory() -> dict:
    return {
        "levels": list(builder.SCOPE_LEVELS),
        "book_count": 2,
        "page_unit_count": 2,
        "sentence_count": 3,
        "reuse_unit_count": 1,
        "total_unit_count": 3,
        "per_level": [],
        "source_files": [],
    }


def _themes() -> list[dict]:
    return [
        {"id": "theme:a1_one", "cefr_level": "A1"},
        {"id": "theme:a1_two", "cefr_level": "A1"},
        {"id": "theme:a1_plus", "cefr_level": "A1_plus"},
        {"id": "theme:a2", "cefr_level": "A2"},
    ]


def test_rechecks_a1_a1plus_candidate_counts_and_binds_approvals() -> None:
    package = builder.build_package(
        _material_package(),
        _contextual_package(),
        _inventory(),
        _themes(),
        expected_book_count=2,
        expected_page_unit_count=2,
        expected_sentence_count=3,
        expected_reuse_unit_count=1,
        expected_total_unit_count=3,
    )

    assert package["validation_status"] == builder.PASS_STATUS
    assert package["coverage_gate"]["decision"] == (
        "A1_A1PLUS_CANDIDATE_COUNTS_CONFIRMED_FINAL_PROMOTION_PENDING"
    )
    assert package["approved_theme_decision_binding"]["decision_count"] == 4
    assert package["theme_authority_projection"] == {
        "existing_a1_theme_count": 2,
        "existing_a1plus_theme_count": 1,
        "approved_new_a1_theme_count": 3,
        "projected_a1_theme_count_after_binding": 5,
        "projected_a1plus_theme_count_after_binding": 1,
    }

    observed = package["a1_a1plus_observational_candidate_summary"]
    assert observed["book_count"] == 2
    assert observed["page_unit_count"] == 2
    assert observed["sentence_count"] == 3
    assert observed["reuse_unit_count"] == 1
    assert observed["passage_seed_count"] == 1

    matched = package["a1_a1plus_authority_matched_candidate_summary"]
    assert matched["matched_vocabulary_ref_count"] == 3
    assert matched["matched_chunk_ref_count"] == 1
    assert matched["matched_pattern_ref_count"] == 1
    assert matched["matched_grammar_unit_ref_count"] == 1
    assert matched["authority_matched_page_unit_count"] == 2
    assert matched["final_promoted_page_unit_count"] == 0
    assert matched["sentence_seed_maturity_counts"] == {
        "BROAD_CORE_SENTENCE_SEED": 1,
        "STRICT_CORE_SENTENCE_SEED": 1,
    }
    assert contextual.matching.scan_forbidden_safe_keys(package) == []


def test_tampered_material_package_fails_closed() -> None:
    package = deepcopy(_material_package())
    package["aggregate_summary"]["matched_chunk_ref_count"] = 99
    with pytest.raises(
        builder.CoverageRecheckError,
        match="material_package_sha256_mismatch",
    ):
        builder.build_package(
            package,
            _contextual_package(),
            _inventory(),
            _themes(),
            expected_book_count=2,
            expected_page_unit_count=2,
            expected_sentence_count=3,
            expected_reuse_unit_count=1,
            expected_total_unit_count=3,
        )


def test_missing_approved_theme_family_fails_closed() -> None:
    package = _contextual_package()
    package["contextual_theme_family_placements"] = package[
        "contextual_theme_family_placements"
    ][1:]
    package["package_sha256"] = deep.sha256_value(
        {key: value for key, value in package.items() if key != "package_sha256"}
    )
    with pytest.raises(
        builder.CoverageRecheckError,
        match="approved_theme_family_missing",
    ):
        builder.build_package(
            _material_package(),
            package,
            _inventory(),
            _themes(),
            expected_book_count=2,
            expected_page_unit_count=2,
            expected_sentence_count=3,
            expected_reuse_unit_count=1,
            expected_total_unit_count=3,
        )
