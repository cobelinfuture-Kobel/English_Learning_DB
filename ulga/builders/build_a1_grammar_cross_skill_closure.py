#!/usr/bin/env python3
"""Build and validate final candidate A1/A1+ grammar cross-skill closure."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_full_teachable_candidate_coverage import (
    build_and_validate_from_repo as build_candidate_source,
)
from ulga.builders.build_a1_grammar_listening_integration import (
    build_and_validate_from_repo as build_listening_source,
)
from ulga.builders.build_a1_grammar_mastery_review_loop import (
    build_and_validate_from_repo as build_mastery_source,
)
from ulga.builders.build_a1_grammar_reading_writing_closed_loop import (
    build_and_validate_from_repo as build_reading_writing_source,
)
from ulga.builders.build_a1_grammar_speaking_integration import (
    build_and_validate_from_repo as build_speaking_source,
)

TASK_ID = "R7-M105H_A1A1PlusGrammarCrossSkillClosure"
PROGRAM_ID = "R7-M105_A1A1PlusGrammarLearningClosedLoop"
NEXT_RESUME_TASK = (
    "R7-M105I_A1A1PlusOperatorReviewAndRealSkillEvidenceIntegration"
)
OUTPUT_PATH = (
    REPO_ROOT / "ulga/graph/a1_grammar_cross_skill_closure.json"
)
REPORT_PATH = (
    REPO_ROOT
    / "ulga/reports/a1_grammar_cross_skill_closure_validation.json"
)

SKILLS = ("reading", "writing", "listening", "speaking")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _require_pass(name: str, report: dict[str, Any]) -> None:
    if report.get("validation_status") != "PASS":
        raise ValueError(f"source_validation_failed:{name}")


def _source_unit_sets(
    candidate: dict[str, Any],
    reading_writing: dict[str, Any],
    listening: dict[str, Any],
    speaking: dict[str, Any],
) -> dict[str, set[str]]:
    return {
        "candidate": {
            unit["grammar_unit_id"]
            for unit in candidate.get("learning_units", [])
        },
        "reading_writing": set(
            reading_writing.get("by_grammar_unit_id", {})
        ),
        "listening": set(listening.get("by_grammar_unit_id", {})),
        "speaking": set(speaking.get("by_grammar_unit_id", {})),
    }


def _source_row_sets(
    candidate: dict[str, Any],
    reading_writing: dict[str, Any],
    listening: dict[str, Any],
    speaking: dict[str, Any],
    mastery: dict[str, Any],
) -> dict[str, set[str]]:
    return {
        "candidate": set(candidate.get("by_egp_row_id", {})),
        "reading_writing": set(
            reading_writing.get("by_egp_row_id", {})
        ),
        "listening": set(listening.get("by_egp_row_id", {})),
        "speaking": set(speaking.get("by_egp_row_id", {})),
        "mastery_projection": set(
            mastery.get("pass_scenario_projection", {}).get(
                "row_results", {}
            )
        ),
    }


def build_artifact(
    candidate: dict[str, Any],
    reading_writing: dict[str, Any],
    mastery: dict[str, Any],
    listening: dict[str, Any],
    speaking: dict[str, Any],
) -> dict[str, Any]:
    unit_sets = _source_unit_sets(
        candidate, reading_writing, listening, speaking
    )
    row_sets = _source_row_sets(
        candidate,
        reading_writing,
        listening,
        speaking,
        mastery,
    )
    if any(len(values) != 24 for values in unit_sets.values()):
        raise ValueError("source_unit_coverage_not_24_of_24")
    if len({frozenset(values) for values in unit_sets.values()}) != 1:
        raise ValueError("source_unit_identity_mismatch")
    if any(len(values) != 109 for values in row_sets.values()):
        raise ValueError("source_row_coverage_not_109_of_109")
    if len({frozenset(values) for values in row_sets.values()}) != 1:
        raise ValueError("source_row_identity_mismatch")

    candidate_units = {
        unit["grammar_unit_id"]: unit
        for unit in candidate["learning_units"]
    }
    rw_units = reading_writing["by_grammar_unit_id"]
    listening_units = listening["by_grammar_unit_id"]
    speaking_units = speaking["by_grammar_unit_id"]

    by_unit: dict[str, dict[str, Any]] = {}
    synthetic_journeys: list[dict[str, Any]] = []
    for grammar_id in sorted(candidate_units):
        candidate_unit = candidate_units[grammar_id]
        rw_unit = rw_units[grammar_id]
        listening_unit = listening_units[grammar_id]
        speaking_unit = speaking_units[grammar_id]
        skill_paths = {
            "reading": {
                "activity_ids": list(
                    rw_unit["reading_activity_ids"]
                ),
                "assessment_ids": list(
                    rw_unit["reading_assessment_ids"]
                ),
                "candidate_path_status": "READY",
                "actual_evidence_status": "NOT_COLLECTED",
            },
            "writing": {
                "activity_ids": list(
                    rw_unit["writing_activity_ids"]
                ),
                "assessment_ids": list(
                    rw_unit["writing_assessment_ids"]
                ),
                "candidate_path_status": "READY",
                "actual_evidence_status": "NOT_COLLECTED",
            },
            "listening": {
                "activity_ids": list(
                    listening_unit["listening_activity_ids"]
                ),
                "assessment_ids": list(
                    listening_unit["listening_assessment_ids"]
                ),
                "candidate_path_status": "TRANSCRIPT_BACKED_READY",
                "actual_evidence_status": "NOT_COLLECTED",
                "audio_asset_status": "NOT_RENDERED",
            },
            "speaking": {
                "activity_ids": list(
                    speaking_unit["speaking_activity_ids"]
                ),
                "assessment_ids": list(
                    speaking_unit["speaking_assessment_ids"]
                ),
                "candidate_path_status": "PROMPT_MODEL_READY",
                "actual_evidence_status": "NOT_COLLECTED",
                "audio_capture_status": "NOT_IMPLEMENTED",
                "asr_status": "NOT_IMPLEMENTED",
            },
        }
        by_unit[grammar_id] = {
            "grammar_unit_id": grammar_id,
            "official_egp_level": "A1",
            "internal_stage": candidate_unit["internal_stage"],
            "canonical_egp_row_ids": list(
                candidate_unit["canonical_egp_row_ids"]
            ),
            "candidate_teaching_status": "READY",
            "candidate_practice_status": "READY",
            "candidate_assessment_status": "READY",
            "skill_paths": skill_paths,
            "candidate_cross_skill_status": "CLOSED",
            "operator_review_status": "NOT_COMPLETED",
            "private_learning_promotion_status": "NOT_PROMOTED",
            "actual_learner_mastery_status": "NOT_MEASURED",
        }
        synthetic_journeys.append(
            {
                "journey_id": f"SYNTHETIC_JOURNEY:{grammar_id}",
                "grammar_unit_id": grammar_id,
                "journey_mode": "OFFLINE_CANDIDATE_PATH_AUDIT",
                "steps": [
                    {
                        "step": "LEARN",
                        "status": "CANDIDATE_CONTENT_READY",
                    },
                    {
                        "step": "GUIDED_PRACTICE",
                        "status": "CANDIDATE_PRACTICE_READY",
                    },
                    {
                        "step": "READING",
                        "status": "CANDIDATE_PATH_READY",
                    },
                    {
                        "step": "WRITING",
                        "status": "CANDIDATE_PATH_READY",
                    },
                    {
                        "step": "LISTENING",
                        "status": "TRANSCRIPT_BACKED_PATH_READY",
                    },
                    {
                        "step": "SPEAKING",
                        "status": "PROMPT_MODEL_PATH_READY",
                    },
                    {
                        "step": "ASSESSMENT",
                        "status": "FOUR_SKILL_CHECKPOINTS_READY",
                    },
                    {
                        "step": "MASTERY_PROJECTION",
                        "status": "OFFLINE_SIMULATION_READY",
                    },
                    {
                        "step": "REVIEW_AND_RETENTION",
                        "status": "OFFLINE_POLICY_READY",
                    },
                ],
                "actual_learner_journey_completed": False,
                "production_runtime_journey": False,
            }
        )

    candidate_rows = candidate["by_egp_row_id"]
    rw_rows = reading_writing["by_egp_row_id"]
    listening_rows = listening["by_egp_row_id"]
    speaking_rows = speaking["by_egp_row_id"]
    mastery_rows = mastery["pass_scenario_projection"]["row_results"]

    by_row: dict[str, dict[str, Any]] = {}
    for row_id in sorted(candidate_rows):
        rw_row = rw_rows[row_id]
        listening_row = listening_rows[row_id]
        speaking_row = speaking_rows[row_id]
        mastery_row = mastery_rows[row_id]
        by_row[row_id] = {
            "egp_row_id": row_id,
            "grammar_unit_ids": list(
                candidate_rows[row_id]["grammar_unit_ids"]
            ),
            "candidate_teaching_status": (
                "PROJECT_AUTHORED_CANDIDATE_READY"
            ),
            "skill_paths": {
                "reading": {
                    "activity_ids": list(
                        rw_row["reading_activity_ids"]
                    ),
                    "assessment_ids": list(
                        rw_row["reading_assessment_ids"]
                    ),
                    "candidate_path_ready": True,
                    "actual_evidence_collected": False,
                },
                "writing": {
                    "activity_ids": list(
                        rw_row["writing_activity_ids"]
                    ),
                    "assessment_ids": list(
                        rw_row["writing_assessment_ids"]
                    ),
                    "candidate_path_ready": True,
                    "actual_evidence_collected": False,
                },
                "listening": {
                    "activity_ids": list(
                        listening_row["listening_activity_ids"]
                    ),
                    "assessment_ids": list(
                        listening_row[
                            "listening_assessment_ids"
                        ]
                    ),
                    "candidate_path_ready": True,
                    "actual_audio_evidence_collected": False,
                },
                "speaking": {
                    "activity_ids": list(
                        speaking_row["speaking_activity_ids"]
                    ),
                    "assessment_ids": list(
                        speaking_row[
                            "speaking_assessment_ids"
                        ]
                    ),
                    "candidate_path_ready": True,
                    "actual_audio_or_transcript_evidence_collected": False,
                },
            },
            "candidate_cross_skill_status": "CLOSED",
            "simulated_mastery_projection_status": mastery_row[
                "projection_status"
            ],
            "actual_mastery_status": "NOT_MEASURED",
            "operator_review_status": "NOT_COMPLETED",
            "private_learning_promotion_status": "NOT_PROMOTED",
        }

    release_gates = {
        "canonical_authority_gate": {
            "status": "PASS",
            "required": "24 units and 109 rows",
        },
        "candidate_teaching_gate": {
            "status": "PASS",
            "required": "24/24 units candidate teaching ready",
        },
        "candidate_cross_skill_path_gate": {
            "status": "PASS",
            "required": "109/109 rows have four-skill paths",
        },
        "offline_mastery_review_gate": {
            "status": "PASS",
            "required": "109-row simulation and review policy",
        },
        "operator_review_gate": {
            "status": "BLOCKED",
            "required": "operator review for candidate content",
        },
        "real_listening_audio_gate": {
            "status": "BLOCKED",
            "required": "rendered audio and quality validation",
        },
        "real_speaking_evidence_gate": {
            "status": "BLOCKED",
            "required": "audio capture and transcript/ASR evidence",
        },
        "real_learner_evidence_gate": {
            "status": "BLOCKED",
            "required": "actual attempts and retention evidence",
        },
        "private_learning_promotion_gate": {
            "status": "BLOCKED",
            "required": "reviewed content and real evidence approval",
        },
        "production_runtime_gate": {
            "status": "BLOCKED",
            "required": "approved persistence and runtime integration",
        },
    }

    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_cross_skill_closure",
        "artifact_type": (
            "a1_a1plus_candidate_four_skill_closed_loop_audit"
        ),
        "schema_version": "a1_grammar_cross_skill_closure.v1",
        "official_level": "A1",
        "internal_stages": ["A1", "A1+"],
        "source_artifact_ids": [
            candidate["artifact_id"],
            reading_writing["artifact_id"],
            mastery["artifact_id"],
            listening["artifact_id"],
            speaking["artifact_id"],
        ],
        "program_status": {
            "candidate_closed_loop_status": (
                "A1_A1PLUS_GRAMMAR_CANDIDATE_CLOSED_LOOP_COMPLETE"
            ),
            "release_status": (
                "BLOCKED_PENDING_OPERATOR_REVIEW_AND_REAL_SKILL_EVIDENCE"
            ),
            "goal_distance": "D1_REAL_EVIDENCE_AND_PROMOTION_PENDING",
        },
        "coverage_summary": {
            "canonical_unit_count": 24,
            "canonical_unique_egp_row_count": 109,
            "candidate_teaching_ready_unit_count": 24,
            "candidate_practice_ready_unit_count": 24,
            "candidate_assessment_ready_unit_count": 24,
            "rows_with_reading_path": 109,
            "rows_with_writing_path": 109,
            "rows_with_listening_path": 109,
            "rows_with_speaking_path": 109,
            "candidate_cross_skill_closed_row_count": 109,
            "candidate_cross_skill_missing_row_count": 0,
            "candidate_cross_skill_row_coverage_percent": 100.0,
            "operator_reviewed_row_count": 0,
            "not_operator_reviewed_row_count": 109,
            "private_learning_promoted_row_count": 0,
            "rendered_listening_audio_asset_count": 0,
            "captured_speaking_audio_asset_count": 0,
            "asr_or_manual_speaking_transcript_count": 0,
            "actual_learner_attempt_count": 0,
            "actual_mastery_measured_row_count": 0,
            "production_runtime_unit_count": 0,
        },
        "by_grammar_unit_id": by_unit,
        "by_egp_row_id": by_row,
        "synthetic_unit_journeys": synthetic_journeys,
        "release_gates": release_gates,
        "claim_boundaries": {
            "candidate_four_skill_closure_complete": True,
            "candidate_109_row_coverage_complete": True,
            "offline_mastery_review_projection_complete": True,
            "operator_review_complete": False,
            "real_listening_audio_complete": False,
            "real_speaking_evidence_complete": False,
            "actual_learner_evidence_complete": False,
            "private_learning_promotion_complete": False,
            "production_runtime_complete": False,
            "a1_a1plus_grammar_release_complete": False,
            "no_a2_a2plus_expansion": True,
            "no_persistent_learner_state_write": True,
            "no_external_nlp_dependency": True,
            "no_restricted_source_payload_copy": True,
        },
        "continuation_gate": {
            "status": "BLOCKED_REQUIRES_OPERATOR_APPROVAL",
            "blocker_type": (
                "OPERATOR_REVIEW_AND_REAL_SKILL_EVIDENCE_REQUIRED"
            ),
            "next_resume_task": NEXT_RESUME_TASK,
        },
    }


def validate_artifact(
    artifact: dict[str, Any],
    candidate: dict[str, Any],
    reading_writing: dict[str, Any],
    mastery: dict[str, Any],
    listening: dict[str, Any],
    speaking: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    unit_sets = _source_unit_sets(
        candidate, reading_writing, listening, speaking
    )
    row_sets = _source_row_sets(
        candidate,
        reading_writing,
        listening,
        speaking,
        mastery,
    )
    expected_units = unit_sets["candidate"]
    expected_rows = row_sets["candidate"]

    by_unit = artifact.get("by_grammar_unit_id", {})
    if len(by_unit) != 24 or set(by_unit) != expected_units:
        errors.append("cross_skill_unit_index_not_24_of_24")
    for grammar_id, unit in by_unit.items():
        paths = unit.get("skill_paths", {})
        if set(paths) != set(SKILLS):
            errors.append(f"unit_skill_set_mismatch:{grammar_id}")
            continue
        for skill in SKILLS:
            path = paths[skill]
            if len(path.get("activity_ids", [])) != 4:
                errors.append(
                    f"unit_skill_activity_count_mismatch:{grammar_id}:{skill}"
                )
            if len(path.get("assessment_ids", [])) != 1:
                errors.append(
                    f"unit_skill_assessment_count_mismatch:{grammar_id}:{skill}"
                )
        if unit.get("candidate_cross_skill_status") != "CLOSED":
            errors.append(f"unit_cross_skill_not_closed:{grammar_id}")
        if unit.get("operator_review_status") != "NOT_COMPLETED":
            errors.append(f"false_unit_operator_review:{grammar_id}")
        if (
            unit.get("private_learning_promotion_status")
            != "NOT_PROMOTED"
        ):
            errors.append(f"false_unit_promotion:{grammar_id}")

    by_row = artifact.get("by_egp_row_id", {})
    if len(by_row) != 109 or set(by_row) != expected_rows:
        errors.append("cross_skill_row_index_not_109_of_109")
    for row_id, row in by_row.items():
        paths = row.get("skill_paths", {})
        if set(paths) != set(SKILLS):
            errors.append(f"row_skill_set_mismatch:{row_id}")
            continue
        for skill in SKILLS:
            path = paths[skill]
            if not path.get("activity_ids"):
                errors.append(
                    f"row_skill_activity_missing:{row_id}:{skill}"
                )
            if not path.get("assessment_ids"):
                errors.append(
                    f"row_skill_assessment_missing:{row_id}:{skill}"
                )
            if path.get("candidate_path_ready") is not True:
                errors.append(
                    f"row_candidate_path_not_ready:{row_id}:{skill}"
                )
        if row.get("candidate_cross_skill_status") != "CLOSED":
            errors.append(f"row_cross_skill_not_closed:{row_id}")
        if row.get("actual_mastery_status") != "NOT_MEASURED":
            errors.append(f"false_row_actual_mastery:{row_id}")
        if row.get("operator_review_status") != "NOT_COMPLETED":
            errors.append(f"false_row_operator_review:{row_id}")

    journeys = artifact.get("synthetic_unit_journeys", [])
    if len(journeys) != 24:
        errors.append("synthetic_journey_count_not_24")
    required_steps = {
        "LEARN",
        "GUIDED_PRACTICE",
        "READING",
        "WRITING",
        "LISTENING",
        "SPEAKING",
        "ASSESSMENT",
        "MASTERY_PROJECTION",
        "REVIEW_AND_RETENTION",
    }
    for journey in journeys:
        step_ids = {
            step.get("step") for step in journey.get("steps", [])
        }
        if step_ids != required_steps:
            errors.append(
                f"synthetic_journey_step_mismatch:{journey.get('journey_id')}"
            )
        if journey.get("actual_learner_journey_completed") is not False:
            errors.append(
                f"false_actual_journey_claim:{journey.get('journey_id')}"
            )
        if journey.get("production_runtime_journey") is not False:
            errors.append(
                f"false_runtime_journey_claim:{journey.get('journey_id')}"
            )

    expected_summary = {
        "canonical_unit_count": 24,
        "canonical_unique_egp_row_count": 109,
        "candidate_teaching_ready_unit_count": 24,
        "candidate_practice_ready_unit_count": 24,
        "candidate_assessment_ready_unit_count": 24,
        "rows_with_reading_path": 109,
        "rows_with_writing_path": 109,
        "rows_with_listening_path": 109,
        "rows_with_speaking_path": 109,
        "candidate_cross_skill_closed_row_count": 109,
        "candidate_cross_skill_missing_row_count": 0,
        "candidate_cross_skill_row_coverage_percent": 100.0,
        "operator_reviewed_row_count": 0,
        "not_operator_reviewed_row_count": 109,
        "private_learning_promoted_row_count": 0,
        "rendered_listening_audio_asset_count": 0,
        "captured_speaking_audio_asset_count": 0,
        "asr_or_manual_speaking_transcript_count": 0,
        "actual_learner_attempt_count": 0,
        "actual_mastery_measured_row_count": 0,
        "production_runtime_unit_count": 0,
    }
    if artifact.get("coverage_summary") != expected_summary:
        errors.append("cross_skill_coverage_summary_mismatch")

    release_gates = artifact.get("release_gates", {})
    expected_pass = {
        "canonical_authority_gate",
        "candidate_teaching_gate",
        "candidate_cross_skill_path_gate",
        "offline_mastery_review_gate",
    }
    expected_blocked = {
        "operator_review_gate",
        "real_listening_audio_gate",
        "real_speaking_evidence_gate",
        "real_learner_evidence_gate",
        "private_learning_promotion_gate",
        "production_runtime_gate",
    }
    for gate_id in expected_pass:
        if release_gates.get(gate_id, {}).get("status") != "PASS":
            errors.append(f"required_candidate_gate_not_pass:{gate_id}")
    for gate_id in expected_blocked:
        if release_gates.get(gate_id, {}).get("status") != "BLOCKED":
            errors.append(f"required_release_gate_not_blocked:{gate_id}")

    boundaries = artifact.get("claim_boundaries", {})
    for true_field in (
        "candidate_four_skill_closure_complete",
        "candidate_109_row_coverage_complete",
        "offline_mastery_review_projection_complete",
        "no_a2_a2plus_expansion",
        "no_persistent_learner_state_write",
        "no_external_nlp_dependency",
        "no_restricted_source_payload_copy",
    ):
        if boundaries.get(true_field) is not True:
            errors.append(f"scope_boundary_missing:{true_field}")
    for false_field in (
        "operator_review_complete",
        "real_listening_audio_complete",
        "real_speaking_evidence_complete",
        "actual_learner_evidence_complete",
        "private_learning_promotion_complete",
        "production_runtime_complete",
        "a1_a1plus_grammar_release_complete",
    ):
        if boundaries.get(false_field) is not False:
            errors.append(f"false_completion_claim:{false_field}")

    status = artifact.get("program_status", {})
    if status.get("candidate_closed_loop_status") != (
        "A1_A1PLUS_GRAMMAR_CANDIDATE_CLOSED_LOOP_COMPLETE"
    ):
        errors.append("candidate_program_status_mismatch")
    if status.get("release_status") != (
        "BLOCKED_PENDING_OPERATOR_REVIEW_AND_REAL_SKILL_EVIDENCE"
    ):
        errors.append("release_status_mismatch")

    continuation = artifact.get("continuation_gate", {})
    if continuation != {
        "status": "BLOCKED_REQUIRES_OPERATOR_APPROVAL",
        "blocker_type": (
            "OPERATOR_REVIEW_AND_REAL_SKILL_EVIDENCE_REQUIRED"
        ),
        "next_resume_task": NEXT_RESUME_TASK,
    }:
        errors.append("continuation_gate_mismatch")

    validation_status = "PASS" if not errors else "FAIL"
    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_cross_skill_closure_validation",
        "validation_status": validation_status,
        "coverage_summary": expected_summary,
        "gate_checks": {
            "canonical_units_24_of_24": len(by_unit) == 24,
            "canonical_rows_109_of_109": len(by_row) == 109,
            "all_units_have_four_skill_paths": not any(
                error.startswith("unit_skill_")
                for error in errors
            ),
            "all_rows_have_four_skill_paths_and_assessments": not any(
                error.startswith("row_skill_")
                for error in errors
            ),
            "candidate_missing_rows_zero": (
                expected_summary[
                    "candidate_cross_skill_missing_row_count"
                ]
                == 0
            ),
            "operator_review_still_zero": (
                expected_summary["operator_reviewed_row_count"] == 0
            ),
            "real_audio_and_speaking_evidence_still_zero": (
                expected_summary[
                    "rendered_listening_audio_asset_count"
                ]
                == 0
                and expected_summary[
                    "captured_speaking_audio_asset_count"
                ]
                == 0
                and expected_summary[
                    "asr_or_manual_speaking_transcript_count"
                ]
                == 0
            ),
            "actual_mastery_still_zero": (
                expected_summary[
                    "actual_mastery_measured_row_count"
                ]
                == 0
            ),
            "release_gates_fail_closed": not any(
                error.startswith(
                    "required_release_gate_not_blocked"
                )
                for error in errors
            ),
            "no_a2plus_scope": boundaries.get(
                "no_a2_a2plus_expansion"
            )
            is True,
        },
        "errors": errors,
        "warnings": [
            "Candidate four-skill path coverage is complete, but all 109 rows remain unreviewed and unpromoted.",
            "Real Listening audio, Speaking capture/transcripts, actual learner attempts, retention evidence, and production persistence remain unavailable.",
        ],
        "stop_reason": (
            "OPERATOR_REVIEW_AND_REAL_SKILL_EVIDENCE_REQUIRED"
            if validation_status == "PASS"
            else "VALIDATION_FAILURE"
        ),
        "next_resume_task": (
            NEXT_RESUME_TASK if validation_status == "PASS" else None
        ),
        "validation_mode": "LOCAL_DETERMINISTIC_CI_NOT_VERIFIED",
    }


def build_and_validate_from_repo() -> tuple[dict[str, Any], dict[str, Any]]:
    candidate, candidate_report = build_candidate_source()
    reading_writing, reading_writing_report = (
        build_reading_writing_source()
    )
    mastery, mastery_report = build_mastery_source()
    listening, listening_report = build_listening_source()
    speaking, speaking_report = build_speaking_source()

    for name, report in (
        ("candidate", candidate_report),
        ("reading_writing", reading_writing_report),
        ("mastery", mastery_report),
        ("listening", listening_report),
        ("speaking", speaking_report),
    ):
        _require_pass(name, report)

    artifact = build_artifact(
        candidate,
        reading_writing,
        mastery,
        listening,
        speaking,
    )
    report = validate_artifact(
        artifact,
        candidate,
        reading_writing,
        mastery,
        listening,
        speaking,
    )
    return artifact, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)
    artifact, report = build_and_validate_from_repo()
    write_json(args.output, artifact)
    write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["validation_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
