from __future__ import annotations

import pytest

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_ai_acl_v1_s03_authority_linkage as linkage
from ulga.builders import build_raz_ai_acl_v1_s04_admission_resolution as resolution


def _row(group: str, ref: str, admission: str, scope: str) -> dict:
    status = {
        "A1_READY_CANDIDATE": "AUTHORITY_LINKED_A1_READY",
        "A1PLUS_READY_CANDIDATE": "AUTHORITY_LINKED_A1PLUS_READY",
        "REWRITE_REQUIRED": "AUTHORITY_LINKED_REWRITE_REQUIRED",
        "SUPPORT_ONLY": "AUTHORITY_LINKED_SUPPORT_ONLY",
        "REJECTED_UNUSABLE": "REJECTED_NOT_PROMOTABLE",
    }[admission]
    links = [{"authority_type": "THEME", "authority_ref": "theme:a1_school", "link_status": "VERIFIED_EXISTING_AUTHORITY_MATCH"}]
    if "READY" in admission:
        links += [
            {"authority_type": "VOCABULARY", "authority_ref": "vocabulary:book", "link_status": "VERIFIED_EXISTING_AUTHORITY_MATCH"},
            {"authority_type": "GRAMMAR", "authority_ref": "GRAMMAR_BE_BASIC", "link_status": "VERIFIED_EXISTING_AUTHORITY_MATCH"},
        ]
    return {
        "semantic_duplicate_group_id": group,
        "selected_source_unit_ref": ref,
        "source_level": "A",
        "source_book_id": "BOOK_A",
        "representative_admission_status": admission,
        "candidate_cefr_scope": scope,
        "authority_links": links,
        "authority_link_count": len(links),
        "authority_linkage_status": status,
        "promotion_status": "NOT_PROMOTED",
    }


def _package() -> dict:
    rows = [
        _row("G1", "A_001", "A1_READY_CANDIDATE", "A1"),
        _row("G2", "B_001", "A1PLUS_READY_CANDIDATE", "A1_PLUS"),
        _row("G3", "C_001", "REWRITE_REQUIRED", "A1_A1PLUS_UNRESOLVED"),
        _row("G4", "D_001", "SUPPORT_ONLY", "NONE"),
        _row("G5", "E_001", "REJECTED_UNUSABLE", "NONE"),
    ]
    package = {
        "task_id": linkage.TASK_ID,
        "schema_version": linkage.SCHEMA_VERSION,
        "validation_status": linkage.PASS_STATUS,
        "input_identity": {},
        "scope_contract": {"a1_a1plus_observational_levels": list("AI"), "deferred_levels": list("JW"), "a_i_is_not_cefr_equivalence": True, "a2_a2plus_processing_status": "DEFERRED_NOT_OPENED"},
        "authority_linkage_rows": rows,
        "duplicate_bindings": [{"semantic_duplicate_group_id": "G1", "duplicate_source_unit_ref": "A_002", "representative_source_unit_ref": "A_001", "binding_status": "BOUND_TO_SEMANTIC_REPRESENTATIVE"}],
        "authority_reference_type_conflicts": [],
        "aggregate_summary": {"source_candidate_count": 7, "a1_a1plus_scope_candidate_count": 6, "semantic_identity_count": 5, "representative_count": 5, "duplicate_binding_count": 1, "deferred_a2_a2plus_count": 1, "authority_reference_type_conflict_count": 0, "final_promoted_material_count": 0},
        "authority_linkage_gate": {"decision": "AUTHORITY_LINKAGE_READY", "ready_for_rewrite_and_admission_resolution": True, "ready_for_material_promotion": False},
        "claim_boundaries": {},
        "errors": [],
    }
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _build(package: dict | None = None) -> dict:
    return resolution.build_package(package or _package(), expected_total_page_unit_count=7, expected_scope_page_unit_count=6, expected_semantic_identity_count=5, expected_duplicate_binding_count=1, expected_deferred_page_unit_count=1)


def test_resolves_all_lanes_without_promoting_rewrite_rows() -> None:
    output = _build()
    assert output["validation_status"] == resolution.PASS_STATUS
    assert output["admission_resolution_gate"]["decision"] == "ADMISSION_RESOLUTION_READY"
    assert output["admission_resolution_gate"]["distance_after"] == "D2"
    assert output["aggregate_summary"]["promotion_eligible_count"] == 2
    assert output["aggregate_summary"]["remediation_required_count"] == 1
    rows = {row["selected_source_unit_ref"]: row for row in output["resolved_admission_rows"]}
    assert rows["C_001"]["admission_resolution"] == "REMEDIATION_REQUIRED"
    assert rows["C_001"]["promotion_status"] == "NOT_PROMOTABLE"


@pytest.mark.parametrize(
    ("row_index", "invalid_scope"),
    [
        (0, "A1_PLUS"),
        (1, "A1"),
        (2, "NONE"),
        (2, "A1"),
        (3, "A1_A1PLUS_UNRESOLVED"),
        (4, "A1_A1PLUS_UNRESOLVED"),
    ],
)
def test_admission_status_scope_mismatch_fails_closed(
    row_index: int, invalid_scope: str
) -> None:
    package = _package()
    package["authority_linkage_rows"][row_index][
        "candidate_cefr_scope"
    ] = invalid_scope
    package["package_sha256"] = deep.sha256_value(
        {key: value for key, value in package.items() if key != "package_sha256"}
    )
    with pytest.raises(
        resolution.AdmissionResolutionError,
        match="candidate_cefr_scope_mismatch",
    ):
        _build(package)


def test_tampered_linkage_package_fails_closed() -> None:
    package = _package()
    package["aggregate_summary"]["semantic_identity_count"] = 99
    with pytest.raises(resolution.AdmissionResolutionError, match="linkage_package_sha256_mismatch"):
        _build(package)


def test_safe_output_contains_no_text_title_or_premature_promotion() -> None:
    output = _build()
    assert matching.scan_forbidden_safe_keys(output) == []
    serialized = deep.canonical_json(output)
    assert '"text"' not in serialized
    assert '"title"' not in serialized
    assert output["claim_boundaries"]["automatic_rewrite_performed"] is False
    assert output["claim_boundaries"]["material_promotion_performed"] is False
