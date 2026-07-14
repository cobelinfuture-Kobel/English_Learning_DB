#!/usr/bin/env python3
"""Validate final M04B3 private revision decisions and reviewed Reading bank."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_a1plus_source_grounded_reading_review_promotion import (  # noqa: E402
    read_json,
    write_json_atomic,
)
from ulga.builders.materialize_a1_a1plus_reading_private_revision_operator_approval import (  # noqa: E402
    validate_approval_outputs,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-queue", type=Path, required=True)
    parser.add_argument("--prior-reviewed-bank", type=Path, required=True)
    parser.add_argument("--final-decisions", type=Path, required=True)
    parser.add_argument("--final-reviewed-bank", type=Path, required=True)
    parser.add_argument("--promotion-safe-report", type=Path, required=True)
    parser.add_argument("--approval-safe-report", type=Path, required=True)
    parser.add_argument("--validation-report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = validate_approval_outputs(
            read_json(args.review_queue),
            read_json(args.prior_reviewed_bank),
            read_json(args.final_decisions),
            read_json(args.final_reviewed_bank),
            read_json(args.promotion_safe_report),
            read_json(args.approval_safe_report),
        )
    except (OSError, KeyError, TypeError, ValueError) as exc:
        result = {
            "validation_status": "FAIL_PRIVATE_REVISION_OPERATOR_APPROVAL",
            "error_count": 1,
            "errors": [str(exc)],
        }
    write_json_atomic(args.validation_report, result)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("error_count") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
