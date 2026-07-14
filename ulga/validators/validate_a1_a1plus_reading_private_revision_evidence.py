#!/usr/bin/env python3
"""Validate private and metadata-only M04B3 revision evidence artifacts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_a1plus_reading_private_revision_evidence import (  # noqa: E402
    validate_revision_evidence,
)
from ulga.builders.build_a1_a1plus_source_grounded_reading_review_promotion import (  # noqa: E402
    read_json,
    write_json_atomic,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-input", type=Path, required=True)
    parser.add_argument("--safe-report", type=Path, required=True)
    parser.add_argument("--validation-report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = validate_revision_evidence(
            read_json(args.private_input),
            read_json(args.safe_report),
        )
        write_json_atomic(args.validation_report, result)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["error_count"] == 0 else 1
    except (OSError, KeyError, TypeError, ValueError) as exc:
        result = {
            "validation_status": "FAIL_PRIVATE_REVISION_EVIDENCE",
            "error_count": 1,
            "errors": [str(exc)],
        }
        write_json_atomic(args.validation_report, result)
        print(json.dumps(result, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
