#!/usr/bin/env python3
"""Classify RAZ A-W page-unit evidence for A1/A1+ material admission.

S01 consumes the verified A-W text-free material package and the verified S00
A1/A1+ coverage package.  It classifies every page unit exactly once, defers
J-W without opening A2/A2+, and emits no source text or title.

RAZ level is used only to select the approved A-I observational scope.  It is
never treated as CEFR equivalence.  A1 versus A1+ candidate classification is
based on canonical Authority matches, grammar-unit signals, discourse shape,
seed maturity, and exact semantic-duplicate identity.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_derived_material_extraction_minimal as material
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_aw_theme_gap_evidence_topic_review as contextual
from ulga.builders import build_raz_ai_a1_a1plus_coverage_recheck as coverage

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AI-ACL-V1-S01_MaterialAdmissionClassification"
SCHEMA_VERSION = "raz.ai.acl.v1.s01.material_admission.v1"
PASS_STATUS = "PASS_RAZ_AI_ACL_V1_S01_MATERIAL_ADMISSION"

A1_A1PLUS_LEVELS = tuple(chr(code) for code in range(ord("A"), ord("I") + 1))
DEFERRED_LEVELS = tuple(chr(code) for code in range(ord("J"), ord("W") + 1))
EXPECTED_TOTAL_PAGE_UNIT_COUNT = 22632
EXPECTED_SCOPE_PAGE_UNIT_COUNT = 7957
EXPECTED_SCOPE_DUPLICATE_GROUP_COUNT = 7849
EXPECTED_DEFERRED_PAGE_UNIT_COUNT = 14675

DEFAULT_MATERIAL = (
    REPO_ROOT
    / ".local/raz_aw/derived_material_extraction_minimal/"
    / "derived_material_extraction_minimal.safe.json"
)
DEFAULT_COVERAGE = (
    REPO_ROOT
    / ".local/raz_ai/a1_a1plus_coverage_recheck/"
    / "a1_a1plus_coverage_recheck.safe.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT
    / ".local/raz_ai/acl_v1_s01_material_admission/"
    / "material_admission_classification.safe.json"
)

ADMISSION_STATUSES = {
    "A1_READY_CANDIDATE",
    "A1PLUS_READY_CANDIDATE",
    "REWRITE_REQUIRED",
    "SUPPORT_ONLY",
    "DUPLICATE_CANDIDATE",
    "DEFERRED_A2_A2PLUS",
    "REJECTED_UNUSABLE",
}
READY_STATUSES = {"A1_READY_CANDIDATE", "A1PLUS_READY_CANDIDATE"}

# These are still A1-family Learning Units in the grammar graph.  They are used
# as A1+ spiral-placement signals because they add tense, polarity, clause,
# object, frequency, or coordination complexity beyond the basic A1 core.
A1PLUS_SIGNAL_GRAMMAR_UNITS = {
    "GRAMMAR_OBJECT_PRONOUNS_BASIC",
    "GRAMMAR_PRESENT_SIMPLE_NEGATIVES",
    "GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS",
    "GRAMMAR_WILL_FUTURE_A1",
    "GRAMMAR_PAST_SIMPLE_A1",
    "GRAMMAR_COORDINATION_A1",
    "GRAMMAR_BECAUSE_REASON_CLAUSES_A1",
    "GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1",
    "GRAMMAR_ADVERB_PHRASES_A1",
}
A1PLUS_SIGNAL_DISCOURSE = {
    "sequence",
    "cause_effect",
    "comparison_or_contrast",
}

APPROVED_THEME_CANDIDATE_REFS = {
    target
    for action in coverage.APPROVED_THEME_ACTIONS
    for target in action["candidate_target_refs"]
    if target.startswith("theme_candidate:")
}

CLAIM_BOUNDARIES = {
    "source_text_read_performed": False,
    "source_text_included_in_output": False,
    "source_title_included_in_output": False,
    "raz_level_used_as_cefr_equivalence": False,
    "a_i_used_as_observational_candidate_scope": True,
    "a2_a2plus_semantic_admission_performed": False,
    "a2_a2plus_rows_deferred_without_promotion": True,
    "human_content_approval_fabricated": False,
    "canonical_authority_write_performed": False,
    "authority_promotion_performed": False,
    "learner_facing_content_created": False,
}


class MaterialAdmissionError(ValueError):
    """Fail-closed package, identity, accounting, or boundary error."""


def _verify_hash(package: Mapping[str, Any], label: str) -> None:
    claimed = package.get("package_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise MaterialAdmissionError(f"{label}_package_sha256_invalid")
    reconstructed = dict(package)
    reconstructed.pop("package_sha256", None)
    if deep.sha256_value(reconstructed) != claimed:
        raise MaterialAdmissionError(f"{label}_package_sha256_mismatch")


def _verify_material(
    package: Mapping[str, Any], *, expected_total_page_unit_count: int
) -> list[Mapping[str, Any]]:
    if package.get("task_id") != material.TASK_ID:
        raise MaterialAdmissionError("material_task_id_mismatch")
    if package.get("validation_status") != material.PASS_STATUS:
        raise MaterialAdmissionError("material_validation_status_not_pass")
    if package.get("errors") != []:
        raise MaterialAdmissionError("material_errors_not_empty")
    _verify_hash(package, "material")
    rows = package.get("page_unit_evidence")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise MaterialAdmissionError("material_page_unit_evidence_invalid")
    if len(rows) != expected_total_page_unit_count:
        raise MaterialAdmissionError(
            f"material_page_unit_count_mismatch:{len(rows)}:"
            f"{expected_total_page_unit_count}"
        )
    return rows


def _verify_coverage(
    package: Mapping[str, Any],
    material_package: Mapping[str, Any],
    *,
    expected_scope_page_unit_count: int,
    expected_scope_duplicate_group_count: int,
) -> None:
    if package.get("task_id") != coverage.TASK_ID:
        raise MaterialAdmissionError("coverage_task_id_mismatch")
    if package.get("validation_status") != coverage.PASS_STATUS:
        raise MaterialAdmissionError("coverage_validation_status_not_pass")
    if package.get("errors") != []:
        raise MaterialAdmissionError("coverage_errors_not_empty")
    _verify_hash(package, "coverage")
    gate = package.get("coverage_gate")
    if not isinstance(gate, Mapping) or gate.get("decision") != (
        "A1_A1PLUS_CANDIDATE_COUNTS_CONFIRMED_FINAL_PROMOTION_PENDING"
    ):
        raise MaterialAdmissionError("coverage_gate_not_ready")
    identity = package.get("input_identity")
    if not isinstance(identity, Mapping) or identity.get(
        "material_package_sha256"
    ) != material_package.get("package_sha256"):
        raise MaterialAdmissionError("coverage_material_identity_mismatch")
    observational = package.get("a1_a1plus_observational_candidate_summary")
    matched = package.get("a1_a1plus_authority_matched_candidate_summary")
    decisions = package.get("approved_theme_decision_binding")
    if not isinstance(observational, Mapping) or not isinstance(matched, Mapping):
        raise MaterialAdmissionError("coverage_summaries_missing")
    if observational.get("page_unit_count") != expected_scope_page_unit_count:
        raise MaterialAdmissionError("coverage_scope_page_unit_count_mismatch")
    if (
        observational.get("semantic_duplicate_group_count")
        != expected_scope_duplicate_group_count
    ):
        raise MaterialAdmissionError("coverage_duplicate_group_count_mismatch")
    if matched.get("final_promoted_page_unit_count") != 0:
        raise MaterialAdmissionError("coverage_promoted_count_not_zero")
    if not isinstance(decisions, Mapping) or decisions.get("decision_count") != 4:
        raise MaterialAdmissionError("approved_theme_decision_binding_missing")
    if decisions.get("decision_status") != (
        "OPERATOR_APPROVED_READY_FOR_CANONICAL_BINDING"
    ):
        raise MaterialAdmissionError("approved_theme_decision_status_invalid")


def _strings(row: Mapping[str, Any], key: str) -> set[str]:
    values = row.get(key, [])
    if not isinstance(values, list):
        raise MaterialAdmissionError(f"row_list_field_invalid:{key}")
    return {str(value) for value in values if isinstance(value, str) and value}


def _candidate_theme_refs(row: Mapping[str, Any]) -> set[str]:
    refs: set[str] = set()
    for label in _strings(row, "source_macro_theme_labels"):
        direct = matching.SOURCE_MACRO_THEME_ALIASES.get(matching._normal_label(label))
        if direct is not None:
            refs.add(direct)
            continue
        try:
            family = matching._source_macro_family(label)
        except matching.ThemeAuthorityCandidateMatchingError as exc:
            raise MaterialAdmissionError(
                f"source_macro_theme_label_unrecognized:{label}"
            ) from exc
        placement = contextual.GAP_FAMILY_PLACEMENTS.get(family)
        if placement is None:
            continue
        refs.update(
            str(target)
            for target in placement.get("candidate_target_refs", [])
            if isinstance(target, str)
            and (target.startswith("theme:") or target.startswith("theme_candidate:"))
        )
    unapproved = {
        ref
        for ref in refs
        if ref.startswith("theme_candidate:")
        and ref not in APPROVED_THEME_CANDIDATE_REFS
    }
    if unapproved:
        raise MaterialAdmissionError(
            "unapproved_theme_candidate_ref:" + ",".join(sorted(unapproved))
        )
    return refs


def _duplicate_representatives(
    scope_rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, str], int]:
    members: dict[str, list[str]] = defaultdict(list)
    for row in scope_rows:
        ref = str(row.get("source_unit_ref") or "")
        group = str(row.get("semantic_duplicate_group_id") or "")
        if not ref or not group:
            raise MaterialAdmissionError(f"scope_identity_or_duplicate_group_missing:{ref}")
        members[group].append(ref)
    representatives = {group: min(refs) for group, refs in members.items()}
    duplicate_count = sum(len(refs) - 1 for refs in members.values())
    return representatives, duplicate_count


def _classify_scope_row(
    row: Mapping[str, Any], *, duplicate_representative: str
) -> tuple[str, str, list[str]]:
    ref = str(row.get("source_unit_ref") or "")
    if ref != duplicate_representative:
        return (
            "DUPLICATE_CANDIDATE",
            "NONE",
            ["EXACT_NORMALIZED_TEXT_DUPLICATE_NON_REPRESENTATIVE"],
        )

    vocabulary = _strings(row, "matched_vocabulary_refs")
    grammar = _strings(row, "matched_grammar_unit_refs")
    chunks = _strings(row, "matched_chunk_refs")
    patterns = _strings(row, "matched_pattern_refs")
    skills = _strings(row, "four_skill_affordances")
    discourse = str(row.get("discourse_shape") or "")
    maturity = str(row.get("sentence_seed_maturity") or "")
    passage_supported = row.get("passage_seed_status") == "SUPPORTED"

    if vocabulary and grammar:
        plus_signals: list[str] = []
        grammar_signals = sorted(grammar & A1PLUS_SIGNAL_GRAMMAR_UNITS)
        if grammar_signals:
            plus_signals.append("A1PLUS_GRAMMAR_SIGNAL")
        if discourse in A1PLUS_SIGNAL_DISCOURSE:
            plus_signals.append("A1PLUS_DISCOURSE_SIGNAL")
        if plus_signals:
            return (
                "A1PLUS_READY_CANDIDATE",
                "A1_PLUS",
                plus_signals + ["VOCABULARY_AND_GRAMMAR_AUTHORITY_MATCHED"],
            )
        return (
            "A1_READY_CANDIDATE",
            "A1",
            ["VOCABULARY_AND_GRAMMAR_AUTHORITY_MATCHED", maturity or "SEED_PRESENT"],
        )

    if vocabulary or grammar:
        reasons = ["PARTIAL_AUTHORITY_MATCH_REQUIRES_CONTROLLED_REWRITE"]
        if vocabulary:
            reasons.append("VOCABULARY_MATCHED_GRAMMAR_MISSING")
        if grammar:
            reasons.append("GRAMMAR_MATCHED_VOCABULARY_MISSING")
        return "REWRITE_REQUIRED", "A1_A1PLUS_UNRESOLVED", reasons

    support_evidence = bool(chunks or patterns or passage_supported or (skills - {"READING_SOURCE"}))
    if support_evidence:
        return (
            "SUPPORT_ONLY",
            "NONE",
            ["NO_VOCABULARY_OR_GRAMMAR_MATCH", "NON_CANONICAL_TEACHER_SUPPORT_VALUE"],
        )
    return (
        "REJECTED_UNUSABLE",
        "NONE",
        ["NO_AUTHORITY_MATCH_OR_DISTINCT_TEACHING_SUPPORT"],
    )


def build_package(
    material_package: Mapping[str, Any],
    coverage_package: Mapping[str, Any],
    *,
    expected_total_page_unit_count: int = EXPECTED_TOTAL_PAGE_UNIT_COUNT,
    expected_scope_page_unit_count: int = EXPECTED_SCOPE_PAGE_UNIT_COUNT,
    expected_scope_duplicate_group_count: int = EXPECTED_SCOPE_DUPLICATE_GROUP_COUNT,
    expected_deferred_page_unit_count: int = EXPECTED_DEFERRED_PAGE_UNIT_COUNT,
) -> dict[str, Any]:
    rows = _verify_material(
        material_package,
        expected_total_page_unit_count=expected_total_page_unit_count,
    )
    _verify_coverage(
        coverage_package,
        material_package,
        expected_scope_page_unit_count=expected_scope_page_unit_count,
        expected_scope_duplicate_group_count=expected_scope_duplicate_group_count,
    )

    refs = [str(row.get("source_unit_ref") or "") for row in rows]
    if any(not ref for ref in refs) or len(refs) != len(set(refs)):
        raise MaterialAdmissionError("material_ref_missing_or_duplicate")

    scope_rows = [
        row
        for row in rows
        if str(row.get("source_level") or "") in A1_A1PLUS_LEVELS
    ]
    deferred_rows = [
        row
        for row in rows
        if str(row.get("source_level") or "") in DEFERRED_LEVELS
    ]
    unknown_levels = {
        str(row.get("source_level") or "")
        for row in rows
        if str(row.get("source_level") or "")
        not in set(A1_A1PLUS_LEVELS) | set(DEFERRED_LEVELS)
    }
    if unknown_levels:
        raise MaterialAdmissionError(
            "source_level_outside_closed_scope:" + ",".join(sorted(unknown_levels))
        )
    if len(scope_rows) != expected_scope_page_unit_count:
        raise MaterialAdmissionError(
            f"scope_page_unit_count_mismatch:{len(scope_rows)}:"
            f"{expected_scope_page_unit_count}"
        )
    if len(deferred_rows) != expected_deferred_page_unit_count:
        raise MaterialAdmissionError(
            f"deferred_page_unit_count_mismatch:{len(deferred_rows)}:"
            f"{expected_deferred_page_unit_count}"
        )

    representatives, duplicate_count = _duplicate_representatives(scope_rows)
    if len(representatives) != expected_scope_duplicate_group_count:
        raise MaterialAdmissionError(
            f"scope_duplicate_group_count_mismatch:{len(representatives)}:"
            f"{expected_scope_duplicate_group_count}"
        )
    expected_duplicate_count = (
        expected_scope_page_unit_count - expected_scope_duplicate_group_count
    )
    if duplicate_count != expected_duplicate_count:
        raise MaterialAdmissionError(
            f"scope_duplicate_excess_count_mismatch:{duplicate_count}:"
            f"{expected_duplicate_count}"
        )

    output_rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    level_status_counts: dict[str, Counter[str]] = defaultdict(Counter)

    for row in sorted(rows, key=lambda item: str(item.get("source_unit_ref") or "")):
        ref = str(row["source_unit_ref"])
        level = str(row.get("source_level") or "")
        group = str(row.get("semantic_duplicate_group_id") or "")
        theme_refs = _candidate_theme_refs(row)
        if level in DEFERRED_LEVELS:
            status = "DEFERRED_A2_A2PLUS"
            candidate_scope = "DEFERRED_A2_A2PLUS"
            reasons = ["OUTSIDE_APPROVED_A1_A1PLUS_PROGRAM_SCOPE"]
            representative = None
        else:
            representative = representatives[group]
            status, candidate_scope, reasons = _classify_scope_row(
                row, duplicate_representative=representative
            )

        status_counts[status] += 1
        level_status_counts[level][status] += 1
        output_rows.append(
            {
                "source_unit_ref": ref,
                "source_level": level,
                "source_book_id": str(row.get("source_book_id") or ""),
                "admission_status": status,
                "candidate_cefr_scope": candidate_scope,
                "admission_reason_codes": reasons,
                "candidate_theme_refs": sorted(theme_refs),
                "matched_vocabulary_refs": sorted(
                    _strings(row, "matched_vocabulary_refs")
                ),
                "matched_chunk_refs": sorted(_strings(row, "matched_chunk_refs")),
                "matched_pattern_refs": sorted(_strings(row, "matched_pattern_refs")),
                "matched_grammar_unit_refs": sorted(
                    _strings(row, "matched_grammar_unit_refs")
                ),
                "semantic_duplicate_group_id": group,
                "duplicate_representative_source_unit_ref": representative,
                "sentence_seed_maturity": str(
                    row.get("sentence_seed_maturity") or ""
                ),
                "passage_seed_status": str(row.get("passage_seed_status") or ""),
                "discourse_shape": str(row.get("discourse_shape") or ""),
                "scene_structure": str(row.get("scene_structure") or ""),
                "four_skill_affordances": sorted(
                    _strings(row, "four_skill_affordances")
                ),
                "promotion_status": "NOT_PROMOTED",
            }
        )

    classified_refs = {row["source_unit_ref"] for row in output_rows}
    admitted_rows = [
        row for row in output_rows if row["admission_status"] in READY_STATUSES
    ]
    deferred_output = [
        row
        for row in output_rows
        if row["admission_status"] == "DEFERRED_A2_A2PLUS"
    ]
    checks = {
        "all_material_rows_classified_once": (
            len(output_rows) == expected_total_page_unit_count
            and classified_refs == set(refs)
        ),
        "admission_statuses_closed": all(
            row["admission_status"] in ADMISSION_STATUSES for row in output_rows
        ),
        "status_counts_reconcile": sum(status_counts.values()) == len(output_rows),
        "a_i_rows_not_deferred": all(
            row["admission_status"] != "DEFERRED_A2_A2PLUS"
            for row in output_rows
            if row["source_level"] in A1_A1PLUS_LEVELS
        ),
        "j_w_rows_all_deferred": len(deferred_output)
        == expected_deferred_page_unit_count
        and all(row["source_level"] in DEFERRED_LEVELS for row in deferred_output),
        "a2_a2plus_not_opened": all(
            row["candidate_cefr_scope"] != "A2"
            and row["candidate_cefr_scope"] != "A2_PLUS"
            for row in output_rows
        ),
        "duplicate_count_exact": status_counts["DUPLICATE_CANDIDATE"]
        == expected_duplicate_count,
        "ready_rows_have_vocabulary_and_grammar": all(
            row["matched_vocabulary_refs"] and row["matched_grammar_unit_refs"]
            for row in admitted_rows
        ),
        "approved_theme_candidates_only": all(
            ref in APPROVED_THEME_CANDIDATE_REFS
            for row in output_rows
            for ref in row["candidate_theme_refs"]
            if ref.startswith("theme_candidate:")
        ),
        "no_pending_admission_rows": all(
            row["admission_status"] != "PENDING" for row in output_rows
        ),
        "no_promoted_rows": all(
            row["promotion_status"] == "NOT_PROMOTED" for row in output_rows
        ),
    }
    ready = all(checks.values())

    package: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS if ready else "FAIL",
        "input_identity": {
            "material_task_id": material_package["task_id"],
            "material_package_sha256": material_package["package_sha256"],
            "coverage_task_id": coverage_package["task_id"],
            "coverage_package_sha256": coverage_package["package_sha256"],
        },
        "scope_contract": {
            "a1_a1plus_observational_levels": list(A1_A1PLUS_LEVELS),
            "deferred_levels": list(DEFERRED_LEVELS),
            "a_i_is_not_cefr_equivalence": True,
            "a2_a2plus_processing_status": "DEFERRED_NOT_OPENED",
        },
        "admission_rows": output_rows,
        "per_level_status_counts": {
            level: dict(sorted(counts.items()))
            for level, counts in sorted(level_status_counts.items())
        },
        "aggregate_summary": {
            "source_candidate_count": len(output_rows),
            "a1_a1plus_scope_candidate_count": len(scope_rows),
            "semantic_duplicate_group_count": len(representatives),
            "admission_status_counts": dict(sorted(status_counts.items())),
            "a1_ready_candidate_count": status_counts["A1_READY_CANDIDATE"],
            "a1plus_ready_candidate_count": status_counts[
                "A1PLUS_READY_CANDIDATE"
            ],
            "rewrite_required_count": status_counts["REWRITE_REQUIRED"],
            "support_only_count": status_counts["SUPPORT_ONLY"],
            "duplicate_candidate_count": status_counts["DUPLICATE_CANDIDATE"],
            "deferred_a2_a2plus_count": status_counts["DEFERRED_A2_A2PLUS"],
            "rejected_unusable_count": status_counts["REJECTED_UNUSABLE"],
            "ready_candidate_count": len(admitted_rows),
            "final_promoted_material_count": 0,
        },
        "admission_gate": {
            "source_checks": checks,
            "decision": (
                "MATERIAL_ADMISSION_CLASSIFICATION_READY"
                if ready
                else "BLOCKED_MATERIAL_ADMISSION_CLASSIFICATION"
            ),
            "distance_before": "D6",
            "distance_after": "D5" if ready else "D6",
            "ready_for_semantic_dedup": ready,
            "ready_for_canonical_linkage": False,
            "ready_for_material_promotion": False,
        },
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "errors": [],
    }
    leakage = matching.scan_forbidden_safe_keys(package)
    if leakage:
        raise MaterialAdmissionError(
            "safe_output_leakage:" + ";".join(leakage[:20])
        )
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _readback(package: Mapping[str, Any]) -> dict[str, Any]:
    summary = package["aggregate_summary"]
    return {
        "task_id": TASK_ID,
        "decision": package["admission_gate"]["decision"],
        "distance_after": package["admission_gate"]["distance_after"],
        **summary,
        "package_sha256": package["package_sha256"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--material-package", type=Path, default=DEFAULT_MATERIAL)
    parser.add_argument("--coverage-package", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        material_package = deep.read_json(args.material_package)
        coverage_package = deep.read_json(args.coverage_package)
        if not isinstance(material_package, Mapping):
            raise MaterialAdmissionError("material_package_not_object")
        if not isinstance(coverage_package, Mapping):
            raise MaterialAdmissionError("coverage_package_not_object")
        package = build_package(material_package, coverage_package)
        deep.write_json_atomic(args.output, package)
        print(json.dumps(_readback(package), sort_keys=True))
        return 0
    except (
        MaterialAdmissionError,
        matching.ThemeAuthorityCandidateMatchingError,
        contextual.ThemeGapEvidenceError,
        coverage.CoverageRecheckError,
        deep.AlignmentError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
