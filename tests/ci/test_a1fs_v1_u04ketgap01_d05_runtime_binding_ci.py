from __future__ import annotations

import json
from pathlib import Path

from product.a1fs_v1_2_1 import (
    u04fsv2_current360_contextual_form_runtime as fsv2,
)


ROOT = Path(__file__).resolve().parents[2]
ASSET = ROOT / "product/a1fs_v1_2_1/u04ketgap01_short_message_meaning_gpt56_approved20.json"
REPORT = fsv2.build_unit04_fsv2_current360_contextual_form_runtime()
BASELINE = fsv2._apply_approved_section_a(
    fsv2._base.build_unit04_fsv2_current360_contextual_form_runtime()
)
APPROVED = json.loads(ASSET.read_text(encoding="utf-8"))
APPROVED_BY_FORM = {int(row["form_number"]): row for row in APPROVED["items"]}


def _item(report, form_number: int, section: str, local: int):
    return next(
        row for row in report["active_items"]
        if int(row["form_number"]) == form_number
        and row["section"] == section
        and int(row["section_activity_ordinal"]) == local
    )


def _runtime(report, form_number: int, section: str, local: int):
    return next(
        row for row in report["runtime_bindings"]
        if int(row["form_number"]) == form_number
        and row["section"] == section
        and int(row["section_activity_ordinal"]) == local
    )


def test_short_message_cutover_binds_exactly_d05_q31_for_all_20_forms() -> None:
    assert len(REPORT["forms"]) == 20
    assert len(REPORT["active_items"]) == 800
    assert len(REPORT["runtime_bindings"]) == 800
    assert REPORT["coverage"]["short_message_meaning_activity_count"] == 20
    assert REPORT["coverage"]["reading_simple_gist_seed_activity_count"] == 0
    assert REPORT["materialization_contract"]["short_message_meaning_activity_count"] == 20
    assert REPORT["materialization_contract"]["short_message_meaning_slot_per_form"] == "D05"
    assert REPORT["materialization_contract"]["short_message_meaning_learner_question_number"] == "Q31"

    for form_number in range(1, 21):
        row = _item(REPORT, form_number, "D", 5)
        approved = APPROVED_BY_FORM[form_number]
        expected_answer = approved["options"][approved["correct_option_index"]]
        assert row["task_variant"] == "SHORT_MESSAGE_MEANING"
        assert row["learner_activity"] == {
            "question_number": "Q31",
            "skill": "READING",
            "stimulus": f"Message: {approved['message']}",
            "prompt": approved["question"],
            "options": approved["options"],
            "response_mode": "select_one",
            "capture_enabled": True,
            "practice_only": False,
        }
        assert row["scoring_contract"]["scoring_mode"] == "EXACT_OPTION"
        assert row["scoring_contract"]["reference_answer"] == expected_answer
        assert row["answer_key_private"]["reference_answer"] == expected_answer
        assert row["direct_target_relation_scoring"] is False


def test_short_message_cutover_preserves_current_d05_e05_context_and_all_non_d05_items() -> None:
    baseline_by_slot = {
        (int(row["form_number"]), row["section"], int(row["section_activity_ordinal"])): row
        for row in BASELINE["active_items"]
    }
    current_by_slot = {
        (int(row["form_number"]), row["section"], int(row["section_activity_ordinal"])): row
        for row in REPORT["active_items"]
    }

    changed_slots = []
    for slot, baseline in baseline_by_slot.items():
        current = current_by_slot[slot]
        if current != baseline:
            changed_slots.append(slot)
    assert changed_slots == [(form_number, "D", 5) for form_number in range(1, 21)]

    for form_number in range(1, 21):
        before_d05 = _item(BASELINE, form_number, "D", 5)
        after_d05 = _item(REPORT, form_number, "D", 5)
        before_e05 = _item(BASELINE, form_number, "E", 5)
        after_e05 = _item(REPORT, form_number, "E", 5)

        assert after_e05 == before_e05
        assert after_d05["current360_episode_lineage"] == before_d05["current360_episode_lineage"]
        assert after_d05["target_relation_surface"] == before_d05["target_relation_surface"]
        assert (
            after_d05["current360_episode_lineage"]["episode_id"]
            == after_e05["current360_episode_lineage"]["episode_id"]
        )
        assert (
            after_d05["current360_episode_lineage"]["micro_scene_id"]
            == after_e05["current360_episode_lineage"]["micro_scene_id"]
        )

    baseline_runtime = {
        (int(row["form_number"]), row["section"], int(row["section_activity_ordinal"])): row
        for row in BASELINE["runtime_bindings"]
    }
    current_runtime = {
        (int(row["form_number"]), row["section"], int(row["section_activity_ordinal"])): row
        for row in REPORT["runtime_bindings"]
    }
    runtime_changed = [
        slot for slot in baseline_runtime
        if baseline_runtime[slot] != current_runtime[slot]
    ]
    assert runtime_changed == [(form_number, "D", 5) for form_number in range(1, 21)]


def test_short_message_lineage_keeps_approved_authoring_source_and_runtime_context_separate() -> None:
    for form_number in range(1, 21):
        row = _item(REPORT, form_number, "D", 5)
        approved = APPROVED_BY_FORM[form_number]
        lineage = row["short_message_meaning_lineage"]
        authoring = lineage["authoring_current360_episode_lineage"]
        runtime_context = lineage["runtime_current360_episode_lineage_preserved"]

        assert lineage["task_id"] == APPROVED["task_id"]
        assert lineage["ket_task_family"] == "SHORT_MESSAGE_MEANING"
        assert lineage["generation_model"] == "GPT-5.6"
        assert lineage["operator_status"] == "APPROVED"
        assert lineage["runtime_binding_approved"] is True
        assert authoring["episode_id"] == approved["authoring_source_episode_id"]
        assert authoring["micro_scene_id"] == approved["micro_scene_id"]
        assert runtime_context == row["current360_episode_lineage"]
        assert lineage["shared_e05_current360_episode_id"] == runtime_context["episode_id"]
        assert (
            lineage["runtime_context_binding_mode"]
            == "PRESERVE_EXISTING_D05_E05_CURRENT360_CONTEXT_WHILE_BINDING_APPROVED_MESSAGE"
        )


def test_section_a_120_and_bounded_at_policy_survive_d05_cutover() -> None:
    section_a_rows = [row for row in REPORT["active_items"] if row["section"] == "A"]
    assert len(section_a_rows) == 120
    assert REPORT["coverage"]["section_a_current360_binding_count"] == 120
    assert REPORT["coverage"]["section_a_at_selected_response_count"] == 15
    assert REPORT["safety"]["selected_at_default_guard_retained"] is True
    assert REPORT["safety"]["section_a_at_global_unlocked"] is False
    assert REPORT["safety"]["section_a_current360_approved120_preserved"] is True
    assert REPORT["safety"]["q31_d05_modified_by_section_a_cutover"] is False


def test_short_message_cutover_safety_and_no_learner_private_metadata() -> None:
    assert REPORT["cutover_contract"]["d05_q31_active_task_variant"] == "SHORT_MESSAGE_MEANING"
    assert REPORT["cutover_contract"]["d05_q31_superseded_task_variant"] == "READING_SIMPLE_GIST_SEED"
    assert REPORT["cutover_contract"]["d05_q31_parallel_runtime_allowed"] is False
    assert REPORT["cutover_contract"]["d05_e05_current360_shared_context_preserved"] is True
    assert REPORT["safety"]["q31_d05_modified_by_short_message_cutover"] is True
    assert REPORT["safety"]["e05_q39_modified_by_short_message_cutover"] is False
    assert REPORT["safety"]["d05_e05_current360_shared_context_preserved"] is True
    assert REPORT["safety"]["short_message_parallel_runtime_created"] is False
    assert REPORT["safety"]["a2_a2plus_unlocked_by_short_message_cutover"] is False

    forbidden = {
        "correct_answer",
        "reference_answer",
        "answer_key",
        "source_q10_item_id",
        "source_runtime_slot_id",
        "source_fact_lineage",
        "correct_option_index",
        "operator_status",
        "generation_model",
    }
    for form_number in range(1, 21):
        activity = _item(REPORT, form_number, "D", 5)["learner_activity"]
        assert not forbidden.intersection(activity)


def test_short_message_runtime_is_deterministic() -> None:
    replay = fsv2.build_unit04_fsv2_current360_contextual_form_runtime()
    assert replay == REPORT
