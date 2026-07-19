#!/usr/bin/env python3
"""Recover an unanswerable R5 session without rewriting learner evidence.

The recovery uses the existing R1/R5 validity ledger and R5 session state
machine. It backs up the database, proves that the active or paused session
contains at least one learner-unanswerable item, invalidates any captured
attempts as content errors, abandons the session, and performs an explicitly
authorized PracticeBank rebind. It does not generate questions, change
canonical authority, write mastery, unlock A2, or claim real learner success.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_r1_evidence_validity_system_error_governance as r1
from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5
from ulga.builders import build_a1fs_v1_r5_production_bootstrap_first_session as bootstrap
from ulga.validators.validate_a1fs_v1_learner_answerability_gate import validate_bank

TASK_ID = "A1FS-V1-R5_ContentErrorSessionRecovery"
SCHEMA_VERSION = "a1fs.v1.r5.content_error_session_recovery.v1"
STATUS = "PASS_A1FS_V1_R5_CONTENT_ERROR_SESSION_RECOVERY"
NEXT_SHORT_STEP = "A1FS-V1-R5_ProductionBootstrapAndFirstLearnerSession"
PRIVATE_RECEIPT = "a1fs_v1_r5_content_error_recovery.private.json"
SAFE_REPORT = "a1fs_v1_r5_content_error_recovery.safe.json"
DEFAULT_REASON_CODE = "REQUIRED_STIMULUS_NOT_RENDERED"


class ContentErrorRecoveryError(ValueError):
    """Fail-closed content-error recovery error."""


def _read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContentErrorRecoveryError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise ContentErrorRecoveryError(f"{code}_not_object")
    return value


def _write_private(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _load_bootstrap_receipt(path: Path) -> dict[str, Any]:
    value = _read_json(path, "bootstrap_receipt")
    if (
        value.get("task_id") != bootstrap.TASK_ID
        or value.get("schema_version") != bootstrap.SCHEMA_VERSION
        or value.get("validation_status") != bootstrap.STATUS
        or value.get("private_local_only") is not True
    ):
        raise ContentErrorRecoveryError("bootstrap_receipt_identity_invalid")
    core = {key: child for key, child in value.items() if key != "receipt_sha256"}
    if value.get("receipt_sha256") != bootstrap.digest(core):
        raise ContentErrorRecoveryError("bootstrap_receipt_digest_invalid")
    if not value.get("session_id") or not value.get("access_token") or not value.get("learner_id"):
        raise ContentErrorRecoveryError("bootstrap_receipt_session_binding_missing")
    return value


def _session_snapshot(runtime: r5.LocalEdgeRuntime, receipt: Mapping[str, Any]) -> dict[str, Any]:
    session_id = str(receipt["session_id"])
    access_token = str(receipt["access_token"])
    defects: list[dict[str, str]] = []
    with runtime.connect() as connection:
        session = runtime._session(connection, session_id)
        runtime._auth(session, access_token)
        if session["learner_id"] != receipt["learner_id"]:
            raise ContentErrorRecoveryError("receipt_learner_session_mismatch")
        if session["session_state"] not in {"ACTIVE", "PAUSED"}:
            raise ContentErrorRecoveryError(f"session_not_recoverable:{session['session_state']}")
        rows = connection.execute(
            """SELECT a.item_id,i.item_json FROM edge_assignments a
            JOIN edge_runtime_items i USING(item_id)
            WHERE a.session_id=? ORDER BY a.assignment_sequence""",
            (session_id,),
        ).fetchall()
        for row in rows:
            item = json.loads(row["item_json"])
            try:
                r5._safe_item(item)
            except r5.LocalEdgeRuntimeError as exc:
                if "SESSION_ITEM_NOT_ANSWERABLE" not in str(exc):
                    raise
                defects.append({"item_id": row["item_id"], "error": str(exc)})
        attempts = connection.execute(
            "SELECT attempt_id,validity_status FROM edge_attempts WHERE session_id=? ORDER BY submitted_at,attempt_id",
            (session_id,),
        ).fetchall()
        return {
            "session_id": session_id,
            "learner_id": session["learner_id"],
            "session_state": session["session_state"],
            "session_version": int(session["session_version"]),
            "defects": defects,
            "attempts": [dict(row) for row in attempts],
        }


def recover(
    *, database_path: Path, bootstrap_receipt_path: Path, bank_path: Path,
    supply_report_path: Path, output_root: Path, actor_id: str,
    reason_code: str = DEFAULT_REASON_CODE, occurred_at: str | None = None,
) -> dict[str, Any]:
    database_path = Path(database_path).resolve()
    output_root = Path(output_root).resolve()
    actor_id = str(actor_id).strip()
    reason_code = str(reason_code).strip()
    if not actor_id:
        raise ContentErrorRecoveryError("actor_id_required")
    if not reason_code:
        raise ContentErrorRecoveryError("reason_code_required")
    if not database_path.is_file():
        raise ContentErrorRecoveryError("database_missing")
    output_root.mkdir(parents=True, exist_ok=True)

    receipt = _load_bootstrap_receipt(bootstrap_receipt_path)
    answerability = validate_bank(bank_path)
    if answerability.get("error_count") != 0:
        raise ContentErrorRecoveryError(
            "replacement_bank_answerability_failed:" + "|".join(answerability.get("errors", []))
        )

    runtime = r5.LocalEdgeRuntime(database_path)
    snapshot = _session_snapshot(runtime, receipt)
    if not snapshot["defects"]:
        raise ContentErrorRecoveryError("session_has_no_proven_answerability_defect")

    backup_path = output_root / "a1fs_v1_r5_pre_content_error_recovery.sqlite3"
    manifest_path = output_root / "a1fs_v1_r5_pre_content_error_recovery.manifest.private.json"
    backup = runtime.backup(
        backup_path=backup_path,
        manifest_path=manifest_path,
        created_at=occurred_at,
    )
    invalidated: list[str] = []
    skipped_terminal: list[str] = []
    try:
        for attempt in snapshot["attempts"]:
            attempt_id = str(attempt["attempt_id"])
            if attempt["validity_status"] in r1.TERMINAL_STATUSES:
                skipped_terminal.append(attempt_id)
                continue
            runtime.set_attempt_validity(
                attempt_id=attempt_id,
                new_status="INVALIDATED_CONTENT_ERROR",
                reason_code=reason_code,
                actor_id=actor_id,
                detail={
                    "session_id": snapshot["session_id"],
                    "defect_count": len(snapshot["defects"]),
                    "defect_codes": sorted({row["error"].split(":", 1)[0] for row in snapshot["defects"]}),
                },
                occurred_at=occurred_at,
            )
            invalidated.append(attempt_id)

        abandoned = runtime.abandon_session(
            session_id=snapshot["session_id"],
            access_token=str(receipt["access_token"]),
            expected_session_version=snapshot["session_version"],
            at=occurred_at,
        )
        init_result = runtime.initialize(
            bank_path=bank_path,
            supply_report_path=supply_report_path,
            allow_bank_rebind=True,
        )
    except Exception:
        r5.LocalEdgeRuntime.restore(
            backup_path=backup_path,
            manifest_path=manifest_path,
            target_path=database_path,
        )
        raise

    private_core = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": STATUS,
        "private_local_only": True,
        "session_id": snapshot["session_id"],
        "learner_id": snapshot["learner_id"],
        "previous_session_state": snapshot["session_state"],
        "new_session_state": abandoned["session"]["session_state"],
        "defects": snapshot["defects"],
        "invalidated_attempt_ids": invalidated,
        "skipped_terminal_attempt_ids": skipped_terminal,
        "reason_code": reason_code,
        "actor_id": actor_id,
        "backup": backup,
        "replacement_bank_sha256": init_result["source_bank_sha256"],
        "replacement_supply_report_sha256": init_result["source_supply_report_sha256"],
        "claim_boundaries": {
            "raw_attempt_rewritten": False,
            "mastery_written": False,
            "retention_confirmed": False,
            "a2_unlocked": False,
            "replacement_question_generated": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    private = {**private_core, "receipt_sha256": r5.digest(private_core)}
    _write_private(output_root / PRIVATE_RECEIPT, private)

    safe_core = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": STATUS,
        "session_ref_sha256": r5.digest(snapshot["session_id"]),
        "learner_ref_sha256": r5.digest(snapshot["learner_id"]),
        "previous_session_state": snapshot["session_state"],
        "new_session_state": abandoned["session"]["session_state"],
        "defect_count": len(snapshot["defects"]),
        "invalidated_attempt_count": len(invalidated),
        "skipped_terminal_attempt_count": len(skipped_terminal),
        "reason_code": reason_code,
        "replacement_bank_sha256": init_result["source_bank_sha256"],
        "replacement_supply_report_sha256": init_result["source_supply_report_sha256"],
        "private_receipt_sha256": private["receipt_sha256"],
        "claim_boundaries": private_core["claim_boundaries"],
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": r5.digest(safe_core)}
    _write_private(output_root / SAFE_REPORT, safe)
    return safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--bootstrap-receipt", type=Path, required=True)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--actor-id", required=True)
    parser.add_argument("--reason-code", default=DEFAULT_REASON_CODE)
    parser.add_argument("--occurred-at")
    args = parser.parse_args()
    try:
        result = recover(
            database_path=args.database,
            bootstrap_receipt_path=args.bootstrap_receipt,
            bank_path=args.bank,
            supply_report_path=args.report,
            output_root=args.output_root,
            actor_id=args.actor_id,
            reason_code=args.reason_code,
            occurred_at=args.occurred_at,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (
        ContentErrorRecoveryError, r5.LocalEdgeRuntimeError,
        bootstrap.ProductionBootstrapError, OSError, sqlite3.Error,
        KeyError, TypeError, ValueError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
