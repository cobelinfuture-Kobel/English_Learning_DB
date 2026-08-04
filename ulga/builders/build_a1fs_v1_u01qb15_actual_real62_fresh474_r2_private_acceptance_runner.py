#!/usr/bin/env python3
"""Single-command private-local Actual Real62 acceptance for U01QB15/U01QB14R2."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import _u01qb14r2_runtime_capacity_spiral_reuse_selector as r2
from ulga.builders import _u01qb15_fast_context_assignment_optimizer as optimizer
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_razq01e_unit01_approved_content_existing_qb_learner_stimulus_runtime as razq01e
from ulga.builders import build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02
from ulga.builders import build_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as task_patch
from ulga.builders import build_a1fs_v1_u01qb14r1_unit01_cumulative_scene_world_runtime_bindability_gate_fullfix as r1
from ulga.builders import build_a1fs_v1_u01qb15_unit01_context_stratified_question_bank_replacement_and_per_scene_runtime_capacity_fullfix as u15
from ulga.validators import validate_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as task_validator

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Private-local orchestration over existing M3, U01QB02, RAZQ01E, U01QB15, U01QB14R2, U01QB09 and U01QB14 authorities only; no new learner content or canonical learner-state mutation."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB15_ActualReal62Fresh474MigrationAndU01QB14R2ReplayRunner"
PASS_STATUS = "PASS_A1FS_V1_U01QB15_ACTUAL_REAL62_FRESH474_R2_PRIVATE_ACCEPTANCE"
EXPECTED_REAL62_SHA256 = "5b8564788cb645d8d3dd784316be5b05f950260da173a2bee7cfcbe1a7d9ab46"
BASE = 288
EXTENSION = 186
RUNTIME = 474
FORMS = 12
SESSIONS = 36
ACTIVITIES = 240
SCORED = 192
REUSE = 17
DEFAULT_OUTPUT_DIR = Path(".local/a1fs_v1/u01qb15/actual_real62_r2_acceptance")
NEXT_SHORT_STEP = "A1FS-V1-U01QB15_ActualReal62Fresh474MigrationAndU01QB14R2ReplayReadback"


class ActualReal62AcceptanceError(ValueError):
    pass


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _paths(root: Path) -> dict[str, Path]:
    return {
        "root": root,
        "baseline": root / "u01qb15_actual_real62_fresh474.sqlite3",
        "replay": root / "u01qb14r2_actual_real62_twelve_form_replay.sqlite3",
        "candidate": root / "u01qb15.candidate.private.json",
        "approved": root / "u01qb15.approved.private.json",
        "migration": root / "u01qb15.migration.readback.json",
        "rotation": root / "u01qb14r2.rotation.json",
        "allocation": root / "u01qb14r2.runtime_task_aware_allocation.json",
        "replay_report": root / "u01qb14r2.actual_real62_replay.json",
        "final": root / "u01qb15_u01qb14r2.actual_real62_acceptance.json",
    }


def _prepare_outputs(paths: Mapping[str, Path], *, replace: bool) -> None:
    paths["root"].mkdir(parents=True, exist_ok=True)
    managed = [path for key, path in paths.items() if key != "root"]
    existing = [path for path in managed if path.exists()]
    if existing and not replace:
        raise ActualReal62AcceptanceError("OUTPUT_EXISTS_USE_REPLACE")
    if replace:
        for path in managed:
            if path.exists():
                path.unlink()
            for suffix in ("-wal", "-shm", "-journal"):
                sidecar = Path(str(path) + suffix)
                if sidecar.exists():
                    sidecar.unlink()


def _bootstrap_fresh_474(database: Path, real62_path: Path) -> dict[str, Any]:
    with sqlite3.connect(database) as connection:
        connection.executescript(m3.SCHEMA_SQL)
        connection.executemany(
            "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
            {
                "task_id": m3.TASK_ID,
                "schema_version": m3.SCHEMA_VERSION,
                "validation_status": m3.STATUS,
                "consumer_sha256": "0" * 64,
                "scoring_write_enabled": "false",
                "mastery_write_enabled": "false",
                "a2_session_enabled": "false",
                "learner_release_approved": "false",
                "next_short_step": m3.NEXT_SHORT_STEP,
            }.items(),
        )
        for skill, lesson_id in qb02.UNIT01_LESSONS.items():
            connection.execute(
                "INSERT INTO lesson_catalog(lesson_id,lesson_node_id,skill,level,roles_json,requirement_node_ids_json,payload_access_allowed) VALUES(?,?,?,?,?,?,?)",
                (lesson_id, f"U01QB15-ACTUAL-REAL62-{skill}", skill, "A1", "[]", "[]", 1),
            )

    base = qb02.Unit01ApprovedVariantSessionRuntime(database).initialize()
    approved_content = json.loads(real62_path.read_text(encoding="utf-8"))
    candidate = razq01e.build_candidate(approved_content)
    approved = razq01e.admit_candidate(candidate)
    extension = razq01e.materialize_runtime(database, approved)
    counts = (
        int(base["registered_item_count"]),
        int(extension["extension_item_count"]),
        int(extension["combined_runtime_item_count"]),
    )
    if counts != (BASE, EXTENSION, RUNTIME):
        raise ActualReal62AcceptanceError(f"FRESH_474_DENOMINATOR_INVALID:{counts}")
    return {
        "status": "PASS_FRESH_ACTUAL_REAL62_474_BASELINE",
        "base_item_count": BASE,
        "extension_item_count": EXTENSION,
        "runtime_item_count": RUNTIME,
    }


def _migrate_u01qb15(database: Path, paths: Mapping[str, Path]) -> tuple[dict[str, Any], dict[str, Any]]:
    optimizer.install()
    candidate = u15.build_candidate()
    approved = u15.admit_candidate(candidate)
    write_json(paths["candidate"], candidate)
    write_json(paths["approved"], approved)
    migration = u15.migrate_fresh_legacy_runtime(
        database,
        approved_artifact_sha256=str(approved["artifact_sha256"]),
    )
    if (
        migration.get("base_item_count") != BASE
        or migration.get("extension_item_count") != EXTENSION
        or migration.get("runtime_item_count") != RUNTIME
        or migration.get("real62_extension_modified") is not False
    ):
        raise ActualReal62AcceptanceError("U01QB15_MIGRATION_DENOMINATOR_INVALID")
    capacity = migration.get("per_scene_runtime_capacity") or {}
    if (
        capacity.get("all_36_skill_sessions_distinct_item_capacity_proven") is not True
        or capacity.get("verified_activity_count") != ACTIVITIES
        or capacity.get("runtime_capacity_reuse_selected_scene_count") != REUSE
    ):
        raise ActualReal62AcceptanceError("U01QB15_R2_CAPACITY_PROOF_INVALID")
    write_json(paths["migration"], migration)
    return migration, approved


def _materialize_r2_and_allocation(database: Path, paths: Mapping[str, Path], migration: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    capacity = migration["per_scene_runtime_capacity"]
    excluded = list(capacity.get("runtime_capacity_reuse_excluded_scene_refs") or [])
    rotation = r2.rematerialize_rotation(
        u15._legacy_rotation_from_authorities(),
        reuse_excluded_refs=excluded,
    )
    usage = {row["scene_ref_id"]: row for row in rotation["scene_usage_summary"]}
    for ref in excluded:
        if int((usage.get(ref) or {}).get("exposure_count") or 0) != 1:
            raise ActualReal62AcceptanceError(f"R2_EXCLUDED_SCENE_NOT_SINGLE_EXPOSURE:{ref}")
    if sum(bool(row.get("selected_for_spiral_reuse")) for row in usage.values()) != REUSE:
        raise ActualReal62AcceptanceError("R2_REUSE_SCENE_COUNT_INVALID")

    allocation = task_patch.build_runtime_aware_allocation(rotation, database)
    validation = task_validator.validate(allocation)
    if validation["runtime_item_count"] != RUNTIME or validation["verified_activity_count"] != ACTIVITIES:
        raise ActualReal62AcceptanceError("RUNTIME_TASK_AWARE_ALLOCATION_INVALID")
    write_json(paths["rotation"], rotation)
    write_json(paths["allocation"], allocation)
    return rotation, allocation


def _run_private_replay(source_database: Path, paths: Mapping[str, Path], *, learner_id: str) -> dict[str, Any]:
    before = file_sha256(source_database)
    report = r1.run_private_replay(
        rotation_path=paths["rotation"],
        allocation_path=paths["allocation"],
        source_database=source_database,
        disposable_database=paths["replay"],
        replace_disposable=True,
        learner_id=learner_id,
    )
    if file_sha256(source_database) != before:
        raise ActualReal62AcceptanceError("TEST_SOURCE_DATABASE_CHANGED_DURING_REPLAY")
    execution = report.get("execution_acceptance") or {}
    if (
        execution.get("form_count") != FORMS
        or execution.get("session_count") != SESSIONS
        or execution.get("blueprint_exposure_count") != ACTIVITIES
        or execution.get("response_attempt_count") != SCORED
        or execution.get("support_filler_exposure_count") != 0
        or report.get("canonical_database_safety", {}).get("canonical_database_unchanged") is not True
    ):
        raise ActualReal62AcceptanceError("U01QB14_R2_EXECUTION_ACCEPTANCE_INVALID")
    write_json(paths["replay_report"], report)
    return report


def run_acceptance(*, real62_path: Path, output_dir: Path, replace: bool, learner_id: str, expected_real62_sha256: str | None = EXPECTED_REAL62_SHA256) -> dict[str, Any]:
    real62_path = real62_path.resolve(strict=True)
    actual_sha = file_sha256(real62_path)
    if expected_real62_sha256 and actual_sha != expected_real62_sha256:
        raise ActualReal62AcceptanceError(f"REAL62_SHA256_INVALID:{actual_sha}:{expected_real62_sha256}")
    paths = _paths(output_dir.resolve())
    _prepare_outputs(paths, replace=replace)
    bootstrap = _bootstrap_fresh_474(paths["baseline"], real62_path)
    migration, approved = _migrate_u01qb15(paths["baseline"], paths)
    _rotation, allocation = _materialize_r2_and_allocation(paths["baseline"], paths, migration)
    replay = _run_private_replay(paths["baseline"], paths, learner_id=learner_id)
    capacity = migration["per_scene_runtime_capacity"]
    task_gate = allocation["runtime_task_bindability"]
    execution = replay["execution_acceptance"]
    result = {
        "schema_version": "a1fs.v1.u01qb15.actual_real62_r2_private_acceptance.v1",
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "actual_real62_sha256": actual_sha,
        "fresh_runtime": bootstrap,
        "u01qb15": {
            "approved_artifact_sha256": approved["artifact_sha256"],
            "base_item_count": migration["base_item_count"],
            "extension_item_count": migration["extension_item_count"],
            "runtime_item_count": migration["runtime_item_count"],
            "real62_extension_modified": migration["real62_extension_modified"],
        },
        "u01qb14r2": {
            "reuse_excluded_scene_refs": list(capacity["runtime_capacity_reuse_excluded_scene_refs"]),
            "selected_reuse_scene_count": capacity["runtime_capacity_reuse_selected_scene_count"],
            "runtime_bindable_scene_count": capacity["runtime_bindable_scene_count"],
            "deferred_scene_refs": list(capacity["deferred_scene_refs"]),
        },
        "runtime_task_allocation": {
            "verified_activity_count": task_gate["verified_activity_count"],
            "all_36_skill_sessions_distinct_item_capacity_proven": task_gate["all_36_skill_sessions_distinct_item_capacity_proven"],
        },
        "execution_acceptance": {
            "form_count": execution["form_count"],
            "session_count": execution["session_count"],
            "blueprint_exposure_count": execution["blueprint_exposure_count"],
            "response_attempt_count": execution["response_attempt_count"],
            "outcome_counts": dict(execution["outcome_counts"]),
            "assessment_scored_attempt_count": execution["assessment_scored_attempt_count"],
            "support_filler_exposure_count": execution["support_filler_exposure_count"],
        },
        "source_test_baseline_unchanged_during_replay": replay["canonical_database_safety"]["canonical_database_unchanged"],
        "real_canonical_learner_state_touched": False,
        "outputs": {key: str(value) for key, value in paths.items() if key != "root"},
        "next_short_step": NEXT_SHORT_STEP,
    }
    write_json(paths["final"], result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real62", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--learner-id", default="u01qb15-actual-real62-r2-learner")
    args = parser.parse_args(argv)
    try:
        report = run_acceptance(
            real62_path=args.real62,
            output_dir=args.output_dir,
            replace=args.replace,
            learner_id=args.learner_id,
        )
    except Exception as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB15_ACTUAL_REAL62_FRESH474_R2_PRIVATE_ACCEPTANCE")
        print(f"ERROR={exc}")
        return 1
    execution = report["execution_acceptance"]
    print(f"STATUS={report['status']}")
    print("BASE_ITEMS=288")
    print("REAL62_EXTENSION_ITEMS=186")
    print("RUNTIME_ITEMS=474")
    print("R2_REUSE_EXCLUDED_SCENES=" + ",".join(report["u01qb14r2"]["reuse_excluded_scene_refs"]))
    print(f"R2_SELECTED_REUSE_SCENE_COUNT={report['u01qb14r2']['selected_reuse_scene_count']}")
    print(f"RUNTIME_TASK_COMPATIBLE_ACTIVITIES={report['runtime_task_allocation']['verified_activity_count']}")
    print(f"DISTINCT_ITEM_CAPACITY_PROVEN={report['runtime_task_allocation']['all_36_skill_sessions_distinct_item_capacity_proven']}")
    print(f"FORMS={execution['form_count']}")
    print(f"SESSIONS={execution['session_count']}")
    print(f"BLUEPRINT_EXPOSURES={execution['blueprint_exposure_count']}")
    print(f"SCORED_ATTEMPTS={execution['response_attempt_count']}")
    print(f"AUTO_PASS={execution['outcome_counts'].get('AUTO_PASS', 0)}")
    print(f"PENDING_HUMAN_REVIEW={execution['outcome_counts'].get('PENDING_HUMAN_REVIEW', 0)}")
    print(f"ASSESSMENT_SCORED={execution['assessment_scored_attempt_count']}")
    print(f"SUPPORT_FILLER_EXPOSURES={execution['support_filler_exposure_count']}")
    print(f"SOURCE_TEST_BASELINE_UNCHANGED={report['source_test_baseline_unchanged_during_replay']}")
    print("REAL_CANONICAL_LEARNER_STATE_TOUCHED=False")
    print(f"REPORT={report['outputs']['final']}")
    print(f"NEXT_SHORT_STEP={report['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
