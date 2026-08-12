"""Install R4R2 Writing parity at the U16C-owned assembler boundary.

R4R2 originally wrapped ``matching.assemble_form_component`` directly, which
violated U16C public ownership. R1 then composed Writing parity by replacing
``u16c.migrate_unbound_reading_form``; that restored assembler ownership but
broke U16C's direct migration API contract.

R2 preserves both contracts. It leaves ``migrate_unbound_reading_form`` exactly
unchanged and installs one U16C-owned assembler wrapper. The wrapper runs the
skill-gated R4R2 unbound-Writing formal-selector parity migration, then delegates
to the original U16C assembler, which continues to run its own Reading migration
and its existing U18E semantic delegate. ``matching.assemble_form_component``
and ``u16c.assemble_form_component`` are moved together to the same function, so
U16C remains the public owner and ``u16c.installed()`` stays true.

No QuestionBank item, scene, scoring authority, learner attempt, runtime, planner,
database authority, Unit02-24 content, audio, Speaking score or A2 content is
created or modified by this adapter.
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

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Ownership-preserving U16C assembler hook for the existing R4R2 unbound Writing "
    "selector-parity migration. It preserves the exact U16C direct Reading-migration "
    "API, U16C public assembler ownership and U18E internal semantic ownership; it "
    "authors no content and changes no QuestionBank, bound learner evidence, scoring/"
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
    """Run Writing parity, then delegate to the unchanged U16C assembler chain."""
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

    # Move the public owner references together. The original U16C assembler remains
    # the delegate and still owns Reading migration + the U18E semantic chain.
    u16c.assemble_form_component = assemble_form_component_with_writing_parity
    matching.assemble_form_component = assemble_form_component_with_writing_parity
    _INSTALLED = True

    # Keep direct R4R2 status/introspection callers aligned with product topology.
    r4r2.install = install
    r4r2.installed = installed


def installed() -> bool:
    return (
        _INSTALLED
        and u16c.migrate_unbound_reading_form is _ORIGINAL_U16C_READING_MIGRATION
        and u16c.assemble_form_component
        is assemble_form_component_with_writing_parity
        and matching.assemble_form_component
        is assemble_form_component_with_writing_parity
        and matching.assemble_form_component is u16c.assemble_form_component
        and matching.candidate_preserves_scoring_class
        is quality.candidate_preserves_scoring_class_with_learner_quality
        and visible.installed()
        and quality.installed()
        and u16c.installed()
    )
