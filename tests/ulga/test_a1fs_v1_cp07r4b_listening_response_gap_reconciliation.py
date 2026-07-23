from __future__ import annotations

from copy import deepcopy

from ulga.builders import build_a1fs_v1_cp07r4a_ket_asset_response_media_capability_admission as r4a
from ulga.builders import build_a1fs_v1_cp07r4b_listening_response_gap_reconciliation as builder
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.validators import validate_a1fs_v1_cp07r4b_listening_response_gap_reconciliation as validator


def _source(*, role: str, payload: dict, response_keys: list[str] | None = None) -> dict:
    asset_key = f"KET:LISTENING:{role}:1"
    asset = {
        "asset_id": asset_key,
        "asset_key": asset_key,
        "lesson_id": "KETL-LF-L001",
        "skill": "LISTENING",
        "level": "A1",
        "role": role,
        "payload": deepcopy(payload),
        "content_digest": "1" * 64,
        "release_scope": "PRIVATE_INTERNAL_D0",
    }
    return {
        "task_id": "A1FS-V1-M2_FourSkillAssetBodyConsumerAndQuery",
        "schema_version": "a1fs.v1.m2.four_skill_asset_body_consumer.v1",
        "validation_status": "PASS_A1FS_V1_M2_FOUR_SKILL_ASSET_BODY_CONSUMER_READY",
        "asset_records": [asset],
        "lesson_catalog": [
            {
                "lesson_id": "KETL-LF-L001",
                "lesson_node_id": "LESSON:LISTENING:KETL-LF-L001",
                "skill": "LISTENING",
                "level": "A1",
                "asset_keys": [asset_key],
                "roles": [role],
                "requirement_node_ids": [],
                "release_scope": "PRIVATE_INTERNAL_D0",
            }
        ],
        "counts": {
            "asset_record_count": 1,
            "lesson_count": 1,
            "learning_lesson_count": 1,
            "a2_handoff_lesson_count": 0,
            "cp07r4a_response_contract_count": 1,
            "cp07r4a_response_capture_asset_count": len(response_keys or []),
        },
        "cp07r4_task_id": "A1FS-V1-CP07F-R4_ReferenceAwarePrivateDeliveryConsumer",
        "cp07r4_schema_version": "a1fs.v1.cp07f.r4.reference_aware_private_delivery_consumer.v1",
        "cp07r4_validation_status": "PASS_CP07F_R4_REFERENCE_AWARE_PRIVATE_DELIVERY_CONSUMER_READY",
        "cp07r4a_task_id": r4a.TASK_ID,
        "cp07r4a_schema_version": r4a.SCHEMA_VERSION,
        "cp07r4a_validation_status": r4a.PASS_STATUS,
        "cp07d_stop_reason": "NONE",
        "cp07d_errors": [],
        "cp07d_delivery_contract": {
            "selected_lesson_id": "KETL-LF-L001",
            "selected_skill": "LISTENING",
            "selected_level": "A1",
            "mounted_ket_asset_keys": [asset_key],
            "projected_asset_keys": [],
            "response_capture_asset_keys": list(response_keys or []),
            "listening_audio_asset_keys": [],
            "speaking_recording_asset_keys": [],
            "m6_feature_rubric_compatible": bool(response_keys),
            "m10_private_media_registration_compatible": False,
            "missing_reference_blocks_delivery": False,
            "real_attempt_completed": False,
            "real_media_registered": False,
            "a2_payload_included": False,
        },
        "cp07r4a_capability_admission": {
            "authority": {},
            "response_contracts": [],
            "media_admissions": [],
            "actual_attempt_count": 0,
            "actual_media_registration_count": 0,
            "automatic_speaking_score_enabled": False,
        },
        "cp07r4_capability_gaps": {
            "response_capture_contract_missing": not bool(response_keys),
            "listening_audio_registration_contract_missing": True,
            "speaking_recording_contract_missing": False,
            "optional_context_not_projected": True,
        },
    }


def test_exact_prompt_and_explicit_contract_create_capture_adapter() -> None:
    source = _source(
        role="GDT",
        payload={
            "prompt": "Which animal do you hear?",
            "answer_contract": {
                "scoring_mode": "NORMALIZED_TEXT",
                "accepted_texts": ["cat"],
            },
        },
    )
    artifact = builder.build_reconciliation(source)
    report = validator.validate_artifact(artifact, r4a_consumer=source)
    reconciliation = artifact["cp07r4b_reconciliation"]
    assert report["validation_status"] == builder.PASS_STATUS, report["errors"]
    assert reconciliation["remediation_status"] == "AUTO_REMEDIATED_FROM_EXPLICIT_SOURCE_CONTRACT"
    assert reconciliation["adapter_count"] == 1
    adapter_key = reconciliation["adapter_asset_keys"][0]
    adapter = next(row for row in artifact["asset_records"] if row["asset_key"] == adapter_key)
    assert adapter["role"] == "CHK"
    assert m6.derive_contract(adapter)["capture_enabled"] is True
    assert artifact["asset_records"][0] == source["asset_records"][0]


def test_prompt_only_remains_blocked_and_does_not_create_content() -> None:
    source = _source(role="GDT", payload={"prompt": "Which animal do you hear?"})
    artifact = builder.build_reconciliation(source)
    report = validator.validate_artifact(artifact, r4a_consumer=source)
    assert report["validation_status"] == builder.PASS_STATUS, report["errors"]
    assert report["remediation_status"] == "BLOCKED_EXPLICIT_SCORING_EVIDENCE_REQUIRED"
    assert report["adapter_count"] == 0
    assert report["operator_evidence_required"] is True
    assert artifact["asset_records"] == source["asset_records"]


def test_aud_asset_is_never_used_as_response_adapter_source() -> None:
    source = _source(
        role="AUD",
        payload={
            "prompt": "Which animal do you hear?",
            "answer_contract": {
                "scoring_mode": "NORMALIZED_TEXT",
                "accepted_texts": ["cat"],
            },
        },
    )
    artifact = builder.build_reconciliation(source)
    classification = artifact["cp07r4b_reconciliation"]["safe_gap_classifications"][0]
    assert classification["reason_code"] == "AUD_ASSET_NOT_RESPONSE_ADAPTER_SOURCE"
    assert artifact["cp07r4b_reconciliation"]["adapter_count"] == 0


def test_explicit_capture_disable_is_respected() -> None:
    source = _source(
        role="GDT",
        payload={
            "prompt": "Which animal do you hear?",
            "response_capture_enabled": False,
            "answer_contract": {
                "scoring_mode": "NORMALIZED_TEXT",
                "accepted_texts": ["cat"],
            },
        },
    )
    artifact = builder.build_reconciliation(source)
    classification = artifact["cp07r4b_reconciliation"]["safe_gap_classifications"][0]
    assert classification["reason_code"] == "SOURCE_EXPLICITLY_DISABLES_RESPONSE_CAPTURE"
    assert artifact["cp07r4b_reconciliation"]["adapter_count"] == 0


def test_existing_capture_contract_needs_no_remediation() -> None:
    source = _source(
        role="CHK",
        payload={
            "prompt": "Which animal do you hear?",
            "answer_contract": {
                "scoring_mode": "NORMALIZED_TEXT",
                "accepted_texts": ["cat"],
            },
        },
    )
    key = source["asset_records"][0]["asset_key"]
    source["cp07d_delivery_contract"]["response_capture_asset_keys"] = [key]
    source["cp07d_delivery_contract"]["m6_feature_rubric_compatible"] = True
    source["counts"]["cp07r4a_response_capture_asset_count"] = 1
    source["cp07r4_capability_gaps"]["response_capture_contract_missing"] = False
    artifact = builder.build_reconciliation(source)
    assert artifact["cp07r4b_reconciliation"]["remediation_status"] == "NO_REMEDIATION_NEEDED"
    assert artifact["cp07r4b_reconciliation"]["adapter_count"] == 0


def test_validator_rejects_adapter_contract_tamper() -> None:
    source = _source(
        role="GDT",
        payload={
            "prompt": "Which animal do you hear?",
            "answer_contract": {
                "scoring_mode": "NORMALIZED_TEXT",
                "accepted_texts": ["cat"],
            },
        },
    )
    artifact = builder.build_reconciliation(source)
    tampered = deepcopy(artifact)
    adapter_key = tampered["cp07r4b_reconciliation"]["adapter_asset_keys"][0]
    adapter = next(row for row in tampered["asset_records"] if row["asset_key"] == adapter_key)
    adapter["payload"]["private_scoring_contract"]["accepted_texts"] = ["dog"]
    report = validator.validate_artifact(tampered, r4a_consumer=source)
    assert report["validation_status"] != builder.PASS_STATUS
    assert any(error.startswith("adapter_contract_not_exact_copy:") for error in report["errors"])
