"""Deterministic execution optimizer for U01QB15.

The U01QB15 source-selection problem has already been solved against the current
five-context authority and 31-scene Unit01 rotation.  This module installs that
solved, authority-derived assignment into the canonical U01QB15 builder and
leaves the final 288-base U01QB14R1 exact distinct-item capacity proof as the
fail-closed acceptance gate.

This is not a second QuestionBank authority.  It changes only source-selection
execution strategy; the canonical U01QB15 builder still constructs/adopts the
288-item bank, validates all denominators, performs migration, and preserves the
186-item Real62 extension.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_v1_u01qb15_unit01_context_stratified_question_bank_replacement_and_per_scene_runtime_capacity_fullfix
    as target,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Deterministic source-selection execution helper only; all QuestionBank "
    "construction, validation, exact runtime-capacity proof, and migration remain "
    "owned by the canonical U01QB15 builder."
)

F04, F05, F08 = target.READING_REPLACEMENT_FAMILIES
F09 = target.WRITING_CONTEXT_REPLACEMENT_FAMILY

# Solved against the current Unit01 five-context authority and the exact R1
# rotation.  Overlap between PF04/PF05/PF08 is intentional and required for
# scenes such as C3/egg to expose four distinct Writing angles across repeated
# Guided -> Independent use while retaining enough Reading angles.
DETERMINISTIC_NOUN_ASSIGNMENT: dict[str, dict[str, tuple[str, ...]]] = {
    "U01-C1-CLASSROOM-BAG": {
        F04: ("apple", "bag"),
        F05: ("apple", "bag"),
        F08: ("apple", "bag"),
        F09: ("apple", "book"),
    },
    "U01-C2-HOME-TOY-BOX": {
        F04: ("bag", "bed"),
        F05: ("bag", "bed"),
        F08: ("bag", "bed"),
        F09: ("bag", "bed"),
    },
    "U01-C3-PICNIC-FOOD": {
        F04: ("apple", "egg"),
        F05: ("apple", "egg"),
        F08: ("bag", "book"),
        F09: ("apple", "bag"),
    },
    "U01-C4-TOY-SHOP": {
        F04: ("apple", "bag", "bed"),
        F05: ("apple", "bag", "bed"),
        F08: ("apple", "bed", "shop"),
        F09: ("apple", "bag", "shop"),
    },
    "U01-C5-PARK-BIRTHDAY": {
        F04: ("apple", "bag", "dog"),
        F05: ("apple", "bag", "dog"),
        F08: ("book", "box", "cat"),
        F09: ("apple", "bag", "book"),
    },
}


def _assignment() -> dict[str, dict[str, tuple[tuple[str, str], ...]]]:
    result: dict[str, dict[str, tuple[tuple[str, str], ...]]] = {}
    contexts = tuple(target.u01qb10.seed.CONTEXT_IDS)
    if set(DETERMINISTIC_NOUN_ASSIGNMENT) != set(contexts):
        raise target.ContextStratifiedFullFixError("DETERMINISTIC_CONTEXT_SET_DRIFT")
    for context in contexts:
        families = DETERMINISTIC_NOUN_ASSIGNMENT[context]
        if set(families) != set(target.REPLACEMENT_FAMILIES):
            raise target.ContextStratifiedFullFixError(
                f"DETERMINISTIC_FAMILY_SET_DRIFT:{context}"
            )
        result[context] = {
            family: tuple((context, noun) for noun in families[family])
            for family in target.REPLACEMENT_FAMILIES
        }
    return result


def production_assignment_by_context_fast(
    items: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, tuple[tuple[str, str], ...]]]:
    # Validate every declared pair against the current seed authority, so a
    # future noun/context drift fails instead of silently reusing this manifest.
    grouped = {
        family: target._group_context_rows(items, family)
        for family in target.REPLACEMENT_FAMILIES
    }
    assignment = _assignment()
    for context, families in assignment.items():
        for family, pairs in families.items():
            legal = {target._pair_key(row) for row in grouped[family].get(context, [])}
            missing = [pair for pair in pairs if pair not in legal]
            if missing:
                raise target.ContextStratifiedFullFixError(
                    "DETERMINISTIC_SOURCE_PAIR_NOT_IN_CURRENT_AUTHORITY:"
                    + family
                    + ":"
                    + context
                    + ":"
                    + ",".join(pair[1] for pair in missing)
                )
    return deepcopy(assignment)


def quota_by_family_fast() -> dict[str, dict[str, int]]:
    assignment = _assignment()
    quotas = {
        family: {
            context: len(assignment[context][family])
            for context in target.u01qb10.seed.CONTEXT_IDS
        }
        for family in target.REPLACEMENT_FAMILIES
    }
    for family, by_context in quotas.items():
        if sum(by_context.values()) != target.CONTEXT_REPLACEMENT_COUNT:
            raise target.ContextStratifiedFullFixError(
                f"DETERMINISTIC_FAMILY_TOTAL_INVALID:{family}:{sum(by_context.values())}"
            )
        if not all(
            target.MIN_CONTEXT_QUOTA <= value <= target.MAX_CONTEXT_QUOTA
            for value in by_context.values()
        ):
            raise target.ContextStratifiedFullFixError(
                f"DETERMINISTIC_CONTEXT_QUOTA_INVALID:{family}"
            )
    return quotas


def replacement_sources_fast(
    items: Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    assignment = production_assignment_by_context_fast(items)
    grouped = {
        family: target._group_context_rows(items, family)
        for family in target.REPLACEMENT_FAMILIES
    }
    result = {family: [] for family in target.REPLACEMENT_FAMILIES}
    for context in target.u01qb10.seed.CONTEXT_IDS:
        for family in target.REPLACEMENT_FAMILIES:
            by_pair = {
                target._pair_key(row): row
                for row in grouped[family].get(context, [])
            }
            for pair in assignment[context][family]:
                row = by_pair.get(pair)
                if row is None:
                    raise target.ContextStratifiedFullFixError(
                        f"ASSIGNED_SOURCE_ROW_MISSING:{family}:{context}:{pair[1]}"
                    )
                result[family].append(deepcopy(row))
    for family, rows in result.items():
        if len(rows) != target.CONTEXT_REPLACEMENT_COUNT:
            raise target.ContextStratifiedFullFixError(
                f"REPLACEMENT_COUNT_INVALID:{family}:{len(rows)}"
            )
    return result


def reading_pair_survival_diagnostic(
    items: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    tracked = {*target.READING_REPLACEMENT_FAMILIES, target.u01qb12.PF16}
    counts: Counter[tuple[str, str]] = Counter()
    for item in items:
        if str(item.get("pattern_family_id")) in tracked:
            pair = target._pair_key(item)
            if pair[0] and pair[1]:
                counts[pair] += 1
    seed_pairs = sorted(
        {
            target._pair_key(row)
            for row in target.u01qb10.seed_bank()[1]
            if row.get("pattern_family_id") == target.READING_REPLACEMENT_FAMILIES[0]
        }
    )
    below_two = [pair for pair in seed_pairs if counts[pair] < 2]
    minimum = min(counts[pair] for pair in seed_pairs)
    return {
        "approved_context_noun_pair_count": len(seed_pairs),
        "minimum_surviving_context_bound_reading_identities_per_pair": minimum,
        "pairs_below_two_count": len(below_two),
        "pairs_below_two": [f"{context}:{noun}" for context, noun in below_two],
        "all_pairs_retain_at_least_two_context_bound_reading_identities": not below_two,
        "diagnostic_only_not_acceptance_gate": True,
        "authoritative_acceptance_gate": "PER_SCENE_RUNTIME_CAPACITY",
    }


def build_payload_fast() -> dict[str, Any]:
    if target._PAYLOAD_CACHE is not None:
        return deepcopy(target._PAYLOAD_CACHE)

    final_items, lineage = target.build_context_stratified_u01qb12_items()
    replacements = lineage["u01qb10_replacements"]
    reading_retired_pairs = [
        target._pair_key(row)
        for family in target.READING_REPLACEMENT_FAMILIES
        for row in replacements[family]
    ]
    family_counts = dict(
        sorted(Counter(str(row["pattern_family_id"]) for row in final_items).items())
    )
    skill_counts = dict(
        sorted(Counter(str(row["skill"]) for row in final_items).items())
    )
    if family_counts != target.EXPECTED_FINAL_FAMILY_COUNTS:
        raise target.ContextStratifiedFullFixError("FINAL_FAMILY_COUNTS_INVALID")
    if skill_counts != target.EXPECTED_FINAL_SKILL_COUNTS:
        raise target.ContextStratifiedFullFixError("FINAL_SKILL_COUNTS_INVALID")

    assignment = production_assignment_by_context_fast(target.u01qb10.seed_bank()[1])
    quotas = quota_by_family_fast()
    survival = reading_pair_survival_diagnostic(final_items)
    # This is the authoritative, exact 288-base proof.  It uses the real
    # U01QB14R1 scene/task selector and distinct-item matching; no Real62 rows
    # are available to mask a base-bank deficit.
    capacity = target.base_only_scene_runtime_capacity_proof(final_items)

    payload: dict[str, Any] = {
        "schema_version": target.SCHEMA_VERSION,
        "program_id": target.PROGRAM_ID,
        "task_id": target.TASK_ID,
        "status": target.PASS_STATUS,
        "unit_id": target.UNIT_ID,
        "bank_identity": {
            "bank_id": target.BANK_ID,
            "bank_version": target.BANK_VERSION,
            "canonical_revision": target.CANONICAL_REVISION,
            "supersedes_selection_policy": [
                target.u01qb10.CANONICAL_REVISION,
                target.u01qb12.CANONICAL_REVISION,
            ],
            "historical_task_identity_rewritten": False,
            "second_question_bank_created": False,
        },
        "source_identity": {
            "seed_task_id": target.u01qb10.seed.TASK_ID,
            "u01qb10_constructor_task_id": target.u01qb10.TASK_ID,
            "u01qb12_constructor_task_id": target.u01qb12.TASK_ID,
        },
        "count_preservation": {
            "base_item_count": target.EXPECTED_BASE_COUNT,
            "u01qb10_retired_and_added": target.EXPECTED_U01QB10_RETIRED,
            "u01qb12_retired_and_added": target.EXPECTED_U01QB12_RETIRED,
            "unchanged_real62_extension_count": target.EXPECTED_EXTENSION_COUNT,
            "projected_runtime_total_count": target.EXPECTED_RUNTIME_COUNT,
        },
        "u01qb10_context_stratified_replacement": {
            "replacement_count_per_family": target.CONTEXT_REPLACEMENT_COUNT,
            "minimum_context_quota": target.MIN_CONTEXT_QUOTA,
            "maximum_context_quota": target.MAX_CONTEXT_QUOTA,
            "context_quota_by_family": quotas,
            "reading_family_ids": list(target.READING_REPLACEMENT_FAMILIES),
            "reading_retired_selection_count": len(reading_retired_pairs),
            "reading_retired_unique_pair_count": len(set(reading_retired_pairs)),
            "reading_retired_context_noun_pair_overlap_allowed": True,
            "scene_reading_and_writing_stage_assignment_proven": True,
            "exact_scene_capacity_is_authoritative": True,
            "assignment_pairs_by_context": {
                context: {
                    family: [list(pair) for pair in pairs]
                    for family, pairs in families.items()
                }
                for context, families in assignment.items()
            },
            "replacement_source_ids_by_family": {
                family: [str(row["item_id"]) for row in rows]
                for family, rows in replacements.items()
            },
        },
        "u01qb12_context_stratified_reference_replacement": {
            "replacement_count": target.REFERENCE_REPLACEMENT_COUNT,
            "context_quota": deepcopy(target.U01QB12_REFERENCE_CONTEXT_QUOTA),
            "source_item_ids": [
                str(row["item_id"])
                for row in lineage["u01qb12_reference_sources"]
            ],
            "replacement_family_id": target.u01qb12.PF16,
        },
        "distribution_counts": {
            "family": family_counts,
            "skill": skill_counts,
            "context_family": target._context_family_counts(final_items),
        },
        "reading_context_noun_survival": survival,
        "per_scene_runtime_capacity": capacity,
        "reconciled_items": [deepcopy(dict(row)) for row in final_items],
        "boundaries": {
            "question_bank_total_expanded": False,
            "real62_extension_modified": False,
            "new_scene_authored": False,
            "second_planner_created": False,
            "second_runtime_created": False,
            "parallel_database_created": False,
            "parallel_scoring_created": False,
            "speaking_capture_enabled": False,
            "speaking_scoring_enabled": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        },
        "next_short_step": target.NEXT_SHORT_STEP,
    }
    payload["reconciliation_sha256"] = target.digest(payload)
    target._PAYLOAD_CACHE = deepcopy(payload)
    return payload


def install() -> None:
    """Install the deterministic execution strategy into canonical U01QB15."""
    target._ASSIGNMENT_CACHE = None
    target._QUOTA_CACHE = None
    target._PAYLOAD_CACHE = None
    target._production_assignment_by_context = production_assignment_by_context_fast
    target._quota_by_family = quota_by_family_fast
    target.context_stratified_u01qb10_replacement_sources = replacement_sources_fast
    target._reading_pair_survival = reading_pair_survival_diagnostic
    target.build_payload = build_payload_fast


def main(argv: Sequence[str] | None = None) -> int:
    install()
    return target.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
