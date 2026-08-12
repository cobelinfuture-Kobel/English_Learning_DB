"""Preserve the full scored-activity schema in R4R3 donor simulations.

Actual production R4 replay reached the R4R3R3 formal matcher and failed with
``KeyError: 'assessment_candidate'``.  The canonical blueprint table contains
``scored`` and ``assessment_candidate``, and the real U01QB13/R4R2 formal selector
uses both fields.  R4R3's historical ``_all_rows`` helper projected a smaller
scene-rotation shape and omitted those columns, so downstream donor simulation
silently dropped formal assessment metadata before R4R3R3 invoked R4R2.

R4R3R3R2 changes only that private read projection.  The scene swap itself still
modifies only scene identity/anchors; scored/assessment flags are carried through
unchanged from ``u01qb13_blueprint_activities``.  No content, QuestionBank item,
learner evidence, runtime/planner/scoring authority, Unit02-24 state, audio,
Speaking scoring or A2 state is changed.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from ulga.builders import _u01qb18f_r4r3_runtime_capacity_aware_reuse_scene_migration as r4r3

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Private read-projection schema parity adapter for existing Unit01 donor simulation. "
    "It preserves canonical scored/assessment metadata and authors no content; changes no "
    "QuestionBank, learner evidence, runtime/planner/scoring authority, Unit02-24, audio, "
    "Speaking scoring or A2 state."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18F-R4R3R3R2_FormalProbeRowSchemaParityFullFix"
PASS_STATUS = "PASS_A1FS_V1_U01QB18F_R4R3R3R2_FORMAL_PROBE_ROW_SCHEMA_PARITY_FULLFIX"
NEXT_SHORT_STEP = r4r3.NEXT_SHORT_STEP

_ORIGINAL_ALL_ROWS = r4r3._all_rows
_INSTALLED = False


class FormalProbeRowSchemaParityError(ValueError):
    """Fail-closed R4R3R3R2 projection/installation error."""


def _formal_complete_all_rows(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    """Read the existing blueprint with every field required by formal selectors."""
    return [
        dict(row)
        for row in connection.execute(
            """SELECT activity_id,form_id,form_ordinal,scene_ref_id,situation_family,
                      setting,skill,task_angle,support_level,scored,
                      assessment_candidate,pattern_family_ids_json,scene_anchors_json,
                      practice_projection_json,activity_digest
               FROM u01qb13_blueprint_activities
               ORDER BY form_ordinal,activity_id"""
        )
    ]


def install() -> None:
    global _INSTALLED
    if installed():
        _INSTALLED = True
        return
    if r4r3._all_rows is not _ORIGINAL_ALL_ROWS:
        raise FormalProbeRowSchemaParityError("R4R3_ALL_ROWS_OWNER_DRIFT")
    r4r3._all_rows = _formal_complete_all_rows
    _INSTALLED = True


def installed() -> bool:
    return _INSTALLED and r4r3._all_rows is _formal_complete_all_rows
