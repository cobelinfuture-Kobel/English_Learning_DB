import json
import subprocess
import sys
from pathlib import Path

from ulga.builders.build_learner_state import build_learner_state_payload, load_json, parse_timestamp, run_build
from ulga.validators.validate_dialogue_exception_tightening import validate_dialogue_exception_tightening
from ulga.validators.validate_learner_state_guardrail_output import validate_guardrail_output
from ulga.validators.validate_learner_state_schema import validate_learner_state_collection


BASE_DIR = Path(__file__).resolve().parents[2]
BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_learner_state.py"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_dialogue_exception_tightening.py"
SAMPLE_EVENTS_PATH = BASE_DIR / "ulga" / "learner_state" / "sample_evidence_events.json"


def clone_sample_events():
    return json.loads(json.dumps(load_json(SAMPLE_EVENTS_PATH)))["events"]


def build_payload_from_events(events):
    return build_learner_state_payload(
        sorted(events, key=lambda event: (parse_timestamp(event["timestamp"]), event["event_id"])),
        parse_timestamp("2026-06-17T11:00:00Z"),
    )[0]


def get_record(payload, learner_id, node_id):
    return next(
        record
        for record in payload["learner_state_records"]
        if record["learner_id"] == learner_id and record["node_id"] == node_id
    )


def test_single_event_supporting_context_dialogue_capped_at_049():
    payload = build_payload_from_events(clone_sample_events())
    record = get_record(payload, "learner:cyndi", "dialogue:DIALOGUE_ORDERING_FOOD_A1_001")
    assert record["mastery_score"] == 0.49
    assert record["mastery_band"] == "practicing"


def test_single_event_primary_target_dialogue_still_allowed():
    events = clone_sample_events()
    events[1]["node_refs"] = [
        {
            "node_id": "dialogue:DIALOGUE_ORDERING_FOOD_A1_001",
            "node_type": "dialogue",
            "role": "primary_target",
            "weight": 1.0,
        }
    ]
    payload = build_payload_from_events(events)
    record = get_record(payload, "learner:cyndi", "dialogue:DIALOGUE_ORDERING_FOOD_A1_001")
    assert record["mastery_score"] == 0.62
    assert record["mastery_band"] == "functional"


def test_multi_event_dialogue_unaffected_by_single_event_ceiling():
    events = clone_sample_events()
    events[1]["node_refs"] = [
        {
            "node_id": "dialogue:DIALOGUE_ORDERING_FOOD_A1_001",
            "node_type": "dialogue",
            "role": "supporting_context",
            "weight": 0.35,
        }
    ]
    second_dialogue = json.loads(json.dumps(events[1]))
    second_dialogue["event_id"] = "event:dialogue_20260617_004"
    second_dialogue["timestamp"] = "2026-06-17T10:15:10Z"
    second_dialogue["processing_idempotency_key"] = "dialogue_session_20260617_004:turn_02"
    events.append(second_dialogue)
    payload = build_payload_from_events(events)
    record = get_record(payload, "learner:cyndi", "dialogue:DIALOGUE_ORDERING_FOOD_A1_001")
    assert record["exposure_count"] == 2
    assert record["mastery_score"] == 0.62
    assert record["mastery_band"] == "functional"


def test_s9c_validation_still_passes(tmp_path):
    output_path = tmp_path / "learner_state.json"
    summary_path = tmp_path / "summary.json"
    guardrail_path = tmp_path / "guardrail.json"
    dialogue_path = tmp_path / "dialogue.json"
    payload, _ = run_build(
        output_path=output_path,
        summary_path=summary_path,
        guardrail_summary_path=guardrail_path,
        dialogue_tightening_summary_path=dialogue_path,
    )
    validate_learner_state_collection(payload)


def test_guardrail_validator_still_passes(tmp_path):
    output_path = tmp_path / "learner_state.json"
    summary_path = tmp_path / "summary.json"
    guardrail_path = tmp_path / "guardrail.json"
    dialogue_path = tmp_path / "dialogue.json"
    run_build(
        output_path=output_path,
        summary_path=summary_path,
        guardrail_summary_path=guardrail_path,
        dialogue_tightening_summary_path=dialogue_path,
    )
    validate_guardrail_output(learner_state_path=output_path, guardrail_summary_path=guardrail_path)
    validate_dialogue_exception_tightening(learner_state_path=output_path, summary_path=dialogue_path)


def test_output_deterministic(tmp_path):
    paths_one = [tmp_path / "one_state.json", tmp_path / "one_summary.json", tmp_path / "one_guardrail.json", tmp_path / "one_dialogue.json"]
    paths_two = [tmp_path / "two_state.json", tmp_path / "two_summary.json", tmp_path / "two_guardrail.json", tmp_path / "two_dialogue.json"]
    payload_one, summary_one = run_build(
        output_path=paths_one[0],
        summary_path=paths_one[1],
        guardrail_summary_path=paths_one[2],
        dialogue_tightening_summary_path=paths_one[3],
    )
    payload_two, summary_two = run_build(
        output_path=paths_two[0],
        summary_path=paths_two[1],
        guardrail_summary_path=paths_two[2],
        dialogue_tightening_summary_path=paths_two[3],
    )
    assert payload_one == payload_two
    assert summary_one == summary_two
    assert load_json(paths_one[2]) == load_json(paths_two[2])
    assert load_json(paths_one[3]) == load_json(paths_two[3])


def test_builder_cli_writes_dialogue_tightening_summary():
    result = subprocess.run(
        [sys.executable, str(BUILDER_PATH)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "dialogue_exception_tightening_summary.json" in result.stdout


def test_dialogue_tightening_validator_cli_passes():
    result = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout
