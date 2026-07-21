from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from ulga.builders import build_raz_af_deep_semantic_material_alignment as builder
from ulga.validators import validate_raz_af_deep_semantic_material_alignment as validator


def _authority(name: str, forms: list[str]) -> dict:
    rows = [
        {
            "id": f"{name}:{index:02d}",
            "form": form,
            "normalized": builder.normalize(form),
            "regex": builder._literal_template(form)
            if name in {"chunks", "patterns"}
            else None,
            "metadata": {},
        }
        for index, form in enumerate(forms, 1)
    ]
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
            ["child", "school", "book", "teacher", "happy", "can", "read", "because"],
        ),
        "chunks": _authority("chunks", ["at school", "read sth", "be called sth"]),
        "patterns": _authority(
            "patterns",
            [
                "I can {verb_stem}.",
                "Can you {verb_stem}?",
                "be called sth",
            ],
        ),
        "themes": _authority("themes", ["School"]),
    }


def _units() -> dict:
    rows = []
    row_number = 1
    for index, unit_id in enumerate(builder.UNIT_IDS):
        count = 5 if index < 13 else 4
        ids = [f"EGP_{value:03d}" for value in range(row_number, row_number + count)]
        row_number += count
        rows.append({"grammar_unit_id": unit_id, "canonical_egp_row_ids": ids})
    assert row_number - 1 == 109
    return {"learning_units": rows}


def _record(index: int, text: str = "The child can read a book at school.") -> dict:
    return {
        "page_unit_id": f"RAZ_A_{index}_P001",
        "book_id": str(index),
        "level": "ABCDEF"[(index - 1) % 6],
        "title": "School Reading",
        "page_number": 1,
        "sentence_count": 1,
        "text": text,
        "content_unit_tags": {
            "has_direct_speech": "?" in text,
            "has_sequence": "then" in text.casefold(),
        },
        "theme_tags": {
            "primary_theme": "School",
            "mapped_theme": "School",
        },
        "reuse_tags": {
            "reusability_tags": ["picture_prompt_seed"],
        },
    }


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


def _report(records: list[dict], monkeypatch) -> dict:
    for key in (
        "vocabulary_authority_coverage_rate",
        "chunk_authority_coverage_rate",
        "pattern_authority_coverage_rate",
        "semantic_record_completion_rate",
    ):
        monkeypatch.setitem(builder.THRESHOLDS, key, 0.0)
    for key in (
        "unit_record_count",
        "unit_situation_family_count",
        "unit_micro_situation_count",
        "unit_communicative_function_count",
        "unit_strict_core_seed_count",
        "unit_passage_seed_count",
    ):
        monkeypatch.setitem(builder.THRESHOLDS, key, 0)
    return builder.build_report(
        records,
        _file_index(records),
        {},
        _authorities(),
        _units(),
        expected_record_count=len(records),
        expected_book_count=len({(row["level"], row["book_id"]) for row in records}),
    )


def test_template_compiler_matches_slots_optionals_and_alternatives():
    assert __import__("re").search(
        builder._literal_template("be called sth"), "she is called mia"
    )
    assert __import__("re").search(
        builder._literal_template("get (sb) up"), "get him up"
    )
    assert __import__("re").search(
        builder._literal_template("put sth down/in/on, etc."), "put the book on"
    )


def test_semantic_alignment_emits_family_micro_function_role_and_goal():
    aligned = builder.semantic_alignment(
        _record(1, "Where is my book at school? The teacher can help.")
    )
    assert "school_and_classroom" in aligned["situation_families"]
    assert aligned["micro_situations"]
    assert "asking_for_information" in aligned["communicative_functions"]
    assert "student_teacher" in aligned["participant_roles"]
    assert "locate_or_identify" in aligned["interaction_goals"]


def test_weak_unit_detectors_cover_negative_question_future_and_because():
    assert "GRAMMAR_PRESENT_SIMPLE_NEGATIVES" in builder.grammar_units(
        "I don't like milk.", []
    )
    assert "GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS" in builder.grammar_units(
        "Do you like milk?", []
    )
    assert "GRAMMAR_CAN_NEGATIVE_A1" in builder.grammar_units(
        "She cannot swim.", []
    )
    assert "GRAMMAR_WILL_FUTURE_A1" in builder.grammar_units(
        "We will go tomorrow.", []
    )
    assert "GRAMMAR_BECAUSE_REASON_CLAUSES_A1" in builder.grammar_units(
        "I am happy because school is fun.", []
    )


def test_report_has_all_six_material_layers_and_24_unit_projection(monkeypatch):
    records = [_record(index) for index in range(1, 25)]
    report = _report(records, monkeypatch)
    material = report["material_alignment"]

    assert set(material) == {
        "vocabulary",
        "chunks",
        "sentence_patterns",
        "theme_situation",
        "grammar_usage",
        "discourse_shape_counts",
        "seeds",
    }
    assert material["theme_situation"]["semantic_complete_record_count"] == 24
    assert material["seeds"]["strict_core_sentence_seed_record_count"] == 24
    assert len(report["learning_unit_suitability"]) == 24
    assert report["source_scope"]["g_w_read_performed"] is False


def test_targeted_gw_requires_completed_af_semantics(monkeypatch):
    records = [_record(index) for index in range(1, 25)]
    report = _report(records, monkeypatch)
    report["sufficiency_gate"]["checks"]["chunk_coverage"] = False
    report["sufficiency_gate"]["decision"] = "TARGETED_GW_EXPANSION_REQUIRED"
    report["sufficiency_gate"]["targeted_gw_expansion_allowed"] = True
    report["sufficiency_gate"]["af_sufficient_for_content_population"] = False
    report["report_sha256"] = builder.sha256_value({
        key: value for key, value in report.items() if key != "report_sha256"
    })

    result = validator.validate_report(report)
    assert result["error_count"] == 0, result

    invalid = deepcopy(report)
    invalid["sufficiency_gate"]["checks"]["semantic_alignment_complete"] = False
    invalid["report_sha256"] = builder.sha256_value({
        key: value for key, value in invalid.items() if key != "report_sha256"
    })
    failed = validator.validate_report(invalid)
    assert "gw_expansion_before_af_semantic_completion" in failed["errors"]


def test_validator_rejects_hash_tampering_and_text_leakage(monkeypatch):
    report = _report([_record(index) for index in range(1, 25)], monkeypatch)
    valid = validator.validate_report(
        report,
        schema_path=Path(__file__).resolve().parents[2]
        / "ulga/schemas/raz_af_deep_semantic_material_alignment.schema.json",
    )
    assert valid["error_count"] == 0, valid

    tampered = deepcopy(report)
    tampered["material_alignment"]["seeds"]["strict_core_sentence_seed_record_count"] = 0
    failed = validator.validate_report(tampered)
    assert "report_sha256_mismatch" in failed["errors"]

    leaked = deepcopy(report)
    leaked["source_text"] = "forbidden"
    assert builder.scan_forbidden_safe_keys(leaked)
