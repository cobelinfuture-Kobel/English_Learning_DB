#!/usr/bin/env python3
"""Materialize the Unit03 final working package against current GitHub authority.

The handoff directory supplies the already-reviewed large/private Q01-Q04/Q06-Q08
exports. Current merged GitHub authority supplies Q05 and successor Q09/Q10.
This module is an export/materialization consumer only; it creates no canonical
content, QuestionBank/runtime authority, SentenceAssets, scenes, learner state,
scoring authority, Unit04 content, or A2 authority.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_v1_u03fp01_unit03_q1_q10_final_package_successor_reconciliation as fp01,
)
from ulga.builders import (
    build_a1fs_v1_u03q05r1_unit03_exact_lesson_sentence_pattern_binding_crosscheck as q5,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Read-only Unit03 final-working-package materialization. It validates and copies already-reviewed Q01-Q04/Q06-Q08 handoff artifacts, regenerates current Q05/Q09/Q10 exports from merged GitHub authority, and creates no canonical content, authority, selector, runtime, renderer, learner state, scoring, Unit04, Q11, or A2 content."

PROGRAM_ID = "A1FS-V1"
UNIT_ID = "GRAMMAR_SUBJECT_PRONOUNS"
TASK_ID = "A1FS-V1-U03FP02_Unit03FinalWorkingPackageCurrentAuthorityMaterialization"
SCHEMA_VERSION = "a1fs.v1.u03fp02.final_working_package_current_authority_materialization.v1"
PASS_STATUS = "PASS_A1FS_V1_U03FP02_UNIT03_FINAL_WORKING_PACKAGE_CURRENT_AUTHORITY_MATERIALIZATION"

Q1_SHA = fp01.Q1_SHA
Q3_SHA = fp01.Q3_SHA
Q6_SHA = fp01.Q6_SHA
Q4_SHA = "45cda8023e49bd99dd1719d5697241c20ba219f4cf66dfe09bd253413e41cd18"
Q8_SHA = "af8e625b06de44da4b47e8c80f91c24a4cfc8fc5507f4a1ae3486dd02c39e9cb"

REQUIRED_HANDOFF_FILES = (
    "Unit03_Q01_Grammar.json",
    "Unit03_Q02_Vocabulary.json",
    "Unit03_Q03_Pronoun_Forms.json",
    "Unit03_Q04_Chunks.json",
    "Unit03_Q06_Sentence_Assets.json",
    "Unit03_Q06_Sentence_Assets.csv",
    "Unit03_Q07_MicroScene_Coverage.json",
    "Unit03_Q07_Canonical_Scene_Reuse.csv",
    "Unit03_Q07_Structural_Scene_Projections.csv",
    "Unit03_Q08_Communicative_Functions.json",
)
OPTIONAL_HANDOFF_FILES = (
    "Unit03_Q02_Vocabulary.csv",
    "Unit03_Q03_Pronoun_Forms.csv",
    "Unit03_Q04_Chunks.csv",
    "Unit03_Q06_Context_Bindings.csv",
    "Unit03_Q06_Exclusion_Summary.json",
    "Unit03_Q07_Pronoun_Coverage.csv",
    "Unit03_Q08_Communicative_Functions.csv",
    "Unit03_Q08_Function_Pronoun_Matrix.csv",
)
CURRENT_Q05_FILES = (
    "Q05_Sentence_Patterns.json",
    "Q05_Pedagogical_Pattern_Families.csv",
    "Q05_Exact_Sentence_Frames.csv",
)
MANIFEST_NAME = "Unit03_Final_Working_Package_Current_Manifest.json"


class U03FP02MaterializationError(ValueError):
    pass


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _cell(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return value


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            key = str(key)
            if key not in seen:
                seen.add(key)
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _cell(row.get(field)) for field in fields})


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _embedded_sha(payload: Mapping[str, Any]) -> str:
    return str(payload.get("sha256") or "")


def _validate_handoff(handoff_dir: Path) -> dict[str, Any]:
    missing = [name for name in REQUIRED_HANDOFF_FILES if not (handoff_dir / name).is_file()]
    if missing:
        raise U03FP02MaterializationError("MISSING_HANDOFF_FILES:" + ",".join(missing))

    current = fp01.build_export_payload()
    fp01.validate(current)
    qmap = current["q01_q10_map"]

    q1 = _load_json(handoff_dir / "Unit03_Q01_Grammar.json")
    grammar = q1.get("grammar_scope", {})
    if _embedded_sha(q1) != Q1_SHA:
        raise U03FP02MaterializationError("Q01_HANDOFF_SHA_DRIFT")
    if grammar.get("pronoun_inventory_denominator") != qmap["Q01"]["pronoun_count"]:
        raise U03FP02MaterializationError("Q01_PRONOUN_COUNT_DRIFT")
    rows = q1.get("target_egp_rows", [])
    if len(rows) != 1 or rows[0].get("egp_row_id") != qmap["Q01"]["egp_row_id"]:
        raise U03FP02MaterializationError("Q01_EGP_ROW_DRIFT")

    q2 = _load_json(handoff_dir / "Unit03_Q02_Vocabulary.json")
    if q2.get("row_count") != qmap["Q02"]["support_pool_count"]:
        raise U03FP02MaterializationError("Q02_SUPPORT_POOL_DRIFT")
    if len(q2.get("rows", [])) != 40:
        raise U03FP02MaterializationError("Q02_ROW_COUNT_DRIFT")
    if q2.get("scope_summary", {}).get("unit03_definitely_new_vocabulary_claimed") is not False:
        raise U03FP02MaterializationError("Q02_UNSAFE_NEW_VOCABULARY_CLAIM")

    q3 = _load_json(handoff_dir / "Unit03_Q03_Pronoun_Forms.json")
    if _embedded_sha(q3) != Q3_SHA:
        raise U03FP02MaterializationError("Q03_HANDOFF_SHA_DRIFT")
    d3 = q3.get("coverage_denominators", {})
    if (d3.get("closed_subject_pronoun_form_count"), d3.get("generated_inflection_count")) != (7, 0):
        raise U03FP02MaterializationError("Q03_DENOMINATOR_DRIFT")

    q4 = _load_json(handoff_dir / "Unit03_Q04_Chunks.json")
    if _embedded_sha(q4) != Q4_SHA:
        raise U03FP02MaterializationError("Q04_HANDOFF_SHA_DRIFT")
    d4 = q4.get("coverage_denominators", {})
    if (d4.get("cumulative_distinct_surface_rows"), d4.get("unit03_native_surface_rows")) != (
        qmap["Q04"]["cumulative_distinct_surface_rows"], 0
    ):
        raise U03FP02MaterializationError("Q04_DENOMINATOR_DRIFT")

    q6_path = handoff_dir / "Unit03_Q06_Sentence_Assets.json"
    if _file_sha256(q6_path) != Q6_SHA:
        raise U03FP02MaterializationError("Q06_FILE_SHA_DRIFT")

    q7 = _load_json(handoff_dir / "Unit03_Q07_MicroScene_Coverage.json")
    d7 = q7.get("coverage_denominators", {})
    if (
        d7.get("subject_pronoun_scene_covered_count"),
        d7.get("unit03_structural_pronoun_projection_row_count"),
        d7.get("unit03_new_canonical_scene_count"),
    ) != (7, 540, 0):
        raise U03FP02MaterializationError("Q07_DENOMINATOR_DRIFT")

    q8 = _load_json(handoff_dir / "Unit03_Q08_Communicative_Functions.json")
    if _embedded_sha(q8) != Q8_SHA:
        raise U03FP02MaterializationError("Q08_HANDOFF_SHA_DRIFT")
    functions = [str(row.get("function")) for row in q8.get("functions", [])]
    if functions != fp01.Q8_FUNCTIONS:
        raise U03FP02MaterializationError("Q08_FUNCTION_DRIFT")

    return {"current": current, "q1": q1, "q2": q2, "q3": q3, "q4": q4, "q7": q7, "q8": q8}


def _write_current_q05(output_dir: Path) -> list[str]:
    report = q5.build_report()
    q5.validate(report)
    families = report["q5_pattern_family_coverage"]
    frames = report["q5_exact_frame_coverage"]
    payload = {
        "schema_version": "a1fs.unit03.final_package.q5.current_main.v3",
        "program_id": PROGRAM_ID,
        "unit_id": UNIT_ID,
        "q": "Q05",
        "status": "CURRENT_MAIN_EXACT_BINDING_RECONCILED",
        "source_task_id": q5.TASK_ID,
        "pedagogical_pattern_families": families,
        "exact_sentence_frames": frames,
        "lesson_binding": report["lesson_binding"],
        "admission_decision": report["admission_decision"],
        "supersedes_old_eight_family_working_handoff": True,
        "claim_boundaries": report["claim_boundaries"],
    }
    _write_json(output_dir / CURRENT_Q05_FILES[0], payload)
    _write_csv(output_dir / CURRENT_Q05_FILES[1], list(families["inherited_families"]))
    _write_csv(output_dir / CURRENT_Q05_FILES[2], list(frames["inherited_exact_frames"]))
    return list(CURRENT_Q05_FILES)


def _copy_handoff_files(handoff_dir: Path, output_dir: Path) -> list[str]:
    names: list[str] = []
    for name in (*REQUIRED_HANDOFF_FILES, *OPTIONAL_HANDOFF_FILES):
        source = handoff_dir / name
        if source.is_file():
            shutil.copy2(source, output_dir / name)
            names.append(name)
    return names


def _currentize_q8(output_dir: Path) -> None:
    path = output_dir / "Unit03_Q08_Communicative_Functions.json"
    payload = _load_json(path)
    source_claim_boundaries = dict(payload.get("claim_boundaries", {}))
    payload["source_snapshot_claim_boundaries"] = source_claim_boundaries
    boundaries = dict(source_claim_boundaries)
    boundaries.pop("q9_not_materialized", None)
    boundaries.pop("q10_not_materialized", None)
    payload["claim_boundaries"] = boundaries
    payload["current_package_reconciliation"] = {
        "source_snapshot_preserved": True,
        "q09_current_successor_materialized": True,
        "q10_current_successor_materialized": True,
        "q08_authority_mutated": False,
    }
    payload.pop("sha256", None)
    _write_json(path, payload)


def _ensure_simple_csv_exports(validated: Mapping[str, Any], output_dir: Path) -> list[str]:
    generated: list[str] = []
    specs = (
        ("Unit03_Q02_Vocabulary.csv", validated["q2"].get("rows", [])),
        ("Unit03_Q03_Pronoun_Forms.csv", validated["q3"].get("forms", validated["q3"].get("rows", []))),
        ("Unit03_Q04_Chunks.csv", validated["q4"].get("rows", [])),
        ("Unit03_Q07_Pronoun_Coverage.csv", validated["q7"].get("pronoun_coverage", [])),
        ("Unit03_Q08_Communicative_Functions.csv", validated["q8"].get("functions", [])),
    )
    for name, rows in specs:
        path = output_dir / name
        if not path.exists() and rows:
            _write_csv(path, list(rows))
            generated.append(name)
    return generated


def _write_zip(package_dir: Path, zip_output: Path) -> None:
    zip_output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(package_dir.iterdir()):
            if path.is_file():
                archive.write(path, arcname=f"Unit03_Final_Working_Package/{path.name}")


def materialize(handoff_dir: Path, output_dir: Path, zip_output: Path | None = None) -> dict[str, Any]:
    validated = _validate_handoff(handoff_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    copied = _copy_handoff_files(handoff_dir, output_dir)
    generated = _ensure_simple_csv_exports(validated, output_dir)
    _currentize_q8(output_dir)
    q05_files = _write_current_q05(output_dir)
    fp01_paths = fp01.write_exports(output_dir)

    current = validated["current"]
    current_files = sorted(set(q05_files) | set(fp01_paths))
    package_files = sorted(path.name for path in output_dir.iterdir() if path.is_file())
    role_map = {
        "Q01": ["Unit03_Q01_Grammar.json"],
        "Q02": [name for name in package_files if name.startswith("Unit03_Q02_Vocabulary")],
        "Q03": [name for name in package_files if name.startswith("Unit03_Q03_Pronoun_Forms")],
        "Q04": [name for name in package_files if name.startswith("Unit03_Q04_Chunks")],
        "Q05": list(CURRENT_Q05_FILES),
        "Q06": [name for name in package_files if name.startswith("Unit03_Q06_")],
        "Q07": [name for name in package_files if name.startswith("Unit03_Q07_")],
        "Q08": [name for name in package_files if name.startswith("Unit03_Q08_")],
        "Q09": [fp01.Q09_JSON, fp01.Q09_CSV],
        "Q10": [fp01.Q10I_JSON, fp01.Q10I_CSV, fp01.Q10R_JSON, fp01.Q10R_CSV],
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "unit_id": UNIT_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "package_role": "READ_ONLY_FINAL_WORKING_HANDOFF_AND_DOWNSTREAM_BUILDER_INPUT",
        "format_baseline": "Unit02 final working package Q1-Q10 role structure; Unit03 actual evidence files are retained where their delivery shape differs.",
        "current_authority": {
            "fp01_task_id": fp01.TASK_ID,
            "fp01_status": current["status"],
            "fp01_package_sha256": current["package_sha256"],
            "authority_rule": "Current approved GitHub authority wins over handoff/export bytes.",
        },
        "q01_q10_map": current["q01_q10_map"],
        "role_file_map": role_map,
        "source_handoff_files_copied": sorted(copied),
        "derived_csv_files_generated_when_missing": sorted(generated),
        "current_git_authority_files_materialized": current_files,
        "stale_replacements": {
            "old_q05_eight_family_handoff_replaced": True,
            "old_q09_q10_files_replaced": True,
            "historical_640_runtime_current": False,
            "current_successor_runtime_occurrences": 800,
        },
        "downstream_readiness": {
            "q1_q10_roles_present": all(role_map[f"Q{i:02d}"] for i in range(1, 11)),
            "q6_large_sentence_asset_payload_present": True,
            "q7_projection_evidence_present": True,
            "q10_successor_inventory_present": True,
            "q10_successor_runtime_plan_present": True,
            "form_production_input_ready": True,
        },
        "claim_boundaries": {
            "canonical_authority_mutated": False,
            "questionbank_or_runtime_authority_created": False,
            "sentence_assets_created": False,
            "canonical_scene_authority_created": False,
            "learner_state_mutated": False,
            "scoring_authority_created": False,
            "q11_opened": False,
            "unit04_opened": False,
            "a2_unlocked": False,
        },
    }
    _write_json(output_dir / MANIFEST_NAME, manifest)
    if zip_output is not None:
        _write_zip(output_dir, zip_output)
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handoff-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--zip-output", type=Path)
    args = parser.parse_args(argv)
    manifest = materialize(args.handoff_dir, args.output_dir, args.zip_output)
    print(f"STATUS={manifest['status']}")
    print(f"Q1_Q10_ROLES_PRESENT={manifest['downstream_readiness']['q1_q10_roles_present']}")
    print(f"FORM_PRODUCTION_INPUT_READY={manifest['downstream_readiness']['form_production_input_ready']}")
    print(f"CURRENT_Q10_RUNTIME={manifest['stale_replacements']['current_successor_runtime_occurrences']}")
    print(f"OUTPUT_DIR={args.output_dir}")
    if args.zip_output is not None:
        print(f"ZIP_OUTPUT={args.zip_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
