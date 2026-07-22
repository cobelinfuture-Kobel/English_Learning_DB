from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_ai_acl_v1_s01_material_admission as admission
from ulga.builders import build_raz_ai_acl_v1_s02_semantic_dedup as dedup


def _row(
    ref: str,
    level: str,
    group: str,
    status: str,
    provisional: str | None,
    *,
    vocabulary: list[str] | None = None,
    grammar: list[str] | None = None,
    chunks: list[str] | None = None,
    patterns: list[str] | None = None,
    themes: list[str] | None = None,
    skills: list[str] | None = None,
    maturity: str = "BROAD_CORE_SENTENCE_SEED",
    discourse: str = "simple_narrative_or_description",
    passage: str = "NOT_A_PASSAGE",
) -> dict[str, object]:
    return {
        "source_unit_ref": ref,
        "source_level": level,
        "source_book_id": f"BOOK_{level}",
        "admission_status": status,
        "candidate_cefr_scope": (
            "DEFERRED_A2_A2PLUS"
            if status == "DEFERRED_A2_A2PLUS"
            else "NONE"
        ),
        "admission_reason_codes": ["FIXTURE"],
        "candidate_theme_refs": themes or ["theme:a1_school_and_classroom"],
        "matched_vocabulary_refs": vocabulary or [],
        "matched_chunk_refs": chunks or [],
        "matched_pattern_refs": patterns or [],
        "matched_grammar_unit_refs": grammar or [],
        "semantic_duplicate_group_id": group,
        "duplicate_representative_source_unit_ref": provisional,
        "sentence_seed_maturity": maturity,
        "passage_seed_status": passage,
        "discourse_shape": discourse,
        "scene_structure": "GENERAL_CONTEXT_SCENE",
        "four_skill_affordances": skills or ["READING_SOURCE"],
        "promotion_status": "NOT_PROMOTED",
    }


def _package() -> dict[str, object]:
    rows = [
        _row(
            "A_001",
            "A",
            "G1",
            "SUPPORT_ONLY",
            "A_001",
            chunks=["chunk:look_at"],
        ),
        _row(
            "A_002",
            "A",
            "G1",
            "DUPLICATE_CANDIDATE",
            "A_001",
            vocabulary=["vocabulary:cat"],
            grammar=["GRAMMAR_BE_VERB_BASIC"],
            skills=["READING_SOURCE", "SPEAKING_PROMPT"],
            maturity="STRICT_CORE_SENTENCE_SEED",
        ),
        _row(
            "B_001",
            "B",
            "G2",
            "A1PLUS_READY_CANDIDATE",
            "B_001",
            vocabulary=["vocabulary:went"],
            grammar=["GRAMMAR_PAST_SIMPLE_A1"],
            discourse="sequence",
        ),
        _row(
            "C_001",
            "C",
            "G3",
            "REWRITE_REQUIRED",
            "C_001",
            vocabulary=["vocabulary:book"],
        ),
        _row(
            "D_001",
            "D",
            "G4",
            "SUPPORT_ONLY",
            "D_001",
            chunks=["chunk:in_the"],
            skills=["READING_SOURCE", "WRITING_MODEL"],
        ),
        _row(
            "J_001",
            "J",
            "G5",
            "DEFERRED_A2_A2PLUS",
            None,
            vocabulary=["vocabulary:advanced"],
            grammar=["GRAMMAR_PAST_SIMPLE_A1"],
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
            "source_candidate_count": 6,
            "a1_a1plus_scope_candidate_count": 5,
            "semantic_duplicate_group_count": 4,
            "admission_status_counts": dict(sorted(status_counts.items())),
            "a1_ready_candidate_count": 0,
            "a1plus_ready_candidate_count": 1,
            "rewrite_required_count": 1,
            "support_only_count": 2,
            "duplicate_candidate_count": 1,
            "deferred_a2_a2plus_count": 1,
            "rejected_unusable_count": 0,
            "ready_candidate_count": 1,
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


def _build(package: dict[str, object] | None = None) -> dict[str, object]:
    return dedup.build_package(
        package or _package(),
        expected_total_page_unit_count=6,
        expected_scope_page_unit_count=5,
        expected_semantic_identity_count=4,
        expected_duplicate_binding_count=1,
        expected_deferred_page_unit_count=1,
    )


def test_selects_stronger_representative_and_reconciles_every_scope_row() -> None:
    package = _build()
    assert package["validation_status"] == dedup.PASS_STATUS
    assert package["dedup_gate"]["decision"] == (
        "SEMANTIC_DEDUP_REPRESENTATIVES_READY"
    )
    assert package["dedup_gate"]["distance_after"] == "D4"

    summary = package["aggregate_summary"]
    assert summary["representative_count"] == 4
    assert summary["duplicate_binding_count"] == 1
    assert summary["ready_representative_count"] == 2
    assert summary["a1_ready_representative_count"] == 1
    assert summary["a1plus_ready_representative_count"] == 1
    assert summary["rewrite_required_representative_count"] == 1
    assert summary["support_only_representative_count"] == 1
    assert summary["representative_changed_from_s01_count"] == 1
    assert summary["classification_conflict_group_count"] == 1
    assert summary["final_promoted_material_count"] == 0

    representatives = {
        row["semantic_duplicate_group_id"]: row
        for row in package["semantic_representatives"]
    }
    assert representatives["G1"]["selected_source_unit_ref"] == "A_002"
    assert representatives["G1"]["representative_admission_status"] == (
        "A1_READY_CANDIDATE"
    )
    assert representatives["G1"]["representative_changed_from_s01"] is True
    assert package["duplicate_bindings"] == [
        {
            "semantic_duplicate_group_id": "G1",
            "duplicate_source_unit_ref": "A_001",
            "representative_source_unit_ref": "A_002",
            "binding_status": "BOUND_TO_SEMANTIC_REPRESENTATIVE",
        }
    ]


def test_equal_quality_uses_source_ref_only_as_stable_tiebreaker() -> None:
    package = _package()
    first, second = package["admission_rows"][:2]
    for key in (
        "candidate_theme_refs",
        "matched_vocabulary_refs",
        "matched_chunk_refs",
        "matched_pattern_refs",
        "matched_grammar_unit_refs",
        "sentence_seed_maturity",
        "passage_seed_status",
        "discourse_shape",
        "scene_structure",
        "four_skill_affordances",
    ):
        first[key] = deepcopy(second[key])
    package["package_sha256"] = deep.sha256_value(
        {key: value for key, value in package.items() if key != "package_sha256"}
    )
    output = _build(package)
    row = next(
        item
        for item in output["semantic_representatives"]
        if item["semantic_duplicate_group_id"] == "G1"
    )
    assert row["selected_source_unit_ref"] == "A_001"
    assert "SOURCE_UNIT_REF_STABLE_TIEBREAKER" in row["selection_reason_codes"]


def test_tampered_admission_package_fails_closed() -> None:
    package = _package()
    package["aggregate_summary"]["duplicate_candidate_count"] = 99
    with pytest.raises(
        dedup.SemanticDedupError,
        match="admission_package_sha256_mismatch",
    ):
        _build(package)


def test_safe_output_contains_no_source_text_or_title() -> None:
    package = _build()
    assert matching.scan_forbidden_safe_keys(package) == []
    serialized = deep.canonical_json(package)
    assert '"text"' not in serialized
    assert '"title"' not in serialized
    assert package["claim_boundaries"]["raz_level_used_as_cefr_equivalence"] is False
    assert package["dedup_gate"]["ready_for_material_promotion"] is False
