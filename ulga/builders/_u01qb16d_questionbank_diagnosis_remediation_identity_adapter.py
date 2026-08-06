"""Enrich canonical M7 diagnosis/remediation with Unit01 QuestionBank identity.

M7 remains the only mastery, diagnosis, remediation and reassessment authority.
This adapter supplies deterministic Unit01 QuestionBank metadata for failed
attempts so M7 can distinguish first-mention article errors, a/an sound-choice
errors, known-reference errors, reference-evidence errors, word-order errors and
sentence-production errors instead of reducing every auto-scored failure to the
generic ``response_mismatch`` tag.

No answer, score, mastery state, remediation queue identity, learner attempt or
QuestionBank content is rewritten. The adapter only enriches M7's existing error
tags and strategy selection while its snapshot is being built. Context-local
state is used so concurrent learner snapshots cannot leak diagnostic metadata.
"""
from __future__ import annotations

import contextvars
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_m7_mastery_error_remediation_reassessment as m7

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Diagnostic identity adapter over existing U01QB item/attempt metadata and the canonical M7 engine; creates no content, answers, scoring, mastery engine, learner attempt, QuestionBank mutation, Unit02-24 content, audio, speaking scoring, or A2 unlock."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB16D_Unit01QuestionBankErrorDiagnosisAndRemediationIdentityClosure"
PASS_STATUS = "PASS_A1FS_V1_U01QB16D_UNIT01_QUESTIONBANK_ERROR_DIAGNOSIS_AND_REMEDIATION_IDENTITY_CLOSURE"
NEXT_SHORT_STEP = "A1FS-V1-U01QB16E_Unit01LearnerVisibleLanguageNaturalnessQualityReconciliation"

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
        if learner_answer in {"a", "an"} and correct_answer in {"a", "an"} and learner_answer != correct_answer:
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
            """SELECT a.attempt_id,a.response_json,c.item_id,c.pattern_family_id,c.private_item_json
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
        correct_answer = _json_scalar(json.dumps(item.get("correct_answer"), ensure_ascii=False))
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
    identity = _ATTEMPT_DIAGNOSTIC_CONTEXT.get({}).get(str(row.get("attempt_id") or ""))
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
        return _ORIGINAL_BUILD_SNAPSHOT(
            self,
            learner_id=learner_id,
            output_root=output_root,
            created_at=created_at,
        )
    finally:
        _ATTEMPT_DIAGNOSTIC_CONTEXT.reset(token)


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
