#!/usr/bin/env python3
"""Build privacy-safe QA and coverage expansion from complete M12D evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m12_real_learner_pilot_evidence_capture as m12  # noqa: E402
from ulga.builders import build_e4s_a1v1_m12c_real_learner_pilot_evidence_qa as m12c  # noqa: E402
from ulga.builders import build_e4s_a1v1_m12d_representative_pilot_expansion as m12d  # noqa: E402

TASK_ID = "E4S-A1V1-M12E_RepresentativePilotEvidenceQAAndCoverageExpansion"
SCHEMA_VERSION = "e4s.a1v1.m12e.representative_evidence_qa.v1"
REAL_STATUS = "PASS_M12E_REAL_LEARNER_REPRESENTATIVE_EVIDENCE_QA_COMPLETE"
TEST_STATUS = "PASS_M12E_TEST_FIXTURE_QA_VALIDATED"
DEFAULT_INPUT_ROOT = REPO_ROOT / ".local/e4s_a1v1/pilot/m12"
DEFAULT_QA_ROOT = REPO_ROOT / ".local/e4s_a1v1/pilot/m12c"
DEFAULT_REPRESENTATIVE_ROOT = REPO_ROOT / ".local/e4s_a1v1/pilot/m12d"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".local/e4s_a1v1/pilot/m12e"
SCHEMA_PATH = REPO_ROOT / "ulga/schemas/e4s_a1v1_m12e_representative_evidence_qa.schema.json"
OUTCOMES = m12c.OUTCOMES
DEFERRED_GRAMMAR_ID = m12d.DEFERRED_GRAMMAR_ID
MAX_QUEUE_SIZE = 8


class RepresentativeEvidenceQAError(ValueError):
    """Fail-closed M12E error."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RepresentativeEvidenceQAError(f"json_unreadable:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise RepresentativeEvidenceQAError(f"json_root_not_object:{path}")
    return value


def write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _safe_root(path: Path) -> Path:
    resolved = path.resolve()
    approved = (REPO_ROOT / ".local").resolve()
    if not resolved.is_relative_to(approved):
        raise RepresentativeEvidenceQAError(f"path_outside_local:{resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _require(actual: Any, expected: Any, code: str) -> None:
    if actual != expected:
        raise RepresentativeEvidenceQAError(f"{code}:expected={expected!r}:actual={actual!r}")


def _assert_schema(value: Mapping[str, Any]) -> None:
    schema = read_json(SCHEMA_PATH)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise RepresentativeEvidenceQAError(f"schema_validation_failed:{location}:{first.message}")


def _safe_scan(value: Any) -> None:
    forbidden = {
        "response", "learner_response", "learner_responses", "prompt", "answer",
        "answer_key", "accepted_texts", "accepted_sequence", "private_scoring_contract",
        "model_texts", "session_id", "learner_ref", "submitted_at",
    }

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                lowered = str(key).casefold()
                if lowered in forbidden or lowered.endswith("_absolute_path"):
                    raise RepresentativeEvidenceQAError(f"private_field_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            if Path(node).is_absolute() or (len(node) > 2 and node[1:3] in {":\\", ":/"}):
                raise RepresentativeEvidenceQAError("absolute_path_leak")

    walk(value)


def _percent(count: int, total: int) -> float:
    return round(count * 100.0 / total, 2) if total else 0.0


def _expected_m12c_status(origin: str) -> str:
    return m12c.REAL_STATUS if origin == "REAL_LEARNER" else m12c.TEST_STATUS


def _expected_m12d_status(origin: str) -> str:
    return m12d.REAL_STATUS if origin == "REAL_LEARNER" else m12d.TEST_STATUS


def _queue_item(row: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return {
        "item_id": str(row["item_id"]),
        "grammar_unit_id": str(row["grammar_unit_id"]),
        "canonical_egp_row_ids": list(row["canonical_egp_row_ids"]),
        "internal_stage": str(row["internal_stage"]),
        "skill": str(row["skill"]),
        "item_role": str(row["item_role"]),
        "evidence_dimension": str(row["evidence_dimension"]),
        "task_type": str(row["task_type"]),
        "reason_code": reason,
    }


def _build_queue(
    query_items: list[dict[str, Any]],
    ledger_entries: list[dict[str, Any]],
    skill_counts: Counter[str],
    role_counts: Counter[str],
) -> list[dict[str, Any]]:
    attempted_ids = {str(row["item_id"]) for row in ledger_entries}
    attempted_units = {str(row["grammar_unit_id"]) for row in ledger_entries}
    failed_units = {
        str(row["grammar_unit_id"])
        for row in ledger_entries
        if row.get("outcome") in {"AUTO_FAIL", "HUMAN_REJECT"}
    }
    unattempted = [
        row for row in query_items
        if str(row["item_id"]) not in attempted_ids
        and row.get("grammar_unit_id") != DEFERRED_GRAMMAR_ID
    ]
    unattempted_units = sorted({str(row["grammar_unit_id"]) for row in unattempted} - attempted_units)
    queue: list[dict[str, Any]] = []
    used_items: set[str] = set()
    per_unit: Counter[str] = Counter()

    def add(row: Mapping[str, Any], reason: str, *, unit_limit: int | None = None) -> None:
        item_id = str(row["item_id"])
        grammar_id = str(row["grammar_unit_id"])
        if item_id in used_items or len(queue) >= MAX_QUEUE_SIZE:
            return
        if unit_limit is not None and per_unit[grammar_id] >= unit_limit:
            return
        used_items.add(item_id)
        per_unit[grammar_id] += 1
        queue.append(_queue_item(row, reason))

    def unit_rows(grammar_id: str) -> list[dict[str, Any]]:
        return sorted(
            [row for row in unattempted if str(row["grammar_unit_id"]) == grammar_id],
            key=lambda row: (
                0 if row.get("item_role") == "practice" else 1,
                0 if row.get("skill") == "reading" else 1,
                str(row["item_id"]),
            ),
        )

    for grammar_id in sorted(failed_units):
        for row in unit_rows(grammar_id):
            add(row, "FAILED_UNIT_REMEDIATION", unit_limit=2)
            if len(queue) >= MAX_QUEUE_SIZE:
                return queue

    for grammar_id in unattempted_units:
        rows = unit_rows(grammar_id)
        preferred: list[dict[str, Any]] = []
        for skill in ("reading", "writing"):
            match = next(
                (row for row in rows if row.get("skill") == skill and row.get("item_role") == "practice"),
                None,
            )
            if match is not None:
                preferred.append(match)
        for row in preferred or rows:
            add(row, "UNATTEMPTED_UNIT_COVERAGE", unit_limit=2)
        if len(queue) >= MAX_QUEUE_SIZE:
            return queue

    for row in sorted(
        unattempted,
        key=lambda item: (
            skill_counts[str(item["skill"])],
            role_counts[str(item["item_role"])],
            per_unit[str(item["grammar_unit_id"])],
            str(item["internal_stage"]),
            str(item["grammar_unit_id"]),
            str(item["item_id"]),
        ),
    ):
        add(row, "SKILL_ROLE_BALANCE")
        if len(queue) >= MAX_QUEUE_SIZE:
            break
    return queue


def build_qa(
    input_root: Path,
    qa_root: Path,
    representative_root: Path,
    output_root: Path,
    *,
    expected_origin: str,
) -> dict[str, Any]:
    source = _safe_root(input_root)
    prior_qa_root = _safe_root(qa_root)
    representative = _safe_root(representative_root)
    target = _safe_root(output_root)
    if expected_origin not in {"REAL_LEARNER", "TEST_FIXTURE"}:
        raise RepresentativeEvidenceQAError(f"expected_origin_invalid:{expected_origin}")

    m12_manifest = read_json(source / "pilot_capture_manifest.private.json")
    m12c_report = read_json(prior_qa_root / "real_evidence_qa_safe_report.json")
    m12d_manifest = read_json(representative / "representative_batch_manifest.private.json")
    m12d_report = read_json(representative / "representative_pilot_expansion_safe_report.json")
    registry = read_json(representative / "cumulative_attempt_registry.private.json")
    ledger = read_json(representative / "cumulative_progress_ledger.private.json")
    query = read_json(representative / "cumulative_progress_query_index.json")

    _require(m12_manifest.get("task_id"), m12.TASK_ID, "m12_manifest_task")
    _require(m12c_report.get("task_id"), m12c.TASK_ID, "m12c_task")
    _require(m12c_report.get("evidence_origin"), expected_origin, "m12c_origin")
    _require(m12c_report.get("validation_status"), _expected_m12c_status(expected_origin), "m12c_status")
    _require(m12d_manifest.get("task_id"), m12d.TASK_ID, "m12d_manifest_task")
    _require(m12d_manifest.get("evidence_origin"), expected_origin, "m12d_manifest_origin")
    _require(m12d_report.get("task_id"), m12d.TASK_ID, "m12d_report_task")
    _require(m12d_report.get("evidence_origin"), expected_origin, "m12d_report_origin")
    _require(m12d_report.get("validation_status"), _expected_m12d_status(expected_origin), "m12d_status")
    _require(m12d_report.get("stop_reason"), "NONE" if expected_origin == "REAL_LEARNER" else "REAL_LEARNER_REPRESENTATIVE_BATCH_REQUIRED", "m12d_stop_reason")
    _require(m12d_report.get("batch_attempt_count"), 8, "m12d_batch_attempts")
    _require(m12d_report.get("remaining_batch_attempt_count"), 0, "m12d_remaining_attempts")
    _require(m12d_manifest.get("batch_selection", {}).get("batch_size"), 8, "m12d_batch_size")
    _require(m12d_manifest.get("batch_selection", {}).get("grammar_unit_count"), 4, "m12d_batch_units")
    _require(m12d_manifest.get("batch_selection", {}).get("skill_counts"), {"reading": 4, "writing": 4}, "m12d_batch_skills")
    _require(m12d_manifest.get("batch_selection", {}).get("role_counts"), {"practice": 4, "assessment": 4}, "m12d_batch_roles")

    prior_summary = m12c_report.get("evidence_summary", {})
    prior_attempts = int(prior_summary.get("attempt_count", 0))
    prior_units = int(prior_summary.get("attempted_unit_count", 0))
    prior_rows = int(prior_summary.get("attempted_row_count", 0))
    _require(m12d_report.get("prior_attempt_count"), prior_attempts, "m12c_m12d_prior_attempts")
    _require(m12d_manifest.get("prior_evidence", {}).get("attempt_count"), prior_attempts, "m12d_manifest_prior_attempts")

    _require(m12_manifest.get("selection", {}).get("selectable_item_count"), 184, "selectable_items")
    _require(m12_manifest.get("selection", {}).get("private_ready_unit_count"), 23, "private_units")
    _require(m12_manifest.get("selection", {}).get("private_ready_row_count"), 107, "private_rows")
    allowed = set(m12_manifest["selection"]["selectable_item_ids"])
    if len(allowed) != 184:
        raise RepresentativeEvidenceQAError(f"allowed_item_identity_not_184:{len(allowed)}")

    entries = list(ledger.get("entries", []))
    current_attempts = len(entries)
    _require(ledger.get("attempt_count"), current_attempts, "ledger_attempt_count")
    _require(query.get("attempt_count"), current_attempts, "query_attempt_count")
    _require(len(registry.get("attempts", [])), current_attempts, "registry_attempt_count")
    _require(m12d_report.get("cumulative_attempt_count"), current_attempts, "m12d_cumulative_attempts")
    _require(current_attempts, prior_attempts + 8, "prior_plus_batch_attempts")
    _require(registry.get("session_bank_sha256"), m12d_manifest.get("attempt_registry_contract", {}).get("session_bank_sha256"), "registry_bank_hash")
    item_ids = [str(row.get("item_id")) for row in entries]
    if len(item_ids) != len(set(item_ids)):
        raise RepresentativeEvidenceQAError("duplicate_ledger_item")
    if any(item_id not in allowed for item_id in item_ids):
        raise RepresentativeEvidenceQAError("nonselectable_ledger_item")
    if any(item_id.startswith(DEFERRED_GRAMMAR_ID) for item_id in item_ids):
        raise RepresentativeEvidenceQAError("deferred_will_attempted")

    query_items = [dict(row) for row in query.get("items", []) if str(row.get("item_id")) in allowed]
    if len(query_items) != 184:
        raise RepresentativeEvidenceQAError(f"selectable_query_count_drift:{len(query_items)}")
    entries_by_id = {str(row["item_id"]): row for row in entries}
    for item_id, entry in entries_by_id.items():
        match = next((row for row in query_items if str(row.get("item_id")) == item_id), None)
        if match is None or match.get("attempted") is not True or match.get("outcome") != entry.get("outcome"):
            raise RepresentativeEvidenceQAError(f"query_ledger_mismatch:{item_id}")

    outcome_counts = Counter(str(row.get("outcome")) for row in entries)
    skill_counts = Counter(str(row.get("skill")) for row in entries)
    role_counts = Counter(str(row.get("item_role")) for row in entries)
    attempted_units = {str(row.get("grammar_unit_id")) for row in entries}
    attempted_rows = {str(row_id) for row in entries for row_id in row.get("canonical_egp_row_ids", [])}
    current_units = len(attempted_units)
    current_rows = len(attempted_rows)
    if current_units < prior_units or current_rows < prior_rows:
        raise RepresentativeEvidenceQAError("coverage_regressed_after_representative_batch")
    _require(m12d_report.get("cumulative_attempted_unit_count"), current_units, "m12d_cumulative_units")
    _require(m12d_report.get("cumulative_attempted_row_count"), current_rows, "m12d_cumulative_rows")

    pending = outcome_counts["PENDING_HUMAN_REVIEW"]
    fail_count = outcome_counts["AUTO_FAIL"] + outcome_counts["HUMAN_REJECT"]
    coverage_complete = current_attempts == 184 and current_units == 23 and current_rows == 107
    queue = [] if coverage_complete else _build_queue(query_items, entries, skill_counts, role_counts)
    if not coverage_complete and len(queue) != MAX_QUEUE_SIZE:
        raise RepresentativeEvidenceQAError(f"coverage_expansion_queue_not_8:{len(queue)}")
    queued_ids = [row["item_id"] for row in queue]
    if len(queued_ids) != len(set(queued_ids)) or any(item_id in entries_by_id for item_id in queued_ids):
        raise RepresentativeEvidenceQAError("coverage_queue_identity_invalid")

    if pending:
        quality_state = "PASS_HUMAN_REVIEW_REQUIRED"
        stop_reason = "HUMAN_REVIEW_DECISIONS_REQUIRED"
        next_step = "E4S-A1V1-M12E1_HumanReviewDecisionMaterialization"
    elif fail_count:
        quality_state = "PASS_REMEDIATION_AND_EXPANSION_REQUIRED"
        stop_reason = "NONE"
        next_step = "E4S-A1V1-M12F_RemediationAndCoverageExpansion"
    elif coverage_complete:
        quality_state = "PASS_COVERAGE_COMPLETE"
        stop_reason = "NONE"
        next_step = "E4S-A1V1-M12G_CoverageEvidenceCloseout"
    else:
        quality_state = "PASS_COVERAGE_EXPANSION_REQUIRED"
        stop_reason = "NONE"
        next_step = "E4S-A1V1-M12F_CoverageExpansionBatch"

    report = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": "REPRESENTATIVE_EVIDENCE_QA_AND_COVERAGE_EXPANSION",
        "evidence_origin": expected_origin,
        "source_hashes": {
            "m12_capture_manifest_sha256": sha256_value(m12_manifest),
            "m12c_qa_report_sha256": sha256_value(m12c_report),
            "m12d_batch_manifest_sha256": sha256_value(m12d_manifest),
            "m12d_expansion_report_sha256": sha256_value(m12d_report),
            "cumulative_registry_sha256": sha256_value(registry),
            "cumulative_ledger_sha256": sha256_value(ledger),
            "cumulative_query_sha256": sha256_value(query),
        },
        "representative_batch": {
            "prior_attempt_count": prior_attempts,
            "batch_attempt_count": 8,
            "cumulative_attempt_count": current_attempts,
            "batch_unit_count": 4,
            "batch_row_count": int(m12d_manifest["batch_selection"]["canonical_egp_row_count"]),
            "skill_counts": {"reading": 4, "writing": 4},
            "role_counts": {"practice": 4, "assessment": 4},
            "complete": True,
        },
        "evidence_summary": {
            "attempt_count": current_attempts,
            "attempted_unit_count": current_units,
            "attempted_row_count": current_rows,
            "skill_attempt_counts": {"reading": skill_counts["reading"], "writing": skill_counts["writing"]},
            "role_attempt_counts": {"practice": role_counts["practice"], "assessment": role_counts["assessment"]},
            "outcome_counts": {name: outcome_counts[name] for name in OUTCOMES},
            "pending_human_review_count": pending,
            "auto_fail_count": outcome_counts["AUTO_FAIL"],
            "auto_pass_count": outcome_counts["AUTO_PASS"],
        },
        "coverage_progress": {
            "selectable_items": 184,
            "private_ready_units": 23,
            "private_ready_rows": 107,
            "prior": {"items": prior_attempts, "units": prior_units, "rows": prior_rows},
            "current": {"items": current_attempts, "units": current_units, "rows": current_rows},
            "delta": {"items": current_attempts - prior_attempts, "units": current_units - prior_units, "rows": current_rows - prior_rows},
            "remaining": {"items": 184 - current_attempts, "units": 23 - current_units, "rows": 107 - current_rows},
            "current_percent": {
                "items": _percent(current_attempts, 184),
                "units": _percent(current_units, 23),
                "rows": _percent(current_rows, 107),
            },
            "representative_pilot_completed": True,
            "coverage_complete": coverage_complete,
        },
        "quality_gate": {
            "state": quality_state,
            "human_review_required": pending > 0,
            "remediation_required": fail_count > 0,
            "representative_batch_valid": True,
            "deterministic_evidence_valid": True,
        },
        "coverage_expansion_queue": {
            "candidate_count": len(queue),
            "maximum_batch_size": MAX_QUEUE_SIZE,
            "selection_policy": "REMEDIATION_THEN_UNATTEMPTED_UNIT_THEN_SKILL_ROLE_BALANCE",
            "items": queue,
        },
        "claim_boundaries": {
            "metadata_only_report": True,
            "private_responses_included": False,
            "learner_identity_included": False,
            "test_fixture_counted_as_real_evidence": False,
            "canonical_authority_write": False,
            "canonical_egp_mapping_changed": False,
            "public_delivery": False,
            "production_runtime_enabled": False,
            "a2_content_promoted": False,
            "audio_or_recording_processed": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "representative_pilot_completed": True,
            "full_private_coverage_claimed": coverage_complete,
        },
        "validation_status": REAL_STATUS if expected_origin == "REAL_LEARNER" else TEST_STATUS,
        "stop_reason": stop_reason,
        "next_short_step": next_step,
        "errors": [],
    }
    _safe_scan(report)
    _assert_schema(report)
    write_json_atomic(target / "representative_evidence_qa_safe_report.json", report)
    write_json_atomic(target / "coverage_expansion_queue.json", report["coverage_expansion_queue"])
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--qa-root", type=Path, default=DEFAULT_QA_ROOT)
    parser.add_argument("--representative-root", type=Path, default=DEFAULT_REPRESENTATIVE_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--expected-origin", choices=["REAL_LEARNER", "TEST_FIXTURE"], required=True)
    args = parser.parse_args(argv)
    try:
        result = build_qa(
            args.input_root,
            args.qa_root,
            args.representative_root,
            args.output_root,
            expected_origin=args.expected_origin,
        )
        print(json.dumps({
            "evidence_origin": result["evidence_origin"],
            "attempt_count": result["evidence_summary"]["attempt_count"],
            "attempted_unit_count": result["evidence_summary"]["attempted_unit_count"],
            "attempted_row_count": result["evidence_summary"]["attempted_row_count"],
            "auto_pass_count": result["evidence_summary"]["auto_pass_count"],
            "auto_fail_count": result["evidence_summary"]["auto_fail_count"],
            "pending_human_review_count": result["evidence_summary"]["pending_human_review_count"],
            "coverage_delta": result["coverage_progress"]["delta"],
            "iteration_candidate_count": result["coverage_expansion_queue"]["candidate_count"],
            "validation_status": result["validation_status"],
            "stop_reason": result["stop_reason"],
            "next_short_step": result["next_short_step"],
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except (
        RepresentativeEvidenceQAError,
        m12.PilotCaptureError,
        m12c.EvidenceQAError,
        m12d.RepresentativePilotError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
