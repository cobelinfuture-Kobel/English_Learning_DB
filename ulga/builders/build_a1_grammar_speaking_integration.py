#!/usr/bin/env python3
"""Build and validate candidate A1/A1+ grammar Speaking integration."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_full_teachable_candidate_coverage import (
    build_and_validate_from_repo as build_candidate_source,
)
from ulga.query.a1_practice_item_grammar_gate import validate_practice_item

TASK_ID = "R7-M105G_A1GrammarSpeakingSystemIntegration"
PROGRAM_ID = "R7-M105_A1A1PlusGrammarLearningClosedLoop"
NEXT_SHORT_STEP = "R7-M105H_A1A1PlusGrammarCrossSkillClosure"
OUTPUT_PATH = REPO_ROOT / "ulga/graph/a1_grammar_speaking_integration.json"
REPORT_PATH = REPO_ROOT / "ulga/reports/a1_grammar_speaking_integration_validation.json"

SPEAKING_DIMENSIONS = (
    "controlled_oral_production",
    "guided_oral_production",
    "contextual_oral_production",
    "speaking_checkpoint",
)
FAILURE_DOMAINS = {
    "none",
    "grammar",
    "pronunciation",
    "asr",
    "fluency",
    "task_fulfillment",
    "transcript_uncertainty",
}
NON_GRAMMAR_CONFOUND_DOMAINS = FAILURE_DOMAINS - {"none", "grammar"}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _unique(values: Iterable[str]) -> list[str]:
    return sorted({value for value in values if isinstance(value, str) and value})


def _gate(grammar_id: str, text: str, role: str) -> dict[str, Any]:
    return {
        "gate_version": "a1_practice_item_grammar_gate.v1",
        "validation_targets": [
            {"grammar_id": grammar_id, "text": text, "target_role": role}
        ],
        "require_all_focus_matches": True,
        "validator_mode": "OFFLINE_STATIC_PROTOTYPE",
        "production_runtime_validator": False,
        "learner_state_write": False,
    }


def _targets(unit: dict[str, Any]) -> list[str]:
    values = [
        example.get("text", "")
        for example in unit.get("positive_examples", [])
        if isinstance(example, dict)
    ]
    values = [value for value in values if value]
    if len(values) < 2:
        raise ValueError(
            f"speaking_target_minimum_not_met:{unit.get('grammar_unit_id')}"
        )
    return values


def _speaking_activity(
    unit: dict[str, Any],
    *,
    code: str,
    dimension: str,
    model_text: str,
    prompt: str,
    communicative_function: str,
    activity_role: str,
    repair_mode: str,
) -> dict[str, Any]:
    grammar_id = unit["grammar_unit_id"]
    activity_id = f"{grammar_id}__{code}"
    return {
        "activity_id": activity_id,
        "activity_role": activity_role,
        "grammar_unit_id": grammar_id,
        "official_egp_level": "A1",
        "internal_stage": unit["internal_stage"],
        "canonical_egp_row_ids": list(unit["canonical_egp_row_ids"]),
        "skill": "speaking",
        "evidence_dimension": dimension,
        "task_type": "project_authored_speaking_prompt_candidate",
        "prompt_contract": {
            "prompt": prompt,
            "communicative_function": communicative_function,
            "expected_grammar_evidence": {
                "grammar_id": grammar_id,
                "model_text": model_text,
                "minimum_matching_target_count": 1,
            },
            "allowed_variation": {
                "lexical_substitution_allowed": True,
                "subject_substitution_allowed": True,
                "meaning_must_remain_compatible": True,
                "grammar_form_must_remain_target_compatible": True,
            },
            "repair_opportunity": {
                "available": True,
                "mode": repair_mode,
                "maximum_repairs": 1,
                "repair_counts_as_evidence": True,
                "initial_and_repaired_transcripts_required_for_real_use": True,
            },
        },
        "response_mode": "spoken_response",
        "answer_key": {
            "model_texts": [model_text],
            "exact_text_match_required": False,
            "grammar_evidence_required": True,
        },
        "content_binding": {"grammar_focus": [grammar_id]},
        "grammar_gate": _gate(
            grammar_id,
            model_text,
            f"speaking_{dimension}_model",
        ),
        "capture_contract": {
            "audio_capture_status": "NOT_IMPLEMENTED",
            "audio_ref": None,
            "audio_bytes_persisted": False,
            "asr_status": "NOT_IMPLEMENTED",
            "asr_transcript": None,
            "manual_transcript_status": "NOT_COLLECTED",
            "manual_transcript": None,
            "grammar_evidence_confidence_status": "NOT_MEASURED",
        },
        "confound_boundaries": {
            "pronunciation_measured": False,
            "fluency_measured": False,
            "task_fulfillment_measured": False,
            "asr_used": False,
            "transcript_confidence_measured": False,
            "non_grammar_confounds_do_not_lower_grammar_mastery": True,
        },
        "source_trace": {
            "content_origin": "project_authored_derived_content",
            "raw_external_source_text_copied": False,
            "restricted_source_payload_persisted": False,
        },
    }


def build_artifact(candidate: dict[str, Any]) -> dict[str, Any]:
    summary = candidate.get("coverage_summary", {})
    if summary.get("candidate_teaching_ready_unit_count") != 24:
        raise ValueError("candidate_source_not_24_units")
    if summary.get("candidate_teachable_unique_egp_row_count") != 109:
        raise ValueError("candidate_source_not_109_rows")
    if summary.get("promoted_private_learning_unit_count") != 0:
        raise ValueError("candidate_source_already_promoted")

    activities: list[dict[str, Any]] = []
    by_unit: dict[str, dict[str, Any]] = {}
    row_work: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "grammar_unit_ids": set(),
            "speaking_activity_ids": [],
            "speaking_assessment_ids": [],
            "evidence_dimensions": set(),
        }
    )

    for unit in candidate["learning_units"]:
        targets = _targets(unit)
        selected = [targets[index % len(targets)] for index in range(4)]
        unit_activities = [
            _speaking_activity(
                unit,
                code="S01",
                dimension="controlled_oral_production",
                model_text=selected[0],
                prompt="Say the model sentence or phrase using the target grammar.",
                communicative_function="controlled_reproduction",
                activity_role="practice",
                repair_mode="repeat_after_form_hint",
            ),
            _speaking_activity(
                unit,
                code="S02",
                dimension="guided_oral_production",
                model_text=selected[1],
                prompt="Answer the guided prompt using the target grammar.",
                communicative_function="guided_response",
                activity_role="practice",
                repair_mode="retry_after_grammar_cue",
            ),
            _speaking_activity(
                unit,
                code="S03",
                dimension="contextual_oral_production",
                model_text=selected[2],
                prompt="Respond to the situation with one target-grammar utterance.",
                communicative_function="contextual_response",
                activity_role="practice",
                repair_mode="self_correction_after_recast",
            ),
            _speaking_activity(
                unit,
                code="S04",
                dimension="speaking_checkpoint",
                model_text=selected[3],
                prompt="Complete the Speaking grammar checkpoint.",
                communicative_function="independent_checkpoint_response",
                activity_role="assessment",
                repair_mode="single_delayed_self_repair",
            ),
        ]
        activities.extend(unit_activities)
        grammar_id = unit["grammar_unit_id"]
        by_unit[grammar_id] = {
            "grammar_unit_id": grammar_id,
            "internal_stage": unit["internal_stage"],
            "canonical_egp_row_ids": list(unit["canonical_egp_row_ids"]),
            "speaking_activity_ids": [
                item["activity_id"] for item in unit_activities
            ],
            "speaking_assessment_ids": [unit_activities[-1]["activity_id"]],
            "speaking_candidate_status": "CANDIDATE_PATH_READY",
            "audio_capture_status": "NOT_IMPLEMENTED",
            "asr_status": "NOT_IMPLEMENTED",
            "actual_speaking_evidence_status": "NOT_COLLECTED",
        }
        for row_id in unit["canonical_egp_row_ids"]:
            row = row_work[row_id]
            row["grammar_unit_ids"].add(grammar_id)
            row["speaking_activity_ids"].extend(
                item["activity_id"] for item in unit_activities
            )
            row["speaking_assessment_ids"].append(
                unit_activities[-1]["activity_id"]
            )
            row["evidence_dimensions"].update(
                item["evidence_dimension"] for item in unit_activities
            )

    by_row = {
        row_id: {
            "egp_row_id": row_id,
            "grammar_unit_ids": sorted(value["grammar_unit_ids"]),
            "speaking_activity_ids": sorted(
                set(value["speaking_activity_ids"])
            ),
            "speaking_assessment_ids": sorted(
                set(value["speaking_assessment_ids"])
            ),
            "speaking_evidence_dimensions": sorted(
                value["evidence_dimensions"]
            ),
            "candidate_speaking_path_status": "READY",
            "actual_audio_evidence_status": "NOT_COLLECTED",
            "actual_transcript_evidence_status": "NOT_COLLECTED",
            "grammar_mastery_status": "NOT_MEASURED",
        }
        for row_id, value in sorted(row_work.items())
    }

    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_speaking_integration",
        "artifact_type": "a1_a1plus_candidate_speaking_activity_bank",
        "schema_version": "a1_grammar_speaking_integration.v1",
        "official_level": "A1",
        "internal_stages": ["A1", "A1+"],
        "source_artifact_id": candidate["artifact_id"],
        "coverage_summary": {
            "canonical_unit_count": 24,
            "canonical_unique_egp_row_count": 109,
            "speaking_activity_count": len(activities),
            "speaking_practice_count": sum(
                item["activity_role"] == "practice"
                for item in activities
            ),
            "speaking_assessment_count": sum(
                item["activity_role"] == "assessment"
                for item in activities
            ),
            "units_with_speaking_path": len(by_unit),
            "rows_with_speaking_path": len(by_row),
            "rows_with_speaking_assessment": len(by_row),
            "candidate_speaking_row_coverage_percent": 100.0,
            "captured_audio_asset_count": 0,
            "asr_transcript_count": 0,
            "manual_transcript_count": 0,
            "actual_speaking_attempt_count": 0,
            "actual_speaking_mastery_evidence_count": 0,
        },
        "speaking_activity_bank": activities,
        "by_grammar_unit_id": by_unit,
        "by_egp_row_id": by_row,
        "evidence_adapter_policy": {
            "eligible_failure_domain": "grammar",
            "ineligible_confound_domains": sorted(
                NON_GRAMMAR_CONFOUND_DOMAINS
            ),
            "self_correction_can_resolve_grammar_failure": True,
            "asr_or_pronunciation_failure_does_not_lower_grammar_mastery": True,
            "transcript_uncertainty_requires_manual_or_retry_route": True,
            "persistent_learner_state_write": False,
        },
        "claim_boundaries": {
            "candidate_speaking_contract_complete": True,
            "candidate_prompt_coverage_complete": True,
            "audio_capture_complete": False,
            "asr_integration_complete": False,
            "manual_transcript_collection_complete": False,
            "pronunciation_validation_complete": False,
            "fluency_validation_complete": False,
            "actual_speaking_attempt_collection_complete": False,
            "actual_speaking_mastery_complete": False,
            "production_runtime_integration_complete": False,
            "no_a2_a2plus_expansion": True,
            "no_persistent_learner_state_write": True,
            "no_external_nlp_dependency": True,
            "no_restricted_source_payload_copy": True,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def adapt_speaking_attempt(
    activity: dict[str, Any],
    *,
    learner_ref: str,
    attempt_sequence: int,
    outcome: str,
    failure_domain: str = "none",
    grammar_error_tags: Iterable[str] = (),
    initial_transcript: str | None = None,
    repaired_transcript: str | None = None,
    repair_used: bool = False,
    self_correction: bool = False,
    synthetic_fixture: bool = False,
) -> dict[str, Any]:
    tags = _unique(grammar_error_tags)
    grammar_eligible = failure_domain in {"none", "grammar"}
    repair_resolved = (
        repair_used
        and outcome == "PASS"
        and failure_domain == "none"
        and bool(repaired_transcript)
    )
    return {
        "event_id": (
            f"{learner_ref}:{activity['activity_id']}:{attempt_sequence}"
        ),
        "event_schema_version": "a1_grammar_speaking_attempt.v1",
        "learner_ref": learner_ref,
        "attempt_sequence": attempt_sequence,
        "activity_id": activity["activity_id"],
        "grammar_unit_id": activity["grammar_unit_id"],
        "canonical_egp_row_ids": list(
            activity["canonical_egp_row_ids"]
        ),
        "skill": "speaking",
        "evidence_dimension": activity["evidence_dimension"],
        "outcome": outcome,
        "failure_domain": failure_domain,
        "grammar_error_tags": tags,
        "initial_transcript": initial_transcript,
        "repaired_transcript": repaired_transcript,
        "repair_used": repair_used,
        "self_correction": self_correction,
        "repair_resolved": repair_resolved,
        "grammar_mastery_eligible": grammar_eligible,
        "synthetic_fixture": synthetic_fixture,
        "persistent_learner_state_write": False,
        "production_runtime_event": False,
    }


def validate_speaking_attempt(
    event: dict[str, Any],
    activities: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    activity_id = event.get("activity_id")
    activity = activities.get(activity_id)
    if not activity:
        return [f"unknown_speaking_activity:{activity_id}"]

    for field, expected in (
        ("grammar_unit_id", activity["grammar_unit_id"]),
        (
            "canonical_egp_row_ids",
            activity["canonical_egp_row_ids"],
        ),
        ("skill", "speaking"),
        ("evidence_dimension", activity["evidence_dimension"]),
    ):
        if event.get(field) != expected:
            errors.append(
                f"speaking_attempt_identity_mismatch:{activity_id}:{field}"
            )

    if event.get("outcome") not in {"PASS", "FAIL", "UNRESOLVED"}:
        errors.append(f"invalid_speaking_outcome:{activity_id}")

    domain = event.get("failure_domain")
    if domain not in FAILURE_DOMAINS:
        errors.append(f"invalid_failure_domain:{activity_id}:{domain}")

    tags = event.get("grammar_error_tags", [])
    if not isinstance(tags, list) or len(tags) != len(set(tags)):
        errors.append(f"invalid_grammar_error_tags:{activity_id}")
        tags = []

    if event.get("outcome") == "PASS" and domain != "none":
        errors.append(f"pass_with_failure_domain:{activity_id}")
    if domain == "grammar" and event.get("outcome") == "FAIL" and not tags:
        errors.append(f"grammar_failure_missing_tags:{activity_id}")
    if domain != "grammar" and tags:
        errors.append(f"confound_domain_has_grammar_tags:{activity_id}")

    expected_eligible = domain in {"none", "grammar"}
    if event.get("grammar_mastery_eligible") is not expected_eligible:
        errors.append(f"grammar_eligibility_mismatch:{activity_id}")

    repair_used = event.get("repair_used")
    repaired_transcript = event.get("repaired_transcript")
    if repair_used is True and not repaired_transcript:
        errors.append(f"repair_used_without_transcript:{activity_id}")
    if repair_used is False and repaired_transcript:
        errors.append(f"repair_transcript_without_repair:{activity_id}")
    if event.get("self_correction") is True and repair_used is not True:
        errors.append(f"self_correction_without_repair:{activity_id}")
    expected_repair_resolved = (
        repair_used is True
        and event.get("outcome") == "PASS"
        and domain == "none"
        and bool(repaired_transcript)
    )
    if event.get("repair_resolved") is not expected_repair_resolved:
        errors.append(f"repair_resolution_mismatch:{activity_id}")

    if event.get("persistent_learner_state_write") is not False:
        errors.append(f"unsafe_persistent_write:{activity_id}")
    if event.get("production_runtime_event") is not False:
        errors.append(f"unsafe_runtime_event:{activity_id}")

    return errors


def validate_artifact(
    artifact: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    activities = artifact.get("speaking_activity_bank", [])
    activity_map = {
        item.get("activity_id"): item
        for item in activities
        if item.get("activity_id")
    }
    source_units = {
        unit["grammar_unit_id"]: unit
        for unit in candidate.get("learning_units", [])
    }

    if len(activities) != 96 or len(activity_map) != 96:
        errors.append("speaking_activity_count_or_identity_mismatch")

    for item in activities:
        activity_id = item.get("activity_id")
        grammar_id = item.get("grammar_unit_id")
        unit = source_units.get(grammar_id)
        if not unit:
            errors.append(f"unknown_grammar_unit:{activity_id}")
            continue
        if (
            item.get("canonical_egp_row_ids")
            != unit.get("canonical_egp_row_ids")
        ):
            errors.append(
                f"speaking_row_binding_mismatch:{activity_id}"
            )

        prompt = item.get("prompt_contract", {})
        expected = prompt.get("expected_grammar_evidence", {})
        if expected.get("grammar_id") != grammar_id:
            errors.append(
                f"speaking_prompt_grammar_mismatch:{activity_id}"
            )
        if not expected.get("model_text"):
            errors.append(f"speaking_model_text_missing:{activity_id}")
        repair = prompt.get("repair_opportunity", {})
        if (
            repair.get("available") is not True
            or repair.get("maximum_repairs") != 1
        ):
            errors.append(
                f"speaking_repair_contract_invalid:{activity_id}"
            )

        capture = item.get("capture_contract", {})
        expected_capture = {
            "audio_capture_status": "NOT_IMPLEMENTED",
            "audio_ref": None,
            "audio_bytes_persisted": False,
            "asr_status": "NOT_IMPLEMENTED",
            "asr_transcript": None,
            "manual_transcript_status": "NOT_COLLECTED",
            "manual_transcript": None,
            "grammar_evidence_confidence_status": "NOT_MEASURED",
        }
        if capture != expected_capture:
            errors.append(f"false_capture_or_transcript_claim:{activity_id}")

        gate_item = {
            "item_id": activity_id,
            "content_binding": item.get("content_binding"),
            "grammar_gate": item.get("grammar_gate"),
        }
        gate = validate_practice_item(gate_item)
        if gate.get("gate_status") != "PASS":
            errors.append(f"speaking_grammar_gate_fail:{activity_id}")

        source = item.get("source_trace", {})
        if (
            source.get("raw_external_source_text_copied") is not False
            or source.get(
                "restricted_source_payload_persisted"
            ) is not False
        ):
            errors.append(f"unsafe_speaking_source:{activity_id}")

    by_unit = artifact.get("by_grammar_unit_id", {})
    if len(by_unit) != 24 or set(by_unit) != set(source_units):
        errors.append("speaking_unit_index_mismatch")
    for grammar_id, unit in by_unit.items():
        if len(unit.get("speaking_activity_ids", [])) != 4:
            errors.append(
                f"unit_speaking_path_incomplete:{grammar_id}"
            )
        if len(unit.get("speaking_assessment_ids", [])) != 1:
            errors.append(
                f"unit_speaking_assessment_missing:{grammar_id}"
            )
        if unit.get("audio_capture_status") != "NOT_IMPLEMENTED":
            errors.append(f"unit_false_capture_status:{grammar_id}")
        if unit.get("asr_status") != "NOT_IMPLEMENTED":
            errors.append(f"unit_false_asr_status:{grammar_id}")

    source_rows = set(candidate.get("by_egp_row_id", {}))
    by_row = artifact.get("by_egp_row_id", {})
    if len(by_row) != 109 or set(by_row) != source_rows:
        errors.append("speaking_row_index_not_109_of_109")
    for row_id, row in by_row.items():
        if (
            not row.get("speaking_activity_ids")
            or not row.get("speaking_assessment_ids")
        ):
            errors.append(f"row_speaking_path_missing:{row_id}")
        if set(
            row.get("speaking_evidence_dimensions", [])
        ) != set(SPEAKING_DIMENSIONS):
            errors.append(f"row_speaking_dimension_gap:{row_id}")
        if row.get("grammar_mastery_status") != "NOT_MEASURED":
            errors.append(f"false_speaking_mastery_claim:{row_id}")

    expected_summary = {
        "canonical_unit_count": 24,
        "canonical_unique_egp_row_count": 109,
        "speaking_activity_count": 96,
        "speaking_practice_count": 72,
        "speaking_assessment_count": 24,
        "units_with_speaking_path": 24,
        "rows_with_speaking_path": 109,
        "rows_with_speaking_assessment": 109,
        "candidate_speaking_row_coverage_percent": 100.0,
        "captured_audio_asset_count": 0,
        "asr_transcript_count": 0,
        "manual_transcript_count": 0,
        "actual_speaking_attempt_count": 0,
        "actual_speaking_mastery_evidence_count": 0,
    }
    if artifact.get("coverage_summary") != expected_summary:
        errors.append("speaking_coverage_summary_mismatch")

    policy = artifact.get("evidence_adapter_policy", {})
    if (
        policy.get(
            "asr_or_pronunciation_failure_does_not_lower_grammar_mastery"
        )
        is not True
    ):
        errors.append("speaking_confound_policy_missing")
    if policy.get("self_correction_can_resolve_grammar_failure") is not True:
        errors.append("speaking_repair_policy_missing")

    boundaries = artifact.get("claim_boundaries", {})
    for false_field in (
        "audio_capture_complete",
        "asr_integration_complete",
        "manual_transcript_collection_complete",
        "pronunciation_validation_complete",
        "fluency_validation_complete",
        "actual_speaking_attempt_collection_complete",
        "actual_speaking_mastery_complete",
        "production_runtime_integration_complete",
    ):
        if boundaries.get(false_field) is not False:
            errors.append(f"false_completion_claim:{false_field}")
    for true_field in (
        "candidate_speaking_contract_complete",
        "candidate_prompt_coverage_complete",
        "no_a2_a2plus_expansion",
        "no_persistent_learner_state_write",
        "no_external_nlp_dependency",
        "no_restricted_source_payload_copy",
    ):
        if boundaries.get(true_field) is not True:
            errors.append(f"scope_boundary_missing:{true_field}")

    status = "PASS" if not errors else "FAIL"
    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_speaking_integration_validation",
        "validation_status": status,
        "coverage_summary": expected_summary,
        "gate_checks": {
            "speaking_units_24_of_24": len(by_unit) == 24,
            "speaking_rows_109_of_109": len(by_row) == 109,
            "speaking_activities_96": len(activity_map) == 96,
            "all_model_targets_grammar_gated": not any(
                error.startswith("speaking_grammar_gate_fail")
                for error in errors
            ),
            "all_rows_have_speaking_assessment": not any(
                error.startswith("row_speaking_path_missing")
                for error in errors
            ),
            "capture_asr_transcripts_still_zero": (
                expected_summary["captured_audio_asset_count"] == 0
                and expected_summary["asr_transcript_count"] == 0
                and expected_summary["manual_transcript_count"] == 0
            ),
            "confounds_separated_from_grammar": policy.get(
                "asr_or_pronunciation_failure_does_not_lower_grammar_mastery"
            )
            is True,
            "repair_contract_available": policy.get(
                "self_correction_can_resolve_grammar_failure"
            )
            is True,
            "actual_speaking_evidence_still_zero": (
                expected_summary["actual_speaking_attempt_count"] == 0
            ),
            "no_a2plus_scope": boundaries.get(
                "no_a2_a2plus_expansion"
            )
            is True,
        },
        "errors": errors,
        "warnings": [
            "Speaking coverage is prompt/model candidate coverage; no audio, ASR, or manual transcript evidence has been collected.",
            "Pronunciation, fluency, task fulfillment, transcript confidence, and actual learner mastery remain unmeasured.",
        ],
        "stop_reason": "NONE" if status == "PASS" else "VALIDATION_FAILURE",
        "next_short_step": NEXT_SHORT_STEP if status == "PASS" else None,
        "validation_mode": "LOCAL_DETERMINISTIC_CI_NOT_VERIFIED",
    }


def build_and_validate_from_repo() -> tuple[dict[str, Any], dict[str, Any]]:
    candidate, candidate_report = build_candidate_source()
    if candidate_report.get("validation_status") != "PASS":
        raise RuntimeError("candidate_source_validation_failed")
    artifact = build_artifact(candidate)
    report = validate_artifact(artifact, candidate)
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
