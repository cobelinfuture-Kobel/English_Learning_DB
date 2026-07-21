from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_raz_af_full_material_yield_and_sufficiency as builder
from ulga.validators import validate_raz_af_full_material_yield_and_sufficiency as validator

HEX = "a" * 64


def _record(index: int, *, semantic: bool = False) -> dict:
    unit_id = f"GRAMMAR_UNIT_{index:02d}"
    return {
        "identity": {
            "source_unit_ref": f"RAZ_A_{index}_P001",
            "source_level": "ABCDEF"[(index - 1) % 6],
            "source_book_id": str(index),
        },
        "observations": {
            "vocabulary_exposure": {"items": [{"evp_candidate_refs": [f"vocabulary:v{index}:v_1"]}]},
            "chunk_exposure": {"items": [{"canonical_chunk_id": f"CHUNK_{index:02d}"}]},
            "sentence_pattern_observations": {"items": [{
                "pattern_authority_candidate_refs": [f"pattern:P{index:02d}"],
                "grammar_candidate_refs": [unit_id],
            }]},
            "situation_function_observations": {
                "macro_domain_candidates": [f"theme_{index % 4}"],
                "situation_family_candidates": [f"family_{index}"],
                "micro_situation_candidates": [f"micro_{index}"],
                "communicative_function_candidates": [f"function_{index}"],
                "participant_role_candidates": ["child_parent"],
                "interaction_goal_candidates": ["share_information"],
            },
            "discourse_observation": {
                "discourse_shape": "question_answer",
                "retelling_potential": True,
            },
            "pedagogical_signals": {
                "picture_support_potential": {"status": "SUPPORTED"},
            },
            "quality_and_review": {
                "semantic_pass_status": "APPLIED" if semantic else "NOT_SUPPLIED",
            },
        },
    }


def _learning_units() -> dict:
    rows = []
    row_number = 1
    for index in range(1, 25):
        count = 5 if index <= 13 else 4
        ids = [f"EGP_{row_number + offset:03d}" for offset in range(count)]
        row_number += count
        rows.append({
            "grammar_unit_id": f"GRAMMAR_UNIT_{index:02d}",
            "canonical_egp_row_ids": ids,
        })
    assert row_number - 1 == 109
    return {"learning_units": rows}


def _baselines() -> dict:
    return {
        "vocabulary": {
            "count": 24,
            "ids": [f"vocabulary:v{i}:v_1" for i in range(1, 25)],
            "source_path": "ulga/graph/vocabulary_nodes.json",
            "source_sha256": HEX,
        },
        "chunks": {
            "count": 24,
            "ids": [f"CHUNK_{i:02d}" for i in range(1, 25)],
            "source_path": "chunk_profile/json/chunks_generator_safe.json",
            "source_sha256": HEX,
        },
        "patterns": {
            "count": 24,
            "ids": [f"pattern:P{i:02d}" for i in range(1, 25)],
            "source_path": "ulga/graph/sentence_patterns.json",
            "source_sha256": HEX,
        },
        "themes": {
            "count": 4,
            "ids": [f"theme_{i}" for i in range(4)],
            "source_path": "ulga/graph/theme_nodes.json",
            "source_sha256": HEX,
        },
    }


def _bundle(*, semantic: bool = False):
    records = [_record(index, semantic=semantic) for index in range(1, 25)]
    query = {"record_count": 24}
    coverage = {"summary": {"s12c_records_indexed": 24, "represented_book_count": 24}}
    return records, query, coverage, _learning_units(), _baselines()


def _build(*, semantic: bool = False):
    return builder.build_report(
        *_bundle(semantic=semantic),
        expected_records=24,
        expected_books=24,
    )


def test_full_af_report_counts_theme_core_sentence_and_24_unit_projection():
    report = _build()
    observed = report["observed_material_yield"]

    assert report["source_accounting"]["record_count"] == 24
    assert report["source_accounting"]["learning_unit_count"] == 24
    assert report["source_accounting"]["canonical_grammar_row_count"] == 109
    assert observed["vocabulary_authority_ref_count"] == 24
    assert observed["canonical_chunk_ref_count"] == 24
    assert observed["sentence_pattern_ref_count"] == 24
    assert observed["macro_domain_count"] == 4
    assert observed["situation_family_count"] == 24
    assert observed["micro_situation_count"] == 24
    assert observed["core_sentence_seed_record_count"] == 24
    assert len(report["unit_suitability"]) == 24
    assert all(row["record_count"] == 1 for row in report["unit_suitability"])


def test_incomplete_semantic_depth_blocks_gw_expansion_and_requires_deeper_af_reading():
    report = _build(semantic=False)
    gate = report["sufficiency_gate"]

    assert gate["source_integrity"]["pass"] is True
    assert gate["decision"] == "DEEPEN_AF_SEMANTIC_EXTRACTION_BEFORE_GW"
    assert gate["targeted_gw_expansion_allowed"] is False
    assert report["scope"]["g_w_read_performed"] is False


def test_semantically_complete_but_still_sparse_allows_only_targeted_gw_expansion():
    report = _build(semantic=True)
    gate = report["sufficiency_gate"]

    assert report["observed_material_yield"]["semantic_completion_rate"] == 1.0
    assert gate["decision"] == "TARGETED_GW_EXPANSION_REQUIRED"
    assert gate["targeted_gw_expansion_allowed"] is True


def test_dense_af_material_can_pass_population_gate(monkeypatch):
    for key in (
        "unit_records",
        "unit_families",
        "unit_micro_situations",
        "unit_functions",
        "unit_core_seeds",
        "unit_passage_seeds",
    ):
        monkeypatch.setitem(builder.THRESHOLDS, key, 1)

    report = _build(semantic=True)
    gate = report["sufficiency_gate"]
    assert gate["decision"] == "AF_SUFFICIENT_FOR_CONTENT_POPULATION"
    assert gate["af_sufficient_for_content_population"] is True
    assert gate["targeted_gw_expansion_allowed"] is False


def test_source_accounting_drift_fails_closed_before_sufficiency_claim():
    records, query, coverage, units, baselines = _bundle()
    query["record_count"] = 23
    report = builder.build_report(
        records, query, coverage, units, baselines,
        expected_records=24, expected_books=24,
    )
    assert report["sufficiency_gate"]["decision"] == "BLOCKED_SOURCE_INTEGRITY"
    assert report["sufficiency_gate"]["source_integrity"]["checks"]["query_record_count_matches"] is False


def test_independent_validator_accepts_deterministic_report_and_rejects_tampering():
    bundle = _bundle()
    report = builder.build_report(*bundle, expected_records=24, expected_books=24)
    validation = validator.validate_report(
        report,
        records=bundle[0],
        query=bundle[1],
        coverage=bundle[2],
        units=bundle[3],
        baselines=bundle[4],
    )
    assert validation["error_count"] == 0, validation

    tampered = deepcopy(report)
    tampered["observed_material_yield"]["core_sentence_seed_record_count"] = 0
    failed = validator.validate_report(tampered)
    assert failed["validation_status"] == "FAIL"
    assert "report_sha256_mismatch" in failed["errors"]


def test_safe_report_rejects_text_bearing_fields():
    report = _build()
    report["source_text"] = "forbidden"
    errors = builder.scan_forbidden(report)
    assert any("source_text" in error for error in errors)
