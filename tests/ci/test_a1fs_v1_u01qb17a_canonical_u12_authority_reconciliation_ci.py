from __future__ import annotations

import pytest

from ulga.builders import (
    build_a1fs_v1_u01qb12_unit01_reference_evidence_and_phrase_construction_partial_coverage_fullfix as u12,
)
from ulga.builders import (
    build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u13,
)
from ulga.builders import (
    build_a1fs_v1_u01qb17a_unit01_remaining_partial_angle_full_alignment_candidate_reconciliation as u17a,
)


def test_canonical_pf16_pf17_authority_is_existing_u01qb12() -> None:
    payload = u12.reconciled_payload()
    items = payload["reconciled_items"]
    pf16 = [row for row in items if row["pattern_family_id"] == u12.PF16]
    pf17 = [row for row in items if row["pattern_family_id"] == u12.PF17]

    assert u12.TASK_ID == u17a.CANONICAL_AUTHORITY_TASK_ID
    assert len(pf16) == u12.EXPECTED_REFERENCE_EVIDENCE_COUNT == 24
    assert len(pf17) == u12.EXPECTED_PHRASE_CONSTRUCTION_COUNT == 12
    assert u12.EXPECTED_RUNTIME_COUNT == u17a.CANONICAL_RUNTIME_COUNT == 474


def test_u01qb13_already_consumes_u01qb12_exact_pf16_pf17_bindings() -> None:
    assert u13.PF16 == u12.PF16
    assert u13.PF17 == u12.PF17
    assert u13.EXACT_SCORED_BINDINGS[("READING", "REFERENCE_EVIDENCE")] == (u12.PF16,)
    assert u13.EXACT_SCORED_BINDINGS[("WRITING", "PHRASE_CONSTRUCTION")] == (u12.PF17,)
    assert u13.EXPECTED_RUNTIME_COUNT == 474


def test_redundant_u01qb17a_content_entrypoints_fail_closed() -> None:
    readback = u17a.canonical_readback()
    assert readback["duplicate_content_authority_active"] is False
    assert readback["candidate_generation_allowed"] is False
    assert readback["runtime_migration_allowed"] is False
    assert readback["learner_state_modified"] is False
    assert readback["next_short_step"].startswith("A1FS-V1-U01QB17B_")

    for action in (
        u17a.build_candidate,
        u17a.admit_candidate,
        u17a.materialize,
        u17a.reconciled_payload,
    ):
        with pytest.raises(
            u17a.RedundantAuthorityForbidden,
            match="U01QB17A_REDUNDANT_AUTHORITY_FORBIDDEN:USE_CANONICAL_U01QB12",
        ):
            action()


def test_u01qb17a_tombstone_is_not_a_content_producer() -> None:
    assert u17a.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert u17a.A1FS_CONTENT_POLICY_EXEMPTION
    assert u17a.CANONICAL_RUNTIME_COUNT == 474
