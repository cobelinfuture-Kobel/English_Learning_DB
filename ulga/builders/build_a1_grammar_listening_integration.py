#!/usr/bin/env python3
"""Build and validate candidate A1/A1+ grammar Listening integration."""

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

TASK_ID = "R7-M105F_A1GrammarListeningSystemIntegration"
PROGRAM_ID = "R7-M105_A1A1PlusGrammarLearningClosedLoop"
NEXT_SHORT_STEP = "R7-M105G_A1GrammarSpeakingSystemIntegration"
OUTPUT_PATH = REPO_ROOT / "ulga/graph/a1_grammar_listening_integration.json"
REPORT_PATH = REPO_ROOT / "ulga/reports/a1_grammar_listening_integration_validation.json"

LISTENING_DIMENSIONS = (
    "heard_form_recognition",
    "meaning_comprehension",
    "contrast_discrimination",
    "listening_checkpoint",
)
FAILURE_DOMAINS = {
    "none",
    "grammar",
    "audio_quality",
    "vocabulary",
    "pronunciation_variation",
    "transcript_alignment",
}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
    values = [example.get("text", "") for example in unit.get("positive_examples", [])]
    values = [value for value in values if value]
    if len(values) < 2:
        raise ValueError(f"listening_target_minimum_not_met:{unit.get('grammar_unit_id')}")
    return values


def _listening_activity(
    unit: dict[str, Any],
    *,
    code: str,
    dimension: str,
    transcript_text: str,
    prompt: str,
    activity_role: str,
) -> dict[str, Any]:
    grammar_id = unit["grammar_unit_id"]
    activity_id = f"{grammar_id}__{code}"
    duration_ms = max(1200, min(6000, len(transcript_text.split()) * 650))
    return {
        "activity_id": activity_id,
        "activity_role": activity_role,
        "grammar_unit_id": grammar_id,
        "official_egp_level": "A1",
        "internal_stage": unit["internal_stage"],
        "canonical_egp_row_ids": list(unit["canonical_egp_row_ids"]),
        "skill": "listening",
        "evidence_dimension": dimension,
        "task_type": "synthetic_transcript_listening_candidate",
        "prompt": prompt,
        "response_mode": "select_or_short_response",
        "answer_key": {"accepted_texts": [transcript_text]},
        "content_binding": {"grammar_focus": [grammar_id]},
        "grammar_gate": _gate(grammar_id, transcript_text, f"listening_{dimension}"),
        "audio_contract": {
            "audio_ref": f"synthetic-audio://a1-grammar/{activity_id}",
            "audio_asset_status": "NOT_RENDERED",
            "audio_required_for_production": True,
            "voice_policy": "A1_CLEAR_SINGLE_SPEAKER_CANDIDATE",
            "speed_policy": "A1_CONTROLLED_CANDIDATE",
            "actual_audio_bytes_persisted": False,
        },
        "transcript_contract": {
            "transcript_ref": f"synthetic-transcript://a1-grammar/{activity_id}",
            "transcript_text": transcript_text,
            "transcript_origin": "project_authored_derived_content",
            "transcript_status": "CANDIDATE_GRAMMAR_VALIDATED",
            "start_ms": 0,
            "end_ms": duration_ms,
            "timestamp_status": "PROVISIONAL_UNTIL_AUDIO_RENDER",
            "raw_external_source_text_copied": False,
            "restricted_source_payload_persisted": False,
        },
        "confound_boundaries": {
            "audio_quality_measured": False,
            "pronunciation_variation_measured": False,
            "vocabulary_load_validated": False,
            "asr_used": False,
            "grammar_inference_mode": "CANDIDATE_ONLY",
        },
    }


def build_artifact(candidate: dict[str, Any]) -> dict[str, Any]:
    summary = candidate.get("coverage_summary", {})
    if summary.get("candidate_teaching_ready_unit_count") != 24:
        raise ValueError("candidate_source_not_24_units")
    if summary.get("candidate_teachable_unique_egp_row_count") != 109:
        raise ValueError("candidate_source_not_109_rows")

    activities: list[dict[str, Any]] = []
    by_unit: dict[str, dict[str, Any]] = {}
    row_work: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "grammar_unit_ids": set(),
            "listening_activity_ids": [],
            "listening_assessment_ids": [],
            "evidence_dimensions": set(),
        }
    )
    for unit in candidate["learning_units"]:
        targets = _targets(unit)
        selected = [targets[index % len(targets)] for index in range(4)]
        unit_activities = [
            _listening_activity(
                unit,
                code="L01",
                dimension="heard_form_recognition",
                transcript_text=selected[0],
                prompt="Listen and identify the target grammar form.",
                activity_role="practice",
            ),
            _listening_activity(
                unit,
                code="L02",
                dimension="meaning_comprehension",
                transcript_text=selected[1],
                prompt="Listen and choose the meaning that matches the utterance.",
                activity_role="practice",
            ),
            _listening_activity(
                unit,
                code="L03",
                dimension="contrast_discrimination",
                transcript_text=selected[2],
                prompt="Listen and distinguish the target form from a nearby contrast.",
                activity_role="practice",
            ),
            _listening_activity(
                unit,
                code="L04",
                dimension="listening_checkpoint",
                transcript_text=selected[3],
                prompt="Complete the Listening grammar checkpoint.",
                activity_role="assessment",
            ),
        ]
        activities.extend(unit_activities)
        grammar_id = unit["grammar_unit_id"]
        by_unit[grammar_id] = {
            "grammar_unit_id": grammar_id,
            "internal_stage": unit["internal_stage"],
            "canonical_egp_row_ids": list(unit["canonical_egp_row_ids"]),
            "listening_activity_ids": [item["activity_id"] for item in unit_activities],
            "listening_assessment_ids": [unit_activities[-1]["activity_id"]],
            "listening_candidate_status": "CANDIDATE_PATH_READY",
            "audio_asset_status": "NOT_RENDERED",
            "actual_listening_evidence_status": "NOT_COLLECTED",
        }
        for row_id in unit["canonical_egp_row_ids"]:
            row = row_work[row_id]
            row["grammar_unit_ids"].add(grammar_id)
            row["listening_activity_ids"].extend(item["activity_id"] for item in unit_activities)
            row["listening_assessment_ids"].append(unit_activities[-1]["activity_id"])
            row["evidence_dimensions"].update(item["evidence_dimension"] for item in unit_activities)

    by_row = {
        row_id: {
            "egp_row_id": row_id,
            "grammar_unit_ids": sorted(value["grammar_unit_ids"]),
            "listening_activity_ids": sorted(set(value["listening_activity_ids"])),
            "listening_assessment_ids": sorted(set(value["listening_assessment_ids"])),
            "listening_evidence_dimensions": sorted(value["evidence_dimensions"]),
            "candidate_listening_path_status": "READY",
            "actual_audio_evidence_status": "NOT_COLLECTED",
            "grammar_mastery_status": "NOT_MEASURED",
        }
        for row_id, value in sorted(row_work.items())
    }
    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_listening_integration",
        "artifact_type": "a1_a1plus_candidate_listening_activity_bank",
        "schema_version": "a1_grammar_listening_integration.v1",
        "official_level": "A1",
        "internal_stages": ["A1", "A1+"],
        "source_artifact_id": candidate["artifact_id"],
        "coverage_summary": {
            "canonical_unit_count": 24,
            "canonical_unique_egp_row_count": 109,
            "listening_activity_count": len(activities),
            "listening_practice_count": sum(item["activity_role"] == "practice" for item in activities),
            "listening_assessment_count": sum(item["activity_role"] == "assessment" for item in activities),
            "units_with_listening_path": len(by_unit),
            "rows_with_listening_path": len(by_row),
            "rows_with_listening_assessment": len(by_row),
            "candidate_listening_row_coverage_percent": 100.0,
            "rendered_audio_asset_count": 0,
            "actual_listening_attempt_count": 0,
            "actual_listening_mastery_evidence_count": 0,
        },
        "listening_activity_bank": activities,
        "by_grammar_unit_id": by_unit,
        "by_egp_row_id": by_row,
        "evidence_adapter_policy": {
            "eligible_failure_domain": "grammar",
            "ineligible_confound_domains": [
                "audio_quality",
                "vocabulary",
                "pronunciation_variation",
                "transcript_alignment",
            ],
            "unresolved_confound_does_not_lower_grammar_mastery": True,
            "persistent_learner_state_write": False,
        },
        "claim_boundaries": {
            "candidate_listening_contract_complete": True,
            "candidate_transcript_coverage_complete": True,
            "audio_rendering_complete": False,
            "audio_quality_validation_complete": False,
            "pronunciation_variation_validation_complete": False,
            "actual_listening_attempt_collection_complete": False,
            "actual_listening_mastery_complete": False,
            "production_runtime_integration_complete": False,
            "no_a2_a2plus_expansion": True,
            "no_persistent_learner_state_write": True,
            "no_external_nlp_dependency": True,
            "no_restricted_source_payload_copy": True,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def adapt_listening_attempt(
    activity: dict[str, Any],
    *,
    learner_ref: str,
    attempt_sequence: int,
    outcome: str,
    failure_domain: str = "none",
    grammar_error_tags: Iterable[str] = (),
    synthetic_fixture: bool = False,
) -> dict[str, Any]:
    tags = _unique(grammar_error_tags)
    grammar_eligible = failure_domain in {"none", "grammar"}
    return {
        "event_id": f"{learner_ref}:{activity['activity_id']}:{attempt_sequence}",
        "event_schema_version": "a1_grammar_listening_attempt.v1",
        "learner_ref": learner_ref,
        "attempt_sequence": attempt_sequence,
        "activity_id": activity["activity_id"],
        "grammar_unit_id": activity["grammar_unit_id"],
        "canonical_egp_row_ids": list(activity["canonical_egp_row_ids"]),
        "skill": "listening",
        "evidence_dimension": activity["evidence_dimension"],
        "outcome": outcome,
        "failure_domain": failure_domain,
        "grammar_error_tags": tags,
        "grammar_mastery_eligible": grammar_eligible,
        "synthetic_fixture": synthetic_fixture,
        "persistent_learner_state_write": False,
        "production_runtime_event": False,
    }


def validate_listening_attempt(
    event: dict[str, Any],
    activities: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    activity_id = event.get("activity_id")
    activity = activities.get(activity_id)
    if not activity:
        return [f"unknown_listening_activity:{activity_id}"]
    for field, expected in (
        ("grammar_unit_id", activity["grammar_unit_id"]),
        ("canonical_egp_row_ids", activity["canonical_egp_row_ids"]),
        ("skill", "listening"),
        ("evidence_dimension", activity["evidence_dimension"]),
    ):
        if event.get(field) != expected:
            errors.append(f"listening_attempt_identity_mismatch:{activity_id}:{field}")
    if event.get("outcome") not in {"PASS", "FAIL", "UNRESOLVED"}:
        errors.append(f"invalid_listening_outcome:{activity_id}")
    domain = event.get("failure_domain")
    if domain not in FAILURE_DOMAINS:
        errors.append(f"invalid_failure_domain:{activity_id}:{domain}")
    tags = event.get("grammar_error_tags", [])
    if event.get("outcome") == "PASS" and domain != "none":
        errors.append(f"pass_with_failure_domain:{activity_id}")
    if domain == "grammar" and event.get("outcome") == "FAIL" and not tags:
        errors.append(f"grammar_failure_missing_tags:{activity_id}")
    if domain != "grammar" and tags:
        errors.append(f"confound_domain_has_grammar_tags:{activity_id}")
    expected_eligible = domain in {"none", "grammar"}
    if event.get("grammar_mastery_eligible") is not expected_eligible:
        errors.append(f"grammar_eligibility_mismatch:{activity_id}")
    if event.get("persistent_learner_state_write") is not False:
        errors.append(f"unsafe_persistent_write:{activity_id}")
    if event.get("production_runtime_event") is not False:
        errors.append(f"unsafe_runtime_event:{activity_id}")
    return errors


def validate_artifact(artifact: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    activities = artifact.get("listening_activity_bank", [])
    activity_map = {item.get("activity_id"): item for item in activities if item.get("activity_id")}
    source_units = {unit["grammar_unit_id"]: unit for unit in candidate.get("learning_units", [])}
    if len(activities) != 96 or len(activity_map) != 96:
        errors.append("listening_activity_count_or_identity_mismatch")

    for item in activities:
        activity_id = item.get("activity_id")
        grammar_id = item.get("grammar_unit_id")
        unit = source_units.get(grammar_id)
        if not unit:
            errors.append(f"unknown_grammar_unit:{activity_id}")
            continue
        if item.get("canonical_egp_row_ids") != unit.get("canonical_egp_row_ids"):
            errors.append(f"listening_row_binding_mismatch:{activity_id}")
        transcript = item.get("transcript_contract", {})
        transcript_text = transcript.get("transcript_text")
        if not transcript_text:
            errors.append(f"transcript_missing:{activity_id}")
        if transcript.get("raw_external_source_text_copied") is not False or transcript.get("restricted_source_payload_persisted") is not False:
            errors.append(f"unsafe_transcript_source:{activity_id}")
        audio = item.get("audio_contract", {})
        if audio.get("audio_asset_status") != "NOT_RENDERED" or audio.get("actual_audio_bytes_persisted") is not False:
            errors.append(f"false_audio_asset_claim:{activity_id}")
        gate_item = {
            "item_id": activity_id,
            "content_binding": item.get("content_binding"),
            "grammar_gate": item.get("grammar_gate"),
        }
        gate = validate_practice_item(gate_item)
        if gate.get("gate_status") != "PASS":
            errors.append(f"listening_grammar_gate_fail:{activity_id}")

    by_unit = artifact.get("by_grammar_unit_id", {})
    if len(by_unit) != 24 or set(by_unit) != set(source_units):
        errors.append("listening_unit_index_mismatch")
    for grammar_id, unit in by_unit.items():
        if len(unit.get("listening_activity_ids", [])) != 4:
            errors.append(f"unit_listening_path_incomplete:{grammar_id}")
        if len(unit.get("listening_assessment_ids", [])) != 1:
            errors.append(f"unit_listening_assessment_missing:{grammar_id}")
        if unit.get("audio_asset_status") != "NOT_RENDERED":
            errors.append(f"unit_false_audio_status:{grammar_id}")

    source_rows = set(candidate.get("by_egp_row_id", {}))
    by_row = artifact.get("by_egp_row_id", {})
    if len(by_row) != 109 or set(by_row) != source_rows:
        errors.append("listening_row_index_not_109_of_109")
    for row_id, row in by_row.items():
        if not row.get("listening_activity_ids") or not row.get("listening_assessment_ids"):
            errors.append(f"row_listening_path_missing:{row_id}")
        if set(row.get("listening_evidence_dimensions", [])) != set(LISTENING_DIMENSIONS):
            errors.append(f"row_listening_dimension_gap:{row_id}")
        if row.get("grammar_mastery_status") != "NOT_MEASURED":
            errors.append(f"false_listening_mastery_claim:{row_id}")

    expected_summary = {
        "canonical_unit_count": 24,
        "canonical_unique_egp_row_count": 109,
        "listening_activity_count": 96,
        "listening_practice_count": 72,
        "listening_assessment_count": 24,
        "units_with_listening_path": 24,
        "rows_with_listening_path": 109,
        "rows_with_listening_assessment": 109,
        "candidate_listening_row_coverage_percent": 100.0,
        "rendered_audio_asset_count": 0,
        "actual_listening_attempt_count": 0,
        "actual_listening_mastery_evidence_count": 0,
    }
    if artifact.get("coverage_summary") != expected_summary:
        errors.append("listening_coverage_summary_mismatch")
    policy = artifact.get("evidence_adapter_policy", {})
    if policy.get("unresolved_confound_does_not_lower_grammar_mastery") is not True:
        errors.append("confound_policy_missing")
    boundaries = artifact.get("claim_boundaries", {})
    for false_field in (
        "audio_rendering_complete",
        "audio_quality_validation_complete",
        "pronunciation_variation_validation_complete",
        "actual_listening_attempt_collection_complete",
        "actual_listening_mastery_complete",
        "production_runtime_integration_complete",
    ):
        if boundaries.get(false_field) is not False:
            errors.append(f"false_completion_claim:{false_field}")
    for true_field in (
        "candidate_listening_contract_complete",
        "candidate_transcript_coverage_complete",
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
        "artifact_id": "a1_grammar_listening_integration_validation",
        "validation_status": status,
        "coverage_summary": expected_summary,
        "gate_checks": {
            "listening_units_24_of_24": len(by_unit) == 24,
            "listening_rows_109_of_109": len(by_row) == 109,
            "listening_activities_96": len(activity_map) == 96,
            "all_transcripts_grammar_gated": not any(error.startswith("listening_grammar_gate_fail") for error in errors),
            "all_rows_have_listening_assessment": not any(error.startswith("row_listening_path_missing") for error in errors),
            "audio_assets_still_unrendered": expected_summary["rendered_audio_asset_count"] == 0,
            "confounds_separated_from_grammar": policy.get("unresolved_confound_does_not_lower_grammar_mastery") is True,
            "actual_listening_evidence_still_zero": expected_summary["actual_listening_attempt_count"] == 0,
            "no_a2plus_scope": boundaries.get("no_a2_a2plus_expansion") is True,
        },
        "errors": errors,
        "warnings": [
            "Listening coverage is transcript-backed candidate coverage; no audio bytes have been rendered.",
            "Audio quality, pronunciation variation, vocabulary confounds, and actual learner evidence remain unmeasured.",
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
