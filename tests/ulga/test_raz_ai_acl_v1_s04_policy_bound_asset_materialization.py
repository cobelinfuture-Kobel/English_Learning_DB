from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as content_policy
from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_ai_acl_v1_s02_semantic_dedup as dedup
from ulga.builders import build_raz_ai_acl_v1_s03_authority_linkage as linkage
from ulga.builders import build_raz_ai_acl_v1_s04_policy_bound_asset_materialization as materialize
from ulga.validators import validate_raz_ai_acl_v1_s04_policy_bound_asset_materialization as validator


def _representative(
    group: str,
    ref: str,
    status: str,
    scope: str,
    *,
    maturity: str = "SUPPORT_SENTENCE_SEED",
    passage: bool = False,
    skills: list[str] | None = None,
    theme: list[str] | None = None,
    vocabulary: list[str] | None = None,
    chunks: list[str] | None = None,
    patterns: list[str] | None = None,
    grammar: list[str] | None = None,
) -> dict:
    return {
        "semantic_duplicate_group_id": group,
        "selected_source_unit_ref": ref,
        "source_level": "A",
        "source_book_id": "BOOK_A",
        "member_count": 1,
        "duplicate_member_count": 0,
        "s01_provisional_representative_source_unit_ref": ref,
        "representative_changed_from_s01": False,
        "representative_admission_status": status,
        "candidate_cefr_scope": scope,
        "representative_reason_codes": ["FIXTURE"],
        "selection_reason_codes": ["HIGHEST_DEDUP_QUALITY_VECTOR"],
        "quality_vector": {},
        "member_hypothetical_statuses": [status],
        "member_candidate_cefr_scopes": [scope],
        "classification_conflict_observed": False,
        "candidate_theme_refs": theme or ["theme:a1_personal_information_and_greetings"],
        "matched_vocabulary_refs": vocabulary or [],
        "matched_chunk_refs": chunks or [],
        "matched_pattern_refs": patterns or [],
        "matched_grammar_unit_refs": grammar or [],
        "sentence_seed_maturity": maturity,
        "passage_seed_status": "SUPPORTED" if passage else "NOT_A_PASSAGE",
        "discourse_shape": "simple_narrative_or_description",
        "scene_structure": "GENERAL_CONTEXT_SCENE",
        "four_skill_affordances": skills or ["READING_SOURCE"],
        "promotion_status": "NOT_PROMOTED",
    }


def _dedup_package() -> dict:
    rows = [
        _representative(
            "G1",
            "A_001",
            "A1_READY_CANDIDATE",
            "A1",
            maturity="STRICT_CORE_SENTENCE_SEED",
            passage=True,
            skills=[
                "READING_SOURCE",
                "LISTENING_ADAPTATION",
                "SPEAKING_PROMPT",
                "WRITING_MODEL",
            ],
            vocabulary=["vocabulary:cat"],
            chunks=["chunk:on_the"],
            patterns=["pattern:there_is"],
            grammar=["GRAMMAR_BE_BASIC"],
        ),
        _representative(
            "G2",
            "B_001",
            "A1PLUS_READY_CANDIDATE",
            "A1_PLUS",
            maturity="BROAD_CORE_SENTENCE_SEED",
            skills=["READING_SOURCE", "SPEAKING_PROMPT"],
            vocabulary=["vocabulary:family"],
            grammar=["GRAMMAR_PAST_SIMPLE_A1"],
        ),
        _representative(
            "G3",
            "C_001",
            "REWRITE_REQUIRED",
            "NONE",
            vocabulary=["vocabulary:book"],
        ),
        _representative(
            "G4",
            "D_001",
            "SUPPORT_ONLY",
            "NONE",
            chunks=["chunk:look_at"],
            skills=["READING_SOURCE", "SPEAKING_PROMPT"],
        ),
        _representative("G5", "E_001", "REJECTED_UNUSABLE", "NONE"),
    ]
    package = {
        "task_id": dedup.TASK_ID,
        "schema_version": dedup.SCHEMA_VERSION,
        "validation_status": dedup.PASS_STATUS,
        "input_identity": {},
        "scope_contract": {
            "a1_a1plus_observational_levels": list("AI"),
            "deferred_levels": list("JW"),
            "a_i_is_not_cefr_equivalence": True,
            "a2_a2plus_processing_status": "DEFERRED_NOT_OPENED",
        },
        "semantic_representatives": rows,
        "duplicate_bindings": [
            {
                "semantic_duplicate_group_id": "G1",
                "duplicate_source_unit_ref": "A_002",
                "representative_source_unit_ref": "A_001",
                "binding_status": "BOUND_TO_SEMANTIC_REPRESENTATIVE",
            }
        ],
        "aggregate_summary": {
            "source_candidate_count": 7,
            "a1_a1plus_scope_candidate_count": 6,
            "semantic_identity_count": 5,
            "representative_count": 5,
            "duplicate_binding_count": 1,
            "deferred_a2_a2plus_count": 1,
            "final_promoted_material_count": 0,
        },
        "dedup_gate": {
            "decision": "SEMANTIC_DEDUP_REPRESENTATIVES_READY",
            "ready_for_authority_linkage": True,
            "ready_for_material_promotion": False,
        },
        "claim_boundaries": {},
        "errors": [],
    }
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _linkage_package(dedup_package: dict) -> dict:
    return linkage.build_package(
        dedup_package,
        expected_total_page_unit_count=7,
        expected_scope_page_unit_count=6,
        expected_semantic_identity_count=5,
        expected_duplicate_binding_count=1,
        expected_deferred_page_unit_count=1,
    )


def _build() -> dict:
    dedup_package = _dedup_package()
    return materialize.build_candidate(
        dedup_package,
        _linkage_package(dedup_package),
        expected_total_page_unit_count=7,
        expected_scope_page_unit_count=6,
        expected_semantic_identity_count=5,
        expected_duplicate_binding_count=1,
        expected_deferred_page_unit_count=1,
    )


def test_materializes_ready_rows_as_policy_bound_text_free_candidates() -> None:
    candidate = _build()
    assert candidate["artifact_role"] == content_policy.CANDIDATE_ROLE
    assert candidate["learner_facing"] is False
    assert candidate["admission"] == {
        "status": "PENDING_VALIDATION",
        "decision_ref": None,
    }
    payload = candidate["payload"]
    assert payload["validation_status"] == materialize.PASS_STATUS
    assert payload["materialization_gate"]["decision"] == (
        "POLICY_BOUND_ASSET_CANDIDATES_READY"
    )
    assert payload["materialization_gate"]["distance_after"] == "D2"
    assert payload["aggregate_summary"]["materialized_candidate_count"] == 2
    assert payload["aggregate_summary"]["non_materialized_count"] == 3
    assert payload["aggregate_summary"]["level_candidate_counts"] == {
        "A1": 1,
        "A1+": 1,
    }
    rows = {
        row["semantic_identity_id"]: row for row in payload["material_candidates"]
    }
    assert "STRICT_CORE_SENTENCE_CANDIDATE" in rows["G1"]["material_roles"]
    assert "PASSAGE_CANDIDATE" in rows["G1"]["material_roles"]
    assert "LISTENING_ADAPTATION_CANDIDATE" in rows["G1"]["material_roles"]
    assert "BROAD_CORE_SENTENCE_CANDIDATE" in rows["G2"]["material_roles"]
    assert all(row["learner_facing"] is False for row in rows.values())


def test_independent_validator_passes_and_reconciles_roles() -> None:
    report = validator.validate_candidate(_build())
    assert report["validation_status"] == validator.PASS_STATUS, report["errors"]
    assert report["error_count"] == 0
    assert report["materialized_candidate_count"] == 2
    assert report["non_materialized_count"] == 3
    assert report["a2_unlocked"] is False
    assert report["canonical_promotion_performed"] is False


def test_missing_required_grammar_link_fails_closed() -> None:
    dedup_package = _dedup_package()
    linkage_package = _linkage_package(dedup_package)
    linkage_package["authority_linkage_rows"][0]["authority_links"] = [
        link
        for link in linkage_package["authority_linkage_rows"][0]["authority_links"]
        if link["authority_type"] != "GRAMMAR"
    ]
    linkage_package["authority_linkage_rows"][0]["authority_link_count"] -= 1
    linkage_package["package_sha256"] = deep.sha256_value(
        {
            key: value
            for key, value in linkage_package.items()
            if key != "package_sha256"
        }
    )
    with pytest.raises(
        materialize.AssetMaterializationError,
        match="ready_candidate_required_authority_missing",
    ):
        materialize.build_candidate(
            dedup_package,
            linkage_package,
            expected_total_page_unit_count=7,
            expected_scope_page_unit_count=6,
            expected_semantic_identity_count=5,
            expected_duplicate_binding_count=1,
            expected_deferred_page_unit_count=1,
        )


def test_a2_injection_fails_independent_validation_even_with_rebuilt_hash() -> None:
    candidate = deepcopy(_build())
    candidate["payload"]["material_candidates"][0]["level"] = "A2"
    candidate["artifact_sha256"] = content_policy.digest(
        {
            key: value
            for key, value in candidate.items()
            if key != "artifact_sha256"
        }
    )
    report = validator.validate_candidate(candidate)
    assert report["validation_status"] == "FAIL"
    assert any(error.startswith("candidate_level_invalid") for error in report["errors"])


def test_output_contains_no_source_text_or_title() -> None:
    candidate = _build()
    serialized = content_policy.canonical(candidate)
    assert '"text"' not in serialized
    assert '"title"' not in serialized
    assert "The cat is on the mat" not in serialized
    assert candidate["payload"]["claim_boundaries"][
        "controlled_rewrite_required_before_learner_facing_use"
    ] is True
