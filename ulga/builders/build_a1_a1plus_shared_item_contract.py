#!/usr/bin/env python3
"""Normalize 384 A1/A1+ Reading, Writing, Listening, and Speaking items.

The artifact certifies a common item/answer/scoring/media envelope. It does not
claim rendered Listening audio, captured Speaking audio, learner transcripts,
mastery, retention, persistent learner state, or production runtime readiness.
"""
from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_a1plus_cross_skill_learning_units import (
    NEXT_SHORT_STEP as M02_NEXT_SHORT_STEP,
    build_artifact as build_learning_units,
)
from ulga.builders.build_a1_grammar_listening_integration import (
    build_and_validate_from_repo as build_listening_source,
)
from ulga.builders.build_a1_grammar_speaking_integration import (
    build_and_validate_from_repo as build_speaking_source,
)
from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import (
    build_and_validate_from_repo as build_text_mode_source,
)

TASK_ID = "E4S-A1V1-M03_SharedItemAnswerScoringMediaContract"
EPIC_ID = "E4S-A1V1_A1A1PlusCompleteFourSkillLearningSystem"
ARTIFACT_ID = "e4s_a1v1_shared_item_contract"
SCHEMA_VERSION = "e4s.a1v1.shared_item.v1"
SCHEMA_PATH = REPO_ROOT / "ulga/schemas/items/a1_a1plus_shared_item.schema.json"
OUTPUT_PATH = REPO_ROOT / "ulga/graph/e4s_a1v1_shared_item_contract.json"
NEXT_SHORT_STEP = "E4S-A1V1-M04_ReadingV1CompletionAndIntegration"
SKILLS = ("reading", "writing", "listening", "speaking")
SOURCE_COUNTS = {skill: 96 for skill in SKILLS}


def _require_pass(name: str, report: Mapping[str, Any]) -> None:
    if report.get("validation_status") != "PASS":
        raise RuntimeError(f"m03_source_validation_failed:{name}")


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if isinstance(value, str) and value))


def _learning_unit_index(artifact: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    units = artifact.get("learning_units", [])
    index = {str(unit.get("grammar_unit_id")): unit for unit in units}
    if len(index) != 24:
        raise ValueError("m03_learning_unit_source_not_24")
    return index


def _coverage_binding(unit: Mapping[str, Any]) -> tuple[list[str], str]:
    rows = list(unit.get("canonical_egp_row_ids", []))
    mode = str(unit.get("coverage_binding", {}).get("mode") or "")
    if mode not in {"DIRECT_CANONICAL_ROWS", "ROWLESS_STRUCTURAL_PACKAGE_GATE"}:
        raise ValueError(f"m03_invalid_coverage_mode:{unit.get('grammar_unit_id')}")
    if mode == "DIRECT_CANONICAL_ROWS" and not rows:
        raise ValueError(f"m03_direct_unit_missing_rows:{unit.get('grammar_unit_id')}")
    if mode == "ROWLESS_STRUCTURAL_PACKAGE_GATE" and rows:
        raise ValueError(f"m03_rowless_unit_has_rows:{unit.get('grammar_unit_id')}")
    return rows, mode


def _base_item(
    *,
    source_item_id: str,
    source_kind: str,
    source_artifact_id: str,
    source_builder_path: str,
    unit: Mapping[str, Any],
    skill: str,
    item_role: str,
    evidence_dimension: str,
    task_type: str,
    prompt_contract: Mapping[str, Any],
    response_contract: Mapping[str, Any],
    answer_contract: Mapping[str, Any],
    scoring_contract: Mapping[str, Any],
    media_contract: Mapping[str, Any],
    source_trace_extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if skill not in SKILLS:
        raise ValueError(f"m03_invalid_skill:{skill}")
    if item_role not in {"practice", "assessment"}:
        raise ValueError(f"m03_invalid_item_role:{source_item_id}:{item_role}")
    rows, coverage_mode = _coverage_binding(unit)
    trace = {
        "source_kind": source_kind,
        "source_artifact_id": source_artifact_id,
        "source_builder_path": source_builder_path,
        "raw_external_source_text_copied": False,
    }
    if source_trace_extra:
        trace.update(deepcopy(dict(source_trace_extra)))
    return {
        "shared_item_id": f"E4S_A1V1_ITEM:{source_item_id}",
        "source_item_id": source_item_id,
        "schema_version": SCHEMA_VERSION,
        "learning_unit_id": unit["learning_unit_id"],
        "grammar_unit_id": unit["grammar_unit_id"],
        "official_cefr_level": "A1",
        "internal_stage": unit["internal_stage"],
        "skill": skill,
        "item_role": item_role,
        "evidence_dimension": evidence_dimension,
        "task_type": task_type,
        "prompt_contract": deepcopy(dict(prompt_contract)),
        "response_contract": deepcopy(dict(response_contract)),
        "answer_contract": deepcopy(dict(answer_contract)),
        "scoring_contract": deepcopy(dict(scoring_contract)),
        "media_contract": deepcopy(dict(media_contract)),
        "content_binding": {
            "grammar_focus": [unit["grammar_unit_id"]],
            "canonical_egp_row_ids": rows,
            "coverage_mode": coverage_mode,
        },
        "source_trace": trace,
        "readiness": {
            "shared_item_contract_complete": True,
            "answer_contract_complete": True,
            "scoring_contract_complete": True,
            "media_contract_complete": True,
            "real_skill_delivery_complete": False,
            "actual_learner_evidence_complete": False,
        },
        "claim_boundaries": {
            "contract_completion_is_real_skill_completion": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "persistent_learner_state_write": False,
            "production_runtime_event": False,
            "a2_a2plus_in_scope": False,
        },
    }


def _text_answer_mode(item: Mapping[str, Any]) -> str:
    response_mode = str(item.get("response_mode") or "").lower()
    task_type = str(item.get("task_type") or "").lower()
    if response_mode == "select_one" or item.get("options"):
        return "DETERMINISTIC_OPTION"
    if response_mode in {"ordered_tokens", "ordered_morphemes"} or any(
        key in item
        for key in (
            "correct_token_sequence",
            "correct_morphology_parts",
        )
    ):
        return "DETERMINISTIC_SEQUENCE"
    if response_mode in {"short_text", "text", "typed_text"}:
        return "DETERMINISTIC_NORMALIZED_TEXT"
    if "structured" in task_type or item.get("answer_key", {}).get("accepted_texts"):
        return "DETERMINISTIC_NORMALIZED_TEXT"
    return "FEATURE_RUBRIC_CANDIDATE"


def _text_item(
    source: Mapping[str, Any],
    unit: Mapping[str, Any],
    source_artifact_id: str,
) -> dict[str, Any]:
    source_id = str(source["item_id"])
    mode = _text_answer_mode(source)
    deterministic = mode != "FEATURE_RUBRIC_CANDIDATE"
    answer_payload = {
        "answer_mode": mode,
        "answer_status": "CANDIDATE_CONTRACT_AVAILABLE",
        "exact_text_match_required": bool(
            mode in {"DETERMINISTIC_OPTION", "DETERMINISTIC_SEQUENCE"}
        ),
        "answer_key": deepcopy(source.get("answer_key", {})),
    }
    for key in (
        "options",
        "correct_token_sequence",
        "correct_morphology_parts",
        "gap_spec",
        "accepted_variation_policy",
        "option_rationales",
        "distractor_error_tags",
    ):
        if key in source:
            answer_payload[key] = deepcopy(source[key])
    response_payload = {
        "response_mode": str(source.get("response_mode") or "text_response"),
        "learner_input_required": True,
    }
    for key in ("options", "token_sequence", "morphology_parts"):
        if key in source:
            response_payload[key] = deepcopy(source[key])
    prompt_payload = {
        "prompt_text": str(source.get("prompt") or "Complete the item."),
        "prompt_status": "PROJECT_AUTHORED_CANDIDATE",
    }
    if "context" in source:
        prompt_payload["context"] = deepcopy(source["context"])
    return _base_item(
        source_item_id=source_id,
        source_kind="READING_WRITING_TEXT_MODE",
        source_artifact_id=source_artifact_id,
        source_builder_path="ulga/builders/build_a1_grammar_text_mode_private_pilot_package.py",
        unit=unit,
        skill=str(source["skill"]),
        item_role=str(source["item_role"]),
        evidence_dimension=str(source.get("evidence_dimension") or "unspecified"),
        task_type=str(source.get("task_type") or "text_mode_candidate"),
        prompt_contract=prompt_payload,
        response_contract=response_payload,
        answer_contract=answer_payload,
        scoring_contract={
            "scoring_mode": mode,
            "deterministic_candidate": deterministic,
            "real_skill_scoring_ready": deterministic,
            "human_review_fallback": not deterministic,
            "required_evidence": ["learner_text_response"],
        },
        media_contract={
            "text_status": "AVAILABLE",
            "audio_required": False,
            "audio_status": "NOT_REQUIRED",
            "transcript_required": False,
            "transcript_status": "NOT_REQUIRED",
            "image_required": False,
            "image_status": "NOT_REQUIRED",
            "learner_capture_required": False,
            "learner_capture_status": "NOT_REQUIRED",
        },
        source_trace_extra={
            "source_unit_id": source.get("source_trace", {}).get("source_unit_id"),
            "grammar_gate_version": source.get("grammar_gate", {}).get("gate_version"),
        },
    )


def _listening_item(
    source: Mapping[str, Any],
    unit: Mapping[str, Any],
    source_artifact_id: str,
) -> dict[str, Any]:
    source_id = str(source["activity_id"])
    audio = source.get("audio_contract", {})
    transcript = source.get("transcript_contract", {})
    answer_key = source.get("answer_key", {})
    return _base_item(
        source_item_id=source_id,
        source_kind="LISTENING_CANDIDATE",
        source_artifact_id=source_artifact_id,
        source_builder_path="ulga/builders/build_a1_grammar_listening_integration.py",
        unit=unit,
        skill="listening",
        item_role=str(source["activity_role"]),
        evidence_dimension=str(source["evidence_dimension"]),
        task_type=str(source["task_type"]),
        prompt_contract={
            "prompt_text": str(source.get("prompt") or "Complete the Listening item."),
            "prompt_status": "PROJECT_AUTHORED_CANDIDATE",
        },
        response_contract={
            "response_mode": str(source.get("response_mode") or "select_or_short_response"),
            "learner_input_required": True,
        },
        answer_contract={
            "answer_mode": "TRANSCRIPT_BACKED_CANDIDATE",
            "answer_status": "CANDIDATE_CONTRACT_AVAILABLE",
            "exact_text_match_required": False,
            "accepted_texts": list(answer_key.get("accepted_texts", [])),
            "transcript_ref": transcript.get("transcript_ref"),
            "transcript_text": transcript.get("transcript_text"),
        },
        scoring_contract={
            "scoring_mode": "TRANSCRIPT_BACKED_CANDIDATE",
            "deterministic_candidate": True,
            "real_skill_scoring_ready": False,
            "human_review_fallback": True,
            "required_evidence": ["rendered_audio_asset", "learner_response"],
        },
        media_contract={
            "text_status": "AVAILABLE",
            "audio_required": True,
            "audio_status": str(audio.get("audio_asset_status") or "NOT_RENDERED"),
            "transcript_required": True,
            "transcript_status": "CANDIDATE_AVAILABLE",
            "image_required": False,
            "image_status": "NOT_REQUIRED",
            "learner_capture_required": False,
            "learner_capture_status": "NOT_REQUIRED",
        },
        source_trace_extra={
            "audio_ref": audio.get("audio_ref"),
            "transcript_ref": transcript.get("transcript_ref"),
            "timestamp_status": transcript.get("timestamp_status"),
        },
    )


def _speaking_item(
    source: Mapping[str, Any],
    unit: Mapping[str, Any],
    source_artifact_id: str,
) -> dict[str, Any]:
    source_id = str(source["activity_id"])
    prompt = source.get("prompt_contract", {})
    capture = source.get("capture_contract", {})
    answer_key = source.get("answer_key", {})
    return _base_item(
        source_item_id=source_id,
        source_kind="SPEAKING_CANDIDATE",
        source_artifact_id=source_artifact_id,
        source_builder_path="ulga/builders/build_a1_grammar_speaking_integration.py",
        unit=unit,
        skill="speaking",
        item_role=str(source["activity_role"]),
        evidence_dimension=str(source["evidence_dimension"]),
        task_type=str(source["task_type"]),
        prompt_contract={
            "prompt_text": str(prompt.get("prompt") or "Complete the Speaking item."),
            "prompt_status": "PROJECT_AUTHORED_CANDIDATE",
            "communicative_function": prompt.get("communicative_function"),
            "expected_grammar_evidence": deepcopy(prompt.get("expected_grammar_evidence", {})),
            "allowed_variation": deepcopy(prompt.get("allowed_variation", {})),
            "repair_opportunity": deepcopy(prompt.get("repair_opportunity", {})),
        },
        response_contract={
            "response_mode": str(source.get("response_mode") or "spoken_response"),
            "learner_input_required": True,
            "audio_capture_required": True,
            "transcript_required_for_scoring": True,
        },
        answer_contract={
            "answer_mode": "FEATURE_RUBRIC_CANDIDATE",
            "answer_status": "CANDIDATE_CONTRACT_AVAILABLE",
            "exact_text_match_required": False,
            "model_texts": list(answer_key.get("model_texts", [])),
            "grammar_evidence_required": bool(answer_key.get("grammar_evidence_required")),
            "expected_grammar_evidence": deepcopy(prompt.get("expected_grammar_evidence", {})),
            "allowed_variation": deepcopy(prompt.get("allowed_variation", {})),
        },
        scoring_contract={
            "scoring_mode": "FEATURE_RUBRIC_CANDIDATE",
            "deterministic_candidate": False,
            "real_skill_scoring_ready": False,
            "human_review_fallback": True,
            "required_evidence": ["learner_audio_capture", "learner_transcript", "grammar_feature_evaluation"],
        },
        media_contract={
            "text_status": "MODEL_TEXT_AVAILABLE",
            "audio_required": True,
            "audio_status": str(capture.get("audio_capture_status") or "NOT_IMPLEMENTED"),
            "transcript_required": True,
            "transcript_status": "NOT_COLLECTED",
            "image_required": False,
            "image_status": "NOT_REQUIRED",
            "learner_capture_required": True,
            "learner_capture_status": str(capture.get("audio_capture_status") or "NOT_IMPLEMENTED"),
        },
        source_trace_extra={
            "audio_ref": capture.get("audio_ref"),
            "asr_status": capture.get("asr_status"),
            "manual_transcript_status": capture.get("manual_transcript_status"),
        },
    )


def build_artifact() -> dict[str, Any]:
    if M02_NEXT_SHORT_STEP != TASK_ID:
        raise RuntimeError("m02_continuation_contract_mismatch")
    learning_units = build_learning_units()
    unit_index = _learning_unit_index(learning_units)

    text_source, text_report = build_text_mode_source()
    listening_source, listening_report = build_listening_source()
    speaking_source, speaking_report = build_speaking_source()
    _require_pass("text_mode", text_report)
    _require_pass("listening", listening_report)
    _require_pass("speaking", speaking_report)

    items: list[dict[str, Any]] = []
    for source in text_source.get("item_bank", []):
        grammar_id = str(source.get("content_binding", {}).get("grammar_focus", [""])[0])
        unit = unit_index.get(grammar_id)
        if not unit:
            raise ValueError(f"m03_text_item_unknown_unit:{source.get('item_id')}")
        items.append(_text_item(source, unit, str(text_source["artifact_id"])))

    for source in listening_source.get("listening_activity_bank", []):
        grammar_id = str(source.get("grammar_unit_id") or "")
        unit = unit_index.get(grammar_id)
        if not unit:
            raise ValueError(f"m03_listening_item_unknown_unit:{source.get('activity_id')}")
        items.append(_listening_item(source, unit, str(listening_source["artifact_id"])))

    for source in speaking_source.get("speaking_activity_bank", []):
        grammar_id = str(source.get("grammar_unit_id") or "")
        unit = unit_index.get(grammar_id)
        if not unit:
            raise ValueError(f"m03_speaking_item_unknown_unit:{source.get('activity_id')}")
        items.append(_speaking_item(source, unit, str(speaking_source["artifact_id"])))

    shared_ids = [item["shared_item_id"] for item in items]
    source_ids = [item["source_item_id"] for item in items]
    if len(items) != 384:
        raise ValueError(f"m03_item_count_not_384:{len(items)}")
    if len(set(shared_ids)) != 384 or len(set(source_ids)) != 384:
        raise ValueError("m03_item_ids_not_unique_384")

    items.sort(
        key=lambda item: (
            unit_index[item["grammar_unit_id"]]["sequence_index"],
            SKILLS.index(item["skill"]),
            item["source_item_id"],
        )
    )
    by_unit: dict[str, list[str]] = {unit_id: [] for unit_id in unit_index}
    by_skill: dict[str, list[str]] = {skill: [] for skill in SKILLS}
    by_source_item_id: dict[str, str] = {}
    for item in items:
        by_unit[item["grammar_unit_id"]].append(item["shared_item_id"])
        by_skill[item["skill"]].append(item["shared_item_id"])
        by_source_item_id[item["source_item_id"]] = item["shared_item_id"]

    skill_counts = {skill: len(by_skill[skill]) for skill in SKILLS}
    if skill_counts != SOURCE_COUNTS:
        raise ValueError(f"m03_skill_counts_mismatch:{skill_counts}")
    unit_item_counts = {grammar_id: len(item_ids) for grammar_id, item_ids in by_unit.items()}
    if set(unit_item_counts.values()) != {16}:
        raise ValueError(f"m03_unit_item_counts_not_16:{unit_item_counts}")

    assessment_counts = {
        skill: sum(item["skill"] == skill and item["item_role"] == "assessment" for item in items)
        for skill in SKILLS
    }
    practice_counts = {
        skill: sum(item["skill"] == skill and item["item_role"] == "practice" for item in items)
        for skill in SKILLS
    }
    return {
        "task_id": TASK_ID,
        "epic_id": EPIC_ID,
        "artifact_id": ARTIFACT_ID,
        "artifact_type": "a1_a1plus_shared_four_skill_item_contract",
        "schema_version": SCHEMA_VERSION,
        "schema_path": str(SCHEMA_PATH.relative_to(REPO_ROOT)),
        "scope": "A1_A1_PLUS_ONLY",
        "coverage_summary": {
            "learning_unit_count": 24,
            "canonical_egp_row_count": 109,
            "direct_canonical_unit_count": 23,
            "rowless_structural_unit_count": 1,
            "shared_item_count": len(items),
            "items_per_unit": 16,
            "skill_item_counts": skill_counts,
            "skill_practice_counts": practice_counts,
            "skill_assessment_counts": assessment_counts,
            "rendered_listening_audio_count": 0,
            "captured_speaking_audio_count": 0,
            "collected_speaking_transcript_count": 0,
        },
        "source_artifact_ids": [
            learning_units["artifact_id"],
            text_source["artifact_id"],
            listening_source["artifact_id"],
            speaking_source["artifact_id"],
        ],
        "shared_items": items,
        "by_grammar_unit_id": by_unit,
        "by_skill": by_skill,
        "by_source_item_id": by_source_item_id,
        "claim_boundaries": {
            "m03_shared_item_contract_complete": True,
            "answer_scoring_contract_complete": True,
            "media_contract_complete": True,
            "reading_v1_complete": False,
            "writing_v1_complete": False,
            "listening_audio_assets_complete": False,
            "speaking_capture_complete": False,
            "real_learner_evidence_complete": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "persistent_learner_state_write": False,
            "production_runtime_event": False,
            "a2_a2plus_in_scope": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    artifact = build_artifact()
    write_json(args.output, artifact)
    print(json.dumps(artifact["coverage_summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
