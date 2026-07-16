#!/usr/bin/env python3
"""Compatibility and unresolved-review guards for the canonical M12E builder.

M12D reports generated before the partial-batch FullFix did not contain
``remaining_batch_attempt_count``. This wrapper normalizes only exact-complete
legacy reports. It also keeps any ``HUMAN_DEFER`` outcome on the M12E1 review
gate: a defer is a materialized decision, but it is not a resolved learning
evidence decision. All canonical coverage, scoring, registry, ledger, query,
origin, status, and prior-plus-eight checks remain in the unchanged core.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m12e_representative_pilot_evidence_qa_core as _core  # noqa: E402

for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

_original_read_json = _core.read_json
_original_build_qa = _core.build_qa


def read_json(path: Path) -> dict[str, Any]:
    value = _original_read_json(path)
    if path.name != "representative_pilot_expansion_safe_report.json":
        return value
    if "remaining_batch_attempt_count" in value:
        return value

    prior_attempts = value.get("prior_attempt_count")
    cumulative_attempts = value.get("cumulative_attempt_count")
    legacy_exact_complete = (
        value.get("mode") == "IMPORT"
        and value.get("batch_attempt_count") == 8
        and isinstance(prior_attempts, int)
        and isinstance(cumulative_attempts, int)
        and cumulative_attempts == prior_attempts + 8
        and value.get("batch_selection", {}).get("batch_size") == 8
        and value.get("validation_status") in {_core.m12d.REAL_STATUS, _core.m12d.TEST_STATUS}
    )
    if not legacy_exact_complete:
        return value

    normalized = dict(value)
    normalized["remaining_batch_attempt_count"] = 0
    return normalized


def build_qa(
    input_root: Path,
    qa_root: Path,
    representative_root: Path,
    output_root: Path,
    *,
    expected_origin: str,
) -> dict[str, Any]:
    result = _original_build_qa(
        input_root,
        qa_root,
        representative_root,
        output_root,
        expected_origin=expected_origin,
    )
    deferred_count = int(
        result.get("evidence_summary", {})
        .get("outcome_counts", {})
        .get("HUMAN_DEFER", 0)
    )
    if deferred_count <= 0:
        return result

    guarded = dict(result)
    guarded["quality_gate"] = dict(result["quality_gate"])
    guarded["quality_gate"]["state"] = "PASS_HUMAN_REVIEW_REQUIRED"
    guarded["quality_gate"]["human_review_required"] = True
    guarded["stop_reason"] = "HUMAN_REVIEW_DECISIONS_REQUIRED"
    guarded["next_short_step"] = "E4S-A1V1-M12E1_HumanReviewDecisionMaterialization"
    _core._assert_schema(guarded)
    _core.write_json_atomic(
        Path(output_root) / "representative_evidence_qa_safe_report.json",
        guarded,
    )
    return guarded


_core.read_json = read_json
_core.build_qa = build_qa
main = _core.main


if __name__ == "__main__":
    raise SystemExit(main())
