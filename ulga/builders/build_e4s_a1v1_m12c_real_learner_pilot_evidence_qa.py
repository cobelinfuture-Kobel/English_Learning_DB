#!/usr/bin/env python3
"""Build privacy-safe QA and a deterministic next-batch queue from M12 evidence."""
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

TASK_ID = "E4S-A1V1-M12C_RealLearnerPilotEvidenceQAAndIteration"
SCHEMA_VERSION = "e4s.a1v1.m12c.real_evidence_qa.v1"
REAL_STATUS = "PASS_M12C_REAL_LEARNER_PILOT_EVIDENCE_QA_COMPLETE"
TEST_STATUS = "PASS_M12C_TEST_FIXTURE_QA_VALIDATED"
DEFAULT_INPUT_ROOT = REPO_ROOT / ".local/e4s_a1v1/pilot/m12"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".local/e4s_a1v1/pilot/m12c"
SCHEMA_PATH = REPO_ROOT / "ulga/schemas/e4s_a1v1_m12c_real_evidence_qa.schema.json"
OUTCOMES = ("AUTO_PASS", "AUTO_FAIL", "PENDING_HUMAN_REVIEW", "HUMAN_APPROVE", "HUMAN_REJECT", "HUMAN_DEFER")


class EvidenceQAError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceQAError(f"json_unreadable:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceQAError(f"json_root_not_object:{path}")
    return value


def write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _safe_root(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to((REPO_ROOT / ".local").resolve()):
        raise EvidenceQAError(f"path_outside_local:{resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _require(actual: Any, expected: Any, code: str) -> None:
    if actual != expected:
        raise EvidenceQAError(f"{code}:expected={expected!r}:actual={actual!r}")


def _assert_schema(value: Mapping[str, Any]) -> None:
    schema = read_json(SCHEMA_PATH)
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda e: list(e.absolute_path))
    if errors:
        first = errors[0]
        loc = ".".join(str(v) for v in first.absolute_path) or "$"
        raise EvidenceQAError(f"schema_validation_failed:{loc}:{first.message}")


def _safe_scan(value: Any) -> None:
    forbidden = {"response", "learner_response", "learner_responses", "prompt", "answer", "answer_key", "accepted_texts", "accepted_sequence", "private_scoring_contract", "model_texts", "session_id", "learner_ref", "submitted_at"}
    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in forbidden or str(key).casefold().endswith("_absolute_path"):
                    raise EvidenceQAError(f"private_field_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            if Path(node).is_absolute() or (len(node) > 2 and node[1:3] in {":\\", ":/"}):
                raise EvidenceQAError("absolute_path_leak")
    walk(value)


def _percent(count: int, total: int) -> float:
    return round(count * 100.0 / total, 2) if total else 0.0


def build_qa(input_root: Path, output_root: Path, *, expected_origin: str) -> dict[str, Any]:
    source = _safe_root(input_root)
    target = _safe_root(output_root)
    if expected_origin not in {"REAL_LEARNER", "TEST_FIXTURE"}:
        raise EvidenceQAError(f"expected_origin_invalid:{expected_origin}")

    manifest = read_json(source / "pilot_capture_manifest.private.json")
    capture = read_json(source / "pilot_evidence_capture_safe_report.json")
    ledger = read_json(source / "pilot_progress_ledger.private.json")
    query = read_json(source / "pilot_progress_query_index.json")

    _require(manifest.get("task_id"), m12.TASK_ID, "manifest_task_id")
    _require(capture.get("task_id"), m12.TASK_ID, "capture_task_id")
    _require(capture.get("mode"), "IMPORT", "capture_mode")
    _require(capture.get("evidence_origin"), expected_origin, "capture_origin")
    _require(capture.get("actual_attempt_count"), ledger.get("attempt_count"), "capture_ledger_attempts")
    if int(ledger.get("attempt_count", 0)) < 1:
        raise EvidenceQAError("qa_requires_nonzero_attempts")
    _require(query.get("attempt_count"), ledger.get("attempt_count"), "query_attempt_count")
    _require(manifest.get("selection", {}).get("selectable_item_count"), 184, "selectable_items")
    _require(manifest.get("selection", {}).get("private_ready_unit_count"), 23, "private_units")
    _require(manifest.get("selection", {}).get("private_ready_row_count"), 107, "private_rows")

    allowed = set(manifest["selection"]["selectable_item_ids"])
    entries = list(ledger.get("entries", []))
    if len({str(row.get("item_id")) for row in entries}) != len(entries):
        raise EvidenceQAError("duplicate_ledger_item")
    if any(str(row.get("item_id")) not in allowed for row in entries):
        raise EvidenceQAError("nonselectable_ledger_item")
    attempted_by_id = {str(row["item_id"]): row for row in entries}
    query_items = [row for row in query.get("items", []) if str(row.get("item_id")) in allowed]
    if len(query_items) != 184:
        raise EvidenceQAError(f"selectable_query_count_drift:{len(query_items)}")
    for item_id, entry in attempted_by_id.items():
        match = next((row for row in query_items if row.get("item_id") == item_id), None)
        if not match or match.get("attempted") is not True or match.get("outcome") != entry.get("outcome"):
            raise EvidenceQAError(f"query_ledger_mismatch:{item_id}")

    outcome_counts = Counter(str(row.get("outcome")) for row in entries)
    skill_counts = Counter(str(row.get("skill")) for row in entries)
    role_counts = Counter(str(row.get("item_role")) for row in entries)
    attempted_units = {str(row.get("grammar_unit_id")) for row in entries}
    attempted_rows = {str(row_id) for row in entries for row_id in row.get("canonical_egp_row_ids", [])}
    pending = outcome_counts["PENDING_HUMAN_REVIEW"]
    auto_fail = outcome_counts["AUTO_FAIL"]

    unattempted = [row for row in query_items if not row.get("attempted")]
    queue: list[dict[str, Any]] = []
    used: set[str] = set()

    failed_units = {str(row["grammar_unit_id"]) for row in entries if row.get("outcome") in {"AUTO_FAIL", "HUMAN_REJECT"}}
    def add(row: Mapping[str, Any], reason: str) -> None:
        item_id = str(row["item_id"])
        if item_id in used or len(queue) >= 8:
            return
        used.add(item_id)
        queue.append({
            "item_id": item_id,
            "grammar_unit_id": str(row["grammar_unit_id"]),
            "canonical_egp_row_ids": list(row["canonical_egp_row_ids"]),
            "internal_stage": str(row["internal_stage"]),
            "skill": str(row["skill"]),
            "item_role": str(row["item_role"]),
            "evidence_dimension": str(row["evidence_dimension"]),
            "task_type": str(row["task_type"]),
            "reason_code": reason,
        })

    for row in sorted(unattempted, key=lambda r: (str(r["grammar_unit_id"]), str(r["skill"]), str(r["item_role"]), str(r["item_id"]))):
        if str(row["grammar_unit_id"]) in failed_units and row.get("item_role") == "practice":
            add(row, "AUTO_FAIL_REMEDIATION")
    unattempted_units = {str(row["grammar_unit_id"]) for row in unattempted} - attempted_units
    for row in sorted(unattempted, key=lambda r: (str(r["internal_stage"]), str(r["grammar_unit_id"]), str(r["skill"]), str(r["item_role"]), str(r["item_id"]))):
        if str(row["grammar_unit_id"]) in unattempted_units and row.get("item_role") == "practice":
            add(row, "UNATTEMPTED_UNIT_COVERAGE")
    for row in sorted(unattempted, key=lambda r: (skill_counts[str(r["skill"])], role_counts[str(r["item_role"])], str(r["internal_stage"]), str(r["item_id"]))):
        add(row, "SKILL_ROLE_BALANCE")

    if pending:
        state = "PASS_HUMAN_REVIEW_REQUIRED"
        stop_reason = "HUMAN_REVIEW_DECISIONS_REQUIRED"
        next_step = "E4S-A1V1-M12C1_HumanReviewDecisionMaterialization"
    elif auto_fail:
        state = "PASS_REMEDIATION_AND_EXPANSION_REQUIRED"
        stop_reason = "NONE"
        next_step = "E4S-A1V1-M12D_RepresentativePilotExpansion"
    else:
        state = "PASS_CONTINUE_EXPANSION"
        stop_reason = "NONE"
        next_step = "E4S-A1V1-M12D_RepresentativePilotExpansion"

    report = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": "EVIDENCE_QA_AND_ITERATION",
        "evidence_origin": expected_origin,
        "source_hashes": {
            "capture_manifest_sha256": sha256_value(manifest),
            "capture_safe_report_sha256": sha256_value(capture),
            "progress_ledger_sha256": sha256_value(ledger),
            "progress_query_index_sha256": sha256_value(query),
        },
        "evidence_summary": {
            "attempt_count": len(entries),
            "attempted_unit_count": len(attempted_units),
            "attempted_row_count": len(attempted_rows),
            "skill_attempt_counts": {"reading": skill_counts["reading"], "writing": skill_counts["writing"]},
            "role_attempt_counts": {"practice": role_counts["practice"], "assessment": role_counts["assessment"]},
            "outcome_counts": {name: outcome_counts[name] for name in OUTCOMES},
            "pending_human_review_count": pending,
            "auto_fail_count": auto_fail,
            "auto_pass_count": outcome_counts["AUTO_PASS"],
        },
        "coverage_progress": {
            "selectable_items": 184,
            "private_ready_units": 23,
            "private_ready_rows": 107,
            "attempted_item_percent": _percent(len(entries), 184),
            "attempted_unit_percent": _percent(len(attempted_units), 23),
            "attempted_row_percent": _percent(len(attempted_rows), 107),
            "pilot_completed": False,
        },
        "quality_gate": {
            "state": state,
            "human_review_required": pending > 0,
            "remediation_required": auto_fail > 0 or outcome_counts["HUMAN_REJECT"] > 0,
            "deterministic_evidence_valid": True,
        },
        "iteration_queue": {"candidate_count": len(queue), "maximum_batch_size": 8, "items": queue},
        "claim_boundaries": {
            "metadata_only_report": True,
            "private_responses_included": False,
            "learner_identity_included": False,
            "canonical_authority_write": False,
            "canonical_egp_mapping_changed": False,
            "public_delivery": False,
            "production_runtime_enabled": False,
            "a2_content_promoted": False,
            "audio_or_recording_processed": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "real_learner_pilot_completed": False,
            "test_fixture_counted_as_real_evidence": False,
        },
        "validation_status": REAL_STATUS if expected_origin == "REAL_LEARNER" else TEST_STATUS,
        "stop_reason": stop_reason,
        "next_short_step": next_step,
        "errors": [],
    }
    _safe_scan(report)
    _assert_schema(report)
    write_json_atomic(target / "real_evidence_qa_safe_report.json", report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--expected-origin", choices=["REAL_LEARNER", "TEST_FIXTURE"], required=True)
    args = parser.parse_args(argv)
    try:
        result = build_qa(args.input_root, args.output_root, expected_origin=args.expected_origin)
        print(json.dumps({
            "evidence_origin": result["evidence_origin"],
            "attempt_count": result["evidence_summary"]["attempt_count"],
            "auto_pass_count": result["evidence_summary"]["auto_pass_count"],
            "auto_fail_count": result["evidence_summary"]["auto_fail_count"],
            "pending_human_review_count": result["evidence_summary"]["pending_human_review_count"],
            "iteration_candidate_count": result["iteration_queue"]["candidate_count"],
            "validation_status": result["validation_status"],
            "stop_reason": result["stop_reason"],
            "next_short_step": result["next_short_step"],
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except (EvidenceQAError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
