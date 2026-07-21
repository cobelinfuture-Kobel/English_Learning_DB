#!/usr/bin/env python3
"""Recheck RAZ A-I A1/A1+ candidate counts and bind approved Theme actions.

This consumer separates source totals, A1/A1+ observational candidates, and
Authority-matched candidates. It does not promote RAZ text, write canonical
Theme Authority, open A2/A2+, or emit source text/title.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_derived_material_extraction_minimal as material
from ulga.builders import build_raz_aw_theme_gap_evidence_topic_review as contextual

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AI_A1A1PlusCoverageRecheckAndApprovedThemeBinding"
SCHEMA_VERSION = "raz.ai.a1_a1plus_coverage_recheck.v1"
PASS_STATUS = "PASS_RAZ_AI_A1_A1PLUS_COVERAGE_RECHECK"
SCOPE_LEVELS = tuple(chr(code) for code in range(ord("A"), ord("I") + 1))

EXPECTED_BOOK_COUNT = 830
EXPECTED_PAGE_UNIT_COUNT = 7957
EXPECTED_SENTENCE_COUNT = 15818
EXPECTED_REUSE_UNIT_COUNT = 4690
EXPECTED_TOTAL_UNIT_COUNT = 12647

DEFAULT_MATERIAL = (
    REPO_ROOT
    / ".local/raz_aw/derived_material_extraction_minimal/"
    / "derived_material_extraction_minimal.safe.json"
)
DEFAULT_CONTEXTUAL = (
    REPO_ROOT
    / ".local/raz_aw/theme_gap_evidence_topic_review/"
    / "theme_gap_evidence_topic_review.safe.json"
)
DEFAULT_SOURCE_ROOT = REPO_ROOT / "raz_output_jsons"
DEFAULT_THEME_AUTHORITY = REPO_ROOT / "ulga/graph/theme_nodes.json"
DEFAULT_OUTPUT = (
    REPO_ROOT
    / ".local/raz_ai/a1_a1plus_coverage_recheck/"
    / "a1_a1plus_coverage_recheck.safe.json"
)

APPROVED_THEME_ACTIONS = (
    {
        "source_macro_theme_family_id": "animals_and_habitats",
        "decision": "APPROVE",
        "action": "ADD_A1_THEME",
        "candidate_target_refs": ["theme_candidate:a1_animals_and_habitats"],
    },
    {
        "source_macro_theme_family_id": "nature_and_environment",
        "decision": "APPROVE",
        "action": "ADD_A1_THEME",
        "candidate_target_refs": ["theme_candidate:a1_nature_and_environment"],
    },
    {
        "source_macro_theme_family_id": "holidays_and_culture",
        "decision": "APPROVE",
        "action": "ADD_A1_THEME",
        "candidate_target_refs": ["theme_candidate:a1_holidays_and_culture"],
    },
    {
        "source_macro_theme_family_id": "feelings_character_and_social_emotional",
        "decision": "APPROVE",
        "action": "EXPAND_EXISTING_A1_THEME_AND_KEEP_SEL_SEPARATE",
        "candidate_target_refs": [
            "theme:a1_personal_information_and_greetings",
            "sel_domain:social_emotional_learning",
        ],
    },
)

CLAIM_BOUNDARIES = {
    "source_text_read_for_counting_only": True,
    "source_text_included_in_output": False,
    "source_title_included_in_output": False,
    "operator_theme_decision_bound": True,
    "canonical_theme_write_performed": False,
    "authority_promotion_performed": False,
    "learner_facing_content_created": False,
    "a2_a2plus_opened": False,
    "a_i_is_observational_candidate_scope_not_cefr_equivalence": True,
}


class CoverageRecheckError(ValueError):
    """Fail-closed package, source, identity, or accounting error."""


def _verify_hash(package: Mapping[str, Any], label: str) -> None:
    claimed = package.get("package_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise CoverageRecheckError(f"{label}_package_sha256_invalid")
    reconstructed = dict(package)
    reconstructed.pop("package_sha256", None)
    if deep.sha256_value(reconstructed) != claimed:
        raise CoverageRecheckError(f"{label}_package_sha256_mismatch")


def _verify_material(package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if package.get("task_id") != material.TASK_ID:
        raise CoverageRecheckError("material_task_id_mismatch")
    if package.get("validation_status") != material.PASS_STATUS:
        raise CoverageRecheckError("material_validation_status_not_pass")
    if package.get("errors") != []:
        raise CoverageRecheckError("material_errors_not_empty")
    _verify_hash(package, "material")
    rows = package.get("page_unit_evidence")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise CoverageRecheckError("material_page_unit_evidence_invalid")
    return rows


def _verify_contextual(package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if package.get("task_id") != contextual.TASK_ID:
        raise CoverageRecheckError("contextual_task_id_mismatch")
    if package.get("validation_status") != contextual.PASS_STATUS:
        raise CoverageRecheckError("contextual_validation_status_not_pass")
    if package.get("errors") != []:
        raise CoverageRecheckError("contextual_errors_not_empty")
    gate = package.get("placement_gate")
    if not isinstance(gate, Mapping) or gate.get("decision") != (
        "CONTEXTUAL_THEME_AND_TOPIC_PLACEMENTS_READY"
    ):
        raise CoverageRecheckError("contextual_gate_not_ready")
    _verify_hash(package, "contextual")
    rows = package.get("contextual_theme_family_placements")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise CoverageRecheckError("contextual_theme_rows_invalid")
    return rows


def _discover(source_root: Path, level: str, filename: str) -> Path:
    candidates = [
        source_root / "derived" / f"Level_{level}" / "enriched" / filename,
        source_root / "derived" / f"Level_{level}" / "normalized" / filename,
        source_root / f"Level_{level}" / "enriched" / filename,
        source_root / f"Level_{level}" / "normalized" / filename,
        source_root / filename,
    ]
    present = [path.resolve() for path in candidates if path.is_file()]
    if not present:
        present = [path.resolve() for path in source_root.rglob(filename)]
    unique = sorted(set(present))
    if len(unique) != 1:
        raise CoverageRecheckError(
            f"source_file_resolution_not_unique:{level}:{filename}:{len(unique)}"
        )
    return unique[0]


def _records(path: Path) -> list[Mapping[str, Any]]:
    payload = deep.read_json(path)
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, Mapping) and isinstance(payload.get("records"), list):
        rows = payload["records"]
    else:
        raise CoverageRecheckError(f"records_unavailable:{path}")
    if not all(isinstance(row, Mapping) for row in rows):
        raise CoverageRecheckError(f"record_not_object:{path}")
    return list(rows)


def load_scope_inventory(
    source_root: Path,
    *,
    levels: Sequence[str] = SCOPE_LEVELS,
) -> dict[str, Any]:
    per_level: list[dict[str, Any]] = []
    source_files: list[dict[str, Any]] = []
    for level in levels:
        books_path = _discover(source_root, level, f"raz_{level}_enriched_books.json")
        sentences_path = _discover(
            source_root, level, f"raz_{level}_enriched_sentences.json"
        )
        pages_path = _discover(source_root, level, f"raz_{level}_page_unit_enriched.json")
        reuse_path = _discover(
            source_root, level, f"raz_{level}_normalized_reuse_units.json"
        )
        books = _records(books_path)
        sentences = _records(sentences_path)
        pages = _records(pages_path)
        reuse = _records(reuse_path)
        sentence_count_from_pages = sum(int(row.get("sentence_count") or 0) for row in pages)
        if sentence_count_from_pages != len(sentences):
            raise CoverageRecheckError(
                f"sentence_count_reconciliation_failed:{level}:"
                f"{sentence_count_from_pages}:{len(sentences)}"
            )
        per_level.append(
            {
                "level": level,
                "book_count": len(books),
                "page_unit_count": len(pages),
                "sentence_count": len(sentences),
                "reuse_unit_count": len(reuse),
                "total_unit_count": len(pages) + len(reuse),
            }
        )
        for kind, path, count in (
            ("books", books_path, len(books)),
            ("sentences", sentences_path, len(sentences)),
            ("page_units", pages_path, len(pages)),
            ("reuse_units", reuse_path, len(reuse)),
        ):
            source_files.append(
                {
                    "level": level,
                    "kind": kind,
                    "path": path.relative_to(source_root).as_posix()
                    if path.is_relative_to(source_root)
                    else str(path),
                    "record_count": count,
                    "sha256": deep.sha256_file(path),
                }
            )
    return {
        "levels": list(levels),
        "book_count": sum(row["book_count"] for row in per_level),
        "page_unit_count": sum(row["page_unit_count"] for row in per_level),
        "sentence_count": sum(row["sentence_count"] for row in per_level),
        "reuse_unit_count": sum(row["reuse_unit_count"] for row in per_level),
        "total_unit_count": sum(row["total_unit_count"] for row in per_level),
        "per_level": per_level,
        "source_files": source_files,
    }


def _theme_baseline(theme_rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = Counter(str(row.get("cefr_level") or "") for row in theme_rows)
    return {
        "existing_a1_theme_count": counts["A1"],
        "existing_a1plus_theme_count": counts["A1_plus"],
        "approved_new_a1_theme_count": sum(
            row["action"] == "ADD_A1_THEME" for row in APPROVED_THEME_ACTIONS
        ),
        "projected_a1_theme_count_after_binding": counts["A1"]
        + sum(row["action"] == "ADD_A1_THEME" for row in APPROVED_THEME_ACTIONS),
        "projected_a1plus_theme_count_after_binding": counts["A1_plus"],
    }


def build_package(
    material_package: Mapping[str, Any],
    contextual_package: Mapping[str, Any],
    scope_inventory: Mapping[str, Any],
    theme_rows: Sequence[Mapping[str, Any]],
    *,
    expected_book_count: int = EXPECTED_BOOK_COUNT,
    expected_page_unit_count: int = EXPECTED_PAGE_UNIT_COUNT,
    expected_sentence_count: int = EXPECTED_SENTENCE_COUNT,
    expected_reuse_unit_count: int = EXPECTED_REUSE_UNIT_COUNT,
    expected_total_unit_count: int = EXPECTED_TOTAL_UNIT_COUNT,
) -> dict[str, Any]:
    material_rows = _verify_material(material_package)
    contextual_rows = _verify_contextual(contextual_package)
    approved_family_ids = {
        row["source_macro_theme_family_id"] for row in APPROVED_THEME_ACTIONS
    }
    contextual_by_family = {
        str(row.get("source_macro_theme_family_id")): row for row in contextual_rows
    }
    if not approved_family_ids <= set(contextual_by_family):
        raise CoverageRecheckError(
            "approved_theme_family_missing:"
            + ",".join(sorted(approved_family_ids - set(contextual_by_family)))
        )

    scope_rows = [
        row for row in material_rows if str(row.get("source_level") or "") in SCOPE_LEVELS
    ]
    if len(scope_rows) != expected_page_unit_count:
        raise CoverageRecheckError(
            f"material_scope_page_unit_count_mismatch:{len(scope_rows)}:"
            f"{expected_page_unit_count}"
        )

    def aggregate(key: str) -> set[str]:
        return {
            str(value)
            for row in scope_rows
            for value in row.get(key, [])
            if isinstance(value, str) and value
        }

    maturity_counts = Counter(str(row.get("sentence_seed_maturity") or "") for row in scope_rows)
    skill_counts: Counter[str] = Counter()
    for row in scope_rows:
        skill_counts.update(
            str(value)
            for value in row.get("four_skill_affordances", [])
            if isinstance(value, str) and value
        )
    promoted_count = sum(
        row.get("promotion_status") not in {None, "NOT_PROMOTED", "promotion_blocked"}
        for row in scope_rows
    )
    authority_matched_page_count = sum(
        bool(row.get("matched_vocabulary_refs"))
        and bool(row.get("matched_grammar_unit_refs"))
        for row in scope_rows
    )

    inventory = dict(scope_inventory)
    checks = {
        "scope_levels_exact": set(inventory.get("levels", [])) == set(SCOPE_LEVELS),
        "book_count_exact": inventory.get("book_count") == expected_book_count,
        "page_unit_count_exact": inventory.get("page_unit_count")
        == expected_page_unit_count,
        "sentence_count_exact": inventory.get("sentence_count")
        == expected_sentence_count,
        "reuse_unit_count_exact": inventory.get("reuse_unit_count")
        == expected_reuse_unit_count,
        "total_unit_count_exact": inventory.get("total_unit_count")
        == expected_total_unit_count,
        "material_scope_reconciled": len(scope_rows) == inventory.get("page_unit_count"),
        "approved_theme_action_count_exact": len(APPROVED_THEME_ACTIONS) == 4,
        "approved_theme_families_have_context_evidence": all(
            int(contextual_by_family[family].get("source_unit_count") or 0) > 0
            for family in approved_family_ids
        ),
        "final_promoted_count_zero": promoted_count == 0,
    }
    ready = all(checks.values())

    package: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS if ready else "FAIL",
        "input_identity": {
            "material_task_id": material_package["task_id"],
            "material_package_sha256": material_package["package_sha256"],
            "contextual_task_id": contextual_package["task_id"],
            "contextual_package_sha256": contextual_package["package_sha256"],
        },
        "approved_theme_decision_binding": {
            "decision_count": len(APPROVED_THEME_ACTIONS),
            "decisions": [dict(row) for row in APPROVED_THEME_ACTIONS],
            "decision_status": "OPERATOR_APPROVED_READY_FOR_CANONICAL_BINDING",
        },
        "theme_authority_projection": _theme_baseline(theme_rows),
        "source_total_summary": {
            "level_count": len(material_package.get("source_scope", {}).get("levels", [])),
            "book_count": material_package.get("source_scope", {}).get("book_count"),
            "page_unit_count": material_package.get("source_scope", {}).get("page_unit_count"),
            "matched_vocabulary_ref_count": material_package.get("aggregate_summary", {}).get(
                "matched_vocabulary_ref_count"
            ),
            "matched_chunk_ref_count": material_package.get("aggregate_summary", {}).get(
                "matched_chunk_ref_count"
            ),
            "matched_pattern_ref_count": material_package.get("aggregate_summary", {}).get(
                "matched_pattern_ref_count"
            ),
            "matched_grammar_unit_ref_count": material_package.get(
                "aggregate_summary", {}
            ).get("matched_grammar_unit_ref_count"),
        },
        "a1_a1plus_observational_candidate_summary": {
            "scope_levels": list(SCOPE_LEVELS),
            "scope_semantics": "OBSERVATIONAL_CANDIDATE_NOT_CEFR_EQUIVALENCE",
            "book_count": inventory["book_count"],
            "page_unit_count": inventory["page_unit_count"],
            "sentence_count": inventory["sentence_count"],
            "reuse_unit_count": inventory["reuse_unit_count"],
            "total_unit_count": inventory["total_unit_count"],
            "passage_seed_count": sum(
                row.get("passage_seed_status") == "SUPPORTED" for row in scope_rows
            ),
            "semantic_duplicate_group_count": len(
                {str(row.get("semantic_duplicate_group_id")) for row in scope_rows}
            ),
        },
        "a1_a1plus_authority_matched_candidate_summary": {
            "matched_vocabulary_ref_count": len(aggregate("matched_vocabulary_refs")),
            "matched_chunk_ref_count": len(aggregate("matched_chunk_refs")),
            "matched_pattern_ref_count": len(aggregate("matched_pattern_refs")),
            "matched_grammar_unit_ref_count": len(
                aggregate("matched_grammar_unit_refs")
            ),
            "authority_matched_page_unit_count": authority_matched_page_count,
            "sentence_seed_maturity_counts": dict(sorted(maturity_counts.items())),
            "four_skill_affordance_counts": dict(sorted(skill_counts.items())),
            "final_promoted_page_unit_count": promoted_count,
            "status": "CANDIDATE_COUNTS_CONFIRMED_FINAL_PROMOTION_PENDING",
        },
        "scope_inventory": inventory,
        "coverage_gate": {
            "source_checks": checks,
            "decision": (
                "A1_A1PLUS_CANDIDATE_COUNTS_CONFIRMED_FINAL_PROMOTION_PENDING"
                if ready
                else "BLOCKED_A1_A1PLUS_COVERAGE_RECHECK"
            ),
            "source_totals_confirmed": True,
            "observational_candidate_counts_confirmed": ready,
            "authority_matched_candidate_counts_confirmed": ready,
            "final_promoted_counts_confirmed": False,
            "ready_for_canonical_theme_binding": ready,
            "ready_for_learner_content_promotion": False,
        },
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "errors": [],
    }
    leakage = contextual.matching.scan_forbidden_safe_keys(package)
    if leakage:
        raise CoverageRecheckError("safe_output_leakage:" + ";".join(leakage[:20]))
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _readback(package: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "decision": package["coverage_gate"]["decision"],
        "approved_theme_action_count": package["approved_theme_decision_binding"][
            "decision_count"
        ],
        **package["a1_a1plus_observational_candidate_summary"],
        **package["a1_a1plus_authority_matched_candidate_summary"],
        "projected_a1_theme_count_after_binding": package[
            "theme_authority_projection"
        ]["projected_a1_theme_count_after_binding"],
        "projected_a1plus_theme_count_after_binding": package[
            "theme_authority_projection"
        ]["projected_a1plus_theme_count_after_binding"],
        "package_sha256": package["package_sha256"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--material-package", type=Path, default=DEFAULT_MATERIAL)
    parser.add_argument("--contextual-package", type=Path, default=DEFAULT_CONTEXTUAL)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--theme-authority", type=Path, default=DEFAULT_THEME_AUTHORITY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        material_package = deep.read_json(args.material_package)
        contextual_package = deep.read_json(args.contextual_package)
        theme_rows = deep.read_json(args.theme_authority)
        if not isinstance(material_package, Mapping):
            raise CoverageRecheckError("material_package_not_object")
        if not isinstance(contextual_package, Mapping):
            raise CoverageRecheckError("contextual_package_not_object")
        if not isinstance(theme_rows, list) or not all(
            isinstance(row, Mapping) for row in theme_rows
        ):
            raise CoverageRecheckError("theme_authority_rows_invalid")
        package = build_package(
            material_package,
            contextual_package,
            load_scope_inventory(args.source_root),
            theme_rows,
        )
        deep.write_json_atomic(args.output, package)
        print(json.dumps(_readback(package), sort_keys=True))
        return 0
    except (
        CoverageRecheckError,
        contextual.ThemeGapEvidenceError,
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
