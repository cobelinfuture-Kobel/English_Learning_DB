#!/usr/bin/env python3
"""Build a learner-safe Pages payload for the next eligible A1 pilot unit."""
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
from ulga.builders.run_a1_grammar_text_mode_private_pilot_next_unit import (
    OPEN_PRODUCTIVE_TASK_TYPES,
    _learner_task_material,
    _learner_visible_context,
    select_next_unit,
)
from ulga.query.a1_a1plus_coverage_query import load_coverage
from ulga.validators.a1_a1plus_delivery_coverage_gate import (
    validate_delivery_unit_coverage,
)

DEFAULT_OUTPUT = REPO_ROOT / "pages/private-pilot-review/next-unit.json"
EXECUTED = {
    "GRAMMAR_ARTICLES_BASIC",
    "GRAMMAR_REGULAR_PLURAL_NOUNS",
    "GRAMMAR_SUBJECT_PRONOUNS",
}
PROGRESSION_READY = set(EXECUTED)


def _strip_option_prefix(value: str) -> str:
    text = str(value).strip()
    parts = text.split(". ", 1)
    return parts[1] if len(parts) == 2 and parts[0].isdigit() else text


def _safe_item(item: Mapping[str, Any]) -> dict[str, Any]:
    material = _learner_task_material(item)
    rubric = item.get("scoring_rubric", {})
    return {
        "item_id": item["item_id"],
        "skill": item.get("skill"),
        "item_role": item.get("item_role"),
        "task_type": item.get("task_type"),
        "prompt": item.get("prompt", ""),
        "context": _learner_visible_context(item),
        "options": [_strip_option_prefix(value) for value in item.get("options", [])],
        "material": (
            {"label": material[0], "values": material[1]}
            if material is not None else None
        ),
        "manual_score_required": item.get("task_type") in OPEN_PRODUCTIVE_TASK_TYPES,
        "minimum_score": float(rubric.get("minimum_score", 1.0)),
        "attempt_sequence": 1,
    }


def require_unit_coverage(
    unit: Mapping[str, Any],
    coverage_report: Mapping[str, Any],
) -> list[str]:
    """Backward-compatible Pages helper backed by the shared validator."""
    try:
        gate = validate_delivery_unit_coverage(
            unit,
            coverage_report=coverage_report,
            error_prefix="next_unit_pages",
        )
    except ValueError as exc:
        detail = str(exc)
        grammar_id = unit.get("grammar_unit_id")
        if "unit_has_no_canonical_rows" in detail:
            raise RuntimeError(
                f"next_unit_pages_canonical_rows_missing:{grammar_id}"
            ) from exc
        raise RuntimeError(
            f"next_unit_pages_uncovered_canonical_rows:{grammar_id}:{detail}"
        ) from exc
    return list(gate["canonical_egp_row_ids"])


def build_payload() -> dict[str, Any]:
    package, report = build_and_validate_from_repo()
    if report.get("validation_status") != "PASS":
        raise RuntimeError("next_unit_pages_package_validation_failed")
    unit = select_next_unit(
        package,
        executed_unit_ids=EXECUTED,
        progression_ready_unit_ids=PROGRESSION_READY,
    )
    if unit is None:
        raise RuntimeError("next_unit_pages_no_remaining_unit")
    covered_row_ids = require_unit_coverage(unit, load_coverage())
    index = {item["item_id"]: item for item in package.get("item_bank", [])}
    plan = unit["delivery_plan"]
    item_ids = list(plan["practice_item_ids"]) + list(plan["assessment_item_ids"])
    return {
        "schema_version": "a1_private_pilot_pages_payload.v1",
        "grammar_unit_id": unit["grammar_unit_id"],
        "sequence_index": unit["sequence_index"],
        "title_en": unit.get("learning_content", {}).get("title_en"),
        "coverage_gate": {
            "status": "PASS_ALL_CANONICAL_ROWS_COVERED",
            "canonical_egp_row_ids": covered_row_ids,
        },
        "learner_ref": "learner-local-01",
        "operator_ref": "operator-local-01",
        "item_count": len(item_ids),
        "items": [_safe_item(index[item_id]) for item_id in item_ids],
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
    print(json.dumps({"validation_status":"PASS","grammar_unit_id":payload["grammar_unit_id"],"item_count":payload["item_count"],"coverage_gate":payload["coverage_gate"]["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
