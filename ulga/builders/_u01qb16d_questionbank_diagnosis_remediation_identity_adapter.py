"""Enrich canonical M7 diagnosis/remediation with exact Unit01 QuestionBank identity.

M7 remains the only mastery, diagnosis, remediation and reassessment authority.
This adapter adds two bounded capabilities over the existing M7 path:

1. enrich M7 diagnosis tags/strategies with the failed Unit01 QuestionBank item
   identity, so a/an, first-mention, known-reference, reference-evidence,
   phrase/order and sentence-production failures are not collapsed to a generic
   ``response_mismatch``; and
2. after M7 builds its canonical diagnosis/remediation/reassessment state,
   materialize an auditable link from that diagnosis back to the exact U01QB13
   activity/task angle/capability and nominate a different existing QuestionBank
   item with a different learner-visible signature for reassessment.

No answer, score, mastery state, M7 queue identity, learner attempt, QuestionBank
content, Unit02-24 content, audio, Speaking score or A2 state is rewritten.
"""
from __future__ import annotations

import contextvars
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import _u01qb16_learner_visible_distinctness_adapter as u16
from ulga.builders import _u01qb16b_task_angle_progression_adapter as u16b
from ulga.builders import build_a1fs_v1_m7_mastery_error_remediation_reassessment as m7
from ulga.builders import (
    build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration
    as u13,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Diagnostic/lineage adapter over existing Unit01 QuestionBank attempts, "
    "U01QB13 bindings and canonical M7 diagnosis/remediation/reassessment state; "
    "it enriches tags and records a different existing-item reassessment "
    "candidate without creating content, answers, scoring, mastery policy, a "
    "parallel remediation engine, Unit02-24 content, audio, Speaking scoring or "
    "A2 unlock."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB16D_Unit01QuestionBankErrorDiagnosisAndRemediationIdentityClosure"
PASS_STATUS = "PASS_A1FS_V1_U01QB16D_UNIT01_QUESTIONBANK_ERROR_DIAGNOSIS_AND_REMEDIATION_IDENTITY_CLOSURE"
NEXT_SHORT_STEP = "A1FS-V1-U01QB16E_Unit01DifferentItemReassessmentConsumerIntegration"

_ORIGINAL_DIAGNOSTIC_TAGS = m7._diagnostic_tags
_ORIGINAL_STRATEGY = m7._strategy
_ORIGINAL_BUILD_SNAPSHOT = m7.MasteryRemediationEngine.build_snapshot
_ATTEMPT_DIAGNOSTIC_CONTEXT: contextvars.ContextVar[dict[str, dict[str, Any]]] = (
    contextvars.ContextVar("a1fs_u01qb16d_attempt_diagnostic_context", default={})
)
_INSTALLED = False

PF_FIRST_MENTION = {
    "U01-PF01-AAN-NOUN-GAP",
    "U01-PF02-AAN-ADJ-NOUN-GAP",
    "U01-PF03-VERY-ADJ-NOUN-GAP",
    "U01-PF04-FIRST-MENTION-CONTEXT",
    "U01-PF08-TRANSFER-FIRST-MENTION",
}
PF_KNOWN_REFERENCE = {
    "U01-PF05-KNOWN-REFERENCE-CONTEXT",
    "U01-PF09-TRANSFER-KNOWN-REFERENCE",
}
PF_ERROR_DISCRIMINATION = {
    "U01-PF06-ERROR-DISCRIMINATION",
    "U01-PF13-ERROR-CORRECTION-PRODUCTION",
}
PF_WORD_ORDER = {
    "U01-PF07-WORD-ORDER",
    "U01-PF17-PHRASE-CONSTRUCTION-PRODUCTION",
}
PF_REFERENCE_EVIDENCE = {"U01-PF16-REFERENCE-EVIDENCE"}
PF_COMPLETE_SENTENCE = {"U01-PF14-COMPLETE-SENTENCE-PRODUCTION"}
PF_CONNECTED_SENTENCE = {"U01-PF15-CONNECTED-SENTENCE-PRODUCTION"}

METADATA_TABLE = "u01qb16d_metadata"
LINK_TABLE = "u01qb16d_diagnosis_remediation_links"
LINK_SQL = f"""
CREATE TABLE IF NOT EXISTS {METADATA_TABLE}(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS {LINK_TABLE}(
  diagnosis_id TEXT PRIMARY KEY,
  learner_id TEXT NOT NULL,
  attempt_id TEXT NOT NULL,
  item_id TEXT NOT NULL,
  activity_id TEXT NOT NULL,
  form_ordinal INTEGER NOT NULL,
  skill TEXT NOT NULL,
  task_angle TEXT NOT NULL,
  capability_class TEXT NOT NULL,
  targeted_error_tag TEXT NOT NULL,
  targeted_remediation_strategy TEXT NOT NULL,
  remediation_ids_json TEXT NOT NULL,
  reassessment_ids_json TEXT NOT NULL,
  failed_learner_visible_signature TEXT NOT NULL,
  different_item_id TEXT,
  different_asset_key TEXT,
  different_learner_visible_signature TEXT,
  candidate_state TEXT NOT NULL CHECK(candidate_state IN('READY','NO_DISTINCT_CANDIDATE')),
  link_digest TEXT NOT NULL UNIQUE
);
"""


class QuestionBankDiagnosisIdentityError(ValueError):
    pass


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _json_scalar(raw: Any) -> str:
    try:
        value = json.loads(str(raw))
    except (TypeError, json.JSONDecodeError):
        value = raw
    if isinstance(value, str):
        return " ".join(value.casefold().split())
    if isinstance(value, (int, float, bool)):
        return str(value).casefold()
    return ""


def _private_item(raw: Any) -> Mapping[str, Any]:
    try:
        value = json.loads(str(raw))
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, Mapping) else {}


def _identity_tags(
    *,
    pattern_family_id: str,
    learner_answer: str,
    correct_answer: str,
    item: Mapping[str, Any],
) -> list[str]:
    tags = ["u01_questionbank_attempt"]
    family = str(pattern_family_id)
    if family in PF_FIRST_MENTION:
        tags.append("u01_first_mention_article_control")
        if (
            learner_answer in {"a", "an"}
            and correct_answer in {"a", "an"}
            and learner_answer != correct_answer
        ):
            tags.append("u01_a_an_sound_choice_error")
        elif learner_answer == "the" and correct_answer in {"a", "an"}:
            tags.append("u01_first_mention_definiteness_error")
    elif family in PF_KNOWN_REFERENCE:
        tags.append("u01_known_reference_control")
        if learner_answer in {"a", "an"} and correct_answer == "the":
            tags.append("u01_known_reference_definiteness_error")
    elif family in PF_REFERENCE_EVIDENCE:
        tags.append("u01_reference_evidence_control")
    elif family in PF_ERROR_DISCRIMINATION:
        tags.append("u01_article_error_discrimination")
    elif family in PF_WORD_ORDER:
        tags.append("u01_article_noun_phrase_order")
    elif family in PF_COMPLETE_SENTENCE:
        tags.append("u01_complete_sentence_production")
    elif family in PF_CONNECTED_SENTENCE:
        tags.append("u01_connected_sentence_production")

    for target in item.get("grammar_target_ids") or []:
        normalized = "_".join(str(target).casefold().split())
        if normalized:
            tags.append("grammar_target_" + normalized)
    return sorted(set(tags))


def attempt_diagnostic_identity_map(
    database_path: Path,
    *,
    learner_id: str,
) -> dict[str, dict[str, Any]]:
    database_path = Path(database_path)
    if not database_path.is_file():
        return {}
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        required = {"response_attempts", "u01qb02_item_catalog"}
        if not all(_table_exists(connection, table) for table in required):
            return {}
        rows = connection.execute(
            """SELECT a.attempt_id,a.response_json,c.item_id,c.pattern_family_id,
                      c.private_item_json
               FROM response_attempts a
               JOIN u01qb02_item_catalog c ON c.asset_key=a.asset_key
               WHERE a.learner_id=?
               ORDER BY a.attempt_id""",
            (learner_id,),
        ).fetchall()

    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = _private_item(row["private_item_json"])
        learner_answer = _json_scalar(row["response_json"])
        correct_answer = _json_scalar(
            json.dumps(item.get("correct_answer"), ensure_ascii=False)
        )
        result[str(row["attempt_id"])] = {
            "item_id": str(row["item_id"]),
            "pattern_family_id": str(row["pattern_family_id"]),
            "tags": _identity_tags(
                pattern_family_id=str(row["pattern_family_id"]),
                learner_answer=learner_answer,
                correct_answer=correct_answer,
                item=item,
            ),
        }
    return result


def diagnostic_tags(row: Mapping[str, Any]) -> list[str]:
    tags = list(_ORIGINAL_DIAGNOSTIC_TAGS(row))
    identity = _ATTEMPT_DIAGNOSTIC_CONTEXT.get({}).get(
        str(row.get("attempt_id") or "")
    )
    if identity:
        tags.extend(str(tag) for tag in identity.get("tags") or [])
    return sorted(set(tags))


def strategy(tags: set[str]) -> str:
    tags = set(tags)
    if "u01_a_an_sound_choice_error" in tags:
        return "RETEACH_A_AN_SOUND_CHOICE_WITH_MINIMAL_PAIRS"
    if "u01_first_mention_definiteness_error" in tags:
        return "RETEACH_FIRST_MENTION_A_AN_VS_THE_WITH_CONTRAST"
    if "u01_known_reference_definiteness_error" in tags:
        return "RETEACH_FIRST_TO_REPEATED_REFERENCE_WITH_CONTRAST"
    if "u01_reference_evidence_control" in tags:
        return "REBUILD_REFERENCE_EVIDENCE_THEN_RETRY"
    if "u01_article_error_discrimination" in tags:
        return "RETEACH_ARTICLE_ERROR_CONTRAST_AND_RETRY"
    if "u01_article_noun_phrase_order" in tags:
        return "REBUILD_ARTICLE_NOUN_PHRASE_WITH_GUIDED_ORDER"
    if "u01_connected_sentence_production" in tags:
        return "MODEL_FIRST_TO_REPEATED_REFERENCE_PAIR_THEN_RETRY"
    if "u01_complete_sentence_production" in tags:
        return "MODEL_COMPLETE_ARTICLE_NOUN_SENTENCE_THEN_RETRY"
    if "u01_known_reference_control" in tags:
        return "RETEACH_KNOWN_REFERENCE_THE_THEN_RETRY"
    if "u01_first_mention_article_control" in tags:
        return "RETEACH_FIRST_MENTION_ARTICLE_THEN_RETRY"
    return _ORIGINAL_STRATEGY(tags)


def _targeted_identity_tag(tags: list[str]) -> str:
    priority = (
        "u01_a_an_sound_choice_error",
        "u01_first_mention_definiteness_error",
        "u01_known_reference_definiteness_error",
        "u01_reference_evidence_control",
        "u01_article_error_discrimination",
        "u01_article_noun_phrase_order",
        "u01_connected_sentence_production",
        "u01_complete_sentence_production",
        "u01_known_reference_control",
        "u01_first_mention_article_control",
    )
    tag_set = set(tags)
    return next((tag for tag in priority if tag in tag_set), "u01_questionbank_attempt")


def _lineage_ready(connection: sqlite3.Connection) -> bool:
    return all(
        _table_exists(connection, table)
        for table in (
            "response_attempts",
            "u01qb02_item_catalog",
            "u01qb13_blueprint_activities",
            "u01qb13_session_bindings",
            "error_diagnoses",
            "remediation_assignments",
            "reassessment_queue",
        )
    )


def _diagnosis_rows(
    connection: sqlite3.Connection, *, learner_id: str
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """SELECT d.diagnosis_id,d.node_ids_json,a.attempt_id,a.session_id,
                  a.asset_key,a.response_json,c.item_id,c.skill,c.pattern_family_id,
                  c.support_level,c.capture_enabled,c.private_item_json,
                  b.activity_id,p.form_ordinal,p.task_angle,p.pattern_family_ids_json
           FROM error_diagnoses d
           JOIN response_attempts a ON a.attempt_id=d.attempt_id
           JOIN u01qb02_item_catalog c ON c.asset_key=a.asset_key
           JOIN u01qb13_session_bindings b
             ON b.session_id=a.session_id AND b.item_id=c.item_id
           JOIN u01qb13_blueprint_activities p ON p.activity_id=b.activity_id
           WHERE d.learner_id=?
           ORDER BY d.diagnosis_id""",
        (learner_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _m7_queue_ids(
    connection: sqlite3.Connection,
    *,
    learner_id: str,
    node_ids_json: str,
) -> tuple[list[str], list[str]]:
    try:
        node_ids = [str(value) for value in json.loads(str(node_ids_json))]
    except json.JSONDecodeError as exc:
        raise QuestionBankDiagnosisIdentityError("M7_DIAGNOSIS_NODE_IDS_INVALID") from exc
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
    return sorted(set(remediation_ids)), sorted(set(reassessment_ids))


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
        families = (str(failed["pattern_family_id"]),)
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
    exposed: set[str] = set()
    if _table_exists(connection, "u01qb02_item_exposures"):
        exposed = {
            str(row[0])
            for row in connection.execute(
                "SELECT DISTINCT item_id FROM u01qb02_item_exposures WHERE learner_id=?",
                (learner_id,),
            ).fetchall()
        }
    return sorted(
        (dict(row) for row in rows),
        key=lambda row: (
            str(row["item_id"]) in exposed,
            str(row["support_level"]) != str(failed["support_level"]),
            str(row["item_id"]),
        ),
    )


def _different_item_candidate(
    connection: sqlite3.Connection,
    *,
    learner_id: str,
    failed: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    failed_signature = u16.learner_visible_signature(failed)
    for row in _candidate_rows(connection, learner_id=learner_id, failed=failed):
        signature = u16.learner_visible_signature(row)
        if signature != failed_signature:
            return row, signature
    return None, None


def materialize_diagnosis_remediation_links(
    database_path: Path,
    *,
    learner_id: str,
) -> dict[str, Any]:
    database_path = Path(database_path)
    if not database_path.is_file():
        return {
            "validation_status": PASS_STATUS,
            "action": "SKIP_DATABASE_MISSING",
            "diagnosis_link_count": 0,
        }
    identities = attempt_diagnostic_identity_map(database_path, learner_id=learner_id)
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        if not _lineage_ready(connection):
            return {
                "validation_status": PASS_STATUS,
                "action": "SKIP_U01QB13_OR_M7_LINEAGE_NOT_READY",
                "diagnosis_link_count": 0,
            }
        connection.executescript(LINK_SQL)
        diagnosis_rows = _diagnosis_rows(connection, learner_id=learner_id)
        diagnosis_ids = [str(row["diagnosis_id"]) for row in diagnosis_rows]
        if diagnosis_ids:
            placeholders = ",".join("?" for _ in diagnosis_ids)
            connection.execute(
                f"DELETE FROM {LINK_TABLE} WHERE diagnosis_id IN ({placeholders})",
                tuple(diagnosis_ids),
            )

        ready_count = 0
        unresolved_count = 0
        for row in diagnosis_rows:
            attempt_id = str(row["attempt_id"])
            identity = identities.get(attempt_id, {"tags": ["u01_questionbank_attempt"]})
            tags = [str(tag) for tag in identity.get("tags") or []]
            capability = u16b.capability_class(str(row["skill"]), str(row["task_angle"]))
            failed_signature = u16.learner_visible_signature(row)
            candidate, candidate_signature = _different_item_candidate(
                connection,
                learner_id=learner_id,
                failed=row,
            )
            state = "READY" if candidate is not None else "NO_DISTINCT_CANDIDATE"
            if candidate is None:
                unresolved_count += 1
            else:
                ready_count += 1
            remediation_ids, reassessment_ids = _m7_queue_ids(
                connection,
                learner_id=learner_id,
                node_ids_json=str(row["node_ids_json"]),
            )
            core = {
                "diagnosis_id": str(row["diagnosis_id"]),
                "learner_id": learner_id,
                "attempt_id": attempt_id,
                "item_id": str(row["item_id"]),
                "activity_id": str(row["activity_id"]),
                "form_ordinal": int(row["form_ordinal"]),
                "skill": str(row["skill"]),
                "task_angle": str(row["task_angle"]),
                "capability_class": capability,
                "targeted_error_tag": _targeted_identity_tag(tags),
                "targeted_remediation_strategy": strategy(set(tags)),
                "remediation_ids": remediation_ids,
                "reassessment_ids": reassessment_ids,
                "failed_learner_visible_signature": failed_signature,
                "different_item_id": None if candidate is None else str(candidate["item_id"]),
                "different_asset_key": None if candidate is None else str(candidate["asset_key"]),
                "different_learner_visible_signature": candidate_signature,
                "candidate_state": state,
            }
            connection.execute(
                f"""INSERT INTO {LINK_TABLE} VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    core["diagnosis_id"],
                    learner_id,
                    attempt_id,
                    core["item_id"],
                    core["activity_id"],
                    core["form_ordinal"],
                    core["skill"],
                    core["task_angle"],
                    capability,
                    core["targeted_error_tag"],
                    core["targeted_remediation_strategy"],
                    json.dumps(remediation_ids, separators=(",", ":")),
                    json.dumps(reassessment_ids, separators=(",", ":")),
                    failed_signature,
                    core["different_item_id"],
                    core["different_asset_key"],
                    candidate_signature,
                    state,
                    m7.digest(core),
                ),
            )

        metadata = {
            "task_id": TASK_ID,
            "validation_status": PASS_STATUS,
            "learner_id_scope": learner_id,
            "diagnosis_link_count": str(len(diagnosis_rows)),
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
        "diagnosis_link_count": len(diagnosis_rows),
        "different_item_candidate_ready_count": ready_count,
        "different_item_candidate_unresolved_count": unresolved_count,
        "questionbank_modified": False,
        "scoring_modified": False,
        "a2_unlocked": False,
        "next_short_step": NEXT_SHORT_STEP,
    }


def reassessment_candidate(
    database_path: Path,
    *,
    diagnosis_id: str,
) -> dict[str, Any] | None:
    with sqlite3.connect(Path(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        if not _table_exists(connection, LINK_TABLE):
            return None
        row = connection.execute(
            f"""SELECT different_item_id,different_asset_key,capability_class,
                       targeted_error_tag,targeted_remediation_strategy,
                       candidate_state,different_learner_visible_signature
                FROM {LINK_TABLE} WHERE diagnosis_id=?""",
            (diagnosis_id,),
        ).fetchone()
        return dict(row) if row else None


def build_snapshot(
    self,
    *,
    learner_id: str,
    output_root: Path,
    created_at: str | None = None,
):
    identity_map = attempt_diagnostic_identity_map(
        self.database_path,
        learner_id=learner_id,
    )
    token = _ATTEMPT_DIAGNOSTIC_CONTEXT.set(identity_map)
    try:
        result = _ORIGINAL_BUILD_SNAPSHOT(
            self,
            learner_id=learner_id,
            output_root=output_root,
            created_at=created_at,
        )
    finally:
        _ATTEMPT_DIAGNOSTIC_CONTEXT.reset(token)
    links = materialize_diagnosis_remediation_links(
        self.database_path,
        learner_id=learner_id,
    )
    return {**result, "u01qb16d_identity": links}


def install() -> None:
    """Install idempotently into the existing M7 authority implementation."""
    global _INSTALLED
    if (
        m7._diagnostic_tags is diagnostic_tags
        and m7._strategy is strategy
        and m7.MasteryRemediationEngine.build_snapshot is build_snapshot
    ):
        _INSTALLED = True
        return
    if m7._diagnostic_tags is not _ORIGINAL_DIAGNOSTIC_TAGS:
        raise QuestionBankDiagnosisIdentityError("M7_DIAGNOSTIC_TAGS_ALREADY_PATCHED")
    if m7._strategy is not _ORIGINAL_STRATEGY:
        raise QuestionBankDiagnosisIdentityError("M7_REMEDIATION_STRATEGY_ALREADY_PATCHED")
    if m7.MasteryRemediationEngine.build_snapshot is not _ORIGINAL_BUILD_SNAPSHOT:
        raise QuestionBankDiagnosisIdentityError("M7_BUILD_SNAPSHOT_ALREADY_PATCHED")
    m7._diagnostic_tags = diagnostic_tags
    m7._strategy = strategy
    m7.MasteryRemediationEngine.build_snapshot = build_snapshot
    _INSTALLED = True


def installed() -> bool:
    return (
        _INSTALLED
        and m7._diagnostic_tags is diagnostic_tags
        and m7._strategy is strategy
        and m7.MasteryRemediationEngine.build_snapshot is build_snapshot
    )
