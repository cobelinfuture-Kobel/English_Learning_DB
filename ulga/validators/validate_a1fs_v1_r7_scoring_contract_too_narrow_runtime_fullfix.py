#!/usr/bin/env python3
"""Independent validator for the R7 versioned scoring-contract FullFix."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5
from ulga.builders import build_a1fs_v1_r7_scoring_contract_too_narrow_runtime_fullfix as fullfix

STATUS = "PASS_R7_SCORING_CONTRACT_RUNTIME_FULLFIX_VALIDATION"
FORBIDDEN_SAFE_KEYS = {"effective_contract", "override_contract_json", "contract_json", "accepted_texts", "response"}


def _scan_safe(value: Any, errors: list[str]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in FORBIDDEN_SAFE_KEYS:
                errors.append(f"safe_private_field:{key}")
            _scan_safe(child, errors)
    elif isinstance(value, list):
        for child in value:
            _scan_safe(child, errors)
    elif isinstance(value, str) and Path(value).is_absolute():
        errors.append("safe_absolute_path")


def validate_artifacts(
    private: Mapping[str, Any], safe: Mapping[str, Any], *, database_path: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    private_core = {key: value for key, value in private.items() if key != "artifact_sha256"}
    if private.get("artifact_sha256") != r5.digest(private_core):
        errors.append("private_artifact_digest_invalid")
    remediation_core = {
        key: private.get(key) for key in (
            "task_id", "schema_version", "source_gate_sha256", "source_bank_sha256",
            "candidate_identity", "plans",
        )
    }
    if private.get("remediation_sha256") != r5.digest(remediation_core):
        errors.append("remediation_digest_invalid")
    if private.get("task_id") != fullfix.TASK_ID or private.get("schema_version") != fullfix.SCHEMA_VERSION:
        errors.append("private_identity_invalid")
    plans = private.get("plans") or []
    records = private.get("applied_records") or []
    if len(plans) != 4 or len(records) != 4:
        errors.append("four_remediation_records_required")
    if len({row.get("item_id") for row in records}) != len(records):
        errors.append("remediation_item_identity_duplicate")
    for row in records:
        contract = row.get("effective_contract")
        if not isinstance(contract, Mapping):
            errors.append(f"effective_contract_missing:{row.get('item_id')}")
            continue
        if contract.get("scoring_mode") != "FEATURE_RUBRIC" or contract.get("human_review_fallback") is not True:
            errors.append(f"feature_rubric_contract_invalid:{row.get('item_id')}")
        if r5.digest(contract) != row.get("effective_contract_digest"):
            errors.append(f"effective_contract_digest_invalid:{row.get('item_id')}")
        if row.get("base_contract_digest") == row.get("effective_contract_digest"):
            errors.append(f"effective_contract_unchanged:{row.get('item_id')}")
        criteria = contract.get("rubric", {}).get("criteria", [])
        if len(criteria) != 3 or not all(isinstance(value, Mapping) and value.get("required") is True for value in criteria):
            errors.append(f"feature_rubric_criteria_invalid:{row.get('item_id')}")
        if "accepted_texts" in contract or "accepted_sequence" in contract:
            errors.append(f"response_acceptance_list_forbidden:{row.get('item_id')}")
    migration = private.get("migration") or {}
    if migration.get("historical_rows_unchanged") is not True:
        errors.append("historical_rows_changed")
    if migration.get("history_before_sha256") != migration.get("history_after_sha256"):
        errors.append("historical_history_digest_mismatch")
    if migration.get("r4_bank_unchanged") is not True or migration.get("candidate_identity_unchanged") is not True:
        errors.append("r4_or_candidate_identity_changed")
    expected_safe = fullfix.safe_artifact(private)
    if safe != expected_safe:
        errors.append("safe_artifact_rebuild_mismatch")
    safe_core = {key: value for key, value in safe.items() if key != "report_sha256"}
    if safe.get("report_sha256") != r5.digest(safe_core):
        errors.append("safe_report_digest_invalid")
    _scan_safe(safe, errors)
    if database_path is not None:
        try:
            connection = sqlite3.connect(f"file:{Path(database_path)}?mode=ro", uri=True)
            connection.row_factory = sqlite3.Row
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                errors.append("sqlite_integrity_failed")
            if connection.execute("PRAGMA foreign_key_check").fetchall():
                errors.append("sqlite_foreign_key_failed")
            for record in records:
                row = connection.execute(
                    "SELECT * FROM edge_runtime_scoring_contract_overrides WHERE item_id=? AND status='ACTIVE'",
                    (record["item_id"],),
                ).fetchone()
                if not row:
                    errors.append(f"runtime_override_missing:{record['item_id']}")
                    continue
                if row["base_contract_digest"] != record["base_contract_digest"]:
                    errors.append(f"runtime_override_base_mismatch:{record['item_id']}")
                if row["effective_contract_digest"] != record["effective_contract_digest"]:
                    errors.append(f"runtime_override_effective_mismatch:{record['item_id']}")
                try:
                    snapshot = r5.historical_scoring_contract(connection, record["effective_contract_digest"])
                except r5.LocalEdgeRuntimeError as exc:
                    errors.append(f"runtime_snapshot_invalid:{record['item_id']}:{exc}")
                else:
                    if snapshot != record["effective_contract"]:
                        errors.append(f"runtime_snapshot_contract_mismatch:{record['item_id']}")
        except sqlite3.Error as exc:
            errors.append(f"database_unreadable:{exc}")
        finally:
            if "connection" in locals():
                connection.close()
    return {
        "validation_status": STATUS if not errors else "FAIL_R7_SCORING_CONTRACT_RUNTIME_FULLFIX_VALIDATION",
        "error_count": len(errors), "errors": errors,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-artifact", type=Path, required=True)
    parser.add_argument("--safe-artifact", type=Path, required=True)
    parser.add_argument("--database", type=Path)
    args = parser.parse_args(argv)
    result = validate_artifacts(
        r5.read_json(args.private_artifact, "private_artifact"),
        r5.read_json(args.safe_artifact, "safe_artifact"), database_path=args.database,
    )
    print(json.dumps(result, indent=2))
    return 0 if not result["error_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
