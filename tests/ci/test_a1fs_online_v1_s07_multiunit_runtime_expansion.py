from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from ulga.builders import build_a1_a1plus_shared_item_contract as m03
from ulga.builders import build_a1fs_online_v1_s02_first_nonaudio_unit_admission as s02
from ulga.builders import build_a1fs_online_v1_s03_unified_learner_runtime as s03
from ulga.builders import build_a1fs_online_v1_s04_private_online_learner_workbench_execution as s04
from ulga.builders import build_a1fs_online_v1_s05_private_learner_identity_progress_persistence as s05
from ulga.builders import build_a1fs_online_v1_s06_private_e2e_progress_readback as s06
from ulga.builders import build_a1fs_online_v1_s07_multiunit_runtime_expansion as s07
from ulga.validators.validate_a1fs_online_v1_s07_multiunit_runtime_expansion import validate_outputs

SKILLS = ("reading", "writing", "listening", "speaking")
MODES = (
    "DETERMINISTIC_OPTION",
    "DETERMINISTIC_SEQUENCE",
    "DETERMINISTIC_NORMALIZED_TEXT",
    "FEATURE_RUBRIC_CANDIDATE",
)


def _cp01() -> dict:
    units = []
    for index in range(1, 25):
        grammar_id = f"GRAMMAR_TEST_{index:02d}"
        learning_id = f"A1FS_UNIT_{index:02d}"
        units.append({
            "learning_unit_id": learning_id,
            "grammar_unit_id": grammar_id,
            "sequence_index": index,
            "internal_stage": "A1" if index <= 12 else "A1_PLUS_EXTENSION",
            "canonical_egp_row_ids": [f"EGP_TEST_{index:03d}"],
            "prerequisite_unit_ids": [] if index == 1 else [f"A1FS_UNIT_{index - 1:02d}"],
        })
    return {
        "task_id": "A1FS-V1-CP01_Existing24UnitCurriculumContractAndContentBackfill",
        "program_id": "A1FS-V1_A1A1PlusFourSkillUnitCurriculumPlanningAndPopulation",
        "schema_version": "a1fs.v1.cp01.existing_content_backfill.v1",
        "scope": "A1_A1_PLUS_ONLY",
        "coverage_summary": {"learning_unit_count": 24},
        "learning_units": units,
        "stop_reason": "NONE",
    }


def _item(unit: dict, skill: str, ordinal: int) -> dict:
    grammar_id = unit["grammar_unit_id"]
    learning_id = unit["learning_unit_id"]
    mode = MODES[ordinal - 1] if skill in {"reading", "writing"} else "FEATURE_RUBRIC_CANDIDATE"
    shared_id = f"E4S_A1V1_ITEM:{grammar_id}:{skill}:{ordinal}"
    answer: dict = {
        "answer_mode": mode,
        "answer_status": "CANDIDATE_CONTRACT_AVAILABLE",
    }
    response: dict = {"response_mode": "short_text", "learner_input_required": True}
    evidence = ["learner_text_response"]
    if mode == "DETERMINISTIC_OPTION":
        answer.update(
            answer_key={"accepted_texts": [f"{grammar_id}-choice-{ordinal}"]},
            options=[f"{grammar_id}-choice-{ordinal}", "other"],
        )
        response.update(response_mode="select_one", options=list(answer["options"]))
    elif mode == "DETERMINISTIC_SEQUENCE":
        answer["correct_token_sequence"] = ["a", f"{grammar_id.lower()}-{ordinal}"]
        response.update(
            response_mode="ordered_tokens",
            token_sequence=list(answer["correct_token_sequence"]),
        )
    elif mode == "DETERMINISTIC_NORMALIZED_TEXT":
        answer["answer_key"] = {"accepted_texts": [f"{grammar_id} answer {ordinal}."]}
    else:
        evidence = ["grammar_feature_evaluation", "teacher_review_required"]
    return {
        "shared_item_id": shared_id,
        "source_item_id": f"SRC:{shared_id}",
        "schema_version": m03.SCHEMA_VERSION,
        "learning_unit_id": learning_id,
        "grammar_unit_id": grammar_id,
        "official_cefr_level": "A1",
        "internal_stage": unit["internal_stage"],
        "skill": skill,
        "item_role": "assessment" if ordinal == 4 else "practice",
        "evidence_dimension": "controlled_practice",
        "task_type": "guided_response",
        "prompt_contract": {
            "prompt_text": f"Complete {grammar_id} {skill} item {ordinal}.",
            "prompt_status": "PROJECT_AUTHORED_CANDIDATE",
        },
        "response_contract": response,
        "answer_contract": answer,
        "scoring_contract": {
            "scoring_mode": mode,
            "deterministic_candidate": mode != "FEATURE_RUBRIC_CANDIDATE",
            "real_skill_scoring_ready": mode != "FEATURE_RUBRIC_CANDIDATE",
            "human_review_fallback": mode == "FEATURE_RUBRIC_CANDIDATE",
            "required_evidence": evidence,
        },
        "media_contract": {
            "text_status": "AVAILABLE",
            "audio_required": skill in {"listening", "speaking"},
            "audio_status": "NOT_IMPLEMENTED" if skill in {"listening", "speaking"} else "NOT_REQUIRED",
            "transcript_required": skill in {"listening", "speaking"},
            "transcript_status": "NOT_COLLECTED" if skill in {"listening", "speaking"} else "NOT_REQUIRED",
            "learner_capture_required": skill == "speaking",
            "learner_capture_status": "NOT_IMPLEMENTED" if skill == "speaking" else "NOT_REQUIRED",
        },
        "content_binding": {
            "grammar_focus": [grammar_id],
            "canonical_egp_row_ids": list(unit["canonical_egp_row_ids"]),
            "coverage_mode": "DIRECT_CANONICAL_ROWS",
        },
        "source_trace": {"source_kind": "TEST", "raw_external_source_text_copied": False},
        "readiness": {
            "shared_item_contract_complete": True,
            "answer_contract_complete": True,
            "scoring_contract_complete": True,
            "media_contract_complete": True,
        },
        "claim_boundaries": {
            "learner_mastery_claimed": False,
            "a2_a2plus_in_scope": False,
        },
    }


def _m03(curriculum: dict) -> dict:
    items = [
        _item(unit, skill, ordinal)
        for unit in curriculum["learning_units"]
        for skill in SKILLS
        for ordinal in range(1, 5)
    ]
    assert len(items) == 384
    return {
        "task_id": m03.TASK_ID,
        "epic_id": m03.EPIC_ID,
        "artifact_id": m03.ARTIFACT_ID,
        "schema_version": m03.SCHEMA_VERSION,
        "scope": "A1_A1_PLUS_ONLY",
        "coverage_summary": {
            "learning_unit_count": 24,
            "shared_item_count": 384,
            "items_per_unit": 16,
        },
        "shared_items": items,
        "stop_reason": "NONE",
    }


def _cp04(curriculum: dict, shared: dict, *, unavailable_sequence: int | None = None) -> dict:
    by_grammar: dict[str, list[dict]] = {}
    for item in shared["shared_items"]:
        by_grammar.setdefault(item["grammar_unit_id"], []).append(item)
    units = []
    for source in curriculum["learning_units"]:
        exercises = []
        for skill in ("reading", "writing"):
            if source["sequence_index"] == unavailable_sequence and skill == "writing":
                continue
            for item in by_grammar[source["grammar_unit_id"]]:
                if item["skill"] != skill:
                    continue
                exercises.append({
                    "exercise_candidate_id": f"EX:{item['shared_item_id']}",
                    "content_candidate_id": f"CONTENT:{item['shared_item_id']}",
                    "source_kind": "M11B_REVIEWED_SHARED_ITEM",
                    "source_ref": item["shared_item_id"],
                    "target_skill_lanes": [skill],
                    "candidate_mode": "REUSE_EXISTING_REVIEWED_EXERCISE",
                    "candidate_state": "READY_FOR_PRIVATE_POPULATION",
                    "new_content_authoring_required": False,
                })
        units.append({
            "learning_unit_id": source["learning_unit_id"],
            "grammar_unit_id": source["grammar_unit_id"],
            "sequence_index": source["sequence_index"],
            "internal_stage": source["internal_stage"],
            "canonical_egp_row_ids": list(source["canonical_egp_row_ids"]),
            "content_candidates": [],
            "exercise_candidates": exercises,
            "scene_candidates": [{
                "scene_candidate_id": f"SCENE:{source['grammar_unit_id']}",
                "candidate_state": "AUTHORITY_BACKED_METADATA_READY",
            }],
            "candidate_counts": {},
            "candidate_population_status": "CONTENT_EXERCISE_AND_SCENE_CANDIDATES_AVAILABLE",
        })
    return {
        "task_id": "A1FS-V1-CP04_UnifiedContentExerciseAndSceneCandidateBuild",
        "program_id": "A1FS-V1",
        "schema_version": "a1fs.v1.cp04.unified_content_exercise_scene_candidates.v1",
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
    }


def _sources(*, unavailable_sequence: int | None = None) -> tuple[dict, dict, dict, dict]:
    curriculum = _cp01()
    shared = _m03(curriculum)
    candidates = _cp04(curriculum, shared, unavailable_sequence=unavailable_sequence)
    first = s02.build_artifact(curriculum, candidates, shared)
    return curriculum, candidates, shared, first


def _write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _pipeline(tmp_path: Path) -> dict:
    curriculum, candidates, shared, first = _sources(unavailable_sequence=5)
    cp01_path = _write(tmp_path / "sources/cp01.json", curriculum)
    cp04_path = _write(tmp_path / "sources/cp04.json", candidates)
    m03_path = _write(tmp_path / "sources/m03.json", shared)
    s02_path = _write(tmp_path / "sources/s02.private.json", first)

    s03_root = tmp_path / "s03"
    s03_receipt, _ = s03.materialize_runtime(
        s02_artifact=first,
        m03_artifact=shared,
        output_root=s03_root,
    )
    s03_path = _write(s03_root / "unified_learner_runtime.private.json", s03_receipt)

    s04_root = tmp_path / "s04"
    s04_receipt, _ = s04.materialize(s03_receipt_path=s03_path, output_root=s04_root)
    s04_path = _write(s04_root / "private_online_workbench_execution.private.json", s04_receipt)

    s05_root = tmp_path / "s05"
    s05_receipt, _ = s05.materialize(s04_receipt_path=s04_path, output_root=s05_root)
    s05_path = _write(s05_root / "private_learner_identity_progress_persistence.private.json", s05_receipt)

    outputs = s05_receipt["persistent_outputs"]
    app = s05.PersistentWorkbenchApplication(
        database_path=Path(outputs["database_path"]),
        bundles=s04._load_bundles(Path(outputs["ui_root"])),
    )
    active = app.start_session({
        "skill": "reading",
        "learner_id": s05.DEFAULT_LEARNER_ID,
        "session_id": "S07_EXISTING_ACTIVE_SESSION",
        "at": "2026-01-07T00:00:00Z",
    })
    assert active["session_state"] == "ACTIVE"

    s06_root = tmp_path / "s06"
    s06_receipt, _ = s06.materialize(s05_receipt_path=s05_path, output_root=s06_root)
    s06_path = _write(s06_root / "private_e2e_progress_readback.private.json", s06_receipt)

    database = Path(outputs["database_path"])
    before = s07.progress_state_digest(database)
    s07_root = tmp_path / "s07"
    receipt, safe = s07.materialize(
        cp01_path=cp01_path,
        cp04_path=cp04_path,
        m03_path=m03_path,
        s02_path=s02_path,
        s05_path=s05_path,
        s06_path=s06_path,
        output_root=s07_root,
    )
    report = validate_outputs(
        receipt=receipt,
        safe_report=safe,
        output_root=s07_root,
        cp01_path=cp01_path,
        cp04_path=cp04_path,
        m03_path=m03_path,
        s02_path=s02_path,
        s05_path=s05_path,
        s06_path=s06_path,
    )
    assert report["error_count"] == 0, report["errors"]
    return {
        "receipt": receipt,
        "safe": safe,
        "database": database,
        "before": before,
        "after": s07.progress_state_digest(database),
    }


def test_admits_full_content_ready_prerequisite_closure_and_preserves_first_unit() -> None:
    curriculum, candidates, shared, first = _sources()
    admission = s07.build_admission(
        cp01_artifact=curriculum,
        cp04_artifact=candidates,
        m03_artifact=shared,
        s02_artifact=first,
    )
    assert admission["admission_summary"]["admitted_unit_count"] == 24
    assert admission["admission_summary"]["runtime_lesson_count"] == 72
    assert admission["admission_summary"]["admitted_nonaudio_item_count"] == 264
    assert admission["closure_proof"] == {
        "first_unit_identity_preserved": True,
        "prerequisite_closure_valid": True,
        "canonical_sequence_monotonic": True,
    }
    selected = first["selected_unit"]
    expanded = admission["admitted_units"][0]
    assert expanded["learning_unit_id"] == selected["learning_unit_id"]
    for skill in s07.SKILL_ORDER:
        assert expanded["admitted_lanes"][skill]["item_ids"] == selected["admitted_lanes"][skill]["item_ids"]


def test_content_gap_blocks_its_downstream_prerequisite_chain_without_bypass() -> None:
    curriculum, candidates, shared, first = _sources(unavailable_sequence=5)
    admission = s07.build_admission(
        cp01_artifact=curriculum,
        cp04_artifact=candidates,
        m03_artifact=shared,
        s02_artifact=first,
    )
    assert [row["sequence_index"] for row in admission["admitted_units"]] == [1, 2, 3, 4]
    assert admission["admission_summary"]["content_unavailable_unit_count"] == 1
    assert admission["admission_summary"]["prerequisite_blocked_unit_count"] == 19


@pytest.fixture(scope="module")
def full_pipeline(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return _pipeline(tmp_path_factory.mktemp("s07-full-pipeline"))


def test_full_multiunit_migration_preserves_existing_progress_and_runs_new_unit_canary(full_pipeline: dict) -> None:
    result = full_pipeline
    receipt = result["receipt"]
    assert result["before"] == result["after"]
    assert receipt["admission_summary"]["admitted_unit_count"] == 4
    assert receipt["runtime_summary"] == {
        "expanded_unit_count": 4,
        "expanded_lesson_count": 12,
        "expanded_asset_count": 44,
        "m5_renderer_bundle_count": 12,
        "m5_rendered_asset_count": 44,
        "m6_response_contract_count": 44,
        "m6_capture_enabled_contract_count": 32,
        "speaking_capture_enabled_count": 0,
        "listening_runtime_item_count": 0,
        "audio_runtime_asset_count": 0,
    }
    assert receipt["migration_summary"]["production_progress_preserved"] is True
    assert receipt["new_unit_runtime_canary"]["newly_admitted_unit_runtime_canary"] is True
    with sqlite3.connect(result["database"]) as connection:
        row = connection.execute(
            "SELECT session_state FROM learning_sessions WHERE session_id='S07_EXISTING_ACTIVE_SESSION'"
        ).fetchone()
        assert row == ("ACTIVE",)


def test_multiunit_bootstrap_uses_canonical_order_and_safe_report_has_no_private_content(full_pipeline: dict) -> None:
    result = full_pipeline
    receipt = result["receipt"]
    outputs = receipt["runtime_outputs"]
    bundles, sequence = s07._load_bundle_index(Path(outputs["bundle_index_path"]))
    app = s07.MultiUnitWorkbenchApplication(
        database_path=Path(outputs["database_path"]),
        bundles=bundles,
        sequence_by_grammar=sequence,
    )
    bootstrap = app.bootstrap()
    assert [unit["sequence_index"] for unit in bootstrap["units"]] == [1, 2, 3, 4]
    assert all([lane["skill"] for lane in unit["lanes"]] == ["READING", "WRITING", "SPEAKING"] for unit in bootstrap["units"])
    rendered = json.dumps(result["safe"], ensure_ascii=False)
    for token in (
        s05.DEFAULT_LEARNER_ID,
        s07.CANARY_LEARNER_ID,
        "learner_id",
        "database_path",
        "asset_key",
        "accepted_texts",
        "answer_contract",
        "learner_payload",
    ):
        assert token not in rendered
    with pytest.raises(s07.MultiUnitExpansionError, match="non_loopback_host_forbidden"):
        s07.MultiUnitWorkbenchServer(("0.0.0.0", 0), app, Path(outputs["static_root"]))
