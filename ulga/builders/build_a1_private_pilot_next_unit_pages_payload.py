#!/usr/bin/env python3
"""Build a learner-safe P03 targeted review payload for subject pronouns."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import build_and_validate_from_repo
from ulga.builders.run_a1_grammar_text_mode_private_pilot_next_unit import _learner_visible_context

DEFAULT_OUTPUT = REPO_ROOT / "pages/private-pilot-review/next-unit.json"
UNIT = "GRAMMAR_SUBJECT_PRONOUNS"
TARGET_ITEM = f"{UNIT}__TFX_P03"


def _strip_option_prefix(value: str) -> str:
    text = str(value).strip()
    parts = text.split(". ", 1)
    return parts[1] if len(parts) == 2 and parts[0].isdigit() else text


def _safe_item(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "item_id": item["item_id"],
        "skill": item.get("skill"),
        "item_role": item.get("item_role"),
        "task_type": item.get("task_type"),
        "prompt": item.get("prompt", ""),
        "context": _learner_visible_context(item),
        "options": [_strip_option_prefix(value) for value in item.get("options", [])],
        "material": None,
        "manual_score_required": False,
        "minimum_score": 1.0,
        "attempt_sequence": 2,
    }


def build_payload() -> dict[str, Any]:
    package, report = build_and_validate_from_repo()
    if report.get("validation_status") != "PASS":
        raise RuntimeError("subject_pronouns_review_package_validation_failed")
    index = {item["item_id"]: item for item in package.get("item_bank", [])}
    if TARGET_ITEM not in index:
        raise RuntimeError("subject_pronouns_p03_not_found")
    return {
        "schema_version": "a1_private_pilot_pages_payload.v1",
        "grammar_unit_id": UNIT,
        "sequence_index": None,
        "title_en": "Subject pronouns · P03 targeted review",
        "learner_ref": "learner-local-01",
        "operator_ref": "operator-local-01",
        "item_count": 1,
        "items": [_safe_item(index[TARGET_ITEM])],
        "privacy": {
            "answer_key_included": False,
            "network_submission": False,
            "browser_local_only": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = build_payload()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"validation_status":"PASS","grammar_unit_id":UNIT,"item_count":1,"attempt_sequence":2}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
