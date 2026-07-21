from __future__ import annotations

import json
from copy import deepcopy

import pytest

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_derived_material_extraction_minimal as material
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_aw_theme_gap_evidence_topic_review as builder


def _authorities() -> dict:
    theme_rows = [
        {
            "id": "theme:a1_homes_and_neighborhoods",
            "normalized": "home",
        },
        {
            "id": "theme:a1_personal_information_and_greetings",
            "normalized": "personal",
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
                "source_unit_ref": "RAZ_A_1_P002",
                "source_level": "A",
                "source_book_id": "1",
                "source_macro_theme_labels": ["Home"],
                "source_subtheme_labels": ["building", "jupe"],
            },
            {
                "source_unit_ref": "RAZ_B_2_P002",
                "source_level": "B",
                "source_book_id": "2",
                "source_macro_theme_labels": ["Animals"],
                "source_subtheme_labels": [
                    "animal_care",
                    "bears",
                    "running",
                ],
            },
        ],
        "aggregate_summary": {
            "source_macro_theme_label_count": 2,
            "source_macro_theme_labels": ["Animals", "Home"],
            "source_subtheme_label_count": 5,
            "source_subtheme_labels": [
                "animal_care",
                "bears",
                "building",
                "jupe",
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


def _context_row(
    ref: str,
    level: str,
    book_id: str,
    page_number: int,
    source_text: str,
    source_title: str,
    primary_theme: str,
    subthemes: list[str],
) -> dict:
    return {
        "page_unit_id": ref,
        "book_id": book_id,
        "level": level,
        "page_number": page_number,
        "text": source_text,
        "title": source_title,
        "theme_tags": {
            "primary_theme": primary_theme,
            "mapped_theme": primary_theme,
            "subthemes": subthemes,
        },
    }


def _context_rows() -> list[dict]:
    return [
        _context_row(
            "RAZ_A_1_P001",
            "A",
            "1",
            1,
            "They start building a house.",
            "Building a House",
            "Home",
            ["building"],
        ),
        _context_row(
            "RAZ_A_1_P002",
            "A",
            "1",
            2,
            "Jupe looks at the tall building.",
            "Jupe in Town",
            "Home",
            ["building", "jupe"],
        ),
        _context_row(
            "RAZ_A_1_P003",
            "A",
            "1",
            3,
            "The building has many rooms.",
            "Jupe in Town",
            "Home",
            ["building"],
        ),
        _context_row(
            "RAZ_B_2_P001",
            "B",
            "2",
            1,
            "The bears live in the forest.",
            "Bears",
            "Animals",
            ["bears"],
        ),
        _context_row(
            "RAZ_B_2_P002",
            "B",
            "2",
            2,
            "The bears are running.",
            "Bears",
            "Animals",
            ["bears", "running"],
        ),
        _context_row(
            "RAZ_B_2_P003",
            "B",
            "2",
            3,
            "Children learn about animal care.",
            "Animal Care",
            "Pets and Animal Care",
            ["animal_care"],
        ),
    ]


def _gap_contract() -> dict:
    return {
        "animals_and_habitats": builder.GAP_FAMILY_PLACEMENTS[
            "animals_and_habitats"
        ]
    }


def test_contextually_places_every_gap_and_topic_without_manual_topic_queue() -> None:
    context_rows = _context_rows()
    package = builder.build_package(
        _matching_package(),
        context_rows,
        [
            {
                "level": "A",
                "source_path": "A.json",
                "source_page_unit_count": 3,
                "source_book_count": 1,
                "source_sha256": "a" * 64,
            },
            {
                "level": "B",
                "source_path": "B.json",
                "source_page_unit_count": 3,
                "source_book_count": 1,
                "source_sha256": "b" * 64,
            },
        ],
        _authorities(),
        expected_page_unit_count=2,
        expected_book_count=2,
        expected_context_page_unit_count=6,
        expected_gap_family_count=1,
        expected_unverified_topic_label_count=5,
        gap_family_placements=_gap_contract(),
    )

    assert package["validation_status"] == builder.PASS_STATUS
    assert package["placement_gate"]["decision"] == (
        "CONTEXTUAL_THEME_AND_TOPIC_PLACEMENTS_READY"
    )
    assert package["placement_gate"]["human_topic_placement_required"] is False
    assert package["placement_gate"]["ready_for_canonical_promotion"] is False

    summary = package["aggregate_summary"]
    assert summary["contextual_theme_family_placement_count"] == 1
    assert summary["contextual_source_topic_placement_count"] == 5
    assert summary["manual_topic_placement_required_count"] == 0
    assert summary["canonical_theme_action_family_count"] == 1

    gap = package["contextual_theme_family_placements"][0]
    assert gap["source_macro_theme_family_id"] == "animals_and_habitats"
    assert gap["placement_disposition"] == "NEW_A1_THEME_CANDIDATE"
    assert gap["candidate_target_refs"] == [
        "theme_candidate:a1_animals_and_habitats"
    ]
    assert gap["source_unit_count"] == 2
    assert gap["canonical_action"] == (
        "HUMAN_THEME_AUTHORITY_DECISION_REQUIRED"
    )

    topics = {
        row["source_topic_label"]: row
        for row in package["contextual_source_topic_placements"]
    }
    assert topics["jupe"]["primary_placement_layers"] == ["ENTITY_REGISTRY"]
    assert topics["jupe"]["candidate_target_refs"] == [
        "entity_registry:character:jupe"
    ]
    assert topics["animal_care"]["primary_placement_layers"] == [
        "SITUATION_TAXONOMY"
    ]
    assert topics["animal_care"]["candidate_target_refs"] == [
        "situation:animal_care"
    ]
    assert topics["bears"]["candidate_target_refs"] == [
        "vocabulary_candidate:bear"
    ]
    assert topics["running"]["candidate_target_refs"] == [
        "vocabulary_candidate:run"
    ]
    assert topics["building"]["candidate_target_refs"] == [
        "vocabulary_candidate:build",
        "vocabulary_candidate:building",
    ]
    assert topics["building"]["context_variant_count"] >= 2
    assert all(
        row["manual_placement_required"] is False
        for row in topics.values()
    )
    assert matching.scan_forbidden_safe_keys(package) == []


def test_private_context_loader_reads_source_but_output_never_contains_it(
    tmp_path,
) -> None:
    source = tmp_path / "raz_output_jsons"
    for level, rows in {
        "A": _context_rows()[:3],
        "B": _context_rows()[3:],
    }.items():
        path = (
            source
            / "derived"
            / f"Level_{level}"
            / "enriched"
            / f"raz_{level}_page_unit_enriched.json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(rows, ensure_ascii=False),
            encoding="utf-8",
        )

    loaded, source_index = builder.load_context_rows(
        source,
        levels=("A", "B"),
        expected_context_page_unit_count=6,
    )
    assert len(loaded) == 6
    assert len(source_index) == 2

    package = builder.build_package(
        _matching_package(),
        loaded,
        source_index,
        _authorities(),
        expected_page_unit_count=2,
        expected_book_count=2,
        expected_context_page_unit_count=6,
        expected_gap_family_count=1,
        expected_unverified_topic_label_count=5,
        gap_family_placements=_gap_contract(),
    )
    serialized = json.dumps(package, ensure_ascii=False)
    assert "They start building a house." not in serialized
    assert "Jupe in Town" not in serialized
    assert package["claim_boundaries"][
        "raz_a_i_private_context_read_performed"
    ] is True
    assert package["claim_boundaries"][
        "source_text_included_in_safe_output"
    ] is False


def test_unknown_context_primary_theme_fails_closed() -> None:
    rows = _context_rows()
    rows[0]["theme_tags"]["primary_theme"] = "Completely New Theme"
    rows[0]["theme_tags"]["mapped_theme"] = "Completely New Theme"
    with pytest.raises(
        builder.ThemeGapEvidenceError,
        match="context_primary_theme_unrecognized",
    ):
        builder.build_package(
            _matching_package(),
            rows,
            [],
            _authorities(),
            expected_page_unit_count=2,
            expected_book_count=2,
            expected_context_page_unit_count=6,
            expected_gap_family_count=1,
            expected_unverified_topic_label_count=5,
            gap_family_placements=_gap_contract(),
        )


def test_missing_context_for_one_topic_fails_closed() -> None:
    rows = _context_rows()
    for row in rows:
        row["theme_tags"]["subthemes"] = [
            value
            for value in row["theme_tags"]["subthemes"]
            if value != "jupe"
        ]
    with pytest.raises(
        builder.ThemeGapEvidenceError,
        match="context_topic_labels_not_reconciled",
    ):
        builder.build_package(
            _matching_package(),
            rows,
            [],
            _authorities(),
            expected_page_unit_count=2,
            expected_book_count=2,
            expected_context_page_unit_count=6,
            expected_gap_family_count=1,
            expected_unverified_topic_label_count=5,
            gap_family_placements=_gap_contract(),
        )


def test_tampered_matching_package_fails_closed() -> None:
    package = deepcopy(_matching_package())
    package["aggregate_summary"]["source_macro_theme_family_count"] = 999
    with pytest.raises(
        builder.ThemeGapEvidenceError,
        match="matching_package_sha256_mismatch",
    ):
        builder.build_package(
            package,
            _context_rows(),
            [],
            _authorities(),
            expected_page_unit_count=2,
            expected_book_count=2,
            expected_context_page_unit_count=6,
            expected_gap_family_count=1,
            expected_unverified_topic_label_count=5,
            gap_family_placements=_gap_contract(),
        )
