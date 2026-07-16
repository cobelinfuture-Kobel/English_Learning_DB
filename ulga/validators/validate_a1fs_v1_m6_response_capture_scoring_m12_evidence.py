#!/usr/bin/env python3
"""Independent validator for A1FS V1 M6 response/scoring evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

TASK_ID = "A1FS-V1-M6_ResponseCaptureScoringAndM12Evidence"
STATUS = "PASS_A1FS_V1_M6_RESPONSE_CAPTURE_SCORING_M12_EVIDENCE_READY"
NEXT_SHORT_STEP = "A1FS-V1-M7_MasteryErrorDiagnosisRemediationAndReassessment"
TABLES = {"response_contracts", "response_attempts", "scoring_results", "human_review_queue", "evidence_exports"}
OUTCOMES = {"AUTO_PASS", "AUTO_FAIL", "PENDING_HUMAN_REVIEW", "HUMAN_APPROVE", "HUMAN_REJECT", "HUMAN_DEFER"}


def canonical(value: Any) -> str: return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8") if not isinstance(value, str) else value.encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
def normalize(value: str, case: bool = True, punctuation: bool = True) -> str:
    result = re.sub(r"\s+", " ", value.strip())
    if punctuation: result = re.sub(r"[.!?]+$", "", result).strip()
    return result.casefold() if case else result


def expected_score(contract: Mapping[str, Any], response: Any, decision: str) -> tuple[str, float | None]:
    mode = contract["scoring_mode"]
    if mode == "FEATURE_RUBRIC":
        return {"PENDING": ("PENDING_HUMAN_REVIEW", None), "APPROVE": ("HUMAN_APPROVE", 1.0), "REJECT": ("HUMAN_REJECT", 0.0), "DEFER": ("HUMAN_DEFER", None)}[decision]
    if decision != "PENDING": raise ValueError("deterministic_review_override")
    if mode in {"EXACT_OPTION", "NORMALIZED_TEXT"}:
        actual = normalize(response, contract["case_insensitive"], contract["punctuation_tolerance"])
        accepted = {normalize(row, contract["case_insensitive"], contract["punctuation_tolerance"]) for row in contract["accepted_texts"]}
        passed = actual in accepted and bool(actual)
    elif mode == "EXACT_SEQUENCE": passed = [normalize(row) for row in response] == [normalize(row) for row in contract["accepted_sequence"]]
    else: raise ValueError("unsupported_mode")
    return ("AUTO_PASS", 1.0) if passed else ("AUTO_FAIL", 0.0)


def validate(database_path: Path, evidence_registry_path: Path | None = None, m12_registry_path: Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    try:
        connection = sqlite3.connect(database_path); connection.row_factory = sqlite3.Row; connection.execute("PRAGMA foreign_keys=ON")
    except sqlite3.Error as exc:
        return {"validation_status": "FAIL", "error_count": 1, "errors": [f"database_unreadable:{exc}"]}
    with connection:
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        if metadata.get("m6_validation_status") != STATUS: errors.append("m6_metadata_status_invalid")
        if metadata.get("response_capture_enabled") != "true": errors.append("response_capture_not_enabled")
        if metadata.get("scoring_write_enabled") != "true": errors.append("scoring_write_not_enabled")
        if metadata.get("mastery_write_enabled") != "false": errors.append("mastery_write_boundary_broken")
        names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for name in sorted(TABLES - names): errors.append(f"table_missing:{name}")
        if errors and TABLES - names:
            connection.close(); return {"validation_status": "FAIL", "error_count": len(errors), "errors": errors}
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok": errors.append("sqlite_integrity_failed")
        if connection.execute("PRAGMA foreign_key_check").fetchall(): errors.append("foreign_key_check_failed")
        contracts = {row["asset_key"]: row for row in connection.execute("SELECT * FROM response_contracts")}
        for key, row in contracts.items():
            try: value = json.loads(row["contract_json"])
            except json.JSONDecodeError: errors.append(f"contract_json_invalid:{key}"); continue
            if digest(value) != row["contract_digest"]: errors.append(f"contract_digest_mismatch:{key}")
            if value.get("skill") == "LISTENING" and value.get("role") == "AUD" and row["capture_enabled"]: errors.append(f"unfinished_audio_capture_enabled:{key}")
        previous = "0" * 64; attempts = []
        rows = connection.execute("""SELECT a.*,c.contract_json,c.contract_digest,s.scoring_mode,s.outcome,s.score,s.human_review_required,
            q.decision,q.reviewer_id,q.reviewed_at,q.criteria_json,q.notes,ls.level,ls.learner_id AS session_learner,ls.lesson_id AS session_lesson
            FROM response_attempts a JOIN response_contracts c USING(asset_key) JOIN scoring_results s USING(attempt_id)
            JOIN human_review_queue q USING(attempt_id) JOIN learning_sessions ls USING(session_id) ORDER BY a.rowid""").fetchall()
        for row in rows:
            if row["previous_hash"] != previous: errors.append(f"attempt_previous_hash_mismatch:{row['attempt_id']}")
            core = {"attempt_id": row["attempt_id"], "learner_id": row["learner_id"], "session_id": row["session_id"], "lesson_id": row["lesson_id"],
                    "asset_key": row["asset_key"], "attempt_sequence": row["attempt_sequence"], "response": json.loads(row["response_json"]), "submitted_at": row["submitted_at"]}
            calculated = digest(previous + canonical(core))
            if calculated != row["attempt_hash"]: errors.append(f"attempt_hash_mismatch:{row['attempt_id']}")
            previous = row["attempt_hash"]
            if row["level"] not in {"A1", "A1+"}: errors.append(f"a2_attempt_present:{row['attempt_id']}")
            if row["learner_id"] != row["session_learner"] or row["lesson_id"] != row["session_lesson"]: errors.append(f"attempt_session_binding_mismatch:{row['attempt_id']}")
            contract = json.loads(row["contract_json"]); response = json.loads(row["response_json"])
            if row["contract_digest"] != contracts[row["asset_key"]]["contract_digest"]: errors.append(f"score_contract_digest_mismatch:{row['attempt_id']}")
            try: outcome, score = expected_score(contract, response, row["decision"])
            except (ValueError, TypeError, KeyError): errors.append(f"score_rebuild_failed:{row['attempt_id']}"); continue
            if outcome != row["outcome"] or score != row["score"]: errors.append(f"score_mismatch:{row['attempt_id']}")
            if row["outcome"] not in OUTCOMES: errors.append(f"outcome_invalid:{row['attempt_id']}")
            if row["outcome"] == "PENDING_HUMAN_REVIEW" and row["human_review_required"] != 1: errors.append(f"pending_review_flag_invalid:{row['attempt_id']}")
            attempts.append(row)
        if evidence_registry_path:
            try: registry = json.loads(evidence_registry_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc: errors.append(f"registry_unreadable:{exc}")
            else:
                if registry.get("task_id") != TASK_ID or registry.get("validation_status") != STATUS: errors.append("registry_identity_invalid")
                if registry.get("attempt_count") != len(registry.get("entries", [])): errors.append("registry_attempt_count_mismatch")
                if registry.get("entries_sha256") != digest(registry.get("entries", [])): errors.append("registry_entries_digest_mismatch")
                if registry.get("claim_boundaries", {}).get("mastery_written") is not False: errors.append("registry_mastery_boundary_broken")
        if m12_registry_path:
            try: m12 = json.loads(m12_registry_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc: errors.append(f"m12_registry_unreadable:{exc}")
            else:
                required = {"task_id", "schema_version", "private_local_only", "session_bank_sha256", "session_id", "learner_ref", "attempts"}
                if set(m12) != required: errors.append("m12_registry_top_level_shape_invalid")
                if m12.get("task_id") != "E4S-A1V1-M08_TextModeLearnerSessionAndProgressEvidenceIntegration": errors.append("m12_registry_task_invalid")
                if not re.fullmatch(r"[0-9a-f]{64}", str(m12.get("session_bank_sha256", ""))): errors.append("m12_registry_bank_hash_invalid")
                for attempt in m12.get("attempts", []):
                    if set(attempt) != {"item_id", "attempt_sequence", "response", "submitted_at", "operator_review"}: errors.append("m12_attempt_shape_invalid")
    connection.close()
    outcomes = Counter(row["outcome"] for row in rows)
    return {"validation_status": STATUS if not errors else "FAIL_A1FS_V1_M6_VALIDATION", "error_count": len(errors), "errors": errors,
            "contract_count": len(contracts), "attempt_count": len(rows), "outcome_counts": dict(outcomes),
            "claim_boundaries": {"mastery_written": False, "retention_confirmed": False, "a2_unlocked": False},
            "next_short_step": NEXT_SHORT_STEP if not errors else TASK_ID}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--database", type=Path, required=True); parser.add_argument("--registry", type=Path); parser.add_argument("--m12-registry", type=Path)
    args = parser.parse_args(); report = validate(args.database, args.registry, args.m12_registry)
    print(json.dumps(report, ensure_ascii=False, indent=2)); return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__": raise SystemExit(main())
