#!/usr/bin/env python3
"""Project cumulative Unit01 scene-world assets into the Unit01-bindable runtime subset.

U01QB14R1 preserves every approved cumulative life scene. It does not rewrite or
remove model-authored scene authority. Instead, it applies the Unit01 language
boundary at the rotation edge: a scene may enter the Unit01 12-form rotation only
when at least one scene object/setting token is an active Unit01 noun. Scenes that
are valid life-world assets but not yet bindable remain deferred in the cumulative
scene world for later-unit reprojection.

The FullFix rematerializes an already-validated U01QB08 rotation into a filtered
U01QB08-compatible rotation, rebuilds U01QB09 allocation, and installs a bounded
U01QB13 semantic-index adapter only while U01QB14 executes. No second planner,
runtime, learner database authority, QuestionBank, or scoring engine is created.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from ulga.builders import build_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission as s01
from ulga.builders import build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as u01qb01
from ulga.builders import build_a1fs_v1_u01qb07_unit01_micro_scene_seed_enrichment as u01qb07
from ulga.builders import build_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as u01qb08
from ulga.builders import build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u01qb09
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u01qb13
from ulga.builders import build_a1fs_v1_u01qb14_unit01_twelve_form_private_production_replay_and_learner_form_acceptance as u01qb14
from ulga.validators import validate_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as u01qb08_validator
from ulga.validators import validate_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u01qb09_validator
from ulga.validators import validate_a1fs_v1_u01qb14_unit01_twelve_form_private_production_replay_and_learner_form_acceptance as u01qb14_validator

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Deterministic Unit01 runtime-bindability projection over already-approved cumulative scenes; preserves scene authority and only filters rotation eligibility before delegating to the existing U01QB08/U01QB09/U01QB13/U01QB14 chain."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB14R1_Unit01CumulativeSceneWorldRuntimeBindabilityGateFullFix"
SCHEMA_VERSION = "a1fs.v1.u01qb14r1.unit01_scene_runtime_bindability_gate.v1"
PASS_STATUS = "PASS_A1FS_V1_U01QB14R1_UNIT01_CUMULATIVE_SCENE_WORLD_RUNTIME_BINDABILITY_GATE_FULLFIX"
UNIT_ID = u01qb08.UNIT_ID
GATE_RULE = "UNIT_ACTIVE_NOUN_ANCHOR_REQUIRED"
EXPECTED_CUMULATIVE_SCENE_WORLD_COUNT = 32
EXPECTED_UNIT01_BINDABLE_SCENE_COUNT = 31
EXPECTED_DEFERRED_SCENE_REFS = ("U01-MA-FOOD-04",)
HARD_MIN_BINDABLE_SCENES = 24
TARGET_MIN_BINDABLE_SCENES = 28
TARGET_MAX_BINDABLE_SCENES = 36
MIN_SITUATION_FAMILIES = 5
REQUIRED_ROTATION_SLOTS = 48
DEFAULT_ROTATION_OUTPUT = Path(".local/a1fs_v1/u01qb14r1/u01qb08_unit01_runtime_bindable_rotation.json")
DEFAULT_ALLOCATION_OUTPUT = Path(".local/a1fs_v1/u01qb14r1/u01qb09_unit01_runtime_bindable_allocation.json")
DEFAULT_REPLAY_REPORT = Path(".local/a1fs_v1/u01qb14r1/u01qb14_actual_real62_runtime_bindable_replay.json")
NEXT_SHORT_STEP = "A1FS-V1-U01QB14R1_ActualReal62TwelveFormAcceptanceReadback"


class RuntimeBindabilityGateError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _words(value: str) -> set[str]:
    return set(re.findall(r"[a-z]+", str(value).casefold().replace("_", " ")))


def active_unit01_nouns() -> set[str]:
    return {str(row["lemma"]).casefold() for row in u01qb01.nouns()}


def _read_supplement() -> dict[str, Any]:
    try:
        value = json.loads(Path(u01qb07.DEFAULT_SPEC).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeBindabilityGateError(f"SCENE_SUPPLEMENT_UNREADABLE:{exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeBindabilityGateError("SCENE_SUPPLEMENT_OBJECT_REQUIRED")
    return value


def scene_bindability_index() -> dict[str, dict[str, Any]]:
    """Return Unit01 bindability without mutating cumulative scene authority."""
    active = active_unit01_nouns()
    result: dict[str, dict[str, Any]] = {}

    for context in s01.CONTEXTS:
        ref = str(context["context_id"])
        text = " ".join(str(row) for row in context["sentences"])
        anchors = sorted(_words(text) & active)
        if not anchors:
            raise RuntimeBindabilityGateError(f"CANONICAL_SCENE_ANCHORS_MISSING:{ref}")
        result[ref] = {
            "scene_ref_id": ref,
            "runtime_bindable": True,
            "anchors": anchors,
            "gate_reason": "UNIT_ACTIVE_NOUN_ANCHOR_PRESENT",
            "source": "CANONICAL_CONTEXT",
        }

    supplement = _read_supplement()
    rows = u01qb07.candidates(supplement)
    for candidate in rows:
        ref = str(candidate["candidate_id"])
        object_words = {str(row).casefold() for row in candidate.get("objects", [])}
        setting_words = _words(str(candidate.get("medium_setting") or ""))
        anchors = sorted((object_words | setting_words) & active)
        result[ref] = {
            "scene_ref_id": ref,
            "runtime_bindable": bool(anchors),
            "anchors": anchors,
            "gate_reason": (
                "UNIT_ACTIVE_NOUN_ANCHOR_PRESENT"
                if anchors
                else "UNIT_ACTIVE_NOUN_ANCHOR_MISSING_DEFER_FOR_LATER_UNIT"
            ),
            "source": "MODEL_AUTHORED_APPROVED_SCENE",
        }
    return result


def _unique_scene_rows_from_rotation(rotation: Mapping[str, Any]) -> list[dict[str, Any]]:
    u01qb08_validator.validate(rotation)
    rows: dict[str, dict[str, Any]] = {}
    for form in rotation.get("forms") or []:
        for slot in form.get("scene_slots") or []:
            ref = str(slot.get("scene_ref_id") or "")
            if not ref:
                raise RuntimeBindabilityGateError("ROTATION_SCENE_REF_MISSING")
            row = {
                "scene_ref_id": ref,
                "semantic_scene_signature_v2": str(slot.get("semantic_scene_signature_v2") or ""),
                "situation_family": str(slot.get("situation_family") or ""),
                "setting": str(slot.get("setting") or ""),
                "micro_scene_event_id": str(slot.get("micro_scene_event_id") or ""),
                "scene_origin": str(slot.get("scene_origin") or ""),
            }
            previous = rows.get(ref)
            if previous is not None and previous != row:
                raise RuntimeBindabilityGateError(f"ROTATION_SCENE_IDENTITY_DRIFT:{ref}")
            rows[ref] = row
    usage_refs = {
        str(row.get("scene_ref_id") or "")
        for row in rotation.get("scene_usage_summary") or []
        if isinstance(row, Mapping)
    }
    if set(rows) != usage_refs:
        raise RuntimeBindabilityGateError("ROTATION_SCENE_USAGE_IDENTITY_MISMATCH")
    return sorted(rows.values(), key=lambda row: (row["situation_family"], row["scene_ref_id"]))


def project_existing_rotation(rotation: Mapping[str, Any]) -> dict[str, Any]:
    """Project a validated 32-scene U01QB08 artifact to the Unit01-bindable subset."""
    world_rows = _unique_scene_rows_from_rotation(rotation)
    index = scene_bindability_index()
    unknown = sorted(row["scene_ref_id"] for row in world_rows if row["scene_ref_id"] not in index)
    if unknown:
        raise RuntimeBindabilityGateError("SCENE_BINDABILITY_IDENTITY_MISSING:" + ",".join(unknown))

    runtime_rows: list[dict[str, Any]] = []
    deferred_rows: list[dict[str, Any]] = []
    for source_row in world_rows:
        ref = source_row["scene_ref_id"]
        gate = index[ref]
        row = deepcopy(source_row)
        row["unit_runtime_bindable"] = bool(gate["runtime_bindable"])
        row["unit_runtime_anchors"] = list(gate["anchors"])
        row["runtime_bindability_gate_rule"] = GATE_RULE
        row["runtime_bindability_gate_reason"] = str(gate["gate_reason"])
        if row["unit_runtime_bindable"]:
            if not row["unit_runtime_anchors"]:
                raise RuntimeBindabilityGateError(f"BINDABLE_SCENE_ANCHORS_EMPTY:{ref}")
            runtime_rows.append(row)
        else:
            deferred_rows.append(row)

    families = Counter(row["situation_family"] for row in runtime_rows)
    world_count = len(world_rows)
    runtime_count = len(runtime_rows)
    deferred_refs = sorted(row["scene_ref_id"] for row in deferred_rows)
    capacity_pass = (
        runtime_count >= HARD_MIN_BINDABLE_SCENES
        and TARGET_MIN_BINDABLE_SCENES <= runtime_count <= TARGET_MAX_BINDABLE_SCENES
        and len(families) >= MIN_SITUATION_FAMILIES
        and runtime_count * u01qb08.MAX_EXPOSURES >= REQUIRED_ROTATION_SLOTS
    )
    if not capacity_pass:
        raise RuntimeBindabilityGateError(
            f"UNIT01_RUNTIME_BINDABLE_CAPACITY_FAIL:{runtime_count}:{len(families)}"
        )

    if world_count != EXPECTED_CUMULATIVE_SCENE_WORLD_COUNT:
        raise RuntimeBindabilityGateError(f"CUMULATIVE_SCENE_WORLD_COUNT_DRIFT:{world_count}")
    if runtime_count != EXPECTED_UNIT01_BINDABLE_SCENE_COUNT:
        raise RuntimeBindabilityGateError(f"UNIT01_BINDABLE_SCENE_COUNT_DRIFT:{runtime_count}")
    if tuple(deferred_refs) != EXPECTED_DEFERRED_SCENE_REFS:
        raise RuntimeBindabilityGateError(
            "UNIT01_DEFERRED_SCENE_SET_DRIFT:" + ",".join(deferred_refs)
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "gate_rule": GATE_RULE,
        "active_unit01_noun_count": len(active_unit01_nouns()),
        "cumulative_scene_world_count": world_count,
        "unit_runtime_bindable_scene_count": runtime_count,
        "unit_runtime_deferred_scene_count": len(deferred_rows),
        "deferred_scene_refs": deferred_refs,
        "deferred_scenes_remain_in_cumulative_scene_world": True,
        "unit_runtime_situation_family_count": len(families),
        "unit_runtime_family_counts": dict(sorted(families.items())),
        "unit_runtime_maximum_slots_at_two_uses_each": runtime_count * u01qb08.MAX_EXPOSURES,
        "required_rotation_slots": REQUIRED_ROTATION_SLOTS,
        "rotation_capacity_pass": capacity_pass,
        "runtime_rows": runtime_rows,
        "deferred_rows": deferred_rows,
        "boundaries": {
            "cumulative_scene_authority_mutated": False,
            "deferred_scene_deleted": False,
            "new_scene_authored": False,
            "question_bank_modified": False,
            "runtime_item_total_modified": False,
            "second_planner_created": False,
            "second_runtime_created": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        },
    }


def rematerialize_rotation(rotation: Mapping[str, Any]) -> dict[str, Any]:
    projection = project_existing_rotation(rotation)
    runtime_rows = [deepcopy(row) for row in projection["runtime_rows"]]
    original = u01qb08.approved_scene_rows
    source = rotation.get("source_identity") or {}
    fake_approved = {
        "artifact_sha256": str(source.get("approved_scene_artifact_sha256") or ""),
        "artifact_role": str(source.get("approved_scene_artifact_role") or ""),
        "payload": {"task_id": str(source.get("approved_scene_task_id") or "")},
    }
    try:
        u01qb08.approved_scene_rows = lambda _approved: deepcopy(runtime_rows)
        rebuilt = u01qb08.build_rotation(fake_approved)
    finally:
        u01qb08.approved_scene_rows = original

    public_projection = {key: deepcopy(value) for key, value in projection.items() if key not in {"runtime_rows", "deferred_rows"}}
    rebuilt["runtime_bindability_projection"] = public_projection
    rebuilt["boundaries"]["new_scene_authored"] = False
    rebuilt["rotation_sha256"] = u01qb08.scene_policy.digest(
        {key: deepcopy(value) for key, value in rebuilt.items() if key != "rotation_sha256"}
    )
    u01qb08_validator.validate(rebuilt)
    validate_rotation_runtime_bindability(rebuilt)
    return rebuilt


def rematerialize_allocation(rotation: Mapping[str, Any]) -> dict[str, Any]:
    validate_rotation_runtime_bindability(rotation)
    allocation = u01qb09.build_allocation(rotation)
    u01qb09_validator.validate(allocation)
    return allocation


def tolerant_scene_semantic_index() -> dict[str, dict[str, Any]]:
    """Mirror U01QB13 semantics while retaining deferred cumulative scenes."""
    active = active_unit01_nouns()
    bindability = scene_bindability_index()
    result: dict[str, dict[str, Any]] = {}
    for context in s01.CONTEXTS:
        ref = str(context["context_id"])
        gate = bindability[ref]
        result[ref] = {
            "scene_ref_id": ref,
            "objects": list(gate["anchors"]),
            "anchors": list(gate["anchors"]),
            "setting": str(context["setting"]),
            "source": "CANONICAL_CONTEXT",
            "event": str(context["title"]),
            "unit_runtime_bindable": True,
        }

    supplement = _read_supplement()
    for candidate in u01qb07.candidates(supplement):
        ref = str(candidate["candidate_id"])
        gate = bindability[ref]
        object_words = {str(row).casefold() for row in candidate.get("objects", [])}
        result[ref] = {
            "scene_ref_id": ref,
            "objects": sorted(object_words),
            "anchors": list(gate["anchors"]),
            "setting": str(candidate.get("medium_setting") or ""),
            "source": "MODEL_AUTHORED_APPROVED_SCENE",
            "event": str(candidate.get("small_micro_scene_event") or ""),
            "action": list(candidate.get("actions") or []),
            "relations": list(candidate.get("relations") or []),
            "communicative_goal": str(candidate.get("communicative_goal") or ""),
            "unit_runtime_bindable": bool(gate["runtime_bindable"]),
        }
    return result


def validate_rotation_runtime_bindability(rotation: Mapping[str, Any]) -> dict[str, Any]:
    u01qb08_validator.validate(rotation)
    projection = rotation.get("runtime_bindability_projection")
    if not isinstance(projection, Mapping):
        raise RuntimeBindabilityGateError("RUNTIME_BINDABILITY_PROJECTION_MISSING")
    if (
        projection.get("task_id") != TASK_ID
        or projection.get("status") != PASS_STATUS
        or projection.get("gate_rule") != GATE_RULE
        or projection.get("deferred_scenes_remain_in_cumulative_scene_world") is not True
        or projection.get("rotation_capacity_pass") is not True
    ):
        raise RuntimeBindabilityGateError("RUNTIME_BINDABILITY_PROJECTION_IDENTITY_INVALID")

    bindability = scene_bindability_index()
    used_refs: set[str] = set()
    for form in rotation.get("forms") or []:
        for slot in form.get("scene_slots") or []:
            ref = str(slot.get("scene_ref_id") or "")
            gate = bindability.get(ref)
            if not gate or gate.get("runtime_bindable") is not True:
                raise RuntimeBindabilityGateError(f"ROTATION_SCENE_NOT_UNIT_RUNTIME_BINDABLE:{ref}")
            expected_anchors = list(gate.get("anchors") or [])
            actual_anchors = list(slot.get("unit_runtime_anchors") or [])
            if not expected_anchors or actual_anchors != expected_anchors:
                raise RuntimeBindabilityGateError(f"ROTATION_SCENE_ANCHOR_DRIFT:{ref}")
            used_refs.add(ref)

    deferred_refs = sorted(str(row) for row in projection.get("deferred_scene_refs") or [])
    if tuple(deferred_refs) != EXPECTED_DEFERRED_SCENE_REFS:
        raise RuntimeBindabilityGateError("DEFERRED_SCENE_PROJECTION_DRIFT")
    if used_refs & set(deferred_refs):
        raise RuntimeBindabilityGateError("DEFERRED_SCENE_LEAKED_INTO_ROTATION")
    if len(used_refs) != EXPECTED_UNIT01_BINDABLE_SCENE_COUNT:
        raise RuntimeBindabilityGateError(f"ROTATION_DISTINCT_BINDABLE_SCENE_COUNT_INVALID:{len(used_refs)}")
    return {
        "status": PASS_STATUS,
        "cumulative_scene_world_count": int(projection["cumulative_scene_world_count"]),
        "unit_runtime_bindable_scene_count": len(used_refs),
        "deferred_scene_refs": deferred_refs,
        "scene_slot_count": sum(len(form.get("scene_slots") or []) for form in rotation.get("forms") or []),
    }


@contextmanager
def u01qb13_deferred_scene_adapter() -> Iterator[None]:
    original = u01qb13._scene_semantic_index
    u01qb13._scene_semantic_index = tolerant_scene_semantic_index
    try:
        yield
    finally:
        u01qb13._scene_semantic_index = original


def run_private_replay(
    *,
    rotation_path: Path,
    allocation_path: Path,
    source_database: Path,
    disposable_database: Path,
    replace_disposable: bool = False,
    learner_id: str = "u01qb14r1-disposable-learner",
) -> dict[str, Any]:
    rotation = u01qb14.read_json(rotation_path)
    allocation = u01qb14.read_json(allocation_path)
    validate_rotation_runtime_bindability(rotation)
    u01qb09_validator.validate(allocation)
    if allocation.get("source_identity", {}).get("rotation_sha256") != rotation.get("rotation_sha256"):
        raise RuntimeBindabilityGateError("ALLOCATION_NOT_BOUND_TO_RUNTIME_BINDABLE_ROTATION")
    with u01qb13_deferred_scene_adapter():
        report = u01qb14.run_private_replay(
            rotation_path=rotation_path,
            allocation_path=allocation_path,
            canonical_database=source_database,
            disposable_database=disposable_database,
            replace_disposable=replace_disposable,
            learner_id=learner_id,
        )
    u01qb14_validator.validate_report(report)
    return report


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _materialize(existing_rotation: Path, rotation_output: Path, allocation_output: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    old_rotation = u01qb08.read_json(existing_rotation)
    rotation = rematerialize_rotation(old_rotation)
    allocation = rematerialize_allocation(rotation)
    write_json(rotation_output, rotation)
    write_json(allocation_output, allocation)
    return rotation, allocation


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    materialize = commands.add_parser("materialize")
    materialize.add_argument("--existing-rotation", type=Path, required=True)
    materialize.add_argument("--rotation-output", type=Path, default=DEFAULT_ROTATION_OUTPUT)
    materialize.add_argument("--allocation-output", type=Path, default=DEFAULT_ALLOCATION_OUTPUT)

    replay = commands.add_parser("replay")
    replay.add_argument("--rotation", type=Path, required=True)
    replay.add_argument("--allocation", type=Path, required=True)
    replay.add_argument("--source-database", type=Path, required=True)
    replay.add_argument("--disposable-database", type=Path, required=True)
    replay.add_argument("--report", type=Path, default=DEFAULT_REPLAY_REPORT)
    replay.add_argument("--replace-disposable", action="store_true")
    replay.add_argument("--learner-id", default="u01qb14r1-disposable-learner")

    full = commands.add_parser("full")
    full.add_argument("--existing-rotation", type=Path, required=True)
    full.add_argument("--rotation-output", type=Path, default=DEFAULT_ROTATION_OUTPUT)
    full.add_argument("--allocation-output", type=Path, default=DEFAULT_ALLOCATION_OUTPUT)
    full.add_argument("--source-database", type=Path, required=True)
    full.add_argument("--disposable-database", type=Path, required=True)
    full.add_argument("--report", type=Path, default=DEFAULT_REPLAY_REPORT)
    full.add_argument("--replace-disposable", action="store_true")
    full.add_argument("--learner-id", default="u01qb14r1-disposable-learner")

    args = parser.parse_args(argv)
    try:
        if args.command == "materialize":
            rotation, allocation = _materialize(
                args.existing_rotation.resolve(strict=True),
                args.rotation_output.resolve(),
                args.allocation_output.resolve(),
            )
            gate = validate_rotation_runtime_bindability(rotation)
            print(f"STATUS={PASS_STATUS}")
            print(f"CUMULATIVE_SCENE_WORLD={gate['cumulative_scene_world_count']}")
            print(f"UNIT01_RUNTIME_BINDABLE_SCENES={gate['unit_runtime_bindable_scene_count']}")
            print("DEFERRED_SCENE_REFS=" + ",".join(gate["deferred_scene_refs"]))
            print(f"ROTATION_SCENE_SLOTS={gate['scene_slot_count']}")
            print(f"ACTIVITY_SLOTS={allocation['allocation_metrics']['activity_slot_count']}")
            return 0

        if args.command == "full":
            _materialize(
                args.existing_rotation.resolve(strict=True),
                args.rotation_output.resolve(),
                args.allocation_output.resolve(),
            )
            rotation_path = args.rotation_output.resolve(strict=True)
            allocation_path = args.allocation_output.resolve(strict=True)
        else:
            rotation_path = args.rotation.resolve(strict=True)
            allocation_path = args.allocation.resolve(strict=True)

        report = run_private_replay(
            rotation_path=rotation_path,
            allocation_path=allocation_path,
            source_database=args.source_database.resolve(strict=True),
            disposable_database=args.disposable_database.resolve(strict=False),
            replace_disposable=args.replace_disposable,
            learner_id=args.learner_id,
        )
        write_json(args.report.resolve(), report)
    except (
        RuntimeBindabilityGateError,
        u01qb08.SceneRotationError,
        u01qb13.BlueprintIntegrationError,
        u01qb14.PrivateProductionReplayError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB14R1_UNIT01_RUNTIME_BINDABILITY_GATE")
        print(f"ERROR={exc}")
        return 1

    acceptance = report["execution_acceptance"]
    print(f"STATUS={PASS_STATUS}")
    print("CUMULATIVE_SCENE_WORLD=32")
    print("UNIT01_RUNTIME_BINDABLE_SCENES=31")
    print("DEFERRED_SCENE_REFS=U01-MA-FOOD-04")
    print(f"FORMS={acceptance['form_count']}")
    print(f"BLUEPRINT_EXPOSURES={acceptance['blueprint_exposure_count']}")
    print(f"SCORED_ATTEMPTS={acceptance['response_attempt_count']}")
    print(f"SUPPORT_FILLER_EXPOSURES={acceptance['support_filler_exposure_count']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
