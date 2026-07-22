from __future__ import annotations

import pytest

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_ai_acl_v1_s04_admission_resolution as resolution
from ulga.builders import build_raz_ai_acl_v1_s05_material_registry as registry


def _row(group: str, ref: str, lane: str, scope: str = "NONE") -> dict:
    return {"semantic_duplicate_group_id": group, "selected_source_unit_ref": ref, "source_level": "A", "source_book_id": "BOOK_A", "candidate_cefr_scope": scope, "authority_links": [{"authority_type": "THEME", "authority_ref": "theme:a1_school", "link_status": "VERIFIED_EXISTING_AUTHORITY_MATCH"}], "authority_link_count": 1, "admission_resolution": lane, "remediation_reason_codes": [], "promotion_status": "ELIGIBLE_NOT_PROMOTED" if lane == "PROMOTION_ELIGIBLE" else "NOT_PROMOTABLE"}


def _package() -> dict:
    rows = [_row("G1", "A_001", "PROMOTION_ELIGIBLE", "A1"), _row("G2", "B_001", "PROMOTION_ELIGIBLE", "A1_PLUS"), _row("G3", "C_001", "REMEDIATION_REQUIRED"), _row("G4", "D_001", "SUPPORT_ADMITTED"), _row("G5", "E_001", "REJECTED_CLOSED")]
    package = {"task_id": resolution.TASK_ID, "schema_version": resolution.SCHEMA_VERSION, "validation_status": resolution.PASS_STATUS, "input_identity": {}, "scope_contract": {"a1_a1plus_observational_levels": list("AI"), "deferred_levels": list("JW"), "a_i_is_not_cefr_equivalence": True, "a2_a2plus_processing_status": "DEFERRED_NOT_OPENED"}, "resolved_admission_rows": rows, "duplicate_bindings": [{"semantic_duplicate_group_id": "G1", "duplicate_source_unit_ref": "A_002", "representative_source_unit_ref": "A_001", "binding_status": "BOUND_TO_SEMANTIC_REPRESENTATIVE"}], "aggregate_summary": {"source_candidate_count": 7, "a1_a1plus_scope_candidate_count": 6, "semantic_identity_count": 5, "duplicate_binding_count": 1, "deferred_a2_a2plus_count": 1, "final_promoted_material_count": 0}, "admission_resolution_gate": {"decision": "ADMISSION_RESOLUTION_READY", "ready_for_material_registry_promotion": True, "remediation_queue_is_nonpromotable": True}, "claim_boundaries": {}, "errors": []}
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _build(package: dict | None = None) -> dict:
    return registry.build_package(package or _package(), expected_total_page_unit_count=7, expected_scope_page_unit_count=6, expected_semantic_identity_count=5, expected_duplicate_binding_count=1, expected_deferred_page_unit_count=1)


def test_promotes_only_eligible_rows_to_stable_registry() -> None:
    output = _build()
    assert output["validation_status"] == registry.PASS_STATUS
    assert output["material_registry_gate"]["decision"] == "A1_A1PLUS_MATERIAL_REGISTRY_READY"
    assert output["material_registry_gate"]["distance_after"] == "D1"
    assert output["aggregate_summary"]["final_promoted_material_count"] == 2
    assert len(output["remediation_queue"]) == 1
    assert all(row["registry_status"] == "PROMOTED_TO_A1_A1PLUS_MATERIAL_REGISTRY" for row in output["promoted_material_registry"])
    assert len({row["material_id"] for row in output["promoted_material_registry"]}) == 2


def test_noneligible_row_cannot_enter_promoted_registry() -> None:
    package = _package()
    package["resolved_admission_rows"][2]["admission_resolution"] = "PROMOTION_ELIGIBLE"
    package["package_sha256"] = deep.sha256_value({key: value for key, value in package.items() if key != "package_sha256"})
    with pytest.raises(registry.MaterialRegistryError, match="promoted_scope_invalid"):
        _build(package)


def test_tampered_resolution_package_fails_closed() -> None:
    package = _package()
    package["aggregate_summary"]["semantic_identity_count"] = 99
    with pytest.raises(registry.MaterialRegistryError, match="resolution_package_sha256_mismatch"):
        _build(package)


def test_safe_output_contains_no_source_text_or_title() -> None:
    output = _build()
    assert matching.scan_forbidden_safe_keys(output) == []
    serialized = deep.canonical_json(output)
    assert '"text"' not in serialized
    assert '"title"' not in serialized
    assert output["claim_boundaries"]["rewrite_required_rows_promoted"] is False
    assert output["material_registry_gate"]["ready_for_learner_facing_content"] is False
