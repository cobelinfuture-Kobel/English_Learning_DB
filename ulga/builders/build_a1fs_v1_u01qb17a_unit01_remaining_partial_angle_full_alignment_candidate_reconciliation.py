#!/usr/bin/env python3
"""Fail closed: U01QB12 is the canonical PF16/PF17 full-alignment authority.

PR #484 briefly introduced a redundant U01QB17A content-authority path after
misreading the historical U01QB10 partial-coverage readback. Mainline inspection
confirmed that U01QB12 already closed those exact partials, migrated the same
288 + 186 = 474 runtime, and U01QB13 consumes its PF16/PF17 identities.

This protected builder path is retained only as a governance-compatible tombstone.
It cannot build, admit, materialize, migrate, or modify learner-facing content.
"""
from __future__ import annotations

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Fail-closed compatibility tombstone only. Canonical PF16/PF17 content and "
    "runtime authority already exists in A1FS-V1-U01QB12; this module creates no "
    "candidate, approved artifact, QuestionBank item, runtime migration, learner "
    "state, scoring change, Unit02-24 content, audio, Speaking score, or A2 state."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB17A_CanonicalU01QB12AuthorityReconciliationAndDuplicateRollback"
PASS_STATUS = "PASS_A1FS_V1_U01QB17A_CANONICAL_U01QB12_AUTHORITY_RECONCILIATION"
CANONICAL_AUTHORITY_TASK_ID = (
    "A1FS-V1-U01QB12_Unit01ReferenceEvidenceAndPhraseConstructionPartialCoverageFullFix"
)
CANONICAL_RUNTIME_COUNT = 474
NEXT_SHORT_STEP = (
    "A1FS-V1-U01QB17B_Unit01TwelveFormLearnerVisibleProductionQualityAndProgressionAcceptance"
)


class RedundantAuthorityForbidden(RuntimeError):
    """Raised whenever the retired U01QB17A content path is invoked."""


def canonical_readback() -> dict[str, object]:
    return {
        "status": PASS_STATUS,
        "task_id": TASK_ID,
        "canonical_authority_task_id": CANONICAL_AUTHORITY_TASK_ID,
        "canonical_runtime_count": CANONICAL_RUNTIME_COUNT,
        "duplicate_content_authority_active": False,
        "candidate_generation_allowed": False,
        "runtime_migration_allowed": False,
        "learner_state_modified": False,
        "next_short_step": NEXT_SHORT_STEP,
    }


def _forbidden(*_args: object, **_kwargs: object) -> None:
    raise RedundantAuthorityForbidden(
        "U01QB17A_REDUNDANT_AUTHORITY_FORBIDDEN:USE_CANONICAL_U01QB12"
    )


build_candidate = _forbidden
admit_candidate = _forbidden
materialize = _forbidden
reconciled_payload = _forbidden


def main() -> int:
    value = canonical_readback()
    print(f"STATUS={value['status']}")
    print(f"CANONICAL_AUTHORITY_TASK_ID={value['canonical_authority_task_id']}")
    print(f"CANONICAL_RUNTIME_COUNT={value['canonical_runtime_count']}")
    print("DUPLICATE_CONTENT_AUTHORITY_ACTIVE=False")
    print(f"NEXT_SHORT_STEP={value['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
