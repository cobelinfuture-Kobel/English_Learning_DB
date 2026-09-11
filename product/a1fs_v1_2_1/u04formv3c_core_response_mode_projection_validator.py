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
REVISION = "FORMV3C_CORE_SIX_RESPONSE_MODE_PROJECTION_V1"
EXPECTED_FORMS = tuple(range(1, 9))
DIRECT_AUTHORED_TEMPLATE = "u04formv3c_direct_authored_form{number:02d}.json"
REDUCED_BLUEPRINT_TEMPLATE = "u04formv3c_reduced_support_blueprint_form{number:02d}.json"


class Unit04CoreResponseProjectionError(ValueError):
    pass


def _root(repo_root: Path | str | None = None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]


def _load_form(root: Path, form_number: int) -> dict[str, Any]:
    product = root / "product" / "a1fs_v1_2_1"
    if form_number <= 4:
        path = product / DIRECT_AUTHORED_TEMPLATE.format(number=form_number)
        if not path.is_file():
            raise Unit04CoreResponseProjectionError(f"FORM_ASSET_MISSING:F{form_number:02d}")
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        form = payload.get("form") or {}
    else:
        path = product / REDUCED_BLUEPRINT_TEMPLATE.format(number=form_number)
        if not path.is_file():
            raise Unit04CoreResponseProjectionError(f"FORM_BLUEPRINT_MISSING:F{form_number:02d}")
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
    return form


def validate_form01_08_core_projection(repo_root: Path | str | None = None) -> dict[str, Any]:
    root = _root(repo_root)
    contract_report = core_contract.validate_contract()
    if contract_report.get("status") != core_contract.STATUS:
        raise Unit04CoreResponseProjectionError("CORE_CONTRACT_NOT_PASS")

    global_counts: Counter[str] = Counter()
    legacy_counts: Counter[str] = Counter()
    deferred_picture_count = 0
    forms: list[dict[str, Any]] = []

    for form_number in EXPECTED_FORMS:
        form = _load_form(root, form_number)
        core_counts: Counter[str] = Counter()
        legacy_form_counts: Counter[str] = Counter()
        deferred = 0

        for task in form["tasks"]:
            legacy_mode = str(task.get("response_mode") or "")
            if not legacy_mode:
                raise Unit04CoreResponseProjectionError(
                    f"RESPONSE_MODE_MISSING:F{form_number:02d}:Q{task.get('question_number')}"
                )
            legacy_form_counts[legacy_mode] += 1
            legacy_counts[legacy_mode] += 1
            try:
                core_mode = core_contract.project_core_response_mode(task)
            except core_contract.CoreResponseModeContractError as exc:
                raise Unit04CoreResponseProjectionError(
                    f"CORE_PROJECTION_FAILED:F{form_number:02d}:Q{task.get('question_number')}:{exc}"
                ) from exc
            if core_mode is None:
                deferred += 1
                deferred_picture_count += 1
                continue
            if core_mode not in core_contract.CORE_RESPONSE_MODES:
                raise Unit04CoreResponseProjectionError(
                    f"CORE_MODE_OUTSIDE_CONTRACT:F{form_number:02d}:{core_mode}"
                )
            core_counts[core_mode] += 1
            global_counts[core_mode] += 1

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
            }
        )

    if set(global_counts) != set(core_contract.CORE_RESPONSE_MODES):
        raise Unit04CoreResponseProjectionError(
            f"GLOBAL_CORE_MODE_COVERAGE_DRIFT:{sorted(global_counts)}"
        )

    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "form_count": len(EXPECTED_FORMS),
        "task_count": len(EXPECTED_FORMS) * 40,
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
    }
