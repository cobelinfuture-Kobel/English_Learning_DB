#!/usr/bin/env python3
"""Export the current Unit02 Q1-Q10 final-package handoff without new content authority."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_u02qb02_unit02_plain_s_questionbank_candidate_pool as qb02
from ulga.builders import build_a1fs_v1_u02ch02_unit01_unit02_cumulative_chunk_coverage_recheck as ch02
from ulga.builders import build_a1fs_v1_u02sp02_unit01_unit02_exact_sentence_frame_coverage_recheck as sp02
from ulga.builders import build_a1fs_v1_u02sc04_unit02_admitted_scene_candidate_materialization_and_coverage_recheck as sc04
from ulga.builders import build_a1fs_v1_u02cf01_unit02_communicative_function_coverage_denominator as cf01
from ulga.builders import build_a1fs_v1_u02ta01_unit02_task_angle_question_type_coverage_denominator as ta01
from ulga.builders import build_a1fs_v1_u02qbc02_unit02_questionbank_gap_materialization_and_per_slot_distinct_capacity_proof as qbc02
from ulga.builders import build_a1fs_v1_u02qb03_unit02_cumulative_questionbank_runtime_integration as qb03
from ulga.builders import build_a1fs_v1_u02qb03r1_main_readback_requested_q2q3_q6_list_export as qb03r1

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Read-only final-package export over already-approved Unit02 Q1-Q10 authorities; creates no canonical grammar, vocabulary, chunks, patterns, scenes, QuestionBank items, SentenceAssets, runtime/state/scoring authority, or A2 content."

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U02FP01_Unit02FinalPackageQ1ToQ10Export"
SCHEMA_VERSION = "a1fs.v1.u02fp01.unit02_final_package_q1_q10_export.v1"
PASS_STATUS = "PASS_A1FS_V1_U02FP01_UNIT02_FINAL_PACKAGE_Q1_Q10_EXPORT"
UNIT_ID = qb02.UNIT_ID


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _q1() -> dict[str, Any]:
    inventory = qb02.load_inventory()
    counts = inventory["counts"]
    return {
        "unit_id": UNIT_ID,
        "grammar_target_ids": ["REGULAR_PLURAL_NOUNS"],
        "morphology_scope": "PLAIN_S_ONLY",
        "target_egp_row_ids": list(qb02.TARGET_EGP_ROWS),
        "target_egp_project_aliases": {
            "KP011": qb02.KP011,
            "KP012": qb02.KP012,
            "KP013": qb02.KP013,
            "KP014": qb02.KP014,
        },
        "prerequisite_egp_row_ids": [qb02.PREREQUISITE_KP009],
        "plain_s_vocabulary_denominator": counts["plain_s_denominator"],
        "exact_active_vocabulary_ref_count": counts["plain_s_exact_active_vocabulary_refs"],
        "excluded_morphology": ["-es", "-ies", "-ves", "-oes", "irregular"],
        "source_task_ids": [
            "A1FS-V1-U02QB01_ExactPlainSActiveVocabularyInventory",
            qb02.TASK_ID,
        ],
    }


def _q4() -> dict[str, Any]:
    report = ch02.build_report()
    return {
        **report,
        "unit01_rows": ch02.unit01_rows(),
        "unit02_rows": ch02.unit02_rows(),
    }


def _q5() -> dict[str, Any]:
    return sp02.build_report()


def _q7() -> dict[str, Any]:
    return sc04.build_payload()


def _q8() -> dict[str, Any]:
    return cf01.payload()


def _q9(qb03_report: Mapping[str, Any]) -> dict[str, Any]:
    baseline_families = ta01.task_family_rows()
    baseline_roles = ta01.task_role_rows(baseline_families)
    base_items = list(qbc02._base_approved_payload()["approved_items"])
    new_items = qbc02.materialized_gap_items()
    pools = qbc02.task_family_pools(base_items, new_items)
    runtime_counts = qb03_report["runtime_form_contract"]["selected_count_by_task_family"]
    baseline_by_family = {str(row["task_family"]): dict(row) for row in baseline_families}
    current_families = []
    for family in qbc02.TASK_FAMILIES:
        current_families.append(
            {
                "task_family": family,
                "q9_baseline_coverage_status": baseline_by_family[family]["coverage_status"],
                "q9_baseline_coverage_reason": baseline_by_family[family]["coverage_reason"],
                "post_qbc02_pool_depth": len(pools[family]),
                "post_qbc02_supply_materialized": True,
                "qb03_runtime_selected_occurrences": int(runtime_counts[family]),
                "qb03_runtime_connected": True,
            }
        )
    return {
        "unit_id": UNIT_ID,
        "source_task_ids": [ta01.TASK_ID, qbc02.TASK_ID, qb03.TASK_ID],
        "baseline_task_family_denominator": baseline_families,
        "baseline_pedagogical_role_denominator": baseline_roles,
        "post_materialization_task_families": current_families,
        "post_materialization_summary": {
            "task_family_count": len(current_families),
            "minimum_pool_depth": min(row["post_qbc02_pool_depth"] for row in current_families),
            "all_ten_task_family_pools_materialized": all(row["post_qbc02_supply_materialized"] for row in current_families),
            "runtime_occurrence_count": qb03_report["runtime_form_contract"]["runtime_occurrence_count"],
            "post_qbc02_pedagogical_full_partial_gap_recheck_separately_materialized": False,
            "interpretation": "PR531 FULL/PARTIAL/GAP is preserved as historical denominator evidence; current supply/runtime truth is represented by pool depth and runtime occurrence fields rather than silently relabeling the historical statuses.",
        },
    }


def _q10(qb03_report: Mapping[str, Any]) -> dict[str, Any]:
    base_items = [dict(row) for row in qbc02._base_approved_payload()["approved_items"]]
    new_items = [dict(row) for row in qbc02.materialized_gap_items()]
    approved_items = base_items + new_items
    pools = qbc02.task_family_pools(base_items, new_items)
    capacity_slots = qbc02.capacity_slot_matrix(pools)
    runtime_rows = [dict(row) for row in qb03_report["runtime_occurrences"]]
    if len(approved_items) != qbc02.EXPECTED_UNIT02_APPROVED_ITEMS:
        raise ValueError(f"U02FP01_Q10_APPROVED_COUNT_DRIFT:{len(approved_items)}")
    if len({str(row['item_id']) for row in approved_items}) != len(approved_items):
        raise ValueError("U02FP01_Q10_APPROVED_ITEM_ID_NOT_DISTINCT")
    if len(capacity_slots) != qbc02.TOTAL_SLOTS:
        raise ValueError(f"U02FP01_Q10_CAPACITY_SLOT_COUNT_DRIFT:{len(capacity_slots)}")
    if len(runtime_rows) != qb03.EXPECTED_RUNTIME_OCCURRENCES:
        raise ValueError(f"U02FP01_Q10_RUNTIME_COUNT_DRIFT:{len(runtime_rows)}")
    return {
        "unit_id": UNIT_ID,
        "source_task_ids": [qbc02.TASK_ID, qb03.TASK_ID],
        "inventory_summary": qb03_report["cumulative_questionbank_catalog"],
        "runtime_eligibility": qb03_report["runtime_eligibility"],
        "sentence_asset_integration": qb03_report["sentence_asset_integration"],
        "runtime_form_contract": qb03_report["runtime_form_contract"],
        "unit02_approved_items": approved_items,
        "capacity_slot_matrix": capacity_slots,
        "runtime_occurrences": runtime_rows,
        "full_unit02_approved_item_inventory_exported": True,
        "full_runtime_occurrence_plan_exported": True,
    }


def build_export_payload() -> dict[str, Any]:
    qb03_report = qb03.build_report()
    existing = qb03r1.build_export_payload()
    payload = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "q1_grammar": _q1(),
        "q2_q3_existing_export_ref": {
            "row_count": existing["q2_q3_vocabulary_morphology"]["row_count"],
            "sha256": existing["q2_q3_vocabulary_morphology"]["sha256"],
            "not_duplicated_in_this_export": True,
        },
        "q4_chunks": _q4(),
        "q5_sentence_patterns": _q5(),
        "q6_existing_export_ref": {
            "asset_count": existing["q6_sentence_assets"]["asset_count"],
            "asset_digest": existing["q6_sentence_assets"]["asset_digest"],
            "export_sha256": existing["q6_sentence_assets"]["export_sha256"],
            "not_duplicated_in_this_export": True,
        },
        "q7_micro_scenes": _q7(),
        "q8_communicative_functions": _q8(),
        "q9_task_angle_question_type": _q9(qb03_report),
        "q10_questionbank_capacity_runtime": _q10(qb03_report),
        "claim_boundaries": {
            "readback_only": True,
            "canonical_content_created": False,
            "questionbank_items_created": False,
            "sentence_assets_created": False,
            "runtime_authority_created": False,
            "learner_state_mutated": False,
            "a2_unlocked": False,
        },
    }
    payload["package_sha256"] = digest({key: value for key, value in payload.items() if key != "package_sha256"})
    return payload


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return value


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            key = str(key)
            if key not in seen:
                seen.add(key)
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in keys})


def write_exports(output_dir: Path) -> dict[str, str]:
    payload = build_export_payload()
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}

    json_sections = {
        "Q01_Grammar.json": payload["q1_grammar"],
        "Q04_Chunks.json": payload["q4_chunks"],
        "Q05_Sentence_Patterns.json": payload["q5_sentence_patterns"],
        "Q07_MicroScene_Coverage.json": payload["q7_micro_scenes"],
        "Q08_Communicative_Functions.json": payload["q8_communicative_functions"],
        "Q09_Task_Angle_Question_Type.json": payload["q9_task_angle_question_type"],
        "Q10_QuestionBank_Capacity_Runtime.json": payload["q10_questionbank_capacity_runtime"],
    }
    for name, value in json_sections.items():
        path = output_dir / name
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        paths[name] = str(path)

    csv_exports = {
        "Q04_Chunks.csv": payload["q4_chunks"]["unit01_rows"] + payload["q4_chunks"]["unit02_rows"],
        "Q05_Exact_Sentence_Frames.csv": payload["q5_sentence_patterns"]["exact_frame_coverage"]["unit01_exact_frames"] + payload["q5_sentence_patterns"]["exact_frame_coverage"]["unit02_new_canonical_exact_frames"],
        "Q07_MicroScene_Coverage.csv": payload["q7_micro_scenes"]["coverage_recheck"],
        "Q07_Structural_Scene_Candidates.csv": payload["q7_micro_scenes"]["materialized_scene_candidates"],
        "Q08_Communicative_Functions.csv": payload["q8_communicative_functions"]["communicative_function_denominator"],
        "Q09_Task_Families.csv": payload["q9_task_angle_question_type"]["post_materialization_task_families"],
        "Q10_Unit02_Approved_QuestionBank.csv": payload["q10_questionbank_capacity_runtime"]["unit02_approved_items"],
        "Q10_Runtime_Occurrences.csv": payload["q10_questionbank_capacity_runtime"]["runtime_occurrences"],
    }
    for name, rows in csv_exports.items():
        path = output_dir / name
        _write_csv(path, rows)
        paths[name] = str(path)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "unit_id": UNIT_ID,
        "status": PASS_STATUS,
        "package_sha256": payload["package_sha256"],
        "q2_q3_existing_export_ref": payload["q2_q3_existing_export_ref"],
        "q6_existing_export_ref": payload["q6_existing_export_ref"],
        "files": sorted(paths),
    }
    manifest_path = output_dir / "Unit02_Final_Package_Manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths[manifest_path.name] = str(manifest_path)
    return paths


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    payload = build_export_payload()
    paths = write_exports(args.output_dir)
    print(f"STATUS={PASS_STATUS}")
    print(f"Q1_TARGET_EGP_ROWS={len(payload['q1_grammar']['target_egp_row_ids'])}")
    print(f"Q4_CUMULATIVE_CHUNKS={payload['q4_chunks']['coverage_denominators']['cumulative_distinct_surface_rows']}")
    print(f"Q5_CORE_PATTERN_FAMILIES={payload['q5_sentence_patterns']['pattern_family_coverage']['cumulative_pedagogical_core_pattern_family_count']}")
    print(f"Q5_EXACT_FRAMES={payload['q5_sentence_patterns']['exact_frame_coverage']['cumulative_declared_exact_frame_count']}")
    print(f"Q7_VOCABULARY_ROWS={payload['q7_micro_scenes']['coverage_denominators']['unit02_vocabulary_surface_count']}")
    print(f"Q8_FUNCTIONS={payload['q8_communicative_functions']['coverage_denominators']['communicative_function_family_count']}")
    print(f"Q9_TASK_FAMILIES={payload['q9_task_angle_question_type']['post_materialization_summary']['task_family_count']}")
    print(f"Q10_UNIT02_APPROVED_ITEMS={len(payload['q10_questionbank_capacity_runtime']['unit02_approved_items'])}")
    print(f"Q10_RUNTIME_OCCURRENCES={len(payload['q10_questionbank_capacity_runtime']['runtime_occurrences'])}")
    print(f"PACKAGE_SHA256={payload['package_sha256']}")
    for name, path in sorted(paths.items()):
        print(f"EXPORT_{name}={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
