from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_online_v1_s02_first_nonaudio_unit_admission as s02
from ulga.builders import build_a1fs_online_v1_s09_twentyfour_unit_production_population as s09

REPO_ROOT = Path(__file__).resolve().parents[2]


def _item(
    *,
    item_id: str,
    grammar_id: str,
    learning_id: str,
    skill: str,
    role: str,
) -> dict:
    media = {
        "text_status": "AVAILABLE",
        "audio_required": False,
        "audio_status": "NOT_REQUIRED",
        "transcript_required": False,
        "transcript_status": "NOT_REQUIRED",
        "image_required": False,
        "image_status": "NOT_REQUIRED",
        "learner_capture_required": False,
        "learner_capture_status": "NOT_REQUIRED",
    }
    if skill == "listening":
        media["audio_required"] = True
        media["audio_status"] = "NOT_RENDERED"
    return {
        "shared_item_id": item_id,
        "learning_unit_id": learning_id,
        "grammar_unit_id": grammar_id,
        "skill": skill,
        "item_role": role,
        "prompt_contract": {
            "prompt_text": f"Prompt {item_id}",
            "prompt_status": "PROJECT_AUTHORED_CANDIDATE",
        },
        "response_contract": {
            "response_mode": "select_one",
            "learner_input_required": True,
        },
        "answer_contract": {
            "answer_mode": "DETERMINISTIC_OPTION",
            "answer_status": "CANDIDATE_CONTRACT_AVAILABLE",
        },
        "scoring_contract": {
            "scoring_mode": "DETERMINISTIC_OPTION",
            "real_skill_scoring_ready": skill in {"reading", "writing"},
            "human_review_fallback": skill not in {"reading", "writing"},
        },
        "media_contract": media,
        "readiness": {
            "shared_item_contract_complete": True,
            "answer_contract_complete": True,
            "scoring_contract_complete": True,
            "media_contract_complete": True,
        },
    }


def _fixtures(*, scene_gap: bool = True) -> tuple[dict, dict, dict]:
    cp01_units = []
    cp04_units = []
    shared_items = []
    scene_count = 0
    for index in range(1, 25):
        grammar_id = f"GRAMMAR_UNIT_{index:02d}"
        learning_id = f"E4S_A1V1_UNIT:{grammar_id}"
        skill_lanes = {}
        for skill, suffix in (
            ("reading", "R"),
            ("writing", "W"),
            ("listening", "L"),
            ("speaking", "S"),
        ):
            ids = []
            for item_index in range(1, 5):
                item_id = f"E4S_A1V1_ITEM:{grammar_id}__{suffix}{item_index:02d}"
                ids.append(item_id)
                shared_items.append(
                    _item(
                        item_id=item_id,
                        grammar_id=grammar_id,
                        learning_id=learning_id,
                        skill=skill,
                        role="assessment" if item_index == 4 else "practice",
                    )
                )
            skill_lanes[skill] = {"candidate_item_ids": ids}
        prerequisites = [] if index == 1 else [f"GRAMMAR_UNIT_{index - 1:02d}"]
        cp01_units.append({
            "learning_unit_id": learning_id,
            "grammar_unit_id": grammar_id,
            "sequence_index": index,
            "internal_stage": "A1" if index <= 18 else "A1_PLUS",
            "canonical_egp_row_ids": [f"EGP_{index:03d}"],
            "prerequisite_unit_ids": prerequisites,
            "skill_lanes": skill_lanes,
        })
        scenes = []
        if not (scene_gap and index == 24):
            scenes = [{
                "scene_candidate_id": f"SCENE_{index:02d}",
                "candidate_state": "AUTHORITY_BACKED_METADATA_READY",
            }]
            scene_count += 1
        cp04_units.append({
            "learning_unit_id": learning_id,
            "grammar_unit_id": grammar_id,
            "sequence_index": index,
            "internal_stage": "A1" if index <= 18 else "A1_PLUS",
            "canonical_egp_row_ids": [f"EGP_{index:03d}"],
            "candidate_counts": {"raz_content_candidate_count": 1},
            "scene_candidates": scenes,
        })
    cp01 = {
        "task_id": s02.cp01.TASK_ID,
        "scope": "A1_A1_PLUS_ONLY",
        "stop_reason": "NONE",
        "coverage_summary": {"learning_unit_count": 24},
        "learning_units": cp01_units,
    }
    cp04 = {
        "task_id": s02.cp04.TASK_ID,
        "scope": "A1_A1_PLUS_ONLY",
        "stop_reason": "NONE",
        "candidate_contract": {
            "course_container": "EXISTING_24_CANONICAL_UNITS_ONLY",
            "new_unit_creation_allowed": False,
            "private_source_read_performed": False,
        },
        "coverage_summary": {
            "raz_material_binding_candidate_count": 24,
            "scene_candidate_count": scene_count,
            "scene_authority_gap_unit_count": 24 - scene_count,
        },
        "learning_units": cp04_units,
    }
    m03 = {
        "task_id": s02.m03.TASK_ID,
        "scope": "A1_A1_PLUS_ONLY",
        "stop_reason": "NONE",
        "coverage_summary": {
            "learning_unit_count": 24,
            "shared_item_count": 384,
        },
        "shared_items": shared_items,
    }
    return cp01, cp04, m03


def test_full_population_admits_all_24_units_and_264_nonaudio_items() -> None:
    cp01, cp04, m03 = _fixtures()
    artifact = s09.build_full_admission(
        cp01_artifact=cp01,
        cp04_artifact=cp04,
        m03_artifact=m03,
    )
    summary = artifact["population_summary"]
    assert summary["populated_unit_count"] == 24
    assert summary["reading_item_count"] == 96
    assert summary["writing_item_count"] == 96
    assert summary["speaking_practice_card_count"] == 72
    assert summary["admitted_nonaudio_item_count"] == 264
    assert summary["runtime_lesson_count"] == 72
    assert summary["scene_authority_gap_unit_count"] == 1
    assert artifact["admitted_units"][1]["prerequisite_unit_ids"] == [
        "E4S_A1V1_UNIT:GRAMMAR_UNIT_01"
    ]
    assert artifact["admitted_units"][-1]["scene_population_status"] == (
        "SCENE_AUTHORITY_PENDING_NONBLOCKING_TEXT_MODE"
    )


def test_repository_cp01_grammar_prerequisite_resolves_to_learning_identity() -> None:
    cp01 = json.loads(
        (REPO_ROOT / "ulga/reports/a1fs_v1_cp01_existing_content_backfill.json").read_text(
            encoding="utf-8"
        )
    )
    units = s09._verify_cp01_with_resolved_prerequisites(cp01)
    assert units["GRAMMAR_BASIC_PREPOSITIONS_PLACE"]["prerequisite_unit_ids"] == [
        "E4S_A1V1_UNIT:GRAMMAR_ARTICLES_BASIC"
    ]


def test_missing_candidate_item_fails_closed() -> None:
    cp01, cp04, m03 = _fixtures()
    missing_id = cp01["learning_units"][10]["skill_lanes"]["writing"]["candidate_item_ids"][0]
    m03["shared_items"] = [row for row in m03["shared_items"] if row["shared_item_id"] != missing_id]
    m03["coverage_summary"]["shared_item_count"] = len(m03["shared_items"])
    with pytest.raises(s02.FirstUnitAdmissionError, match="m03_denominator_invalid"):
        s09.build_full_admission(cp01_artifact=cp01, cp04_artifact=cp04, m03_artifact=m03)


def test_prerequisite_bypass_is_rejected() -> None:
    cp01, cp04, m03 = _fixtures()
    cp01 = deepcopy(cp01)
    cp01["learning_units"][1]["prerequisite_unit_ids"] = [
        "E4S_A1V1_UNIT:GRAMMAR_UNIT_24"
    ]
    with pytest.raises(s09.PopulationError, match="canonical_prerequisite_order_invalid"):
        s09.build_full_admission(cp01_artifact=cp01, cp04_artifact=cp04, m03_artifact=m03)


def test_unknown_prerequisite_reference_is_rejected() -> None:
    cp01, cp04, m03 = _fixtures()
    cp01 = deepcopy(cp01)
    cp01["learning_units"][1]["prerequisite_unit_ids"] = ["GRAMMAR_NOT_CANONICAL"]
    with pytest.raises(
        s09.PopulationError,
        match="prerequisite_reference_unknown:GRAMMAR_UNIT_02:GRAMMAR_NOT_CANONICAL",
    ):
        s09.build_full_admission(cp01_artifact=cp01, cp04_artifact=cp04, m03_artifact=m03)


def test_semantic_duplicate_prerequisite_reference_is_rejected() -> None:
    cp01, cp04, m03 = _fixtures()
    cp01 = deepcopy(cp01)
    cp01["learning_units"][1]["prerequisite_unit_ids"] = [
        "GRAMMAR_UNIT_01",
        "E4S_A1V1_UNIT:GRAMMAR_UNIT_01",
    ]
    with pytest.raises(s09.PopulationError, match="prerequisite_semantic_duplicate"):
        s09.build_full_admission(cp01_artifact=cp01, cp04_artifact=cp04, m03_artifact=m03)


def test_consumer_compatibility_alias_supports_existing_s07_runtime_helper(monkeypatch) -> None:
    cp01, cp04, m03 = _fixtures()
    admission = s09.build_full_admission(
        cp01_artifact=cp01,
        cp04_artifact=cp04,
        m03_artifact=m03,
    )
    captured = {}

    def fake_build_consumer(compatible, _m03):
        captured["admission_summary"] = compatible["admission_summary"]
        return {
            "asset_records": [],
            "lesson_catalog": [],
            "counts": {"lesson_count": 72, "asset_record_count": 264},
            "s07_runtime_projection": {"admitted_unit_count": 24},
            "next_short_step": "old",
        }

    monkeypatch.setattr(s09.s07, "build_consumer", fake_build_consumer)
    consumer = s09.build_consumer(admission, m03)
    assert captured["admission_summary"] == admission["population_summary"]
    assert consumer["counts"]["lesson_count"] == 72
    assert consumer["counts"]["asset_record_count"] == 264
    assert consumer["s09_runtime_projection"]["admitted_unit_count"] == 24
