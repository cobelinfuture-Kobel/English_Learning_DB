"""Require formal learner-visible whole-form capacity before R4R3 scene-donor admission.

R4 production replay proved that task-angle capacity alone is not sufficient for a
scene swap.  The F11 U01-C4-TOY-SHOP donor passed R4R3R2's Reading/Writing/Speaking
task-angle solver, but the resulting Form08 Reading component failed the installed
U16 learner-visible whole-form matcher: distinct item IDs existed while eight
learner-visible-distinct questions did not.

R4R3R3 therefore replaces only R4R3R1's private donor-candidate function after
R4R3R2 is installed.  Every same-family pairwise donor is filtered through:

1. frozen-form and exposure/repeat-gap legality,
2. existing Reading/Writing/Speaking task-angle capacity,
3. the exact current formal candidate predicates (pattern family, canonical scoring,
   scene/context, installed learner-quality gate), and
4. the installed U16 whole-form learner-visible distinct matcher for Reading and
   Writing after applying the task-angle state that U16C/R4R2 would actually use.

Only then is the historical deterministic preference applied: legal single-exposure
donors first, then legal exposure-count-two donors, each by nearest future Form and
stable scene identity.  The probe is read-only.  It authors no content and changes no
QuestionBank, scene authority, learner evidence, scoring/runtime/planner authority,
Unit02-24, audio, Speaking scoring, or A2 state.
"""
from __future__ import annotations

import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import _u01qb13_distinct_item_matching_adapter as matching
from ulga.builders import _u01qb16_learner_visible_distinctness_adapter as visible
from ulga.builders import _u01qb18f_r4r2_unbound_writing_selector_parity_fullfix as r4r2
from ulga.builders import _u01qb18f_r4r3r1_donor_rejection_diagnostic as diagnostic
from ulga.builders import _u01qb18f_r4r3r1_support_stage_scene_swap_fullfix as r4r3r1
from ulga.builders import _u01qb18f_r4r3r2_broaden_pairwise_donor_eligibility_fullfix as r4r3r2
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u13
from ulga.builders import build_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as runtime_allocation

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only formal learner-visible donor-admission guard over already-approved Unit01 "
    "scenes and the existing 474-item QuestionBank. It reuses the installed canonical "
    "scoring/scene/context/learner-quality predicates and U16 learner-visible matcher; "
    "it authors no content and changes no QuestionBank, bound learner evidence, scoring/"
    "runtime/planner/database authority, Unit02-24, audio, Speaking scoring, or A2 state."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18F-R4R3R3_FormalLearnerVisibleWholeFormCapacityAwareDonorAdmissionFullFix"
PASS_STATUS = "PASS_A1FS_V1_U01QB18F_R4R3R3_FORMAL_LEARNER_VISIBLE_WHOLE_FORM_CAPACITY_AWARE_DONOR_ADMISSION_FULLFIX"
NEXT_SHORT_STEP = r4r3r2.NEXT_SHORT_STEP

_ORIGINAL_R4R3R2_CANDIDATE_SWAP = r4r3r2._broadened_candidate_swap
_INSTALLED = False
_PROBE_LEARNER_ID = "R4R3R3-FORMAL-CAPACITY-PROBE"


class FormalLearnerVisibleDonorAdmissionError(ValueError):
    """Fail-closed R4R3R3 installation or formal-probe error."""


def _formal_runtime_state(
    database: Path,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Load the same catalog/scoring authority used by the formal U01QB13 matcher."""
    with closing(sqlite3.connect(Path(database))) as connection:
        connection.row_factory = sqlite3.Row
        lesson_ids = [
            str(row[0])
            for row in connection.execute(
                "SELECT DISTINCT lesson_id FROM u01qb02_item_catalog ORDER BY lesson_id"
            )
        ]
        if len(lesson_ids) != 1:
            raise FormalLearnerVisibleDonorAdmissionError(
                "R4R3R3_UNIT01_LESSON_DENOMINATOR_INVALID:" + ",".join(lesson_ids)
            )
        lesson_id = lesson_ids[0]
        catalog = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM u01qb02_item_catalog WHERE lesson_id=? ORDER BY item_id",
                (lesson_id,),
            )
        ]
        scoring = matching.load_runtime_item_scoring_classes(
            connection,
            lesson_id=lesson_id,
        )
    if not catalog or set(scoring) != {str(row["item_id"]) for row in catalog}:
        raise FormalLearnerVisibleDonorAdmissionError(
            "R4R3R3_RUNTIME_SCORING_CLASS_CATALOG_IDENTITY_MISMATCH"
        )
    return catalog, scoring


def _effective_reading_rows(
    all_rows: Sequence[Mapping[str, Any]],
    *,
    form_ordinal: int,
    choices: Mapping[str, tuple[str, ...]],
) -> list[dict[str, Any]]:
    """Project exactly the Reading task-angle/family mutation U16C would apply."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in all_rows:
        if int(source["form_ordinal"]) == int(form_ordinal) and str(source["skill"]) == "READING":
            grouped[str(source["scene_ref_id"])].append(dict(source))
    if len(grouped) != u13.SCENES_PER_FORM or any(len(rows) != 2 for rows in grouped.values()):
        raise FormalLearnerVisibleDonorAdmissionError(
            f"R4R3R3_READING_FORM_DENOMINATOR_INVALID:F{form_ordinal:02d}"
        )

    result: list[dict[str, Any]] = []
    for ref in sorted(grouped):
        activity_rows = sorted(grouped[ref], key=lambda row: str(row["activity_id"]))
        angles = tuple(choices.get(ref, ()))
        if len(angles) != len(activity_rows):
            raise FormalLearnerVisibleDonorAdmissionError(
                f"R4R3R3_READING_CHOICE_DENOMINATOR_INVALID:{ref}"
            )
        for row, angle in zip(activity_rows, angles):
            families = tuple(u13.EXACT_SCORED_BINDINGS.get(("READING", str(angle)), ()))
            if not families:
                raise FormalLearnerVisibleDonorAdmissionError(
                    f"R4R3R3_READING_EFFECTIVE_ANGLE_BINDING_MISSING:{angle}"
                )
            row["task_angle"] = str(angle)
            row["pattern_family_ids_json"] = u13.canonical(list(families))
            result.append(row)
    return sorted(result, key=lambda row: str(row["activity_id"]))


def _formal_assignment_exists(
    activities: Sequence[Mapping[str, Any]],
    *,
    catalog: Sequence[Mapping[str, Any]],
    scoring: Mapping[str, str],
    form_ordinal: int,
    skill: str,
) -> bool:
    """Use the installed formal selector and U16 learner-visible whole-form matcher."""
    return r4r2._formal_assignment_exists(
        activities,
        catalog=catalog,
        scoring=scoring,
        learner_id=_PROBE_LEARNER_ID,
        session_id=f"R4R3R3-F{int(form_ordinal):02d}-{skill}",
        exposed=set(),
        recent=set(),
    )


def _writing_form_exists(
    all_rows: Sequence[Mapping[str, Any]],
    *,
    form_ordinal: int,
    catalog: Sequence[Mapping[str, Any]],
    scoring: Mapping[str, str],
) -> bool:
    """Let R4R2 perform the exact formal Writing replan it would use after a swap."""
    rows = [
        dict(row)
        for row in all_rows
        if int(row["form_ordinal"]) == int(form_ordinal) and str(row["skill"]) == "WRITING"
    ]
    if len(rows) != u13.WRITING_PER_FORM:
        raise FormalLearnerVisibleDonorAdmissionError(
            f"R4R3R3_WRITING_FORM_DENOMINATOR_INVALID:F{form_ordinal:02d}:{len(rows)}"
        )
    prior = r4r3r1._prior_angles_from_rows(all_rows, form_ordinal=form_ordinal)
    try:
        effective = r4r2._choose_form_rows(
            rows,
            prior=prior,
            catalog=catalog,
            scoring=scoring,
            learner_id=_PROBE_LEARNER_ID,
            session_id=f"R4R3R3-F{int(form_ordinal):02d}-WRITING",
            exposed=set(),
            recent=set(),
        )
    except r4r2.WritingSelectorParityError:
        return False
    return _formal_assignment_exists(
        effective,
        catalog=catalog,
        scoring=scoring,
        form_ordinal=form_ordinal,
        skill="WRITING",
    )


def _formal_pair_passes(
    *,
    simulated: Sequence[Mapping[str, Any]],
    current_form: int,
    donor_form: int,
    current_choices: Mapping[str, Mapping[str, tuple[str, ...]]],
    donor_choices: Mapping[str, Mapping[str, tuple[str, ...]]],
    catalog: Sequence[Mapping[str, Any]],
    scoring: Mapping[str, str],
) -> bool:
    """Require formal Reading + Writing whole-form capacity on both swap endpoints."""
    current_reading = _effective_reading_rows(
        simulated,
        form_ordinal=current_form,
        choices=current_choices["READING"],
    )
    donor_reading = _effective_reading_rows(
        simulated,
        form_ordinal=donor_form,
        choices=donor_choices["READING"],
    )
    if not _formal_assignment_exists(
        current_reading,
        catalog=catalog,
        scoring=scoring,
        form_ordinal=current_form,
        skill="READING",
    ):
        return False
    if not _formal_assignment_exists(
        donor_reading,
        catalog=catalog,
        scoring=scoring,
        form_ordinal=donor_form,
        skill="READING",
    ):
        return False
    if not _writing_form_exists(
        simulated,
        form_ordinal=current_form,
        catalog=catalog,
        scoring=scoring,
    ):
        return False
    if not _writing_form_exists(
        simulated,
        form_ordinal=donor_form,
        catalog=catalog,
        scoring=scoring,
    ):
        return False
    return True


def _formal_learner_visible_candidate_swap(
    database: Path,
    *,
    current_form: int,
    failing_ref: str,
    all_rows: Sequence[Mapping[str, Any]],
    frozen_forms: set[int],
):
    """Filter all legal pairwise donors by formal whole-form capacity, then rank."""
    usage = r4r3r1.r4r3._scene_usage(all_rows)
    failing_usage = usage.get(str(failing_ref))
    if failing_usage is None:
        raise FormalLearnerVisibleDonorAdmissionError(
            f"FAILING_SCENE_USAGE_MISSING:{failing_ref}"
        )
    if int(failing_usage["exposure_count"]) != 1:
        return None

    family = str(failing_usage["situation_family"])
    current_refs = {
        str(row["scene_ref_id"])
        for row in all_rows
        if int(row["form_ordinal"]) == int(current_form)
    }
    task_catalog = runtime_allocation._catalog(Path(database))
    formal_catalog, scoring = _formal_runtime_state(Path(database))
    ranked: list[tuple[tuple[Any, ...], Any]] = []
    seen: set[tuple[int, str]] = set()

    for row in all_rows:
        donor_form = int(row["form_ordinal"])
        donor_ref = str(row["scene_ref_id"])
        key = (donor_form, donor_ref)
        if key in seen:
            continue
        seen.add(key)
        if donor_form <= int(current_form) or donor_form in frozen_forms:
            continue
        if donor_ref == str(failing_ref) or donor_ref in current_refs:
            continue

        donor_usage = usage.get(donor_ref)
        if donor_usage is None:
            continue
        exposure_count = int(donor_usage["exposure_count"])
        if exposure_count not in (1, 2):
            continue
        if str(donor_usage["situation_family"]) != family:
            continue

        donor_form_refs = {
            str(value["scene_ref_id"])
            for value in all_rows
            if int(value["form_ordinal"]) == donor_form
        }
        if str(failing_ref) in donor_form_refs:
            continue
        if exposure_count == 2:
            repeat_ok, _repeat_detail = diagnostic._post_swap_repeat_gap(
                donor_usage=donor_usage,
                donor_form=donor_form,
                current_form=current_form,
            )
            if not repeat_ok:
                continue

        simulated = r4r3r1._swap_scene_packages_in_memory(
            all_rows,
            current_form=current_form,
            failing_ref=failing_ref,
            donor_form=donor_form,
            donor_ref=donor_ref,
        )
        try:
            current_choices = {
                skill: r4r3r1._form_skill_choices(
                    all_rows=simulated,
                    form_ordinal=current_form,
                    skill=skill,
                    catalog=task_catalog,
                )
                for skill in ("READING", "WRITING", "SPEAKING")
            }
            donor_choices = {
                skill: r4r3r1._form_skill_choices(
                    all_rows=simulated,
                    form_ordinal=donor_form,
                    skill=skill,
                    catalog=task_catalog,
                )
                for skill in ("READING", "WRITING", "SPEAKING")
            }
        except runtime_allocation.RuntimeTaskAwareAllocationError:
            continue

        if not _formal_pair_passes(
            simulated=simulated,
            current_form=current_form,
            donor_form=donor_form,
            current_choices=current_choices,
            donor_choices=donor_choices,
            catalog=formal_catalog,
            scoring=scoring,
        ):
            continue

        # Preserve R4R3R2 policy: any legal legacy single-exposure donor outranks
        # broadened reused-scene donors; each class is nearest-form then stable-ref.
        rank = (
            0 if exposure_count == 1 else 1,
            donor_form - int(current_form),
            donor_ref,
        )
        ranked.append(
            (
                rank,
                (
                    donor_form,
                    donor_ref,
                    simulated,
                    current_choices["SPEAKING"],
                    donor_choices["SPEAKING"],
                ),
            )
        )

    if not ranked:
        return None
    ranked.sort(key=lambda value: value[0])
    return ranked[0][1]


def install() -> None:
    global _INSTALLED
    if installed():
        _INSTALLED = True
        return
    if r4r3r1._candidate_swap is not _ORIGINAL_R4R3R2_CANDIDATE_SWAP:
        raise FormalLearnerVisibleDonorAdmissionError(
            "R4R3R2_PRIVATE_CANDIDATE_OWNER_DRIFT"
        )
    if matching.solve_distinct_activity_assignment is not visible.solve_learner_visible_distinct_activity_assignment:
        raise FormalLearnerVisibleDonorAdmissionError(
            "U16_LEARNER_VISIBLE_MATCHER_NOT_ACTIVE"
        )
    r4r3r1._candidate_swap = _formal_learner_visible_candidate_swap
    _INSTALLED = True


def installed() -> bool:
    return (
        _INSTALLED
        and r4r3r1._candidate_swap is _formal_learner_visible_candidate_swap
        and matching.solve_distinct_activity_assignment
        is visible.solve_learner_visible_distinct_activity_assignment
    )
