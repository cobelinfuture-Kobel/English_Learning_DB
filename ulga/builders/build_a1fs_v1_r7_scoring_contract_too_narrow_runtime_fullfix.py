#!/usr/bin/env python3
"""Apply a versioned, future-only R7 scoring-contract remediation."""
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

from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4
from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5
from ulga.builders import build_a1fs_v1_r7_real_evidence_autofail_root_cause_and_representative_acceptance_gate as gate

TASK_ID = "A1FS-V1-R7_ScoringContractTooNarrow4ItemVersionedRuntimeFullFix"
SCHEMA_VERSION = "a1fs.v1.r7.scoring_contract_runtime_fullfix.v1"
STATUS = "PASS_R7_SCORING_CONTRACT_RUNTIME_FULLFIX"
OVERRIDE_VERSION = "A1FS_R7_FEATURE_RUBRIC_V1"
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Changes runtime scoring metadata only; canonical content and R4 candidate identity remain immutable."


class FullFixError(RuntimeError):
    """Fail-closed remediation error."""


def _validate_owned(value: Mapping[str, Any], field: str) -> None:
    gate.validate_owned_digest(value, field)


def _candidate_identity(bank: Mapping[str, Any]) -> dict[str, Any]:
    rows = sorted(
        (str(row.get("item_id") or ""), str(row.get("candidate_sha256") or ""))
        for row in bank.get("items", []) if isinstance(row, Mapping)
    )
    if not rows or any(not item_id or not candidate_sha for item_id, candidate_sha in rows):
        raise FullFixError("r4_candidate_identity_missing")
    return {"candidate_count": len(rows), "candidate_identity_sha256": r5.digest(rows)}


def _effective_contract(base: Mapping[str, Any]) -> dict[str, Any]:
    """Build a response-independent human-review contract from the prior contract only."""
    contract = {
        key: value for key, value in dict(base).items()
        if key not in {"accepted_texts", "accepted_sequence", "rubric", "scoring_mode", "human_review_fallback"}
    }
    contract.update({
        "response_type": "string",
        "scoring_mode": "FEATURE_RUBRIC",
        "human_review_fallback": True,
        "rubric": {
            "review_mode": "HUMAN_REQUIRED",
            "criteria": [
                {"criterion_id": "MAIN_MESSAGE_SUPPORTED_BY_RENDERED_SOURCE", "required": True},
                {"criterion_id": "CITED_WORDS_PRESENT_IN_RENDERED_SOURCE", "required": True},
                {"criterion_id": "BOTH_INSTRUCTION_PARTS_ADDRESSED", "required": True},
            ],
        },
    })
    return contract


def _history_digest(connection: sqlite3.Connection) -> str:
    rows = []
    for table, order in (
        ("edge_attempts", "attempt_id"),
        ("edge_scoring_results", "attempt_id"),
        ("edge_review_queue", "attempt_id"),
        ("edge_runtime_events", "event_seq"),
    ):
        columns = [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
        values = [dict(zip(columns, row)) for row in connection.execute(f"SELECT * FROM {table} ORDER BY {order}")]
        rows.append((table, values))
    return r5.digest(rows)


def _validate_inputs(
    *, gate_artifact: Mapping[str, Any], bank: Mapping[str, Any], connection: sqlite3.Connection,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _validate_owned(gate_artifact, "artifact_sha256")
    _validate_owned(bank, "bank_sha256")
    if bank.get("task_id") != r4.TASK_ID or bank.get("validation_status") != r4.STATUS:
        raise FullFixError("r4_bank_identity_invalid")
    if any(str(row.get("level")) not in {"A1", "A1_PLUS"} for row in bank.get("items", [])):
        raise FullFixError("A2_REMEDIATION_LOCKED")
    if gate_artifact.get("counts", {}).get("synthetic_evidence_count") != 0:
        raise FullFixError("synthetic_evidence_forbidden")
    findings = [
        dict(row) for row in gate_artifact.get("autofail_root_causes", [])
        if row.get("root_cause") == "SCORING_CONTRACT_TOO_NARROW"
    ]
    if len(findings) != 4 or len({row.get("item_id") for row in findings}) != 4:
        raise FullFixError("exactly_four_unique_scoring_contract_findings_required")
    metadata = dict(connection.execute("SELECT key,value FROM r5_metadata"))
    if metadata.get("source_bank_sha256") != bank.get("bank_sha256"):
        raise FullFixError("runtime_r4_bank_binding_mismatch")
    bank_items = {str(row.get("item_id")): row for row in bank.get("items", [])}
    for finding in findings:
        item_id = str(finding.get("item_id") or "")
        runtime = connection.execute("SELECT item_json FROM edge_runtime_items WHERE item_id=?", (item_id,)).fetchone()
        if item_id not in bank_items or not runtime:
            raise FullFixError(f"remediation_item_missing:{item_id}")
        runtime_item = json.loads(runtime[0])
        if (
            runtime_item.get("candidate_sha256") != bank_items[item_id].get("candidate_sha256")
            or r5.digest(runtime_item.get("private_scoring_contract") or {})
            != r5.digest(bank_items[item_id].get("private_scoring_contract") or {})
        ):
            raise FullFixError(f"runtime_r4_item_binding_mismatch:{item_id}")
    return sorted(findings, key=lambda row: str(row["item_id"])), _candidate_identity(bank)


def _ensure_backup(
    runtime: r5.LocalEdgeRuntime, *, backup_path: Path, manifest_path: Path, created_at: str,
) -> dict[str, Any]:
    if backup_path.exists() or manifest_path.exists():
        if not (backup_path.exists() and manifest_path.exists()):
            raise FullFixError("partial_backup_state")
        manifest = r5.read_json(manifest_path, "backup_manifest")
        core = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
        if manifest.get("manifest_sha256") != r5.digest(core):
            raise FullFixError("backup_manifest_invalid")
        if manifest.get("backup_sha256") != r5.file_digest(backup_path):
            raise FullFixError("backup_digest_invalid")
        return manifest
    return runtime.backup(backup_path=backup_path, manifest_path=manifest_path, created_at=created_at)


def migrate(
    *, database_path: Path, gate_artifact: Mapping[str, Any], bank: Mapping[str, Any],
    backup_path: Path, backup_manifest_path: Path, applied_at: str,
) -> dict[str, Any]:
    """Back up, snapshot all history, and atomically install four future-only overrides."""
    applied_at = r5.utc(applied_at)
    runtime = r5.LocalEdgeRuntime(database_path)
    with runtime.connect() as check:
        findings, candidate_identity = _validate_inputs(
            gate_artifact=gate_artifact, bank=bank, connection=check,
        )
        history_before = _history_digest(check)
        attempt_binding_count = check.execute("SELECT COUNT(*) FROM edge_scoring_results").fetchone()[0]
    backup = _ensure_backup(
        runtime, backup_path=backup_path, manifest_path=backup_manifest_path, created_at=applied_at,
    )
    plans = []
    with runtime.connect() as connection:
        for finding in findings:
            item = json.loads(connection.execute(
                "SELECT item_json FROM edge_runtime_items WHERE item_id=?", (finding["item_id"],)
            ).fetchone()[0])
            base = dict(item["private_scoring_contract"])
            effective = _effective_contract(base)
            plans.append({
                "attempt_id": finding["attempt_id"], "work_item_id": finding.get("work_item_id"),
                "item_id": finding["item_id"], "root_cause": finding["root_cause"],
                "base_contract_digest": r5.digest(base), "effective_contract_digest": r5.digest(effective),
                "override_version": OVERRIDE_VERSION, "effective_contract": effective,
                "remediation_reason": "FUTURE_ONLY_HUMAN_REVIEW_REQUIRED",
            })
    remediation_core = {
        "task_id": TASK_ID, "schema_version": SCHEMA_VERSION,
        "source_gate_sha256": gate_artifact["artifact_sha256"],
        "source_bank_sha256": bank["bank_sha256"], "candidate_identity": candidate_identity,
        "plans": plans,
    }
    remediation_sha256 = r5.digest(remediation_core)

    connection = runtime.connect()
    try:
        connection.executescript("BEGIN IMMEDIATE;\n" + r5.SCORING_CONTRACT_SQL)
        for row in connection.execute(
            """SELECT s.scoring_contract_digest,s.scored_at,a.item_id,i.item_json
            FROM edge_scoring_results s JOIN edge_attempts a USING(attempt_id)
            JOIN edge_runtime_items i USING(item_id) ORDER BY a.attempt_id"""
        ):
            existing = connection.execute(
                "SELECT 1 FROM edge_scoring_contract_snapshots WHERE scoring_contract_digest=?",
                (row["scoring_contract_digest"],),
            ).fetchone()
            if existing:
                r5.historical_scoring_contract(connection, row["scoring_contract_digest"])
                continue
            base = json.loads(row["item_json"])["private_scoring_contract"]
            if r5.digest(base) != row["scoring_contract_digest"]:
                raise FullFixError(f"historical_contract_unrecoverable:{row['item_id']}")
            r5.store_scoring_contract_snapshot(
                connection, item_id=row["item_id"], contract=base,
                contract_version="HISTORICAL_BASE_V1", created_at=row["scored_at"],
                source_type="HISTORICAL_ATTEMPT_MIGRATION", remediation_sha256=remediation_sha256,
            )
        historical_unique_snapshot_count = connection.execute(
            "SELECT COUNT(*) FROM edge_scoring_contract_snapshots WHERE source_type!='R7_SCORING_CONTRACT_FULLFIX'"
        ).fetchone()[0]
        applied_records = []
        for plan in plans:
            if plan["base_contract_digest"] == plan["effective_contract_digest"]:
                raise FullFixError(f"effective_contract_not_changed:{plan['item_id']}")
            r5.store_scoring_contract_snapshot(
                connection, item_id=plan["item_id"], contract=plan["effective_contract"],
                contract_version=OVERRIDE_VERSION, created_at=applied_at,
                source_type="R7_SCORING_CONTRACT_FULLFIX", remediation_sha256=remediation_sha256,
            )
            existing = connection.execute(
                "SELECT * FROM edge_runtime_scoring_contract_overrides WHERE item_id=?", (plan["item_id"],)
            ).fetchone()
            expected = (
                plan["base_contract_digest"], plan["effective_contract_digest"],
                r5.canonical(plan["effective_contract"]), OVERRIDE_VERSION, "ACTIVE", remediation_sha256,
            )
            if existing:
                actual = (
                    existing["base_contract_digest"], existing["effective_contract_digest"],
                    existing["override_contract_json"], existing["override_version"],
                    existing["status"], existing["remediation_sha256"],
                )
                if actual != expected:
                    raise FullFixError(f"conflicting_scoring_override:{plan['item_id']}")
                record_applied_at = existing["applied_at"]
            else:
                record_applied_at = applied_at
                connection.execute(
                    """INSERT INTO edge_runtime_scoring_contract_overrides
                    (item_id,base_contract_digest,effective_contract_digest,override_contract_json,
                     override_version,status,applied_at,remediation_sha256) VALUES(?,?,?,?,?,?,?,?)""",
                    (plan["item_id"], *expected[:4], expected[4], record_applied_at, expected[5]),
                )
            applied_records.append({**plan, "applied_at": record_applied_at})
        if _history_digest(connection) != history_before:
            raise FullFixError("historical_runtime_rows_changed")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    with runtime.connect() as verification:
        history_after = _history_digest(verification)
        snapshot_count = verification.execute("SELECT COUNT(*) FROM edge_scoring_contract_snapshots").fetchone()[0]
        override_count = verification.execute(
            "SELECT COUNT(*) FROM edge_runtime_scoring_contract_overrides WHERE status='ACTIVE'"
        ).fetchone()[0]
        for plan in plans:
            item = json.loads(verification.execute(
                "SELECT item_json FROM edge_runtime_items WHERE item_id=?", (plan["item_id"],)
            ).fetchone()[0])
            resolved, resolved_digest = r5.effective_scoring_contract(
                verification, item_id=plan["item_id"], item=item,
            )
            if resolved != plan["effective_contract"] or resolved_digest != plan["effective_contract_digest"]:
                raise FullFixError(f"runtime_override_verification_failed:{plan['item_id']}")
    if history_after != history_before:
        raise FullFixError("historical_runtime_rows_changed_after_commit")
    artifact_core = {
        **remediation_core,
        "remediation_sha256": remediation_sha256,
        "applied_records": applied_records,
        "migration": {
            "backup_sha256": backup["backup_sha256"],
            "historical_attempt_binding_count": attempt_binding_count,
            "historical_scoring_snapshot_count": attempt_binding_count,
            "historical_unique_snapshot_row_count": historical_unique_snapshot_count,
            "immutable_snapshot_row_count": snapshot_count,
            "effective_unique_snapshot_row_count": snapshot_count - historical_unique_snapshot_count,
            "active_override_count": override_count,
            "history_before_sha256": history_before, "history_after_sha256": history_after,
            "historical_rows_unchanged": history_before == history_after,
            "r4_bank_unchanged": True, "candidate_identity_unchanged": True,
        },
        "validation_status": STATUS,
    }
    return {**artifact_core, "artifact_sha256": r5.digest(artifact_core)}


def safe_artifact(private: Mapping[str, Any]) -> dict[str, Any]:
    records = [{
        "attempt_id": row["attempt_id"], "work_item_id": row.get("work_item_id"), "item_id": row["item_id"],
        "root_cause": row["root_cause"], "base_contract_digest": row["base_contract_digest"],
        "effective_contract_digest": row["effective_contract_digest"], "override_version": row["override_version"],
        "remediation_reason": row["remediation_reason"],
    } for row in private["applied_records"]]
    core = {
        "task_id": TASK_ID, "schema_version": SCHEMA_VERSION,
        "source_gate_sha256": private["source_gate_sha256"], "source_bank_sha256": private["source_bank_sha256"],
        "candidate_identity": private["candidate_identity"], "remediation_sha256": private["remediation_sha256"],
        "records": records, "counts": {
            "identified": len(records), "remediated": len(records), "unresolved": 0,
            "historical_attempt_bindings": private["migration"]["historical_attempt_binding_count"],
            "historical_scoring_snapshots": private["migration"]["historical_scoring_snapshot_count"],
            "historical_unique_snapshot_rows": private["migration"]["historical_unique_snapshot_row_count"],
            "immutable_snapshot_rows": private["migration"]["immutable_snapshot_row_count"],
        },
        "historical_rows_unchanged": private["migration"]["historical_rows_unchanged"],
        "r4_bank_unchanged": True, "candidate_identity_unchanged": True,
        "validation_status": STATUS,
    }
    return {**core, "report_sha256": r5.digest(core)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--gate-artifact", type=Path, required=True)
    parser.add_argument("--r4-bank", type=Path, required=True)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--backup-manifest", type=Path, required=True)
    parser.add_argument("--applied-at", required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--safe-output", type=Path, required=True)
    args = parser.parse_args(argv)
    artifact = migrate(
        database_path=args.database, gate_artifact=gate.read_json(args.gate_artifact),
        bank=gate.read_json(args.r4_bank), backup_path=args.backup,
        backup_manifest_path=args.backup_manifest, applied_at=args.applied_at,
    )
    r5.write_private(args.private_output, artifact)
    r5.write_private(args.safe_output, safe_artifact(artifact))
    print(json.dumps({"validation_status": STATUS, "artifact_sha256": artifact["artifact_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
