import json
from pathlib import Path

from ulga.builders.build_learner_state_replay_prototype import (
    BASE_DIR,
    build_replay_projection,
    load_events,
    sort_events_for_replay,
    write_outputs,
)


FIXTURE_PATH = BASE_DIR / "tests" / "fixtures" / "ulga" / "learner_event_replay_prototype_events.json"
CANONICAL_LEARNER_STATE_PATH = BASE_DIR / "ulga" / "learner_state" / "learner_state.json"


def load_fixture_payload():
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_node(nodes, node_id, node_type):
    for node in nodes:
        if node["node_id"] == node_id and node["node_type"] == node_type:
            return node
    raise AssertionError(f"Missing node {node_type}:{node_id}")


def test_input_list_loading_works(tmp_path):
    payload = load_fixture_payload()
    input_path = tmp_path / "events_list.json"
    with input_path.open("w", encoding="utf-8") as handle:
        json.dump(payload["events"], handle)

    events = load_events(input_path)
    assert isinstance(events, list)
    assert len(events) == len(payload["events"])


def test_wrapper_object_loading_works():
    events = load_events(FIXTURE_PATH)
    assert isinstance(events, list)
    assert len(events) > 0


def test_deterministic_sorting_by_timestamp_event_id_and_input_index():
    events = [
        {"event_id": "evt_b", "occurred_at": "2026-06-18T10:00:00Z", "quality_flags": {"valid_event": True, "requires_review": False}},
        {"event_id": "evt_a", "occurred_at": "2026-06-18T10:00:00Z", "quality_flags": {"valid_event": True, "requires_review": False}},
        {"event_id": "evt_a", "occurred_at": "2026-06-18T10:00:00Z", "quality_flags": {"valid_event": True, "requires_review": False}},
        {"event_id": "evt_c", "occurred_at": "2026-06-18T09:59:59Z", "quality_flags": {"valid_event": True, "requires_review": False}},
    ]

    sorted_events = sort_events_for_replay(events)
    assert [event["event_id"] for event in sorted_events] == ["evt_c", "evt_a", "evt_a", "evt_b"]
    assert [event["input_index"] for event in sorted_events if event["event_id"] == "evt_a"] == [1, 2]


def test_quarantined_events_are_excluded():
    projection = build_replay_projection(load_events(FIXTURE_PATH))
    node_ids = {node["node_id"] for node in projection["learner_state_projection"]["nodes"]}
    assert "vocab:orange" not in node_ids
    assert projection["summary"]["input_summary"]["events_excluded_quarantine"] == 1


def test_invalid_producer_marked_events_are_excluded():
    projection = build_replay_projection(load_events(FIXTURE_PATH))
    node_ids = {node["node_id"] for node in projection["learner_state_projection"]["nodes"]}
    assert "vocab:grape" not in node_ids
    assert projection["summary"]["input_summary"]["events_excluded_invalid"] == 1


def test_exposure_only_node_becomes_seen_not_functional_or_mastered():
    projection = build_replay_projection(load_events(FIXTURE_PATH))
    node = get_node(projection["learner_state_projection"]["nodes"], "vocab:apple", "vocabulary")
    assert node["exposure"]["count"] == 1
    assert node["practice"]["attempt_count"] == 0
    assert node["assessment"]["attempt_count"] == 0
    assert node["mastery_projection"]["band"] == "seen"


def test_correct_practice_event_updates_practice_metrics():
    projection = build_replay_projection(load_events(FIXTURE_PATH))
    node = get_node(projection["learner_state_projection"]["nodes"], "vocab:banana", "vocabulary")
    assert node["practice"]["attempt_count"] == 2
    assert node["practice"]["first_try_correct_count"] == 1
    assert node["practice"]["correct_count"] == 1
    assert node["practice"]["success_rate"] == 0.5


def test_retry_event_updates_retry_and_reinforcement_metrics():
    projection = build_replay_projection(load_events(FIXTURE_PATH))
    node = get_node(projection["learner_state_projection"]["nodes"], "vocab:banana", "vocabulary")
    assert node["practice"]["retry_count"] >= 1
    assert node["reinforcement"]["retry_count"] >= 1
    assert node["reinforcement"]["incorrect_count"] >= 1


def test_hint_used_event_updates_hint_and_reinforcement_metrics():
    projection = build_replay_projection(load_events(FIXTURE_PATH))
    node = get_node(projection["learner_state_projection"]["nodes"], "vocab:banana", "vocabulary")
    assert node["practice"]["hint_count"] == 1
    assert node["reinforcement"]["hint_count"] == 1
    assert node["reinforcement"]["weak_node_signal_count"] >= 1


def test_assessment_attempt_updates_assessment_metrics():
    projection = build_replay_projection(load_events(FIXTURE_PATH))
    node = get_node(projection["learner_state_projection"]["nodes"], "vocab:banana", "vocabulary")
    assert node["assessment"]["attempt_count"] == 3
    assert node["assessment"]["score_total"] == 2.0
    assert node["assessment"]["max_score_total"] == 3.0
    assert node["assessment"]["retention_check_pass_count"] == 1
    assert node["assessment"]["retention_check_fail_count"] == 1


def test_failed_mastery_check_produces_review_needed():
    projection = build_replay_projection(load_events(FIXTURE_PATH))
    node = get_node(projection["learner_state_projection"]["nodes"], "vocab:banana", "vocabulary")
    assert node["mastery_projection"]["band"] == "review_needed"


def test_theme_node_does_not_receive_direct_mastery_score():
    projection = build_replay_projection(load_events(FIXTURE_PATH))
    node = get_node(projection["learner_state_projection"]["nodes"], "theme:a1_food_and_drink", "theme")
    assert node["mastery_projection"]["raw_score"] == 0.0
    assert node["mastery_projection"]["band"] == "seen"


def test_output_files_are_written_to_prototype_directory_only(tmp_path):
    projection = build_replay_projection(load_events(FIXTURE_PATH))
    output_dir = tmp_path / "prototype"
    report_path = tmp_path / "reports" / "summary.json"

    write_outputs(projection, output_dir, report_path)

    assert (output_dir / "learner_state_projection_prototype.json").exists()
    assert (output_dir / "mastery_graph_projection_prototype.json").exists()
    assert report_path.exists()
    assert not (tmp_path / "learner_state.json").exists()


def test_canonical_learner_state_is_not_created_or_modified_by_test(tmp_path):
    before_bytes = CANONICAL_LEARNER_STATE_PATH.read_bytes() if CANONICAL_LEARNER_STATE_PATH.exists() else None

    projection = build_replay_projection(load_events(FIXTURE_PATH))
    output_dir = tmp_path / "prototype"
    report_path = tmp_path / "reports" / "summary.json"
    write_outputs(projection, output_dir, report_path)

    after_bytes = CANONICAL_LEARNER_STATE_PATH.read_bytes() if CANONICAL_LEARNER_STATE_PATH.exists() else None
    assert before_bytes == after_bytes


def test_summary_report_includes_complete_idempotency_claimed_false(tmp_path):
    projection = build_replay_projection(load_events(FIXTURE_PATH))
    output_dir = tmp_path / "prototype"
    report_path = tmp_path / "reports" / "summary.json"
    write_outputs(projection, output_dir, report_path)

    with report_path.open("r", encoding="utf-8") as handle:
        report = json.load(handle)

    assert report["policy_summary"]["complete_idempotency_claimed"] is False
