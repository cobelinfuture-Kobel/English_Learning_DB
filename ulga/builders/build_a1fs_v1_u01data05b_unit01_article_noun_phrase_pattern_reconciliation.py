#!/usr/bin/env python3
"""Reconcile Unit01 activity patterns to article noun-phrase targets.

The current U01E S01/S03 lineage broadcasts two demonstrative clause patterns
(`SP_000016` / `SP_000017`) to every Unit01 activity. Unit01 teaches articles
inside noun phrases; `This is` is only a formulaic carrier and demonstratives
are not assessed. This builder produces a metadata-only corrective overlay.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Reconciles existing Unit01 activity metadata to unit-local article noun-phrase "
    "patterns. It creates no learner text, question, answer, score, state, audio, A2 "
    "target, global Pattern Authority mutation, or parallel curriculum."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = (
    "A1FS-V1-U01DATA05B_"
    "Unit01ArticleNounPhrasePatternAuthorityReconciliationFullFix"
)
SCHEMA_VERSION = "a1fs.v1.u01data05b.unit01_article_np_pattern_reconciliation.v1"
PASS_STATUS = "PASS_A1FS_V1_U01DATA05B_UNIT01_ARTICLE_NP_PATTERN_RECONCILIATION"
UNIT_ID = "GRAMMAR_ARTICLES_BASIC"
LEGACY_DEMONSTRATIVE_PATTERN_IDS = ("SP_000016", "SP_000017")
OPEN_WRITING_ACTIVITY_ID = "U01E-S03-C05-W01"
EXPECTED_ARTICLE_NP_ACTIVITY_IDS = frozenset({
    "U01-R-01", "U01-R-02", "U01-R-03", "U01-R-04",
    "U01-W-01", "U01-W-02", "U01-W-03", "U01-W-04",
    "U01-S-01", "U01-S-02", "U01-S-03",
    "U01E-S03-C02-R01", "U01E-S03-C02-R02", "U01E-S03-C02-W01",
    "U01E-S03-C03-R01", "U01E-S03-C03-W01", "U01E-S03-C03-S01",
    "U01E-S03-C04-R01", "U01E-S03-C04-W01", "U01E-S03-C04-S01",
    "U01E-S03-C05-R01", "U01E-S03-C05-R02", "U01E-S03-C05-S01",
})
EXPECTED_ACTIVITY_COUNT = 24
EXPECTED_EXISTING_ACTIVITY_COUNT = 11
EXPECTED_FIXED_ACTIVITY_COUNT = 13
DEFAULT_INPUT = Path(
    "ulga/graph/a1fs_v1_u01data02_unit01_existing_u01e_projection_and_cumulative_linkage.json"
)
DEFAULT_OUTPUT = Path(
    "ulga/graph/a1fs_v1_u01data05b_unit01_article_np_pattern_reconciliation.json"
)
NEXT_SHORT_STEP = (
    "A1FS-V1-U01DATA05C_"
    "Unit01CorrectedPatternCoverageWorkbookAndRuntimeReadbackIntegration"
)

UNIT_LOCAL_PATTERNS: tuple[dict[str, Any], ...] = (
    {
        "pattern_id": "U01-NP-ARTICLE-NOUN",
        "template": "{ARTICLE} {THING}",
        "structural_signature": "DET+N",
        "learning_role": "CORE_TARGET",
        "assessment_scope": "ARTICLE_SELECTION_AND_SINGULAR_COUNTABLE_NOUN_PHRASE",
        "global_pattern_authority_claimed": False,
    },
    {
        "pattern_id": "U01-NP-ARTICLE-ADJECTIVE-NOUN",
        "template": "{ARTICLE} {ADJECTIVE} {THING}",
        "structural_signature": "DET+ADJ+N",
        "learning_role": "CORE_TARGET",
        "assessment_scope": "ARTICLE_SOUND_SELECTION_BEFORE_ADJECTIVE_AND_NOUN_PHRASE",
        "global_pattern_authority_claimed": False,
    },
    {
        "pattern_id": "U01-NP-A-VERY-ADJECTIVE-NOUN",
        "template": "a very {ADJECTIVE} {THING}",
        "structural_signature": "DET+VERY+ADJ+N",
        "learning_role": "GUIDED_EXTENSION",
        "assessment_scope": "A_BEFORE_VERY_PLUS_ADJECTIVE_PLUS_SINGULAR_NOUN",
        "global_pattern_authority_claimed": False,
    },
)


class ReconciliationError(ValueError):
    """Fail-closed Unit01 pattern reconciliation error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def verify_digest(report: Mapping[str, Any], field: str) -> None:
    expected = str(report.get(field) or "")
    core = {key: deepcopy(value) for key, value in report.items() if key != field}
    if expected != digest(core):
        raise ReconciliationError(f"INPUT_DIGEST_INVALID:{field}")


def activities(report: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups = report.get("activity_projections") or {}
    if not isinstance(groups, Mapping):
        raise ReconciliationError("ACTIVITY_PROJECTIONS_NOT_OBJECT")
    existing = groups.get("existing_response_contract_activities") or []
    fixed = groups.get("fixed_admitted_items") or []
    if not isinstance(existing, list) or not isinstance(fixed, list):
        raise ReconciliationError("ACTIVITY_GROUP_NOT_LIST")
    if len(existing) != EXPECTED_EXISTING_ACTIVITY_COUNT:
        raise ReconciliationError(f"EXISTING_ACTIVITY_COUNT_INVALID:{len(existing)}")
    if len(fixed) != EXPECTED_FIXED_ACTIVITY_COUNT:
        raise ReconciliationError(f"FIXED_ACTIVITY_COUNT_INVALID:{len(fixed)}")
    return [deepcopy(row) for row in existing], [deepcopy(row) for row in fixed]


def reconcile_activity(row: Mapping[str, Any]) -> dict[str, Any]:
    activity_id = str(row.get("activity_id") or "")
    if not activity_id:
        raise ReconciliationError("ACTIVITY_ID_MISSING")
    legacy = sorted(str(value) for value in row.get("target_pattern_ids", []) or [])
    if legacy != sorted(LEGACY_DEMONSTRATIVE_PATTERN_IDS):
        raise ReconciliationError(
            f"LEGACY_PATTERN_BROADCAST_SHAPE_INVALID:{activity_id}:{legacy}"
        )
    if activity_id not in EXPECTED_ARTICLE_NP_ACTIVITY_IDS and activity_id != OPEN_WRITING_ACTIVITY_ID:
        raise ReconciliationError(f"UNREVIEWED_ACTIVITY_ID:{activity_id}")
    if activity_id == OPEN_WRITING_ACTIVITY_ID:
        resolved: list[str] = []
        status = "PENDING_LEARNER_RESPONSE_AND_HUMAN_REVIEW"
        evidence_mode = "OPEN_WRITING_NO_PREDETERMINED_NOUN_PHRASE_STRUCTURE"
        coverage_eligible = False
    else:
        resolved = ["U01-NP-ARTICLE-NOUN"]
        status = "RESOLVED_FROM_APPROVED_ITEM_OR_RESPONSE_CONTRACT_EVIDENCE"
        evidence_mode = "APPROVED_ARTICLE_NOUN_PHRASE_OR_COMPLETE_MODEL_SENTENCE"
        coverage_eligible = True
    return {
        "activity_id": activity_id,
        "activity_source": str(row.get("activity_source") or ""),
        "skill": str(row.get("skill") or ""),
        "question_type": str(row.get("question_type") or ""),
        "legacy_broadcast_pattern_ids": legacy,
        "legacy_broadcast_status": "REJECTED_NOT_ACTIVITY_SPECIFIC_EVIDENCE",
        "unit_allowed_pattern_ids": [row["pattern_id"] for row in UNIT_LOCAL_PATTERNS],
        "activity_realized_pattern_ids": resolved,
        "pattern_resolution_status": status,
        "pattern_evidence_mode": evidence_mode,
        "pattern_coverage_eligible": coverage_eligible,
        "demonstrative_pattern_coverage_claimed": False,
        "global_pattern_authority_mutated": False,
    }


def build_report(projection_report: Mapping[str, Any]) -> dict[str, Any]:
    if projection_report.get("unit", {}).get("unit_id") != UNIT_ID:
        raise ReconciliationError("UNIT_IDENTITY_INVALID")
    if projection_report.get("linkage_summary", {}).get("total_activity_count") != EXPECTED_ACTIVITY_COUNT:
        raise ReconciliationError("PROJECTION_ACTIVITY_DENOMINATOR_INVALID")
    verify_digest(projection_report, "projection_sha256")
    existing, fixed = activities(projection_report)
    rows = [reconcile_activity(row) for row in existing + fixed]
    rows.sort(key=lambda row: row["activity_id"])
    if len(rows) != EXPECTED_ACTIVITY_COUNT or len({row["activity_id"] for row in rows}) != len(rows):
        raise ReconciliationError("RECONCILED_ACTIVITY_IDENTITY_INVALID")
    eligible = [row for row in rows if row["pattern_coverage_eligible"]]
    coverage = {
        pattern["pattern_id"]: sum(
            pattern["pattern_id"] in row["activity_realized_pattern_ids"] for row in eligible
        )
        for pattern in UNIT_LOCAL_PATTERNS
    }
    core = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit": {"unit_id": UNIT_ID, "unit_sequence": 1, "level_scope": ["A1"]},
        "source_identity": {
            "u01data02_task_id": projection_report.get("task_id"),
            "u01data02_projection_sha256": projection_report.get("projection_sha256"),
        },
        "unit_local_pattern_contract": {
            "authority_scope": "UNIT_LOCAL_ARTICLE_NOUN_PHRASE_STRUCTURE",
            "patterns": [deepcopy(row) for row in UNIT_LOCAL_PATTERNS],
            "this_is_carrier_clause_role": "FORMULAIC_SCAFFOLD_NOT_UNIT01_ASSESSMENT_TARGET",
            "global_pattern_authority_write_allowed": False,
        },
        "deferred_global_patterns": [
            {
                "pattern_id": "SP_000016",
                "canonical_template": "This is {noun_phrase}.",
                "unit01_status": "DEFERRED_TO_DEMONSTRATIVE_UNIT_NOT_UNIT01_TARGET",
                "reason": "THIS_IS_IS_A_FORMULAIC_CARRIER_IN_UNIT01;DEMONSTRATIVE_GRAMMAR_NOT_ASSESSED",
                "coverage_claim_allowed": False,
            },
            {
                "pattern_id": "SP_000017",
                "canonical_template": "That is {noun_phrase}.",
                "unit01_status": "DEFERRED_TO_DEMONSTRATIVE_UNIT_NOT_UNIT01_TARGET",
                "reason": "NO_THAT_IS_FRAME_SENTENCE_OR_ACTIVITY_IN_UNIT01",
                "coverage_claim_allowed": False,
            },
        ],
        "activity_pattern_reconciliations": rows,
        "coverage_summary": {
            "activity_count": len(rows),
            "coverage_eligible_activity_count": len(eligible),
            "pending_open_writing_activity_count": sum(not row["pattern_coverage_eligible"] for row in rows),
            "unit_local_pattern_count": len(UNIT_LOCAL_PATTERNS),
            "activity_count_by_unit_local_pattern": coverage,
            "covered_unit_local_pattern_ids": sorted(key for key, value in coverage.items() if value),
            "uncovered_unit_local_pattern_ids": sorted(key for key, value in coverage.items() if not value),
            "legacy_demonstrative_broadcast_activity_count": sum(
                row["legacy_broadcast_pattern_ids"] == sorted(LEGACY_DEMONSTRATIVE_PATTERN_IDS)
                for row in rows
            ),
            "demonstrative_pattern_coverage_count": 0,
            "coverage_merge_across_np_structures_allowed": False,
        },
        "boundaries": {
            "unit02_to_unit24_modified": False,
            "global_pattern_authority_modified": False,
            "existing_pattern_ids_redefined": False,
            "new_that_is_frame_created": False,
            "learner_facing_content_modified": False,
            "question_or_answer_content_copied": False,
            "learner_database_written": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
            "parallel_curriculum_created": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    core["reconciliation_sha256"] = digest(core)
    return core


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReconciliationError(f"OBJECT_REQUIRED:{path}")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projection-report", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        report = build_report(load(args.projection_report.resolve()))
        args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
        args.output.resolve().write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except (OSError, json.JSONDecodeError, ReconciliationError, KeyError, TypeError, ValueError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01DATA05B_UNIT01_ARTICLE_NP_PATTERN_RECONCILIATION")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={report['status']}")
    for key, value in report["coverage_summary"].items():
        if isinstance(value, (str, int, bool)):
            print(f"{key.upper()}={value}")
    print(f"RECONCILIATION_SHA256={report['reconciliation_sha256']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
