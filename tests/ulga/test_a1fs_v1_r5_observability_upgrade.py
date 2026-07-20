from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5
from ulga.builders import build_a1fs_v1_r6_gpt_diagnostic_package_controlled_recommendation_gate as r6
from ulga.validators import validate_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5_validator

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _r5_fixture(tmp_path: Path):
    module = _load(
        "r5_observability_fixture",
        REPO_ROOT / "tests/ulga/test_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector.py",
    )
    database, runtime = module._runtime_fixture(tmp_path)
    module._complete_core_session(runtime)
    return database, runtime


def test_future_runtime_event_and_exports_preserve_observability(tmp_path: Path) -> None:
    database, runtime = _r5_fixture(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        events = connection.execute(
            "SELECT payload_json FROM edge_runtime_events "
            "WHERE event_type='EDGE_RESPONSE_CAPTURED' ORDER BY event_seq"
        ).fetchall()
    assert len(events) == 2
    for event in events:
        payload = json.loads(event["payload_json"])
        reference = r5.validate_rendered_stimulus_reference(
            payload["learner_rendered_stimulus_reference"]
        )
        assert reference["capture_status"] == "CAPTURED"
        assert payload["telemetry_status"] == "CAPTURED_RUNTIME"
        assert payload["response_time_ms"] > 0

    exported = runtime.export_evidence(
        learner_id="learner",
        output_root=tmp_path / "evidence",
        exported_at="2026-07-19T00:30:00Z",
    )
    package = json.loads(Path(exported["package_path"]).read_text(encoding="utf-8"))
    safe = json.loads(Path(exported["safe_summary_path"]).read_text(encoding="utf-8"))
    assert all(row["telemetry_status"] == "CAPTURED_RUNTIME" for row in package["entries"])
    assert all(
        row["learner_rendered_stimulus_reference"]["capture_status"] == "CAPTURED"
        for row in package["entries"]
    )
    assert all(
        "learner_rendered_stimulus_reference" in row for row in safe["entries"]
    )
    db_result = r5_validator.validate_database(database)
    export_result = r5_validator.validate_exports(
        Path(exported["package_path"]),
        Path(exported["safe_summary_path"]),
        Path(exported["jsonl_path"]),
    )
    assert db_result["error_count"] == 0, db_result["errors"]
    assert export_result["error_count"] == 0, export_result["errors"]


def test_legacy_runtime_event_replay_is_preserved_and_marked(tmp_path: Path) -> None:
    database, runtime = _r5_fixture(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        previous = "0" * 64
        rows = connection.execute(
            "SELECT * FROM edge_runtime_events ORDER BY event_seq"
        ).fetchall()
        for row in rows:
            payload = json.loads(row["payload_json"])
            if row["event_type"] == "EDGE_RESPONSE_CAPTURED":
                payload.pop("learner_rendered_stimulus_reference", None)
                payload.pop("telemetry_status", None)
            core = {
                "event_id": row["event_id"],
                "learner_id": row["learner_id"],
                "session_id": row["session_id"],
                "event_type": row["event_type"],
                "event_at": row["event_at"],
                "payload": payload,
            }
            event_hash = r5.digest(previous + r5.canonical(core))
            connection.execute(
                "UPDATE edge_runtime_events SET payload_json=?,previous_hash=?,event_hash=? "
                "WHERE event_seq=?",
                (r5.canonical(payload), previous, event_hash, row["event_seq"]),
            )
            previous = event_hash
        connection.commit()

    db_result = r5_validator.validate_database(database)
    assert db_result["error_count"] == 0, db_result["errors"]
    exported = runtime.export_evidence(
        learner_id="learner",
        output_root=tmp_path / "legacy-evidence",
        exported_at="2026-07-19T00:31:00Z",
    )
    package = json.loads(Path(exported["package_path"]).read_text(encoding="utf-8"))
    assert all(
        row["telemetry_status"] == "CAPTURED_RUNTIME_PRE_STIMULUS_REFERENCE"
        for row in package["entries"]
    )
    assert all(
        row["learner_rendered_stimulus_reference"]["capture_status"]
        == "LEGACY_UNAVAILABLE"
        for row in package["entries"]
    )
    export_result = r5_validator.validate_exports(
        Path(exported["package_path"]),
        Path(exported["safe_summary_path"]),
        Path(exported["jsonl_path"]),
    )
    assert export_result["error_count"] == 0, export_result["errors"]


def test_r6_request_remains_compatible_with_observability_fields(tmp_path: Path) -> None:
    module = _load(
        "r6_observability_fixture",
        REPO_ROOT / "tests/ulga/test_a1fs_v1_r6_gpt_diagnostic_package_controlled_recommendation_gate.py",
    )
    sources = module._sources(tmp_path)
    package = json.loads(sources["package"].read_text(encoding="utf-8"))
    safe = json.loads(sources["safe"].read_text(encoding="utf-8"))
    bank = json.loads(sources["bank"].read_text(encoding="utf-8"))
    reference = r5.rendered_stimulus_reference(bank["items"][0])
    valid_attempt = next(
        row for row in package["entries"] if row["validity_status"] == "VALID"
    )
    valid_attempt["learner_rendered_stimulus_reference"] = reference
    valid_attempt["telemetry_status"] = "CAPTURED_RUNTIME"
    safe_attempt = next(
        row for row in safe["entries"] if row["attempt_id"] == valid_attempt["attempt_id"]
    )
    safe_attempt["learner_rendered_stimulus_reference"] = reference
    safe_attempt["telemetry_status"] = "CAPTURED_RUNTIME"
    package["entries_sha256"] = r6.digest(package["entries"])
    package_core = {key: value for key, value in package.items() if key != "package_sha256"}
    package["package_sha256"] = r6.digest(package_core)
    safe["entries_sha256"] = r6.digest(safe["entries"])
    safe_core = {key: value for key, value in safe.items() if key != "summary_sha256"}
    safe["summary_sha256"] = r6.digest(safe_core)
    sources["package"].write_text(json.dumps(package), encoding="utf-8")
    sources["safe"].write_text(json.dumps(safe), encoding="utf-8")

    request, safe_request = r6.build_request(
        evidence_package_path=sources["package"],
        evidence_safe_path=sources["safe"],
        bank_path=sources["bank"],
        coverage_path=sources["coverage"],
    )
    assert request["analysis_window"]["representative_evidence_count"] == 1
    assert request["representative_evidence"][0]["response_time_ms"] == 3500
    assert safe_request["claim_boundaries"]["raw_response_included"] is False
