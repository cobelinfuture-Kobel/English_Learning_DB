"""Read-only formal donor rejection funnel for Unit01 R4 support-stage swaps.

Actual production R4 replay now reaches the R4R3R3 formal donor gate but still
returns SUPPORT_STAGE_SCENE_SWAP_NOT_FOUND.  The older R4R3R1 diagnostic proves
that F11 U01-C4-TOY-SHOP and F12 U01-MA-SHOP-01 both pass repeat-gap plus
Reading/Writing/Speaking task-angle capacity, but it cannot explain which formal
whole-form endpoint rejects each donor.

This diagnostic reports the four scored endpoints for every structurally legal,
task-capacity-valid pairwise donor: current Reading, donor Reading, current
Writing and donor Writing.  For each endpoint it also reports per-activity item
candidate count and learner-visible-signature count before the installed U16
whole-form matcher is invoked.  It is fail-path/read-only only and authors no
content or learner state.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import _u01qb16_learner_visible_distinctness_adapter as visible
from ulga.builders import _u01qb18f_r4r2_unbound_writing_selector_parity_fullfix as r4r2
from ulga.builders import _u01qb18f_r4r3r1_donor_rejection_diagnostic as base_diagnostic
from ulga.builders import _u01qb18f_r4r3r1_support_stage_scene_swap_fullfix as r4r3r1
from ulga.builders import _u01qb18f_r4r3r3_formal_learner_visible_donor_admission_fullfix as r4r3r3
from ulga.builders import build_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as runtime_allocation

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only fail-path diagnostic over the existing Unit01 blueprint and 474-item "
    "runtime. It reports formal selector/matcher capacity only and authors no content, "
    "QuestionBank item, scene, learner evidence, scoring/runtime/planner/database "
    "authority, Unit02-24, audio, Speaking score, or A2 state."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18F-R4R3R3D_FormalDonorRejectionFunnelDiagnostic"
PASS_STATUS = "PASS_A1FS_V1_U01QB18F_R4R3R3D_FORMAL_DONOR_REJECTION_FUNNEL_DIAGNOSTIC"

_PROBE_LEARNER_ID = "R4R3R3D-FORMAL-DIAGNOSTIC"


def _compact_error(exc: BaseException) -> str:
    text = str(exc).replace("\r", " ").replace("\n", " ").strip()
    return f"{exc.__class__.__name__}:{text}" if text else exc.__class__.__name__


def _candidate_summary(
    activities: Sequence[Mapping[str, Any]],
    *,
    catalog: Sequence[Mapping[str, Any]],
    scoring: Mapping[str, str],
    form_ordinal: int,
    skill: str,
) -> tuple[bool, str, str]:
    candidates: dict[str, list[tuple[tuple[Any, ...], Mapping[str, Any]]]] = {}
    detail: list[str] = []
    for activity in activities:
        activity_id = str(activity["activity_id"])
        pairs = r4r2._candidate_pairs(
            activity,
            catalog=catalog,
            scoring=scoring,
            learner_id=_PROBE_LEARNER_ID,
            session_id=f"R4R3R3D-F{int(form_ordinal):02d}-{skill}",
            exposed=set(),
            recent=set(),
        )
        item_count = len({str(row["item_id"]) for _rank, row in pairs})
        visible_count = len({visible.learner_visible_signature(row) for _rank, row in pairs})
        detail.append(f"{activity_id}:items={item_count},visible={visible_count}")
        if not pairs:
            return False, f"ACTIVITY_RUNTIME_CANDIDATES_EMPTY:{activity_id}", ";".join(detail)
        candidates[activity_id] = pairs
    try:
        r4r3r3.matching.solve_distinct_activity_assignment(candidates)
    except Exception as exc:
        return False, _compact_error(exc), ";".join(detail)
    return True, "PASS", ";".join(detail)


def _reading_endpoint(
    simulated: Sequence[Mapping[str, Any]],
    *,
    form_ordinal: int,
    choices: Mapping[str, tuple[str, ...]],
    catalog: Sequence[Mapping[str, Any]],
    scoring: Mapping[str, str],
) -> tuple[bool, str, str]:
    try:
        rows = r4r3r3._effective_reading_rows(
            simulated,
            form_ordinal=form_ordinal,
            choices=choices,
        )
        return _candidate_summary(
            rows,
            catalog=catalog,
            scoring=scoring,
            form_ordinal=form_ordinal,
            skill="READING",
        )
    except Exception as exc:
        return False, _compact_error(exc), "NOT_AVAILABLE"


def _writing_endpoint(
    simulated: Sequence[Mapping[str, Any]],
    *,
    form_ordinal: int,
    catalog: Sequence[Mapping[str, Any]],
    scoring: Mapping[str, str],
) -> tuple[bool, str, str]:
    rows = [
        dict(row)
        for row in simulated
        if int(row["form_ordinal"]) == int(form_ordinal)
        and str(row["skill"]) == "WRITING"
    ]
    prior = r4r3r1._prior_angles_from_rows(simulated, form_ordinal=form_ordinal)
    try:
        effective = r4r2._choose_form_rows(
            rows,
            prior=prior,
            catalog=catalog,
            scoring=scoring,
            learner_id=_PROBE_LEARNER_ID,
            session_id=f"R4R3R3D-F{int(form_ordinal):02d}-WRITING",
            exposed=set(),
            recent=set(),
        )
    except Exception as exc:
        # Preserve a useful candidate-count snapshot of the persisted/simulated
        # Writing rows even when the R4R2 replanner itself is UNSAT.
        try:
            _ok, _err, detail = _candidate_summary(
                rows,
                catalog=catalog,
                scoring=scoring,
                form_ordinal=form_ordinal,
                skill="WRITING",
            )
        except Exception:
            detail = "NOT_AVAILABLE"
        return False, _compact_error(exc), detail
    return _candidate_summary(
        effective,
        catalog=catalog,
        scoring=scoring,
        form_ordinal=form_ordinal,
        skill="WRITING",
    )


def _skill_scoped_state(database: Path):
    state = r4r3r3._formal_runtime_state(Path(database))
    if (
        isinstance(state, tuple)
        and len(state) == 2
        and isinstance(state[0], Mapping)
        and isinstance(state[1], Mapping)
    ):
        catalog_by_skill, scoring_by_skill = state
        return catalog_by_skill, scoring_by_skill
    raise ValueError("R4R3R3D_SKILL_SCOPED_FORMAL_STATE_NOT_INSTALLED")


def diagnose(
    database: Path,
    *,
    current_form: int,
    failing_ref: str,
) -> list[str]:
    database = Path(database)
    with closing(sqlite3.connect(database)) as connection:
        connection.row_factory = sqlite3.Row
        all_rows = r4r3r1.r4r3._all_rows(connection)
        frozen_forms = r4r3r1._bound_form_ordinals(connection)

    usage = r4r3r1.r4r3._scene_usage(all_rows)
    failing_usage = usage.get(str(failing_ref))
    if failing_usage is None:
        return [
            f"R4R3R3D_DIAGNOSTIC_STATUS={PASS_STATUS}",
            f"R4R3R3D_DIAGNOSTIC_ERROR=FAILING_SCENE_USAGE_MISSING:{failing_ref}",
        ]

    try:
        catalog_by_skill, scoring_by_skill = _skill_scoped_state(database)
        reading_catalog = catalog_by_skill["READING"]
        reading_scoring = scoring_by_skill["READING"]
        writing_catalog = catalog_by_skill["WRITING"]
        writing_scoring = scoring_by_skill["WRITING"]
    except Exception as exc:
        return [
            f"R4R3R3D_DIAGNOSTIC_STATUS={PASS_STATUS}",
            "R4R3R3D_DIAGNOSTIC_ERROR=" + _compact_error(exc),
        ]

    family = str(failing_usage["situation_family"])
    current_refs = {
        str(row["scene_ref_id"])
        for row in all_rows
        if int(row["form_ordinal"]) == int(current_form)
    }
    task_catalog = runtime_allocation._catalog(database)
    lines = [
        f"R4R3R3D_DIAGNOSTIC_STATUS={PASS_STATUS}",
        f"R4R3R3D_FAILING_SCENE={failing_ref}",
        f"R4R3R3D_FAILING_FORM={int(current_form)}",
        f"R4R3R3D_FAILING_FAMILY={family}",
    ]
    eligible_count = 0
    formal_pass_count = 0
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
        repeat_detail = "SINGLE_EXPOSURE"
        if exposure_count == 2:
            repeat_ok, repeat_detail = base_diagnostic._post_swap_repeat_gap(
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
        except Exception as exc:
            lines.append(
                f"R4R3R3D_DONOR=F{donor_form:02d}|{donor_ref}|TASK_CAPACITY=FAIL|"
                f"error={_compact_error(exc)}"
            )
            continue

        eligible_count += 1
        endpoints = {
            "CURRENT_READING": _reading_endpoint(
                simulated,
                form_ordinal=current_form,
                choices=current_choices["READING"],
                catalog=reading_catalog,
                scoring=reading_scoring,
            ),
            "DONOR_READING": _reading_endpoint(
                simulated,
                form_ordinal=donor_form,
                choices=donor_choices["READING"],
                catalog=reading_catalog,
                scoring=reading_scoring,
            ),
            "CURRENT_WRITING": _writing_endpoint(
                simulated,
                form_ordinal=current_form,
                catalog=writing_catalog,
                scoring=writing_scoring,
            ),
            "DONOR_WRITING": _writing_endpoint(
                simulated,
                form_ordinal=donor_form,
                catalog=writing_catalog,
                scoring=writing_scoring,
            ),
        }
        pair_pass = all(value[0] for value in endpoints.values())
        formal_pass_count += int(pair_pass)
        lines.append(
            f"R4R3R3D_DONOR=F{donor_form:02d}|{donor_ref}|exposures={exposure_count}|"
            f"repeat_gap={repeat_detail}|formal_pair_pass={str(pair_pass).lower()}"
        )
        for endpoint, (ok, error, detail) in endpoints.items():
            lines.append(
                f"R4R3R3D_ENDPOINT=F{donor_form:02d}|{donor_ref}|{endpoint}|"
                f"status={'PASS' if ok else 'FAIL'}|error={error}|candidates={detail}"
            )

    lines.insert(4, f"R4R3R3D_TASK_CAPACITY_ELIGIBLE_DONOR_COUNT={eligible_count}")
    lines.insert(5, f"R4R3R3D_FORMAL_PAIR_PASS_COUNT={formal_pass_count}")
    return lines
