from __future__ import annotations

import pytest

from ulga.builders import build_raz_aw_derived_material_extraction_minimal as builder


def _authorities() -> dict:
    return {
        "vocabulary": {
            "rows": [{"id": "VOC_CAT", "normalized": "cat"}],
            "count": 1,
            "source_path": "vocabulary.json",
            "source_sha256": "v" * 64,
        },
        "chunks": {
            "rows": [],
            "count": 0,
            "source_path": "chunks.json",
            "source_sha256": "c" * 64,
        },
        "patterns": {
            "rows": [],
            "count": 0,
            "source_path": "patterns.json",
            "source_sha256": "p" * 64,
        },
        "themes": {
            "rows": [],
            "count": 0,
            "source_path": "themes.json",
            "source_sha256": "t" * 64,
        },
    }


def _metadata() -> dict:
    empty_refs = {
        "direct_candidate_vocabulary_refs": [],
        "direct_candidate_chunk_refs": [],
        "direct_candidate_pattern_refs": [],
        "direct_candidate_grammar_refs": [],
    }
    return {
        "A": {
            "theme_labels": ["Home"],
            "pedagogy_labels": ["reading"],
            **empty_refs,
        },
        "J": {
            "theme_labels": ["Animals"],
            "pedagogy_labels": ["dialogue_candidate"],
            **empty_refs,
        },
    }


def _page_units() -> list[dict]:
    return [
        {
            "page_unit_id": "RAZ_A_1_P001",
            "book_id": "1",
            "level": "A",
            "text": "The cat is in the room.",
            "sentence_count": 1,
            "theme_tags": {
                "primary_theme": "Home",
                "mapped_theme": "Home",
                "subthemes": ["room"],
                "theme_confidence": 0.92,
                "theme_source": "rule_based_title",
            },
            "content_unit_tags": {"has_direct_speech": False},
        },
        {
            "page_unit_id": "RAZ_J_2_P001",
            "book_id": "2",
            "level": "J",
            "text": "Where is the cat? The cat is under the chair.",
            "sentence_count": 2,
            "theme_tags": {
                "primary_theme": "Animals",
                "mapped_theme": "Animals",
            },
            "content_unit_tags": {"has_direct_speech": True},
        },
    ]


def test_theme_extraction_excludes_confidence_and_source_metadata():
    labels = builder._theme_labels_from_record(
        {
            "candidate_theme_tags": ["Animals"],
            "theme_tags": {
                "primary_theme": "Animal Nonfiction",
                "mapped_theme": "Animals",
                "subthemes": ["pets"],
                "theme_confidence": 0.92,
                "theme_source": "rule_based_title",
            },
        }
    )

    assert labels == {"Animals", "Animal Nonfiction", "pets"}
    assert "0.92" not in labels
    assert "rule_based_title" not in labels


def test_builds_text_free_a1_and_jw_material_evidence():
    package = builder.build_package(
        _page_units(),
        [
            {"level": "A", "path": "a.json", "record_count": 1, "sha256": "a" * 64},
            {"level": "J", "path": "j.json", "record_count": 1, "sha256": "j" * 64},
        ],
        _metadata(),
        _authorities(),
        {},
        levels=("A", "J"),
        expected_page_unit_count=2,
        expected_book_count=2,
    )

    assert package["validation_status"] == builder.PASS_STATUS
    assert package["extraction_gate"]["decision"] == "DERIVED_MATERIAL_READY_FOR_LOCAL_VALIDATION"
    assert package["aggregate_summary"]["direct_image_evidence_count"] == 0
    assert package["aggregate_summary"]["matched_vocabulary_ref_count"] == 1
    assert builder.scan_forbidden_safe_keys(package) == []

    by_ref = {
        row["source_unit_ref"]: row
        for row in package["page_unit_evidence"]
    }
    assert by_ref["RAZ_A_1_P001"]["a1_a1plus_use_status"] == "A1_A1PLUS_REVIEW_REQUIRED"
    assert by_ref["RAZ_J_2_P001"]["a1_a1plus_use_status"] == "SOURCE_EVIDENCE_ONLY_REWRITE_REQUIRED"
    assert all(
        row["scene_evidence_status"] == "DERIVED_SCENE_STRUCTURE"
        for row in by_ref.values()
    )
    assert "LISTENING_ADAPTATION" in by_ref["RAZ_J_2_P001"]["four_skill_affordances"]


def test_duplicate_page_unit_identity_fails_closed():
    duplicated = _page_units()[:1] * 2
    with pytest.raises(builder.MinimalExtractionError, match="invalid_page_unit_identity"):
        builder.build_package(
            duplicated,
            [],
            {"A": _metadata()["A"]},
            _authorities(),
            {},
            levels=("A",),
            expected_page_unit_count=2,
            expected_book_count=1,
        )


def test_safe_key_scanner_rejects_source_text():
    assert builder.scan_forbidden_safe_keys({"source_text": "forbidden"}) == [
        "forbidden_safe_key:$.source_text"
    ]
