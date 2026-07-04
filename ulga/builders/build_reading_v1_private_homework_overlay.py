"""Synthetic builder scaffold for ReadingV1 private homework overlay candidates.

This builder converts an already validated PracticeBank-like package into a
render-safe overlay. It does not read RAZ files, does not inline source text,
and does not produce HTML.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


def build_overlay_from_practice_bank(
    practice_bank: Mapping[str, Any],
    validation_report: Mapping[str, Any],
) -> Dict[str, Any]:
    """Build a private-homework overlay from a validated PracticeBank package.

    The function trusts only references/locators from the PracticeBank and does
    not copy display source text into the overlay.
    """
    source_practice_bank_id = practice_bank.get("practice_bank_id", "UNKNOWN_PRACTICE_BANK")
    items = practice_bank.get("items", [])
    if not isinstance(items, list):
        items = []

    overlay_items = [
        _build_overlay_item(item, index + 1, validation_report)
        for index, item in enumerate(items)
    ]

    scope = practice_bank.get("scope") if isinstance(practice_bank.get("scope"), Mapping) else {}
    return {
        "overlay_id": f"RV1_OVERLAY_SYNTHETIC_{source_practice_bank_id}",
        "schema_version": "reading_v1_private_homework_overlay.v1",
        "pipeline_stage": "private_homework_overlay_candidate",
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
        "private_homework_only": True,
        "public_ready": False,
        "source_practice_bank_id": source_practice_bank_id,
        "source_validation_report_ref": "in_memory_validation_report",
        "scope": {
            "level_stage": scope.get("level_stage"),
            "theme": scope.get("theme"),
            "situation": scope.get("situation"),
            "item_count": len(overlay_items),
            "render_language": "en",
            "instruction_language": "zh-TW",
        },
        "render_policy": {
            "render_mode": "local_private_homework_only",
            "allow_public_export": False,
            "allow_commercial_distribution": False,
            "allow_raw_source_text": False,
            "allow_full_passage_text": False,
            "allow_source_payload_copy": False,
            "allow_answer_key_display_to_student": False,
            "allow_answer_key_display_to_parent": True,
        },
        "items": overlay_items,
        "overlay_validation_summary": {
            "overlay_ready": False,
            "blocked_count": 0,
            "warning_count": 0,
            "error_count": 0,
        },
        "build_metadata": {
            "builder_name": "build_reading_v1_private_homework_overlay",
            "builder_version": "0.1.0",
            "built_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def _build_overlay_item(
    item: Mapping[str, Any],
    display_order: int,
    validation_report: Mapping[str, Any],
) -> Dict[str, Any]:
    item_id = str(item.get("item_id", f"UNKNOWN_ITEM_{display_order:06d}"))
    question = item.get("question") if isinstance(item.get("question"), Mapping) else {}
    answer_model = item.get("answer_model") if isinstance(item.get("answer_model"), Mapping) else {}
    answer_evidence = item.get("answer_evidence") if isinstance(item.get("answer_evidence"), Mapping) else {}
    source_trace = item.get("source_trace") if isinstance(item.get("source_trace"), Mapping) else {}

    item_validation = _lookup_item_report(validation_report, item_id)
    practice_validator_status = item_validation.get("validator_status", "NOT_RUN")
    html_ready = bool(item_validation.get("computed_html_ready", False))

    source_locator = source_trace.get("source_locator")
    source_unit_ref = source_trace.get("source_unit_ref")
    evidence_refs = answer_evidence.get("evidence_refs")
    if isinstance(evidence_refs, list) and evidence_refs:
        answer_evidence_ref = str(evidence_refs[0])
    else:
        answer_evidence_ref = answer_evidence.get("source_locator") or answer_evidence.get("source_sentence_ref")

    return {
        "overlay_item_id": f"RV1_OVERLAY_ITEM_{display_order:06d}",
        "source_item_id": item_id,
        "level_stage": item.get("level_stage"),
        "question_type": item.get("question_type"),
        "theme": item.get("theme"),
        "display_order": display_order,
        "student_view": {
            "prompt": question.get("prompt"),
            "display_text_ref": source_locator or source_unit_ref,
            "display_text_inline": None,
            "options": question.get("options", []),
            "requires_image": bool(question.get("requires_image", False)),
            "requires_audio": bool(question.get("requires_audio", False)),
        },
        "parent_or_teacher_view": {
            "answer_key_ref": f"{item_id}:answer_model.answer_key" if answer_model.get("answer_key") is not None else None,
            "answer_evidence_ref": answer_evidence_ref,
            "show_answer_key": True,
            "show_source_locator": True,
        },
        "source_trace_view": {
            "source_locator": source_locator,
            "source_unit_ref": source_unit_ref,
            "source_payload_stored": False,
            "raw_source_text_visible": False,
            "full_passage_text_visible": False,
        },
        "policy_flags": {
            "private_homework_only": True,
            "public_ready": False,
            "not_for_public_export": True,
            "not_for_commercial_distribution": True,
            "raw_raz_text_persisted": False,
            "full_passage_text_persisted": False,
            "source_payload_copied_to_repo": False,
        },
        "gates": {
            "practice_bank_validator_status": practice_validator_status,
            "html_ready": html_ready,
            "overlay_ready": False,
            "overlay_ready_reason": None,
        },
    }


def _lookup_item_report(validation_report: Mapping[str, Any], item_id: str) -> Mapping[str, Any]:
    reports = validation_report.get("item_reports", [])
    if not isinstance(reports, list):
        return {}
    for report in reports:
        if isinstance(report, Mapping) and report.get("item_id") == item_id:
            return report
    return {}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build a ReadingV1 private homework overlay candidate.")
    parser.add_argument("--practice-bank", type=Path, required=True)
    parser.add_argument("--validation-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    practice_bank = load_json(args.practice_bank)
    validation_report = load_json(args.validation_report)
    overlay = build_overlay_from_practice_bank(practice_bank, validation_report)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(overlay, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
