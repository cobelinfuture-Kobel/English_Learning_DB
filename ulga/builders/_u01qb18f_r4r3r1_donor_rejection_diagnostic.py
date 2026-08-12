"""Fail-only read-only diagnostic for R4R3R1 support-stage scene swap failures.

The actual production replay can prove that the current pairwise R4R3R1 donor
search found no admissible scene, but the historical error did not expose why
future same-family scene slots were rejected.  This module inspects the same
blueprint/runtime snapshot without mutating it and reports the donor funnel:
form/ref identity, exposure count, frozen/current-form guards, repeat-gap status,
and the exact Reading/Writing/Speaking capacity result for both sides of a
simulated package swap.

It is diagnostic only.  It does not change the QuestionBank, scene authority,
blueprint, learner evidence, scoring/runtime/planner authority, Unit02-24,
audio, Speaking scoring, or A2 state.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import _u01qb18f_r4r3_runtime_capacity_aware_reuse_scene_migration as r4r3
from ulga.builders import _u01qb18f_r4r3r1_support_stage_scene_swap_fullfix as r4r3r1
from ulga.builders import build_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as u08
from ulga.builders import build_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as runtime_allocation

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only fail-path diagnostic over the existing Unit01 blueprint and 474-item "
    "runtime. It authors no content and changes no QuestionBank, scene, learner "
    "evidence, scoring/runtime/planner/database authority, Unit02-24, audio, Speaking "
    "score, or A2 state."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18F-R4R3R1D_DonorRejectionDiagnostic"
PASS_STATUS = "PASS_A1FS_V1_U01QB18F_R4R3R1_DONOR_REJECTION_DIAGNOSTIC"


def _compact_error(exc: BaseException) -> str:
    text = str(exc).replace("\r", " ").replace("\n", " ").strip()
    return f"{exc.__class__.__name__}:{text}" if text else exc.__class__.__name__


def _skill_capacity(
    *,
    all_rows: Sequence[Mapping[str, Any]],
    form_ordinal: int,
    catalog: Mapping[str, list[dict[str, Any]]],
) -> tuple[bool, str]:
    failures: list[str] = []
    for skill in ("READING", "WRITING", "SPEAKING"):
        try:
            r4r3r1._form_skill_choices(
                all_rows=all_rows,
                form_ordinal=form_ordinal,
                skill=skill,
                catalog=catalog,
            )
        except Exception as exc:  # diagnostic must report structural + capacity failures
            failures.append(f"{skill}={_compact_error(exc)}")
    return not failures, "PASS" if not failures else ",".join(failures)


def _post_swap_repeat_gap(
    *,
    donor_usage: Mapping[str, Any],
    donor_form: int,
    current_form: int,
) -> tuple[bool, str]:
    ordinals = [int(value) for value in donor_usage.get("form_ordinals") or []]
    replaced = False
    effective: list[int] = []
    for ordinal in ordinals:
        if not replaced and ordinal == int(donor_form):
            effective.append(int(current_form))
            replaced = True
        else:
            effective.append(ordinal)
    if not replaced:
        return False, "DONOR_FORM_NOT_IN_USAGE"
    effective = sorted(effective)
    if len(effective) > u08.MAX_EXPOSURES:
        return False, "EXPOSURE_COUNT_ABOVE_MAX:" + ",".join(map(str, effective))
    if len(effective) <= 1:
        return True, "SINGLE_EXPOSURE"
    gap = effective[1] - effective[0]
    return (
        gap >= u08.MIN_REPEAT_FORM_DELTA,
        f"FORMS={effective[0]},{effective[1]};GAP={gap};MIN={u08.MIN_REPEAT_FORM_DELTA}",
    )


def diagnose(
    database: Path,
    *,
    current_form: int,
    failing_ref: str,
) -> list[str]:
    """Return console-safe donor funnel lines without modifying the database."""
    database = Path(database)
    with closing(sqlite3.connect(database)) as connection:
        connection.row_factory = sqlite3.Row
        all_rows = r4r3._all_rows(connection)
        frozen_forms = r4r3r1._bound_form_ordinals(connection)

    usage = r4r3._scene_usage(all_rows)
    failing_usage = usage.get(str(failing_ref))
    if failing_usage is None:
        return [
            f"R4R3R1_DIAGNOSTIC_STATUS={PASS_STATUS}",
            f"R4R3R1_DIAGNOSTIC_ERROR=FAILING_SCENE_USAGE_MISSING:{failing_ref}",
        ]

    family = str(failing_usage["situation_family"])
    current_refs = {
        str(row["scene_ref_id"])
        for row in all_rows
        if int(row["form_ordinal"]) == int(current_form)
    }
    catalog = runtime_allocation._catalog(database)
    records: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()

    for row in all_rows:
        donor_form = int(row["form_ordinal"])
        donor_ref = str(row["scene_ref_id"])
        key = (donor_form, donor_ref)
        if key in seen:
            continue
        seen.add(key)
        donor_usage = usage.get(donor_ref)
        if donor_usage is None:
            continue
        if donor_form <= int(current_form):
            continue
        if str(donor_usage["situation_family"]) != family:
            continue

        exposure_count = int(donor_usage["exposure_count"])
        record: dict[str, Any] = {
            "form": donor_form,
            "ref": donor_ref,
            "exposure_count": exposure_count,
            "legacy_single": exposure_count == 1,
            "frozen": donor_form in frozen_forms,
            "in_current": donor_ref in current_refs,
            "same_as_failing": donor_ref == str(failing_ref),
            "failing_already_in_donor_form": False,
            "repeat_gap_pass": False,
            "repeat_gap_detail": "NOT_EVALUATED",
            "current_capacity_pass": False,
            "current_capacity_detail": "NOT_EVALUATED",
            "donor_capacity_pass": False,
            "donor_capacity_detail": "NOT_EVALUATED",
            "broader_pair_pass": False,
        }
        donor_form_refs = {
            str(value["scene_ref_id"])
            for value in all_rows
            if int(value["form_ordinal"]) == donor_form
        }
        record["failing_already_in_donor_form"] = str(failing_ref) in donor_form_refs

        structural_block = (
            record["frozen"]
            or record["in_current"]
            or record["same_as_failing"]
            or record["failing_already_in_donor_form"]
        )
        if not structural_block:
            repeat_ok, repeat_detail = _post_swap_repeat_gap(
                donor_usage=donor_usage,
                donor_form=donor_form,
                current_form=current_form,
            )
            record["repeat_gap_pass"] = repeat_ok
            record["repeat_gap_detail"] = repeat_detail
            try:
                simulated = r4r3r1._swap_scene_packages_in_memory(
                    all_rows,
                    current_form=current_form,
                    failing_ref=failing_ref,
                    donor_form=donor_form,
                    donor_ref=donor_ref,
                )
                current_ok, current_detail = _skill_capacity(
                    all_rows=simulated,
                    form_ordinal=current_form,
                    catalog=catalog,
                )
                donor_ok, donor_detail = _skill_capacity(
                    all_rows=simulated,
                    form_ordinal=donor_form,
                    catalog=catalog,
                )
                record["current_capacity_pass"] = current_ok
                record["current_capacity_detail"] = current_detail
                record["donor_capacity_pass"] = donor_ok
                record["donor_capacity_detail"] = donor_detail
                record["broader_pair_pass"] = bool(repeat_ok and current_ok and donor_ok)
            except Exception as exc:
                record["current_capacity_detail"] = "SIMULATION=" + _compact_error(exc)
        records.append(record)

    legacy_count = sum(
        bool(row["legacy_single"])
        and not bool(row["frozen"])
        and not bool(row["in_current"])
        and not bool(row["same_as_failing"])
        and not bool(row["failing_already_in_donor_form"])
        for row in records
    )
    broader_pass_count = sum(bool(row["broader_pair_pass"]) for row in records)
    lines = [
        f"R4R3R1_DIAGNOSTIC_STATUS={PASS_STATUS}",
        f"R4R3R1_FAILING_SCENE={failing_ref}",
        f"R4R3R1_FAILING_FORM={int(current_form)}",
        f"R4R3R1_FAILING_FAMILY={family}",
        f"R4R3R1_FAILING_EXPOSURE_COUNT={int(failing_usage['exposure_count'])}",
        f"R4R3R1_FUTURE_SAME_FAMILY_SLOT_COUNT={len(records)}",
        f"R4R3R1_LEGACY_SINGLE_EXPOSURE_CANDIDATE_COUNT={legacy_count}",
        f"R4R3R1_BROADER_PAIR_CAPACITY_PASS_COUNT={broader_pass_count}",
    ]
    for record in sorted(records, key=lambda value: (int(value["form"]), str(value["ref"]))):
        lines.append(
            "R4R3R1_DONOR="
            f"F{int(record['form']):02d}|{record['ref']}|"
            f"exposures={int(record['exposure_count'])}|"
            f"legacy_single={str(bool(record['legacy_single'])).lower()}|"
            f"frozen={str(bool(record['frozen'])).lower()}|"
            f"in_current={str(bool(record['in_current'])).lower()}|"
            f"failing_in_donor={str(bool(record['failing_already_in_donor_form'])).lower()}|"
            f"repeat_gap={record['repeat_gap_detail']}|"
            f"current={record['current_capacity_detail']}|"
            f"donor={record['donor_capacity_detail']}|"
            f"broader_pair_pass={str(bool(record['broader_pair_pass'])).lower()}"
        )
    return lines
