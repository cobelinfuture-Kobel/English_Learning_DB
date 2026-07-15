#!/usr/bin/env python3
"""Independently validate M11D A1/A1+ system acceptance and closeout."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any

SOURCE_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(SOURCE_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m11d_system_acceptance_closeout as builder  # noqa: E402

PASS_STATUS = builder.PASS_STATUS
DEFAULT_VALIDATION_PATH = builder.DEFAULT_OUTPUT_ROOT / "system_acceptance_validation.json"


def validate(output_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    acceptance: dict[str, Any] = {}
    rebuild_root: Path | None = None
    try:
        root = builder._safe_output_root(output_root)
        acceptance = builder.read_json(root / "system_acceptance.json")
        builder._assert_schema(acceptance)
        builder._safe_scan(acceptance, name="m11d_system_acceptance")

        canonical = acceptance.get("canonical_structural_coverage", {})
        private = acceptance.get("authority_reviewed_private_path", {})
        deferred = acceptance.get("cambridge_ceiling_deferred", {})
        runtime = acceptance.get("runtime_acceptance", {})
        evidence = acceptance.get("evidence_state", {})

        if canonical != {
            "grammar_units": 24,
            "canonical_egp_rows": 109,
            "covered_rows": 109,
            "draft_only_rows": 0,
            "missing_rows": 0,
            "structural_coverage_percent": 100.0,
            "status": "PASS_CANONICAL_A1_A1PLUS_STRUCTURAL_COVERAGE_COMPLETE",
        }:
            errors.append("canonical_structural_coverage_drift")
        if private.get("private_ready_units") != 23 or private.get("private_ready_rows") != 107:
            errors.append("authority_private_path_count_drift")
        if private.get("selectable_items") != 184:
            errors.append("authority_selectable_item_count_drift")
        if private.get("reading_items") != 92 or private.get("writing_items") != 92:
            errors.append("authority_skill_count_drift")
        if private.get("practice_items") != 138 or private.get("assessment_items") != 46:
            errors.append("authority_role_count_drift")
        if deferred.get("grammar_unit_id") != builder.DEFERRED_GRAMMAR_ID:
            errors.append("deferred_grammar_id_drift")
        if deferred.get("canonical_egp_row_count") != 2 or deferred.get("excluded_item_count") != 8:
            errors.append("deferred_row_or_item_count_drift")
        if deferred.get("canonical_egp_mapping_preserved") is not True:
            errors.append("deferred_canonical_mapping_not_preserved")
        if deferred.get("classified_as_missing") is not False:
            errors.append("deferred_ceiling_misclassified_as_missing")
        if private.get("private_ready_rows", 0) + deferred.get("canonical_egp_row_count", 0) != canonical.get("canonical_egp_rows"):
            errors.append("canonical_private_deferred_count_partition_drift")

        if runtime.get("runtime_status") != builder.m11c.RUNTIME_STATUS:
            errors.append("runtime_status_drift")
        if runtime.get("runtime_validation_errors") != 0:
            errors.append("runtime_validation_errors_nonzero")
        if runtime.get("required_health_checks") != 13 or runtime.get("passed_health_checks") != 13:
            errors.append("runtime_health_check_drift")
        if runtime.get("failed_health_checks") != 0:
            errors.append("runtime_health_failures_nonzero")
        if runtime.get("allowed_host") != "127.0.0.1":
            errors.append("runtime_not_localhost_only")
        if runtime.get("m08_attempt_registry_compatible") is not True:
            errors.append("m08_attempt_registry_incompatible")
        if runtime.get("will_items_learner_exposed") is not False:
            errors.append("will_items_learner_exposed")

        expected_evidence = {
            "actual_learner_attempts": 0,
            "actual_learner_evidence_rows": 0,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "real_learner_pilot_completed": False,
            "speaking_real_audio_evidence": "DEFERRED_BY_OPERATOR",
        }
        if evidence != expected_evidence:
            errors.append("evidence_state_false_claim_or_drift")
        if set(acceptance.get("acceptance_checks", [])) != set(builder.ACCEPTANCE_CHECKS):
            errors.append("acceptance_check_set_drift")
        if len(acceptance.get("acceptance_checks", [])) != len(builder.ACCEPTANCE_CHECKS):
            errors.append("acceptance_check_identity_drift")
        if acceptance.get("acceptance_status") != PASS_STATUS:
            errors.append("acceptance_status_drift")
        if acceptance.get("stop_reason") != "NONE":
            errors.append("acceptance_stop_reason_not_none")
        if acceptance.get("next_short_step") != builder.NEXT_SHORT_STEP:
            errors.append("acceptance_next_short_step_drift")
        if acceptance.get("next_phase_entry_condition") != builder.NEXT_PHASE_ENTRY_CONDITION:
            errors.append("next_phase_entry_condition_drift")

        boundaries = acceptance.get("claim_boundaries", {})
        for key in (
            "private_content_included",
            "learner_responses_included",
            "canonical_authority_write",
            "canonical_egp_mapping_changed",
            "public_delivery",
            "production_runtime_enabled",
            "learner_mastery_claimed",
            "retention_confirmed",
            "real_learner_pilot_claimed",
            "a2_content_promoted",
            "audio_or_recording_processed",
            "deferred_ceiling_classified_as_missing",
        ):
            if boundaries.get(key) is not False:
                errors.append(f"acceptance_claim_boundary_drift:{key}")

        rebuild_root = root.parent / f"m11d-validation-rebuild-{uuid.uuid4().hex}"
        rebuilt = builder.build_acceptance(rebuild_root)
        if rebuilt != acceptance:
            errors.append("system_acceptance_not_reproducible")
    except (
        builder.SystemAcceptanceError,
        builder.m10.CoverageRecheckError,
        builder.m11b.AuthorityExceptionError,
        builder.m11c.AuthorityRuntimeError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(str(exc))
    finally:
        if rebuild_root is not None:
            shutil.rmtree(rebuild_root, ignore_errors=True)

    return {
        "task_id": builder.TASK_ID,
        "validation_status": PASS_STATUS if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "canonical_grammar_unit_count": acceptance.get("canonical_structural_coverage", {}).get("grammar_units", 0),
        "canonical_egp_row_count": acceptance.get("canonical_structural_coverage", {}).get("canonical_egp_rows", 0),
        "private_ready_unit_count": acceptance.get("authority_reviewed_private_path", {}).get("private_ready_units", 0),
        "private_ready_row_count": acceptance.get("authority_reviewed_private_path", {}).get("private_ready_rows", 0),
        "selectable_item_count": acceptance.get("authority_reviewed_private_path", {}).get("selectable_items", 0),
        "deferred_unit_count": 1 if acceptance.get("cambridge_ceiling_deferred") else 0,
        "deferred_row_count": acceptance.get("cambridge_ceiling_deferred", {}).get("canonical_egp_row_count", 0),
        "actual_learner_attempt_count": acceptance.get("evidence_state", {}).get("actual_learner_attempts", 0),
        "learner_mastery_claimed": False,
        "canonical_authority_write": False,
        "canonical_egp_mapping_changed": False,
        "public_delivery": False,
        "a2_content_promoted": False,
        "audio_or_recording_processed": False,
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILURE",
        "next_short_step": builder.NEXT_SHORT_STEP if not errors else None,
        "next_phase_entry_condition": builder.NEXT_PHASE_ENTRY_CONDITION if not errors else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=builder.DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--validation-report", type=Path, default=DEFAULT_VALIDATION_PATH)
    args = parser.parse_args(argv)
    result = validate(args.output_root)
    builder.write_json_atomic(args.validation_report, result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
