#!/usr/bin/env python3
"""Backward-compatible M12E entrypoint for exact-complete legacy M12D reports.

M12D reports generated before the partial-batch FullFix did not contain
``remaining_batch_attempt_count``. This wrapper preserves the canonical M12E
implementation unchanged and normalizes only an exact-complete legacy M12D
report in memory. All downstream manifest, registry, ledger, query, origin,
status, and prior-plus-eight checks remain fail-closed in the core builder.
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


_core.read_json = read_json
build_qa = _core.build_qa
main = _core.main


if __name__ == "__main__":
    raise SystemExit(main())
