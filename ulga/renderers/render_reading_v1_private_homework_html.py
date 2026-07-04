"""In-memory ReadingV1 private homework page renderer."""

from __future__ import annotations

from html import escape
from typing import Any, Mapping

PASS_STATUS = "HTML_ENTRY_ALLOWED"


def render_private_homework_page(
    gate_report: Mapping[str, Any],
    overlay_package: Mapping[str, Any],
    display_payloads: Mapping[str, str],
) -> dict[str, Any]:
    """Return a private page string in memory.

    This renderer does not write files. It expects caller-provided display text
    for each item id and blocks when the gate is not ready.
    """
    if not _gate_allows_render(gate_report):
        return {"render_status": "BLOCKED", "html": "", "errors": ["RV1_HTML_ERR_OUTPUT_GATE_NOT_ALLOWED"]}

    items = overlay_package.get("items", [])
    if not isinstance(items, list):
        return {"render_status": "BLOCKED", "html": "", "errors": ["RV1_HTML_ERR_ITEMS_MISSING"]}

    body_parts = ["<main class=\"rv1-private-homework\">"]
    body_parts.append("<h1>Reading Practice</h1>")
    body_parts.append("<section class=\"student-view\">")

    for index, item in enumerate(items, start=1):
        source_item_id = str(item.get("source_item_id") or "")
        prompt = _student_prompt(item)
        display_text = display_payloads.get(source_item_id)
        if not source_item_id or display_text is None:
            return {"render_status": "BLOCKED", "html": "", "errors": ["RV1_HTML_ERR_DISPLAY_PAYLOAD_MISSING"]}
        body_parts.append(f"<article class=\"practice-item\" data-item=\"{escape(source_item_id)}\">")
        body_parts.append(f"<h2>Item {index}</h2>")
        body_parts.append(f"<p class=\"display-text\">{escape(display_text)}</p>")
        body_parts.append(f"<p class=\"prompt\">{escape(prompt)}</p>")
        body_parts.append("<p class=\"answer-blank\">____________________</p>")
        body_parts.append("</article>")

    body_parts.append("</section>")
    body_parts.append("<section class=\"parent-teacher-view\" hidden>")
    body_parts.append("<p>Answer references are available only in parent or teacher review mode.</p>")
    body_parts.append("</section>")
    body_parts.append("</main>")

    html = "\n".join(body_parts)
    return {"render_status": "PASS", "html": html, "errors": []}


def _gate_allows_render(gate_report: Mapping[str, Any]) -> bool:
    summary = gate_report.get("summary", {})
    if not isinstance(summary, Mapping):
        return False
    policy = gate_report.get("render_policy", {})
    if not isinstance(policy, Mapping):
        return False
    return (
        summary.get("gate_status") == PASS_STATUS
        and summary.get("html_entry_allowed") is True
        and summary.get("error_count") == 0
        and gate_report.get("private_homework_only") is True
        and gate_report.get("public_ready") is False
        and policy.get("render_mode") == "local_private_homework_only"
        and policy.get("allow_answer_key_display_to_student") is False
    )


def _student_prompt(item: Mapping[str, Any]) -> str:
    student_view = item.get("student_view", {})
    if isinstance(student_view, Mapping) and student_view.get("prompt"):
        return str(student_view["prompt"])
    return "Answer the question."
