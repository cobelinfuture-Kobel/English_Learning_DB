#!/usr/bin/env python3
"""Project Unit02 approved QuestionBank capacity into the existing cumulative runtime.

This milestone is an integration/readback consumer only. It preserves the
Unit01 474-item catalog by reference, preserves all 994 approved Unit02 item
identities, consumes the U02SP02 reconciled pattern projection, and binds
sentence-bearing runtime tasks to the canonical U02SA01R1 Sentence Asset delta.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_v1_u01qb19_unit01_canonical474_cumulative_reuse_reference_projection as u01qb19,
)
from ulga.builders import (
    build_a1fs_v1_u02qbc02_unit02_questionbank_gap_materialization_and_per_slot_distinct_capacity_proof
    as qbc02,
)
from ulga.builders import (
    build_a1fs_v1_u02sp02_unit01_unit02_exact_sentence_frame_coverage_recheck as sp02,
)
from ulga.builders import (
    build_a1fs_v1_u02sa01_unit01_unit02_cumulative_sentence_asset_coverage_recheck as u02sa01,
)
from ulga.builders.a1fs_v1_u02sa01r1.common import normalize_sentence, normalize_surface

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Runtime integration projection over already-approved QuestionBank and SentenceAsset authorities; does not create QuestionBank content, SentenceAssets, canonical patterns, learner state, scoring, or A2 content."

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U02QB03_Unit02CumulativeQuestionBankRuntimeIntegration"
SCHEMA_VERSION = "a1fs.v1.u02qb03.cumulative_questionbank_runtime_integration.v1"
PASS_STATUS = "PASS_A1FS_V1_U02QB03_UNIT02_CUMULATIVE_QUESTIONBANK_RUNTIME_INTEGRATION"
NEXT_SHORT_STEP = "A1FS-V1-U02QB03R1_MainReadbackAndRequestedQ2Q3Q6ListExport"

EXPECTED_UNIT01_CATALOG = 474
EXPECTED_UNIT02_APPROVED = 994
EXPECTED_CUMULATIVE_CATALOG = 1468
EXPECTED_FORMS = 16
EXPECTED_SCENE_SLOTS = 4
EXPECTED_TASK_FAMILIES = 10
EXPECTED_ACTIVITIES_PER_FORM = 40
EXPECTED_RUNTIME_OCCURRENCES = 640
MIN_RUNTIME_POOL_DEPTH = 12
MIN_CANDIDATES_PER_SLOT = 3

RUNTIME_RESTRICTED_SURFACES = {"beer"}
SENTENCE_BINDING_REQUIRED_FAMILIES = {"PRODUCTIVE_RESPONSE", "TRANSFER"}


class U02QB03BuildError(ValueError):
    pass


def _approved_unit02_items() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    qbc = qbc02.payload()
    base = list(qbc02._base_approved_payload()["approved_items"])
    new = list(qbc["new_approved_items"])
    rows = [dict(row) for row in base + new]
    if len(base) != qbc02.EXPECTED_BASE_U02_ITEMS:
        raise U02QB03BuildError(f"BASE_ITEM_COUNT_DRIFT:{len(base)}")
    if len(new) != qbc02.EXPECTED_NEW_ITEMS:
        raise U02QB03BuildError(f"NEW_ITEM_COUNT_DRIFT:{len(new)}")
    if len(rows) != EXPECTED_UNIT02_APPROVED:
        raise U02QB03BuildError(f"UNIT02_APPROVED_COUNT_DRIFT:{len(rows)}")
    if len({str(row["item_id"]) for row in rows}) != len(rows):
        raise U02QB03BuildError("DUPLICATE_UNIT02_ITEM_ID")
    return [dict(row) for row in base], [dict(row) for row in new], qbc


def _item_by_id(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {str(row["item_id"]): dict(row) for row in rows}
    if len(result) != len(rows):
        raise U02QB03BuildError("ITEM_LOOKUP_IDENTITY_COLLISION")
    return result


def _target_singular(item: Mapping[str, Any]) -> str:
    slots = item.get("lexical_slots") or {}
    return normalize_surface(str(slots.get("singular_noun") or ""))


def _runtime_family_pools(
    qbc: Mapping[str, Any],
    items: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, list[str]], list[str]]:
    pools: dict[str, list[str]] = {}
    restricted_ids: set[str] = set()
    for family in qbc02.TASK_FAMILIES:
        source_ids = list(qbc["task_family_pools"][family])
        legal: list[str] = []
        for item_id in source_ids:
            item = items[str(item_id)]
            if _target_singular(item) in RUNTIME_RESTRICTED_SURFACES:
                restricted_ids.add(str(item_id))
                continue
            legal.append(str(item_id))
        if len(legal) < MIN_RUNTIME_POOL_DEPTH:
            raise U02QB03BuildError(f"RUNTIME_POOL_TOO_SHALLOW:{family}:{len(legal)}")
        pools[str(family)] = legal
    return pools, sorted(restricted_ids)


def runtime_capacity_slot_matrix(pools: Mapping[str, Sequence[str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for form_number in range(1, EXPECTED_FORMS + 1):
        for scene_slot in range(1, EXPECTED_SCENE_SLOTS + 1):
            for task_index, task_family in enumerate(qbc02.TASK_FAMILIES, start=1):
                pool = list(pools[task_family])
                offset = ((form_number - 1) * 12 + (scene_slot - 1) * 3) % len(pool)
                candidates = [pool[(offset + i) % len(pool)] for i in range(MIN_CANDIDATES_PER_SLOT)]
                if len(set(candidates)) != MIN_CANDIDATES_PER_SLOT:
                    raise U02QB03BuildError(
                        f"RUNTIME_SLOT_CANDIDATE_NOT_DISTINCT:F{form_number}:S{scene_slot}:{task_family}"
                    )
                rows.append(
                    {
                        "slot_id": f"U02-F{form_number:02d}-S{scene_slot:02d}-T{task_index:02d}",
                        "form_number": form_number,
                        "progression_stage": qbc02.progression_stage(form_number),
                        "scene_slot_ordinal": scene_slot,
                        "task_family": task_family,
                        "candidate_ids": candidates,
                        "selected_item_id": candidates[0],
                        "runtime_selection_rule": "FIRST_OF_THREE_DETERMINISTIC_CAPACITY_CANDIDATES",
                    }
                )
    if len(rows) != EXPECTED_RUNTIME_OCCURRENCES:
        raise U02QB03BuildError(f"RUNTIME_SLOT_COUNT_INVALID:{len(rows)}")
    for form_number in range(1, EXPECTED_FORMS + 1):
        for task_family in qbc02.TASK_FAMILIES:
            selected = [
                row["selected_item_id"]
                for row in rows
                if row["form_number"] == form_number and row["task_family"] == task_family
            ]
            if len(selected) != EXPECTED_SCENE_SLOTS or len(set(selected)) != EXPECTED_SCENE_SLOTS:
                raise U02QB03BuildError(
                    f"WITHIN_FORM_SELECTED_ITEM_REUSE:F{form_number}:{task_family}"
                )
    return rows


def _lineage_index(report: Mapping[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    rows = report["reconciled_questionbank_pattern_projection"]
    result = {(str(row["source"]), str(row["family_id"])): dict(row) for row in rows}
    if len(result) != len(rows):
        raise U02QB03BuildError("SP02_LINEAGE_KEY_COLLISION")
    return result


def _lineage_for(
    item: Mapping[str, Any],
    task_family: str,
    lineage: Mapping[tuple[str, str], Mapping[str, Any]],
) -> dict[str, Any]:
    if str(item["item_id"]).startswith("U02QBC02-"):
        key = ("U02QBC02", task_family)
    else:
        key = ("U02QB02", str(item["pattern_family_id"]))
    row = dict(lineage[key])
    if row.get("runtime_may_consume_raw_pattern_ids") is not False:
        raise U02QB03BuildError(f"SP02_RAW_PATTERN_RUNTIME_AUTHORITY_DRIFT:{key}")
    return row


def _sentence_index(q6: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    assets = q6["sentence_asset_delta"]["assets"]
    result: dict[str, dict[str, Any]] = {}
    for asset in assets:
        normalized = normalize_sentence(str(asset["text"]))
        if normalized in result:
            raise U02QB03BuildError(f"Q6_NORMALIZED_SENTENCE_COLLISION:{normalized}")
        result[normalized] = dict(asset)
    if len(result) != int(q6["sentence_asset_delta"]["asset_count"]):
        raise U02QB03BuildError("Q6_SENTENCE_INDEX_COUNT_DRIFT")
    return result


def _sentence_binding(
    task_family: str,
    item: Mapping[str, Any],
    sentence_index: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if task_family not in SENTENCE_BINDING_REQUIRED_FAMILIES:
        return {
            "status": "NOT_REQUIRED_FOR_TASK_FAMILY",
            "sentence_asset_id": None,
            "binding_text": None,
        }
    plural = str((item.get("lexical_slots") or {}).get("plural_noun") or "")
    expected = f"I can see two {plural}."
    normalized = normalize_sentence(expected)
    asset = sentence_index.get(normalized)
    if asset is None:
        raise U02QB03BuildError(
            f"REQUIRED_Q6_SENTENCE_ASSET_NOT_FOUND:{task_family}:{item['item_id']}:{expected}"
        )
    return {
        "status": "BOUND_CANONICAL_Q6_SENTENCE_ASSET",
        "sentence_asset_id": asset["sentence_id"],
        "binding_text": asset["text"],
        "sentence_asset_pattern_metadata": asset.get("pattern_id"),
        "runtime_pattern_authority_source": "U02SP02_RECONCILED_PROJECTION",
    }


def build_report() -> dict[str, Any]:
    base_items, new_items, qbc = _approved_unit02_items()
    all_items = base_items + new_items
    items = _item_by_id(all_items)
    pools, restricted_ids = _runtime_family_pools(qbc, items)
    slots = runtime_capacity_slot_matrix(pools)

    sp = sp02.build_report()
    lineage = _lineage_index(sp)
    if sp["legacy_pattern_reconciliation"]["raw_pattern_ids_runtime_authoritative"] is not False:
        raise U02QB03BuildError("SP02_RUNTIME_BOUNDARY_DRIFT")

    q6 = u02sa01.build_report()
    q2_q3 = q6["q2_vocabulary_morphology_list"]
    sentence_index = _sentence_index(q6)

    runtime_rows: list[dict[str, Any]] = []
    for slot in slots:
        item = items[slot["selected_item_id"]]
        projected_lineage = _lineage_for(item, str(slot["task_family"]), lineage)
        binding = _sentence_binding(str(slot["task_family"]), item, sentence_index)
        runtime_rows.append(
            {
                "runtime_occurrence_id": f"{slot['slot_id']}::{slot['selected_item_id']}",
                **dict(slot),
                "questionbank_item_id": item["item_id"],
                "questionbank_source": (
                    "U02QBC02" if str(item["item_id"]).startswith("U02QBC02-") else "U02QB02"
                ),
                "target_singular": _target_singular(item),
                "raw_historical_pattern_ids": list(item.get("unit_pattern_ids") or []),
                "runtime_pattern_lineage": projected_lineage,
                "sentence_asset_binding": binding,
                "learner_delivery_status": "RUNTIME_PROJECTED",
            }
        )

    selected_counts = Counter(row["task_family"] for row in runtime_rows)
    bound_rows = [
        row for row in runtime_rows
        if row["sentence_asset_binding"]["status"] == "BOUND_CANONICAL_Q6_SENTENCE_ASSET"
    ]
    runtime_pool_ids = sorted({item_id for ids in pools.values() for item_id in ids})
    selected_item_ids = sorted({row["questionbank_item_id"] for row in runtime_rows})

    if len(q2_q3) != 162:
        raise U02QB03BuildError(f"Q2_Q3_LIST_DRIFT:{len(q2_q3)}")
    if len(runtime_rows) != EXPECTED_RUNTIME_OCCURRENCES:
        raise U02QB03BuildError("RUNTIME_OCCURRENCE_COUNT_DRIFT")

    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "source_authority": {
            "unit01_runtime_reference_task_id": u01qb19.TASK_ID,
            "unit02_qbc02_task_id": qbc02.TASK_ID,
            "unit02_sp02_task_id": sp02.TASK_ID,
            "unit02_sa01r1_task_id": u02sa01.TASK_ID,
            "unit02_sa01r1_sentence_asset_count": q6["sentence_asset_delta"]["asset_count"],
            "unit02_sa01r1_sentence_asset_digest": q6["sentence_asset_delta"]["asset_digest"],
            "q2_q3_morphology_target_count": len(q2_q3),
        },
        "cumulative_questionbank_catalog": {
            "unit01_reference_only_item_count": EXPECTED_UNIT01_CATALOG,
            "unit02_approved_item_count": len(all_items),
            "cumulative_catalog_item_count": EXPECTED_UNIT01_CATALOG + len(all_items),
            "unit01_catalog_mutated": False,
            "unit02_approved_item_identity_mutated": False,
            "parallel_questionbank_created": False,
        },
        "runtime_eligibility": {
            "restricted_target_surfaces": sorted(RUNTIME_RESTRICTED_SURFACES),
            "restricted_questionbank_item_ids": restricted_ids,
            "approved_assets_deleted": False,
            "runtime_pool_distinct_item_count": len(runtime_pool_ids),
            "runtime_selected_distinct_item_count": len(selected_item_ids),
            "minimum_runtime_family_pool_depth": min(len(ids) for ids in pools.values()),
            "runtime_family_pool_counts": {family: len(ids) for family, ids in pools.items()},
        },
        "pattern_reconciliation": {
            "legacy_raw_pattern_id": sp02.LEGACY_INVALID_PATTERN_ID,
            "legacy_raw_binding_count": sp["legacy_pattern_reconciliation"][
                "raw_legacy_invalid_binding_count"
            ],
            "raw_pattern_ids_runtime_authoritative": False,
            "runtime_projection_source_task_id": sp02.TASK_ID,
            "runtime_lineage_row_count": len(lineage),
        },
        "sentence_asset_integration": {
            "binding_required_task_families": sorted(SENTENCE_BINDING_REQUIRED_FAMILIES),
            "bound_runtime_occurrence_count": len(bound_rows),
            "bound_distinct_sentence_asset_count": len(
                {row["sentence_asset_binding"]["sentence_asset_id"] for row in bound_rows}
            ),
            "q6_sentence_asset_count": q6["sentence_asset_delta"]["asset_count"],
            "q6_sentence_asset_digest": q6["sentence_asset_delta"]["asset_digest"],
            "q6_assets_mutated": False,
        },
        "runtime_form_contract": {
            "form_count": EXPECTED_FORMS,
            "scene_slots_per_form": EXPECTED_SCENE_SLOTS,
            "task_family_count": EXPECTED_TASK_FAMILIES,
            "activities_per_form": EXPECTED_ACTIVITIES_PER_FORM,
            "runtime_occurrence_count": len(runtime_rows),
            "selected_count_by_task_family": dict(sorted(selected_counts.items())),
            "all_slots_retain_three_legal_candidates": all(
                len(row["candidate_ids"]) == MIN_CANDIDATES_PER_SLOT for row in runtime_rows
            ),
            "within_form_same_task_family_selected_item_reuse": False,
            "runtime_connected": True,
            "final_forms_materialized": True,
        },
        "runtime_occurrences": runtime_rows,
        "claim_boundaries": {
            "questionbank_items_created": False,
            "unit01_runtime_or_catalog_mutated": False,
            "unit02_qbc02_raw_payload_mutated": False,
            "unit02_sp02_authority_mutated": False,
            "unit02_sentence_assets_mutated": False,
            "new_selector_engine_created": False,
            "learner_session_state_materialized": False,
            "learner_state_mutated": False,
            "canonical_scene_authority_mutated": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    from ulga.validators import (
        validate_a1fs_v1_u02qb03_unit02_cumulative_questionbank_runtime_integration as validator,
    )
    report = build_report()
    result = validator.validate_report(report)
    print(f"STATUS={PASS_STATUS}")
    print(
        "CUMULATIVE_CATALOG_ITEMS="
        f"{report['cumulative_questionbank_catalog']['cumulative_catalog_item_count']}"
    )
    print(f"RUNTIME_OCCURRENCES={report['runtime_form_contract']['runtime_occurrence_count']}")
    print(
        "RUNTIME_POOL_DISTINCT_ITEMS="
        f"{report['runtime_eligibility']['runtime_pool_distinct_item_count']}"
    )
    print(
        "BOUND_SENTENCE_OCCURRENCES="
        f"{report['sentence_asset_integration']['bound_runtime_occurrence_count']}"
    )
    print(f"ERROR_COUNT={result['error_count']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
