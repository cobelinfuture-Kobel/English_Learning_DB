"""In-memory ReadingV1 private-homework page renderer.

Every render result carries output-gate and canonical A1 grammar-gate evidence.
A PASS page can therefore be validated as originating from the approved
PracticeBank -> output-gate path instead of being accepted from status text alone.
"""

from __future__ import annotations

from html import escape
from typing import Any, Mapping


TASK_ID = "R7-M104E24B_A1GrammarGateHTMLExportEvidenceIntegration"
EVIDENCE_VERSION = "reading_v1_html_export_gate_evidence.v1"
PASS_STATUS = "HTML_ENTRY_ALLOWED"


def render_private_homework_page(
    gate_report: Mapping[str, Any],
    overlay_package: Mapping[str, Any],
    display_payloads: Mapping[str, str],
) -> dict[str, Any]:
    """Return a private page string and immutable gate-evidence snapshot."""

    evidence = _gate_evidence(gate_report)
    if not _gate_allows_render(gate_report):
        return _result(
            "BLOCKED",
            "",
            ["RV1_HTML_ERR_OUTPUT_GATE_NOT_ALLOWED"],
            evidence,
        )

    items = overlay_package.get("items", [])
    if not isinstance(items, list):
        return _result(
            "BLOCKED",
            "",
            ["RV1_HTML_ERR_ITEMS_MISSING"],
            evidence,
        )

    body_parts = ['<main class="rv1-private-homework">']
    body_parts.append("<h1>Reading Practice</h1>")
    body_parts.append('<section class="student-view">')

    rendered_item_ids: list[str] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, Mapping):
            return _result(
                "BLOCKED",
                "",
                ["RV1_HTML_ERR_ITEMS_MISSING"],
                evidence,
            )
        source_item_id = str(item.get("source_item_id") or "")
        prompt = _student_prompt(item)
        display_text = display_payloads.get(source_item_id)
        if not source_item_id or display_text is None:
            return _result(
                "BLOCKED",
                "",
                ["RV1_HTML_ERR_DISPLAY_PAYLOAD_MISSING"],
                evidence,
            )
        rendered_item_ids.append(source_item_id)
        body_parts.append(
            f'<article class="practice-item" data-item="{escape(source_item_id)}">'
        )
        body_parts.append(f"<h2>Item {index}</h2>")
        body_parts.append(f'<p class="display-text">{escape(display_text)}</p>')
        body_parts.append(f'<p class="prompt">{escape(prompt)}</p>')
        body_parts.append('<p class="answer-blank">____________________</p>')
        body_parts.append("</article>")

    body_parts.append("</section>")
    body_parts.append('<section class="parent-teacher-view" hidden>')
    body_parts.append(
        "<p>Answer references are available only in parent or teacher review mode.</p>"
    )
    body_parts.append("</section>")
    body_parts.append("</main>")

    evidence["rendered_item_ids"] = rendered_item_ids
    evidence["rendered_item_count"] = len(rendered_item_ids)
    html = "\n".join(body_parts)
    return _result("PASS", html, [], evidence)


def _result(
    status: str,
    html: str,
    errors: list[str],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "schema_version": "reading_v1_html_export_result.v1",
        "render_status": status,
        "html": html,
        "errors": list(errors),
        "gate_evidence": dict(evidence),
    }


def _gate_evidence(gate_report: Mapping[str, Any]) -> dict[str, Any]:
    summary = gate_report.get("summary", {})
    if not isinstance(summary, Mapping):
        summary = {}
    policy = gate_report.get("render_policy", {})
    if not isinstance(policy, Mapping):
        policy = {}
    grammar = gate_report.get("grammar_gate_evidence", {})
    if not isinstance(grammar, Mapping):
        grammar = {}
    item_reports = gate_report.get("item_reports", [])
    if not isinstance(item_reports, list):
        item_reports = []

    source_item_ids = [
        str(item.get("source_item_id"))
        for item in item_reports
        if isinstance(item, Mapping) and item.get("source_item_id")
    ]
    return {
        "evidence_version": EVIDENCE_VERSION,
        "renderer_task_id": TASK_ID,
        "output_gate_task_id": gate_report.get("task_id"),
        "output_gate_schema_version": gate_report.get("schema_version"),
        "output_gate_validator_status": gate_report.get("validator_status"),
        "output_gate_gate_status": summary.get("gate_status"),
        "html_entry_allowed": summary.get("html_entry_allowed"),
        "output_gate_error_count": summary.get("error_count"),
        "private_homework_only": gate_report.get("private_homework_only"),
        "public_ready": gate_report.get("public_ready"),
        "render_mode": policy.get("render_mode"),
        "practice_bank_validator_status": grammar.get(
            "practice_bank_validator_status"
        ),
        "practice_bank_grammar_gate_status": grammar.get(
            "practice_bank_grammar_gate_status"
        ),
        "practice_bank_grammar_gate_pass_count": grammar.get(
            "practice_bank_grammar_gate_pass_count"
        ),
        "practice_bank_grammar_gate_fail_count": grammar.get(
            "practice_bank_grammar_gate_fail_count"
        ),
        "practice_bank_item_report_count": grammar.get(
            "practice_bank_item_report_count"
        ),
        "all_output_items_allowed": grammar.get("all_output_items_allowed"),
        "output_item_count": summary.get("item_count"),
        "allowed_item_count": summary.get("allowed_item_count"),
        "blocked_item_count": summary.get("blocked_item_count"),
        "source_item_ids": source_item_ids,
        "rendered_item_ids": [],
        "rendered_item_count": 0,
    }


def _gate_allows_render(gate_report: Mapping[str, Any]) -> bool:
    summary = gate_report.get("summary", {})
    if not isinstance(summary, Mapping):
        return False
    policy = gate_report.get("render_policy", {})
    if not isinstance(policy, Mapping):
        return False
    grammar = gate_report.get("grammar_gate_evidence", {})
    if not isinstance(grammar, Mapping):
        return False
    return (
        gate_report.get("validator_status") == "PASS"
        and summary.get("gate_status") == PASS_STATUS
        and summary.get("html_entry_allowed") is True
        and summary.get("error_count") == 0
        and gate_report.get("private_homework_only") is True
        and gate_report.get("public_ready") is False
        and policy.get("render_mode") == "local_private_homework_only"
        and policy.get("allow_answer_key_display_to_student") is False
        and grammar.get("practice_bank_validator_status") == "PASS"
        and grammar.get("practice_bank_grammar_gate_status") == "PASS"
        and grammar.get("practice_bank_grammar_gate_fail_count") == 0
        and grammar.get("all_output_items_allowed") is True
    )


def _student_prompt(item: Mapping[str, Any]) -> str:
    student_view = item.get("student_view", {})
    if isinstance(student_view, Mapping) and student_view.get("prompt"):
        return str(student_view["prompt"])
    return "Answer the question."
