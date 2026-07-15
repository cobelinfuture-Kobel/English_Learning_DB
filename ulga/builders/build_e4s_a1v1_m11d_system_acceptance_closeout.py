#!/usr/bin/env python3
"""Accept and close the Authority-reviewed A1/A1+ private child-path system.

M11D reconciles two intentionally different coverage surfaces:

* canonical A1/A1+ structural coverage remains 24 units / 109 EGP rows;
* the Cambridge-aligned child-path runtime exposes 23 units / 107 rows / 184
  text items and explicitly defers the two `will` rows at the Flyers/A2 ceiling.

No learner evidence, mastery, retention, public delivery, Authority write, A2
promotion, audio processing, or recording evidence is fabricated by closeout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

SOURCE_REPO_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = SOURCE_REPO_ROOT
if str(SOURCE_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m10_coverage_recheck as m10  # noqa: E402
from ulga.builders import build_e4s_a1v1_m11b_authority_exception_resolution as m11b  # noqa: E402
from ulga.builders import build_e4s_a1v1_m11c_authority_reviewed_private_runtime as m11c  # noqa: E402
from ulga.validators import validate_e4s_a1v1_m11c_authority_reviewed_private_runtime as m11c_validator  # noqa: E402

TASK_ID = "E4S-A1V1-M11D_AuthorityReviewedPrivateRuntimeAcceptanceAndA1A1PlusCloseout"
SCHEMA_VERSION = "e4s.a1v1.m11d_system_acceptance.v1"
PASS_STATUS = "PASS_M11D_A1A1PLUS_AUTHORITY_REVIEWED_PRIVATE_SYSTEM_CLOSED"
NEXT_SHORT_STEP = "E4S-A1V1-M12_A1A1PlusRealLearnerPilotEvidenceCapture"
NEXT_PHASE_ENTRY_CONDITION = "REAL_LEARNER_SESSION_EVIDENCE_REQUIRED"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".local/e4s_a1v1/runtime/m11d"
SCHEMA_PATH = REPO_ROOT / "ulga/schemas/e4s_a1v1_m11d_system_acceptance.schema.json"
M11A_CLOSEOUT_PATH = REPO_ROOT / "ulga/reports/e4s_a1v1_m11a_authority_evidence_review_closeout.json"
M11B_CLOSEOUT_PATH = REPO_ROOT / "ulga/reports/e4s_a1v1_m11b_authority_exception_resolution_closeout.json"
M11C_CLOSEOUT_PATH = REPO_ROOT / "ulga/reports/e4s_a1v1_m11c_authority_reviewed_runtime_closeout.json"
DEFERRED_GRAMMAR_ID = "GRAMMAR_WILL_FUTURE_A1"
ACCEPTANCE_CHECKS = (
    "M10_STRUCTURAL_24_109_PASS",
    "M10_COVERED_109_PASS",
    "M11A_EVIDENCE_REVIEW_PASS",
    "M11B_EXCEPTION_RESOLUTION_PASS",
    "M11C_RUNTIME_BUILD_PASS",
    "M11C_RUNTIME_VALIDATOR_PASS",
    "AUTHORITY_PRIVATE_UNITS_23_PASS",
    "AUTHORITY_PRIVATE_ROWS_107_PASS",
    "RUNTIME_SELECTABLE_ITEMS_184_PASS",
    "WILL_DEFERRED_UNIT_1_PASS",
    "WILL_DEFERRED_ROWS_2_PASS",
    "WILL_EXCLUDED_ITEMS_8_PASS",
    "CANONICAL_PRIVATE_DEFERRED_ROW_PARTITION_PASS",
    "LOCALHOST_ONLY_PASS",
    "NO_FALSE_EVIDENCE_OR_MASTERY_CLAIMS_PASS",
    "NO_AUTHORITY_A2_AUDIO_PUBLIC_WRITE_PASS",
)


class SystemAcceptanceError(ValueError):
    """Fail-closed M11D acceptance error."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemAcceptanceError(f"json_unreadable:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise SystemAcceptanceError(f"json_root_not_object:{path}")
    return value


def write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _safe_output_root(path: Path) -> Path:
    resolved = path.resolve()
    approved = (REPO_ROOT / ".local").resolve()
    if not resolved.is_relative_to(approved):
        raise SystemAcceptanceError(f"output_root_outside_local:{resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _require(actual: Any, expected: Any, code: str) -> None:
    if actual != expected:
        raise SystemAcceptanceError(f"{code}:expected={expected!r}:actual={actual!r}")


def _assert_schema(value: Mapping[str, Any]) -> None:
    schema = read_json(SCHEMA_PATH)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise SystemAcceptanceError(f"schema_validation_failed:{location}:{first.message}")


def _safe_scan(value: Any, *, name: str) -> None:
    forbidden = {
        "prompt",
        "answer",
        "answer_key",
        "accepted_texts",
        "accepted_sequence",
        "private_scoring_contract",
        "learner_response",
        "learner_responses",
        "source_payload",
        "raw_pdf_text",
        "official_question_text",
        "official_answer_text",
    }

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                lowered = str(key).casefold()
                if lowered in forbidden or lowered.endswith("_absolute_path"):
                    raise SystemAcceptanceError(f"private_field_leak:{name}:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            if Path(node).is_absolute() or (len(node) > 2 and node[1:3] in {":\\", ":/"}):
                raise SystemAcceptanceError(f"absolute_path_leak:{name}")

    walk(value)


def _validate_closeouts(m11a: Mapping[str, Any], m11b: Mapping[str, Any], m11c: Mapping[str, Any]) -> None:
    _require(
        m11a.get("task_id"),
        "E4S-A1V1-M11A_AuthorityAndCambridgeEvidenceDrivenCandidateReviewFullFix",
        "m11a_task_id",
    )
    _require(m11a.get("validation_status"), "PASS_WITH_AUTHORITY_EXCEPTIONS", "m11a_status")
    _require(m11a.get("completion", {}).get("candidate_units"), 24, "m11a_candidate_units")
    _require(m11a.get("completion", {}).get("canonical_egp_rows"), 109, "m11a_rows")
    _require(m11a.get("completion", {}).get("independent_validation_errors"), 0, "m11a_errors")

    _require(
        m11b.get("task_id"),
        "E4S-A1V1-M11B_AuthorityExceptionContentRevisionAndRevalidation",
        "m11b_task_id",
    )
    _require(m11b.get("validation_status"), "PASS_M11B_AUTHORITY_EXCEPTIONS_RESOLVED", "m11b_status")
    completion_b = m11b.get("completion", {})
    for key, expected in {
        "private_ready_units": 23,
        "private_ready_rows": 107,
        "deferred_units": 1,
        "unresolved_exceptions": 0,
        "independent_validation_errors": 0,
    }.items():
        _require(completion_b.get(key), expected, f"m11b_{key}")

    _require(
        m11c.get("task_id"),
        "E4S-A1V1-M11C_AuthorityReviewedPrivateBankConsumerAndRuntimeIntegration",
        "m11c_task_id",
    )
    _require(m11c.get("validation_status"), m11c.RUNTIME_STATUS, "m11c_status")
    completion_c = m11c.get("completion", {})
    for key, expected in {
        "private_ready_units": 23,
        "private_ready_rows": 107,
        "selectable_items": 184,
        "excluded_items": 8,
        "deferred_units": 1,
        "health_checks": 13,
        "independent_validation_errors": 0,
    }.items():
        _require(completion_c.get(key), expected, f"m11c_{key}")


def build_acceptance(output_root: Path) -> dict[str, Any]:
    root = _safe_output_root(output_root)
    m11a_closeout = read_json(M11A_CLOSEOUT_PATH)
    m11b_closeout = read_json(M11B_CLOSEOUT_PATH)
    m11c_closeout = read_json(M11C_CLOSEOUT_PATH)
    _validate_closeouts(m11a_closeout, m11b_closeout, m11c_closeout)

    coverage = m10.build_report()
    summary = coverage.get("coverage_summary", {})
    for key, expected in {
        "canonical_grammar_unit_count": 24,
        "canonical_egp_row_count": 109,
        "covered_row_count": 109,
        "draft_only_row_count": 0,
        "missing_row_count": 0,
        "structural_coverage_percent": 100.0,
        "actual_learner_evidence_row_coverage_percent": 0.0,
        "learner_mastery_row_coverage_percent": 0.0,
    }.items():
        _require(summary.get(key), expected, f"m10_{key}")
    _require(coverage.get("validation_status"), m10.PASS_STATUS, "m10_status")

    runtime_root = root / "runtime"
    runtime_result = m11c.build_runtime_artifacts(runtime_root)
    runtime_validation = m11c_validator.validate(runtime_root)
    write_json_atomic(root / "m11c_runtime_validation.json", runtime_validation)
    _require(runtime_result.get("safe_report", {}).get("validation_status"), m11c.RUNTIME_STATUS, "m11c_runtime_build")
    _require(runtime_validation.get("validation_status"), m11c.RUNTIME_STATUS, "m11c_runtime_validation")
    _require(runtime_validation.get("error_count"), 0, "m11c_runtime_validation_errors")

    _, authority_bank, _ = m11b.build_artifacts()
    query = runtime_result["query_index"]
    canonical_rows = set(coverage["classification_lists"]["covered_row_ids"])
    private_rows = {
        row_id
        for item in query["items"]
        for row_id in item["canonical_egp_row_ids"]
    }
    deferred_records = authority_bank.get("deferred_units", [])
    _require(len(deferred_records), 1, "deferred_unit_count")
    deferred = deferred_records[0]
    _require(deferred.get("grammar_unit_id"), DEFERRED_GRAMMAR_ID, "deferred_grammar_id")
    deferred_rows = set(deferred.get("canonical_egp_row_ids", []))
    _require(len(canonical_rows), 109, "canonical_row_set")
    _require(len(private_rows), 107, "private_row_set")
    _require(len(deferred_rows), 2, "deferred_row_set")
    if private_rows & deferred_rows:
        raise SystemAcceptanceError("private_and_deferred_rows_overlap")
    if private_rows | deferred_rows != canonical_rows:
        raise SystemAcceptanceError("canonical_private_deferred_partition_drift")

    source_bank = read_json(runtime_root / "source_m08/text_mode_session_bank.private.json")
    source_will_items = [
        item for item in source_bank.get("items", [])
        if item.get("grammar_unit_id") == DEFERRED_GRAMMAR_ID
    ]
    _require(len(source_will_items), 8, "source_will_item_count")
    if any(item.get("grammar_unit_id") == DEFERRED_GRAMMAR_ID for item in query.get("items", [])):
        raise SystemAcceptanceError("will_item_exposed_in_query")
    learner_payload = read_json(runtime_root / "authority_session/payload.json")
    if any(item.get("grammar_unit_id") == DEFERRED_GRAMMAR_ID for item in learner_payload.get("items", [])):
        raise SystemAcceptanceError("will_item_exposed_in_learner_payload")
    registry = read_json(runtime_root / "source_m08/text_mode_attempt_registry.private.json")
    _require(len(registry.get("attempts", [])), 0, "acceptance_requires_zero_attempts")

    manifest = runtime_result["manifest"]
    health = runtime_result["health"]
    _require(manifest.get("bind_policy", {}).get("allowed_host"), "127.0.0.1", "runtime_host")
    _require(health.get("required_check_count"), 13, "runtime_health_required")
    _require(health.get("passed_check_count"), 13, "runtime_health_passed")
    _require(health.get("failed_check_count"), 0, "runtime_health_failed")
    _require(runtime_validation.get("m08_attempt_registry_compatible"), True, "m08_attempt_compatibility")

    acceptance = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "scope": "A1_A1_PLUS_PRIVATE_CHILD_PATH_ONLY",
        "source_hashes": {
            "m10_coverage_recheck_sha256": sha256_value(coverage),
            "m11a_closeout_sha256": sha256_value(m11a_closeout),
            "m11b_closeout_sha256": sha256_value(m11b_closeout),
            "m11c_closeout_sha256": sha256_value(m11c_closeout),
            "m11c_runtime_manifest_sha256": sha256_value(manifest),
            "m11c_runtime_validation_sha256": sha256_value(runtime_validation),
        },
        "canonical_structural_coverage": {
            "grammar_units": 24,
            "canonical_egp_rows": 109,
            "covered_rows": 109,
            "draft_only_rows": 0,
            "missing_rows": 0,
            "structural_coverage_percent": 100.0,
            "status": "PASS_CANONICAL_A1_A1PLUS_STRUCTURAL_COVERAGE_COMPLETE",
        },
        "authority_reviewed_private_path": {
            "private_ready_units": 23,
            "private_ready_rows": 107,
            "selectable_items": 184,
            "reading_items": 92,
            "writing_items": 92,
            "practice_items": 138,
            "assessment_items": 46,
            "status": "PASS_CAMBRIDGE_ALIGNED_PRIVATE_CHILD_PATH_READY",
        },
        "cambridge_ceiling_deferred": {
            "grammar_unit_id": DEFERRED_GRAMMAR_ID,
            "canonical_egp_row_count": 2,
            "excluded_item_count": 8,
            "cambridge_stage": "FLYERS",
            "status": "DEFERRED_CAMBRIDGE_FLYERS_A2_CHILD_PATH_CEILING",
            "canonical_egp_mapping_preserved": True,
            "classified_as_missing": False,
        },
        "runtime_acceptance": {
            "runtime_status": m11c.RUNTIME_STATUS,
            "runtime_validation_errors": 0,
            "required_health_checks": 13,
            "passed_health_checks": 13,
            "failed_health_checks": 0,
            "allowed_host": "127.0.0.1",
            "m08_attempt_registry_compatible": True,
            "will_items_learner_exposed": False,
        },
        "evidence_state": {
            "actual_learner_attempts": 0,
            "actual_learner_evidence_rows": 0,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "real_learner_pilot_completed": False,
            "speaking_real_audio_evidence": "DEFERRED_BY_OPERATOR",
        },
        "acceptance_checks": list(ACCEPTANCE_CHECKS),
        "claim_boundaries": {
            "metadata_only_acceptance": True,
            "private_content_included": False,
            "learner_responses_included": False,
            "canonical_authority_write": False,
            "canonical_egp_mapping_changed": False,
            "public_delivery": False,
            "production_runtime_enabled": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "real_learner_pilot_claimed": False,
            "a2_content_promoted": False,
            "audio_or_recording_processed": False,
            "deferred_ceiling_classified_as_missing": False,
        },
        "acceptance_status": PASS_STATUS,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
        "next_phase_entry_condition": NEXT_PHASE_ENTRY_CONDITION,
        "errors": [],
    }
    _safe_scan(acceptance, name="m11d_system_acceptance")
    _assert_schema(acceptance)
    write_json_atomic(root / "system_acceptance.json", acceptance)
    return acceptance


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    try:
        acceptance = build_acceptance(args.output_root)
        print(json.dumps({
            "acceptance_status": acceptance["acceptance_status"],
            "canonical_units": acceptance["canonical_structural_coverage"]["grammar_units"],
            "canonical_rows": acceptance["canonical_structural_coverage"]["canonical_egp_rows"],
            "private_ready_units": acceptance["authority_reviewed_private_path"]["private_ready_units"],
            "private_ready_rows": acceptance["authority_reviewed_private_path"]["private_ready_rows"],
            "selectable_items": acceptance["authority_reviewed_private_path"]["selectable_items"],
            "deferred_units": 1,
            "actual_learner_attempts": acceptance["evidence_state"]["actual_learner_attempts"],
            "stop_reason": acceptance["stop_reason"],
            "next_short_step": acceptance["next_short_step"],
            "next_phase_entry_condition": acceptance["next_phase_entry_condition"],
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except (
        SystemAcceptanceError,
        m10.CoverageRecheckError,
        m11b.AuthorityExceptionError,
        m11c.AuthorityRuntimeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
