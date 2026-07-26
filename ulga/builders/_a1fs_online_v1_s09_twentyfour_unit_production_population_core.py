#!/usr/bin/env python3
"""Populate all existing A1/A1+ canonical units into the private no-audio runtime.

S09 promotes the already-existing M03 text-mode and oral-practice contracts for all
24 canonical units after per-item contract validation. It reuses CP01/CP04 authority,
the S08 learner journey surface, the M3 learner state store, the M5 renderer, and the
M6 response/scoring engine. It does not author learner content, bypass canonical unit
identity, enable Listening without audio, capture Speaking, write mastery, or publish
on a public network.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_online_v1_s02_first_nonaudio_unit_admission as s02  # noqa: E402
from ulga.builders import build_a1fs_online_v1_s05_private_learner_identity_progress_persistence as s05  # noqa: E402
from ulga.builders import build_a1fs_online_v1_s07_multiunit_runtime_expansion as s07  # noqa: E402
from ulga.builders import build_a1fs_online_v1_s08_private_multiunit_learner_journey_qa as s08  # noqa: E402
from ulga.runners.run_a1fs_s07_with_explicit_sqlite_close import explicit_sqlite_context_close  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Promotes existing M03 item identities after complete prompt/answer/scoring/media contract checks, "
    "projects them through the existing S07/S08 runtime, and atomically expands the existing persistent "
    "database. No curriculum, learner content, answer key, audio, Speaking capture, mastery, public "
    "delivery, or parallel state/scoring engine is authored."
)

PROGRAM_ID = "A1FS-ONLINE-V1"
TASK_ID = "A1FS-ONLINE-V1-S09_TwentyFourUnitProductionPopulation_NoAudio"
SCHEMA_VERSION = "a1fs.online.v1.s09.twentyfour_unit_production_population.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_S09_TWENTYFOUR_UNIT_PRODUCTION_POPULATED"
PRODUCT_STATUS = "PRIVATE_TWENTYFOUR_UNIT_NONAUDIO_POPULATION_READY_NOT_PUBLIC"
RELEASE_PROFILE = "ONLINE_V1_AUDIO_DEFERRED"
NEXT_SHORT_STEP = "A1FS-ONLINE-V1-S09_SharedAuthorityProductionMaterializationReadback"
SKILL_ORDER = ("reading", "writing", "speaking")
EXPECTED_UNIT_COUNT = 24
EXPECTED_READING_PER_UNIT = 4
EXPECTED_WRITING_PER_UNIT = 4
EXPECTED_SPEAKING_PRACTICE_PER_UNIT = 3
EXPECTED_ITEM_COUNT = EXPECTED_UNIT_COUNT * (
    EXPECTED_READING_PER_UNIT + EXPECTED_WRITING_PER_UNIT + EXPECTED_SPEAKING_PRACTICE_PER_UNIT
)


class PopulationError(ValueError):
    """Fail-closed S09 population, migration, or serving error."""


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PopulationError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise PopulationError(f"{code}_not_object")
    return value


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    s07.write_json(Path(path), value, private=private)


def _verify_s08(receipt: Mapping[str, Any]) -> tuple[Path, Path]:
    if (
        receipt.get("task_id") != s08.TASK_ID
        or receipt.get("schema_version") != s08.SCHEMA_VERSION
        or receipt.get("validation_status") != s08.PASS_STATUS
        or receipt.get("product_status") != s08.PRODUCT_STATUS
        or receipt.get("stop_reason") != "NONE"
    ):
        raise PopulationError("s08_receipt_contract_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s08.digest(core):
        raise PopulationError("s08_receipt_digest_invalid")
    outputs = receipt.get("runtime_outputs", {})
    database = Path(str(outputs.get("database_path") or "")).resolve()
    bundle_index = Path(str(outputs.get("bundle_index_path") or "")).resolve()
    if not database.is_file() or not bundle_index.is_file():
        raise PopulationError("s08_runtime_outputs_missing")
    return database, bundle_index


def _verify_text_item(
    *,
    item: Mapping[str, Any],
    item_id: str,
    grammar_id: str,
    learning_id: str,
    skill: str,
) -> None:
    readiness = item.get("readiness", {})
    prompt = item.get("prompt_contract", {})
    response = item.get("response_contract", {})
    answer = item.get("answer_contract", {})
    scoring = item.get("scoring_contract", {})
    media = item.get("media_contract", {})
    if (
        item.get("shared_item_id") != item_id
        or item.get("grammar_unit_id") != grammar_id
        or item.get("learning_unit_id") != learning_id
        or item.get("skill") != skill
        or item.get("item_role") not in {"practice", "assessment"}
    ):
        raise PopulationError(f"item_binding_invalid:{skill}:{item_id}")
    if (
        not isinstance(prompt, Mapping)
        or not str(prompt.get("prompt_text") or "").strip()
        or prompt.get("prompt_status") != "PROJECT_AUTHORED_CANDIDATE"
        or not isinstance(response, Mapping)
        or response.get("learner_input_required") is not True
        or not isinstance(answer, Mapping)
        or not str(answer.get("answer_mode") or "")
        or not isinstance(scoring, Mapping)
        or (
            scoring.get("real_skill_scoring_ready") is not True
            and scoring.get("human_review_fallback") is not True
        )
        or not isinstance(media, Mapping)
        or media.get("text_status") != "AVAILABLE"
        or media.get("audio_required") is not False
        or media.get("audio_status") != "NOT_REQUIRED"
    ):
        raise PopulationError(f"text_item_contract_invalid:{skill}:{item_id}")
    required = (
        "shared_item_contract_complete",
        "answer_contract_complete",
        "scoring_contract_complete",
        "media_contract_complete",
    )
    if any(readiness.get(key) is not True for key in required):
        raise PopulationError(f"text_item_readiness_invalid:{skill}:{item_id}")


def _text_lane_ids(
    *,
    curriculum_unit: Mapping[str, Any],
    item_index: Mapping[str, Mapping[str, Any]],
    skill: str,
) -> list[str]:
    grammar_id = str(curriculum_unit["grammar_unit_id"])
    learning_id = str(curriculum_unit["learning_unit_id"])
    lane = curriculum_unit.get("skill_lanes", {}).get(skill, {})
    item_ids = lane.get("candidate_item_ids")
    if not isinstance(item_ids, list) or len(item_ids) != 4 or len(set(item_ids)) != 4:
        raise PopulationError(f"cp01_candidate_lane_invalid:{grammar_id}:{skill}")
    roles: list[str] = []
    for raw_id in item_ids:
        item_id = str(raw_id or "")
        item = item_index.get(item_id)
        if not item_id or item is None:
            raise PopulationError(f"candidate_item_missing:{grammar_id}:{skill}:{item_id}")
        _verify_text_item(
            item=item,
            item_id=item_id,
            grammar_id=grammar_id,
            learning_id=learning_id,
            skill=skill,
        )
        roles.append(str(item["item_role"]))
    if roles.count("practice") != 3 or roles.count("assessment") != 1:
        raise PopulationError(f"candidate_lane_role_distribution_invalid:{grammar_id}:{skill}")
    return [str(item_id) for item_id in item_ids]


def _scene_ids(candidate_unit: Mapping[str, Any]) -> list[str]:
    result = sorted({
        str(row.get("scene_candidate_id"))
        for row in candidate_unit.get("scene_candidates", [])
        if isinstance(row, Mapping)
        and row.get("candidate_state") == "AUTHORITY_BACKED_METADATA_READY"
        and str(row.get("scene_candidate_id") or "")
    })
    return result


def build_full_admission(
    *,
    cp01_artifact: Mapping[str, Any],
    cp04_artifact: Mapping[str, Any],
    m03_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    cp01_units = s02._verify_cp01(cp01_artifact)
    cp04_units = s02._verify_cp04(cp04_artifact)
    item_index = s02._verify_m03(m03_artifact)
    if set(cp01_units) != set(cp04_units):
        raise PopulationError("cp01_cp04_unit_set_mismatch")

    ordered_curriculum = sorted(
        cp01_units.values(), key=lambda row: (int(row["sequence_index"]), str(row["learning_unit_id"]))
    )
    if [int(row["sequence_index"]) for row in ordered_curriculum] != list(range(1, 25)):
        raise PopulationError("canonical_sequence_invalid")

    admitted_units: list[dict[str, Any]] = []
    admitted_learning_ids: set[str] = set()
    all_item_ids: list[str] = []
    scene_unit_count = 0
    scene_count = 0
    raz_binding_count = 0

    for curriculum_unit in ordered_curriculum:
        grammar_id = str(curriculum_unit["grammar_unit_id"])
        learning_id = str(curriculum_unit["learning_unit_id"])
        candidate_unit = cp04_units[grammar_id]
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
        if identity != peer:
            raise PopulationError(f"cp01_cp04_unit_identity_drift:{grammar_id}")
        prerequisites = curriculum_unit.get("prerequisite_unit_ids")
        if not isinstance(prerequisites, list) or len(prerequisites) != len(set(prerequisites)):
            raise PopulationError(f"prerequisite_contract_invalid:{grammar_id}")
        if not set(str(value) for value in prerequisites).issubset(admitted_learning_ids):
            raise PopulationError(f"canonical_prerequisite_order_invalid:{grammar_id}")

        reading = _text_lane_ids(
            curriculum_unit=curriculum_unit, item_index=item_index, skill="reading"
        )
        writing = _text_lane_ids(
            curriculum_unit=curriculum_unit, item_index=item_index, skill="writing"
        )
        speaking, speaking_assessments = s02._speaking_practice_ids(grammar_id, item_index)
        if len(speaking) != 3 or len(speaking_assessments) != 1:
            raise PopulationError(f"speaking_lane_distribution_invalid:{grammar_id}")
        for item_id in speaking:
            item = item_index[item_id]
            if item.get("learning_unit_id") != learning_id:
                raise PopulationError(f"speaking_learning_unit_binding_invalid:{item_id}")

        candidate_counts = candidate_unit.get("candidate_counts", {})
        unit_raz_count = int(candidate_counts.get("raz_content_candidate_count") or 0)
        if unit_raz_count < 1:
            raise PopulationError(f"raz_source_grounding_missing:{grammar_id}")
        raz_binding_count += unit_raz_count
        scenes = _scene_ids(candidate_unit)
        scene_count += len(scenes)
        scene_unit_count += bool(scenes)

        lanes = {
            "reading": s02._admitted_lane(
                reading,
                "INTERACTIVE_TEXT_ITEM",
                "M03_COMPLETE_CONTRACT_PROMOTED_BY_S09_PER_ITEM_VALIDATION",
            ),
            "writing": s02._admitted_lane(
                writing,
                "INTERACTIVE_TEXT_ITEM",
                "M03_COMPLETE_CONTRACT_PROMOTED_BY_S09_PER_ITEM_VALIDATION",
            ),
            "speaking": s02._admitted_lane(
                speaking,
                "ORAL_PRACTICE_CARD_NO_CAPTURE",
                "NO_SCORING_NO_MASTERY_EVIDENCE",
            ),
        }
        unit_ids = [item_id for skill in SKILL_ORDER for item_id in lanes[skill]["item_ids"]]
        if len(unit_ids) != 11 or len(unit_ids) != len(set(unit_ids)):
            raise PopulationError(f"unit_item_identity_invalid:{grammar_id}")
        all_item_ids.extend(unit_ids)
        admitted_learning_ids.add(learning_id)
        admitted_units.append({
            "learning_unit_id": learning_id,
            "grammar_unit_id": grammar_id,
            "sequence_index": int(curriculum_unit["sequence_index"]),
            "internal_stage": str(curriculum_unit["internal_stage"]),
            "canonical_egp_row_ids": list(curriculum_unit["canonical_egp_row_ids"]),
            "prerequisite_unit_ids": [str(value) for value in prerequisites],
            "selection_rank": int(curriculum_unit["sequence_index"]),
            "selection_origin": "S09_ALL_EXISTING_CANONICAL_UNITS_M03_CONTRACT_VALIDATION",
            "admitted_lanes": lanes,
            "scene_candidate_ids": scenes,
            "scene_population_status": (
                "AUTHORITY_BACKED_SCENE_METADATA_AVAILABLE"
                if scenes
                else "SCENE_AUTHORITY_PENDING_NONBLOCKING_TEXT_MODE"
            ),
            "raz_source_grounding_candidate_count": unit_raz_count,
            "deferred_lanes": {
                "listening": {
                    "status": "DEFERRED_POST_LAUNCH_AUDIO",
                    "reason": "PLAYABLE_AUDIO_REQUIRED_AND_NOT_IN_PRELAUNCH_SCOPE",
                    "item_ids": [],
                },
                "speaking_assessment": {
                    "status": "DEFERRED_POST_LAUNCH_AUDIO",
                    "reason": "RECORDING_TRANSCRIPT_AND_SCORING_NOT_IN_PRELAUNCH_SCOPE",
                    "item_ids": speaking_assessments,
                },
            },
            "unit_admission_status": "ADMITTED_NONAUDIO_TWENTYFOUR_UNIT_PRODUCTION",
        })

    if len(admitted_units) != 24 or len(all_item_ids) != EXPECTED_ITEM_COUNT:
        raise PopulationError("twentyfour_unit_population_denominator_invalid")
    if len(all_item_ids) != len(set(all_item_ids)):
        raise PopulationError("cross_unit_item_identity_collision")

    cp04_summary = cp04_artifact.get("coverage_summary", {})
    if raz_binding_count != cp04_summary.get("raz_material_binding_candidate_count"):
        raise PopulationError("raz_binding_count_not_reconciled")
    scene_gap = 24 - scene_unit_count
    if scene_count != cp04_summary.get("scene_candidate_count") or scene_gap != cp04_summary.get("scene_authority_gap_unit_count"):
        raise PopulationError("scene_coverage_not_reconciled")

    core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "artifact_type": "twentyfour_unit_nonaudio_production_population",
        "scope": "A1_A1_PLUS_ONLY",
        "release_profile": RELEASE_PROFILE,
        "source_identity": {
            "cp01_sha256": s02.digest(cp01_artifact),
            "cp04_sha256": s02.digest(cp04_artifact),
            "m03_sha256": s02.digest(m03_artifact),
        },
        "population_contract": {
            "course_container": "EXISTING_24_CANONICAL_UNITS_ONLY",
            "population_mode": "ALL_UNITS_EXISTING_M03_COMPLETE_CONTRACT_PROMOTION",
            "m03_candidate_only_items_require_s09_contract_validation": True,
            "raz_materials_remain_source_grounding_candidate_pool": True,
            "scene_authority_gap_is_explicit_and_nonblocking_for_text_mode": True,
            "new_unit_creation_allowed": False,
            "prerequisite_bypass_allowed": False,
            "listening_without_playable_audio_allowed": False,
            "speaking_capture_or_scoring_claim_allowed": False,
        },
        "admitted_units": admitted_units,
        "population_summary": {
            "canonical_unit_denominator": 24,
            "populated_unit_count": 24,
            "reading_item_count": 96,
            "writing_item_count": 96,
            "speaking_practice_card_count": 72,
            "admitted_nonaudio_item_count": EXPECTED_ITEM_COUNT,
            "runtime_lesson_count": 72,
            "raz_material_binding_candidate_count": raz_binding_count,
            "authority_backed_scene_unit_count": scene_unit_count,
            "scene_candidate_count": scene_count,
            "scene_authority_gap_unit_count": scene_gap,
            "listening_item_count": 0,
            "speaking_assessment_item_count": 0,
        },
        "closure_proof": {
            "all_24_existing_unit_identities_preserved": True,
            "prerequisite_closure_valid": True,
            "canonical_sequence_monotonic": True,
        },
        "claim_boundaries": {
            "new_curriculum_created": False,
            "new_learner_content_authored": False,
            "raz_private_source_text_materialized": False,
            "scene_gap_fabricated": False,
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
    return {**core, "artifact_sha256": s07.digest(core)}


@contextmanager
def _patched_s07_identity() -> Iterator[None]:
    names = ("TASK_ID", "SCHEMA_VERSION", "PASS_STATUS", "NEXT_SHORT_STEP", "PRODUCT_STATUS")
    previous = {name: getattr(s07, name) for name in names}
    try:
        s07.TASK_ID = TASK_ID
        s07.SCHEMA_VERSION = SCHEMA_VERSION
        s07.PASS_STATUS = PASS_STATUS
        s07.NEXT_SHORT_STEP = NEXT_SHORT_STEP
        s07.PRODUCT_STATUS = PRODUCT_STATUS
        yield
    finally:
        for name, value in previous.items():
            setattr(s07, name, value)


def build_consumer(admission: Mapping[str, Any], m03_artifact: Mapping[str, Any]) -> dict[str, Any]:
    with _patched_s07_identity():
        consumer = s07.build_consumer(admission, m03_artifact)
    for asset in consumer["asset_records"]:
        asset["release_scope"] = "PRIVATE_INTERNAL_A1FS_ONLINE_V1_S09"
    for lesson in consumer["lesson_catalog"]:
        lesson["release_scope"] = "PRIVATE_INTERNAL_A1FS_ONLINE_V1_S09"
        lesson["runtime_projection"]["selection_authority_task_id"] = TASK_ID
    projection = consumer["s07_runtime_projection"]
    projection.update({
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "admitted_unit_count": 24,
        "twentyfour_unit_population": True,
        "s07_runtime_engine_reused": True,
    })
    consumer["s09_runtime_projection"] = deepcopy(projection)
    consumer["next_short_step"] = NEXT_SHORT_STEP
    return consumer


class PopulationWorkbenchApplication(s08.JourneyWorkbenchApplication):
    def bootstrap(self) -> dict[str, Any]:
        value = super().bootstrap()
        value.update({
            "task_id": TASK_ID,
            "validation_status": PASS_STATUS,
            "product_status": PRODUCT_STATUS,
            "release_profile": RELEASE_PROFILE,
            "source_runtime": {
                "task_id": s08.TASK_ID,
                "validation_status": s08.PASS_STATUS,
                "product_status": s08.PRODUCT_STATUS,
            },
            "population_contract": {
                "canonical_unit_count": 24,
                "nonaudio_item_count": EXPECTED_ITEM_COUNT,
                "navigation_locked_while_active": True,
            },
        })
        return value


def _application_from_receipt(receipt_path: Path) -> tuple[PopulationWorkbenchApplication, Path]:
    receipt = read_json(receipt_path, "s09_receipt")
    if (
        receipt.get("task_id") != TASK_ID
        or receipt.get("schema_version") != SCHEMA_VERSION
        or receipt.get("validation_status") != PASS_STATUS
        or receipt.get("product_status") != PRODUCT_STATUS
        or receipt.get("stop_reason") != "NONE"
    ):
        raise PopulationError("s09_receipt_contract_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s07.digest(core):
        raise PopulationError("s09_receipt_digest_invalid")
    outputs = receipt.get("runtime_outputs", {})
    database = Path(str(outputs.get("database_path") or "")).resolve()
    bundle_index = Path(str(outputs.get("bundle_index_path") or "")).resolve()
    static_root = Path(str(outputs.get("static_root") or "")).resolve()
    if not database.is_file() or not bundle_index.is_file() or not static_root.is_dir():
        raise PopulationError("s09_runtime_outputs_missing")
    bundles, sequence_by_grammar = s07._load_bundle_index(bundle_index)
    if len(sequence_by_grammar) != 24 or len(bundles) != 72:
        raise PopulationError("s09_runtime_denominator_invalid")
    return PopulationWorkbenchApplication(
        database_path=database,
        bundles=bundles,
        sequence_by_grammar=sequence_by_grammar,
        default_learner_id=s05.DEFAULT_LEARNER_ID,
    ), static_root


def serve(*, receipt_path: Path, host: str, port: int) -> None:
    app, static_root = _application_from_receipt(receipt_path)
    server = s08.JourneyWorkbenchServer((host, port), app, static_root)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def readback(*, receipt_path: Path) -> dict[str, Any]:
    app, _ = _application_from_receipt(receipt_path)
    return {
        "unit_count": len(app.sequence_by_grammar),
        "lesson_count": len(app.lesson_bundles),
        "active_session": app.active_session_readback(),
        "progress": app.progress_readback(),
    }


def materialize(
    *,
    cp01_path: Path,
    cp04_path: Path,
    m03_path: Path,
    s08_path: Path,
    output_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    cp01_artifact = read_json(cp01_path, "cp01")
    cp04_artifact = read_json(cp04_path, "cp04")
    m03_artifact = read_json(m03_path, "m03")
    s08_receipt = read_json(s08_path, "s08")
    production_database, _ = _verify_s08(s08_receipt)
    admission = build_full_admission(
        cp01_artifact=cp01_artifact,
        cp04_artifact=cp04_artifact,
        m03_artifact=m03_artifact,
    )
    consumer = build_consumer(admission, m03_artifact)

    output_root = Path(output_root).resolve()
    runtime_root = output_root / "twentyfour_unit_runtime"
    if runtime_root.exists():
        shutil.rmtree(runtime_root)
    runtime_root.mkdir(parents=True, exist_ok=True)
    admission_path = runtime_root / "twentyfour_unit_admission.private.json"
    consumer_path = runtime_root / "twentyfour_unit_runtime_consumer.private.json"
    ui_root = runtime_root / "ui"
    static_root = runtime_root / "static"
    bundle_index_path = runtime_root / "bundle_index.private.json"
    write_json(admission_path, admission, private=True)
    write_json(consumer_path, consumer, private=True)
    with _patched_s07_identity():
        bundle_paths, rendered_asset_count = s07._render_bundles(
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
    s08._write_static(static_root)

    with explicit_sqlite_context_close():
        progress_before = s07.progress_state_digest(production_database)
        counts_before = s07._database_counts(production_database)
        staging_database = runtime_root / "twentyfour_unit_production_candidate.sqlite3"
        with _patched_s07_identity():
            counts_after = s07._migrate_clone(
                source_database=production_database,
                target_database=staging_database,
                consumer_path=consumer_path,
                consumer=consumer,
                bundle_paths=bundle_paths,
            )
        progress_candidate = s07.progress_state_digest(staging_database)
        if progress_candidate != progress_before:
            raise PopulationError("production_progress_state_changed_during_population")
        with sqlite3.connect(staging_database) as connection:
            metadata = {
                "s09_task_id": TASK_ID,
                "s09_schema_version": SCHEMA_VERSION,
                "s09_validation_status": PASS_STATUS,
                "s09_populated_unit_count": "24",
                "s09_nonaudio_item_count": str(EXPECTED_ITEM_COUNT),
                "mastery_write_enabled": "false",
                "a2_session_enabled": "false",
                "learner_release_approved": "false",
            }
            connection.executemany(
                "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)", metadata.items()
            )
            connection.commit()
        canary_database = runtime_root / "unit24_runtime_canary.sqlite3"
        with _patched_s07_identity():
            canary = s07._run_new_unit_canary(
                database_path=staging_database,
                bundle_index_path=bundle_index_path,
                second_unit=admission["admitted_units"][-1],
                canary_database=canary_database,
            )
        backup_database = runtime_root / "production_before_s09_population.sqlite3"
        shutil.copy2(production_database, backup_database)
        try:
            os.replace(staging_database, production_database)
        except OSError as exc:
            raise PopulationError(f"production_database_atomic_replace_failed:{exc}") from exc
        progress_after = s07.progress_state_digest(production_database)
        if progress_after != progress_before:
            try:
                os.replace(backup_database, production_database)
            except OSError:
                pass
            raise PopulationError("production_progress_state_changed_after_atomic_replace")
        try:
            backup_database.unlink()
        except OSError:
            pass

    if counts_after["lesson_count"] != 72 or counts_after["asset_count"] != EXPECTED_ITEM_COUNT:
        raise PopulationError("runtime_population_count_invalid")
    if counts_after["response_contract_count"] != EXPECTED_ITEM_COUNT:
        raise PopulationError("response_contract_population_count_invalid")
    if counts_after["capture_enabled_contract_count"] != 192:
        raise PopulationError("capture_enabled_contract_count_invalid")
    if counts_after["speaking_capture_enabled_count"] != 0 or counts_after["listening_lesson_count"] != 0:
        raise PopulationError("audio_or_speaking_capture_boundary_invalid")

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
            "s08_sha256": s08.digest(s08_receipt),
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
        "population_summary": deepcopy(admission["population_summary"]),
        "runtime_summary": {
            "populated_unit_count": 24,
            "populated_lesson_count": counts_after["lesson_count"],
            "populated_asset_count": counts_after["asset_count"],
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
            "first_three_unit_identity_preserved": True,
        },
        "unit24_runtime_canary": {
            **canary,
            "canary_unit_sequence_index": 24,
        },
        "learner_surface": {
            "s08_journey_surface_reused": True,
            "active_session_readback": True,
            "resume_after_restart": True,
            "abandon_active_session": True,
            "navigation_locked_while_active": True,
            "twentyfour_unit_navigation": True,
            "progress_readback": True,
        },
        "capability_contract": {
            "existing_24_unit_curriculum_reused": True,
            "m03_complete_contract_items_reused": True,
            "s08_learner_journey_surface_reused": True,
            "m3_session_progress_authority_reused": True,
            "m5_renderer_authority_reused": True,
            "m6_response_scoring_authority_reused": True,
            "persistent_database_migrated_in_place": True,
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
            "scene_authority_complete": admission["population_summary"]["scene_authority_gap_unit_count"] == 0,
            "a2_unlocked": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    receipt = {**receipt_core, "artifact_sha256": s07.digest(receipt_core)}
    safe_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "release_profile": RELEASE_PROFILE,
        "population_summary": deepcopy(receipt_core["population_summary"]),
        "runtime_summary": deepcopy(receipt_core["runtime_summary"]),
        "migration_summary": {
            key: value
            for key, value in receipt_core["migration_summary"].items()
            if not key.startswith("progress_state_sha256")
        },
        "unit24_runtime_canary": deepcopy(receipt_core["unit24_runtime_canary"]),
        "learner_surface": deepcopy(receipt_core["learner_surface"]),
        "capability_contract": deepcopy(receipt_core["capability_contract"]),
        "product_status": PRODUCT_STATUS,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": s07.digest(safe_core)}
    s07.safe_scan(safe)
    return receipt, safe


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("materialize")
    build.add_argument("--cp01", type=Path, required=True)
    build.add_argument("--cp04", type=Path, required=True)
    build.add_argument("--m03", type=Path, required=True)
    build.add_argument("--s08", type=Path, required=True)
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
            s08_path=args.s08,
            output_root=args.output.parent,
        )
        from ulga.validators.validate_a1fs_online_v1_s09_twentyfour_unit_production_population import validate_outputs

        validation = validate_outputs(
            receipt=receipt,
            safe_report=safe,
            output_root=args.output.parent,
            cp01_path=args.cp01,
            cp04_path=args.cp04,
            m03_path=args.m03,
            s08_path=args.s08,
        )
        if validation["error_count"]:
            raise PopulationError("validation_failed:" + "|".join(validation["errors"]))
        write_json(args.output, receipt, private=True)
        write_json(args.report, safe)
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (
        PopulationError,
        s02.FirstUnitAdmissionError,
        s07.MultiUnitExpansionError,
        s08.JourneyQAError,
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
