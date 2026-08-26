#!/usr/bin/env python3
"""Cross-check Unit03 exact lesson-to-sentence-pattern binding without promotion."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import (
    build_a1fs_v1_u02sp02_unit01_unit02_exact_sentence_frame_coverage_recheck as u02sp02,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Read-only Unit03 lesson-to-sentence-pattern binding cross-check; no grammar, sentence pattern, sentence asset, QuestionBank, scene, runtime/state/scoring, learner content, or A2 authority is created or mutated."

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U03Q05R1_Unit03ExactLessonSentencePatternBindingCrossCheck"
SCHEMA_VERSION = "a1fs.v1.u03q05r1.exact_lesson_sentence_pattern_binding_crosscheck.v1"
PASS_STATUS = "PASS_A1FS_V1_U03Q05R1_UNIT03_EXACT_LESSON_SENTENCE_PATTERN_BINDING_CROSSCHECK"
NEXT_SHORT_STEP = "A1FS-V1-U03Q06R1_Unit03CumulativeSentenceAssetCoverageProjection"
NEXT_SCOPE_STATUS = "OUTSIDE_APPROVED_Q5_SCOPE"
UNIT_ID = "GRAMMAR_SUBJECT_PRONOUNS"
LESSON_ID = "KLSN-WF02-L02"
LESSON_REQUIREMENT_ID = "REF:WRITING:A1W-08"

REPO_ROOT = Path(__file__).resolve().parents[2]
SENTENCE_PATTERN_AUTHORITY_PATH = REPO_ROOT / "ulga/graph/sentence_patterns.json"
RULE_PRIMITIVE_PATH = REPO_ROOT / "ulga/rules/a1_a1plus_rule_primitives_batch_01.json"

LESSON_GRAMMAR_RESOURCE_IDS = ("KPOP-GR-014", "KPOP-GR-015")
LESSON_SENTENCE_PATTERN_RESOURCE_IDS: tuple[str, ...] = ()
LESSON_TARGET = "subject/object reference"
LESSON_PRODUCTION_SHAPE = "TWO_CONNECTED_SENTENCES_ONE_CHILD_ONE_TOY_PRONOUN_CLEAR"
LESSON_SOURCE_PROVIDES_COMPLETE_TARGET_SENTENCE = False
LESSON_SOURCE_ALLOWS_AUTOMATIC_SENTENCE_GENERATION = False
LESSON_REQUIRES_SEPARATELY_REVIEWED_EXAMPLE = True
LESSON_NOTICE_EXAMPLES = ("Ben has a kite.", "He likes it.")

SUBJECT_PRONOUN_RULE_ID = "SUBJECT_PRONOUN_CLOSED_LIST_BEFORE_VERB"
SUBJECT_PRONOUN_CORE_PATTERN = "subject pronoun + finite verb"
GLOBAL_OVERLAP_PATTERN_ID = "SP_000001"
GLOBAL_OVERLAP_CANONICAL_PATTERN = "I am {adjective/noun_phrase}."
GLOBAL_OVERLAP_EXAMPLE = "I am happy."


class U03Q05R1BuildError(ValueError):
    pass


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sentence_pattern_index() -> dict[str, dict[str, Any]]:
    rows = _load_json(SENTENCE_PATTERN_AUTHORITY_PATH)
    if not isinstance(rows, list):
        raise U03Q05R1BuildError("SENTENCE_PATTERN_AUTHORITY_NOT_LIST")
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        authority_source = row.get("authority_source", {})
        source_id = str(authority_source.get("source_record_id") or "") if isinstance(authority_source, Mapping) else ""
        if source_id:
            index[source_id] = dict(row)
    required = {GLOBAL_OVERLAP_PATTERN_ID, *u02sp02.UNIT02_NEW_CANONICAL_PATTERNS}
    missing = sorted(required - set(index))
    if missing:
        raise U03Q05R1BuildError(f"SENTENCE_PATTERN_AUTHORITY_MISSING:{','.join(missing)}")
    return index


def _canonical_pattern_row(sp_id: str, row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = row.get("metadata", {})
    if not isinstance(metadata, Mapping):
        metadata = {}
    return {
        "source_record_id": sp_id,
        "canonical_pattern": str(metadata.get("canonical_pattern") or ""),
        "pattern_family_id": str(metadata.get("pattern_family_id") or ""),
        "pattern_type": str(metadata.get("pattern_type") or ""),
        "review_status": str(metadata.get("review_status") or ""),
        "example_sentences": list(metadata.get("example_sentences") or []),
    }


def _subject_pronoun_rule_evidence() -> dict[str, Any]:
    payload = _load_json(RULE_PRIMITIVE_PATH)
    nodes = payload.get("batch_nodes", []) if isinstance(payload, Mapping) else []
    matches = [row for row in nodes if isinstance(row, Mapping) and row.get("grammar_id") == UNIT_ID]
    if len(matches) != 1:
        raise U03Q05R1BuildError(f"SUBJECT_PRONOUN_RULE_NODE_COUNT:{len(matches)}")
    node = matches[0]
    primitives = node.get("rule_primitives", [])
    if len(primitives) != 1 or not isinstance(primitives[0], Mapping):
        raise U03Q05R1BuildError("SUBJECT_PRONOUN_RULE_PRIMITIVE_SHAPE_INVALID")
    primitive = primitives[0]
    batch_policy = payload.get("batch_policy", {}) if isinstance(payload, Mapping) else {}
    evidence = {
        "grammar_id": str(node.get("grammar_id") or ""),
        "rule_id": str(primitive.get("rule_id") or ""),
        "core_pattern": str(primitive.get("core_pattern") or ""),
        "positive_test_cases": list(node.get("positive_test_cases") or []),
        "verified": bool(node.get("verified")),
        "batch_candidate_only": bool(batch_policy.get("candidate_only")),
        "coverage_claim_allowed": bool(batch_policy.get("coverage_claim_allowed")),
    }
    if evidence["rule_id"] != SUBJECT_PRONOUN_RULE_ID:
        raise U03Q05R1BuildError("SUBJECT_PRONOUN_RULE_ID_DRIFT")
    if evidence["core_pattern"] != SUBJECT_PRONOUN_CORE_PATTERN:
        raise U03Q05R1BuildError("SUBJECT_PRONOUN_CORE_PATTERN_DRIFT")
    return evidence


def _inherited_pattern_families(index: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in u02sp02.UNIT01_PEDAGOGICAL_CORE_FAMILIES:
        rows.append({
            "source_unit": "Unit01",
            "family_id": row["family_id"],
            "surface": row["surface"],
            "authority_class": "INHERITED_PEDAGOGICAL_CORE_FAMILY",
        })
    for sp_id, expected in u02sp02.UNIT02_NEW_CANONICAL_PATTERNS.items():
        canonical = _canonical_pattern_row(sp_id, index[sp_id])
        if canonical["canonical_pattern"] != expected or canonical["review_status"] != "accepted":
            raise U03Q05R1BuildError(f"UNIT02_CANONICAL_PATTERN_DRIFT:{sp_id}")
        rows.append({
            "source_unit": "Unit02",
            "family_id": sp_id,
            "surface": canonical["canonical_pattern"],
            "canonical_pattern_family_id": canonical["pattern_family_id"],
            "authority_class": "INHERITED_CANONICAL_SP_PATTERN",
        })
    if len(rows) != 7:
        raise U03Q05R1BuildError(f"INHERITED_PATTERN_FAMILY_COUNT_DRIFT:{len(rows)}")
    return rows


def _inherited_exact_frames(index: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        {
            "source_unit": "Unit01",
            "frame_id": row["frame_id"],
            "template": row["template"],
            "frame_group": row["frame_group"],
            "authority_class": "INHERITED_UNIT01_EXACT_FRAME",
        }
        for row in u02sp02.unit01_exact_frames()
    ]
    for sp_id, expected in u02sp02.UNIT02_NEW_CANONICAL_PATTERNS.items():
        canonical = _canonical_pattern_row(sp_id, index[sp_id])
        if canonical["canonical_pattern"] != expected:
            raise U03Q05R1BuildError(f"UNIT02_EXACT_FRAME_DRIFT:{sp_id}")
        rows.append({
            "source_unit": "Unit02",
            "frame_id": sp_id,
            "template": canonical["canonical_pattern"],
            "frame_group": "CANONICAL_SENTENCE_PATTERN",
            "authority_class": "INHERITED_UNIT02_EXACT_FRAME",
        })
    if len(rows) != 15:
        raise U03Q05R1BuildError(f"INHERITED_EXACT_FRAME_COUNT_DRIFT:{len(rows)}")
    return rows


def build_report() -> dict[str, Any]:
    index = _sentence_pattern_index()
    rule = _subject_pronoun_rule_evidence()
    overlap = _canonical_pattern_row(GLOBAL_OVERLAP_PATTERN_ID, index[GLOBAL_OVERLAP_PATTERN_ID])
    if overlap["canonical_pattern"] != GLOBAL_OVERLAP_CANONICAL_PATTERN:
        raise U03Q05R1BuildError("GLOBAL_OVERLAP_PATTERN_DRIFT")
    if GLOBAL_OVERLAP_EXAMPLE not in overlap["example_sentences"]:
        raise U03Q05R1BuildError("GLOBAL_OVERLAP_EXAMPLE_DRIFT")

    inherited_families = _inherited_pattern_families(index)
    inherited_frames = _inherited_exact_frames(index)
    positive_overlap = GLOBAL_OVERLAP_EXAMPLE in rule["positive_test_cases"]

    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "unit_id": UNIT_ID,
        "status": PASS_STATUS,
        "lesson_binding": {
            "lesson_id": LESSON_ID,
            "requirement_node_id": LESSON_REQUIREMENT_ID,
            "lesson_target": LESSON_TARGET,
            "grammar_resource_ids": list(LESSON_GRAMMAR_RESOURCE_IDS),
            "explicit_sentence_pattern_resource_ids": list(LESSON_SENTENCE_PATTERN_RESOURCE_IDS),
            "production_shape": LESSON_PRODUCTION_SHAPE,
            "source_provides_complete_target_sentence": LESSON_SOURCE_PROVIDES_COMPLETE_TARGET_SENTENCE,
            "source_allows_automatic_sentence_generation": LESSON_SOURCE_ALLOWS_AUTOMATIC_SENTENCE_GENERATION,
            "source_requires_separately_reviewed_example": LESSON_REQUIRES_SEPARATELY_REVIEWED_EXAMPLE,
            "notice_example_surfaces": list(LESSON_NOTICE_EXAMPLES),
            "unit03_exact_canonical_sentence_pattern_binding_ids": [],
            "binding_result": "NO_EXPLICIT_UNIT03_SENTENCE_PATTERN_RESOURCE_BINDING",
        },
        "subject_pronoun_rule_primitive": {
            **rule,
            "sentence_pattern_authority": False,
            "may_materialize_unit03_q5_pattern": False,
        },
        "global_pattern_overlap_diagnostic": {
            "source_record_id": GLOBAL_OVERLAP_PATTERN_ID,
            "canonical_pattern": overlap["canonical_pattern"],
            "example_surface": GLOBAL_OVERLAP_EXAMPLE,
            "same_example_surface_present_in_rule_primitive": positive_overlap,
            "lesson_explicit_binding": False,
            "unit03_q5_admitted": False,
            "reason": "GLOBAL_PATTERN_OR_RULE_EXAMPLE_OVERLAP_IS_NOT_EXACT_LESSON_BINDING",
        },
        "q5_pattern_family_coverage": {
            "unit01_unit02_inherited_family_count": len(inherited_families),
            "unit03_new_canonical_pattern_family_count": 0,
            "cumulative_pattern_family_count": len(inherited_families),
            "inherited_families": inherited_families,
            "unit03_new_families": [],
        },
        "q5_exact_frame_coverage": {
            "unit01_unit02_inherited_exact_frame_count": len(inherited_frames),
            "unit03_new_exact_frame_count": 0,
            "cumulative_exact_frame_count": len(inherited_frames),
            "inherited_exact_frames": inherited_frames,
            "unit03_new_exact_frames": [],
        },
        "admission_decision": {
            "unit03_native_sentence_pattern_family_count": 0,
            "unit03_native_exact_frame_count": 0,
            "pronoun_substitution_creates_new_pattern_family": False,
            "generalize_i_patterns_across_pronouns_without_explicit_authority": False,
            "learner_generated_or_notice_example_promoted_to_pattern_authority": False,
        },
        "claim_boundaries": {
            "canonical_sentence_pattern_authority_mutated": False,
            "grammar_rule_authority_mutated": False,
            "sentence_assets_created": False,
            "questionbank_items_created": False,
            "canonical_scene_authority_mutated": False,
            "runtime_or_learner_state_mutated": False,
            "a2_unlocked": False,
        },
        "next_scope": {
            "scope_status": NEXT_SCOPE_STATUS,
            "next_short_step": NEXT_SHORT_STEP,
        },
    }


def validate(report: Mapping[str, Any]) -> None:
    if report.get("status") != PASS_STATUS:
        raise U03Q05R1BuildError("STATUS_NOT_PASS")
    lesson = report.get("lesson_binding", {})
    if lesson.get("explicit_sentence_pattern_resource_ids") != []:
        raise U03Q05R1BuildError("LESSON_EXPLICIT_SP_BINDING_NOT_EMPTY")
    if lesson.get("unit03_exact_canonical_sentence_pattern_binding_ids") != []:
        raise U03Q05R1BuildError("UNIT03_EXACT_SP_BINDING_NOT_EMPTY")
    families = report.get("q5_pattern_family_coverage", {})
    frames = report.get("q5_exact_frame_coverage", {})
    if (families.get("unit01_unit02_inherited_family_count"), families.get("unit03_new_canonical_pattern_family_count"), families.get("cumulative_pattern_family_count")) != (7, 0, 7):
        raise U03Q05R1BuildError("Q5_PATTERN_FAMILY_DENOMINATOR_INVALID")
    if (frames.get("unit01_unit02_inherited_exact_frame_count"), frames.get("unit03_new_exact_frame_count"), frames.get("cumulative_exact_frame_count")) != (15, 0, 15):
        raise U03Q05R1BuildError("Q5_EXACT_FRAME_DENOMINATOR_INVALID")


def main() -> int:
    report = build_report()
    validate(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
