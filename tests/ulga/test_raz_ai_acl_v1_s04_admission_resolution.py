from __future__ import annotations

import pytest

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_ai_acl_v1_s03_authority_linkage as linkage
from ulga.builders import build_raz_ai_acl_v1_s04_admission_resolution as resolution


def _row(group: str, ref: str, admission: str, scope: str) -> dict:
    status = {
        "A1_READY_CANDIDATE": "CANONICAL_LINKED_A1_READY",
        "A1PLUS_READY_CANDIDATE": "CANONICAL_LINKED_A1PLUS_READY",
        "REWRITE_REQUIRED": "CANONICAL_LINKED_REWRITE_REQUIRED",
        "SUPPORT_ONLY": "CANONICAL_LINKED_SUPPORT_ONLY",
        "REJECTED_UNUSABLE": "REJECTED_NOT_PROMOTABLE",
    }[admission]
    links = [
        {
            "authority_type": "THEME",
            "source_authority_ref": "theme:a1_school_and_classroom",
            "canonical_authority_ref": "theme:a1_school_and_classroom",
            "resolution": "DIRECT_EXISTING_AUTHORITY_REF",
            "link_status": "VERIFIED_CANONICAL_AUTHORITY_LINK",
        }
    ]
    refs = {
        "THEME": ["theme:a1_school_and_classroom"],
        "VOCABULARY": [],
        "CHUNK": [],
        "PATTERN": [],
        "GRAMMAR": [],
    }
    ready = admission in {"A1_READY_CANDIDATE", "A1PLUS_READY_CANDIDATE"}
    if ready:
        links += [
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
        refs["VOCABULARY"] = ["vocabulary:book"]
        refs["GRAMMAR"] = ["GRAMMAR_BE_VERB_BASIC"]
    elif admission == "SUPPORT_ONLY":
        links.append(
            {
                "authority_type": "CHUNK",
                "source_authority_ref": "chunk:on_the",
                "canonical_authority_ref": "chunk:on_the",
                "resolution": "DIRECT_EXISTING_AUTHORITY_REF",
                "link_status": "VERIFIED_CANONICAL_AUTHORITY_LINK",
            }
        )
        refs["CHUNK"] = ["chunk:on_the"]
    return {
        "semantic_duplicate_group_id": group,
        "selected_source_unit_ref": ref,
        "source_level": "A",
        "source_book_id": "BOOK_A",
        "representative_admission_status": admission,
        "candidate_cefr_scope": scope,
        "authority_links": links,
        "authority_refs_by_type": refs,
        "canonical_egp_row_refs": ["EGP_A1_BE_001"] if ready else [],
        "authority_link_count": len(links),
        "authority_linkage_status": status,
        "sentence_seed_maturity": "STRICT_CORE_SENTENCE_SEED" if ready else "SUPPORT_SENTENCE_SEED",
        "passage_seed_status": "SUPPORTED" if ready else "NOT_A_PASSAGE",
        "four_skill_affordances": ["READING_SOURCE", "SPEAKING_PROMPT"] if ready else ["READING_SOURCE"],
        "candidate_asset_roles": [
            "CORE_SENTENCE_ASSET_CANDIDATE",
            "PASSAGE_ASSET_CANDIDATE",
            "SENTENCE_ASSET_CANDIDATE",
        ] if ready else [],
        "candidate_skill_asset_roles": [
            "READING_SOURCE_ASSET",
            "SPEAKING_PROMPT_SEED",
        ] if ready else [],
        "canonical_linkage_complete": True,
        "promotion_status": "NOT_PROMOTED",
    }


def _package() -> dict:
    rows = [
        _row("G1", "A_001", "A1_READY_CANDIDATE", "A1"),
        _row("G2", "B_001", "A1PLUS_READY_CANDIDATE", "A1_PLUS"),
        _row("G3", "C_001", "REWRITE_REQUIRED", "NONE"),
        _row("G4", "D_001", "SUPPORT_ONLY", "NONE"),
        _row("G5", "E_001", "REJECTED_UNUSABLE", "NONE"),
    ]
    package = {
        "task_id": linkage.TASK_ID,
        "schema_version": linkage.SCHEMA_VERSION,
        "validation_status": linkage.PASS_STATUS,
        "input_identity": {},
        "scope_contract": {
            "a1_a1plus_observational_levels": list("AI"),
            "deferred_levels": list("JW"),
            "a_i_is_not_cefr_equivalence": True,
            "a2_a2plus_processing_status": "DEFERRED_NOT_OPENED",
        },
        "authority_linkage_rows": rows,
        "duplicate_bindings": [
            {
                "semantic_duplicate_group_id": "G1",
                "duplicate_source_unit_ref": "A_002",
                "representative_source_unit_ref": "A_001",
                "binding_status": "BOUND_TO_SEMANTIC_REPRESENTATIVE",
            }
        ],
        "authority_reference_type_conflicts": [],
        "aggregate_summary": {
            "source_candidate_count": 7,
            "a1_a1plus_scope_candidate_count": 6,
            "semantic_identity_count": 5,
            "representative_count": 5,
            "duplicate_binding_count": 1,
            "deferred_a2_a2plus_count": 1,
            "authority_reference_type_conflict_count": 0,
            "unresolved_authority_ref_count": 0,
            "final_promoted_material_count": 0,
        },
        "authority_linkage_gate": {
            "decision": "CANONICAL_AUTHORITY_ASSET_ROLE_LINKAGE_READY",
            "ready_for_safe_asset_materialization": True,
            "ready_for_material_promotion": False,
        },
        "claim_boundaries": {},
        "errors": [],
    }
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _build(package: dict | None = None) -> dict:
    return resolution.build_package(
        package or _package(),
        expected_total_page_unit_count=7,
        expected_scope_page_unit_count=6,
        expected_semantic_identity_count=5,
        expected_duplicate_binding_count=1,
        expected_deferred_page_unit_count=1,
    )


def test_materializes_asset_roles_and_resolves_all_lanes() -> None:
    output = _build()
    assert output["validation_status"] == resolution.PASS_STATUS
    assert output["admission_resolution_gate"]["decision"] == (
        "SAFE_ASSET_ROLE_MATERIALIZATION_READY"
    )
    assert output["admission_resolution_gate"]["distance_after"] == "D2"
    assert output["admission_resolution_gate"][
        "ready_for_mainline_consumer_integration"
    ] is True
    assert output["aggregate_summary"]["promotion_eligible_count"] == 2
    assert output["aggregate_summary"]["remediation_required_count"] == 1
    assert output["aggregate_summary"]["safe_sentence_asset_candidate_count"] == 2
    assert output["aggregate_summary"]["safe_core_sentence_asset_candidate_count"] == 2
    assert output["aggregate_summary"]["safe_passage_asset_candidate_count"] == 2
    rows = {
        row["selected_source_unit_ref"]: row
        for row in output["resolved_admission_rows"]
    }
    assert rows["A_001"]["admission_resolution"] == "PROMOTION_ELIGIBLE"
    assert {
        binding["asset_role"] for binding in rows["A_001"]["asset_role_bindings"]
    } == {
        "CORE_SENTENCE_ASSET_CANDIDATE",
        "PASSAGE_ASSET_CANDIDATE",
        "READING_SOURCE_ASSET",
        "SENTENCE_ASSET_CANDIDATE",
        "SPEAKING_PROMPT_SEED",
    }
    assert rows["C_001"]["admission_resolution"] == "REMEDIATION_REQUIRED"
    assert rows["C_001"]["promotion_status"] == "NOT_PROMOTABLE"


def test_noncanonical_link_fails_closed() -> None:
    package = _package()
    package["authority_linkage_rows"][0]["authority_links"][0]["link_status"] = (
        "APPROVED_PENDING_CANONICAL_MOUNT"
    )
    package["package_sha256"] = deep.sha256_value(
        {key: value for key, value in package.items() if key != "package_sha256"}
    )
    with pytest.raises(
        resolution.AdmissionResolutionError,
        match="noncanonical_authority_link",
    ):
        _build(package)


def test_rewrite_row_with_promotable_scope_fails_closed() -> None:
    package = _package()
    package["authority_linkage_rows"][2]["candidate_cefr_scope"] = "A1"
    package["package_sha256"] = deep.sha256_value(
        {key: value for key, value in package.items() if key != "package_sha256"}
    )
    with pytest.raises(
        resolution.AdmissionResolutionError, match="nonpromotion_scope_invalid"
    ):
        _build(package)


def test_tampered_linkage_package_fails_closed() -> None:
    package = _package()
    package["aggregate_summary"]["semantic_identity_count"] = 99
    with pytest.raises(
        resolution.AdmissionResolutionError,
        match="linkage_package_sha256_mismatch",
    ):
        _build(package)


def test_safe_output_contains_no_text_title_or_premature_registry_promotion() -> None:
    output = _build()
    assert matching.scan_forbidden_safe_keys(output) == []
    serialized = deep.canonical_json(output)
    assert '"text"' not in serialized
    assert '"title"' not in serialized
    assert output["claim_boundaries"]["automatic_rewrite_performed"] is False
    assert output["claim_boundaries"]["material_registry_promotion_performed"] is False
