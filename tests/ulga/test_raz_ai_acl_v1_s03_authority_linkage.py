from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_ai_acl_v1_s02_semantic_dedup as dedup
from ulga.builders import build_raz_ai_acl_v1_s03_authority_linkage as linkage


def _representative(
    group: str,
    ref: str,
    status: str,
    scope: str,
    *,
    theme_ref: str = "theme:a1_school_and_classroom",
) -> dict:
    ready = status in {"A1_READY_CANDIDATE", "A1PLUS_READY_CANDIDATE"}
    return {
        "semantic_duplicate_group_id": group,
        "selected_source_unit_ref": ref,
        "source_level": "A",
        "source_book_id": "BOOK_A",
        "representative_admission_status": status,
        "candidate_cefr_scope": scope,
        "candidate_theme_refs": [theme_ref],
        "matched_vocabulary_refs": ["vocabulary:book"] if ready else [],
        "matched_chunk_refs": ["chunk:on_the"] if status == "SUPPORT_ONLY" else [],
        "matched_pattern_refs": [],
        "matched_grammar_unit_refs": ["GRAMMAR_BE_VERB_BASIC"] if ready else [],
        "sentence_seed_maturity": "STRICT_CORE_SENTENCE_SEED" if ready else "SUPPORT_SENTENCE_SEED",
        "passage_seed_status": "SUPPORTED" if ready else "NOT_A_PASSAGE",
        "discourse_shape": "simple_narrative_or_description",
        "scene_structure": "GENERAL_CONTEXT_SCENE",
        "four_skill_affordances": ["READING_SOURCE", "SPEAKING_PROMPT"] if ready else ["READING_SOURCE"],
        "promotion_status": "NOT_PROMOTED",
    }


def _dedup_package() -> dict:
    rows = [
        _representative(
            "G1",
            "A_001",
            "A1_READY_CANDIDATE",
            "A1",
            theme_ref="theme_candidate:a1_animals_and_habitats",
        ),
        _representative("G2", "B_001", "A1PLUS_READY_CANDIDATE", "A1_PLUS"),
        _representative("G3", "C_001", "REWRITE_REQUIRED", "NONE"),
        _representative("G4", "D_001", "SUPPORT_ONLY", "NONE"),
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


def _authorities() -> dict[str, set[str]]:
    shared = "shared:cross_type"
    return {
        "THEME": {
            "theme:a1_school_and_classroom",
            "theme:a1_animals_and_habitats",
        },
        "VOCABULARY": {"vocabulary:book", shared},
        "CHUNK": {"chunk:on_the", shared},
        "PATTERN": {"pattern:svo"},
        "GRAMMAR": {"GRAMMAR_BE_VERB_BASIC"},
    }


def _grammar_to_egp() -> dict[str, list[str]]:
    return {"GRAMMAR_BE_VERB_BASIC": ["EGP_A1_BE_001", "EGP_A1_BE_002"]}


def _build(package: dict | None = None, authorities: dict[str, set[str]] | None = None) -> dict:
    return linkage.build_package(
        package or _dedup_package(),
        authorities or _authorities(),
        {key: {"source_sha256": key.lower() * 8} for key in _authorities()},
        _grammar_to_egp(),
        expected_total_page_unit_count=7,
        expected_scope_page_unit_count=6,
        expected_semantic_identity_count=5,
        expected_duplicate_binding_count=1,
        expected_deferred_page_unit_count=1,
    )


def test_validates_canonical_links_resolves_theme_mount_and_advances_distance() -> None:
    package = _build()
    assert package["validation_status"] == linkage.PASS_STATUS
    assert package["authority_linkage_gate"]["decision"] == (
        "CANONICAL_AUTHORITY_ASSET_ROLE_LINKAGE_READY"
    )
    assert package["authority_linkage_gate"]["distance_after"] == "D3"
    assert package["authority_linkage_gate"]["ready_for_safe_asset_materialization"] is True
    row = package["authority_linkage_rows"][0]
    theme = next(link for link in row["authority_links"] if link["authority_type"] == "THEME")
    assert theme == {
        "authority_type": "THEME",
        "source_authority_ref": "theme_candidate:a1_animals_and_habitats",
        "canonical_authority_ref": "theme:a1_animals_and_habitats",
        "resolution": "OPERATOR_APPROVED_THEME_CANDIDATE_TO_CANONICAL",
        "link_status": "VERIFIED_CANONICAL_AUTHORITY_LINK",
    }
    assert row["authority_refs_by_type"]["GRAMMAR"] == ["GRAMMAR_BE_VERB_BASIC"]
    assert row["canonical_egp_row_refs"] == ["EGP_A1_BE_001", "EGP_A1_BE_002"]
    assert row["candidate_asset_roles"] == [
        "CORE_SENTENCE_ASSET_CANDIDATE",
        "PASSAGE_ASSET_CANDIDATE",
        "SENTENCE_ASSET_CANDIDATE",
    ]
    assert row["candidate_skill_asset_roles"] == [
        "READING_SOURCE_ASSET",
        "SPEAKING_PROMPT_SEED",
    ]
    assert package["aggregate_summary"][
        "resolved_operator_approved_theme_candidate_link_count"
    ] == 1
    assert package["aggregate_summary"]["unresolved_authority_ref_count"] == 0


def test_unknown_authority_reference_fails_closed() -> None:
    package = _dedup_package()
    package["semantic_representatives"][0]["matched_vocabulary_refs"] = [
        "vocabulary:not_in_registry"
    ]
    package["package_sha256"] = deep.sha256_value(
        {key: value for key, value in package.items() if key != "package_sha256"}
    )
    with pytest.raises(
        linkage.AuthorityLinkageError,
        match="authority_ref_not_found:VOCABULARY",
    ):
        _build(package)


def test_unapproved_theme_candidate_fails_closed() -> None:
    package = _dedup_package()
    package["semantic_representatives"][0]["candidate_theme_refs"] = [
        "theme_candidate:a1_unapproved"
    ]
    package["package_sha256"] = deep.sha256_value(
        {key: value for key, value in package.items() if key != "package_sha256"}
    )
    with pytest.raises(
        linkage.AuthorityLinkageError,
        match="unapproved_theme_candidate_ref",
    ):
        _build(package)


def test_ready_representative_without_grammar_fails_closed() -> None:
    package = _dedup_package()
    package["semantic_representatives"][0]["matched_grammar_unit_refs"] = []
    package["package_sha256"] = deep.sha256_value(
        {key: value for key, value in package.items() if key != "package_sha256"}
    )
    with pytest.raises(
        linkage.AuthorityLinkageError,
        match="ready_representative_missing_required_authority",
    ):
        _build(package)


def test_same_reference_in_two_authority_types_blocks_gate() -> None:
    package = _dedup_package()
    package["semantic_representatives"][0]["matched_vocabulary_refs"] = [
        "shared:cross_type"
    ]
    package["semantic_representatives"][0]["matched_chunk_refs"] = [
        "shared:cross_type"
    ]
    package["package_sha256"] = deep.sha256_value(
        {key: value for key, value in package.items() if key != "package_sha256"}
    )
    output = _build(package)
    assert output["validation_status"] == "FAIL"
    assert output["authority_linkage_gate"]["distance_after"] == "D4"
    assert output["aggregate_summary"]["authority_reference_type_conflict_count"] == 1


def test_tampered_dedup_package_fails_closed() -> None:
    package = _dedup_package()
    package["aggregate_summary"]["representative_count"] = 99
    with pytest.raises(
        linkage.AuthorityLinkageError, match="dedup_package_sha256_mismatch"
    ):
        _build(package)


def test_safe_output_contains_no_source_text_title_or_promotion() -> None:
    package = _build()
    assert matching.scan_forbidden_safe_keys(package) == []
    serialized = deep.canonical_json(package)
    assert '"text"' not in serialized
    assert '"title"' not in serialized
    assert package["claim_boundaries"]["canonical_authority_write_performed_by_this_builder"] is False
    assert package["claim_boundaries"]["material_promotion_performed"] is False
