"""Restore unbound Unit01 Reading parity with the formal product selector.

Production R4 evidence proved that task-angle capacity is weaker than actual
learner execution.  F12 U01-MA-SHOP-01 passed repeat-gap and raw Reading/Writing/
Speaking task-capacity checks after a legal scene swap, but the donor Reading
projection selected a task angle for U01-FORM-12-S01-A02 with zero formal runtime
candidates.  U16C currently calls only the raw U01QB14R1 task-capacity solver
before writing Reading task angles.

R4R3R4 strengthens that existing U16C private migration plan without replacing
its public migration API or assembler ownership.  For an unbound Reading form it
searches the ordinary U01QB09 support-profile angles, preserves the no-repeat
contract, and accepts only a deterministic minimum-change whole-form assignment
that passes the installed canonical scoring, scene/context, learner-quality and
U16 learner-visible matcher.  The same formal Reading chooser is used by the
R4R3R3 donor-admission probe so admission and the later U16C mutation share one
capacity definition.

No QuestionBank item or scene is authored.  Bound learner evidence, scoring,
runtime/planner authority, Unit02-24, audio, Speaking scoring and A2 remain
unchanged.
"""
from __future__ import annotations

import itertools
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import _u01qb16c_unbound_form_progression_overlay as u16c
from ulga.builders import _u01qb18f_r4r2_unbound_writing_selector_parity_fullfix as r4r2
from ulga.builders import _u01qb18f_r4r3r1_support_stage_scene_swap_fullfix as r4r3r1
from ulga.builders import _u01qb18f_r4r3r3_formal_learner_visible_donor_admission_fullfix as r4r3r3
from ulga.builders import _u01qb18f_r4r3r3r1_skill_scoped_formal_catalog_adapter as r4r3r3r1
from ulga.builders import build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u09
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u13

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Learner-state-safe formal selector parity repair over existing Unit01 Reading "
    "blueprint rows and the existing 474-item QuestionBank. It reuses U01QB09 task "
    "angles plus installed canonical scoring/scene/context/learner-quality and U16 "
    "learner-visible matching; it authors no content, changes no bound evidence, "
    "creates no runtime/planner/scoring authority, modifies no Unit02-24 content, "
    "enables no audio/Speaking score, and unlocks no A2."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18F-R4R3R4_UnboundReadingFormalSelectorParityFullFix"
PASS_STATUS = "PASS_A1FS_V1_U01QB18F_R4R3R4_UNBOUND_READING_FORMAL_SELECTOR_PARITY_FULLFIX"
NEXT_SHORT_STEP = r4r3r3.NEXT_SHORT_STEP

_ORIGINAL_U16C_MIGRATION_PLAN = u16c._migration_plan
_ORIGINAL_FORMAL_PAIR_PASSES = r4r3r3._formal_pair_passes
_INSTALLED = False
_PROBE_LEARNER_ID = "R4R3R4-READING-FORMAL-PROBE"


class ReadingSelectorParityError(ValueError):
    """Fail-closed Reading formal-selector parity error."""


def _normalized_reading_rows(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for source in rows:
        row = dict(source)
        support = str(row.get("support_level") or "")
        row.setdefault("skill", "READING")
        row.setdefault("scored", 1)
        row.setdefault("assessment_candidate", int(support == "TRANSFER"))
        values.append(row)
    return values


def _angle_row(source: Mapping[str, Any], angle: str) -> dict[str, Any]:
    families = tuple(u13.EXACT_SCORED_BINDINGS.get(("READING", str(angle)), ()))
    if not families:
        raise ReadingSelectorParityError(
            f"READING_EFFECTIVE_ANGLE_BINDING_MISSING:{angle}"
        )
    value = dict(source)
    value["skill"] = "READING"
    value["scored"] = 1
    value["assessment_candidate"] = int(
        str(value.get("support_level") or "") == "TRANSFER"
    )
    value["task_angle"] = str(angle)
    value["pattern_family_ids_json"] = u13.canonical(list(families))
    return value


def _formal_assignment_exists(
    activities: Sequence[Mapping[str, Any]],
    *,
    catalog: Sequence[Mapping[str, Any]],
    scoring: Mapping[str, str],
    session_id: str,
) -> bool:
    return r4r2._formal_assignment_exists(
        activities,
        catalog=catalog,
        scoring=scoring,
        learner_id=_PROBE_LEARNER_ID,
        session_id=session_id,
        exposed=set(),
        recent=set(),
    )


def _scene_options(
    rows: Sequence[Mapping[str, Any]],
    *,
    prior: set[str],
    catalog: Sequence[Mapping[str, Any]],
    scoring: Mapping[str, str],
    session_id: str,
) -> list[list[dict[str, Any]]]:
    if len(rows) != 2:
        raise ReadingSelectorParityError("READING_SCENE_ACTIVITY_DENOMINATOR_INVALID")
    supports = {str(row["support_level"]) for row in rows}
    if len(supports) != 1:
        raise ReadingSelectorParityError("READING_SCENE_SUPPORT_DRIFT")
    support = next(iter(supports))
    profile = [
        str(angle)
        for angle in u09.SUPPORT_PROFILES[support]["candidates"]["READING"]
        if str(angle) not in prior
        and u13.EXACT_SCORED_BINDINGS.get(("READING", str(angle)))
    ]
    if len(profile) < 2:
        raise ReadingSelectorParityError(
            f"READING_UNREPEATED_ANGLE_CAPACITY_INSUFFICIENT:{support}"
        )

    ordered_rows = sorted((dict(row) for row in rows), key=lambda row: str(row["activity_id"]))
    profile_index = {angle: index for index, angle in enumerate(profile)}
    options: list[tuple[tuple[Any, ...], list[dict[str, Any]]]] = []
    for angles in itertools.combinations(profile, 2):
        proposed = [
            _angle_row(row, angle)
            for row, angle in zip(ordered_rows, angles)
        ]
        if not _formal_assignment_exists(
            proposed,
            catalog=catalog,
            scoring=scoring,
            session_id=session_id + ":SCENE",
        ):
            continue
        changed = sum(
            str(before["task_angle"]) != str(after["task_angle"])
            for before, after in zip(ordered_rows, proposed)
        )
        key = (
            changed,
            tuple(profile_index[str(after["task_angle"])] for after in proposed),
            tuple(str(after["task_angle"]) for after in proposed),
        )
        options.append((key, proposed))
    options.sort(key=lambda value: value[0])
    return [rows for _key, rows in options]


def choose_form_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    prior: Mapping[str, Mapping[str, set[str]]],
    catalog: Sequence[Mapping[str, Any]],
    scoring: Mapping[str, str],
    session_id: str,
) -> list[dict[str, Any]]:
    """Choose a deterministic Reading form that the installed selector can execute."""
    current = _normalized_reading_rows(rows)
    if len(current) != u13.READING_PER_FORM:
        raise ReadingSelectorParityError(
            f"READING_FORM_ACTIVITY_DENOMINATOR_INVALID:{len(current)}"
        )
    supports = {str(row["support_level"]) for row in current}
    if len(supports) != 1:
        raise ReadingSelectorParityError("READING_FORM_SUPPORT_DRIFT")
    if _formal_assignment_exists(
        current,
        catalog=catalog,
        scoring=scoring,
        session_id=session_id + ":CURRENT",
    ):
        return current

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in current:
        grouped[str(row["scene_ref_id"])].append(row)
    if len(grouped) != u13.SCENES_PER_FORM or any(len(values) != 2 for values in grouped.values()):
        raise ReadingSelectorParityError("READING_FORM_SCENE_ACTIVITY_DENOMINATOR_INVALID")

    scene_refs = sorted(grouped)
    options_by_scene = {
        ref: _scene_options(
            grouped[ref],
            prior=set(prior.get(ref, {}).get("READING", set())),
            catalog=catalog,
            scoring=scoring,
            session_id=f"{session_id}:{ref}",
        )
        for ref in scene_refs
    }
    if any(not options_by_scene[ref] for ref in scene_refs):
        detail = ";".join(f"{ref}={len(options_by_scene[ref])}" for ref in scene_refs)
        raise ReadingSelectorParityError(
            "UNBOUND_READING_FORM_FORMAL_SELECTOR_CAPACITY_UNSAT:" + detail
        )

    chosen: list[dict[str, Any]] = []

    def solve(index: int) -> bool:
        if index == len(scene_refs):
            return _formal_assignment_exists(
                chosen,
                catalog=catalog,
                scoring=scoring,
                session_id=session_id + ":WHOLE",
            )
        ref = scene_refs[index]
        for option in options_by_scene[ref]:
            start = len(chosen)
            chosen.extend(option)
            if _formal_assignment_exists(
                chosen,
                catalog=catalog,
                scoring=scoring,
                session_id=session_id + f":PARTIAL:{index}",
            ) and solve(index + 1):
                return True
            del chosen[start:]
        return False

    if not solve(0):
        detail = ";".join(f"{ref}={len(options_by_scene[ref])}" for ref in scene_refs)
        raise ReadingSelectorParityError(
            "UNBOUND_READING_FORM_FORMAL_SELECTOR_CAPACITY_UNSAT:" + detail
        )
    return sorted(chosen, key=lambda row: str(row["activity_id"]))


def _reading_state(database: Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    state = r4r3r3._formal_runtime_state(Path(database))
    if not isinstance(state, tuple) or len(state) != 2:
        raise ReadingSelectorParityError("READING_FORMAL_RUNTIME_STATE_INVALID")
    catalog_by_skill, scoring_by_skill = state
    if not isinstance(catalog_by_skill, Mapping) or not isinstance(scoring_by_skill, Mapping):
        raise ReadingSelectorParityError("READING_SKILL_SCOPED_RUNTIME_STATE_REQUIRED")
    catalog = catalog_by_skill.get("READING")
    scoring = scoring_by_skill.get("READING")
    if catalog is None or scoring is None:
        raise ReadingSelectorParityError("READING_FORMAL_RUNTIME_STATE_MISSING")
    return list(catalog), dict(scoring)


def _formal_reading_migration_plan(
    database: Path,
    *,
    form_ordinal: int,
    rows: list[dict[str, Any]],
    prior: Mapping[str, Mapping[str, set[str]]],
) -> list[dict[str, str]]:
    database = Path(database)
    if not r4r3r3._formal_schema_present(database):
        return _ORIGINAL_U16C_MIGRATION_PLAN(
            database,
            form_ordinal=form_ordinal,
            rows=rows,
            prior=prior,
        )
    catalog, scoring = _reading_state(database)
    effective = choose_form_rows(
        rows,
        prior=prior,
        catalog=catalog,
        scoring=scoring,
        session_id=f"R4R3R4-F{int(form_ordinal):02d}-READING",
    )
    originals = {str(row["activity_id"]): dict(row) for row in rows}
    plan: list[dict[str, str]] = []
    for row in effective:
        activity_id = str(row["activity_id"])
        before = originals[activity_id]
        original_angle = str(before["task_angle"])
        original_families_json = str(before["pattern_family_ids_json"])
        effective_angle = str(row["task_angle"])
        effective_families_json = str(row["pattern_family_ids_json"])
        if original_angle == effective_angle and original_families_json == effective_families_json:
            continue
        effective_digest = u13.digest(
            {
                "migration_task_id": u16c.TASK_ID,
                "base_activity_id": activity_id,
                "base_activity_digest": str(before["activity_digest"]),
                "effective_task_angle": effective_angle,
                "effective_pattern_family_ids": json.loads(effective_families_json),
            }
        )
        plan.append(
            {
                "activity_id": activity_id,
                "original_task_angle": original_angle,
                "effective_task_angle": effective_angle,
                "original_pattern_family_ids_json": original_families_json,
                "effective_pattern_family_ids_json": effective_families_json,
                "original_activity_digest": str(before["activity_digest"]),
                "effective_activity_digest": effective_digest,
            }
        )
    return plan


def _formal_pair_passes_with_reading_parity(
    *,
    simulated: Sequence[Mapping[str, Any]],
    current_form: int,
    donor_form: int,
    current_choices: Mapping[str, Mapping[str, tuple[str, ...]]],
    donor_choices: Mapping[str, Mapping[str, tuple[str, ...]]],
    catalog: Mapping[str, Sequence[Mapping[str, Any]]],
    scoring: Mapping[str, Mapping[str, str]],
) -> bool:
    reading_catalog = catalog.get("READING")
    reading_scoring = scoring.get("READING")
    writing_catalog = catalog.get("WRITING")
    writing_scoring = scoring.get("WRITING")
    if reading_catalog is None or reading_scoring is None:
        raise ReadingSelectorParityError("READING_FORMAL_STATE_MISSING")
    if writing_catalog is None or writing_scoring is None:
        raise ReadingSelectorParityError("WRITING_FORMAL_STATE_MISSING")

    for form_ordinal in (current_form, donor_form):
        reading_rows = [
            dict(row)
            for row in simulated
            if int(row["form_ordinal"]) == int(form_ordinal)
            and str(row["skill"]) == "READING"
        ]
        prior = r4r3r1._prior_angles_from_rows(simulated, form_ordinal=form_ordinal)
        try:
            choose_form_rows(
                reading_rows,
                prior=prior,
                catalog=reading_catalog,
                scoring=reading_scoring,
                session_id=f"R4R3R4-F{int(form_ordinal):02d}-READING-DONOR-PROBE",
            )
        except ReadingSelectorParityError:
            return False

    if not r4r3r3._writing_form_exists(
        simulated,
        form_ordinal=current_form,
        catalog=writing_catalog,
        scoring=writing_scoring,
    ):
        return False
    if not r4r3r3._writing_form_exists(
        simulated,
        form_ordinal=donor_form,
        catalog=writing_catalog,
        scoring=writing_scoring,
    ):
        return False
    return True


def install() -> None:
    global _INSTALLED
    if installed():
        _INSTALLED = True
        return
    if u16c._migration_plan is not _ORIGINAL_U16C_MIGRATION_PLAN:
        raise ReadingSelectorParityError("U16C_READING_MIGRATION_PLAN_OWNER_DRIFT")
    if r4r3r3._formal_pair_passes is not _ORIGINAL_FORMAL_PAIR_PASSES:
        raise ReadingSelectorParityError("R4R3R3_FORMAL_PAIR_OWNER_DRIFT")
    if not r4r3r3r1.installed():
        raise ReadingSelectorParityError("R4R3R3R1_SKILL_SCOPED_FORMAL_STATE_REQUIRED")
    u16c._migration_plan = _formal_reading_migration_plan
    r4r3r3._formal_pair_passes = _formal_pair_passes_with_reading_parity
    _INSTALLED = True


def installed() -> bool:
    return (
        _INSTALLED
        and u16c._migration_plan is _formal_reading_migration_plan
        and r4r3r3._formal_pair_passes is _formal_pair_passes_with_reading_parity
    )
