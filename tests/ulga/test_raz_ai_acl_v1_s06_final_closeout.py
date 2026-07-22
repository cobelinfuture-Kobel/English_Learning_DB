from __future__ import annotations

import pytest

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_ai_acl_v1_s05_material_registry as registry
from ulga.builders import build_raz_ai_acl_v1_s06_final_closeout as closeout


def _base(group: str, ref: str) -> dict:
    return {"semantic_duplicate_group_id": group, "selected_source_unit_ref": ref, "source_level": "A", "source_book_id": "BOOK_A", "authority_links": [{"authority_type": "VOCABULARY", "authority_ref": "vocabulary:book", "link_status": "VERIFIED_EXISTING_AUTHORITY_MATCH"}, {"authority_type": "GRAMMAR", "authority_ref": "GRAMMAR_BE_BASIC", "link_status": "VERIFIED_EXISTING_AUTHORITY_MATCH"}]}


def _package() -> dict:
    promoted = [{"material_id": "RAZ_A1A1PLUS_MATERIAL_001", **_base("G1", "A_001"), "candidate_cefr_scope": "A1", "registry_status": "PROMOTED_TO_A1_A1PLUS_MATERIAL_REGISTRY", "source_payload_access": "PRIVATE_SOURCE_REF_REQUIRED"}, {"material_id": "RAZ_A1A1PLUS_MATERIAL_002", **_base("G2", "B_001"), "candidate_cefr_scope": "A1_PLUS", "registry_status": "PROMOTED_TO_A1_A1PLUS_MATERIAL_REGISTRY", "source_payload_access": "PRIVATE_SOURCE_REF_REQUIRED"}]
    remediation = [{**_base("G3", "C_001"), "remediation_status": "PENDING_CONTENT_REWRITE_EVIDENCE", "promotion_status": "NOT_PROMOTED"}]
    support = [{**_base("G4", "D_001"), "support_status": "ADMITTED_SUPPORT_ONLY"}]
    rejected = [{**_base("G5", "E_001"), "rejection_status": "CLOSED_UNUSABLE"}]
    package = {"task_id": registry.TASK_ID, "schema_version": registry.SCHEMA_VERSION, "validation_status": registry.PASS_STATUS, "input_identity": {}, "scope_contract": {"a1_a1plus_observational_levels": list("AI"), "deferred_levels": list("JW"), "a_i_is_not_cefr_equivalence": True, "a2_a2plus_processing_status": "DEFERRED_NOT_OPENED"}, "promoted_material_registry": promoted, "remediation_queue": remediation, "support_registry": support, "rejected_registry": rejected, "duplicate_bindings": [{"semantic_duplicate_group_id": "G1", "duplicate_source_unit_ref": "A_002", "representative_source_unit_ref": "A_001", "binding_status": "BOUND_TO_SEMANTIC_REPRESENTATIVE"}], "aggregate_summary": {"source_candidate_count": 7, "a1_a1plus_scope_candidate_count": 6, "semantic_identity_count": 5, "duplicate_binding_count": 1, "deferred_a2_a2plus_count": 1, "final_promoted_material_count": 2, "remediation_queue_count": 1, "support_registry_count": 1, "rejected_registry_count": 1}, "material_registry_gate": {"decision": "A1_A1PLUS_MATERIAL_REGISTRY_READY", "ready_for_final_coverage_reconciliation": True}, "claim_boundaries": {}, "errors": []}
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _build(package: dict | None = None) -> dict:
    return closeout.build_package(package or _package(), expected_total_page_unit_count=7, expected_scope_page_unit_count=6, expected_semantic_identity_count=5, expected_duplicate_binding_count=1, expected_deferred_page_unit_count=1)


def test_reconciles_coverage_and_closes_program_at_d0() -> None:
    output = _build()
    gate = output["final_closeout_gate"]
    assert output["validation_status"] == closeout.PASS_STATUS
    assert gate["decision"] == "RAZ_AI_ACL_V1_D0_CLOSED"
    assert gate["program_status"] == "PASS_ACCEPTED_AND_CLOSED"
    assert gate["distance_after"] == "D0"
    assert gate["remaining_in_scope_blocker_count"] == 0
    assert gate["a2_a2plus_status"] == "DEFERRED_A2_A2PLUS"
    assert output["coverage_reconciliation"]["promoted_material_count"] == 2


def test_missing_promoted_grammar_link_blocks_closeout() -> None:
    package = _package()
    package["promoted_material_registry"][0]["authority_links"] = package["promoted_material_registry"][0]["authority_links"][:1]
    package["package_sha256"] = deep.sha256_value({key: value for key, value in package.items() if key != "package_sha256"})
    output = _build(package)
    assert output["validation_status"] == "FAIL"
    assert output["final_closeout_gate"]["distance_after"] == "D1"
    assert output["final_closeout_gate"]["source_checks"]["promoted_authority_complete"] is False


def test_tampered_registry_package_fails_closed() -> None:
    package = _package()
    package["aggregate_summary"]["semantic_identity_count"] = 99
    with pytest.raises(closeout.FinalCloseoutError, match="registry_package_sha256_mismatch"):
        _build(package)


def test_safe_closeout_makes_no_mastery_or_retention_claim() -> None:
    output = _build()
    assert matching.scan_forbidden_safe_keys(output) == []
    serialized = deep.canonical_json(output)
    assert '"text"' not in serialized
    assert '"title"' not in serialized
    assert output["claim_boundaries"]["mastery_claimed"] is False
    assert output["claim_boundaries"]["retention_claimed"] is False
