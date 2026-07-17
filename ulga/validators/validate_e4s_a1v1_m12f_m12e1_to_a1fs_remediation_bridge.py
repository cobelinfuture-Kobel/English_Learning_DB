#!/usr/bin/env python3
"""Independently validate the M12E1-to-A1FS M12F remediation bridge."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge as bridge  # noqa: E402
from ulga.validators import validate_a1fs_v1_m7_mastery_error_remediation_reassessment as m7_validator  # noqa: E402


def validate(
    *,
    mode: str,
    source_bank_path: Path,
    resolved_root: Path,
    m12e1_root: Path,
    consumer_path: Path,
    graph_path: Path,
    output_root: Path,
    database_path: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    report: dict[str, Any] = {}
    try:
        if mode not in {"inspect", "import-resolved"}:
            raise bridge.BridgeError("validation_mode_invalid")
        output_root = bridge._safe_root(output_root)
        report_path = output_root / (
            "m12f_bridge_mapping_safe_report.json" if mode == "inspect" else "m12f_bridge_import_safe_report.json"
        )
        report = bridge.read_json(report_path, "bridge_report")
        bridge._schema_validate(report)
        bridge._safe_scan(report)
        source = bridge._load_sources(
            source_bank_path=source_bank_path,
            resolved_root=resolved_root,
            m12e1_root=m12e1_root,
            consumer_path=consumer_path,
            graph_path=graph_path,
        )
        mapping = bridge._mapping(source)
        expected_mapping = bridge._base_report(source, mapping, mode="INSPECT")["mapping"]
        if report.get("mapping") != expected_mapping:
            errors.append("mapping_not_independently_reproducible")
        source_counts = Counter(str(row["outcome"]) for row in source["ledger"]["entries"])
        expected_counts = {name: source_counts[name] for name in bridge.m08.OUTCOMES}
        if report.get("source_outcome_counts") != expected_counts:
            errors.append("source_outcome_partition_drift")

        if mode == "inspect":
            expected_status = bridge.INSPECT_READY if mapping["ready"] else bridge.INSPECT_BLOCKED
            expected_stop = "NONE" if mapping["ready"] else "MAPPING_AUTHORITY_REQUIRED"
            if report.get("mode") != "INSPECT": errors.append("inspect_mode_drift")
            if report.get("validation_status") != expected_status: errors.append("inspect_status_drift")
            if report.get("stop_reason") != expected_stop: errors.append("inspect_stop_reason_drift")
            if report.get("import_result") is not None: errors.append("inspect_import_result_present")
        else:
            if database_path is None:
                errors.append("database_path_required")
            if not mapping["ready"]:
                errors.append("import_mapping_not_ready")
            if report.get("mode") != "IMPORT": errors.append("import_mode_drift")
            if report.get("validation_status") not in {bridge.IMPORT_STATUS, bridge.REPLAY_STATUS}:
                errors.append("import_status_drift")
            if report.get("stop_reason") != "NONE": errors.append("import_stop_reason_drift")
            imported = report.get("import_result")
            if not isinstance(imported, dict):
                errors.append("import_result_missing")
            if database_path is not None:
                database_path = Path(database_path)
                snapshot_path = output_root / "m7/a1fs_v1_m7_mastery_snapshot.private.json"
                if not database_path.is_file():
                    errors.append("database_missing")
                if not snapshot_path.is_file():
                    errors.append("m7_snapshot_missing")
                if database_path.is_file():
                    with sqlite3.connect(database_path) as connection:
                        connection.row_factory = sqlite3.Row
                        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                            errors.append("sqlite_integrity_failed")
                        if connection.execute("PRAGMA foreign_key_check").fetchall():
                            errors.append("sqlite_foreign_key_failed")
                        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
                        if metadata.get("validation_status") != bridge.m3.STATUS:
                            errors.append("m3_status_missing")
                        if metadata.get("m6_validation_status") != bridge.m6.STATUS:
                            errors.append("m6_status_missing")
                        m7_meta = dict(connection.execute("SELECT key,value FROM m7_metadata"))
                        if m7_meta.get("validation_status") != bridge.m7.STATUS:
                            errors.append("m7_status_missing")
                        receipt_table = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='m12f_bridge_receipts'").fetchone()
                        if not receipt_table:
                            errors.append("bridge_receipt_table_missing")
                        else:
                            registry_hash = bridge.m08.sha256_value(source["registry"])
                            receipt = connection.execute("SELECT * FROM m12f_bridge_receipts WHERE source_registry_sha256=?", (registry_hash,)).fetchone()
                            if not receipt:
                                errors.append("bridge_receipt_missing")
                            elif json.loads(receipt["report_json"]).get("validation_status") != bridge.IMPORT_STATUS:
                                errors.append("bridge_receipt_status_invalid")
                        rows = connection.execute(
                            """SELECT s.outcome,ls.session_state,a.attempt_id
                            FROM response_attempts a JOIN scoring_results s USING(attempt_id)
                            JOIN learning_sessions ls USING(session_id)
                            WHERE a.attempt_id LIKE 'M12F_ATT:%'"""
                        ).fetchall()
                        actual_counts = Counter(str(row["outcome"]) for row in rows)
                        if len(rows) != bridge.EXPECTED_ATTEMPTS:
                            errors.append("imported_attempt_count_invalid")
                        if {name: actual_counts[name] for name in bridge.m08.OUTCOMES} != expected_counts:
                            errors.append("database_outcome_partition_drift")
                        if any(row["session_state"] != "COMPLETED" for row in rows):
                            errors.append("bridge_session_not_completed")
                        if actual_counts["PENDING_HUMAN_REVIEW"] or actual_counts["HUMAN_DEFER"]:
                            errors.append("database_unresolved_outcome_present")
                if database_path.is_file() and snapshot_path.is_file():
                    m7_result = m7_validator.validate(database_path, graph_path, snapshot_path)
                    if m7_result["error_count"]:
                        errors.append(f"m7_validator_failed:{m7_result['errors']}")
                    snapshot = bridge.read_json(snapshot_path, "m7_snapshot")
                    open_count = sum(row.get("assignment_state") == "OPEN" for row in snapshot.get("remediation_assignments", []))
                    pending_count = sum(row.get("queue_state") == "PENDING" for row in snapshot.get("reassessment_queue", []))
                    if open_count < 1: errors.append("open_remediation_missing")
                    if pending_count < 1: errors.append("pending_reassessment_missing")
                    if snapshot.get("claim_boundaries", {}).get("human_pilot_claimed") is not False:
                        errors.append("human_pilot_overclaim")
                    if imported and (
                        imported.get("open_remediation_count") != open_count
                        or imported.get("pending_reassessment_count") != pending_count
                    ):
                        errors.append("report_snapshot_remediation_drift")
        boundaries = report.get("claim_boundaries", {})
        for key in (
            "private_responses_included", "learner_identity_included", "canonical_authority_write",
            "canonical_egp_mapping_changed", "duplicate_remediation_engine_created", "a2_content_promoted",
            "a2_payload_access_granted", "public_delivery", "audio_or_recording_processed",
            "learner_mastery_claimed", "retention_confirmed",
        ):
            if boundaries.get(key) is not False:
                errors.append(f"claim_boundary_drift:{key}")
    except (bridge.BridgeError, OSError, sqlite3.Error, KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))

    result = {
        "task_id": bridge.TASK_ID,
        "validation_mode": mode,
        "validation_status": report.get("validation_status") if not errors else "FAIL_M12F_BRIDGE_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
        "source_attempt_count": report.get("source_attempt_count", 0),
        "mapped_count": report.get("mapping", {}).get("mapped_count", 0),
        "source_outcome_counts": report.get("source_outcome_counts", {}),
        "import_result": report.get("import_result"),
        "a2_content_promoted": False,
        "canonical_authority_write": False,
        "canonical_egp_mapping_changed": False,
        "duplicate_remediation_engine_created": False,
        "learner_mastery_claimed": False,
        "retention_confirmed": False,
        "stop_reason": report.get("stop_reason", "VALIDATION_FAILURE") if not errors else "VALIDATION_FAILURE",
        "next_short_step": report.get("next_short_step") if not errors else None,
    }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["inspect", "import-resolved"])
    parser.add_argument("--source-bank", type=Path, required=True)
    parser.add_argument("--resolved-root", type=Path, required=True)
    parser.add_argument("--m12e1-root", type=Path, required=True)
    parser.add_argument("--consumer", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--validation-report", type=Path, required=True)
    args = parser.parse_args(argv)
    result = validate(
        mode=args.mode,
        source_bank_path=args.source_bank,
        resolved_root=args.resolved_root,
        m12e1_root=args.m12e1_root,
        consumer_path=args.consumer,
        graph_path=args.graph,
        output_root=args.output_root,
        database_path=args.database,
    )
    bridge.write_json(args.validation_report, result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
