#!/usr/bin/env python3
"""Independent reconstruction validator for R3/R4 production population."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_r2_complete_breadth_ontology_deployment_contract as r2
from ulga.builders import build_a1fs_v1_r3_complete_breadth_denominator_coverage_gap_planner as r3
from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4
from ulga.builders import build_a1fs_v1_r3r4_authority_reviewed_production_population as population
from ulga.validators import validate_a1fs_v1_r2_complete_breadth_ontology_deployment_contract as r2_validator

ARTIFACTS = (
    population.PROFILE_OUTPUT,
    population.DEPLOYMENT_OUTPUT,
    population.COVERAGE_OUTPUT,
    population.CANDIDATE_OUTPUT,
    population.POLICY_OUTPUT,
    population.BANK_OUTPUT,
    population.SUPPLY_OUTPUT,
    population.REPORT_OUTPUT,
)


def read(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_not_object:{path}")
    return value


def validate(
    *, ontology_path: Path, graph_path: Path, consumer_path: Path, output_root: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    root = Path(output_root)
    report_path = root / population.REPORT_OUTPUT
    try:
        report = read(report_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {"validation_status": "FAIL", "error_count": 1, "errors": [f"report_unreadable:{exc}"]}
    reviewed_at = report.get("reviewed_at")
    rebuild = root / ".validation_rebuild"
    shutil.rmtree(rebuild, ignore_errors=True)
    try:
        expected_report = population.materialize(
            ontology_path=ontology_path,
            graph_path=graph_path,
            consumer_path=consumer_path,
            output_root=rebuild,
            reviewed_at=str(reviewed_at),
        )
        for name in ARTIFACTS:
            actual = read(root / name)
            expected = read(rebuild / name)
            if actual != expected:
                errors.append(f"artifact_rebuild_drift:{name}")
        if expected_report != report:
            errors.append("report_rebuild_drift")
    except Exception as exc:
        errors.append(f"rebuild_failed:{exc}")
    finally:
        shutil.rmtree(rebuild, ignore_errors=True)

    try:
        profiles = read(root / population.PROFILE_OUTPUT)
        deployments = read(root / population.DEPLOYMENT_OUTPUT)
        coverage = read(root / population.COVERAGE_OUTPUT)
        candidates = read(root / population.CANDIDATE_OUTPUT)
        bank = read(root / population.BANK_OUTPUT)
        supply = read(root / population.SUPPLY_OUTPUT)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"artifact_unreadable:{exc}")
        profiles = deployments = coverage = candidates = bank = supply = {}

    profile_rows = profiles.get("profiles", []) if isinstance(profiles, Mapping) else []
    states = {"PROFILE_DEFINED", population.PARTIAL_PROFILE_STATE, "PROFILE_NOT_POPULATED"}
    for row in profile_rows:
        state = row.get("profile_state")
        if state not in states:
            errors.append(f"profile_state_invalid:{row.get('capability_node_id')}")
            continue
        obligations = row.get("obligations")
        dimension_states = row.get("dimension_states")
        if not isinstance(obligations, list) or not isinstance(dimension_states, Mapping):
            errors.append(f"profile_shape_invalid:{row.get('capability_node_id')}")
            continue
        if state == population.PARTIAL_PROFILE_STATE:
            if not obligations or "NOT_POPULATED" not in set(dimension_states.values()):
                errors.append(f"partial_profile_not_explicitly_incomplete:{row.get('capability_node_id')}")
        if state == "PROFILE_NOT_POPULATED" and obligations:
            errors.append(f"unpopulated_profile_has_obligations:{row.get('capability_node_id')}")
        if state == "PROFILE_DEFINED" and (not obligations or "NOT_POPULATED" in set(dimension_states.values())):
            errors.append(f"defined_profile_incomplete:{row.get('capability_node_id')}")

    for contract in deployments.get("contracts", []) if isinstance(deployments, Mapping) else []:
        contract_errors = r2_validator.validate_contract(contract, r2.build_contract_schema())
        if contract_errors:
            errors.append("deployment_contract_invalid:" + "|".join(contract_errors))

    if coverage:
        core = {key: value for key, value in coverage.items() if key != "report_sha256"}
        if coverage.get("report_sha256") != r3.digest(core):
            errors.append("coverage_digest_invalid")
        counts = coverage.get("counts", {})
        cells = coverage.get("cells", [])
        if counts.get("denominator_cell_count") != len(cells):
            errors.append("coverage_denominator_invalid")
        placeholders = [row for row in cells if row.get("status") == "PROFILE_DEFINITION_REQUIRED"]
        incomplete_nodes = {
            row.get("capability_node_id") for row in profile_rows
            if row.get("profile_state") in {population.PARTIAL_PROFILE_STATE, "PROFILE_NOT_POPULATED"}
        }
        if {row.get("capability_node_id") for row in placeholders} != incomplete_nodes:
            errors.append("partial_or_missing_profile_placeholder_partition_invalid")
        if coverage.get("coverage_metrics", {}).get("false_100_percent_blocked") is not True:
            errors.append("false_100_percent_guard_not_active")

    candidate_rows = candidates.get("candidates", []) if isinstance(candidates, Mapping) else []
    if candidates and candidates.get("candidates_sha256") != r4.digest(candidate_rows):
        errors.append("candidate_registry_digest_invalid")
    if candidates and candidates.get("semantic_sha256") != r4.candidate_registry_semantic_digest(candidate_rows):
        errors.append("candidate_registry_semantic_digest_invalid")
    if bank:
        bank_core = {key: value for key, value in bank.items() if key != "bank_sha256"}
        if bank.get("bank_sha256") != r4.digest(bank_core):
            errors.append("practice_bank_digest_invalid")
        if bank.get("item_count") != len(bank.get("items", [])):
            errors.append("practice_bank_count_invalid")
        for item in bank.get("items", []):
            review = item.get("authority_review", {}) if isinstance(item, Mapping) else {}
            if isinstance(review, Mapping) and "reviewed_at" in review:
                errors.append(f"practice_bank_volatile_review_timestamp:{item.get('item_id')}")
    if supply:
        supply_core = {key: value for key, value in supply.items() if key != "report_sha256"}
        if supply.get("report_sha256") != r4.digest(supply_core):
            errors.append("supply_report_digest_invalid")
        try:
            r4.safe_scan(supply)
        except r4.QuestionSupplyError as exc:
            errors.append(f"supply_safe_scan_failed:{exc}")
    try:
        population.safe_scan(report)
    except population.ProductionPopulationError as exc:
        errors.append(f"population_safe_scan_failed:{exc}")

    boundaries = report.get("claim_boundaries", {})
    for key in (
        "canonical_authority_modified", "m1_graph_modified", "complete_breadth_denominator_reduced",
        "unpopulated_dimensions_hidden", "new_learner_questions_generated", "test_fixture_promoted",
        "learner_mastery_claimed", "retention_claimed", "audio_or_recording_completed",
        "a2_content_admitted", "a2_unlocked", "qwen_required",
    ):
        if boundaries.get(key) is not False:
            errors.append(f"claim_boundary_broken:{key}")

    return {
        "validation_status": population.STATUS if not errors else "FAIL_A1FS_V1_R3R4_PRODUCTION_POPULATION",
        "error_count": len(errors),
        "errors": errors,
        "approved_practice_item_count": report.get("counts", {}).get("approved_practice_item_count", 0),
        "ready_for_local_selection_cell_count": report.get("counts", {}).get("ready_for_local_selection_cell_count", 0),
        "profile_placeholder_cell_count": report.get("counts", {}).get("profile_placeholder_cell_count", 0),
        "next_short_step": population.NEXT_SHORT_STEP if not errors else population.TASK_ID,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ontology", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--consumer", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = validate(
        ontology_path=args.ontology, graph_path=args.graph,
        consumer_path=args.consumer, output_root=args.output_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
