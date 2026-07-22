from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2
from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_ai_acl_v1_s02_semantic_dedup as dedup
from ulga.builders import build_raz_ai_acl_v1_s05_material_registry as registry
from ulga.builders import build_raz_ai_acl_v1_s06_final_closeout as closeout


def _base(group: str, ref: str) -> dict:
    return {
        "semantic_duplicate_group_id": group,
        "selected_source_unit_ref": ref,
        "source_level": "A",
        "source_book_id": "BOOK_A",
        "authority_links": [
            {
                "authority_type": "THEME",
                "authority_ref": "theme:a1_personal_information_and_greetings",
                "link_status": "VERIFIED_EXISTING_AUTHORITY_MATCH",
            },
            {
                "authority_type": "VOCABULARY",
                "authority_ref": "vocabulary:book",
                "link_status": "VERIFIED_EXISTING_AUTHORITY_MATCH",
            },
            {
                "authority_type": "GRAMMAR",
                "authority_ref": "GRAMMAR_BE_BASIC",
                "link_status": "VERIFIED_EXISTING_AUTHORITY_MATCH",
            },
        ],
    }


def _registry_package() -> dict:
    promoted = [
        {
            "material_id": "RAZ_A1A1PLUS_MATERIAL_001",
            **_base("G1", "A_001"),
            "candidate_cefr_scope": "A1",
            "registry_status": "PROMOTED_TO_A1_A1PLUS_MATERIAL_REGISTRY",
            "source_payload_access": "PRIVATE_SOURCE_REF_REQUIRED",
        },
        {
            "material_id": "RAZ_A1A1PLUS_MATERIAL_002",
            **_base("G2", "B_001"),
            "candidate_cefr_scope": "A1_PLUS",
            "registry_status": "PROMOTED_TO_A1_A1PLUS_MATERIAL_REGISTRY",
            "source_payload_access": "PRIVATE_SOURCE_REF_REQUIRED",
        },
    ]
    remediation = [
        {
            **_base("G3", "C_001"),
            "remediation_status": "PENDING_CONTENT_REWRITE_EVIDENCE",
            "promotion_status": "NOT_PROMOTED",
        }
    ]
    support = [
        {**_base("G4", "D_001"), "support_status": "ADMITTED_SUPPORT_ONLY"}
    ]
    rejected = [{**_base("G5", "E_001"), "rejection_status": "CLOSED_UNUSABLE"}]
    package = {
        "task_id": registry.TASK_ID,
        "schema_version": registry.SCHEMA_VERSION,
        "validation_status": registry.PASS_STATUS,
        "input_identity": {},
        "scope_contract": {
            "a1_a1plus_observational_levels": list("AI"),
            "deferred_levels": list("JW"),
            "a_i_is_not_cefr_equivalence": True,
            "a2_a2plus_processing_status": "DEFERRED_NOT_OPENED",
        },
        "promoted_material_registry": promoted,
        "remediation_queue": remediation,
        "support_registry": support,
        "rejected_registry": rejected,
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
            "duplicate_binding_count": 1,
            "deferred_a2_a2plus_count": 1,
            "final_promoted_material_count": 2,
            "remediation_queue_count": 1,
            "support_registry_count": 1,
            "rejected_registry_count": 1,
        },
        "material_registry_gate": {
            "decision": "A1_A1PLUS_MATERIAL_REGISTRY_READY",
            "ready_for_final_coverage_reconciliation": True,
        },
        "claim_boundaries": {},
        "errors": [],
    }
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _representative(
    group: str,
    ref: str,
    status: str,
    scope: str,
    *,
    maturity: str = "SUPPORT_SENTENCE_SEED",
    passage: bool = False,
    skills: list[str] | None = None,
) -> dict:
    return {
        "semantic_duplicate_group_id": group,
        "selected_source_unit_ref": ref,
        "source_level": "A",
        "source_book_id": "BOOK_A",
        "representative_admission_status": status,
        "candidate_cefr_scope": scope,
        "candidate_theme_refs": ["theme:a1_personal_information_and_greetings"],
        "matched_vocabulary_refs": ["vocabulary:book"] if status.endswith("READY_CANDIDATE") else [],
        "matched_chunk_refs": [],
        "matched_pattern_refs": [],
        "matched_grammar_unit_refs": ["GRAMMAR_BE_BASIC"] if status.endswith("READY_CANDIDATE") else [],
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
        ),
        _representative(
            "G2",
            "B_001",
            "A1PLUS_READY_CANDIDATE",
            "A1_PLUS",
            maturity="BROAD_CORE_SENTENCE_SEED",
            skills=["READING_SOURCE", "SPEAKING_PROMPT"],
        ),
        _representative("G3", "C_001", "REWRITE_REQUIRED", "NONE"),
        _representative("G4", "D_001", "SUPPORT_ONLY", "NONE"),
        _representative("G5", "E_001", "REJECTED_UNUSABLE", "NONE"),
    ]
    package = {
        "task_id": dedup.TASK_ID,
        "schema_version": dedup.SCHEMA_VERSION,
        "validation_status": dedup.PASS_STATUS,
        "input_identity": {},
        "scope_contract": {},
        "semantic_representatives": rows,
        "duplicate_bindings": [],
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
        },
        "claim_boundaries": {},
        "errors": [],
    }
    package["package_sha256"] = deep.sha256_value(package)
    return package


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
                "payload": {"prompt": "locked fixture"},
                "content_digest": "d" * 64,
                "release_scope": "PRIVATE_INTERNAL_D0",
            },
        ],
        "lesson_catalog": [
            {
                "lesson_id": "LESSON-R-A1",
                "requirement_node_ids": ["REF:READING:A1-001"],
            },
            {
                "lesson_id": "LESSON-W-A1P",
                "requirement_node_ids": ["REF:WRITING:A1P-001"],
            },
            {
                "lesson_id": "LESSON-L-A2",
                "requirement_node_ids": ["REF:LISTENING:A2-001"],
            },
        ],
        "counts": {},
        "access_contract": {
            "learning_query_levels": ["A1", "A1+"],
            "a2_payload_query_allowed": False,
        },
        "claim_boundaries": {},
        "errors": [],
        "next_short_step": "FIXTURE",
    }


def _build(
    registry_package: dict | None = None,
    dedup_package: dict | None = None,
    mainline: dict | None = None,
) -> dict:
    mainline = mainline or _mainline()
    return closeout.build_package(
        registry_package or _registry_package(),
        dedup_package or _dedup_package(),
        mainline,
        mainline_index_sha256=deep.sha256_value(mainline),
        expected_total_page_unit_count=7,
        expected_scope_page_unit_count=6,
        expected_semantic_identity_count=5,
        expected_duplicate_binding_count=1,
        expected_deferred_page_unit_count=1,
    )


def test_reconciles_coverage_proves_consumption_and_closes_at_d0() -> None:
    output = _build()
    gate = output["final_closeout_gate"]
    assert output["validation_status"] == closeout.PASS_STATUS
    assert gate["decision"] == "RAZ_AI_ACL_V1_D0_CLOSED"
    assert gate["program_status"] == "PASS_ACCEPTED_AND_CLOSED"
    assert gate["distance_after"] == "D0"
    assert gate["remaining_in_scope_blocker_count"] == 0
    assert gate["mainline_consumer_proof"] is True
    assert gate["a2_lock_status"] == "PASS_LOCKED"
    coverage = output["coverage_reconciliation"]
    assert coverage["promoted_material_count"] == 2
    assert coverage["mainline_material_count"] == 2
    assert coverage["mainline_a2_asset_count_skipped"] == 1
    assert coverage["integrated_material_count"] == 4
    assert coverage["linked_sentence_candidate_count"] == 2
    assert coverage["linked_core_sentence_candidate_count"] == 2
    assert coverage["linked_passage_candidate_count"] == 1
    assert coverage["four_skill_candidate_counts"] == {
        "LISTENING": 1,
        "READING": 2,
        "SPEAKING": 2,
        "WRITING": 1,
    }


def test_integrated_query_reads_both_source_partitions() -> None:
    output = _build()
    raz = closeout.query_index(
        output,
        source_type="RAZ_DERIVED_MATERIAL",
        authority_ref="vocabulary:book",
        material_role="PASSAGE_CANDIDATE",
    )
    assert raz["total_match_count"] == 1
    assert raz["integrated_materials"][0]["source_unit_ref"] == "A_001"
    mainline = closeout.query_index(
        output,
        source_type="MAINLINE_ASSET_BODY",
        skill="READING",
        level="A1",
    )
    assert mainline["total_match_count"] == 1
    assert mainline["integrated_materials"][0]["material_ref"] == "READING:R-A1"
    assert raz["learner_facing_payload_included"] is False
    assert mainline["a2_payload_included"] is False


def test_a2_query_fails_closed() -> None:
    with pytest.raises(closeout.FinalCloseoutError, match="A2_QUERY_LOCKED"):
        closeout.query_index(_build(), level="A2")


def test_missing_promoted_grammar_link_fails_closed() -> None:
    package = _registry_package()
    package["promoted_material_registry"][0]["authority_links"] = package[
        "promoted_material_registry"
    ][0]["authority_links"][:2]
    package["package_sha256"] = deep.sha256_value(
        {key: value for key, value in package.items() if key != "package_sha256"}
    )
    with pytest.raises(
        closeout.FinalCloseoutError,
        match="promoted_required_authority_missing",
    ):
        _build(registry_package=package)


def test_tampered_registry_package_fails_closed() -> None:
    package = _registry_package()
    package["aggregate_summary"]["semantic_identity_count"] = 99
    with pytest.raises(
        closeout.FinalCloseoutError,
        match="registry_package_sha256_mismatch",
    ):
        _build(registry_package=package)


def test_safe_closeout_contains_no_private_payload_or_learning_claim() -> None:
    output = _build()
    assert matching.scan_forbidden_safe_keys(output) == []
    serialized = deep.canonical_json(output)
    assert '"payload"' not in serialized
    assert '"text"' not in serialized
    assert '"title"' not in serialized
    assert "private fixture" not in serialized
    assert output["claim_boundaries"]["mainline_payload_traversal_performed"] is False
    assert output["claim_boundaries"]["mastery_claimed"] is False
    assert output["claim_boundaries"]["retention_claimed"] is False
    assert output["claim_boundaries"]["program_closeout_is_registry_capability_closeout"] is False
