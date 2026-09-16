from __future__ import annotations

from collections import Counter

import pytest

from product.a1fs_v1_2_1 import (
    u04fsv2_current360_contextual_form_runtime as fsv2,
)
from product.a1fs_v1_2_1 import (
    u04fsv2a_section_a_current360_approved_binding as section_a,
)


REPORT = fsv2.build_unit04_fsv2_current360_contextual_form_runtime()


def _section_a_rows():
    return [row for row in REPORT["active_items"] if row["section"] == "A"]


def test_section_a_approved120_is_bound_without_changing_20x40_denominator() -> None:
    rows = _section_a_rows()
    assert len(REPORT["forms"]) == 20
    assert len(REPORT["active_items"]) == 800
    assert len(REPORT["runtime_bindings"]) == 800
    assert len(rows) == 120
    assert REPORT["materialization_contract"]["section_a_current360_approved_activity_count"] == 120
    assert REPORT["coverage"]["section_a_current360_binding_count"] == 120
    assert REPORT["coverage"]["section_a_gpt5_6_review_pass_count"] == 120
    assert REPORT["coverage"]["section_a_operator_approved_count"] == 120
    assert len({row["section_a_candidate_id"] for row in rows}) == 120
    assert all(row["current360_episode_lineage"] is None for row in rows)
    assert all(row["section_a_current360_lineage"] for row in rows)


def test_section_a_at_is_bounded_and_global_default_guard_remains_closed() -> None:
    rows = _section_a_rows()
    at_rows = [row for row in rows if row["target_relation_surface"] == "at"]
    assert len(at_rows) == 15
    assert REPORT["coverage"]["section_a_at_selected_response_count"] == 15
    assert REPORT["safety"]["selected_at_default_guard_retained"] is True
    assert REPORT["safety"]["section_a_at_bounded_exception_count"] == 15
    assert REPORT["safety"]["section_a_at_global_unlocked"] is False
    assert REPORT["safety"]["section_a_requires_current360_gpt5_6_operator_approval"] is True
    for row in at_rows:
        lineage = row["section_a_current360_lineage"]
        assert lineage["source_authority"] == section_a.SOURCE_AUTHORITY
        assert lineage["gpt5_6_semantic_review"] == "PASS"
        assert lineage["operator_approved"] is True
        assert lineage["at_policy"] == section_a.AT_POLICY
        assert row["scoring_contract"]["reference_answer"] == "at"
        assert "at" in row["learner_activity"]["options"]
    with pytest.raises(fsv2.Unit04FSV2Error, match="AT_SELECTED_RELATION_FORBIDDEN"):
        fsv2._relation_options("at", 1)


def test_section_a_relation_distribution_is_balanced_and_form_local_unique() -> None:
    rows = _section_a_rows()
    assert Counter(row["target_relation_surface"] for row in rows) == Counter(
        {relation: 15 for relation in section_a.TARGET_RELATIONS}
    )
    for form_number in range(1, 21):
        form_rows = [row for row in rows if row["form_number"] == form_number]
        assert len(form_rows) == 6
        assert len({row["target_relation_surface"] for row in form_rows}) == 6
        assert len({row["section_a_current360_lineage"]["episode_id"] for row in form_rows}) == 6

    for stage, forms in section_a.STAGE_FORMS.items():
        stage_rows = [row for row in rows if row["form_number"] in forms]
        assert len(stage_rows) == 24, stage
        assert Counter(row["target_relation_surface"] for row in stage_rows) == Counter(
            {relation: 3 for relation in section_a.TARGET_RELATIONS}
        )


def test_operator_approved_first_six_samples_keep_locked_form_bindings() -> None:
    index = section_a.build_section_a_binding_index()
    assert index[(1, 1)]["candidate_id"] == "U04-SA-C001"
    assert index[(2, 1)]["candidate_id"] == "U04-SA-C002"
    assert index[(3, 1)]["candidate_id"] == "U04-SA-C003"
    assert index[(4, 1)]["candidate_id"] == "U04-SA-C004"
    assert index[(5, 1)]["candidate_id"] == "U04-SA-C005"
    assert index[(6, 1)]["candidate_id"] == "U04-SA-C006"


def test_section_a_learner_surface_has_no_private_review_or_answer_metadata() -> None:
    forbidden = {
        "correct_answer",
        "reference_answer",
        "answer_key",
        "source_q10_item_id",
        "source_runtime_slot_id",
        "source_fact_lineage",
        "gpt5_6_semantic_review",
        "operator_approved",
        "section_a_candidate_id",
    }
    for row in _section_a_rows():
        activity = row["learner_activity"]
        assert not forbidden.intersection(activity)
        assert activity["response_mode"] == "select_one"
        assert len(activity["options"]) == 4
        assert row["scoring_contract"]["reference_answer"] in activity["options"]


def test_section_a_cutover_preserves_b_to_e_except_later_approved_q31_d05_cutover() -> None:
    baseline = fsv2._base.build_unit04_fsv2_current360_contextual_form_runtime()
    baseline_contextual = [
        row for row in baseline["active_items"]
        if row["section"] in {"B", "C", "D", "E"}
        and not (row["section"] == "D" and row["section_activity_ordinal"] == 5)
    ]
    current_contextual = [
        row for row in REPORT["active_items"]
        if row["section"] in {"B", "C", "D", "E"}
        and not (row["section"] == "D" and row["section_activity_ordinal"] == 5)
    ]
    assert current_contextual == baseline_contextual

    d05 = [
        row for row in REPORT["active_items"]
        if row["section"] == "D" and row["section_activity_ordinal"] == 5
    ]
    assert len(d05) == 20
    assert all(row["task_variant"] == "SHORT_MESSAGE_MEANING" for row in d05)
    assert REPORT["coverage"]["short_message_meaning_activity_count"] == 20
    assert REPORT["coverage"]["reading_simple_gist_seed_activity_count"] == 0
    assert REPORT["safety"]["q31_d05_modified_by_section_a_cutover"] is False
    assert REPORT["safety"]["b_c_d_e_items_modified_by_section_a_cutover"] is False
    assert REPORT["safety"]["q31_d05_modified_by_short_message_cutover"] is True


def test_section_a_runtime_is_deterministic() -> None:
    replay = fsv2.build_unit04_fsv2_current360_contextual_form_runtime()
    assert replay == REPORT
