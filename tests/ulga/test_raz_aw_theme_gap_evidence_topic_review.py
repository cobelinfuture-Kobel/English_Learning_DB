from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_derived_material_extraction_minimal as material
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_aw_theme_gap_evidence_topic_review as builder


def _authorities() -> dict:
    theme_rows = [
        {"id": "theme:a1_homes_and_neighborhoods", "normalized": "home"},
        {"id": "theme:a1_school_and_classroom", "normalized": "school"},
    ]
    vocabulary_rows = [
        {"id": "VOC_ROOM", "normalized": "room"},
        {"id": "VOC_BOOK", "normalized": "book"},
    ]
    return {
        "themes": {
            "rows": theme_rows,
            "ids": {row["id"] for row in theme_rows},
            "count": len(theme_rows),
            "source_path": "theme_nodes.json",
            "source_sha256": "t" * 64,
        },
        "vocabulary": {
            "rows": vocabulary_rows,
            "ids": {row["id"] for row in vocabulary_rows},
            "count": len(vocabulary_rows),
            "source_path": "vocabulary_nodes.json",
            "source_sha256": "v" * 64,
        },
    }


def _material_package() -> dict:
    package = {
        "task_id": material.TASK_ID,
        "schema_version": material.SCHEMA_VERSION,
        "validation_status": material.PASS_STATUS,
        "source_scope": {
            "levels": ["A", "B"],
            "page_unit_count": 2,
            "book_count": 2,
            "source_files": [],
        },
        "authority_baselines": {},
        "per_level_summary": [],
        "page_unit_evidence": [
            {
                "source_unit_ref": "RAZ_A_1_P001",
                "source_level": "A",
                "source_book_id": "1",
                "source_macro_theme_labels": ["Home"],
                "source_subtheme_labels": ["room", "jupe", "animal_care"],
            },
            {
                "source_unit_ref": "RAZ_B_2_P001",
                "source_level": "B",
                "source_book_id": "2",
                "source_macro_theme_labels": ["School", "Animals"],
                "source_subtheme_labels": ["books", "running", "bears"],
            },
        ],
        "aggregate_summary": {
            "source_macro_theme_label_count": 3,
            "source_macro_theme_labels": ["Animals", "Home", "School"],
            "source_subtheme_label_count": 6,
            "source_subtheme_labels": [
                "animal_care",
                "bears",
                "books",
                "jupe",
                "room",
                "running",
            ],
        },
        "extraction_gate": {
            "decision": "DERIVED_MATERIAL_READY_FOR_LOCAL_VALIDATION",
        },
        "claim_boundaries": {},
        "errors": [],
    }
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _matching_package() -> dict:
    return matching.build_package(
        _material_package(),
        _authorities(),
        expected_page_unit_count=2,
        expected_book_count=2,
    )


def test_materializes_gap_and_topic_review_evidence_without_decisions() -> None:
    package = builder.build_package(
        _matching_package(),
        expected_page_unit_count=2,
        expected_book_count=2,
        expected_gap_family_count=1,
        expected_unverified_topic_label_count=4,
    )

    assert package["validation_status"] == builder.PASS_STATUS
    assert package["review_gate"]["decision"] == (
        "THEME_GAP_AND_TOPIC_REVIEW_EVIDENCE_READY"
    )
    assert package["review_gate"]["human_decision_required"] is True
    assert package["review_gate"]["ready_for_canonical_promotion"] is False

    gaps = package["theme_authority_gap_evidence"]
    assert len(gaps) == 1
    gap = gaps[0]
    assert gap["source_macro_theme_family_id"] == "animals_and_habitats"
    assert gap["source_unit_count"] == 1
    assert gap["source_book_count"] == 1
    assert gap["source_levels"] == ["B"]
    assert gap["associated_source_topic_label_count"] == 3
    assert gap["review_status"] == "pending"
    assert gap["promotion_status"] == "promotion_blocked"

    topics = {
        row["source_topic_label"]: row
        for row in package["source_topic_review_candidates"]
    }
    assert set(topics) == {"animal_care", "bears", "jupe", "running"}
    assert topics["animal_care"]["review_route"] == "TOPIC_TAG_SEMANTIC_REVIEW"
    assert topics["running"]["review_route"] == (
        "LEMMA_OR_VOCABULARY_AUTHORITY_GAP_REVIEW"
    )
    assert topics["bears"]["review_route"] == (
        "LEMMA_OR_VOCABULARY_AUTHORITY_GAP_REVIEW"
    )
    assert topics["jupe"]["review_route"] == (
        "SPELLING_OR_VOCABULARY_AUTHORITY_GAP_REVIEW"
    )
    assert topics["jupe"]["source_macro_theme_family_ids"] == ["home"]
    assert all(row["review_priority"] == "LOW" for row in topics.values())
    assert all(row["review_status"] == "pending" for row in topics.values())
    assert matching.scan_forbidden_safe_keys(package) == []


def test_review_priority_is_frequency_based() -> None:
    assert builder._priority(1) == "LOW"
    assert builder._priority(20) == "MEDIUM"
    assert builder._priority(100) == "HIGH"


def test_tampered_matching_package_fails_closed() -> None:
    package = deepcopy(_matching_package())
    package["aggregate_summary"]["source_macro_theme_family_count"] = 999
    with pytest.raises(
        builder.ThemeGapEvidenceError,
        match="matching_package_sha256_mismatch",
    ):
        builder.build_package(
            package,
            expected_page_unit_count=2,
            expected_book_count=2,
            expected_gap_family_count=1,
            expected_unverified_topic_label_count=4,
        )


def test_missing_topic_evidence_fails_closed() -> None:
    package = _matching_package()
    package["theme_subtheme_candidates"][0][
        "source_topic_label_classifications"
    ] = []
    package["package_sha256"] = deep.sha256_value(
        {key: value for key, value in package.items() if key != "package_sha256"}
    )
    with pytest.raises(
        builder.ThemeGapEvidenceError,
        match="topic_label_evidence_missing",
    ):
        builder.build_package(
            package,
            expected_page_unit_count=2,
            expected_book_count=2,
            expected_gap_family_count=1,
            expected_unverified_topic_label_count=4,
        )
