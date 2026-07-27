#!/usr/bin/env python3
"""Accept the complete S09 24-unit runtime as a private no-audio release candidate.

S10 executes the existing S09 learner surface through real loopback HTTP requests on
an isolated database clone. It proves bootstrap, static delivery, response scoring,
restart/resume, Unit 24 access, Speaking submission blocking, and progress readback.
It does not author curriculum/content, mutate production progress, enable audio,
write mastery, unlock A2, or allow public-network binding.
"""
from __future__ import annotations

import argparse
import http.client
import json
import shutil
import sqlite3
import sys
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_online_v1_s09_twentyfour_unit_production_population as s09  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Executes the existing S09 24-unit learner runtime through loopback HTTP on an isolated "
    "database clone and records release-candidate acceptance evidence. It creates no curriculum, "
    "learner content, answers, audio, mastery, A2 unlock, public delivery, or parallel runtime."
)

PROGRAM_ID = "A1FS-ONLINE-V1"
TASK_ID = "A1FS-ONLINE-V1-S10_TwentyFourUnitPrivateReleaseCandidateHTTPAcceptance_NoAudio"
SCHEMA_VERSION = "a1fs.online.v1.s10.private_release_candidate_http_acceptance.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_S10_PRIVATE_RELEASE_CANDIDATE_HTTP_ACCEPTED"
PRODUCT_STATUS = "PRIVATE_TWENTYFOUR_UNIT_NONAUDIO_RELEASE_CANDIDATE_HTTP_ACCEPTED_NOT_PUBLIC"
RELEASE_PROFILE = "ONLINE_V1_AUDIO_DEFERRED"
NEXT_SHORT_STEP = "A1FS-ONLINE-V1-S11_SecureAuthenticatedOnlineReleaseBoundary_NoAudio"

CANARY_LEARNER_ID = "A1FS_ONLINE_V1_S10_HTTP_CANARY"
CANARY_SUBJECT_KEY = "A1FS_ONLINE_V1_S10_PRIVATE_SLOT"
READING_SESSION_ID = "A1FS_ONLINE_V1_S10_SESSION:UNIT01:READING"
READING_ATTEMPT_ID = "A1FS_ONLINE_V1_S10_ATTEMPT:UNIT01:READING:FAIL"
WRITING_SESSION_ID = "A1FS_ONLINE_V1_S10_SESSION:UNIT24:WRITING"
WRITING_ATTEMPT_ID = "A1FS_ONLINE_V1_S10_ATTEMPT:UNIT24:WRITING:PASS"
SPEAKING_SESSION_ID = "A1FS_ONLINE_V1_S10_SESSION:UNIT24:SPEAKING"

FORBIDDEN_SAFE_KEYS = {
    "accepted_texts", "accepted_sequence", "answer", "answer_contract", "answer_key",
    "asset_key", "database_path", "display_label", "learner_id", "learner_payload",
    "private_scoring_contract", "private_subject_digest", "prompt", "prompt_text",
    "response", "rubric", "scoring_contract", "session_id", "subject_key",
}


class ReleaseCandidateError(ValueError):
    """Fail-closed S10 acceptance or release-candidate error."""


def digest(value: Any) -> str:
    return s09.s07.digest(value)


def file_digest(path: Path) -> str:
    return s09.s07.file_digest(path)


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseCandidateError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise ReleaseCandidateError(f"{code}_not_object")
    return value


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    s09.write_json(Path(path), value, private=private)


def safe_scan(value: Any) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in FORBIDDEN_SAFE_KEYS:
                    raise ReleaseCandidateError(f"private_content_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(value)


def _verify_s09(
    receipt_path: Path,
) -> tuple[dict[str, Any], Path, Path, Path, dict[str, dict[str, Any]], dict[str, int]]:
    receipt_path = Path(receipt_path).resolve()
    receipt = read_json(receipt_path, "s09_receipt")
    identity = (
        receipt.get("task_id"), receipt.get("schema_version"),
        receipt.get("validation_status"), receipt.get("product_status"),
        receipt.get("stop_reason"),
    )
    expected = (s09.TASK_ID, s09.SCHEMA_VERSION, s09.PASS_STATUS, s09.PRODUCT_STATUS, "NONE")
    if identity != expected:
        raise ReleaseCandidateError("s09_receipt_contract_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest(core):
        raise ReleaseCandidateError("s09_receipt_digest_invalid")

    population = receipt.get("population_summary", {})
    runtime = receipt.get("runtime_summary", {})
    required_counts = {
        "populated_unit_count": 24,
        "admitted_nonaudio_item_count": 264,
        "runtime_lesson_count": 72,
        "listening_item_count": 0,
        "speaking_assessment_item_count": 0,
    }
    for key, expected_value in required_counts.items():
        if population.get(key) != expected_value:
            raise ReleaseCandidateError(f"s09_population_count_invalid:{key}")
    if (
        runtime.get("populated_unit_count") != 24
        or runtime.get("populated_lesson_count") != 72
        or runtime.get("populated_asset_count") != 264
        or runtime.get("speaking_capture_enabled_count") != 0
        or runtime.get("listening_runtime_item_count") != 0
        or runtime.get("audio_runtime_asset_count") != 0
    ):
        raise ReleaseCandidateError("s09_runtime_summary_invalid")

    outputs = receipt.get("runtime_outputs", {})
    database = Path(str(outputs.get("database_path") or "")).resolve()
    bundle_index = Path(str(outputs.get("bundle_index_path") or "")).resolve()
    static_root = Path(str(outputs.get("static_root") or "")).resolve()
    if not database.is_file() or not bundle_index.is_file() or not static_root.is_dir():
        raise ReleaseCandidateError("s09_runtime_outputs_missing")
    bundles, sequence_by_grammar = s09.s07._load_bundle_index(bundle_index)
    if len(sequence_by_grammar) != 24 or len(bundles) != 72:
        raise ReleaseCandidateError("s09_runtime_denominator_invalid")
    if sum(len(bundle["assets"]) for bundle in bundles.values()) != 264:
        raise ReleaseCandidateError("s09_runtime_asset_denominator_invalid")
    return receipt, database, bundle_index, static_root, bundles, sequence_by_grammar


def _http(
    port: int,
    method: str,
    path: str,
    payload: Mapping[str, Any] | None = None,
    *,
    expected_status: int = 200,
    expect_json: bool = True,
) -> Any:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read()
    finally:
        connection.close()
    if response.status != expected_status:
        raise ReleaseCandidateError(
            f"http_status_invalid:{method}:{path}:{response.status}:{expected_status}"
        )
    if not expect_json:
        return raw.decode("utf-8")
    try:
        value = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ReleaseCandidateError(f"http_json_invalid:{method}:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ReleaseCandidateError(f"http_json_not_object:{method}:{path}")
    return value


def _app(
    *,
    database_path: Path,
    bundles: Mapping[str, Mapping[str, Any]],
    sequence_by_grammar: Mapping[str, int],
) -> s09.PopulationWorkbenchApplication:
    return s09.PopulationWorkbenchApplication(
        database_path=database_path,
        bundles=bundles,
        sequence_by_grammar=sequence_by_grammar,
        default_learner_id=CANARY_LEARNER_ID,
    )


def _start_server(
    app: s09.PopulationWorkbenchApplication,
    static_root: Path,
) -> tuple[s09.s08.JourneyWorkbenchServer, threading.Thread, int]:
    server = s09.s08.JourneyWorkbenchServer(("127.0.0.1", 0), app, static_root)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, int(server.server_address[1])


def _stop_server(server: s09.s08.JourneyWorkbenchServer, thread: threading.Thread) -> None:
    server.shutdown()
    server.server_close()
    thread.join(timeout=10)
    if thread.is_alive():
        raise ReleaseCandidateError("http_server_thread_did_not_stop")


def _lane(bootstrap: Mapping[str, Any], *, sequence_index: int, skill: str) -> Mapping[str, Any]:
    units = bootstrap.get("units")
    if not isinstance(units, list):
        raise ReleaseCandidateError("bootstrap_units_invalid")
    for unit in units:
        if not isinstance(unit, Mapping) or unit.get("sequence_index") != sequence_index:
            continue
        for lane in unit.get("lanes", []):
            if isinstance(lane, Mapping) and str(lane.get("skill") or "").upper() == skill.upper():
                return lane
    raise ReleaseCandidateError(f"bootstrap_lane_missing:{sequence_index}:{skill}")


def _validate_bootstrap(bootstrap: Mapping[str, Any]) -> dict[str, int]:
    if (
        bootstrap.get("task_id") != s09.TASK_ID
        or bootstrap.get("validation_status") != s09.PASS_STATUS
        or bootstrap.get("product_status") != s09.PRODUCT_STATUS
        or bootstrap.get("audio_enabled") is not False
        or bootstrap.get("speaking_capture_enabled") is not False
        or bootstrap.get("unit_count") != 24
    ):
        raise ReleaseCandidateError("http_bootstrap_identity_or_boundary_invalid")
    units = bootstrap.get("units")
    if not isinstance(units, list) or len(units) != 24:
        raise ReleaseCandidateError("http_bootstrap_unit_count_invalid")
    sequences = [unit.get("sequence_index") for unit in units if isinstance(unit, Mapping)]
    if sequences != list(range(1, 25)):
        raise ReleaseCandidateError("http_bootstrap_sequence_invalid")
    lesson_count = 0
    asset_count = 0
    for unit in units:
        lanes = unit.get("lanes") if isinstance(unit, Mapping) else None
        if not isinstance(lanes, list) or {str(row.get("skill")) for row in lanes} != {
            "READING", "WRITING", "SPEAKING"
        }:
            raise ReleaseCandidateError("http_bootstrap_lane_set_invalid")
        lesson_count += len(lanes)
        asset_count += sum(int(row.get("asset_count") or 0) for row in lanes)
    if lesson_count != 72 or asset_count != 264:
        raise ReleaseCandidateError("http_bootstrap_runtime_denominator_invalid")
    return {"unit_count": 24, "lesson_count": 72, "asset_count": 264}


def _validate_progress(progress: Mapping[str, Any]) -> dict[str, int]:
    summary = progress.get("summary")
    if not isinstance(summary, Mapping):
        raise ReleaseCandidateError("http_progress_summary_invalid")
    expected = {
        "session_count": 3,
        "completed_session_count": 2,
        "active_session_count": 0,
        "abandoned_session_count": 1,
        "exposure_count": 3,
        "attempt_count": 2,
        "auto_pass_count": 1,
        "auto_fail_count": 1,
        "pending_human_review_count": 0,
        "unit_count_with_sessions": 2,
        "skill_count_with_sessions": 3,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise ReleaseCandidateError(
                f"http_progress_count_invalid:{key}:{summary.get(key)}:{value}"
            )
    if progress.get("last_event_hash_present") is not True:
        raise ReleaseCandidateError("http_progress_event_chain_missing")
    return dict(expected)


def _run_http_acceptance(
    *,
    canary_database: Path,
    static_root: Path,
    bundles: Mapping[str, Mapping[str, Any]],
    sequence_by_grammar: Mapping[str, int],
) -> dict[str, Any]:
    app = _app(
        database_path=canary_database,
        bundles=bundles,
        sequence_by_grammar=sequence_by_grammar,
    )
    app.enroll(
        learner_id=CANARY_LEARNER_ID,
        display_label="S10 HTTP Acceptance Canary",
        subject_key=CANARY_SUBJECT_KEY,
        at="2026-01-11T00:00:00Z",
    )
    non_loopback_blocked = False
    try:
        s09.s08.JourneyWorkbenchServer(("0.0.0.0", 0), app, static_root)
    except s09.s08.JourneyQAError as exc:
        non_loopback_blocked = str(exc).startswith("non_loopback_host_forbidden:")
    if not non_loopback_blocked:
        raise ReleaseCandidateError("non_loopback_binding_not_blocked")

    server, thread, port = _start_server(app, static_root)
    try:
        health = _http(port, "GET", "/api/health")
        if health != {"status": "PASS", "loopback_only": True, "audio_enabled": False}:
            raise ReleaseCandidateError("http_health_contract_invalid")
        index_html = _http(port, "GET", "/index.html", expect_json=False)
        app_js = _http(port, "GET", "/app.js", expect_json=False)
        if "A1FS 多單元學習旅程工作台" not in index_html or "navigationLocked" not in app_js:
            raise ReleaseCandidateError("http_static_release_surface_invalid")
        bootstrap = _http(port, "GET", "/api/bootstrap")
        denominators = _validate_bootstrap(bootstrap)

        reading_lane = _lane(bootstrap, sequence_index=1, skill="READING")
        reading_asset, wrong_response = s09.s08._deterministic_response(
            canary_database, reading_lane["assets"], should_pass=False
        )
        reading = _http(port, "POST", "/api/session/start", {
            "learner_id": CANARY_LEARNER_ID,
            "lesson_id": reading_lane["lesson_id"],
            "session_id": READING_SESSION_ID,
            "at": "2026-01-11T00:00:10Z",
        })
        reading = _http(port, "POST", "/api/exposure", {
            "session_id": READING_SESSION_ID,
            "asset_key": reading_asset,
            "expected_session_version": reading["session_version"],
            "at": "2026-01-11T00:00:20Z",
        })
        reading_scored = _http(port, "POST", "/api/response", {
            "learner_id": CANARY_LEARNER_ID,
            "session_id": READING_SESSION_ID,
            "asset_key": reading_asset,
            "response": wrong_response,
            "expected_session_version": reading["session_version"],
            "attempt_id": READING_ATTEMPT_ID,
            "submitted_at": "2026-01-11T00:00:30Z",
        })
        if reading_scored.get("outcome") != "AUTO_FAIL":
            raise ReleaseCandidateError("unit01_reading_failure_path_not_proven")
    finally:
        _stop_server(server, thread)

    app = _app(
        database_path=canary_database,
        bundles=bundles,
        sequence_by_grammar=sequence_by_grammar,
    )
    server, thread, port = _start_server(app, static_root)
    try:
        resumed = _http(port, "GET", "/api/session/active")
        if (
            resumed.get("active") is not True
            or resumed.get("session", {}).get("session_id") != READING_SESSION_ID
            or resumed.get("session", {}).get("session_version") != reading_scored.get("session_version")
        ):
            raise ReleaseCandidateError("http_restart_resume_invalid")
        reading_done = _http(port, "POST", "/api/session/complete", {
            "session_id": READING_SESSION_ID,
            "expected_session_version": resumed["session"]["session_version"],
            "at": "2026-01-11T00:00:40Z",
        })
        if reading_done.get("session_state") != "COMPLETED":
            raise ReleaseCandidateError("unit01_reading_completion_failed")

        bootstrap = _http(port, "GET", "/api/bootstrap")
        writing_lane = _lane(bootstrap, sequence_index=24, skill="WRITING")
        writing_asset, correct_response = s09.s08._deterministic_response(
            canary_database, writing_lane["assets"], should_pass=True
        )
        writing = _http(port, "POST", "/api/session/start", {
            "learner_id": CANARY_LEARNER_ID,
            "lesson_id": writing_lane["lesson_id"],
            "session_id": WRITING_SESSION_ID,
            "at": "2026-01-11T00:01:00Z",
        })
        writing = _http(port, "POST", "/api/exposure", {
            "session_id": WRITING_SESSION_ID,
            "asset_key": writing_asset,
            "expected_session_version": writing["session_version"],
            "at": "2026-01-11T00:01:10Z",
        })
        writing_scored = _http(port, "POST", "/api/response", {
            "learner_id": CANARY_LEARNER_ID,
            "session_id": WRITING_SESSION_ID,
            "asset_key": writing_asset,
            "response": correct_response,
            "expected_session_version": writing["session_version"],
            "attempt_id": WRITING_ATTEMPT_ID,
            "submitted_at": "2026-01-11T00:01:20Z",
        })
        if writing_scored.get("outcome") != "AUTO_PASS":
            raise ReleaseCandidateError("unit24_writing_success_path_not_proven")
        writing_done = _http(port, "POST", "/api/session/complete", {
            "session_id": WRITING_SESSION_ID,
            "expected_session_version": writing_scored["session_version"],
            "at": "2026-01-11T00:01:30Z",
        })
        if writing_done.get("session_state") != "COMPLETED":
            raise ReleaseCandidateError("unit24_writing_completion_failed")

        speaking_lane = _lane(bootstrap, sequence_index=24, skill="SPEAKING")
        speaking_asset = str(speaking_lane["assets"][0]["asset_key"])
        speaking = _http(port, "POST", "/api/session/start", {
            "learner_id": CANARY_LEARNER_ID,
            "lesson_id": speaking_lane["lesson_id"],
            "session_id": SPEAKING_SESSION_ID,
            "at": "2026-01-11T00:02:00Z",
        })
        speaking = _http(port, "POST", "/api/exposure", {
            "session_id": SPEAKING_SESSION_ID,
            "asset_key": speaking_asset,
            "expected_session_version": speaking["session_version"],
            "at": "2026-01-11T00:02:10Z",
        })
        speaking_error = _http(port, "POST", "/api/response", {
            "learner_id": CANARY_LEARNER_ID,
            "session_id": SPEAKING_SESSION_ID,
            "asset_key": speaking_asset,
            "response": "synthetic speaking text must remain blocked",
            "expected_session_version": speaking["session_version"],
            "attempt_id": "A1FS_ONLINE_V1_S10_FORBIDDEN_SPEAKING_ATTEMPT",
        }, expected_status=400)
        if speaking_error.get("error") != "response_capture_not_enabled_for_asset":
            raise ReleaseCandidateError("speaking_submission_block_reason_invalid")
        speaking_done = _http(port, "POST", "/api/session/abandon", {
            "session_id": SPEAKING_SESSION_ID,
            "expected_session_version": speaking["session_version"],
            "at": "2026-01-11T00:02:20Z",
        })
        if speaking_done.get("session_state") != "ABANDONED":
            raise ReleaseCandidateError("unit24_speaking_abandon_failed")
        if _http(port, "GET", "/api/session/active") != {"active": False}:
            raise ReleaseCandidateError("http_final_active_session_not_clear")
        progress = _http(port, "GET", "/api/progress")
        progress_counts = _validate_progress(progress)
    finally:
        _stop_server(server, thread)

    return {
        **denominators,
        **progress_counts,
        "health_endpoint_pass": True,
        "static_index_served": True,
        "static_application_served": True,
        "server_process_start_count": 2,
        "restart_resume_pass": True,
        "unit01_reading_auto_fail": True,
        "unit24_writing_auto_pass": True,
        "unit24_speaking_submission_blocked": True,
        "unit24_speaking_abandoned": True,
        "non_loopback_binding_blocked": True,
        "loopback_only": True,
    }


def materialize(*, s09_receipt_path: Path, output_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    s09_receipt_path = Path(s09_receipt_path).resolve()
    s09_receipt, production_database, bundle_index, static_root, bundles, sequence = _verify_s09(
        s09_receipt_path
    )
    output_root = Path(output_root).resolve()
    candidate_root = output_root / "private_release_candidate_http_acceptance"
    if candidate_root.exists():
        shutil.rmtree(candidate_root)
    candidate_root.mkdir(parents=True, exist_ok=True)
    canary_database = candidate_root / "s10_http_acceptance_canary.sqlite3"
    shutil.copy2(production_database, canary_database)

    production_sha_before = file_digest(production_database)
    acceptance = _run_http_acceptance(
        canary_database=canary_database,
        static_root=static_root,
        bundles=bundles,
        sequence_by_grammar=sequence,
    )
    production_sha_after = file_digest(production_database)
    if production_sha_before != production_sha_after:
        raise ReleaseCandidateError("production_database_mutated_by_http_acceptance")

    receipt_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "release_profile": RELEASE_PROFILE,
        "source_identity": {
            "s09_sha256": digest(s09_receipt),
            "production_database_sha256": production_sha_before,
        },
        "runtime_outputs": {
            "root": str(candidate_root),
            "source_s09_receipt_path": str(s09_receipt_path),
            "source_database_path": str(production_database),
            "source_bundle_index_path": str(bundle_index),
            "source_static_root": str(static_root),
            "canary_database_path": str(canary_database),
        },
        "release_candidate_summary": acceptance,
        "production_safety": {
            "database_sha256_before": production_sha_before,
            "database_sha256_after": production_sha_after,
            "production_database_unchanged": True,
            "http_acceptance_executed_on_isolated_clone": True,
            "real_learner_progress_mutated_by_canary": False,
        },
        "release_candidate_entrypoint": {
            "serve_command_available": True,
            "readback_command_available": True,
            "default_host": "127.0.0.1",
            "default_port": 8765,
            "public_network_binding_allowed": False,
        },
        "capability_contract": {
            "s09_twentyfour_unit_runtime_reused": True,
            "s08_learner_journey_surface_reused": True,
            "m3_session_progress_authority_reused": True,
            "m5_renderer_authority_reused": True,
            "m6_response_scoring_authority_reused": True,
            "real_http_acceptance_executed": True,
            "restart_resume_proven_over_http": True,
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
            "public_online_delivery_claimed": False,
            "real_learner_attempt_claimed": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
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
        "release_candidate_summary": deepcopy(acceptance),
        "production_safety": {
            "production_database_unchanged": True,
            "http_acceptance_executed_on_isolated_clone": True,
            "real_learner_progress_mutated_by_canary": False,
        },
        "release_candidate_entrypoint": deepcopy(receipt_core["release_candidate_entrypoint"]),
        "capability_contract": deepcopy(receipt_core["capability_contract"]),
        "product_status": PRODUCT_STATUS,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    safe_scan(safe)
    return receipt, safe


def _source_s09_from_s10(receipt_path: Path) -> Path:
    receipt = read_json(receipt_path, "s10_receipt")
    identity = (
        receipt.get("task_id"), receipt.get("schema_version"),
        receipt.get("validation_status"), receipt.get("product_status"), receipt.get("stop_reason"),
    )
    if identity != (TASK_ID, SCHEMA_VERSION, PASS_STATUS, PRODUCT_STATUS, "NONE"):
        raise ReleaseCandidateError("s10_receipt_contract_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest(core):
        raise ReleaseCandidateError("s10_receipt_digest_invalid")
    source = Path(str(receipt.get("runtime_outputs", {}).get("source_s09_receipt_path") or "")).resolve()
    _verify_s09(source)
    return source


def serve(*, receipt_path: Path, host: str, port: int) -> None:
    s09.serve(receipt_path=_source_s09_from_s10(receipt_path), host=host, port=port)


def readback(*, receipt_path: Path) -> dict[str, Any]:
    source = _source_s09_from_s10(receipt_path)
    receipt = read_json(receipt_path, "s10_receipt")
    return {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "release_candidate_summary": deepcopy(receipt["release_candidate_summary"]),
        "runtime": s09.readback(receipt_path=source),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("materialize")
    build.add_argument("--s09", type=Path, required=True)
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
        receipt, safe = materialize(s09_receipt_path=args.s09, output_root=args.output.parent)
        from ulga.validators.validate_a1fs_online_v1_s10_private_release_candidate_http_acceptance import validate_outputs
        validation = validate_outputs(
            receipt=receipt,
            safe_report=safe,
            output_root=args.output.parent,
            s09_path=args.s09,
        )
        if validation["error_count"]:
            raise ReleaseCandidateError("validation_failed:" + "|".join(validation["errors"]))
        write_json(args.output, receipt, private=True)
        write_json(args.report, safe)
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (
        ReleaseCandidateError,
        s09.PopulationError,
        s09.s08.JourneyQAError,
        s09.s07.MultiUnitExpansionError,
        s09.s05.PersistenceError,
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
