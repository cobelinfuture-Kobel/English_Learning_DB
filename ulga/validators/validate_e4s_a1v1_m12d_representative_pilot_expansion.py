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
        if mode == "prepare":
            report = builder.read_json(root / "representative_batch_readiness_safe_report.json")
        else:
            report = builder.read_json(root / "representative_pilot_expansion_safe_report.json")
        builder._assert_schema("e4s_a1v1_m12d_representative_pilot_safe_report.schema.json", report)
        builder._safe_scan(report, name="m12d_validation_safe_report")

        if manifest.get("evidence_origin") != expected_origin:
            errors.append("manifest_origin_drift")
        selection = manifest.get("batch_selection", {})
        if selection.get("batch_size") != 8:
            errors.append("batch_size_not_8")
        if selection.get("grammar_unit_count") != 4:
            errors.append("batch_unit_count_not_4")
        if selection.get("skill_counts") != {"reading": 4, "writing": 4}:
            errors.append("batch_skill_distribution_drift")
        if selection.get("role_counts") != {"practice": 4, "assessment": 4}:
            errors.append("batch_role_distribution_drift")
        item_ids = list(selection.get("item_ids", []))
        if len(item_ids) != 8 or len(set(item_ids)) != 8:
            errors.append("batch_item_identity_not_8")
        if any(str(item_id).startswith(builder.DEFERRED_GRAMMAR_ID) for item_id in item_ids):
            errors.append("deferred_will_item_in_batch")

        payload = builder.read_json(root / "session/payload.json")
        if payload.get("item_count") != 8:
            errors.append("batch_payload_item_count_not_8")
        payload_ids = [str(row.get("item_id")) for row in payload.get("items", [])]
        if payload_ids != item_ids:
            errors.append("batch_payload_order_or_identity_drift")
        encoded_payload = json.dumps(payload, ensure_ascii=False).casefold()
        for forbidden in (
            '"answer_key"',
            '"accepted_texts"',
            '"accepted_sequence"',
            '"private_scoring_contract"',
            '"model_texts"',
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

        expected_status = builder.PREPARE_STATUS if mode == "prepare" else (
            builder.REAL_STATUS if expected_origin == "REAL_LEARNER" else builder.TEST_STATUS
        )
        if report.get("validation_status") != expected_status:
            errors.append("safe_report_status_drift")
        if report.get("prior_attempt_count") != source["ledger"].get("attempt_count"):
            errors.append("prior_attempt_count_drift")
        if report.get("batch_selection", {}).get("skill_counts") != {"reading": 4, "writing": 4}:
            errors.append("safe_report_skill_distribution_drift")
        if report.get("batch_selection", {}).get("role_counts") != {"practice": 4, "assessment": 4}:
            errors.append("safe_report_role_distribution_drift")

        if mode == "prepare":
            if report.get("batch_attempt_count") != 0:
                errors.append("prepare_batch_attempt_count_not_zero")
            if report.get("cumulative_attempt_count") != report.get("prior_attempt_count"):
                errors.append("prepare_cumulative_attempt_drift")
            if report.get("stop_reason") != "REAL_LEARNER_REPRESENTATIVE_BATCH_REQUIRED":
                errors.append("prepare_stop_reason_drift")
            rebuild_root = root.parent / f"m12d-prepare-rebuild-{uuid.uuid4().hex}"
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
        else:
            batch_registry = builder.read_json(root / "representative_batch_attempt_registry.private.json")
            cumulative_registry = builder.read_json(root / "cumulative_attempt_registry.private.json")
            ledger = builder.read_json(root / "cumulative_progress_ledger.private.json")
            query = builder.read_json(root / "cumulative_progress_query_index.json")
            try:
                batch_attempts = builder._validate_batch_registry(manifest, source["registry"], batch_registry)
            except builder.RepresentativePilotError as exc:
                errors.append(str(exc))
                batch_attempts = []
            if report.get("batch_attempt_count") != len(batch_attempts):
                errors.append("batch_attempt_count_drift")
            if ledger.get("attempt_count") != report.get("cumulative_attempt_count"):
                errors.append("cumulative_ledger_report_attempt_drift")
            if query.get("attempt_count") != ledger.get("attempt_count"):
                errors.append("cumulative_query_ledger_attempt_drift")
            if len(cumulative_registry.get("attempts", [])) != ledger.get("attempt_count"):
                errors.append("cumulative_registry_ledger_attempt_drift")
            if ledger.get("attempt_count") != source["ledger"].get("attempt_count") + len(batch_attempts):
                errors.append("prior_plus_batch_attempt_accounting_drift")
            cumulative_ids = [str(row.get("item_id")) for row in cumulative_registry.get("attempts", [])]
            if len(cumulative_ids) != len(set(cumulative_ids)):
                errors.append("cumulative_duplicate_item")
            if any(item_id.startswith(builder.DEFERRED_GRAMMAR_ID) for item_id in cumulative_ids):
                errors.append("cumulative_deferred_will_item")
            if cumulative_registry.get("session_bank_sha256") != manifest.get("attempt_registry_contract", {}).get("session_bank_sha256"):
                errors.append("cumulative_registry_bank_hash_drift")
            if expected_origin == "REAL_LEARNER":
                if report.get("stop_reason") != "NONE":
                    errors.append("real_import_stop_reason_not_none")
                if report.get("next_short_step") != builder.NEXT_QA:
                    errors.append("real_import_next_step_drift")
            else:
                if report.get("stop_reason") != "REAL_LEARNER_REPRESENTATIVE_BATCH_REQUIRED":
                    errors.append("fixture_import_stop_reason_drift")
                if report.get("next_short_step") != builder.NEXT_IMPORT:
                    errors.append("fixture_import_next_step_drift")
            rebuild_root = root.parent / f"m12d-import-rebuild-{uuid.uuid4().hex}"
            rebuilt = builder.import_batch(
                input_root,
                qa_root,
                rebuild_root,
                root / "representative_batch_attempt_registry.private.json",
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
            "private_responses_included",
            "learner_identity_included",
            "test_fixture_counted_as_real_evidence",
            "canonical_authority_write",
            "canonical_egp_mapping_changed",
            "public_delivery",
            "production_runtime_enabled",
            "a2_content_promoted",
            "audio_or_recording_processed",
            "learner_mastery_claimed",
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

    expected_status = builder.PREPARE_STATUS if mode == "prepare" else (
        builder.REAL_STATUS if expected_origin == "REAL_LEARNER" else builder.TEST_STATUS
    )
    return {
        "task_id": builder.TASK_ID,
        "validation_mode": mode,
        "validation_status": expected_status if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "evidence_origin": report.get("evidence_origin"),
        "prior_attempt_count": report.get("prior_attempt_count", 0),
        "batch_attempt_count": report.get("batch_attempt_count", 0),
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
