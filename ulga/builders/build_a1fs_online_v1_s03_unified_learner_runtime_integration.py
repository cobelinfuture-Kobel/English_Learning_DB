#!/usr/bin/env python3
"""Connect the S02 non-audio unit to the existing M3/M5/M6 learner runtime.

S02 remains the unit and item admission authority. This adapter creates no new
curriculum selection logic and no second session, renderer, or scoring engine.
It projects the admitted Reading, Writing, and display-only Speaking lanes into
an M2-compatible private consumer, then executes the existing M3 state store,
M5 renderer, and M6 response-contract initialization as a deterministic canary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1_a1plus_shared_item_contract as m03  # noqa: E402
from ulga.builders import build_a1fs_online_v1_s02_first_nonaudio_unit_admission as s02  # noqa: E402
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2  # noqa: E402
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3  # noqa: E402
from ulga.builders import build_a1fs_v1_m4_lesson_planner_selection_a2_lock as m4  # noqa: E402
from ulga.builders import build_a1fs_v1_m5_four_skill_renderer_learner_ui as m5  # noqa: E402
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6  # noqa: E402
from ulga.builders import build_a1fs_v1_shared_learner_stimulus_contract_renderer as stimulus  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Projects already-admitted S02 item contracts into existing M3/M5/M6 runtime interfaces; "
    "no curriculum, learner content, answer, or scoring authority is authored."
)

PROGRAM_ID = s02.PROGRAM_ID
TASK_ID = "A1FS-ONLINE-V1-S03_UnifiedLearnerRuntimeIntegration_NoAudio"
SCHEMA_VERSION = "a1fs.online.v1.s03.unified_learner_runtime.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_S03_UNIFIED_LEARNER_RUNTIME_CONNECTED"
NEXT_SHORT_STEP = "A1FS-ONLINE-V1-S04_PrivateOnlineLearnerWorkbenchExecution_NoAudio"
CANARY_LEARNER_ID = "A1FS_ONLINE_V1_CANARY"
CANARY_DISPLAY_LABEL = "A1FS Online V1 Canary"
SKILL_ORDER = ("reading", "writing", "speaking")
SKILL_UPPER = {skill: skill.upper() for skill in SKILL_ORDER}
MODE_MAP = {
    "DETERMINISTIC_OPTION": "EXACT_OPTION",
    "DETERMINISTIC_SEQUENCE": "EXACT_SEQUENCE",
    "DETERMINISTIC_NORMALIZED_TEXT": "NORMALIZED_TEXT",
    "FEATURE_RUBRIC_CANDIDATE": "FEATURE_RUBRIC",
}
FORBIDDEN_SAFE_KEYS = {
    "accepted_texts", "accepted_sequence", "answer", "answer_contract", "answer_key",
    "context", "learner_payload", "model_text", "model_texts", "payload", "private_scoring_contract",
    "prompt", "prompt_contract", "prompt_text", "response", "rubric", "scoring_contract",
}


class RuntimeIntegrationError(ValueError):
    """Fail-closed S03 integration error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeIntegrationError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeIntegrationError(f"{code}_not_object")
    return value


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    if private:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


def _verify_s02(artifact: Mapping[str, Any]) -> Mapping[str, Any]:
    if (
        artifact.get("task_id") != s02.TASK_ID
        or artifact.get("schema_version") != s02.SCHEMA_VERSION
        or artifact.get("validation_status") != s02.PASS_STATUS
        or artifact.get("scope") != "A1_A1_PLUS_ONLY"
        or artifact.get("release_profile") != s02.RELEASE_PROFILE
        or artifact.get("stop_reason") != "NONE"
    ):
        raise RuntimeIntegrationError("s02_contract_invalid")
    core = {key: value for key, value in artifact.items() if key != "artifact_sha256"}
    if artifact.get("artifact_sha256") != s02.digest(core):
        raise RuntimeIntegrationError("s02_artifact_digest_invalid")
    selection = artifact.get("selection_contract", {})
    if (
        selection.get("course_container") != "EXISTING_24_CANONICAL_UNITS_ONLY"
        or selection.get("new_unit_creation_allowed") is not False
        or selection.get("listening_without_playable_audio_allowed") is not False
        or selection.get("speaking_capture_or_scoring_claim_allowed") is not False
    ):
        raise RuntimeIntegrationError("s02_selection_boundary_invalid")
    unit = artifact.get("selected_unit")
    if not isinstance(unit, Mapping) or unit.get("unit_admission_status") != "ADMITTED_NONAUDIO_FIRST_PRODUCTION_UNIT":
        raise RuntimeIntegrationError("s02_selected_unit_invalid")
    lanes = unit.get("admitted_lanes")
    if not isinstance(lanes, Mapping) or set(lanes) != set(SKILL_ORDER):
        raise RuntimeIntegrationError("s02_admitted_lane_set_invalid")
    if unit.get("deferred_lanes", {}).get("listening", {}).get("item_ids") != []:
        raise RuntimeIntegrationError("s02_listening_not_deferred")
    if artifact.get("admission_summary", {}).get("listening_item_count") != 0:
        raise RuntimeIntegrationError("s02_listening_count_not_zero")
    if artifact.get("admission_summary", {}).get("speaking_assessment_item_count") != 0:
        raise RuntimeIntegrationError("s02_speaking_assessment_count_not_zero")
    return unit


def _verify_m03(artifact: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if (
        artifact.get("task_id") != m03.TASK_ID
        or artifact.get("schema_version") != m03.SCHEMA_VERSION
        or artifact.get("scope") != "A1_A1_PLUS_ONLY"
        or artifact.get("stop_reason") != "NONE"
    ):
        raise RuntimeIntegrationError("m03_contract_invalid")
    rows = artifact.get("shared_items")
    if not isinstance(rows, list) or len(rows) != 384:
        raise RuntimeIntegrationError("m03_item_denominator_invalid")
    index: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise RuntimeIntegrationError("m03_item_not_object")
        item_id = str(row.get("shared_item_id") or "")
        if not item_id or item_id in index:
            raise RuntimeIntegrationError(f"m03_item_identity_invalid:{item_id}")
        index[item_id] = row
    return index


def _strings(value: Any) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [str(row).strip() for row in value if isinstance(row, str) and row.strip()]
    return []


def _accepted_texts(answer: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    sources = [answer]
    answer_key = answer.get("answer_key")
    if isinstance(answer_key, Mapping):
        sources.append(answer_key)
    for source in sources:
        for key in ("accepted_texts", "correct_answers", "correct_answer", "answer"):
            values.extend(_strings(source.get(key)))
    return list(dict.fromkeys(values))


def _accepted_sequence(answer: Mapping[str, Any]) -> list[str]:
    sources = [answer]
    answer_key = answer.get("answer_key")
    if isinstance(answer_key, Mapping):
        sources.append(answer_key)
    for source in sources:
        for key in ("correct_token_sequence", "correct_morphology_parts", "accepted_sequence"):
            values = _strings(source.get(key))
            if values:
                return values
    return []


def _private_scoring(item: Mapping[str, Any], *, capture_enabled: bool) -> dict[str, Any]:
    source = item.get("scoring_contract")
    answer = item.get("answer_contract")
    if not isinstance(source, Mapping) or not isinstance(answer, Mapping):
        raise RuntimeIntegrationError(f"item_scoring_contract_missing:{item.get('shared_item_id')}")
    source_mode = str(source.get("scoring_mode") or "")
    mode = MODE_MAP.get(source_mode)
    if mode is None:
        raise RuntimeIntegrationError(f"item_scoring_mode_unsupported:{item.get('shared_item_id')}:{source_mode}")
    contract: dict[str, Any] = {
        "scoring_mode": mode,
        "case_insensitive": True,
        "punctuation_tolerance": True,
        "human_review_fallback": mode == "FEATURE_RUBRIC",
    }
    if mode in {"EXACT_OPTION", "NORMALIZED_TEXT"}:
        accepted = _accepted_texts(answer)
        if capture_enabled and not accepted:
            raise RuntimeIntegrationError(f"item_accepted_texts_missing:{item.get('shared_item_id')}")
        contract["accepted_texts"] = accepted
    elif mode == "EXACT_SEQUENCE":
        sequence = _accepted_sequence(answer)
        if capture_enabled and not sequence:
            raise RuntimeIntegrationError(f"item_accepted_sequence_missing:{item.get('shared_item_id')}")
        contract["accepted_sequence"] = sequence
    else:
        criteria = _strings(source.get("required_evidence")) or ["teacher_review_required"]
        contract["rubric"] = {criterion: {"required": True} for criterion in criteria}
    return contract


def _learner_payload(item: Mapping[str, Any], *, capture_enabled: bool) -> dict[str, Any]:
    prompt = item.get("prompt_contract")
    response = item.get("response_contract")
    if not isinstance(prompt, Mapping) or not isinstance(response, Mapping):
        raise RuntimeIntegrationError(f"item_prompt_or_response_contract_missing:{item.get('shared_item_id')}")
    prompt_text = str(prompt.get("prompt_text") or "").strip()
    if not prompt_text:
        raise RuntimeIntegrationError(f"item_prompt_missing:{item.get('shared_item_id')}")
    learner: dict[str, Any] = {
        "prompt": prompt_text,
        "response_mode": str(response.get("response_mode") or "text_response"),
        "response_capture_enabled": capture_enabled,
        "private_scoring_contract": _private_scoring(item, capture_enabled=capture_enabled),
        "source_binding": {
            "shared_item_id": str(item["shared_item_id"]),
            "learning_unit_id": str(item["learning_unit_id"]),
            "grammar_unit_id": str(item["grammar_unit_id"]),
            "item_role": str(item["item_role"]),
        },
    }
    if "context" in prompt:
        learner["context"] = deepcopy(prompt["context"])
    options = response.get("options") or item.get("answer_contract", {}).get("options")
    if options:
        learner["options"] = deepcopy(options)
    if response.get("token_sequence"):
        learner["supplied_tokens"] = deepcopy(response["token_sequence"])
    if response.get("morphology_parts"):
        learner["supplied_morphemes"] = deepcopy(response["morphology_parts"])
    return stimulus.ensure_learner_contract(
        item_id=str(item["shared_item_id"]),
        task_type=str(item.get("task_type") or "runtime_item"),
        learner=learner,
        scoring={"scoring_may_use_hidden_information": False},
        media_payload_state="NOT_REQUIRED",
    )


def _runtime_asset(item: Mapping[str, Any], *, lesson_id: str, lane: str) -> dict[str, Any]:
    practice = item.get("item_role") == "practice"
    capture_enabled = lane in {"reading", "writing"}
    if lane == "speaking" and not practice:
        raise RuntimeIntegrationError(f"speaking_assessment_not_allowed:{item.get('shared_item_id')}")
    token = digest(str(item["shared_item_id"]))[:24]
    role = "PRD" if practice else "CHK"
    payload = _learner_payload(item, capture_enabled=capture_enabled)
    if lane == "speaking":
        payload["delivery_mode"] = "ORAL_PRACTICE_CARD_NO_CAPTURE"
        payload["response_capture_enabled"] = False
        payload["audio_capture_required"] = False
        payload["recording_capture_required"] = False
        payload["evidence_policy"] = "NO_SCORING_NO_MASTERY_EVIDENCE"
    asset_key = f"S03:{lane.upper()}:{token}"
    return {
        "asset_id": asset_key,
        "asset_key": asset_key,
        "lesson_id": lesson_id,
        "skill": SKILL_UPPER[lane],
        "level": "A1",
        "role": role,
        "payload": payload,
        "content_digest": digest(payload),
        "release_scope": "PRIVATE_INTERNAL_A1FS_ONLINE_V1_S03",
    }


def build_runtime_consumer(
    s02_artifact: Mapping[str, Any],
    m03_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    unit = _verify_s02(s02_artifact)
    item_index = _verify_m03(m03_artifact)
    grammar_id = str(unit.get("grammar_unit_id") or "")
    learning_id = str(unit.get("learning_unit_id") or "")
    if not grammar_id or not learning_id:
        raise RuntimeIntegrationError("selected_unit_identity_missing")
    level = "A1+" if str(unit.get("internal_stage") or "").upper() in {"A1+", "A1_PLUS"} else "A1"
    assets: list[dict[str, Any]] = []
    catalog: list[dict[str, Any]] = []
    admitted_seen: set[str] = set()
    for lane in SKILL_ORDER:
        lane_contract = unit["admitted_lanes"][lane]
        item_ids = lane_contract.get("item_ids")
        if not isinstance(item_ids, list) or not item_ids:
            raise RuntimeIntegrationError(f"admitted_lane_empty:{lane}")
        lesson_id = f"A1FS_ONLINE_V1:{grammar_id}:{lane.upper()}"
        lane_assets: list[dict[str, Any]] = []
        for item_id in item_ids:
            item_id = str(item_id)
            if item_id in admitted_seen:
                raise RuntimeIntegrationError(f"admitted_item_duplicate:{item_id}")
            admitted_seen.add(item_id)
            item = item_index.get(item_id)
            if item is None:
                raise RuntimeIntegrationError(f"admitted_item_not_in_m03:{item_id}")
            if item.get("grammar_unit_id") != grammar_id or item.get("learning_unit_id") != learning_id:
                raise RuntimeIntegrationError(f"admitted_item_unit_binding_invalid:{item_id}")
            if item.get("skill") != lane:
                raise RuntimeIntegrationError(f"admitted_item_skill_binding_invalid:{lane}:{item_id}")
            lane_assets.append(_runtime_asset(item, lesson_id=lesson_id, lane=lane))
        assets.extend(lane_assets)
        catalog.append({
            "lesson_id": lesson_id,
            "lesson_node_id": f"RUNTIME_PROJECTION:{lane.upper()}:{grammar_id}",
            "skill": SKILL_UPPER[lane],
            "level": level,
            "asset_keys": [row["asset_key"] for row in lane_assets],
            "roles": list(dict.fromkeys(row["role"] for row in lane_assets)),
            "requirement_node_ids": list(unit.get("canonical_egp_row_ids", [])),
            "release_scope": "PRIVATE_INTERNAL_A1FS_ONLINE_V1_S03",
            "runtime_projection": {
                "source_learning_unit_id": learning_id,
                "source_grammar_unit_id": grammar_id,
                "selection_authority_task_id": s02.TASK_ID,
                "new_curriculum_unit_created": False,
            },
        })
    expected = int(s02_artifact["admission_summary"]["admitted_nonaudio_item_count"])
    if len(assets) != expected or len(admitted_seen) != expected:
        raise RuntimeIntegrationError("runtime_asset_count_mismatch")
    consumer = {
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
            "max_query_limit": 100,
            "filter_fields": ["skill", "level", "lesson_id", "role"],
        },
        "s03_runtime_projection": {
            "task_id": TASK_ID,
            "schema_version": SCHEMA_VERSION,
            "source_s02_sha256": digest(s02_artifact),
            "source_m03_sha256": digest(m03_artifact),
            "source_learning_unit_id": learning_id,
            "source_grammar_unit_id": grammar_id,
            "selection_authority": "S02_ALREADY_SELECTED_CANONICAL_UNIT",
            "m4_new_curriculum_selection_performed": False,
            "runtime_engine_authorities": {
                "session_state": m3.TASK_ID,
                "learner_renderer": m5.TASK_ID,
                "response_scoring": m6.TASK_ID,
            },
        },
        "claim_boundaries": {
            "new_curriculum_created": False,
            "parallel_runtime_created": False,
            "m4_planner_selection_claimed": False,
            "public_online_delivery_claimed": False,
            "real_learner_attempt_claimed": False,
            "listening_complete": False,
            "speaking_capture_complete": False,
            "mastery_claimed": False,
            "a2_unlocked": False,
        },
        "errors": [],
        "next_short_step": NEXT_SHORT_STEP,
    }
    return consumer


def _plan_for_lesson(lesson: Mapping[str, Any]) -> dict[str, Any]:
    skill = str(lesson["skill"])
    return {
        "task_id": m4.TASK_ID,
        "schema_version": m4.SCHEMA_VERSION,
        "validation_status": m4.STATUS,
        "plan_id": f"A1FS_ONLINE_V1_S03_PLAN:{skill}",
        "learner_id": CANARY_LEARNER_ID,
        "plan_status": "PLAN_LEARNING_LESSON",
        "selected_lesson": {
            key: deepcopy(lesson[key])
            for key in ("lesson_id", "lesson_node_id", "skill", "level", "roles", "requirement_node_ids")
        },
        "rationale": {
            "reason": "S02_ALREADY_SELECTED_CANONICAL_UNIT_RUNTIME_LANE_BINDING",
            "selection_authority_task_id": s02.TASK_ID,
            "m4_new_selection_performed": False,
        },
        "a2_lock": {
            "a2_lock_state": "LOCKED",
            "mastery_authority_valid": False,
            "required_mastery_count": 0,
            "mastered_required_count": 0,
            "missing_mastery_count": 0,
            "missing_mastery_node_ids": [],
            "unlock_rule": "A2_OUT_OF_SCOPE_FOR_S03",
            "a2_payload_access_granted": False,
            "a2_session_start_granted": False,
        },
        "a2_payload_included": False,
        "a2_session_started": False,
        "s03_task_id": TASK_ID,
        "next_short_step": NEXT_SHORT_STEP,
    }


def _database_counts(database_path: Path) -> dict[str, int]:
    with sqlite3.connect(database_path) as connection:
        queries = {
            "profile_count": "SELECT COUNT(*) FROM learner_profiles",
            "session_count": "SELECT COUNT(*) FROM learning_sessions",
            "completed_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE session_state='COMPLETED'",
            "state_event_count": "SELECT COUNT(*) FROM state_events",
            "lesson_count": "SELECT COUNT(*) FROM lesson_catalog",
            "asset_count": "SELECT COUNT(*) FROM lesson_assets",
            "response_contract_count": "SELECT COUNT(*) FROM response_contracts",
            "capture_enabled_contract_count": "SELECT COUNT(*) FROM response_contracts WHERE capture_enabled=1",
            "speaking_capture_enabled_count": "SELECT COUNT(*) FROM response_contracts WHERE skill='SPEAKING' AND capture_enabled=1",
        }
        return {name: int(connection.execute(sql).fetchone()[0]) for name, sql in queries.items()}


def materialize_runtime(
    *,
    s02_artifact: Mapping[str, Any],
    m03_artifact: Mapping[str, Any],
    output_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    output_root = Path(output_root)
    runtime_root = output_root / "runtime"
    if runtime_root.exists():
        shutil.rmtree(runtime_root)
    runtime_root.mkdir(parents=True, exist_ok=True)

    consumer = build_runtime_consumer(s02_artifact, m03_artifact)
    consumer_path = runtime_root / "unified_runtime_consumer.private.json"
    write_json(consumer_path, consumer, private=True)

    database_path = runtime_root / "learner_state.sqlite3"
    store = m3.LearnerStateStore(database_path)
    m3_init = store.initialize(consumer_path)
    store.create_profile(
        learner_id=CANARY_LEARNER_ID,
        display_label=CANARY_DISPLAY_LABEL,
        locale="zh-TW",
        timezone_name="Asia/Taipei",
        at="2026-01-01T00:00:00Z",
    )

    lane_receipts: list[dict[str, Any]] = []
    capture_contract_total = 0
    for lane_index, lesson in enumerate(consumer["lesson_catalog"], start=1):
        skill = str(lesson["skill"])
        plan = _plan_for_lesson(lesson)
        plan_path = runtime_root / "plans" / f"{skill.casefold()}.plan.private.json"
        write_json(plan_path, plan, private=True)
        ui_root = runtime_root / "ui" / skill.casefold()
        ui_manifest = m5.build_ui(consumer_path=consumer_path, plan_path=plan_path, output_root=ui_root)
        bundle_path = ui_root / "lesson.private.json"
        m6_result = m6.ResponseEvidenceStore(database_path).initialize(
            consumer_path=consumer_path,
            lesson_bundle_path=bundle_path,
        )
        capture_contract_total += int(m6_result["capture_contract_count"])

        session_id = f"A1FS_ONLINE_V1_S03_SESSION:{skill}"
        session = store.start_session(
            learner_id=CANARY_LEARNER_ID,
            lesson_id=str(lesson["lesson_id"]),
            session_id=session_id,
            at=f"2026-01-01T00:0{lane_index}:00Z",
        )
        version = int(session["session_version"])
        for asset_key in lesson["asset_keys"]:
            session = store.record_exposure(
                session_id=session_id,
                asset_key=str(asset_key),
                expected_session_version=version,
                at=f"2026-01-01T00:0{lane_index}:10Z",
            )
            version = int(session["session_version"])
        session = store.end_session(
            session_id=session_id,
            outcome="COMPLETED",
            expected_session_version=version,
            at=f"2026-01-01T00:0{lane_index}:20Z",
        )
        lane_receipts.append({
            "skill": skill,
            "lesson_id": lesson["lesson_id"],
            "asset_count": len(lesson["asset_keys"]),
            "session_state": session["session_state"],
            "session_version": session["session_version"],
            "m5_manifest_path": str(ui_root / "manifest.json"),
            "m5_asset_count": ui_manifest["asset_count"],
            "m6_capture_contract_count": m6_result["capture_contract_count"],
        })

    counts = _database_counts(database_path)
    receipt_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "release_profile": s02.RELEASE_PROFILE,
        "source_identity": {
            "s02_task_id": s02.TASK_ID,
            "s02_sha256": digest(s02_artifact),
            "m03_task_id": m03.TASK_ID,
            "m03_sha256": digest(m03_artifact),
        },
        "selected_unit": {
            "learning_unit_id": s02_artifact["selected_unit"]["learning_unit_id"],
            "grammar_unit_id": s02_artifact["selected_unit"]["grammar_unit_id"],
            "sequence_index": s02_artifact["selected_unit"]["sequence_index"],
        },
        "runtime_outputs": {
            "consumer_path": str(consumer_path),
            "database_path": str(database_path),
            "ui_root": str(runtime_root / "ui"),
        },
        "runtime_summary": {
            "runtime_lesson_count": len(consumer["lesson_catalog"]),
            "runtime_asset_count": len(consumer["asset_records"]),
            "m3_profile_count": counts["profile_count"],
            "m3_session_count": counts["session_count"],
            "m3_completed_session_count": counts["completed_session_count"],
            "m3_exposure_event_count": len(consumer["asset_records"]),
            "m5_renderer_bundle_count": len(lane_receipts),
            "m6_response_contract_count": counts["response_contract_count"],
            "m6_capture_enabled_contract_count": counts["capture_enabled_contract_count"],
            "speaking_capture_enabled_count": counts["speaking_capture_enabled_count"],
            "listening_runtime_item_count": 0,
            "audio_runtime_asset_count": 0,
        },
        "lane_receipts": lane_receipts,
        "capability_contract": {
            "s02_admission_authority_preserved": True,
            "m3_session_state_engine_reused": True,
            "m5_renderer_engine_reused": True,
            "m6_response_contract_engine_reused": True,
            "parallel_runtime_created": False,
            "m4_new_curriculum_selection_performed": False,
            "speaking_practice_display_only": True,
            "listening_deferred": True,
        },
        "product_status": "PRIVATE_RUNTIME_CONNECTED_NOT_PUBLIC_ONLINE",
        "claim_boundaries": {
            "public_online_delivery_claimed": False,
            "real_learner_attempt_claimed": False,
            "actual_response_submitted": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "listening_complete": False,
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
        "release_profile": s02.RELEASE_PROFILE,
        "selected_unit": dict(receipt_core["selected_unit"]),
        "runtime_summary": dict(receipt_core["runtime_summary"]),
        "capability_contract": dict(receipt_core["capability_contract"]),
        "product_status": receipt_core["product_status"],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    safe_scan(safe)
    return receipt, safe


def safe_scan(value: Any) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in FORBIDDEN_SAFE_KEYS:
                    raise RuntimeIntegrationError(f"private_content_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(value)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s02", type=Path, required=True)
    parser.add_argument("--m03", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        s02_artifact = read_json(args.s02, "s02")
        m03_artifact = read_json(args.m03, "m03")
        receipt, safe = materialize_runtime(
            s02_artifact=s02_artifact,
            m03_artifact=m03_artifact,
            output_root=args.output.parent,
        )
        write_json(args.output, receipt, private=True)
        from ulga.validators.validate_a1fs_online_v1_s03_unified_learner_runtime_integration import validate_outputs

        validation = validate_outputs(
            receipt=receipt,
            safe_report=safe,
            output_root=args.output.parent,
            s02_artifact=s02_artifact,
            m03_artifact=m03_artifact,
        )
        if validation["error_count"]:
            raise RuntimeIntegrationError("validation_failed:" + "|".join(validation["errors"]))
        write_json(args.report, safe)
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (
        RuntimeIntegrationError,
        stimulus.StimulusContractError,
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
