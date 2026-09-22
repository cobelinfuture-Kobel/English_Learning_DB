from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TASK_ID = "A1FS-V1-U05FAR1_Unit05FinalPracticeArchitectureRecomposition"
STATUS = "PASS_A1FS_V1_U05FAR1_FINAL_PRACTICE_ARCHITECTURE_RECOMPOSED"
NEXT_SHORT_STEP = "A1FS-V1-U05FAR2_CoverageDrivenPracticeSlotMaterialization"

REPO_ROOT = Path(__file__).resolve().parents[2]
ARCH_PATH = REPO_ROOT / "product/a1fs_v1_2_1/data/unit05_final_practice_architecture.json"
KET_S2_PATH = REPO_ROOT / "data/ket/ket_s2_semantic_task_profiles.json"
KET_S9_PATH = REPO_ROOT / "data/ket/ket_s9_level_adaptation_contract.json"
Q06_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u05_q06_sentence_assets.json"
CURRENT360_PATH = REPO_ROOT / "product/a1fs_v1_2_1/data/unit05_current360_360.json"
SPOKEN360_PATH = REPO_ROOT / "product/a1fs_v1_2_1/data/unit05_spoken360_360.json"
PATTERN360_PATH = REPO_ROOT / "product/a1fs_v1_2_1/data/unit05_pattern360_360.json"

EXPECTED_FRAMES = {
    "U05-BF-NP-AFF",
    "U05-BF-NP-NEG",
    "U05-BF-ADJ-AFF",
    "U05-BF-ADJ-NEG",
    "U05-BF-PLACE-AFF",
    "U05-BF-PLACE-NEG",
}
EXPECTED_STAGES = [
    "GUIDED",
    "REDUCED_SUPPORT",
    "INDEPENDENT",
    "UNSEEN_TRANSFER",
    "DELAYED_RETENTION",
]


class U05FAR1Error(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise U05FAR1Error(f"MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise U05FAR1Error(f"NOT_OBJECT:{path}")
    return value


def build_report() -> dict[str, Any]:
    arch = _load(ARCH_PATH)
    s2 = _load(KET_S2_PATH)
    s9 = _load(KET_S9_PATH)
    q06 = _load(Q06_PATH)
    current = _load(CURRENT360_PATH)
    spoken = _load(SPOKEN360_PATH)
    pattern = _load(PATTERN360_PATH)

    if arch.get("task_id") != TASK_ID or arch.get("status") != STATUS:
        raise U05FAR1Error("ARCH_ID_OR_STATUS_DRIFT")

    decision = arch["architecture_decision"]
    if decision["fixed_form_count_required"] is not False:
        raise U05FAR1Error("FIXED_FORM_COUNT_REINTRODUCED")
    if decision["fixed_questions_per_form_required"] is not False:
        raise U05FAR1Error("FIXED_QUESTION_COUNT_REINTRODUCED")
    if decision["fixed_total_question_cap_required"] is not False:
        raise U05FAR1Error("FIXED_TOTAL_CAP_REINTRODUCED")
    if decision["legacy_20x40_is_final_authority"] is not False:
        raise U05FAR1Error("LEGACY_20X40_REPROMOTED")

    progression = arch["progression_contract"]
    if progression["stages"] != EXPECTED_STAGES:
        raise U05FAR1Error("PROGRESSION_STAGE_DRIFT")
    if progression["native_a2_task_demand_required"] is not False:
        raise U05FAR1Error("A2_NATIVE_TASK_DEMAND_UNLOCKED")

    reader = arch["reader360_keep_contract"]
    if reader["current360_episode_count"] != 360:
        raise U05FAR1Error("CURRENT360_ARCH_COUNT_DRIFT")
    if reader["spoken360_episode_count"] != 360:
        raise U05FAR1Error("SPOKEN360_ARCH_COUNT_DRIFT")
    if reader["pattern360_episode_count"] != 360:
        raise U05FAR1Error("PATTERN360_ARCH_COUNT_DRIFT")
    if reader["learner_facing_reader_text_may_be_rewritten"] is not False:
        raise U05FAR1Error("READER_REWRITE_UNLOCKED")

    if len(current.get("episodes") or []) != 360:
        raise U05FAR1Error("CURRENT360_SOURCE_COUNT_DRIFT")
    if len(spoken.get("entries") or []) != 360:
        raise U05FAR1Error("SPOKEN360_SOURCE_COUNT_DRIFT")
    if len(pattern.get("entries") or []) != 360:
        raise U05FAR1Error("PATTERN360_SOURCE_COUNT_DRIFT")

    core = arch["core_grammar_practice"]
    frames = core["frame_requirements"]
    frame_ids = {row["frame_id"] for row in frames}
    if frame_ids != EXPECTED_FRAMES:
        raise U05FAR1Error(f"FRAME_SET_DRIFT:{sorted(frame_ids)}")
    frame_total = sum(int(row["minimum_task_count"]) for row in frames)
    if frame_total != 480 or core["minimum_total_task_count"] != 480:
        raise U05FAR1Error(f"CORE_TASK_FLOOR_DRIFT:{frame_total}")
    for row in frames:
        if sum(int(v) for v in row["stage_distribution"].values()) != int(row["minimum_task_count"]):
            raise U05FAR1Error(f"FRAME_STAGE_SUM_DRIFT:{row['frame_id']}")
        if list(row["stage_distribution"]) != EXPECTED_STAGES:
            raise U05FAR1Error(f"FRAME_STAGE_ORDER_DRIFT:{row['frame_id']}")

    q06_subjects = set(q06["coverage"]["subject_class_counts"])
    subject_floor = core["subject_class_floor"]
    if set(subject_floor["subject_classes"]) != q06_subjects or len(q06_subjects) != 9:
        raise U05FAR1Error("SUBJECT_CLASS_SET_DRIFT")
    if int(subject_floor["minimum_occurrences_per_subject_class"]) < 48:
        raise U05FAR1Error("SUBJECT_CLASS_FLOOR_TOO_LOW")

    q06_relations = set(q06["coverage"]["direct_static_place_relation_counts"])
    relation_floor = core["place_relation_floor"]
    if set(relation_floor["relations"]) != q06_relations or len(q06_relations) != 8:
        raise U05FAR1Error("PLACE_RELATION_SET_DRIFT")
    if int(relation_floor["minimum_occurrences_per_relation"]) < 24:
        raise U05FAR1Error("PLACE_RELATION_FLOOR_TOO_LOW")

    ket = arch["ket_adapted_practice"]
    families = list(ket["task_families"])
    source_profiles = list(s2["task_profiles"])
    if len(families) != 14 or ket["family_count"] != 14:
        raise U05FAR1Error("KET_FAMILY_COUNT_DRIFT")
    if [row["ket_profile_id"] for row in families] != [row["id"] for row in source_profiles]:
        raise U05FAR1Error("KET_PROFILE_ID_ORDER_DRIFT")
    if [row["task_family"] for row in families] != [row["task_family"] for row in source_profiles]:
        raise U05FAR1Error("KET_TASK_FAMILY_ORDER_DRIFT")
    for row in families:
        if int(row["minimum_task_count"]) < 48:
            raise U05FAR1Error(f"KET_FAMILY_FLOOR_TOO_LOW:{row['task_family']}")
        if sum(int(v) for v in row["stage_distribution"].values()) != int(row["minimum_task_count"]):
            raise U05FAR1Error(f"KET_STAGE_SUM_DRIFT:{row['task_family']}")
        if row["adaptation_level"] != "A1":
            raise U05FAR1Error(f"KET_ADAPTATION_LEVEL_DRIFT:{row['task_family']}")
        if row["adaptation_rule"] != s9["level_adaptation_policy"]["adaptation_rule"]:
            raise U05FAR1Error(f"KET_ADAPTATION_RULE_DRIFT:{row['task_family']}")

    ket_total = sum(int(row["minimum_task_count"]) for row in families)
    if ket_total != 672 or ket["minimum_total_task_count"] != 672:
        raise U05FAR1Error(f"KET_TASK_FLOOR_DRIFT:{ket_total}")
    if ket["native_a2_response_demand_locked"] is not True:
        raise U05FAR1Error("A2_NATIVE_RESPONSE_DEMAND_NOT_LOCKED")

    listening = arch["listening_audio_and_delayed_dictation"]
    if listening["full_dialogue_audio_target_count"] != 360:
        raise U05FAR1Error("FULL_AUDIO_TARGET_DRIFT")
    if listening["first_delayed_dictation"]["unique_episode_floor"] != 360:
        raise U05FAR1Error("FIRST_DICTATION_COVERAGE_DRIFT")
    if listening["second_spaced_dictation"]["unique_episode_floor"] < 120:
        raise U05FAR1Error("SECOND_DICTATION_COVERAGE_TOO_LOW")
    if listening["minimum_dictation_event_count"] < 480:
        raise U05FAR1Error("DICTATION_EVENT_FLOOR_TOO_LOW")
    if listening["transcript_visible_during_dictation"] is not False:
        raise U05FAR1Error("DICTATION_TRANSCRIPT_VISIBILITY_DRIFT")

    output = arch["productive_output_levels"]
    distribution = output["minimum_distribution_across_productive_ket_families"]
    if int(distribution["O1_ONE_SENTENCE"]) < 40:
        raise U05FAR1Error("OUTPUT_O1_FLOOR_TOO_LOW")
    if int(distribution["O2_TWO_CONNECTED_SENTENCES"]) < 72:
        raise U05FAR1Error("OUTPUT_O2_FLOOR_TOO_LOW")
    if int(distribution["O3_THREE_TO_FOUR_CONNECTED_SENTENCES"]) < 48:
        raise U05FAR1Error("OUTPUT_O3_FLOOR_TOO_LOW")
    if int(distribution["O4_A1_COMMUNICATIVE_OUTPUT"]) < 24:
        raise U05FAR1Error("OUTPUT_O4_FLOOR_TOO_LOW")
    if output["a2_25_word_message_unlocked"] is not False:
        raise U05FAR1Error("A2_25_WORD_MESSAGE_UNLOCKED")
    if output["a2_35_word_story_unlocked"] is not False:
        raise U05FAR1Error("A2_35_WORD_STORY_UNLOCKED")
    if output["past_narrative_requirement_unlocked"] is not False:
        raise U05FAR1Error("PAST_NARRATIVE_UNLOCKED")

    derived = arch["derived_capacity_summary"]
    expected_total = frame_total + ket_total + int(listening["minimum_dictation_event_count"])
    if expected_total != 1632 or derived["minimum_total_practice_events"] != 1632:
        raise U05FAR1Error(f"TOTAL_PRACTICE_FLOOR_DRIFT:{expected_total}")
    if derived["reader_study_episodes_not_counted_as_questions"] != 360:
        raise U05FAR1Error("READER_STUDY_COUNT_DRIFT")
    if derived["reader_mode_touchpoints_not_counted_as_questions"] != 1080:
        raise U05FAR1Error("READER_TOUCHPOINT_COUNT_DRIFT")

    gates = arch["coverage_admission_gates"]
    if gates["total_practice_event_floor"] != 1632:
        raise U05FAR1Error("ADMISSION_TOTAL_FLOOR_DRIFT")
    if gates["admission_requires_all_gates"] is not True:
        raise U05FAR1Error("ALL_GATES_NOT_REQUIRED")

    safety = arch["scope_safety"]
    if any([
        safety["pdf_materialized"],
        safety["learner_facing_questionbank_materialized"],
        safety["reader360_text_modified"],
        safety["a2_grammar_unlocked"],
        safety["a2_native_ket_response_floor_unlocked"],
        safety["legacy_q10_deleted"],
        safety["legacy_q10r1_deleted"],
        safety["legacy_p05_deleted"],
        safety["other_units_modified"],
    ]):
        raise U05FAR1Error("SCOPE_SAFETY_DRIFT")

    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "core_grammar_task_floor": frame_total,
        "ket_family_count": len(families),
        "ket_adapted_task_floor": ket_total,
        "dictation_event_floor": int(listening["minimum_dictation_event_count"]),
        "minimum_total_practice_events": expected_total,
        "reader_study_episode_count": int(derived["reader_study_episodes_not_counted_as_questions"]),
        "reader_mode_touchpoint_floor": int(derived["reader_mode_touchpoints_not_counted_as_questions"]),
        "fixed_form_count": False,
        "fixed_total_question_cap": False,
        "a2_native_task_demand_unlocked": False,
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    print(json.dumps(build_report(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
