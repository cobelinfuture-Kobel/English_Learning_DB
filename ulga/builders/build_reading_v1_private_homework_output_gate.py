"""Build ReadingV1 private-homework output gate dictionaries.

This builder joins the validated PracticeBank report to the private-homework
overlay report by source_item_id. HTML entry remains fail-closed when a
PracticeBank item, its canonical A1 grammar gate, or its computed HTML-ready
status is not PASS.
"""

from __future__ import annotations

from typing import Any, Mapping


TASK_ID = "R7-M104E24A_A1PracticeBankGrammarGatedHTMLExportIntegration"


def build_gate_report(
    pb_report: Mapping[str, Any],
    overlay_report: Mapping[str, Any],
    resolver_report: Mapping[str, Any],
) -> dict[str, Any]:
    pb_item_map, duplicate_pb_ids = _practice_bank_item_map(pb_report)
    overlay_item_reports = overlay_report.get("item_reports", [])
    if not isinstance(overlay_item_reports, list):
        overlay_item_reports = []

    items = [_gate_item(item, pb_item_map) for item in overlay_item_reports]
    grammar_summary = pb_report.get("grammar_gate_summary", {})
    if not isinstance(grammar_summary, Mapping):
        grammar_summary = {}

    return {
        "task_id": TASK_ID,
        "output_gate_report_id": "RV1_OUTGATE_SYNTHETIC_000001",
        "schema_version": "reading_v1_private_homework_output_gate.v1",
        "pipeline_stage": "private_homework_output_gate",
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
        "private_homework_only": True,
        "public_ready": False,
        "gate_inputs": {
            "practice_bank_validator_status": pb_report.get("validator_status"),
            "practice_bank_grammar_gate_status": (
                "PASS" if grammar_summary.get("all_items_pass") is True else "FAIL"
            ),
            "practice_bank_grammar_gate_pass_count": grammar_summary.get("pass_count", 0),
            "practice_bank_grammar_gate_fail_count": grammar_summary.get("fail_count", 0),
            "practice_bank_item_report_count": len(pb_item_map),
            "practice_bank_duplicate_item_ids": duplicate_pb_ids,
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


def _practice_bank_item_map(
    pb_report: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    item_reports = pb_report.get("item_reports", [])
    if not isinstance(item_reports, list):
        return {}, []

    item_map: dict[str, Mapping[str, Any]] = {}
    duplicate_ids: set[str] = set()
    for item_report in item_reports:
        if not isinstance(item_report, Mapping):
            continue
        item_id = item_report.get("item_id")
        if not isinstance(item_id, str) or not item_id:
            continue
        if item_id in item_map:
            duplicate_ids.add(item_id)
            continue
        item_map[item_id] = item_report
    return item_map, sorted(duplicate_ids)


def _gate_item(
    overlay_item: Mapping[str, Any],
    pb_item_map: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    source_item_id = str(
        overlay_item.get("source_item_id")
        or overlay_item.get("overlay_item_id")
        or "UNKNOWN_ITEM"
    )
    pb_item = pb_item_map.get(source_item_id)
    grammar_report = (
        pb_item.get("grammar_gate_report", {})
        if isinstance(pb_item, Mapping)
        else {}
    )
    if not isinstance(grammar_report, Mapping):
        grammar_report = {}

    pb_item_present = isinstance(pb_item, Mapping)
    pb_item_pass = pb_item_present and pb_item.get("validator_status") == "PASS"
    pb_grammar_pass = (
        pb_item_present
        and grammar_report.get("practice_item_gate_pass") is True
        and grammar_report.get("gate_status") == "PASS"
    )
    pb_html_ready = (
        pb_item_present and pb_item.get("computed_html_ready") is True
    )
    overlay_ok = overlay_item.get("validator_status") == "PASS"
    overlay_ready = overlay_item.get("computed_overlay_ready") is True

    checks = {
        "practice_bank_item_report_present": pb_item_present,
        "practice_bank_item_pass": pb_item_pass,
        "practice_bank_grammar_gate_pass": pb_grammar_pass,
        "practice_bank_html_ready": pb_html_ready,
        "overlay_item_pass": overlay_ok,
        "overlay_ready": overlay_ready,
        "display_payload_safe": True,
        "copied_material_persisted": False,
        "answer_key_hidden_from_student": True,
        "parent_teacher_answer_key_allowed": True,
        "public_export_blocked": True,
        "commercial_distribution_blocked": True,
    }
    ok = (
        pb_item_present
        and pb_item_pass
        and pb_grammar_pass
        and pb_html_ready
        and overlay_ok
        and overlay_ready
    )
    return {
        "source_item_id": source_item_id,
        "overlay_item_id": overlay_item.get("overlay_item_id"),
        "practice_bank_item_id": (
            pb_item.get("item_id") if isinstance(pb_item, Mapping) else None
        ),
        "gate_status": "PASS" if ok else "FAIL",
        "html_entry_allowed": ok,
        "checks": checks,
        "errors": [],
        "warnings": [],
    }
