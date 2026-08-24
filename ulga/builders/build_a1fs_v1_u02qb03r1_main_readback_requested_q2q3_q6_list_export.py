#!/usr/bin/env python3
"""Read back merged U02QB03 and export the requested Q2/Q3 and Q6 complete lists."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_v1_u02qb03_unit02_cumulative_questionbank_runtime_integration as u02qb03,
)
from ulga.builders import (
    build_a1fs_v1_u02sa01_unit01_unit02_cumulative_sentence_asset_coverage_recheck as u02sa01,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Read-only operator export of already-approved U02QB03 runtime readback plus Q2/Q3 and Q6 lists; creates no canonical content, QuestionBank items, SentenceAssets, learner state, scoring authority, or A2 content."

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U02QB03R1_MainReadbackAndRequestedQ2Q3Q6ListExport"
SCHEMA_VERSION = "a1fs.v1.u02qb03r1.requested_q2q3_q6_list_export.v1"
PASS_STATUS = "PASS_A1FS_V1_U02QB03R1_MAIN_READBACK_AND_REQUESTED_Q2Q3_Q6_LIST_EXPORT"
EXPECTED_Q2_Q3_ROWS = 162
EXPECTED_UNIT01_REFERENCE_ITEMS = 474
EXPECTED_UNIT02_APPROVED_ITEMS = 994
EXPECTED_CUMULATIVE_ITEMS = 1468
EXPECTED_RUNTIME_OCCURRENCES = 640
EXPECTED_Q6_BOUND_RUNTIME_OCCURRENCES = 128


class U02QB03R1ExportError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def build_export_payload() -> dict[str, Any]:
    runtime = u02qb03.build_report()
    q6 = u02sa01.build_report()
    q2_rows = [dict(row) for row in q6["q2_vocabulary_morphology_list"]]
    q6_assets = [dict(row) for row in q6["sentence_asset_delta"]["assets"]]

    catalog = runtime["cumulative_questionbank_catalog"]
    form = runtime["runtime_form_contract"]
    integration = runtime["sentence_asset_integration"]

    if runtime.get("status") != u02qb03.PASS_STATUS:
        raise U02QB03R1ExportError("QB03_MAIN_READBACK_STATUS_INVALID")
    if catalog.get("unit01_reference_only_item_count") != EXPECTED_UNIT01_REFERENCE_ITEMS:
        raise U02QB03R1ExportError("UNIT01_REFERENCE_COUNT_DRIFT")
    if catalog.get("unit02_approved_item_count") != EXPECTED_UNIT02_APPROVED_ITEMS:
        raise U02QB03R1ExportError("UNIT02_APPROVED_COUNT_DRIFT")
    if catalog.get("cumulative_catalog_item_count") != EXPECTED_CUMULATIVE_ITEMS:
        raise U02QB03R1ExportError("CUMULATIVE_CATALOG_COUNT_DRIFT")
    if form.get("runtime_occurrence_count") != EXPECTED_RUNTIME_OCCURRENCES:
        raise U02QB03R1ExportError("RUNTIME_OCCURRENCE_COUNT_DRIFT")
    if form.get("runtime_connected") is not True:
        raise U02QB03R1ExportError("QB03_RUNTIME_NOT_CONNECTED")
    if integration.get("bound_runtime_occurrence_count") != EXPECTED_Q6_BOUND_RUNTIME_OCCURRENCES:
        raise U02QB03R1ExportError("Q6_RUNTIME_BINDING_COUNT_DRIFT")
    if len(q2_rows) != EXPECTED_Q2_Q3_ROWS:
        raise U02QB03R1ExportError(f"Q2_Q3_ROW_COUNT_DRIFT:{len(q2_rows)}")
    if len({str(row["singular"]).casefold() for row in q2_rows}) != EXPECTED_Q2_Q3_ROWS:
        raise U02QB03R1ExportError("Q2_Q3_IDENTITY_NOT_DISTINCT")
    if len(q6_assets) != int(q6["sentence_asset_delta"]["asset_count"]):
        raise U02QB03R1ExportError("Q6_ASSET_COUNT_DRIFT")
    if len({str(row["sentence_id"]) for row in q6_assets}) != len(q6_assets):
        raise U02QB03R1ExportError("Q6_SENTENCE_ID_NOT_DISTINCT")
    if len({str(row["normalized_text"]) for row in q6_assets}) != len(q6_assets):
        raise U02QB03R1ExportError("Q6_NORMALIZED_TEXT_NOT_DISTINCT")

    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "main_readback": {
            "qb03_task_id": u02qb03.TASK_ID,
            "qb03_status": runtime["status"],
            "unit01_reference_item_count": catalog["unit01_reference_only_item_count"],
            "unit02_approved_item_count": catalog["unit02_approved_item_count"],
            "cumulative_catalog_item_count": catalog["cumulative_catalog_item_count"],
            "runtime_occurrence_count": form["runtime_occurrence_count"],
            "q6_bound_runtime_occurrence_count": integration["bound_runtime_occurrence_count"],
            "runtime_connected": form["runtime_connected"],
        },
        "q2_q3_vocabulary_morphology": {
            "row_count": len(q2_rows),
            "sha256": digest(q2_rows),
            "rows": q2_rows,
        },
        "q6_sentence_assets": {
            "asset_count": len(q6_assets),
            "asset_digest": q6["sentence_asset_delta"]["asset_digest"],
            "export_sha256": digest(q6_assets),
            "assets": q6_assets,
        },
        "claim_boundaries": {
            "readback_only": True,
            "canonical_content_created": False,
            "questionbank_mutated": False,
            "sentence_assets_mutated": False,
            "runtime_mutated": False,
            "learner_state_mutated": False,
            "a2_unlocked": False,
        },
    }


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return value


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                keys.append(str(key))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in keys})


def write_exports(output_dir: Path) -> dict[str, str]:
    payload = build_export_payload()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    q2_json = output_dir / "Unit02_Q2_Q3_Vocabulary_Morphology_Master_List.json"
    q2_csv = output_dir / "Unit02_Q2_Q3_Vocabulary_Morphology_Master_List.csv"
    q6_json = output_dir / "Unit02_Q6_Admitted_Sentence_Assets.json"
    q6_csv = output_dir / "Unit02_Q6_Admitted_Sentence_Assets.csv"
    readback_json = output_dir / "Unit02_QB03R1_Main_Readback.json"

    q2_json.write_text(
        json.dumps(payload["q2_q3_vocabulary_morphology"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    q6_json.write_text(
        json.dumps(payload["q6_sentence_assets"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    readback_json.write_text(
        json.dumps(
            {key: value for key, value in payload.items() if key not in {"q2_q3_vocabulary_morphology", "q6_sentence_assets"}},
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    _write_csv(q2_csv, payload["q2_q3_vocabulary_morphology"]["rows"])
    _write_csv(q6_csv, payload["q6_sentence_assets"]["assets"])
    return {
        "q2_q3_json": str(q2_json),
        "q2_q3_csv": str(q2_csv),
        "q6_json": str(q6_json),
        "q6_csv": str(q6_csv),
        "readback_json": str(readback_json),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    payload = build_export_payload()
    paths = write_exports(args.output_dir)
    print(f"STATUS={PASS_STATUS}")
    print(f"Q2_Q3_ROWS={payload['q2_q3_vocabulary_morphology']['row_count']}")
    print(f"Q6_SENTENCE_ASSETS={payload['q6_sentence_assets']['asset_count']}")
    print(f"Q6_ASSET_DIGEST={payload['q6_sentence_assets']['asset_digest']}")
    for key, value in sorted(paths.items()):
        print(f"EXPORT_{key.upper()}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
