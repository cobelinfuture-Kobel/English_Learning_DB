#!/usr/bin/env python3
"""Validate every private PracticeBank item for learner-visible answerability."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4
from ulga.builders import build_a1fs_v1_shared_learner_stimulus_contract_renderer as stimulus

TASK_ID = "A1FS-V1_LearnerAnswerabilityGate"
SCHEMA_VERSION = "a1fs.v1.learner_answerability_gate.v1"
STATUS = "PASS_A1FS_V1_LEARNER_ANSWERABILITY_GATE"


def validate_bank(path: Path) -> dict[str, Any]:
    try:
        bank = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"validation_status": "FAIL", "error_count": 1, "errors": [f"bank_unreadable:{exc}"]}
    errors: list[str] = []
    if not isinstance(bank, dict):
        errors.append("bank_not_object")
        items = []
    else:
        if bank.get("task_id") != r4.TASK_ID or bank.get("schema_version") != r4.BANK_SCHEMA_VERSION:
            errors.append("bank_identity_invalid")
        if bank.get("validation_status") != r4.STATUS:
            errors.append("bank_status_invalid")
        items = bank.get("items")
        if not isinstance(items, list) or bank.get("item_count") != len(items):
            errors.append("bank_item_denominator_invalid")
            items = []
    scan = stimulus.scan_items(items)
    counts = scan["counts"]
    if counts["answerability_failed"]:
        errors.append(f"ready_item_answerability_failure:{counts['answerability_failed']}")
    if counts["payload_missing"]:
        errors.append(f"ready_item_required_payload_missing:{counts['payload_missing']}")
    if counts["renderer_unsupported"]:
        errors.append(f"ready_item_renderer_unsupported:{counts['renderer_unsupported']}")
    if counts["serialization_loss"]:
        errors.append(f"ready_item_serialization_loss:{counts['serialization_loss']}")
    report_core = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": STATUS if not errors else "FAIL_A1FS_V1_LEARNER_ANSWERABILITY_GATE",
        "error_count": len(errors),
        "errors": errors,
        "counts": counts,
        "failures": scan["failures"],
        "source_bank_sha256": bank.get("bank_sha256") if isinstance(bank, dict) else None,
    }
    return {**report_core, "report_sha256": stimulus.digest(report_core)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = validate_bank(args.bank)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
