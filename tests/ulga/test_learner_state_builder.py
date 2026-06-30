import json
import subprocess
import sys
from pathlib import Path

import pytest

from ulga.builders.build_learner_state import (
    DEFAULT_INPUT_PATH,
    build_learner_state_payload,
    load_json,
    parse_timestamp,
    run_build,
)
from ulga.validators.validate_learner_state_builder_output import validate_builder_output
from ulga.validators.validate_learner_state_schema import validate_learner_state_collection


BASE_DIR = Path(__file__).resolve().parents[2]
BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_learner_state.py"
OUTPUT_PATH = BASE_DIR / "ulga" / "learner_state" / "learner_state.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "learner_state_builder_summary.json"


def clone_sample_events():
    return json.loads(json.dumps(load_json(DEFAULT_INPUT_PATH)))


def test_builder_creates_learner_state_json(tmp_path):
    output_path = tmp_path / "learner_state.json"
    summary_path = tmp_path / "summary.json"
    run_build(output_path=output_path, summary_path=summary_path)
    assert output_path.exists()


def test_builder_creates_summary_json(tmp_path):
    output_path = tmp_path / "learner_state.json"
    summary_path = tmp_path / "summary.json"
    run_build(output_path=output_path, summary_path=summary_path)
    assert summary_path.exists()


def test_output_validates_against_s9c_validator(tmp_path):
    output_path = tmp_path / "learner_state.json"
    summary_path = tmp_path / "summary.json"
    run_build(output_path=output_path, summary_path=summary_path)
    validate_learner_state_collection(load_json(output_path))


def test_duplicate_event_id_input_fails(tmp_path):
    payload = clone_sample_events()
    payload["events"][1]["event_id"] = payload["events"][0]["event_id"]
    input_path = tmp_path / "events.json"
    output_path = tmp_path / "learner_state.json"
    summary_path = tmp_path / "summary.json"
    input_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with pytest.raises(Exception, match="duplicate event_id"):
        run_build(input_path=input_path, output_path=output_path, summary_path=summary_path)


def test_duplicate_event_processing_idempotency_key_input_fails(tmp_path):
    payload = clone_sample_events()
    payload["events"][1]["processing_idempotency_key"] = payload["events"][0]["processing_idempotency_key"]
    input_path = tmp_path / "events.json"
    output_path = tmp_path / "learner_state.json"
    summary_path = tmp_path / "summary.json"
    input_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with pytest.raises(Exception, match="duplicate processing_idempotency_key"):
        run_build(input_path=input_path, output_path=output_path, summary_path=summary_path)


def test_output_has_one_record_per_learner_node_pair(tmp_path):
    output_path = tmp_path / "learner_state.json"
    summary_path = tmp_path / "summary.json"
    payload, _ = run_build(output_path=output_path, summary_path=summary_path)
    pairs = [(record["learner_id"], record["node_id"]) for record in payload["learner_state_records"]]
    assert len(pairs) == len(set(pairs))


def test_exposure_count_uses_raw_event_count(tmp_path):
    output_path = tmp_path / "learner_state.json"
    summary_path = tmp_path / "summary.json"
    payload, _ = run_build(output_path=output_path, summary_path=summary_path)
    record_map = {(record["learner_id"], record["node_id"]): record for record in payload["learner_state_records"]}
    assert record_map[("learner:james", "grammar:GRAMMAR_NODE_000123")]["exposure_count"] == 1
    assert record_map[("learner:cyndi", "chunk:SAFE_CHUNK_000321")]["exposure_count"] == 1


def test_correct_count_plus_incorrect_count_not_exceed_exposure_count(tmp_path):
    output_path = tmp_path / "learner_state.json"
    summary_path = tmp_path / "summary.json"
    payload, _ = run_build(output_path=output_path, summary_path=summary_path)
    for record in payload["learner_state_records"]:
        assert record["correct_count"] + record["incorrect_count"] <= record["exposure_count"]


def test_mastery_band_matches_mastery_score(tmp_path):
    output_path = tmp_path / "learner_state.json"
    summary_path = tmp_path / "summary.json"
    payload, _ = run_build(output_path=output_path, summary_path=summary_path)
    validate_learner_state_collection(payload)


def test_output_is_deterministic_across_repeated_runs(tmp_path):
    output_path_one = tmp_path / "learner_state_one.json"
    summary_path_one = tmp_path / "summary_one.json"
    output_path_two = tmp_path / "learner_state_two.json"
    summary_path_two = tmp_path / "summary_two.json"
    payload_one, summary_one = run_build(output_path=output_path_one, summary_path=summary_path_one)
    payload_two, summary_two = run_build(output_path=output_path_two, summary_path=summary_path_two)
    assert payload_one == payload_two
    assert summary_one == summary_two


def test_learner_james_and_learner_cyndi_remain_separated(tmp_path):
    output_path = tmp_path / "learner_state.json"
    summary_path = tmp_path / "summary.json"
    payload, _ = run_build(output_path=output_path, summary_path=summary_path)
    james_nodes = {record["node_id"] for record in payload["learner_state_records"] if record["learner_id"] == "learner:james"}
    cyndi_nodes = {record["node_id"] for record in payload["learner_state_records"] if record["learner_id"] == "learner:cyndi"}
    assert james_nodes
    assert cyndi_nodes
    assert james_nodes.isdisjoint(cyndi_nodes)


def test_no_candidate_ranking_or_planner_fields_appear_in_output(tmp_path):
    output_path = tmp_path / "learner_state.json"
    summary_path = tmp_path / "summary.json"
    payload, _ = run_build(output_path=output_path, summary_path=summary_path)
    forbidden_fields = {"candidate_ranking", "planner_decision", "lesson_recommendation", "scheduler_policy"}
    for record in payload["learner_state_records"]:
        assert forbidden_fields.isdisjoint(record.keys())


def test_builder_validator_script_passes(tmp_path):
    output_path = tmp_path / "learner_state.json"
    summary_path = tmp_path / "summary.json"
    run_build(output_path=output_path, summary_path=summary_path)
    validate_builder_output(learner_state_path=output_path, summary_path=summary_path)


def test_builder_script_passes():
    result = subprocess.run(
        [sys.executable, str(BUILDER_PATH)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout


def test_expected_build_timestamp_uses_latest_input_event():
    events = clone_sample_events()["events"]
    payload, summary, _ = build_learner_state_payload(
        sorted(events, key=lambda event: (parse_timestamp(event["timestamp"]), event["event_id"])),
        parse_timestamp("2026-06-17T11:00:00Z"),
    )
    assert summary["build_timestamp"] == "2026-06-17T11:00:00Z"
    assert {record["state_updated_at"] for record in payload["learner_state_records"]} == {"2026-06-17T11:00:00Z"}
