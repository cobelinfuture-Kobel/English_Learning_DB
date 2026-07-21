from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_gi_targeted_gap_source_expansion as builder
from ulga.validators import validate_raz_gi_targeted_gap_source_expansion as validator


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
            ["child", "read", "book", "school", "happy", "because"],
        ),
        "chunks": _authority(
            "chunks",
            ["at school", "read sth", "because of sth", "be happy"],
        ),
        "patterns": _authority(
            "patterns",
            ["I can {verb_stem}.", "cannot {verb_stem}", "because {clause}"],
        ),
        "themes": _authority("themes", ["School"]),
    }


def _record(ref: str, level: str, book_id: str, text: str) -> dict:
    return {
        "page_unit_id": ref,
        "book_id": book_id,
        "level": level,
        "title": "Fixture",
        "page_number": 1,
        "sentence_count": 2 if "." in text.rstrip(".") else 1,
        "text": text,
        "content_unit_tags": {
            "has_direct_speech": "?" in text,
            "has_sequence": False,
        },
        "theme_tags": {
            "primary_theme": "School",
            "mapped_theme": "School",
        },
        "reuse_tags": {"reusability_tags": ["picture_prompt_seed"]},
    }


def _indexes(levels: tuple[str, ...], records: list[dict]) -> list[dict]:
    return [
        {
            "level": level,
            "path": f"raz_{level}_page_unit_enriched.json",
            "page_unit_count": sum(row["level"] == level for row in records),
            "book_count": len({row["book_id"] for row in records if row["level"] == level}),
            "sha256": "b" * 64,
        }
        for level in levels
    ]


def _bundle():
    af = [
        _record("RAZ_A_1_P001", "A", "1", "The child can read a book at school."),
        _record("RAZ_B_2_P001", "B", "2", "The child is happy at school."),
        _record("RAZ_C_3_P001", "C", "3", "The child reads a book at school."),
        _record("RAZ_D_4_P001", "D", "4", "The child can read."),
        _record("RAZ_E_5_P001", "E", "5", "The child is at school."),
        _record("RAZ_F_6_P001", "F", "6", "The child has a book."),
    ]
    gi = [
        _record("RAZ_G_7_P001", "G", "7", "The child cannot read at school."),
        _record("RAZ_H_8_P001", "H", "8", "The child is happy because school is fun."),
        _record("RAZ_I_9_P001", "I", "9", "The child can read a book at school."),
    ]
    return af, _indexes(builder.AF_LEVELS, af), gi, _indexes(builder.GI_LEVELS, gi)


def _build(monkeypatch, **thresholds):
    defaults = {
        "combined_vocabulary_coverage_rate": 0.0,
        "combined_chunk_coverage_rate": 0.0,
        "combined_pattern_coverage_rate": 0.0,
        "target_unit_record_count": 1,
        "target_unit_strict_core_seed_count": 1,
        "target_unit_passage_seed_count": 0,
    }
    defaults.update(thresholds)
    for key, value in defaults.items():
        monkeypatch.setitem(builder.THRESHOLDS, key, value)
    af, af_index, gi, gi_index = _bundle()
    return builder.build_report(
        af,
        af_index,
        gi,
        gi_index,
        _authorities(),
        {},
        expected_af_records=len(af),
        expected_af_books=6,
        expected_gi_records=len(gi),
        expected_gi_books=3,
    )


def test_gi_report_preserves_scope_and_recomputes_af_delta(monkeypatch):
    report = _build(monkeypatch)
    scope = report["source_scope"]

    assert scope["af_levels"] == list(builder.AF_LEVELS)
    assert scope["gi_levels"] == list(builder.GI_LEVELS)
    assert scope["af_record_count"] == 6
    assert scope["gi_record_count"] == 3
    assert scope["j_w_read_performed"] is False
    assert report["claim_boundaries"] == builder.CLAIM_BOUNDARIES


def test_gi_adds_material_and_repairs_can_negative(monkeypatch):
    report = _build(monkeypatch)
    coverage = report["targeted_gap_yield"]["authority_coverage"]
    units = {
        row["grammar_unit_id"]: row
        for row in report["targeted_gap_yield"]["target_learning_units"]
    }

    assert coverage["patterns"]["gi_new_authority_count"] >= 1
    assert coverage["chunks"]["combined_observed_count"] >= coverage["chunks"]["af_observed_count"]
    assert units["GRAMMAR_CAN_NEGATIVE_A1"]["gi_record_count"] == 1
    assert units["GRAMMAR_CAN_NEGATIVE_A1"]["combined_strict_core_seed_count"] >= 1


def test_proven_remaining_gap_opens_only_targeted_jw(monkeypatch):
    report = _build(
        monkeypatch,
        combined_chunk_coverage_rate=1.0,
        target_unit_record_count=2,
        target_unit_strict_core_seed_count=2,
    )
    gate = report["sufficiency_gate"]

    assert gate["decision"] == "TARGETED_JW_EXPANSION_REQUIRED"
    assert gate["targeted_j_w_expansion_allowed"] is True
    assert gate["a_i_sufficient_for_content_population"] is False
    assert gate["remaining_asset_gap_counts"]["chunks"] > 0 or gate["remaining_weak_units"]


def test_complete_ai_gate_blocks_unnecessary_jw(monkeypatch):
    report = _build(monkeypatch)
    gate = report["sufficiency_gate"]

    assert gate["decision"] == "AI_SUFFICIENT_FOR_CONTENT_POPULATION"
    assert gate["a_i_sufficient_for_content_population"] is True
    assert gate["targeted_j_w_expansion_allowed"] is False


def test_source_drift_fails_closed(monkeypatch):
    for key in builder.THRESHOLDS:
        monkeypatch.setitem(builder.THRESHOLDS, key, 0)
    af, af_index, gi, gi_index = _bundle()
    report = builder.build_report(
        af,
        af_index,
        gi,
        gi_index,
        _authorities(),
        {},
        expected_af_records=len(af) + 1,
        expected_af_books=6,
        expected_gi_records=len(gi),
        expected_gi_books=3,
    )
    assert report["sufficiency_gate"]["decision"] == "BLOCKED_SOURCE_INTEGRITY"


def test_validator_accepts_deterministic_report_and_rejects_tampering(monkeypatch):
    report = _build(monkeypatch)
    valid = validator.validate_report(
        report,
        rebuilt=report,
        schema_path=Path(__file__).resolve().parents[2]
        / "ulga/schemas/raz_gi_targeted_gap_source_expansion.schema.json",
    )
    assert valid["error_count"] == 0, valid

    tampered = deepcopy(report)
    tampered["sufficiency_gate"]["remaining_asset_gap_counts"]["chunks"] = 0
    failed = validator.validate_report(tampered)
    assert "report_sha256_mismatch" in failed["errors"]


def test_safe_output_rejects_text_fields(monkeypatch):
    report = _build(monkeypatch)
    report["source_text"] = "forbidden"
    assert deep.scan_forbidden_safe_keys(report)
