import subprocess
import sys
from pathlib import Path

from ulga.builders.build_learner_state import (
    DEFAULT_GUARDRAIL_SUMMARY_PATH,
    build_learner_state_payload,
    load_json,
    parse_timestamp,
    run_build,
)
from ulga.validators.validate_learner_state_guardrail_output import validate_guardrail_output
from ulga.validators.validate_learner_state_schema import validate_learner_state_collection


BASE_DIR = Path(__file__).resolve().parents[2]
BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_learner_state.py"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_learner_state_guardrail_output.py"


def build_sample_payload():
    events = load_json(BASE_DIR / "ulga" / "learner_state" / "sample_evidence_events.json")["events"]
    return build_learner_state_payload(
        sorted(events, key=lambda event: (parse_timestamp(event["timestamp"]), event["event_id"])),
        parse_timestamp("2026-06-17T11:00:00Z"),
    )[0]


def get_record_map(payload):
    return {(record["learner_id"], record["node_id"]): record for record in payload["learner_state_records"]}


def test_coverage_signal_cannot_exceed_024():
    record = get_record_map(build_sample_payload())[("learner:james", "theme:a1_daily_life_and_routines")]
    assert record["mastery_score"] <= 0.24


def test_review_signal_cannot_exceed_024():
    record = get_record_map(build_sample_payload())[("learner:james", "assessment:SHORT_WRITING_CHECK_A2_001")]
    assert record["mastery_score"] <= 0.24


def test_diagnostic_signal_cannot_exceed_049():
    record = get_record_map(build_sample_payload())[("learner:james", "morphology:word_family_read")]
    assert record["mastery_score"] <= 0.49


def test_supporting_context_cannot_exceed_069():
    record = get_record_map(build_sample_payload())[("learner:james", "sentence_pattern:PATTERN_NODE_000014")]
    assert record["mastery_score"] <= 0.69


def test_single_event_non_primary_cannot_exceed_049():
    record = get_record_map(build_sample_payload())[("learner:james", "skill:writing_revision")]
    assert record["mastery_score"] <= 0.49


def test_theme_cannot_exceed_049():
    record = get_record_map(build_sample_payload())[("learner:james", "theme:a1_daily_life_and_routines")]
    assert record["mastery_score"] <= 0.49


def test_morphology_cannot_exceed_049():
    record = get_record_map(build_sample_payload())[("learner:james", "morphology:word_family_read")]
    assert record["mastery_score"] <= 0.49


def test_assessment_cannot_exceed_049():
    record = get_record_map(build_sample_payload())[("learner:james", "assessment:SHORT_WRITING_CHECK_A2_001")]
    assert record["mastery_score"] <= 0.49


def test_mastered_requires_threshold():
    record = get_record_map(build_sample_payload())[("learner:james", "sentence_pattern:PATTERN_NODE_000014")]
    assert record["mastery_band"] != "mastered"


def test_automatic_requires_threshold():
    assert all(record["mastery_band"] != "automatic" for record in build_sample_payload()["learner_state_records"])


def test_s9c_validator_still_passes(tmp_path):
    output_path = tmp_path / "learner_state.json"
    summary_path = tmp_path / "summary.json"
    guardrail_summary_path = tmp_path / "guardrail_summary.json"
    payload, _ = run_build(output_path=output_path, summary_path=summary_path, guardrail_summary_path=guardrail_summary_path)
    validate_learner_state_collection(payload)


def test_learner_isolation_preserved(tmp_path):
    output_path = tmp_path / "learner_state.json"
    summary_path = tmp_path / "summary.json"
    guardrail_summary_path = tmp_path / "guardrail_summary.json"
    payload, _ = run_build(output_path=output_path, summary_path=summary_path, guardrail_summary_path=guardrail_summary_path)
    james_nodes = {record["node_id"] for record in payload["learner_state_records"] if record["learner_id"] == "learner:james"}
    cyndi_nodes = {record["node_id"] for record in payload["learner_state_records"] if record["learner_id"] == "learner:cyndi"}
    assert james_nodes.isdisjoint(cyndi_nodes)


def test_output_deterministic(tmp_path):
    first_output = tmp_path / "one.json"
    first_summary = tmp_path / "one_summary.json"
    first_guardrail = tmp_path / "one_guardrail.json"
    second_output = tmp_path / "two.json"
    second_summary = tmp_path / "two_summary.json"
    second_guardrail = tmp_path / "two_guardrail.json"
    payload_one, summary_one = run_build(output_path=first_output, summary_path=first_summary, guardrail_summary_path=first_guardrail)
    payload_two, summary_two = run_build(output_path=second_output, summary_path=second_summary, guardrail_summary_path=second_guardrail)
    assert payload_one == payload_two
    assert summary_one == summary_two
    assert load_json(first_guardrail) == load_json(second_guardrail)


def test_guardrail_validator_passes(tmp_path):
    output_path = tmp_path / "learner_state.json"
    summary_path = tmp_path / "summary.json"
    guardrail_summary_path = tmp_path / "guardrail_summary.json"
    run_build(output_path=output_path, summary_path=summary_path, guardrail_summary_path=guardrail_summary_path)
    validate_guardrail_output(learner_state_path=output_path, guardrail_summary_path=guardrail_summary_path)


def test_builder_cli_writes_guardrail_summary():
    result = subprocess.run(
        [sys.executable, str(BUILDER_PATH)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout
    assert DEFAULT_GUARDRAIL_SUMMARY_PATH.exists()


def test_guardrail_validator_cli_passes():
    result = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout
