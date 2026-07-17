#!/usr/bin/env python3
"""Bridge resolved M12E1 evidence into the canonical A1FS M3/M6/M7 chain.

The bridge never guesses an item mapping. Every imported M12 item must map
one-to-one to an A1/A1+ M2 asset through explicit ``m12_item_id`` and the exact
``m12_session_bank_sha256``. Import is performed against a temporary SQLite
copy and atomically committed only after M3 events, M6 outcomes, the M7
snapshot, and independent M7 validation all succeed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3  # noqa: E402
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6  # noqa: E402
from ulga.builders import build_a1fs_v1_m7_mastery_error_remediation_reassessment as m7  # noqa: E402
from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as m08  # noqa: E402
from ulga.validators import validate_a1fs_v1_m7_mastery_error_remediation_reassessment as m7_validator  # noqa: E402

TASK_ID = "E4S-A1V1-M12F_M12E1ResolvedEvidenceToA1FSRemediationBridge"
SCHEMA_VERSION = "e4s.a1v1.m12f.m12e1_to_a1fs_remediation_bridge.v1"
INSPECT_READY = "PASS_M12F_BRIDGE_MAPPING_READY"
INSPECT_BLOCKED = "BLOCKED_M12F_MAPPING_AUTHORITY_REQUIRED"
IMPORT_STATUS = "PASS_M12F_RESOLVED_EVIDENCE_IMPORTED_TO_A1FS_M7"
REPLAY_STATUS = "PASS_M12F_BRIDGE_ALREADY_IMPORTED"
NEXT_SHORT_STEP = "E4S-A1V1-M12G_RemediationReassessmentExecution"
M12E1_TASK_ID = "E4S-A1V1-M12E1_HumanReviewDecisionMaterialization"
M12E1_STATUS = "PASS_M12E1_HUMAN_REVIEW_DECISIONS_MATERIALIZED"
CONSUMER_STATUS = m6.CONSUMER_STATUS
GRAPH_STATUS = m7.GRAPH_STATUS
SCHEMA_PATH = REPO_ROOT / "ulga/schemas/e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge.schema.json"
PASS_OUTCOMES = {"AUTO_PASS", "HUMAN_APPROVE"}
FAIL_OUTCOMES = {"AUTO_FAIL", "HUMAN_REJECT"}
RESOLVED_OUTCOMES = PASS_OUTCOMES | FAIL_OUTCOMES
EXPECTED_ATTEMPTS = 9


class BridgeError(ValueError):
    """Fail-closed bridge error."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BridgeError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise BridgeError(f"{code}_not_object")
    return value


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    if private:
        os.chmod(path, 0o600)


def _safe_root(path: Path) -> Path:
    resolved = path.resolve()
    approved = (REPO_ROOT / ".local").resolve()
    if not resolved.is_relative_to(approved):
        raise BridgeError(f"path_outside_local:{resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _require(actual: Any, expected: Any, code: str) -> None:
    if actual != expected:
        raise BridgeError(f"{code}:expected={expected!r}:actual={actual!r}")


def _schema_validate(report: Mapping[str, Any]) -> None:
    schema = read_json(SCHEMA_PATH, "bridge_schema")
    errors = sorted(Draft202012Validator(schema).iter_errors(report), key=lambda error: list(error.absolute_path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise BridgeError(f"schema_validation_failed:{location}:{first.message}")


def _safe_scan(value: Any) -> None:
    forbidden = {
        "response", "learner_response", "learner_ref", "display_label", "session_id",
        "reviewer_id", "reviewed_at", "notes", "prompt", "context", "accepted_texts",
        "accepted_sequence", "private_scoring_contract", "answer", "answer_key",
    }

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in forbidden or str(key).casefold().endswith("_absolute_path"):
                    raise BridgeError(f"private_field_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            if Path(node).is_absolute() or (len(node) > 2 and node[1:3] in {":\\", ":/"}):
                raise BridgeError("absolute_path_leak")

    walk(value)


def _load_sources(
    *,
    source_bank_path: Path,
    resolved_root: Path,
    m12e1_root: Path,
    consumer_path: Path,
    graph_path: Path,
) -> dict[str, Any]:
    bank = read_json(source_bank_path, "source_bank")
    registry = read_json(resolved_root / "cumulative_attempt_registry.private.json", "resolved_registry")
    ledger = read_json(resolved_root / "cumulative_progress_ledger.private.json", "resolved_ledger")
    query = read_json(resolved_root / "cumulative_progress_query_index.json", "resolved_query")
    m12e1_report = read_json(m12e1_root / "human_review_materialization_safe_report.json", "m12e1_report")
    consumer = read_json(consumer_path, "consumer")
    graph = read_json(graph_path, "graph")

    bank_hash = m08.sha256_value(bank)
    _require(registry.get("task_id"), m08.TASK_ID, "registry_task")
    _require(registry.get("schema_version"), m08.ATTEMPT_SCHEMA_VERSION, "registry_schema")
    _require(registry.get("session_bank_sha256"), bank_hash, "registry_bank_hash")
    _require(ledger.get("task_id"), m08.TASK_ID, "ledger_task")
    _require(ledger.get("session_bank_sha256"), bank_hash, "ledger_bank_hash")
    _require(ledger.get("attempt_registry_sha256"), m08.sha256_value(registry), "ledger_registry_hash")
    _require(query.get("attempt_count"), ledger.get("attempt_count"), "query_ledger_count")
    _require(m12e1_report.get("task_id"), M12E1_TASK_ID, "m12e1_task")
    _require(m12e1_report.get("validation_status"), M12E1_STATUS, "m12e1_status")
    _require(m12e1_report.get("remaining_pending_count"), 0, "m12e1_pending")
    _require(m12e1_report.get("stop_reason"), "NONE", "m12e1_stop_reason")
    _require(consumer.get("validation_status"), CONSUMER_STATUS, "consumer_status")
    _require(graph.get("validation_status"), GRAPH_STATUS, "graph_status")
    _require(consumer.get("source_graph_sha256"), file_sha(graph_path), "consumer_graph_hash")

    attempts = registry.get("attempts")
    entries = ledger.get("entries")
    if not isinstance(attempts, list) or not isinstance(entries, list):
        raise BridgeError("resolved_evidence_arrays_invalid")
    _require(len(attempts), EXPECTED_ATTEMPTS, "resolved_attempt_count")
    _require(len(entries), EXPECTED_ATTEMPTS, "resolved_ledger_count")
    if len({str(row.get("item_id")) for row in attempts}) != EXPECTED_ATTEMPTS:
        raise BridgeError("resolved_attempt_identity_invalid")
    entries_by_id = {str(row["item_id"]): row for row in entries}
    if set(entries_by_id) != {str(row["item_id"]) for row in attempts}:
        raise BridgeError("registry_ledger_item_partition_drift")
    if any(str(row.get("outcome")) not in RESOLVED_OUTCOMES for row in entries):
        raise BridgeError("unresolved_outcome_present")
    counts = Counter(str(row["outcome"]) for row in entries)
    if counts["AUTO_FAIL"] < 1 or counts["HUMAN_REJECT"] < 1:
        raise BridgeError("remediation_source_failure_missing")

    bank_by_id = {str(row["item_id"]): row for row in bank.get("items", [])}
    missing_bank = sorted(set(entries_by_id) - set(bank_by_id))
    if missing_bank:
        raise BridgeError(f"source_bank_items_missing:{missing_bank}")
    return {
        "bank": bank,
        "bank_hash": bank_hash,
        "registry": registry,
        "ledger": ledger,
        "query": query,
        "m12e1_report": m12e1_report,
        "consumer": consumer,
        "graph": graph,
        "attempts": attempts,
        "entries_by_id": entries_by_id,
        "bank_by_id": bank_by_id,
    }


def _contract_drift(asset: Mapping[str, Any], source_item: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        derived = m6.derive_contract(asset)
    except Exception as exc:
        return [f"derive_contract_failed:{exc}"]
    source = source_item.get("private_scoring_contract")
    if not isinstance(source, Mapping):
        return ["source_scoring_contract_missing"]
    for key in ("scoring_mode", "response_type"):
        if derived.get(key) != source.get(key):
            errors.append(f"{key}_drift")
    mode = source.get("scoring_mode")
    if mode in {"EXACT_OPTION", "NORMALIZED_TEXT"}:
        if sorted(derived.get("accepted_texts", [])) != sorted(source.get("accepted_texts", [])):
            errors.append("accepted_texts_drift")
    elif mode == "EXACT_SEQUENCE":
        if list(derived.get("accepted_sequence", [])) != list(source.get("accepted_sequence", [])):
            errors.append("accepted_sequence_drift")
    elif mode == "FEATURE_RUBRIC":
        if canonical_sha(derived.get("rubric", {})) != canonical_sha(source.get("rubric", {})):
            errors.append("rubric_drift")
    if not derived.get("capture_enabled"):
        errors.append("capture_disabled")
    return errors


def _mapping(source: Mapping[str, Any]) -> dict[str, Any]:
    item_ids = sorted(source["entries_by_id"])
    assets = source["consumer"].get("asset_records", [])
    graph = source["graph"]
    required = set(graph.get("a2_lock_contract", {}).get("required_mastery_node_ids", []))
    covered_assets: dict[str, set[str]] = defaultdict(set)
    for row in graph.get("coverage", []):
        if row.get("node_id") in required:
            for asset_id in row.get("asset_body_ids", []):
                covered_assets[str(asset_id)].add(str(row["node_id"]))

    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    wrong_hash: dict[str, list[str]] = defaultdict(list)
    for asset in assets:
        payload = asset.get("payload")
        if not isinstance(payload, Mapping):
            continue
        item_id = payload.get("m12_item_id")
        if not isinstance(item_id, str) or item_id not in source["entries_by_id"]:
            continue
        legacy_hash = payload.get("m12_session_bank_sha256")
        if legacy_hash != source["bank_hash"]:
            wrong_hash[item_id].append(str(asset.get("asset_key")))
            continue
        candidates[item_id].append(asset)

    mapped: list[dict[str, Any]] = []
    unmapped: list[str] = []
    duplicates: list[str] = []
    contract_drift: list[str] = []
    coverage_missing: list[str] = []
    a2_items: list[str] = []
    for item_id in item_ids:
        rows = candidates.get(item_id, [])
        if not rows:
            unmapped.append(item_id)
            continue
        if len(rows) != 1:
            duplicates.append(item_id)
            continue
        asset = rows[0]
        if asset.get("level") not in {"A1", "A1+"}:
            a2_items.append(item_id)
            continue
        drift = _contract_drift(asset, source["bank_by_id"][item_id])
        if drift:
            contract_drift.append(f"{item_id}:{','.join(drift)}")
            continue
        nodes = sorted(covered_assets.get(str(asset.get("asset_id")), set()))
        if not nodes:
            coverage_missing.append(item_id)
            continue
        mapped.append({
            "item_id": item_id,
            "asset_key": str(asset["asset_key"]),
            "asset_id": str(asset["asset_id"]),
            "lesson_id": str(asset["lesson_id"]),
            "skill": str(asset["skill"]),
            "level": str(asset["level"]),
            "role": str(asset["role"]),
            "required_node_ids": nodes,
        })
    issues = {
        "unmapped_item_ids": unmapped,
        "duplicate_item_ids": duplicates,
        "wrong_bank_hash_item_ids": sorted(wrong_hash),
        "contract_drift_items": contract_drift,
        "coverage_missing_item_ids": coverage_missing,
        "a2_item_ids": a2_items,
    }
    ready = len(mapped) == EXPECTED_ATTEMPTS and not any(issues.values())
    return {"ready": ready, "mapped": mapped, "issues": issues}


def _base_report(source: Mapping[str, Any], mapping: Mapping[str, Any], *, mode: str) -> dict[str, Any]:
    counts = Counter(str(row["outcome"]) for row in source["ledger"]["entries"])
    report = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": mode,
        "source_attempt_count": EXPECTED_ATTEMPTS,
        "source_outcome_counts": {name: counts[name] for name in m08.OUTCOMES},
        "mapping": {
            "required_count": EXPECTED_ATTEMPTS,
            "mapped_count": len(mapping["mapped"]),
            "mapped_item_ids": [row["item_id"] for row in mapping["mapped"]],
            **mapping["issues"],
        },
        "import_result": None,
        "claim_boundaries": {
            "private_responses_included": False,
            "learner_identity_included": False,
            "canonical_authority_write": False,
            "canonical_egp_mapping_changed": False,
            "duplicate_remediation_engine_created": False,
            "a2_content_promoted": False,
            "a2_payload_access_granted": False,
            "public_delivery": False,
            "audio_or_recording_processed": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
        },
        "validation_status": INSPECT_READY if mapping["ready"] else INSPECT_BLOCKED,
        "stop_reason": "NONE" if mapping["ready"] else "MAPPING_AUTHORITY_REQUIRED",
        "next_short_step": TASK_ID,
        "errors": [],
    }
    return report


def inspect_bridge(**kwargs: Any) -> dict[str, Any]:
    output_root = _safe_root(Path(kwargs.pop("output_root")))
    source = _load_sources(**kwargs)
    mapping = _mapping(source)
    report = _base_report(source, mapping, mode="INSPECT")
    _safe_scan(report)
    _schema_validate(report)
    write_json(output_root / "m12f_bridge_mapping_safe_report.json", report)
    return {"source": source, "mapping": mapping, "safe_report": report}


def _bundle(consumer: Mapping[str, Any], consumer_path: Path, lesson_id: str, output_path: Path) -> Path:
    lesson = next((row for row in consumer["lesson_catalog"] if row["lesson_id"] == lesson_id), None)
    if not lesson or lesson.get("level") not in {"A1", "A1+"}:
        raise BridgeError(f"lesson_not_importable:{lesson_id}")
    assets = [row for row in consumer["asset_records"] if row["lesson_id"] == lesson_id]
    bundle = {
        "task_id": "A1FS-V1-M5_FourSkillRendererAndLearnerUI",
        "schema_version": "a1fs.v1.m5.four_skill_learner_ui.v1",
        "validation_status": m6.M5_STATUS,
        "source_consumer_sha256": file_sha(consumer_path),
        "source_plan_sha256": "0" * 64,
        "lesson": {key: lesson[key] for key in ("lesson_id", "lesson_node_id", "skill", "level", "roles", "requirement_node_ids")},
        "assets": [{"asset_key": row["asset_key"]} for row in assets],
        "subtitle_contract": {"mode": "BRIDGE_NOT_RENDERED", "timing_status": "NOT_APPLICABLE", "timed_cues": [], "actual_srt_loaded": False, "audio_synchronized": False},
        "boundary_notice": "Private evidence bridge bundle; learner rendering is not performed.",
        "capabilities": {"response_capture_enabled": False, "scoring_enabled": False, "a2_content_included": False},
        "next_short_step": m6.TASK_ID,
    }
    write_json(output_path, bundle)
    return output_path


def _profile_exists(database: Path, learner_id: str) -> bool:
    with sqlite3.connect(database) as connection:
        return bool(connection.execute("SELECT 1 FROM learner_profiles WHERE learner_id=?", (learner_id,)).fetchone())


def _receipt(connection: sqlite3.Connection, registry_hash: str) -> sqlite3.Row | None:
    connection.row_factory = sqlite3.Row
    connection.execute("""CREATE TABLE IF NOT EXISTS m12f_bridge_receipts(
        source_registry_sha256 TEXT PRIMARY KEY,
        learner_id TEXT NOT NULL,
        report_json TEXT NOT NULL,
        report_sha256 TEXT NOT NULL,
        imported_at TEXT NOT NULL
    )""")
    return connection.execute("SELECT * FROM m12f_bridge_receipts WHERE source_registry_sha256=?", (registry_hash,)).fetchone()


def import_resolved(
    *,
    source_bank_path: Path,
    resolved_root: Path,
    m12e1_root: Path,
    consumer_path: Path,
    graph_path: Path,
    database_path: Path,
    learner_id: str,
    display_label: str,
    output_root: Path,
) -> dict[str, Any]:
    output_root = _safe_root(output_root)
    inspected = inspect_bridge(
        source_bank_path=source_bank_path,
        resolved_root=resolved_root,
        m12e1_root=m12e1_root,
        consumer_path=consumer_path,
        graph_path=graph_path,
        output_root=output_root,
    )
    source, mapping = inspected["source"], inspected["mapping"]
    if not mapping["ready"]:
        raise BridgeError("MAPPING_AUTHORITY_REQUIRED")
    registry_hash = m08.sha256_value(source["registry"])
    target_db = Path(database_path).resolve()
    if not target_db.is_relative_to((REPO_ROOT / ".local").resolve()):
        raise BridgeError("database_outside_local")
    target_db.parent.mkdir(parents=True, exist_ok=True)

    if target_db.is_file():
        with sqlite3.connect(target_db) as existing:
            existing.row_factory = sqlite3.Row
            if existing.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='m12f_bridge_receipts'").fetchone():
                row = existing.execute("SELECT * FROM m12f_bridge_receipts WHERE source_registry_sha256=?", (registry_hash,)).fetchone()
                if row:
                    report = json.loads(row["report_json"])
                    report["validation_status"] = REPLAY_STATUS
                    _schema_validate(report)
                    write_json(output_root / "m12f_bridge_import_safe_report.json", report)
                    return {"safe_report": report, "replayed": True}

    temp_dir = Path(tempfile.mkdtemp(prefix="m12f-bridge-", dir=str(target_db.parent)))
    temp_db = temp_dir / target_db.name
    snapshot_root = temp_dir / "m7"
    try:
        if target_db.is_file():
            shutil.copy2(target_db, temp_db)
        state = m3.LearnerStateStore(temp_db)
        state.initialize(consumer_path)
        if not _profile_exists(temp_db, learner_id):
            state.create_profile(learner_id=learner_id, display_label=display_label)
        else:
            profile = state.profile_snapshot(learner_id)["profile"]
            if profile["profile_state"] != "ACTIVE":
                raise BridgeError("learner_profile_not_active")

        mapping_by_id = {row["item_id"]: row for row in mapping["mapped"]}
        attempts_by_id = {str(row["item_id"]): row for row in source["attempts"]}
        grouped: dict[str, list[str]] = defaultdict(list)
        for item_id, row in mapping_by_id.items():
            grouped[row["lesson_id"]].append(item_id)
        consumer = source["consumer"]
        response_store = m6.ResponseEvidenceStore(temp_db)
        imported_outcomes: dict[str, str] = {}
        imported_attempt_ids: list[str] = []
        for lesson_id in sorted(grouped):
            bundle_path = _bundle(consumer, consumer_path, lesson_id, temp_dir / "bundles" / f"{canonical_sha(lesson_id)[:16]}.private.json")
            response_store.initialize(consumer_path=consumer_path, lesson_bundle_path=bundle_path)
            session_id = f"M12F:{canonical_sha([registry_hash, lesson_id])[:24]}"
            item_ids = sorted(grouped[lesson_id], key=lambda item_id: (attempts_by_id[item_id]["submitted_at"], item_id))
            first_at = attempts_by_id[item_ids[0]]["submitted_at"]
            session = state.start_session(learner_id=learner_id, lesson_id=lesson_id, session_id=session_id, at=first_at)
            version = int(session["session_version"])
            for item_id in item_ids:
                mapped = mapping_by_id[item_id]
                attempt = attempts_by_id[item_id]
                source_entry = source["entries_by_id"][item_id]
                session = state.record_exposure(session_id=session_id, asset_key=mapped["asset_key"], expected_session_version=version, at=attempt["submitted_at"])
                version = int(session["session_version"])
                attempt_id = f"M12F_ATT:{canonical_sha([registry_hash, item_id])[:24]}"
                captured = response_store.capture_response(
                    learner_id=learner_id,
                    session_id=session_id,
                    asset_key=mapped["asset_key"],
                    response=deepcopy(attempt["response"]),
                    expected_session_version=version,
                    attempt_id=attempt_id,
                    submitted_at=attempt["submitted_at"],
                )
                version += 1
                final_outcome = captured["outcome"]
                review = attempt["operator_review"]
                if source_entry["scoring_mode"] == "FEATURE_RUBRIC":
                    decision = str(review["decision"])
                    if decision not in {"APPROVE", "REJECT"}:
                        raise BridgeError(f"resolved_review_decision_invalid:{item_id}:{decision}")
                    reviewed = response_store.review_response(
                        attempt_id=attempt_id,
                        decision=decision,
                        reviewer_id=str(review["reviewer_id"]),
                        criteria=review["criteria"],
                        notes=review.get("notes"),
                        reviewed_at=review["reviewed_at"],
                    )
                    final_outcome = reviewed["outcome"]
                if final_outcome != source_entry["outcome"]:
                    raise BridgeError(f"outcome_rebuild_drift:{item_id}:{final_outcome}:{source_entry['outcome']}")
                imported_outcomes[item_id] = final_outcome
                imported_attempt_ids.append(attempt_id)
            state.end_session(session_id=session_id, outcome="COMPLETED", expected_session_version=version, at=attempts_by_id[item_ids[-1]]["submitted_at"])

        engine = m7.MasteryRemediationEngine(database_path=temp_db, graph_path=graph_path)
        engine.initialize()
        m7_result = engine.build_snapshot(learner_id=learner_id, output_root=snapshot_root)
        snapshot_path = snapshot_root / "a1fs_v1_m7_mastery_snapshot.private.json"
        m7_validation = m7_validator.validate(temp_db, graph_path, snapshot_path)
        if m7_validation["error_count"]:
            raise BridgeError(f"m7_validation_failed:{m7_validation['errors']}")
        snapshot = read_json(snapshot_path, "m7_snapshot")
        imported_counts = Counter(imported_outcomes.values())
        source_counts = Counter(str(row["outcome"]) for row in source["ledger"]["entries"])
        if imported_counts != source_counts:
            raise BridgeError("imported_outcome_partition_drift")
        open_remediation = sum(row["assignment_state"] == "OPEN" for row in snapshot["remediation_assignments"])
        pending_reassessment = sum(row["queue_state"] == "PENDING" for row in snapshot["reassessment_queue"])
        if open_remediation < 1 or pending_reassessment < 1:
            raise BridgeError("remediation_not_generated")

        report = _base_report(source, mapping, mode="IMPORT")
        report["import_result"] = {
            "imported_attempt_count": len(imported_attempt_ids),
            "imported_outcome_counts": {name: imported_counts[name] for name in m08.OUTCOMES},
            "completed_session_count": len(grouped),
            "m7_error_diagnosis_count": len(snapshot["error_diagnoses"]),
            "open_remediation_count": open_remediation,
            "pending_reassessment_count": pending_reassessment,
            "mastered_required_count": snapshot["mastered_required_count"],
            "required_mastery_node_count": snapshot["required_mastery_node_count"],
            "a2_lock_state": snapshot["a2_lock_state"],
            "m7_validation_error_count": 0,
        }
        report["validation_status"] = IMPORT_STATUS
        report["stop_reason"] = "NONE"
        report["next_short_step"] = NEXT_SHORT_STEP
        _safe_scan(report)
        _schema_validate(report)

        receipt_connection = sqlite3.connect(temp_db)
        try:
            _receipt(receipt_connection, registry_hash)
            now = m6.utc()
            receipt_connection.execute(
                "INSERT INTO m12f_bridge_receipts VALUES(?,?,?,?,?)",
                (registry_hash, learner_id, json.dumps(report, ensure_ascii=False, sort_keys=True), canonical_sha(report), now),
            )
            if receipt_connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise BridgeError("sqlite_integrity_failed")
            if receipt_connection.execute("PRAGMA foreign_key_check").fetchall():
                raise BridgeError("sqlite_foreign_key_failed")
            receipt_connection.commit()
        finally:
            receipt_connection.close()
        os.chmod(temp_db, 0o600)
        os.replace(temp_db, target_db)
        final_snapshot_root = output_root / "m7"
        final_snapshot_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(snapshot_path, final_snapshot_root / snapshot_path.name)
        write_json(output_root / "m12f_bridge_import_safe_report.json", report)
        return {"safe_report": report, "m7_snapshot": snapshot, "m7_validation": m7_validation, "replayed": False}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("inspect", "import-resolved"):
        current = sub.add_parser(command)
        current.add_argument("--source-bank", type=Path, required=True)
        current.add_argument("--resolved-root", type=Path, required=True)
        current.add_argument("--m12e1-root", type=Path, required=True)
        current.add_argument("--consumer", type=Path, required=True)
        current.add_argument("--graph", type=Path, required=True)
        current.add_argument("--output-root", type=Path, required=True)
        if command == "import-resolved":
            current.add_argument("--database", type=Path, required=True)
            current.add_argument("--learner-id", required=True)
            current.add_argument("--display-label", default="M12F Imported Learner")
    args = parser.parse_args(argv)
    common = {
        "source_bank_path": args.source_bank,
        "resolved_root": args.resolved_root,
        "m12e1_root": args.m12e1_root,
        "consumer_path": args.consumer,
        "graph_path": args.graph,
        "output_root": args.output_root,
    }
    try:
        if args.command == "inspect":
            result = inspect_bridge(**common)
        else:
            result = import_resolved(**common, database_path=args.database, learner_id=args.learner_id, display_label=args.display_label)
        report = result["safe_report"]
        print(json.dumps({
            "mode": report["mode"],
            "validation_status": report["validation_status"],
            "mapped_count": report["mapping"]["mapped_count"],
            "source_outcome_counts": report["source_outcome_counts"],
            "import_result": report["import_result"],
            "stop_reason": report["stop_reason"],
            "next_short_step": report["next_short_step"],
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except (BridgeError, m3.StateStoreError, m6.ResponseEvidenceError, m7.MasteryError, m08.TextModeSessionError, OSError, sqlite3.Error, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
