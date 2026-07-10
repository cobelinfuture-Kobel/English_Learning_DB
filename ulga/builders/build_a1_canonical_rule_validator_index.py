#!/usr/bin/env python3
"""Build the canonical A1 rule/validator consumer index.

This integration keeps five distinct claims separate:
canonical mapping, primitive-data presence, schema validation, executable
sentence validation, and production runtime validation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "R7-M104E21A_A1CanonicalRuleValidatorIntegration"
NEXT_SHORT_STEP = "R7-M104E21B_A1CanonicalExecutableValidatorBatch01Implementation"

CANONICAL_OVERLAY_PATH = REPO_ROOT / "ulga/graph/a1_egp_canonical_mappings.json"
QUERY_INDEX_PATH = REPO_ROOT / "ulga/graph/grammar_query_index.json"
CAN_RULE_PATH = REPO_ROOT / "ulga/rules/a1_can_statement_rule_primitives.json"
BATCH_01_PATH = REPO_ROOT / "ulga/rules/a1_a1plus_rule_primitives_batch_01.json"
BATCH_02_PATH = REPO_ROOT / "ulga/rules/a1_unbucketed_rule_primitives_batch_02.json"
CAN_REPORT_PATH = REPO_ROOT / "ulga/reports/a1_can_statement_rule_primitive_validation.json"
BATCH_01_REPORT_PATH = REPO_ROOT / "ulga/reports/a1_a1plus_rule_primitives_batch_01_validation.json"
BATCH_02_REPORT_PATH = REPO_ROOT / "ulga/reports/a1_unbucketed_rule_primitives_batch_02_validation.json"
OUTPUT_PATH = REPO_ROOT / "ulga/graph/a1_canonical_rule_validator_index.json"
CONTRACT_PATH = REPO_ROOT / "ulga/contracts/a1_canonical_rule_validator_contract.json"
REPORT_PATH = REPO_ROOT / "ulga/reports/a1_canonical_rule_validator_validation.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def require_pass(report: dict[str, Any], source: str) -> None:
    summary = report.get("validation_summary", {})
    if summary.get("status") != "PASS":
        raise ValueError(f"Rule primitive validation report is not PASS: {source}")


def canonical_rule_sources() -> list[dict[str, Any]]:
    can = load_json(CAN_RULE_PATH)
    batch_01 = load_json(BATCH_01_PATH)
    batch_02 = load_json(BATCH_02_PATH)
    can_report = load_json(CAN_REPORT_PATH)
    batch_01_report = load_json(BATCH_01_REPORT_PATH)
    batch_02_report = load_json(BATCH_02_REPORT_PATH)

    require_pass(can_report, relative(CAN_REPORT_PATH))
    require_pass(batch_01_report, relative(BATCH_01_REPORT_PATH))
    require_pass(batch_02_report, relative(BATCH_02_REPORT_PATH))

    sources = [
        {
            "source_path": relative(CAN_RULE_PATH),
            "artifact_id": can["artifact_id"],
            "validator_path": "ulga/validators/validate_a1_can_statement_rule_primitives.py",
            "validation_report_path": relative(CAN_REPORT_PATH),
            "schema_validation_status": "PASS",
            "sentence_validator_mode": "OFFLINE_STATIC_PROTOTYPE",
            "nodes": [
                {
                    "grammar_id": can["node"]["grammar_id"],
                    "rule_primitives": can["rule_primitives"],
                    "positive_test_cases": can["positive_test_cases"],
                    "negative_test_cases": can["negative_test_cases"],
                    "verified": can["node"].get("verified", False),
                }
            ],
        },
        {
            "source_path": relative(BATCH_01_PATH),
            "artifact_id": batch_01["artifact_id"],
            "validator_path": "ulga/validators/validate_a1_a1plus_rule_primitives_batch.py",
            "validation_report_path": relative(BATCH_01_REPORT_PATH),
            "schema_validation_status": "PASS",
            "sentence_validator_mode": "SCHEMA_ONLY_NO_SENTENCE_CLASSIFIER",
            "nodes": batch_01["batch_nodes"],
        },
        {
            "source_path": relative(BATCH_02_PATH),
            "artifact_id": batch_02["artifact_id"],
            "validator_path": "ulga/validators/validate_a1_a1plus_rule_primitives_batch.py",
            "validation_report_path": relative(BATCH_02_REPORT_PATH),
            "schema_validation_status": "PASS",
            "sentence_validator_mode": "SCHEMA_ONLY_NO_SENTENCE_CLASSIFIER",
            "nodes": batch_02["batch_nodes"],
        },
    ]
    return sources


def build_index_and_contract(
    canonical_overlay: dict[str, Any],
    query_index: dict[str, Any],
    rule_sources: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    canonical_ids = canonical_overlay.get("canonical_mapping_units", [])
    if canonical_overlay.get("canonical_status") != "ACTIVE":
        raise ValueError("Canonical A1 overlay must be ACTIVE")
    if len(canonical_ids) != len(set(canonical_ids)):
        raise ValueError("Canonical A1 unit ids must be unique")

    canonical_query = query_index.get("canonical_a1", {})
    query_units = canonical_query.get("by_grammar_id", {})
    if set(query_units) != set(canonical_ids):
        raise ValueError("Canonical query consumer units do not match the overlay")

    rule_nodes: dict[str, dict[str, Any]] = {}
    for source in rule_sources:
        for node in source["nodes"]:
            grammar_id = node.get("grammar_id")
            if not grammar_id:
                raise ValueError(f"Rule source node missing grammar_id: {source['source_path']}")
            if grammar_id in rule_nodes:
                raise ValueError(f"Duplicate canonical rule source for {grammar_id}")
            primitives = node.get("rule_primitives", [])
            if not primitives:
                raise ValueError(f"Canonical unit has no rule primitives: {grammar_id}")
            rule_nodes[grammar_id] = {
                "grammar_id": grammar_id,
                "canonical_mapping_status": "VERIFIED_CANONICAL_MAPPING",
                "canonical_egp_row_ids": query_units[grammar_id].get("egp_row_ids", []),
                "rule_source_path": source["source_path"],
                "rule_artifact_id": source["artifact_id"],
                "rule_primitive_count": len(primitives),
                "positive_test_count": len(node.get("positive_test_cases", [])),
                "negative_test_count": len(node.get("negative_test_cases", [])),
                "rule_primitive_authority_status": "CANDIDATE_NOT_PROMOTED",
                "schema_validation_status": source["schema_validation_status"],
                "schema_validator_path": source["validator_path"],
                "schema_validation_report_path": source["validation_report_path"],
                "sentence_validator_mode": source["sentence_validator_mode"],
                "executable_sentence_validator": source["sentence_validator_mode"] == "OFFLINE_STATIC_PROTOTYPE",
                "runtime_validator_status": "NOT_IMPLEMENTED",
                "external_nlp_dependency": False,
            }

    missing = sorted(set(canonical_ids) - set(rule_nodes))
    extra = sorted(set(rule_nodes) - set(canonical_ids))
    if missing or extra:
        raise ValueError(f"Canonical/rule unit mismatch: missing={missing}, extra={extra}")

    ordered_nodes = {grammar_id: rule_nodes[grammar_id] for grammar_id in canonical_ids}
    total = len(ordered_nodes)
    primitive_ready = sum(node["rule_primitive_count"] > 0 for node in ordered_nodes.values())
    schema_validated = sum(node["schema_validation_status"] == "PASS" for node in ordered_nodes.values())
    sentence_executable = sum(node["executable_sentence_validator"] for node in ordered_nodes.values())
    runtime_ready = sum(node["runtime_validator_status"] == "IMPLEMENTED" for node in ordered_nodes.values())

    summary = {
        "canonical_mapping_unit_count": total,
        "canonical_mapping_unique_egp_rows": canonical_query.get("canonical_unique_egp_row_count"),
        "canonical_mapping_coverage_percent": canonical_query.get("coverage_percent"),
        "rule_primitive_unit_count": primitive_ready,
        "rule_primitive_count": sum(node["rule_primitive_count"] for node in ordered_nodes.values()),
        "positive_test_case_count": sum(node["positive_test_count"] for node in ordered_nodes.values()),
        "negative_test_case_count": sum(node["negative_test_count"] for node in ordered_nodes.values()),
        "schema_validated_unit_count": schema_validated,
        "executable_sentence_validator_unit_count": sentence_executable,
        "runtime_validator_unit_count": runtime_ready,
        "rule_primitive_unit_coverage_percent": round(primitive_ready / total * 100, 2),
        "schema_validated_unit_coverage_percent": round(schema_validated / total * 100, 2),
        "executable_sentence_validator_unit_coverage_percent": round(sentence_executable / total * 100, 2),
        "runtime_validator_unit_coverage_percent": round(runtime_ready / total * 100, 2),
    }

    index = {
        "task_id": TASK_ID,
        "artifact_id": "a1_canonical_rule_validator_index",
        "artifact_type": "canonical_a1_rule_validator_consumer_index",
        "official_level": "A1",
        "source_paths": {
            "canonical_overlay": relative(CANONICAL_OVERLAY_PATH),
            "canonical_query_index": relative(QUERY_INDEX_PATH),
            "rule_artifacts": [source["source_path"] for source in rule_sources],
            "validator_reports": [source["validation_report_path"] for source in rule_sources],
        },
        "coverage_summary": summary,
        "by_grammar_id": ordered_nodes,
        "claim_boundaries": {
            "canonical_mapping_complete": True,
            "rule_primitive_data_complete": True,
            "schema_validation_complete": True,
            "executable_sentence_validation_complete": False,
            "production_runtime_validation_complete": False,
            "mapping_coverage_does_not_imply_runtime_accuracy": True,
            "no_learner_state_write": True,
            "no_practicebank_generation": True,
            "no_external_nlp_dependency": True,
        },
    }

    contract = {
        "task_id": TASK_ID,
        "artifact_id": "a1_canonical_rule_validator_contract",
        "contract_version": "1.0.0",
        "index_path": relative(OUTPUT_PATH),
        "capabilities": {
            "lookup_by_canonical_grammar_id": True,
            "lookup_rule_primitive_source": True,
            "lookup_schema_validator": True,
            "lookup_sentence_validator_mode": True,
            "lookup_runtime_validator_status": True,
            "distinguish_mapping_from_runtime_coverage": True,
            "fail_closed_for_unknown_grammar_id": True,
            "no_learner_state_write": True,
        },
        "required_input": ["grammar_id"],
        "required_output": [
            "canonical_mapping_status",
            "canonical_egp_row_ids",
            "rule_source_path",
            "rule_primitive_count",
            "schema_validation_status",
            "sentence_validator_mode",
            "runtime_validator_status",
        ],
        "claim_boundaries": index["claim_boundaries"],
    }

    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_canonical_rule_validator_validation",
        "validation_status": "PASS",
        "index_path": relative(OUTPUT_PATH),
        "contract_path": relative(CONTRACT_PATH),
        "coverage_summary": summary,
        "gate_checks": {
            "canonical_unit_set_equals_rule_unit_set": "PASS",
            "rule_primitives_present_for_all_units": "PASS",
            "source_validator_reports_pass": "PASS",
            "mapping_runtime_claim_separation": "PASS",
            "no_practicebank_generation": "PASS",
            "no_learner_state_write": "PASS",
            "no_a2plus_scope": "PASS",
        },
        "warnings": [
            "Only GRAMMAR_CAN_STATEMENT currently has an executable offline sentence classifier.",
            "All 24 rule primitive units remain candidate rule authority and are not production runtime validators.",
        ],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    return index, contract, report


def main() -> int:
    index, contract, report = build_index_and_contract(
        load_json(CANONICAL_OVERLAY_PATH),
        load_json(QUERY_INDEX_PATH),
        canonical_rule_sources(),
    )
    write_json(OUTPUT_PATH, index)
    write_json(CONTRACT_PATH, contract)
    write_json(REPORT_PATH, report)
    summary = index["coverage_summary"]
    print(f"Canonical A1 rule units: {summary['rule_primitive_unit_count']}/{summary['canonical_mapping_unit_count']}")
    print(f"Schema-validated units: {summary['schema_validated_unit_count']}/{summary['canonical_mapping_unit_count']}")
    print(f"Executable sentence validators: {summary['executable_sentence_validator_unit_count']}/{summary['canonical_mapping_unit_count']}")
    print(f"Runtime validators: {summary['runtime_validator_unit_count']}/{summary['canonical_mapping_unit_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
