from __future__ import annotations

import json
from pathlib import Path

import pytest

from ulga.builders import build_raz_aw_derived_schema_compatibility as compat


def _sentence(uid: str, text: str, *, dialogue: bool = False) -> dict:
    return {
        "sentence_uid": uid,
        "book_uid": "raz_W_1",
        "level": "W",
        "text": text,
        "punctuation_profile": {
            "contains_question_mark": "?" in text,
            "contains_quote_mark": False,
        },
        "dialogue_candidate_flag": dialogue,
    }


def _payloads():
    units = {
        "schema_version": "raz_enriched_units.v1",
        "records": [
            {
                "unit_uid": "raz_W_1_p0001",
                "unit_type": "page_unit",
                "book_uid": "raz_W_1",
                "level": "W",
                "sentence_uids": ["raz_W_1_s0001", "raz_W_1_s0002"],
                "candidate_reuse_tags": ["multi_sentence_unit", "page_unit"],
            }
        ],
    }
    sentences = {
        "schema_version": "raz_enriched_sentences.v1",
        "records": [
            _sentence("raz_W_1_s0001", "Where is the station?", dialogue=True),
            _sentence("raz_W_1_s0002", "The station is near the road."),
        ],
    }
    books = {
        "schema_version": "raz_enriched_books.v1",
        "records": [
            {
                "book_uid": "raz_W_1",
                "level": "W",
                "book_id": "1",
                "title": "Travel",
                "candidate_theme_tags": ["Travel"],
            }
        ],
    }
    return units, sentences, books


def test_reconstructs_j_w_page_unit_from_unit_sentence_book_registries():
    units, sentences, books = _payloads()
    rows = compat.reconstruct_page_units("W", units, sentences, books)

    assert len(rows) == 1
    row = rows[0]
    assert row["page_unit_id"] == "raz_W_1_p0001"
    assert row["book_id"] == "1"
    assert row["level"] == "W"
    assert row["sentence_count"] == 2
    assert row["text"] == "Where is the station? The station is near the road."
    assert row["content_unit_tags"]["has_direct_speech"] is True
    assert row["theme_tags"]["mapped_theme"] == "Travel"


def test_reconstruction_fails_closed_on_missing_sentence_uid():
    units, sentences, books = _payloads()
    units["records"][0]["sentence_uids"].append("raz_W_1_s9999")

    with pytest.raises(
        compat.DerivedSchemaCompatibilityError,
        match="unit_sentence_missing",
    ):
        compat.reconstruct_page_units("W", units, sentences, books)


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_load_derived_level_supports_legacy_and_reconstructed_contracts(tmp_path):
    legacy = [
        {
            "page_unit_id": "raz_A_1_p0001",
            "book_id": "1",
            "level": "A",
            "text": "A book.",
            "sentence_count": 1,
        }
    ]
    _write(
        tmp_path / "derived/Level_A/enriched/raz_A_page_unit_enriched.json",
        legacy,
    )
    a_rows, a_paths, a_schema = compat.load_derived_level(tmp_path, "A")
    assert a_rows == legacy
    assert len(a_paths) == 1
    assert a_schema == "page_unit_enriched.v1"

    units, sentences, books = _payloads()
    _write(
        tmp_path / "derived/Level_W/enriched/raz_W_enriched_units.json",
        units,
    )
    _write(
        tmp_path / "derived/Level_W/enriched/raz_W_enriched_sentences.json",
        sentences,
    )
    _write(
        tmp_path / "derived/Level_W/enriched/raz_W_enriched_books.json",
        books,
    )
    w_rows, w_paths, w_schema = compat.load_derived_level(tmp_path, "W")
    assert len(w_rows) == 1
    assert len(w_paths) == 3
    assert w_schema == "reconstructed_enriched_v1"


def test_review_bridge_source_ref_prefers_page_unit_id():
    record = {
        "source_traceability": {
            "source_page_unit_id": "raz_W_1_p0001",
            "source_passage_unit_id": None,
        }
    }
    assert compat.source_ref(record) == "raz_W_1_p0001"
