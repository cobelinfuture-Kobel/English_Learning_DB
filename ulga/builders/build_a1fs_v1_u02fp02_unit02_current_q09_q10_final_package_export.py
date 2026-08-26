#!/usr/bin/env python3
"""Export the current Unit02 Q09/Q10 handoff package from R4R1 authority.

This is a read-only final-package consumer. It does not create or mutate
QuestionBank, runtime, SentenceAsset, scene, learner-state, scoring, or A2
authority. Q01-Q08 remain owned by the already accepted FP01 package; these
exports replace only the stale Q09/Q10 handoff files.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_u02form03r3_source_authority_pedagogical_fullfix_and_global_distinct_runtime
    as current,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Read-only Unit02 final-package export over merged U02FORM03R4R1 current Q09/Q10 authority; creates no canonical content, QuestionBank/runtime authority, SentenceAssets, scenes, learner state, scoring authority, Unit03+ content, or A2 authority."

PROGRAM_ID = "A1FS-V1"
UNIT_ID = "GRAMMAR_REGULAR_PLURAL_NOUNS"
TASK_ID = "A1FS-V1-U02FP02_Unit02CurrentQ09Q10FinalPackageExport"
SCHEMA_VERSION = "a1fs.v1.u02fp02.current_q09_q10_final_package_export.v1"
PASS_STATUS = "PASS_A1FS_V1_U02FP02_UNIT02_CURRENT_Q09_Q10_FINAL_PACKAGE_EXPORT"
R4R1_MERGE_SHA = "167d264613da7e54c5037aa06db93fa8a65a07ca"
R4R2_EVIDENCE_ZIP_SHA256 = "3748a540718b6bdd661b1b7b18e740d5d5da76214fae439ebccdaf73b71d8c81"
R4R2_PR = 543
R4R2_PR_COMMENT_ID = 5420959589

EXPECTED_UNIT02_ITEMS = 1730
EXPECTED_CUMULATIVE_ITEMS = 2204
EXPECTED_RUNTIME = 640
EXPECTED_FORMS = 16
EXPECTED_ACTIVITIES_PER_FORM = 40
EXPECTED_TASK_FAMILIES = 10
EXPECTED_Q6_BOUND = 128
EXPECTED_TRANSFER_STAGE = 160


class U02FP02ExportError(ValueError):
    pass


def _digest(value: Any) -> str:
    return policy_artifact.digest(value)


def _source_authority() -> dict[str, Any]:
    return {
        "current_authority_task_id": current.TASK_ID,
        "r4r1_merge_sha": R4R1_MERGE_SHA,
        "r4r2_human_acceptance": {
            "status": "PASS",
            "evidence_zip_sha256": R4R2_EVIDENCE_ZIP_SHA256,
            "pr": R4R2_PR,
            "pr_comment_id": R4R2_PR_COMMENT_ID,
            "forms01_12_preservation": "PASS",
            "forms13_16_transfer_reacceptance": "PASS",
            "forms_human_accepted": 16,
            "activities_human_accepted": 640,
        },
        "authority_rule": "GitHub current approved authority wins over handoff/export bytes.",
    }


def build_export_payload() -> dict[str, Any]:
    full = current.build_export_payload()
    q9 = full["q9_task_angle_question_type"]
    q10 = full["q10_questionbank_capacity_runtime"]
    inventory = q10["inventory_summary"]
    form_contract = q10["runtime_form_contract"]
    proof = q10["global_distinctness_proof"]

    if inventory["unit02_approved_item_count"] != EXPECTED_UNIT02_ITEMS:
        raise U02FP02ExportError("UNIT02_ITEM_COUNT_DRIFT")
    if inventory["cumulative_catalog_item_count"] != EXPECTED_CUMULATIVE_ITEMS:
        raise U02FP02ExportError("CUMULATIVE_ITEM_COUNT_DRIFT")
    if form_contract["runtime_occurrence_count"] != EXPECTED_RUNTIME:
        raise U02FP02ExportError("RUNTIME_COUNT_DRIFT")
    if form_contract["form_count"] != EXPECTED_FORMS:
        raise U02FP02ExportError("FORM_COUNT_DRIFT")
    if form_contract["activities_per_form"] != EXPECTED_ACTIVITIES_PER_FORM:
        raise U02FP02ExportError("ACTIVITIES_PER_FORM_DRIFT")
    if q9["post_materialization_summary"]["task_family_count"] != EXPECTED_TASK_FAMILIES:
        raise U02FP02ExportError("TASK_FAMILY_COUNT_DRIFT")
    if q10["sentence_asset_integration"]["bound_runtime_occurrence_count"] != EXPECTED_Q6_BOUND:
        raise U02FP02ExportError("Q6_BOUND_COUNT_DRIFT")
    if q10["progression_support_contract"]["transfer_stage_runtime_occurrences"] != EXPECTED_TRANSFER_STAGE:
        raise U02FP02ExportError("TRANSFER_STAGE_COUNT_DRIFT")
    if proof["global_640_distinct_runtime_question_proof"] is not True:
        raise U02FP02ExportError("GLOBAL_DISTINCTNESS_NOT_PROVEN")
    if proof["distinct_visible_signatures"] != EXPECTED_RUNTIME:
        raise U02FP02ExportError("VISIBLE_DISTINCTNESS_DRIFT")
    if proof["prior_activity_direct_answer_leaks"] != 0:
        raise U02FP02ExportError("PRIOR_ANSWER_LEAK_DRIFT")

    result = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "unit_id": UNIT_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "source_authority": _source_authority(),
        "q9_task_angle_question_type": q9,
        "q10_questionbank_capacity_runtime": q10,
        "claim_boundaries": {
            "q01_q08_reexported": False,
            "q01_q08_mutated": False,
            "q09_q10_read_only_export": True,
            "canonical_content_created": False,
            "questionbank_or_runtime_authority_created": False,
            "sentence_assets_created": False,
            "canonical_scene_authority_created": False,
            "learner_state_mutated": False,
            "scoring_authority_created": False,
            "a2_unlocked": False,
        },
    }
    result["current_q09_q10_sha256"] = _digest(result)
    return result


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return value


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            name = str(key)
            if name not in seen:
                seen.add(name)
                keys.append(name)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in keys})


def _q10_summary(q10: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "unit_id": UNIT_ID,
        "source_authority": _source_authority(),
        "inventory_summary": q10["inventory_summary"],
        "runtime_eligibility": q10["runtime_eligibility"],
        "sentence_asset_integration": q10["sentence_asset_integration"],
        "runtime_form_contract": q10["runtime_form_contract"],
        "global_distinctness_proof": q10["global_distinctness_proof"],
        "progression_support_contract": q10["progression_support_contract"],
        "legacy_runtime_authority_superseded_for_current_delivery": q10[
            "legacy_runtime_authority_superseded_for_current_delivery"
        ],
        "full_unit02_approved_item_inventory_exported": True,
        "full_runtime_occurrence_plan_exported": True,
    }


def _q10_inventory(q10: Mapping[str, Any]) -> dict[str, Any]:
    items = list(q10["unit02_approved_items"])
    return {
        "schema_version": SCHEMA_VERSION,
        "unit_id": UNIT_ID,
        "source_authority": _source_authority(),
        "item_count": len(items),
        "distinct_item_id_count": len({str(row["item_id"]) for row in items}),
        "items_sha256": _digest(items),
        "items": items,
    }


def _q10_runtime_plan(q10: Mapping[str, Any]) -> dict[str, Any]:
    rows = list(q10["runtime_occurrences"])
    return {
        "schema_version": SCHEMA_VERSION,
        "unit_id": UNIT_ID,
        "source_authority": _source_authority(),
        **dict(q10["runtime_form_contract"]),
        "runtime_restricted_surfaces": list(q10["runtime_eligibility"]["restricted_target_surfaces"]),
        "restricted_questionbank_item_ids": list(q10["runtime_eligibility"]["restricted_questionbank_item_ids"]),
        "q6_bound_runtime_occurrence_count": q10["sentence_asset_integration"]["bound_runtime_occurrence_count"],
        "q6_bound_distinct_sentence_asset_count": q10["sentence_asset_integration"]["bound_distinct_sentence_asset_count"],
        "global_distinctness_proof": q10["global_distinctness_proof"],
        "progression_support_contract": q10["progression_support_contract"],
        "runtime_rows_sha256": _digest(rows),
        "runtime_occurrences": rows,
    }


def write_exports(output_dir: Path) -> dict[str, str]:
    payload = build_export_payload()
    q9 = payload["q9_task_angle_question_type"]
    q10 = payload["q10_questionbank_capacity_runtime"]
    summary = _q10_summary(q10)
    inventory = _q10_inventory(q10)
    runtime_plan = _q10_runtime_plan(q10)

    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}

    json_files = {
        "Q09_Task_Angle_Question_Type.json": q9,
        "Q10_QuestionBank_Runtime_Summary.json": summary,
        "Q10_QuestionBank_Inventory.json": inventory,
        "Q10_Runtime_Form_Plan.json": runtime_plan,
    }
    for name, value in json_files.items():
        path = output_dir / name
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        paths[name] = str(path)

    csv_files = {
        "Q09_Task_Families.csv": q9["post_materialization_task_families"],
        "Q10_QuestionBank_Runtime_Summary.csv": [
            {
                "unit01_reference_only_item_count": summary["inventory_summary"]["unit01_reference_only_item_count"],
                "unit02_approved_item_count": summary["inventory_summary"]["unit02_approved_item_count"],
                "cumulative_catalog_item_count": summary["inventory_summary"]["cumulative_catalog_item_count"],
                "runtime_occurrence_count": summary["runtime_form_contract"]["runtime_occurrence_count"],
                "form_count": summary["runtime_form_contract"]["form_count"],
                "activities_per_form": summary["runtime_form_contract"]["activities_per_form"],
                "task_family_count": summary["runtime_form_contract"]["task_family_count"],
                "q6_bound_runtime_occurrence_count": summary["sentence_asset_integration"]["bound_runtime_occurrence_count"],
                "distinct_visible_signatures": summary["global_distinctness_proof"]["distinct_visible_signatures"],
                "prior_activity_direct_answer_leaks": summary["global_distinctness_proof"]["prior_activity_direct_answer_leaks"],
                "global_640_distinct_runtime_question_proof": summary["global_distinctness_proof"]["global_640_distinct_runtime_question_proof"],
                "transfer_stage_runtime_occurrences": summary["progression_support_contract"]["transfer_stage_runtime_occurrences"],
                "transfer_demand_proven": summary["progression_support_contract"]["transfer_demand_proven"],
                "human_acceptance": "PASS",
                "r4r2_evidence_zip_sha256": R4R2_EVIDENCE_ZIP_SHA256,
            }
        ],
        "Q10_QuestionBank_Inventory.csv": q10["unit02_approved_items"],
        "Q10_Runtime_Form_Plan.csv": q10["runtime_occurrences"],
    }
    for name, rows in csv_files.items():
        path = output_dir / name
        _write_csv(path, rows)
        paths[name] = str(path)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "unit_id": UNIT_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "source_authority": _source_authority(),
        "current_q09_q10_sha256": payload["current_q09_q10_sha256"],
        "replacement_scope": "REPLACE_OLD_UNIT02_Q09_Q10_FILES_ONLY",
        "q01_q08_preserved_from_existing_final_package": True,
        "files": sorted(paths),
    }
    manifest_path = output_dir / "Unit02_Q09_Q10_Current_Manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths[manifest_path.name] = str(manifest_path)
    return paths


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    payload = build_export_payload()
    paths = write_exports(args.output_dir)
    q9 = payload["q9_task_angle_question_type"]
    q10 = payload["q10_questionbank_capacity_runtime"]
    print(f"STATUS={PASS_STATUS}")
    print(f"Q9_TASK_FAMILIES={q9['post_materialization_summary']['task_family_count']}")
    print(f"Q10_UNIT02_APPROVED_ITEMS={q10['inventory_summary']['unit02_approved_item_count']}")
    print(f"Q10_CUMULATIVE_ITEMS={q10['inventory_summary']['cumulative_catalog_item_count']}")
    print(f"Q10_RUNTIME_OCCURRENCES={q10['runtime_form_contract']['runtime_occurrence_count']}")
    print(f"Q10_DISTINCT_VISIBLE={q10['global_distinctness_proof']['distinct_visible_signatures']}")
    print(f"Q10_PRIOR_ANSWER_LEAKS={q10['global_distinctness_proof']['prior_activity_direct_answer_leaks']}")
    print(f"TRANSFER_STAGE_OCCURRENCES={q10['progression_support_contract']['transfer_stage_runtime_occurrences']}")
    print("R4R2_HUMAN_ACCEPTANCE=PASS")
    print(f"CURRENT_Q09_Q10_SHA256={payload['current_q09_q10_sha256']}")
    for name, path in sorted(paths.items()):
        print(f"EXPORT_{name}={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
