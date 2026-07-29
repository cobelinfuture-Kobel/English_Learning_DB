#!/usr/bin/env python3
"""Validate Unit01 three-skill candidate selection and coverage balancing."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_razq01c_unit01_three_skill_candidate_selection_coverage_balancing as selection

VALIDATOR_ID = (
    "A1FS_V1_RAZQ01C_UNIT01_THREE_SKILL_CANDIDATE_SELECTION_VALIDATOR"
)
PASS_STATUS = (
    "PASS_A1FS_V1_RAZQ01C_UNIT01_THREE_SKILL_CANDIDATE_SELECTION_VALIDATION"
)


class SelectionValidationError(ValueError):
    pass


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise SelectionValidationError(code)


def validate_report(report: Mapping[str, Any]) -> dict[str, Any]:
    _require(
        report.get("schema_version") == selection.SCHEMA_VERSION,
        "schema_version_invalid",
    )
    _require(report.get("task_id") == selection.TASK_ID, "task_id_invalid")
    _require(report.get("status") == selection.PASS_STATUS, "status_invalid")
    scope = report.get("scope", {})
    _require(scope.get("allowed_units") == [selection.UNIT_ID], "unit_scope_invalid")
    _require(
        scope.get("blocked_units") == "UNIT_02_TO_UNIT_24",
        "blocked_unit_scope_invalid",
    )
    _require(
        scope.get("canonical_promotion") is False,
        "canonical_promotion_forbidden",
    )
    _require(
        scope.get("learner_facing_content_write") is False,
        "learner_content_write_forbidden",
    )
    _require(scope.get("a2_status") == "LOCKED", "a2_lock_invalid")
    inputs = report.get("inputs", {})
    _require(
        inputs.get("approved_contract_sha256")
        == selection.APPROVED_CONTRACT_SHA256,
        "contract_digest_invalid",
    )
    _require(
        inputs.get("complete_strict_candidate_manifest") is True,
        "strict_manifest_incomplete",
    )
    summary = report.get("selection_summary", {})
    strict_count = int(summary.get("strict_candidate_count") or 0)
    candidates = report.get("selected_candidates", [])
    _require(isinstance(candidates, list), "selected_candidates_invalid")
    _require(len(candidates) == strict_count, "selected_candidate_count_mismatch")
    identities = [row.get("semantic_identity") for row in candidates]
    _require(all(identities), "semantic_identity_missing")
    _require(
        len(set(identities)) == len(identities),
        "semantic_identity_duplicate",
    )
    actual_counts = Counter(row.get("selection_class") for row in candidates)
    declared_counts = summary.get("classification_counts", {})
    _require(
        set(declared_counts) == set(selection.SELECTION_CLASSES),
        "classification_keys_invalid",
    )
    _require(
        declared_counts
        == {
            name: actual_counts.get(name, 0)
            for name in selection.SELECTION_CLASSES
        },
        "classification_counts_invalid",
    )
    _require(
        sum(declared_counts.values()) == strict_count,
        "classification_total_invalid",
    )
    for row in candidates:
        _require(
            row.get("selection_class") in selection.SELECTION_CLASSES,
            "selection_class_invalid",
        )
        _require(
            row.get("canonical_admission") is False,
            "candidate_canonical_admission_forbidden",
        )
        if row.get("selection_class") == "REJECT":
            _require(
                not row.get("direct_task_candidate_roles"),
                "reject_direct_role_forbidden",
            )
    coverage = report.get("coverage", {})
    source = coverage.get("source_coverage", {})
    planned = coverage.get("planned_coverage_after_gap_specs", {})
    expected_dimensions = {
        "active_nouns",
        "active_adjectives",
        "articles",
        "sentence_frames",
    }
    _require(set(source) == expected_dimensions, "coverage_dimensions_invalid")
    _require(set(planned) == set(source), "planned_coverage_dimensions_invalid")
    for dimension, item in source.items():
        target = item.get("target", [])
        covered = item.get("covered", [])
        missing = item.get("missing", [])
        _require(
            len(target) == len(set(target)),
            f"coverage_target_duplicate:{dimension}",
        )
        _require(
            set(covered) <= set(target),
            f"coverage_outside_target:{dimension}",
        )
        _require(
            set(missing) == set(target) - set(covered),
            f"coverage_missing_invalid:{dimension}",
        )
        _require(
            planned[dimension].get("missing_after_gap_specs") == [],
            f"planned_gap_remaining:{dimension}",
        )
        _require(
            set(planned[dimension].get("covered_after_gap_specs", []))
            == set(target),
            f"planned_coverage_invalid:{dimension}",
        )
    gaps = coverage.get("project_authored_gap_specs", [])
    _require(isinstance(gaps, list), "gap_specs_invalid")
    for gap in gaps:
        _require(
            gap.get("candidate_only") is True,
            "gap_spec_candidate_only_required",
        )
        _require(gap.get("generated") is True, "gap_spec_generated_required")
        _require(
            gap.get("review_status") == "PENDING",
            "gap_spec_review_status_invalid",
        )
        _require(
            gap.get("canonical_admission") is False,
            "gap_spec_canonical_admission_forbidden",
        )
        _require(
            not any(
                key in gap for key in ("text", "prompt", "answer", "answer_key")
            ),
            "gap_spec_learner_text_forbidden",
        )
    _require(
        coverage.get("planned_coverage_complete") is True,
        "planned_coverage_not_complete",
    )
    listening = report.get("listening_readback", {})
    _require(
        listening.get("status")
        == "DEFERRED_NO_LISTENING_LESSON_IN_UNIT01_RUNTIME",
        "listening_status_invalid",
    )
    _require(
        listening.get("listening_task_candidate_count") == 0,
        "listening_candidate_count_nonzero",
    )
    _require(listening.get("audio_enabled") is False, "audio_enabled_forbidden")
    _require(
        listening.get("listening_claimed_complete") is False,
        "listening_completion_claim_forbidden",
    )
    validation = report.get("validation", {})
    for key in (
        "unit01_only",
        "complete_strict_candidate_manifest",
        "all_strict_candidates_classified",
        "coverage_balancing_applied",
        "gap_specs_candidate_only",
    ):
        _require(validation.get(key) is True, f"validation_gate_missing:{key}")
    _require(
        validation.get("canonical_content_modified") is False,
        "canonical_content_modified",
    )
    _require(
        validation.get("unit02_to_unit24_modified") is False,
        "other_units_modified",
    )
    _require(validation.get("a2_unlocked") is False, "a2_unlocked")
    _require(
        report.get("next_short_step") == selection.NEXT_SHORT_STEP,
        "next_short_step_invalid",
    )
    return {
        "validator_id": VALIDATOR_ID,
        "validation_status": PASS_STATUS,
        "error_count": 0,
        "strict_candidate_count": strict_count,
        "gap_spec_count": len(gaps),
        "source_coverage_complete": bool(
            coverage.get("source_coverage_complete")
        ),
        "planned_coverage_complete": True,
        "listening_status": listening["status"],
        "next_short_step": selection.NEXT_SHORT_STEP,
    }


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SelectionValidationError(f"unreadable:{path}:{exc}") from exc
    _require(isinstance(value, dict), f"object_required:{path}")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = validate_report(_load(args.report.resolve()))
    except (SelectionValidationError, ValueError, KeyError, TypeError) as exc:
        print(
            "STATUS=FAIL_A1FS_V1_RAZQ01C_UNIT01_THREE_SKILL_"
            "CANDIDATE_SELECTION_VALIDATION"
        )
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={result['validation_status']}")
    print(f"STRICT_CANDIDATES={result['strict_candidate_count']}")
    print(f"GAP_SPECS={result['gap_spec_count']}")
    print(f"LISTENING_STATUS={result['listening_status']}")
    print(f"NEXT_SHORT_STEP={result['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
