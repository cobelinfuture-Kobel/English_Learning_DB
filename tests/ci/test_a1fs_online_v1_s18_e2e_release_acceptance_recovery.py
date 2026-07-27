from __future__ import annotations

import json
from pathlib import Path

from ulga.builders import build_a1fs_online_v1_s18_nonaudio_learner_product_e2e_release_acceptance_recovery as s18
from ulga.validators import validate_a1fs_online_v1_s18_nonaudio_learner_product_e2e_release_acceptance_recovery as validator


def test_s18_operator_lifecycle_reuses_exact_s17_start_stop_status_contract(tmp_path: Path) -> None:
    start = tmp_path / "start.ps1"
    stop = tmp_path / "stop.ps1"
    status = tmp_path / "status.ps1"
    contract = tmp_path / "contract.json"
    start.write_text(
        "A1FS_S17_LOCALHOST_STARTED=PASS PORT_IN_USE PID_FILE_ALREADY_EXISTS "
        "build_a1fs_online_v1_s17_learner_parent_teacher_dashboard_human_review_runtime",
        encoding="utf-8",
    )
    stop.write_text(
        "PID_OWNERSHIP_MISMATCH PORT_STILL_LISTENING A1FS_S17_LOCALHOST_STOPPED=PASS",
        encoding="utf-8",
    )
    status.write_text(
        "PORT_OWNERSHIP_INVALID UNHEALTHY A1FS_S17_LOCALHOST_STATUS=RUNNING",
        encoding="utf-8",
    )
    contract.write_text(
        json.dumps({
            "host": "127.0.0.1",
            "authentication_required": True,
            "csrf_required_for_review_decision": True,
            "external_network_binding_allowed": False,
            "cloudflare_enabled": False,
            "audio_enabled": False,
            "a2_session_enabled": False,
        }),
        encoding="utf-8",
    )

    result = s18._operator_lifecycle_contract({
        "start": start,
        "stop": stop,
        "status": status,
        "contract": contract,
    })

    assert result == {
        "start_script_contract_pass": True,
        "stop_script_contract_pass": True,
        "status_script_contract_pass": True,
        "launch_contract_boundary_pass": True,
    }


def test_s18_safe_validator_allows_recovery_capability_names_but_rejects_private_keys() -> None:
    safe = {
        "e2e_release_acceptance_summary": {
            "authenticated_session_survived_server_restart": True,
            "review_queue_survived_server_restart": True,
            "active_learning_session_survived_server_restart": True,
        },
        "capability_contract": {
            "release_candidate_created": False,
        },
    }
    assert validator._find_exact_private_keys(safe) == set()
    s18.safe_scan(safe)

    private = {
        "nested": [
            {"attempt_id": "private"},
            {"session_id": "private"},
            {"asset_key": "private"},
            {"response_json": {}},
            {"review_queue": []},
        ]
    }
    assert validator._find_exact_private_keys(private) == {
        "attempt_id", "session_id", "asset_key", "response_json", "review_queue",
    }


def test_s18_is_acceptance_only_and_hands_off_to_s19_release_candidate() -> None:
    assert s18.PRODUCT_STATUS == "LOCALHOST_NONAUDIO_PRODUCT_E2E_ACCEPTED_RECOVERY_VERIFIED_NOT_RELEASE_CANDIDATE"
    assert s18.NEXT_SHORT_STEP == "A1FS-ONLINE-V1-S19_LocalhostNoAudioLearnerProductReleaseCandidate"
