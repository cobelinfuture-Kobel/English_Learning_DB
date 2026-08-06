"""Runtime hook for the U01QB16C unbound-form progression migration.

The hook wraps the existing U01QB13 form assembler in place. On an already
cut-over product database it reconciles still-unbound Reading blueprint rows
before the next form is bound. Fresh/private build databases without the product
cutover marker follow the original U01QB13 path unchanged.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ulga.builders import _u01qb16c_existing_product_unbound_form_progression_overlay as overlay
from ulga.builders import (
    build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u13,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "In-place hook on the existing U01QB13 form assembler that invokes the U01QB16C unbound-row migration only for an already-cut-over product database; it creates no second runtime, planner, QuestionBank, scoring authority, learner database, content, audio, speaking scoring, Unit02-24 mutation, or A2 unlock."
PROGRAM_ID = overlay.PROGRAM_ID
TASK_ID = overlay.TASK_ID
PASS_STATUS = overlay.PASS_STATUS
NEXT_SHORT_STEP = overlay.NEXT_SHORT_STEP

_ORIGINAL_ASSEMBLE_FORM_COMPONENT = u13.assemble_form_component
_INSTALLED = False


class UnboundProgressionRuntimeHookError(overlay.UnboundProgressionOverlayError):
    pass


def assemble_form_component_with_progression_overlay(
    database: Path,
    *,
    learner_id: str,
    session_id: str,
    form_ordinal: int,
    selected_at: str | None = None,
) -> dict[str, Any]:
    if overlay.migration_applicable(Path(database)):
        overlay.ensure_migrated(Path(database))
    return _ORIGINAL_ASSEMBLE_FORM_COMPONENT(
        Path(database),
        learner_id=learner_id,
        session_id=session_id,
        form_ordinal=form_ordinal,
        selected_at=selected_at,
    )


def install() -> None:
    global _INSTALLED
    if u13.assemble_form_component is assemble_form_component_with_progression_overlay:
        _INSTALLED = True
        return
    if u13.assemble_form_component is not _ORIGINAL_ASSEMBLE_FORM_COMPONENT:
        raise UnboundProgressionRuntimeHookError(
            "U01QB13_ASSEMBLE_FORM_COMPONENT_ALREADY_PATCHED_BY_OTHER_AUTHORITY"
        )
    u13.assemble_form_component = assemble_form_component_with_progression_overlay
    _INSTALLED = True


def installed() -> bool:
    return _INSTALLED and u13.assemble_form_component is assemble_form_component_with_progression_overlay
