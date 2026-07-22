from __future__ import annotations

from copy import deepcopy

from ulga.builders import build_a1fs_v1_cp03_unified_existing_24_unit_binding as cp03
from ulga.builders import build_a1fs_v1_cp04_unified_content_exercise_scene_candidates as cp04
from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_ai_acl_v1_s05_material_registry as registry
from ulga.builders import run_a1fs_v1_cp04r_private_production as runner
from ulga.validators import validate_a1fs_v1_cp04r_real_private_candidate_build as validator


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


def _build() -> tuple[dict, dict, dict]:
    cp01_artifact = cp03._read(cp03.CP01_PATH)
    cp02_artifact = cp03._read(cp03.CP02_PATH)
    cp03_artifact = cp03.build_artifact(
        cp01_artifact, cp02_artifact, _registry_package()
    )
    cp04_artifact = cp04.build_artifact(cp03_artifact)
    readback = runner.build_readback(
        cp03_artifact, cp04_artifact, execution_mode="SYNTHETIC_TEST"
    )
    return readback, cp03_artifact, cp04_artifact


def test_cp04r_emits_exact_24_unit_count_readback() -> None:
    readback, cp03_artifact, cp04_artifact = _build()
    report = validator.validate_artifact(readback, cp03_artifact, cp04_artifact)

    assert report["validation_status"] == runner.PASS_STATUS
    assert report["errors"] == []
    assert len(readback["unit_count_readback"]) == 24
    assert readback["coverage_summary"]["new_learning_unit_count"] == 0
    assert readback["coverage_summary"]["raz_promoted_material_input_count"] == 2
    assert readback["coverage_summary"]["raz_distinct_bound_material_count"] == 2
    assert readback["coverage_summary"]["raz_material_unit_binding_count"] == 3
    assert readback["coverage_summary"]["content_candidate_count"] == 187
    assert readback["coverage_summary"]["exercise_candidate_count"] == 187


def test_cp04r_readback_is_deterministic() -> None:
    readback, cp03_artifact, cp04_artifact = _build()
    repeated = runner.build_readback(
        cp03_artifact, cp04_artifact, execution_mode="SYNTHETIC_TEST"
    )
    assert readback == repeated


def test_cp04r_validator_rejects_count_tampering() -> None:
    readback, cp03_artifact, cp04_artifact = _build()
    readback["coverage_summary"]["raz_material_unit_binding_count"] += 1
    readback["unit_count_readback"][0]["content_candidate_count"] += 1

    report = validator.validate_artifact(readback, cp03_artifact, cp04_artifact)
    assert report["validation_status"] == "FAIL"
    assert "coverage_summary_not_reconciled" in report["errors"]
    assert "unit_count_readback_not_reconciled" in report["errors"]


def test_cp04r_validator_rejects_private_content_leak() -> None:
    readback, cp03_artifact, cp04_artifact = _build()
    tampered = deepcopy(readback)
    tampered["unit_count_readback"][0]["prompt"] = "forbidden"

    report = validator.validate_artifact(tampered, cp03_artifact, cp04_artifact)
    assert report["validation_status"] == "FAIL"
    assert "private_or_learner_content_leak:prompt" in report["errors"]


def test_cp04r_fails_closed_for_invalid_execution_mode() -> None:
    _, cp03_artifact, cp04_artifact = _build()
    try:
        runner.build_readback(
            cp03_artifact, cp04_artifact, execution_mode="UNVERIFIED"
        )
    except runner.PrivateProductionRunError as exc:
        assert str(exc) == "execution_mode_invalid"
    else:
        raise AssertionError("invalid execution mode must fail closed")


def test_cp04r_is_metadata_only_policy_exempt_builder() -> None:
    assert runner.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert runner.A1FS_CONTENT_POLICY_EXEMPTION
