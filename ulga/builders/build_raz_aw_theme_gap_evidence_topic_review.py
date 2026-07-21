#!/usr/bin/env python3
"""Materialize safe review evidence for RAZ Theme gaps and topic labels.

Consumes the verified output of
``build_raz_aw_theme_authority_candidate_matching``. It does not reread RAZ
source text, modify Theme or Vocabulary Authority, fabricate human decisions,
or populate Learning Units.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AW_ThemeGapEvidenceAndTopicReview"
SCHEMA_VERSION = "raz.aw.theme_gap_evidence_topic_review.v1"
PASS_STATUS = "PASS_RAZ_AW_THEME_GAP_EVIDENCE_TOPIC_REVIEW"
EXPECTED_PAGE_UNIT_COUNT = 22632
EXPECTED_BOOK_COUNT = 1959
EXPECTED_GAP_FAMILY_COUNT = 10
EXPECTED_UNVERIFIED_TOPIC_LABEL_COUNT = 240
DEFAULT_INPUT = (
    REPO_ROOT
    / ".local/raz_aw/theme_authority_candidate_matching/"
    / "theme_authority_candidate_matching.safe.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT
    / ".local/raz_aw/theme_gap_evidence_topic_review/"
    / "theme_gap_evidence_topic_review.safe.json"
)

CLAIM_BOUNDARIES = {
    "candidate_matching_package_read_performed": True,
    "raz_source_text_read_performed": False,
    "review_bridge_linkage_read_performed": False,
    "human_semantic_review_performed": False,
    "human_decision_fabricated": False,
    "canonical_authority_write_performed": False,
    "authority_promotion_performed": False,
    "learning_unit_population_performed": False,
    "learner_facing_content_created": False,
    "a2_a2plus_opened": False,
}


class ThemeGapEvidenceError(ValueError):
    """Fail-closed input, identity, accounting, or leakage error."""


def _verify_input(
    package: Mapping[str, Any],
    *,
    expected_page_unit_count: int,
    expected_book_count: int,
) -> tuple[list[Mapping[str, Any]], set[str], set[str]]:
    if package.get("task_id") != matching.TASK_ID:
        raise ThemeGapEvidenceError("matching_task_id_mismatch")
    if package.get("validation_status") != matching.PASS_STATUS:
        raise ThemeGapEvidenceError("matching_validation_status_not_pass")
    if package.get("errors") != []:
        raise ThemeGapEvidenceError("matching_errors_not_empty")
    gate = package.get("matching_gate")
    if not isinstance(gate, Mapping) or gate.get("decision") != (
        "THEME_AUTHORITY_CANDIDATES_READY_FOR_LOCAL_VALIDATION"
    ):
        raise ThemeGapEvidenceError("matching_gate_not_ready")

    claimed_hash = package.get("package_sha256")
    if not isinstance(claimed_hash, str) or len(claimed_hash) != 64:
        raise ThemeGapEvidenceError("matching_package_sha256_invalid")
    reconstructed = dict(package)
    reconstructed.pop("package_sha256", None)
    if deep.sha256_value(reconstructed) != claimed_hash:
        raise ThemeGapEvidenceError("matching_package_sha256_mismatch")

    identity = package.get("input_material_identity")
    if not isinstance(identity, Mapping):
        raise ThemeGapEvidenceError("input_material_identity_missing")
    if identity.get("page_unit_count") != expected_page_unit_count:
        raise ThemeGapEvidenceError("page_unit_count_mismatch")
    if identity.get("book_count") != expected_book_count:
        raise ThemeGapEvidenceError("book_count_mismatch")

    rows = package.get("theme_subtheme_candidates")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise ThemeGapEvidenceError("candidate_rows_invalid")
    if len(rows) != expected_page_unit_count:
        raise ThemeGapEvidenceError("candidate_row_count_mismatch")
    refs = [str(row.get("source_unit_ref") or "") for row in rows]
    if any(not ref for ref in refs) or len(refs) != len(set(refs)):
        raise ThemeGapEvidenceError("candidate_ref_invalid_or_duplicate")

    family_rows = package.get("source_macro_theme_family_candidates")
    if not isinstance(family_rows, list):
        raise ThemeGapEvidenceError("source_macro_theme_family_candidates_missing")
    gap_ids = {
        str(row.get("source_macro_theme_family_id"))
        for row in family_rows
        if isinstance(row, Mapping)
        and row.get("coverage_status") == "AUTHORITY_GAP_CANDIDATE"
    }

    topic = package.get("source_topic_label_classification")
    if not isinstance(topic, Mapping):
        raise ThemeGapEvidenceError("source_topic_label_classification_missing")
    unverified = topic.get("unverified_source_topic_labels")
    if not isinstance(unverified, list) or not all(isinstance(value, str) for value in unverified):
        raise ThemeGapEvidenceError("unverified_source_topic_labels_invalid")

    leakage = matching.scan_forbidden_safe_keys(package)
    if leakage:
        raise ThemeGapEvidenceError("matching_package_safe_output_leakage:" + ";".join(leakage[:20]))
    return rows, gap_ids, set(unverified)


def _review_route(label_type: str) -> str:
    if label_type == "COMPOUND_OR_MULTIWORD_TOPIC_TAG":
        return "TOPIC_TAG_SEMANTIC_REVIEW"
    if label_type in {
        "UNVERIFIED_INFLECTED_SINGLE_TOKEN",
        "UNVERIFIED_PLURAL_OR_THIRD_PERSON_SINGLE_TOKEN",
    }:
        return "LEMMA_OR_VOCABULARY_AUTHORITY_GAP_REVIEW"
    return "SPELLING_OR_VOCABULARY_AUTHORITY_GAP_REVIEW"


def _priority(unit_count: int) -> str:
    if unit_count >= 100:
        return "HIGH"
    if unit_count >= 20:
        return "MEDIUM"
    return "LOW"


def build_package(
    matching_package: Mapping[str, Any],
    *,
    expected_page_unit_count: int = EXPECTED_PAGE_UNIT_COUNT,
    expected_book_count: int = EXPECTED_BOOK_COUNT,
    expected_gap_family_count: int = EXPECTED_GAP_FAMILY_COUNT,
    expected_unverified_topic_label_count: int = EXPECTED_UNVERIFIED_TOPIC_LABEL_COUNT,
) -> dict[str, Any]:
    rows, gap_ids, unverified_labels = _verify_input(
        matching_package,
        expected_page_unit_count=expected_page_unit_count,
        expected_book_count=expected_book_count,
    )

    family_state: dict[str, dict[str, set[str]]] = {
        family: {
            "levels": set(),
            "books": set(),
            "units": set(),
            "source_labels": set(),
            "topic_labels": set(),
        }
        for family in gap_ids
    }
    topic_state: dict[str, dict[str, Any]] = {
        label: {
            "label_type": None,
            "levels": set(),
            "books": set(),
            "units": set(),
            "families": set(),
        }
        for label in unverified_labels
    }

    family_catalog = {
        str(row.get("source_macro_theme_family_id")): row
        for row in matching_package.get("source_macro_theme_family_candidates", [])
        if isinstance(row, Mapping)
    }

    for row in rows:
        unit_ref = str(row.get("source_unit_ref") or "")
        level = str(row.get("source_level") or "")
        book_id = str(row.get("source_book_id") or "")
        family_ids = {
            str(value)
            for value in row.get("source_macro_theme_family_ids", [])
            if isinstance(value, str) and value
        }
        source_labels = {
            str(value)
            for value in row.get("source_macro_theme_labels", [])
            if isinstance(value, str) and value
        }
        topic_labels = {
            str(value)
            for value in row.get("source_subtheme_labels", [])
            if isinstance(value, str) and value
        }

        for family in family_ids & gap_ids:
            state = family_state[family]
            state["levels"].add(level)
            state["books"].add(f"{level}:{book_id}")
            state["units"].add(unit_ref)
            state["source_labels"].update(source_labels)
            state["topic_labels"].update(topic_labels)

        classifications = row.get("source_topic_label_classifications", [])
        if not isinstance(classifications, list):
            raise ThemeGapEvidenceError(f"topic_classifications_invalid:{unit_ref}")
        for item in classifications:
            if not isinstance(item, Mapping):
                raise ThemeGapEvidenceError(f"topic_classification_not_object:{unit_ref}")
            label = str(item.get("source_subtheme_label") or "")
            if label not in topic_state:
                continue
            label_type = str(item.get("source_topic_label_type") or "")
            state = topic_state[label]
            previous = state["label_type"]
            if previous is not None and previous != label_type:
                raise ThemeGapEvidenceError(
                    f"topic_label_type_conflict:{label}:{previous}:{label_type}"
                )
            state["label_type"] = label_type
            state["levels"].add(level)
            state["books"].add(f"{level}:{book_id}")
            state["units"].add(unit_ref)
            state["families"].update(family_ids)

    gap_rows: list[dict[str, Any]] = []
    for family in sorted(gap_ids):
        state = family_state[family]
        catalog = family_catalog.get(family)
        if not isinstance(catalog, Mapping):
            raise ThemeGapEvidenceError(f"gap_family_catalog_missing:{family}")
        gap_rows.append(
            {
                "candidate_id": f"THEME_GAP_{family.upper()}",
                "source_macro_theme_family_id": family,
                "source_macro_theme_labels": list(catalog.get("source_macro_theme_labels", [])),
                "source_level_count": len(state["levels"]),
                "source_levels": sorted(state["levels"]),
                "source_book_count": len(state["books"]),
                "source_unit_count": len(state["units"]),
                "associated_source_topic_label_count": len(state["topic_labels"]),
                "review_route": "HUMAN_THEME_AUTHORITY_DECISION_REQUIRED",
                "authority_status": "candidate_only",
                "review_status": "pending",
                "promotion_status": "promotion_blocked",
            }
        )

    topic_rows: list[dict[str, Any]] = []
    for label in sorted(unverified_labels):
        state = topic_state[label]
        label_type = state["label_type"]
        if not isinstance(label_type, str) or not label_type:
            raise ThemeGapEvidenceError(f"topic_label_evidence_missing:{label}")
        unit_count = len(state["units"])
        topic_rows.append(
            {
                "candidate_id": "TOPIC_REVIEW_" + deep.sha256_value(label)[:16].upper(),
                "source_topic_label": label,
                "source_topic_label_type": label_type,
                "source_level_count": len(state["levels"]),
                "source_levels": sorted(state["levels"]),
                "source_book_count": len(state["books"]),
                "source_unit_count": unit_count,
                "source_macro_theme_family_ids": sorted(state["families"]),
                "review_route": _review_route(label_type),
                "review_priority": _priority(unit_count),
                "authority_status": "candidate_only",
                "review_status": "pending",
                "promotion_status": "promotion_blocked",
            }
        )

    observed_gap_ids = {row["source_macro_theme_family_id"] for row in gap_rows}
    observed_topic_labels = {row["source_topic_label"] for row in topic_rows}
    checks = {
        "gap_family_count_exact": len(gap_rows) == expected_gap_family_count,
        "unverified_topic_label_count_exact": len(topic_rows)
        == expected_unverified_topic_label_count,
        "gap_family_ids_reconciled": observed_gap_ids == gap_ids,
        "unverified_topic_labels_reconciled": observed_topic_labels == unverified_labels,
        "all_gap_families_have_source_evidence": all(
            row["source_unit_count"] > 0 and row["source_book_count"] > 0
            for row in gap_rows
        ),
        "all_topic_labels_have_source_evidence": all(
            row["source_unit_count"] > 0 and row["source_book_count"] > 0
            for row in topic_rows
        ),
        "candidate_boundaries_preserved": all(
            row["authority_status"] == "candidate_only"
            and row["review_status"] == "pending"
            and row["promotion_status"] == "promotion_blocked"
            for row in gap_rows + topic_rows
        ),
    }
    ready = all(checks.values())

    priority_counts: dict[str, int] = defaultdict(int)
    route_counts: dict[str, int] = defaultdict(int)
    for row in topic_rows:
        priority_counts[row["review_priority"]] += 1
        route_counts[row["review_route"]] += 1

    package: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS if ready else "FAIL",
        "input_matching_identity": {
            "task_id": matching_package["task_id"],
            "package_sha256": matching_package["package_sha256"],
            "page_unit_count": expected_page_unit_count,
            "book_count": expected_book_count,
        },
        "theme_authority_gap_evidence": gap_rows,
        "source_topic_review_candidates": topic_rows,
        "aggregate_summary": {
            "theme_authority_gap_candidate_count": len(gap_rows),
            "unverified_source_topic_review_candidate_count": len(topic_rows),
            "source_topic_review_priority_counts": dict(sorted(priority_counts.items())),
            "source_topic_review_route_counts": dict(sorted(route_counts.items())),
        },
        "review_gate": {
            "source_checks": checks,
            "decision": (
                "THEME_GAP_AND_TOPIC_REVIEW_EVIDENCE_READY"
                if ready
                else "BLOCKED_THEME_GAP_OR_TOPIC_REVIEW_EVIDENCE"
            ),
            "human_decision_required": True,
            "ready_for_canonical_promotion": False,
            "ready_for_learning_unit_population": False,
            "next_short_step": "RAZ-AW_ThemeGapAndTopicHumanDecisionBinding",
        },
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "errors": [],
    }
    package["package_sha256"] = deep.sha256_value(package)
    return package


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matching-package", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        source = deep.read_json(args.matching_package)
        if not isinstance(source, Mapping):
            raise ThemeGapEvidenceError("matching_package_not_object")
        package = build_package(source)
        leakage = matching.scan_forbidden_safe_keys(package)
        if leakage:
            raise ThemeGapEvidenceError("safe_output_leakage:" + ";".join(leakage[:20]))
        deep.write_json_atomic(args.output, package)
        print(
            json.dumps(
                {
                    "task_id": TASK_ID,
                    "decision": package["review_gate"]["decision"],
                    **package["aggregate_summary"],
                    "package_sha256": package["package_sha256"],
                },
                sort_keys=True,
            )
        )
        return 0
    except (
        ThemeGapEvidenceError,
        matching.ThemeAuthorityCandidateMatchingError,
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
