#!/usr/bin/env python3
"""Validate and independently reproduce the metadata-only M04 closeout receipt."""
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
from ulga.builders.build_e4s_a1v1_m04_reading_promotion_closeout_receipt import (  # noqa: E402
    validate_receipt,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-queue", type=Path, required=True)
    parser.add_argument("--final-decisions", type=Path, required=True)
    parser.add_argument("--final-reviewed-bank", type=Path, required=True)
    parser.add_argument("--promotion-safe-report", type=Path, required=True)
    parser.add_argument("--approval-safe-report", type=Path, required=True)
    parser.add_argument("--approval-validation", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--validation-report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = validate_receipt(
            read_json(args.review_queue),
            read_json(args.final_decisions),
            read_json(args.final_reviewed_bank),
            read_json(args.promotion_safe_report),
            read_json(args.approval_safe_report),
            read_json(args.approval_validation),
            read_json(args.receipt),
        )
    except (OSError, KeyError, TypeError, ValueError) as exc:
        result = {
            "validation_status": "FAIL_M04_READING_PROMOTION_CLOSEOUT_RECEIPT",
            "error_count": 1,
            "errors": [str(exc)],
        }
    write_json_atomic(args.validation_report, result)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("error_count") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
