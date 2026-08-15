#!/usr/bin/env python3
"""Project the active Unit01 474-item QuestionBank as reusable references.

U01QB19 is a read-only consumer adapter over the existing U01QB02/U01QB13
QuestionBank/exposure authority and the existing M7/M8 remediation, reassessment,
and spaced-review state.  It never copies learner items, opens a second bank,
changes selector quotas, authors questions, reads private_item_json, changes
answers/scoring, or unlocks Unit02/A2 content.

The projection answers one narrow question for downstream cumulative learning:
which existing canonical Unit01 item references are currently reusable, and for
which already-governed purpose?  Selection remains owned by U01QB02/U01QB13;
M7/M8 remain the learning-state authorities.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_m7_mastery_error_remediation_reassessment as m7
from ulga.builders import build_a1fs_v1_m8_review_scheduling_retention_spaced_practice as m8
from ulga.builders import build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02
from ulga.builders import build_a1fs_v1_u01qb12_unit01_reference_evidence_and_phrase_construction_partial_coverage_fullfix as u12
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u13

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Reads only canonical U01QB02 item identity and eligibility fields plus existing exposure, M7 reassessment, and M8 review state to project reusable references; creates no learner content, copied QuestionBank, answer or scoring authority, selector quota, planner, learner-state authority, Unit02 content, audio, or A2 unlock."

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB19_Unit01Canonical474CumulativeReuseReferenceProjection"
SCHEMA_VERSION = "a1fs.v1.u01qb19.unit01_canonical474_cumulative_reuse_reference_projection.v1"
PASS_STATUS = "PASS_A1FS_V1_U01QB19_UNIT01_CANONICAL474_CUMULATIVE_REUSE_REFERENCE_PROJECTION"
NEXT_SHORT_STEP = "A1FS-V1-U01QB19R1_Canonical474ReuseConsumerAcceptance"
EXPECTED_RUNTIME_ITEMS = u13.EXPECTED_RUNTIME_COUNT
EXPECTED_BASE_ITEMS = u12.EXPECTED_BASE_COUNT
EXPECTED_EXTENSION_ITEMS = u12.EXPECTED_EXTENSION_COUNT
RECENT_EXPOSURE_WINDOW = qb02.RECENT_EXPOSURE_WINDOW
REUSE_PURPOSES = (
    "REVIEW",
    "RETENTION",
    "REMEDIATION",
    "REASSESSMENT",
    "CROSS_UNIT_TRANSFER",
)


class ReuseProjectionError(ValueError):
    """Fail-closed U01QB19 projection error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _connect_read_only(database: Path) -> sqlite3.Connection:
    path = Path(database).resolve()
    if not path.is_file():
        raise ReuseProjectionError("LEARNER_DATABASE_MISSING")
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _required_table(connection: sqlite3.Connection, table: str) -> None:
    if not _table_exists(connection, table):
        raise ReuseProjectionError(f"REQUIRED_TABLE_MISSING:{table}")


def _catalog_rows(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    _required_table(connection, "u01qb02_item_catalog")
    rows = [
        dict(row)
        for row in connection.execute(
            """SELECT item_id,asset_key,lesson_id,skill,pattern_family_id,unit_pattern_id,
                      support_level,assessment_eligible,transfer_eligible,capture_enabled,item_digest
               FROM u01qb02_item_catalog ORDER BY item_id"""
        ).fetchall()
    ]
    if len(rows) != EXPECTED_RUNTIME_ITEMS:
        raise ReuseProjectionError(f"CANONICAL_RUNTIME_DENOMINATOR_INVALID:{len(rows)}")
    item_ids = [str(row["item_id"]) for row in rows]
    asset_keys = [str(row["asset_key"]) for row in rows]
    if len(set(item_ids)) != EXPECTED_RUNTIME_ITEMS:
        raise ReuseProjectionError("CANONICAL_ITEM_ID_NOT_UNIQUE")
    if len(set(asset_keys)) != EXPECTED_RUNTIME_ITEMS:
        raise ReuseProjectionError("CANONICAL_ASSET_KEY_NOT_UNIQUE")
    return rows


def _exposure_state(
    connection: sqlite3.Connection, learner_id: str
) -> tuple[set[str], set[str]]:
    if not _table_exists(connection, "u01qb02_item_exposures"):
        return set(), set()
    exposed = {
        str(row[0])
        for row in connection.execute(
            "SELECT DISTINCT item_id FROM u01qb02_item_exposures WHERE learner_id=?",
            (learner_id,),
        ).fetchall()
    }
    recent = {
        str(row[0])
        for row in connection.execute(
            """SELECT item_id FROM u01qb02_item_exposures
               WHERE learner_id=? ORDER BY exposure_seq DESC LIMIT ?""",
            (learner_id, RECENT_EXPOSURE_WINDOW),
        ).fetchall()
    }
    return exposed, recent


def _latest_failed_items(connection: sqlite3.Connection, learner_id: str) -> set[str]:
    required = ("response_attempts", "scoring_results", "u01qb02_item_catalog")
    if not all(_table_exists(connection, table) for table in required):
        return set()
    latest: dict[str, str] = {}
    for row in connection.execute(
        """SELECT c.item_id,r.outcome
           FROM response_attempts a
           JOIN scoring_results r USING(attempt_id)
           JOIN u01qb02_item_catalog c ON c.asset_key=a.asset_key
           WHERE a.learner_id=? ORDER BY a.rowid DESC""",
        (learner_id,),
    ).fetchall():
        latest.setdefault(str(row["item_id"]), str(row["outcome"]))
    return {item_id for item_id, outcome in latest.items() if outcome in qb02.FAIL_OUTCOMES}


def _pending_reassessment_asset_keys(connection: sqlite3.Connection, learner_id: str) -> set[str]:
    if not _table_exists(connection, "reassessment_queue"):
        return set()
    result: set[str] = set()
    for row in connection.execute(
        """SELECT asset_keys_json FROM reassessment_queue
           WHERE learner_id=? AND queue_state='PENDING'""",
        (learner_id,),
    ).fetchall():
        try:
            values = json.loads(str(row[0]))
        except json.JSONDecodeError as exc:
            raise ReuseProjectionError("M7_REASSESSMENT_ASSET_KEYS_INVALID") from exc
        if not isinstance(values, list):
            raise ReuseProjectionError("M7_REASSESSMENT_ASSET_KEYS_NOT_LIST")
        result.update(str(value) for value in values)
    return result


def _due_review_lessons(connection: sqlite3.Connection, learner_id: str) -> set[str]:
    """Resolve only M8 lesson-node schedules; capability-node selection stays with M8/M7."""
    if not _table_exists(connection, "review_schedules"):
        return set()
    lessons: set[str] = set()
    for row in connection.execute(
        """SELECT node_id FROM review_schedules
           WHERE learner_id=? AND schedule_state IN('DUE','OVERDUE')""",
        (learner_id,),
    ).fetchall():
        node_id = str(row[0])
        for skill in ("READING", "WRITING", "SPEAKING"):
            prefix = f"LESSON:{skill}:"
            if node_id.startswith(prefix):
                lessons.add(node_id[len(prefix):])
                break
    return lessons


def build_reuse_projection(database: Path, *, learner_id: str) -> dict[str, Any]:
    """Return the 474 canonical references without mutating any runtime/state table."""
    if not str(learner_id).strip():
        raise ReuseProjectionError("LEARNER_ID_REQUIRED")
    with _connect_read_only(database) as connection:
        rows = _catalog_rows(connection)
        exposed, recent = _exposure_state(connection, learner_id)
        failed = _latest_failed_items(connection, learner_id)
        reassessment_keys = _pending_reassessment_asset_keys(connection, learner_id)
        due_lessons = _due_review_lessons(connection, learner_id)

        catalog_item_ids = {str(row["item_id"]) for row in rows}
        catalog_asset_keys = {str(row["asset_key"]) for row in rows}
        if not exposed.issubset(catalog_item_ids):
            raise ReuseProjectionError("EXPOSURE_REFERENCES_NONCANONICAL_ITEM")
        if not reassessment_keys.issubset(catalog_asset_keys):
            raise ReuseProjectionError("M7_REASSESSMENT_REFERENCES_NONCANONICAL_ASSET")

        items: list[dict[str, Any]] = []
        purpose_counts = {purpose: 0 for purpose in REUSE_PURPOSES}
        for row in rows:
            item_id = str(row["item_id"])
            asset_key = str(row["asset_key"])
            lesson_id = str(row["lesson_id"])
            purposes: list[str] = []
            if item_id in exposed and item_id not in recent:
                purposes.append("REVIEW")
            if lesson_id in due_lessons and item_id in exposed:
                purposes.append("RETENTION")
            if item_id in failed:
                purposes.append("REMEDIATION")
            if asset_key in reassessment_keys:
                purposes.append("REASSESSMENT")
            if bool(row["transfer_eligible"]):
                purposes.append("CROSS_UNIT_TRANSFER")
            for purpose in purposes:
                purpose_counts[purpose] += 1
            items.append(
                {
                    "item_id": item_id,
                    "asset_key": asset_key,
                    "lesson_id": lesson_id,
                    "skill": str(row["skill"]),
                    "pattern_family_id": str(row["pattern_family_id"]),
                    "unit_pattern_id": str(row["unit_pattern_id"]),
                    "support_level": str(row["support_level"]),
                    "assessment_eligible": bool(row["assessment_eligible"]),
                    "transfer_eligible": bool(row["transfer_eligible"]),
                    "capture_enabled": bool(row["capture_enabled"]),
                    "item_digest": str(row["item_digest"]),
                    "reuse_purposes": purposes,
                }
            )

    identity = [
        {"item_id": row["item_id"], "asset_key": row["asset_key"], "item_digest": row["item_digest"]}
        for row in items
    ]
    return {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "unit_id": u12.UNIT_ID,
        "learner_id": learner_id,
        "canonical_item_count": len(items),
        "base_item_count": EXPECTED_BASE_ITEMS,
        "extension_item_count": EXPECTED_EXTENSION_ITEMS,
        "unique_canonical_item_count": len({row["item_id"] for row in items}),
        "canonical_identity_sha256": digest(identity),
        "reuse_mode": "REFERENCE_ONLY",
        "reuse_purpose_counts": purpose_counts,
        "items": items,
        "authority": {
            "canonical_item_authority": qb02.TASK_ID,
            "form_selection_authority": u13.TASK_ID,
            "mastery_remediation_reassessment_authority": m7.TASK_ID,
            "review_retention_authority": m8.TASK_ID,
        },
        "semantic_boundaries": {
            "question_authoring_performed": False,
            "canonical_id_mutation": False,
            "answer_read_or_mutation": False,
            "scoring_mutation": False,
            "selector_quota_mutation": False,
            "form_activity_authority_created": False,
            "parallel_questionbank_created": False,
            "parallel_learning_state_created": False,
            "unit02_content_created": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--learner-id", required=True)
    args = parser.parse_args(argv)
    value = build_reuse_projection(args.database, learner_id=args.learner_id)
    summary = {key: value[key] for key in (
        "validation_status", "canonical_item_count", "base_item_count",
        "extension_item_count", "unique_canonical_item_count", "reuse_mode",
        "reuse_purpose_counts", "semantic_boundaries", "next_short_step",
    )}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
