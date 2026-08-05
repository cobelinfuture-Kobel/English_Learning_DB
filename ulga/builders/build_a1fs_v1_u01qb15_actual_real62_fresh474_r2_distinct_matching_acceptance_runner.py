#!/usr/bin/env python3
"""Run Actual Real62 R2 acceptance with distinct matching and blueprint-derived scoring composition.

U01QB14's historical 156/36 outcome constants describe the earlier fixed
allocation. U01QB14R2 rematerializes task angles against the live 474-item
runtime, so the exact number of FEATURE_RUBRIC Writing production activities
must be derived from the already-materialized allocation before replay. This
runner derives that expectation from blueprint semantics, installs the existing
U01QB13 distinct matcher, and delegates to the existing private acceptance path.
It does not derive expectations from observed scoring outcomes.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import _u01qb13_distinct_item_matching_adapter as matching
from ulga.builders import (
    build_a1fs_v1_u01qb14_unit01_twelve_form_private_production_replay_and_learner_form_acceptance
    as replay_builder,
)
from ulga.builders import (
    build_a1fs_v1_u01qb14r1_unit01_cumulative_scene_world_runtime_bindability_gate_fullfix
    as r1,
)
from ulga.builders import (
    build_a1fs_v1_u01qb15_actual_real62_fresh474_r2_private_acceptance_runner
    as base,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Operator entrypoint that installs deterministic whole-form distinct-item matching into the existing U01QB13 runtime and derives the R2 replay scoring-composition expectation from the already-approved allocation blueprint before delegating to the existing U01QB15 Actual Real62 disposable acceptance runner; no content, QuestionBank, planner, runtime, scoring, scene, or learner-state authority is created."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB15_ActualReal62Fresh474R2DistinctMatchingAcceptance"
PASS_STATUS = base.PASS_STATUS
NEXT_SHORT_STEP = base.NEXT_SHORT_STEP

HUMAN_REVIEW_WRITING_ANGLES = frozenset(
    {
        "COMPLETE_SENTENCE_PRODUCTION",
        "CONNECTED_SENTENCE_PRODUCTION",
    }
)

_ORIGINAL_R1_RUN_PRIVATE_REPLAY = r1.run_private_replay
_LAST_EXPECTED_OUTCOME_COUNTS: dict[str, int] | None = None


class BlueprintScoringCompositionError(ValueError):
    pass


def expected_outcome_counts_from_allocation(
    allocation: Mapping[str, Any],
) -> dict[str, int]:
    """Derive pre-replay outcome expectations from scored blueprint semantics."""
    auto_pass = 0
    pending_human = 0
    scored = 0
    forms = allocation.get("forms")
    if not isinstance(forms, list) or len(forms) != base.FORMS:
        raise BlueprintScoringCompositionError("R2_ALLOCATION_FORMS_INVALID")

    for form in forms:
        scenes = form.get("scene_packages") if isinstance(form, Mapping) else None
        if not isinstance(scenes, list):
            raise BlueprintScoringCompositionError("R2_ALLOCATION_SCENE_PACKAGES_INVALID")
        for scene in scenes:
            activities = scene.get("activities") if isinstance(scene, Mapping) else None
            if not isinstance(activities, list):
                raise BlueprintScoringCompositionError("R2_ALLOCATION_ACTIVITIES_INVALID")
            for activity in activities:
                if not isinstance(activity, Mapping) or not bool(activity.get("scored")):
                    continue
                scored += 1
                skill = str(activity.get("skill") or "")
                angle = str(activity.get("task_angle") or "")
                if skill == "WRITING" and angle in HUMAN_REVIEW_WRITING_ANGLES:
                    pending_human += 1
                else:
                    auto_pass += 1

    if scored != base.SCORED or auto_pass + pending_human != base.SCORED:
        raise BlueprintScoringCompositionError(
            f"R2_BLUEPRINT_SCORED_DENOMINATOR_INVALID:{scored}:{auto_pass}:{pending_human}"
        )
    if pending_human <= 0 or auto_pass <= 0:
        raise BlueprintScoringCompositionError(
            f"R2_BLUEPRINT_SCORING_COMPOSITION_INVALID:{auto_pass}:{pending_human}"
        )
    return {
        "AUTO_PASS": auto_pass,
        "PENDING_HUMAN_REVIEW": pending_human,
    }


def _read_allocation_expected_outcomes(allocation_path: Path) -> dict[str, int]:
    try:
        value = json.loads(Path(allocation_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BlueprintScoringCompositionError(
            f"R2_ALLOCATION_UNREADABLE:{allocation_path}:{exc}"
        ) from exc
    if not isinstance(value, Mapping):
        raise BlueprintScoringCompositionError("R2_ALLOCATION_OBJECT_REQUIRED")
    return expected_outcome_counts_from_allocation(value)


def _run_private_replay_with_blueprint_scoring_composition(*args, **kwargs):
    global _LAST_EXPECTED_OUTCOME_COUNTS
    allocation_path = kwargs.get("allocation_path")
    if allocation_path is None:
        raise BlueprintScoringCompositionError("R2_ALLOCATION_PATH_REQUIRED")
    expected = _read_allocation_expected_outcomes(Path(allocation_path))
    _LAST_EXPECTED_OUTCOME_COUNTS = expected

    # U01QB14 and its validator share the same builder module object. Update
    # the two acceptance constants only for this R2 replay, then restore them.
    old_auto = replay_builder.EXPECTED_AUTO_PASS
    old_human = replay_builder.EXPECTED_PENDING_HUMAN
    replay_builder.EXPECTED_AUTO_PASS = expected["AUTO_PASS"]
    replay_builder.EXPECTED_PENDING_HUMAN = expected["PENDING_HUMAN_REVIEW"]
    try:
        return _ORIGINAL_R1_RUN_PRIVATE_REPLAY(*args, **kwargs)
    finally:
        replay_builder.EXPECTED_AUTO_PASS = old_auto
        replay_builder.EXPECTED_PENDING_HUMAN = old_human


def main(argv: Sequence[str] | None = None) -> int:
    global _LAST_EXPECTED_OUTCOME_COUNTS
    _LAST_EXPECTED_OUTCOME_COUNTS = None
    matching.install()
    original = r1.run_private_replay
    r1.run_private_replay = _run_private_replay_with_blueprint_scoring_composition
    try:
        result = base.main(argv)
    finally:
        r1.run_private_replay = original

    if _LAST_EXPECTED_OUTCOME_COUNTS is not None:
        print(
            "BLUEPRINT_EXPECTED_AUTO_PASS="
            f"{_LAST_EXPECTED_OUTCOME_COUNTS['AUTO_PASS']}"
        )
        print(
            "BLUEPRINT_EXPECTED_PENDING_HUMAN_REVIEW="
            f"{_LAST_EXPECTED_OUTCOME_COUNTS['PENDING_HUMAN_REVIEW']}"
        )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
