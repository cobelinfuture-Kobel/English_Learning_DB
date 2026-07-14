#!/usr/bin/env python3
"""Integrate the current Reading contract surface and fail closed on missing sources.

This M04A milestone proves that the 96 grammar-aligned Reading candidates and
the six-type ReadingV1 PracticeBank contract are healthy, while refusing to
claim source-grounded ReadingV1 completion when the CI-readable RAZ intake is
empty. No raw RAZ or full-passage text is persisted by this artifact.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_a1plus_shared_item_contract import (
    build_artifact as build_shared_items,
)
from ulga.builders.build_raz_reading_authority_intake_query_index import build_index
from ulga.builders.build_reading_v1_practice_bank import (
    build_validated_synthetic_practice_bank,
)

TASK_ID = "E4S-A1V1-M04A_ReadingGrammarIntegrationAndSourceAvailabilityGate"
EPIC_ID = "E4S-A1V1_A1A1PlusCompleteFourSkillLearningSystem"
ARTIFACT_ID = "e4s_a1v1_reading_v1_integration_gate"
PASS_STATUS = "PASS_READING_INTEGRATION_SOURCE_GAP_IDENTIFIED"
OUTPUT_PATH = REPO_ROOT / "ulga/reports/e4s_a1v1_reading_v1_integration_gate.json"
RESUME_TASK = "E4S-A1V1-M04B_SourceGroundedReadingPracticeBankCompletion"
DRIVE_RAZ_OUTPUT_FOLDER_ID = "15P1dahD12t9Hsht1cPKIEj8K0oPc6Noz"
V1_QUESTION_TYPES = {
    "literal_who",
    "literal_what",
    "literal_where",
    "true_false",
    "sentence_ordering",
    "cloze_vocabulary",
}


def _reading_items(shared: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    items = [item for item in shared.get("shared_items", []) if item.get("skill") == "reading"]
    if len(items) != 96:
        raise ValueError(f"m04_reading_shared_item_count_not_96:{len(items)}")
    return items


def build_report() -> dict[str, Any]:
    shared = build_shared_items()
    reading_items = _reading_items(shared)
    fixture = build_validated_synthetic_practice_bank()
    intake = build_index()

    by_unit = Counter(str(item.get("grammar_unit_id")) for item in reading_items)
    role_counts = Counter(str(item.get("item_role")) for item in reading_items)
    task_type_counts = Counter(str(item.get("task_type")) for item in reading_items)
    source_kind_counts = Counter(
        str(item.get("source_trace", {}).get("source_kind")) for item in reading_items
    )
    fixture_items = fixture.get("items", [])
    fixture_types = {str(item.get("question_type")) for item in fixture_items}
    fixture_summary = fixture.get("validation_summary", {})
    intake_items = intake.get("items", [])
    intake_levels = intake.get("levels", [])
    intake_summary = intake.get("summary", {})

    if len(by_unit) != 24 or set(by_unit.values()) != {4}:
        raise ValueError("m04_reading_shared_items_not_24x4")
    if role_counts != Counter({"practice": 72, "assessment": 24}):
        raise ValueError(f"m04_reading_role_counts_invalid:{dict(role_counts)}")
    if source_kind_counts != Counter({"READING_WRITING_TEXT_MODE": 96}):
        raise ValueError("m04_reading_source_kind_invalid")
    if len(fixture_items) != 6 or fixture_types != V1_QUESTION_TYPES:
        raise ValueError("m04_reading_v1_fixture_not_six_question_types")
    if fixture_summary.get("validator_status") != "PASS":
        raise RuntimeError("m04_reading_v1_fixture_validation_failed")

    source_count = len(intake_items)
    source_available = source_count > 0
    stop_reason = "NONE" if source_available else "SOURCE_EVIDENCE_REQUIRED"
    blocker_type = None if source_available else "CI_READABLE_READING_SOURCE_ARTIFACT_MISSING"

    return {
        "task_id": TASK_ID,
        "epic_id": EPIC_ID,
        "artifact_id": ARTIFACT_ID,
        "validation_status": PASS_STATUS,
        "scope": "A1_A1_PLUS_ONLY",
        "reading_grammar_integration": {
            "status": "PASS",
            "shared_reading_item_count": len(reading_items),
            "learning_unit_count": len(by_unit),
            "items_per_unit": 4,
            "practice_item_count": role_counts["practice"],
            "assessment_item_count": role_counts["assessment"],
            "task_type_counts": dict(sorted(task_type_counts.items())),
            "source_kind_counts": dict(sorted(source_kind_counts.items())),
            "semantic_role": "GRAMMAR_ALIGNED_READING_RECOGNITION",
            "not_claimed_as": "SOURCE_GROUNDED_PASSAGE_COMPREHENSION",
        },
        "reading_v1_contract_fixture": {
            "status": "PASS",
            "validator_status": fixture_summary.get("validator_status"),
            "item_count": len(fixture_items),
            "question_types": sorted(fixture_types),
            "html_ready_count": fixture_summary.get("html_ready_count"),
            "blocked_count": fixture_summary.get("blocked_count"),
            "grammar_gate_status": fixture_summary.get("grammar_gate_status"),
            "synthetic_fixture_only": True,
            "real_source_coverage_claimed": False,
        },
        "reading_source_availability": {
            "status": "AVAILABLE" if source_available else "BLOCKED",
            "github_ci_readable_intake_item_count": source_count,
            "github_ci_readable_levels": list(intake_levels),
            "intake_summary_status": intake_summary.get("status"),
            "intake_warning_count": len(intake_summary.get("warnings", [])),
            "drive_source_folder_discovered": True,
            "drive_source_folder_id": DRIVE_RAZ_OUTPUT_FOLDER_ID,
            "drive_connector_visible_structure": "LEVEL_A_TO_W_AND_DERIVED_FOLDERS",
            "drive_connector_visible_normalized_file_count": 0,
            "raw_source_text_persisted": False,
            "full_passage_text_persisted": False,
            "source_payload_copied_to_repo": False,
        },
        "m04_gate": {
            "grammar_reading_bank_integrated": True,
            "reading_v1_six_type_contract_healthy": True,
            "source_grounded_comprehension_content_available": source_available,
            "reading_v1_complete": False,
            "m05_progression_allowed": False,
        },
        "required_operator_action": (
            None
            if source_available
            else (
                "Provide a CI-readable metadata-only/derived Reading source artifact for A1/A1+ "
                "with stable source_unit_ref/source_locator, level, source policy, and evidence tags; "
                "do not commit raw RAZ or full-passage text. Alternatively run the local RAZ intake "
                "pipeline and provide the approved safe derived PracticeBank candidates plus evidence refs."
            )
        ),
        "claim_boundaries": {
            "m04a_integration_gate_complete": True,
            "m04_reading_v1_complete": False,
            "grammar_reading_items_are_source_grounded_comprehension": False,
            "synthetic_fixture_is_real_source_coverage": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "persistent_learner_state_write": False,
            "production_runtime_event": False,
            "a2_a2plus_in_scope": False,
        },
        "stop_reason": stop_reason,
        "blocker_type": blocker_type,
        "last_completed_status": "M04A_READING_INTEGRATION_GATE_COMPLETE",
        "next_short_step": RESUME_TASK if source_available else None,
        "next_resume_task": RESUME_TASK,
    }


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    report = build_report()
    write_json(args.output, report)
    print(json.dumps({
        "validation_status": report["validation_status"],
        "reading_item_count": report["reading_grammar_integration"]["shared_reading_item_count"],
        "source_item_count": report["reading_source_availability"]["github_ci_readable_intake_item_count"],
        "stop_reason": report["stop_reason"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
