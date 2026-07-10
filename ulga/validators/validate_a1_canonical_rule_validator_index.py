#!/usr/bin/env python3
"""Validate the canonical A1 rule/validator consumer integration."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "R7-M104E21C_A1CanonicalExecutableValidatorBatch02Implementation"
NEXT_SHORT_STEP = "R7-M104E22A_A1CanonicalValidatorDispatcherImplementation"
OVERLAY_PATH = REPO_ROOT / "ulga/graph/a1_egp_canonical_mappings.json"
INDEX_PATH = REPO_ROOT / "ulga/graph/a1_canonical_rule_validator_index.json"
CONTRACT_PATH = REPO_ROOT / "ulga/contracts/a1_canonical_rule_validator_contract.json"
REPORT_PATH = REPO_ROOT / "ulga/reports/a1_canonical_rule_validator_validation.json"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate() -> list[str]:
    errors: list[str] = []
    for path in (OVERLAY_PATH, INDEX_PATH, CONTRACT_PATH, REPORT_PATH):
        if not path.is_file():
            errors.append(f"missing required artifact: {path.relative_to(REPO_ROOT)}")
    if errors:
        return errors

    overlay = load(OVERLAY_PATH)
    index = load(INDEX_PATH)
    contract = load(CONTRACT_PATH)
    report = load(REPORT_PATH)

    for name, payload in (("index", index), ("contract", contract), ("report", report)):
        if payload.get("task_id") != TASK_ID:
            errors.append(f"{name} task_id mismatch")

    canonical_ids = overlay.get("canonical_mapping_units", [])
    nodes = index.get("by_grammar_id", {})
    if list(nodes) != canonical_ids:
        errors.append("index canonical unit ordering/set mismatch")
    if len(nodes) != 24:
        errors.append("expected exactly 24 canonical A1 rule units")

    summary = index.get("coverage_summary", {})
    expected_counts = {
        "canonical_mapping_unit_count": 24,
        "canonical_mapping_unique_egp_rows": 109,
        "canonical_mapping_coverage_percent": 100.0,
        "rule_primitive_unit_count": 24,
        "schema_validated_unit_count": 24,
        "executable_sentence_validator_unit_count": 24,
        "runtime_validator_unit_count": 0,
        "rule_primitive_unit_coverage_percent": 100.0,
        "schema_validated_unit_coverage_percent": 100.0,
        "executable_sentence_validator_unit_coverage_percent": 100.0,
        "runtime_validator_unit_coverage_percent": 0.0,
    }
    for key, expected in expected_counts.items():
        if summary.get(key) != expected:
            errors.append(f"coverage summary mismatch for {key}: expected={expected}, actual={summary.get(key)}")

    if report.get("coverage_summary") != summary:
        errors.append("report coverage summary differs from index")
    if report.get("validation_status") != "PASS":
        errors.append("report validation_status must be PASS")
    if report.get("stop_reason") != "NONE":
        errors.append("report stop_reason must be NONE")
    if report.get("next_short_step") != NEXT_SHORT_STEP:
        errors.append("report next_short_step mismatch")

    executable_ids = []
    for grammar_id, node in nodes.items():
        if node.get("canonical_mapping_status") != "VERIFIED_CANONICAL_MAPPING":
            errors.append(f"{grammar_id}: canonical mapping status mismatch")
        if node.get("rule_primitive_count", 0) <= 0:
            errors.append(f"{grammar_id}: no rule primitives")
        if node.get("schema_validation_status") != "PASS":
            errors.append(f"{grammar_id}: schema validation is not PASS")
        if node.get("rule_primitive_authority_status") != "CANDIDATE_NOT_PROMOTED":
            errors.append(f"{grammar_id}: rule authority boundary mismatch")
        if node.get("runtime_validator_status") != "NOT_IMPLEMENTED":
            errors.append(f"{grammar_id}: runtime validator must remain NOT_IMPLEMENTED")
        if node.get("external_nlp_dependency") is not False:
            errors.append(f"{grammar_id}: external NLP dependency must be false")
        if node.get("executable_sentence_validator"):
            executable_ids.append(grammar_id)
            if not node.get("sentence_validator_path") or not node.get("sentence_validation_report_path"):
                errors.append(f"{grammar_id}: executable validator source/report missing")

    expected_executable = set(canonical_ids)
    if set(executable_ids) != expected_executable:
        errors.append(f"unexpected executable sentence validator set: {executable_ids}")

    boundaries = index.get("claim_boundaries", {})
    for key in (
        "canonical_mapping_complete",
        "rule_primitive_data_complete",
        "schema_validation_complete",
        "mapping_coverage_does_not_imply_runtime_accuracy",
        "no_learner_state_write",
        "no_practicebank_generation",
        "no_external_nlp_dependency",
    ):
        if boundaries.get(key) is not True:
            errors.append(f"claim boundary must be true: {key}")
    if boundaries.get("executable_sentence_validation_complete") is not True:
        errors.append("claim boundary must be true: executable_sentence_validation_complete")
    if boundaries.get("production_runtime_validation_complete") is not False:
        errors.append("claim boundary must be false: production_runtime_validation_complete")

    capabilities = contract.get("capabilities", {})
    if not capabilities or not all(value is True for value in capabilities.values()):
        errors.append("all declared contract capabilities must be true")
    if contract.get("contract_version") != "1.0.0":
        errors.append("contract version mismatch")
    if contract.get("claim_boundaries") != boundaries:
        errors.append("contract claim boundaries differ from index")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("A1 canonical rule-validator integration: FAIL")
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("A1 canonical rule-validator integration: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
