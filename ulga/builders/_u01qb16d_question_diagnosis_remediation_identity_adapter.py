"""Bind Unit01 QuestionBank attempts to canonical M7 diagnosis/remediation identities.

U01QB16D does not create a second diagnosis, remediation, reassessment, scoring,
or learner-state engine. M6/M7 remain authoritative. This adapter materializes
an auditable Unit01 identity bridge after the existing M7 snapshot is built:

question item -> U01QB13 activity/task angle -> pedagogical capability ->
M7 diagnosis -> M7 remediation/reassessment -> different-item candidate.

The bridge is count-preserving and content-preserving. It never changes the
474-item QuestionBank, completed attempts, scores, M7 mastery policy, Unit02-24,
Speaking scoring, audio, or A2 state.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import _u01qb16_learner_visible_distinctness_adapter as u16
from ulga.builders import _u01qb16b_task_angle_progression_adapter as u16b
from ulga.builders import build_a1fs_v1_m7_mastery_error_remediation_reassessment as m7
from ulga.builders import (
    build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration
    as u13,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Deterministic lineage bridge from existing Unit01 M6 failures and U01QB13 "
    "question bindings into the existing M7 diagnosis/remediation/reassessment "
    "identities, plus a different-item reassessment candidate chosen only from "
    "the existing QuestionBank. No learner content, score, mastery policy, "
    "QuestionBank item, Unit02-24 content, audio, Speaking score, or A2 state is "
    "created or mutated."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB16D_Unit01QuestionBankErrorDiagnosisAndRemediationIdentityClosure"
PASS_STATUS = "PASS_A1FS_V1_U01QB16D_UNIT01_QUESTIONBANK_ERROR_DIAGNOSIS_REMEDIATION_IDENTITY_CLOSURE"
NEXT_SHORT_STEP = "A1FS-V1-U01QB16E_Unit01DifferentItemReassessmentConsumerIntegration"
FAIL_OUTCOMES = frozenset({"AUTO_FAIL", "HUMAN_REJECT"})

METADATA_TABLE = "u01qb16d_metadata"
ATTEMPT_TABLE = "u01qb16d_attempt_identity"
LINK_TABLE = "u01qb16d_diagnosis_remediation_links"

SQL = f"""
CREATE TABLE IF NOT EXISTS {METADATA_TABLE}(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS {ATTEMPT_TABLE}(
  attempt_id TEXT PRIMARY KEY,
  learner_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  item_id TEXT NOT NULL,
  asset_key TEXT NOT NULL,
  activity_id TEXT NOT NULL,
  form_ordinal INTEGER NOT NULL,
  skill TEXT NOT NULL,
  task_angle TEXT NOT NULL,
  capability_class TEXT NOT NULL,
  support_level TEXT NOT NULL,
  pattern_family_ids_json TEXT NOT NULL,
  learner_visible_signature TEXT NOT NULL,
  identity_digest TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS {LINK_TABLE}(
  diagnosis_id TEXT PRIMARY KEY,
  attempt_id TEXT NOT NULL,
  item_id TEXT NOT NULL,
  activity_id TEXT NOT NULL,
  capability_class TEXT NOT NULL,
  targeted_error_tag TEXT NOT NULL,
  targeted_remediation_strategy TEXT NOT NULL,
  remediation_ids_json TEXT NOT NULL,
  reassessment_ids_json TEXT NOT NULL,
  different_item_id TEXT,
  different_asset_key TEXT,
  different_learner_visible_signature TEXT,
  candidate_state TEXT NOT NULL CHECK(candidate_state IN('READY','NO_DISTINCT_CANDIDATE')),
  link_digest TEXT NOT NULL UNIQUE
);
"""


class DiagnosisIdentityError(ValueError):
    pass


_ERROR_TAG = {
    u16b.FIRST_MENTION_SELECTION: "article_first_mention_selection_error",
    u16b.KNOWN_REFERENCE_USE: "known_reference_use_error",
    u16b.ERROR_DISCRIMINATION: "error_discrimination_error",
    u16b.REFERENCE_EVIDENCE: "reference_evidence_error",
    "PHRASE_CONSTRUCTION": "phrase_construction_error",
    "WORD_ORDER": "word_order_error",
    "CONTEXTUAL_REFERENCE_GAP": "contextual_reference_error",
    "ERROR_CHECK": "error_discrimination_error",
    "COMPLETE_SENTENCE_PRODUCTION": "complete_sentence_production_error",
    "CONNECTED_SENTENCE_PRODUCTION": "connected_sentence_production_error",
}

_REMEDIATION_STRATEGY = {
    u16b.FIRST_MENTION_SELECTION: "RETEACH_ARTICLE_FIRST_MENTION_WITH_CONTRAST",
    u16b.KNOWN_REFERENCE_USE: "RETEACH_KNOWN_REFERENCE_WITH_MINIMAL_PAIRS",
    u16b.ERROR_DISCRIMINATION: "COMPARE_CORRECT_AND_INCORRECT_ARTICLE_REFERENCE",
    u16b.REFERENCE_EVIDENCE: "TRACE_FIRST_AND_REPEAT_MENTION_EVIDENCE",
    "PHRASE_CONSTRUCTION": "REBUILD_ARTICLE_NOUN_PHRASE",
    "WORD_ORDER": "REBUILD_SENTENCE_WITH_GUIDED_ORDER",
    "CONTEXTUAL_REFERENCE_GAP": "RECONTEXTUALIZE_REFERENCE_AND_RETRY",
    "ERROR_CHECK": "COMPARE_CORRECT_AND_INCORRECT_ARTICLE_REFERENCE",
    "COMPLETE_SENTENCE_PRODUCTION": "MODEL_COMPLETE_SENTENCE_THEN_RETRY",
    "CONNECTED_SENTENCE_PRODUCTION": "MODEL_FIRST_AND_REPEAT_MENTION_PAIR",
}

_ORIGINAL_BUILD_SNAPSHOT = m7.MasteryRemediationEngine.build_snapshot
_INSTALLED = False


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _required_tables_present(connection: sqlite3.Connection) -> bool:
    return all(
        _table_exists(connection, table)
        for table in (
            "response_attempts",
            "scoring_results",
            "u01qb02_item_catalog",
            "u01qb13_blueprint_activities",
            "u01qb13_session_bindings",
            "error_diagnoses",
            "remediation_assignments",
            "reassessment_queue",
        )
    )


def _targeted_error_tag(capability: str) -> str:
    return _ERROR_TAG.get(capability, f"task_capability_{capability.casefold()}_error")


def _targeted_strategy(capability: str) -> str:
    return _REMEDIATION_STRATEGY.get(capability, "RETEACH_TARGET_WITH_CONTRAST_AND_RETRY")


def _failed_attempts(connection: sqlite3.Connection, learner_id: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        """SELECT r.attempt_id,r.learner_id,r.session_id,r.asset_key,s.outcome,
                  c.item_id,c.skill,c.private_item_json,
                  b.activity_id,a.form_ordinal,a.task_angle,a.support_level,
                  a.pattern_family_ids_json
           FROM response_attempts r
           JOIN scoring_results s USING(attempt_id)
           JOIN u01qb02_item_catalog c ON c.asset_key=r.asset_key
           JOIN u01qb13_session_bindings b
             ON b.session_id=r.session_id AND b.item_id=c.item_id
           JOIN u01qb13_blueprint_activities a ON a.activity_id=b.activity_id
           WHERE r.learner_id=? AND s.outcome IN ('AUTO_FAIL','HUMAN_REJECT')
           ORDER BY r.attempt_id""",
        (learner_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _candidate_rows(
    connection: sqlite3.Connection,
    *,
    learner_id: str,
    failed: Mapping[str, Any],
) -> list[dict[str, Any]]:
    skill = str(failed["skill"]).upper()
    angle = str(failed["task_angle"])
    families = tuple(u13.EXACT_SCORED_BINDINGS.get((skill, angle), ()))
    if not families:
        return []
    placeholders = ",".join("?" for _ in families)
    rows = connection.execute(
        f"""SELECT item_id,asset_key,skill,pattern_family_id,support_level,
                   capture_enabled,private_item_json
            FROM u01qb02_item_catalog
            WHERE skill=? AND capture_enabled=1
              AND pattern_family_id IN ({placeholders})
              AND item_id<>?
            ORDER BY item_id""",
        (skill, *families, str(failed["item_id"])),
    ).fetchall()
    exposed = {
        str(row[0])
        for row in connection.execute(
            "SELECT DISTINCT item_id FROM u01qb02_item_exposures WHERE learner_id=?",
            (learner_id,),
        ).fetchall()
    } if _table_exists(connection, "u01qb02_item_exposures") else set()
    return sorted(
        (dict(row) for row in rows),
        key=lambda row: (
            str(row["item_id"]) in exposed,
            str(row["support_level"]) != str(failed["support_level"]),
            str(row["item_id"]),
        ),
    )


def _distinct_candidate(
    connection: sqlite3.Connection,
    *,
    learner_id: str,
    failed: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    failed_signature = u16.learner_visible_signature(failed)
    for row in _candidate_rows(connection, learner_id=learner_id, failed=failed):
        signature = u16.learner_visible_signature(row)
        if signature == failed_signature:
            continue
        return row, signature
    return None, None


def _m7_links(connection: sqlite3.Connection, *, learner_id: str, attempt_id: str) -> list[dict[str, Any]]:
    diagnoses = [
        dict(row)
        for row in connection.execute(
            "SELECT diagnosis_id,node_ids_json FROM error_diagnoses WHERE learner_id=? AND attempt_id=? ORDER BY diagnosis_id",
            (learner_id, attempt_id),
        ).fetchall()
    ]
    result: list[dict[str, Any]] = []
    for diagnosis in diagnoses:
        try:
            node_ids = [str(value) for value in json.loads(str(diagnosis["node_ids_json"]))]
        except json.JSONDecodeError as exc:
            raise DiagnosisIdentityError(f"M7_DIAGNOSIS_NODE_IDS_INVALID:{diagnosis['diagnosis_id']}") from exc
        remediation_ids: list[str] = []
        reassessment_ids: list[str] = []
        for node_id in node_ids:
            row = connection.execute(
                "SELECT remediation_id FROM remediation_assignments WHERE learner_id=? AND node_id=?",
                (learner_id, node_id),
            ).fetchone()
            if row:
                remediation_ids.append(str(row[0]))
            row = connection.execute(
                "SELECT reassessment_id FROM reassessment_queue WHERE learner_id=? AND node_id=?",
                (learner_id, node_id),
            ).fetchone()
            if row:
                reassessment_ids.append(str(row[0]))
        result.append(
            {
                "diagnosis_id": str(diagnosis["diagnosis_id"]),
                "remediation_ids": sorted(set(remediation_ids)),
                "reassessment_ids": sorted(set(reassessment_ids)),
            }
        )
    return result


def materialize(database: Path, *, learner_id: str) -> dict[str, Any]:
    database = Path(database)
    if not database.is_file():
        return {"validation_status": PASS_STATUS, "action": "SKIP_DATABASE_MISSING", "link_count": 0}
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        if not _required_tables_present(connection):
            return {"validation_status": PASS_STATUS, "action": "SKIP_U01QB_RUNTIME_NOT_READY", "link_count": 0}
        connection.executescript(SQL)
        failed_rows = _failed_attempts(connection, learner_id)
        connection.execute(f"DELETE FROM {ATTEMPT_TABLE} WHERE learner_id=?", (learner_id,))
        diagnosis_ids = [
            str(row[0])
            for row in connection.execute(
                "SELECT diagnosis_id FROM error_diagnoses WHERE learner_id=?", (learner_id,)
            ).fetchall()
        ]
        if diagnosis_ids:
            placeholders = ",".join("?" for _ in diagnosis_ids)
            connection.execute(
                f"DELETE FROM {LINK_TABLE} WHERE diagnosis_id IN ({placeholders})",
                tuple(diagnosis_ids),
            )

        link_count = 0
        ready_count = 0
        unresolved_count = 0
        for failed in failed_rows:
            capability = u16b.capability_class(str(failed["skill"]), str(failed["task_angle"]))
            visible_signature = u16.learner_visible_signature(failed)
            identity_core = {
                "attempt_id": str(failed["attempt_id"]),
                "learner_id": learner_id,
                "session_id": str(failed["session_id"]),
                "item_id": str(failed["item_id"]),
                "asset_key": str(failed["asset_key"]),
                "activity_id": str(failed["activity_id"]),
                "form_ordinal": int(failed["form_ordinal"]),
                "skill": str(failed["skill"]),
                "task_angle": str(failed["task_angle"]),
                "capability_class": capability,
                "support_level": str(failed["support_level"]),
                "pattern_family_ids": json.loads(str(failed["pattern_family_ids_json"])),
                "learner_visible_signature": visible_signature,
            }
            connection.execute(
                f"""INSERT INTO {ATTEMPT_TABLE}
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    identity_core["attempt_id"],
                    learner_id,
                    identity_core["session_id"],
                    identity_core["item_id"],
                    identity_core["asset_key"],
                    identity_core["activity_id"],
                    identity_core["form_ordinal"],
                    identity_core["skill"],
                    identity_core["task_angle"],
                    capability,
                    identity_core["support_level"],
                    json.dumps(identity_core["pattern_family_ids"], separators=(",", ":")),
                    visible_signature,
                    m7.digest(identity_core),
                ),
            )
            candidate, candidate_signature = _distinct_candidate(
                connection, learner_id=learner_id, failed=failed
            )
            state = "READY" if candidate is not None else "NO_DISTINCT_CANDIDATE"
            if candidate is not None:
                ready_count += 1
            else:
                unresolved_count += 1
            for links in _m7_links(
                connection, learner_id=learner_id, attempt_id=str(failed["attempt_id"])
            ):
                link_core = {
                    "diagnosis_id": links["diagnosis_id"],
                    "attempt_id": str(failed["attempt_id"]),
                    "item_id": str(failed["item_id"]),
                    "activity_id": str(failed["activity_id"]),
                    "capability_class": capability,
                    "targeted_error_tag": _targeted_error_tag(capability),
                    "targeted_remediation_strategy": _targeted_strategy(capability),
                    "remediation_ids": links["remediation_ids"],
                    "reassessment_ids": links["reassessment_ids"],
                    "different_item_id": None if candidate is None else str(candidate["item_id"]),
                    "different_asset_key": None if candidate is None else str(candidate["asset_key"]),
                    "different_learner_visible_signature": candidate_signature,
                    "candidate_state": state,
                }
                connection.execute(
                    f"""INSERT INTO {LINK_TABLE}
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        link_core["diagnosis_id"],
                        link_core["attempt_id"],
                        link_core["item_id"],
                        link_core["activity_id"],
                        capability,
                        link_core["targeted_error_tag"],
                        link_core["targeted_remediation_strategy"],
                        json.dumps(link_core["remediation_ids"], separators=(",", ":")),
                        json.dumps(link_core["reassessment_ids"], separators=(",", ":")),
                        link_core["different_item_id"],
                        link_core["different_asset_key"],
                        link_core["different_learner_visible_signature"],
                        state,
                        m7.digest(link_core),
                    ),
                )
                link_count += 1

        metadata = {
            "task_id": TASK_ID,
            "validation_status": PASS_STATUS,
            "learner_id_scope": learner_id,
            "failed_attempt_identity_count": str(len(failed_rows)),
            "diagnosis_link_count": str(link_count),
            "different_item_candidate_ready_count": str(ready_count),
            "different_item_candidate_unresolved_count": str(unresolved_count),
            "m7_authority_reused": "true",
            "questionbank_modified": "false",
            "scoring_modified": "false",
            "unit02_to_unit24_modified": "false",
            "speaking_scoring_enabled": "false",
            "a2_unlocked": "false",
            "next_short_step": NEXT_SHORT_STEP,
        }
        connection.executemany(
            f"INSERT OR REPLACE INTO {METADATA_TABLE}(key,value) VALUES(?,?)",
            metadata.items(),
        )
        connection.commit()
    return {
        "validation_status": PASS_STATUS,
        "action": "MATERIALIZED",
        "failed_attempt_identity_count": len(failed_rows),
        "link_count": link_count,
        "different_item_candidate_ready_count": ready_count,
        "different_item_candidate_unresolved_count": unresolved_count,
        "questionbank_modified": False,
        "scoring_modified": False,
        "a2_unlocked": False,
        "next_short_step": NEXT_SHORT_STEP,
    }


def reassessment_candidate(database: Path, *, diagnosis_id: str) -> dict[str, Any] | None:
    with sqlite3.connect(Path(database)) as connection:
        connection.row_factory = sqlite3.Row
        if not _table_exists(connection, LINK_TABLE):
            return None
        row = connection.execute(
            f"""SELECT different_item_id,different_asset_key,capability_class,
                       candidate_state,different_learner_visible_signature
                FROM {LINK_TABLE} WHERE diagnosis_id=?""",
            (diagnosis_id,),
        ).fetchone()
        return dict(row) if row else None


def build_snapshot_with_u01qb16d_identity(self, *, learner_id: str, output_root: Path, created_at: str | None = None):
    result = _ORIGINAL_BUILD_SNAPSHOT(
        self, learner_id=learner_id, output_root=output_root, created_at=created_at
    )
    identity = materialize(self.database_path, learner_id=learner_id)
    return {**result, "u01qb16d_identity": identity}


def install() -> None:
    global _INSTALLED
    current = m7.MasteryRemediationEngine.build_snapshot
    if current is build_snapshot_with_u01qb16d_identity:
        _INSTALLED = True
        return
    if current is not _ORIGINAL_BUILD_SNAPSHOT:
        raise DiagnosisIdentityError("M7_BUILD_SNAPSHOT_ALREADY_PATCHED_BY_OTHER_AUTHORITY")
    m7.MasteryRemediationEngine.build_snapshot = build_snapshot_with_u01qb16d_identity
    _INSTALLED = True


def installed() -> bool:
    return _INSTALLED and m7.MasteryRemediationEngine.build_snapshot is build_snapshot_with_u01qb16d_identity
