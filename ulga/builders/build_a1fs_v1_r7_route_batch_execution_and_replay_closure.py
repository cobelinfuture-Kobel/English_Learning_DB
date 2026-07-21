#!/usr/bin/env python3
"""Classify real R5 evidence for R7 Planner redeployments and prepare safe sessions."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

TASK_ID = "A1FS-V1-R7_RouteBatchExecutionAndReplayClosure"
INTAKE_SCHEMA = "a1fs.v1.r7.real_evidence_intake.v1"
INTAKE_SAFE_SCHEMA = "a1fs.v1.r7.real_evidence_intake_safe.v1"
SESSION_SCHEMA = "a1fs.v1.r7.real_learner_session_batch.v1"
SESSION_SAFE_SCHEMA = "a1fs.v1.r7.real_learner_session_batch_safe.v1"
REPLAY_SCHEMA = "a1fs.v1.r7.route_batch_replay_result.v1"
STATUS = "PASS_R7_ROUTE_BATCH_PREFLIGHT_AND_REAL_EVIDENCE_INTAKE_READY"
CLASSIFICATIONS = (
    "VALID_REAL_EVIDENCE_READY", "HUMAN_SCORING_REQUIRED", "LEARNER_ATTEMPT_MISSING",
    "CANDIDATE_BINDING_MISMATCH", "DEPLOYMENT_BINDING_MISMATCH", "EVIDENCE_INVALIDATED",
    "SYSTEM_ERROR_RETRY_REQUIRED", "DUPLICATE_EVIDENCE_IGNORED",
)


class ExecutionError(RuntimeError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ExecutionError(f"json_object_required:{path.name}")
    return value


def atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _artifact_sha(value: Mapping[str, Any], field: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or len(result) != 64:
        raise ExecutionError(f"artifact_digest_missing:{field}")
    return result


def _validate_digest(value: Mapping[str, Any], field: str) -> str:
    actual = _artifact_sha(value, field)
    if actual != digest({key: child for key, child in value.items() if key != field}):
        raise ExecutionError(f"artifact_digest_invalid:{field}")
    return actual


def _timestamp(previous: Mapping[str, Any] | None, source: Mapping[str, Any]) -> str:
    if (previous and isinstance(previous.get("generated_at"), str)
            and all(previous.get(key) == value for key, value in source.items())):
        return str(previous["generated_at"])
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _classification(deployment: Mapping[str, Any], attempts: Sequence[Mapping[str, Any]]) -> tuple[str, Mapping[str, Any] | None, int]:
    if not attempts:
        return "LEARNER_ATTEMPT_MISSING", None, 0
    exact = [row for row in attempts if row.get("breadth_cell_id") == deployment.get("breadth_cell_id")]
    if not exact:
        return "DEPLOYMENT_BINDING_MISMATCH", attempts[-1], 0
    bound = [row for row in exact if row.get("stimulus_fingerprint") == deployment.get("selected_stimulus_fingerprint")]
    if not bound:
        return "CANDIDATE_BINDING_MISMATCH", exact[-1], 0
    unique: dict[str, Mapping[str, Any]] = {}
    duplicate_count = 0
    for row in bound:
        identity = str(row.get("attempt_hash") or row.get("attempt_id") or "")
        if not identity or identity in unique:
            duplicate_count += 1
        else:
            unique[identity] = row
    selected = sorted(unique.values(), key=lambda row: str(row.get("submitted_at") or ""))[-1]
    validity = str(selected.get("validity_status") or "")
    telemetry = str(selected.get("telemetry_status") or "")
    if "SYSTEM_ERROR" in validity or "SYSTEM_ERROR" in telemetry:
        return "SYSTEM_ERROR_RETRY_REQUIRED", selected, duplicate_count
    if validity not in {"VALID", "PASS", "VALID_REAL_EVIDENCE"}:
        return "EVIDENCE_INVALIDATED", selected, duplicate_count
    if selected.get("human_review_required") is True:
        review = selected.get("operator_review")
        if not isinstance(review, Mapping) or review.get("status") not in {"PASS", "COMPLETED", "APPROVED"}:
            return "HUMAN_SCORING_REQUIRED", selected, duplicate_count
    required = ("attempt_id", "session_id", "item_id", "response", "submitted_at", "score", "outcome")
    if any(selected.get(key) is None for key in required):
        return "EVIDENCE_INVALIDATED", selected, duplicate_count
    return "VALID_REAL_EVIDENCE_READY", selected, duplicate_count


def build(*, controller: Mapping[str, Any], queue: Mapping[str, Any], deployment_queue: Mapping[str, Any],
          bank: Mapping[str, Any], packages: Sequence[Mapping[str, Any]], previous_session: Mapping[str, Any] | None = None
          ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    counts = deployment_queue.get("counts", {})
    deployments = deployment_queue.get("deployments")
    items = bank.get("items")
    if controller.get("next_short_step") != TASK_ID or not isinstance(deployments, list) or not isinstance(items, list):
        raise ExecutionError("source_contract_invalid")
    _validate_digest(controller, "controller_sha256")
    _validate_digest(queue, "queue_sha256")
    _validate_digest(deployment_queue, "deployment_queue_sha256")
    _validate_digest(bank, "bank_sha256")
    if len(deployments) != 209 or counts.get("ready_for_real_learner_session_count") != 209:
        raise ExecutionError("planner_denominator_or_supply_invalid")
    if counts.get("blocked_approved_supply_required_count") != 0:
        raise ExecutionError("planner_supply_blocked")
    if any(item.get("level") == "A2" for item in items):
        raise ExecutionError("a2_unlock_detected")
    bindings = deployment_queue.get("source_bindings", {})
    if bindings.get("r7_queue_sha256") != queue.get("queue_sha256"):
        raise ExecutionError("deployment_queue_r7_binding_mismatch")
    if bindings.get("r4_bank_sha256") != bank.get("bank_sha256"):
        raise ExecutionError("deployment_queue_r4_binding_mismatch")
    bank_by_id = {str(item.get("item_id")): item for item in items}
    attempt_by_item: dict[str, list[Mapping[str, Any]]] = {}
    synthetic_count = 0
    package_refs: list[dict[str, Any]] = []
    real_attempt_count = 0
    for package in packages:
        _validate_digest(package, "package_sha256")
        entries = package.get("entries", [])
        if not isinstance(entries, list):
            raise ExecutionError("evidence_entries_invalid")
        package_refs.append({"package_sha256": _artifact_sha(package, "package_sha256"), "attempt_count": len(entries)})
        for attempt in entries:
            if not isinstance(attempt, Mapping):
                raise ExecutionError("attempt_object_required")
            if attempt.get("synthetic") is True or attempt.get("simulated") is True:
                synthetic_count += 1
                continue
            real_attempt_count += 1
            attempt_by_item.setdefault(str(attempt.get("item_id") or ""), []).append(attempt)
    if synthetic_count:
        raise ExecutionError("synthetic_evidence_prohibited")
    rows: list[dict[str, Any]] = []
    duplicate_total = 0
    for deployment in deployments:
        item_id = str(deployment.get("selected_item_id") or "")
        candidate = bank_by_id.get(item_id)
        if not candidate or candidate.get("candidate_sha256") is None:
            raise ExecutionError(f"selected_candidate_missing:{item_id}")
        if candidate.get("stimulus_fingerprint") != deployment.get("selected_stimulus_fingerprint"):
            raise ExecutionError(f"deployment_candidate_drift:{item_id}")
        classification, attempt, duplicate_count = _classification(deployment, attempt_by_item.get(item_id, []))
        duplicate_total += duplicate_count
        rows.append({
            "work_item_id": deployment["work_item_id"], "finding_id": deployment["finding_id"],
            "deployment_identity": digest(deployment), "item_id": item_id,
            "candidate_sha256": candidate["candidate_sha256"],
            "stimulus_fingerprint": candidate["stimulus_fingerprint"], "classification": classification,
            "evidence_identity": (attempt or {}).get("attempt_hash"), "attempt_id": (attempt or {}).get("attempt_id"),
        })
    class_counts = Counter(row["classification"] for row in rows)
    class_counts["DUPLICATE_EVIDENCE_IGNORED"] = duplicate_total
    source = {
        "source_controller_sha256": _artifact_sha(controller, "controller_sha256"),
        "source_queue_sha256": _artifact_sha(queue, "queue_sha256"),
        "source_deployment_queue_sha256": _artifact_sha(deployment_queue, "deployment_queue_sha256"),
        "source_r4_bank_sha256": _artifact_sha(bank, "bank_sha256"),
    }
    intake_core = {"task_id": TASK_ID, "schema_version": INTAKE_SCHEMA, "validation_status": STATUS,
                   "private_local_only": True, "source_bindings": source, "evidence_packages": package_refs,
                   "counts": {"work_item_count": len(rows), "real_evidence_package_count": len(packages),
                              "real_attempt_count": real_attempt_count, "synthetic_evidence_count": 0,
                              **{key.lower() + "_count": int(class_counts[key]) for key in CLASSIFICATIONS}},
                   "classifications": rows, "a2_unlocked": False}
    intake = {**intake_core, "intake_sha256": digest(intake_core)}
    safe_core = {"task_id": TASK_ID, "schema_version": INTAKE_SAFE_SCHEMA, "validation_status": STATUS,
                 "source_bindings": source, "counts": intake["counts"], "a2_unlocked": False}
    intake_safe = {**safe_core, "report_sha256": digest(safe_core)}
    missing = [row for row in rows if row["classification"] in {"LEARNER_ATTEMPT_MISSING", "SYSTEM_ERROR_RETRY_REQUIRED"}]
    generated_at = _timestamp(previous_session, source)
    batches = []
    dep_by_work = {row["work_item_id"]: row for row in deployments}
    for index, row in enumerate(missing, 1):
        dep = dep_by_work[row["work_item_id"]]
        candidate = bank_by_id[row["item_id"]]
        batches.append({"batch_id": f"R7_REAL_SESSION_BATCH_{index:03d}", "work_item_ids": [row["work_item_id"]],
                        "deployment_identities": [row["deployment_identity"]],
                        "candidate_identities": [{"item_id": row["item_id"], "candidate_sha256": row["candidate_sha256"],
                                                  "stimulus_fingerprint": row["stimulus_fingerprint"]}],
                        "skill_distribution": {str(candidate["skill"]): 1},
                        "response_mode_distribution": {str(candidate["learner_contract"]["response_mode"]): 1},
                        "human_review_required_count": int(candidate["private_scoring_contract"].get("human_review_fallback") is True),
                        "runtime_launch_contract": {"builder": deployment_queue["runtime_consumer_contract"]["consumer_builder"],
                            "execution_order": "SEQUENTIAL_ONE_ACTIVE_SESSION_PER_LEARNER", "planned_item_count": 1,
                            "start_command_template": deployment_queue["runtime_consumer_contract"]["start_command_template"]},
                        "evidence_export_destination": "r5_exports/<learner_ref>/<session_id>"})
    session_core = {"task_id": TASK_ID, "schema_version": SESSION_SCHEMA, "private_local_only": True,
                    **source, "generated_at": generated_at, "remaining_work_item_count": len(missing),
                    "learner_assignment_policy": "OPERATOR_ASSIGNED_DEIDENTIFIED_LEARNER_ONE_ACTIVE_SESSION",
                    "session_batch_count": len(batches), "session_batches": batches}
    session = {**session_core, "manifest_sha256": digest(session_core)}
    session_safe_core = {"task_id": TASK_ID, "schema_version": SESSION_SAFE_SCHEMA, "validation_status": STATUS,
                         "source_controller_sha256": source["source_controller_sha256"], "generated_at": generated_at,
                         "remaining_work_item_count": len(missing), "session_batch_count": len(batches),
                         "maximum_items_per_batch": max((len(row["work_item_ids"]) for row in batches), default=0),
                         "a2_unlocked": False}
    session_safe = {**session_safe_core, "report_sha256": digest(session_safe_core)}
    valid = int(class_counts["VALID_REAL_EVIDENCE_READY"])
    replay_core = {"task_id": TASK_ID, "schema_version": REPLAY_SCHEMA, "validation_status": STATUS,
                   "source_bindings": source, "replay_attempted_count": valid, "replay_closed_count": 0,
                   "replay_failed_count": 0, "closures": [],
                   "stop_reason": "REAL_LEARNER_EVIDENCE_REQUIRED" if missing else "REPLAY_CLOSURE_REQUIRED"}
    replay = {**replay_core, "replay_sha256": digest(replay_core)}
    return intake, intake_safe, session, session_safe, replay


def safe_scan(value: Any) -> None:
    forbidden = {"response", "learner_id", "learner_ref", "accepted_texts", "private_scoring_contract", "reviewer_notes"}
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in forbidden:
                raise ExecutionError(f"safe_private_field:{key}")
            safe_scan(child)
    elif isinstance(value, list):
        for child in value:
            safe_scan(child)
    elif isinstance(value, str) and Path(value).is_absolute():
        raise ExecutionError("safe_absolute_path")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--controller", type=Path, required=True); parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--deployment-queue", type=Path, required=True); parser.add_argument("--r4-bank", type=Path, required=True)
    parser.add_argument("--evidence-package", type=Path, action="append", default=[])
    parser.add_argument("--intake-output", type=Path, required=True); parser.add_argument("--intake-safe-output", type=Path, required=True)
    parser.add_argument("--session-output", type=Path, required=True); parser.add_argument("--session-safe-output", type=Path, required=True)
    parser.add_argument("--replay-output", type=Path, required=True)
    args = parser.parse_args()
    previous = read_json(args.session_output) if args.session_output.exists() else None
    values = build(controller=read_json(args.controller), queue=read_json(args.queue),
                   deployment_queue=read_json(args.deployment_queue), bank=read_json(args.r4_bank),
                   packages=[read_json(path) for path in args.evidence_package], previous_session=previous)
    safe_scan(values[1]); safe_scan(values[3])
    for path, value in zip((args.intake_output, args.intake_safe_output, args.session_output, args.session_safe_output, args.replay_output), values):
        atomic_write(path, value)
    print(json.dumps({"validation_status": STATUS, "counts": values[0]["counts"],
                      "session_batch_count": values[2]["session_batch_count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
