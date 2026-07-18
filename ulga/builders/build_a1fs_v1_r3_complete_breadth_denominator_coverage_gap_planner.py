#!/usr/bin/env python3
"""Build the complete A1/A1+ breadth denominator, coverage matrix and gap plan."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_r2_complete_breadth_ontology_deployment_contract as r2
from ulga.validators import validate_a1fs_v1_r2_complete_breadth_ontology_deployment_contract as r2_validator

TASK_ID = "A1FS-V1-R3_CompleteBreadthDenominatorCoverageAndGapPlanner"
SCHEMA_VERSION = "a1fs.v1.r3.breadth_denominator_coverage.v1"
PROFILE_SCHEMA_VERSION = "a1fs.v1.r3.breadth_requirement_profiles.v1"
DEPLOYMENT_REGISTRY_SCHEMA_VERSION = "a1fs.v1.r3.breadth_deployment_registry.v1"
STATUS = "PASS_A1FS_V1_R3_COMPLETE_BREADTH_DENOMINATOR_COVERAGE_GAP_PLANNER"
GRAPH_STATUS = "PASS_A1FS_V1_M1_PREREQUISITE_GRAPH_AND_COVERAGE"
NEXT_SHORT_STEP = "A1FS-V1-R4_CentralQuestionSupplySkillProjectionAndCapacityGovernance"

PROFILE_DIMENSIONS = [
    "required_domains", "required_life_tasks", "required_skills", "required_support_levels",
    "required_initiative_levels", "required_variation_types", "required_transfer_distances",
    "required_evidence_levels", "required_retention_stages", "required_media_policy",
]
PROFILE_STATES = {"PROFILE_DEFINED", "PROFILE_NOT_POPULATED"}
CELL_STATUSES = (
    "PROFILE_DEFINITION_REQUIRED", "CONTENT_MISSING", "ITEMS_MISSING", "READY_TO_DEPLOY",
    "DEPLOYED", "EVIDENCE_INSUFFICIENT", "SUPPORTED_PASS", "INDEPENDENT_PASS",
    "TRANSFER_PASS", "RETENTION_PASS", "BLOCKED_SYSTEM_ERROR", "DEFERRED_MEDIA",
)
GAP_PRIORITY = {
    "PROFILE_DEFINITION_REQUIRED": 0,
    "CONTENT_MISSING": 1,
    "ITEMS_MISSING": 2,
    "BLOCKED_SYSTEM_ERROR": 3,
    "READY_TO_DEPLOY": 4,
    "DEPLOYED": 5,
    "EVIDENCE_INSUFFICIENT": 6,
    "SUPPORTED_PASS": 7,
    "INDEPENDENT_PASS": 8,
    "TRANSFER_PASS": 9,
    "DEFERRED_MEDIA": 10,
    "RETENTION_PASS": 99,
}
INVALID_EVIDENCE = {
    "PENDING_VALIDITY_REVIEW", "INVALIDATED_SYSTEM_ERROR",
    "INVALIDATED_CONTENT_ERROR", "INVALIDATED_DUPLICATE_SUBMISSION",
}
PASS_RESULTS = {"PASS"}
SUPPORTED_LEVELS = {"S3_FULL_MODEL", "S2_FRAME", "S1_KEYWORD_OR_VISUAL"}
INDEPENDENT_LEVEL = "S0_INDEPENDENT"


class BreadthCoverageError(ValueError):
    """Fail-closed breadth denominator/coverage error."""


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
        raise BreadthCoverageError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise BreadthCoverageError(f"{code}_not_object")
    return value


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _load_ontology(path: Path) -> dict[str, Any]:
    ontology = read_json(path, "ontology")
    errors = r2_validator.validate_ontology(ontology)
    if errors:
        raise BreadthCoverageError("ontology_invalid:" + "|".join(errors))
    return ontology


def _load_graph(path: Path) -> tuple[dict[str, Any], str]:
    graph = read_json(path, "graph")
    if graph.get("validation_status") != GRAPH_STATUS:
        raise BreadthCoverageError("graph_status_invalid")
    required = graph.get("a2_lock_contract", {}).get("required_mastery_node_ids")
    if not isinstance(required, list) or not required:
        raise BreadthCoverageError("graph_required_denominator_invalid")
    nodes = {str(row.get("node_id")): row for row in graph.get("nodes", []) if isinstance(row, Mapping)}
    if set(required) - set(nodes):
        raise BreadthCoverageError("graph_required_node_missing")
    if graph.get("counts", {}).get("required_mastery_node_count") != len(required):
        raise BreadthCoverageError("graph_required_count_mismatch")
    if graph.get("a2_lock_contract", {}).get("state") != "LOCKED_BY_DESIGN":
        raise BreadthCoverageError("a2_design_lock_missing")
    return graph, file_digest(path)


def capability_nodes(graph: Mapping[str, Any]) -> list[dict[str, Any]]:
    required = set(graph["a2_lock_contract"]["required_mastery_node_ids"])
    rows = [
        dict(row) for row in graph.get("nodes", [])
        if row.get("node_id") in required and row.get("node_type") not in {"LESSON", "A2_LOCK"}
    ]
    rows.sort(key=lambda row: str(row["node_id"]))
    if not rows:
        raise BreadthCoverageError("required_capability_nodes_empty")
    for row in rows:
        if row.get("level") not in {"A1", "A1+"}:
            raise BreadthCoverageError(f"capability_level_out_of_scope:{row.get('node_id')}")
    return rows


def empty_profile_registry(graph_sha256: str, ontology_sha256: str) -> dict[str, Any]:
    core = {
        "task_id": TASK_ID,
        "schema_version": PROFILE_SCHEMA_VERSION,
        "source_graph_sha256": graph_sha256,
        "ontology_sha256": ontology_sha256,
        "profiles": [],
    }
    return {**core, "profiles_sha256": digest(core["profiles"])}


def deployment_registry(ontology_sha256: str, contracts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(row) for row in contracts]
    core = {
        "task_id": TASK_ID,
        "schema_version": DEPLOYMENT_REGISTRY_SCHEMA_VERSION,
        "ontology_sha256": ontology_sha256,
        "contracts": rows,
    }
    return {**core, "contracts_sha256": digest(rows)}


def _validate_obligation(obligation: Mapping[str, Any], capability_id: str) -> dict[str, Any]:
    required = {
        "obligation_id", "life_task_id", "domain", "required_skills", "required_support_levels",
        "required_initiative_levels", "required_variation_types", "required_transfer_distances",
        "required_evidence_levels", "required_retention_stages", "required_media_policy", "source_refs",
    }
    if set(obligation) != required:
        raise BreadthCoverageError(f"obligation_shape_invalid:{capability_id}")
    obligation_id = str(obligation["obligation_id"])
    if not obligation_id.startswith("BREADTH_OBLIGATION_"):
        raise BreadthCoverageError(f"obligation_id_invalid:{obligation_id}")
    life_task_id = str(obligation["life_task_id"])
    if not life_task_id.startswith("LIFE_TASK_"):
        raise BreadthCoverageError(f"life_task_id_invalid:{obligation_id}")
    if obligation["domain"] not in r2.ENUMS["domains"]:
        raise BreadthCoverageError(f"obligation_domain_invalid:{obligation_id}")
    enum_fields = {
        "required_skills": "skills",
        "required_support_levels": "support_levels",
        "required_initiative_levels": "initiative_levels",
        "required_variation_types": "interaction_variations",
        "required_transfer_distances": "transfer_distances",
        "required_evidence_levels": "evidence_levels",
        "required_retention_stages": "retention_stages",
    }
    row = dict(obligation)
    for field, enum_name in enum_fields.items():
        values = row[field]
        if not isinstance(values, list) or not values or len(values) != len(set(values)):
            raise BreadthCoverageError(f"obligation_dimension_invalid:{obligation_id}:{field}")
        if set(values) - set(r2.ENUMS[enum_name]):
            raise BreadthCoverageError(f"obligation_enum_invalid:{obligation_id}:{field}")
    if row["required_media_policy"] not in r2.ENUMS["media_requirements"]:
        raise BreadthCoverageError(f"obligation_media_policy_invalid:{obligation_id}")
    if not isinstance(row["source_refs"], list) or not row["source_refs"]:
        raise BreadthCoverageError(f"obligation_source_refs_missing:{obligation_id}")
    return row


def _load_profiles(
    path: Path, *, graph_sha256: str, ontology_sha256: str,
    capability_rows: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    registry = read_json(path, "profiles")
    if registry.get("task_id") != TASK_ID or registry.get("schema_version") != PROFILE_SCHEMA_VERSION:
        raise BreadthCoverageError("profiles_identity_invalid")
    if registry.get("source_graph_sha256") != graph_sha256:
        raise BreadthCoverageError("profiles_graph_binding_mismatch")
    if registry.get("ontology_sha256") != ontology_sha256:
        raise BreadthCoverageError("profiles_ontology_binding_mismatch")
    profiles = registry.get("profiles")
    if not isinstance(profiles, list) or registry.get("profiles_sha256") != digest(profiles):
        raise BreadthCoverageError("profiles_digest_invalid")
    capability_node_ids = {str(row["node_id"]) for row in capability_rows}
    result: dict[str, dict[str, Any]] = {}
    for raw in profiles:
        if not isinstance(raw, Mapping):
            raise BreadthCoverageError("profile_not_object")
        node_id = str(raw.get("capability_node_id") or "")
        if node_id not in capability_node_ids or node_id in result:
            raise BreadthCoverageError(f"profile_node_invalid_or_duplicate:{node_id}")
        capability_id = str(raw.get("capability_id") or "")
        if not capability_id.startswith("CAP_"):
            raise BreadthCoverageError(f"profile_capability_id_invalid:{node_id}")
        state = raw.get("profile_state")
        if state not in PROFILE_STATES:
            raise BreadthCoverageError(f"profile_state_invalid:{node_id}")
        dimension_states = raw.get("dimension_states")
        if not isinstance(dimension_states, Mapping) or set(dimension_states) != set(PROFILE_DIMENSIONS):
            raise BreadthCoverageError(f"profile_dimension_states_invalid:{node_id}")
        if any(value not in {"POPULATED", "NOT_POPULATED", "NOT_APPLICABLE_WITH_JUSTIFICATION"} for value in dimension_states.values()):
            raise BreadthCoverageError(f"profile_dimension_state_value_invalid:{node_id}")
        justifications = raw.get("dimension_justifications")
        if not isinstance(justifications, Mapping):
            raise BreadthCoverageError(f"profile_justifications_invalid:{node_id}")
        for field, value in dimension_states.items():
            if value == "NOT_APPLICABLE_WITH_JUSTIFICATION" and not str(justifications.get(field, "")).strip():
                raise BreadthCoverageError(f"profile_justification_missing:{node_id}:{field}")
        obligations_raw = raw.get("obligations")
        if not isinstance(obligations_raw, list):
            raise BreadthCoverageError(f"profile_obligations_invalid:{node_id}")
        if state == "PROFILE_DEFINED":
            if not obligations_raw or any(value == "NOT_POPULATED" for value in dimension_states.values()):
                raise BreadthCoverageError(f"defined_profile_incomplete:{node_id}")
        elif obligations_raw:
            raise BreadthCoverageError(f"unpopulated_profile_has_obligations:{node_id}")
        obligations = [_validate_obligation(row, capability_id) for row in obligations_raw]
        ids = [row["obligation_id"] for row in obligations]
        if len(ids) != len(set(ids)):
            raise BreadthCoverageError(f"duplicate_obligation_id:{node_id}")
        result[node_id] = {
            "capability_node_id": node_id,
            "capability_id": capability_id,
            "profile_state": state,
            "dimension_states": dict(dimension_states),
            "dimension_justifications": dict(justifications),
            "obligations": obligations,
        }
    return result


def _load_deployments(path: Path, *, ontology_sha256: str) -> list[dict[str, Any]]:
    registry = read_json(path, "deployments")
    if registry.get("task_id") != TASK_ID or registry.get("schema_version") != DEPLOYMENT_REGISTRY_SCHEMA_VERSION:
        raise BreadthCoverageError("deployments_identity_invalid")
    if registry.get("ontology_sha256") != ontology_sha256:
        raise BreadthCoverageError("deployments_ontology_binding_mismatch")
    contracts = registry.get("contracts")
    if not isinstance(contracts, list) or registry.get("contracts_sha256") != digest(contracts):
        raise BreadthCoverageError("deployments_digest_invalid")
    ids: set[str] = set()
    result: list[dict[str, Any]] = []
    schema = r2.build_contract_schema()
    for raw in contracts:
        if not isinstance(raw, Mapping):
            raise BreadthCoverageError("deployment_contract_not_object")
        errors = r2_validator.validate_contract(raw, schema)
        if errors:
            raise BreadthCoverageError("deployment_contract_invalid:" + "|".join(errors))
        deployment_id = str(raw["deployment_id"])
        if deployment_id in ids:
            raise BreadthCoverageError(f"duplicate_deployment_id:{deployment_id}")
        ids.add(deployment_id)
        result.append(dict(raw))
    return result


def _passed(contract: Mapping[str, Any]) -> bool:
    return (
        contract.get("accuracy_result") in PASS_RESULTS
        and contract.get("meaning_result") in PASS_RESULTS
        and contract.get("task_completion_result") in PASS_RESULTS
    )


def _dimension_projection(matches: Sequence[Mapping[str, Any]], obligation: Mapping[str, Any]) -> dict[str, Any]:
    valid = [row for row in matches if row.get("evidence_validity") not in INVALID_EVIDENCE and row.get("system_error_status") not in {"SUSPECTED", "CONFIRMED"}]
    populated = [row for row in valid if row.get("validator_status") == "PASS"]
    passed = [row for row in populated if _passed(row)]
    supported_passed = [row for row in passed if row.get("support_level") in SUPPORTED_LEVELS]
    independent_passed = [
        row for row in passed
        if row.get("support_level") == INDEPENDENT_LEVEL
        and row.get("evidence_level") in {
            "E3_INDEPENDENT_PRODUCTION", "E4_CROSS_CONTEXT_TRANSFER",
            "E5_DELAYED_RETENTION", "E6_AUTHENTIC_TASK_PERFORMANCE",
        }
    ]
    transfer_passed = [
        row for row in passed
        if row.get("evidence_level") in {"E4_CROSS_CONTEXT_TRANSFER", "E5_DELAYED_RETENTION", "E6_AUTHENTIC_TASK_PERFORMANCE"}
    ]
    retention_passed = [
        row for row in passed
        if row.get("retention_stage") == "RETAINED"
        and row.get("evidence_level") in {"E5_DELAYED_RETENTION", "E6_AUTHENTIC_TASK_PERFORMANCE"}
    ]
    mapping = {
        "skills": ("required_skills", "skill"),
        "support_levels": ("required_support_levels", "support_level"),
        "initiative_levels": ("required_initiative_levels", "initiative_level"),
        "variation_types": ("required_variation_types", "interaction_variation"),
        "transfer_distances": ("required_transfer_distances", "transfer_distance"),
        "evidence_levels": ("required_evidence_levels", "evidence_level"),
        "retention_stages": ("required_retention_stages", "retention_stage"),
    }
    dimensions: dict[str, Any] = {}
    for name, (required_key, contract_key) in mapping.items():
        required_values = list(obligation[required_key])
        observed_values = sorted({str(row.get(contract_key)) for row in valid if row.get(contract_key) is not None})
        dimensions[name] = {
            "required": required_values,
            "observed": observed_values,
            "missing": sorted(set(required_values) - set(observed_values)),
        }
    return {
        "matching_contract_count": len(matches),
        "valid_contract_count": len(valid),
        "validator_pass_contract_count": len(populated),
        "passed_contract_count": len(passed),
        "supported_pass_contract_count": len(supported_passed),
        "independent_pass_contract_count": len(independent_passed),
        "transfer_pass_contract_count": len(transfer_passed),
        "retention_pass_contract_count": len(retention_passed),
        "dimensions": dimensions,
        "valid_contracts": valid,
        "validator_pass_contracts": populated,
        "passed_contracts": passed,
        "supported_passed": supported_passed,
        "independent_passed": independent_passed,
        "transfer_passed": transfer_passed,
        "retention_passed": retention_passed,
    }


def _cell_status(projection: Mapping[str, Any], obligation: Mapping[str, Any]) -> str:
    matches = projection["matching_contract_count"]
    valid = projection["valid_contract_count"]
    validated = projection["validator_pass_contract_count"]
    if matches == 0:
        return "CONTENT_MISSING"
    if valid == 0:
        return "BLOCKED_SYSTEM_ERROR"
    media_required = obligation["required_media_policy"] == "REQUIRED"
    if media_required and all(row.get("media_payload_state") == "DEFERRED_MEDIA_PAYLOAD" for row in projection["valid_contracts"]):
        return "DEFERRED_MEDIA"
    if validated == 0:
        return "ITEMS_MISSING"
    dimensions = projection["dimensions"]
    if projection["retention_pass_contract_count"] and all(not row["missing"] for row in dimensions.values()):
        return "RETENTION_PASS"
    base_dimensions = ("skills", "support_levels", "initiative_levels", "variation_types", "transfer_distances")
    if projection["transfer_pass_contract_count"] and all(not dimensions[name]["missing"] for name in base_dimensions):
        return "TRANSFER_PASS"
    if projection["independent_pass_contract_count"] and INDEPENDENT_LEVEL not in dimensions["support_levels"]["missing"]:
        return "INDEPENDENT_PASS"
    if projection["supported_pass_contract_count"]:
        return "SUPPORTED_PASS"
    if projection["passed_contract_count"]:
        return "EVIDENCE_INSUFFICIENT"
    evidence_values = {row.get("evidence_level") for row in projection["validator_pass_contracts"]}
    if evidence_values - {None, "E0_EXPOSURE"}:
        return "EVIDENCE_INSUFFICIENT"
    if "E0_EXPOSURE" in evidence_values:
        return "DEPLOYED"
    return "READY_TO_DEPLOY"


def _next_actions(status: str, cell: Mapping[str, Any]) -> list[str]:
    actions = {
        "PROFILE_DEFINITION_REQUIRED": ["AUTHOR_BREADTH_REQUIREMENT_PROFILE"],
        "CONTENT_MISSING": ["POPULATE_CONTEXT_AND_LIFE_TASK_CONTENT"],
        "ITEMS_MISSING": ["BUILD_AND_VALIDATE_APPROVED_PRACTICE_ITEMS"],
        "READY_TO_DEPLOY": ["DEPLOY_TO_LOCAL_RUNTIME"],
        "DEPLOYED": ["COLLECT_RESOLVED_LEARNER_EVIDENCE"],
        "EVIDENCE_INSUFFICIENT": ["COLLECT_MISSING_DIMENSION_EVIDENCE"],
        "SUPPORTED_PASS": ["REDUCE_SUPPORT_AND_TEST_INDEPENDENT_USE"],
        "INDEPENDENT_PASS": ["TEST_NEAR_MEDIUM_FAR_TRANSFER"],
        "TRANSFER_PASS": ["SCHEDULE_DELAYED_RETENTION"],
        "BLOCKED_SYSTEM_ERROR": ["ROUTE_TO_R1_EVIDENCE_GOVERNANCE_AND_RETEST"],
        "DEFERRED_MEDIA": ["KEEP_MEDIA_CONTRACT_VISIBLE_FOR_R10"],
        "RETENTION_PASS": [],
    }[status]
    missing = cell.get("dimension_coverage", {})
    if status in {"EVIDENCE_INSUFFICIENT", "SUPPORTED_PASS", "INDEPENDENT_PASS", "TRANSFER_PASS"}:
        for dimension, row in sorted(missing.items()):
            if row.get("missing"):
                actions.append(f"FILL_{dimension.upper()}_GAP")
    return actions


def build(
    *, ontology_path: Path, graph_path: Path, profiles_path: Path,
    deployments_path: Path, m10_report_path: Path | None = None,
) -> dict[str, Any]:
    ontology = _load_ontology(ontology_path)
    graph, graph_sha = _load_graph(graph_path)
    capability_rows = capability_nodes(graph)
    profiles = _load_profiles(
        profiles_path, graph_sha256=graph_sha, ontology_sha256=ontology["ontology_sha256"],
        capability_rows=capability_rows,
    )
    deployments = _load_deployments(deployments_path, ontology_sha256=ontology["ontology_sha256"])
    m10_binding = None
    if m10_report_path:
        m10 = read_json(m10_report_path, "m10_report")
        if m10.get("task_id") != "E4S-A1V1-M10_A1A1PlusCoverageRecheckAndBacklogClosure_NoNewDesignDocs":
            raise BreadthCoverageError("m10_report_identity_invalid")
        m10_binding = {
            "source_sha256": file_digest(m10_report_path),
            "validation_status": m10.get("validation_status") or m10.get("status"),
        }
    contracts_by_key: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in deployments:
        key = (str(row["capability_id"]), str(row["life_task_id"]), str(row["domain"]))
        contracts_by_key.setdefault(key, []).append(row)
    cells: list[dict[str, Any]] = []
    profile_missing: list[str] = []
    for node in capability_rows:
        node_id = str(node["node_id"])
        profile = profiles.get(node_id)
        if not profile or profile["profile_state"] != "PROFILE_DEFINED":
            profile_missing.append(node_id)
            cell = {
                "cell_id": f"BREADTH_CELL_PROFILE_REQUIRED_{digest(node_id)[:20].upper()}",
                "capability_node_id": node_id,
                "capability_id": profile["capability_id"] if profile else f"CAP_UNMAPPED_{digest(node_id)[:20].upper()}",
                "obligation_id": None,
                "life_task_id": None,
                "domain": None,
                "status": "PROFILE_DEFINITION_REQUIRED",
                "dimension_coverage": {
                    field: {"required": [], "observed": [], "missing": ["PROFILE_NOT_POPULATED"]}
                    for field in PROFILE_DIMENSIONS
                },
                "matching_deployment_ids": [],
                "next_actions": ["AUTHOR_BREADTH_REQUIREMENT_PROFILE"],
            }
            cells.append(cell)
            continue
        for obligation in profile["obligations"]:
            key = (profile["capability_id"], obligation["life_task_id"], obligation["domain"])
            matches = contracts_by_key.get(key, [])
            projection = _dimension_projection(matches, obligation)
            cell = {
                "cell_id": f"BREADTH_CELL_{digest([node_id, obligation['obligation_id']])[:24].upper()}",
                "capability_node_id": node_id,
                "capability_id": profile["capability_id"],
                "obligation_id": obligation["obligation_id"],
                "life_task_id": obligation["life_task_id"],
                "domain": obligation["domain"],
                "status": "",
                "dimension_coverage": projection["dimensions"],
                "matching_deployment_ids": sorted(str(row["deployment_id"]) for row in matches),
                "source_refs": list(obligation["source_refs"]),
            }
            cell["status"] = _cell_status(projection, obligation)
            cell["next_actions"] = _next_actions(cell["status"], cell)
            cells.append(cell)
    cells.sort(key=lambda row: (GAP_PRIORITY[row["status"]], str(row["capability_node_id"]), str(row.get("obligation_id"))))
    status_counts = Counter(row["status"] for row in cells)
    for status in CELL_STATUSES:
        status_counts.setdefault(status, 0)
    gaps = [
        {
            "rank": index,
            "cell_id": row["cell_id"],
            "capability_node_id": row["capability_node_id"],
            "capability_id": row["capability_id"],
            "life_task_id": row.get("life_task_id"),
            "domain": row.get("domain"),
            "status": row["status"],
            "next_actions": row["next_actions"],
        }
        for index, row in enumerate((row for row in cells if row["status"] != "RETENTION_PASS"), start=1)
    ]
    final_complete = status_counts["RETENTION_PASS"]
    denominator = len(cells)
    structural_ready = sum(status_counts[status] for status in (
        "READY_TO_DEPLOY", "DEPLOYED", "EVIDENCE_INSUFFICIENT", "SUPPORTED_PASS",
        "INDEPENDENT_PASS", "TRANSFER_PASS", "RETENTION_PASS", "DEFERRED_MEDIA",
    ))
    core = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": STATUS,
        "source_bindings": {
            "ontology_sha256": ontology["ontology_sha256"],
            "graph_sha256": graph_sha,
            "profiles_sha256": digest([profiles[key] for key in sorted(profiles)]),
            "deployments_sha256": digest(deployments),
            "m10_structural_coverage": m10_binding,
        },
        "counts": {
            "required_mastery_node_count": len(graph["a2_lock_contract"]["required_mastery_node_ids"]),
            "required_capability_node_count": len(capability_rows),
            "profile_defined_count": sum(profile["profile_state"] == "PROFILE_DEFINED" for profile in profiles.values()),
            "profile_missing_count": len(profile_missing),
            "denominator_cell_count": denominator,
            "deployment_contract_count": len(deployments),
            "gap_count": len(gaps),
            "status_counts": dict(sorted(status_counts.items())),
        },
        "coverage_metrics": {
            "structural_ready_count": structural_ready,
            "structural_ready_percent": round(structural_ready * 100.0 / denominator, 2) if denominator else 0.0,
            "retention_complete_count": final_complete,
            "retention_complete_percent": round(final_complete * 100.0 / denominator, 2) if denominator else 0.0,
            "false_100_percent_blocked": final_complete != denominator,
            "completion_denominator_source": "EXPLICIT_BREADTH_REQUIREMENT_CELLS_PLUS_PROFILE_PLACEHOLDERS",
        },
        "profile_missing_capability_node_ids": sorted(profile_missing),
        "cells": cells,
        "ranked_gaps": gaps,
        "claim_boundaries": {
            "m1_graph_modified": False,
            "m10_structural_coverage_replaced": False,
            "cartesian_product_generated": False,
            "a2_unlocked": False,
            "mastery_claimed": False,
            "retention_claimed_from_structure": False,
            "audio_completion_required": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    return {**core, "report_sha256": digest(core)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ontology", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--deployments", type=Path, required=True)
    parser.add_argument("--m10-report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build(
        ontology_path=args.ontology,
        graph_path=args.graph,
        profiles_path=args.profiles,
        deployments_path=args.deployments,
        m10_report_path=args.m10_report,
    )
    write_json(args.output, report)
    print(json.dumps({
        "validation_status": STATUS,
        "output": str(args.output),
        "denominator_cell_count": report["counts"]["denominator_cell_count"],
        "gap_count": report["counts"]["gap_count"],
        "next_short_step": NEXT_SHORT_STEP,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
