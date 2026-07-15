#!/usr/bin/env python3
"""Independently validate the M11C Authority-reviewed private runtime."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any

SOURCE_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(SOURCE_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m11c_authority_reviewed_private_runtime as builder  # noqa: E402

PASS_STATUS = builder.RUNTIME_STATUS
DEFAULT_VALIDATION_PATH = builder.DEFAULT_OUTPUT_ROOT / "authority_runtime_validation.json"


def validate(output_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    manifest: dict[str, Any] = {}
    report: dict[str, Any] = {}
    query: dict[str, Any] = {}
    payload: dict[str, Any] = {}
    rebuild_root: Path | None = None
    try:
        root = builder._safe_output_root(output_root)
        manifest = builder.read_json(root / "runtime_manifest.json")
        report = builder.read_json(root / "authority_runtime_safe_report.json")
        query = builder.read_json(root / "authority_runtime_query_index.json")
        payload = builder.read_json(root / "authority_session/payload.json")
        builder._assert_schema("e4s_a1v1_m11c_authority_runtime_manifest.schema.json", manifest)
        builder._assert_schema("e4s_a1v1_m11c_authority_runtime_safe_report.schema.json", report)

        health = builder.run_health(root)
        if health.get("health_status") != PASS_STATUS or health.get("failed_check_count") != 0:
            errors.extend(f"runtime_health:{value}" for value in health.get("errors", []))
        if query.get("item_count") != 184:
            errors.append("query_item_count_not_184")
        if query.get("unit_count") != 23:
            errors.append("query_unit_count_not_23")
        if query.get("canonical_egp_row_count") != 107:
            errors.append("query_row_count_not_107")
        query_items = list(query.get("items", []))
        if len(query_items) != 184 or len({row.get("item_id") for row in query_items}) != 184:
            errors.append("query_identity_not_184")
        if any(row.get("grammar_unit_id") == builder.DEFERRED_GRAMMAR_ID for row in query_items):
            errors.append("deferred_will_query_leak")
        if query.get("items_sha256") != builder.sha256_value(query_items):
            errors.append("query_items_hash_drift")

        allowed_ids = {str(row.get("grammar_unit_id")) for row in query_items}
        try:
            builder._validate_learner_payload(payload, allowed_ids)
        except builder.AuthorityRuntimeError as exc:
            errors.append(str(exc))
        source_bank = builder.read_json(root / "source_m08/text_mode_session_bank.private.json")
        source_items = list(source_bank.get("items", []))
        if len(source_items) != 192:
            errors.append("source_m08_item_count_not_192")
        excluded = [row for row in source_items if row.get("grammar_unit_id") == builder.DEFERRED_GRAMMAR_ID]
        if len(excluded) != 8:
            errors.append("source_m08_will_item_count_not_8")
        if payload.get("session_bank_sha256") != builder.sha256_value(source_bank):
            errors.append("m08_session_bank_hash_compatibility_drift")
        if payload.get("task_id") != builder.m08.TASK_ID:
            errors.append("attempt_registry_task_compatibility_drift")
        if payload.get("schema_version") != "e4s.a1v1.text_mode_learner_safe_payload.v1":
            errors.append("learner_payload_schema_version_drift")

        skill_counts: dict[str, int] = {"reading": 0, "writing": 0}
        role_counts: dict[str, int] = {"practice": 0, "assessment": 0}
        rows: set[str] = set()
        units: set[str] = set()
        for row in query_items:
            skill_counts[str(row["skill"])] += 1
            role_counts[str(row["item_role"])] += 1
            units.add(str(row["grammar_unit_id"]))
            rows.update(row["canonical_egp_row_ids"])
        if skill_counts != {"reading": 92, "writing": 92}:
            errors.append("query_skill_distribution_drift")
        if role_counts != {"practice": 138, "assessment": 46}:
            errors.append("query_role_distribution_drift")
        if len(units) != 23 or len(rows) != 107:
            errors.append("query_unit_or_row_union_drift")

        if report.get("validation_status") != PASS_STATUS:
            errors.append("safe_report_status_drift")
        if report.get("stop_reason") != "NONE":
            errors.append("safe_report_stop_reason_not_none")
        if report.get("next_short_step") != builder.NEXT_SHORT_STEP:
            errors.append("safe_report_next_short_step_drift")
        boundaries = report.get("claim_boundaries", {})
        for key in (
            "private_answers_included",
            "learner_responses_included",
            "canonical_authority_write",
            "canonical_egp_mapping_changed",
            "public_delivery",
            "learner_mastery_claimed",
            "a2_content_promoted",
            "audio_or_recording_processed",
        ):
            if boundaries.get(key) is not False:
                errors.append(f"safe_report_claim_boundary_drift:{key}")

        rebuild_root = root.parent / f"m11c-validation-rebuild-{uuid.uuid4().hex}"
        rebuilt = builder.build_runtime_artifacts(rebuild_root, port=manifest["bind_policy"]["default_port"])
        if rebuilt["manifest"] != manifest:
            errors.append("runtime_manifest_not_reproducible")
        if rebuilt["query_index"] != query:
            errors.append("runtime_query_not_reproducible")
        if rebuilt["learner_payload"] != payload:
            errors.append("learner_payload_not_reproducible")
        if rebuilt["safe_report"] != report:
            errors.append("runtime_safe_report_not_reproducible")
    except (
        builder.AuthorityRuntimeError,
        builder.m11b.AuthorityExceptionError,
        builder.m08.TextModeSessionError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(str(exc))
    finally:
        if rebuild_root is not None:
            shutil.rmtree(rebuild_root, ignore_errors=True)

    return {
        "task_id": builder.TASK_ID,
        "validation_status": PASS_STATUS if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "private_ready_unit_count": manifest.get("authority_selection", {}).get("private_ready_units", 0),
        "private_ready_row_count": manifest.get("authority_selection", {}).get("private_ready_rows", 0),
        "selectable_item_count": query.get("item_count", 0),
        "excluded_item_count": manifest.get("text_mode_runtime", {}).get("excluded_items", 0),
        "deferred_unit_count": len(manifest.get("deferred_units", [])),
        "m08_attempt_registry_compatible": payload.get("session_bank_sha256") is not None,
        "canonical_authority_write": False,
        "canonical_egp_mapping_changed": False,
        "public_delivery": False,
        "learner_mastery_claimed": False,
        "a2_content_promoted": False,
        "audio_or_recording_processed": False,
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILURE",
        "next_short_step": builder.NEXT_SHORT_STEP if not errors else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=builder.DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--validation-report", type=Path, default=DEFAULT_VALIDATION_PATH)
    args = parser.parse_args(argv)
    result = validate(args.output_root)
    builder.write_json_atomic(args.validation_report, result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
