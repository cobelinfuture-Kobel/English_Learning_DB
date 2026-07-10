"""Run the complete synthetic ReadingV1 private-homework chain offline.

The runner executes the approved canonical A1 path in one process:

PracticeBank builder -> PracticeBank validator -> private overlay builder ->
overlay validator -> grammar-gated output gate -> renderer -> HTML validator.

It uses synthetic display payloads only, writes no learner state, performs no
production runtime validation, and never reads RAZ or other restricted source
payloads.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional

from ulga.builders.build_reading_v1_practice_bank import (
    build_synthetic_practice_bank,
)
from ulga.builders.build_reading_v1_private_homework_output_gate import (
    build_gate_report,
)
from ulga.builders.build_reading_v1_private_homework_overlay import (
    build_overlay_from_practice_bank,
)
from ulga.renderers.render_reading_v1_private_homework_html import (
    render_private_homework_page,
)
from ulga.validators.validate_reading_v1_html_export import (
    validate_html_export_result,
)
from ulga.validators.validate_reading_v1_practice_bank import validate_package
from ulga.validators.validate_reading_v1_private_homework_output_gate import (
    validate_output_gate_report,
)
from ulga.validators.validate_reading_v1_private_homework_overlay import (
    validate_overlay_package,
)


TASK_ID = "R7-M104E24D_A1GrammarGatedPrivateHomeworkChainRunner"
CHAIN_VERSION = "reading_v1_a1_grammar_gated_private_homework_chain.v1"
DEFAULT_VALID_GRAMMAR_TEXT = "They go to school."


def run_synthetic_private_homework_chain(
    *,
    first_item_grammar_text: Optional[str] = None,
) -> dict[str, Any]:
    """Execute the full synthetic chain and return a compact audit result."""

    practice_bank = build_synthetic_practice_bank()
    if first_item_grammar_text is not None:
        practice_bank["items"][0]["grammar_gate"]["validation_targets"][0][
            "text"
        ] = first_item_grammar_text

    practice_bank_report = validate_package(practice_bank)
    overlay = build_overlay_from_practice_bank(
        practice_bank,
        practice_bank_report,
    )
    overlay_report = validate_overlay_package(overlay)

    raw_output_gate = build_gate_report(
        practice_bank_report,
        overlay_report,
        {
            "resolver_status": "PASS",
            "resolver_mode": "synthetic_in_memory_display_payloads",
            "source_payload_persisted": False,
        },
    )
    output_gate_report = validate_output_gate_report(raw_output_gate)

    display_payloads = {
        item["item_id"]: f"Synthetic display text for {item['item_id']}."
        for item in practice_bank["items"]
    }
    render_result = render_private_homework_page(
        output_gate_report,
        overlay,
        display_payloads,
    )
    html_validation_report = validate_html_export_result(render_result)

    stage_status = {
        "practice_bank_validator": practice_bank_report.get(
            "validator_status"
        ),
        "overlay_validator": overlay_report.get("validator_status"),
        "output_gate_validator": output_gate_report.get("validator_status"),
        "renderer": render_result.get("render_status"),
        "html_export_validator": html_validation_report.get(
            "validator_status"
        ),
    }
    chain_status = _chain_status(stage_status, render_result)

    item_ids = [item["item_id"] for item in practice_bank["items"]]
    grammar_summary = practice_bank_report.get("grammar_gate_summary", {})
    overlay_summary = overlay_report.get("summary", {})
    output_summary = output_gate_report.get("summary", {})
    gate_evidence = render_result.get("gate_evidence", {})

    return {
        "task_id": TASK_ID,
        "chain_version": CHAIN_VERSION,
        "execution_mode": "SYNTHETIC_OFFLINE_LOCAL_ONLY",
        "chain_status": chain_status,
        "chain_pass": chain_status == "PASS",
        "safe_block": (
            chain_status == "BLOCKED"
            and render_result.get("html") == ""
            and html_validation_report.get("validator_status") == "PASS"
        ),
        "practice_bank_id": practice_bank.get("practice_bank_id"),
        "item_ids": item_ids,
        "stage_status": stage_status,
        "stage_counts": {
            "practice_item_count": len(item_ids),
            "grammar_gate_pass_count": grammar_summary.get("pass_count", 0),
            "grammar_gate_fail_count": grammar_summary.get("fail_count", 0),
            "overlay_ready_count": overlay_summary.get(
                "overlay_ready_count", 0
            ),
            "overlay_blocked_count": overlay_summary.get("blocked_count", 0),
            "output_allowed_item_count": output_summary.get(
                "allowed_item_count", 0
            ),
            "output_blocked_item_count": output_summary.get(
                "blocked_item_count", 0
            ),
            "rendered_item_count": (
                gate_evidence.get("rendered_item_count", 0)
                if isinstance(gate_evidence, dict)
                else 0
            ),
        },
        "failure_codes": _failure_codes(
            practice_bank_report,
            overlay_report,
            output_gate_report,
            render_result,
            html_validation_report,
        ),
        "html_export": {
            "render_status": render_result.get("render_status"),
            "validator_status": html_validation_report.get(
                "validator_status"
            ),
            "html": render_result.get("html", ""),
            "renderer_errors": render_result.get("errors", []),
            "validator_errors": html_validation_report.get("errors", []),
            "gate_evidence": gate_evidence,
        },
        "safety": {
            "private_homework_only": True,
            "public_ready": False,
            "source_payload_persisted": False,
            "raw_raz_text_read": False,
            "full_passage_text_read": False,
            "learner_state_write": False,
            "production_runtime_validator": False,
            "external_nlp_dependency": False,
            "a2plus_grammar_authority_modified": False,
        },
    }


def _chain_status(
    stage_status: dict[str, Any],
    render_result: dict[str, Any],
) -> str:
    if stage_status.get("html_export_validator") != "PASS":
        return "FAIL"
    if stage_status.get("renderer") == "BLOCKED":
        return "BLOCKED"
    if all(
        stage_status.get(key) == "PASS"
        for key in (
            "practice_bank_validator",
            "overlay_validator",
            "output_gate_validator",
            "renderer",
            "html_export_validator",
        )
    ):
        return "PASS"
    if render_result.get("html"):
        return "FAIL"
    return "BLOCKED"


def _failure_codes(*reports: Any) -> list[str]:
    codes: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            code = value.get("code")
            if isinstance(code, str) and code:
                codes.add(code)
            for key, nested in value.items():
                if key in {
                    "package_errors",
                    "errors",
                    "item_reports",
                    "renderer_errors",
                    "validator_errors",
                }:
                    visit(nested)
        elif isinstance(value, list):
            for nested in value:
                if isinstance(nested, str) and nested:
                    codes.add(nested)
                else:
                    visit(nested)

    for report in reports:
        visit(report)
    return sorted(codes)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the synthetic grammar-gated ReadingV1 private-homework chain."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON output path. Otherwise prints to stdout.",
    )
    parser.add_argument(
        "--first-item-grammar-text",
        default=None,
        help=(
            "Optional synthetic failure-injection text for the first grammar "
            "target. This never reads an external source."
        ),
    )
    args = parser.parse_args(argv)

    result = run_synthetic_private_homework_chain(
        first_item_grammar_text=args.first_item_grammar_text
    )
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)

    if result["chain_status"] == "PASS":
        return 0
    if result["chain_status"] == "BLOCKED" and result["safe_block"]:
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
