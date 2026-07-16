#!/usr/bin/env python3
"""A1FS V1 M6 private response capture, scoring, review, and M12 export."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

TASK_ID = "A1FS-V1-M6_ResponseCaptureScoringAndM12Evidence"
SCHEMA_VERSION = "a1fs.v1.m6.response_evidence.sqlite.v1"
REGISTRY_SCHEMA_VERSION = "a1fs.v1.m6.evidence_registry.v1"
STATUS = "PASS_A1FS_V1_M6_RESPONSE_CAPTURE_SCORING_M12_EVIDENCE_READY"
M3_STATUS = "PASS_A1FS_V1_M3_LEARNER_PROFILE_SESSION_STATE_STORAGE_READY"
M5_STATUS = "PASS_A1FS_V1_M5_FOUR_SKILL_RENDERER_LEARNER_UI_READY"
CONSUMER_STATUS = "PASS_A1FS_V1_M2_FOUR_SKILL_ASSET_BODY_CONSUMER_READY"
NEXT_SHORT_STEP = "A1FS-V1-M7_MasteryErrorDiagnosisRemediationAndReassessment"
M08_TASK_ID = "E4S-A1V1-M08_TextModeLearnerSessionAndProgressEvidenceIntegration"
M08_SCHEMA_VERSION = "e4s.a1v1.text_mode_attempt_registry.v1"
CAPTURE_ROLES = {"CHK", "PRD", "XFR", "EVD"}
REVIEW_DECISIONS = {"APPROVE", "REJECT", "DEFER"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ResponseEvidenceError(ValueError):
    """Fail-closed M6 error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode() if isinstance(value, str) else canonical(value).encode()
    return hashlib.sha256(raw).hexdigest()


def utc(value: str | None = None) -> str:
    value = value or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ResponseEvidenceError("timestamp_invalid") from exc
    if parsed.tzinfo is None:
        raise ResponseEvidenceError("timestamp_timezone_required")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def read(path: Path, code: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise ResponseEvidenceError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise ResponseEvidenceError(f"{code}_not_object")
    return value, raw


def write_private(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    os.chmod(path, 0o600)


def walk(value: Any, keys: set[str]) -> list[Any]:
    result: list[Any] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in keys:
                result.append(child)
            result.extend(walk(child, keys))
    elif isinstance(value, list):
        for child in value:
            result.extend(walk(child, keys))
    return result


def strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(row, str) for row in value):
        return list(value)
    return []


def norm(value: str, case: bool = True, punctuation: bool = True) -> str:
    result = re.sub(r"\s+", " ", value.strip())
    if punctuation:
        result = re.sub(r"[.!?]+$", "", result).strip()
    return result.casefold() if case else result


def derive_contract(asset: Mapping[str, Any]) -> dict[str, Any]:
    payload = asset.get("payload")
    if not isinstance(payload, Mapping):
        raise ResponseEvidenceError(f"asset_payload_invalid:{asset.get('asset_key')}")
    explicit = next((dict(payload[name]) for name in ("private_scoring_contract", "scoring_contract", "answer_contract") if isinstance(payload.get(name), Mapping)), {})
    accepted_texts = strings(explicit.get("accepted_texts"))
    accepted_sequence = strings(explicit.get("accepted_sequence"))
    if not accepted_texts:
        for candidate in walk(payload, {"accepted_texts", "accepted_missing_tokens", "correct_answer", "answer"}):
            accepted_texts.extend(strings(candidate))
    if not accepted_sequence:
        for candidate in walk(payload, {"accepted_sequence", "correct_sequence", "correct_token_sequence", "correct_morphology_parts"}):
            if strings(candidate):
                accepted_sequence = strings(candidate)
                break
    rubric = explicit.get("rubric") if isinstance(explicit.get("rubric"), Mapping) else payload.get("scoring_rubric") if isinstance(payload.get("scoring_rubric"), Mapping) else {}
    skill, role = str(asset["skill"]), str(asset["role"])
    mode = str(explicit.get("scoring_mode") or "")
    if mode not in {"EXACT_OPTION", "EXACT_SEQUENCE", "NORMALIZED_TEXT", "FEATURE_RUBRIC"}:
        mode = "EXACT_SEQUENCE" if accepted_sequence else "NORMALIZED_TEXT" if accepted_texts else "FEATURE_RUBRIC" if rubric or (skill in {"SPEAKING", "WRITING"} and role in {"PRD", "XFR", "EVD"}) else "NONE"
    if (mode in {"EXACT_OPTION", "NORMALIZED_TEXT"} and not accepted_texts) or (mode == "EXACT_SEQUENCE" and not accepted_sequence):
        mode = "NONE"
    prompts = walk(payload, {"question", "prompt", "launch_cue", "instruction"})
    legacy_hash = payload.get("m12_session_bank_sha256")
    if legacy_hash is not None and (not isinstance(legacy_hash, str) or not HEX64.fullmatch(legacy_hash)):
        raise ResponseEvidenceError(f"m12_session_bank_sha256_invalid:{asset['asset_key']}")
    return {
        "asset_key": str(asset["asset_key"]), "lesson_id": str(asset["lesson_id"]), "skill": skill, "role": role,
        "prompt": next((row.strip() for row in prompts if isinstance(row, str) and row.strip()), "Complete this learning step."),
        "capture_enabled": bool(payload.get("response_capture_enabled", True)) and role in CAPTURE_ROLES and mode != "NONE" and not (skill == "LISTENING" and role == "AUD"),
        "response_type": "string_array" if mode == "EXACT_SEQUENCE" else "string", "scoring_mode": mode,
        "accepted_texts": list(dict.fromkeys(accepted_texts)), "accepted_sequence": accepted_sequence,
        "case_insensitive": bool(explicit.get("case_insensitive", True)), "punctuation_tolerance": bool(explicit.get("punctuation_tolerance", True)),
        "human_review_fallback": mode == "FEATURE_RUBRIC", "rubric": dict(rubric),
        "m12_item_id": str(payload.get("m12_item_id") or f"A1FS_ASSET:{asset['asset_key']}"), "m12_session_bank_sha256": legacy_hash,
    }


SQL = """
CREATE TABLE IF NOT EXISTS response_contracts(asset_key TEXT PRIMARY KEY REFERENCES lesson_assets(asset_key),lesson_id TEXT NOT NULL,skill TEXT NOT NULL,role TEXT NOT NULL,contract_json TEXT NOT NULL,contract_digest TEXT NOT NULL UNIQUE,capture_enabled INTEGER NOT NULL CHECK(capture_enabled IN(0,1)));
CREATE TABLE IF NOT EXISTS response_attempts(attempt_id TEXT PRIMARY KEY,learner_id TEXT NOT NULL REFERENCES learner_profiles(learner_id),session_id TEXT NOT NULL REFERENCES learning_sessions(session_id),lesson_id TEXT NOT NULL,asset_key TEXT NOT NULL REFERENCES response_contracts(asset_key),attempt_sequence INTEGER NOT NULL CHECK(attempt_sequence>=1),response_json TEXT NOT NULL,submitted_at TEXT NOT NULL,previous_hash TEXT NOT NULL,attempt_hash TEXT NOT NULL UNIQUE,UNIQUE(session_id,asset_key,attempt_sequence));
CREATE TABLE IF NOT EXISTS scoring_results(attempt_id TEXT PRIMARY KEY REFERENCES response_attempts(attempt_id),scoring_mode TEXT NOT NULL,outcome TEXT NOT NULL CHECK(outcome IN('AUTO_PASS','AUTO_FAIL','PENDING_HUMAN_REVIEW','HUMAN_APPROVE','HUMAN_REJECT','HUMAN_DEFER')),score REAL,human_review_required INTEGER NOT NULL CHECK(human_review_required IN(0,1)),scored_at TEXT NOT NULL,contract_digest TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS human_review_queue(attempt_id TEXT PRIMARY KEY REFERENCES response_attempts(attempt_id),decision TEXT NOT NULL CHECK(decision IN('PENDING','APPROVE','REJECT','DEFER')),reviewer_id TEXT,reviewed_at TEXT,criteria_json TEXT NOT NULL,notes TEXT);
CREATE TABLE IF NOT EXISTS evidence_exports(export_id TEXT PRIMARY KEY,session_id TEXT NOT NULL REFERENCES learning_sessions(session_id),exported_at TEXT NOT NULL,registry_digest TEXT NOT NULL,m12_registry_digest TEXT NOT NULL,legacy_import_ready INTEGER NOT NULL CHECK(legacy_import_ready IN(0,1)));
"""


class ResponseEvidenceStore:
    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    @contextmanager
    def write(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self, *, consumer_path: Path, lesson_bundle_path: Path) -> dict[str, Any]:
        consumer, consumer_raw = read(consumer_path, "consumer")
        bundle, bundle_raw = read(lesson_bundle_path, "bundle")
        if consumer.get("validation_status") != CONSUMER_STATUS:
            raise ResponseEvidenceError("consumer_status_invalid")
        if bundle.get("validation_status") != M5_STATUS:
            raise ResponseEvidenceError("bundle_status_invalid")
        if bundle.get("source_consumer_sha256") != sha(consumer_raw):
            raise ResponseEvidenceError("bundle_consumer_binding_mismatch")
        lesson = bundle.get("lesson") or {}
        if lesson.get("level") not in {"A1", "A1+"}:
            raise ResponseEvidenceError("A2_RESPONSE_CAPTURE_LOCKED")
        assets = {str(row["asset_key"]): row for row in consumer.get("asset_records", []) if row.get("lesson_id") == lesson.get("lesson_id")}
        if set(assets) != {str(row["asset_key"]) for row in bundle.get("assets", [])}:
            raise ResponseEvidenceError("bundle_asset_identity_mismatch")
        with self.write() as connection:
            metadata = dict(connection.execute("SELECT key,value FROM metadata"))
            if metadata.get("validation_status") != M3_STATUS:
                raise ResponseEvidenceError("m3_database_status_invalid")
            if metadata.get("consumer_sha256") != sha(consumer_raw):
                raise ResponseEvidenceError("database_consumer_binding_mismatch")
            level = connection.execute("SELECT level FROM lesson_catalog WHERE lesson_id=?", (lesson["lesson_id"],)).fetchone()
            if not level or level[0] not in {"A1", "A1+"}:
                raise ResponseEvidenceError("database_lesson_not_captureable")
            connection.executescript(SQL)
            enabled_count = 0
            for asset in assets.values():
                contract = derive_contract(asset)
                enabled_count += int(contract["capture_enabled"])
                connection.execute(
                    """INSERT INTO response_contracts VALUES(?,?,?,?,?,?,?) ON CONFLICT(asset_key) DO UPDATE SET contract_json=excluded.contract_json,contract_digest=excluded.contract_digest,capture_enabled=excluded.capture_enabled""",
                    (contract["asset_key"], contract["lesson_id"], contract["skill"], contract["role"], canonical(contract), sha(contract), int(contract["capture_enabled"])),
                )
            updates = {
                "m6_task_id": TASK_ID, "m6_schema_version": SCHEMA_VERSION, "m6_validation_status": STATUS,
                "response_capture_enabled": "true", "scoring_write_enabled": "true", "mastery_write_enabled": "false",
                "m6_bundle_sha256": sha(bundle_raw), "m6_next_short_step": NEXT_SHORT_STEP,
            }
            connection.executemany("INSERT OR REPLACE INTO metadata VALUES(?,?)", updates.items())
        return {"validation_status": STATUS, "lesson_id": lesson["lesson_id"], "capture_contract_count": enabled_count, "mastery_write_enabled": False, "next_short_step": NEXT_SHORT_STEP}

    @staticmethod
    def score(contract: Mapping[str, Any], response: Any) -> tuple[str, float | None]:
        if contract["response_type"] == "string":
            if not isinstance(response, str) or not response.strip():
                raise ResponseEvidenceError("response_string_required")
        elif not isinstance(response, list) or not response or not all(isinstance(row, str) and row.strip() for row in response):
            raise ResponseEvidenceError("response_string_array_required")
        mode = contract["scoring_mode"]
        if mode == "FEATURE_RUBRIC":
            return "PENDING_HUMAN_REVIEW", None
        if mode in {"EXACT_OPTION", "NORMALIZED_TEXT"}:
            actual = norm(response, contract["case_insensitive"], contract["punctuation_tolerance"])
            accepted = {norm(row, contract["case_insensitive"], contract["punctuation_tolerance"]) for row in contract["accepted_texts"]}
            passed = actual in accepted and bool(actual)
        elif mode == "EXACT_SEQUENCE":
            passed = [norm(row) for row in response] == [norm(row) for row in contract["accepted_sequence"]]
        else:
            raise ResponseEvidenceError("unsupported_scoring_mode")
        return ("AUTO_PASS", 1.0) if passed else ("AUTO_FAIL", 0.0)

    def capture_response(self, *, learner_id: str, session_id: str, asset_key: str, response: Any, expected_session_version: int, attempt_id: str | None = None, submitted_at: str | None = None) -> dict[str, Any]:
        submitted_at = utc(submitted_at)
        attempt_id = attempt_id or str(uuid.uuid4())
        with self.write() as connection:
            session = connection.execute("SELECT * FROM learning_sessions WHERE session_id=?", (session_id,)).fetchone()
            if not session or session["session_state"] != "ACTIVE": raise ResponseEvidenceError("session_not_active")
            if session["learner_id"] != learner_id: raise ResponseEvidenceError("session_learner_mismatch")
            if session["level"] not in {"A1", "A1+"}: raise ResponseEvidenceError("A2_RESPONSE_CAPTURE_LOCKED")
            if session["session_version"] != expected_session_version: raise ResponseEvidenceError("session_version_conflict")
            row = connection.execute("SELECT * FROM response_contracts WHERE asset_key=?", (asset_key,)).fetchone()
            if not row or row["lesson_id"] != session["lesson_id"]: raise ResponseEvidenceError("asset_not_in_session_lesson")
            contract = json.loads(row["contract_json"])
            if not contract["capture_enabled"]: raise ResponseEvidenceError("response_capture_not_enabled_for_asset")
            outcome, score = self.score(contract, response)
            sequence = connection.execute("SELECT COALESCE(MAX(attempt_sequence),0)+1 FROM response_attempts WHERE session_id=? AND asset_key=?", (session_id, asset_key)).fetchone()[0]
            previous = connection.execute("SELECT attempt_hash FROM response_attempts ORDER BY rowid DESC LIMIT 1").fetchone()
            previous_hash = previous[0] if previous else "0" * 64
            core = {"attempt_id": attempt_id, "learner_id": learner_id, "session_id": session_id, "lesson_id": session["lesson_id"], "asset_key": asset_key, "attempt_sequence": sequence, "response": response, "submitted_at": submitted_at}
            attempt_hash = sha(previous_hash + canonical(core))
            connection.execute("INSERT INTO response_attempts VALUES(?,?,?,?,?,?,?,?,?,?)", (attempt_id, learner_id, session_id, session["lesson_id"], asset_key, sequence, canonical(response), submitted_at, previous_hash, attempt_hash))
            connection.execute("INSERT INTO scoring_results VALUES(?,?,?,?,?,?,?)", (attempt_id, contract["scoring_mode"], outcome, score, int(outcome == "PENDING_HUMAN_REVIEW"), submitted_at, row["contract_digest"]))
            criteria = {"grammar_target_match": None, "meaning_matches_context": None, "complete_response": None}
            connection.execute("INSERT INTO human_review_queue VALUES(?,?,?,?,?,?)", (attempt_id, "PENDING", None, None, canonical(criteria), None))
            connection.execute("UPDATE learning_sessions SET session_version=session_version+1 WHERE session_id=?", (session_id,))
        return {"attempt_id": attempt_id, "attempt_sequence": sequence, "outcome": outcome, "score": score, "human_review_required": outcome == "PENDING_HUMAN_REVIEW", "mastery_claimed": False}

    def review_response(self, *, attempt_id: str, decision: str, reviewer_id: str, criteria: Mapping[str, Any], notes: str | None = None, reviewed_at: str | None = None) -> dict[str, Any]:
        if decision not in REVIEW_DECISIONS: raise ResponseEvidenceError("review_decision_invalid")
        if not reviewer_id.strip(): raise ResponseEvidenceError("reviewer_id_required")
        keys = {"grammar_target_match", "meaning_matches_context", "complete_response"}
        if set(criteria) != keys or any(criteria[key] not in {True, False} for key in keys): raise ResponseEvidenceError("review_criteria_invalid")
        if decision == "APPROVE" and not all(criteria.values()): raise ResponseEvidenceError("approved_review_criteria_not_all_true")
        reviewed_at = utc(reviewed_at)
        with self.write() as connection:
            row = connection.execute("SELECT scoring_mode FROM scoring_results WHERE attempt_id=?", (attempt_id,)).fetchone()
            if not row: raise ResponseEvidenceError("attempt_not_found")
            if row[0] != "FEATURE_RUBRIC": raise ResponseEvidenceError("deterministic_item_review_override_forbidden")
            outcome = {"APPROVE": "HUMAN_APPROVE", "REJECT": "HUMAN_REJECT", "DEFER": "HUMAN_DEFER"}[decision]
            score = 1.0 if decision == "APPROVE" else 0.0 if decision == "REJECT" else None
            connection.execute("UPDATE human_review_queue SET decision=?,reviewer_id=?,reviewed_at=?,criteria_json=?,notes=? WHERE attempt_id=?", (decision, reviewer_id, reviewed_at, canonical(dict(criteria)), notes, attempt_id))
            connection.execute("UPDATE scoring_results SET outcome=?,score=?,human_review_required=0,scored_at=? WHERE attempt_id=?", (outcome, score, reviewed_at, attempt_id))
        return {"attempt_id": attempt_id, "outcome": outcome, "score": score, "mastery_claimed": False}

    def export_evidence(self, *, session_id: str, output_root: Path, exported_at: str | None = None) -> dict[str, Any]:
        exported_at = utc(exported_at)
        with self.connect() as connection:
            session = connection.execute("SELECT * FROM learning_sessions WHERE session_id=?", (session_id,)).fetchone()
            if not session: raise ResponseEvidenceError("session_not_found")
            rows = connection.execute("""SELECT a.*,c.contract_json,c.contract_digest,r.scoring_mode,r.outcome,r.score,q.decision,q.reviewer_id,q.reviewed_at,q.criteria_json,q.notes FROM response_attempts a JOIN response_contracts c USING(asset_key) JOIN scoring_results r USING(attempt_id) JOIN human_review_queue q USING(attempt_id) WHERE a.session_id=? ORDER BY a.asset_key,a.attempt_sequence""", (session_id,)).fetchall()
            entries, attempts, bank_hashes = [], [], set()
            explicit_legacy = True
            for row in rows:
                contract = json.loads(row["contract_json"])
                response = json.loads(row["response_json"])
                review = {"decision": row["decision"], "reviewer_id": row["reviewer_id"], "reviewed_at": row["reviewed_at"], "criteria": json.loads(row["criteria_json"]), "notes": row["notes"]}
                if contract.get("m12_session_bank_sha256"): bank_hashes.add(contract["m12_session_bank_sha256"])
                else: explicit_legacy = False
                if contract["m12_item_id"].startswith("A1FS_ASSET:"): explicit_legacy = False
                attempts.append({"item_id": contract["m12_item_id"], "attempt_sequence": row["attempt_sequence"], "response": response, "submitted_at": row["submitted_at"], "operator_review": review})
                entries.append({"evidence_id": f"M6_EVIDENCE:{row['attempt_id']}", "attempt_id": row["attempt_id"], "learner_id": row["learner_id"], "session_id": row["session_id"], "lesson_id": row["lesson_id"], "asset_key": row["asset_key"], "skill": contract["skill"], "role": contract["role"], "attempt_sequence": row["attempt_sequence"], "response": response, "submitted_at": row["submitted_at"], "scoring_mode": row["scoring_mode"], "outcome": row["outcome"], "score": row["score"], "operator_review": review, "contract_digest": row["contract_digest"], "mastery_claimed": False})
            compatibility = [{"item_id": json.loads(row["contract_json"])["m12_item_id"], "contract_digest": row["contract_digest"]} for row in rows]
            legacy_ready = bool(rows) and explicit_legacy and len(bank_hashes) == 1
            bank_hash = next(iter(bank_hashes)) if legacy_ready else sha(compatibility)
            m12 = {"task_id": M08_TASK_ID, "schema_version": M08_SCHEMA_VERSION, "private_local_only": True, "session_bank_sha256": bank_hash, "session_id": session_id, "learner_ref": session["learner_id"], "attempts": attempts}
            registry = {
                "task_id": TASK_ID, "schema_version": REGISTRY_SCHEMA_VERSION, "validation_status": STATUS, "private_local_only": True,
                "database_binding_sha256": sha(self.database_path.read_bytes()),
                "session": {"session_id": session_id, "learner_id": session["learner_id"], "lesson_id": session["lesson_id"], "skill": session["skill"], "level": session["level"]},
                "attempt_count": len(entries), "entries": entries, "entries_sha256": sha(entries),
                "m12_compatibility": {"registry_schema_compatible": True, "scoring_semantics_compatible": True, "legacy_allowlist_import_ready": legacy_ready, "compatibility_bank_sha256": bank_hash, "boundary_note": "Legacy M12 direct import requires explicit legacy item IDs and one exact legacy bank hash."},
                "claim_boundaries": {"mastery_written": False, "retention_confirmed": False, "a2_unlocked": False, "public_delivery": False, "audio_evidence_used": False, "speaking_recording_used": False},
                "next_short_step": NEXT_SHORT_STEP,
            }
        root = Path(output_root)
        registry_path = root / "a1fs_v1_m6_evidence_registry.private.json"
        m12_path = root / "m12_attempt_registry.private.json"
        write_private(registry_path, registry)
        write_private(m12_path, m12)
        with self.write() as connection:
            connection.execute("INSERT INTO evidence_exports VALUES(?,?,?,?,?,?)", (str(uuid.uuid4()), session_id, exported_at, sha(registry), sha(m12), int(legacy_ready)))
        return {"validation_status": STATUS, "registry_path": str(registry_path), "m12_registry_path": str(m12_path), "attempt_count": len(entries), "legacy_allowlist_import_ready": legacy_ready, "next_short_step": NEXT_SHORT_STEP}


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init"); init.add_argument("--database", type=Path, required=True); init.add_argument("--consumer", type=Path, required=True); init.add_argument("--bundle", type=Path, required=True)
    capture = commands.add_parser("capture"); capture.add_argument("--database", type=Path, required=True); capture.add_argument("--learner-id", required=True); capture.add_argument("--session-id", required=True); capture.add_argument("--asset-key", required=True); capture.add_argument("--response-json", required=True); capture.add_argument("--expected-session-version", type=int, required=True)
    review = commands.add_parser("review"); review.add_argument("--database", type=Path, required=True); review.add_argument("--attempt-id", required=True); review.add_argument("--decision", required=True); review.add_argument("--reviewer-id", required=True); review.add_argument("--criteria-json", required=True); review.add_argument("--notes")
    export = commands.add_parser("export"); export.add_argument("--database", type=Path, required=True); export.add_argument("--session-id", required=True); export.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(); store = ResponseEvidenceStore(args.database)
    if args.command == "init": result = store.initialize(consumer_path=args.consumer, lesson_bundle_path=args.bundle)
    elif args.command == "capture": result = store.capture_response(learner_id=args.learner_id, session_id=args.session_id, asset_key=args.asset_key, response=json.loads(args.response_json), expected_session_version=args.expected_session_version)
    elif args.command == "review": result = store.review_response(attempt_id=args.attempt_id, decision=args.decision, reviewer_id=args.reviewer_id, criteria=json.loads(args.criteria_json), notes=args.notes)
    else: result = store.export_evidence(session_id=args.session_id, output_root=args.output_root)
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
