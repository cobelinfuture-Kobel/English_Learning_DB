from __future__ import annotations

import json
from pathlib import Path

from ulga.builders import build_raz_aw_derived_material_extraction_minimal as builder
from ulga.validators import validate_raz_aw_derived_material_extraction_minimal as validator


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _registry(schema: str, records: list[dict]) -> dict:
    return {"schema_version": schema, "records": records}


def _level(root: Path, level: str, *, rich: bool) -> None:
    enriched = root / "derived" / f"Level_{level}" / "enriched"
    book_uid = f"raz_{level}_1"
    sentences = [
        {
            "sentence_uid": f"{book_uid}_s0001",
            "book_uid": book_uid,
            "level": level,
            "text": "Where is the book?",
            "candidate_vocab_refs": [],
            "candidate_pattern_refs": [],
            "candidate_grammar_refs": [],
        },
        {
            "sentence_uid": f"{book_uid}_s0002",
            "book_uid": book_uid,
            "level": level,
            "text": "The book is in the room.",
            "candidate_vocab_refs": [],
            "candidate_pattern_refs": [],
            "candidate_grammar_refs": [],
        },
    ]
    units = [
        {
            "unit_uid": f"{book_uid}_p0001",
            "unit_type": "page_unit",
            "book_uid": book_uid,
            "level": level,
            "sentence_uids": [row["sentence_uid"] for row in sentences],
        },
        {
            "unit_uid": f"{book_uid}_r0001",
            "unit_type": "reuse_unit",
            "book_uid": book_uid,
            "level": level,
            "sentence_uids": [sentences[1]["sentence_uid"]],
        },
    ]
    _write(
        enriched / f"raz_{level}_enriched_books.json",
        _registry(
            "raz_enriched_books.v1",
            [
                {
                    "book_uid": book_uid,
                    "book_id": "1",
                    "level": level,
                    "candidate_theme_tags": ["Home"],
                    "candidate_pedagogical_tags": ["speaking"],
                }
            ],
        ),
    )
    _write(
        enriched / f"raz_{level}_enriched_sentences.json",
        _registry("raz_enriched_sentences.v1", sentences),
    )
    _write(
        enriched / f"raz_{level}_enriched_units.json",
        _registry("raz_enriched_units.v1", units),
    )
    if rich:
        _write(
            enriched / f"raz_{level}_page_unit_enriched.json",
            [
                {
                    "page_unit_id": f"RAZ_{level}_1_P003",
                    "theme_tags": {
                        "primary_theme": "Home",
                        "mapped_theme": "Home",
                        "subthemes": ["room"],
                    },
                    "pedagogical_tags": {"skill_area": "reading"},
                }
            ],
        )
        _write(
            enriched / f"raz_{level}_reuse_unit_enriched.json",
            [
                {
                    "reuse_unit_id": f"RAZ_{level}_1_REUSE_000001",
                    "theme_tags": {
                        "primary_theme": "Home",
                        "mapped_theme": "Home",
                        "subthemes": ["room"],
                    },
                    "pedagogical_tags": {"skill_area": "writing"},
                }
            ],
        )


def _base_package() -> dict:
    return {
        "task_id": "old",
        "schema_version": "old",
        "validation_status": "PASS",
        "source_scope": {"levels": ["A", "J"]},
        "page_unit_evidence": [
            {
                "source_unit_ref": "A1",
                "scene_evidence_status": "DERIVED_SCENE_STRUCTURE",
                "situation_families": ["home_objects_and_activities"],
                "micro_situations": ["home_objects_and_activities__locate_or_identify"],
            },
            {
                "source_unit_ref": "J1",
                "scene_evidence_status": "DERIVED_SCENE_STRUCTURE",
                "situation_families": ["travel_and_places"],
                "micro_situations": ["travel_and_places__locate_or_identify"],
            },
        ],
        "aggregate_summary": {"direct_picture_or_visual_tag_count": 1},
        "extraction_gate": {"ready_for_review_bridge_linkage_binding": True},
        "claim_boundaries": {},
        "errors": [],
    }


def _expected() -> dict[str, int]:
    return {
        "book_count": 2,
        "sentence_count": 4,
        "unit_count": 4,
        "page_unit_count": 2,
        "reuse_unit_count": 2,
        "rich_a_i_unit_count": 2,
    }


def test_source_reality_matches_a_i_and_j_w_shapes(tmp_path: Path):
    _level(tmp_path, "A", rich=True)
    _level(tmp_path, "J", rich=False)
    reality = builder.scan_source_reality(tmp_path, levels=("A", "J"))

    assert reality["counts"] == _expected()
    assert reality["direct_chunk_field_present"] is False
    assert reality["direct_situation_field_present"] is False
    assert reality["direct_scene_image_field_present"] is False
    assert reality["direct_nonempty_counts"] == {
        "vocabulary": 0,
        "patterns": 0,
        "grammar": 0,
    }


def test_finalize_package_binds_reality_and_removes_image_claim(tmp_path: Path):
    _level(tmp_path, "A", rich=True)
    _level(tmp_path, "J", rich=False)
    reality = builder.scan_source_reality(tmp_path, levels=("A", "J"))
    package = builder.finalize_package(
        _base_package(),
        reality,
        expected_counts=_expected(),
        levels=("A", "J"),
    )

    assert package["validation_status"] == builder.PASS_STATUS
    assert package["extraction_gate"]["decision"] == "DERIVED_MATERIAL_READY_FOR_GOVERNANCE_BINDING"
    assert package["aggregate_summary"]["direct_picture_or_visual_tag_count"] == 0
    assert all(
        row["scene_evidence_status"] == "DERIVED_SCENE_STRUCTURE_ONLY"
        for row in package["page_unit_evidence"]
    )
    assert package["source_reality"]["theme_granularity"] == {
        "A_I": "BOOK_AND_UNIT",
        "J_W": "BOOK_ONLY_WITH_UNIT_PROJECTION",
    }
    assert not builder.base.scan_forbidden_safe_keys(package)
    assert validator.validate_package(
        package,
        expected_counts=_expected(),
        levels=("A", "J"),
    ) == []


def test_finalize_fails_gate_when_registry_count_drifts(tmp_path: Path):
    _level(tmp_path, "A", rich=True)
    _level(tmp_path, "J", rich=False)
    reality = builder.scan_source_reality(tmp_path, levels=("A", "J"))
    reality["counts"]["sentence_count"] -= 1
    package = builder.finalize_package(
        _base_package(),
        reality,
        expected_counts=_expected(),
        levels=("A", "J"),
    )

    assert package["validation_status"] == "FAIL"
    assert package["extraction_gate"]["ready_for_review_bridge_linkage_binding"] is False


def test_direct_scene_key_is_reported_not_promoted(tmp_path: Path):
    _level(tmp_path, "A", rich=True)
    path = tmp_path / "derived/Level_A/enriched/raz_A_enriched_books.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["records"][0]["picture_tags"] = ["room"]
    _write(path, payload)
    reality = builder.scan_source_reality(tmp_path, levels=("A",))

    assert reality["direct_scene_image_field_present"] is True
