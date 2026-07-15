#!/usr/bin/env python3
"""Independently validate the M09 localhost private learning runtime."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SOURCE_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(SOURCE_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m09_private_learning_runtime as builder  # noqa: E402

DEFAULT_VALIDATION_PATH = (
    builder.DEFAULT_OUTPUT_ROOT / "runtime_validation.json"
)


def validate(output_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        root = builder._safe_output_root(output_root)
        manifest = builder.read_json(root / "runtime_manifest.json")
        acceptance = builder.read_json(root / "runtime_acceptance.json")
        stored_health = builder.read_json(root / "runtime_health.json")
        builder._assert_schema(
            "e4s_a1v1_private_runtime_manifest.schema.json", manifest
        )
        builder._assert_schema(
            "e4s_a1v1_private_runtime_acceptance.schema.json", acceptance
        )
        builder._safe_scan(manifest, name="runtime_manifest")
        builder._safe_scan(acceptance, name="runtime_acceptance")
        builder._safe_scan(stored_health, name="runtime_health")

        rebuilt_health = builder.run_health(root)
        if rebuilt_health != stored_health:
            errors.append("runtime_health_not_reproducible")
        expected_acceptance = builder.build_acceptance(manifest, rebuilt_health)
        if expected_acceptance != acceptance:
            errors.append("runtime_acceptance_not_reproducible")

        m07 = builder.read_json(builder.M07_RECEIPT_PATH)
        m08 = builder.read_json(builder.M08_RECEIPT_PATH)
        text_report = builder.read_json(
            root / "text_mode/text_mode_progress_safe_report.json"
        )
        text_validation = builder.read_json(
            root / "text_mode/text_mode_session_validation.json"
        )
        expected_manifest = builder.build_manifest(
            m07,
            m08,
            text_report,
            text_validation,
            port=manifest.get("bind_policy", {}).get(
                "default_port", builder.DEFAULT_PORT
            ),
        )
        if expected_manifest != manifest:
            errors.append("runtime_manifest_not_reproducible")

        expected_hashes = m08.get("artifact_hashes", {})
        actual_hashes = {
            "session_bank_sha256": builder.sha256_file(
                root / "text_mode/text_mode_session_bank.private.json"
            ),
            "learner_safe_payload_sha256": builder.sha256_file(
                root / "text_mode/text_mode_learner_safe_payload.json"
            ),
            "progress_safe_report_sha256": builder.sha256_file(
                root / "text_mode/text_mode_progress_safe_report.json"
            ),
            "validation_sha256": builder.sha256_file(
                root / "text_mode/text_mode_session_validation.json"
            ),
        }
        if actual_hashes != expected_hashes:
            errors.append("m08_runtime_artifact_hash_drift")

        if manifest.get("runtime_status") != builder.RUNTIME_STATUS:
            errors.append("runtime_status_not_pass")
        if acceptance.get("acceptance_status") != builder.ACCEPTANCE_STATUS:
            errors.append("acceptance_status_not_pass")
        if manifest.get("bind_policy", {}).get("allowed_host") != builder.DEFAULT_HOST:
            errors.append("localhost_bind_policy_drift")
        if manifest.get("bind_policy", {}).get("network_submission_enabled") is not False:
            errors.append("network_submission_enabled")
        if manifest.get("bind_policy", {}).get("external_network_dependency") is not False:
            errors.append("external_network_dependency_enabled")

        speaking = manifest.get("skill_runtime_states", {}).get("speaking", {})
        if speaking.get("recording_controls_enabled") is not False:
            errors.append("recording_controls_enabled")
        if speaking.get("real_audio_evidence_state") != "DEFERRED_BY_OPERATOR":
            errors.append("speaking_audio_state_drift")
        listening = manifest.get("skill_runtime_states", {}).get("listening", {})
        if listening.get("new_audio_asset_processing") is not False:
            errors.append("new_listening_audio_processing_claim")

        boundaries = manifest.get("claim_boundaries", {})
        expected_false = (
            "production_runtime_enabled",
            "public_delivery_enabled",
            "canonical_authority_write",
            "persistent_learner_state_service_enabled",
            "actual_learner_evidence_complete",
            "learner_mastery_claimed",
            "retention_confirmed",
            "new_audio_processing_performed",
            "recording_enabled",
            "a2_a2plus_in_scope",
        )
        for key in expected_false:
            if boundaries.get(key) is not False:
                errors.append(f"claim_boundary_not_false:{key}")
        if boundaries.get("private_local_only") is not True:
            errors.append("private_local_only_not_true")

        dashboard = (root / "dashboard/index.html").read_text(
            encoding="utf-8"
        )
        builder._validate_dashboard(dashboard)
        if manifest.get("next_short_step") != builder.NEXT_SHORT_STEP:
            errors.append("next_short_step_drift")
        if acceptance.get("stop_reason") != "NONE":
            errors.append("stop_reason_not_none")
    except (
        builder.PrivateRuntimeError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(str(exc))
        manifest = {}
        acceptance = {}
        stored_health = {}

    return {
        "task_id": builder.TASK_ID,
        "validation_status": (
            builder.ACCEPTANCE_STATUS if not errors else "FAIL"
        ),
        "error_count": len(errors),
        "errors": errors,
        "runtime_status": manifest.get("runtime_status"),
        "available_item_count": manifest.get("text_mode_runtime", {}).get(
            "available_items", 0
        ),
        "reading_item_count": manifest.get("text_mode_runtime", {}).get(
            "reading_items", 0
        ),
        "writing_item_count": manifest.get("text_mode_runtime", {}).get(
            "writing_items", 0
        ),
        "health_check_count": stored_health.get(
            "required_check_count", 0
        ),
        "recording_enabled": False,
        "new_audio_processing_performed": False,
        "actual_learner_evidence_complete": False,
        "learner_mastery_claimed": False,
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILURE",
        "next_short_step": builder.NEXT_SHORT_STEP,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root", type=Path, default=builder.DEFAULT_OUTPUT_ROOT
    )
    parser.add_argument(
        "--validation-report",
        type=Path,
        default=DEFAULT_VALIDATION_PATH,
    )
    args = parser.parse_args(argv)
    result = validate(args.output_root)
    builder.write_json_atomic(args.validation_report, result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["validation_status"] == builder.ACCEPTANCE_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
