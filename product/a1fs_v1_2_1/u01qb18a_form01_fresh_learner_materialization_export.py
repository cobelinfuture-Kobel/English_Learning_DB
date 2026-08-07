#!/usr/bin/env python3
"""Export the exact learner-visible Unit01 Form01 selected by the active 474 runtime.

This is an operator/readback tool, not a content producer and not a second
selector.  It takes a consistent SQLite snapshot of an already-cut-over A1FS
V1.2.1 production learner database, creates one disposable fresh learner inside
that snapshot, and invokes the same U01QB13/U01QB16 matching path consumed by
the product runtime for Form01 Reading, Writing, and Speaking.

The source production database is never modified.  Support fillers are omitted.
Correct answers, scoring contracts, rubrics, private_item_json and other private
answer-side fields are never written to the export.  The resulting JSON is a
private local review artifact and must not be committed to GitHub.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

# Importing the product package installs the already-approved U01QB16/U01QB16B/
# U01QB16C product guards before matching.install() rebinds U01QB13.
from product import a1fs_v1_2_1 as _product_package  # noqa: F401
from product.a1fs_v1_2_1 import u01qb15_runtime_server_e2e as product_runtime
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Private operator exporter over the existing U01QB15/U01QB13/U01QB16 product "
    "selection path. It snapshots an already-cut-over 474-item production DB and "
    "exports only the exact learner-visible Form01 payload; it creates no learner "
    "content, QuestionBank item, scene, planner, selector, scoring authority, "
    "canonical graph write, Unit02-24 content, audio, speaking score, or A2 content."
)

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18A_FreshLearnerForm01ExactRuntimeMaterializationExporter"
PASS_STATUS = "PASS_A1FS_V1_U01QB18A_FRESH_LEARNER_FORM01_EXACT_RUNTIME_MATERIALIZATION"
NEXT_SHORT_STEP = "A1FS-V1-U01QB18B_Unit01Form01LearnerReviewPdfAndQuestionByQuestionReview"
FORM_ORDINAL = 1
SKILLS = ("READING", "WRITING", "SPEAKING")
EXPECTED_SKILL_COUNTS = {"READING": 8, "WRITING": 8, "SPEAKING": 4}
EXPECTED_SCENE_COUNT = 4
EXPECTED_ACTIVITIES_PER_SCENE = 5
EXPECTED_ACTIVITY_COUNT = 20
DEFAULT_LEARNER_ID = "U01_FORM01_FRESH_REVIEW"
DEFAULT_OUTPUT = Path(".local/a1fs_v1/review/unit01_form01_fresh_learner_materialization.json")

FORBIDDEN_EXPORT_KEYS = frozenset(
    {
        "answer",
        "answer_key",
        "correct_answer",
        "correct_answers",
        "expected_answer",
        "expected_response",
        "rubric",
        "scoring_contract",
        "scoring_model",
        "private_item_json",
    }
)


class Form01MaterializationError(ValueError):
    """Fail-closed Form01 export error."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sqlite_snapshot(source: Path, target: Path) -> None:
    source = Path(source).resolve(strict=True)
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    try:
        with sqlite3.connect(source) as source_connection, sqlite3.connect(target) as target_connection:
            source_connection.execute("PRAGMA query_only = ON")
            source_connection.backup(target_connection)
            target_connection.commit()
    except sqlite3.Error as exc:
        raise Form01MaterializationError(f"PRODUCTION_DATABASE_SNAPSHOT_FAILED:{exc}") from exc
    try:
        target.chmod(0o600)
    except OSError:
        pass


def _assert_fresh_learner_absent(database: Path, learner_id: str) -> None:
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT 1 FROM learner_profiles WHERE learner_id=? LIMIT 1",
            (learner_id,),
        ).fetchone()
    if row is not None:
        raise Form01MaterializationError(
            f"FRESH_REVIEW_LEARNER_ALREADY_EXISTS:{learner_id}:USE_A_NEW_LEARNER_ID"
        )


def _abandon_disposable_session(
    store: m3.LearnerStateStore,
    *,
    session_id: str,
    session_version: int,
) -> None:
    store.end_session(
        session_id=session_id,
        outcome="ABANDONED",
        expected_session_version=int(session_version),
    )


def _materialize_skill(
    database: Path,
    *,
    learner_id: str,
    skill: str,
) -> dict[str, Any]:
    impl = product_runtime.impl
    u13 = impl.u13
    qb02 = impl.qb02
    store = m3.LearnerStateStore(database)
    session_id = f"U01QB18A:FORM01:FRESH:{skill}"
    session = store.start_session(
        learner_id=learner_id,
        lesson_id=qb02.UNIT01_LESSONS[skill],
        session_id=session_id,
    )

    # This is the same product execution path as U01QB15ProductApplication:
    # matching.install() -> U01QB13 assemble -> learner_form_payload.
    impl.matching.install()
    component = u13.assemble_form_component(
        database,
        learner_id=learner_id,
        session_id=str(session["session_id"]),
        form_ordinal=FORM_ORDINAL,
    )
    payload = impl.learner_form_payload(database, component)
    expected = EXPECTED_SKILL_COUNTS[skill]
    if int(payload.get("form_ordinal", 0)) != FORM_ORDINAL:
        raise Form01MaterializationError(f"FORM_ORDINAL_DRIFT:{skill}")
    if str(payload.get("skill") or "") != skill:
        raise Form01MaterializationError(f"SKILL_IDENTITY_DRIFT:{skill}")
    if int(payload.get("blueprint_activity_count", -1)) != expected:
        raise Form01MaterializationError(
            f"LEARNER_VISIBLE_ACTIVITY_COUNT_INVALID:{skill}:{payload.get('blueprint_activity_count')}:{expected}"
        )
    if len(payload.get("items") or []) != expected:
        raise Form01MaterializationError(
            f"LEARNER_VISIBLE_ITEM_COUNT_INVALID:{skill}:{len(payload.get('items') or [])}:{expected}"
        )
    if payload.get("support_fillers_exposed_to_learner") is not False:
        raise Form01MaterializationError(f"SUPPORT_FILLER_EXPOSURE_DRIFT:{skill}")

    _abandon_disposable_session(
        store,
        session_id=str(session["session_id"]),
        session_version=int(payload["session_version"]),
    )
    return payload


def _blueprint_order(database: Path) -> list[dict[str, Any]]:
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT activity_id,form_id,form_ordinal,scene_ref_id,situation_family,
                      setting,skill,task_angle,support_level
               FROM u01qb13_blueprint_activities
               WHERE form_ordinal=?
               ORDER BY activity_id""",
            (FORM_ORDINAL,),
        ).fetchall()
    values = [dict(row) for row in rows]
    if len(values) != EXPECTED_ACTIVITY_COUNT:
        raise Form01MaterializationError(
            f"FORM01_BLUEPRINT_ACTIVITY_COUNT_INVALID:{len(values)}:{EXPECTED_ACTIVITY_COUNT}"
        )
    return values


def _student_activity(
    *,
    number: int,
    blueprint: Mapping[str, Any],
    selected: Mapping[str, Any],
) -> dict[str, Any]:
    options = list(selected.get("options") or [])
    response_mode = str(selected.get("response_mode") or "")
    if response_mode not in {"select_one", "ordered_tokens", "short_text", "practice_only"}:
        raise Form01MaterializationError(
            f"RESPONSE_MODE_INVALID:{selected.get('activity_id')}:{response_mode}"
        )
    if str(selected.get("scene_ref_id")) != str(blueprint.get("scene_ref_id")):
        raise Form01MaterializationError(
            f"SCENE_BINDING_DRIFT:{selected.get('activity_id')}"
        )
    if str(selected.get("skill")) != str(blueprint.get("skill")):
        raise Form01MaterializationError(
            f"SKILL_BINDING_DRIFT:{selected.get('activity_id')}"
        )
    return {
        "question_number": f"Q{number:02d}",
        "skill": str(selected["skill"]),
        "scene_ref_id": str(selected["scene_ref_id"]),
        "setting": str(selected.get("setting") or ""),
        "stimulus": str(selected.get("stimulus") or ""),
        "prompt": str(selected.get("prompt") or ""),
        "options": options,
        "response_mode": response_mode,
        "capture_enabled": bool(selected.get("capture_enabled")),
        "practice_only": bool(selected.get("practice_only")),
    }


def _assert_no_answer_leak(value: Any, *, path: str = "root") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).casefold()
            if normalized in FORBIDDEN_EXPORT_KEYS:
                raise Form01MaterializationError(f"ANSWER_OR_PRIVATE_KEY_EXPORTED:{path}.{key}")
            _assert_no_answer_leak(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_no_answer_leak(child, path=f"{path}[{index}]")


def _compose_export(
    *,
    learner_id: str,
    cutover: Mapping[str, Any],
    source_snapshot_sha256: str,
    skill_payloads: Mapping[str, Mapping[str, Any]],
    blueprint_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    selected_by_activity: dict[str, Mapping[str, Any]] = {}
    selected_item_ids_by_skill: dict[str, list[str]] = {}
    form_ids: set[str] = set()

    for skill in SKILLS:
        payload = skill_payloads[skill]
        form_ids.add(str(payload["form_id"]))
        selected_item_ids_by_skill[skill] = []
        for item in payload["items"]:
            activity_id = str(item["activity_id"])
            if activity_id in selected_by_activity:
                raise Form01MaterializationError(f"DUPLICATE_ACTIVITY_BINDING:{activity_id}")
            selected_by_activity[activity_id] = item
            selected_item_ids_by_skill[skill].append(str(item["item_id"]))

    if len(selected_by_activity) != EXPECTED_ACTIVITY_COUNT:
        raise Form01MaterializationError(
            f"SELECTED_ACTIVITY_DENOMINATOR_INVALID:{len(selected_by_activity)}:{EXPECTED_ACTIVITY_COUNT}"
        )
    if len(form_ids) != 1:
        raise Form01MaterializationError(f"MULTIPLE_FORM_IDENTITIES:{sorted(form_ids)}")

    activities: list[dict[str, Any]] = []
    scene_order: list[str] = []
    scene_records: dict[str, dict[str, Any]] = {}
    scene_activity_counts: Counter[str] = Counter()
    skill_counts: Counter[str] = Counter()

    for index, blueprint in enumerate(blueprint_rows, 1):
        activity_id = str(blueprint["activity_id"])
        selected = selected_by_activity.get(activity_id)
        if selected is None:
            raise Form01MaterializationError(f"BLUEPRINT_ACTIVITY_NOT_SELECTED:{activity_id}")
        activity = _student_activity(number=index, blueprint=blueprint, selected=selected)
        activities.append(activity)
        skill_counts[activity["skill"]] += 1
        scene_ref = activity["scene_ref_id"]
        scene_activity_counts[scene_ref] += 1
        if scene_ref not in scene_records:
            scene_order.append(scene_ref)
            scene_records[scene_ref] = {
                "scene_number": len(scene_order),
                "scene_ref_id": scene_ref,
                "situation_family": str(blueprint.get("situation_family") or ""),
                "setting": str(blueprint.get("setting") or ""),
            }

    if dict(skill_counts) != EXPECTED_SKILL_COUNTS:
        raise Form01MaterializationError(
            f"FORM01_SKILL_COUNTS_INVALID:{dict(skill_counts)}:{EXPECTED_SKILL_COUNTS}"
        )
    if len(scene_order) != EXPECTED_SCENE_COUNT:
        raise Form01MaterializationError(
            f"FORM01_SCENE_COUNT_INVALID:{len(scene_order)}:{EXPECTED_SCENE_COUNT}"
        )
    invalid_scene_counts = {
        scene: count
        for scene, count in scene_activity_counts.items()
        if count != EXPECTED_ACTIVITIES_PER_SCENE
    }
    if invalid_scene_counts:
        raise Form01MaterializationError(
            f"FORM01_SCENE_ACTIVITY_COUNTS_INVALID:{invalid_scene_counts}"
        )

    student_form = {
        "unit_id": "UNIT01",
        "form_id": next(iter(form_ids)),
        "form_ordinal": FORM_ORDINAL,
        "learner_mode": "FRESH",
        "learner_id": learner_id,
        "scene_count": len(scene_order),
        "learner_visible_activity_count": len(activities),
        "skill_counts": dict(skill_counts),
        "scenes": [scene_records[ref] for ref in scene_order],
        "activities": activities,
    }
    _assert_no_answer_leak(student_form)

    return {
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "student_form": student_form,
        "runtime_proof": {
            "questionbank_revision": str(cutover.get("questionbank_revision") or ""),
            "runtime_item_count": int(cutover.get("runtime_item_count", 0)),
            "real62_extension_item_count": int(cutover.get("extension_item_count", 0)),
            "real62_artifact_sha256": str(cutover.get("real62_artifact_sha256") or ""),
            "source_database_snapshot_sha256": source_snapshot_sha256,
            "formal_selector": "U01QB13/U01QB16_PRODUCT_MATCHING_PATH",
            "support_fillers_exposed_to_learner": False,
            "selected_item_ids_by_skill": selected_item_ids_by_skill,
            "source_production_database_modified": False,
            "questionbank_modified": False,
            "new_question_items_authored": 0,
        },
        "pdf_contract": {
            "show_engineering_metadata": False,
            "show_answers": False,
            "render_stimulus": True,
            "render_options_or_answer_area": True,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def materialize_fresh_form01(
    *,
    database: Path,
    output: Path,
    learner_id: str = DEFAULT_LEARNER_ID,
) -> dict[str, Any]:
    database = Path(database).resolve(strict=True)
    output = Path(output).resolve()
    if output == database:
        raise Form01MaterializationError("OUTPUT_MUST_NOT_OVERWRITE_PRODUCTION_DATABASE")

    with tempfile.TemporaryDirectory(prefix="a1fs_u01qb18a_form01_") as temporary:
        snapshot = Path(temporary) / "form01_review_snapshot.sqlite3"
        _sqlite_snapshot(database, snapshot)
        source_snapshot_sha256 = _sha256_file(snapshot)

        cutover = product_runtime.impl.require_cutover(snapshot)
        if int(cutover.get("runtime_item_count", 0)) != 474:
            raise Form01MaterializationError("RUNTIME_474_REQUIRED")
        if int(cutover.get("extension_item_count", 0)) != 186:
            raise Form01MaterializationError("REAL62_186_REQUIRED")

        _assert_fresh_learner_absent(snapshot, learner_id)
        store = m3.LearnerStateStore(snapshot)
        store.create_profile(
            learner_id=learner_id,
            display_label="Unit01 Form01 Fresh Review Learner",
            locale="zh-TW",
            timezone_name="Asia/Taipei",
        )

        skill_payloads = {
            skill: _materialize_skill(snapshot, learner_id=learner_id, skill=skill)
            for skill in SKILLS
        }
        blueprint_rows = _blueprint_order(snapshot)
        value = _compose_export(
            learner_id=learner_id,
            cutover=cutover,
            source_snapshot_sha256=source_snapshot_sha256,
            skill_payloads=skill_payloads,
            blueprint_rows=blueprint_rows,
        )

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
        value = materialize_fresh_form01(
            database=args.database,
            output=args.output,
            learner_id=str(args.learner_id),
        )
    except (Form01MaterializationError, m3.StateStoreError, OSError, KeyError, TypeError, ValueError, sqlite3.Error) as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB18A_FRESH_LEARNER_FORM01_EXACT_RUNTIME_MATERIALIZATION")
        print(f"ERROR={exc}")
        return 1

    student = value["student_form"]
    proof = value["runtime_proof"]
    print(f"STATUS={value['validation_status']}")
    print(f"FORM_ID={student['form_id']}")
    print(f"SCENES={student['scene_count']}")
    print(f"ACTIVITIES={student['learner_visible_activity_count']}")
    print(f"READING={student['skill_counts']['READING']}")
    print(f"WRITING={student['skill_counts']['WRITING']}")
    print(f"SPEAKING={student['skill_counts']['SPEAKING']}")
    print(f"RUNTIME_ITEMS={proof['runtime_item_count']}")
    print(f"REAL62_EXTENSION_ITEMS={proof['real62_extension_item_count']}")
    print(f"SOURCE_PRODUCTION_DATABASE_MODIFIED={proof['source_production_database_modified']}")
    print(f"OUTPUT={Path(args.output).resolve()}")
    print(f"NEXT_SHORT_STEP={value['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
