from __future__ import annotations

import copy

import pytest

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_ai_acl_v1_s05_material_registry as registry
from ulga.builders import build_raz_ai_acl_v1_s06_final_closeout as closeout


def _refs() -> dict[str, list[str]]:
    return {
        "THEME": ["theme:a1_school_and_classroom"],
        "VOCABULARY": ["vocabulary:book"],
        "CHUNK": ["chunk:on_the"],
        "PATTERN": ["pattern:svo"],
        "GRAMMAR": ["GRAMMAR_BE_VERB_BASIC"],
    }


def _base(group: str, ref: str) -> dict:
    return {
        "semantic_duplicate_group_id": group,
        "selected_source_unit_ref": ref,
        "source_level": "A",
        "source_book_id": "BOOK_A",
        "authority_refs_by_type": _refs(),
        "canonical_egp_row_refs": ["EGP_A1_BE_001"],
        "asset_role_bindings": [],
        "private_source_content_sha256": "a" * 64,
    }


def _promoted(material_id: str, group: str, ref: str, scope: str, skills: list[str]) -> dict:
    return {
        "material_id": material_id,
        **_base(group, ref),
        "candidate_cefr_scope": scope,
        "mainline_level": "A1" if scope == "A1" else "A1+",
        "extension_asset_keys": [
            f"RAZ_DERIVED:{skill}:{material_id}" for skill in skills
        ],
        "material_asset_roles": [
            "SENTENCE_ASSET_CANDIDATE",
            "CORE_SENTENCE_ASSET_CANDIDATE",
            "PASSAGE_ASSET_CANDIDATE",
        ],
        "skill_asset_roles": [],
        "registry_status": "INTEGRATED_WITH_MAINLINE_M2_CONSUMER",
        "source_payload_access": "PRIVATE_SOURCE_RESOLVER_REQUIRED",
    }


def _extension(material_id: str, group: str, ref: str, skill: str, level: str) -> dict:
    return {
        "origin": "RAZ_DERIVED_EXTENSION",
        "asset_key": f"RAZ_DERIVED:{skill}:{material_id}",
        "asset_id": material_id,
        "material_id": material_id,
        "semantic_duplicate_group_id": group,
        "selected_source_unit_ref": ref,
        "skill": skill,
        "level": level,
        "role": f"{skill}_ROLE",
        "material_asset_roles": [
            "SENTENCE_ASSET_CANDIDATE",
            "CORE_SENTENCE_ASSET_CANDIDATE",
            "PASSAGE_ASSET_CANDIDATE",
        ],
        "authority_refs_by_type": _refs(),
        "all_canonical_authority_refs": sorted(
            {value for values in _refs().values() for value in values}
        ),
        "canonical_egp_row_refs": ["EGP_A1_BE_001"],
        "mainline_lesson_ids": [f"LESSON_{level}_{skill}"],
        "matched_mainline_requirement_node_ids": ["EGP_A1_BE_001"],
        "private_source_content_sha256": "a" * 64,
        "private_source_resolution": "RAZ_PAGE_UNIT_BY_SOURCE_REF",
        "release_scope": "PRIVATE_INTERNAL_DERIVED_EXTENSION",
    }


def _package() -> dict:
    promoted = [
        _promoted(
            "RAZ_A1A1PLUS_MATERIAL_001",
            "G1",
            "A_001",
            "A1",
            ["READING", "LISTENING"],
        ),
        _promoted(
            "RAZ_A1A1PLUS_MATERIAL_002",
            "G2",
            "B_001",
            "A1_PLUS",
            ["SPEAKING", "WRITING"],
        ),
    ]
    extension = [
        _extension("RAZ_A1A1PLUS_MATERIAL_001", "G1", "A_001", "READING", "A1"),
        _extension("RAZ_A1A1PLUS_MATERIAL_001", "G1", "A_001", "LISTENING", "A1"),
        _extension("RAZ_A1A1PLUS_MATERIAL_002", "G2", "B_001", "SPEAKING", "A1+"),
        _extension("RAZ_A1A1PLUS_MATERIAL_002", "G2", "B_001", "WRITING", "A1+"),
    ]
    remediation = [
        {
            **_base("G3", "C_001"),
            "remediation_status": "PENDING_CONTROLLED_REWRITE_EVIDENCE",
            "promotion_status": "NOT_PROMOTED",
        }
    ]
    support = [{**_base("G4", "D_001"), "support_status": "ADMITTED_SUPPORT_ONLY"}]
    rejected = [{**_base("G5", "E_001"), "rejection_status": "CLOSED_UNUSABLE"}]
    package = {
        "task_id": registry.TASK_ID,
        "schema_version": registry.SCHEMA_VERSION,
        "validation_status": registry.PASS_STATUS,
        "input_identity": {
            "mainline_m2_index_sha256": "m" * 64,
        },
        "scope_contract": {
            "a1_a1plus_observational_levels": list("AI"),
            "deferred_levels": list("JW"),
            "a_i_is_not_cefr_equivalence": True,
            "a2_a2plus_processing_status": "DEFERRED_NOT_OPENED",
        },
        "private_source_index": [],
        "mainline_m2_summary": {
            "asset_record_count": 10,
            "lesson_count": 8,
            "a2_payload_query_allowed": False,
        },
        "promoted_material_registry": promoted,
        "mainline_extension_records": extension,
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
        "consumer_query_proof": {
            "combined_origin_query": {
                "skill": "READING",
                "level": "A1",
                "mainline_match_count": 2,
                "raz_extension_match_count": 1,
            },
            "authority_query": {
                "authority_ref": "vocabulary:book",
                "raz_extension_match_count": 4,
            },
            "asset_role_query": {
                "asset_role": "CORE_SENTENCE_ASSET_CANDIDATE",
                "raz_extension_match_count": 4,
            },
            "a2_lock_verified": True,
        },
        "aggregate_summary": {
            "source_candidate_count": 7,
            "a1_a1plus_scope_candidate_count": 6,
            "semantic_identity_count": 5,
            "duplicate_binding_count": 1,
            "deferred_a2_a2plus_count": 1,
            "lane_counts": {
                "PROMOTION_ELIGIBLE": 2,
                "REMEDIATION_REQUIRED": 1,
                "SUPPORT_ADMITTED": 1,
                "REJECTED_CLOSED": 1,
            },
            "promoted_cefr_scope_counts": {"A1": 1, "A1_PLUS": 1},
            "mainline_extension_skill_counts": {
                "LISTENING": 1,
                "READING": 1,
                "SPEAKING": 1,
                "WRITING": 1,
            },
            "asset_role_binding_counts": {},
            "final_promoted_material_count": 2,
            "mainline_extension_asset_count": 4,
            "mainline_lesson_linked_extension_asset_count": 4,
            "remediation_queue_count": 1,
            "support_registry_count": 1,
            "rejected_registry_count": 1,
        },
        "mainline_consumer_gate": {
            "decision": "MAINLINE_M2_CONSUMER_EXTENSION_READY",
            "ready_for_end_to_end_d0_recloseout": True,
            "ready_for_learner_facing_release": False,
        },
        "claim_boundaries": {},
        "errors": [],
    }
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _build(package: dict | None = None) -> dict:
    return closeout.build_package(
        package or _package(),
        expected_total_page_unit_count=7,
        expected_scope_page_unit_count=6,
        expected_semantic_identity_count=5,
        expected_duplicate_binding_count=1,
        expected_deferred_page_unit_count=1,
    )


def test_reconciles_real_mainline_consumer_proof_and_recloses_d0() -> None:
    output = _build()
    gate = output["final_closeout_gate"]
    assert output["validation_status"] == closeout.PASS_STATUS
    assert gate["decision"] == (
        "RAZ_AI_ACL_V1_D0_RECLOSED_AFTER_MAINLINE_CONSUMER_FULLFIX"
    )
    assert gate["program_status"] == "PASS_ACCEPTED_AND_CLOSED"
    assert gate["distance_after"] == "D0"
    assert gate["remaining_in_scope_blocker_count"] == 0
    assert gate["a2_a2plus_status"] == "DEFERRED_A2_A2PLUS"
    coverage = output["coverage_reconciliation"]
    assert coverage["promoted_material_count"] == 2
    assert coverage["mainline_extension_asset_count"] == 4
    assert coverage["linked_theme_count"] == 1
    assert coverage["linked_vocabulary_count"] == 1
    assert coverage["linked_grammar_unit_count"] == 1
    assert coverage["linked_sentence_material_count"] == 2
    assert coverage["linked_core_sentence_material_count"] == 2
    assert coverage["linked_passage_material_count"] == 2
    assert coverage["linked_four_skill_asset_count"] == 4
    assert coverage["linked_mainline_lesson_count"] == 4
    assert output["claim_boundaries"][
        "program_closeout_is_registry_capability_closeout"
    ] is False


def test_registry_only_package_without_consumer_proof_is_rejected() -> None:
    package = copy.deepcopy(_package())
    package["consumer_query_proof"]["combined_origin_query"] = None
    package["package_sha256"] = deep.sha256_value(
        {key: value for key, value in package.items() if key != "package_sha256"}
    )
    output = _build(package)
    assert output["validation_status"] == "FAIL"
    assert output["final_closeout_gate"]["distance_after"] == "D1"
    assert output["final_closeout_gate"]["source_checks"][
        "combined_mainline_and_raz_query_proven"
    ] is False


def test_missing_promoted_grammar_link_blocks_closeout() -> None:
    package = copy.deepcopy(_package())
    package["promoted_material_registry"][0]["authority_refs_by_type"]["GRAMMAR"] = []
    package["package_sha256"] = deep.sha256_value(
        {key: value for key, value in package.items() if key != "package_sha256"}
    )
    output = _build(package)
    assert output["validation_status"] == "FAIL"
    assert output["final_closeout_gate"]["distance_after"] == "D1"
    assert output["final_closeout_gate"]["source_checks"][
        "promoted_canonical_theme_vocabulary_grammar_complete"
    ] is False


def test_incomplete_four_skill_extension_blocks_closeout() -> None:
    package = copy.deepcopy(_package())
    package["mainline_extension_records"] = [
        row for row in package["mainline_extension_records"] if row["skill"] != "WRITING"
    ]
    package["aggregate_summary"]["mainline_extension_asset_count"] = 3
    package["package_sha256"] = deep.sha256_value(
        {key: value for key, value in package.items() if key != "package_sha256"}
    )
    output = _build(package)
    assert output["validation_status"] == "FAIL"
    assert output["final_closeout_gate"]["source_checks"][
        "four_skill_extension_coverage_complete"
    ] is False


def test_tampered_registry_package_fails_closed() -> None:
    package = _package()
    package["aggregate_summary"]["semantic_identity_count"] = 99
    with pytest.raises(
        closeout.FinalCloseoutError, match="registry_package_sha256_mismatch"
    ):
        _build(package)


def test_safe_closeout_makes_no_release_mastery_or_retention_claim() -> None:
    output = _build()
    assert matching.scan_forbidden_safe_keys(output) == []
    serialized = deep.canonical_json(output)
    assert '"text"' not in serialized
    assert '"title"' not in serialized
    assert output["claim_boundaries"]["learner_facing_release_approved"] is False
    assert output["claim_boundaries"]["mastery_claimed"] is False
    assert output["claim_boundaries"]["retention_claimed"] is False
