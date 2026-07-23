#!/usr/bin/env python3
"""Validate R3G KET99 full semantic inventory and A1/A1+ coverage expansion."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp07r3g_ket99_full_semantic_inventory_and_a1a1plus_coverage_expansion as builder  # noqa: E402

EXPECTED_TRANSCRIPTS = {f"P{number:03d}" for number in range(4, 103)}
ALLOWED_BASES = {
    "BASELINE_R3E_REFERENCE",
    "EXACT_CP07B_M1_NODE_TARGET",
    "CONTROLLED_CANONICAL_GRAMMAR_TOKEN_MATCH",
    "EXACT_NORMALIZED_SEMANTIC_ATOM",
    "CONTROLLED_TOPIC_DOMAIN_AND_SKILL",
    "CONTROLLED_STRATEGY_DOMAIN_AND_SKILL",
}


def error(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def validate_artifact(
    artifact: Mapping[str, Any],
    *,
    m1_graph: Mapping[str, Any],
    m2_consumer: Mapping[str, Any],
    cp07b_overlay: Mapping[str, Any],
    r3e_baseline: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    error(errors, artifact.get("task_id") == builder.TASK_ID, "task_id_invalid")
    error(errors, artifact.get("schema_version") == builder.SCHEMA_VERSION, "schema_version_invalid")
    error(errors, artifact.get("validation_status") == builder.PASS_STATUS, "status_invalid")
    error(errors, artifact.get("scope") == "A1_A1_PLUS_ONLY", "scope_invalid")
    error(errors, artifact.get("errors") == [], "artifact_errors_not_empty")
    error(errors, artifact.get("stop_reason") == "NONE", "stop_reason_invalid")

    expected_identity = {
        "m1_hard_graph_sha256": builder.digest(m1_graph),
        "m2_consumer_sha256": builder.digest(m2_consumer),
        "cp07b_instructional_overlay_sha256": builder.digest(cp07b_overlay),
        "r3e_baseline_sha256": builder.digest(r3e_baseline),
    }
    error(errors, artifact.get("source_identity") == expected_identity, "source_identity_mismatch")

    authority = artifact.get("authority_contract")
    error(errors, isinstance(authority, Mapping), "authority_contract_missing")
    if isinstance(authority, Mapping):
        error(errors, authority.get("mapping_model") == "CONTROLLED_MULTI_DOMAIN_EXACT_TAXONOMY", "mapping_model_invalid")
        error(errors, authority.get("free_form_fuzzy_matching_allowed") is False, "fuzzy_matching_not_locked")
        error(errors, authority.get("generic_teacher_delivery_role_sufficient_for_mapping") is False, "generic_role_mapping_not_locked")
        error(errors, authority.get("hard_graph_mutation_allowed") is False, "hard_graph_mutation_not_locked")
        error(errors, authority.get("hard_lesson_selection_allowed") is False, "lesson_selection_not_locked")
        error(errors, authority.get("delivery_block_on_missing_reference_allowed") is False, "missing_reference_block_not_locked")
        error(errors, authority.get("a2_a2plus_status") == "LOCKED", "a2_lock_invalid")

    inventories = artifact.get("transcript_semantic_inventory")
    lessons = artifact.get("lesson_instructional_references")
    error(errors, isinstance(inventories, list), "transcript_inventory_missing")
    error(errors, isinstance(lessons, list), "lesson_reference_rows_missing")
    inventories = inventories if isinstance(inventories, list) else []
    lessons = lessons if isinstance(lessons, list) else []

    transcript_ids = [str(row.get("transcript_id") or "") for row in inventories if isinstance(row, Mapping)]
    error(errors, len(inventories) == 99, "transcript_inventory_count_not_99")
    error(errors, set(transcript_ids) == EXPECTED_TRANSCRIPTS, "transcript_identity_set_invalid")
    error(errors, len(transcript_ids) == len(set(transcript_ids)), "transcript_identity_duplicate")

    source_lessons = [
        row for row in m2_consumer.get("lesson_catalog", [])
        if isinstance(row, Mapping) and row.get("level") in {"A1", "A1+"}
    ]
    source_lesson_ids = {str(row.get("lesson_id") or "") for row in source_lessons}
    lesson_ids = [str(row.get("lesson_id") or "") for row in lessons if isinstance(row, Mapping)]
    error(errors, len(lessons) == len(source_lessons), "lesson_inventory_count_mismatch")
    error(errors, set(lesson_ids) == source_lesson_ids, "lesson_identity_set_mismatch")
    error(errors, len(lesson_ids) == len(set(lesson_ids)), "lesson_identity_duplicate")

    cp07b_occurrences: dict[str, tuple[str, str]] = {}
    for transcript in cp07b_overlay.get("transcript_overlays", []):
        if not isinstance(transcript, Mapping):
            continue
        transcript_id = str(transcript.get("transcript_id") or "")
        source_sha = str(transcript.get("source_lineage", {}).get("source_evidence_sha256") or "")
        for occurrence in transcript.get("evidence_occurrences", []):
            if isinstance(occurrence, Mapping):
                occurrence_id = str(occurrence.get("evidence_occurrence_id") or "")
                if occurrence_id:
                    cp07b_occurrences[occurrence_id] = (transcript_id, source_sha)

    actual_transcript_lessons: defaultdict[str, set[str]] = defaultdict(set)
    actual_reference_count = 0
    skill_actual = {
        skill: {"lesson_count": 0, "referenced_lesson_count": 0, "unreferenced_lesson_count": 0, "instructional_reference_count": 0}
        for skill in builder.SKILLS
    }

    for row in lessons:
        if not isinstance(row, Mapping):
            errors.append("lesson_row_invalid")
            continue
        lesson_id = str(row.get("lesson_id") or "")
        skill = str(row.get("skill") or "")
        level = str(row.get("level") or "")
        references = row.get("instructional_references")
        if not isinstance(references, list):
            errors.append(f"lesson_references_invalid:{lesson_id}")
            references = []
        error(errors, skill in builder.SKILLS, f"lesson_skill_invalid:{lesson_id}")
        error(errors, level in builder.LEVELS, f"lesson_level_invalid:{lesson_id}")
        error(errors, row.get("delivery_blocked_by_missing_reference") is False, f"missing_reference_blocks_delivery:{lesson_id}")
        error(errors, row.get("hard_lesson_selection_changed") is False, f"lesson_selection_changed:{lesson_id}")
        expected_status = "REFERENCED" if references else "NO_EXACT_OR_CONTROLLED_KET99_REFERENCE"
        error(errors, row.get("reference_status") == expected_status, f"lesson_reference_status_invalid:{lesson_id}")
        occurrence_ids: list[str] = []
        for reference in references:
            if not isinstance(reference, Mapping):
                errors.append(f"reference_row_invalid:{lesson_id}")
                continue
            occurrence_id = str(reference.get("evidence_occurrence_id") or "")
            transcript_id = str(reference.get("transcript_id") or "")
            source_sha = str(reference.get("source_evidence_sha256") or "")
            occurrence_ids.append(occurrence_id)
            expected = cp07b_occurrences.get(occurrence_id)
            error(errors, expected is not None, f"reference_occurrence_not_in_cp07b:{lesson_id}:{occurrence_id}")
            if expected is not None:
                error(errors, expected == (transcript_id, source_sha), f"reference_lineage_mismatch:{lesson_id}:{occurrence_id}")
            bases = reference.get("mapping_basis")
            error(errors, isinstance(bases, list) and bool(bases), f"reference_mapping_basis_missing:{lesson_id}:{occurrence_id}")
            if isinstance(bases, list):
                error(errors, set(str(value) for value in bases).issubset(ALLOWED_BASES), f"reference_mapping_basis_invalid:{lesson_id}:{occurrence_id}")
            error(errors, reference.get("runtime_effect") == "OPTIONAL_TEACHING_REFERENCE_ONLY", f"reference_runtime_effect_invalid:{lesson_id}:{occurrence_id}")
            actual_transcript_lessons[transcript_id].add(lesson_id)
        error(errors, len(occurrence_ids) == len(set(occurrence_ids)), f"lesson_reference_duplicate:{lesson_id}")
        actual_reference_count += len(references)
        if skill in skill_actual:
            skill_actual[skill]["lesson_count"] += 1
            skill_actual[skill]["referenced_lesson_count"] += int(bool(references))
            skill_actual[skill]["unreferenced_lesson_count"] += int(not references)
            skill_actual[skill]["instructional_reference_count"] += len(references)

    disposition_counts: Counter[str] = Counter()
    for row in inventories:
        if not isinstance(row, Mapping):
            errors.append("transcript_inventory_row_invalid")
            continue
        transcript_id = str(row.get("transcript_id") or "")
        disposition = str(row.get("disposition") or "")
        error(errors, disposition in builder.DISPOSITIONS, f"transcript_disposition_invalid:{transcript_id}")
        expected_lessons = actual_transcript_lessons.get(transcript_id, set())
        error(errors, int(row.get("referenced_lesson_count", -1)) == len(expected_lessons), f"transcript_lesson_count_mismatch:{transcript_id}")
        expected_skills = sorted(
            str(lesson.get("skill") or "")
            for lesson in source_lessons
            if str(lesson.get("lesson_id") or "") in expected_lessons
        )
        error(errors, row.get("referenced_skills") == sorted(set(expected_skills)), f"transcript_skill_set_mismatch:{transcript_id}")
        if expected_lessons:
            error(errors, disposition == "USED_FOR_A1_A1PLUS", f"used_transcript_disposition_invalid:{transcript_id}")
        elif disposition == "USED_FOR_A1_A1PLUS":
            errors.append(f"used_transcript_has_no_lesson:{transcript_id}")
        disposition_counts[disposition] += 1

    summary = artifact.get("coverage_summary")
    error(errors, isinstance(summary, Mapping), "coverage_summary_missing")
    summary = summary if isinstance(summary, Mapping) else {}
    referenced_lesson_count = sum(bool(row.get("instructional_references")) for row in lessons if isinstance(row, Mapping))
    referenced_transcript_count = sum(bool(actual_transcript_lessons.get(transcript_id)) for transcript_id in EXPECTED_TRANSCRIPTS)
    baseline_summary = r3e_baseline.get("coverage_summary", {})
    baseline_lessons = int(baseline_summary.get("referenced_lesson_count", 0))
    baseline_transcripts = int(baseline_summary.get("referenced_transcript_count", 0))

    expected_summary = {
        "learning_lesson_count": len(lessons),
        "referenced_lesson_count": referenced_lesson_count,
        "unreferenced_lesson_count": len(lessons) - referenced_lesson_count,
        "instructional_reference_count": actual_reference_count,
        "transcript_count": len(inventories),
        "referenced_transcript_count": referenced_transcript_count,
        "unused_transcript_count": len(inventories) - referenced_transcript_count,
        "transcript_disposition_counts": {value: disposition_counts[value] for value in builder.DISPOSITIONS},
        "baseline_referenced_lesson_count": baseline_lessons,
        "baseline_referenced_transcript_count": baseline_transcripts,
        "referenced_lesson_delta": referenced_lesson_count - baseline_lessons,
        "referenced_transcript_delta": referenced_transcript_count - baseline_transcripts,
        "hard_graph_edge_delta": 0,
        "blocked_lesson_count": 0,
    }
    error(errors, dict(summary) == expected_summary, "coverage_summary_mismatch")
    error(errors, sum(disposition_counts.values()) == 99, "transcript_dispositions_not_exhaustive")
    error(errors, referenced_lesson_count > baseline_lessons, "referenced_lesson_coverage_not_increased")
    error(errors, referenced_transcript_count > baseline_transcripts, "referenced_transcript_coverage_not_increased")

    error(errors, artifact.get("skill_coverage_summary") == skill_actual, "skill_coverage_summary_mismatch")

    baseline_pairs = {
        (str(lesson.get("lesson_id") or ""), str(reference.get("evidence_occurrence_id") or ""))
        for lesson in r3e_baseline.get("lesson_instructional_references", [])
        if isinstance(lesson, Mapping)
        for reference in lesson.get("instructional_references", [])
        if isinstance(reference, Mapping)
    }
    actual_pairs = {
        (str(lesson.get("lesson_id") or ""), str(reference.get("evidence_occurrence_id") or ""))
        for lesson in lessons
        if isinstance(lesson, Mapping)
        for reference in lesson.get("instructional_references", [])
        if isinstance(reference, Mapping)
    }
    error(errors, baseline_pairs.issubset(actual_pairs), "r3e_baseline_reference_regression")

    rebuilt = builder.build_artifact(m1_graph, m2_consumer, cp07b_overlay, r3e_baseline)
    deterministic = rebuilt == artifact
    error(errors, deterministic, "deterministic_rebuild_mismatch")

    try:
        builder.walk_forbidden(artifact)
    except builder.R3GError as exc:
        errors.append(str(exc))

    return {
        "task_id": builder.TASK_ID,
        "schema_version": builder.SCHEMA_VERSION,
        "validation_status": builder.PASS_STATUS if not errors else "FAIL_CP07F_R3G_KET99_FULL_SEMANTIC_INVENTORY_AND_A1A1PLUS_COVERAGE_EXPANSION",
        "error_count": len(errors),
        "errors": errors,
        "transcript_count": len(inventories),
        "transcript_disposition_count": sum(disposition_counts.values()),
        "learning_lesson_count": len(lessons),
        "referenced_lesson_count": referenced_lesson_count,
        "referenced_transcript_count": referenced_transcript_count,
        "referenced_lesson_delta": referenced_lesson_count - baseline_lessons,
        "referenced_transcript_delta": referenced_transcript_count - baseline_transcripts,
        "deterministic_rebuild_matches": deterministic,
        "hard_graph_unchanged": summary.get("hard_graph_edge_delta") == 0,
        "a2_status": "LOCKED",
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILED",
        "next_short_step": artifact.get("next_short_step"),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--m1-graph", type=Path, default=builder.DEFAULT_M1)
    parser.add_argument("--m2-consumer", type=Path, default=builder.DEFAULT_M2)
    parser.add_argument("--cp07b-overlay", type=Path, default=builder.DEFAULT_CP07B)
    parser.add_argument("--r3e-baseline", type=Path, default=builder.DEFAULT_R3E)
    parser.add_argument("--report", type=Path, default=builder.DEFAULT_REPORT)
    args = parser.parse_args(argv)
    artifact = builder.read(args.artifact)
    report = validate_artifact(
        artifact,
        m1_graph=builder.read(args.m1_graph),
        m2_consumer=builder.read(args.m2_consumer),
        cp07b_overlay=builder.read(args.cp07b_overlay),
        r3e_baseline=builder.read(args.r3e_baseline),
    )
    builder.write(args.report, report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["validation_status"] == builder.PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
