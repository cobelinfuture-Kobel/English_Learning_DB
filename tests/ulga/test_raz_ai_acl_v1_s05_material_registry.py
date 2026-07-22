from __future__ import annotations

import copy

import pytest

from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2
from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_ai_acl_v1_s04_admission_resolution as resolution
from ulga.builders import build_raz_ai_acl_v1_s05_material_registry as registry


def _authority_links() -> list[dict]:
    return [
        {
            "authority_type": "THEME",
            "source_authority_ref": "theme:a1_school_and_classroom",
            "canonical_authority_ref": "theme:a1_school_and_classroom",
            "resolution": "DIRECT_EXISTING_AUTHORITY_REF",
            "link_status": "VERIFIED_CANONICAL_AUTHORITY_LINK",
        },
        {
            "authority_type": "VOCABULARY",
            "source_authority_ref": "vocabulary:book",
            "canonical_authority_ref": "vocabulary:book",
            "resolution": "DIRECT_EXISTING_AUTHORITY_REF",
            "link_status": "VERIFIED_CANONICAL_AUTHORITY_LINK",
        },
        {
            "authority_type": "GRAMMAR",
            "source_authority_ref": "GRAMMAR_BE_VERB_BASIC",
            "canonical_authority_ref": "GRAMMAR_BE_VERB_BASIC",
            "resolution": "DIRECT_EXISTING_AUTHORITY_REF",
            "link_status": "VERIFIED_CANONICAL_AUTHORITY_LINK",
        },
    ]


def _row(group: str, ref: str, lane: str, scope: str = "NONE") -> dict:
    ready = lane == "PROMOTION_ELIGIBLE"
    roles = []
    if ready:
        roles = [
            {"asset_role": "SENTENCE_ASSET_CANDIDATE", "binding_status": "SAFE_PRIVATE_SOURCE_ROLE_BOUND"},
            {"asset_role": "CORE_SENTENCE_ASSET_CANDIDATE", "binding_status": "SAFE_PRIVATE_SOURCE_ROLE_BOUND"},
            {"asset_role": "PASSAGE_ASSET_CANDIDATE", "binding_status": "SAFE_PRIVATE_SOURCE_ROLE_BOUND"},
            {"asset_role": "READING_SOURCE_ASSET", "binding_status": "SAFE_PRIVATE_SOURCE_ROLE_BOUND"},
            {"asset_role": "SPEAKING_PROMPT_SEED", "binding_status": "SAFE_PRIVATE_SOURCE_ROLE_BOUND"},
        ]
    return {
        "semantic_duplicate_group_id": group,
        "selected_source_unit_ref": ref,
        "source_level": "A",
        "source_book_id": "BOOK_A",
        "candidate_cefr_scope": scope,
        "authority_links": _authority_links() if ready else [],
        "authority_refs_by_type": {
            "THEME": ["theme:a1_school_and_classroom"] if ready else [],
            "VOCABULARY": ["vocabulary:book"] if ready else [],
            "CHUNK": [],
            "PATTERN": [],
            "GRAMMAR": ["GRAMMAR_BE_VERB_BASIC"] if ready else [],
        },
        "canonical_egp_row_refs": ["EGP_A1_BE_001"] if ready else [],
        "authority_link_count": 3 if ready else 0,
        "asset_role_bindings": roles,
        "four_skill_affordances": ["READING_SOURCE", "SPEAKING_PROMPT"] if ready else [],
        "sentence_seed_maturity": "STRICT_CORE_SENTENCE_SEED" if ready else "SUPPORT_SENTENCE_SEED",
        "passage_seed_status": "SUPPORTED" if ready else "NOT_A_PASSAGE",
        "admission_resolution": lane,
        "remediation_reason_codes": [],
        "private_source_materialization_status": (
            "PRIVATE_SOURCE_RESOLUTION_REQUIRED"
            if lane in {"PROMOTION_ELIGIBLE", "SUPPORT_ADMITTED"}
            else "NOT_MATERIALIZABLE"
        ),
        "promotion_status": (
            "ELIGIBLE_NOT_PROMOTED" if ready else "NOT_PROMOTABLE"
        ),
    }


def _package() -> dict:
    rows = [
        _row("G1", "A_001", "PROMOTION_ELIGIBLE", "A1"),
        _row("G2", "B_001", "PROMOTION_ELIGIBLE", "A1_PLUS"),
        _row("G3", "C_001", "REMEDIATION_REQUIRED"),
        _row("G4", "D_001", "SUPPORT_ADMITTED"),
        _row("G5", "E_001", "REJECTED_CLOSED"),
    ]
    package = {
        "task_id": resolution.TASK_ID,
        "schema_version": resolution.SCHEMA_VERSION,
        "validation_status": resolution.PASS_STATUS,
        "input_identity": {},
        "scope_contract": {
            "a1_a1plus_observational_levels": list("AI"),
            "deferred_levels": list("JW"),
            "a_i_is_not_cefr_equivalence": True,
            "a2_a2plus_processing_status": "DEFERRED_NOT_OPENED",
        },
        "resolved_admission_rows": rows,
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
            "final_promoted_material_count": 0,
        },
        "admission_resolution_gate": {
            "decision": "SAFE_ASSET_ROLE_MATERIALIZATION_READY",
            "ready_for_mainline_consumer_integration": True,
            "remediation_queue_is_nonpromotable": True,
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
        "asset_records": [
            {
                "asset_key": "READING:BASE_A1",
                "asset_id": "BASE_A1",
                "lesson_id": "LESSON_A1_READING",
                "skill": "READING",
                "level": "A1",
                "role": "EVD",
                "payload": {"body": "Private mainline fixture"},
                "content_digest": "a" * 64,
                "release_scope": "PRIVATE_INTERNAL_D0",
            },
            {
                "asset_key": "SPEAKING:BASE_A1",
                "asset_id": "BASE_A1_S",
                "lesson_id": "LESSON_A1_SPEAKING",
                "skill": "SPEAKING",
                "level": "A1",
                "role": "PRD",
                "payload": {"body": "Private speaking fixture"},
                "content_digest": "b" * 64,
                "release_scope": "PRIVATE_INTERNAL_D0",
            },
            {
                "asset_key": "READING:BASE_A1PLUS",
                "asset_id": "BASE_A1PLUS",
                "lesson_id": "LESSON_A1PLUS_READING",
                "skill": "READING",
                "level": "A1+",
                "role": "EVD",
                "payload": {"body": "Private A1 plus fixture"},
                "content_digest": "c" * 64,
                "release_scope": "PRIVATE_INTERNAL_D0",
            },
            {
                "asset_key": "READING:A2_LOCKED",
                "asset_id": "A2_LOCKED",
                "lesson_id": "LESSON_A2_READING",
                "skill": "READING",
                "level": "A2",
                "role": "EVD",
                "payload": {"body": "A2 must stay locked"},
                "content_digest": "d" * 64,
                "release_scope": "PRIVATE_INTERNAL_D0",
            },
        ],
        "lesson_catalog": [
            {
                "lesson_id": "LESSON_A1_READING",
                "lesson_node_id": "LESSON:READING:LESSON_A1_READING",
                "skill": "READING",
                "level": "A1",
                "asset_keys": ["READING:BASE_A1"],
                "roles": ["EVD"],
                "requirement_node_ids": ["EGP_A1_BE_001"],
                "release_scope": "PRIVATE_INTERNAL_D0",
            },
            {
                "lesson_id": "LESSON_A1_SPEAKING",
                "lesson_node_id": "LESSON:SPEAKING:LESSON_A1_SPEAKING",
                "skill": "SPEAKING",
                "level": "A1",
                "asset_keys": ["SPEAKING:BASE_A1"],
                "roles": ["PRD"],
                "requirement_node_ids": ["GRAMMAR_BE_VERB_BASIC"],
                "release_scope": "PRIVATE_INTERNAL_D0",
            },
            {
                "lesson_id": "LESSON_A1PLUS_READING",
                "lesson_node_id": "LESSON:READING:LESSON_A1PLUS_READING",
                "skill": "READING",
                "level": "A1+",
                "asset_keys": ["READING:BASE_A1PLUS"],
                "roles": ["EVD"],
                "requirement_node_ids": ["EGP_A1_BE_001"],
                "release_scope": "PRIVATE_INTERNAL_D0",
            },
            {
                "lesson_id": "LESSON_A2_READING",
                "lesson_node_id": "LESSON:READING:LESSON_A2_READING",
                "skill": "READING",
                "level": "A2",
                "asset_keys": ["READING:A2_LOCKED"],
                "roles": ["EVD"],
                "requirement_node_ids": ["A2_ONLY"],
                "release_scope": "PRIVATE_INTERNAL_D0",
            },
        ],
        "counts": {
            "asset_record_count": 4,
            "lesson_count": 4,
            "learning_lesson_count": 3,
            "a2_handoff_lesson_count": 1,
        },
        "access_contract": {
            "visibility": "PRIVATE_INTERNAL",
            "learning_query_levels": ["A1", "A1+"],
            "a2_payload_query_allowed": False,
            "a2_handoff_metadata_allowed": True,
            "max_query_limit": 100,
            "filter_fields": [
                "skill", "level", "lesson_id", "role", "requirement_node_id"
            ],
        },
        "claim_boundaries": {},
        "errors": [],
    }


def _digests() -> dict[str, str]:
    return {
        "A_001": "1" * 64,
        "A_002": "2" * 64,
        "B_001": "3" * 64,
        "C_001": "4" * 64,
        "D_001": "5" * 64,
        "E_001": "6" * 64,
    }


def _build(package: dict | None = None) -> dict:
    mainline = _mainline()
    return registry.build_package(
        package or _package(),
        mainline,
        _digests(),
        [{"level": "A", "source_path": "A.json", "record_count": 6, "sha256": "f" * 64}],
        mainline_index_sha256=registry._material_id("M2", "fixture"),
        expected_total_page_unit_count=7,
        expected_scope_page_unit_count=6,
        expected_semantic_identity_count=5,
        expected_duplicate_binding_count=1,
        expected_deferred_page_unit_count=1,
    )


def test_integrates_promoted_materials_with_combined_m2_consumer() -> None:
    output = _build()
    assert output["validation_status"] == registry.PASS_STATUS
    assert output["mainline_consumer_gate"]["decision"] == (
        "MAINLINE_M2_CONSUMER_EXTENSION_READY"
    )
    assert output["mainline_consumer_gate"]["distance_after"] == "D1"
    assert output["aggregate_summary"]["final_promoted_material_count"] == 2
    assert output["aggregate_summary"]["mainline_extension_asset_count"] == 4
    assert output["aggregate_summary"][
        "mainline_lesson_linked_extension_asset_count"
    ] == 4
    assert len(output["remediation_queue"]) == 1
    assert all(
        row["registry_status"] == "INTEGRATED_WITH_MAINLINE_M2_CONSUMER"
        for row in output["promoted_material_registry"]
    )
    assert output["consumer_query_proof"]["combined_origin_query"] is not None
    assert output["consumer_query_proof"]["a2_lock_verified"] is True


def test_combined_query_returns_mainline_and_raz_and_supports_authority_filter() -> None:
    output = _build()
    combined = registry.query_combined_index(
        _mainline(), output, skill="READING", level="A1", limit=100
    )
    assert combined["mainline_match_count"] == 1
    assert combined["raz_extension_match_count"] == 1
    assert {row["origin"] for row in combined["records"]} == {
        "MAINLINE_M2", "RAZ_DERIVED_EXTENSION"
    }
    authority = registry.query_combined_index(
        _mainline(), output, authority_ref="vocabulary:book", limit=100
    )
    assert authority["mainline_match_count"] == 0
    assert authority["raz_extension_match_count"] == 4
    role = registry.query_combined_index(
        _mainline(), output, asset_role="CORE_SENTENCE_ASSET_CANDIDATE", limit=100
    )
    assert role["raz_extension_match_count"] == 4
    with pytest.raises(registry.MaterialRegistryError, match="A2_PAYLOAD_LOCKED"):
        registry.query_combined_index(_mainline(), output, level="A2")


def test_noneligible_row_cannot_enter_promoted_registry() -> None:
    package = _package()
    package["resolved_admission_rows"][2]["admission_resolution"] = "PROMOTION_ELIGIBLE"
    package["package_sha256"] = deep.sha256_value(
        {key: value for key, value in package.items() if key != "package_sha256"}
    )
    with pytest.raises(registry.MaterialRegistryError, match="promoted_scope_invalid"):
        _build(package)


def test_missing_private_source_fails_closed() -> None:
    mainline = _mainline()
    digests = _digests()
    digests.pop("A_001")
    with pytest.raises(registry.MaterialRegistryError, match="private_source_ref_missing"):
        registry.build_package(
            _package(),
            mainline,
            digests,
            [],
            mainline_index_sha256="a" * 64,
            expected_total_page_unit_count=7,
            expected_scope_page_unit_count=6,
            expected_semantic_identity_count=5,
            expected_duplicate_binding_count=1,
            expected_deferred_page_unit_count=1,
        )


def test_tampered_resolution_package_fails_closed() -> None:
    package = copy.deepcopy(_package())
    package["aggregate_summary"]["semantic_identity_count"] = 99
    with pytest.raises(
        registry.MaterialRegistryError,
        match="resolution_package_sha256_mismatch",
    ):
        _build(package)


def test_safe_output_contains_no_source_text_or_title() -> None:
    output = _build()
    assert matching.scan_forbidden_safe_keys(output) == []
    serialized = deep.canonical_json(output)
    assert '"text"' not in serialized
    assert '"title"' not in serialized
    assert "Private mainline fixture" not in serialized
    assert output["claim_boundaries"]["rewrite_required_rows_promoted"] is False
    assert output["mainline_consumer_gate"]["ready_for_learner_facing_release"] is False
