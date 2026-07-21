from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import jsonschema
import pytest

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as builder
from ulga.validators import validate_a1fs_v1_policy_bound_content_artifact as validator


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY = json.loads(
    (REPO_ROOT / "ulga/contracts/a1fs_v1_canonical_content_production_policy.json").read_text(
        encoding="utf-8"
    )
)
SCHEMA = json.loads(
    (REPO_ROOT / "ulga/schemas/a1fs_v1_policy_bound_content_artifact.schema.json").read_text(
        encoding="utf-8"
    )
)


def receipt(name: str = "semantic-validator") -> dict:
    return {
        "validator_id": name,
        "status": "PASS",
        "receipt_sha256": builder.digest({"validator": name, "status": "PASS"}),
    }


def candidate() -> dict:
    return builder.build_candidate(
        payload={
            "content_id": "CONTENT_A1_HOME_0001",
            "sentence": "The red ball is under the chair.",
        },
        producer_id="test-candidate-builder",
        level_scope=["A1"],
        source_bindings={
            "authority_query_sha256": builder.digest({"query": "A1 home location"}),
        },
        policy=POLICY,
    )


def approved() -> dict:
    return builder.admit_candidate(
        candidate(),
        validation_receipts=[
            receipt("schema-validator"),
            receipt("level-validator"),
            receipt("semantic-validator"),
            receipt("answerability-validator"),
        ],
        decision_ref="AUTHORITY_DECISION:CONTENT_A1_HOME_0001",
        producer_id="test-admission-builder",
        policy=POLICY,
    )


def projection(skill: str = "SPEAKING") -> dict:
    return builder.build_four_skill_projection(
        approved(),
        skill=skill,
        projection_payload={
            "skill": skill,
            "prompt": "Look at the picture. Where is the red ball?",
            "response_mode": "spoken_response",
            "support_level": "S0_INDEPENDENT",
            "initiative_level": "INDEPENDENT_INITIATION",
            "scoring_contract": {
                "scoring_mode": "FEATURE_RUBRIC",
                "required_features": ["ball", "under", "chair"],
            },
            "evidence_level": "E3_INDEPENDENT_PRODUCTION",
            "source_bindings": {
                "content_id": "CONTENT_A1_HOME_0001",
            },
            "content_identity": {
                "content_id": "CONTENT_A1_HOME_0001",
                "revision": 1,
            },
        },
        producer_id=f"test-{skill.lower()}-projection-builder",
        policy=POLICY,
    )


def test_complete_candidate_approval_projection_excel_chain_is_policy_bound():
    candidate_artifact = candidate()
    approved_artifact = approved()
    projection_artifact = projection()
    excel_manifest = builder.build_excel_reference_manifest(
        projection_artifact,
        workbook_filename="a1fs_v1_speaking_reference.xlsx",
        workbook_sha256=builder.digest({"workbook": "fixture"}),
        producer_id="test-excel-exporter",
        policy=POLICY,
    )

    for artifact in (
        candidate_artifact,
        approved_artifact,
        projection_artifact,
        excel_manifest,
    ):
        report = validator.validate_artifact(artifact, policy=POLICY)
        assert report["validation_status"] == validator.PASS_STATUS, report["errors"]
        jsonschema.validate(artifact, SCHEMA)

    assert candidate_artifact["learner_facing"] is False
    assert approved_artifact["learner_facing"] is False
    assert projection_artifact["learner_facing"] is True
    assert excel_manifest["payload"]["role"] == "DERIVED_REFERENCE_ONLY"
    assert excel_manifest["payload"]["export_direction"] == "JSON_TO_EXCEL_ONLY"
    assert excel_manifest["payload"]["canonical_writeback_allowed"] is False


def test_all_four_skill_projection_roles_are_supported():
    for skill in ("LISTENING", "SPEAKING", "READING", "WRITING"):
        artifact = projection(skill)
        report = validator.validate_artifact(artifact, policy=POLICY)
        assert report["validation_status"] == validator.PASS_STATUS, (skill, report["errors"])


def test_candidate_cannot_be_learner_facing():
    tampered = candidate()
    tampered["learner_facing"] = True
    tampered["artifact_sha256"] = builder.digest(
        {key: value for key, value in tampered.items() if key != "artifact_sha256"}
    )
    report = validator.validate_artifact(tampered, policy=POLICY)
    assert "candidate_learner_facing_forbidden" in report["errors"]


def test_approval_requires_all_validation_receipts_to_pass():
    with pytest.raises(
        builder.ContentPolicyBuildError,
        match="validation_receipt_not_pass",
    ):
        builder.admit_candidate(
            candidate(),
            validation_receipts=[
                {
                    "validator_id": "semantic-validator",
                    "status": "FAIL",
                    "receipt_sha256": builder.digest({"status": "FAIL"}),
                }
            ],
            decision_ref="AUTHORITY_DECISION:FAIL",
            producer_id="test-admission-builder",
            policy=POLICY,
        )


def test_projection_cannot_consume_candidate_json():
    with pytest.raises(
        builder.ContentPolicyBuildError,
        match="illegal_source_artifact_role",
    ):
        builder.build_four_skill_projection(
            candidate(),
            skill="READING",
            projection_payload={
                "skill": "READING",
                "prompt": "Read.",
                "response_mode": "short_text",
                "support_level": "S0_INDEPENDENT",
                "initiative_level": "INDEPENDENT_INITIATION",
                "scoring_contract": {},
                "evidence_level": "E3_INDEPENDENT_PRODUCTION",
                "source_bindings": {},
                "content_identity": {},
            },
            producer_id="illegal-builder",
            policy=POLICY,
        )


def test_projection_requires_the_full_skill_contract():
    payload = projection()["payload"]
    payload.pop("scoring_contract")
    with pytest.raises(
        builder.ContentPolicyBuildError,
        match="projection_required_fields_missing",
    ):
        builder.build_four_skill_projection(
            approved(),
            skill="SPEAKING",
            projection_payload=payload,
            producer_id="broken-projection-builder",
            policy=POLICY,
        )


def test_media_manifest_requires_scene_consistency_pass():
    source = approved()
    with pytest.raises(
        builder.ContentPolicyBuildError,
        match="image_scene_consistency_pass_required",
    ):
        builder.build_approved_media_manifest(
            source,
            media_payload={
                "scene_contract_sha256": builder.digest({"scene": 1}),
                "image_sha256": builder.digest({"image": 1}),
                "image_scene_consistency_status": "FAIL",
            },
            scene_consistency_receipt=receipt("scene-consistency-validator"),
            producer_id="test-media-builder",
            policy=POLICY,
        )

    media = builder.build_approved_media_manifest(
        source,
        media_payload={
            "scene_contract_sha256": builder.digest({"scene": 1}),
            "image_sha256": builder.digest({"image": 1}),
            "image_scene_consistency_status": "IMAGE_SCENE_CONSISTENCY_PASS",
        },
        scene_consistency_receipt=receipt("scene-consistency-validator"),
        producer_id="test-media-builder",
        policy=POLICY,
    )
    report = validator.validate_artifact(media, policy=POLICY)
    assert report["validation_status"] == validator.PASS_STATUS, report["errors"]


def test_excel_manifest_cannot_be_created_from_candidate_json():
    with pytest.raises(
        builder.ContentPolicyBuildError,
        match="excel_source_must_be_approved_json",
    ):
        builder.build_excel_reference_manifest(
            candidate(),
            workbook_filename="candidate.xlsx",
            workbook_sha256=builder.digest({"workbook": "candidate"}),
            producer_id="illegal-excel-exporter",
            policy=POLICY,
        )


def test_excel_writeback_tampering_fails_closed():
    artifact = builder.build_excel_reference_manifest(
        approved(),
        workbook_filename="approved_reference.xlsx",
        workbook_sha256=builder.digest({"workbook": "approved"}),
        producer_id="test-excel-exporter",
        policy=POLICY,
    )
    artifact["payload"]["canonical_writeback_allowed"] = True
    artifact["artifact_sha256"] = builder.digest(
        {key: value for key, value in artifact.items() if key != "artifact_sha256"}
    )
    report = validator.validate_artifact(artifact, policy=POLICY)
    assert "excel_writeback_forbidden" in report["errors"]


def test_payload_tampering_breaks_artifact_identity():
    artifact = approved()
    artifact["payload"]["sentence"] = "Tampered."
    report = validator.validate_artifact(artifact, policy=POLICY)
    assert "artifact_sha256_mismatch" in report["errors"]


def test_policy_hash_drift_invalidates_old_binding():
    artifact = candidate()
    changed_policy = deepcopy(POLICY)
    changed_policy["excel"]["canonical_writeback_allowed"] = True
    report = validator.validate_artifact(artifact, policy=changed_policy)
    assert "content_governance_binding_mismatch" in report["errors"]


def test_a2_scope_is_rejected_by_builder_and_validator():
    with pytest.raises(
        builder.ContentPolicyBuildError,
        match="level_scope_outside_a1_a1plus",
    ):
        builder.build_candidate(
            payload={"content_id": "A2"},
            producer_id="test-builder",
            level_scope=["A2"],
            source_bindings={"authority": "fixture"},
            policy=POLICY,
        )

    artifact = candidate()
    artifact["level_scope"] = ["A2"]
    artifact["artifact_sha256"] = builder.digest(
        {key: value for key, value in artifact.items() if key != "artifact_sha256"}
    )
    report = validator.validate_artifact(artifact, policy=POLICY)
    assert "level_scope_invalid" in report["errors"]
