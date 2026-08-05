from __future__ import annotations

import pytest

from ulga.builders import (
    build_a1fs_v1_u01qb15_actual_real62_fresh474_r2_distinct_matching_acceptance_runner
    as runner,
)


def _allocation(human_review_count: int) -> dict[str, object]:
    activities = []
    for index in range(runner.base.SCORED):
        if index < human_review_count:
            activities.append(
                {
                    "scored": True,
                    "skill": "WRITING",
                    "task_angle": "COMPLETE_SENTENCE_PRODUCTION",
                }
            )
        else:
            activities.append(
                {
                    "scored": True,
                    "skill": "READING",
                    "task_angle": "ARTICLE_CONTROL",
                }
            )

    forms = []
    for ordinal in range(runner.base.FORMS):
        start = ordinal * 16
        forms.append(
            {
                "form_ordinal": ordinal + 1,
                "scene_packages": [
                    {"activities": activities[start : start + 16]}
                ],
            }
        )
    return {"forms": forms}


def test_r2_scoring_composition_is_derived_from_blueprint_not_legacy_constant() -> None:
    expected = runner.expected_outcome_counts_from_allocation(_allocation(32))
    assert expected == {
        "AUTO_PASS": 160,
        "PENDING_HUMAN_REVIEW": 32,
    }


def test_r2_scoring_composition_still_accepts_legacy_156_36_when_blueprint_requires_it() -> None:
    expected = runner.expected_outcome_counts_from_allocation(_allocation(36))
    assert expected == {
        "AUTO_PASS": 156,
        "PENDING_HUMAN_REVIEW": 36,
    }


def test_r2_scoring_composition_fails_closed_on_wrong_scored_denominator() -> None:
    allocation = _allocation(32)
    forms = allocation["forms"]
    assert isinstance(forms, list)
    scene_packages = forms[-1]["scene_packages"]
    scene_packages[0]["activities"].pop()
    with pytest.raises(
        runner.BlueprintScoringCompositionError,
        match="R2_BLUEPRINT_SCORED_DENOMINATOR_INVALID",
    ):
        runner.expected_outcome_counts_from_allocation(allocation)


def test_r2_scoring_composition_policy_boundaries_remain_non_content_producer() -> None:
    assert runner.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert runner.A1FS_CONTENT_POLICY_EXEMPTION
    assert runner.PASS_STATUS == runner.base.PASS_STATUS
    assert runner.NEXT_SHORT_STEP == runner.base.NEXT_SHORT_STEP
