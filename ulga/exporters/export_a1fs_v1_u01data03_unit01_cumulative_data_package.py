#!/usr/bin/env python3
"""Export Unit01 cumulative registry and U01E linkage as JSON/CSV workbook source tables."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ulga.builders import build_a1fs_v1_u01data01_unit01_cumulative_reusable_language_asset_registry as u01data01
from ulga.builders import build_a1fs_v1_u01data02_unit01_existing_u01e_projection_and_cumulative_linkage as u01data02
from ulga.validators import validate_a1fs_v1_u01data01_unit01_cumulative_reusable_language_asset_registry as validate_registry
from ulga.validators import validate_a1fs_v1_u01data02_unit01_existing_u01e_projection_and_cumulative_linkage as validate_projection

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Exports approved Unit01 metadata and reference-only linkage into JSON and CSV tables for one-way Excel consumption; it creates no learner-facing content, question, answer, scoring, learner state, audio, A2 target, canonical write, or parallel curriculum."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01DATA03_Unit01CumulativeDataWorkbookAndJsonExport"
SCHEMA_VERSION = "a1fs.v1.u01data03.unit01_cumulative_data_export_package.v1"
PASS_STATUS = "PASS_A1FS_V1_U01DATA03_UNIT01_CUMULATIVE_DATA_EXPORT_PACKAGE"
UNIT_ID = u01data01.UNIT_ID
SNAPSHOT_NAME = "a1fs_v1_u01data03_unit01_cumulative_data_snapshot.json"
WORKBOOK_SPEC_NAME = "a1fs_v1_u01data03_unit01_workbook_spec.json"
FILE_NAMES = {
    "summary": "00_unit_summary.csv",
    "assets": "01_language_assets.csv",
    "contexts": "02_contexts.csv",
    "sentences": "03_sentences.csv",
    "activities": "04_activities.csv",
    "activity_asset_links": "05_activity_asset_links.csv",
    "external_support": "06_external_support.csv",
}
NEXT_SHORT_STEP = "A1FS-V1-U01DATA04_Unit01ProductionWorkbookMaterializationAndOperatorReview"


class ExportError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def joined(values: Iterable[Any]) -> str:
    return " | ".join(str(value) for value in values)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExportError(f"UNREADABLE_JSON:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ExportError(f"OBJECT_REQUIRED:{path}")
    return value


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def asset_rows(registry: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for group_name, rows in registry["asset_bindings"].items():
        for row in rows:
            result.append(
                {
                    "binding_id": row["binding_id"],
                    "asset_id": row["asset_id"],
                    "asset_group": group_name,
                    "asset_kind": row["asset_kind"],
                    "surface_or_template": row.get("surface_form") or row.get("template") or "",
                    "normalized_surface": row.get("normalized_surface") or "",
                    "part_of_speech": row.get("part_of_speech") or "",
                    "cefr_level": row.get("cefr_level") or "",
                    "introduced_unit_id": row["introduced_unit_id"],
                    "introduced_unit_sequence": row["introduced_unit_sequence"],
                    "unit01_role": row["unit01_role"],
                    "unit01_learning_role": row.get("unit01_learning_role") or row.get("frame_role") or "",
                    "production_allowed": row.get("production_allowed", ""),
                    "direct_assessment_allowed": row.get("direct_assessment_allowed", ""),
                    "source_authority": row.get("source_authority") or "",
                    "future_unit_roles": joined(row["eligible_future_unit_roles"]),
                    "copy_on_reuse": row["copy_on_reuse"],
                    "reusable_in_later_units": row["reusable_in_later_units"],
                }
            )
    return sorted(result, key=lambda row: (row["asset_group"], row["binding_id"]))


def context_rows(projection: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "context_id": row["context_id"],
            "context_role": row["context_role"],
            "setting": row["setting"],
            "source_role": row["source_role"],
            "introduced_unit_id": row["introduced_unit_id"],
            "sentence_count": len(row["sentence_ids"]),
            "sentence_ids": joined(row["sentence_ids"]),
            "linked_registry_binding_count": len(row["linked_registry_binding_ids"]),
            "linked_registry_binding_ids": joined(row["linked_registry_binding_ids"]),
            "future_unit_roles": joined(row["eligible_future_unit_roles"]),
            "copy_on_reuse": row["copy_on_reuse"],
        }
        for row in projection["context_projections"]
    ]


def sentence_rows(projection: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "sentence_id": row["sentence_id"],
            "context_id": row["context_id"],
            "learning_role": row["learning_role"],
            "source_role": row["source_role"],
            "introduced_unit_id": row["introduced_unit_id"],
            "linked_registry_binding_count": len(row["linked_registry_binding_ids"]),
            "linked_registry_binding_ids": joined(row["linked_registry_binding_ids"]),
            "text_ownership": row["text_ownership"],
            "future_unit_roles": joined(row["eligible_future_unit_roles"]),
            "copy_on_reuse": row["copy_on_reuse"],
        }
        for row in projection["sentence_asset_projections"]
    ]


def activity_rows(projection: Mapping[str, Any]) -> list[dict[str, Any]]:
    groups = projection["activity_projections"]
    activities = [*groups["existing_response_contract_activities"], *groups["fixed_admitted_items"]]
    return [
        {
            "activity_id": row["activity_id"],
            "activity_source": row["activity_source"],
            "activity_owner_task_id": row["activity_owner_task_id"],
            "item_bank_id": row.get("item_bank_id") or "",
            "item_bank_version": row.get("item_bank_version") or "",
            "lesson_id": row.get("lesson_id") or "",
            "skill": row["skill"],
            "question_type": row["question_type"],
            "learning_role": row.get("learning_role") or "",
            "support_level": row.get("support_level") or "",
            "context_id": row["context_id"],
            "target_sentence_ids": joined(row["target_sentence_ids"]),
            "target_egp_row_ids": joined(row["target_egp_row_ids"]),
            "target_pattern_ids": joined(row["target_pattern_ids"]),
            "linked_registry_binding_count": len(row["linked_registry_binding_ids"]),
            "linked_registry_binding_ids": joined(row["linked_registry_binding_ids"]),
            "unlinked_external_support_count": len(row["unlinked_external_support_target_ids"]),
            "unlinked_external_support_target_ids": joined(row["unlinked_external_support_target_ids"]),
            "linkage_status": row["linkage_status"],
            "semantic_signature": row.get("semantic_signature") or "",
            "future_unit_roles": joined(row["eligible_future_unit_roles"]),
            "copy_on_reuse": row["copy_on_reuse"],
        }
        for row in sorted(activities, key=lambda item: item["activity_id"])
    ]


def link_rows(activities: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for activity in activities:
        for binding_id in str(activity["linked_registry_binding_ids"]).split(" | "):
            if binding_id:
                rows.append(
                    {
                        "activity_id": activity["activity_id"],
                        "skill": activity["skill"],
                        "context_id": activity["context_id"],
                        "binding_id": binding_id,
                        "relationship": "TARGET_OR_STIMULUS_LANGUAGE_REFERENCE",
                    }
                )
    return sorted(rows, key=lambda row: (row["activity_id"], row["binding_id"]))


def external_support_rows(activities: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_target: defaultdict[str, list[str]] = defaultdict(list)
    for row in activities:
        for target in str(row["unlinked_external_support_target_ids"]).split(" | "):
            if target:
                by_target[target].append(str(row["activity_id"]))
    return [
        {
            "external_support_target_id": target,
            "referencing_activity_count": len(activity_ids),
            "referencing_activity_ids": joined(sorted(activity_ids)),
            "promotion_status": "NOT_PROMOTED_TO_U01DATA01_REGISTRY",
            "required_action": "REVIEW_BEFORE_ANY_CUMULATIVE_CORE_ADMISSION",
        }
        for target, activity_ids in sorted(by_target.items())
    ]


def summary_rows(registry: Mapping[str, Any], projection: Mapping[str, Any], tables: Mapping[str, Sequence[Mapping[str, Any]]]) -> list[dict[str, Any]]:
    values = {
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "unit_id": UNIT_ID,
        "registry_sha256": registry["registry_sha256"],
        "projection_sha256": projection["projection_sha256"],
        "language_asset_binding_count": len(tables["assets"]),
        "context_count": len(tables["contexts"]),
        "sentence_count": len(tables["sentences"]),
        "activity_count": len(tables["activities"]),
        "activity_asset_link_count": len(tables["activity_asset_links"]),
        "external_support_target_count": len(tables["external_support"]),
        "reading_activity_count": projection["linkage_summary"]["activity_count_by_skill"]["READING"],
        "writing_activity_count": projection["linkage_summary"]["activity_count_by_skill"]["WRITING"],
        "speaking_activity_count": projection["linkage_summary"]["activity_count_by_skill"]["SPEAKING"],
        "listening_status": "DEFERRED",
        "json_is_authority": True,
        "excel_is_one_way_export": True,
        "excel_writeback_allowed": False,
        "a2_unlocked": False,
    }
    return [{"metric": key, "value": value} for key, value in values.items()]


def workbook_spec(tables: Mapping[str, Sequence[Mapping[str, Any]]], snapshot_sha256: str) -> dict[str, Any]:
    sheet_names = {
        "summary": "00_Unit_Summary",
        "assets": "01_Language_Assets",
        "contexts": "02_Contexts",
        "sentences": "03_Sentences",
        "activities": "04_Activities",
        "activity_asset_links": "05_Activity_Asset_Links",
        "external_support": "06_External_Support",
    }
    return {
        "schema_version": "a1fs.v1.u01data03.unit01_workbook_spec.v1",
        "task_id": TASK_ID,
        "unit_id": UNIT_ID,
        "snapshot_sha256": snapshot_sha256,
        "workbook_file_name": "A1FS_Unit01_Cumulative_Data.xlsx",
        "json_is_authority": True,
        "excel_is_one_way_export": True,
        "excel_writeback_allowed": False,
        "sheet_order": [sheet_names[key] for key in sheet_names],
        "sheets": [
            {
                "table_key": key,
                "sheet_name": sheet_names[key],
                "csv_source": FILE_NAMES[key],
                "row_count": len(tables[key]),
                "columns": list(tables[key][0]) if tables[key] else [],
                "freeze_header": True,
                "filter_enabled": True,
            }
            for key in sheet_names
        ],
        "formatting_policy": {
            "header_style": "DARK_TEAL_WHITE_BOLD",
            "text_columns_wrap": True,
            "boolean_format": "TRUE_FALSE",
            "id_columns_text_format": True,
            "conditional_status_columns": ["linkage_status", "promotion_status"],
        },
    }


def build_export_package(registry: Mapping[str, Any], projection: Mapping[str, Any]) -> dict[str, Any]:
    validate_registry.validate_report(registry)
    validate_projection.validate_report(projection)
    if projection["source_identity"]["u01data01_registry_sha256"] != registry["registry_sha256"]:
        raise ExportError("REGISTRY_PROJECTION_DIGEST_MISMATCH")
    tables: dict[str, list[dict[str, Any]]] = {
        "assets": asset_rows(registry),
        "contexts": context_rows(projection),
        "sentences": sentence_rows(projection),
        "activities": activity_rows(projection),
    }
    tables["activity_asset_links"] = link_rows(tables["activities"])
    tables["external_support"] = external_support_rows(tables["activities"])
    tables["summary"] = summary_rows(registry, projection, tables)
    core = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "source_identity": {
            "registry_sha256": registry["registry_sha256"],
            "projection_sha256": projection["projection_sha256"],
            "registry_task_id": registry["task_id"],
            "projection_task_id": projection["task_id"],
        },
        "authority_contract": {
            "json_is_authority": True,
            "csv_and_excel_are_one_way_exports": True,
            "excel_writeback_allowed": False,
            "stable_ids_preserved": True,
            "question_or_answer_payload_exported": False,
        },
        "table_counts": {key: len(rows) for key, rows in tables.items()},
        "tables": tables,
        "boundaries": {
            "canonical_content_modified": False,
            "learner_state_exported": False,
            "question_content_exported": False,
            "answer_content_exported": False,
            "audio_exported": False,
            "a2_unlocked": False,
            "parallel_curriculum_created": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    core["snapshot_sha256"] = digest(core)
    core["workbook_spec"] = workbook_spec(tables, core["snapshot_sha256"])
    return core


def materialize(*, registry_path: Path, projection_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    package = build_export_package(read_json(registry_path), read_json(projection_path))
    write_json(output_dir / SNAPSHOT_NAME, {key: value for key, value in package.items() if key != "workbook_spec"})
    write_json(output_dir / WORKBOOK_SPEC_NAME, package["workbook_spec"])
    for key, file_name in FILE_NAMES.items():
        rows = package["tables"][key]
        columns = list(rows[0]) if rows else []
        write_csv(output_dir / file_name, rows, columns)
    return package


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry-report", type=Path, required=True)
    parser.add_argument("--projection-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        package = materialize(registry_path=args.registry_report.resolve(), projection_path=args.projection_report.resolve(), output_dir=args.output_dir.resolve())
    except (ExportError, ValueError, KeyError, TypeError, OSError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01DATA03_UNIT01_CUMULATIVE_DATA_EXPORT_PACKAGE")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={package['status']}")
    for key, value in package["table_counts"].items():
        print(f"{key.upper()}_ROWS={value}")
    print(f"SNAPSHOT_SHA256={package['snapshot_sha256']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
