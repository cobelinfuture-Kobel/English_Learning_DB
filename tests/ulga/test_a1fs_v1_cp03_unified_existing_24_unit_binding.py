from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_a1fs_v1_cp03_unified_existing_24_unit_binding as builder
from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_ai_acl_v1_s05_material_registry as registry
from ulga.validators import validate_a1fs_v1_cp03_unified_existing_24_unit_binding as validator


def _sources() -> tuple[dict, dict]:
    return builder._read(builder.CP01_PATH), builder._read(builder.CP02_PATH)


def _material(material_id: str, grammar_refs: list[str], scope: str) -> dict:
    return {
        "material_id": material_id,
        "semantic_duplicate_group_id": f"GROUP_{material_id}",
        "selected_source_unit_ref": f"SOURCE_{material_id}",
        "source_level": "A",
        "source_book_id": "BOOK_A",
        "authority_links": [
            {
                "authority_type": "GRAMMAR",
                "authority_ref": grammar_ref,
                "link_status": "VERIFIED_EXISTING_AUTHORITY_MATCH",
            }
            for grammar_ref in grammar_refs
        ],
        "candidate_cefr_scope": scope,
        "registry_status": "PROMOTED_TO_A1_A1PLUS_MATERIAL_REGISTRY",
        "source_payload_access": "PRIVATE_SOURCE_REF_REQUIRED",
    }


def _registry_package() -> dict:
    promoted = [
        _material(
            "RAZ_A1A1PLUS_MATERIAL_000000000000000000000001",
            ["GRAMMAR_ARTICLES_BASIC"],
            "A1",
        ),
        _material(
            "RAZ_A1A1PLUS_MATERIAL_000000000000000000000002",
            ["GRAMMAR_BE_VERB_BASIC", "GRAMMAR_OBJECT_PRONOUNS_BASIC"],
            "A1_PLUS",
        ),
    ]
    package = {
        "task_id": registry.TASK_ID,
        "schema_version": registry.SCHEMA_VERSION,
        "validation_status": registry.PASS_STATUS,
        "input_identity": {},
        "scope_contract": {},
        "promoted_material_registry": promoted,
        "remediation_queue": [],
        "support_registry": [],
        "rejected_registry": [],
        "duplicate_bindings": [],
        "aggregate_summary": {"final_promoted_material_count": len(promoted)},
        "material_registry_gate": {
            "decision": "A1_A1PLUS_MATERIAL_REGISTRY_READY",
            "ready_for_final_coverage_reconciliation": True,
        },
        "claim_boundaries": {},
        "errors": [],
    }
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _build(registry_package: dict | None = None) -> tuple[dict, dict, dict, dict]:
    cp01, cp02 = _sources()
    package = registry_package or _registry_package()
    artifact = builder.build_artifact(cp01, cp02, package)
    return artifact, cp01, cp02, package


def test_cp03_uses_only_the_existing_24_unit_container() -> None:
    artifact, cp01, cp02, package = _build()
    report = validator.validate_artifact(artifact, cp01, cp02, package)

    assert report["validation_status"] == builder.PASS_STATUS
    assert report["errors"] == []
    assert len(artifact["learning_units"]) == 24
    assert {row["learning_unit_id"] for row in artifact["learning_units"]} == {
        row["learning_unit_id"] for row in cp02["learning_units"]
    }
    assert artifact["binding_contract"]["new_unit_creation_allowed"] is False
    assert artifact["binding_contract"]["raz_specific_parallel_curriculum_allowed"] is False
    assert artifact["coverage_summary"]["new_learning_unit_count"] == 0
    assert artifact["coverage_summary"]["parallel_curriculum_count"] == 0


def test_cp03_consumes_both_sources_without_changing_admission() -> None:
    artifact, *_ = _build()
    summary = artifact["coverage_summary"]

    assert summary["m11b_reviewed_content_unit_count"] == 23
    assert summary["m11b_reviewed_content_item_count"] == 184
    assert summary["raz_promoted_material_input_count"] == 2
    assert summary["raz_distinct_bound_material_count"] == 2
    assert summary["raz_material_unit_binding_count"] == 3
    assert summary["raz_covered_existing_unit_count"] == 3
    assert artifact["claim_boundaries"]["raz_admission_decision_changed"] is False
    assert artifact["claim_boundaries"]["learner_facing_content_created"] is False


def test_cp03_binds_raz_by_verified_grammar_authority_ref() -> None:
    artifact, *_ = _build()
    by_grammar = {row["grammar_unit_id"]: row for row in artifact["learning_units"]}

    article = by_grammar["GRAMMAR_ARTICLES_BASIC"]["raz_admitted_asset_binding"]
    assert article["material_count"] == 1
    assert article["materials"][0]["grammar_authority_ref"] == "GRAMMAR_ARTICLES_BASIC"
    be = by_grammar["GRAMMAR_BE_VERB_BASIC"]["raz_admitted_asset_binding"]
    pronouns = by_grammar["GRAMMAR_OBJECT_PRONOUNS_BASIC"]["raz_admitted_asset_binding"]
    assert be["materials"][0]["material_id"] == pronouns["materials"][0]["material_id"]


def test_cp03_rejects_raz_parallel_or_unknown_unit() -> None:
    package = _registry_package()
    package["promoted_material_registry"][0]["authority_links"][0]["authority_ref"] = "RAZ_PARALLEL_UNIT_001"
    package["package_sha256"] = deep.sha256_value(
        {key: value for key, value in package.items() if key != "package_sha256"}
    )

    cp01, cp02 = _sources()
    with pytest.raises(builder.UnifiedBindingError, match="parallel_or_unknown_unit_forbidden"):
        builder.build_artifact(cp01, cp02, package)


def test_cp03_rejects_unpromoted_raz_asset() -> None:
    package = _registry_package()
    package["promoted_material_registry"][0]["registry_status"] = "SUPPORT_ONLY"
    package["package_sha256"] = deep.sha256_value(
        {key: value for key, value in package.items() if key != "package_sha256"}
    )

    cp01, cp02 = _sources()
    with pytest.raises(builder.UnifiedBindingError, match="raz_material_not_promoted"):
        builder.build_artifact(cp01, cp02, package)


def test_cp03_validator_rejects_a_25th_or_raz_specific_unit() -> None:
    artifact, cp01, cp02, package = _build()
    tampered = deepcopy(artifact)
    extra = deepcopy(tampered["learning_units"][0])
    extra["learning_unit_id"] = "RAZ_A1V1_UNIT:PARALLEL"
    extra["grammar_unit_id"] = "RAZ_PARALLEL_UNIT_001"
    extra["sequence_index"] = 25
    tampered["learning_units"].append(extra)

    report = validator.validate_artifact(tampered, cp01, cp02, package)
    assert report["validation_status"] == "FAIL"
    assert "output_learning_unit_count_not_24" in report["errors"]
    assert "second_or_missing_unit_identity_detected" in report["errors"]


def test_cp03_is_metadata_only_policy_exempt_builder() -> None:
    assert builder.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert builder.A1FS_CONTENT_POLICY_EXEMPTION
