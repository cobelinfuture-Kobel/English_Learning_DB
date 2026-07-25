from __future__ import annotations

import copy
import json

import pytest

from ulga.builders import build_a1_a1plus_shared_item_contract as m03
from ulga.builders import build_a1fs_online_v1_s02_first_nonaudio_unit_admission as s02
from ulga.builders import build_a1fs_v1_cp01_existing_24_unit_curriculum_backfill as cp01
from ulga.builders import build_a1fs_v1_cp04_unified_content_exercise_scene_candidates as cp04
from ulga.validators.validate_a1fs_online_v1_s02_first_nonaudio_unit_admission import (
    validate_artifact,
)


SKILLS = ("reading", "writing", "listening", "speaking")


def _cp01() -> dict:
    units = []
    for index in range(1, 25):
        grammar_id = f"GRAMMAR_TEST_{index:02d}"
        units.append(
            {
                "learning_unit_id": f"A1FS_UNIT_{index:02d}",
                "grammar_unit_id": grammar_id,
                "sequence_index": index,
                "internal_stage": "A1_CORE" if index <= 12 else "A1_PLUS_EXTENSION",
                "canonical_egp_row_ids": [f"EGP_TEST_{index:03d}"],
                "prerequisite_unit_ids": [] if index == 1 else [f"A1FS_UNIT_{index - 1:02d}"],
            }
        )
    return {
        "task_id": cp01.TASK_ID,
        "program_id": cp01.PROGRAM_ID,
        "schema_version": cp01.SCHEMA_VERSION,
        "scope": "A1_A1_PLUS_ONLY",
        "coverage_summary": {"learning_unit_count": 24},
        "learning_units": units,
        "stop_reason": "NONE",
        "next_short_step": cp01.NEXT_SHORT_STEP,
    }


def _item(grammar_id: str, learning_id: str, skill: str, role: str, ordinal: int) -> dict:
    item_id = f"E4S_A1V1_ITEM:{grammar_id}:{skill}:{role}:{ordinal}"
    return {
        "shared_item_id": item_id,
        "source_item_id": f"SRC:{grammar_id}:{skill}:{role}:{ordinal}",
        "schema_version": m03.SCHEMA_VERSION,
        "learning_unit_id": learning_id,
        "grammar_unit_id": grammar_id,
        "official_cefr_level": "A1",
        "internal_stage": "A1_CORE",
        "skill": skill,
        "item_role": role,
        "evidence_dimension": "controlled_practice",
        "task_type": "guided_response",
        "prompt_contract": {
            "prompt_text": f"Private source prompt {ordinal}",
            "prompt_status": "PROJECT_AUTHORED_CANDIDATE",
        },
        "response_contract": {"learner_input_required": True},
        "answer_contract": {"answer_status": "CANDIDATE_CONTRACT_AVAILABLE"},
        "scoring_contract": {"scoring_mode": "TEST"},
        "media_contract": {
            "audio_required": skill in {"listening", "speaking"},
            "audio_status": "NOT_IMPLEMENTED",
        },
        "readiness": {
            "shared_item_contract_complete": True,
            "answer_contract_complete": True,
            "scoring_contract_complete": True,
            "media_contract_complete": True,
            "real_skill_delivery_complete": False,
            "actual_learner_evidence_complete": False,
        },
    }


def _m03(cp01_artifact: dict) -> dict:
    items = []
    by_unit = {}
    by_skill = {skill: [] for skill in SKILLS}
    for unit in cp01_artifact["learning_units"]:
        local = []
        for skill in SKILLS:
            for ordinal in range(1, 5):
                role = "assessment" if ordinal == 4 else "practice"
                item = _item(
                    unit["grammar_unit_id"],
                    unit["learning_unit_id"],
                    skill,
                    role,
                    ordinal,
                )
                items.append(item)
                local.append(item["shared_item_id"])
                by_skill[skill].append(item["shared_item_id"])
        by_unit[unit["grammar_unit_id"]] = local
    return {
        "task_id": m03.TASK_ID,
        "epic_id": m03.EPIC_ID,
        "artifact_id": m03.ARTIFACT_ID,
        "artifact_type": "a1_a1plus_shared_four_skill_item_contract",
        "schema_version": m03.SCHEMA_VERSION,
        "scope": "A1_A1_PLUS_ONLY",
        "coverage_summary": {
            "learning_unit_count": 24,
            "shared_item_count": 384,
            "items_per_unit": 16,
        },
        "shared_items": items,
        "by_grammar_unit_id": by_unit,
        "by_skill": by_skill,
        "stop_reason": "NONE",
        "next_short_step": m03.NEXT_SHORT_STEP,
    }


def _cp04(cp01_artifact: dict, m03_artifact: dict, *, unit1_limit: int | None = None) -> dict:
    by_grammar = {}
    for item in m03_artifact["shared_items"]:
        by_grammar.setdefault(item["grammar_unit_id"], []).append(item)
    units = []
    for source in cp01_artifact["learning_units"]:
        grammar_id = source["grammar_unit_id"]
        exercises = []
        for skill in ("reading", "writing"):
            rows = [
                row
                for row in by_grammar[grammar_id]
                if row["skill"] == skill
            ]
            if source["sequence_index"] == 1 and unit1_limit is not None:
                rows = rows[:unit1_limit]
            for item in rows:
                exercises.append(
                    {
                        "exercise_candidate_id": f"EX:{item['shared_item_id']}",
                        "content_candidate_id": f"CONTENT:{item['shared_item_id']}",
                        "source_kind": "M11B_REVIEWED_SHARED_ITEM",
                        "source_ref": item["shared_item_id"],
                        "target_skill_lanes": [skill],
                        "candidate_mode": "REUSE_EXISTING_REVIEWED_EXERCISE",
                        "candidate_state": "READY_FOR_PRIVATE_POPULATION",
                        "new_content_authoring_required": False,
                    }
                )
        units.append(
            {
                "learning_unit_id": source["learning_unit_id"],
                "grammar_unit_id": grammar_id,
                "sequence_index": source["sequence_index"],
                "internal_stage": source["internal_stage"],
                "canonical_egp_row_ids": list(source["canonical_egp_row_ids"]),
                "content_candidates": [],
                "exercise_candidates": exercises,
                "scene_candidates": [
                    {
                        "scene_candidate_id": f"SCENE:{grammar_id}",
                        "candidate_state": "AUTHORITY_BACKED_METADATA_READY",
                    }
                ],
                "candidate_counts": {},
                "candidate_population_status": "CONTENT_EXERCISE_AND_SCENE_CANDIDATES_AVAILABLE",
            }
        )
    return {
        "task_id": cp04.TASK_ID,
        "program_id": cp04.PROGRAM_ID,
        "schema_version": cp04.SCHEMA_VERSION,
        "artifact_type": "metadata_only_unified_content_exercise_scene_candidate_envelopes",
        "scope": "A1_A1_PLUS_ONLY",
        "candidate_contract": {
            "course_container": "EXISTING_24_CANONICAL_UNITS_ONLY",
            "new_unit_creation_allowed": False,
            "private_source_read_performed": False,
        },
        "coverage_summary": {"existing_learning_unit_count": 24},
        "learning_units": units,
        "stop_reason": "NONE",
        "next_short_step": cp04.NEXT_SHORT_STEP,
    }


def _sources(*, unit1_limit: int | None = None) -> tuple[dict, dict, dict]:
    curriculum = _cp01()
    shared = _m03(curriculum)
    candidates = _cp04(curriculum, shared, unit1_limit=unit1_limit)
    return curriculum, candidates, shared


def test_builds_one_prerequisite_free_three_lane_unit_and_defers_audio() -> None:
    curriculum, candidates, shared = _sources()
    artifact = s02.build_artifact(curriculum, candidates, shared)

    assert artifact["selected_unit"]["sequence_index"] == 1
    lanes = artifact["selected_unit"]["admitted_lanes"]
    assert lanes["reading"]["item_count"] == 4
    assert lanes["writing"]["item_count"] == 4
    assert lanes["speaking"]["item_count"] == 3
    assert lanes["speaking"]["delivery_mode"] == "ORAL_PRACTICE_CARD_NO_CAPTURE"
    assert lanes["speaking"]["evidence_policy"] == "NO_SCORING_NO_MASTERY_EVIDENCE"
    assert artifact["admission_summary"]["listening_item_count"] == 0
    assert artifact["selected_unit"]["deferred_lanes"]["listening"]["item_ids"] == []
    assert len(artifact["selected_unit"]["deferred_lanes"]["speaking_assessment"]["item_ids"]) == 1

    report = validate_artifact(artifact, curriculum, candidates, shared)
    assert report["error_count"] == 0


def test_ranking_uses_availability_before_sequence_among_prerequisite_free_units() -> None:
    curriculum, candidates, shared = _sources(unit1_limit=1)
    curriculum["learning_units"][1]["prerequisite_unit_ids"] = []
    artifact = s02.build_artifact(curriculum, candidates, shared)

    assert artifact["selected_unit"]["sequence_index"] == 2
    assert artifact["eligible_unit_count"] == 2


def test_unit_with_prerequisite_is_never_selected_even_with_more_items() -> None:
    curriculum, candidates, shared = _sources(unit1_limit=1)
    artifact = s02.build_artifact(curriculum, candidates, shared)

    assert artifact["selected_unit"]["sequence_index"] == 1
    assert artifact["eligible_unit_count"] == 1


def test_speaking_assessment_cannot_enter_prelaunch_admitted_lane() -> None:
    curriculum, candidates, shared = _sources()
    artifact = s02.build_artifact(curriculum, candidates, shared)
    speaking_ids = artifact["selected_unit"]["admitted_lanes"]["speaking"]["item_ids"]
    index = {row["shared_item_id"]: row for row in shared["shared_items"]}

    assert speaking_ids
    assert all(index[item_id]["item_role"] == "practice" for item_id in speaking_ids)
    assert all(index[item_id]["skill"] == "speaking" for item_id in speaking_ids)


def test_fails_closed_when_prerequisite_free_unit_has_no_speaking_practice() -> None:
    curriculum, candidates, shared = _sources()
    grammar_id = curriculum["learning_units"][0]["grammar_unit_id"]
    for item in shared["shared_items"]:
        if item["grammar_unit_id"] == grammar_id and item["skill"] == "speaking":
            item["item_role"] = "assessment"

    with pytest.raises(s02.FirstUnitAdmissionError, match="no_prerequisite_free_three_lane_unit_available"):
        s02.build_artifact(curriculum, candidates, shared)


def test_safe_report_contains_counts_but_no_item_or_learner_content() -> None:
    curriculum, candidates, shared = _sources()
    artifact = s02.build_artifact(curriculum, candidates, shared)
    report = s02.build_safe_report(artifact)
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["admission_summary"]["admitted_nonaudio_item_count"] == 11
    assert "E4S_A1V1_ITEM" not in rendered
    assert "Private source prompt" not in rendered
    assert report["audio_deferred"] is True


def test_validator_rejects_injected_listening_admission() -> None:
    curriculum, candidates, shared = _sources()
    artifact = s02.build_artifact(curriculum, candidates, shared)
    tampered = copy.deepcopy(artifact)
    tampered["selected_unit"]["deferred_lanes"]["listening"]["item_ids"] = [
        "E4S_A1V1_ITEM:FAKE_LISTENING"
    ]
    core = {key: value for key, value in tampered.items() if key != "artifact_sha256"}
    tampered["artifact_sha256"] = s02.digest(core)

    report = validate_artifact(tampered, curriculum, candidates, shared)
    assert "listening_item_admitted" in report["errors"]
