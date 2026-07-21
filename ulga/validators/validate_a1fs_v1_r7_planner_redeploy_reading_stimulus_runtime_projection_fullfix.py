#!/usr/bin/env python3
"""Independently validate the R7 Reading runtime stimulus projection FullFix."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5
from ulga.builders import build_a1fs_v1_r7_planner_redeploy_reading_stimulus_runtime_projection_fullfix as projection
from ulga.builders import build_a1fs_v1_shared_learner_stimulus_contract_renderer as stimulus

TASK_ID = projection.TASK_ID
PASS_STATUS = projection.STATUS


def _read(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{code}_not_object")
    return value


def _digest_valid(value: Mapping[str, Any], field: str) -> bool:
    actual = value.get(field)
    return (
        isinstance(actual, str)
        and len(actual) == 64
        and actual == projection.digest({key: child for key, child in value.items() if key != field})
    )


def _validate_runtime_database(
    database_path: Path,
    artifact: Mapping[str, Any],
    errors: list[str],
) -> None:
    try:
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
    except sqlite3.Error as exc:
        errors.append(f"runtime_database_unreadable:{exc}")
        return
    try:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            errors.append("runtime_integrity_check_failed")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            errors.append("runtime_foreign_key_check_failed")
        names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        required = {"r5_metadata", "edge_runtime_items", "edge_runtime_delivery_projection"}
        if required - names:
            errors.extend(f"runtime_table_missing:{name}" for name in sorted(required - names))
            return
        metadata = dict(connection.execute("SELECT key,value FROM r5_metadata"))
        if metadata.get("source_delivery_projection_sha256") != artifact.get("projection_sha256"):
            errors.append("runtime_projection_metadata_binding_mismatch")
        if metadata.get("source_bank_sha256") != artifact.get("source_bindings", {}).get("r4_bank_sha256"):
            errors.append("runtime_r4_bank_metadata_binding_mismatch")
        deliveries = artifact.get("deliveries", [])
        projected_rows = {
            row["item_id"]: row
            for row in connection.execute("SELECT * FROM edge_runtime_delivery_projection")
        }
        if len(projected_rows) != len(deliveries):
            errors.append(f"runtime_projection_row_count_mismatch:{len(projected_rows)}:{len(deliveries)}")
        for delivery in deliveries:
            item_id = str(delivery.get("item_id") or "")
            bound = projected_rows.get(item_id)
            if bound is None:
                errors.append(f"runtime_projection_row_missing:{item_id}")
                continue
            expected_fields = {
                "work_item_id": delivery.get("work_item_id"),
                "canonical_candidate_sha256": delivery.get("canonical_candidate_sha256"),
                "canonical_stimulus_fingerprint": delivery.get("canonical_stimulus_fingerprint"),
                "delivery_fingerprint": delivery.get("delivery_fingerprint"),
                "delivery_contract_sha256": delivery.get("delivery_contract_sha256"),
                "runtime_item_digest": delivery.get("runtime_item_digest"),
                "m2_asset_id": delivery.get("m2_asset_id"),
                "m2_lesson_id": delivery.get("m2_lesson_id"),
                "m2_content_digest": delivery.get("m2_content_digest"),
                "projected_learner_contract_sha256": delivery.get("projected_learner_contract_sha256"),
                "stimulus_render_manifest_sha256": delivery.get("stimulus_render_manifest_sha256"),
                "projection_sha256": artifact.get("projection_sha256"),
            }
            for key, expected in expected_fields.items():
                if bound[key] != expected:
                    errors.append(f"runtime_projection_binding_mismatch:{item_id}:{key}")
            runtime_item = connection.execute(
                "SELECT item_json,item_digest FROM edge_runtime_items WHERE item_id=?", (item_id,)
            ).fetchone()
            if runtime_item is None:
                errors.append(f"runtime_item_missing:{item_id}")
                continue
            try:
                item = json.loads(runtime_item["item_json"])
            except json.JSONDecodeError:
                errors.append(f"runtime_item_json_invalid:{item_id}")
                continue
            if runtime_item["item_digest"] != r5.digest(item):
                errors.append(f"runtime_item_digest_invalid:{item_id}")
            if runtime_item["item_digest"] != delivery.get("runtime_item_digest"):
                errors.append(f"runtime_item_projection_digest_mismatch:{item_id}")
            if item.get("candidate_sha256") != delivery.get("canonical_candidate_sha256"):
                errors.append(f"runtime_candidate_identity_changed:{item_id}")
            if item.get("stimulus_fingerprint") != delivery.get("canonical_stimulus_fingerprint"):
                errors.append(f"runtime_stimulus_identity_changed:{item_id}")
            learner = item.get("learner_contract")
            scoring = item.get("private_scoring_contract")
            if not isinstance(learner, Mapping) or not isinstance(scoring, Mapping):
                errors.append(f"runtime_item_contract_missing:{item_id}")
                continue
            try:
                rebuilt = stimulus.ensure_learner_contract(
                    item_id=item_id,
                    task_type=str(item.get("task_type") or ""),
                    learner=learner,
                    scoring=scoring,
                    media_payload_state=str(item.get("media_payload_state") or "NOT_REQUIRED"),
                )
            except stimulus.StimulusContractError as exc:
                errors.append(f"runtime_item_not_answerable:{item_id}:{exc}")
            else:
                if rebuilt != learner:
                    errors.append(f"runtime_learner_contract_rebuild_drift:{item_id}")
    finally:
        connection.close()


def validate(
    *,
    bank_path: Path,
    deployment_queue_path: Path,
    consumer_path: Path,
    output_root: Path,
    database_path: Path | None = None,
    expected_deployment_count: int = 209,
    expected_projected_count: int = 198,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        bank = _read(bank_path, "r4_bank")
        deployment = _read(deployment_queue_path, "deployment_queue")
        consumer = _read(consumer_path, "m2_consumer")
        artifact = _read(output_root / projection.PROJECTION_FILENAME, "projection")
        safe = _read(output_root / projection.SAFE_FILENAME, "safe_report")
        session = _read(output_root / projection.SESSION_FILENAME, "session_manifest")
        session_safe = _read(output_root / projection.SESSION_SAFE_FILENAME, "session_safe_report")
    except ValueError as exc:
        return {
            "validation_status": "FAIL_R7_READING_RUNTIME_PROJECTION_VALIDATION",
            "error_count": 1,
            "errors": [str(exc)],
        }

    for value, field, code in (
        (artifact, "projection_sha256", "projection_digest_invalid"),
        (safe, "report_sha256", "safe_report_digest_invalid"),
        (session, "manifest_sha256", "session_manifest_digest_invalid"),
        (session_safe, "report_sha256", "session_safe_report_digest_invalid"),
    ):
        if not _digest_valid(value, field):
            errors.append(code)

    if artifact.get("task_id") != TASK_ID or artifact.get("schema_version") != projection.SCHEMA_VERSION:
        errors.append("projection_identity_invalid")
    if artifact.get("validation_status") != PASS_STATUS or artifact.get("private_local_only") is not True:
        errors.append("projection_status_or_privacy_invalid")
    if safe.get("schema_version") != projection.SAFE_SCHEMA_VERSION:
        errors.append("safe_schema_invalid")
    if session.get("schema_version") != projection.SESSION_SCHEMA_VERSION:
        errors.append("session_schema_invalid")
    if session_safe.get("schema_version") != projection.SESSION_SAFE_SCHEMA_VERSION:
        errors.append("session_safe_schema_invalid")

    try:
        expected = projection.build_projection(
            bank=bank,
            deployment_queue=deployment,
            consumer=consumer,
            bank_file_sha256=projection.file_digest(bank_path),
            deployment_file_sha256=projection.file_digest(deployment_queue_path),
            consumer_file_sha256=projection.file_digest(consumer_path),
            expected_deployment_count=expected_deployment_count,
            expected_projected_count=expected_projected_count,
        )
    except Exception as exc:
        errors.append(f"independent_rebuild_failed:{exc}")
        expected = None
    if expected is not None:
        for actual, rebuilt, code in zip(
            (artifact, safe, session, session_safe),
            expected,
            (
                "projection_rebuild_drift", "safe_report_rebuild_drift",
                "session_manifest_rebuild_drift", "session_safe_report_rebuild_drift",
            ),
        ):
            if actual != rebuilt:
                errors.append(code)

    try:
        projection.safe_scan(safe)
        projection.safe_scan(session_safe)
    except projection.RuntimeProjectionError as exc:
        errors.append(f"safe_scan_failed:{exc}")

    items = bank.get("items") if isinstance(bank.get("items"), list) else []
    bank_by_id = {
        str(item.get("item_id")): item
        for item in items
        if isinstance(item, Mapping) and item.get("item_id")
    }
    deliveries = artifact.get("deliveries") if isinstance(artifact.get("deliveries"), list) else []
    if len(deliveries) != expected_deployment_count:
        errors.append(f"delivery_count_mismatch:{len(deliveries)}:{expected_deployment_count}")
    if len({row.get("work_item_id") for row in deliveries}) != len(deliveries):
        errors.append("work_item_identity_not_unique")
    projected_count = 0
    learner_renderable_count = 0
    canonical_change_count = 0
    for delivery in deliveries:
        item_id = str(delivery.get("item_id") or "")
        item = bank_by_id.get(item_id)
        if item is None:
            errors.append(f"canonical_item_missing:{item_id}")
            continue
        if delivery.get("canonical_candidate_sha256") != item.get("candidate_sha256"):
            errors.append(f"canonical_candidate_binding_mismatch:{item_id}")
            canonical_change_count += 1
        if delivery.get("canonical_stimulus_fingerprint") != item.get("stimulus_fingerprint"):
            errors.append(f"canonical_stimulus_binding_mismatch:{item_id}")
            canonical_change_count += 1
        learner = delivery.get("projected_learner_contract")
        scoring = item.get("private_scoring_contract")
        if not isinstance(learner, Mapping) or not isinstance(scoring, Mapping):
            errors.append(f"projected_contract_missing:{item_id}")
            continue
        try:
            rebuilt_learner = stimulus.ensure_learner_contract(
                item_id=item_id,
                task_type=str(item.get("task_type") or ""),
                learner=learner,
                scoring=scoring,
                media_payload_state=str(item.get("media_payload_state") or "NOT_REQUIRED"),
            )
        except stimulus.StimulusContractError as exc:
            errors.append(f"projected_contract_not_answerable:{item_id}:{exc}")
            continue
        if rebuilt_learner != learner:
            errors.append(f"projected_contract_rebuild_drift:{item_id}")
        else:
            learner_renderable_count += 1
        if delivery.get("projection_applied") is True:
            projected_count += 1
            kinds = set(delivery.get("source_dependency_kinds") or [])
            if not kinds & {"TEXT", "DIALOGUE", "TABLE"}:
                errors.append(f"projected_visible_source_missing:{item_id}")
            if not delivery.get("m2_asset_id") or not delivery.get("m2_lesson_id") or not delivery.get("m2_content_digest"):
                errors.append(f"projected_m2_binding_missing:{item_id}")
        runtime_binding = {
            "task_id": TASK_ID,
            "work_item_id": delivery.get("work_item_id"),
            "delivery_fingerprint": delivery.get("delivery_fingerprint"),
            "canonical_candidate_sha256": delivery.get("canonical_candidate_sha256"),
            "canonical_stimulus_fingerprint": delivery.get("canonical_stimulus_fingerprint"),
            "m2_asset_id": delivery.get("m2_asset_id"),
            "m2_lesson_id": delivery.get("m2_lesson_id"),
            "m2_content_digest": delivery.get("m2_content_digest"),
            "projection_applied": delivery.get("projection_applied"),
        }
        runtime_item = deepcopy(dict(item))
        runtime_item["learner_contract"] = deepcopy(dict(learner))
        runtime_item["runtime_delivery_binding"] = runtime_binding
        if delivery.get("runtime_item_digest") != r5.digest(runtime_item):
            errors.append(f"runtime_item_digest_invalid:{item_id}")
        delivery_core = {
            key: value for key, value in delivery.items()
            if key not in {
                "delivery_fingerprint", "delivery_contract_sha256", "runtime_item_digest",
                "projected_learner_contract", "renderability_status",
            }
        }
        if delivery.get("delivery_fingerprint") != projection.digest(delivery_core):
            errors.append(f"delivery_fingerprint_invalid:{item_id}")
        if delivery.get("delivery_contract_sha256") != projection.digest({
            "learner_contract": learner,
            "runtime_delivery_binding": runtime_binding,
        }):
            errors.append(f"delivery_contract_digest_invalid:{item_id}")

    counts = artifact.get("counts", {})
    expected_counts = {
        "deployment_count": expected_deployment_count,
        "source_dependency_projection_count": expected_projected_count,
        "learner_renderable_count": expected_deployment_count,
        "learner_renderability_failure_count": 0,
        "synthetic_evidence_count": 0,
    }
    for key, expected_value in expected_counts.items():
        if counts.get(key) != expected_value:
            errors.append(f"projection_count_invalid:{key}:{counts.get(key)}:{expected_value}")
    if projected_count != expected_projected_count:
        errors.append(f"projected_delivery_count_invalid:{projected_count}:{expected_projected_count}")
    if learner_renderable_count != expected_deployment_count:
        errors.append(f"learner_renderable_rebuild_count_invalid:{learner_renderable_count}:{expected_deployment_count}")
    if canonical_change_count:
        errors.append(f"canonical_identity_change_detected:{canonical_change_count}")
    if session.get("source_projection_sha256") != artifact.get("projection_sha256"):
        errors.append("session_projection_binding_mismatch")
    if session.get("session_batch_count") != expected_deployment_count:
        errors.append("session_batch_count_invalid")
    if session_safe.get("session_batch_count") != expected_deployment_count:
        errors.append("session_safe_batch_count_invalid")
    if any(
        value.get("claim_boundaries", {}).get("a2_unlocked") is not False
        for value in (artifact, safe)
    ) or session.get("a2_unlocked") is not False or session_safe.get("a2_unlocked") is not False:
        errors.append("a2_lock_broken")

    if database_path is not None:
        _validate_runtime_database(database_path, artifact, errors)

    return {
        "validation_status": PASS_STATUS if not errors else "FAIL_R7_READING_RUNTIME_PROJECTION_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
        "deployment_count": len(deliveries),
        "source_dependency_projection_count": projected_count,
        "learner_renderable_count": learner_renderable_count,
        "canonical_identity_change_count": canonical_change_count,
        "database_validated": database_path is not None,
        "a2_unlocked": False,
        "synthetic_evidence_count": 0,
        "next_short_step": projection.NEXT_SHORT_STEP if not errors else TASK_ID,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r4-bank", type=Path, required=True)
    parser.add_argument("--deployment-queue", type=Path, required=True)
    parser.add_argument("--m2-consumer", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--expected-deployment-count", type=int, default=209)
    parser.add_argument("--expected-projected-count", type=int, default=198)
    args = parser.parse_args(argv)
    result = validate(
        bank_path=args.r4_bank,
        deployment_queue_path=args.deployment_queue,
        consumer_path=args.m2_consumer,
        output_root=args.output_root,
        database_path=args.database,
        expected_deployment_count=args.expected_deployment_count,
        expected_projected_count=args.expected_projected_count,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
