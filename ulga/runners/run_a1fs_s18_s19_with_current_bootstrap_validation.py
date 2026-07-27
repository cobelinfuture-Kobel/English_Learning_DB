#!/usr/bin/env python3
"""Run S18/S19 materialization with the current S17 bootstrap identity contract.

The legacy S10 helper correctly validates the 24-unit/72-lesson/264-asset
structure, but it also hard-codes the old S09 task and product identities. S18
and S19 execute the evolved S17 application, whose bootstrap intentionally
publishes S17 identity. This runner preserves the legacy structural validator
while replacing only its obsolete identity precondition with the exact current
S17 no-audio product contract.
"""
from __future__ import annotations

import sys
from copy import deepcopy
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_online_v1_s18_nonaudio_learner_product_e2e_release_acceptance_recovery as s18
from ulga.builders import build_a1fs_online_v1_s19_localhost_nonaudio_learner_product_release_candidate as s19

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Bridges the evolved S17 bootstrap identity to the existing S10 structural denominator validator for S18/S19 acceptance; it creates no learner content, curriculum, scoring, mastery, dashboard, audio, A2, Cloudflare route, release capability, or parallel authority."

_s10 = s18.s17.s16.s15.s11.s10
_LEGACY_VALIDATE_BOOTSTRAP = _s10._validate_bootstrap


def _current_s17_bootstrap_identity_valid(bootstrap: Mapping[str, Any]) -> bool:
    semantics = bootstrap.get("learner_product_semantics")
    return (
        bootstrap.get("task_id") == s18.s17.TASK_ID
        and bootstrap.get("schema_version") == s18.s17.SCHEMA_VERSION
        and bootstrap.get("validation_status") == s18.s17.PASS_STATUS
        and bootstrap.get("product_status") == s18.s17.PRODUCT_STATUS
        and bootstrap.get("release_profile") == s18.s17.RELEASE_PROFILE
        and bootstrap.get("audio_enabled") is False
        and bootstrap.get("speaking_capture_enabled") is False
        and bootstrap.get("unit_count") == 24
        and isinstance(semantics, Mapping)
        and semantics.get("canonical_m7_mastery_connected") is True
        and semantics.get("canonical_m7_remediation_connected") is True
        and semantics.get("canonical_m7_reassessment_connected") is True
        and semantics.get("canonical_m8_review_schedule_connected") is True
        and semantics.get("learner_dashboard_connected") is True
        and semantics.get("parent_dashboard_connected") is True
        and semantics.get("teacher_dashboard_connected") is True
        and semantics.get("human_review_queue_connected") is True
        and semantics.get("role_based_identity_authorization_claimed") is False
        and semantics.get("a2_unlock_enabled") is False
    )


def validate_current_s17_bootstrap(bootstrap: Mapping[str, Any]) -> dict[str, int]:
    """Validate S17 identity/boundaries and reuse S10's structural denominator gate."""
    if not _current_s17_bootstrap_identity_valid(bootstrap):
        raise s18.E2ERecoveryError("http_bootstrap_current_s17_identity_or_boundary_invalid")

    projected = deepcopy(dict(bootstrap))
    projected.update({
        "task_id": _s10.s09.TASK_ID,
        "validation_status": _s10.s09.PASS_STATUS,
        "product_status": _s10.s09.PRODUCT_STATUS,
    })
    try:
        return _LEGACY_VALIDATE_BOOTSTRAP(projected)
    except _s10.ReleaseCandidateError as exc:
        raise s18.E2ERecoveryError(f"http_bootstrap_current_s17_structure_invalid:{exc}") from exc


def activate_current_bootstrap_validation() -> None:
    """Patch the one shared S10 helper used by both S18 and S19 materializers."""
    _s10._validate_bootstrap = validate_current_s17_bootstrap


def main(argv: Sequence[str] | None = None) -> int:
    effective = list(sys.argv[1:] if argv is None else argv)
    if not effective or effective[0] not in {"s18", "s19"}:
        print("FAIL:target_stage_must_be_s18_or_s19", file=sys.stderr)
        return 2
    target = effective.pop(0)
    activate_current_bootstrap_validation()
    return s18.main(effective) if target == "s18" else s19.main(effective)


if __name__ == "__main__":
    raise SystemExit(main())
