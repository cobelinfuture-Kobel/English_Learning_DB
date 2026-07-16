#!/usr/bin/env python3
"""Register and package private A1FS V1 non-audio human-pilot evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

TASK_ID = "A1FS-V1-M11_NonAudioHumanPilotAndEvidenceReview"
SCHEMA_VERSION = "a1fs.v1.m11.non_audio_human_pilot.v1"
READY_STATUS = "READY_A1FS_V1_M11_NON_AUDIO_HUMAN_PILOT_EVIDENCE_REVIEW"
PASS_STATUS = "PASS_A1FS_V1_M11_NON_AUDIO_HUMAN_PILOT"
GRAPH_STATUS = "PASS_A1FS_V1_M1_PREREQUISITE_GRAPH_AND_COVERAGE"
M6_STATUS = "PASS_A1FS_V1_M6_RESPONSE_CAPTURE_SCORING_M12_EVIDENCE_READY"
M7_STATUS = "PASS_A1FS_V1_M7_MASTERY_REMEDIATION_REASSESSMENT"
M8_STATUS = "PASS_A1FS_V1_M8_REVIEW_SCHEDULING_RETENTION_SPACED_PRACTICE"
M9_STATUS = "PASS_A1FS_V1_M9_TEACHER_DASHBOARD_PROGRESS_REPORTING_EXPORT"
NEXT_EXECUTION_STEP = "A1FS-V1-M11B_RealNonAudioHumanPilotExecutionAndEvidenceReview"
NEXT_PASS_STEP = "A1FS-V1-M12_V1AcceptanceCloseoutAndDeferredAudioBacklog"
ALLOWED_SKILLS = {"READING", "WRITING"}
PASS_OUTCOMES = {"AUTO_PASS", "HUMAN_APPROVE"}
FAIL_OUTCOMES = {"AUTO_FAIL", "HUMAN_REJECT"}
RESOLVED_OUTCOMES = PASS_OUTCOMES | FAIL_OUTCOMES
REQUIRED_ATTESTATIONS = {
    "real_learner_participated",
    "facilitator_observed",
    "learner_ui_used",
    "raw_response_not_exported",
    "audio_deferred",
    "speaking_recording_deferred",
    "privacy_review_completed",
}


class PilotEvidenceError(ValueError):
    """Fail-closed M11 pilot evidence error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def parse_at(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise PilotEvidenceError("timestamp_invalid") from exc
    if parsed.tzinfo is None:
        raise PilotEvidenceError("timestamp_timezone_required")
    return parsed.astimezone(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path, code: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = Path(path).read_bytes()
        value = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise PilotEvidenceError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise PilotEvidenceError(f"{code}_not_object")
    return value, raw


def write_private(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    os.chmod(path, 0o600)


SQL = """
CREATE TABLE IF NOT EXISTS m11_metadata(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS non_audio_human_pilot_runs(
  pilot_id TEXT PRIMARY KEY,
  learner_id TEXT NOT NULL,
  subject_key TEXT NOT NULL,
  facilitator_id TEXT NOT NULL,
  started_at TEXT NOT NULL,
  ended_at TEXT NOT NULL,
  session_ids_json TEXT NOT NULL,
  reading_session_count INTEGER NOT NULL,
  writing_session_count INTEGER NOT NULL,
  completed_session_count INTEGER NOT NULL,
  attempt_count INTEGER NOT NULL,
  resolved_attempt_count INTEGER NOT NULL,
  pass_count INTEGER NOT NULL,
  fail_count INTEGER NOT NULL,
  resolved_human_review_count INTEGER NOT NULL,
  attestations_json TEXT NOT NULL,
  source_graph_sha256 TEXT NOT NULL,
  source_m7_snapshot_digest TEXT NOT NULL,
  source_m8_snapshot_digest TEXT NOT NULL,
  source_m9_report_digest TEXT NOT NULL,
  package_digest TEXT NOT NULL UNIQUE,
  recorded_at TEXT NOT NULL
);
"""


class NonAudioHumanPilotEvidenceReview:
    def __init__(
        self,
        *,
        database_path: Path,
        graph_path: Path,
        m7_snapshot_path: Path,
        m8_snapshot_path: Path,
        m9_report_path: Path,
    ):
        self.database_path = Path(database_path)
        self.graph_path = Path(graph_path)
        self.m7_snapshot_path = Path(m7_snapshot_path)
        self.m8_snapshot_path = Path(m8_snapshot_path)
        self.m9_report_path = Path(m9_report_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def sources(self) -> tuple[dict[str, Any], bytes, dict[str, Any], dict[str, Any], dict[str, Any]]:
        graph, graph_raw = load_json(self.graph_path, "graph")
        m7, _ = load_json(self.m7_snapshot_path, "m7_snapshot")
        m8, _ = load_json(self.m8_snapshot_path, "m8_snapshot")
        m9, _ = load_json(self.m9_report_path, "m9_report")
        if graph.get("validation_status") != GRAPH_STATUS:
            raise PilotEvidenceError("graph_status_invalid")
        if m7.get("validation_status") != M7_STATUS:
            raise PilotEvidenceError("m7_status_invalid")
        if m8.get("validation_status") != M8_STATUS:
            raise PilotEvidenceError("m8_status_invalid")
        if m9.get("validation_status") != M9_STATUS:
            raise PilotEvidenceError("m9_status_invalid")
        graph_sha = digest(graph_raw)
        if m7.get("source_graph_sha256") != graph_sha or m8.get("source_graph_sha256") != graph_sha:
            raise PilotEvidenceError("snapshot_graph_binding_mismatch")
        if m8.get("source_m7_snapshot_digest") != digest(m7):
            raise PilotEvidenceError("m8_m7_binding_mismatch")
        bindings = m9.get("source_bindings", {})
        if bindings != {
            "graph_sha256": graph_sha,
            "m7_snapshot_digest": digest(m7),
            "m8_snapshot_digest": digest(m8),
        }:
            raise PilotEvidenceError("m9_source_binding_mismatch")
        learner_ids = {m7.get("learner_id"), m8.get("learner_id"), m9.get("learner", {}).get("learner_id")}
        if None in learner_ids or len(learner_ids) != 1:
            raise PilotEvidenceError("source_learner_mismatch")
        return graph, graph_raw, m7, m8, m9

    @staticmethod
    def _metadata(connection: sqlite3.Connection, table: str) -> dict[str, str]:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not exists:
            raise PilotEvidenceError(f"required_table_missing:{table}")
        return dict(connection.execute(f"SELECT key,value FROM {table}"))

    def initialize(self) -> dict[str, Any]:
        _, graph_raw, m7, m8, m9 = self.sources()
        with self.connect() as connection:
            metadata = self._metadata(connection, "metadata")
            m7_meta = self._metadata(connection, "m7_metadata")
            m8_meta = self._metadata(connection, "m8_metadata")
            m9_meta = self._metadata(connection, "m9_metadata")
            if metadata.get("m6_validation_status") != M6_STATUS:
                raise PilotEvidenceError("m6_database_status_invalid")
            if m7_meta.get("validation_status") != M7_STATUS:
                raise PilotEvidenceError("m7_database_status_invalid")
            if m8_meta.get("validation_status") != M8_STATUS:
                raise PilotEvidenceError("m8_database_status_invalid")
            if m9_meta.get("validation_status") != M9_STATUS:
                raise PilotEvidenceError("m9_database_status_invalid")
            connection.executescript(SQL)
            values = {
                "task_id": TASK_ID,
                "schema_version": SCHEMA_VERSION,
                "validation_status": READY_STATUS,
                "source_graph_sha256": digest(graph_raw),
                "source_m7_snapshot_digest": digest(m7),
                "source_m8_snapshot_digest": digest(m8),
                "source_m9_report_digest": digest(m9),
                "allowed_skills": canonical(sorted(ALLOWED_SKILLS)),
                "audio_deferred": "true",
                "speaking_recording_deferred": "true",
                "four_skill_human_pilot_claim_enabled": "false",
                "next_short_step": NEXT_EXECUTION_STEP,
            }
            connection.executemany("INSERT OR REPLACE INTO m11_metadata VALUES(?,?)", values.items())
            connection.commit()
        return {
            "validation_status": READY_STATUS,
            "pilot_mode": "NON_AUDIO_READING_WRITING",
            "audio_deferred": True,
            "four_skill_human_pilot_claim_enabled": False,
            "next_short_step": NEXT_EXECUTION_STEP,
        }

    def register_pilot(
        self,
        *,
        learner_id: str,
        facilitator_id: str,
        session_ids: Sequence[str],
        started_at: str,
        ended_at: str,
        attestations: Mapping[str, Any],
        output_root: Path,
        pilot_id: str | None = None,
        recorded_at: str | None = None,
    ) -> dict[str, Any]:
        _, graph_raw, m7, m8, m9 = self.sources()
        source_learner = m7["learner_id"]
        if learner_id != source_learner:
            raise PilotEvidenceError("pilot_learner_source_mismatch")
        facilitator_id = facilitator_id.strip()
        if not facilitator_id or facilitator_id == learner_id:
            raise PilotEvidenceError("facilitator_id_invalid")
        normalized_attestations = {str(key): value for key, value in attestations.items()}
        if set(normalized_attestations) != REQUIRED_ATTESTATIONS or any(
            normalized_attestations[key] is not True for key in REQUIRED_ATTESTATIONS
        ):
            raise PilotEvidenceError("operator_attestations_incomplete")
        unique_session_ids = list(dict.fromkeys(str(value).strip() for value in session_ids if str(value).strip()))
        if len(unique_session_ids) != len(session_ids) or len(unique_session_ids) < 2:
            raise PilotEvidenceError("pilot_session_ids_invalid")
        started = parse_at(started_at)
        ended = parse_at(ended_at)
        duration_seconds = (ended - started).total_seconds()
        if duration_seconds < 120 or duration_seconds > 4 * 60 * 60:
            raise PilotEvidenceError("pilot_duration_out_of_bounds")
        recorded = parse_at(recorded_at) if recorded_at else datetime.now(timezone.utc)
        if recorded < ended:
            raise PilotEvidenceError("recorded_at_before_pilot_end")
        placeholders = ",".join("?" for _ in unique_session_ids)
        with self.connect() as connection:
            m11_meta = self._metadata(connection, "m11_metadata")
            expected_bindings = {
                "source_graph_sha256": digest(graph_raw),
                "source_m7_snapshot_digest": digest(m7),
                "source_m8_snapshot_digest": digest(m8),
                "source_m9_report_digest": digest(m9),
            }
            if m11_meta.get("validation_status") != READY_STATUS or any(
                m11_meta.get(key) != value for key, value in expected_bindings.items()
            ):
                raise PilotEvidenceError("m11_not_initialized_for_sources")
            learner = connection.execute(
                "SELECT profile_state FROM learner_profiles WHERE learner_id=?", (learner_id,)
            ).fetchone()
            if not learner or learner["profile_state"] != "ACTIVE":
                raise PilotEvidenceError("learner_not_active")
            sessions = [
                dict(row)
                for row in connection.execute(
                    f"""SELECT session_id,lesson_id,skill,level,session_state,started_at,ended_at
                    FROM learning_sessions WHERE learner_id=? AND session_id IN({placeholders})
                    ORDER BY started_at,session_id""",
                    (learner_id, *unique_session_ids),
                )
            ]
            if {row["session_id"] for row in sessions} != set(unique_session_ids):
                raise PilotEvidenceError("pilot_session_not_found")
            if any(row["session_state"] != "COMPLETED" or not row["ended_at"] for row in sessions):
                raise PilotEvidenceError("pilot_session_not_completed")
            if any(row["skill"] not in ALLOWED_SKILLS for row in sessions):
                raise PilotEvidenceError("audio_or_speaking_session_forbidden")
            if any(row["level"] not in {"A1", "A1+"} for row in sessions):
                raise PilotEvidenceError("A2_PILOT_LOCKED")
            skills = {row["skill"] for row in sessions}
            if skills != ALLOWED_SKILLS:
                raise PilotEvidenceError("reading_and_writing_sessions_required")
            for row in sessions:
                row_start, row_end = parse_at(row["started_at"]), parse_at(row["ended_at"])
                if row_start < started or row_end > ended or row_end <= row_start:
                    raise PilotEvidenceError("session_outside_pilot_window")
            attempts = [
                dict(row)
                for row in connection.execute(
                    f"""SELECT a.attempt_id,a.session_id,a.asset_key,a.submitted_at,c.skill,c.role,
                    s.scoring_mode,s.outcome,s.human_review_required,q.decision
                    FROM response_attempts a JOIN response_contracts c USING(asset_key)
                    JOIN scoring_results s USING(attempt_id) JOIN human_review_queue q USING(attempt_id)
                    WHERE a.learner_id=? AND a.session_id IN({placeholders})
                    ORDER BY a.submitted_at,a.attempt_id""",
                    (learner_id, *unique_session_ids),
                )
            ]
            attempts_by_session = {session_id: 0 for session_id in unique_session_ids}
            for row in attempts:
                attempts_by_session[row["session_id"]] += 1
                if row["outcome"] not in RESOLVED_OUTCOMES:
                    raise PilotEvidenceError("unresolved_pilot_attempt_forbidden")
                submitted = parse_at(row["submitted_at"])
                if submitted < started or submitted > ended:
                    raise PilotEvidenceError("attempt_outside_pilot_window")
            if any(count < 1 for count in attempts_by_session.values()):
                raise PilotEvidenceError("every_pilot_session_requires_attempt")
            if not attempts or not any(row["outcome"] in PASS_OUTCOMES for row in attempts):
                raise PilotEvidenceError("pilot_requires_resolved_pass")
            writing_reviews = [
                row for row in attempts
                if row["skill"] == "WRITING"
                and row["scoring_mode"] == "FEATURE_RUBRIC"
                and row["human_review_required"] == 1
                and row["outcome"] in {"HUMAN_APPROVE", "HUMAN_REJECT"}
                and row["decision"] in {"APPROVE", "REJECT"}
            ]
            if not writing_reviews:
                raise PilotEvidenceError("resolved_writing_human_review_required")
            m7_row = connection.execute(
                "SELECT created_at FROM mastery_snapshots WHERE learner_id=? AND snapshot_digest=?",
                (learner_id, digest(m7)),
            ).fetchone()
            m8_row = connection.execute(
                "SELECT created_at FROM retention_snapshots WHERE learner_id=? AND snapshot_digest=?",
                (learner_id, digest(m8)),
            ).fetchone()
            m9_row = connection.execute(
                "SELECT exported_at FROM dashboard_exports WHERE learner_id=? AND report_digest=?",
                (learner_id, digest(m9)),
            ).fetchone()
            if not m7_row or parse_at(m7_row["created_at"]) < ended:
                raise PilotEvidenceError("m7_snapshot_not_refreshed_after_pilot")
            if not m8_row or parse_at(m8_row["created_at"]) < ended:
                raise PilotEvidenceError("m8_snapshot_not_refreshed_after_pilot")
            if not m9_row or parse_at(m9_row["exported_at"]) < ended:
                raise PilotEvidenceError("m9_report_not_refreshed_after_pilot")
            report_rows = {row["skill"]: row for row in m9.get("four_skill_progress", [])}
            selected_counts = {
                skill: {
                    "sessions": sum(row["skill"] == skill for row in sessions),
                    "attempts": sum(row["skill"] == skill for row in attempts),
                }
                for skill in ALLOWED_SKILLS
            }
            for skill, counts in selected_counts.items():
                report_row = report_rows.get(skill, {})
                if int(report_row.get("completed_session_count", 0)) < counts["sessions"]:
                    raise PilotEvidenceError(f"m9_completed_session_count_stale:{skill}")
                if int(report_row.get("attempt_count", 0)) < counts["attempts"]:
                    raise PilotEvidenceError(f"m9_attempt_count_stale:{skill}")
            session_evidence = []
            for row in sessions:
                session_attempts = [attempt for attempt in attempts if attempt["session_id"] == row["session_id"]]
                session_evidence.append(
                    {
                        "session_id": row["session_id"],
                        "lesson_id": row["lesson_id"],
                        "skill": row["skill"],
                        "level": row["level"],
                        "started_at": iso(parse_at(row["started_at"])),
                        "ended_at": iso(parse_at(row["ended_at"])),
                        "attempt_count": len(session_attempts),
                        "pass_count": sum(attempt["outcome"] in PASS_OUTCOMES for attempt in session_attempts),
                        "fail_count": sum(attempt["outcome"] in FAIL_OUTCOMES for attempt in session_attempts),
                        "resolved_human_review_count": sum(
                            attempt["outcome"] in {"HUMAN_APPROVE", "HUMAN_REJECT"}
                            for attempt in session_attempts
                        ),
                    }
                )
            subject_key = f"M11_SUBJECT:{digest({'learner_id': learner_id, 'pilot_start': iso(started)})[:20]}"
            pilot_id = pilot_id or f"M11_PILOT:{digest({'subject_key': subject_key, 'session_ids': sorted(unique_session_ids)})[:24]}"
            package = {
                "task_id": TASK_ID,
                "schema_version": SCHEMA_VERSION,
                "validation_status": PASS_STATUS,
                "private_local_only": True,
                "pilot_mode": "NON_AUDIO_READING_WRITING",
                "pilot_id": pilot_id,
                "subject_key": subject_key,
                "facilitator_id": facilitator_id,
                "started_at": iso(started),
                "ended_at": iso(ended),
                "recorded_at": iso(recorded),
                "source_bindings": {
                    "graph_sha256": digest(graph_raw),
                    "m7_snapshot_digest": digest(m7),
                    "m8_snapshot_digest": digest(m8),
                    "m9_report_digest": digest(m9),
                },
                "session_evidence": session_evidence,
                "outcome_summary": {
                    "completed_session_count": len(sessions),
                    "reading_session_count": sum(row["skill"] == "READING" for row in sessions),
                    "writing_session_count": sum(row["skill"] == "WRITING" for row in sessions),
                    "attempt_count": len(attempts),
                    "resolved_attempt_count": len(attempts),
                    "pass_count": sum(row["outcome"] in PASS_OUTCOMES for row in attempts),
                    "fail_count": sum(row["outcome"] in FAIL_OUTCOMES for row in attempts),
                    "resolved_human_review_count": len(writing_reviews),
                },
                "workflow_evidence": {
                    "learner_ui_used": True,
                    "response_capture_verified": True,
                    "resolved_scoring_verified": True,
                    "writing_human_review_verified": True,
                    "mastery_snapshot_refreshed": True,
                    "review_retention_snapshot_refreshed": True,
                    "teacher_dashboard_refreshed": True,
                    "audio_evidence_used": False,
                    "speaking_recording_used": False,
                },
                "operator_attestations": normalized_attestations,
                "claim_boundaries": {
                    "non_audio_human_pilot_claimed": True,
                    "four_skill_human_pilot_claimed": False,
                    "listening_audio_complete": False,
                    "speaking_recording_complete": False,
                    "audio_deferred": True,
                    "a2_unlocked": False,
                    "public_delivery": False,
                    "raw_response_exported": False,
                },
                "next_short_step": NEXT_PASS_STEP,
            }
            package_digest = digest(package)
            connection.execute(
                """INSERT INTO non_audio_human_pilot_runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    pilot_id,
                    learner_id,
                    subject_key,
                    facilitator_id,
                    iso(started),
                    iso(ended),
                    canonical(sorted(unique_session_ids)),
                    package["outcome_summary"]["reading_session_count"],
                    package["outcome_summary"]["writing_session_count"],
                    package["outcome_summary"]["completed_session_count"],
                    package["outcome_summary"]["attempt_count"],
                    package["outcome_summary"]["resolved_attempt_count"],
                    package["outcome_summary"]["pass_count"],
                    package["outcome_summary"]["fail_count"],
                    package["outcome_summary"]["resolved_human_review_count"],
                    canonical(normalized_attestations),
                    digest(graph_raw),
                    digest(m7),
                    digest(m8),
                    digest(m9),
                    package_digest,
                    iso(recorded),
                ),
            )
            connection.commit()
        output_path = Path(output_root) / "a1fs_v1_m11_non_audio_human_pilot.private.json"
        write_private(output_path, package)
        return {
            "validation_status": PASS_STATUS,
            "pilot_id": pilot_id,
            "package_path": str(output_path),
            "package_sha256": package_digest,
            "four_skill_human_pilot_claimed": False,
            "audio_deferred": True,
            "next_short_step": NEXT_PASS_STEP,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "register"):
        command = commands.add_parser(name)
        command.add_argument("--database", type=Path, required=True)
        command.add_argument("--graph", type=Path, required=True)
        command.add_argument("--m7-snapshot", type=Path, required=True)
        command.add_argument("--m8-snapshot", type=Path, required=True)
        command.add_argument("--m9-report", type=Path, required=True)
        if name == "register":
            command.add_argument("--learner-id", required=True)
            command.add_argument("--facilitator-id", required=True)
            command.add_argument("--session-id", action="append", required=True)
            command.add_argument("--started-at", required=True)
            command.add_argument("--ended-at", required=True)
            command.add_argument("--attestations", type=Path, required=True)
            command.add_argument("--output-root", type=Path, required=True)
            command.add_argument("--pilot-id")
    args = parser.parse_args()
    engine = NonAudioHumanPilotEvidenceReview(
        database_path=args.database,
        graph_path=args.graph,
        m7_snapshot_path=args.m7_snapshot,
        m8_snapshot_path=args.m8_snapshot,
        m9_report_path=args.m9_report,
    )
    if args.command == "init":
        result = engine.initialize()
    else:
        attestations, _ = load_json(args.attestations, "attestations")
        result = engine.register_pilot(
            learner_id=args.learner_id,
            facilitator_id=args.facilitator_id,
            session_ids=args.session_id,
            started_at=args.started_at,
            ended_at=args.ended_at,
            attestations=attestations,
            output_root=args.output_root,
            pilot_id=args.pilot_id,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
