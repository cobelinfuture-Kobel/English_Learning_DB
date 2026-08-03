#!/usr/bin/env python3
"""Run the repaired U01QB14R1 chain against an actual U01QB12 runtime.

This runner keeps the existing cumulative-scene gate and U01QB08 rotation, but
rebuilds U01QB09 with real 474-item task/runtime compatibility before delegating
to the existing U01QB14R1/U01QB14 disposable replay. No second runtime or planner
is introduced.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from ulga.builders import build_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as u01qb08
from ulga.builders import build_a1fs_v1_u01qb14r1_unit01_cumulative_scene_world_runtime_bindability_gate_fullfix as r1
from ulga.builders import build_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as task_patch
from ulga.validators import validate_a1fs_v1_u01qb14r1_unit01_cumulative_scene_world_runtime_bindability_gate_fullfix as r1_validator

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Orchestrates existing U01QB08/U01QB09/U01QB13/U01QB14 authorities with real-runtime task compatibility on disposable state only; creates no second planner, runtime, QuestionBank, scoring authority, or canonical learner state."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB14R1_RuntimeTaskAwarePrivateReplayFullFix"
PASS_STATUS = "PASS_A1FS_V1_U01QB14R1_RUNTIME_TASK_AWARE_PRIVATE_REPLAY_FULLFIX"
NEXT_SHORT_STEP = "A1FS-V1-U01QB14R1_ActualReal62TwelveFormAcceptanceReadback"


def write_json(path: Path, value: dict) -> None:
    r1.write_json(path, value)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--existing-rotation", type=Path, required=True)
    parser.add_argument("--rotation-output", type=Path, required=True)
    parser.add_argument("--allocation-output", type=Path, required=True)
    parser.add_argument("--source-database", type=Path, required=True)
    parser.add_argument("--disposable-database", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--replace-disposable", action="store_true")
    parser.add_argument("--learner-id", default="u01qb14r1-task-aware-disposable-learner")
    args = parser.parse_args(argv)

    try:
        source_db = args.source_database.resolve(strict=True)
        old_rotation = u01qb08.read_json(args.existing_rotation.resolve(strict=True))
        rotation = r1.rematerialize_rotation(old_rotation)
        allocation = task_patch.build_runtime_aware_allocation(rotation, source_db)
        r1_validator.validate(rotation, allocation)
        write_json(args.rotation_output.resolve(), rotation)
        write_json(args.allocation_output.resolve(), allocation)

        report = r1.run_private_replay(
            rotation_path=args.rotation_output.resolve(strict=True),
            allocation_path=args.allocation_output.resolve(strict=True),
            source_database=source_db,
            disposable_database=args.disposable_database.resolve(strict=False),
            replace_disposable=args.replace_disposable,
            learner_id=args.learner_id,
        )
        write_json(args.report.resolve(), report)
    except Exception as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB14R1_RUNTIME_TASK_AWARE_PRIVATE_REPLAY_FULLFIX")
        print(f"ERROR={exc}")
        return 1

    acceptance = report["execution_acceptance"]
    projection = rotation["runtime_bindability_projection"]
    task_gate = allocation["runtime_task_bindability"]
    print(f"STATUS={PASS_STATUS}")
    print(f"CUMULATIVE_SCENE_WORLD={projection['cumulative_scene_world_count']}")
    print(f"UNIT01_RUNTIME_BINDABLE_SCENES={projection['unit_runtime_bindable_scene_count']}")
    print("DEFERRED_SCENE_REFS=" + ",".join(projection["deferred_scene_refs"]))
    print(f"RUNTIME_TASK_COMPATIBLE_ACTIVITIES={task_gate['verified_activity_count']}")
    print(f"DISTINCT_ITEM_CAPACITY_PROVEN={task_gate['all_36_skill_sessions_distinct_item_capacity_proven']}")
    print(f"FORMS={acceptance['form_count']}")
    print(f"SESSIONS={acceptance['session_count']}")
    print(f"BLUEPRINT_EXPOSURES={acceptance['blueprint_exposure_count']}")
    print(f"SCORED_ATTEMPTS={acceptance['response_attempt_count']}")
    print(f"AUTO_PASS={acceptance['outcome_counts'].get('AUTO_PASS', 0)}")
    print(f"PENDING_HUMAN_REVIEW={acceptance['outcome_counts'].get('PENDING_HUMAN_REVIEW', 0)}")
    print(f"SUPPORT_FILLER_EXPOSURES={acceptance['support_filler_exposure_count']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
