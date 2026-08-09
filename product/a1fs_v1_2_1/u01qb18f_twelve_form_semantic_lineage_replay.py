#!/usr/bin/env python3
"""Replay Unit01 Forms 01..12 through the exact active product semantic path.

This is a private operator/readback tool. It snapshots the already-cut-over
474-item production learner database, creates one disposable fresh learner in
the snapshot, materializes Reading/Writing/Speaking for Forms 01..12 through the
existing U01QB13/U01QB16C/U01QB18C/U01QB18E product path, and validates all 48
micro-scene exposures before exporting learner-safe review data.

No source production row, QuestionBank item, scene, scoring rule or learner
mastery state is modified. Correct answers/private scoring metadata are never
written to the replay artifact.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import sqlite3
import tempfile
from collections import Counter, defaultdict
from contextlib import closing
from pathlib import Path
from typing import Any, Mapping, Sequence

from product import a1fs_v1_2_1 as _product_package  # noqa: F401
from product.a1fs_v1_2_1 import u01qb15_runtime_server_e2e as product_runtime
from product.a1fs_v1_2_1 import u01qb18a_form01_fresh_learner_materialization_export as u18a
from ulga.builders import _u01qb18c_form01_learner_quality_adapter as quality
from ulga.builders import _u01qb18e_micro_scene_semantic_lineage_e2e_adapter as semantic
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Private readback replay over the existing 474-item U01QB15 product and already-"
    "installed U01QB13/U01QB16C/U01QB18C/U01QB18E authorities. It snapshots the "
    "production SQLite, creates only disposable learner/session state in that snapshot, "
    "exports learner-safe review fields plus semantic lineage counts, and creates no "
    "content, second bank, selector, planner, runtime, database, scoring authority, "
    "Unit02-24 content, audio/Speaking score, or A2 content."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18F_Unit01TwelveFormSemanticLineageReplayAndPedagogicalReacceptance"
PASS_STATUS = "PASS_A1FS_V1_U01QB18F_UNIT01_TWELVE_FORM_SEMANTIC_LINEAGE_REPLAY"
FAIL_STATUS = "FAIL_A1FS_V1_U01QB18F_UNIT01_TWELVE_FORM_SEMANTIC_LINEAGE_REPLAY"
NEXT_SHORT_STEP = "A1FS-V1-U01QB18G_Unit01TwelveFormLearnerFacingPedagogicalReviewAndCloseout"

FORM_COUNT = 12
SKILLS = ("READING", "WRITING", "SPEAKING")
EXPECTED_SKILL_COUNTS = {"READING": 8, "WRITING": 8, "SPEAKING": 4}
EXPECTED_SCENES_PER_FORM = 4
EXPECTED_ACTIVITIES_PER_SCENE = 5
EXPECTED_ACTIVITIES_PER_FORM = 20
EXPECTED_TOTAL_SCENE_EXPOSURES = 48
EXPECTED_TOTAL_ACTIVITIES = 240
DEFAULT_LEARNER_ID = "U01_FORMS01_12_FRESH_SEMANTIC_REPLAY"
DEFAULT_OUTPUT = Path(".local/a1fs_v1/review/unit01_forms01_12_semantic_replay.json")


class TwelveFormReplayError(ValueError):
    """Fail-closed twelve-form replay or acceptance error."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _expected_scaffold_stage(form_ordinal: int) -> str:
    if form_ordinal == 1:
        return quality.FORM01_SCAFFOLD_STAGE
    if form_ordinal == 2:
        return quality.FORM02_SCAFFOLD_STAGE
    if form_ordinal == 3:
        return quality.FORM03_SCAFFOLD_STAGE
    return quality.FORM04_PLUS_SCAFFOLD_STAGE


def _materialize_skill(
    database: Path,
    *,
    learner_id: str,
    skill: str,
    form_ordinal: int,
) -> dict[str, Any]:
    impl = product_runtime.impl
    u13 = impl.u13
    qb02 = impl.qb02
    store = u18a._ClosingLearnerStateStore(database)
    session_id = f"U01QB18F:F{form_ordinal:02d}:{skill}:FRESH"
    session = store.start_session(
        learner_id=learner_id,
        lesson_id=qb02.UNIT01_LESSONS[skill],
        session_id=session_id,
    )

    impl.matching.install()
    component = u13.assemble_form_component(
        database,
        learner_id=learner_id,
        session_id=str(session["session_id"]),
        form_ordinal=form_ordinal,
    )
    payload = impl.learner_form_payload(database, component)
    expected = EXPECTED_SKILL_COUNTS[skill]
    if int(payload.get("form_ordinal", 0)) != form_ordinal:
        raise TwelveFormReplayError(f"FORM_ORDINAL_DRIFT:{form_ordinal}:{skill}")
    if str(payload.get("skill") or "") != skill:
        raise TwelveFormReplayError(f"SKILL_IDENTITY_DRIFT:{form_ordinal}:{skill}")
    if int(payload.get("blueprint_activity_count", -1)) != expected:
        raise TwelveFormReplayError(
            f"ACTIVITY_COUNT_INVALID:{form_ordinal}:{skill}:{payload.get('blueprint_activity_count')}:{expected}"
        )
    if len(payload.get("items") or []) != expected:
        raise TwelveFormReplayError(
            f"ITEM_COUNT_INVALID:{form_ordinal}:{skill}:{len(payload.get('items') or [])}:{expected}"
        )
    if payload.get("support_fillers_exposed_to_learner") is not False:
        raise TwelveFormReplayError(f"SUPPORT_FILLER_EXPOSURE_DRIFT:{form_ordinal}:{skill}")

    u18a._abandon_disposable_session(
        store,
        session_id=str(session["session_id"]),
        session_version=int(payload["session_version"]),
    )
    return payload


def _blueprint_order(database: Path, form_ordinal: int) -> list[dict[str, Any]]:
    with closing(sqlite3.connect(database)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT activity_id,form_id,form_ordinal,scene_ref_id,situation_family,
                      setting,skill,task_angle,support_level
               FROM u01qb13_blueprint_activities
               WHERE form_ordinal=? ORDER BY activity_id""",
            (int(form_ordinal),),
        ).fetchall()
    values = [dict(row) for row in rows]
    if len(values) != EXPECTED_ACTIVITIES_PER_FORM:
        raise TwelveFormReplayError(
            f"BLUEPRINT_ACTIVITY_COUNT_INVALID:{form_ordinal}:{len(values)}:{EXPECTED_ACTIVITIES_PER_FORM}"
        )
    return values


def _selected_by_activity(
    skill_payloads: Mapping[str, Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for skill in SKILLS:
        for item in skill_payloads[skill].get("items") or []:
            activity_id = str(item.get("activity_id") or "")
            if not activity_id or activity_id in result:
                raise TwelveFormReplayError(f"ACTIVITY_BINDING_DUPLICATE_OR_MISSING:{activity_id}")
            result[activity_id] = item
    return result


def _student_form(
    *,
    learner_id: str,
    form_ordinal: int,
    skill_payloads: Mapping[str, Mapping[str, Any]],
    blueprint_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    selected = _selected_by_activity(skill_payloads)
    if len(selected) != EXPECTED_ACTIVITIES_PER_FORM:
        raise TwelveFormReplayError(
            f"FORM_SELECTED_ACTIVITY_COUNT_INVALID:{form_ordinal}:{len(selected)}"
        )
    activities: list[dict[str, Any]] = []
    scenes: list[dict[str, Any]] = []
    seen_scenes: set[str] = set()
    skill_counts: Counter[str] = Counter()
    scene_counts: Counter[str] = Counter()
    for number, blueprint in enumerate(blueprint_rows, start=1):
        activity_id = str(blueprint["activity_id"])
        item = selected.get(activity_id)
        if item is None:
            raise TwelveFormReplayError(
                f"BLUEPRINT_ACTIVITY_NOT_SELECTED:{form_ordinal}:{activity_id}"
            )
        activity = u18a._student_activity(
            number=number,
            blueprint=blueprint,
            selected=item,
        )
        activities.append(activity)
        skill_counts[str(activity["skill"])] += 1
        ref = str(activity["scene_ref_id"])
        scene_counts[ref] += 1
        if ref not in seen_scenes:
            seen_scenes.add(ref)
            scenes.append(
                {
                    "scene_number": len(scenes) + 1,
                    "scene_ref_id": ref,
                    "situation_family": str(blueprint.get("situation_family") or ""),
                    "setting": str(blueprint.get("setting") or ""),
                }
            )
    if dict(skill_counts) != EXPECTED_SKILL_COUNTS:
        raise TwelveFormReplayError(
            f"FORM_SKILL_COUNTS_INVALID:{form_ordinal}:{dict(skill_counts)}"
        )
    if len(scenes) != EXPECTED_SCENES_PER_FORM:
        raise TwelveFormReplayError(f"FORM_SCENE_COUNT_INVALID:{form_ordinal}:{len(scenes)}")
    if any(count != EXPECTED_ACTIVITIES_PER_SCENE for count in scene_counts.values()):
        raise TwelveFormReplayError(
            f"FORM_SCENE_ACTIVITY_COUNT_INVALID:{form_ordinal}:{dict(scene_counts)}"
        )
    value = {
        "unit_id": "UNIT01",
        "form_id": f"U01-FORM-{form_ordinal:02d}",
        "form_ordinal": form_ordinal,
        "learner_mode": "FRESH_SEQUENTIAL_REPLAY",
        "learner_id": learner_id,
        "scene_count": len(scenes),
        "learner_visible_activity_count": len(activities),
        "skill_counts": dict(skill_counts),
        "scenes": scenes,
        "activities": activities,
    }
    u18a._assert_no_answer_leak(value)
    return value


def _scene_exposure_summary(
    *,
    form_ordinal: int,
    skill_payloads: Mapping[str, Mapping[str, Any]],
    semantic_report: Mapping[str, Any],
) -> list[dict[str, Any]]:
    selected_by_scene: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for skill in SKILLS:
        for item in skill_payloads[skill].get("items") or []:
            selected_by_scene[str(item.get("scene_ref_id") or "")].append(item)
    semantic_by_scene = {
        str(row.get("scene_ref_id") or ""): row
        for row in semantic_report.get("scene_reports") or []
    }
    rows: list[dict[str, Any]] = []
    for ref in sorted(selected_by_scene):
        items = selected_by_scene[ref]
        semantic_row = semantic_by_scene.get(ref, {})
        rows.append(
            {
                "form_ordinal": form_ordinal,
                "scene_ref_id": ref,
                "selected_item_ids": sorted(str(item.get("item_id") or "") for item in items),
                "task_angles": sorted(str(item.get("task_angle") or "") for item in items),
                "support_levels": sorted({str(item.get("support_level") or "") for item in items}),
                "richer_language_asset_activity_count": int(
                    semantic_row.get("richer_language_asset_activity_count", 0)
                ),
                "semantic_compatible_activity_count": int(
                    semantic_row.get("exact_or_semantic_compatible_activity_count", 0)
                ),
                "semantic_signal_hit_count": int(
                    semantic_row.get("semantic_signal_hit_count", 0)
                ),
                "learner_visible_stimulus_duplicate_count": int(
                    semantic_row.get("learner_visible_stimulus_duplicate_count", 0)
                ),
                "target_noun_counts": dict(semantic_row.get("target_noun_counts") or {}),
                "vocabulary_ref_count": int(semantic_row.get("vocabulary_ref_count", 0)),
                "chunk_ref_count": int(semantic_row.get("chunk_ref_count", 0)),
                "sentence_ref_count": int(semantic_row.get("sentence_ref_count", 0)),
                "content_asset_count": int(semantic_row.get("content_asset_count", 0)),
            }
        )
    return rows


def _scaffold_errors(
    *,
    form_ordinal: int,
    speaking_payload: Mapping[str, Any],
) -> list[str]:
    expected = _expected_scaffold_stage(form_ordinal)
    stages = [
        str(item.get("speaking_scaffold_stage") or "")
        for item in speaking_payload.get("items") or []
    ]
    if len(stages) != EXPECTED_SKILL_COUNTS["SPEAKING"]:
        return [f"SPEAKING_SCAFFOLD_COUNT_INVALID:F{form_ordinal:02d}:{len(stages)}"]
    if any(stage != expected for stage in stages):
        return [f"SPEAKING_SCAFFOLD_STAGE_INVALID:F{form_ordinal:02d}:{stages}:{expected}"]
    return []


def _form_record(
    *,
    learner_id: str,
    form_ordinal: int,
    skill_payloads: Mapping[str, Mapping[str, Any]],
    blueprint_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    semantic_report = semantic.validate_form_components(skill_payloads)
    errors = list(semantic_report.get("errors") or [])
    errors.extend(
        _scaffold_errors(
            form_ordinal=form_ordinal,
            speaking_payload=skill_payloads["SPEAKING"],
        )
    )
    exposures = _scene_exposure_summary(
        form_ordinal=form_ordinal,
        skill_payloads=skill_payloads,
        semantic_report=semantic_report,
    )
    # A micro-scene exposure is not accepted as semantically consumed if all five
    # activities are only anchor-level items. This applies to all 12 Forms, not
    # only early scaffolded Forms.
    for row in exposures:
        ref = str(row["scene_ref_id"])
        if int(row["richer_language_asset_activity_count"]) < 1:
            errors.append(
                f"SCENE_LANGUAGE_ASSET_CONSUMPTION_MISSING:F{form_ordinal:02d}:{ref}"
            )
        if (
            int(row["semantic_compatible_activity_count"]) < 1
            and int(row["semantic_signal_hit_count"]) < 1
        ):
            errors.append(f"SCENE_SEMANTIC_SIGNAL_MISSING:F{form_ordinal:02d}:{ref}")
        if int(row["learner_visible_stimulus_duplicate_count"]) != 0:
            errors.append(f"SCENE_VISIBLE_DUPLICATE:F{form_ordinal:02d}:{ref}")
    return {
        "form_ordinal": form_ordinal,
        "form_id": f"U01-FORM-{form_ordinal:02d}",
        "validation_status": PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        "semantic_e2e": semantic_report,
        "scene_exposures": exposures,
        "student_form": _student_form(
            learner_id=learner_id,
            form_ordinal=form_ordinal,
            skill_payloads=skill_payloads,
            blueprint_rows=blueprint_rows,
        ),
    }


def _repeat_scene_report(form_records: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    by_scene: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for form in form_records:
        for exposure in form.get("scene_exposures") or []:
            by_scene[str(exposure.get("scene_ref_id") or "")].append(exposure)
    reports: list[dict[str, Any]] = []
    errors: list[str] = []
    for ref, exposures in sorted(by_scene.items()):
        if len(exposures) == 1:
            continue
        if len(exposures) != 2:
            errors.append(f"SCENE_EXPOSURE_COUNT_ABOVE_TWO:{ref}:{len(exposures)}")
            continue
        first, second = sorted(exposures, key=lambda row: int(row["form_ordinal"]))
        first_ids = set(first["selected_item_ids"])
        second_ids = set(second["selected_item_ids"])
        overlap = sorted(first_ids & second_ids)
        task_angle_changed = first["task_angles"] != second["task_angles"]
        support_changed = first["support_levels"] != second["support_levels"]
        if overlap:
            errors.append(f"REUSED_SCENE_ITEM_REPLAY:{ref}:{','.join(overlap)}")
        if not task_angle_changed:
            errors.append(f"REUSED_SCENE_TASK_ANGLE_NOT_CHANGED:{ref}")
        if not support_changed:
            errors.append(f"REUSED_SCENE_SUPPORT_NOT_CHANGED:{ref}")
        reports.append(
            {
                "scene_ref_id": ref,
                "first_form_ordinal": int(first["form_ordinal"]),
                "second_form_ordinal": int(second["form_ordinal"]),
                "selected_item_overlap_count": len(overlap),
                "task_angle_changed": task_angle_changed,
                "support_level_changed": support_changed,
            }
        )
    return reports, errors


def _aggregate(
    *,
    learner_id: str,
    cutover: Mapping[str, Any],
    source_snapshot_sha256: str,
    form_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    if len(form_records) != FORM_COUNT:
        errors.append(f"FORM_COUNT_INVALID:{len(form_records)}:{FORM_COUNT}")
    failed_forms = [
        int(row["form_ordinal"])
        for row in form_records
        if row.get("validation_status") != PASS_STATUS
    ]
    if failed_forms:
        errors.append("FORM_SEMANTIC_E2E_FAILURES:" + ",".join(map(str, failed_forms)))
    scene_exposure_count = sum(len(row.get("scene_exposures") or []) for row in form_records)
    activity_count = sum(
        int((row.get("student_form") or {}).get("learner_visible_activity_count", 0))
        for row in form_records
    )
    if scene_exposure_count != EXPECTED_TOTAL_SCENE_EXPOSURES:
        errors.append(
            f"TOTAL_SCENE_EXPOSURE_COUNT_INVALID:{scene_exposure_count}:{EXPECTED_TOTAL_SCENE_EXPOSURES}"
        )
    if activity_count != EXPECTED_TOTAL_ACTIVITIES:
        errors.append(f"TOTAL_ACTIVITY_COUNT_INVALID:{activity_count}:{EXPECTED_TOTAL_ACTIVITIES}")
    repeats, repeat_errors = _repeat_scene_report(form_records)
    errors.extend(repeat_errors)
    value = {
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        "learner_id": learner_id,
        "form_count": len(form_records),
        "scene_exposure_count": scene_exposure_count,
        "learner_visible_activity_count": activity_count,
        "semantic_e2e_pass_form_count": len(form_records) - len(failed_forms),
        "semantic_e2e_failed_form_ordinals": failed_forms,
        "reused_scene_count": len(repeats),
        "reused_scene_reports": repeats,
        "forms": list(form_records),
        "runtime_proof": {
            "questionbank_revision": str(cutover.get("questionbank_revision") or ""),
            "runtime_item_count": int(cutover.get("runtime_item_count", 0)),
            "real62_extension_item_count": int(cutover.get("extension_item_count", 0)),
            "real62_artifact_sha256": str(cutover.get("real62_artifact_sha256") or ""),
            "source_database_snapshot_sha256": source_snapshot_sha256,
            "formal_selector": "U01QB13/U01QB16C/U01QB18C/U01QB18E_PRODUCT_PATH",
            "source_production_database_modified": False,
            "questionbank_modified": False,
            "new_question_items_authored": 0,
        },
        "claim_boundaries": {
            "learner_state_is_disposable_snapshot_only": True,
            "scoring_recorded": False,
            "mastery_recorded": False,
            "audio_enabled": False,
            "speaking_scored": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    u18a._assert_no_answer_leak(value)
    return value


def materialize_twelve_form_replay(
    *,
    database: Path,
    output: Path,
    learner_id: str = DEFAULT_LEARNER_ID,
) -> dict[str, Any]:
    database = Path(database).resolve(strict=True)
    output = Path(output).resolve()
    if output == database:
        raise TwelveFormReplayError("OUTPUT_MUST_NOT_OVERWRITE_PRODUCTION_DATABASE")
    source_before = _sha256_file(database)

    with tempfile.TemporaryDirectory(prefix="a1fs_u01qb18f_forms01_12_") as temporary:
        snapshot = Path(temporary) / "forms01_12_semantic_replay.sqlite3"
        u18a._sqlite_snapshot(database, snapshot)
        snapshot_sha256 = _sha256_file(snapshot)
        cutover = product_runtime.impl.require_cutover(snapshot)
        if int(cutover.get("runtime_item_count", 0)) != 474:
            raise TwelveFormReplayError("RUNTIME_474_REQUIRED")
        if int(cutover.get("extension_item_count", 0)) != 186:
            raise TwelveFormReplayError("REAL62_186_REQUIRED")
        u18a._assert_fresh_learner_absent(snapshot, learner_id)

        store = u18a._ClosingLearnerStateStore(snapshot)
        store.create_profile(
            learner_id=learner_id,
            display_label="Unit01 Forms01-12 Semantic Replay Learner",
            locale="zh-TW",
            timezone_name="Asia/Taipei",
        )

        records: list[dict[str, Any]] = []
        for form_ordinal in range(1, FORM_COUNT + 1):
            payloads = {
                skill: _materialize_skill(
                    snapshot,
                    learner_id=learner_id,
                    skill=skill,
                    form_ordinal=form_ordinal,
                )
                for skill in SKILLS
            }
            records.append(
                _form_record(
                    learner_id=learner_id,
                    form_ordinal=form_ordinal,
                    skill_payloads=payloads,
                    blueprint_rows=_blueprint_order(snapshot, form_ordinal),
                )
            )

        value = _aggregate(
            learner_id=learner_id,
            cutover=cutover,
            source_snapshot_sha256=snapshot_sha256,
            form_records=records,
        )
        del store, records, cutover
        gc.collect()

    source_after = _sha256_file(database)
    if source_after != source_before:
        raise TwelveFormReplayError("SOURCE_PRODUCTION_DATABASE_MODIFIED")

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = output.with_suffix(output.suffix + ".tmp")
    temporary_output.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary_output, output)
    try:
        output.chmod(0o600)
    except OSError:
        pass
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--learner-id", default=DEFAULT_LEARNER_ID)
    args = parser.parse_args(argv)
    try:
        value = materialize_twelve_form_replay(
            database=args.database,
            output=args.output,
            learner_id=str(args.learner_id),
        )
    except (
        TwelveFormReplayError,
        u18a.Form01MaterializationError,
        semantic.MicroSceneSemanticLineageError,
        m3.StateStoreError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        sqlite3.Error,
    ) as exc:
        print(f"STATUS={FAIL_STATUS}")
        print(f"ERROR={exc}")
        return 1

    print(f"STATUS={value['validation_status']}")
    print(f"FORMS={value['form_count']}")
    print(f"SCENE_EXPOSURES={value['scene_exposure_count']}")
    print(f"ACTIVITIES={value['learner_visible_activity_count']}")
    print(f"SEMANTIC_E2E_PASS_FORMS={value['semantic_e2e_pass_form_count']}")
    print(f"REUSED_SCENES={value['reused_scene_count']}")
    print(f"RUNTIME_ITEMS={value['runtime_proof']['runtime_item_count']}")
    print(f"REAL62_EXTENSION_ITEMS={value['runtime_proof']['real62_extension_item_count']}")
    print(f"OUTPUT={Path(args.output).resolve()}")
    print(f"NEXT_SHORT_STEP={value['next_short_step']}")
    return 0 if value["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
