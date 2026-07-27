from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.artifacts.a1fs_artifact_authority import DEFAULT_MANIFEST
from ulga.runners import materialize_a1fs_online_v1 as authority_runner
from ulga.runners import run_a1fs_s18_s19_with_current_bootstrap_validation as runtime_fix


def _s17_bootstrap() -> dict:
    units = []
    for sequence_index in range(1, 25):
        units.append({
            "sequence_index": sequence_index,
            "lanes": [
                {"skill": "READING", "asset_count": 4},
                {"skill": "WRITING", "asset_count": 4},
                {"skill": "SPEAKING", "asset_count": 3},
            ],
        })
    return {
        "task_id": runtime_fix.s18.s17.TASK_ID,
        "schema_version": runtime_fix.s18.s17.SCHEMA_VERSION,
        "validation_status": runtime_fix.s18.s17.PASS_STATUS,
        "product_status": runtime_fix.s18.s17.PRODUCT_STATUS,
        "release_profile": runtime_fix.s18.s17.RELEASE_PROFILE,
        "audio_enabled": False,
        "speaking_capture_enabled": False,
        "unit_count": 24,
        "units": units,
        "learner_product_semantics": {
            "canonical_m7_mastery_connected": True,
            "canonical_m7_remediation_connected": True,
            "canonical_m7_reassessment_connected": True,
            "canonical_m8_review_schedule_connected": True,
            "learner_dashboard_connected": True,
            "parent_dashboard_connected": True,
            "teacher_dashboard_connected": True,
            "human_review_queue_connected": True,
            "role_based_identity_authorization_claimed": False,
            "a2_unlock_enabled": False,
        },
    }


def test_current_s17_bootstrap_reuses_legacy_structural_denominator_gate() -> None:
    assert runtime_fix.validate_current_s17_bootstrap(_s17_bootstrap()) == {
        "unit_count": 24,
        "lesson_count": 72,
        "asset_count": 264,
    }


def test_current_bootstrap_validation_rejects_obsolete_identity_and_boundary_drift() -> None:
    obsolete = _s17_bootstrap()
    obsolete["task_id"] = runtime_fix._s10.s09.TASK_ID
    with pytest.raises(runtime_fix.s18.E2ERecoveryError, match="current_s17_identity"):
        runtime_fix.validate_current_s17_bootstrap(obsolete)

    audio = _s17_bootstrap()
    audio["audio_enabled"] = True
    with pytest.raises(runtime_fix.s18.E2ERecoveryError, match="current_s17_identity"):
        runtime_fix.validate_current_s17_bootstrap(audio)

    a2 = _s17_bootstrap()
    a2["learner_product_semantics"]["a2_unlock_enabled"] = True
    with pytest.raises(runtime_fix.s18.E2ERecoveryError, match="current_s17_identity"):
        runtime_fix.validate_current_s17_bootstrap(a2)


def test_current_bootstrap_validation_rejects_runtime_denominator_drift() -> None:
    bootstrap = _s17_bootstrap()
    bootstrap["units"][0]["lanes"][0]["asset_count"] = 5
    with pytest.raises(runtime_fix.s18.E2ERecoveryError, match="current_s17_structure"):
        runtime_fix.validate_current_s17_bootstrap(bootstrap)


def test_s18_and_s19_authority_commands_use_the_same_governed_runtime_fix() -> None:
    manifest = authority_runner._load_effective_manifest(DEFAULT_MANIFEST)
    for artifact_id, stage in (("S18_SAFE", "s18"), ("S19_SAFE", "s19")):
        entry = manifest["artifacts"][artifact_id]
        command = entry["command"]
        assert command[1:4] == [
            "-m",
            "ulga.runners.run_a1fs_s18_s19_with_current_bootstrap_validation",
            stage,
        ]
        assert "ulga/runners/run_a1fs_s18_s19_with_current_bootstrap_validation.py" in entry["repository_inputs"]


def test_activation_patches_only_the_shared_legacy_bootstrap_helper() -> None:
    original = runtime_fix._s10._validate_bootstrap
    runtime_fix.activate_current_bootstrap_validation()
    try:
        assert runtime_fix._s10._validate_bootstrap is runtime_fix.validate_current_s17_bootstrap
        assert runtime_fix.validate_current_s17_bootstrap(_s17_bootstrap())["asset_count"] == 264
    finally:
        runtime_fix._s10._validate_bootstrap = original


def test_runtime_fix_declares_non_content_producer_governance() -> None:
    assert runtime_fix.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert runtime_fix.A1FS_CONTENT_POLICY_EXEMPTION
