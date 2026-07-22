from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2
from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_ai_acl_v1_s02_semantic_dedup as dedup
from ulga.builders import build_raz_ai_acl_v1_s03_authority_linkage as linkage
from ulga.builders import build_raz_ai_acl_v1_s04_admission_resolution as resolution
from ulga.builders import build_raz_ai_acl_v1_s05_material_registry as registry
from ulga.builders import build_raz_ai_acl_v1_s06_integrated_consumer_d0 as closeout
from ulga.validators import validate_raz_ai_acl_v1_s06_integrated_consumer_d0 as validator


def _representative(
    group: str,
    ref: str,
    status: str,
    scope: str,
    *,
    maturity: str = "SUPPORT_SENTENCE_SEED",
    passage: bool = False,
    skills: list[str] | None = None,
    vocabulary: list[str] | None = None,
    chunks: list[str] | None = None,
    patterns: list[str] | None = None,
    grammar: list[str] | None = None,
) -> dict:
    ready = status in {"A1_READY_CANDIDATE", "A1PLUS_READY_CANDIDATE"}
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
        "candidate_theme_refs": ["theme:a1_personal_information_and_greetings"],
        "matched_vocabulary_refs": vocabulary or (["vocabulary:book"] if ready else []),
        "matched_chunk_refs": chunks or [],
        "matched_pattern_refs": patterns or [],
        "matched_grammar_unit_refs": grammar or (["GRAMMAR_BE_BASIC"] if ready else []),
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


def _chain() -> tuple[dict, dict, dict, dict]:
    d = _dedup_package()
    l = linkage.build_package(
        d,
        expected_total_page_unit_count=7,
        expected_scope_page_unit_count=6,
        expected_semantic_identity_count=5,
        expected_duplicate_binding_count=1,
        expected_deferred_page_unit_count=1,
    )
    r = resolution.build_package(
        l,
        expected_total_page_unit_count=7,
        expected_scope_page_unit_count=6,
        expected_semantic_identity_count=5,
        expected_duplicate_binding_count=1,
        expected_deferred_page_unit_count=1,
    )
    m = registry.build_package(
        r,
        expected_total_page_unit_count=7,
        expected_scope_page_unit_count=6,
        expected_semantic_identity_count=5,
        expected_duplicate_binding_count=1,
        expected_deferred_page_unit_count=1,
    )
    return d, l, r, m


def _mainline() -> dict:
    return {
        "task_id": m2.TASK_ID,
        "schema_version": m2.SCHEMA_VERSION,
        "validation_status": m2.STATUS,
        "source_graph_sha256": "a" * 64,
        "asset_records": [
            {
                "asset_key": "READING:R-A1",
                "asset_id": "R-A1",
                "lesson_id": "LESSON-R-A1",
                "skill": "READING",
                "level": "A1",
                "role": "EVD",
                "payload": {"prompt": "private fixture"},
                "content_digest": "b" * 64,
                "release_scope": "PRIVATE_INTERNAL_D0",
            },
            {
                "asset_key": "WRITING:W-A1P",
                "asset_id": "W-A1P",
                "lesson_id": "LESSON-W-A1P",
                "skill": "WRITING",
                "level": "A1+",
                "role": "MODEL",
                "payload": {"body_text": "private fixture"},
                "content_digest": "c" * 64,
                "release_scope": "PRIVATE_INTERNAL_D0",
            },
            {
                "asset_key": "LISTENING:L-A2",
                "asset_id": "L-A2",
                "lesson_id": "LESSON-L-A2",
                "skill": "LISTENING",
                "level": "A2",
                "role": "EVD",
                "payload": {"prompt": "locked private fixture"},
                "content_digest": "d" * 64,
                "release_scope": "PRIVATE_INTERNAL_D0",
            },
        ],
        "lesson_catalog": [
            {
                "lesson_id": "LESSON-R-A1",
                "lesson_node_id": "LESSON:READING:LESSON-R-A1",
                "skill": "READING",
                "level": "A1",
                "asset_keys": ["READING:R-A1"],
                "roles": ["EVD"],
                "requirement_node_ids": ["REF:READING:A1-001"],
                "release_scope": "PRIVATE_INTERNAL_D0",
            },
            {
                "lesson_id": "LESSON-W-A1P",
                "lesson_node_id": "LESSON:WRITING:LESSON-W-A1P",
                "skill": "WRITING",
                "level": "A1+",
                "asset_keys": ["WRITING:W-A1P"],
                "roles": ["MODEL"],
                "requirement_node_ids": ["REF:WRITING:A1P-001"],
                "release_scope": "PRIVATE_INTERNAL_D0",
            },
            {
                "lesson_id": "LESSON-L-A2",
                "lesson_node_id": "LESSON:LISTENING:LESSON-L-A2",
                "skill": "LISTENING",
                "level": "A2",
                "asset_keys": ["LISTENING:L-A2"],
                "roles": ["EVD"],
                "requirement_node_ids": ["REF:LISTENING:A2-001"],
                "release_scope": "PRIVATE_INTERNAL_D0",
            },
        ],
        "counts": {
            "asset_record_count": 3,
            "lesson_count": 3,
            "learning_lesson_count": 2,
            "a2_handoff_lesson_count": 1,
        },
        "access_contract": {
            "visibility": "PRIVATE_INTERNAL",
            "learning_query_levels": ["A1", "A1+"],
            "a2_payload_query_allowed": False,
            "a2_handoff_metadata_allowed": True,
            "max_query_limit": 100,
            "filter_fields": ["skill", "level", "lesson_id", "role", "requirement_node_id"],
        },
        "claim_boundaries": {},
        "errors": [],
        "next_short_step": "FIXTURE",
    }


def _build() -> dict:
    d, l, r, m = _chain()
    mainline = _mainline()
    return closeout.build_index(
        d,
        l,
        r,
        m,
        mainline,
        mainline_index_sha256=deep.sha256_value(mainline),
        expected_total_page_unit_count=7,
        expected_scope_page_unit_count=6,
        expected_semantic_identity_count=5,
        expected_duplicate_binding_count=1,
        expected_deferred_page_unit_count=1,
    )


def test_builds_integrated_metadata_consumer_and_reaches_d0() -> None:
    index = _build()
    assert index["validation_status"] == closeout.PASS_STATUS
    gate = index["acceptance_gate"]
    assert gate["decision"] == "RAZ_AI_ACL_V1_D0_ACCEPTED"
    assert gate["distance_after"] == "D0"
    assert gate["program_status"] == "PASS_ACCEPTED_AND_CLOSED"
    assert gate["mainline_consumer_proof"] is True
    assert gate["a2_lock_status"] == "PASS_LOCKED"
    summary = index["aggregate_summary"]
    assert summary["mainline_material_count"] == 2
    assert summary["raz_promoted_material_count"] == 2
    assert summary["integrated_material_count"] == 4
    assert summary["mainline_a2_asset_count_skipped"] == 1
    assert summary["linked_sentence_candidate_count"] == 2
    assert summary["linked_core_sentence_candidate_count"] == 2
    assert summary["linked_passage_candidate_count"] == 1
    assert summary["four_skill_candidate_counts"] == {
        "LISTENING": 1,
        "READING": 2,
        "SPEAKING": 2,
        "WRITING": 1,
    }


def test_query_combines_mainline_and_raz_metadata_without_payloads() -> None:
    index = _build()
    raz = closeout.query_index(
        index,
        source_type="RAZ_DERIVED_MATERIAL",
        authority_ref="vocabulary:cat",
        material_role="PASSAGE_CANDIDATE",
    )
    assert raz["total_match_count"] == 1
    assert raz["integrated_materials"][0]["source_unit_ref"] == "A_001"
    mainline = closeout.query_index(
        index,
        source_type="MAINLINE_ASSET_BODY",
        skill="READING",
        level="A1",
    )
    assert mainline["total_match_count"] == 1
    assert mainline["integrated_materials"][0]["material_ref"] == "READING:R-A1"
    assert raz["learner_facing_payload_included"] is False
    assert mainline["a2_payload_included"] is False


def test_a2_query_fails_closed() -> None:
    with pytest.raises(closeout.IntegratedConsumerError, match="A2_QUERY_LOCKED"):
        closeout.query_index(_build(), level="A2")


def test_independent_validator_rechecks_d0_contract() -> None:
    report = validator.validate_index(_build())
    assert report["validation_status"] == validator.PASS_STATUS, report["errors"]
    assert report["error_count"] == 0
    assert report["distance_after"] == "D0"
    assert report["program_status"] == "PASS_ACCEPTED_AND_CLOSED"
    assert report["a2_unlocked"] is False


def test_tampered_registry_lineage_fails_closed() -> None:
    d, l, r, m = _chain()
    m = deepcopy(m)
    m["aggregate_summary"]["final_promoted_material_count"] = 99
    mainline = _mainline()
    with pytest.raises(
        closeout.IntegratedConsumerError,
        match="registry_package_sha256_mismatch",
    ):
        closeout.build_index(
            d,
            l,
            r,
            m,
            mainline,
            mainline_index_sha256=deep.sha256_value(mainline),
            expected_total_page_unit_count=7,
            expected_scope_page_unit_count=6,
            expected_semantic_identity_count=5,
            expected_duplicate_binding_count=1,
            expected_deferred_page_unit_count=1,
        )


def test_safe_output_contains_no_private_text_or_payload() -> None:
    index = _build()
    serialized = deep.canonical_json(index)
    assert '"payload"' not in serialized
    assert '"text"' not in serialized
    assert '"title"' not in serialized
    assert "private fixture" not in serialized
    assert index["claim_boundaries"]["mainline_payload_traversal_performed"] is False
    assert index["claim_boundaries"]["source_text_read_performed"] is False
