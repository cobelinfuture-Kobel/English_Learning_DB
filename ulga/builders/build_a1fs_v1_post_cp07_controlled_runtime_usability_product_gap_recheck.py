#!/usr/bin/env python3
"""Classify post-CP07 controlled runtime usability and remaining product gaps."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import run_a1fs_v1_cp07f_real_learner_end_to_end_acceptance as cp07f

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "READ_ONLY_ACCEPTANCE_AND_PRODUCT_GAP_CLASSIFICATION_WITHOUT_CONTENT_GENERATION_OR_ADMISSION"

TASK_ID = "A1FS-V1-POST_CP07_ControlledRuntimeUsabilityAndRemainingProductGapRecheck"
PROGRAM_ID = cp07f.PROGRAM_ID
SCHEMA_VERSION = "a1fs.v1.post_cp07.controlled_runtime_usability_product_gap_recheck.v1"
PENDING_STATUS = "PASS_POST_CP07_RUNTIME_CONTRACT_READY_REAL_EVIDENCE_PENDING"
USABLE_STATUS = "PASS_POST_CP07_CONTROLLED_RUNTIME_USABLE_PRODUCT_GAPS_REMAIN"
NEXT_REAL_ACCEPTANCE = "A1FS-V1-CP07F_RealLearnerPrivateProductionAcceptance"
NEXT_RETENTION_PILOT = "A1FS-V1-POST_CP07A_RealRetentionAndControlledFamilyPilotEvidence"
DEFAULT_CP07F = cp07f.DEFAULT_SAFE_REPORT
DEFAULT_OUTPUT = Path(".local/a1fs_v1/post_cp07/controlled_runtime_usability_product_gap_recheck.safe.json")
DENOMINATOR_UNITS = cp07f.DENOMINATOR_UNITS

ALLOWED_CP07F_STATUSES = {
    cp07f.PREPARE_STATUS,
    cp07f.TEST_STATUS,
    cp07f.REAL_STATUS,
}

FORBIDDEN_SAFE_KEYS = set(cp07f.FORBIDDEN_SAFE_KEYS) | {
    "manifest_path",
    "private_path",
    "learner_name",
    "guardian_name",
}


class ProductGapError(ValueError):
    """Fail-closed post-CP07 classification error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductGapError(f"cp07f_report_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise ProductGapError("cp07f_report_object_required")
    return value


def safe_scan(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in FORBIDDEN_SAFE_KEYS:
                raise ProductGapError(f"private_key_in_safe_output:{path}.{key}")
            safe_scan(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            safe_scan(child, f"{path}[{index}]")
    elif isinstance(value, str):
        candidate = Path(value)
        if candidate.is_absolute() or (len(value) > 2 and value[1:3] in {":\\", ":/"}):
            raise ProductGapError(f"absolute_path_in_safe_output:{path}")


def _integer(mapping: Mapping[str, Any], key: str) -> int:
    value = mapping.get(key, 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ProductGapError(f"cp07f_nonnegative_integer_required:{key}")
    return value


def _verify_cp07f(report: Mapping[str, Any]) -> tuple[str, Mapping[str, Any], Mapping[str, Any]]:
    if report.get("task_id") != cp07f.TASK_ID:
        raise ProductGapError("cp07f_task_id_invalid")
    if report.get("schema_version") != cp07f.REPORT_SCHEMA_VERSION:
        raise ProductGapError("cp07f_schema_version_invalid")
    status = str(report.get("validation_status") or "")
    if status not in ALLOWED_CP07F_STATUSES:
        raise ProductGapError("cp07f_validation_status_invalid")
    if report.get("a2_a2plus_status") != "LOCKED":
        raise ProductGapError("cp07f_a2_lock_invalid")
    if report.get("errors") not in (None, []):
        raise ProductGapError("cp07f_errors_present")
    aggregate = report.get("aggregate_readback", {})
    gate = report.get("acceptance_gate", {})
    if not isinstance(aggregate, Mapping) or not isinstance(gate, Mapping):
        raise ProductGapError("cp07f_readback_or_gate_invalid")
    return status, aggregate, gate


def build_artifact(cp07f_report: Mapping[str, Any]) -> dict[str, Any]:
    status, aggregate, gate = _verify_cp07f(cp07f_report)

    real_acceptance = (
        status == cp07f.REAL_STATUS
        and cp07f_report.get("evidence_origin") == "REAL_LEARNER"
        and cp07f_report.get("real_learner_evidence_captured") is True
        and cp07f_report.get("real_learner_acceptance_completed") is True
    )
    test_fixture = status == cp07f.TEST_STATUS or cp07f_report.get("evidence_origin") == "TEST_FIXTURE"

    attempted_skill_count = _integer(aggregate, "attempted_skill_count")
    resolved_attempt_count = _integer(aggregate, "resolved_attempt_count")
    distinct_unit_count = _integer(aggregate, "attempted_grammar_unit_count")
    diagnosis_count = _integer(aggregate, "m7_diagnosis_count")
    remediation_count = _integer(aggregate, "completed_remediation_count")
    reassessment_count = _integer(aggregate, "completed_reassessment_count")
    review_event_count = _integer(aggregate, "m8_review_event_count")

    listening_audio = gate.get("listening_audio_registered") is True
    speaking_recording = gate.get("speaking_consented_recording_registered") is True
    four_skill_gate = attempted_skill_count == 4 and resolved_attempt_count >= 4
    lifecycle_gate = (
        diagnosis_count >= 1
        and remediation_count >= 1
        and reassessment_count >= 1
        and review_event_count >= 1
    )

    if real_acceptance and not (
        four_skill_gate and lifecycle_gate and listening_audio and speaking_recording
    ):
        raise ProductGapError("cp07f_real_acceptance_internal_gate_mismatch")
    if test_fixture and real_acceptance:
        raise ProductGapError("test_fixture_cannot_be_real_acceptance")

    gaps: list[dict[str, Any]] = []
    if not real_acceptance:
        gaps.append({
            "gap_id": "REAL_LEARNER_FOUR_SKILL_ACCEPTANCE",
            "gap_class": "BLOCKING_EVIDENCE",
            "evidence_state": "MISSING",
            "blocks_controlled_runtime_usability": True,
        })
        if not listening_audio:
            gaps.append({
                "gap_id": "REAL_LISTENING_AUDIO_AND_ATTEMPT_EVIDENCE",
                "gap_class": "BLOCKING_EVIDENCE",
                "evidence_state": "MISSING",
                "blocks_controlled_runtime_usability": True,
            })
        if not speaking_recording:
            gaps.append({
                "gap_id": "CONSENTED_SPEAKING_RECORDING_AND_HUMAN_REVIEW_EVIDENCE",
                "gap_class": "BLOCKING_EVIDENCE",
                "evidence_state": "MISSING",
                "blocks_controlled_runtime_usability": True,
            })
        if not lifecycle_gate:
            gaps.append({
                "gap_id": "REAL_DIAGNOSIS_REMEDIATION_REASSESSMENT_AND_DELAYED_REVIEW_PATH",
                "gap_class": "BLOCKING_EVIDENCE",
                "evidence_state": "MISSING",
                "blocks_controlled_runtime_usability": True,
            })

    if cp07f_report.get("real_retention_claimed") is not True:
        gaps.append({
            "gap_id": "REAL_RETENTION_LONGITUDINAL_EVIDENCE",
            "gap_class": "PRODUCT_COMPLETION_EVIDENCE",
            "evidence_state": "NOT_PROVEN",
            "blocks_controlled_runtime_usability": False,
        })
    if distinct_unit_count < DENOMINATOR_UNITS:
        gaps.append({
            "gap_id": "FULL_24_UNIT_REAL_ATTEMPT_COVERAGE",
            "gap_class": "PRODUCT_COMPLETION_EVIDENCE",
            "evidence_state": "NOT_PROVEN",
            "observed_unit_count": distinct_unit_count,
            "denominator_unit_count": DENOMINATOR_UNITS,
            "blocks_controlled_runtime_usability": False,
        })
    if cp07f_report.get("claim_boundaries", {}).get("public_delivery_claimed") is not True:
        gaps.append({
            "gap_id": "PUBLIC_DELIVERY_OPERATIONAL_READINESS",
            "gap_class": "RELEASE_READINESS",
            "evidence_state": "NOT_CLAIMED",
            "blocks_controlled_runtime_usability": False,
        })

    controlled_runtime_usable = real_acceptance
    complete_product = False
    validation_status = USABLE_STATUS if controlled_runtime_usable else PENDING_STATUS
    next_short_step = NEXT_RETENTION_PILOT if controlled_runtime_usable else NEXT_REAL_ACCEPTANCE

    artifact = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": validation_status,
        "scope": "A1_A1_PLUS_ONLY",
        "source_identity": {
            "cp07f_task_id": cp07f.TASK_ID,
            "cp07f_schema_version": cp07f.REPORT_SCHEMA_VERSION,
            "cp07f_validation_status": status,
            "cp07f_report_sha256": digest(cp07f_report),
        },
        "mainline_distance_gate": {
            "ultimate_goal": "COMPLETE_A1_A1_PLUS_FOUR_SKILL_LEARNING_SYSTEM",
            "classification": "DIRECT",
            "controlled_runtime_usable": controlled_runtime_usable,
            "complete_product": complete_product,
            "overall_progress_increase_allowed": controlled_runtime_usable,
            "expected_distance_delta": (
                "REAL_FOUR_SKILL_RUNTIME_ACCEPTANCE_PROVEN"
                if controlled_runtime_usable
                else "NO_RUNTIME_USABILITY_CLAIM_UNTIL_REAL_EVIDENCE"
            ),
        },
        "capability_state": {
            "runtime_contract_ready": status in ALLOWED_CP07F_STATUSES,
            "test_fixture_only": test_fixture,
            "real_four_skill_acceptance": real_acceptance,
            "four_skill_attempt_gate_passed": four_skill_gate,
            "diagnosis_remediation_reassessment_review_gate_passed": lifecycle_gate,
            "listening_audio_registered": listening_audio,
            "speaking_consented_recording_registered": speaking_recording,
            "a2_a2plus_locked": True,
            "controlled_runtime_usable": controlled_runtime_usable,
            "complete_product": complete_product,
        },
        "observed_evidence": {
            "attempted_skill_count": attempted_skill_count,
            "resolved_attempt_count": resolved_attempt_count,
            "distinct_grammar_unit_attempted_count": distinct_unit_count,
            "grammar_unit_denominator": DENOMINATOR_UNITS,
            "m7_diagnosis_count": diagnosis_count,
            "completed_remediation_count": remediation_count,
            "completed_reassessment_count": reassessment_count,
            "m8_review_event_count": review_event_count,
        },
        "remaining_product_gaps": gaps,
        "counts": {
            "blocking_gap_count": sum(
                row["blocks_controlled_runtime_usability"] for row in gaps
            ),
            "product_completion_gap_count": sum(
                row["gap_class"] == "PRODUCT_COMPLETION_EVIDENCE" for row in gaps
            ),
            "release_readiness_gap_count": sum(
                row["gap_class"] == "RELEASE_READINESS" for row in gaps
            ),
            "total_gap_count": len(gaps),
        },
        "claim_boundaries": {
            "canonical_content_modified": False,
            "coverage_denominator_modified": False,
            "mastery_or_retention_policy_modified": False,
            "learner_state_modified": False,
            "private_evidence_copied": False,
            "test_fixture_promoted_to_real": False,
            "public_release_claimed": False,
            "a2_unlocked": False,
        },
        "errors": [],
        "stop_reason": "NONE" if controlled_runtime_usable else "REAL_LEARNER_FOUR_SKILL_EVIDENCE_REQUIRED",
        "next_short_step": next_short_step,
    }
    artifact["artifact_sha256"] = digest(artifact)
    safe_scan(artifact)
    return artifact


def write_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cp07f-report", type=Path, default=DEFAULT_CP07F)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    artifact = build_artifact(read_json(args.cp07f_report))
    write_atomic(args.output, artifact)
    print(json.dumps({
        "validation_status": artifact["validation_status"],
        "controlled_runtime_usable": artifact["capability_state"]["controlled_runtime_usable"],
        "complete_product": artifact["capability_state"]["complete_product"],
        "blocking_gap_count": artifact["counts"]["blocking_gap_count"],
        "next_short_step": artifact["next_short_step"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
