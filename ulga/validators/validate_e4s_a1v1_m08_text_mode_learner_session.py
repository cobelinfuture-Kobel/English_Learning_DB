#!/usr/bin/env python3
"""Independently validate M08 local text sessions and progress evidence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SOURCE_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(SOURCE_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as builder  # noqa: E402
from ulga.builders.build_a1_a1plus_shared_item_contract import (  # noqa: E402
    build_artifact as build_shared_contract,
)
from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import (  # noqa: E402
    build_and_validate_from_repo as build_text_package,
)

PASS_STATUSES = {
    builder.ZERO_STATUS,
    builder.PARTIAL_STATUS,
    builder.COMPLETE_STATUS,
}
DEFAULT_VALIDATION_PATH = (
    builder.DEFAULT_OUTPUT_ROOT / "text_mode_session_validation.json"
)


def validate(output_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        root = builder._safe_output_root(output_root)
        bank = builder.read_json(root / "text_mode_session_bank.private.json")
        payload = builder.read_json(root / "text_mode_learner_safe_payload.json")
        registry = builder.read_json(root / "text_mode_attempt_registry.private.json")
        ledger = builder.read_json(root / "text_mode_progress_ledger.private.json")
        report = builder.read_json(root / "text_mode_progress_safe_report.json")
        query = builder.read_json(root / "text_mode_progress_query_index.json")

        builder._assert_schema(
            "e4s_a1v1_text_mode_session_bank.schema.json", bank
        )
        builder._assert_schema(
            "e4s_a1v1_text_mode_attempt_registry.schema.json", registry
        )
        builder._assert_schema(
            "e4s_a1v1_text_mode_progress_ledger.schema.json", ledger
        )
        builder._safe_scan(
            payload,
            name="learner_safe_payload",
            forbidden=builder.LEARNER_FORBIDDEN_KEYS,
        )
        builder._safe_scan(
            report,
            name="progress_safe_report",
            forbidden=builder.SAFE_REPORT_FORBIDDEN_KEYS,
        )
        builder._safe_scan(
            query,
            name="progress_query_index",
            forbidden=builder.SAFE_REPORT_FORBIDDEN_KEYS,
        )

        m07 = builder.read_json(builder.M07_RECEIPT_PATH)
        text_source, text_report = build_text_package()
        if text_report.get("validation_status") != "PASS":
            errors.append("text_source_validation_failed")
        shared = build_shared_contract()
        rebuilt_bank = builder.build_session_bank(m07, text_source, shared)
        if rebuilt_bank != bank:
            errors.append("session_bank_not_reproducible")

        rebuilt_payload = builder.build_learner_safe_payload(bank)
        if rebuilt_payload != payload:
            errors.append("learner_safe_payload_not_reproducible")

        rebuilt_ledger, rebuilt_report, rebuilt_query = (
            builder.build_progress_artifacts(bank, registry)
        )
        if rebuilt_ledger != ledger:
            errors.append("progress_ledger_not_reproducible")
        if rebuilt_report != report:
            errors.append("progress_safe_report_not_reproducible")
        if rebuilt_query != query:
            errors.append("progress_query_index_not_reproducible")

        items = bank.get("items", [])
        if len(items) != 192:
            errors.append("session_item_count_not_192")
        if len({row.get("item_id") for row in items}) != 192:
            errors.append("session_item_identity_not_192")
        if len({row.get("grammar_unit_id") for row in items}) != 24:
            errors.append("session_unit_coverage_not_24")
        row_ids = {
            row_id
            for item in items
            for row_id in item.get("canonical_egp_row_ids", [])
        }
        if len(row_ids) != 109:
            errors.append("session_row_coverage_not_109")
        for skill in builder.SKILLS:
            if sum(row.get("skill") == skill for row in items) != 96:
                errors.append(f"session_skill_count_not_96:{skill}")
            if sum(
                row.get("skill") == skill
                and row.get("item_role") == "practice"
                for row in items
            ) != 72:
                errors.append(f"session_practice_count_not_72:{skill}")
            if sum(
                row.get("skill") == skill
                and row.get("item_role") == "assessment"
                for row in items
            ) != 24:
                errors.append(f"session_assessment_count_not_24:{skill}")

        if ledger.get("attempt_count") != len(ledger.get("entries", [])):
            errors.append("ledger_attempt_count_drift")
        if sum(ledger.get("outcome_counts", {}).values()) != ledger.get(
            "attempt_count"
        ):
            errors.append("ledger_outcome_accounting_drift")
        if report.get("attempt_count") != ledger.get("attempt_count"):
            errors.append("report_attempt_count_drift")
        if report.get("available_item_count") != 192:
            errors.append("report_available_item_count_not_192")
        if report.get("unattempted_item_count") != 192 - ledger.get(
            "attempt_count", 0
        ):
            errors.append("report_unattempted_count_drift")
        if report.get("actual_learner_evidence_count") != ledger.get(
            "attempt_count"
        ):
            errors.append("report_evidence_count_drift")
        if report.get("validation_status") not in PASS_STATUSES:
            errors.append("report_validation_status_invalid")
        if report.get("stop_reason") != "NONE":
            errors.append("report_stop_reason_not_none")
        if report.get("next_short_step") != builder.NEXT_SHORT_STEP:
            errors.append("report_next_short_step_drift")

        boundaries = report.get("claim_boundaries", {})
        expected_boundaries = {
            "metadata_only_report": True,
            "private_responses_included": False,
            "audio_evidence_used": False,
            "speaking_audio_evidence_state": "DEFERRED_BY_OPERATOR",
            "canonical_authority_writes": 0,
            "public_delivery_count": 0,
            "persistent_learner_state_writes": 0,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "production_runtime_enabled": False,
            "a2_a2plus_in_scope": False,
        }
        if boundaries != expected_boundaries:
            errors.append("safe_report_claim_boundaries_drift")
        if any(entry.get("mastery_claimed") is not False for entry in ledger.get("entries", [])):
            errors.append("entry_false_mastery_claim")

        html = (root / "local_session/index.html").read_text(
            encoding="utf-8"
        )
        lowered = html.casefold()
        required_html = (
            "local-only",
            "no network submission",
            "localstorage",
            "download attempt registry",
            "no audio is used",
        )
        for token in required_html:
            if token not in lowered:
                errors.append(f"local_session_html_missing:{token}")
        for forbidden in (
            "fetch('http",
            'fetch("http',
            "xmlhttprequest",
            "websocket",
            "getusermedia",
            "mediarecorder",
            "answer_key",
            "accepted_texts",
        ):
            if forbidden in lowered:
                errors.append(f"local_session_html_forbidden:{forbidden}")
    except (
        builder.TextModeSessionError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(str(exc))
        bank = {}
        ledger = {}
        report = {}

    validation_status = (
        report.get("validation_status", "FAIL") if not errors else "FAIL"
    )
    return {
        "task_id": builder.TASK_ID,
        "validation_status": validation_status,
        "error_count": len(errors),
        "errors": errors,
        "available_item_count": bank.get("item_count", 0),
        "attempt_count": ledger.get("attempt_count", 0),
        "attempted_unit_count": ledger.get("attempted_unit_count", 0),
        "attempted_row_count": ledger.get("attempted_row_count", 0),
        "pending_human_review_count": report.get(
            "pending_human_review_count", 0
        ),
        "learner_mastery_claimed": False,
        "audio_evidence_used": False,
        "next_short_step": builder.NEXT_SHORT_STEP,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root", type=Path, default=builder.DEFAULT_OUTPUT_ROOT
    )
    parser.add_argument(
        "--validation-report",
        type=Path,
        default=DEFAULT_VALIDATION_PATH,
    )
    args = parser.parse_args(argv)
    result = validate(args.output_root)
    builder.write_json_atomic(args.validation_report, result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["validation_status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
