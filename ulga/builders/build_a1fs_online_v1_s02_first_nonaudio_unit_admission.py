#!/usr/bin/env python3
"""Admit the first production A1/A1+ unit for the audio-deferred online release.

The builder reuses the existing CP01/CP04 24-unit authority and M03 shared-item
identity set. It does not create a new curriculum, author learner content, admit
Listening without audio, capture Speaking audio, or claim Speaking assessment
evidence. Speaking is admitted only as a display-only oral practice card.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1_a1plus_shared_item_contract as m03  # noqa: E402
from ulga.builders import build_a1fs_v1_cp01_existing_24_unit_curriculum_backfill as cp01  # noqa: E402
from ulga.builders import build_a1fs_v1_cp04_unified_content_exercise_scene_candidates as cp04  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Selects existing reviewed item IDs and unit-bound Speaking practice-card IDs for one audio-deferred production unit; no learner content is authored or copied."

PROGRAM_ID = "A1FS-ONLINE-V1"
TASK_ID = "A1FS-ONLINE-V1-S02_FirstProductionUnitNonAudioContentAdmission"
SCHEMA_VERSION = "a1fs.online.v1.s02.first_nonaudio_unit_admission.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_S02_FIRST_NONAUDIO_UNIT_ADMITTED"
NEXT_SHORT_STEP = "A1FS-ONLINE-V1-S03_UnifiedLearnerRuntimeIntegration_NoAudio"
RELEASE_PROFILE = "ONLINE_V1_AUDIO_DEFERRED"

CP01_PATH = cp01.OUTPUT_PATH
CP04_PATH = cp04.OUTPUT_PATH
M03_PATH = m03.OUTPUT_PATH
OUTPUT_PATH = REPO_ROOT / ".local/a1fs_online_v1/s02/first_nonaudio_unit_admission.private.json"
REPORT_PATH = REPO_ROOT / ".local/a1fs_online_v1/s02/first_nonaudio_unit_admission.safe.json"

REQUIRED_LANES = ("reading", "writing", "speaking")
AUDIO_DEFERRED_LANES = ("listening", "speaking_assessment")


class FirstUnitAdmissionError(ValueError):
    """Fail-closed source, identity, selection, or audio-boundary error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FirstUnitAdmissionError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise FirstUnitAdmissionError(f"{code}_not_object")
    return value


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _units_by_grammar(artifact: Mapping[str, Any], code: str) -> dict[str, Mapping[str, Any]]:
    rows = artifact.get("learning_units")
    if not isinstance(rows, list) or len(rows) != 24:
        raise FirstUnitAdmissionError(f"{code}_learning_unit_count_not_24")
    result: dict[str, Mapping[str, Any]] = {}
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            raise FirstUnitAdmissionError(f"{code}_unit_not_object")
        grammar_id = str(row.get("grammar_unit_id") or "")
        learning_id = str(row.get("learning_unit_id") or "")
        if (
            not grammar_id
            or not learning_id
            or grammar_id in result
            or row.get("sequence_index") != index
        ):
            raise FirstUnitAdmissionError(f"{code}_unit_identity_invalid:{grammar_id}")
        result[grammar_id] = row
    return result


def _verify_cp01(artifact: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if artifact.get("task_id") != cp01.TASK_ID:
        raise FirstUnitAdmissionError("cp01_task_id_mismatch")
    if artifact.get("scope") != "A1_A1_PLUS_ONLY" or artifact.get("stop_reason") != "NONE":
        raise FirstUnitAdmissionError("cp01_scope_or_status_invalid")
    summary = artifact.get("coverage_summary", {})
    if summary.get("learning_unit_count") != 24:
        raise FirstUnitAdmissionError("cp01_unit_denominator_invalid")
    return _units_by_grammar(artifact, "cp01")


def _verify_cp04(artifact: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if artifact.get("task_id") != cp04.TASK_ID:
        raise FirstUnitAdmissionError("cp04_task_id_mismatch")
    if artifact.get("scope") != "A1_A1_PLUS_ONLY" or artifact.get("stop_reason") != "NONE":
        raise FirstUnitAdmissionError("cp04_scope_or_status_invalid")
    contract = artifact.get("candidate_contract", {})
    if (
        contract.get("course_container") != "EXISTING_24_CANONICAL_UNITS_ONLY"
        or contract.get("new_unit_creation_allowed") is not False
        or contract.get("private_source_read_performed") is not False
    ):
        raise FirstUnitAdmissionError("cp04_candidate_contract_invalid")
    return _units_by_grammar(artifact, "cp04")


def _verify_m03(artifact: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if (
        artifact.get("task_id") != m03.TASK_ID
        or artifact.get("scope") != "A1_A1_PLUS_ONLY"
        or artifact.get("stop_reason") != "NONE"
    ):
        raise FirstUnitAdmissionError("m03_identity_or_status_invalid")
    summary = artifact.get("coverage_summary", {})
    if summary.get("learning_unit_count") != 24 or summary.get("shared_item_count") != 384:
        raise FirstUnitAdmissionError("m03_denominator_invalid")
    rows = artifact.get("shared_items")
    if not isinstance(rows, list) or len(rows) != 384:
        raise FirstUnitAdmissionError("m03_shared_items_invalid")
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise FirstUnitAdmissionError("m03_item_not_object")
        item_id = str(row.get("shared_item_id") or "")
        if not item_id or item_id in result:
            raise FirstUnitAdmissionError(f"m03_item_identity_invalid:{item_id}")
        result[item_id] = row
    return result


def _ready_m11b_ids(
    unit: Mapping[str, Any],
    skill: str,
    item_index: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    result: list[str] = []
    for row in unit.get("exercise_candidates", []):
        if not isinstance(row, Mapping):
            raise FirstUnitAdmissionError("cp04_exercise_candidate_not_object")
        if (
            row.get("source_kind") != "M11B_REVIEWED_SHARED_ITEM"
            or row.get("candidate_state") != "READY_FOR_PRIVATE_POPULATION"
            or row.get("target_skill_lanes") != [skill]
        ):
            continue
        item_id = str(row.get("source_ref") or "")
        item = item_index.get(item_id)
        if (
            item is None
            or item.get("grammar_unit_id") != unit.get("grammar_unit_id")
            or item.get("skill") != skill
            or item.get("item_role") not in {"practice", "assessment"}
            or item.get("readiness", {}).get("shared_item_contract_complete") is not True
        ):
            raise FirstUnitAdmissionError(f"cp04_m11b_item_binding_invalid:{skill}:{item_id}")
        result.append(item_id)
    if len(result) != len(set(result)):
        raise FirstUnitAdmissionError(f"cp04_m11b_item_duplicate:{skill}")
    return sorted(result)


def _speaking_practice_ids(
    grammar_id: str,
    item_index: Mapping[str, Mapping[str, Any]],
) -> tuple[list[str], list[str]]:
    practice: list[str] = []
    assessments: list[str] = []
    for item_id, item in item_index.items():
        if item.get("grammar_unit_id") != grammar_id or item.get("skill") != "speaking":
            continue
        role = str(item.get("item_role") or "")
        if role == "assessment":
            assessments.append(item_id)
            continue
        if role != "practice":
            raise FirstUnitAdmissionError(f"speaking_item_role_invalid:{item_id}")
        prompt = item.get("prompt_contract", {})
        readiness = item.get("readiness", {})
        if (
            not isinstance(prompt, Mapping)
            or not str(prompt.get("prompt_text") or "").strip()
            or prompt.get("prompt_status") != "PROJECT_AUTHORED_CANDIDATE"
            or readiness.get("shared_item_contract_complete") is not True
        ):
            raise FirstUnitAdmissionError(f"speaking_practice_contract_invalid:{item_id}")
        practice.append(item_id)
    return sorted(practice), sorted(assessments)


def _candidate_rows(
    cp01_units: Mapping[str, Mapping[str, Any]],
    cp04_units: Mapping[str, Mapping[str, Any]],
    item_index: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if set(cp01_units) != set(cp04_units):
        raise FirstUnitAdmissionError("cp01_cp04_unit_set_mismatch")
    candidates: list[dict[str, Any]] = []
    for grammar_id, curriculum_unit in cp01_units.items():
        candidate_unit = cp04_units[grammar_id]
        identity = (
            curriculum_unit.get("learning_unit_id"),
            curriculum_unit.get("sequence_index"),
            curriculum_unit.get("internal_stage"),
            curriculum_unit.get("canonical_egp_row_ids"),
        )
        peer_identity = (
            candidate_unit.get("learning_unit_id"),
            candidate_unit.get("sequence_index"),
            candidate_unit.get("internal_stage"),
            candidate_unit.get("canonical_egp_row_ids"),
        )
        if identity != peer_identity:
            raise FirstUnitAdmissionError(f"cp01_cp04_unit_identity_drift:{grammar_id}")
        prerequisites = curriculum_unit.get("prerequisite_unit_ids")
        if not isinstance(prerequisites, list) or len(prerequisites) != len(set(prerequisites)):
            raise FirstUnitAdmissionError(f"prerequisite_contract_invalid:{grammar_id}")
        reading = _ready_m11b_ids(candidate_unit, "reading", item_index)
        writing = _ready_m11b_ids(candidate_unit, "writing", item_index)
        speaking, speaking_assessments = _speaking_practice_ids(grammar_id, item_index)
        if prerequisites or not reading or not writing or not speaking:
            continue
        scenes = [
            str(row.get("scene_candidate_id"))
            for row in candidate_unit.get("scene_candidates", [])
            if isinstance(row, Mapping)
            and row.get("candidate_state") == "AUTHORITY_BACKED_METADATA_READY"
            and str(row.get("scene_candidate_id") or "")
        ]
        lane_counts = {"reading": len(reading), "writing": len(writing), "speaking": len(speaking)}
        candidates.append(
            {
                "grammar_unit_id": grammar_id,
                "learning_unit_id": str(curriculum_unit["learning_unit_id"]),
                "sequence_index": int(curriculum_unit["sequence_index"]),
                "internal_stage": curriculum_unit["internal_stage"],
                "canonical_egp_row_ids": list(curriculum_unit["canonical_egp_row_ids"]),
                "prerequisite_unit_ids": [],
                "reading_item_ids": reading,
                "writing_item_ids": writing,
                "speaking_practice_item_ids": speaking,
                "speaking_assessment_deferred_item_ids": speaking_assessments,
                "scene_candidate_ids": sorted(set(scenes)),
                "lane_counts": lane_counts,
                "availability_score": min(lane_counts.values()) * 1000 + sum(lane_counts.values()),
            }
        )
    candidates.sort(
        key=lambda row: (
            -int(row["availability_score"]),
            int(row["sequence_index"]),
            str(row["learning_unit_id"]),
        )
    )
    return candidates


def _admitted_lane(item_ids: Sequence[str], mode: str, evidence_policy: str) -> dict[str, Any]:
    return {
        "item_ids": list(item_ids),
        "item_count": len(item_ids),
        "delivery_mode": mode,
        "evidence_policy": evidence_policy,
        "admission_status": "ADMITTED_FOR_AUDIO_DEFERRED_ONLINE_RELEASE",
    }


def build_artifact(
    cp01_artifact: Mapping[str, Any],
    cp04_artifact: Mapping[str, Any],
    shared_item_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    cp01_units = _verify_cp01(cp01_artifact)
    cp04_units = _verify_cp04(cp04_artifact)
    item_index = _verify_m03(shared_item_artifact)
    candidates = _candidate_rows(cp01_units, cp04_units, item_index)
    if not candidates:
        raise FirstUnitAdmissionError("no_prerequisite_free_three_lane_unit_available")
    selected = candidates[0]
    admitted_ids = (
        selected["reading_item_ids"]
        + selected["writing_item_ids"]
        + selected["speaking_practice_item_ids"]
    )
    if len(admitted_ids) != len(set(admitted_ids)):
        raise FirstUnitAdmissionError("selected_unit_item_identity_collision")

    selected_unit = {
        "learning_unit_id": selected["learning_unit_id"],
        "grammar_unit_id": selected["grammar_unit_id"],
        "sequence_index": selected["sequence_index"],
        "internal_stage": selected["internal_stage"],
        "canonical_egp_row_ids": selected["canonical_egp_row_ids"],
        "prerequisite_unit_ids": [],
        "selection_rank": 1,
        "availability_score": selected["availability_score"],
        "admitted_lanes": {
            "reading": _admitted_lane(
                selected["reading_item_ids"],
                "INTERACTIVE_TEXT_ITEM",
                "EXISTING_DETERMINISTIC_OR_REVIEWED_SCORING_CONTRACT",
            ),
            "writing": _admitted_lane(
                selected["writing_item_ids"],
                "INTERACTIVE_TEXT_ITEM",
                "EXISTING_DETERMINISTIC_OR_REVIEWED_SCORING_CONTRACT",
            ),
            "speaking": _admitted_lane(
                selected["speaking_practice_item_ids"],
                "ORAL_PRACTICE_CARD_NO_CAPTURE",
                "NO_SCORING_NO_MASTERY_EVIDENCE",
            ),
        },
        "scene_candidate_ids": selected["scene_candidate_ids"],
        "deferred_lanes": {
            "listening": {
                "status": "DEFERRED_POST_LAUNCH_AUDIO",
                "reason": "PLAYABLE_AUDIO_REQUIRED_AND_NOT_IN_PRELAUNCH_SCOPE",
                "item_ids": [],
            },
            "speaking_assessment": {
                "status": "DEFERRED_POST_LAUNCH_AUDIO",
                "reason": "RECORDING_TRANSCRIPT_AND_SCORING_NOT_IN_PRELAUNCH_SCOPE",
                "item_ids": selected["speaking_assessment_deferred_item_ids"],
            },
        },
        "unit_admission_status": "ADMITTED_NONAUDIO_FIRST_PRODUCTION_UNIT",
    }

    core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "artifact_type": "first_production_unit_nonaudio_admission_package",
        "scope": "A1_A1_PLUS_ONLY",
        "release_profile": RELEASE_PROFILE,
        "source_identity": {
            "cp01_task_id": cp01_artifact["task_id"],
            "cp01_sha256": digest(cp01_artifact),
            "cp04_task_id": cp04_artifact["task_id"],
            "cp04_sha256": digest(cp04_artifact),
            "m03_task_id": shared_item_artifact["task_id"],
            "m03_sha256": digest(shared_item_artifact),
        },
        "selection_contract": {
            "course_container": "EXISTING_24_CANONICAL_UNITS_ONLY",
            "eligibility": "PREREQUISITE_FREE_AND_READING_WRITING_SPEAKING_PRACTICE_AVAILABLE",
            "ranking": "HIGHEST_MINIMUM_LANE_COUNT_THEN_TOTAL_COUNT_THEN_SEQUENCE",
            "required_prelaunch_lanes": list(REQUIRED_LANES),
            "audio_deferred_lanes": list(AUDIO_DEFERRED_LANES),
            "new_unit_creation_allowed": False,
            "listening_without_playable_audio_allowed": False,
            "speaking_capture_or_scoring_claim_allowed": False,
        },
        "eligible_unit_count": len(candidates),
        "selected_unit": selected_unit,
        "admission_summary": {
            "admitted_unit_count": 1,
            "reading_item_count": len(selected["reading_item_ids"]),
            "writing_item_count": len(selected["writing_item_ids"]),
            "speaking_practice_card_count": len(selected["speaking_practice_item_ids"]),
            "listening_item_count": 0,
            "speaking_assessment_item_count": 0,
            "admitted_nonaudio_item_count": len(admitted_ids),
            "scene_candidate_count": len(selected["scene_candidate_ids"]),
        },
        "product_status": "INCOMPLETE_NOT_ONLINE_USABLE",
        "claim_boundaries": {
            "canonical_unit_identity_changed": False,
            "new_curriculum_created": False,
            "new_learner_content_authored": False,
            "listening_complete": False,
            "speaking_recording_complete": False,
            "speaking_assessment_evidence_claimed": False,
            "complete_four_skill_product_claimed": False,
            "online_usable_claimed": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "a2_a2plus_in_scope": False,
            "a2_unlocked": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    artifact = {**core, "artifact_sha256": digest(core)}
    safe_scan(artifact)
    return artifact


def build_safe_report(artifact: Mapping[str, Any]) -> dict[str, Any]:
    unit = artifact["selected_unit"]
    core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": artifact["validation_status"],
        "release_profile": artifact["release_profile"],
        "selected_unit": {
            "learning_unit_id": unit["learning_unit_id"],
            "grammar_unit_id": unit["grammar_unit_id"],
            "sequence_index": unit["sequence_index"],
            "prerequisite_unit_count": len(unit["prerequisite_unit_ids"]),
            "scene_candidate_count": len(unit["scene_candidate_ids"]),
        },
        "admission_summary": dict(artifact["admission_summary"]),
        "audio_deferred": True,
        "product_status": artifact["product_status"],
        "stop_reason": artifact["stop_reason"],
        "next_short_step": artifact["next_short_step"],
    }
    report = {**core, "report_sha256": digest(core)}
    safe_scan(report)
    return report


def safe_scan(value: Any) -> None:
    forbidden = {
        "answer",
        "answer_key",
        "accepted_texts",
        "model_text",
        "model_texts",
        "payload",
        "private_scoring_contract",
        "prompt",
        "prompt_text",
        "rubric",
        "transcript",
        "transcript_text",
        "learner_response",
    }

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in forbidden:
                    raise FirstUnitAdmissionError(f"private_or_learner_content_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cp01", type=Path, default=CP01_PATH)
    parser.add_argument("--cp04", type=Path, default=CP04_PATH)
    parser.add_argument("--m03", type=Path, default=M03_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)
    try:
        cp01_artifact = read_json(args.cp01, "cp01")
        cp04_artifact = read_json(args.cp04, "cp04")
        m03_artifact = read_json(args.m03, "m03")
        artifact = build_artifact(cp01_artifact, cp04_artifact, m03_artifact)
        from ulga.validators.validate_a1fs_online_v1_s02_first_nonaudio_unit_admission import validate_artifact

        validation = validate_artifact(artifact, cp01_artifact, cp04_artifact, m03_artifact)
        if validation["error_count"]:
            raise FirstUnitAdmissionError("validation_failed:" + "|".join(validation["errors"]))
        write_json(args.output, artifact)
        write_json(args.report, build_safe_report(artifact))
        print(json.dumps(build_safe_report(artifact), ensure_ascii=False, indent=2))
        return 0
    except (FirstUnitAdmissionError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
