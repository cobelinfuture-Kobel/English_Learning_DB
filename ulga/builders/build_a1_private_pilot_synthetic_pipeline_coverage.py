#!/usr/bin/env python3
"""Exercise every A1/A1+ private-pilot unit without creating learner evidence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import build_and_validate_from_repo
from ulga.builders.import_a1_grammar_text_mode_private_pilot_real_attempts import (
    IMPORT_SCHEMA_VERSION,
    OPEN_PRODUCTIVE_TASK_TYPES,
    run_import,
)

TASK_ID = "R7-M105P08_A1A1PlusRemainingUnitsSyntheticPipelineCoverageAndHumanPilotSampling"
DEFAULT_OUTPUT = REPO_ROOT / "ulga/reports/a1_private_pilot_synthetic_pipeline_coverage.json"
HUMAN_PILOT_UNITS = {
    "GRAMMAR_ARTICLES_BASIC",
    "GRAMMAR_REGULAR_PLURAL_NOUNS",
    "GRAMMAR_SUBJECT_PRONOUNS",
}


def _response_text(item: Mapping[str, Any]) -> str:
    answer_key = item.get("answer_key", {})
    canonical = answer_key.get("canonical_target")
    if isinstance(canonical, str) and canonical.strip():
        return canonical.strip()
    for value in answer_key.get("accepted_texts", []):
        if isinstance(value, str) and value.strip():
            return value.strip()
    for value in item.get("gap_spec", {}).get("accepted_missing_tokens", []):
        if isinstance(value, str) and value.strip():
            return value.strip()
    tokens = item.get("correct_token_sequence")
    if isinstance(tokens, list) and tokens:
        return " ".join(str(value) for value in tokens)
    morphemes = item.get("correct_morphology_parts")
    if isinstance(morphemes, list) and morphemes:
        return "".join(str(value) for value in morphemes)
    raise ValueError(f"synthetic_probe_no_accepted_response:{item.get('item_id')}")


def _source(unit: Mapping[str, Any], item_index: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    grammar_id = unit["grammar_unit_id"]
    item_ids = list(unit["delivery_plan"]["practice_item_ids"]) + list(unit["delivery_plan"]["assessment_item_ids"])
    responses = []
    for item_id in item_ids:
        item = item_index[item_id]
        record: dict[str, Any] = {
            "item_id": item_id,
            "response_text": _response_text(item),
            "attempt_sequence": 1,
            "submitted_at": "2099-01-01T00:00:00Z",
            "evidence_ref": f"synthetic-pipeline://{grammar_id}/{item_id}/attempt/1",
        }
        if item.get("task_type") in OPEN_PRODUCTIVE_TASK_TYPES:
            record.update({
                "score": 1.0,
                "passed": True,
                "evaluator_type": "HYBRID",
                "evaluator_ref": "synthetic-engineering-probe",
                "error_tags": [],
            })
        responses.append(record)
    return {
        "import_schema_version": IMPORT_SCHEMA_VERSION,
        "session": {
            "session_id": f"synthetic-pipeline-{grammar_id.lower()}",
            "learner_ref": "synthetic-engineering-only",
            "operator_ref": "ci-synthetic-probe",
            "started_at": "2099-01-01T00:00:00Z",
            "completed_at": "2099-01-01T00:00:01Z",
            "evidence_source_ref": f"synthetic-pipeline://{grammar_id}",
        },
        "responses": responses,
    }


def build_report() -> dict[str, Any]:
    package, package_report = build_and_validate_from_repo()
    if package_report.get("validation_status") != "PASS":
        raise RuntimeError("synthetic_pipeline_package_validation_failed")
    item_index = {item["item_id"]: item for item in package.get("item_bank", [])}
    units = []
    failures = []
    task_types: set[str] = set()
    for unit in sorted(package.get("learning_units", []), key=lambda row: row["sequence_index"]):
        grammar_id = unit["grammar_unit_id"]
        source = _source(unit, item_index)
        task_types.update(str(item_index[row["item_id"]].get("task_type")) for row in source["responses"])
        _, import_report, normalized, intake_report, projection_bundle = run_import(source, package=package)
        unit_projection = projection_bundle.get("artifact", {}).get("by_grammar_unit_id", {}).get(grammar_id, {})
        checks = {
            "import": import_report.get("validation_status") == "PASS",
            "intake": intake_report.get("validation_status") == "PASS",
            "projection": projection_bundle.get("report", {}).get("validation_status") == "PASS",
            "eight_attempts": len(normalized.get("accepted_attempts", [])) == 8,
            "retention_route": unit_projection.get("projection_status") == "MASTERY_CANDIDATE_PENDING_RETENTION",
            "no_final_mastery": projection_bundle.get("artifact", {}).get("final_mastery_claimed", False) is False,
        }
        if not all(checks.values()):
            failures.append(grammar_id)
        units.append({
            "grammar_unit_id": grammar_id,
            "sequence_index": unit["sequence_index"],
            "human_pilot_sampled": grammar_id in HUMAN_PILOT_UNITS,
            "synthetic_engineering_probe": True,
            "projection_status": unit_projection.get("projection_status"),
            "checks": checks,
        })
    return {
        "task_id": TASK_ID,
        "validation_status": "PASS" if len(units) == 24 and not failures else "FAIL",
        "scope": "A1_A1_PLUS_ONLY",
        "unit_count": len(units),
        "pipeline_pass_unit_count": sum(all(row["checks"].values()) for row in units),
        "human_pilot_sampled_unit_count": sum(row["human_pilot_sampled"] for row in units),
        "synthetic_only_unit_count": sum(not row["human_pilot_sampled"] for row in units),
        "task_type_count": len(task_types),
        "task_types": sorted(task_types),
        "failed_unit_ids": failures,
        "units": units,
        "claims": {
            "learner_evidence_created": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "persistent_learner_state_write": False,
            "production_runtime_event": False,
        },
        "next_short_step": "R7-M105P09_A1A1PlusSyntheticCoverageGapReviewAndHumanPilotMinimumSet",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["validation_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
