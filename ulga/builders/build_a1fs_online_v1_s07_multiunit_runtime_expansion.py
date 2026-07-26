#!/usr/bin/env python3
"""Expand A1FS Online V1 from one admitted unit to a prerequisite-closed multi-unit no-audio runtime.

S07 preserves the existing 24-unit curriculum, S02 first-unit admission, S05 persistent
learner store, M3 session/progress authority, M5 renderer, M6 scoring authority, and
S06 loopback progress surface. It admits only existing authority-backed units whose
prerequisites are already inside the admitted closure. Runtime migration is performed
on a clone and atomically replaces the production database only after validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import uuid
from copy import deepcopy
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_online_v1_s02_first_nonaudio_unit_admission as s02  # noqa: E402
from ulga.builders import build_a1fs_online_v1_s03_unified_learner_runtime as s03  # noqa: E402
from ulga.builders import build_a1fs_online_v1_s04_private_online_learner_workbench_execution as s04  # noqa: E402
from ulga.builders import build_a1fs_online_v1_s05_private_learner_identity_progress_persistence as s05  # noqa: E402
from ulga.builders import build_a1fs_online_v1_s06_private_e2e_progress_readback as s06  # noqa: E402
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2  # noqa: E402
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3  # noqa: E402
from ulga.builders import build_a1fs_v1_m5_four_skill_renderer_learner_ui as m5  # noqa: E402
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Selects existing authority-backed unit/item identities, migrates the existing M3/M6 "
    "persistent runtime, and renders them through M5; no learner content, answer, mastery, "
    "audio, public delivery, or parallel curriculum/runtime authority is authored."
)

PROGRAM_ID = "A1FS-ONLINE-V1"
TASK_ID = "A1FS-ONLINE-V1-S07_MultiUnitProductionAdmissionAndRuntimeExpansion_NoAudio"
SCHEMA_VERSION = "a1fs.online.v1.s07.multiunit_runtime_expansion.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_S07_MULTIUNIT_RUNTIME_EXPANDED"
NEXT_SHORT_STEP = "A1FS-ONLINE-V1-S08_PrivateMultiUnitLearnerJourneyQA_NoAudio"
PRODUCT_STATUS = "PRIVATE_MULTIUNIT_RUNTIME_EXPANDED_NOT_PUBLIC"
RELEASE_PROFILE = "ONLINE_V1_AUDIO_DEFERRED"
SKILL_ORDER = ("reading", "writing", "speaking")
SKILL_UPPER = {skill: skill.upper() for skill in SKILL_ORDER}
CANARY_LEARNER_ID = "A1FS_ONLINE_V1_S07_MULTIUNIT_CANARY"
CANARY_SESSION_ID = "A1FS_ONLINE_V1_S07_SESSION:READING"
CANARY_ATTEMPT_ID = "A1FS_ONLINE_V1_S07_ATTEMPT:READING:1"
CANARY_SUBJECT_KEY = "A1FS_ONLINE_V1_S07_PRIVATE_SLOT"

FORBIDDEN_SAFE_KEYS = {
    "accepted_texts", "accepted_sequence", "answer", "answer_contract", "answer_key",
    "asset_key", "database_path", "display_label", "learner_id", "learner_payload",
    "private_scoring_contract", "private_subject_digest", "prompt", "prompt_text",
    "response", "rubric", "scoring_contract", "session_id", "subject_key",
}

PRESERVED_TABLES = (
    ("learner_profiles", "learner_id"),
    ("learning_sessions", "session_id"),
    ("lesson_progress", "learner_id,lesson_id"),
    ("state_events", "event_seq"),
    ("response_attempts", "attempt_id"),
    ("scoring_results", "attempt_id"),
    ("human_review_queue", "attempt_id"),
    ("s05_identity_bindings", "learner_id"),
    ("s05_progress_checkpoints", "checkpoint_id"),
)


class MultiUnitExpansionError(ValueError):
    """Fail-closed S07 admission, migration, or serving error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MultiUnitExpansionError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise MultiUnitExpansionError(f"{code}_not_object")
    return value


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    if private:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


def safe_scan(value: Any) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in FORBIDDEN_SAFE_KEYS:
                    raise MultiUnitExpansionError(f"private_content_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(value)


def _verify_receipt(receipt: Mapping[str, Any], *, task_id: str, schema: str, status: str, product: str, digest_fn) -> None:
    if (
        receipt.get("task_id") != task_id
        or receipt.get("schema_version") != schema
        or receipt.get("validation_status") != status
        or receipt.get("product_status") != product
        or receipt.get("stop_reason") != "NONE"
    ):
        raise MultiUnitExpansionError(f"source_receipt_contract_invalid:{task_id}")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest_fn(core):
        raise MultiUnitExpansionError(f"source_receipt_digest_invalid:{task_id}")


def _source_paths(s05_receipt: Mapping[str, Any], s06_receipt: Mapping[str, Any]) -> tuple[Path, Path]:
    _verify_receipt(
        s05_receipt, task_id=s05.TASK_ID, schema=s05.SCHEMA_VERSION,
        status=s05.PASS_STATUS, product=s05.PRODUCT_STATUS, digest_fn=s05.digest,
    )
    _verify_receipt(
        s06_receipt, task_id=s06.TASK_ID, schema=s06.SCHEMA_VERSION,
        status=s06.PASS_STATUS, product=s06.PRODUCT_STATUS, digest_fn=s06.digest,
    )
    s05_outputs = s05_receipt.get("persistent_outputs", {})
    s06_outputs = s06_receipt.get("runtime_outputs", {})
    database = Path(str(s05_outputs.get("database_path") or "")).resolve()
    consumer = Path(str(s05_outputs.get("consumer_path") or "")).resolve()
    if database != Path(str(s06_outputs.get("database_path") or "")).resolve():
        raise MultiUnitExpansionError("s05_s06_database_identity_mismatch")
    if not database.is_file() or not consumer.is_file():
        raise MultiUnitExpansionError("persistent_source_outputs_missing")
    return database, consumer


def _unit_candidate(
    curriculum_unit: Mapping[str, Any],
    candidate_unit: Mapping[str, Any],
    item_index: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    grammar_id = str(curriculum_unit.get("grammar_unit_id") or "")
    learning_id = str(curriculum_unit.get("learning_unit_id") or "")
    identity = (
        learning_id,
        curriculum_unit.get("sequence_index"),
        curriculum_unit.get("internal_stage"),
        curriculum_unit.get("canonical_egp_row_ids"),
    )
    peer = (
        candidate_unit.get("learning_unit_id"),
        candidate_unit.get("sequence_index"),
        candidate_unit.get("internal_stage"),
        candidate_unit.get("canonical_egp_row_ids"),
    )
    if not grammar_id or identity != peer:
        raise MultiUnitExpansionError(f"cp01_cp04_unit_identity_drift:{grammar_id}")
    prerequisites = curriculum_unit.get("prerequisite_unit_ids")
    if not isinstance(prerequisites, list) or len(prerequisites) != len(set(prerequisites)):
        raise MultiUnitExpansionError(f"prerequisite_contract_invalid:{grammar_id}")
    reading = s02._ready_m11b_ids(candidate_unit, "reading", item_index)
    writing = s02._ready_m11b_ids(candidate_unit, "writing", item_index)
    speaking, speaking_assessments = s02._speaking_practice_ids(grammar_id, item_index)
    scenes = sorted({
        str(row.get("scene_candidate_id"))
        for row in candidate_unit.get("scene_candidates", [])
        if isinstance(row, Mapping)
        and row.get("candidate_state") == "AUTHORITY_BACKED_METADATA_READY"
        and str(row.get("scene_candidate_id") or "")
    })
    return {
        "learning_unit_id": learning_id,
        "grammar_unit_id": grammar_id,
        "sequence_index": int(curriculum_unit["sequence_index"]),
        "internal_stage": str(curriculum_unit["internal_stage"]),
        "canonical_egp_row_ids": list(curriculum_unit["canonical_egp_row_ids"]),
        "prerequisite_unit_ids": [str(row) for row in prerequisites],
        "reading_item_ids": reading,
        "writing_item_ids": writing,
        "speaking_practice_item_ids": speaking,
        "speaking_assessment_deferred_item_ids": speaking_assessments,
        "scene_candidate_ids": scenes,
        "content_ready": bool(reading and writing and speaking),
    }


def build_admission(
    *,
    cp01_artifact: Mapping[str, Any],
    cp04_artifact: Mapping[str, Any],
    m03_artifact: Mapping[str, Any],
    s02_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    first_unit = s03._verify_s02(s02_artifact)
    cp01_units = s02._verify_cp01(cp01_artifact)
    cp04_units = s02._verify_cp04(cp04_artifact)
    item_index = s02._verify_m03(m03_artifact)
    if set(cp01_units) != set(cp04_units):
        raise MultiUnitExpansionError("cp01_cp04_unit_set_mismatch")
    candidates = [
        _unit_candidate(cp01_units[grammar_id], cp04_units[grammar_id], item_index)
        for grammar_id in cp01_units
    ]
    candidates.sort(key=lambda row: (row["sequence_index"], row["learning_unit_id"]))
    by_learning = {row["learning_unit_id"]: row for row in candidates}
    first_learning_id = str(first_unit.get("learning_unit_id") or "")
    first_candidate = by_learning.get(first_learning_id)
    if not first_candidate or not first_candidate["content_ready"]:
        raise MultiUnitExpansionError("s02_first_unit_not_multiunit_eligible")
    for skill in SKILL_ORDER:
        expected_ids = list(first_unit["admitted_lanes"][skill]["item_ids"])
        actual_ids = list(first_candidate[f"{skill}_item_ids" if skill != "speaking" else "speaking_practice_item_ids"])
        if expected_ids != actual_ids:
            raise MultiUnitExpansionError(f"s02_first_unit_lane_identity_drift:{skill}")

    admitted: dict[str, dict[str, Any]] = {first_learning_id: first_candidate}
    changed = True
    while changed:
        changed = False
        for row in candidates:
            learning_id = row["learning_unit_id"]
            if learning_id in admitted or not row["content_ready"]:
                continue
            if set(row["prerequisite_unit_ids"]).issubset(admitted):
                admitted[learning_id] = row
                changed = True
    ordered = [row for row in candidates if row["learning_unit_id"] in admitted]
    if len(ordered) < 2:
        raise MultiUnitExpansionError("multiunit_admission_requires_at_least_two_units")

    admitted_units: list[dict[str, Any]] = []
    all_item_ids: list[str] = []
    for rank, row in enumerate(ordered, start=1):
        lanes = {
            "reading": s02._admitted_lane(
                row["reading_item_ids"], "INTERACTIVE_TEXT_ITEM",
                "EXISTING_DETERMINISTIC_OR_REVIEWED_SCORING_CONTRACT",
            ),
            "writing": s02._admitted_lane(
                row["writing_item_ids"], "INTERACTIVE_TEXT_ITEM",
                "EXISTING_DETERMINISTIC_OR_REVIEWED_SCORING_CONTRACT",
            ),
            "speaking": s02._admitted_lane(
                row["speaking_practice_item_ids"], "ORAL_PRACTICE_CARD_NO_CAPTURE",
                "NO_SCORING_NO_MASTERY_EVIDENCE",
            ),
        }
        unit_ids = [item_id for skill in SKILL_ORDER for item_id in lanes[skill]["item_ids"]]
        if len(unit_ids) != len(set(unit_ids)):
            raise MultiUnitExpansionError(f"unit_item_identity_collision:{row['learning_unit_id']}")
        all_item_ids.extend(unit_ids)
        admitted_units.append({
            "learning_unit_id": row["learning_unit_id"],
            "grammar_unit_id": row["grammar_unit_id"],
            "sequence_index": row["sequence_index"],
            "internal_stage": row["internal_stage"],
            "canonical_egp_row_ids": row["canonical_egp_row_ids"],
            "prerequisite_unit_ids": row["prerequisite_unit_ids"],
            "selection_rank": rank,
            "selection_origin": "S02_FIRST_UNIT_PRESERVED" if row["learning_unit_id"] == first_learning_id else "CANONICAL_PREREQUISITE_CLOSURE",
            "admitted_lanes": lanes,
            "scene_candidate_ids": row["scene_candidate_ids"],
            "deferred_lanes": {
                "listening": {
                    "status": "DEFERRED_POST_LAUNCH_AUDIO",
                    "reason": "PLAYABLE_AUDIO_REQUIRED_AND_NOT_IN_PRELAUNCH_SCOPE",
                    "item_ids": [],
                },
                "speaking_assessment": {
                    "status": "DEFERRED_POST_LAUNCH_AUDIO",
                    "reason": "RECORDING_TRANSCRIPT_AND_SCORING_NOT_IN_PRELAUNCH_SCOPE",
                    "item_ids": row["speaking_assessment_deferred_item_ids"],
                },
            },
            "unit_admission_status": "ADMITTED_NONAUDIO_MULTIUNIT_PRODUCTION",
        })
    if len(all_item_ids) != len(set(all_item_ids)):
        raise MultiUnitExpansionError("cross_unit_item_identity_collision")

    content_unavailable = [row for row in candidates if not row["content_ready"]]
    prerequisite_blocked = [
        row for row in candidates
        if row["content_ready"] and row["learning_unit_id"] not in admitted
    ]
    reading_count = sum(unit["admitted_lanes"]["reading"]["item_count"] for unit in admitted_units)
    writing_count = sum(unit["admitted_lanes"]["writing"]["item_count"] for unit in admitted_units)
    speaking_count = sum(unit["admitted_lanes"]["speaking"]["item_count"] for unit in admitted_units)
    core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "artifact_type": "multiunit_nonaudio_admission_and_runtime_expansion",
        "scope": "A1_A1_PLUS_ONLY",
        "release_profile": RELEASE_PROFILE,
        "source_identity": {
            "cp01_sha256": s02.digest(cp01_artifact),
            "cp04_sha256": s02.digest(cp04_artifact),
            "m03_sha256": s02.digest(m03_artifact),
            "s02_sha256": s02.digest(s02_artifact),
        },
        "selection_contract": {
            "course_container": "EXISTING_24_CANONICAL_UNITS_ONLY",
            "selection_mode": "MAXIMAL_CONTENT_READY_CANONICAL_PREREQUISITE_CLOSURE",
            "first_unit_authority": s02.TASK_ID,
            "new_unit_creation_allowed": False,
            "prerequisite_bypass_allowed": False,
            "listening_without_playable_audio_allowed": False,
            "speaking_capture_or_scoring_claim_allowed": False,
        },
        "admitted_units": admitted_units,
        "admission_summary": {
            "canonical_unit_denominator": 24,
            "admitted_unit_count": len(admitted_units),
            "multiunit_admission": True,
            "admitted_unit_count_at_least_two": True,
            "reading_item_count": reading_count,
            "writing_item_count": writing_count,
            "speaking_practice_card_count": speaking_count,
            "admitted_nonaudio_item_count": len(all_item_ids),
            "runtime_lesson_count": len(admitted_units) * len(SKILL_ORDER),
            "content_unavailable_unit_count": len(content_unavailable),
            "prerequisite_blocked_unit_count": len(prerequisite_blocked),
            "listening_item_count": 0,
            "speaking_assessment_item_count": 0,
        },
        "closure_proof": {
            "first_unit_identity_preserved": True,
            "prerequisite_closure_valid": all(
                set(unit["prerequisite_unit_ids"]).issubset(
                    {peer["learning_unit_id"] for peer in admitted_units[:index]}
                )
                for index, unit in enumerate(admitted_units)
            ),
            "canonical_sequence_monotonic": [
                unit["sequence_index"] for unit in admitted_units
            ] == sorted(unit["sequence_index"] for unit in admitted_units),
        },
        "claim_boundaries": {
            "new_curriculum_created": False,
            "new_learner_content_authored": False,
            "listening_complete": False,
            "speaking_recording_complete": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "public_online_delivery_claimed": False,
            "a2_unlocked": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    if core["closure_proof"]["prerequisite_closure_valid"] is not True:
        raise MultiUnitExpansionError("admitted_prerequisite_closure_invalid")
    return {**core, "artifact_sha256": digest(core)}


def build_consumer(admission: Mapping[str, Any], m03_artifact: Mapping[str, Any]) -> dict[str, Any]:
    item_index = s03._verify_m03(m03_artifact)
    assets: list[dict[str, Any]] = []
    catalog: list[dict[str, Any]] = []
    seen_items: set[str] = set()
    with s03._patched():
        for unit in admission["admitted_units"]:
            grammar_id = str(unit["grammar_unit_id"])
            learning_id = str(unit["learning_unit_id"])
            level = "A1+" if str(unit["internal_stage"]).upper() in {"A1+", "A1_PLUS", "A1_PLUS_EXTENSION"} else "A1"
            for lane in SKILL_ORDER:
                lesson_id = f"A1FS_ONLINE_V1:{grammar_id}:{lane.upper()}"
                lane_assets: list[dict[str, Any]] = []
                for item_id in unit["admitted_lanes"][lane]["item_ids"]:
                    if item_id in seen_items:
                        raise MultiUnitExpansionError(f"admitted_item_duplicate:{item_id}")
                    seen_items.add(item_id)
                    item = item_index.get(str(item_id))
                    if item is None:
                        raise MultiUnitExpansionError(f"admitted_item_not_in_m03:{item_id}")
                    if (
                        item.get("grammar_unit_id") != grammar_id
                        or item.get("learning_unit_id") != learning_id
                        or item.get("skill") != lane
                    ):
                        raise MultiUnitExpansionError(f"admitted_item_binding_invalid:{item_id}")
                    projected = s03._runtime_asset(item, lesson_id=lesson_id, lane=lane)
                    projected["release_scope"] = "PRIVATE_INTERNAL_A1FS_ONLINE_V1_S07"
                    lane_assets.append(projected)
                assets.extend(lane_assets)
                catalog.append({
                    "lesson_id": lesson_id,
                    "lesson_node_id": f"RUNTIME_PROJECTION:{lane.upper()}:{grammar_id}",
                    "skill": SKILL_UPPER[lane],
                    "level": level,
                    "asset_keys": [row["asset_key"] for row in lane_assets],
                    "roles": list(dict.fromkeys(row["role"] for row in lane_assets)),
                    "requirement_node_ids": list(unit["canonical_egp_row_ids"]),
                    "release_scope": "PRIVATE_INTERNAL_A1FS_ONLINE_V1_S07",
                    "runtime_projection": {
                        "source_learning_unit_id": learning_id,
                        "source_grammar_unit_id": grammar_id,
                        "sequence_index": unit["sequence_index"],
                        "selection_authority_task_id": TASK_ID,
                        "new_curriculum_unit_created": False,
                    },
                })
    expected_assets = int(admission["admission_summary"]["admitted_nonaudio_item_count"])
    if len(assets) != expected_assets or len(seen_items) != expected_assets:
        raise MultiUnitExpansionError("expanded_runtime_asset_count_mismatch")
    return {
        "task_id": m2.TASK_ID,
        "schema_version": m2.SCHEMA_VERSION,
        "validation_status": m2.STATUS,
        "asset_records": assets,
        "lesson_catalog": catalog,
        "counts": {
            "asset_record_count": len(assets),
            "lesson_count": len(catalog),
            "learning_lesson_count": len(catalog),
            "a2_handoff_lesson_count": 0,
        },
        "access_contract": {
            "visibility": "PRIVATE_INTERNAL",
            "learning_query_levels": ["A1", "A1+"],
            "a2_payload_query_allowed": False,
            "a2_handoff_metadata_allowed": False,
            "max_query_limit": max(100, len(assets)),
            "filter_fields": ["skill", "level", "lesson_id", "role"],
        },
        "s07_runtime_projection": {
            "task_id": TASK_ID,
            "schema_version": SCHEMA_VERSION,
            "admission_sha256": digest(admission),
            "source_m03_sha256": digest(m03_artifact),
            "admitted_unit_count": admission["admission_summary"]["admitted_unit_count"],
            "first_unit_identity_preserved": True,
            "runtime_engine_authorities": {
                "session_state": m3.TASK_ID,
                "learner_renderer": m5.TASK_ID,
                "response_scoring": m6.TASK_ID,
            },
        },
        "claim_boundaries": {
            "new_curriculum_created": False,
            "parallel_runtime_created": False,
            "public_online_delivery_claimed": False,
            "listening_complete": False,
            "speaking_capture_complete": False,
            "mastery_claimed": False,
            "a2_unlocked": False,
        },
        "errors": [],
        "next_short_step": NEXT_SHORT_STEP,
    }


def _plan_for_lesson(lesson: Mapping[str, Any]) -> dict[str, Any]:
    plan = s03._plan_for_lesson(lesson)
    grammar_id = str(lesson["runtime_projection"]["source_grammar_unit_id"])
    plan["plan_id"] = f"A1FS_ONLINE_V1_S07_PLAN:{grammar_id}:{lesson['skill']}"
    plan["learner_id"] = CANARY_LEARNER_ID
    plan["rationale"] = {
        "reason": "S07_ADMITTED_CANONICAL_UNIT_RUNTIME_LANE_BINDING",
        "selection_authority_task_id": TASK_ID,
        "m4_new_selection_performed": False,
    }
    plan["s07_task_id"] = TASK_ID
    plan.pop("s03_task_id", None)
    plan["next_short_step"] = NEXT_SHORT_STEP
    return plan


def _render_bundles(*, consumer_path: Path, consumer: Mapping[str, Any], ui_root: Path) -> tuple[dict[str, str], int]:
    if ui_root.exists():
        shutil.rmtree(ui_root)
    index: dict[str, str] = {}
    total = 0
    first_grammar = str(consumer["lesson_catalog"][0]["runtime_projection"]["source_grammar_unit_id"])
    for lesson in consumer["lesson_catalog"]:
        grammar_id = str(lesson["runtime_projection"]["source_grammar_unit_id"])
        skill = str(lesson["skill"]).casefold()
        plan = _plan_for_lesson(lesson)
        plan_path = ui_root / "plans" / grammar_id / f"{skill}.plan.private.json"
        write_json(plan_path, plan, private=True)
        lane_root = ui_root / "units" / grammar_id / skill
        manifest = m5.build_ui(consumer_path=consumer_path, plan_path=plan_path, output_root=lane_root)
        bundle_path = lane_root / "lesson.private.json"
        index[str(lesson["lesson_id"])] = str(bundle_path)
        total += int(manifest["asset_count"])
        if grammar_id == first_grammar:
            compatibility = ui_root / skill
            if compatibility.exists():
                shutil.rmtree(compatibility)
            shutil.copytree(lane_root, compatibility)
    return index, total


def _load_bundle_index(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    value = read_json(path, "bundle_index")
    rows = value.get("lessons")
    units = value.get("units")
    if not isinstance(rows, Mapping) or not rows or not isinstance(units, list) or not units:
        raise MultiUnitExpansionError("bundle_index_invalid")
    sequence_by_grammar: dict[str, int] = {}
    for unit in units:
        if not isinstance(unit, Mapping):
            raise MultiUnitExpansionError("bundle_index_unit_not_object")
        grammar_id = str(unit.get("grammar_unit_id") or "")
        sequence_index = unit.get("sequence_index")
        if (
            not grammar_id
            or not isinstance(sequence_index, int)
            or sequence_index < 1
            or grammar_id in sequence_by_grammar
        ):
            raise MultiUnitExpansionError(f"bundle_index_unit_invalid:{grammar_id}")
        sequence_by_grammar[grammar_id] = sequence_index
    result: dict[str, dict[str, Any]] = {}
    for lesson_id, bundle_path in rows.items():
        bundle = read_json(Path(str(bundle_path)), f"bundle:{lesson_id}")
        lesson = bundle.get("lesson", {})
        assets = bundle.get("assets", [])
        grammar_id = str(lesson_id).split(":", 2)[1] if str(lesson_id).count(":") >= 2 else ""
        if (
            str(lesson.get("lesson_id") or "") != str(lesson_id)
            or not isinstance(assets, list)
            or not assets
            or grammar_id not in sequence_by_grammar
        ):
            raise MultiUnitExpansionError(f"bundle_contract_invalid:{lesson_id}")
        result[str(lesson_id)] = {
            "lesson": {
                "lesson_id": str(lesson["lesson_id"]),
                "skill": str(lesson["skill"]),
                "level": str(lesson["level"]),
            },
            "assets": [s04._safe_asset(asset) for asset in assets],
        }
    return result, sequence_by_grammar


def _table_rows(connection: sqlite3.Connection, table: str, order_by: str) -> list[list[Any]]:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if not exists:
        return []
    return [list(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY {order_by}").fetchall()]


def progress_state_digest(database_path: Path) -> str:
    with sqlite3.connect(database_path) as connection:
        return digest({
            table: _table_rows(connection, table, order_by)
            for table, order_by in PRESERVED_TABLES
        })


def _database_counts(database_path: Path) -> dict[str, int]:
    with sqlite3.connect(database_path) as connection:
        queries = {
            "lesson_count": "SELECT COUNT(*) FROM lesson_catalog",
            "asset_count": "SELECT COUNT(*) FROM lesson_assets",
            "response_contract_count": "SELECT COUNT(*) FROM response_contracts",
            "capture_enabled_contract_count": "SELECT COUNT(*) FROM response_contracts WHERE capture_enabled=1",
            "speaking_capture_enabled_count": "SELECT COUNT(*) FROM response_contracts WHERE skill='SPEAKING' AND capture_enabled=1",
            "listening_lesson_count": "SELECT COUNT(*) FROM lesson_catalog WHERE skill='LISTENING'",
            "profile_count": "SELECT COUNT(*) FROM learner_profiles",
            "session_count": "SELECT COUNT(*) FROM learning_sessions",
            "attempt_count": "SELECT COUNT(*) FROM response_attempts",
        }
        return {name: int(connection.execute(sql).fetchone()[0]) for name, sql in queries.items()}


def _validate_existing_subset(database_path: Path, consumer: Mapping[str, Any]) -> None:
    lessons = {str(row["lesson_id"]): row for row in consumer["lesson_catalog"]}
    assets = {str(row["asset_key"]): row for row in consumer["asset_records"]}
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        for row in connection.execute("SELECT * FROM lesson_catalog"):
            expected = lessons.get(str(row["lesson_id"]))
            if not expected:
                raise MultiUnitExpansionError(f"existing_lesson_not_in_expansion:{row['lesson_id']}")
            actual = (
                row["lesson_node_id"], row["skill"], row["level"],
                json.loads(row["roles_json"]), json.loads(row["requirement_node_ids_json"]),
            )
            target = (
                expected["lesson_node_id"], expected["skill"], expected["level"],
                sorted(expected["roles"]), sorted(expected["requirement_node_ids"]),
            )
            if actual != target:
                raise MultiUnitExpansionError(f"existing_lesson_contract_drift:{row['lesson_id']}")
        for row in connection.execute("SELECT * FROM lesson_assets"):
            expected = assets.get(str(row["asset_key"]))
            if not expected:
                raise MultiUnitExpansionError(f"existing_asset_not_in_expansion:{row['asset_key']}")
            actual = (row["asset_id"], row["lesson_id"], row["role"], row["content_digest"])
            target = (expected["asset_id"], expected["lesson_id"], expected["role"], expected["content_digest"])
            if actual != target:
                raise MultiUnitExpansionError(f"existing_asset_contract_drift:{row['asset_key']}")


def _migrate_clone(
    *,
    source_database: Path,
    target_database: Path,
    consumer_path: Path,
    consumer: Mapping[str, Any],
    bundle_paths: Mapping[str, str],
) -> dict[str, int]:
    shutil.copy2(source_database, target_database)
    _validate_existing_subset(target_database, consumer)
    raw_digest = file_digest(consumer_path)
    with sqlite3.connect(target_database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        if metadata.get("validation_status") != m3.STATUS:
            raise MultiUnitExpansionError("m3_database_status_invalid")
        if metadata.get("mastery_write_enabled") != "false":
            raise MultiUnitExpansionError("mastery_write_boundary_invalid")
        for lesson in consumer["lesson_catalog"]:
            connection.execute(
                """INSERT OR IGNORE INTO lesson_catalog
                (lesson_id,lesson_node_id,skill,level,roles_json,requirement_node_ids_json,payload_access_allowed)
                VALUES(?,?,?,?,?,?,?)""",
                (
                    lesson["lesson_id"], lesson["lesson_node_id"], lesson["skill"], lesson["level"],
                    canonical(sorted(lesson["roles"])), canonical(sorted(lesson["requirement_node_ids"])), 1,
                ),
            )
        for asset in consumer["asset_records"]:
            connection.execute(
                """INSERT OR IGNORE INTO lesson_assets
                (asset_key,asset_id,lesson_id,role,content_digest) VALUES(?,?,?,?,?)""",
                (asset["asset_key"], asset["asset_id"], asset["lesson_id"], asset["role"], asset["content_digest"]),
            )
        updates = {
            "consumer_sha256": raw_digest,
            "s07_task_id": TASK_ID,
            "s07_schema_version": SCHEMA_VERSION,
            "s07_validation_status": PASS_STATUS,
            "s07_admitted_unit_count": str(consumer["s07_runtime_projection"]["admitted_unit_count"]),
            "s07_consumer_sha256": raw_digest,
            "mastery_write_enabled": "false",
            "a2_session_enabled": "false",
            "learner_release_approved": "false",
        }
        connection.executemany("INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)", updates.items())
        connection.commit()
    response_store = m6.ResponseEvidenceStore(target_database)
    for lesson in consumer["lesson_catalog"]:
        response_store.initialize(
            consumer_path=consumer_path,
            lesson_bundle_path=Path(bundle_paths[str(lesson["lesson_id"])]),
        )
    counts = _database_counts(target_database)
    if counts["lesson_count"] != consumer["counts"]["lesson_count"]:
        raise MultiUnitExpansionError("migrated_lesson_count_mismatch")
    if counts["asset_count"] != consumer["counts"]["asset_record_count"]:
        raise MultiUnitExpansionError("migrated_asset_count_mismatch")
    if counts["response_contract_count"] != consumer["counts"]["asset_record_count"]:
        raise MultiUnitExpansionError("migrated_response_contract_count_mismatch")
    if counts["speaking_capture_enabled_count"] != 0 or counts["listening_lesson_count"] != 0:
        raise MultiUnitExpansionError("audio_or_speaking_capture_boundary_invalid")
    return counts


class MultiUnitWorkbenchApplication(s06.ProgressReadbackApplication):
    def __init__(
        self,
        *,
        database_path: Path,
        bundles: Mapping[str, Mapping[str, Any]],
        sequence_by_grammar: Mapping[str, int],
        default_learner_id: str = s05.DEFAULT_LEARNER_ID,
    ):
        if not bundles:
            raise MultiUnitExpansionError("multiunit_bundles_empty")
        self.lesson_bundles = deepcopy(dict(bundles))
        self.sequence_by_grammar = {
            str(grammar_id): int(sequence_index)
            for grammar_id, sequence_index in sequence_by_grammar.items()
        }
        grammar_ids = {
            lesson_id.split(":", 2)[1]
            for lesson_id in self.lesson_bundles
            if lesson_id.count(":") >= 2
        }
        if grammar_ids != set(self.sequence_by_grammar):
            raise MultiUnitExpansionError("multiunit_sequence_index_binding_invalid")
        compatibility: dict[str, Mapping[str, Any]] = {}
        ordered_lessons = sorted(
            self.lesson_bundles.items(),
            key=lambda row: (
                self.sequence_by_grammar[row[0].split(":", 2)[1]],
                SKILL_ORDER.index(str(row[1]["lesson"]["skill"]).casefold()),
            ),
        )
        for _, bundle in ordered_lessons:
            compatibility.setdefault(str(bundle["lesson"]["skill"]).casefold(), bundle)
        if set(compatibility) != set(SKILL_ORDER):
            raise MultiUnitExpansionError("multiunit_compatibility_lane_set_invalid")
        super().__init__(database_path=database_path, bundles=compatibility)
        self.default_learner_id = default_learner_id

    def bootstrap(self) -> dict[str, Any]:
        grouped: dict[str, dict[str, Any]] = {}
        ordered_lessons = sorted(
            self.lesson_bundles.items(),
            key=lambda row: (
                self.sequence_by_grammar[row[0].split(":", 2)[1]],
                SKILL_ORDER.index(str(row[1]["lesson"]["skill"]).casefold()),
            ),
        )
        for lesson_id, bundle in ordered_lessons:
            grammar_id = lesson_id.split(":", 2)[1]
            unit = grouped.setdefault(
                grammar_id,
                {
                    "grammar_unit_id": grammar_id,
                    "sequence_index": self.sequence_by_grammar[grammar_id],
                    "lanes": [],
                },
            )
            unit["lanes"].append({
                "skill": str(bundle["lesson"]["skill"]).upper(),
                "lesson_id": lesson_id,
                "level": bundle["lesson"]["level"],
                "asset_count": len(bundle["assets"]),
                "assets": deepcopy(bundle["assets"]),
            })
        units = sorted(grouped.values(), key=lambda row: row["sequence_index"])
        return {
            "task_id": TASK_ID,
            "validation_status": PASS_STATUS,
            "product_status": PRODUCT_STATUS,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "unit_count": len(units),
            "units": units,
        }

    def start_session(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        lesson_id = str(payload.get("lesson_id") or "")
        learner_id = str(payload.get("learner_id") or self.default_learner_id)
        if lesson_id not in self.lesson_bundles:
            raise MultiUnitExpansionError("workbench_lesson_invalid")
        session_id = str(payload.get("session_id") or f"A1FS_ONLINE_V1_S07_SESSION:{uuid.uuid4().hex}")
        return self.state_store.start_session(
            learner_id=learner_id,
            lesson_id=lesson_id,
            session_id=session_id,
            at=str(payload["at"]) if payload.get("at") else None,
        )

    def progress_readback(self) -> dict[str, Any]:
        return s06._database_progress(self.database_path, self.default_learner_id)


class MultiUnitWorkbenchHandler(s06.ProgressReadbackHandler):
    @property
    def app(self) -> MultiUnitWorkbenchApplication:
        return self.server.app  # type: ignore[attr-defined]


class MultiUnitWorkbenchServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], app: MultiUnitWorkbenchApplication, static_root: Path):
        if str(address[0]).casefold() not in s04.LOOPBACK_HOSTS:
            raise MultiUnitExpansionError(f"non_loopback_host_forbidden:{address[0]}")
        self.app = app
        self.static_root = Path(static_root)
        super().__init__(address, MultiUnitWorkbenchHandler)


def _write_static(static_root: Path) -> None:
    static_root.mkdir(parents=True, exist_ok=True)
    index = """<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'"><title>A1FS Multi-unit Workbench</title><link rel="stylesheet" href="/styles.css"></head><body><main><h1>A1FS 多單元私有學習工作台</h1><p id="status" aria-live="polite">載入中</p><nav id="units" aria-label="學習單元"></nav><nav id="lanes" aria-label="技能"></nav><section id="items"></section><button id="complete" hidden>完成目前技能</button><section class="progress"><h2>學習進度</h2><button id="refresh-progress">更新進度</button><pre id="progress" aria-live="polite"></pre></section></main><script src="/app.js"></script></body></html>"""
    css = """body{font-family:system-ui,sans-serif;margin:0;background:#f4f4f4;color:#181818}main{max-width:960px;margin:auto;padding:24px}button,input,textarea{font:inherit}.unit,.lane,.submit,#complete,#refresh-progress{margin:4px;padding:10px 14px}.selected{font-weight:700;border-width:2px}.card,.progress{background:white;padding:16px;margin:12px 0;border-radius:8px}.options{display:grid;gap:8px}textarea{width:100%;min-height:90px}pre{white-space:pre-wrap;overflow-wrap:anywhere}.result{font-weight:700}button:disabled{opacity:.55}"""
    js = """'use strict';let state=null,unit=null,active=null;const status=document.querySelector('#status'),units=document.querySelector('#units'),lanes=document.querySelector('#lanes'),items=document.querySelector('#items'),complete=document.querySelector('#complete'),progress=document.querySelector('#progress'),refresh=document.querySelector('#refresh-progress');const text=(n,v)=>{n.textContent=v??''};async function api(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});const j=await r.json();if(!r.ok)throw new Error(j.error||'request_failed');return j}async function loadProgress(){text(progress,JSON.stringify(await api('/api/progress'),null,2))}function responseFor(card,asset){const options=asset.learner_payload.options||[];if(options.length){const checked=card.querySelector('input[type=radio]:checked');if(!checked)throw new Error('請先選擇答案');return checked.value}const area=card.querySelector('textarea');if(!area||!area.value.trim())throw new Error('請先輸入答案');return area.value}async function expose(asset){const result=await api('/api/exposure',{session_id:active.session_id,asset_key:asset.asset_key,expected_session_version:active.session_version});active.session_version=result.session_version;return result}function renderLane(lane){items.replaceChildren();for(const asset of lane.assets){const card=document.createElement('article');card.className='card';const prompt=document.createElement('p');text(prompt,asset.learner_payload.prompt);card.append(prompt);const options=asset.learner_payload.options||[];if(options.length){const box=document.createElement('div');box.className='options';for(const option of options){const label=document.createElement('label'),input=document.createElement('input');input.type='radio';input.name=asset.asset_key;input.value=option;label.append(input,document.createTextNode(' '+option));box.append(label)}card.append(box)}else if(asset.learner_payload.response_capture_enabled){const area=document.createElement('textarea');area.setAttribute('aria-label','回答');card.append(area)}const button=document.createElement('button'),result=document.createElement('p');button.className='submit';result.className='result';if(asset.learner_payload.response_capture_enabled){text(button,'送出回答');button.addEventListener('click',async()=>{try{button.disabled=true;await expose(asset);const scored=await api('/api/response',{session_id:active.session_id,asset_key:asset.asset_key,response:responseFor(card,asset),expected_session_version:active.session_version});active.session_version=scored.session_version;text(result,scored.outcome);await loadProgress()}catch(error){text(status,error.message)}finally{button.disabled=false}})}else{text(button,'標記已練習');button.addEventListener('click',async()=>{try{button.disabled=true;await expose(asset);text(result,'RECORDED');await loadProgress()}catch(error){text(status,error.message)}finally{button.disabled=false}})}card.append(button,result);items.append(card)}}async function begin(lane){if(active)throw new Error('請先完成目前技能');active=await api('/api/session/start',{lesson_id:lane.lesson_id});complete.hidden=false;renderLane(lane);text(status,lane.lesson_id+' started')}function chooseUnit(value){if(active)throw new Error('請先完成目前技能');unit=value;lanes.replaceChildren();items.replaceChildren();for(const lane of value.lanes){const button=document.createElement('button');button.className='lane';text(button,lane.skill);button.addEventListener('click',()=>begin(lane).catch(error=>text(status,error.message)));lanes.append(button)}}complete.addEventListener('click',async()=>{try{if(!active)return;const done=await api('/api/session/complete',{session_id:active.session_id,expected_session_version:active.session_version});text(status,done.session_state);active=null;complete.hidden=true;items.replaceChildren();await loadProgress()}catch(error){text(status,error.message)}});refresh.addEventListener('click',()=>loadProgress().catch(error=>text(status,error.message)));async function start(){state=await api('/api/bootstrap');text(status,state.product_status);for(const value of state.units){const button=document.createElement('button');button.className='unit';text(button,value.grammar_unit_id);button.addEventListener('click',()=>{try{chooseUnit(value)}catch(error){text(status,error.message)}});units.append(button)}if(state.units.length)chooseUnit(state.units[0]);await loadProgress()}start().catch(error=>text(status,error.message));"""
    (static_root / "index.html").write_text(index + "\n", encoding="utf-8")
    (static_root / "styles.css").write_text(css + "\n", encoding="utf-8")
    (static_root / "app.js").write_text(js + "\n", encoding="utf-8")


def _run_new_unit_canary(
    *,
    database_path: Path,
    bundle_index_path: Path,
    second_unit: Mapping[str, Any],
    canary_database: Path,
) -> dict[str, Any]:
    shutil.copy2(database_path, canary_database)
    bundles, sequence_by_grammar = _load_bundle_index(bundle_index_path)
    app = MultiUnitWorkbenchApplication(
        database_path=canary_database,
        bundles=bundles,
        sequence_by_grammar=sequence_by_grammar,
        default_learner_id=CANARY_LEARNER_ID,
    )
    app.enroll(
        learner_id=CANARY_LEARNER_ID,
        display_label="S07 Multi-unit Canary",
        subject_key=CANARY_SUBJECT_KEY,
        at="2026-01-09T00:00:00Z",
    )
    grammar_id = str(second_unit["grammar_unit_id"])
    lesson_id = f"A1FS_ONLINE_V1:{grammar_id}:READING"
    reading_bundle = bundles[lesson_id]
    asset_key, wrong = s04._select_canary_response(canary_database, reading_bundle["assets"])
    session = app.start_session({
        "lesson_id": lesson_id,
        "learner_id": CANARY_LEARNER_ID,
        "session_id": CANARY_SESSION_ID,
        "at": "2026-01-09T00:00:10Z",
    })
    session = app.record_exposure({
        "session_id": CANARY_SESSION_ID,
        "asset_key": asset_key,
        "expected_session_version": session["session_version"],
        "at": "2026-01-09T00:00:20Z",
    })
    scored = app.submit_response({
        "learner_id": CANARY_LEARNER_ID,
        "session_id": CANARY_SESSION_ID,
        "asset_key": asset_key,
        "response": wrong,
        "expected_session_version": session["session_version"],
        "attempt_id": CANARY_ATTEMPT_ID,
        "submitted_at": "2026-01-09T00:00:30Z",
    })
    completed = app.complete_session({
        "session_id": CANARY_SESSION_ID,
        "expected_session_version": scored["session_version"],
        "at": "2026-01-09T00:00:40Z",
    })
    progress = s06._database_progress(canary_database, CANARY_LEARNER_ID)
    if scored.get("outcome") != "AUTO_FAIL" or completed.get("session_state") != "COMPLETED":
        raise MultiUnitExpansionError("new_unit_runtime_canary_failed")
    expected = {
        "session_count": 1, "completed_session_count": 1, "exposure_count": 1,
        "attempt_count": 1, "auto_fail_count": 1,
    }
    for key, value in expected.items():
        if progress["summary"].get(key) != value:
            raise MultiUnitExpansionError(f"new_unit_canary_progress_invalid:{key}")
    return {
        "newly_admitted_unit_runtime_canary": True,
        "canary_unit_sequence_index": int(second_unit["sequence_index"]),
        "session_count": 1,
        "completed_session_count": 1,
        "exposure_count": 1,
        "attempt_count": 1,
        "auto_fail_count": 1,
        "speaking_attempt_count": 0,
        "listening_session_count": 0,
    }


def materialize(
    *,
    cp01_path: Path,
    cp04_path: Path,
    m03_path: Path,
    s02_path: Path,
    s05_path: Path,
    s06_path: Path,
    output_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    cp01_artifact = read_json(cp01_path, "cp01")
    cp04_artifact = read_json(cp04_path, "cp04")
    m03_artifact = read_json(m03_path, "m03")
    s02_artifact = read_json(s02_path, "s02")
    s05_receipt = read_json(s05_path, "s05")
    s06_receipt = read_json(s06_path, "s06")
    production_database, _ = _source_paths(s05_receipt, s06_receipt)
    admission = build_admission(
        cp01_artifact=cp01_artifact,
        cp04_artifact=cp04_artifact,
        m03_artifact=m03_artifact,
        s02_artifact=s02_artifact,
    )
    consumer = build_consumer(admission, m03_artifact)

    output_root = Path(output_root).resolve()
    runtime_root = output_root / "expanded_runtime"
    if runtime_root.exists():
        shutil.rmtree(runtime_root)
    runtime_root.mkdir(parents=True, exist_ok=True)
    consumer_path = runtime_root / "multiunit_runtime_consumer.private.json"
    admission_path = runtime_root / "multiunit_admission.private.json"
    ui_root = runtime_root / "ui"
    static_root = runtime_root / "static"
    bundle_index_path = runtime_root / "bundle_index.private.json"
    write_json(admission_path, admission, private=True)
    write_json(consumer_path, consumer, private=True)
    bundle_paths, rendered_asset_count = _render_bundles(
        consumer_path=consumer_path, consumer=consumer, ui_root=ui_root
    )
    write_json(
        bundle_index_path,
        {
            "task_id": TASK_ID,
            "units": [
                {
                    "grammar_unit_id": unit["grammar_unit_id"],
                    "sequence_index": unit["sequence_index"],
                }
                for unit in admission["admitted_units"]
            ],
            "lessons": bundle_paths,
        },
        private=True,
    )
    _write_static(static_root)

    progress_before = progress_state_digest(production_database)
    counts_before = _database_counts(production_database)
    staging_database = runtime_root / "expanded_production_candidate.sqlite3"
    counts_after = _migrate_clone(
        source_database=production_database,
        target_database=staging_database,
        consumer_path=consumer_path,
        consumer=consumer,
        bundle_paths=bundle_paths,
    )
    progress_candidate = progress_state_digest(staging_database)
    if progress_candidate != progress_before:
        raise MultiUnitExpansionError("production_progress_state_changed_during_migration")
    canary_database = runtime_root / "new_unit_runtime_canary.sqlite3"
    canary = _run_new_unit_canary(
        database_path=staging_database,
        bundle_index_path=bundle_index_path,
        second_unit=admission["admitted_units"][1],
        canary_database=canary_database,
    )

    backup_database = runtime_root / "production_before_migration.sqlite3"
    shutil.copy2(production_database, backup_database)
    try:
        os.replace(staging_database, production_database)
    except OSError as exc:
        raise MultiUnitExpansionError(f"production_database_atomic_replace_failed:{exc}") from exc
    progress_after = progress_state_digest(production_database)
    if progress_after != progress_before:
        try:
            os.replace(backup_database, production_database)
        except OSError:
            pass
        raise MultiUnitExpansionError("production_progress_state_changed_after_atomic_replace")
    try:
        backup_database.unlink()
    except OSError:
        pass

    receipt_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "release_profile": RELEASE_PROFILE,
        "source_identity": {
            "cp01_sha256": s02.digest(cp01_artifact),
            "cp04_sha256": s02.digest(cp04_artifact),
            "m03_sha256": s02.digest(m03_artifact),
            "s02_sha256": s02.digest(s02_artifact),
            "s05_sha256": s05.digest(s05_receipt),
            "s06_sha256": s06.digest(s06_receipt),
        },
        "runtime_outputs": {
            "root": str(runtime_root),
            "admission_path": str(admission_path),
            "consumer_path": str(consumer_path),
            "database_path": str(production_database),
            "ui_root": str(ui_root),
            "static_root": str(static_root),
            "bundle_index_path": str(bundle_index_path),
            "canary_database_path": str(canary_database),
        },
        "admission_summary": deepcopy(admission["admission_summary"]),
        "runtime_summary": {
            "expanded_unit_count": admission["admission_summary"]["admitted_unit_count"],
            "expanded_lesson_count": counts_after["lesson_count"],
            "expanded_asset_count": counts_after["asset_count"],
            "m5_renderer_bundle_count": len(bundle_paths),
            "m5_rendered_asset_count": rendered_asset_count,
            "m6_response_contract_count": counts_after["response_contract_count"],
            "m6_capture_enabled_contract_count": counts_after["capture_enabled_contract_count"],
            "speaking_capture_enabled_count": counts_after["speaking_capture_enabled_count"],
            "listening_runtime_item_count": 0,
            "audio_runtime_asset_count": 0,
        },
        "migration_summary": {
            "existing_lesson_count_before": counts_before["lesson_count"],
            "existing_asset_count_before": counts_before["asset_count"],
            "existing_profile_count_preserved": counts_after["profile_count"] == counts_before["profile_count"],
            "existing_session_count_preserved": counts_after["session_count"] == counts_before["session_count"],
            "existing_attempt_count_preserved": counts_after["attempt_count"] == counts_before["attempt_count"],
            "progress_state_sha256_before": progress_before,
            "progress_state_sha256_after": progress_after,
            "production_progress_preserved": progress_after == progress_before,
            "atomic_database_migration": True,
            "first_unit_identity_preserved": True,
        },
        "new_unit_runtime_canary": canary,
        "capability_contract": {
            "s02_first_unit_authority_preserved": True,
            "canonical_prerequisite_closure_enforced": True,
            "m3_session_progress_authority_reused": True,
            "m5_renderer_authority_reused": True,
            "m6_response_scoring_authority_reused": True,
            "persistent_s05_database_migrated_in_place": True,
            "parallel_curriculum_created": False,
            "parallel_state_engine_created": False,
            "parallel_scoring_engine_created": False,
            "public_network_binding_allowed": False,
            "speaking_capture_enabled": False,
            "listening_enabled": False,
            "audio_enabled": False,
            "mastery_write_enabled": False,
        },
        "product_status": PRODUCT_STATUS,
        "claim_boundaries": {
            "real_learner_progress_mutated_by_canary": False,
            "real_learner_attempt_claimed": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "public_online_delivery_claimed": False,
            "audio_complete": False,
            "speaking_recording_complete": False,
            "a2_unlocked": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    receipt = {**receipt_core, "artifact_sha256": digest(receipt_core)}
    safe_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "release_profile": RELEASE_PROFILE,
        "admission_summary": deepcopy(receipt_core["admission_summary"]),
        "runtime_summary": deepcopy(receipt_core["runtime_summary"]),
        "migration_summary": {
            key: value for key, value in receipt_core["migration_summary"].items()
            if not key.startswith("progress_state_sha256")
        },
        "new_unit_runtime_canary": deepcopy(canary),
        "capability_contract": deepcopy(receipt_core["capability_contract"]),
        "product_status": PRODUCT_STATUS,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    safe_scan(safe)
    return receipt, safe


def _application_from_receipt(receipt_path: Path) -> tuple[MultiUnitWorkbenchApplication, Path]:
    receipt = read_json(receipt_path, "s07_receipt")
    if receipt.get("task_id") != TASK_ID or receipt.get("validation_status") != PASS_STATUS:
        raise MultiUnitExpansionError("s07_receipt_status_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest(core):
        raise MultiUnitExpansionError("s07_receipt_digest_invalid")
    outputs = receipt.get("runtime_outputs", {})
    database = Path(str(outputs.get("database_path") or ""))
    bundle_index = Path(str(outputs.get("bundle_index_path") or ""))
    static_root = Path(str(outputs.get("static_root") or ""))
    if not database.is_file() or not bundle_index.is_file() or not static_root.is_dir():
        raise MultiUnitExpansionError("s07_runtime_outputs_missing")
    bundles, sequence_by_grammar = _load_bundle_index(bundle_index)
    return MultiUnitWorkbenchApplication(
        database_path=database,
        bundles=bundles,
        sequence_by_grammar=sequence_by_grammar,
    ), static_root


def serve(*, receipt_path: Path, host: str, port: int) -> None:
    app, static_root = _application_from_receipt(receipt_path)
    server = MultiUnitWorkbenchServer((host, port), app, static_root)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def readback(*, receipt_path: Path) -> dict[str, Any]:
    app, _ = _application_from_receipt(receipt_path)
    return {
        "unit_count": len({lesson_id.split(":", 2)[1] for lesson_id in app.lesson_bundles}),
        "lesson_count": len(app.lesson_bundles),
        "progress": app.progress_readback(),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("materialize")
    build.add_argument("--cp01", type=Path, required=True)
    build.add_argument("--cp04", type=Path, required=True)
    build.add_argument("--m03", type=Path, required=True)
    build.add_argument("--s02", type=Path, required=True)
    build.add_argument("--s05", type=Path, required=True)
    build.add_argument("--s06", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--report", type=Path, required=True)
    server = commands.add_parser("serve")
    server.add_argument("--receipt", type=Path, required=True)
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=8765)
    snap = commands.add_parser("readback")
    snap.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "serve":
            serve(receipt_path=args.receipt, host=args.host, port=args.port)
            return 0
        if args.command == "readback":
            print(json.dumps(readback(receipt_path=args.receipt), ensure_ascii=False, indent=2))
            return 0
        receipt, safe = materialize(
            cp01_path=args.cp01,
            cp04_path=args.cp04,
            m03_path=args.m03,
            s02_path=args.s02,
            s05_path=args.s05,
            s06_path=args.s06,
            output_root=args.output.parent,
        )
        from ulga.validators.validate_a1fs_online_v1_s07_multiunit_runtime_expansion import validate_outputs
        validation = validate_outputs(
            receipt=receipt,
            safe_report=safe,
            output_root=args.output.parent,
            cp01_path=args.cp01,
            cp04_path=args.cp04,
            m03_path=args.m03,
            s02_path=args.s02,
            s05_path=args.s05,
            s06_path=args.s06,
        )
        if validation["error_count"]:
            raise MultiUnitExpansionError("validation_failed:" + "|".join(validation["errors"]))
        write_json(args.output, receipt, private=True)
        write_json(args.report, safe)
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (
        MultiUnitExpansionError,
        s02.FirstUnitAdmissionError,
        s03.RuntimeIntegrationError,
        s04.WorkbenchError,
        s05.PersistenceError,
        s06.ReadbackError,
        m3.StateStoreError,
        m5.RendererError,
        m6.ResponseEvidenceError,
        OSError,
        sqlite3.Error,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
