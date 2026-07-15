#!/usr/bin/env python3
"""Independently validate M12D representative pilot preparation/import."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m12d_representative_pilot_expansion as builder  # noqa: E402

DEFAULT_VALIDATION_PATH = builder.DEFAULT_OUTPUT_ROOT / "representative_pilot_validation.json"


def _expected_import_status(origin: str, batch_count: int) -> tuple[str, str, str]:
    if batch_count < builder.BATCH_SIZE:
        return (
            builder.PARTIAL_STATUS,
            "REAL_LEARNER_REPRESENTATIVE_BATCH_INCOMPLETE",
            builder.NEXT_IMPORT,
        )
    if origin == "REAL_LEARNER":
        return builder.REAL_STATUS, "NONE", builder.NEXT_QA
    return (
        builder.TEST_STATUS,
        "REAL_LEARNER_REPRESENTATIVE_BATCH_REQUIRED",
        builder.NEXT_IMPORT,
    )


def validate(
    mode: str,
    input_root: Path,
    qa_root: Path,
    output_root: Path,
    *,
    expected_origin: str,
) -> dict[str, Any]:
    errors: list[str] = []
    manifest: dict[str, Any] = {}
    report: dict[str, Any] = {}
    rebuild_root: Path | None = None
    try:
        if mode not in {"prepare", "import-batch"}:
            raise builder.RepresentativePilotError(f"validation_mode_invalid:{mode}")
        root = builder._safe_root(output_root)
        manifest = builder.read_json(root / "representative_batch_manifest.private.json")
        builder._assert_schema("e4s_a1v1_m12d_representative_pilot_batch_manifest.schema.json", manifest)
        report_path = root / (
            "representative_batch_readiness_safe_report.json"
            if mode == "prepare"
            else "representative_pilot_expansion_safe_report.json"
        )
        report = builder.read_json(report_path)
        builder._assert_schema("e4s_a1v1_m12d_representative_pilot_safe_report.schema.json", report)
        builder._safe_scan(report, name="m12d_validation_safe_report")

        if manifest.get("evidence_origin") != expected_origin:
            errors.append("manifest_origin_drift")
        selection = manifest.get("batch_selection", {})
        if selection.get("batch_size") != builder.BATCH_SIZE:
            errors.append("batch_size_not_8")
        if selection.get("grammar_unit_count") != 4:
            errors.append("batch_unit_count_not_4")
        if selection.get("skill_counts") != {"reading": 4, "writing": 4}:
            errors.append("batch_skill_distribution_drift")
        if selection.get("role_counts") != {"practice": 4, "assessment": 4}:
            errors.append("batch_role_distribution_drift")
        item_ids = [str(value) for value in selection.get("item_ids", [])]
        if len(item_ids) != builder.BATCH_SIZE or len(set(item_ids)) != builder.BATCH_SIZE:
            errors.append("batch_item_identity_not_8")
        if any(value.startswith(builder.DEFERRED_GRAMMAR_ID) for value in item_ids):
            errors.append("deferred_will_item_in_batch")
        if manifest.get("attempt_registry_contract", {}).get("completion_attempt_count") != builder.BATCH_SIZE:
            errors.append("completion_attempt_contract_not_8")

        payload = builder.read_json(root / "session/payload.json")
        resume = builder.read_json(root / "session/resume_state.json")
        if payload.get("item_count") != builder.BATCH_SIZE:
            errors.append("batch_payload_item_count_not_8")
        payload_ids = [str(row.get("item_id")) for row in payload.get("items", [])]
        if payload_ids != item_ids:
            errors.append("batch_payload_order_or_identity_drift")
        captured_ids = [str(value) for value in resume.get("captured_item_ids", [])]
        remaining_ids = [str(value) for value in resume.get("remaining_item_ids", [])]
        if set(captured_ids) & set(remaining_ids):
            errors.append("resume_state_overlap")
        if set(captured_ids) | set(remaining_ids) != set(item_ids):
            errors.append("resume_state_partition_drift")
        if resume.get("captured_attempt_count") != len(captured_ids):
            errors.append("resume_captured_count_drift")
        if resume.get("remaining_attempt_count") != len(remaining_ids):
            errors.append("resume_remaining_count_drift")
        if len(captured_ids) + len(remaining_ids) != builder.BATCH_SIZE:
            errors.append("resume_total_not_8")
        encoded_payload = json.dumps(payload, ensure_ascii=False).casefold()
        for forbidden in (
            '"answer_key"', '"accepted_texts"', '"accepted_sequence"',
            '"private_scoring_contract"', '"model_texts"',
        ):
            if forbidden in encoded_payload:
                errors.append(f"learner_payload_private_field:{forbidden}")

        source = builder._load_sources(input_root, qa_root, expected_origin=expected_origin)
        expected_selected, expected_selection = builder._select_batch(source)
        if expected_selection != selection:
            errors.append("batch_selection_not_reproducible")
        if [row["item_id"] for row in expected_selected] != item_ids:
            errors.append("batch_selected_items_not_reproducible")
        if manifest.get("source_hashes", {}).get("m08_source_bank_sha256") != builder.m12.m08.sha256_value(source["source_bank"]):
            errors.append("source_bank_hash_drift")
        prior_ids = {str(row["item_id"]) for row in source["ledger"].get("entries", [])}
        if set(item_ids) & prior_ids:
            errors.append("batch_contains_prior_attempted_item")

        saved_registry_path = root / "representative_batch_attempt_registry.private.json"
        saved_registry: dict[str, Any] | None = None
        saved_attempts: list[dict[str, Any]] = []
        if saved_registry_path.is_file():
            saved_registry = builder.read_json(saved_registry_path)
            saved_attempts = builder._validate_batch_registry(manifest, source["registry"], saved_registry)
        saved_count = len(saved_attempts)
        if set(captured_ids) != {str(row["item_id"]) for row in saved_attempts}:
            errors.append("resume_state_saved_registry_drift")
        if report.get("batch_attempt_count") != saved_count:
            errors.append("safe_report_batch_attempt_count_drift")
        if report.get("remaining_batch_attempt_count") != builder.BATCH_SIZE - saved_count:
            errors.append("safe_report_remaining_count_drift")
        if report.get("prior_attempt_count") != source["ledger"].get("attempt_count"):
            errors.append("prior_attempt_count_drift")
        if report.get("batch_selection", {}).get("skill_counts") != {"reading": 4, "writing": 4}:
            errors.append("safe_report_skill_distribution_drift")
        if report.get("batch_selection", {}).get("role_counts") != {"practice": 4, "assessment": 4}:
            errors.append("safe_report_role_distribution_drift")

        if mode == "prepare":
            expected_status = builder.PREPARE_STATUS
            expected_stop = (
                "REAL_LEARNER_REPRESENTATIVE_BATCH_REQUIRED"
                if saved_count == 0
                else "REAL_LEARNER_REPRESENTATIVE_BATCH_INCOMPLETE"
            )
            if report.get("validation_status") != expected_status:
                errors.append("prepare_status_drift")
            if report.get("stop_reason") != expected_stop:
                errors.append("prepare_stop_reason_drift")
            if report.get("next_short_step") != builder.NEXT_IMPORT:
                errors.append("prepare_next_step_drift")
            expected_cumulative = int(source["ledger"]["attempt_count"]) + saved_count
            if report.get("cumulative_attempt_count") != expected_cumulative:
                errors.append("prepare_cumulative_attempt_drift")
            rebuild_root = root.parent / f"m12d-prepare-rebuild-{uuid.uuid4().hex}"
            if saved_registry is not None:
                rebuild_root.mkdir(parents=True, exist_ok=True)
                builder.write_json_atomic(
                    rebuild_root / "representative_batch_attempt_registry.private.json",
                    saved_registry,
                )
            rebuilt = builder.prepare_batch(
                input_root,
                qa_root,
                rebuild_root,
                expected_origin=expected_origin,
                port=manifest["runtime"]["default_port"],
            )
            if rebuilt["manifest"] != manifest:
                errors.append("prepare_manifest_not_reproducible")
            if rebuilt["safe_report"] != report:
                errors.append("prepare_report_not_reproducible")
            if rebuilt["batch_payload"] != payload:
                errors.append("prepare_payload_not_reproducible")
            if rebuilt["resume_state"] != resume:
                errors.append("prepare_resume_state_not_reproducible")
        else:
            if saved_registry is None:
                errors.append("import_saved_registry_missing")
            cumulative_registry = builder.read_json(root / "cumulative_attempt_registry.private.json")
            ledger = builder.read_json(root / "cumulative_progress_ledger.private.json")
            query = builder.read_json(root / "cumulative_progress_query_index.json")
            expected_status, expected_stop, expected_next = _expected_import_status(expected_origin, saved_count)
            if report.get("validation_status") != expected_status:
                errors.append("import_status_drift")
            if report.get("stop_reason") != expected_stop:
                errors.append("import_stop_reason_drift")
            if report.get("next_short_step") != expected_next:
                errors.append("import_next_step_drift")
            if saved_count < builder.BATCH_SIZE and report.get("next_short_step") == builder.NEXT_QA:
                errors.append("partial_batch_advanced_to_m12e")
            if ledger.get("attempt_count") != report.get("cumulative_attempt_count"):
                errors.append("cumulative_ledger_report_attempt_drift")
            if query.get("attempt_count") != ledger.get("attempt_count"):
                errors.append("cumulative_query_ledger_attempt_drift")
            if len(cumulative_registry.get("attempts", [])) != ledger.get("attempt_count"):
                errors.append("cumulative_registry_ledger_attempt_drift")
            if ledger.get("attempt_count") != source["ledger"].get("attempt_count") + saved_count:
                errors.append("prior_plus_batch_attempt_accounting_drift")
            cumulative_ids = [str(row.get("item_id")) for row in cumulative_registry.get("attempts", [])]
            if len(cumulative_ids) != len(set(cumulative_ids)):
                errors.append("cumulative_duplicate_item")
            if any(value.startswith(builder.DEFERRED_GRAMMAR_ID) for value in cumulative_ids):
                errors.append("cumulative_deferred_will_item")
            if cumulative_registry.get("session_bank_sha256") != manifest.get("attempt_registry_contract", {}).get("session_bank_sha256"):
                errors.append("cumulative_registry_bank_hash_drift")
            rebuild_root = root.parent / f"m12d-import-rebuild-{uuid.uuid4().hex}"
            rebuilt = builder.import_batch(
                input_root,
                qa_root,
                rebuild_root,
                saved_registry_path,
                expected_origin=expected_origin,
                port=manifest["runtime"]["default_port"],
            )
            if rebuilt["manifest"] != manifest:
                errors.append("import_manifest_not_reproducible")
            if rebuilt["safe_report"] != report:
                errors.append("import_report_not_reproducible")
            if rebuilt["ledger"] != ledger:
                errors.append("import_ledger_not_reproducible")
            if rebuilt["query"] != query:
                errors.append("import_query_not_reproducible")

        boundaries = report.get("claim_boundaries", {})
        for key in (
            "private_responses_included", "learner_identity_included",
            "test_fixture_counted_as_real_evidence", "canonical_authority_write",
            "canonical_egp_mapping_changed", "public_delivery",
            "production_runtime_enabled", "a2_content_promoted",
            "audio_or_recording_processed", "learner_mastery_claimed",
            "retention_confirmed",
        ):
            if boundaries.get(key) is not False:
                errors.append(f"claim_boundary_drift:{key}")
    except (
        builder.RepresentativePilotError,
        builder.m12.PilotCaptureError,
        builder.m12c.EvidenceQAError,
        builder.m12.m11c.AuthorityRuntimeError,
        builder.m12.m08.TextModeSessionError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(str(exc))
    finally:
        if rebuild_root is not None:
            shutil.rmtree(rebuild_root, ignore_errors=True)

    batch_count = int(report.get("batch_attempt_count", 0) or 0)
    if mode == "prepare":
        expected_status = builder.PREPARE_STATUS
    else:
        expected_status = _expected_import_status(expected_origin, batch_count)[0]
    return {
        "task_id": builder.TASK_ID,
        "validation_mode": mode,
        "validation_status": expected_status if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "evidence_origin": report.get("evidence_origin"),
        "prior_attempt_count": report.get("prior_attempt_count", 0),
        "batch_attempt_count": batch_count,
        "remaining_batch_attempt_count": report.get("remaining_batch_attempt_count", builder.BATCH_SIZE),
        "cumulative_attempt_count": report.get("cumulative_attempt_count", 0),
        "cumulative_attempted_unit_count": report.get("cumulative_attempted_unit_count", 0),
        "cumulative_attempted_row_count": report.get("cumulative_attempted_row_count", 0),
        "batch_size": manifest.get("batch_selection", {}).get("batch_size", 0),
        "batch_unit_count": manifest.get("batch_selection", {}).get("grammar_unit_count", 0),
        "learner_mastery_claimed": False,
        "retention_confirmed": False,
        "public_delivery": False,
        "a2_content_promoted": False,
        "audio_or_recording_processed": False,
        "stop_reason": report.get("stop_reason", "VALIDATION_FAILURE") if not errors else "VALIDATION_FAILURE",
        "next_short_step": report.get("next_short_step") if not errors else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "import-batch"])
    parser.add_argument("--input-root", type=Path, default=builder.DEFAULT_INPUT_ROOT)
    parser.add_argument("--qa-root", type=Path, default=builder.DEFAULT_QA_ROOT)
    parser.add_argument("--output-root", type=Path, default=builder.DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--expected-origin", choices=sorted(builder.EVIDENCE_ORIGINS), required=True)
    parser.add_argument("--validation-report", type=Path, default=DEFAULT_VALIDATION_PATH)
    args = parser.parse_args(argv)
    result = validate(
        args.mode,
        args.input_root,
        args.qa_root,
        args.output_root,
        expected_origin=args.expected_origin,
    )
    builder.write_json_atomic(args.validation_report, result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["validation_status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
