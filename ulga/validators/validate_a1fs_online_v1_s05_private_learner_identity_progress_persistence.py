#!/usr/bin/env python3
"""Reentrant S05 validator preserving the original eleven-contract baseline."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_online_v1_s05_private_learner_identity_progress_persistence as s05
from ulga.validators import _validate_a1fs_online_v1_s05_private_learner_identity_progress_persistence_core as _core

for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Validates preservation of the original S04 response-contract baseline after authorized downstream runtime expansion."
BASELINE_RESPONSE_CONTRACT_COUNT = 11
COUNT_ERROR = "s05_response_contract_count_invalid"


def _baseline_response_contract_readback(
    *,
    database_path: Path,
    consumer_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    result: dict[str, Any] = {
        "baseline_response_contract_count": 0,
        "total_response_contract_count": 0,
        "downstream_response_contract_count": 0,
        "errors": errors,
    }
    try:
        consumer = json.loads(Path(consumer_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"s05_baseline_consumer_unreadable:{exc}")
        return result
    if not isinstance(consumer, Mapping):
        errors.append("s05_baseline_consumer_not_object")
        return result
    assets = consumer.get("asset_records")
    if not isinstance(assets, list):
        errors.append("s05_baseline_asset_records_not_list")
        return result
    baseline_assets: dict[str, Mapping[str, Any]] = {}
    for asset in assets:
        if not isinstance(asset, Mapping):
            errors.append("s05_baseline_asset_not_object")
            continue
        asset_key = str(asset.get("asset_key") or "")
        if not asset_key or asset_key in baseline_assets:
            errors.append(f"s05_baseline_asset_identity_invalid:{asset_key}")
            continue
        baseline_assets[asset_key] = asset
    result["baseline_response_contract_count"] = len(baseline_assets)
    if len(baseline_assets) != BASELINE_RESPONSE_CONTRACT_COUNT:
        errors.append(
            "s05_baseline_response_contract_denominator_invalid:"
            f"{len(baseline_assets)}"
        )
        return result
    if not Path(database_path).is_file():
        errors.append("s05_baseline_database_missing")
        return result
    try:
        with sqlite3.connect(database_path) as connection:
            connection.row_factory = sqlite3.Row
            total = int(
                connection.execute("SELECT COUNT(*) FROM response_contracts").fetchone()[0]
            )
            result["total_response_contract_count"] = total
            result["downstream_response_contract_count"] = max(
                0, total - len(baseline_assets)
            )
            placeholders = ",".join("?" for _ in baseline_assets)
            rows = connection.execute(
                "SELECT asset_key,lesson_id,skill,role,contract_json,"
                "contract_digest,capture_enabled FROM response_contracts "
                f"WHERE asset_key IN ({placeholders})",
                tuple(baseline_assets),
            ).fetchall()
    except sqlite3.Error as exc:
        errors.append(f"s05_baseline_database_invalid:{exc}")
        return result
    stored_by_key = {str(row["asset_key"]): row for row in rows}
    missing = sorted(set(baseline_assets) - set(stored_by_key))
    if missing:
        errors.append("s05_baseline_response_contract_missing:" + ",".join(missing))
    drifted: list[str] = []
    for asset_key, asset in baseline_assets.items():
        row = stored_by_key.get(asset_key)
        if row is None:
            continue
        try:
            contract = s05.m6.derive_contract(asset)
        except (s05.m6.ResponseEvidenceError, KeyError, TypeError, ValueError) as exc:
            errors.append(f"s05_baseline_contract_derivation_failed:{asset_key}:{exc}")
            continue
        expected = (
            str(contract["lesson_id"]),
            str(contract["skill"]),
            str(contract["role"]),
            s05.m6.canonical(contract),
            s05.m6.sha(contract),
            int(bool(contract["capture_enabled"])),
        )
        actual = (
            str(row["lesson_id"]),
            str(row["skill"]),
            str(row["role"]),
            str(row["contract_json"]),
            str(row["contract_digest"]),
            int(row["capture_enabled"]),
        )
        if actual != expected:
            drifted.append(asset_key)
    if drifted:
        errors.append("s05_baseline_response_contract_drift:" + ",".join(sorted(drifted)))
    if result["total_response_contract_count"] < BASELINE_RESPONSE_CONTRACT_COUNT:
        errors.append(
            "s05_total_response_contract_count_below_baseline:"
            f"{result['total_response_contract_count']}"
        )
    return result


def validate_outputs(
    *,
    receipt: Mapping[str, Any],
    safe_report: Mapping[str, Any],
    output_root: Path,
    s04_receipt_path: Path,
) -> dict[str, Any]:
    result = dict(
        _core.validate_outputs(
            receipt=receipt,
            safe_report=safe_report,
            output_root=output_root,
            s04_receipt_path=s04_receipt_path,
        )
    )
    outputs = receipt.get("persistent_outputs", {})
    baseline = _baseline_response_contract_readback(
        database_path=Path(str(outputs.get("database_path") or "")),
        consumer_path=Path(str(outputs.get("consumer_path") or "")),
    )
    errors = [str(error) for error in result.get("errors", [])]
    baseline_errors = [str(error) for error in baseline["errors"]]
    if (
        COUNT_ERROR in errors
        and not baseline_errors
        and baseline["total_response_contract_count"]
        >= baseline["baseline_response_contract_count"]
        == BASELINE_RESPONSE_CONTRACT_COUNT
    ):
        errors = [error for error in errors if error != COUNT_ERROR]
    errors.extend(baseline_errors)
    errors = list(dict.fromkeys(errors))
    counts = dict(result.get("validated_counts", {}))
    counts.update(
        {
            "baseline_response_contract_count": baseline[
                "baseline_response_contract_count"
            ],
            "downstream_response_contract_count": baseline[
                "downstream_response_contract_count"
            ],
        }
    )
    result.update(
        {
            "validation_status": (
                _core.VALIDATION_STATUS
                if not errors
                else "FAIL_A1FS_ONLINE_V1_S05_PRIVATE_IDENTITY_PROGRESS"
            ),
            "error_count": len(errors),
            "errors": errors,
            "validated_counts": counts,
            "stop_reason": (
                "NONE" if not errors else "S05_IDENTITY_PROGRESS_VALIDATION_FAILED"
            ),
            "next_short_step": s05.NEXT_SHORT_STEP if not errors else s05.TASK_ID,
        }
    )
    return result
