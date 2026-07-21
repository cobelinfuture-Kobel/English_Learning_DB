from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_derived_material_extraction_minimal as material
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as builder


def _authorities() -> dict:
    theme_rows = [
        {
            "id": "theme:a1_homes_and_neighborhoods",
            "normalized": "居家與生活環境",
        },
        {
            "id": "theme:a1_school_and_classroom",
            "normalized": "學校與教室情境",
        },
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
                "source_subtheme_labels": ["room", "jupe"],
            },
            {
                "source_unit_ref": "RAZ_B_2_P001",
                "source_level": "B",
                "source_book_id": "2",
                "source_macro_theme_labels": ["School", "Animals"],
                "source_subtheme_labels": ["books"],
            },
        ],
        "aggregate_summary": {
            "source_macro_theme_label_count": 3,
            "source_macro_theme_labels": ["Animals", "Home", "School"],
            "source_subtheme_label_count": 3,
            "source_subtheme_labels": ["books", "jupe", "room"],
        },
        "extraction_gate": {
            "decision": "DERIVED_MATERIAL_READY_FOR_LOCAL_VALIDATION",
        },
        "claim_boundaries": {},
        "errors": [],
    }
    package["package_sha256"] = deep.sha256_value(package)
    return package


def test_maps_source_macros_and_classifies_subthemes_without_promotion() -> None:
    package = builder.build_package(
        _material_package(),
        _authorities(),
        expected_page_unit_count=2,
        expected_book_count=2,
    )

    assert package["validation_status"] == builder.PASS_STATUS
    assert (
        package["matching_gate"]["decision"]
        == "THEME_AUTHORITY_CANDIDATES_READY_FOR_LOCAL_VALIDATION"
    )
    summary = package["aggregate_summary"]
    assert summary["mapped_source_macro_theme_label_count"] == 2
    assert summary["unmapped_source_macro_theme_label_count"] == 1
    assert summary["candidate_theme_authority_ref_count"] == 2
    assert summary["a1_vocabulary_backed_subtheme_label_count"] == 2
    assert summary["unverified_source_subtheme_label_count"] == 1
    assert summary["unverified_source_subtheme_labels"] == ["jupe"]

    by_ref = {
        row["source_unit_ref"]: row
        for row in package["theme_subtheme_candidates"]
    }
    home = by_ref["RAZ_A_1_P001"]
    assert home["candidate_theme_authority_refs"] == [
        "theme:a1_homes_and_neighborhoods"
    ]
    assert home["vocabulary_backed_subthemes"] == [
        {
            "source_subtheme_label": "room",
            "matched_vocabulary_refs": ["VOC_ROOM"],
            "quality_status": "A1_VOCABULARY_BACKED",
        }
    ]
    assert home["authority_status"] == "candidate_only"
    assert home["review_status"] == "pending"
    assert home["promotion_status"] == "promotion_blocked"
    assert package["matching_gate"]["ready_for_canonical_promotion"] is False
    assert builder.scan_forbidden_safe_keys(package) == []


def test_plural_subtheme_uses_existing_morphology_matching() -> None:
    singles, phrases = builder._vocabulary_index(_authorities()["vocabulary"])
    assert builder._subtheme_vocabulary_refs("books", singles, phrases) == {
        "VOC_BOOK"
    }


def test_missing_alias_target_fails_closed() -> None:
    authorities = _authorities()
    authorities["themes"]["rows"] = []
    authorities["themes"]["ids"] = set()
    with pytest.raises(
        builder.ThemeAuthorityCandidateMatchingError,
        match="theme_alias_target_missing_from_authority",
    ):
        builder.build_package(
            _material_package(),
            authorities,
            expected_page_unit_count=2,
            expected_book_count=2,
        )


def test_tampered_material_package_fails_closed() -> None:
    tampered = deepcopy(_material_package())
    tampered["aggregate_summary"]["source_macro_theme_label_count"] = 999
    with pytest.raises(
        builder.ThemeAuthorityCandidateMatchingError,
        match="material_package_sha256_mismatch",
    ):
        builder.build_package(
            tampered,
            _authorities(),
            expected_page_unit_count=2,
            expected_book_count=2,
        )


def test_safe_key_scanner_rejects_source_text() -> None:
    assert builder.scan_forbidden_safe_keys({"source_text": "forbidden"}) == [
        "forbidden_safe_key:$.source_text"
    ]
