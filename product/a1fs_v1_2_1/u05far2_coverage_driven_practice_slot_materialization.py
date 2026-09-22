from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "FAR2 is metadata-only practice-slot materialization. Python may allocate stable "
    "slot identities, Reader360 references, coverage dimensions, stages, retention "
    "links, and practice-set membership. It may not generate learner-facing prompts, "
    "questions, options, answers, transcripts, or rewrite Reader360 English."
)

TASK_ID = "A1FS-V1-U05FAR2_CoverageDrivenPracticeSlotMaterialization"
STATUS = "PASS_A1FS_V1_U05FAR2_COVERAGE_DRIVEN_PRACTICE_SLOTS_MATERIALIZED"
NEXT_SHORT_STEP = "A1FS-V1-U05FAR3_LearnerFacingPracticeMaterializationContract"

REPO_ROOT = Path(__file__).resolve().parents[2]
FAR1_PATH = REPO_ROOT / "product/a1fs_v1_2_1/data/unit05_final_practice_architecture.json"
FAR2_PATH = REPO_ROOT / "product/a1fs_v1_2_1/data/unit05_coverage_driven_practice_slots.json"

EXPECTED_STAGES = [
    "GUIDED",
    "REDUCED_SUPPORT",
    "INDEPENDENT",
    "UNSEEN_TRANSFER",
    "DELAYED_RETENTION",
]
FORBIDDEN_LEARNER_KEYS = {
    "prompt",
    "question",
    "question_text",
    "stem",
    "options",
    "answer",
    "answer_key",
    "transcript",
    "learner_text",
    "instruction_text",
}


class U05FAR2Error(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise U05FAR2Error(f"MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise U05FAR2Error(f"NOT_OBJECT:{path}")
    return value


def _find_forbidden_keys(value: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_LEARNER_KEYS:
                hits.append(f"{path}.{key}")
            hits.extend(_find_forbidden_keys(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(_find_forbidden_keys(child, f"{path}[{index}]"))
    return hits


def _counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(Counter(str(row.get(key)) for row in rows))


def build_report() -> dict[str, Any]:
    far1 = _load(FAR1_PATH)
    far2 = _load(FAR2_PATH)

    if far2.get("task_id") != TASK_ID or far2.get("status") != STATUS:
        raise U05FAR2Error("TASK_OR_STATUS_DRIFT")
    if far2.get("source_architecture_ref") != "product/a1fs_v1_2_1/data/unit05_final_practice_architecture.json":
        raise U05FAR2Error("FAR1_SOURCE_REF_DRIFT")

    contract = far2["materialization_contract"]
    expected = far1["derived_capacity_summary"]
    if contract["total_practice_slot_count"] != expected["minimum_total_practice_events"]:
        raise U05FAR2Error("TOTAL_PRACTICE_SLOT_COUNT_DRIFT")
    if contract["core_grammar_slot_count"] != expected["core_grammar_tasks"]:
        raise U05FAR2Error("CORE_SLOT_COUNT_DRIFT")
    if contract["ket_adapted_slot_count"] != expected["ket_adapted_tasks"]:
        raise U05FAR2Error("KET_SLOT_COUNT_DRIFT")
    if contract["delayed_dictation_slot_count"] != expected["delayed_dictation_events"]:
        raise U05FAR2Error("DICTATION_SLOT_COUNT_DRIFT")
    if contract["reader_study_slot_count"] != 360:
        raise U05FAR2Error("READER_STUDY_SLOT_COUNT_DRIFT")
    if contract["reader_mode_touchpoint_count"] != 1080:
        raise U05FAR2Error("READER_TOUCHPOINT_COUNT_DRIFT")
    if contract["learner_facing_question_text_materialized"] is not False:
        raise U05FAR2Error("LEARNER_QUESTION_TEXT_MATERIALIZED")
    if contract["answer_key_materialized"] is not False:
        raise U05FAR2Error("ANSWER_KEY_MATERIALIZED")
    if contract["pdf_materialized"] is not False:
        raise U05FAR2Error("PDF_MATERIALIZED")
    if contract["fixed_form_count"] is not False:
        raise U05FAR2Error("FIXED_FORM_COUNT_REINTRODUCED")
    if contract["fixed_total_question_cap"] is not False:
        raise U05FAR2Error("FIXED_TOTAL_CAP_REINTRODUCED")

    core = list(far2["core_grammar_slots"])
    ket = list(far2["ket_adapted_slots"])
    dictation = list(far2["delayed_dictation_slots"])
    reader = list(far2["reader_study_slots"])
    sets = list(far2["practice_sets"])
    read_sets = list(far2["reader_study_sets"])
    all_practice = core + ket + dictation

    if len(core) != 480 or len(ket) != 672 or len(dictation) != 480:
        raise U05FAR2Error("PRACTICE_DENOMINATOR_DRIFT")
    if len(all_practice) != 1632:
        raise U05FAR2Error("TOTAL_DENOMINATOR_DRIFT")
    if len({row["slot_id"] for row in all_practice}) != 1632:
        raise U05FAR2Error("PRACTICE_SLOT_ID_COLLISION")
    if len(reader) != 360 or len({row["study_slot_id"] for row in reader}) != 360:
        raise U05FAR2Error("READER_STUDY_ID_DRIFT")
    if len(sets) != 97 or len({row["practice_set_id"] for row in sets}) != 97:
        raise U05FAR2Error("PRACTICE_SET_COUNT_DRIFT")
    if len(read_sets) != 15 or len({row["reader_study_set_id"] for row in read_sets}) != 15:
        raise U05FAR2Error("READER_SET_COUNT_DRIFT")

    far1_frames = {
        row["frame_id"]: int(row["minimum_task_count"])
        for row in far1["core_grammar_practice"]["frame_requirements"]
    }
    core_frame_counts = Counter(row["frame_id"] for row in core)
    if dict(core_frame_counts) != far1_frames:
        raise U05FAR2Error(f"CORE_FRAME_COUNTS_DRIFT:{dict(core_frame_counts)}")

    far1_frame_stage = {
        (row["frame_id"], stage): int(count)
        for row in far1["core_grammar_practice"]["frame_requirements"]
        for stage, count in row["stage_distribution"].items()
    }
    for key, expected_count in far1_frame_stage.items():
        frame_id, stage = key
        actual = sum(1 for row in core if row["frame_id"] == frame_id and row["stage"] == stage)
        if actual != expected_count:
            raise U05FAR2Error(f"CORE_FRAME_STAGE_DRIFT:{frame_id}:{stage}:{actual}")

    subject_counts = Counter(row["subject_class"] for row in core)
    if len(subject_counts) != 9 or min(subject_counts.values()) < 48:
        raise U05FAR2Error(f"SUBJECT_CLASS_FLOOR_FAILURE:{dict(subject_counts)}")
    place_rows = [row for row in core if row.get("place_relation")]
    place_counts = Counter(row["place_relation"] for row in place_rows)
    if len(place_counts) != 8 or set(place_counts.values()) != {24}:
        raise U05FAR2Error(f"PLACE_RELATION_FLOOR_FAILURE:{dict(place_counts)}")

    for frame in far1["core_grammar_practice"]["frame_requirements"]:
        rows = [row for row in core if row["frame_id"] == frame["frame_id"]]
        nonret = [row for row in rows if row["stage"] != "DELAYED_RETENTION"]
        if len({row["episode_id"] for row in nonret}) != len(nonret):
            raise U05FAR2Error(f"CORE_NONRETENTION_EPISODE_REUSE:{frame['frame_id']}")
        independents = {row["slot_id"]: row for row in rows if row["stage"] == "INDEPENDENT"}
        for row in rows:
            if row["stage"] == "DELAYED_RETENTION":
                src = row.get("retention_source_slot_id")
                if src not in independents:
                    raise U05FAR2Error(f"CORE_RETENTION_SOURCE_INVALID:{row['slot_id']}")
                if row["episode_id"] != independents[src]["episode_id"]:
                    raise U05FAR2Error(f"CORE_RETENTION_EPISODE_DRIFT:{row['slot_id']}")

    far1_ket = {
        row["task_family"]: row
        for row in far1["ket_adapted_practice"]["task_families"]
    }
    ket_family_counts = Counter(row["task_family"] for row in ket)
    if set(ket_family_counts) != set(far1_ket):
        raise U05FAR2Error("KET_FAMILY_SET_DRIFT")
    if set(ket_family_counts.values()) != {48}:
        raise U05FAR2Error(f"KET_FAMILY_COUNT_DRIFT:{dict(ket_family_counts)}")

    for family, spec in far1_ket.items():
        rows = [row for row in ket if row["task_family"] == family]
        for stage, expected_count in spec["stage_distribution"].items():
            actual = sum(1 for row in rows if row["stage"] == stage)
            if actual != int(expected_count):
                raise U05FAR2Error(f"KET_STAGE_DRIFT:{family}:{stage}:{actual}")
        nonret = [row for row in rows if row["stage"] != "DELAYED_RETENTION"]
        if len({row["episode_id"] for row in nonret}) != len(nonret):
            raise U05FAR2Error(f"KET_NONRETENTION_EPISODE_REUSE:{family}")
        independents = {row["slot_id"]: row for row in rows if row["stage"] == "INDEPENDENT"}
        for row in rows:
            if row["stage"] == "DELAYED_RETENTION":
                src = row.get("retention_source_slot_id")
                if src not in independents:
                    raise U05FAR2Error(f"KET_RETENTION_SOURCE_INVALID:{row['slot_id']}")
                if row["episode_id"] != independents[src]["episode_id"]:
                    raise U05FAR2Error(f"KET_RETENTION_EPISODE_DRIFT:{row['slot_id']}")

    output_counts = Counter(row["output_level"] for row in ket if row.get("output_level"))
    expected_output = far1["productive_output_levels"]["minimum_distribution_across_productive_ket_families"]
    for level, floor in expected_output.items():
        if output_counts[level] != int(floor):
            raise U05FAR2Error(f"OUTPUT_LEVEL_COUNT_DRIFT:{level}:{output_counts[level]}")

    d1 = [row for row in dictation if row["dictation_pass"] == "D1"]
    d2 = [row for row in dictation if row["dictation_pass"] == "D2"]
    if len(d1) != 360 or len({row["episode_id"] for row in d1}) != 360:
        raise U05FAR2Error("DICTATION_D1_COVERAGE_DRIFT")
    if len(d2) != 120 or len({row["episode_id"] for row in d2}) != 120:
        raise U05FAR2Error("DICTATION_D2_COVERAGE_DRIFT")
    d1_by_id = {row["slot_id"]: row for row in d1}
    for row in d2:
        src = row["retention_source_slot_id"]
        if src not in d1_by_id:
            raise U05FAR2Error(f"DICTATION_D2_SOURCE_INVALID:{row['slot_id']}")
        if row["episode_id"] != d1_by_id[src]["episode_id"]:
            raise U05FAR2Error(f"DICTATION_D2_EPISODE_DRIFT:{row['slot_id']}")
        if row["transcript_visible_during_attempt"] is not False:
            raise U05FAR2Error(f"DICTATION_TRANSCRIPT_VISIBLE:{row['slot_id']}")
        if row["audio_asset_state"] != "PENDING_AUDIO_MATERIALIZATION":
            raise U05FAR2Error(f"DICTATION_AUDIO_STATE_DRIFT:{row['slot_id']}")

    expected_eps = {f"U05-NEB-E{i:03d}" for i in range(1, 361)}
    if {row["episode_id"] for row in reader} != expected_eps:
        raise U05FAR2Error("READER_STUDY_EPISODE_COVERAGE_DRIFT")
    for row in reader:
        suffix = row["episode_id"].rsplit("E", 1)[1]
        if row["current360_ref"] != row["episode_id"]:
            raise U05FAR2Error(f"CURRENT_REF_DRIFT:{row['study_slot_id']}")
        if row["spoken360_ref"] != f"U05-SPOKEN360-E{suffix}":
            raise U05FAR2Error(f"SPOKEN_REF_DRIFT:{row['study_slot_id']}")
        if row["pattern360_ref"] != f"U05-PATTERN360-E{suffix}":
            raise U05FAR2Error(f"PATTERN_REF_DRIFT:{row['study_slot_id']}")
        if row["counted_in_practice_event_floor"] is not False:
            raise U05FAR2Error(f"READER_STUDY_COUNTING_DRIFT:{row['study_slot_id']}")

    set_membership = Counter(row["practice_set_id"] for row in all_practice)
    set_ids = {row["practice_set_id"] for row in sets}
    if set(set_membership) != set_ids:
        raise U05FAR2Error("PRACTICE_SET_MEMBERSHIP_DRIFT")
    for pset in sets:
        count = set_membership[pset["practice_set_id"]]
        if count != int(pset["slot_count"]) or count != len(pset["slot_ids"]):
            raise U05FAR2Error(f"PRACTICE_SET_SIZE_DRIFT:{pset['practice_set_id']}")
        if pset["set_kind"] == "CORE_GRAMMAR" and not (18 <= count <= 24):
            raise U05FAR2Error(f"CORE_SET_SIZE_OUTSIDE_POLICY:{pset['practice_set_id']}:{count}")
        if pset["set_kind"] == "KET_PRODUCTIVE" and not (8 <= count <= 12):
            raise U05FAR2Error(f"PRODUCTIVE_SET_SIZE_OUTSIDE_POLICY:{pset['practice_set_id']}:{count}")
        if pset["set_kind"] == "KET_RECEPTIVE_OR_CONTROLLED" and not (18 <= count <= 24):
            raise U05FAR2Error(f"RECEPTIVE_SET_SIZE_OUTSIDE_POLICY:{pset['practice_set_id']}:{count}")
        if pset["set_kind"] == "DELAYED_DICTATION" and not (8 <= count <= 12):
            raise U05FAR2Error(f"DICTATION_SET_SIZE_OUTSIDE_POLICY:{pset['practice_set_id']}:{count}")

    forbidden = _find_forbidden_keys(far2)
    if forbidden:
        raise U05FAR2Error(f"LEARNER_FACING_KEYS_FOUND:{forbidden[:20]}")

    safety = far2["scope_safety"]
    if any([
        safety["reader360_text_modified"],
        safety["learner_facing_question_text_generated"],
        safety["python_generated_or_rewrote_learner_facing_english"],
        safety["a2_grammar_unlocked"],
        safety["a2_native_ket_response_floor_unlocked"],
        safety["pdf_materialized"],
        safety["other_units_modified"],
    ]):
        raise U05FAR2Error("SCOPE_SAFETY_DRIFT")

    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "practice_slot_count": len(all_practice),
        "core_grammar_slot_count": len(core),
        "ket_adapted_slot_count": len(ket),
        "delayed_dictation_slot_count": len(dictation),
        "practice_set_count": len(sets),
        "reader_study_slot_count": len(reader),
        "reader_study_set_count": len(read_sets),
        "reader_mode_touchpoint_count": len(reader) * 3,
        "subject_class_minimum": min(subject_counts.values()),
        "place_relation_minimum": min(place_counts.values()),
        "ket_family_minimum": min(ket_family_counts.values()),
        "dictation_d1_episode_count": len({row["episode_id"] for row in d1}),
        "dictation_d2_episode_count": len({row["episode_id"] for row in d2}),
        "learner_facing_question_text_materialized": False,
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    print(json.dumps(build_report(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
