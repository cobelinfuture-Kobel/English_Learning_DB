from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "FAR4 is a production preflight and pilot-slot selector. It may inspect FAR2/FAR3 "
    "metadata, classify asset prerequisites, and select representative slot identities. "
    "It does not author learner-facing English, answers, audio, visuals, or PDFs."
)

TASK_ID = "A1FS-V1-U05FAR4_GPT56LearnerFacingPracticeMaterializationPreflight"
STATUS = "PASS_A1FS_V1_U05FAR4_GPT56_LEARNER_FACING_PRACTICE_PREFLIGHT"
NEXT_SHORT_STEP = "A1FS-V1-U05FAR5_GPT56LearnerFacingPracticePilot46"

REPO_ROOT = Path(__file__).resolve().parents[2]
FAR2_PATH = REPO_ROOT / "product/a1fs_v1_2_1/data/unit05_coverage_driven_practice_slots.json"
FAR3_PATH = REPO_ROOT / "product/a1fs_v1_2_1/data/unit05_learner_facing_practice_materialization_contract.json"
FAR4_PATH = REPO_ROOT / "product/a1fs_v1_2_1/data/unit05_gpt56_practice_materialization_preflight.json"

EXPECTED_CORE_FRAMES = {
    "U05-BF-NP-AFF",
    "U05-BF-NP-NEG",
    "U05-BF-ADJ-AFF",
    "U05-BF-ADJ-NEG",
    "U05-BF-PLACE-AFF",
    "U05-BF-PLACE-NEG",
}
EXPECTED_OUTPUT_LEVELS = {
    "O1_ONE_SENTENCE",
    "O2_TWO_CONNECTED_SENTENCES",
    "O3_THREE_TO_FOUR_CONNECTED_SENTENCES",
    "O4_A1_COMMUNICATIVE_OUTPUT",
}
EXPECTED_MULTI_SOURCE_FAMILIES = {
    "PERSON_TEXT_DETAIL_MATCHING",
    "AUDIO_LIST_MATCHING",
}


class U05FAR4Error(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise U05FAR4Error(f"MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise U05FAR4Error(f"NOT_OBJECT:{path}")
    return value


def build_report() -> dict[str, Any]:
    far2 = _load(FAR2_PATH)
    far3 = _load(FAR3_PATH)
    far4 = _load(FAR4_PATH)

    if far4.get("task_id") != TASK_ID or far4.get("status") != STATUS:
        raise U05FAR4Error("TASK_OR_STATUS_DRIFT")
    if far4.get("next_short_step") != NEXT_SHORT_STEP:
        raise U05FAR4Error("NEXT_SHORT_STEP_DRIFT")

    readiness = far4["full_production_readiness"]
    if readiness["far2_practice_slot_count"] != 1632:
        raise U05FAR4Error("TOTAL_SLOT_COUNT_DRIFT")
    if readiness["far2_core_slot_count"] != 480:
        raise U05FAR4Error("CORE_SLOT_COUNT_DRIFT")
    if readiness["far2_ket_slot_count"] != 672:
        raise U05FAR4Error("KET_SLOT_COUNT_DRIFT")
    if readiness["far2_dictation_slot_count"] != 480:
        raise U05FAR4Error("DICTATION_SLOT_COUNT_DRIFT")
    if readiness["all_slots_accounted_for"] is not True:
        raise U05FAR4Error("ALL_SLOTS_NOT_ACCOUNTED")
    if readiness["all_slots_gpt56_authoring_or_binding_ready"] is not True:
        raise U05FAR4Error("AUTHORING_READINESS_DRIFT")
    if readiness["learner_facing_items_materialized"] != 0:
        raise U05FAR4Error("LEARNER_ITEMS_PREMATURELY_MATERIALIZED")
    if readiness["executable_items_materialized"] != 0:
        raise U05FAR4Error("EXECUTABLE_ITEMS_PREMATURELY_MATERIALIZED")
    if readiness["external_asset_binding_required_before_executable_count"] != 816:
        raise U05FAR4Error("ASSET_PENDING_COUNT_DRIFT")
    if readiness["external_asset_free_slot_count"] != 816:
        raise U05FAR4Error("ASSET_FREE_COUNT_DRIFT")

    profile = readiness["ket_asset_profile"]
    expected_profile = {
        "no_external_asset_required": 336,
        "audio_only_required": 192,
        "visual_only_required": 96,
        "audio_and_visual_required": 48,
    }
    if profile != expected_profile:
        raise U05FAR4Error(f"KET_ASSET_PROFILE_DRIFT:{profile}")
    if readiness["dictation_audio_required_count"] != 480:
        raise U05FAR4Error("DICTATION_AUDIO_COUNT_DRIFT")
    if readiness["multi_source_bundle_review_required_count"] != 96:
        raise U05FAR4Error("MULTI_SOURCE_COUNT_DRIFT")
    if set(readiness["multi_source_bundle_families"]) != EXPECTED_MULTI_SOURCE_FAMILIES:
        raise U05FAR4Error("MULTI_SOURCE_FAMILY_SET_DRIFT")
    if readiness["blocker_for_gpt56_text_authoring"] is not False:
        raise U05FAR4Error("TEXT_AUTHORING_INCORRECTLY_BLOCKED")
    if readiness["blocker_for_executable_audio_visual_tasks"] is not True:
        raise U05FAR4Error("ASSET_EXECUTABILITY_BLOCKER_MISSING")

    if len(far2["core_grammar_slots"]) != 480:
        raise U05FAR4Error("FAR2_CORE_DENOMINATOR_DRIFT")
    if len(far2["ket_adapted_slots"]) != 672:
        raise U05FAR4Error("FAR2_KET_DENOMINATOR_DRIFT")
    if len(far2["delayed_dictation_slots"]) != 480:
        raise U05FAR4Error("FAR2_DICTATION_DENOMINATOR_DRIFT")

    quota = far4["full_production_core_archetype_quota_plan"]
    allowed = list(far3["core_grammar_materialization_contract"]["allowed_practice_archetypes"])
    if len(allowed) != 6:
        raise U05FAR4Error("FAR3_ARCHETYPE_COUNT_DRIFT")
    quotas = quota["quotas_by_frame"]
    if set(quotas) != EXPECTED_CORE_FRAMES:
        raise U05FAR4Error("CORE_QUOTA_FRAME_SET_DRIFT")
    frame_counts = Counter(row["frame_id"] for row in far2["core_grammar_slots"])
    for frame, allocation in quotas.items():
        if set(allocation) != set(allowed):
            raise U05FAR4Error(f"CORE_QUOTA_ARCHETYPE_SET_DRIFT:{frame}")
        if sum(int(v) for v in allocation.values()) != frame_counts[frame]:
            raise U05FAR4Error(f"CORE_QUOTA_SUM_DRIFT:{frame}")
        if max(allocation.values()) / frame_counts[frame] > float(quota["maximum_single_archetype_share"]):
            raise U05FAR4Error(f"CORE_QUOTA_SHARE_DRIFT:{frame}")

    pilot_contract = far4["pilot46_contract"]
    if pilot_contract["pilot_item_count"] != 46:
        raise U05FAR4Error("PILOT_COUNT_DRIFT")
    if pilot_contract["core_items"] != 12:
        raise U05FAR4Error("PILOT_CORE_COUNT_DRIFT")
    if pilot_contract["ket_items"] != 28:
        raise U05FAR4Error("PILOT_KET_COUNT_DRIFT")
    if pilot_contract["dictation_items"] != 6:
        raise U05FAR4Error("PILOT_DICTATION_COUNT_DRIFT")
    for key in (
        "all_six_core_frames_covered",
        "all_fourteen_ket_families_covered",
        "deterministic_and_productive_answer_modes_covered",
        "audio_and_visual_asset_preconditions_represented",
        "multi_source_bundle_families_represented",
    ):
        if pilot_contract[key] is not True:
            raise U05FAR4Error(f"PILOT_GATE_NOT_LOCKED:{key}")
    if set(pilot_contract["productive_output_levels_targeted"]) != EXPECTED_OUTPUT_LEVELS:
        raise U05FAR4Error("PILOT_OUTPUT_LEVEL_TARGET_SET_DRIFT")

    pilot = list(far4["pilot_slots"])
    if len(pilot) != 46:
        raise U05FAR4Error("PILOT_ROWS_DRIFT")
    if len({row["pilot_id"] for row in pilot}) != 46:
        raise U05FAR4Error("PILOT_ID_COLLISION")
    if len({row["source_slot_id"] for row in pilot}) != 46:
        raise U05FAR4Error("PILOT_SOURCE_SLOT_COLLISION")

    all_far2 = {
        row["slot_id"]: row
        for row in (
            list(far2["core_grammar_slots"])
            + list(far2["ket_adapted_slots"])
            + list(far2["delayed_dictation_slots"])
        )
    }
    for row in pilot:
        source = all_far2.get(row["source_slot_id"])
        if source is None:
            raise U05FAR4Error(f"PILOT_SOURCE_SLOT_MISSING:{row['pilot_id']}")
        if row["practice_set_id"] != source["practice_set_id"]:
            raise U05FAR4Error(f"PILOT_SET_LINEAGE_DRIFT:{row['pilot_id']}")
        if row["stage"] != source["stage"]:
            raise U05FAR4Error(f"PILOT_STAGE_LINEAGE_DRIFT:{row['pilot_id']}")
        if row["episode_id"] != source["episode_id"]:
            raise U05FAR4Error(f"PILOT_EPISODE_LINEAGE_DRIFT:{row['pilot_id']}")

    core_pilot = [row for row in pilot if row["pilot_category"] == "CORE_GRAMMAR"]
    ket_pilot = [row for row in pilot if row["pilot_category"] == "KET_ADAPTED"]
    dict_pilot = [row for row in pilot if row["pilot_category"] == "DELAYED_DICTATION"]
    if len(core_pilot) != 12 or len(ket_pilot) != 28 or len(dict_pilot) != 6:
        raise U05FAR4Error("PILOT_CATEGORY_COUNT_DRIFT")

    core_frame_counts = Counter(row["frame_id"] for row in core_pilot)
    if set(core_frame_counts) != EXPECTED_CORE_FRAMES or set(core_frame_counts.values()) != {2}:
        raise U05FAR4Error(f"PILOT_CORE_FRAME_DRIFT:{dict(core_frame_counts)}")
    for frame in EXPECTED_CORE_FRAMES:
        stages = {row["stage"] for row in core_pilot if row["frame_id"] == frame}
        if stages != {"GUIDED", "UNSEEN_TRANSFER"}:
            raise U05FAR4Error(f"PILOT_CORE_STAGE_DRIFT:{frame}:{stages}")

    far3_families = {
        row["task_family"]
        for row in far3["ket_adapted_materialization_contract"]["task_family_contracts"]
    }
    ket_family_counts = Counter(row["task_family"] for row in ket_pilot)
    if set(ket_family_counts) != far3_families or set(ket_family_counts.values()) != {2}:
        raise U05FAR4Error(f"PILOT_KET_FAMILY_DRIFT:{dict(ket_family_counts)}")

    output_levels = {
        row["output_level"]
        for row in ket_pilot
        if row.get("output_level") in EXPECTED_OUTPUT_LEVELS
    }
    if output_levels != EXPECTED_OUTPUT_LEVELS:
        raise U05FAR4Error(f"PILOT_OUTPUT_LEVEL_COVERAGE_DRIFT:{sorted(output_levels)}")

    asset_pending = sum(bool(row["executable_asset_preconditions"]) for row in pilot)
    if asset_pending != pilot_contract["counts"]["asset_pending"]:
        raise U05FAR4Error("PILOT_ASSET_PENDING_COUNT_DRIFT")
    bundle_rows = [row for row in pilot if row.get("source_bundle_review_required")]
    if len(bundle_rows) != 4:
        raise U05FAR4Error("PILOT_BUNDLE_REVIEW_COUNT_DRIFT")
    if {row["task_family"] for row in bundle_rows} != EXPECTED_MULTI_SOURCE_FAMILIES:
        raise U05FAR4Error("PILOT_BUNDLE_FAMILY_DRIFT")

    d1 = [row for row in dict_pilot if row["dictation_pass"] == "D1"]
    d2 = [row for row in dict_pilot if row["dictation_pass"] == "D2"]
    if len(d1) != 4 or len(d2) != 2:
        raise U05FAR4Error("PILOT_DICTATION_PASS_COUNT_DRIFT")
    d1_eps = {row["episode_id"] for row in d1}
    d2_eps = {row["episode_id"] for row in d2}
    if not d2_eps.issubset(d1_eps):
        raise U05FAR4Error("PILOT_D2_NOT_REVISITING_SELECTED_D1")
    for row in dict_pilot:
        if row["target_provenance_mode"] != "AUDIO_TRANSCRIPT_EXACT":
            raise U05FAR4Error(f"PILOT_DICTATION_PROVENANCE_DRIFT:{row['pilot_id']}")
        if row["executable_asset_preconditions"] != ["AUDIO_ASSET_BOUND"]:
            raise U05FAR4Error(f"PILOT_DICTATION_ASSET_PRECONDITION_DRIFT:{row['pilot_id']}")

    far5 = far4["far5_admission_contract"]
    if far5["far5_task_id"] != NEXT_SHORT_STEP:
        raise U05FAR4Error("FAR5_TASK_ID_DRIFT")
    for key in (
        "exact_pilot_slot_set_locked",
        "source_refs_must_be_read_before_each_item_authoring",
        "source_bundle_suitability_requires_gpt56_review",
        "deterministic_item_must_have_one_unambiguous_answer",
        "productive_item_must_have_rubric_and_no_single_exact_answer",
        "asset_pending_item_may_be_authored_but_must_remain_not_executable",
        "pilot_must_not_expand_to_full_1632_until_pilot_qa_pass",
        "pilot_failure_repairs_contract_or_item_only_no_mass_regeneration",
    ):
        if far5[key] is not True:
            raise U05FAR4Error(f"FAR5_ADMISSION_GATE_DRIFT:{key}")
    if far5["learner_facing_author_model"] != "GPT-5.6 Sol":
        raise U05FAR4Error("FAR5_AUTHOR_MODEL_DRIFT")
    if far5["semantic_reviewer_model"] != "GPT-5.6 Sol":
        raise U05FAR4Error("FAR5_REVIEWER_MODEL_DRIFT")
    if far5["python_may_author_or_rewrite_learner_facing_english"] is not False:
        raise U05FAR4Error("FAR5_PYTHON_AUTHORING_UNLOCKED")

    safety = far4["scope_safety"]
    if safety["learner_facing_item_count"] != 0:
        raise U05FAR4Error("FAR4_LEARNER_ITEM_COUNT_DRIFT")
    for key in (
        "reader360_modified",
        "far2_modified",
        "far3_modified",
        "audio_generated",
        "visual_asset_generated",
        "pdf_materialized",
        "a2_grammar_unlocked",
        "a2_native_task_demand_unlocked",
        "other_units_modified",
    ):
        if safety[key] is not False:
            raise U05FAR4Error(f"FAR4_SCOPE_SAFETY_DRIFT:{key}")

    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "practice_slot_denominator": readiness["far2_practice_slot_count"],
        "gpt56_authoring_ready_slot_count": 1632,
        "external_asset_free_slot_count": readiness["external_asset_free_slot_count"],
        "external_asset_binding_required_count": readiness["external_asset_binding_required_before_executable_count"],
        "multi_source_bundle_review_required_count": readiness["multi_source_bundle_review_required_count"],
        "pilot_item_count": len(pilot),
        "pilot_core_count": len(core_pilot),
        "pilot_ket_count": len(ket_pilot),
        "pilot_dictation_count": len(dict_pilot),
        "pilot_asset_pending_count": asset_pending,
        "pilot_output_level_count": len(output_levels),
        "learner_facing_item_count": 0,
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    print(json.dumps(build_report(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
