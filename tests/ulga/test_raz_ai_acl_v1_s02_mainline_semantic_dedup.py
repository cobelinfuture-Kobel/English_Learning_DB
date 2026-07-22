from __future__ import annotations

import copy

import pytest

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_ai_acl_v1_s01_material_admission as admission
from ulga.builders import build_raz_ai_acl_v1_s02_mainline_semantic_dedup as builder


def _row(
    ref: str,
    group: str,
    status: str,
    scope: str,
    *,
    vocabulary: list[str] | None = None,
    grammar: list[str] | None = None,
    skills: list[str] | None = None,
    maturity: str = "BROAD_CORE_SENTENCE_SEED",
    passage: bool = False,
) -> dict:
    return {
        "source_unit_ref": ref,
        "source_level": ref[0],
        "source_book_id": f"BOOK_{ref[0]}",
        "admission_status": status,
        "candidate_cefr_scope": scope,
        "admission_reason_codes": ["FIXTURE"],
        "candidate_theme_refs": ["theme:a1_personal_information_and_greetings"],
        "matched_vocabulary_refs": vocabulary or [],
        "matched_chunk_refs": [],
        "matched_pattern_refs": [],
        "matched_grammar_unit_refs": grammar or [],
        "semantic_duplicate_group_id": group,
        "duplicate_representative_source_unit_ref": ref,
        "sentence_seed_maturity": maturity,
        "passage_seed_status": "SUPPORTED" if passage else "NOT_A_PASSAGE",
        "discourse_shape": "simple_narrative_or_description",
        "scene_structure": "GENERAL_CONTEXT_SCENE",
        "four_skill_affordances": skills or ["READING_SOURCE"],
        "promotion_status": "NOT_PROMOTED",
    }


def _admission_package() -> dict:
    rows = [
        _row(
            "A_EXACT", "G_EXACT", "A1_READY_CANDIDATE", "A1",
            vocabulary=["vocabulary:cat"], grammar=["GRAMMAR_BE_VERB_BASIC"],
        ),
        _row(
            "B_NEAR", "G_NEAR", "A1_READY_CANDIDATE", "A1",
            vocabulary=["vocabulary:dog"], grammar=["GRAMMAR_BE_VERB_BASIC"],
            skills=["READING_SOURCE", "SPEAKING_PROMPT"],
        ),
        _row(
            "C_NEW_WEAK", "G_NEW", "A1_READY_CANDIDATE", "A1",
            vocabulary=["vocabulary:bird"], grammar=["GRAMMAR_BE_VERB_BASIC"],
        ),
        _row(
            "C_NEW_STRONG", "G_NEW", "DUPLICATE_CANDIDATE", "NONE",
            vocabulary=["vocabulary:bird", "vocabulary:tree"],
            grammar=["GRAMMAR_BE_VERB_BASIC"],
            skills=["READING_SOURCE", "WRITING_MODEL"],
            maturity="STRICT_CORE_SENTENCE_SEED",
            passage=True,
        ),
        _row(
            "D_CONFLICT", "G_CONFLICT", "A1PLUS_READY_CANDIDATE", "A1_PLUS",
            vocabulary=["vocabulary:family"], grammar=["GRAMMAR_PAST_SIMPLE_A1"],
        ),
        _row(
            "E_REWRITE", "G_REWRITE", "REWRITE_REQUIRED", "A1_A1PLUS_UNRESOLVED",
            vocabulary=["vocabulary:book"],
        ),
        _row(
            "F_SUPPORT", "G_SUPPORT", "SUPPORT_ONLY", "NONE",
            skills=["READING_SOURCE", "SPEAKING_PROMPT"],
        ),
    ]
    package = {
        "task_id": admission.TASK_ID,
        "schema_version": admission.SCHEMA_VERSION,
        "validation_status": admission.PASS_STATUS,
        "admission_rows": rows,
        "admission_gate": {
            "decision": "MATERIAL_ADMISSION_CLASSIFICATION_READY",
            "distance_after": "D5",
        },
        "aggregate_summary": {},
        "errors": [],
    }
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _mainline() -> dict:
    return {
        "task_id": builder.M2_TASK_ID,
        "schema_version": "fixture",
        "validation_status": builder.M2_STATUS,
        "asset_records": [
            {
                "asset_key": "READING:EXACT",
                "asset_id": "EXACT",
                "lesson_id": "L-A1-1",
                "skill": "READING",
                "level": "A1",
                "role": "EVD",
                "payload": {"body": "The cat is on the mat."},
            },
            {
                "asset_key": "READING:NEAR",
                "asset_id": "NEAR",
                "lesson_id": "L-A1-2",
                "skill": "READING",
                "level": "A1",
                "role": "EVD",
                "payload": {"body": "The dog is under the table."},
            },
            {
                "asset_key": "READING:CONFLICT",
                "asset_id": "CONFLICT",
                "lesson_id": "L-A1-3",
                "skill": "READING",
                "level": "A1",
                "role": "EVD",
                "payload": {"body": "My family went to the park."},
            },
            {
                "asset_key": "READING:A2_LOCKED",
                "asset_id": "A2_LOCKED",
                "lesson_id": "L-A2-1",
                "skill": "READING",
                "level": "A2",
                "role": "EVD",
                "payload": {"body": "A bright bird sits in the old tree."},
            },
        ],
        "lesson_catalog": [],
        "counts": {"asset_record_count": 4},
        "access_contract": {
            "learning_query_levels": ["A1", "A1+"],
            "a2_payload_query_allowed": False,
        },
        "errors": [],
    }


def _texts() -> dict[str, str]:
    return {
        "A_EXACT": "The cat is on the mat.",
        "B_NEAR": "The dog is under the small table.",
        "C_NEW_WEAK": "A bright bird sits in the old tree.",
        "C_NEW_STRONG": "A bright bird sits in the old tree.",
        "D_CONFLICT": "My family went to the park.",
        "E_REWRITE": "This book belongs to Mina.",
        "F_SUPPORT": "Look carefully at the picture.",
    }


def _build(monkeypatch: pytest.MonkeyPatch) -> dict:
    monkeypatch.setattr(builder, "EXPECTED_SCOPE_ROW_COUNT", 7)
    monkeypatch.setattr(builder, "EXPECTED_GROUP_COUNT", 6)
    monkeypatch.setattr(builder, "EXPECTED_DUPLICATE_EXCESS", 1)
    mainline = _mainline()
    return builder.build_package(
        _admission_package(),
        mainline,
        _texts(),
        [{"level": "A", "source_path": "A.json", "record_count": 7, "sha256": "a" * 64}],
        mainline_index_sha256=builder._digest(mainline),
        expected_mainline_asset_count=4,
    )


def test_selects_best_representatives_and_resolves_mainline_dedup(monkeypatch: pytest.MonkeyPatch) -> None:
    package = _build(monkeypatch)
    assert package["validation_status"] == builder.PASS_STATUS
    assert package["dedup_gate"]["decision"] == "MAINLINE_SEMANTIC_DEDUP_READY"
    assert package["dedup_gate"]["distance_after"] == "D4"

    rows = {row["semantic_duplicate_group_id"]: row for row in package["representative_rows"]}
    assert rows["G_NEW"]["representative_source_unit_ref"] == "C_NEW_STRONG"
    assert rows["G_EXACT"]["dedup_disposition"] == "EXACT_DUPLICATE"
    assert rows["G_NEAR"]["dedup_disposition"] == "VARIANT_WORTH_KEEPING"
    assert rows["G_NEW"]["dedup_disposition"] == "NEW_COMPLEMENTARY_MATERIAL"
    assert rows["G_CONFLICT"]["dedup_disposition"] == "CONFLICTING_AUTHORITY_MAPPING"
    assert rows["G_CONFLICT"]["conflict_resolution"] == "RESOLVED_BY_EXCLUSION_FROM_LINKAGE"
    assert rows["G_REWRITE"]["dedup_disposition"] == "REWRITE_REQUIRED_NOT_LINKABLE"
    assert rows["G_SUPPORT"]["dedup_disposition"] == "SUPPORT_ONLY_NOT_LINKABLE"

    summary = package["aggregate_summary"]
    assert summary["semantic_identity_count"] == 6
    assert summary["duplicate_excess_count"] == 1
    assert summary["linkage_candidate_count"] == 2
    assert summary["unresolved_conflict_count"] == 0
    assert package["mainline_index_summary"]["a2_asset_record_count_skipped_without_payload_traversal"] == 1


def test_a2_payload_match_is_not_used(monkeypatch: pytest.MonkeyPatch) -> None:
    package = _build(monkeypatch)
    row = next(row for row in package["representative_rows"] if row["semantic_duplicate_group_id"] == "G_NEW")
    assert row["mainline_match"] is None
    assert row["dedup_disposition"] == "NEW_COMPLEMENTARY_MATERIAL"
    assert package["claim_boundaries"]["a2_payload_semantic_comparison_performed"] is False


def test_tampered_admission_package_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(builder, "EXPECTED_SCOPE_ROW_COUNT", 7)
    package = copy.deepcopy(_admission_package())
    package["admission_rows"][0]["source_book_id"] = "tampered"
    with pytest.raises(builder.SemanticDedupError, match="admission_package_sha256_mismatch"):
        builder.build_package(
            package,
            _mainline(),
            _texts(),
            [],
            mainline_index_sha256="f" * 64,
        )


def test_safe_output_contains_no_source_or_mainline_text(monkeypatch: pytest.MonkeyPatch) -> None:
    package = _build(monkeypatch)
    serialized = builder._canonical(package)
    assert "The cat is on the mat" not in serialized
    assert "A bright bird sits" not in serialized
    assert builder._scan_forbidden(package) == []
