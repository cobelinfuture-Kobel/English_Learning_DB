"""Install R4R2 Writing parity at U16C's existing pre-assemble migration call point.

R4R2 originally wrapped ``matching.assemble_form_component`` directly. That made
its Writing parity logic executable, but violated the existing product ownership
contract: U16C must remain the public assembler owner, and U18E must remain its
internal semantic delegate.

This R1 adapter preserves that topology. U16C already calls its module-level
``migrate_unbound_reading_form`` immediately before delegating to the existing
assembler chain. R1 replaces only that internal pre-assemble callable with a
composition that runs the frozen Reading migration first and the R4R2 unbound
Writing formal-selector parity migration second. Reading and Writing functions
remain skill-gated, so each session changes only its own eligible blueprint rows.

No QuestionBank item, scene, scoring authority, learner attempt, runtime, planner,
database authority, Unit02-24 content, audio, Speaking score or A2 content is
created or modified by this adapter.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ulga.builders import _u01qb13_distinct_item_matching_adapter as matching
from ulga.builders import _u01qb16_learner_visible_distinctness_adapter as visible
from ulga.builders import _u01qb16c_unbound_form_progression_overlay as u16c
from ulga.builders import _u01qb18c_form01_learner_quality_adapter as quality
from ulga.builders import (
    _u01qb18f_r4r2_unbound_writing_selector_parity_fullfix as r4r2,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Ownership-preserving internal pre-assemble composition of the existing U16C "
    "Reading migration with the existing R4R2 unbound Writing selector-parity "
    "migration. It preserves U16C public assembler ownership and U18E internal "
    "semantic ownership; it authors no content and changes no QuestionBank, bound "
    "learner evidence, scoring/runtime/planner/database authority, Unit02-24, audio, "
    "Speaking score, or A2 state."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18F-R4R2-R1_PreserveU16CPublicOwnershipAndInstallWritingParityViaPreAssembleHook"
PASS_STATUS = "PASS_A1FS_V1_U01QB18F_R4R2_R1_U16C_PUBLIC_OWNERSHIP_PRESERVED"
NEXT_SHORT_STEP = r4r2.NEXT_SHORT_STEP

_ORIGINAL_U16C_PRE_ASSEMBLE = u16c.migrate_unbound_reading_form
_INSTALLED = False


class R4R2OwnershipAdapterError(ValueError):
    """Fail-closed ownership-preservation error."""


def pre_assemble_reading_then_writing_parity(
    database: Path,
    *,
    learner_id: str,
    session_id: str,
    form_ordinal: int,
    applied_at: str | None = None,
) -> dict[str, Any]:
    """Run both skill-gated migrations without replacing U16C's assembler owner."""
    reading = _ORIGINAL_U16C_PRE_ASSEMBLE(
        Path(database),
        learner_id=learner_id,
        session_id=session_id,
        form_ordinal=form_ordinal,
        applied_at=applied_at,
    )
    writing = r4r2.migrate_unbound_writing_form(
        Path(database),
        learner_id=learner_id,
        session_id=session_id,
        form_ordinal=form_ordinal,
        applied_at=applied_at,
    )
    return {
        "status": PASS_STATUS,
        "reading": reading,
        "writing": writing,
        "u16c_public_owner_preserved": True,
        "questionbank_modified": False,
        "next_short_step": NEXT_SHORT_STEP,
    }


def install() -> None:
    global _INSTALLED
    if installed():
        _INSTALLED = True
        return
    if not u16c.installed():
        raise R4R2OwnershipAdapterError("U01QB16C_REQUIRED_BEFORE_R4R2_R1")
    if not visible.installed():
        raise R4R2OwnershipAdapterError(
            "U01QB16_VISIBLE_DISTINCTNESS_REQUIRED_BEFORE_R4R2_R1"
        )
    if not quality.installed():
        raise R4R2OwnershipAdapterError(
            "U01QB18C_LEARNER_QUALITY_REQUIRED_BEFORE_R4R2_R1"
        )
    if matching.assemble_form_component is not u16c.assemble_form_component:
        raise R4R2OwnershipAdapterError("U01QB16C_PUBLIC_ASSEMBLER_OWNER_DRIFT")
    if (
        matching.candidate_preserves_scoring_class
        is not quality.candidate_preserves_scoring_class_with_learner_quality
    ):
        raise R4R2OwnershipAdapterError("FORMAL_CANDIDATE_QUALITY_GATE_NOT_ACTIVE")
    current = u16c.migrate_unbound_reading_form
    if current is not _ORIGINAL_U16C_PRE_ASSEMBLE:
        raise R4R2OwnershipAdapterError(
            "U01QB16C_PRE_ASSEMBLE_MIGRATION_ALREADY_PATCHED_BY_OTHER_AUTHORITY"
        )
    u16c.migrate_unbound_reading_form = pre_assemble_reading_then_writing_parity
    _INSTALLED = True

    # Keep direct R4R2 status/introspection callers aligned with the canonical
    # product topology. The legacy direct wrapper is no longer the install path.
    r4r2.install = install
    r4r2.installed = installed


def installed() -> bool:
    return (
        _INSTALLED
        and matching.assemble_form_component is u16c.assemble_form_component
        and u16c.migrate_unbound_reading_form
        is pre_assemble_reading_then_writing_parity
        and matching.candidate_preserves_scoring_class
        is quality.candidate_preserves_scoring_class_with_learner_quality
        and visible.installed()
        and quality.installed()
        and u16c.installed()
    )
