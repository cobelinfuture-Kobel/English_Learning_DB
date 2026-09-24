from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1 import a1fs_v1_core_response_mode_contract as core_contract

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Mechanical taxonomy projection only over already-authored Unit04 FormV3C tasks. "
    "This validator does not author learner content or assign pedagogical task families."
)

TASK_ID = "A1FS-V1-U04FORMV3C-CoreResponseModeProjection"
STATUS = "PASS_A1FS_V1_U04FORMV3C_CORE_RESPONSE_MODE_PROJECTION_FORM01_TO08"
REVISION = "FORMV3C_CORE_SIX_RESPONSE_MODE_PROJECTION_V2_DIRECT_FORM05_TO08"
EXPECTED_FORMS = tuple(range(1, 9))
DIRECT_AUTHORED_TEMPLATE = "u04formv3c_direct_authored_form{number:02d}.json"


class Unit04CoreResponseProjectionError(ValueError):
    pass


def _root(repo_root: Path | str | None = None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]


def _load_form(root: Path, form_number: int) -> tuple[dict[str, Any], bool]:
    product = root / "product" / "a1fs_v1_2_1"
    path = product / DIRECT_AUTHORED_TEMPLATE.format(number=form_number)
    if not path.is_file():
        raise Unit04CoreResponseProjectionError(f"FORM_ASSET_MISSING:F{form_number:02d}")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    form = payload.get("form") or {}
    if form.get("form_number") != form_number:
        raise Unit04CoreResponseProjectionError(f"FORM_NUMBER_DRIFT:F{form_number:02d}")
    tasks = list(form.get("tasks") or [])
    if len(tasks) != 40:
        raise Unit04CoreResponseProjectionError(
            f"TASK_COUNT_DRIFT:F{form_number:02d}:{len(tasks)}"
        )
    uses_core_native_schema = form_number >= 5
    if uses_core_native_schema:
        expected_schema = "a1fs.v1.u04.formv3c.direct_authored_reduced_support.v1"
        if payload.get("schema_version") != expected_schema:
            raise Unit04CoreResponseProjectionError(
                f"CORE_NATIVE_SCHEMA_DRIFT:F{form_number:02d}"
            )
    return form, uses_core_native_schema


def _legacy_projection_task(task: dict[str, Any], uses_core_native_schema: bool) -> tuple[dict[str, Any], str]:
    if not uses_core_native_schema:
        legacy_mode = str(task.get("response_mode") or "")
        if not legacy_mode:
            raise Unit04CoreResponseProjectionError("LEGACY_RESPONSE_MODE_MISSING")
        return dict(task), legacy_mode

    legacy_mode = str(task.get("legacy_response_mode") or "")
    if not legacy_mode:
        raise Unit04CoreResponseProjectionError("LEGACY_RESPONSE_MODE_MISSING")
    projection_task = dict(task)
    projection_task["response_mode"] = legacy_mode
    return projection_task, legacy_mode


def validate_form01_08_core_projection(repo_root: Path | str | None = None) -> dict[str, Any]:
    root = _root(repo_root)
    contract_report = core_contract.validate_contract()
    if contract_report.get("status") != core_contract.STATUS:
        raise Unit04CoreResponseProjectionError("CORE_CONTRACT_NOT_PASS")

    global_counts: Counter[str] = Counter()
    legacy_counts: Counter[str] = Counter()
    deferred_picture_count = 0
    core_native_task_count = 0
    forms: list[dict[str, Any]] = []

    for form_number in EXPECTED_FORMS:
        form, uses_core_native_schema = _load_form(root, form_number)
        core_counts: Counter[str] = Counter()
        legacy_form_counts: Counter[str] = Counter()
        deferred = 0

        for task in form["tasks"]:
            projection_task, legacy_mode = _legacy_projection_task(
                task, uses_core_native_schema
            )
            legacy_form_counts[legacy_mode] += 1
            legacy_counts[legacy_mode] += 1
            try:
                projected = core_contract.project_core_response_mode(projection_task)
            except core_contract.CoreResponseModeContractError as exc:
                raise Unit04CoreResponseProjectionError(
                    f"CORE_PROJECTION_FAILED:F{form_number:02d}:"
                    f"Q{task.get('question_number')}:{exc}"
                ) from exc

            if uses_core_native_schema:
                authored_core = task.get("response_mode")
                if authored_core != projected:
                    raise Unit04CoreResponseProjectionError(
                        f"CORE_NATIVE_MODE_DRIFT:F{form_number:02d}:"
                        f"Q{task.get('question_number')}:{authored_core}:{projected}"
                    )
                if not str(task.get("response_format") or "").strip():
                    raise Unit04CoreResponseProjectionError(
                        f"RESPONSE_FORMAT_MISSING:F{form_number:02d}:"
                        f"Q{task.get('question_number')}"
                    )
                core_native_task_count += 1

            if projected is None:
                deferred += 1
                deferred_picture_count += 1
                continue
            if projected not in core_contract.CORE_RESPONSE_MODES:
                raise Unit04CoreResponseProjectionError(
                    f"CORE_MODE_OUTSIDE_CONTRACT:F{form_number:02d}:{projected}"
                )
            core_counts[projected] += 1
            global_counts[projected] += 1

        if sum(core_counts.values()) + deferred != 40:
            raise Unit04CoreResponseProjectionError(
                f"PROJECTION_TOTAL_DRIFT:F{form_number:02d}"
            )
        forms.append(
            {
                "form_number": form_number,
                "core_response_mode_counts": dict(sorted(core_counts.items())),
                "core_response_mode_coverage": sorted(core_counts),
                "core_response_mode_coverage_count": len(core_counts),
                "legacy_response_mode_count": len(legacy_form_counts),
                "legacy_response_mode_counts": dict(sorted(legacy_form_counts.items())),
                "deferred_picture_task_count": deferred,
                "non_picture_task_count": sum(core_counts.values()),
                "core_native_response_mode_schema": uses_core_native_schema,
            }
        )

    if set(global_counts) != set(core_contract.CORE_RESPONSE_MODES):
        raise Unit04CoreResponseProjectionError(
            f"GLOBAL_CORE_MODE_COVERAGE_DRIFT:{sorted(global_counts)}"
        )
    if core_native_task_count != 160:
        raise Unit04CoreResponseProjectionError(
            f"CORE_NATIVE_TASK_COUNT_DRIFT:{core_native_task_count}"
        )

    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "form_count": len(EXPECTED_FORMS),
        "task_count": len(EXPECTED_FORMS) * 40,
        "core_native_task_count": core_native_task_count,
        "core_native_form_numbers": [5, 6, 7, 8],
        "core_response_mode_count": len(core_contract.CORE_RESPONSE_MODES),
        "core_response_modes": list(core_contract.CORE_RESPONSE_MODES),
        "core_response_mode_counts": dict(sorted(global_counts.items())),
        "legacy_response_mode_counts": dict(sorted(legacy_counts.items())),
        "deferred_picture_task_count": deferred_picture_count,
        "picture_interaction_active": core_contract.PICTURE_INTERACTION_ACTIVE,
        "forms": forms,
        "learner_content_changed": False,
        "task_family_changed": False,
        "assessment_capability_changed": False,
        "learner_content_changed_by_projection": False,
        "task_family_changed_by_projection": False,
        "assessment_capability_changed_by_projection": False,
    }
