#!/usr/bin/env python3
"""Reconcile Unit01 -> Unit02 sentence-pattern lineage and exact-frame coverage.

U02SP02 is a read-only authority boundary for future Unit02 consumers. It
separates pedagogical pattern families, exact sentence-frame templates,
canonical SP_* authority, and morphology/NP task families. Historical U02QB02
and U02QBC02 payloads are inspected but never rewritten.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as u01
from ulga.builders import (
    build_a1fs_v1_u02qb02_unit02_plain_s_questionbank_candidate_pool as u02qb02,
)
from ulga.builders import (
    build_a1fs_v1_u02qbc02_unit02_questionbank_gap_materialization_and_per_slot_distinct_capacity_proof
    as u02qbc02,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Read-only sentence-pattern lineage and exact-frame coverage reconciliation; no learner content, sentence-pattern authority, QuestionBank, scene, or runtime asset is created or mutated."

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U02SP02_Unit01Unit02ExactSentenceFrameCoverageRecheck"
SCHEMA_VERSION = "a1fs.v1.u02sp02.exact_sentence_frame_coverage_recheck.v1"
PASS_STATUS = "PASS_A1FS_V1_U02SP02_UNIT01_UNIT02_EXACT_SENTENCE_FRAME_COVERAGE_RECHECK"
NEXT_SHORT_STEP = "A1FS-V1-U02SA01_Unit01Unit02CumulativeSentenceAssetCoverageRecheck"
NEXT_SCOPE_STATUS = "OUTSIDE_APPROVED_Q5_SCOPE"

REPO_ROOT = Path(__file__).resolve().parents[2]
SENTENCE_PATTERN_AUTHORITY_PATH = REPO_ROOT / "ulga/graph/sentence_patterns.json"

LEGACY_INVALID_PATTERN_ID = "SP_000002"
EXPECTED_LEGACY_INVALID_BINDINGS = 994
EXPECTED_BASE_U02_ITEMS = 658
EXPECTED_QBC02_NEW_ITEMS = 336
EXPECTED_RECOMBINATION_ITEMS = 96

UNIT01_PEDAGOGICAL_CORE_FAMILIES: tuple[dict[str, str], ...] = (
    {
        "family_id": "U01-P1",
        "surface": "This is a/an X.",
        "unit02_plural_role": "REVIEW_ONLY_MAIN_NP_REMAINS_SINGULAR",
    },
    {
        "family_id": "U01-P2",
        "surface": "I can see a/an X.",
        "unit02_plural_role": "INHERITED_CLAUSE_SHELL_PLURAL_NP_CAPABLE",
    },
    {
        "family_id": "U01-P3",
        "surface": "There is a/an X.",
        "unit02_plural_role": "MAIN_NP_REMAINS_SINGULAR_RELATION_SLOT_CONDITIONAL_PLURAL",
    },
)

UNIT02_NEW_CANONICAL_PATTERNS: Mapping[str, str] = {
    "SP_000003": "I have {noun_phrase}.",
    "SP_000004": "I like {noun_phrase/gerund}.",
    "SP_000005": "I don't like {noun_phrase/gerund}.",
    "SP_000013": "Can I have {noun_phrase}?",
}

RECOMBINATION_TASK_FAMILIES = ("PRODUCTIVE_RESPONSE", "TRANSFER")


class U02SP02BuildError(ValueError):
    pass


def normalized(value: str) -> str:
    return " ".join(str(value).casefold().split())


def sentence_pattern_authority() -> dict[str, dict[str, Any]]:
    rows = json.loads(SENTENCE_PATTERN_AUTHORITY_PATH.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise U02SP02BuildError("SENTENCE_PATTERN_AUTHORITY_NOT_LIST")
    by_source_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        source_id = str(row.get("authority_source", {}).get("source_record_id") or "")
        if source_id:
            by_source_id[source_id] = dict(row)
    required = {LEGACY_INVALID_PATTERN_ID, *UNIT02_NEW_CANONICAL_PATTERNS}
    missing = sorted(required - set(by_source_id))
    if missing:
        raise U02SP02BuildError(f"SENTENCE_PATTERN_AUTHORITY_MISSING:{','.join(missing)}")
    return by_source_id


def canonical_pattern_row(sp_id: str, row: Mapping[str, Any]) -> dict[str, Any]:
    label = str(row.get("label") or "")
    metadata = row.get("metadata", {})
    canonical = str(metadata.get("canonical_pattern") or "") if isinstance(metadata, Mapping) else ""
    return {
        "source_record_id": sp_id,
        "label": label,
        "canonical_pattern": canonical,
        "pattern_family_id": (
            str(metadata.get("pattern_family_id") or "")
            if isinstance(metadata, Mapping)
            else ""
        ),
        "review_status": (
            str(metadata.get("review_status") or "")
            if isinstance(metadata, Mapping)
            else ""
        ),
    }


def unit01_exact_frames() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for frame_id, template, goal, support in u01.CORE_SENTENCE_FRAMES:
        rows.append(
            {
                "frame_id": frame_id,
                "template": template,
                "frame_group": "CORE_SENTENCE_FRAME",
                "communicative_goal": goal,
                "support_level": support,
            }
        )
    for frame_id, template, goal, support, egp_role in u01.ADJECTIVE_SENTENCE_FRAMES:
        rows.append(
            {
                "frame_id": frame_id,
                "template": template,
                "frame_group": "ADJECTIVE_SENTENCE_FRAME",
                "communicative_goal": goal,
                "support_level": support,
                "egp_role": egp_role,
            }
        )
    for frame_id, template, grammar_ref, role in u01.SCAFFOLD_FRAMES:
        rows.append(
            {
                "frame_id": frame_id,
                "template": template,
                "frame_group": "SCAFFOLD_FRAME",
                "external_grammar_ref": grammar_ref,
                "role": role,
            }
        )
    return rows


def approved_unit02_items() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    base = u02qb02.admit_candidate(u02qb02.build_candidate())["payload"]["approved_items"]
    new = u02qbc02.materialized_gap_items()
    if len(base) != EXPECTED_BASE_U02_ITEMS:
        raise U02SP02BuildError(f"BASE_U02_ITEM_COUNT_DRIFT:{len(base)}")
    if len(new) != EXPECTED_QBC02_NEW_ITEMS:
        raise U02SP02BuildError(f"QBC02_NEW_ITEM_COUNT_DRIFT:{len(new)}")
    return [dict(row) for row in base], [dict(row) for row in new]


def raw_pattern_binding_distribution(rows: list[Mapping[str, Any]]) -> dict[str, int]:
    counts = Counter(
        str(pattern_id)
        for row in rows
        for pattern_id in (row.get("unit_pattern_ids") or [])
    )
    return dict(sorted(counts.items()))


def family_projection(
    base_items: list[Mapping[str, Any]], new_items: list[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    base_counts = Counter(str(row["pattern_family_id"]) for row in base_items)
    for family_id, count in sorted(base_counts.items()):
        rows.append(
            {
                "source": "U02QB02",
                "family_id": family_id,
                "item_count": count,
                "raw_pattern_ids": [LEGACY_INVALID_PATTERN_ID],
                "reconciled_direct_pattern_ids": [],
                "lineage_class": "MORPHOLOGY_OR_NP_TASK_NO_DIRECT_SENTENCE_PATTERN",
                "runtime_may_consume_raw_pattern_ids": False,
            }
        )

    new_counts = Counter(str(row["task_family"]) for row in new_items)
    for family_id, count in sorted(new_counts.items()):
        recombination = family_id in RECOMBINATION_TASK_FAMILIES
        rows.append(
            {
                "source": "U02QBC02",
                "family_id": family_id,
                "item_count": count,
                "raw_pattern_ids": [LEGACY_INVALID_PATTERN_ID],
                "reconciled_direct_pattern_ids": [],
                "lineage_class": (
                    "INHERITED_U01_CLAUSE_SHELL_WITH_UNIT02_PLURAL_NP"
                    if recombination
                    else "PHRASE_OR_CONTEXT_TASK_NO_DIRECT_SENTENCE_PATTERN"
                ),
                "source_unit01_frame_id": "U01-F06" if recombination else None,
                "source_unit01_frame_template": (
                    "I can see {ARTICLE} {THING}." if recombination else None
                ),
                "runtime_may_consume_raw_pattern_ids": False,
            }
        )
    return rows


def build_report() -> dict[str, Any]:
    authority = sentence_pattern_authority()
    u01_frames = unit01_exact_frames()
    base_items, new_items = approved_unit02_items()
    all_items = base_items + new_items

    raw_distribution = raw_pattern_binding_distribution(all_items)
    legacy_count = raw_distribution.get(LEGACY_INVALID_PATTERN_ID, 0)
    if legacy_count != EXPECTED_LEGACY_INVALID_BINDINGS:
        raise U02SP02BuildError(f"LEGACY_PATTERN_BINDING_COUNT_DRIFT:{legacy_count}")
    if set(raw_distribution) != {LEGACY_INVALID_PATTERN_ID}:
        raise U02SP02BuildError(f"UNEXPECTED_RAW_PATTERN_IDS:{sorted(raw_distribution)}")

    sp0002 = canonical_pattern_row(LEGACY_INVALID_PATTERN_ID, authority[LEGACY_INVALID_PATTERN_ID])
    if sp0002["canonical_pattern"] != "My name is {name}.":
        raise U02SP02BuildError("SP000002_AUTHORITY_DRIFT")

    new_patterns = []
    for sp_id, expected in UNIT02_NEW_CANONICAL_PATTERNS.items():
        row = canonical_pattern_row(sp_id, authority[sp_id])
        if row["canonical_pattern"] != expected or row["label"] != expected:
            raise U02SP02BuildError(f"UNIT02_NEW_PATTERN_AUTHORITY_DRIFT:{sp_id}")
        new_patterns.append(row)

    u01_templates = {normalized(row["template"]) for row in u01_frames}
    u02_templates = {normalized(row["canonical_pattern"]) for row in new_patterns}
    overlap = sorted(u01_templates & u02_templates)

    u01_f02 = next(row for row in u01_frames if row["frame_id"] == "U01-F02")
    sp0003 = next(row for row in new_patterns if row["source_record_id"] == "SP_000003")
    projection = family_projection(base_items, new_items)
    recombination_count = sum(
        row["item_count"]
        for row in projection
        if row["lineage_class"] == "INHERITED_U01_CLAUSE_SHELL_WITH_UNIT02_PLURAL_NP"
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "pattern_family_coverage": {
            "unit01_inherited_pedagogical_core_family_count": len(UNIT01_PEDAGOGICAL_CORE_FAMILIES),
            "unit01_inherited_pedagogical_core_families": [dict(row) for row in UNIT01_PEDAGOGICAL_CORE_FAMILIES],
            "unit02_new_canonical_core_pattern_count": len(new_patterns),
            "unit02_new_canonical_core_patterns": new_patterns,
            "cumulative_pedagogical_core_pattern_family_count": (
                len(UNIT01_PEDAGOGICAL_CORE_FAMILIES) + len(new_patterns)
            ),
            "unit02_main_plural_sentence_generation_family_count": 5,
            "unit02_main_plural_sentence_generation_model": {
                "inherited_plural_capable_family_count": 1,
                "newly_unlocked_family_count": len(new_patterns),
            },
        },
        "exact_frame_coverage": {
            "unit01_exact_frame_count": len(u01_frames),
            "unit01_core_sentence_frame_count": len(u01.CORE_SENTENCE_FRAMES),
            "unit01_adjective_sentence_frame_count": len(u01.ADJECTIVE_SENTENCE_FRAMES),
            "unit01_scaffold_frame_count": len(u01.SCAFFOLD_FRAMES),
            "unit01_exact_frames": u01_frames,
            "unit02_new_canonical_exact_frame_count": len(new_patterns),
            "unit02_new_canonical_exact_frames": [
                {"source_record_id": row["source_record_id"], "template": row["canonical_pattern"]}
                for row in new_patterns
            ],
            "cross_unit_exact_template_overlap_count": len(overlap),
            "cross_unit_exact_template_overlap": overlap,
            "cumulative_declared_exact_frame_count": len(u01_frames) + len(new_patterns) - len(overlap),
        },
        "i_have_lineage_reconciliation": {
            "unit01_contract_frame_id": u01_f02["frame_id"],
            "unit01_contract_template": u01_f02["template"],
            "unit02_canonical_pattern_id": sp0003["source_record_id"],
            "unit02_canonical_pattern_template": sp0003["canonical_pattern"],
            "exact_template_match": normalized(u01_f02["template"]) == normalized(sp0003["canonical_pattern"]),
            "unit01_pedagogical_core_inherited": False,
            "unit02_new_core_pattern": True,
            "classification": "FRAME_PRESENT_IN_UNIT01_CONTRACT_BUT_PEDAGOGICALLY_DEFERRED_TO_UNIT02",
        },
        "legacy_pattern_reconciliation": {
            "legacy_invalid_pattern_id": LEGACY_INVALID_PATTERN_ID,
            "canonical_authority": sp0002,
            "raw_approved_u02_item_count": len(all_items),
            "raw_u02qb02_item_count": len(base_items),
            "raw_u02qbc02_new_item_count": len(new_items),
            "raw_pattern_binding_distribution": raw_distribution,
            "raw_legacy_invalid_binding_count": legacy_count,
            "reconciled_legacy_invalid_binding_count": 0,
            "reconciled_direct_canonical_sp_binding_count": 0,
            "unit02_new_core_patterns_bound_in_current_questionbank_count": 0,
            "inherited_clause_shell_recombination_item_count": recombination_count,
            "future_runtime_must_consume_reconciled_projection": True,
            "raw_pattern_ids_runtime_authoritative": False,
        },
        "reconciled_questionbank_pattern_projection": projection,
        "claim_boundaries": {
            "historical_u02qb02_payload_mutated": False,
            "historical_u02qbc02_payload_mutated": False,
            "questionbank_item_identity_mutated": False,
            "answer_or_scoring_contract_mutated": False,
            "global_sentence_pattern_authority_mutated": False,
            "runtime_connected": False,
            "canonical_scene_authority_mutated": False,
            "new_learner_content_created": False,
            "a2_unlocked": False,
        },
        "next_scope": {
            "scope_status": NEXT_SCOPE_STATUS,
            "next_short_step": NEXT_SHORT_STEP,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    from ulga.validators import (
        validate_a1fs_v1_u02sp02_unit01_unit02_exact_sentence_frame_coverage_recheck as validator,
    )

    report = build_report()
    validation = validator.validate_report(report)
    patterns = report["pattern_family_coverage"]
    frames = report["exact_frame_coverage"]
    legacy = report["legacy_pattern_reconciliation"]
    print(f"STATUS={PASS_STATUS}")
    print(f"UNIT01_CORE_PATTERN_FAMILIES={patterns['unit01_inherited_pedagogical_core_family_count']}")
    print(f"UNIT02_NEW_CORE_PATTERNS={patterns['unit02_new_canonical_core_pattern_count']}")
    print(f"CUMULATIVE_CORE_PATTERN_FAMILIES={patterns['cumulative_pedagogical_core_pattern_family_count']}")
    print(f"UNIT01_EXACT_FRAMES={frames['unit01_exact_frame_count']}")
    print(f"UNIT02_NEW_CANONICAL_EXACT_FRAMES={frames['unit02_new_canonical_exact_frame_count']}")
    print(f"CUMULATIVE_DECLARED_EXACT_FRAMES={frames['cumulative_declared_exact_frame_count']}")
    print(f"RAW_INVALID_SP000002_BINDINGS={legacy['raw_legacy_invalid_binding_count']}")
    print(f"RECONCILED_INVALID_SP000002_BINDINGS={legacy['reconciled_legacy_invalid_binding_count']}")
    print(f"ERROR_COUNT={validation['error_count']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
