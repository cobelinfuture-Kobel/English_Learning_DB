#!/usr/bin/env python3
"""Build a private read-only A1FS V1 teacher/parent progress dashboard."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

TASK_ID = "A1FS-V1-M9_TeacherDashboardProgressReportingAndExport"
SCHEMA_VERSION = "a1fs.v1.m9.teacher_dashboard.v1"
STATUS = "PASS_A1FS_V1_M9_TEACHER_DASHBOARD_PROGRESS_REPORTING_EXPORT"
GRAPH_STATUS = "PASS_A1FS_V1_M1_PREREQUISITE_GRAPH_AND_COVERAGE"
M7_STATUS = "PASS_A1FS_V1_M7_MASTERY_REMEDIATION_REASSESSMENT"
M8_STATUS = "PASS_A1FS_V1_M8_REVIEW_SCHEDULING_RETENTION_SPACED_PRACTICE"
NEXT_SHORT_STEP = "A1FS-V1-M10_ListeningAudioAndSpeakingRecordingIntegration"
SKILLS = ("LISTENING", "SPEAKING", "READING", "WRITING")


class DashboardError(ValueError):
    """Fail-closed M9 error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode() if isinstance(value, str) else canonical(value).encode()
    return hashlib.sha256(raw).hexdigest()


def timestamp(value: str | None = None) -> str:
    value = value or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise DashboardError("timestamp_timezone_required")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def load(path: Path, code: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise DashboardError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise DashboardError(f"{code}_not_object")
    return value, raw


def write_private(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)
    os.chmod(path, 0o600)


SQL = """
CREATE TABLE IF NOT EXISTS m9_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS dashboard_exports(
  export_id TEXT PRIMARY KEY,
  learner_id TEXT NOT NULL,
  exported_at TEXT NOT NULL,
  source_graph_sha256 TEXT NOT NULL,
  source_m7_snapshot_digest TEXT NOT NULL,
  source_m8_snapshot_digest TEXT NOT NULL,
  report_digest TEXT NOT NULL UNIQUE,
  html_digest TEXT NOT NULL UNIQUE
);
"""


def skill_rows(connection: sqlite3.Connection, learner_id: str) -> list[dict[str, Any]]:
    sessions = {
        row["skill"]: dict(row)
        for row in connection.execute(
            """SELECT skill,COUNT(*) session_count,SUM(session_state='COMPLETED') completed_session_count
            FROM learning_sessions WHERE learner_id=? GROUP BY skill""",
            (learner_id,),
        )
    }
    attempts = {
        row["skill"]: dict(row)
        for row in connection.execute(
            """SELECT c.skill,COUNT(*) attempt_count,
            SUM(s.outcome IN('AUTO_PASS','HUMAN_APPROVE')) pass_count,
            SUM(s.outcome IN('AUTO_FAIL','HUMAN_REJECT')) fail_count,
            SUM(s.outcome IN('PENDING_HUMAN_REVIEW','HUMAN_DEFER')) pending_review_count
            FROM response_attempts a JOIN response_contracts c USING(asset_key)
            JOIN scoring_results s USING(attempt_id)
            WHERE a.learner_id=? GROUP BY c.skill""",
            (learner_id,),
        )
    }
    result = []
    for skill in SKILLS:
        session = sessions.get(skill, {})
        attempt = attempts.get(skill, {})
        passed = int(attempt.get("pass_count") or 0)
        failed = int(attempt.get("fail_count") or 0)
        result.append(
            {
                "skill": skill,
                "session_count": int(session.get("session_count") or 0),
                "completed_session_count": int(session.get("completed_session_count") or 0),
                "attempt_count": int(attempt.get("attempt_count") or 0),
                "pass_count": passed,
                "fail_count": failed,
                "pending_review_count": int(attempt.get("pending_review_count") or 0),
                "resolved_pass_rate": round(passed / max(1, passed + failed), 6),
            }
        )
    return result


def render_html(report: Mapping[str, Any]) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(row['skill'].title())}</td>"
        f"<td>{row['completed_session_count']}/{row['session_count']}</td>"
        f"<td>{row['attempt_count']}</td><td>{row['pass_count']}</td>"
        f"<td>{row['fail_count']}</td><td>{row['pending_review_count']}</td></tr>"
        for row in report["four_skill_progress"]
    )
    alerts = "".join(f"<li>{html.escape(item)}</li>" for item in report["attention_items"]) or "<li>None</li>"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>A1FS Private Progress Report</title><style>body{{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #999;padding:.45rem;text-align:left}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:.75rem}}.card{{border:1px solid #aaa;padding:.8rem;border-radius:.4rem}}small{{color:#555}}</style></head><body><h1>A1/A1+ Four-Skill Progress</h1><p><strong>Learner:</strong> {html.escape(report['learner']['display_label'])}</p><p><small>Private local report · generated {html.escape(report['generated_at'])}</small></p><div class="grid"><div class="card"><strong>Mastery</strong><br>{report['mastery']['mastered_required_count']} / {report['mastery']['required_mastery_node_count']}</div><div class="card"><strong>Retention</strong><br>{report['retention']['retained_required_count']} / {report['retention']['required_mastery_node_count']}</div><div class="card"><strong>Open remediation</strong><br>{report['remediation']['open_count']}</div><div class="card"><strong>Due reviews</strong><br>{report['retention']['due_or_overdue_count']}</div></div><h2>Four skills</h2><table><thead><tr><th>Skill</th><th>Completed sessions</th><th>Attempts</th><th>Pass</th><th>Fail</th><th>Pending review</th></tr></thead><tbody>{rows}</tbody></table><h2>Attention</h2><ul>{alerts}</ul><p><strong>A2 lock:</strong> {html.escape(report['a2_lock']['state'])}; payload access remains denied.</p></body></html>"""


class DashboardExporter:
    def __init__(
        self,
        *,
        database_path: Path,
        graph_path: Path,
        m7_snapshot_path: Path,
        m8_snapshot_path: Path,
    ):
        self.database_path = Path(database_path)
        self.graph_path = Path(graph_path)
        self.m7_snapshot_path = Path(m7_snapshot_path)
        self.m8_snapshot_path = Path(m8_snapshot_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def sources(self) -> tuple[dict[str, Any], bytes, dict[str, Any], dict[str, Any]]:
        graph, graph_raw = load(self.graph_path, "graph")
        m7, _ = load(self.m7_snapshot_path, "m7")
        m8, _ = load(self.m8_snapshot_path, "m8")
        if graph.get("validation_status") != GRAPH_STATUS:
            raise DashboardError("graph_status_invalid")
        if m7.get("validation_status") != M7_STATUS:
            raise DashboardError("m7_status_invalid")
        if m8.get("validation_status") != M8_STATUS:
            raise DashboardError("m8_status_invalid")
        graph_sha = digest(graph_raw)
        if m7.get("source_graph_sha256") != graph_sha or m8.get("source_graph_sha256") != graph_sha:
            raise DashboardError("source_graph_binding_mismatch")
        if m8.get("source_m7_snapshot_digest") != digest(m7):
            raise DashboardError("m8_m7_binding_mismatch")
        if m7.get("learner_id") != m8.get("learner_id"):
            raise DashboardError("source_learner_mismatch")
        return graph, graph_raw, m7, m8

    def initialize(self) -> dict[str, Any]:
        _, graph_raw, m7, m8 = self.sources()
        with self.connect() as connection:
            connection.executescript(SQL)
            values = {
                "task_id": TASK_ID,
                "schema_version": SCHEMA_VERSION,
                "validation_status": STATUS,
                "source_graph_sha256": digest(graph_raw),
                "source_m7_snapshot_digest": digest(m7),
                "source_m8_snapshot_digest": digest(m8),
                "read_only_report": "true",
                "raw_response_exported": "false",
                "a2_payload_access_granted": "false",
                "next_short_step": NEXT_SHORT_STEP,
            }
            connection.executemany("INSERT OR REPLACE INTO m9_metadata VALUES(?,?)", values.items())
            connection.commit()
        return {
            "validation_status": STATUS,
            "learner_id": m7["learner_id"],
            "next_short_step": NEXT_SHORT_STEP,
        }

    def build(
        self,
        *,
        learner_id: str,
        output_root: Path,
        generated_at: str | None = None,
    ) -> dict[str, Any]:
        _, graph_raw, m7, m8 = self.sources()
        generated_at = timestamp(generated_at)
        if learner_id != m7["learner_id"]:
            raise DashboardError("learner_mismatch")
        with self.connect() as connection:
            metadata = dict(connection.execute("SELECT key,value FROM m9_metadata"))
            if metadata.get("validation_status") != STATUS or metadata.get("source_m8_snapshot_digest") != digest(m8):
                raise DashboardError("m9_not_initialized_for_sources")
            learner = connection.execute(
                "SELECT learner_id,display_label,locale,timezone_name,profile_state FROM learner_profiles WHERE learner_id=?",
                (learner_id,),
            ).fetchone()
            if not learner or learner["profile_state"] != "ACTIVE":
                raise DashboardError("learner_not_active")
            progress = skill_rows(connection, learner_id)
            pending_human = connection.execute(
                """SELECT COUNT(*) FROM response_attempts a JOIN scoring_results s USING(attempt_id)
                WHERE a.learner_id=? AND s.outcome IN('PENDING_HUMAN_REVIEW','HUMAN_DEFER')""",
                (learner_id,),
            ).fetchone()[0]
        open_remediation = [
            row for row in m7.get("remediation_assignments", [])
            if row.get("assignment_state") == "OPEN"
        ]
        pending_reassessment = [
            row for row in m7.get("reassessment_queue", [])
            if row.get("queue_state") == "PENDING"
        ]
        due_reviews = [
            row for row in m8.get("review_schedules", [])
            if row.get("schedule_state") in {"DUE", "OVERDUE"}
        ]
        attention: list[str] = []
        if pending_human:
            attention.append(f"{pending_human} response(s) require human review.")
        if open_remediation:
            attention.append(f"{len(open_remediation)} mastery node(s) require remediation.")
        if pending_reassessment:
            attention.append(f"{len(pending_reassessment)} reassessment item(s) are pending.")
        if due_reviews:
            attention.append(f"{len(due_reviews)} spaced review(s) are due or overdue.")
        report = {
            "task_id": TASK_ID,
            "schema_version": SCHEMA_VERSION,
            "validation_status": STATUS,
            "private_local_only": True,
            "generated_at": generated_at,
            "source_bindings": {
                "graph_sha256": digest(graph_raw),
                "m7_snapshot_digest": digest(m7),
                "m8_snapshot_digest": digest(m8),
            },
            "learner": dict(learner),
            "four_skill_progress": progress,
            "mastery": {
                "required_mastery_node_count": m7["required_mastery_node_count"],
                "mastered_required_count": m7["mastered_required_count"],
                "missing_mastery_count": len(m7["missing_mastery_node_ids"]),
            },
            "remediation": {
                "open_count": len(open_remediation),
                "pending_reassessment_count": len(pending_reassessment),
                "open_node_ids": sorted(row["node_id"] for row in open_remediation),
            },
            "retention": {
                "required_mastery_node_count": m8["required_mastery_node_count"],
                "retained_required_count": m8["retained_required_count"],
                "retention_confirmed": m8["retention_confirmed"],
                "due_or_overdue_count": len(due_reviews),
                "due_node_ids": sorted({row["node_id"] for row in due_reviews}),
            },
            "human_review": {"pending_count": pending_human},
            "attention_items": attention,
            "a2_lock": {
                "state": m7["a2_lock_state"],
                "payload_access_granted": False,
                "session_start_granted": False,
            },
            "privacy_boundaries": {
                "raw_response_text_exported": False,
                "prompt_text_exported": False,
                "public_delivery": False,
                "human_pilot_claimed": False,
            },
            "next_short_step": NEXT_SHORT_STEP,
        }
        root = Path(output_root)
        json_path = root / "a1fs_v1_m9_progress_report.private.json"
        html_path = root / "a1fs_v1_m9_progress_report.private.html"
        html_text = render_html(report)
        write_private(json_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        write_private(html_path, html_text)
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO dashboard_exports VALUES(?,?,?,?,?,?,?,?)",
                (
                    str(uuid.uuid4()), learner_id, generated_at, digest(graph_raw),
                    digest(m7), digest(m8), digest(report), digest(html_text),
                ),
            )
            connection.commit()
        return {
            "validation_status": STATUS,
            "json_path": str(json_path),
            "html_path": str(html_path),
            "report_sha256": digest(report),
            "html_sha256": digest(html_text),
            "next_short_step": NEXT_SHORT_STEP,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "build"):
        command = subcommands.add_parser(name)
        command.add_argument("--database", type=Path, required=True)
        command.add_argument("--graph", type=Path, required=True)
        command.add_argument("--m7-snapshot", type=Path, required=True)
        command.add_argument("--m8-snapshot", type=Path, required=True)
        if name == "build":
            command.add_argument("--learner-id", required=True)
            command.add_argument("--output-root", type=Path, required=True)
            command.add_argument("--generated-at")
    args = parser.parse_args()
    exporter = DashboardExporter(
        database_path=args.database,
        graph_path=args.graph,
        m7_snapshot_path=args.m7_snapshot,
        m8_snapshot_path=args.m8_snapshot,
    )
    result = exporter.initialize() if args.command == "init" else exporter.build(
        learner_id=args.learner_id,
        output_root=args.output_root,
        generated_at=args.generated_at,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
