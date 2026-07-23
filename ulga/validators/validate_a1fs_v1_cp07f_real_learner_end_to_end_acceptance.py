#!/usr/bin/env python3
"""Independently rebuild and validate a CP07F safe acceptance report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import run_a1fs_v1_cp07f_real_learner_end_to_end_acceptance as runner

FAIL_STATUS = "FAIL_CP07F_REAL_LEARNER_END_TO_END_ACCEPTANCE"


class CP07FValidationError(ValueError):
    """Independent CP07F validation error."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise CP07FValidationError(code)


def validate_report(report: Mapping[str, Any], *, manifest_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    rebuilt: dict[str, Any] | None = None
    try:
        runner._safe_scan(report)
        _require(report.get("task_id") == runner.TASK_ID, "task_id_invalid")
        _require(report.get("program_id") == runner.PROGRAM_ID, "program_id_invalid")
        _require(report.get("schema_version") == runner.REPORT_SCHEMA_VERSION, "schema_version_invalid")
        _require(report.get("mode") == "VALIDATE", "mode_invalid")
        origin = report.get("evidence_origin")
        _require(origin in runner.EVIDENCE_ORIGINS, "evidence_origin_invalid")
        expected_status = runner.REAL_STATUS if origin == "REAL_LEARNER" else runner.TEST_STATUS
        _require(report.get("validation_status") == expected_status, "validation_status_invalid")
        _require(report.get("errors") == [], "report_errors_not_empty")
        _require(isinstance(report.get("learner_ref_sha256"), str) and len(report["learner_ref_sha256"]) == 64, "learner_ref_hash_invalid")
        skills = report.get("skill_readback")
        _require(isinstance(skills, list) and len(skills) == 4, "exact_four_skill_readback_required")
        _require(sorted(row.get("skill") for row in skills if isinstance(row, Mapping)) == sorted(runner.SKILLS), "four_skill_readback_partition_invalid")
        aggregate = report.get("aggregate_readback")
        _require(isinstance(aggregate, Mapping), "aggregate_readback_required")
        _require(aggregate.get("required_skill_count") == 4, "required_skill_count_invalid")
        _require(aggregate.get("attempted_skill_count") == 4, "attempted_skill_count_invalid")
        _require(aggregate.get("existing_learning_unit_denominator") == 24, "learning_unit_denominator_invalid")
        attempted_units = aggregate.get("attempted_grammar_unit_count")
        remaining_units = aggregate.get("remaining_unattempted_unit_count")
        _require(isinstance(attempted_units, int) and 1 <= attempted_units <= 24, "attempted_unit_count_invalid")
        _require(remaining_units == 24 - attempted_units, "remaining_unit_count_invalid")
        gate = report.get("acceptance_gate")
        _require(isinstance(gate, Mapping), "acceptance_gate_required")
        required_true = {
            "same_private_learner_across_four_skills",
            "four_skill_resolved_attempts_present",
            "four_skill_pass_evidence_present",
            "four_skill_m8_schedule_present",
            "representative_completed_remediation_path_present",
            "delayed_review_event_present",
            "listening_audio_registered",
            "speaking_consented_recording_registered",
            "a2_a2plus_locked",
        }
        _require(all(gate.get(key) is True for key in required_true), "acceptance_gate_not_closed")
        boundaries = report.get("claim_boundaries")
        _require(isinstance(boundaries, Mapping), "claim_boundaries_required")
        _require(all(value is False for value in boundaries.values()), "claim_boundary_must_remain_false")
        _require(report.get("real_retention_claimed") is False, "real_retention_claim_forbidden")
        if origin == "REAL_LEARNER":
            _require(report.get("real_learner_evidence_captured") is True, "real_evidence_capture_required")
            _require(report.get("real_learner_acceptance_completed") is True, "real_acceptance_required")
            _require(report.get("stop_reason") == "NONE", "real_stop_reason_invalid")
            _require(report.get("next_short_step") == runner.NEXT_SHORT_STEP, "real_next_short_step_invalid")
            _require(gate.get("decision") == "CONTROLLED_LEARNER_RUNTIME_USABLE", "real_decision_invalid")
        else:
            _require(report.get("real_learner_evidence_captured") is False, "fixture_counted_as_real_evidence")
            _require(report.get("real_learner_acceptance_completed") is False, "fixture_counted_as_real_acceptance")
            _require(report.get("stop_reason") == "REAL_LEARNER_FOUR_SKILL_EVIDENCE_REQUIRED", "fixture_stop_reason_invalid")
            _require(report.get("next_short_step") == runner.TASK_ID, "fixture_next_short_step_invalid")
            _require(gate.get("decision") == "TEST_FIXTURE_CONTRACT_ONLY", "fixture_decision_invalid")
        rebuilt = runner.evaluate_manifest(manifest_path)
        _require(dict(report) == rebuilt, "deterministic_rebuild_mismatch")
    except (CP07FValidationError, runner.CP07FAcceptanceError, OSError, KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return {
        "task_id": runner.TASK_ID,
        "schema_version": "a1fs.v1.cp07f.real_learner_acceptance.validation.v1",
        "validation_status": report.get("validation_status") if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        "deterministic_rebuild_matches": not errors and rebuilt == dict(report),
        "evidence_origin": report.get("evidence_origin"),
        "real_learner_acceptance_completed": report.get("real_learner_acceptance_completed") is True and not errors,
        "real_retention_claimed": False,
        "a2_a2plus_status": "LOCKED",
        "stop_reason": report.get("stop_reason") if not errors else "VALIDATION_FAILED",
        "next_short_step": report.get("next_short_step") if not errors else runner.TASK_ID,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--validation-report", type=Path)
    args = parser.parse_args(argv)
    report = runner._read(args.report, "safe_report")
    validation = validate_report(report, manifest_path=args.manifest)
    if args.validation_report:
        runner._write_atomic(args.validation_report, validation)
    print(json.dumps(validation, ensure_ascii=False, sort_keys=True))
    return 0 if validation["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
