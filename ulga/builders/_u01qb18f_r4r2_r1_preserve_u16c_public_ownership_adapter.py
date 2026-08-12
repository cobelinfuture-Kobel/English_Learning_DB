"""Install the Unit01 unbound-form FullFix chain at the U16C-owned assembler boundary.

The public owner remains U16C. Before its unchanged Reading migration executes,
this wrapper composes three bounded migrations in order:

1. R4R3R1 swaps a single-exposure scene with a later same-family scene when its
   assigned support stage has no executable runtime capacity.
2. R4R3 handles the distinct reused-scene case where a second exposure has no
   enough unrepeated task angles.
3. R4R2 restores unbound Writing selector parity.

The original U16C assembler then performs its own Reading migration and existing
U18E semantic delegate. ``matching`` and U16C remain pointed at the same public
owner function and ``migrate_unbound_reading_form`` itself is not replaced.

No QuestionBank item, scoring authority, learner attempt, runtime, planner,
database authority, Unit02-24 content, audio, Speaking score or A2 content is
created by this adapter.
"""
from __future__ import annotations

from pathlib import Path

from ulga.builders import _u01qb13_distinct_item_matching_adapter as matching
from ulga.builders import _u01qb16_learner_visible_distinctness_adapter as visible
from ulga.builders import _u01qb16c_unbound_form_progression_overlay as u16c
from ulga.builders import _u01qb18c_form01_learner_quality_adapter as quality
from ulga.builders import (
    _u01qb18f_r4r2_unbound_writing_selector_parity_fullfix as r4r2,
)
from ulga.builders import (
    _u01qb18f_r4r3_runtime_capacity_aware_reuse_scene_migration as r4r3,
)
from ulga.builders import (
    _u01qb18f_r4r3r1_support_stage_scene_swap_fullfix as r4r3r1,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Ownership-preserving U16C assembler hook for the existing R4R3R1 support-stage "
    "scene assignment repair, R4R3 reuse-scene capacity migration and R4R2 unbound "
    "Writing selector-parity migration. It preserves the exact U16C direct Reading-"
    "migration API, U16C public assembler ownership and U18E internal semantic ownership; "
    "it authors no content and changes no QuestionBank, bound learner evidence, scoring/"
    "runtime/planner/database authority, Unit02-24, audio, Speaking score, or A2 state."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18F-R4R2-R2_TrueU16CAssemblerPreHookWithoutDirectMigrationAPIOverride"
PASS_STATUS = "PASS_A1FS_V1_U01QB18F_R4R2_R2_U16C_DIRECT_MIGRATION_API_PRESERVED"
NEXT_SHORT_STEP = r4r2.NEXT_SHORT_STEP

_ORIGINAL_U16C_ASSEMBLER = u16c.assemble_form_component
_ORIGINAL_U16C_READING_MIGRATION = u16c.migrate_unbound_reading_form
_INSTALLED = False


class R4R2OwnershipAdapterError(ValueError):
    """Fail-closed ownership-preservation error."""


def assemble_form_component_with_writing_parity(
    database,
    *,
    learner_id: str,
    session_id: str,
    form_ordinal: int,
    selected_at: str | None = None,
):
    """Repair support-stage/reuse capacity, run Writing parity, then delegate to U16C."""
    r4r3r1.migrate_unbound_support_stage_scene_assignment(
        Path(database),
        learner_id=learner_id,
        session_id=session_id,
        form_ordinal=form_ordinal,
        applied_at=selected_at,
    )
    r4r3.migrate_unbound_form_reuse_scene(
        Path(database),
        learner_id=learner_id,
        session_id=session_id,
        form_ordinal=form_ordinal,
        applied_at=selected_at,
    )
    r4r2.migrate_unbound_writing_form(
        Path(database),
        learner_id=learner_id,
        session_id=session_id,
        form_ordinal=form_ordinal,
        applied_at=selected_at,
    )
    return _ORIGINAL_U16C_ASSEMBLER(
        database,
        learner_id=learner_id,
        session_id=session_id,
        form_ordinal=form_ordinal,
        selected_at=selected_at,
    )


def install() -> None:
    global _INSTALLED
    if installed():
        _INSTALLED = True
        return
    if not u16c.installed():
        raise R4R2OwnershipAdapterError("U01QB16C_REQUIRED_BEFORE_R4R2_R2")
    if not visible.installed():
        raise R4R2OwnershipAdapterError(
            "U01QB16_VISIBLE_DISTINCTNESS_REQUIRED_BEFORE_R4R2_R2"
        )
    if not quality.installed():
        raise R4R2OwnershipAdapterError(
            "U01QB18C_LEARNER_QUALITY_REQUIRED_BEFORE_R4R2_R2"
        )
    if matching.assemble_form_component is not _ORIGINAL_U16C_ASSEMBLER:
        raise R4R2OwnershipAdapterError("U01QB16C_PUBLIC_ASSEMBLER_OWNER_DRIFT")
    if u16c.assemble_form_component is not _ORIGINAL_U16C_ASSEMBLER:
        raise R4R2OwnershipAdapterError("U01QB16C_MODULE_ASSEMBLER_OWNER_DRIFT")
    if u16c.migrate_unbound_reading_form is not _ORIGINAL_U16C_READING_MIGRATION:
        raise R4R2OwnershipAdapterError("U01QB16C_DIRECT_MIGRATION_API_DRIFT")
    if (
        matching.candidate_preserves_scoring_class
        is not quality.candidate_preserves_scoring_class_with_learner_quality
    ):
        raise R4R2OwnershipAdapterError("FORMAL_CANDIDATE_QUALITY_GATE_NOT_ACTIVE")

    u16c.assemble_form_component = assemble_form_component_with_writing_parity
    matching.assemble_form_component = assemble_form_component_with_writing_parity
    _INSTALLED = True

    r4r2.install = install
    r4r2.installed = installed


def installed() -> bool:
    return (
        _INSTALLED
        and u16c.migrate_unbound_reading_form is _ORIGINAL_U16C_READING_MIGRATION
        and u16c.assemble_form_component is assemble_form_component_with_writing_parity
        and matching.assemble_form_component is assemble_form_component_with_writing_parity
        and matching.assemble_form_component is u16c.assemble_form_component
        and matching.candidate_preserves_scoring_class
        is quality.candidate_preserves_scoring_class_with_learner_quality
        and visible.installed()
        and quality.installed()
        and u16c.installed()
    )
