"""Offline batch validator for A1/A1+ rule primitive data.

This is a schema-and-test-consistency validator for candidate rule primitive
artifacts. It intentionally does not implement a production grammar parser and
must not be used to claim verified EGP coverage.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_NODE_FIELDS = {
    "grammar_id",
    "zh_label",
    "en_label",
    "candidate_bucket_count",
    "rule_primitives",
    "positive_test_cases",
    "negative_test_cases",
    "verified",
}

REQUIRED_PRIMITIVE_FIELDS = {
    "rule_id",
    "core_pattern",
    "required_gates",
    "false_positive_filters",
}


def validate_batch(batch: dict[str, Any]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    errors: list[str] = []

    nodes = batch.get("batch_nodes", [])
    if not isinstance(nodes, list) or not nodes:
        errors.append("batch_nodes must be a non-empty list")
        nodes = []

    for node in nodes:
        grammar_id = node.get("grammar_id", "<missing>")
        missing_node_fields = sorted(REQUIRED_NODE_FIELDS - set(node.keys()))
        node_errors: list[str] = []
        if missing_node_fields:
            node_errors.append(f"missing_node_fields={missing_node_fields}")
        if node.get("verified") is not False:
            node_errors.append("verified must be false for candidate batch")
        if not isinstance(node.get("candidate_bucket_count"), int) or node.get("candidate_bucket_count", 0) <= 0:
            node_errors.append("candidate_bucket_count must be positive integer")

        primitives = node.get("rule_primitives", [])
        if not isinstance(primitives, list) or not primitives:
            node_errors.append("rule_primitives must be non-empty list")
            primitives = []
        for primitive in primitives:
            missing_primitive_fields = sorted(REQUIRED_PRIMITIVE_FIELDS - set(primitive.keys()))
            if missing_primitive_fields:
                node_errors.append(f"{primitive.get('rule_id', '<missing>')}: missing_primitive_fields={missing_primitive_fields}")
            if not primitive.get("required_gates"):
                node_errors.append(f"{primitive.get('rule_id', '<missing>')}: required_gates empty")
            if not primitive.get("false_positive_filters"):
                node_errors.append(f"{primitive.get('rule_id', '<missing>')}: false_positive_filters empty")

        for case_field in ("positive_test_cases", "negative_test_cases"):
            cases = node.get(case_field, [])
            if not isinstance(cases, list) or not cases:
                node_errors.append(f"{case_field} must be non-empty list")
            elif not all(isinstance(case, str) and case.strip() for case in cases):
                node_errors.append(f"{case_field} must contain non-empty strings")

        status = "PASS" if not node_errors else "FAIL"
        if node_errors:
            errors.extend(f"{grammar_id}: {err}" for err in node_errors)
        results.append(
            {
                "grammar_id": grammar_id,
                "primitive_count": len(primitives),
                "positive_test_count": len(node.get("positive_test_cases", [])) if isinstance(node.get("positive_test_cases"), list) else 0,
                "negative_test_count": len(node.get("negative_test_cases", [])) if isinstance(node.get("negative_test_cases"), list) else 0,
                "status": status,
                "errors": node_errors,
            }
        )

    return {
        "node_count": len(nodes),
        "pass_node_count": sum(1 for item in results if item["status"] == "PASS"),
        "fail_node_count": sum(1 for item in results if item["status"] == "FAIL"),
        "errors": errors,
        "node_results": results,
    }


def build_report(batch: dict[str, Any], source_path: str) -> dict[str, Any]:
    validation = validate_batch(batch)
    status = "PASS" if validation["fail_node_count"] == 0 and not validation["errors"] else "FAIL"
    return {
        "task_id": "R7-M104E18A_BatchPrimitivesAndValidator_NoNewDesignDocs",
        "artifact_type": "batch_validator_output_report",
        "validator_mode": "offline_schema_and_test_consistency_no_external_nlp",
        "source_batch_artifact": source_path,
        "scope_constraints": {
            "no_new_design_docs": True,
            "no_practicebank_generation": True,
            "no_learner_state_write": True,
            "no_canonical_graph_write": True,
            "no_verified_egp_ref_backfill": True,
            "no_grammar_nodes_json_write": True,
            "no_grammar_coverage_matrix_write": True,
            "no_a2_a2plus_expansion": True,
            "no_external_nlp_dependency_integration": True,
        },
        "validation_summary": {
            "node_count": validation["node_count"],
            "pass_node_count": validation["pass_node_count"],
            "fail_node_count": validation["fail_node_count"],
            "status": status,
        },
        "node_results": validation["node_results"],
        "result_status": {
            "batch_validator_status": "BUILT",
            "test_status": status,
            "runtime_validator_status": "NOT_IMPLEMENTED",
            "verified_mapping_status": "NOT_STARTED",
            "coverage_status": "NO_VERIFIED_COVERAGE_CLAIM",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--batch-artifact",
        default="ulga/rules/a1_a1plus_rule_primitives_batch_01.json",
    )
    parser.add_argument(
        "--output",
        default="ulga/reports/a1_a1plus_rule_primitives_batch_01_validation.json",
    )
    args = parser.parse_args()

    source_path = Path(args.batch_artifact)
    output_path = Path(args.output)
    batch = json.loads(source_path.read_text(encoding="utf-8"))
    report = build_report(batch, args.batch_artifact)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if report["validation_summary"]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
