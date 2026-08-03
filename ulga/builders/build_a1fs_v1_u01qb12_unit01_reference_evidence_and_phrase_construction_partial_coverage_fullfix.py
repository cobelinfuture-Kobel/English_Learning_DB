#!/usr/bin/env python3
"""Close the remaining scored Unit01 QuestionBank partial task-angle coverage.

U01QB12 consumes the approved U01QB10 288-item revision and deterministically
replaces 24 partially supporting PF05 items with exact Reading reference-evidence
items and 12 partially supporting PF07 items with exact Writing phrase-construction
items. The base denominator remains 288 and the existing Real62 extension remains
186, so the active U01QB02 runtime remains exactly 474 items.

The same milestone also migrates the approved U01QB12 revision into the existing
U01QB02/M3/M6/Real62 SQLite runtime. Historical response contracts and attempts
for retired items are preserved. Any U01QB02 plan/exposure rows that reference a
retired item are archived before the active catalog rows are replaced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02
from ulga.builders import build_a1fs_v1_u01qb10_unit01_question_bank_production_angle_coverage_reconciliation as u01qb10
from ulga.builders import _u01qb11_runtime_migration_474_replay_impl as u01qb11

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB12_Unit01ReferenceEvidenceAndPhraseConstructionPartialCoverageFullFix"
SCHEMA_VERSION = "a1fs.v1.u01qb12.unit01_reference_evidence_phrase_construction_fullfix.v1"
PASS_STATUS = "PASS_A1FS_V1_U01QB12_UNIT01_REFERENCE_EVIDENCE_AND_PHRASE_CONSTRUCTION_PARTIAL_COVERAGE_FULLFIX"
DECISION_REF = "OPERATOR_APPROVAL:2026-08-03:U01QB12"
UNIT_ID = u01qb10.UNIT_ID
BANK_ID = u01qb10.BANK_ID
BANK_VERSION = u01qb10.BANK_VERSION
CANONICAL_REVISION = "U01QB12-R1"
EXPECTED_BASE_COUNT = 288
EXPECTED_EXTENSION_COUNT = 186
EXPECTED_RUNTIME_COUNT = 474
EXPECTED_RETIRED_COUNT = 36
EXPECTED_ADDED_COUNT = 36
EXPECTED_REFERENCE_EVIDENCE_COUNT = 24
EXPECTED_PHRASE_CONSTRUCTION_COUNT = 12
EXPECTED_SKILL_COUNTS = {"READING": 192, "SPEAKING": 87, "WRITING": 195}
EXPECTED_CAPTURE_ENABLED = 387
EXPECTED_AUTO_PASS_REPLAY = 351
EXPECTED_PENDING_HUMAN_REPLAY = 36
EXPECTED_SPEAKING_PRACTICE_ONLY = 87
PF16 = "U01-PF16-READING-REFERENCE-EVIDENCE"
PF17 = "U01-PF17-WRITING-PHRASE-CONSTRUCTION"
SOURCE_REFERENCE_FAMILY = "U01-PF05-KNOWN-REFERENCE-CONTEXT"
SOURCE_PHRASE_FAMILY = "U01-PF07-WORD-ORDER"
REFERENCE_SUPPORT_SEQUENCE = ("REDUCED_SUPPORT", "INDEPENDENT", "TRANSFER")
PHRASE_SUPPORT_SEQUENCE = ("GUIDED", "REDUCED_SUPPORT", "INDEPENDENT", "TRANSFER")
PHRASE_STRUCTURE_QUOTA = {"NOUN": 6, "ADJECTIVE": 4, "VERY": 2}
DEFAULT_CANDIDATE = Path("ulga/private/a1fs_v1_u01qb12_unit01_partial_coverage_fullfix.candidate.private.json")
DEFAULT_APPROVED = Path("ulga/private/a1fs_v1_u01qb12_unit01_partial_coverage_fullfix.approved.private.json")
DEFAULT_REPORT = Path("ulga/reports/a1fs_v1_u01qb12_unit01_partial_coverage_fullfix_474_replay.json")
NEXT_SHORT_STEP = "A1FS-V1-U01QB13_Unit01TwelveFormRuntimeSelectionAndAssessmentBlueprintIntegration"

ARCHIVE_SQL = """
CREATE TABLE IF NOT EXISTS u01qb12_retired_runtime_history(
  archive_seq INTEGER PRIMARY KEY AUTOINCREMENT,
  record_type TEXT NOT NULL CHECK(record_type IN ('SESSION_PLAN','SESSION_ITEM','ITEM_EXPOSURE')),
  record_key TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  archived_at TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  UNIQUE(record_type,record_key,payload_sha256)
);
CREATE TABLE IF NOT EXISTS u01qb12_metadata(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""


class PartialCoverageFullFixError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    if private:
        try:
            path.chmod(0o600)
        except OSError:
            pass


def _u01qb10_authority() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidate = u01qb10.build_candidate()
    approved = u01qb10.admit_candidate(candidate)
    from ulga.validators import validate_a1fs_v1_u01qb10_unit01_question_bank_production_angle_coverage_reconciliation as validator

    report = validator.validate_approved(candidate, approved)
    if report.get("error_count"):
        raise PartialCoverageFullFixError("U01QB10_AUTHORITY_INVALID:" + "|".join(report.get("errors") or []))
    rows = approved.get("payload", {}).get("reconciled_items")
    if not isinstance(rows, list) or len(rows) != EXPECTED_BASE_COUNT:
        raise PartialCoverageFullFixError("U01QB10_BASE_COUNT_INVALID")
    return approved, [deepcopy(dict(row)) for row in rows]


def _reference_sources(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_context: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in items:
        if row.get("pattern_family_id") == SOURCE_REFERENCE_FAMILY:
            by_context[str(row.get("context_id") or "")].append(deepcopy(dict(row)))
    for rows in by_context.values():
        rows.sort(key=lambda row: str(row["item_id"]))
    selected: list[dict[str, Any]] = []
    contexts = sorted(key for key in by_context if key)
    if not contexts:
        raise PartialCoverageFullFixError("REFERENCE_SOURCE_CONTEXTS_MISSING")
    cursor = 0
    while len(selected) < EXPECTED_REFERENCE_EVIDENCE_COUNT:
        progressed = False
        for context_id in contexts:
            rows = by_context[context_id]
            if cursor < len(rows):
                selected.append(rows[cursor])
                progressed = True
                if len(selected) == EXPECTED_REFERENCE_EVIDENCE_COUNT:
                    break
        if not progressed:
            break
        cursor += 1
    if len(selected) != EXPECTED_REFERENCE_EVIDENCE_COUNT:
        raise PartialCoverageFullFixError(f"REFERENCE_SOURCE_CAPACITY_INVALID:{len(selected)}")
    return selected


def _phrase_sources(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_structure: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in items:
        if row.get("pattern_family_id") == SOURCE_PHRASE_FAMILY:
            by_structure[str(row.get("candidate_structure") or "")].append(deepcopy(dict(row)))
    selected: list[dict[str, Any]] = []
    for structure, quota in PHRASE_STRUCTURE_QUOTA.items():
        rows = sorted(by_structure.get(structure, []), key=lambda row: str(row["item_id"]))
        if len(rows) < quota:
            raise PartialCoverageFullFixError(f"PHRASE_SOURCE_CAPACITY_INVALID:{structure}:{len(rows)}")
        selected.extend(rows[:quota])
    if len(selected) != EXPECTED_PHRASE_CONSTRUCTION_COUNT:
        raise PartialCoverageFullFixError(f"PHRASE_SOURCE_COUNT_INVALID:{len(selected)}")
    return selected


def _reference_evidence_item(source: Mapping[str, Any], ordinal: int) -> dict[str, Any]:
    slots = dict(source.get("lexical_slots") or {})
    noun = str(slots.get("noun") or "")
    context_id = str(source.get("context_id") or slots.get("context_id") or "")
    if not noun or context_id not in u01qb10.seed.CONTEXT_LOCATION:
        raise PartialCoverageFullFixError(f"REFERENCE_SOURCE_INVALID:{source.get('item_id')}")
    location = u01qb10.seed.CONTEXT_LOCATION[context_id]
    article = u01qb10.seed.article(noun)
    first_phrase = f"{article} {noun}"
    reference_phrase = f"the {noun}"
    support = REFERENCE_SUPPORT_SEQUENCE[(ordinal - 1) % len(REFERENCE_SUPPORT_SEQUENCE)]
    item = deepcopy(dict(source))
    item.update(
        {
            "item_id": f"U01QB12-{PF16}-{u01qb10.seed.slug(context_id)}-{u01qb10.seed.slug(noun)}",
            "pattern_family_id": PF16,
            "skill": "READING",
            "question_type": "reference_evidence",
            "task_angle": "REFERENCE_EVIDENCE",
            "prompt": f"Choose the words in sentence 2 that name the same {noun} again.",
            "stimulus": f"There is {first_phrase} {location}. The {noun} is easy to see.",
            "options": [first_phrase, reference_phrase],
            "correct_answer": reference_phrase,
            "accepted_answers": [reference_phrase],
            "scoring_mode": "EXACT_OPTION",
            "support_level": support,
            "learner_visible_capable": True,
            "learner_delivery_status": "NOT_RUNTIME_CONNECTED",
            "assessment_eligible": True,
            "reassessment_eligible": True,
            "transfer_eligible": support == "TRANSFER",
            "human_review_required": False,
            "audio_required": False,
            "speaking_capture_enabled": False,
            "runtime_generation_used": False,
            "response_contract": {
                "scoring_mode": "EXACT_OPTION",
                "response_type": "string",
                "accepted_texts": [reference_phrase],
                "accepted_sequence": [],
                "capture_enabled": True,
                "human_review_fallback": False,
                "rubric": {
                    "practice_only": False,
                    "reference_evidence_target": True,
                    "same_referent_required": True,
                },
            },
            "reconciliation_source_item_id": str(source["item_id"]),
            "admission_proposal": {
                "status": "AUTO_APPROVED",
                "reason_codes": ["U01QB12_REFERENCE_EVIDENCE_EXACT_SUPPORT_FULLFIX"],
            },
        }
    )
    refs = list(item.get("source_refs") or [])
    refs.append(
        {
            "source_type": "U01QB10_APPROVED_ITEM_RECONCILIATION",
            "source_item_id": str(source["item_id"]),
            "source_pattern_family_id": SOURCE_REFERENCE_FAMILY,
            "reconciliation_task_id": TASK_ID,
        }
    )
    item["source_refs"] = refs
    item["semantic_signature"] = digest(
        {
            "family": PF16,
            "context": context_id,
            "noun": noun,
            "prompt": item["prompt"],
            "stimulus": item["stimulus"],
            "options": item["options"],
            "answer": reference_phrase,
            "support": support,
        }
    )
    return item


def _phrase_construction_item(source: Mapping[str, Any], ordinal: int) -> dict[str, Any]:
    sequence = source.get("correct_answer")
    slots = dict(source.get("lexical_slots") or {})
    if not isinstance(sequence, list) or not sequence or not all(isinstance(token, str) and token for token in sequence):
        raise PartialCoverageFullFixError(f"PHRASE_SOURCE_SEQUENCE_INVALID:{source.get('item_id')}")
    model = " ".join(sequence)
    structure = str(source.get("candidate_structure") or "")
    noun = str(slots.get("noun") or "")
    adjective = str(slots.get("adjective") or "")
    support = PHRASE_SUPPORT_SEQUENCE[(ordinal - 1) % len(PHRASE_SUPPORT_SEQUENCE)]
    cue_parts = [f"noun: {noun}"]
    if adjective:
        cue_parts.insert(0, f"describing word: {adjective}")
    if structure == "VERY":
        cue_parts.insert(0, "use: very")
    cue_parts.insert(0, "use: a/an")
    item = deepcopy(dict(source))
    item.update(
        {
            "item_id": f"U01QB12-{PF17}-{u01qb10.seed.slug(str(source['item_id']))}",
            "pattern_family_id": PF17,
            "skill": "WRITING",
            "question_type": "phrase_construction",
            "task_angle": "PHRASE_CONSTRUCTION",
            "prompt": "Write the complete noun phrase from the cues.",
            "stimulus": " | ".join(cue_parts),
            "options": [],
            "correct_answer": model,
            "accepted_answers": [model],
            "scoring_mode": "NORMALIZED_TEXT",
            "support_level": support,
            "learner_visible_capable": True,
            "learner_delivery_status": "NOT_RUNTIME_CONNECTED",
            "assessment_eligible": True,
            "reassessment_eligible": True,
            "transfer_eligible": support == "TRANSFER",
            "human_review_required": False,
            "audio_required": False,
            "speaking_capture_enabled": False,
            "runtime_generation_used": False,
            "response_contract": {
                "scoring_mode": "NORMALIZED_TEXT",
                "response_type": "string",
                "accepted_texts": [model],
                "accepted_sequence": [],
                "capture_enabled": True,
                "human_review_fallback": False,
                "rubric": {
                    "practice_only": False,
                    "article_control_required": True,
                    "phrase_order_required": True,
                    "target_structure": structure,
                },
            },
            "reconciliation_source_item_id": str(source["item_id"]),
            "admission_proposal": {
                "status": "AUTO_APPROVED",
                "reason_codes": ["U01QB12_PHRASE_CONSTRUCTION_EXACT_SUPPORT_FULLFIX"],
            },
        }
    )
    refs = list(item.get("source_refs") or [])
    refs.append(
        {
            "source_type": "U01QB10_APPROVED_ITEM_RECONCILIATION",
            "source_item_id": str(source["item_id"]),
            "source_pattern_family_id": SOURCE_PHRASE_FAMILY,
            "reconciliation_task_id": TASK_ID,
        }
    )
    item["source_refs"] = refs
    item["semantic_signature"] = digest(
        {
            "family": PF17,
            "structure": structure,
            "slots": slots,
            "prompt": item["prompt"],
            "stimulus": item["stimulus"],
            "answer": model,
            "support": support,
        }
    )
    return item


def reconciled_payload() -> dict[str, Any]:
    approved_source, source_items = _u01qb10_authority()
    reference_sources = _reference_sources(source_items)
    phrase_sources = _phrase_sources(source_items)
    retired_ids = {str(row["item_id"]) for row in [*reference_sources, *phrase_sources]}
    retained = [deepcopy(dict(row)) for row in source_items if str(row["item_id"]) not in retired_ids]
    added = [
        *[_reference_evidence_item(row, index) for index, row in enumerate(reference_sources, start=1)],
        *[_phrase_construction_item(row, index) for index, row in enumerate(phrase_sources, start=1)],
    ]
    items = sorted([*retained, *added], key=lambda row: str(row["item_id"]))
    if len(retired_ids) != EXPECTED_RETIRED_COUNT or len(added) != EXPECTED_ADDED_COUNT:
        raise PartialCoverageFullFixError("COUNT_PRESERVATION_COMPONENT_INVALID")
    if len(items) != EXPECTED_BASE_COUNT:
        raise PartialCoverageFullFixError(f"RECONCILED_BASE_COUNT_INVALID:{len(items)}")
    if len({str(row["item_id"]) for row in items}) != EXPECTED_BASE_COUNT:
        raise PartialCoverageFullFixError("DUPLICATE_ITEM_ID")
    if len({str(row["semantic_signature"]) for row in items}) != EXPECTED_BASE_COUNT:
        raise PartialCoverageFullFixError("DUPLICATE_SEMANTIC_SIGNATURE")
    family_counts = dict(sorted(Counter(str(row["pattern_family_id"]) for row in items).items()))
    skill_counts = dict(sorted(Counter(str(row["skill"]) for row in items).items()))
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "bank_identity": {
            "bank_id": BANK_ID,
            "bank_version": BANK_VERSION,
            "canonical_revision": CANONICAL_REVISION,
            "supersedes_revision": u01qb10.CANONICAL_REVISION,
            "second_question_bank_created": False,
        },
        "source_identity": {
            "u01qb10_task_id": u01qb10.TASK_ID,
            "u01qb10_artifact_sha256": approved_source["artifact_sha256"],
            "u01qb10_base_item_count": len(source_items),
        },
        "count_preservation": {
            "source_base_count": len(source_items),
            "retained_base_count": len(retained),
            "retired_partial_support_count": len(retired_ids),
            "exact_support_items_added": len(added),
            "reconciled_base_count": len(items),
            "unchanged_real62_extension_count": EXPECTED_EXTENSION_COUNT,
            "projected_runtime_total_count": EXPECTED_RUNTIME_COUNT,
        },
        "replacement_plan": {
            "reading_reference_evidence": {
                "source_pattern_family_id": SOURCE_REFERENCE_FAMILY,
                "retired_count": len(reference_sources),
                "replacement_pattern_family_id": PF16,
                "source_item_ids": [str(row["item_id"]) for row in reference_sources],
            },
            "writing_phrase_construction": {
                "source_pattern_family_id": SOURCE_PHRASE_FAMILY,
                "retired_count": len(phrase_sources),
                "replacement_pattern_family_id": PF17,
                "source_item_ids": [str(row["item_id"]) for row in phrase_sources],
            },
        },
        "reconciled_items": items,
        "distribution_counts": {"family": family_counts, "skill": skill_counts},
        "scored_task_angle_coverage": {
            "scored_gap_count_after_u01qb10": 0,
            "scored_partial_support_before": 36,
            "reading_reference_evidence_partial_before": 24,
            "writing_phrase_construction_partial_before": 12,
            "reading_reference_evidence_exact_support_after": 24,
            "writing_phrase_construction_exact_support_after": 12,
            "scored_partial_support_after": 0,
            "remaining_scored_gap_angles": [],
            "remaining_scored_partial_angles": [],
            "scored_question_bank_full_alignment_ready": True,
            "speaking_practice_alignment_unchanged": True,
            "speaking_scoring_enabled": False,
        },
        "boundaries": {
            "new_scene_authored": False,
            "question_bank_total_expanded": False,
            "second_question_bank_created": False,
            "real62_extension_modified": False,
            "m3_learner_state_rewritten": False,
            "m6_attempts_or_scoring_deleted": False,
            "speaking_scoring_enabled": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    payload["reconciliation_sha256"] = policy_artifact.digest(payload)
    return payload


def build_candidate() -> dict[str, Any]:
    payload = reconciled_payload()
    return policy_artifact.build_candidate(
        payload=payload,
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings={
            "u01qb10_task_id": u01qb10.TASK_ID,
            "bank_id": BANK_ID,
            "bank_version": BANK_VERSION,
            "canonical_revision": CANONICAL_REVISION,
            "count_preserving": True,
            "operator_decision_ref": DECISION_REF,
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import validate_a1fs_v1_u01qb12_unit01_reference_evidence_and_phrase_construction_partial_coverage_fullfix as validator

    receipt = validator.validate_candidate(candidate)
    return policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[receipt],
        decision_ref=DECISION_REF,
        producer_id=TASK_ID,
    )


def approved_bank() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidate = build_candidate()
    approved = admit_candidate(candidate)
    from ulga.validators import validate_a1fs_v1_u01qb12_unit01_reference_evidence_and_phrase_construction_partial_coverage_fullfix as validator

    report = validator.validate_approved(candidate, approved)
    if report.get("error_count"):
        raise PartialCoverageFullFixError("U01QB12_APPROVED_INVALID:" + "|".join(report.get("errors") or []))
    rows = approved.get("payload", {}).get("reconciled_items")
    if not isinstance(rows, list) or len(rows) != EXPECTED_BASE_COUNT:
        raise PartialCoverageFullFixError("U01QB12_APPROVED_BASE_COUNT_INVALID")
    return approved, [deepcopy(dict(row)) for row in rows]


def _archive_affected_history(connection: sqlite3.Connection, retired_ids: set[str], *, archived_at: str) -> tuple[int, int]:
    if not retired_ids:
        return 0, 0
    placeholders = ",".join("?" for _ in retired_ids)
    ids = tuple(sorted(retired_ids))
    session_ids = {
        str(row[0])
        for row in connection.execute(
            f"SELECT DISTINCT session_id FROM u01qb02_session_items WHERE item_id IN ({placeholders})", ids
        )
    }
    session_ids.update(
        str(row[0])
        for row in connection.execute(
            f"SELECT DISTINCT session_id FROM u01qb02_item_exposures WHERE item_id IN ({placeholders})", ids
        )
    )
    archived = 0

    def archive(record_type: str, key: str, payload: Mapping[str, Any]) -> None:
        nonlocal archived
        raw = canonical(payload)
        connection.execute(
            """INSERT OR IGNORE INTO u01qb12_retired_runtime_history
            (record_type,record_key,payload_json,archived_at,payload_sha256) VALUES(?,?,?,?,?)""",
            (record_type, key, raw, archived_at, hashlib.sha256(raw.encode("utf-8")).hexdigest()),
        )
        archived += 1

    for session_id in sorted(session_ids):
        plan = connection.execute("SELECT * FROM u01qb02_session_plans WHERE session_id=?", (session_id,)).fetchone()
        if plan is not None:
            archive("SESSION_PLAN", session_id, dict(plan))
        for row in connection.execute("SELECT * FROM u01qb02_session_items WHERE session_id=? ORDER BY item_position", (session_id,)):
            archive("SESSION_ITEM", f"{session_id}:{row['item_position']}", dict(row))
        for row in connection.execute("SELECT * FROM u01qb02_item_exposures WHERE session_id=? ORDER BY exposure_seq", (session_id,)):
            archive("ITEM_EXPOSURE", str(row["exposure_id"]), dict(row))
    for session_id in sorted(session_ids):
        connection.execute("DELETE FROM u01qb02_item_exposures WHERE session_id=?", (session_id,))
        connection.execute("DELETE FROM u01qb02_session_items WHERE session_id=?", (session_id,))
        connection.execute("DELETE FROM u01qb02_session_plans WHERE session_id=?", (session_id,))
    return len(session_ids), archived


def migrate_runtime(database: Path) -> dict[str, Any]:
    database = Path(database)
    prerequisite = u01qb11.migrate_runtime(database)
    approved, desired_items = approved_bank()
    desired_by_id = {str(row["item_id"]): row for row in desired_items}
    desired_ids = set(desired_by_id)
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(database)
    archived_at = utc_now()
    with runtime.write() as connection:
        connection.row_factory = sqlite3.Row
        for table in (
            "metadata", "lesson_catalog", "lesson_assets", "response_contracts", "response_attempts",
            "scoring_results", "u01qb02_metadata", "u01qb02_item_catalog", "u01qb02_session_plans",
            "u01qb02_session_items", "u01qb02_item_exposures", "razq01e_metadata", "razq01e_extension_items",
        ):
            u01qb11._require_table(connection, table)
        connection.executescript(ARCHIVE_SQL)
        extension_before = u01qb11._extension_snapshot(connection)
        extension_ids = set(extension_before["item_ids"])
        current_ids = {
            str(row[0])
            for row in connection.execute("SELECT item_id FROM u01qb02_item_catalog ORDER BY item_id")
        }
        current_base_ids = current_ids - extension_ids
        already_migrated = current_base_ids == desired_ids and len(current_ids) == EXPECTED_RUNTIME_COUNT
        if already_migrated:
            retired_ids: set[str] = set()
            missing_ids: set[str] = set()
            affected_session_count = 0
            archived_record_count = 0
        else:
            if len(current_base_ids) != EXPECTED_BASE_COUNT or len(current_ids) != EXPECTED_RUNTIME_COUNT:
                raise PartialCoverageFullFixError(
                    f"PRE_MIGRATION_DENOMINATOR_INVALID:{len(current_base_ids)}:{len(current_ids)}"
                )
            retired_ids = current_base_ids - desired_ids
            missing_ids = desired_ids - current_base_ids
            if len(retired_ids) != EXPECTED_RETIRED_COUNT or len(missing_ids) != EXPECTED_ADDED_COUNT:
                raise PartialCoverageFullFixError(f"U01QB12_DELTA_INVALID:{len(retired_ids)}:{len(missing_ids)}")
            affected_session_count, archived_record_count = _archive_affected_history(
                connection, retired_ids, archived_at=archived_at
            )
            placeholders = ",".join("?" for _ in retired_ids)
            connection.execute(
                f"DELETE FROM u01qb02_item_catalog WHERE item_id IN ({placeholders})",
                tuple(sorted(retired_ids)),
            )
            for item_id in sorted(missing_ids):
                u01qb11._register_base_item(connection, desired_by_id[item_id])
        for item_id, item in desired_by_id.items():
            row = connection.execute("SELECT item_digest FROM u01qb02_item_catalog WHERE item_id=?", (item_id,)).fetchone()
            if row is None or str(row["item_digest"]) != qb02.digest(item):
                raise PartialCoverageFullFixError(f"RECONCILED_BASE_IDENTITY_INVALID:{item_id}")
        extension_after = u01qb11._extension_snapshot(connection)
        if extension_after["identity_sha256"] != extension_before["identity_sha256"]:
            raise PartialCoverageFullFixError("REAL62_EXTENSION_IDENTITY_CHANGED")
        total = int(connection.execute("SELECT COUNT(*) FROM u01qb02_item_catalog").fetchone()[0])
        extension_count = int(connection.execute("SELECT COUNT(*) FROM razq01e_extension_items").fetchone()[0])
        base_count = total - extension_count
        if (base_count, extension_count, total) != (EXPECTED_BASE_COUNT, EXPECTED_EXTENSION_COUNT, EXPECTED_RUNTIME_COUNT):
            raise PartialCoverageFullFixError(f"POST_MIGRATION_DENOMINATOR_INVALID:{base_count}:{extension_count}:{total}")
        combined_sha = digest(
            {
                "base_question_bank_artifact_sha256": approved["artifact_sha256"],
                "content_extension_artifact_sha256": extension_after["artifact_sha256"],
            }
        )
        connection.executemany(
            "INSERT OR REPLACE INTO u01qb02_metadata(key,value) VALUES(?,?)",
            {
                "base_source_bank_artifact_sha256": str(approved["artifact_sha256"]),
                "source_bank_artifact_sha256": combined_sha,
                "approved_item_count": str(EXPECTED_BASE_COUNT),
                "razq01e_extension_artifact_sha256": str(extension_after["artifact_sha256"]),
                "razq01e_extension_item_count": str(EXPECTED_EXTENSION_COUNT),
                "razq01e_combined_runtime_item_count": str(EXPECTED_RUNTIME_COUNT),
                "u01qb12_task_id": TASK_ID,
                "u01qb12_schema_version": SCHEMA_VERSION,
                "u01qb12_validation_status": PASS_STATUS,
                "u01qb12_base_revision": CANONICAL_REVISION,
                "u01qb12_next_short_step": NEXT_SHORT_STEP,
            }.items(),
        )
        connection.executemany(
            "INSERT OR REPLACE INTO razq01e_metadata(key,value) VALUES(?,?)",
            {
                "base_item_count": str(EXPECTED_BASE_COUNT),
                "combined_runtime_item_count": str(EXPECTED_RUNTIME_COUNT),
                "base_source_bank_artifact_sha256": str(approved["artifact_sha256"]),
                "combined_source_bank_sha256": combined_sha,
            }.items(),
        )
        connection.executemany(
            "INSERT OR REPLACE INTO u01qb12_metadata(key,value) VALUES(?,?)",
            {
                "task_id": TASK_ID,
                "schema_version": SCHEMA_VERSION,
                "validation_status": PASS_STATUS,
                "base_revision": CANONICAL_REVISION,
                "base_artifact_sha256": str(approved["artifact_sha256"]),
                "extension_artifact_sha256": str(extension_after["artifact_sha256"]),
                "combined_source_bank_sha256": combined_sha,
                "base_item_count": str(base_count),
                "extension_item_count": str(extension_count),
                "runtime_item_count": str(total),
                "next_short_step": NEXT_SHORT_STEP,
            }.items(),
        )
    return {
        "validation_status": PASS_STATUS,
        "database": str(database),
        "prerequisite_u01qb11": prerequisite,
        "already_migrated": already_migrated,
        "retired_partial_support_item_count": len(retired_ids),
        "exact_support_item_added_count": len(missing_ids),
        "affected_session_count": affected_session_count,
        "archived_runtime_history_record_count": archived_record_count,
        "base_item_count": EXPECTED_BASE_COUNT,
        "extension_item_count": EXPECTED_EXTENSION_COUNT,
        "combined_runtime_item_count": EXPECTED_RUNTIME_COUNT,
        "u01qb12_artifact_sha256": str(approved["artifact_sha256"]),
        "real62_extension_artifact_sha256": extension_after["artifact_sha256"],
        "real62_extension_identity_sha256": extension_after["identity_sha256"],
        "combined_source_bank_sha256": combined_sha,
        "m3_learner_state_rewritten": False,
        "m6_attempts_or_scoring_deleted": False,
        "historical_retired_response_contracts_preserved": True,
        "next_short_step": NEXT_SHORT_STEP,
    }


def replay_474(database: Path) -> dict[str, Any]:
    replay = u01qb11.replay_474(database)
    with sqlite3.connect(database) as connection:
        family_counts = dict(
            connection.execute(
                "SELECT pattern_family_id,COUNT(*) FROM u01qb02_item_catalog GROUP BY pattern_family_id"
            ).fetchall()
        )
    if family_counts.get(PF16) != EXPECTED_REFERENCE_EVIDENCE_COUNT:
        raise PartialCoverageFullFixError(f"PF16_RUNTIME_COUNT_INVALID:{family_counts.get(PF16)}")
    if family_counts.get(PF17) != EXPECTED_PHRASE_CONSTRUCTION_COUNT:
        raise PartialCoverageFullFixError(f"PF17_RUNTIME_COUNT_INVALID:{family_counts.get(PF17)}")
    if replay["runtime_item_count"] != EXPECTED_RUNTIME_COUNT:
        raise PartialCoverageFullFixError("REPLAY_RUNTIME_COUNT_INVALID")
    if replay["skill_distribution"] != EXPECTED_SKILL_COUNTS:
        raise PartialCoverageFullFixError("REPLAY_SKILL_DISTRIBUTION_INVALID")
    if (
        replay["capture_enabled_item_count"] != EXPECTED_CAPTURE_ENABLED
        or replay["deterministic_auto_pass_replay_count"] != EXPECTED_AUTO_PASS_REPLAY
        or replay["feature_rubric_pending_human_replay_count"] != EXPECTED_PENDING_HUMAN_REPLAY
        or replay["speaking_practice_only_count"] != EXPECTED_SPEAKING_PRACTICE_ONLY
    ):
        raise PartialCoverageFullFixError("REPLAY_OUTCOME_DENOMINATOR_INVALID")
    core = {
        **replay,
        "exact_support_family_counts": {PF16: family_counts[PF16], PF17: family_counts[PF17]},
        "scored_partial_support_after": 0,
        "scored_question_bank_full_alignment_ready": True,
    }
    unsigned = dict(core)
    unsigned.pop("replay_sha256", None)
    core["replay_sha256"] = digest(unsigned)
    return core


def _attempt_family(database: Path, *, family: str, skill: str, learner_id: str, session_id: str) -> dict[str, Any]:
    state = m3.LearnerStateStore(database)
    try:
        profile = state.create_profile(learner_id=learner_id, display_label="U01QB12 Disposable Exact Support Canary")
    except m3.StateStoreError as exc:
        if "learner_profile_exists" not in str(exc):
            raise
        profile = state.profile_snapshot(learner_id)
    lesson_id = qb02.UNIT01_LESSONS[skill]
    with sqlite3.connect(database) as connection:
        active = connection.execute(
            "SELECT session_id,session_version FROM learning_sessions WHERE learner_id=? AND session_state='ACTIVE'",
            (learner_id,),
        ).fetchone()
    if active is not None:
        state.end_session(session_id=str(active[0]), outcome="ABANDONED", expected_session_version=int(active[1]))
    state.start_session(
        learner_id=learner_id,
        lesson_id=lesson_id,
        session_id=session_id,
        expected_profile_version=int(profile["profile"]["profile_version"]),
    )
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT item_id,asset_key,private_item_json FROM u01qb02_item_catalog WHERE pattern_family_id=? ORDER BY item_id LIMIT 1",
            (family,),
        ).fetchone()
    if row is None:
        raise PartialCoverageFullFixError(f"CANARY_FAMILY_MISSING:{family}")
    snapshot = state.session_snapshot(session_id)
    exposed = state.record_exposure(
        session_id=session_id,
        asset_key=str(row["asset_key"]),
        expected_session_version=int(snapshot["session_version"]),
    )
    private_item = json.loads(str(row["private_item_json"]))
    attempted = m6.ResponseEvidenceStore(database).capture_response(
        learner_id=learner_id,
        session_id=session_id,
        asset_key=str(row["asset_key"]),
        response=private_item["correct_answer"],
        expected_session_version=int(exposed["session_version"]),
    )
    final_snapshot = state.session_snapshot(session_id)
    state.end_session(
        session_id=session_id,
        outcome="COMPLETED",
        expected_session_version=int(final_snapshot["session_version"]),
    )
    if attempted["outcome"] != "AUTO_PASS":
        raise PartialCoverageFullFixError(f"CANARY_OUTCOME_INVALID:{family}:{attempted['outcome']}")
    return {
        "family": family,
        "skill": skill,
        "item_id": str(row["item_id"]),
        "attempt_id": str(attempted["attempt_id"]),
        "outcome": str(attempted["outcome"]),
        "m3_exposure_authority_reused": True,
        "m6_response_capture_reused": True,
        "m6_scoring_authority_reused": True,
    }


def exact_support_attempt_canary(database: Path) -> dict[str, Any]:
    results = [
        _attempt_family(
            database,
            family=PF16,
            skill="READING",
            learner_id="u01qb12-reference-canary",
            session_id="u01qb12-reference-session",
        ),
        _attempt_family(
            database,
            family=PF17,
            skill="WRITING",
            learner_id="u01qb12-phrase-canary",
            session_id="u01qb12-phrase-session",
        ),
    ]
    return {
        "attempt_count": len(results),
        "results": results,
        "all_auto_pass": all(row["outcome"] == "AUTO_PASS" for row in results),
        "speaking_capture_or_scoring_used": False,
    }


def run_acceptance(database: Path, *, run_attempt_canary: bool = True) -> dict[str, Any]:
    candidate = build_candidate()
    approved = admit_candidate(candidate)
    from ulga.validators import validate_a1fs_v1_u01qb12_unit01_reference_evidence_and_phrase_construction_partial_coverage_fullfix as validator

    approval_report = validator.validate_approved(candidate, approved)
    if approval_report["error_count"]:
        raise PartialCoverageFullFixError("APPROVED_VALIDATION_FAILED:" + "|".join(approval_report["errors"]))
    migration = migrate_runtime(database)
    replay = replay_474(database)
    canary = exact_support_attempt_canary(database) if run_attempt_canary else {"executed": False}
    core = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "approved_artifact_sha256": approved["artifact_sha256"],
        "approval_validation": approval_report,
        "migration": migration,
        "replay_474": replay,
        "exact_support_attempt_canary": canary,
        "coverage_closeout": {
            "reading_reference_evidence": "FULL",
            "writing_phrase_construction": "FULL",
            "scored_gap_count": 0,
            "scored_partial_support_count": 0,
            "scored_question_bank_full_alignment_ready": True,
            "speaking_practice_alignment_unchanged": True,
        },
        "boundaries": {
            "question_bank_total_expanded": False,
            "second_question_bank_created": False,
            "existing_u01qb02_runtime_reused": True,
            "existing_real62_extension_reused": True,
            "m3_learner_state_rewritten": False,
            "m6_attempts_or_scoring_deleted": False,
            "speaking_scoring_enabled": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    return {**core, "readback_sha256": digest(core)}


def materialize(*, candidate_path: Path, approved_path: Path, report_path: Path, database: Path | None = None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidate = build_candidate()
    approved = admit_candidate(candidate)
    from ulga.validators import validate_a1fs_v1_u01qb12_unit01_reference_evidence_and_phrase_construction_partial_coverage_fullfix as validator

    approval_report = validator.validate_approved(candidate, approved)
    if approval_report["error_count"]:
        raise PartialCoverageFullFixError("APPROVED_VALIDATION_FAILED:" + "|".join(approval_report["errors"]))
    report = run_acceptance(database, run_attempt_canary=True) if database is not None else {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "approved_artifact_sha256": approved["artifact_sha256"],
        "approval_validation": approval_report,
        "runtime_acceptance_executed": False,
        "next_short_step": NEXT_SHORT_STEP,
    }
    write_json(candidate_path, candidate, private=True)
    write_json(approved_path, approved, private=True)
    write_json(report_path, report)
    return candidate, approved, report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--approved", type=Path, default=DEFAULT_APPROVED)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--database", type=Path)
    args = parser.parse_args(argv)
    try:
        _, approved, report = materialize(
            candidate_path=args.candidate.resolve(),
            approved_path=args.approved.resolve(),
            report_path=args.report.resolve(),
            database=args.database.resolve() if args.database else None,
        )
        if args.database:
            from ulga.validators import validate_a1fs_v1_u01qb12_unit01_reference_evidence_and_phrase_construction_partial_coverage_fullfix as validator
            validator.validate_report(report)
    except (
        PartialCoverageFullFixError,
        policy_artifact.ContentPolicyBuildError,
        u01qb11.RuntimeMigrationError,
        m3.StateStoreError,
        m6.ResponseEvidenceError,
        sqlite3.Error,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB12_UNIT01_REFERENCE_EVIDENCE_AND_PHRASE_CONSTRUCTION_PARTIAL_COVERAGE_FULLFIX")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={PASS_STATUS}")
    print(f"BASE_COUNT={approved['payload']['count_preservation']['reconciled_base_count']}")
    print(f"PROJECTED_RUNTIME_TOTAL={approved['payload']['count_preservation']['projected_runtime_total_count']}")
    print(f"SCORED_PARTIAL_SUPPORT_AFTER={approved['payload']['scored_task_angle_coverage']['scored_partial_support_after']}")
    print(f"RUNTIME_ACCEPTANCE_EXECUTED={bool(args.database)}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
