from __future__ import annotations

import copy

import pytest

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_ai_acl_v1_s01_material_admission as admission
from ulga.builders import build_raz_ai_acl_v1_s02_semantic_dedup as dedup


def _row(
    ref: str,
    level: str,
    group: str,
    status: str,
    scope: str,
    provisional: str | None,
    *,
    vocabulary: list[str] | None = None,
    grammar: list[str] | None = None,
    chunks: list[str] | None = None,
    patterns: list[str] | None = None,
    skills: list[str] | None = None,
    maturity: str = "BROAD_CORE_SENTENCE_SEED",
    passage: bool = False,
) -> dict[str, object]:
    return {
        "source_unit_ref": ref,
        "source_level": level,
        "source_book_id": f"BOOK_{level}",
        "admission_status": status,
        "candidate_cefr_scope": scope,
        "admission_reason_codes": ["FIXTURE"],
        "candidate_theme_refs": ["theme:a1_personal_information_and_greetings"],
        "matched_vocabulary_refs": vocabulary or [],
        "matched_chunk_refs": chunks or [],
        "matched_pattern_refs": patterns or [],
        "matched_grammar_unit_refs": grammar or [],
        "semantic_duplicate_group_id": group,
        "duplicate_representative_source_unit_ref": provisional,
        "sentence_seed_maturity": maturity,
        "passage_seed_status": "SUPPORTED" if passage else "NOT_A_PASSAGE",
        "discourse_shape": "simple_narrative_or_description",
        "scene_structure": "GENERAL_CONTEXT_SCENE",
        "four_skill_affordances": skills or ["READING_SOURCE"],
        "promotion_status": "NOT_PROMOTED",
    }


def _admission_package() -> dict[str, object]:
    rows = [
        _row(
            "A_EXACT", "A", "G_EXACT", "A1_READY_CANDIDATE", "A1", "A_EXACT",
            vocabulary=["vocabulary:cat"], grammar=["GRAMMAR_BE_VERB_BASIC"],
        ),
        _row(
            "B_NEAR", "B", "G_NEAR", "A1_READY_CANDIDATE", "A1", "B_NEAR",
            vocabulary=["vocabulary:dog"], grammar=["GRAMMAR_BE_VERB_BASIC"],
            skills=["READING_SOURCE", "SPEAKING_PROMPT"],
        ),
        _row(
            "C_NEW_WEAK", "C", "G_NEW", "A1_READY_CANDIDATE", "A1", "C_NEW_WEAK",
            vocabulary=["vocabulary:bird"], grammar=["GRAMMAR_BE_VERB_BASIC"],
        ),
        _row(
            "C_NEW_STRONG", "C", "G_NEW", "DUPLICATE_CANDIDATE", "NONE", "C_NEW_WEAK",
            vocabulary=["vocabulary:bird", "vocabulary:tree"],
            grammar=["GRAMMAR_BE_VERB_BASIC"],
            skills=["READING_SOURCE", "WRITING_MODEL"],
            maturity="STRICT_CORE_SENTENCE_SEED",
            passage=True,
        ),
        _row(
            "D_CONFLICT", "D", "G_CONFLICT", "A1PLUS_READY_CANDIDATE", "A1_PLUS", "D_CONFLICT",
            vocabulary=["vocabulary:family"], grammar=["GRAMMAR_PAST_SIMPLE_A1"],
        ),
        _row(
            "E_REWRITE", "E", "G_REWRITE", "REWRITE_REQUIRED", "A1_A1PLUS_UNRESOLVED", "E_REWRITE",
            vocabulary=["vocabulary:book"],
        ),
        _row(
            "F_SUPPORT", "F", "G_SUPPORT", "SUPPORT_ONLY", "NONE", "F_SUPPORT",
            chunks=["chunk:look_at"],
            skills=["READING_SOURCE", "SPEAKING_PROMPT"],
        ),
        _row(
            "J_DEFER", "J", "G_DEFER", "DEFERRED_A2_A2PLUS", "DEFERRED_A2_A2PLUS", None,
            vocabulary=["vocabulary:advanced"], grammar=["GRAMMAR_PAST_SIMPLE_A1"],
        ),
    ]
    status_counts: dict[str, int] = {}
    for row in rows:
        status = str(row["admission_status"])
        status_counts[status] = status_counts.get(status, 0) + 1
    package: dict[str, object] = {
        "task_id": admission.TASK_ID,
        "schema_version": admission.SCHEMA_VERSION,
        "validation_status": admission.PASS_STATUS,
        "input_identity": {},
        "scope_contract": {},
        "admission_rows": rows,
        "per_level_status_counts": {},
        "aggregate_summary": {
            "source_candidate_count": 8,
            "a1_a1plus_scope_candidate_count": 7,
            "semantic_duplicate_group_count": 6,
            "admission_status_counts": dict(sorted(status_counts.items())),
            "a1_ready_candidate_count": 3,
            "a1plus_ready_candidate_count": 1,
            "rewrite_required_count": 1,
            "support_only_count": 1,
            "duplicate_candidate_count": 1,
            "deferred_a2_a2plus_count": 1,
            "rejected_unusable_count": 0,
            "ready_candidate_count": 4,
            "final_promoted_material_count": 0,
        },
        "admission_gate": {
            "source_checks": {},
            "decision": "MATERIAL_ADMISSION_CLASSIFICATION_READY",
            "distance_before": "D6",
            "distance_after": "D5",
            "ready_for_semantic_dedup": True,
            "ready_for_canonical_linkage": False,
            "ready_for_material_promotion": False,
        },
        "claim_boundaries": {},
        "errors": [],
    }
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _mainline() -> dict[str, object]:
    return {
        "task_id": dedup.M2_TASK_ID,
        "schema_version": "fixture",
        "validation_status": dedup.M2_STATUS,
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


def _build(package: dict[str, object] | None = None) -> dict[str, object]:
    mainline = _mainline()
    return dedup.build_package(
        package or _admission_package(),
        mainline,
        _texts(),
        [{"level": "A", "source_path": "A.json", "record_count": 7, "sha256": "a" * 64}],
        mainline_index_sha256=dedup._digest(mainline),
        expected_total_page_unit_count=8,
        expected_scope_page_unit_count=7,
        expected_semantic_identity_count=6,
        expected_duplicate_binding_count=1,
        expected_deferred_page_unit_count=1,
        expected_mainline_asset_count=4,
    )


def test_selects_best_representative_and_resolves_mainline_dispositions() -> None:
    package = _build()
    assert package["validation_status"] == dedup.PASS_STATUS
    assert package["dedup_gate"]["decision"] == "MAINLINE_SEMANTIC_DEDUP_READY"
    assert package["dedup_gate"]["distance_after"] == "D4"
    rows = {
        row["semantic_duplicate_group_id"]: row
        for row in package["semantic_representatives"]
    }
    assert rows["G_NEW"]["selected_source_unit_ref"] == "C_NEW_STRONG"
    assert rows["G_EXACT"]["dedup_disposition"] == "EXACT_DUPLICATE"
    assert rows["G_NEAR"]["dedup_disposition"] == "VARIANT_WORTH_KEEPING"
    assert rows["G_NEW"]["dedup_disposition"] == "NEW_COMPLEMENTARY_MATERIAL"
    assert rows["G_CONFLICT"]["dedup_disposition"] == "CONFLICTING_AUTHORITY_MAPPING"
    assert rows["G_CONFLICT"]["conflict_resolution"] == "RESOLVED_BY_EXCLUSION_FROM_LINKAGE"
    assert rows["G_REWRITE"]["dedup_disposition"] == "REWRITE_REQUIRED_NOT_LINKABLE"
    assert rows["G_SUPPORT"]["dedup_disposition"] == "SUPPORT_ONLY_NOT_LINKABLE"
    summary = package["aggregate_summary"]
    assert summary["semantic_identity_count"] == 6
    assert summary["duplicate_binding_count"] == 1
    assert summary["deferred_a2_a2plus_count"] == 1
    assert summary["linkage_candidate_count"] == 2
    assert summary["unresolved_conflict_count"] == 0
    assert package["mainline_index_summary"][
        "a2_asset_record_count_skipped_without_payload_traversal"
    ] == 1


def test_a2_payload_match_is_not_used() -> None:
    package = _build()
    row = next(
        row for row in package["semantic_representatives"]
        if row["semantic_duplicate_group_id"] == "G_NEW"
    )
    assert row["mainline_match"] is None
    assert row["dedup_disposition"] == "NEW_COMPLEMENTARY_MATERIAL"
    assert package["claim_boundaries"][
        "a2_payload_semantic_comparison_performed"
    ] is False


def test_tampered_admission_package_fails_closed() -> None:
    package = copy.deepcopy(_admission_package())
    package["aggregate_summary"]["duplicate_candidate_count"] = 99
    with pytest.raises(
        dedup.SemanticDedupError,
        match="admission_package_sha256_mismatch",
    ):
        _build(package)


def test_safe_output_contains_no_source_or_mainline_text() -> None:
    package = _build()
    serialized = dedup._canonical(package)
    assert "The cat is on the mat" not in serialized
    assert "A bright bird sits" not in serialized
    assert dedup._scan_forbidden(package) == []
    assert package["claim_boundaries"]["raz_level_used_as_cefr_equivalence"] is False
    assert package["dedup_gate"]["ready_for_material_promotion"] is False
