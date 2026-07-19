#!/usr/bin/env python3
"""Build and evaluate the A1FS V1 real-learner breadth/transfer/repair pilot.

This milestone does not invent learner evidence and does not claim a Human Pilot from
CI fixtures. It binds the complete R3 breadth denominator, R4 supply state, the R5
private/safe evidence pair, the R7 repair-loop state, and an explicit real-learner
operator attestation. R8 may pass only from hash-bound, non-synthetic, completed
local-runtime sessions. Listening/Speaking media gaps remain visible for R10.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

TASK_ID = "A1FS-V1-R8_RealLearnerBreadthTransferAndRepairPilot"
CONTRACT_SCHEMA_VERSION = "a1fs.v1.r8.real_learner_pilot_contract.v1"
ATTESTATION_SCHEMA_VERSION = "a1fs.v1.r8.real_learner_attestation.v1"
REPORT_SCHEMA_VERSION = "a1fs.v1.r8.real_learner_pilot_report.v1"
STATUS = "PASS_A1FS_V1_R8_REAL_LEARNER_BREADTH_TRANSFER_REPAIR_PILOT_GATE_READY"
NEXT_SHORT_STEP = "A1FS-V1-R9_LongitudinalRetentionReliabilityAndProductOperation"
EVIDENCE_COLLECTION_STEP = "A1FS-V1-R8_CollectRealLearnerBreadthTransferAndRepairEvidence"

R3_TASK_ID = "A1FS-V1-R3_CompleteBreadthDenominatorCoverageAndGapPlanner"
R3_SCHEMA_VERSION = "a1fs.v1.r3.breadth_denominator_coverage.v1"
R3_STATUS = "PASS_A1FS_V1_R3_COMPLETE_BREADTH_DENOMINATOR_COVERAGE_GAP_PLANNER"
R4_TASK_ID = "A1FS-V1-R4_CentralQuestionSupplySkillProjectionAndCapacityGovernance"
R4_SCHEMA_VERSION = "a1fs.v1.r4.central_question_supply.v1"
R4_STATUS = "PASS_A1FS_V1_R4_CENTRAL_QUESTION_SUPPLY_CAPACITY_GOVERNANCE"
R5_TASK_ID = "A1FS-V1-R5_LocalEdgeRuntimeAndCompleteEvidenceCollector"
R5_PACKAGE_SCHEMA_VERSION = "a1fs.v1.r5.edge_evidence_package.v1"
R5_SAFE_SCHEMA_VERSION = "a1fs.v1.r5.edge_evidence_safe_summary.v1"
R5_STATUS = "PASS_A1FS_V1_R5_LOCAL_EDGE_RUNTIME_COMPLETE_EVIDENCE_COLLECTOR"
R7_TASK_ID = "A1FS-V1-R7_CollectorRuntimeAndCoverageGapRepairLoop"
R7_REPORT_SCHEMA_VERSION = "a1fs.v1.r7.repair_loop_safe_report.v1"
R7_STATUS = "PASS_A1FS_V1_R7_COLLECTOR_RUNTIME_COVERAGE_GAP_REPAIR_LOOP"

PILOT_STATES = {"PRECONDITION_BLOCKED", "EVIDENCE_REQUIRED", "IN_PROGRESS", "PASS", "FAIL"}
RESULT_STATES = {"NOT_EVALUATED", "PASS", "PARTIAL", "FAIL", "INSUFFICIENT_EVIDENCE", "NOT_APPLICABLE"}
EVIDENCE_LEVELS = {
    "E0_EXPOSURE", "E1_RECOGNITION", "E2_CONTROLLED_PRODUCTION",
    "E3_INDEPENDENT_PRODUCTION", "E4_CROSS_CONTEXT_TRANSFER",
    "E5_DELAYED_RETENTION", "E6_AUTHENTIC_TASK_PERFORMANCE",
}
R8_EVIDENCE_LEVELS = EVIDENCE_LEVELS - {"E5_DELAYED_RETENTION"}
DELAYED_RETENTION_LEVELS = {"E5_DELAYED_RETENTION"}
VALID_OUTCOMES = {"AUTO_PASS", "AUTO_FAIL", "HUMAN_APPROVE", "HUMAN_REJECT"}
PASS_OUTCOMES = {"AUTO_PASS", "HUMAN_APPROVE"}
SUPPLY_READY = "READY_FOR_LOCAL_SELECTION"
MEDIA_DEFERRED = "MEDIA_DEFERRED"
R3_BLOCKING_STATUSES = {
    "PROFILE_DEFINITION_REQUIRED", "CONTENT_MISSING", "ITEMS_MISSING", "BLOCKED_SYSTEM_ERROR",
}
BLOCKING_R7_ROUTES = {"CODE_FULLFIX", "CONTENT_EXPANSION", "AUTHORITY_REVIEW"}
OBSERVATION_RESULTS = (
    "language_accuracy", "meaning_success", "life_task_completion",
    "pragmatic_appropriacy", "independence", "initiative", "repair", "transfer",
)
DELIVERY_MODES = {"LOCAL_RUNTIME", "MANUAL_MEDIA_ALTERNATIVE", "AUTHENTIC_LIFE_TASK"}
HEX64 = set("0123456789abcdef")


class RealLearnerPilotError(ValueError):
    """Fail-closed R8 pilot error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RealLearnerPilotError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise RealLearnerPilotError(f"{code}_not_object")
    return value


def write_private(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def timezone_timestamp(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RealLearnerPilotError(code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RealLearnerPilotError(code) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RealLearnerPilotError(code)
    return value


def is_hex64(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 64 and set(text) <= HEX64


def validate_digest(value: Mapping[str, Any], key: str, code: str) -> None:
    core = {name: child for name, child in value.items() if name != key}
    if value.get(key) != digest(core):
        raise RealLearnerPilotError(code)


def _load_r3(path: Path) -> dict[str, Any]:
    value = read_json(path, "r3")
    if value.get("task_id") != R3_TASK_ID or value.get("schema_version") != R3_SCHEMA_VERSION or value.get("validation_status") != R3_STATUS:
        raise RealLearnerPilotError("r3_identity_or_status_invalid")
    validate_digest(value, "report_sha256", "r3_digest_invalid")
    cells = value.get("cells")
    if not isinstance(cells, list) or value.get("counts", {}).get("denominator_cell_count") != len(cells):
        raise RealLearnerPilotError("r3_cell_denominator_invalid")
    return value


def _load_r4(path: Path, r3_sha: str) -> dict[str, Any]:
    value = read_json(path, "r4")
    if value.get("task_id") != R4_TASK_ID or value.get("schema_version") != R4_SCHEMA_VERSION or value.get("validation_status") != R4_STATUS:
        raise RealLearnerPilotError("r4_identity_or_status_invalid")
    validate_digest(value, "report_sha256", "r4_digest_invalid")
    if value.get("source_bindings", {}).get("coverage_sha256") != r3_sha:
        raise RealLearnerPilotError("r4_r3_binding_mismatch")
    if not isinstance(value.get("cell_supply"), list):
        raise RealLearnerPilotError("r4_cell_supply_invalid")
    return value


def _load_r7(path: Path, *, r3_sha: str, r4_sha: str, r5_sha: str | None = None) -> dict[str, Any]:
    value = read_json(path, "r7_report")
    if value.get("task_id") != R7_TASK_ID or value.get("schema_version") != R7_REPORT_SCHEMA_VERSION or value.get("validation_status") != R7_STATUS:
        raise RealLearnerPilotError("r7_identity_or_status_invalid")
    validate_digest(value, "report_sha256", "r7_digest_invalid")
    bindings = value.get("source_bindings", {})
    if bindings.get("r3_report_sha256") != r3_sha or bindings.get("r4_report_sha256") != r4_sha:
        raise RealLearnerPilotError("r7_upstream_binding_mismatch")
    if r5_sha is not None and bindings.get("r5_summary_sha256") != r5_sha:
        raise RealLearnerPilotError("r7_r5_binding_mismatch")
    if not isinstance(value.get("work_items"), list):
        raise RealLearnerPilotError("r7_work_items_invalid")
    return value


def _dimensions(cell: Mapping[str, Any]) -> dict[str, list[str]]:
    source = cell.get("dimension_coverage")
    if not isinstance(source, Mapping):
        raise RealLearnerPilotError(f"r3_dimension_coverage_invalid:{cell.get('cell_id')}")
    result: dict[str, list[str]] = {}
    for name in ("skills", "support_levels", "initiative_levels", "variation_types", "transfer_distances", "evidence_levels"):
        row = source.get(name, {})
        required = row.get("required", []) if isinstance(row, Mapping) else []
        if not isinstance(required, list) or len(required) != len(set(required)):
            raise RealLearnerPilotError(f"r3_required_dimension_invalid:{cell.get('cell_id')}:{name}")
        result[name] = [str(item) for item in required]
    result["r8_evidence_levels"] = [item for item in result["evidence_levels"] if item in R8_EVIDENCE_LEVELS]
    result["r9_deferred_evidence_levels"] = [item for item in result["evidence_levels"] if item in DELAYED_RETENTION_LEVELS]
    return result


def build_pilot_contract(*, r3_path: Path, r4_path: Path, r7_report_path: Path) -> dict[str, Any]:
    r3 = _load_r3(r3_path)
    r4 = _load_r4(r4_path, r3["report_sha256"])
    r7 = _load_r7(r7_report_path, r3_sha=r3["report_sha256"], r4_sha=r4["report_sha256"])
    supply = {str(row.get("breadth_cell_id")): row for row in r4["cell_supply"] if isinstance(row, Mapping)}
    if len(supply) != len(r4["cell_supply"]):
        raise RealLearnerPilotError("r4_duplicate_or_invalid_cell_supply")
    planner_redeploy = {
        str(row.get("breadth_cell_id")) for row in r7["work_items"]
        if row.get("route") == "PLANNER_REDEPLOY" and row.get("work_state") in {"OPEN", "CLOSED"}
    }
    blocking_work = [
        {key: row.get(key) for key in ("work_item_id", "route", "severity", "work_state", "breadth_cell_id", "summary_code")}
        for row in r7["work_items"]
        if row.get("work_state") == "BLOCKED"
        or (row.get("work_state") == "OPEN" and row.get("route") in BLOCKING_R7_ROUTES)
    ]
    rows: list[dict[str, Any]] = []
    for cell in r3["cells"]:
        cell_id = str(cell.get("cell_id") or "")
        if not cell_id:
            raise RealLearnerPilotError("r3_cell_id_missing")
        dimensions = _dimensions(cell)
        supply_row = supply.get(cell_id)
        supply_status = str(supply_row.get("supply_status")) if supply_row else "SUPPLY_NOT_REGISTERED"
        status = str(cell.get("status"))
        if status in R3_BLOCKING_STATUSES:
            pilot_role, blocker = "PRECONDITION_BLOCKED", f"R3_{status}"
        elif supply_status == MEDIA_DEFERRED or status == "DEFERRED_MEDIA":
            pilot_role, blocker = "MEDIA_DEFERRED_TO_R10", None
        elif supply_status == SUPPLY_READY:
            pilot_role, blocker = "REAL_LEARNER_EVIDENCE_REQUIRED", None
        else:
            pilot_role, blocker = "PRECONDITION_BLOCKED", f"R4_{supply_status}"
        rows.append({
            "breadth_cell_id": cell_id,
            "capability_node_id": cell.get("capability_node_id"),
            "capability_id": cell.get("capability_id"),
            "life_task_id": cell.get("life_task_id"),
            "domain": cell.get("domain"),
            "r3_status": status,
            "r4_supply_status": supply_status,
            "pilot_role": pilot_role,
            "precondition_blocker": blocker,
            "reassessment_or_redeploy_required": cell_id in planner_redeploy,
            "required_dimensions": dimensions,
        })
    rows.sort(key=lambda row: row["breadth_cell_id"])
    required = [row for row in rows if row["pilot_role"] == "REAL_LEARNER_EVIDENCE_REQUIRED"]
    media = [row for row in rows if row["pilot_role"] == "MEDIA_DEFERRED_TO_R10"]
    blocked = [row for row in rows if row["pilot_role"] == "PRECONDITION_BLOCKED"]
    core = {
        "task_id": TASK_ID,
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "validation_status": STATUS,
        "private_local_only": True,
        "source_bindings": {
            "r3_report_sha256": r3["report_sha256"],
            "r4_report_sha256": r4["report_sha256"],
            "r7_report_sha256": r7["report_sha256"],
        },
        "counts": {
            "complete_breadth_denominator_count": len(rows),
            "real_learner_required_cell_count": len(required),
            "media_deferred_cell_count": len(media),
            "precondition_blocked_cell_count": len(blocked),
            "blocking_r7_work_item_count": len(blocking_work),
            "reassessment_or_redeploy_required_cell_count": sum(row["reassessment_or_redeploy_required"] for row in rows),
            "r9_deferred_requirement_count": sum(len(row["required_dimensions"]["r9_deferred_evidence_levels"]) for row in rows),
        },
        "cells": rows,
        "blocking_r7_work_items": blocking_work,
        "contract_ready_for_real_evidence": bool(required) and not blocked and not blocking_work,
        "claim_boundaries": {
            "real_learner_pilot_claimed": False,
            "synthetic_fixture_accepted": False,
            "complete_denominator_reduced": False,
            "media_completion_claimed": False,
            "retention_claimed": False,
            "a2_unlocked": False,
        },
        "next_short_step": EVIDENCE_COLLECTION_STEP,
    }
    return {**core, "contract_sha256": digest(core)}


def _load_contract(path: Path) -> dict[str, Any]:
    value = read_json(path, "pilot_contract")
    if value.get("task_id") != TASK_ID or value.get("schema_version") != CONTRACT_SCHEMA_VERSION or value.get("validation_status") != STATUS:
        raise RealLearnerPilotError("pilot_contract_identity_or_status_invalid")
    validate_digest(value, "contract_sha256", "pilot_contract_digest_invalid")
    if value.get("private_local_only") is not True:
        raise RealLearnerPilotError("pilot_contract_privacy_invalid")
    if value.get("counts", {}).get("complete_breadth_denominator_count") != len(value.get("cells", [])):
        raise RealLearnerPilotError("pilot_contract_denominator_invalid")
    return value


def _load_r5_pair(package_path: Path, safe_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    package = read_json(package_path, "r5_package")
    safe = read_json(safe_path, "r5_safe")
    if package.get("task_id") != R5_TASK_ID or package.get("schema_version") != R5_PACKAGE_SCHEMA_VERSION or package.get("validation_status") != R5_STATUS:
        raise RealLearnerPilotError("r5_package_identity_or_status_invalid")
    if safe.get("task_id") != R5_TASK_ID or safe.get("schema_version") != R5_SAFE_SCHEMA_VERSION or safe.get("validation_status") != R5_STATUS:
        raise RealLearnerPilotError("r5_safe_identity_or_status_invalid")
    validate_digest(package, "package_sha256", "r5_package_digest_invalid")
    validate_digest(safe, "summary_sha256", "r5_safe_digest_invalid")
    if package.get("private_local_only") is not True:
        raise RealLearnerPilotError("r5_package_privacy_invalid")
    if safe.get("learner_ref_sha256") != digest(package.get("learner_id")):
        raise RealLearnerPilotError("r5_learner_reference_mismatch")
    entries, safe_entries = package.get("entries"), safe.get("entries")
    if not isinstance(entries, list) or not isinstance(safe_entries, list):
        raise RealLearnerPilotError("r5_entries_invalid")
    if package.get("entries_sha256") != digest(entries) or safe.get("entries_sha256") != digest(safe_entries):
        raise RealLearnerPilotError("r5_entries_digest_invalid")
    projected = [{key: child for key, child in row.items() if key not in {"response", "operator_review"}} for row in entries]
    if projected != safe_entries:
        raise RealLearnerPilotError("r5_private_safe_projection_mismatch")
    if package.get("attempt_count") != len(entries) or safe.get("attempt_count") != len(safe_entries):
        raise RealLearnerPilotError("r5_attempt_denominator_invalid")
    return package, safe


def _validate_observation(row: Mapping[str, Any], *, operator_ref: str) -> dict[str, Any]:
    required = {
        "attempt_id", "session_id", "breadth_cell_id", "observed_at", "operator_ref",
        "delivery_mode", *OBSERVATION_RESULTS, "evidence_level", "evidence_refs",
    }
    if set(row) != required:
        raise RealLearnerPilotError(f"observation_shape_invalid:{row.get('attempt_id')}")
    if row.get("operator_ref") != operator_ref:
        raise RealLearnerPilotError(f"observation_operator_mismatch:{row.get('attempt_id')}")
    timezone_timestamp(row.get("observed_at"), f"observation_timestamp_invalid:{row.get('attempt_id')}")
    if row.get("delivery_mode") not in DELIVERY_MODES:
        raise RealLearnerPilotError(f"observation_delivery_mode_invalid:{row.get('attempt_id')}")
    for field in OBSERVATION_RESULTS:
        if row.get(field) not in RESULT_STATES:
            raise RealLearnerPilotError(f"observation_result_invalid:{row.get('attempt_id')}:{field}")
    if row.get("evidence_level") not in EVIDENCE_LEVELS:
        raise RealLearnerPilotError(f"observation_evidence_level_invalid:{row.get('attempt_id')}")
    refs = row.get("evidence_refs")
    if not isinstance(refs, list) or not refs or not all(isinstance(item, str) and item.strip() for item in refs):
        raise RealLearnerPilotError(f"observation_evidence_refs_invalid:{row.get('attempt_id')}")
    return deepcopy(dict(row))


def _load_attestation(path: Path, *, package_sha: str, safe_sha: str, learner_ref_sha: str) -> dict[str, Any]:
    value = read_json(path, "attestation")
    if value.get("task_id") != TASK_ID or value.get("schema_version") != ATTESTATION_SCHEMA_VERSION:
        raise RealLearnerPilotError("attestation_identity_invalid")
    validate_digest(value, "attestation_sha256", "attestation_digest_invalid")
    required = {
        "task_id", "schema_version", "evidence_origin", "synthetic_fixture",
        "learner_ref_sha256", "r5_package_sha256", "r5_summary_sha256",
        "operator_ref", "attested_at", "real_learner_present",
        "consent_or_guardian_authorization", "normal_learning_operation",
        "session_recovery_observed", "session_recovery_event_refs", "session_ids",
        "observation_records", "attestation_sha256",
    }
    if set(value) != required:
        raise RealLearnerPilotError("attestation_shape_invalid")
    if value.get("evidence_origin") != "REAL_LEARNER_SESSION" or value.get("synthetic_fixture") is not False:
        raise RealLearnerPilotError("synthetic_or_non_real_learner_evidence_forbidden")
    if value.get("learner_ref_sha256") != learner_ref_sha or value.get("r5_package_sha256") != package_sha or value.get("r5_summary_sha256") != safe_sha:
        raise RealLearnerPilotError("attestation_source_binding_mismatch")
    if not str(value.get("operator_ref") or "").strip():
        raise RealLearnerPilotError("attestation_operator_ref_missing")
    timezone_timestamp(value.get("attested_at"), "attestation_timestamp_invalid")
    for flag in ("real_learner_present", "consent_or_guardian_authorization", "normal_learning_operation", "session_recovery_observed"):
        if value.get(flag) is not True:
            raise RealLearnerPilotError(f"attestation_required_flag_false:{flag}")
    recovery_refs = value.get("session_recovery_event_refs")
    if not isinstance(recovery_refs, list) or not recovery_refs:
        raise RealLearnerPilotError("session_recovery_evidence_missing")
    sessions = value.get("session_ids")
    if not isinstance(sessions, list) or not sessions or len(sessions) != len(set(sessions)):
        raise RealLearnerPilotError("attestation_session_ids_invalid")
    observations = value.get("observation_records")
    if not isinstance(observations, list) or not observations:
        raise RealLearnerPilotError("attestation_observations_missing")
    normalized = [_validate_observation(row, operator_ref=value["operator_ref"]) for row in observations if isinstance(row, Mapping)]
    if len(normalized) != len(observations):
        raise RealLearnerPilotError("attestation_observation_not_object")
    ids = [row["attempt_id"] for row in normalized]
    if len(ids) != len(set(ids)):
        raise RealLearnerPilotError("attestation_duplicate_observation_attempt")
    return {**value, "observation_records": normalized}


def _required_dimension_gaps(cell: Mapping[str, Any], entries: Sequence[Mapping[str, Any]], observations: Mapping[str, Mapping[str, Any]]) -> dict[str, list[str]]:
    required = cell["required_dimensions"]
    valid_entries = [row for row in entries if row["attempt_id"] in observations]
    observed = {
        "skills": {str(row.get("skill")) for row in valid_entries},
        "support_levels": {str(row.get("support_level")) for row in valid_entries},
        "initiative_levels": {str(row.get("initiative_level")) for row in valid_entries},
        "variation_types": {str(row.get("interaction_variation")) for row in valid_entries},
        "transfer_distances": {str(row.get("transfer_distance")) for row in valid_entries},
        "r8_evidence_levels": {str(observations[row["attempt_id"]].get("evidence_level")) for row in valid_entries},
    }
    return {name: sorted(set(required.get(name, [])) - observed.get(name, set())) for name in observed}


def _performance_errors(entries: Sequence[Mapping[str, Any]], observations: Mapping[str, Mapping[str, Any]]) -> list[str]:
    errors: list[str] = []
    for row in entries:
        observation = observations.get(str(row.get("attempt_id")))
        if not observation:
            continue
        attempt_id = str(row["attempt_id"])
        if row.get("outcome") not in PASS_OUTCOMES:
            errors.append(f"attempt_not_pass:{attempt_id}")
        for field in ("language_accuracy", "meaning_success", "life_task_completion", "pragmatic_appropriacy"):
            if observation.get(field) != "PASS":
                errors.append(f"{field}_not_pass:{attempt_id}")
        if row.get("support_level") == "S0_INDEPENDENT" and observation.get("independence") != "PASS":
            errors.append(f"independence_not_pass:{attempt_id}")
        if row.get("initiative_level") in {"INDEPENDENT_INITIATION", "SUSTAIN_INTERACTION", "REPAIR_AND_CLOSE_TASK"} and observation.get("initiative") != "PASS":
            errors.append(f"initiative_not_pass:{attempt_id}")
        if row.get("interaction_variation") in {"UNEXPECTED_EVENT", "REPAIR_REQUIRED"} and observation.get("repair") != "PASS":
            errors.append(f"repair_not_pass:{attempt_id}")
        if row.get("transfer_distance") not in {None, "NONE"} and observation.get("transfer") != "PASS":
            errors.append(f"transfer_not_pass:{attempt_id}")
    return errors


def _reassessment_errors(cell: Mapping[str, Any], all_entries: Sequence[Mapping[str, Any]]) -> list[str]:
    if not cell.get("reassessment_or_redeploy_required"):
        return []
    rows = sorted(all_entries, key=lambda row: (str(row.get("submitted_at")), str(row.get("attempt_id"))))
    reassess = [row for row in rows if row.get("purpose") == "REASSESSMENT" and row.get("outcome") in PASS_OUTCOMES and row.get("validity_status") == "VALID"]
    if not reassess:
        return ["reassessment_pass_missing"]
    previous_fingerprints = {
        str(row.get("stimulus_fingerprint")) for row in rows
        if row.get("purpose") in {"CORE_PRACTICE", "REMEDIATION"} and row.get("stimulus_fingerprint")
    }
    if any(str(row.get("stimulus_fingerprint")) not in previous_fingerprints for row in reassess):
        return []
    return ["reassessment_stimulus_not_distinct"]


def evaluate_pilot(*, contract_path: Path, r5_package_path: Path, r5_safe_path: Path, r7_report_path: Path, attestation_path: Path) -> dict[str, Any]:
    contract = _load_contract(contract_path)
    package, safe = _load_r5_pair(r5_package_path, r5_safe_path)
    r7 = _load_r7(
        r7_report_path,
        r3_sha=contract["source_bindings"]["r3_report_sha256"],
        r4_sha=contract["source_bindings"]["r4_report_sha256"],
        r5_sha=safe["summary_sha256"],
    )
    if r7["report_sha256"] != contract["source_bindings"]["r7_report_sha256"]:
        raise RealLearnerPilotError("contract_r7_report_binding_mismatch")
    attestation = _load_attestation(
        attestation_path,
        package_sha=package["package_sha256"],
        safe_sha=safe["summary_sha256"],
        learner_ref_sha=safe["learner_ref_sha256"],
    )
    entries_by_attempt = {str(row.get("attempt_id")): row for row in package["entries"]}
    if len(entries_by_attempt) != len(package["entries"]):
        raise RealLearnerPilotError("r5_duplicate_attempt_id")
    observations = {row["attempt_id"]: row for row in attestation["observation_records"]}
    for attempt_id, observation in observations.items():
        entry = entries_by_attempt.get(attempt_id)
        if not entry:
            raise RealLearnerPilotError(f"observation_attempt_not_in_r5:{attempt_id}")
        if observation["session_id"] != entry.get("session_id") or observation["breadth_cell_id"] != entry.get("breadth_cell_id"):
            raise RealLearnerPilotError(f"observation_attempt_binding_mismatch:{attempt_id}")
        if entry.get("session_id") not in attestation["session_ids"]:
            raise RealLearnerPilotError(f"observation_session_not_attested:{attempt_id}")
        if entry.get("session_state") != "COMPLETED":
            raise RealLearnerPilotError(f"observation_session_not_completed:{attempt_id}")
        if entry.get("validity_status") != "VALID" or entry.get("outcome") not in VALID_OUTCOMES:
            raise RealLearnerPilotError(f"observation_attempt_not_valid_resolved:{attempt_id}")
    valid_resolved = [
        row for row in package["entries"]
        if row.get("validity_status") == "VALID" and row.get("outcome") in VALID_OUTCOMES and row.get("session_state") == "COMPLETED"
    ]
    excluded = [row for row in package["entries"] if row not in valid_resolved]
    entries_by_cell: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in valid_resolved:
        entries_by_cell[str(row.get("breadth_cell_id"))].append(row)
    cell_results: list[dict[str, Any]] = []
    all_dimension_gaps = all_performance_errors = all_reassessment_errors = 0
    for cell in contract["cells"]:
        cell_id = cell["breadth_cell_id"]
        rows = entries_by_cell.get(cell_id, [])
        observed_rows = [row for row in rows if row["attempt_id"] in observations]
        if cell["pilot_role"] == "MEDIA_DEFERRED_TO_R10":
            state, gaps, performance, reassessment = "MEDIA_DEFERRED_TO_R10", {}, [], []
        elif cell["pilot_role"] == "PRECONDITION_BLOCKED":
            state, gaps, performance, reassessment = "PRECONDITION_BLOCKED", {}, [], []
        else:
            gaps = _required_dimension_gaps(cell, observed_rows, observations)
            performance = _performance_errors(observed_rows, observations)
            reassessment = _reassessment_errors(cell, rows)
            missing_observation_count = len([row for row in rows if row["attempt_id"] not in observations])
            if not observed_rows:
                state = "REAL_LEARNER_EVIDENCE_REQUIRED"
            elif any(gaps.values()) or missing_observation_count:
                state = "IN_PROGRESS"
            elif performance or reassessment:
                state = "FAIL"
            else:
                state = "PASS"
            all_dimension_gaps += sum(len(value) for value in gaps.values()) + missing_observation_count
            all_performance_errors += len(performance)
            all_reassessment_errors += len(reassessment)
        cell_results.append({
            "breadth_cell_id": cell_id,
            "pilot_role": cell["pilot_role"],
            "pilot_state": state,
            "valid_resolved_attempt_count": len(rows),
            "observed_attempt_count": len(observed_rows),
            "dimension_gaps": gaps,
            "performance_errors": performance,
            "reassessment_errors": reassessment,
            "r9_deferred_evidence_levels": cell["required_dimensions"]["r9_deferred_evidence_levels"],
        })
    required_results = [row for row in cell_results if row["pilot_role"] == "REAL_LEARNER_EVIDENCE_REQUIRED"]
    media_results = [row for row in cell_results if row["pilot_role"] == "MEDIA_DEFERRED_TO_R10"]
    blocked_results = [row for row in cell_results if row["pilot_role"] == "PRECONDITION_BLOCKED"]
    r7_blocking = [
        row for row in r7["work_items"]
        if row.get("work_state") == "BLOCKED"
        or (row.get("work_state") == "OPEN" and row.get("route") in BLOCKING_R7_ROUTES)
    ]
    gates = {
        "COMPLETE_DENOMINATOR_PRESERVED": contract["counts"]["complete_breadth_denominator_count"] == len(cell_results),
        "REAL_LEARNER_ATTESTED": True,
        "NO_SYNTHETIC_EVIDENCE": attestation["synthetic_fixture"] is False,
        "R5_PRIVATE_SAFE_BINDING_VALID": True,
        "R7_NO_BLOCKING_TECHNICAL_CONTENT_OR_AUTHORITY_GAPS": not r7_blocking,
        "NO_PRECONDITION_BLOCKED_BREADTH_CELLS": not blocked_results,
        "ALL_REQUIRED_CELLS_HAVE_OBSERVED_EVIDENCE": bool(required_results) and all(row["observed_attempt_count"] > 0 for row in required_results),
        "ALL_SOURCE_REQUIRED_DIMENSIONS_COVERED": all_dimension_gaps == 0,
        "LANGUAGE_MEANING_LIFE_TASK_PRAGMATIC_GATES_PASS": all_performance_errors == 0,
        "INDEPENDENCE_INITIATIVE_REPAIR_TRANSFER_GATES_PASS": all_performance_errors == 0,
        "DIFFERENT_ITEM_REASSESSMENT_OR_REDEPLOY_PASS": all_reassessment_errors == 0,
        "INVALID_OR_UNRESOLVED_EVIDENCE_EXCLUDED": all(row.get("validity_status") != "VALID" or row.get("outcome") not in VALID_OUTCOMES or row.get("session_state") != "COMPLETED" for row in excluded),
        "SESSION_RECOVERY_OBSERVED": attestation["session_recovery_observed"] is True and bool(attestation["session_recovery_event_refs"]),
        "MEDIA_DEFERRED_REMAINS_VISIBLE": len(media_results) == contract["counts"]["media_deferred_cell_count"],
        "A2_LOCK_PRESERVED": True,
    }
    if blocked_results or r7_blocking:
        pilot_state = "PRECONDITION_BLOCKED"
    elif required_results and all(row["pilot_state"] == "PASS" for row in required_results) and all(gates.values()):
        pilot_state = "PASS"
    elif any(row["pilot_state"] == "FAIL" for row in required_results):
        pilot_state = "FAIL"
    elif any(row["observed_attempt_count"] > 0 for row in required_results):
        pilot_state = "IN_PROGRESS"
    else:
        pilot_state = "EVIDENCE_REQUIRED"
    core = {
        "task_id": TASK_ID,
        "schema_version": REPORT_SCHEMA_VERSION,
        "validation_status": STATUS,
        "private_local_only": True,
        "pilot_state": pilot_state,
        "source_bindings": {
            "contract_sha256": contract["contract_sha256"],
            "r3_report_sha256": contract["source_bindings"]["r3_report_sha256"],
            "r4_report_sha256": contract["source_bindings"]["r4_report_sha256"],
            "r5_package_sha256": package["package_sha256"],
            "r5_summary_sha256": safe["summary_sha256"],
            "r7_report_sha256": r7["report_sha256"],
            "attestation_sha256": attestation["attestation_sha256"],
            "learner_ref_sha256": safe["learner_ref_sha256"],
        },
        "counts": {
            "complete_breadth_denominator_count": len(cell_results),
            "real_learner_required_cell_count": len(required_results),
            "passed_required_cell_count": sum(row["pilot_state"] == "PASS" for row in required_results),
            "in_progress_required_cell_count": sum(row["pilot_state"] in {"IN_PROGRESS", "REAL_LEARNER_EVIDENCE_REQUIRED"} for row in required_results),
            "failed_required_cell_count": sum(row["pilot_state"] == "FAIL" for row in required_results),
            "media_deferred_cell_count": len(media_results),
            "precondition_blocked_cell_count": len(blocked_results),
            "source_attempt_count": len(package["entries"]),
            "valid_resolved_completed_attempt_count": len(valid_resolved),
            "excluded_attempt_count": len(excluded),
            "attested_observation_count": len(observations),
            "dimension_gap_count": all_dimension_gaps,
            "performance_error_count": all_performance_errors,
            "reassessment_error_count": all_reassessment_errors,
        },
        "gates": gates,
        "cells": cell_results,
        "claim_boundaries": {
            "real_learner_pilot_claimed": pilot_state == "PASS",
            "synthetic_fixture_accepted": False,
            "mastery_written": False,
            "retention_confirmed": False,
            "media_completion_claimed": False,
            "true_four_skill_release_claimed": False,
            "learner_release_approved": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP if pilot_state == "PASS" else EVIDENCE_COLLECTION_STEP,
    }
    return {**core, "report_sha256": digest(core)}


def attestation_registry(*, learner_ref_sha256: str, r5_package_sha256: str, r5_summary_sha256: str, operator_ref: str, attested_at: str, session_ids: Sequence[str], observations: Sequence[Mapping[str, Any]], session_recovery_event_refs: Sequence[str]) -> dict[str, Any]:
    if not is_hex64(learner_ref_sha256) or not is_hex64(r5_package_sha256) or not is_hex64(r5_summary_sha256):
        raise RealLearnerPilotError("attestation_source_hash_invalid")
    core = {
        "task_id": TASK_ID,
        "schema_version": ATTESTATION_SCHEMA_VERSION,
        "evidence_origin": "REAL_LEARNER_SESSION",
        "synthetic_fixture": False,
        "learner_ref_sha256": learner_ref_sha256,
        "r5_package_sha256": r5_package_sha256,
        "r5_summary_sha256": r5_summary_sha256,
        "operator_ref": operator_ref,
        "attested_at": timezone_timestamp(attested_at, "attestation_timestamp_invalid"),
        "real_learner_present": True,
        "consent_or_guardian_authorization": True,
        "normal_learning_operation": True,
        "session_recovery_observed": True,
        "session_recovery_event_refs": list(session_recovery_event_refs),
        "session_ids": list(session_ids),
        "observation_records": [deepcopy(dict(row)) for row in observations],
    }
    return {**core, "attestation_sha256": digest(core)}


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    contract = commands.add_parser("build-contract")
    contract.add_argument("--r3", type=Path, required=True)
    contract.add_argument("--r4", type=Path, required=True)
    contract.add_argument("--r7-report", type=Path, required=True)
    contract.add_argument("--output", type=Path, required=True)
    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("--contract", type=Path, required=True)
    evaluate.add_argument("--r5-package", type=Path, required=True)
    evaluate.add_argument("--r5-safe", type=Path, required=True)
    evaluate.add_argument("--r7-report", type=Path, required=True)
    evaluate.add_argument("--attestation", type=Path, required=True)
    evaluate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "build-contract":
        result = build_pilot_contract(r3_path=args.r3, r4_path=args.r4, r7_report_path=args.r7_report)
    else:
        result = evaluate_pilot(
            contract_path=args.contract, r5_package_path=args.r5_package,
            r5_safe_path=args.r5_safe, r7_report_path=args.r7_report,
            attestation_path=args.attestation,
        )
    write_private(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
