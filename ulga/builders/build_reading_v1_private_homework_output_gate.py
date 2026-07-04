"""Build ReadingV1 private homework gate dictionaries for tests."""

from __future__ import annotations

from typing import Any, Mapping


def build_gate_report(pb_report: Mapping[str, Any], overlay_report: Mapping[str, Any], resolver_report: Mapping[str, Any]) -> dict[str, Any]:
    item_reports = overlay_report.get("item_reports", [])
    if not isinstance(item_reports, list):
        item_reports = []

    items = [_gate_item(item) for item in item_reports]
    return {
        "output_gate_report_id": "RV1_OUTGATE_SYNTHETIC_000001",
        "schema_version": "reading_v1_private_homework_output_gate.v1",
        "pipeline_stage": "private_homework_output_gate",
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
        "private_homework_only": True,
        "public_ready": False,
        "gate_inputs": {
            "practice_bank_validator_status": pb_report.get("validator_status"),
            "overlay_validator_status": overlay_report.get("validator_status"),
            "local_resolver_status": resolver_report.get("resolver_status"),
        },
        "render_policy": {
            "render_mode": "local_private_homework_only",
            "allow_public_export": False,
            "allow_commercial_distribution": False,
            "allow_copied_material_persistence": False,
            "allow_answer_key_display_to_student": False,
            "allow_answer_key_display_to_parent": True,
        },
        "item_gate_results": items,
        "summary": {
            "gate_status": "HTML_ENTRY_BLOCKED",
            "html_entry_allowed": False,
            "item_count": len(items),
            "allowed_item_count": 0,
            "blocked_item_count": len(items),
            "warning_count": 0,
            "error_count": 0,
        },
    }


def _gate_item(item: Mapping[str, Any]) -> dict[str, Any]:
    overlay_ok = item.get("validator_status") == "PASS"
    ready = item.get("computed_overlay_ready") is True
    ok = overlay_ok and ready
    return {
        "source_item_id": str(item.get("source_item_id") or item.get("overlay_item_id") or "UNKNOWN_ITEM"),
        "overlay_item_id": item.get("overlay_item_id"),
        "gate_status": "PASS" if ok else "FAIL",
        "html_entry_allowed": ok,
        "checks": {
            "practice_bank_item_pass": True,
            "overlay_item_pass": overlay_ok,
            "overlay_ready": ready,
            "display_payload_safe": True,
            "copied_material_persisted": False,
            "answer_key_hidden_from_student": True,
            "parent_teacher_answer_key_allowed": True,
            "public_export_blocked": True,
            "commercial_distribution_blocked": True,
        },
        "errors": [],
        "warnings": [],
    }
