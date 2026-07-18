#!/usr/bin/env python3
"""Classify A1FS gaps, route repairs, and close them only after replay gates.

Task: A1FS-V1-R7_CollectorRuntimeAndCoverageGapRepairLoop

The builder consumes R3/R4/R5/R6 outputs and optional explicit technical findings.
It creates an executable work queue for VSCode/Codex, content expansion, planner
redeployment, or Authority review. It never edits code, canonical Authority,
mastery, PracticeBank, planner policy, or A2 state. Repair results are hash-bound
and close work only when every route-specific CI/replay gate passes.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import sys
from collections import Counter
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_r1_evidence_validity_system_error_governance as r1
from ulga.builders import build_a1fs_v1_r3_complete_breadth_denominator_coverage_gap_planner as r3
from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4
from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5
from ulga.builders import build_a1fs_v1_r6_gpt_diagnostic_package_controlled_recommendation_gate as r6

TASK_ID = "A1FS-V1-R7_CollectorRuntimeAndCoverageGapRepairLoop"
QUEUE_SCHEMA_VERSION = "a1fs.v1.r7.gap_repair_work_queue.v1"
FINDING_SCHEMA_VERSION = "a1fs.v1.r7.explicit_finding_registry.v1"
RESULT_SCHEMA_VERSION = "a1fs.v1.r7.repair_result_registry.v1"
CLOSED_SCHEMA_VERSION = "a1fs.v1.r7.repair_closure_queue.v1"
REPORT_SCHEMA_VERSION = "a1fs.v1.r7.repair_loop_safe_report.v1"
STATUS = "PASS_A1FS_V1_R7_COLLECTOR_RUNTIME_COVERAGE_GAP_REPAIR_LOOP"
NEXT_SHORT_STEP = "A1FS-V1-R8_RealLearnerBreadthTransferAndRepairPilot"

FINDING_TYPES = {
    "EVIDENCE_FIELD_MISSING", "EVIDENCE_INVALID", "COLLECTOR_BUG",
    "UI_SERIALIZATION_BUG", "CONTENT_CAPACITY_INSUFFICIENT", "VALIDATOR_GAP",
    "COVERAGE_REQUIREMENT_GAP", "PEDAGOGICAL_EVIDENCE_INSUFFICIENT",
    "AUTHORITY_DECISION_REQUIRED",
}
ROUTES = {"CODE_FULLFIX", "CONTENT_EXPANSION", "PLANNER_REDEPLOY", "AUTHORITY_REVIEW"}
SEVERITIES = {"P0", "P1", "P2", "P3"}
RESULT_STATES = {"PASS", "FAIL", "BLOCKED"}
WORK_STATES = {"OPEN", "CLOSED", "BLOCKED"}
CI_CONCLUSIONS = {"success", "failure", "cancelled", "skipped", "neutral", "timed_out", "action_required"}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")

ROUTE_BY_FINDING = {
    "EVIDENCE_FIELD_MISSING": "CODE_FULLFIX",
    "EVIDENCE_INVALID": "CODE_FULLFIX",
    "COLLECTOR_BUG": "CODE_FULLFIX",
    "UI_SERIALIZATION_BUG": "CODE_FULLFIX",
    "CONTENT_CAPACITY_INSUFFICIENT": "CONTENT_EXPANSION",
    "VALIDATOR_GAP": "CODE_FULLFIX",
    "COVERAGE_REQUIREMENT_GAP": "AUTHORITY_REVIEW",
    "PEDAGOGICAL_EVIDENCE_INSUFFICIENT": "PLANNER_REDEPLOY",
    "AUTHORITY_DECISION_REQUIRED": "AUTHORITY_REVIEW",
}

ALLOWED_PATHS = {
    "EVIDENCE_FIELD_MISSING": [
        "ulga/builders/build_a1fs_v1_r5_*", "ulga/validators/validate_a1fs_v1_r5_*",
        "tests/ulga/test_a1fs_v1_r5_*", ".github/workflows/a1fs-v1-r5-*",
    ],
    "EVIDENCE_INVALID": [
        "ulga/builders/build_a1fs_v1_r1_*", "ulga/builders/build_a1fs_v1_r5_*",
        "ulga/validators/validate_a1fs_v1_r1_*", "ulga/validators/validate_a1fs_v1_r5_*",
        "tests/ulga/test_a1fs_v1_r1_*", "tests/ulga/test_a1fs_v1_r5_*",
        ".github/workflows/a1fs-v1-r1-*", ".github/workflows/a1fs-v1-r5-*",
    ],
    "COLLECTOR_BUG": [
        "ulga/builders/build_a1fs_v1_r5_*", "ulga/validators/validate_a1fs_v1_r5_*",
        "tests/ulga/test_a1fs_v1_r5_*", ".github/workflows/a1fs-v1-r5-*",
    ],
    "UI_SERIALIZATION_BUG": [
        "ulga/builders/build_a1fs_v1_r5_*", "tests/ulga/test_a1fs_v1_r5_*",
        ".github/workflows/a1fs-v1-r5-*",
    ],
    "VALIDATOR_GAP": [
        "ulga/validators/validate_a1fs_v1_r*", "tests/ulga/test_a1fs_v1_r*",
        ".github/workflows/a1fs-v1-r*",
    ],
    "CONTENT_CAPACITY_INSUFFICIENT": [
        ".local/**", "ulga/builders/build_a1fs_v1_r4_*", "ulga/validators/validate_a1fs_v1_r4_*",
        "tests/ulga/test_a1fs_v1_r4_*", ".github/workflows/a1fs-v1-r4-*",
    ],
    "COVERAGE_REQUIREMENT_GAP": [
        ".local/**", "ulga/builders/build_a1fs_v1_r2_*", "ulga/builders/build_a1fs_v1_r3_*",
        "ulga/validators/validate_a1fs_v1_r2_*", "ulga/validators/validate_a1fs_v1_r3_*",
        "tests/ulga/test_a1fs_v1_r2_*", "tests/ulga/test_a1fs_v1_r3_*",
    ],
    "PEDAGOGICAL_EVIDENCE_INSUFFICIENT": [".local/**"],
    "AUTHORITY_DECISION_REQUIRED": [".local/**"],
}
FORBIDDEN_PATHS = [
    "ulga/graph/**", "**/*canonical*graph*", "**/A2/**", "**/a2/**",
    "**/*frozen*.zip", "**/*authority*.json" , "**/*mastery_snapshot*.json",
]

REQUIRED_GATES = {
    "CODE_FULLFIX": [
        "SOURCE_HASH_BOUND", "NO_FORBIDDEN_PATHS", "FOCUSED_TESTS_PASS",
        "UPSTREAM_REGRESSION_PASS", "CI_PASS", "MIGRATION_REPLAY_PASS",
        "RAW_EVIDENCE_PRESERVED", "A2_LOCK_PRESERVED",
    ],
    "CONTENT_EXPANSION": [
        "SOURCE_HASH_BOUND", "NO_FORBIDDEN_PATHS", "AUTHORITY_REVIEW_PASS",
        "ITEM_VALIDATOR_PASS", "STIMULUS_DEDUP_PASS", "CAPACITY_RECHECK_PASS",
        "CI_PASS", "A2_LOCK_PRESERVED",
    ],
    "PLANNER_REDEPLOY": [
        "SOURCE_HASH_BOUND", "APPROVED_BANK_ONLY", "NEW_VALID_EVIDENCE_COLLECTED",
        "NO_REPEATED_STIMULUS_BYPASS", "COVERAGE_RECHECK_PASS", "A2_LOCK_PRESERVED",
    ],
    "AUTHORITY_REVIEW": [
        "SOURCE_HASH_BOUND", "EXPLICIT_AUTHORITY_DECISION", "DECISION_HASH_BOUND",
        "NO_DIRECT_CANONICAL_WRITE", "A2_LOCK_PRESERVED",
    ],
}


class RepairLoopError(ValueError):
    """Fail-closed R7 repair-loop error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RepairLoopError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise RepairLoopError(f"{code}_not_object")
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
        raise RepairLoopError(code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RepairLoopError(code) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RepairLoopError(code)
    return value


def _validate_digest(value: Mapping[str, Any], digest_key: str, code: str) -> None:
    core = {key: child for key, child in value.items() if key != digest_key}
    if value.get(digest_key) != digest(core):
        raise RepairLoopError(code)


def explicit_finding_registry(findings: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [deepcopy(dict(row)) for row in findings]
    core = {"task_id": TASK_ID, "schema_version": FINDING_SCHEMA_VERSION, "findings": rows}
    return {**core, "findings_sha256": digest(rows)}


def _load_r3(path: Path) -> dict[str, Any]:
    value = read_json(path, "r3")
    if value.get("task_id") != r3.TASK_ID or value.get("schema_version") != r3.SCHEMA_VERSION or value.get("validation_status") != r3.STATUS:
        raise RepairLoopError("r3_identity_or_status_invalid")
    _validate_digest(value, "report_sha256", "r3_digest_invalid")
    return value


def _load_r4(path: Path) -> dict[str, Any]:
    value = read_json(path, "r4")
    if value.get("task_id") != r4.TASK_ID or value.get("schema_version") != r4.SCHEMA_VERSION or value.get("validation_status") != r4.STATUS:
        raise RepairLoopError("r4_identity_or_status_invalid")
    _validate_digest(value, "report_sha256", "r4_digest_invalid")
    return value


def _load_r5(path: Path) -> dict[str, Any]:
    value = read_json(path, "r5")
    if value.get("task_id") != r5.TASK_ID or value.get("schema_version") != r5.SAFE_SCHEMA_VERSION or value.get("validation_status") != r5.STATUS:
        raise RepairLoopError("r5_identity_or_status_invalid")
    _validate_digest(value, "summary_sha256", "r5_digest_invalid")
    return value


def _load_r6_queue(path: Path) -> dict[str, Any]:
    value = read_json(path, "r6_queue")
    if value.get("task_id") != r6.TASK_ID or value.get("schema_version") != r6.QUEUE_SCHEMA_VERSION or value.get("validation_status") != r6.STATUS:
        raise RepairLoopError("r6_queue_identity_or_status_invalid")
    _validate_digest(value, "queue_sha256", "r6_queue_digest_invalid")
    if value.get("private_local_only") is not True:
        raise RepairLoopError("r6_queue_privacy_invalid")
    return value


def _load_r6_report(path: Path) -> dict[str, Any]:
    value = read_json(path, "r6_report")
    if value.get("task_id") != r6.TASK_ID or value.get("schema_version") != r6.REPORT_SCHEMA_VERSION or value.get("validation_status") != r6.STATUS:
        raise RepairLoopError("r6_report_identity_or_status_invalid")
    _validate_digest(value, "report_sha256", "r6_report_digest_invalid")
    return value


def _load_explicit(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    registry = read_json(path, "explicit_findings")
    if registry.get("task_id") != TASK_ID or registry.get("schema_version") != FINDING_SCHEMA_VERSION:
        raise RepairLoopError("explicit_findings_identity_invalid")
    rows = registry.get("findings")
    if not isinstance(rows, list) or registry.get("findings_sha256") != digest(rows):
        raise RepairLoopError("explicit_findings_digest_invalid")
    result: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise RepairLoopError("explicit_finding_not_object")
        required = {
            "finding_id", "finding_type", "severity", "source_refs", "evidence_refs",
            "breadth_cell_id", "summary_code", "detail", "reproducible", "source_sha256",
        }
        if set(row) != required:
            raise RepairLoopError(f"explicit_finding_shape_invalid:{row.get('finding_id')}")
        if row.get("finding_type") not in FINDING_TYPES or row.get("severity") not in SEVERITIES:
            raise RepairLoopError(f"explicit_finding_class_invalid:{row.get('finding_id')}")
        if not isinstance(row.get("source_refs"), list) or not row["source_refs"]:
            raise RepairLoopError(f"explicit_finding_source_refs_invalid:{row.get('finding_id')}")
        if not isinstance(row.get("evidence_refs"), list):
            raise RepairLoopError(f"explicit_finding_evidence_refs_invalid:{row.get('finding_id')}")
        if not isinstance(row.get("reproducible"), bool):
            raise RepairLoopError(f"explicit_finding_reproducible_invalid:{row.get('finding_id')}")
        if not HEX64.fullmatch(str(row.get("source_sha256") or "")):
            raise RepairLoopError(f"explicit_finding_source_hash_invalid:{row.get('finding_id')}")
        result.append(deepcopy(dict(row)))
    ids = [row["finding_id"] for row in result]
    if len(ids) != len(set(ids)):
        raise RepairLoopError("explicit_finding_duplicate_id")
    return result


def _finding(
    *, finding_type: str, severity: str, source_kind: str, source_id: str,
    source_sha256: str, breadth_cell_id: str | None, summary_code: str,
    source_refs: Sequence[str], evidence_refs: Sequence[str] = (),
    detail: Mapping[str, Any] | None = None, reproducible: bool = True,
) -> dict[str, Any]:
    signature = [finding_type, source_kind, source_id, breadth_cell_id, summary_code, sorted(source_refs), sorted(evidence_refs)]
    finding_id = f"R7_FINDING:{digest(signature)[:24]}"
    return {
        "finding_id": finding_id,
        "finding_type": finding_type,
        "severity": severity,
        "source_kind": source_kind,
        "source_id": source_id,
        "source_sha256": source_sha256,
        "breadth_cell_id": breadth_cell_id,
        "summary_code": summary_code,
        "source_refs": sorted(set(str(row) for row in source_refs)),
        "evidence_refs": sorted(set(str(row) for row in evidence_refs)),
        "detail": deepcopy(dict(detail or {})),
        "reproducible": bool(reproducible),
    }


def _r3_findings(value: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    source_hash = str(value["report_sha256"])
    for cell in value.get("cells", []):
        cell_id, status = str(cell.get("cell_id")), str(cell.get("status"))
        base = dict(
            source_kind="R3_BREADTH_CELL", source_id=cell_id, source_sha256=source_hash,
            breadth_cell_id=cell_id, source_refs=[cell_id, str(cell.get("capability_id")), str(cell.get("life_task_id"))],
            detail={"coverage_status": status, "next_actions": cell.get("next_actions", [])},
        )
        if status == "PROFILE_DEFINITION_REQUIRED":
            result.append(_finding(finding_type="COVERAGE_REQUIREMENT_GAP", severity="P1", summary_code="BREADTH_PROFILE_MISSING", **base))
        elif status in {"CONTENT_MISSING", "ITEMS_MISSING"}:
            result.append(_finding(finding_type="CONTENT_CAPACITY_INSUFFICIENT", severity="P1", summary_code=status, **base))
        elif status == "BLOCKED_SYSTEM_ERROR":
            result.append(_finding(finding_type="EVIDENCE_INVALID", severity="P0", summary_code="BREADTH_BLOCKED_SYSTEM_ERROR", **base))
        elif status in {"EVIDENCE_INSUFFICIENT", "SUPPORTED_PASS", "INDEPENDENT_PASS", "TRANSFER_PASS", "DEPLOYED", "READY_TO_DEPLOY"}:
            result.append(_finding(finding_type="PEDAGOGICAL_EVIDENCE_INSUFFICIENT", severity="P2", summary_code=f"BREADTH_{status}", **base))
    return result


def _r4_findings(value: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    source_hash = str(value["report_sha256"])
    for cell in value.get("cell_supply", []):
        cell_id, status = str(cell.get("breadth_cell_id")), str(cell.get("supply_status"))
        base = dict(
            source_kind="R4_CELL_SUPPLY", source_id=cell_id, source_sha256=source_hash,
            breadth_cell_id=cell_id, source_refs=[cell_id],
            detail={
                "supply_status": status, "skill_missing": cell.get("skill_projection", {}).get("missing", []),
                "purpose_capacity": cell.get("purpose_capacity", {}),
            },
        )
        if status in {"CONTENT_MISSING", "CAPACITY_INSUFFICIENT"}:
            result.append(_finding(finding_type="CONTENT_CAPACITY_INSUFFICIENT", severity="P1", summary_code=f"SUPPLY_{status}", **base))
        elif status == "VALIDATOR_FAILED":
            result.append(_finding(finding_type="VALIDATOR_GAP", severity="P0", summary_code="SUPPLY_VALIDATOR_FAILED", **base))
        elif status == "CAPACITY_POLICY_MISSING":
            result.append(_finding(finding_type="COVERAGE_REQUIREMENT_GAP", severity="P1", summary_code="CAPACITY_POLICY_MISSING", **base))
        elif status == "HUMAN_REVIEW_REQUIRED":
            result.append(_finding(finding_type="AUTHORITY_DECISION_REQUIRED", severity="P1", summary_code="QUESTION_AUTHORITY_REVIEW_REQUIRED", **base))
    return result


def _r5_findings(value: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    source_hash = str(value["summary_sha256"])
    validity = value.get("validity_counts", {})
    invalid_count = sum(int(validity.get(status, 0)) for status in r1.INVALID_STATUSES)
    pending_count = int(validity.get(r1.PENDING, 0))
    if invalid_count or pending_count:
        result.append(_finding(
            finding_type="EVIDENCE_INVALID", severity="P0", source_kind="R5_SAFE_SUMMARY",
            source_id="VALIDITY_COUNTS", source_sha256=source_hash, breadth_cell_id=None,
            summary_code="INVALID_OR_PENDING_EVIDENCE_PRESENT",
            source_refs=["R5_VALIDITY_COUNTS"], detail={"invalid_count": invalid_count, "pending_count": pending_count},
        ))
    for cell_id, counts in value.get("objective_summary", {}).items():
        unresolved = int(counts.get("unresolved", 0))
        if unresolved:
            result.append(_finding(
                finding_type="AUTHORITY_DECISION_REQUIRED", severity="P1", source_kind="R5_OBJECTIVE_SUMMARY",
                source_id=str(cell_id), source_sha256=source_hash, breadth_cell_id=str(cell_id),
                summary_code="UNRESOLVED_HUMAN_REVIEW_PRESENT", source_refs=[str(cell_id)],
                detail={"unresolved_count": unresolved},
            ))
    return result


def _r6_findings(queue: Mapping[str, Any], report: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    source_hash = str(queue["queue_sha256"])
    type_map = {
        "COLLECTOR_GAP_CANDIDATE": "EVIDENCE_FIELD_MISSING",
        "CONTENT_GAP_CANDIDATE": "CONTENT_CAPACITY_INSUFFICIENT",
        "HUMAN_REVIEW_CANDIDATE": "AUTHORITY_DECISION_REQUIRED",
        "REMEDIATION_CANDIDATE": "PEDAGOGICAL_EVIDENCE_INSUFFICIENT",
        "NEXT_DEPLOYMENT_CELL_CANDIDATE": "PEDAGOGICAL_EVIDENCE_INSUFFICIENT",
        "SKILL_TRANSFER_CANDIDATE": "PEDAGOGICAL_EVIDENCE_INSUFFICIENT",
        "SUPPORT_CHANGE_CANDIDATE": "PEDAGOGICAL_EVIDENCE_INSUFFICIENT",
        "REPAIR_TASK_CANDIDATE": "PEDAGOGICAL_EVIDENCE_INSUFFICIENT",
        "RETENTION_REVIEW_CANDIDATE": "PEDAGOGICAL_EVIDENCE_INSUFFICIENT",
    }
    for candidate in queue.get("candidates", []):
        recommendation_id = str(candidate.get("recommendation_id"))
        recommendation_type = str(candidate.get("type"))
        finding_type = type_map.get(recommendation_type)
        if not finding_type:
            continue
        result.append(_finding(
            finding_type=finding_type,
            severity="P1" if finding_type != "PEDAGOGICAL_EVIDENCE_INSUFFICIENT" else "P2",
            source_kind="R6_CONTROLLED_CANDIDATE", source_id=recommendation_id,
            source_sha256=source_hash, breadth_cell_id=candidate.get("target_breadth_cell_id"),
            summary_code=recommendation_type,
            source_refs=[recommendation_id] + list(candidate.get("diagnosis_ids", [])),
            evidence_refs=list(candidate.get("evidence_refs", [])),
            detail={"action_payload": candidate.get("action_payload", {}), "gate": candidate.get("gate", {})},
        ))
    if queue.get("source_bindings") != report.get("source_bindings"):
        raise RepairLoopError("r6_queue_report_binding_mismatch")
    return result


def _explicit_findings(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "finding_id": row["finding_id"],
        "finding_type": row["finding_type"],
        "severity": row["severity"],
        "source_kind": "EXPLICIT_TECHNICAL_FINDING",
        "source_id": row["finding_id"],
        "source_sha256": row["source_sha256"],
        "breadth_cell_id": row["breadth_cell_id"],
        "summary_code": row["summary_code"],
        "source_refs": list(row["source_refs"]),
        "evidence_refs": list(row["evidence_refs"]),
        "detail": deepcopy(dict(row["detail"])),
        "reproducible": row["reproducible"],
    } for row in rows]


def _merge_findings(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for raw in rows:
        row = deepcopy(dict(raw))
        signature = digest([
            row["finding_type"], row.get("breadth_cell_id"), row["summary_code"],
            sorted(row["source_refs"]), sorted(row["evidence_refs"]),
        ])
        if signature not in grouped:
            row["finding_id"] = f"R7_FINDING:{signature[:24]}"
            row["source_kinds"] = [row.pop("source_kind")]
            row["source_ids"] = [row.pop("source_id")]
            row["source_hashes"] = [row.pop("source_sha256")]
            grouped[signature] = row
        else:
            current = grouped[signature]
            current["source_kinds"] = sorted(set(current["source_kinds"] + [row["source_kind"]]))
            current["source_ids"] = sorted(set(current["source_ids"] + [row["source_id"]]))
            current["source_hashes"] = sorted(set(current["source_hashes"] + [row["source_sha256"]]))
            current["source_refs"] = sorted(set(current["source_refs"] + row["source_refs"]))
            current["evidence_refs"] = sorted(set(current["evidence_refs"] + row["evidence_refs"]))
            current["reproducible"] = bool(current["reproducible"] and row["reproducible"])
            if row["severity"] < current["severity"]:
                current["severity"] = row["severity"]
    return sorted(grouped.values(), key=lambda row: (row["severity"], row["finding_type"], row["finding_id"]))


def _work_item(finding: Mapping[str, Any]) -> dict[str, Any]:
    finding_type = str(finding["finding_type"])
    route = ROUTE_BY_FINDING[finding_type]
    work_item_id = f"R7_WORK:{digest([finding['finding_id'], route])[:24]}"
    actions = {
        "CODE_FULLFIX": [
            "REPRODUCE_FROM_HASH_BOUND_SOURCE", "PATCH_ONLY_ALLOWED_COMPONENTS",
            "ADD_OR_UPDATE_FOCUSED_TEST", "RUN_UPSTREAM_REGRESSION",
            "RUN_MIGRATION_AND_REPLAY", "OPEN_PR_AND_REQUIRE_CI",
        ],
        "CONTENT_EXPANSION": [
            "RETURN_TO_R4_CANDIDATE_SUPPLY", "REQUIRE_AUTHORITY_REVIEW",
            "VALIDATE_LEARNER_AND_SCORING_CONTRACT", "RECHECK_STIMULUS_DIVERSITY_AND_CAPACITY",
        ],
        "PLANNER_REDEPLOY": [
            "SELECT_MISSING_BREADTH_DIMENSION", "ASSIGN_APPROVED_BANK_ITEM",
            "COLLECT_NEW_VALID_EVIDENCE", "REBUILD_R3_COVERAGE",
        ],
        "AUTHORITY_REVIEW": [
            "PRESENT_HASH_BOUND_SOURCE_EVIDENCE", "RECORD_EXPLICIT_AUTHORITY_DECISION",
            "ROUTE_APPROVED_DECISION_TO_OWNING_PIPELINE",
        ],
    }[route]
    return {
        "work_item_id": work_item_id,
        "finding_id": finding["finding_id"],
        "finding_type": finding_type,
        "route": route,
        "severity": finding["severity"],
        "breadth_cell_id": finding.get("breadth_cell_id"),
        "summary_code": finding["summary_code"],
        "source_refs": list(finding["source_refs"]),
        "evidence_refs": list(finding["evidence_refs"]),
        "source_hashes": list(finding["source_hashes"]),
        "reproducible": bool(finding["reproducible"]),
        "allowed_path_patterns": list(ALLOWED_PATHS[finding_type]),
        "forbidden_path_patterns": list(FORBIDDEN_PATHS),
        "required_actions": actions,
        "required_gates": list(REQUIRED_GATES[route]),
        "replay_contract": {
            "required": route in {"CODE_FULLFIX", "CONTENT_EXPANSION", "PLANNER_REDEPLOY"},
            "preserve_raw_evidence": True,
            "rebuild_required": ["R3_COVERAGE", "R4_SUPPLY", "R5_SAFE_EVIDENCE"] if route != "AUTHORITY_REVIEW" else [],
            "a2_lock_required": True,
        },
        "work_state": "OPEN",
        "closure": None,
    }


def build_queue(
    *, r3_path: Path, r4_path: Path, r5_path: Path,
    r6_queue_path: Path, r6_report_path: Path, explicit_findings_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    r3_value = _load_r3(r3_path)
    r4_value = _load_r4(r4_path)
    r5_value = _load_r5(r5_path)
    r6_queue = _load_r6_queue(r6_queue_path)
    r6_report = _load_r6_report(r6_report_path)
    explicit = _load_explicit(explicit_findings_path)
    findings = _merge_findings(
        _r3_findings(r3_value) + _r4_findings(r4_value) + _r5_findings(r5_value)
        + _r6_findings(r6_queue, r6_report) + _explicit_findings(explicit)
    )
    work_items = [_work_item(row) for row in findings]
    queue_core = {
        "task_id": TASK_ID,
        "schema_version": QUEUE_SCHEMA_VERSION,
        "validation_status": STATUS,
        "private_local_only": True,
        "source_bindings": {
            "r3_report_sha256": r3_value["report_sha256"],
            "r4_report_sha256": r4_value["report_sha256"],
            "r5_summary_sha256": r5_value["summary_sha256"],
            "r6_queue_sha256": r6_queue["queue_sha256"],
            "r6_report_sha256": r6_report["report_sha256"],
            "explicit_findings_sha256": file_digest(explicit_findings_path) if explicit_findings_path else None,
        },
        "counts": {
            "finding_count": len(findings),
            "work_item_count": len(work_items),
            "finding_type_counts": dict(sorted(Counter(row["finding_type"] for row in findings).items())),
            "route_counts": dict(sorted(Counter(row["route"] for row in work_items).items())),
            "state_counts": {"OPEN": len(work_items), "CLOSED": 0, "BLOCKED": 0},
        },
        "findings": findings,
        "work_items": work_items,
        "claim_boundaries": {
            "code_modified": False,
            "github_issue_created": False,
            "canonical_authority_modified": False,
            "practice_bank_modified": False,
            "planner_policy_modified": False,
            "mastery_modified": False,
            "a2_unlocked": False,
            "gpt_candidate_executed_directly": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    queue = {**queue_core, "queue_sha256": digest(queue_core)}
    safe_core = {
        "task_id": TASK_ID,
        "schema_version": REPORT_SCHEMA_VERSION,
        "validation_status": STATUS,
        "source_bindings": queue_core["source_bindings"],
        "counts": queue_core["counts"],
        "work_items": [{
            "work_item_id": row["work_item_id"], "finding_type": row["finding_type"],
            "route": row["route"], "severity": row["severity"],
            "breadth_cell_id": row["breadth_cell_id"], "summary_code": row["summary_code"],
            "work_state": row["work_state"], "required_gates": row["required_gates"],
        } for row in work_items],
        "claim_boundaries": queue_core["claim_boundaries"],
        "next_short_step": NEXT_SHORT_STEP,
    }
    report = {**safe_core, "report_sha256": digest(safe_core)}
    return queue, report


def result_registry(*, queue_sha256: str, results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [deepcopy(dict(row)) for row in results]
    core = {"task_id": TASK_ID, "schema_version": RESULT_SCHEMA_VERSION, "queue_sha256": queue_sha256, "results": rows}
    return {**core, "results_sha256": digest(rows)}


def _path_allowed(path: str, patterns: Sequence[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def _path_forbidden(path: str, patterns: Sequence[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def _validate_result(result: Mapping[str, Any], work: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "work_item_id", "result_state", "completed_at", "actor_id", "commit_sha",
        "changed_paths", "gate_results", "ci", "replay", "output_hashes", "notes",
    }
    if set(result) != required:
        return ["result_shape_invalid"]
    if result.get("result_state") not in RESULT_STATES:
        errors.append("result_state_invalid")
    try:
        timezone_timestamp(result.get("completed_at"), "result_timestamp_invalid")
    except RepairLoopError as exc:
        errors.append(str(exc))
    if not str(result.get("actor_id") or "").strip():
        errors.append("result_actor_missing")
    commit_sha = result.get("commit_sha")
    if work["route"] == "CODE_FULLFIX" and not HEX40.fullmatch(str(commit_sha or "")):
        errors.append("code_fullfix_commit_sha_invalid")
    if work["route"] != "CODE_FULLFIX" and commit_sha is not None and not HEX40.fullmatch(str(commit_sha)):
        errors.append("optional_commit_sha_invalid")
    changed = result.get("changed_paths")
    if not isinstance(changed, list) or not all(isinstance(row, str) and row.strip() for row in changed):
        errors.append("changed_paths_invalid"); changed = []
    if work["route"] == "CODE_FULLFIX" and not changed:
        errors.append("code_fullfix_changed_paths_missing")
    for path in changed:
        if _path_forbidden(path, work["forbidden_path_patterns"]):
            errors.append(f"forbidden_path_changed:{path}")
        if work["route"] == "CODE_FULLFIX" and not _path_allowed(path, work["allowed_path_patterns"]):
            errors.append(f"path_outside_allowed_scope:{path}")
    gates = result.get("gate_results")
    if not isinstance(gates, Mapping) or set(gates) != set(work["required_gates"]):
        errors.append("gate_results_denominator_invalid")
    elif any(gates[key] not in {True, False} for key in gates):
        errors.append("gate_results_value_invalid")
    ci = result.get("ci")
    if not isinstance(ci, Mapping) or set(ci) != {"run_id", "conclusion", "test_commands"}:
        errors.append("ci_shape_invalid")
    else:
        if ci.get("conclusion") not in CI_CONCLUSIONS:
            errors.append("ci_conclusion_invalid")
        if not isinstance(ci.get("test_commands"), list):
            errors.append("ci_test_commands_invalid")
    replay = result.get("replay")
    if not isinstance(replay, Mapping) or set(replay) != {"status", "source_hashes", "preserved_raw_evidence", "rebuilt_outputs"}:
        errors.append("replay_shape_invalid")
    else:
        if replay.get("status") not in {"PASS", "FAIL", "NOT_REQUIRED"}:
            errors.append("replay_status_invalid")
        hashes = replay.get("source_hashes")
        if not isinstance(hashes, list) or set(work["source_hashes"]) - set(hashes):
            errors.append("replay_source_hash_binding_invalid")
        if replay.get("preserved_raw_evidence") is not True:
            errors.append("raw_evidence_preservation_invalid")
        if not isinstance(replay.get("rebuilt_outputs"), list):
            errors.append("replay_rebuilt_outputs_invalid")
    output_hashes = result.get("output_hashes")
    if not isinstance(output_hashes, Mapping) or any(not HEX64.fullmatch(str(value)) for value in output_hashes.values()):
        errors.append("output_hashes_invalid")
    if result.get("result_state") == "PASS":
        if not isinstance(gates, Mapping) or not all(gates.values()):
            errors.append("pass_result_gate_not_all_true")
        if work["route"] == "CODE_FULLFIX" and ci.get("conclusion") != "success":
            errors.append("pass_code_fullfix_ci_not_success")
        if work["replay_contract"]["required"] and replay.get("status") != "PASS":
            errors.append("pass_result_replay_not_pass")
    return errors


def apply_results(*, queue: Mapping[str, Any], registry: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if queue.get("task_id") != TASK_ID or queue.get("schema_version") != QUEUE_SCHEMA_VERSION or queue.get("validation_status") != STATUS:
        raise RepairLoopError("queue_identity_or_status_invalid")
    _validate_digest(queue, "queue_sha256", "queue_digest_invalid")
    if registry.get("task_id") != TASK_ID or registry.get("schema_version") != RESULT_SCHEMA_VERSION:
        raise RepairLoopError("result_registry_identity_invalid")
    if registry.get("queue_sha256") != queue.get("queue_sha256"):
        raise RepairLoopError("result_queue_binding_invalid")
    results = registry.get("results")
    if not isinstance(results, list) or registry.get("results_sha256") != digest(results):
        raise RepairLoopError("result_registry_digest_invalid")
    work_by_id = {str(row["work_item_id"]): row for row in queue.get("work_items", [])}
    result_by_id: dict[str, dict[str, Any]] = {}
    for row in results:
        if not isinstance(row, Mapping):
            raise RepairLoopError("result_not_object")
        work_id = str(row.get("work_item_id") or "")
        if work_id not in work_by_id or work_id in result_by_id:
            raise RepairLoopError(f"result_work_item_invalid:{work_id}")
        errors = _validate_result(row, work_by_id[work_id])
        if errors:
            raise RepairLoopError(f"repair_result_invalid:{work_id}:" + "|".join(errors))
        result_by_id[work_id] = deepcopy(dict(row))
    output = deepcopy(dict(queue))
    output.pop("queue_sha256", None)
    for work in output["work_items"]:
        result = result_by_id.get(work["work_item_id"])
        if not result:
            continue
        state = result["result_state"]
        work["work_state"] = "CLOSED" if state == "PASS" else "BLOCKED" if state == "BLOCKED" else "OPEN"
        work["closure"] = {
            "result_state": state,
            "completed_at": result["completed_at"],
            "actor_id": result["actor_id"],
            "commit_sha": result["commit_sha"],
            "ci": deepcopy(result["ci"]),
            "replay": deepcopy(result["replay"]),
            "output_hashes": deepcopy(dict(result["output_hashes"])),
        }
    state_counts = Counter(row["work_state"] for row in output["work_items"])
    output["schema_version"] = CLOSED_SCHEMA_VERSION
    output["counts"]["state_counts"] = {state: int(state_counts.get(state, 0)) for state in sorted(WORK_STATES)}
    output["counts"]["closed_count"] = int(state_counts.get("CLOSED", 0))
    output["counts"]["remaining_open_count"] = int(state_counts.get("OPEN", 0))
    output["counts"]["blocked_count"] = int(state_counts.get("BLOCKED", 0))
    output["source_bindings"]["result_registry_sha256"] = registry["results_sha256"]
    output["claim_boundaries"]["code_modified"] = False
    output["next_short_step"] = NEXT_SHORT_STEP
    closed = {**output, "queue_sha256": digest(output)}
    safe_core = {
        "task_id": TASK_ID,
        "schema_version": REPORT_SCHEMA_VERSION,
        "validation_status": STATUS,
        "source_bindings": closed["source_bindings"],
        "counts": closed["counts"],
        "work_items": [{
            "work_item_id": row["work_item_id"], "finding_type": row["finding_type"],
            "route": row["route"], "severity": row["severity"],
            "breadth_cell_id": row["breadth_cell_id"], "summary_code": row["summary_code"],
            "work_state": row["work_state"],
            "result_state": row["closure"]["result_state"] if row["closure"] else None,
            "commit_sha": row["closure"]["commit_sha"] if row["closure"] else None,
        } for row in closed["work_items"]],
        "claim_boundaries": closed["claim_boundaries"],
        "next_short_step": NEXT_SHORT_STEP,
    }
    report = {**safe_core, "report_sha256": digest(safe_core)}
    return closed, report


def safe_scan(value: Any) -> None:
    forbidden = {"detail", "action_payload", "gate", "notes", "evidence_refs", "source_hashes", "allowed_path_patterns"}
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in forbidden:
                raise RepairLoopError(f"safe_private_field:{key}")
            safe_scan(child)
    elif isinstance(value, list):
        for child in value:
            safe_scan(child)
    elif isinstance(value, str):
        if Path(value).is_absolute() or (len(value) > 2 and value[1:3] in {":/", ":\\"}):
            raise RepairLoopError("safe_absolute_path")


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    build_cmd = commands.add_parser("build")
    build_cmd.add_argument("--r3", type=Path, required=True)
    build_cmd.add_argument("--r4", type=Path, required=True)
    build_cmd.add_argument("--r5", type=Path, required=True)
    build_cmd.add_argument("--r6-queue", type=Path, required=True)
    build_cmd.add_argument("--r6-report", type=Path, required=True)
    build_cmd.add_argument("--explicit-findings", type=Path)
    build_cmd.add_argument("--queue-output", type=Path, required=True)
    build_cmd.add_argument("--report-output", type=Path, required=True)
    close_cmd = commands.add_parser("close")
    close_cmd.add_argument("--queue", type=Path, required=True)
    close_cmd.add_argument("--results", type=Path, required=True)
    close_cmd.add_argument("--queue-output", type=Path, required=True)
    close_cmd.add_argument("--report-output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "build":
        queue, report = build_queue(
            r3_path=args.r3, r4_path=args.r4, r5_path=args.r5,
            r6_queue_path=args.r6_queue, r6_report_path=args.r6_report,
            explicit_findings_path=args.explicit_findings,
        )
    else:
        queue = read_json(args.queue, "queue")
        results = read_json(args.results, "results")
        queue, report = apply_results(queue=queue, registry=results)
    safe_scan(report)
    write_private(args.queue_output, queue)
    write_private(args.report_output, report)
    print(json.dumps({
        "validation_status": STATUS,
        "queue_output": str(args.queue_output), "report_output": str(args.report_output),
        "work_item_count": queue["counts"]["work_item_count"],
        "next_short_step": NEXT_SHORT_STEP,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
