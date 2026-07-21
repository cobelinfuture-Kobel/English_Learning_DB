from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_ai_theme_sentence_scene_candidate_classification as builder
from ulga.validators import validate_raz_ai_theme_sentence_scene_candidate_classification as validator


def _authority(name: str, forms: list[str]) -> dict:
    rows = []
    for index, form in enumerate(forms, 1):
        rows.append({
            "id": f"{name}:{index:02d}",
            "form": form,
            "normalized": deep.normalize(form),
            "regex": deep._literal_template(form)
            if name in {"chunks", "patterns"}
            else None,
            "metadata": {},
        })
    return {
        "rows": rows,
        "count": len(rows),
        "ids": {row["id"] for row in rows},
        "source_path": f"fixture/{name}.json",
        "source_sha256": "a" * 64,
    }


def _authorities() -> dict:
    return {
        "vocabulary": _authority(
            "vocabulary",
            ["child", "book", "school", "read", "happy", "because", "bus", "map"],
        ),
        "chunks": _authority("chunks", ["at school", "read sth", "because of sth"]),
        "patterns": _authority(
            "patterns",
            ["I can {verb_stem}.", "because {clause}", "Where is {noun_phrase}?"],
        ),
        "themes": _authority("themes", ["School", "Travel"]),
    }


def _record(index: int, level: str, text: str, theme: str = "School") -> dict:
    return {
        "page_unit_id": f"RAZ_{level}_{index}_P001",
        "book_id": str(index),
        "level": level,
        "title": "Fixture",
        "page_number": 1,
        "sentence_count": 2 if text.count(".") >= 2 else 1,
        "text": text,
        "content_unit_tags": {
            "has_direct_speech": "?" in text,
            "has_sequence": "then" in text.casefold(),
        },
        "theme_tags": {
            "primary_theme": theme,
            "mapped_theme": theme,
        },
        "reuse_tags": {"reusability_tags": ["picture_prompt_seed"]},
    }


def _records() -> list[dict]:
    texts = [
        ("A", "The child can read a book at school.", "School"),
        ("B", "Where is the book at school?", "School"),
        ("C", "The child is happy because school is fun.", "School"),
        ("D", "First the child reads. Then the child writes.", "School"),
        ("E", "The child cannot read the book.", "School"),
        ("F", "The child has a red book.", "School"),
        ("G", "The child looks at a map near the bus.", "Travel"),
        ("H", "The child is at school. The teacher can help.", "School"),
        ("I", "The child reads a book at school.", "School"),
    ]
    return [
        _record(index, level, text, theme)
        for index, (level, text, theme) in enumerate(texts, 1)
    ]


def _file_index(records: list[dict]) -> list[dict]:
    return [
        {
            "level": level,
            "path": f"raz_{level}_page_unit_enriched.json",
            "page_unit_count": sum(row["level"] == level for row in records),
            "book_count": len({row["book_id"] for row in records if row["level"] == level}),
            "sha256": "b" * 64,
        }
        for level in builder.LEVELS
    ]


def _package():
    records = _records()
    return builder.build_package(
        records,
        _file_index(records),
        _authorities(),
        {},
        expected_record_count=len(records),
        expected_book_count=len(records),
    )


def test_classifies_theme_sentence_scene_and_cross_links_for_every_record():
    package = _package()
    summary = package["classification_summary"]

    assert summary["sentence_seed_candidate_count"] == 9
    assert summary["scene_seed_candidate_count"] == 9
    assert summary["cross_link_count"] == 9
    assert summary["theme_situation_candidate_count"] > 0
    assert all(row["theme_situation_candidate_ids"] for row in package["cross_links"])
    assert package["classification_gate"]["decision"] == "CLASSIFICATION_READY_FOR_REVIEW"


def test_sentence_seed_maturity_and_duplicate_grouping_are_deterministic():
    package = _package()
    rows = {row["source_unit_ref"]: row for row in package["sentence_seed_candidates"]}

    assert rows["RAZ_A_1_P001"]["seed_maturity"] == "STRICT_CORE_SENTENCE_SEED"
    assert rows["RAZ_B_2_P001"]["seed_maturity"] in {
        "BROAD_CORE_SENTENCE_SEED",
        "DIALOGUE_TURN_SEED",
    }
    assert all(row["promotion_status"] == "NOT_PROMOTED" for row in rows.values())


def test_scene_classifier_distinguishes_sequence_cause_and_route():
    package = _package()
    rows = {row["source_unit_ref"]: row for row in package["scene_seed_candidates"]}

    assert rows["RAZ_C_3_P001"]["scene_type"] == "CAUSE_EFFECT_SCENE"
    assert rows["RAZ_D_4_P001"]["scene_type"] == "SEQUENCE_SCENE"
    assert rows["RAZ_G_7_P001"]["scene_type"] == "MAP_OR_ROUTE_SCENE"
    assert rows["RAZ_D_4_P001"]["presentation_format"] == "MULTI_PANEL_SEQUENCE"


def test_theme_candidates_remain_unpromoted_and_preserve_canonical_match():
    package = _package()
    school = [
        row for row in package["theme_situation_candidates"]
        if row["source_macro_domain"] == "School"
    ]

    assert school
    assert all(row["canonical_theme_id"] == "themes:01" for row in school)
    assert all(row["disposition"] == "CANONICAL_THEME_MATCH" for row in school)
    assert all(row["promotion_status"] == "NOT_PROMOTED" for row in school)


def test_validator_accepts_deterministic_package_and_rejects_tampering():
    package = _package()
    valid = validator.validate_package(
        package,
        rebuilt=package,
        schema_path=Path(__file__).resolve().parents[2]
        / "ulga/schemas/raz_ai_theme_sentence_scene_candidate_classification.schema.json",
    )
    assert valid["error_count"] == 0, valid

    tampered = deepcopy(package)
    tampered["classification_summary"]["scene_seed_candidate_count"] = 0
    failed = validator.validate_package(tampered)
    assert "package_sha256_mismatch" in failed["errors"]
    assert "scene_seed_count_mismatch" in failed["errors"]


def test_safe_package_rejects_source_text_fields():
    package = _package()
    package["source_text"] = "forbidden"
    assert builder.scan_forbidden_safe_keys(package)
