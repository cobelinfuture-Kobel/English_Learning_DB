#!/usr/bin/env python3
"""Resolve M11A Authority exceptions without changing canonical EGP data.

Three broad project-authored units are narrowed to Cambridge-aligned private
content and revalidated through the existing complete candidate validator.
The EGP-A1 `will` unit remains canonical but is deferred from the child A1/A1+
private path because Cambridge YLE places it at Flyers/A2.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

SOURCE_REPO_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = SOURCE_REPO_ROOT
if str(SOURCE_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m11a_authority_evidence_review as m11a  # noqa: E402

TASK_ID = "E4S-A1V1-M11B_AuthorityExceptionContentRevisionAndRevalidation"
SCHEMA_VERSION_MATRIX = "e4s.a1v1.m11b_exception_resolution_matrix.v1"
SCHEMA_VERSION_BANK = "e4s.a1v1.m11b_reviewed_private_learning_unit_bank.v1"
SCHEMA_VERSION_REPORT = "e4s.a1v1.m11b_exception_resolution_safe_report.v1"
NEXT_SHORT_STEP = "E4S-A1V1-M11C_AuthorityReviewedPrivateBankConsumerAndRuntimeIntegration"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".local/e4s_a1v1/content_review/m11b"
POLICY_PATH = SOURCE_REPO_ROOT / "ulga/evidence/e4s_a1v1_m11b_authority_exception_resolution_policy.json"
SCHEMA_DIR = SOURCE_REPO_ROOT / "ulga/schemas"
REVISION_FIELDS = (
    "title_en",
    "title_zh_tw",
    "learning_objectives",
    "form_rules",
    "meaning_functions",
    "usage_conditions",
)
EXPECTED_EXCEPTION_IDS = {
    "GRAMMAR_COORDINATION_A1",
    "GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1",
    "GRAMMAR_ADVERB_PHRASES_A1",
    "GRAMMAR_WILL_FUTURE_A1",
}


class AuthorityExceptionError(ValueError):
    """Fail-closed M11B error."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorityExceptionError(f"json_unreadable:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise AuthorityExceptionError(f"json_root_not_object:{path}")
    return value


def write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _schema(name: str) -> dict[str, Any]:
    return read_json(SCHEMA_DIR / name)


def _assert_schema(name: str, value: Mapping[str, Any]) -> None:
    errors = sorted(
        Draft202012Validator(_schema(name)).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise AuthorityExceptionError(f"schema_validation_failed:{name}:{location}:{first.message}")


def _safe_output_root(path: Path) -> Path:
    resolved = path.resolve()
    approved = (REPO_ROOT / ".local").resolve()
    if not resolved.is_relative_to(approved):
        raise AuthorityExceptionError(f"output_root_outside_local:{resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _load_policy() -> dict[str, Any]:
    policy = read_json(POLICY_PATH)
    if policy.get("task_id") != TASK_ID:
        raise AuthorityExceptionError("resolution_policy_task_id_drift")
    records = policy.get("resolution_records", [])
    if len(records) != 4 or {row.get("grammar_unit_id") for row in records} != EXPECTED_EXCEPTION_IDS:
        raise AuthorityExceptionError("resolution_policy_exception_set_drift")
    if policy.get("expected_resolution_distribution") != {
        "RESOLVED_AUTO_PASS": 3,
        "DEFERRED_CAMBRIDGE_CEILING": 1,
        "UNRESOLVED": 0,
    }:
        raise AuthorityExceptionError("resolution_policy_distribution_drift")
    return policy


def _apply_revision(unit: Mapping[str, Any], revision: Mapping[str, Any]) -> dict[str, Any]:
    if set(revision) != set(REVISION_FIELDS):
        raise AuthorityExceptionError(f"revision_field_contract_drift:{unit.get('grammar_unit_id')}")
    revised = deepcopy(unit)
    for field in REVISION_FIELDS:
        revised[field] = deepcopy(revision[field])
    revised["content_review_status"] = "AUTHORITY_EVIDENCE_REVISED_PRIVATE"
    trace = deepcopy(revised.get("source_trace", {}))
    trace["authority_exception_resolution"] = TASK_ID
    trace["canonical_authority_payload_mutated"] = False
    revised["source_trace"] = trace
    return revised


def _validation_metrics(unit: Mapping[str, Any], full_pass: bool) -> dict[str, Any]:
    result = m11a._unit_validation(unit)
    return {
        "positive_pass": result["positive_pass"],
        "positive_total": result["positive_total"],
        "negative_pass": result["negative_pass"],
        "negative_total": result["negative_total"],
        "practice_pass": result["practice_pass"],
        "practice_total": result["practice_total"],
        "assessment_pass": result["assessment_pass"],
        "assessment_total": result["assessment_total"],
        "full_candidate_validator_pass": full_pass,
    }


def _metrics_pass(metrics: Mapping[str, Any]) -> bool:
    return (
        metrics.get("positive_total", 0) >= 2
        and metrics.get("positive_pass") == metrics.get("positive_total")
        and metrics.get("negative_total", 0) >= 3
        and metrics.get("negative_pass") == metrics.get("negative_total")
        and metrics.get("practice_total", 0) >= 6
        and metrics.get("practice_pass") == metrics.get("practice_total")
        and metrics.get("assessment_total", 0) >= 2
        and metrics.get("assessment_pass") == metrics.get("assessment_total")
        and metrics.get("full_candidate_validator_pass") is True
    )


def build_artifacts() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    policy = _load_policy()
    m11a_matrix, m11a_bank, m11a_report = m11a.build_artifacts()
    if m11a_report.get("decision_counts") != {
        "AUTO_PASS": 20,
        "REVISION_REQUIRED": 3,
        "AUTHORITY_CONFLICT": 1,
        "SOURCE_EVIDENCE_MISSING": 0,
    }:
        raise AuthorityExceptionError("m11a_source_distribution_drift")
    source_candidate, source_validation = m11a.m11._source_candidate()
    if source_validation.get("validation_status") != "PASS":
        raise AuthorityExceptionError("source_candidate_validation_failed")
    units_by_id = {
        str(unit["grammar_unit_id"]): unit
        for unit in source_candidate.get("learning_units", [])
    }
    source_exceptions = {
        row["grammar_unit_id"]: row
        for row in m11a_matrix["entries"]
        if row["automated_decision"] != "AUTO_PASS"
    }
    if set(source_exceptions) != EXPECTED_EXCEPTION_IDS:
        raise AuthorityExceptionError("m11a_exception_set_drift")

    policy_by_id = {row["grammar_unit_id"]: row for row in policy["resolution_records"]}
    replacements: dict[str, Mapping[str, Any]] = {}
    for grammar_id, record in policy_by_id.items():
        if record["resolution"] == "REVISE_AND_REVALIDATE":
            replacements[grammar_id] = _apply_revision(units_by_id[grammar_id], record["revision"])
        elif record["resolution"] == "DEFER_PRIVATE_PROMOTION":
            if record.get("revision") is not None:
                raise AuthorityExceptionError(f"deferred_unit_has_revision:{grammar_id}")
        else:
            raise AuthorityExceptionError(f"unknown_resolution:{grammar_id}:{record.get('resolution')}")

    revised_candidate = m11a.m11._validate_revised_candidate(source_candidate, replacements)
    revised_by_id = {
        str(unit["grammar_unit_id"]): unit
        for unit in revised_candidate["learning_units"]
    }
    resolution_records: list[dict[str, Any]] = []
    for grammar_id in sorted(EXPECTED_EXCEPTION_IDS):
        policy_record = policy_by_id[grammar_id]
        source_entry = source_exceptions[grammar_id]
        before = units_by_id[grammar_id]
        after = revised_by_id[grammar_id]
        is_revised = policy_record["resolution"] == "REVISE_AND_REVALIDATE"
        metrics = _validation_metrics(after, True)
        if not _metrics_pass(metrics):
            raise AuthorityExceptionError(f"exception_revalidation_failed:{grammar_id}")
        if is_revised:
            changed = [field for field in REVISION_FIELDS if before.get(field) != after.get(field)]
            if set(changed) != set(REVISION_FIELDS):
                raise AuthorityExceptionError(f"revision_fields_not_all_changed:{grammar_id}:{changed}")
            resolution_status = "RESOLVED_AUTO_PASS"
            private_ready = True
        else:
            changed = []
            if sha256_value(before) != sha256_value(after):
                raise AuthorityExceptionError(f"deferred_payload_drift:{grammar_id}")
            resolution_status = "DEFERRED_CAMBRIDGE_CEILING"
            private_ready = False
        record = {
            "grammar_unit_id": grammar_id,
            "source_decision": source_entry["automated_decision"],
            "resolution_status": resolution_status,
            "cambridge_stage": policy_record["cambridge_stage"],
            "canonical_egp_row_ids": list(before["canonical_egp_row_ids"]),
            "before_payload_sha256": sha256_value(before),
            "after_payload_sha256": sha256_value(after),
            "changed_fields": sorted(changed),
            "evidence_refs": sorted(set(policy_record["evidence_refs"])),
            "reason_codes": sorted(set(policy_record["reason_codes"])),
            "revalidation": metrics,
            "private_learning_ready": private_ready,
        }
        record["record_sha256"] = sha256_value(record)
        resolution_records.append(record)

    resolution_counts = Counter(row["resolution_status"] for row in resolution_records)
    if {
        "RESOLVED_AUTO_PASS": resolution_counts["RESOLVED_AUTO_PASS"],
        "DEFERRED_CAMBRIDGE_CEILING": resolution_counts["DEFERRED_CAMBRIDGE_CEILING"],
        "UNRESOLVED": 0,
    } != policy["expected_resolution_distribution"]:
        raise AuthorityExceptionError("resolution_distribution_drift")

    matrix = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION_MATRIX,
        "private_local_only": True,
        "source_m11a_matrix_sha256": sha256_value(m11a_matrix),
        "source_candidate_sha256": sha256_value(source_candidate),
        "revised_candidate_sha256": sha256_value(revised_candidate),
        "exception_count": 4,
        "records": resolution_records,
        "records_sha256": sha256_value(resolution_records),
        "claim_boundaries": {
            "private_local_only": True,
            "canonical_egp_mapping_changed": False,
            "canonical_authority_write": False,
            "a2_content_promoted": False,
            "manual_checkbox_approval_required": False,
        },
    }
    _assert_schema("e4s_a1v1_m11b_exception_resolution_matrix.schema.json", matrix)

    reviewed_units: list[dict[str, Any]] = []
    for source_row in m11a_bank["reviewed_units"]:
        grammar_id = source_row["grammar_unit_id"]
        token = hashlib.sha256(grammar_id.encode("utf-8")).hexdigest()[:20].upper()
        reviewed_units.append({
            "reviewed_unit_id": f"M11B_UNIT_{token}",
            "status": "EVIDENCE_REVIEWED_PRIVATE_LEARNING_UNIT",
            "grammar_unit_id": grammar_id,
            "internal_stage": source_row["internal_stage"],
            "canonical_egp_row_ids": list(source_row["canonical_egp_row_ids"]),
            "final_private_unit_payload": deepcopy(source_row["final_private_unit_payload"]),
            "authority_resolution": "M11A_AUTO_PASS",
            "evidence_record_sha256": source_row["evidence_record_sha256"],
            "private_learning_ready": True,
            "mastery_trackable": False,
            "canonical_authority_promotion": False,
        })
    by_resolution = {row["grammar_unit_id"]: row for row in resolution_records}
    for grammar_id in sorted(replacements):
        token = hashlib.sha256(grammar_id.encode("utf-8")).hexdigest()[:20].upper()
        resolution = by_resolution[grammar_id]
        reviewed_units.append({
            "reviewed_unit_id": f"M11B_UNIT_{token}",
            "status": "EVIDENCE_REVISED_PRIVATE_LEARNING_UNIT",
            "grammar_unit_id": grammar_id,
            "internal_stage": revised_by_id[grammar_id]["internal_stage"],
            "canonical_egp_row_ids": list(revised_by_id[grammar_id]["canonical_egp_row_ids"]),
            "final_private_unit_payload": deepcopy(revised_by_id[grammar_id]),
            "authority_resolution": "M11B_REVISED_AND_REVALIDATED",
            "evidence_record_sha256": resolution["record_sha256"],
            "private_learning_ready": True,
            "mastery_trackable": False,
            "canonical_authority_promotion": False,
        })
    reviewed_units.sort(key=lambda row: row["grammar_unit_id"])
    if len(reviewed_units) != 23 or len({row["grammar_unit_id"] for row in reviewed_units}) != 23:
        raise AuthorityExceptionError("private_ready_unit_identity_not_23")
    reviewed_rows = {
        row_id for row in reviewed_units for row_id in row["canonical_egp_row_ids"]
    }
    will = revised_by_id["GRAMMAR_WILL_FUTURE_A1"]
    deferred_units = [{
        "grammar_unit_id": "GRAMMAR_WILL_FUTURE_A1",
        "status": "DEFERRED_CAMBRIDGE_FLYERS_A2_CEILING",
        "cambridge_stage": "FLYERS",
        "canonical_egp_row_ids": list(will["canonical_egp_row_ids"]),
        "reason_codes": list(policy_by_id["GRAMMAR_WILL_FUTURE_A1"]["reason_codes"]),
        "private_learning_ready": False,
        "canonical_egp_mapping_preserved": True,
        "a2_content_promoted": False,
    }]
    bank = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION_BANK,
        "private_local_only": True,
        "source_m11a_bank_sha256": sha256_value(m11a_bank),
        "source_resolution_matrix_sha256": sha256_value(matrix),
        "reviewed_unit_count": 23,
        "canonical_egp_row_count": len(reviewed_rows),
        "deferred_unit_count": 1,
        "reviewed_units": reviewed_units,
        "deferred_units": deferred_units,
        "reviewed_units_sha256": sha256_value(reviewed_units),
        "claim_boundaries": {
            "private_local_only": True,
            "must_not_be_committed": True,
            "canonical_authority_promotion": False,
            "public_delivery": False,
            "learner_mastery_claimed": False,
            "persistent_learner_state_write": False,
            "a2_content_promoted": False,
        },
    }
    _assert_schema("e4s_a1v1_m11b_reviewed_private_learning_unit_bank.schema.json", bank)

    report = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION_REPORT,
        "candidate_unit_count": 24,
        "canonical_egp_row_count": 109,
        "source_exception_count": 4,
        "resolution_counts": {
            "RESOLVED_AUTO_PASS": 3,
            "DEFERRED_CAMBRIDGE_CEILING": 1,
            "UNRESOLVED": 0,
        },
        "private_ready_unit_count": 23,
        "private_ready_row_count": len(reviewed_rows),
        "deferred_unit_count": 1,
        "unresolved_exception_count": 0,
        "claim_boundaries": {
            "metadata_only_report": True,
            "private_candidate_content_included": False,
            "raw_cambridge_source_included": False,
            "canonical_egp_mapping_changed": False,
            "canonical_authority_promotion": False,
            "public_delivery": False,
            "learner_mastery_claimed": False,
            "a2_content_promoted": False,
            "manual_checkbox_approval_required": False,
        },
        "validation_status": "PASS_M11B_AUTHORITY_EXCEPTIONS_RESOLVED",
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
        "errors": [],
    }
    m11a._safe_scan(report, name="m11b_exception_resolution_safe_report")
    _assert_schema("e4s_a1v1_m11b_exception_resolution_safe_report.schema.json", report)
    return matrix, bank, report


def build_to_root(output_root: Path) -> dict[str, Any]:
    root = _safe_output_root(output_root)
    matrix, bank, report = build_artifacts()
    write_json_atomic(root / "authority_exception_resolution_matrix.private.json", matrix)
    write_json_atomic(root / "reviewed_private_learning_unit_bank.json", bank)
    write_json_atomic(root / "authority_exception_resolution_safe_report.json", report)
    return {"matrix": matrix, "bank": bank, "safe_report": report}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    try:
        result = build_to_root(args.output_root)
        report = result["safe_report"]
        print(json.dumps({
            "candidate_units": report["candidate_unit_count"],
            "canonical_egp_rows": report["canonical_egp_row_count"],
            "resolution_counts": report["resolution_counts"],
            "private_ready_units": report["private_ready_unit_count"],
            "private_ready_rows": report["private_ready_row_count"],
            "deferred_units": report["deferred_unit_count"],
            "validation_status": report["validation_status"],
            "stop_reason": report["stop_reason"],
            "next_short_step": report["next_short_step"],
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except (AuthorityExceptionError, m11a.AuthorityEvidenceError, m11a.m11.CandidateReviewError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
