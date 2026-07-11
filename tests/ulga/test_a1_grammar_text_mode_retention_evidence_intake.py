from __future__ import annotations

import copy
import json
from pathlib import Path

from ulga.builders.build_a1_grammar_text_mode_evidence_projection_review_routing import (
    build_artifact as build_projection_artifact,
    validate_artifact as validate_projection_artifact,
)
from ulga.builders.build_a1_grammar_text_mode_private_pilot_evidence_intake import (
    INTAKE_PATH,
    normalize_and_validate,
)
from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import (
    build_and_validate_from_repo as build_package_source,
)
from ulga.builders.import_a1_grammar_text_mode_private_pilot_real_attempts import (
    IMPORT_SCHEMA_VERSION,
    REPO_ROOT,
    _private_path_error,
    build_evidence_payload,
)
from ulga.builders.import_a1_grammar_text_mode_retention_evidence import (
    NEXT_FINAL_MASTERY_TASK,
    NEXT_REVIEW_TASK,
    RETENTION_SCHEMA_VERSION,
    build_retention_artifact,
)


def package():
    artifact, report = build_package_source()
    assert report["validation_status"] == "PASS"
    return artifact


def template():
    return json.loads(Path(INTAKE_PATH).read_text(encoding="utf-8"))


def answer_text(item):
    answer_key = item.get("answer_key", {})
    canonical = answer_key.get("canonical_target")
    if isinstance(canonical, str) and canonical:
        return canonical
    accepted = answer_key.get("accepted_texts", [])
    if accepted:
        return accepted[0]
    gap = item.get("gap_spec", {}).get("accepted_missing_tokens", [])
    if gap:
        return gap[0]
    tokens = item.get("correct_token_sequence")
    if tokens:
        return " ".join(tokens)
    morphemes = item.get("correct_morphology_parts")
    if morphemes:
        return "".join(morphemes)
    raise AssertionError(f"No answer model for {item.get('item_id')}")


def baseline_bundle():
    source_package = package()
    first_unit = min(
        source_package["learning_units"],
        key=lambda unit: unit["sequence_index"],
    )
    item_index = {
        item["item_id"]: item
        for item in source_package["item_bank"]
    }
    item_ids = (
        list(first_unit["delivery_plan"]["practice_item_ids"])
        + list(first_unit["delivery_plan"]["assessment_item_ids"])
    )
    responses = [
        {
            "item_id": item_id,
            "response_text": answer_text(item_index[item_id]),
            "attempt_sequence": 1,
            "submitted_at": f"2026-07-01T08:{5 + index:02d}:00+08:00",
        }
        for index, item_id in enumerate(item_ids)
    ]
    source = {
        "import_schema_version": IMPORT_SCHEMA_VERSION,
        "session": {
            "session_id": "session:A1_BASELINE_001",
            "learner_ref": "learner:PRIVATE_001",
            "operator_ref": "operator:cobelinfuture-Kobel",
            "started_at": "2026-07-01T08:00:00+08:00",
            "completed_at": "2026-07-01T08:30:00+08:00",
            "evidence_source_ref": "local_private_pilot://A1_BASELINE_001",
        },
        "responses": responses,
    }
    evidence, import_report = build_evidence_payload(
        source,
        source_package,
        template(),
    )
    assert import_report["validation_status"] == "PASS"
    normalized, intake_report = normalize_and_validate(
        evidence,
        source_package,
    )
    assert intake_report["validation_status"] == "PASS"
    projection = build_projection_artifact(source_package, normalized)
    projection_report = validate_projection_artifact(
        projection,
        source_package,
        normalized,
    )
    assert projection_report["validation_status"] == "PASS"
    assert projection["coverage_summary"]["mastery_candidate_unit_count"] == 1
    return source_package, first_unit, item_index, normalized, projection


def retention_source(first_unit, item_index, *, reading_text=None):
    assessment_ids = list(first_unit["delivery_plan"]["assessment_item_ids"])
    responses = []
    for index, item_id in enumerate(assessment_ids):
        item = item_index[item_id]
        text = answer_text(item)
        if item.get("skill") == "reading" and reading_text is not None:
            text = reading_text
        responses.append(
            {
                "item_id": item_id,
                "response_text": text,
                "submitted_at": f"2026-07-02T09:0{5 + index}:00+08:00",
            }
        )
    return {
        "retention_schema_version": RETENTION_SCHEMA_VERSION,
        "baseline_session_id": "session:A1_BASELINE_001",
        "grammar_unit_ids": [first_unit["grammar_unit_id"]],
        "session": {
            "session_id": "session:A1_RETENTION_001",
            "learner_ref": "learner:PRIVATE_001",
            "operator_ref": "operator:cobelinfuture-Kobel",
            "started_at": "2026-07-02T09:00:00+08:00",
            "completed_at": "2026-07-02T09:15:00+08:00",
            "evidence_source_ref": "local_private_pilot://A1_RETENTION_001",
        },
        "responses": responses,
    }


def test_delayed_assessment_pair_confirms_retention_without_final_mastery():
    source_package, first_unit, item_index, baseline, projection = baseline_bundle()
    artifact, report = build_retention_artifact(
        retention_source(first_unit, item_index),
        source_package,
        baseline,
        projection,
        template(),
    )

    assert report["validation_status"] == "PASS"
    assert report["retention_status"] == (
        "RETENTION_CONFIRMED_PENDING_FINAL_MASTERY_PROJECTION"
    )
    assert report["next_task"] == NEXT_FINAL_MASTERY_TASK
    assert artifact["coverage_summary"]["selected_unit_count"] == 1
    assert artifact["coverage_summary"]["required_assessment_item_count"] == 2
    assert artifact["coverage_summary"]["accepted_retention_attempt_count"] == 2
    assert artifact["coverage_summary"]["confirmed_unit_count"] == 1
    assert artifact["coverage_summary"]["final_mastered_unit_count"] == 0
    assert artifact["coverage_summary"]["final_mastered_row_count"] == 0
    result = artifact["by_grammar_unit_id"][first_unit["grammar_unit_id"]]
    assert result["reading_assessment_pass"] is True
    assert result["writing_assessment_pass"] is True
    assert result["retention_confirmed"] is True
    assert result["final_mastery_status"] == "NOT_CLAIMED"
    assert result["persistent_learner_state_write"] is False
    assert artifact["claim_boundaries"]["actual_final_mastery_measured"] is False
    assert artifact["claim_boundaries"]["final_mastery_claimed"] is False


def test_retention_before_24_hours_fails_closed():
    source_package, first_unit, item_index, baseline, projection = baseline_bundle()
    source = retention_source(first_unit, item_index)
    source["session"]["started_at"] = "2026-07-01T09:00:00+08:00"
    source["session"]["completed_at"] = "2026-07-01T09:15:00+08:00"
    for index, record in enumerate(source["responses"]):
        record["submitted_at"] = f"2026-07-01T09:0{5 + index}:00+08:00"

    artifact, report = build_retention_artifact(
        source,
        source_package,
        baseline,
        projection,
        template(),
    )

    assert report["validation_status"] == "FAIL"
    assert report["retention_status"] == "REJECTED"
    assert any(
        error.startswith("retention_minimum_delay_not_met")
        for error in report["errors"]
    )
    assert artifact["accepted_retention_attempts"] == []


def test_retention_requires_same_pseudonymous_learner_and_distinct_session():
    source_package, first_unit, item_index, baseline, projection = baseline_bundle()
    source = retention_source(first_unit, item_index)
    source["session"]["learner_ref"] = "learner:OTHER"
    source["session"]["session_id"] = "session:A1_BASELINE_001"

    _, report = build_retention_artifact(
        source,
        source_package,
        baseline,
        projection,
        template(),
    )

    assert report["validation_status"] == "FAIL"
    assert "retention_learner_ref_mismatch" in report["errors"]
    assert "retention_session_must_be_distinct" in report["errors"]


def test_retention_requires_both_reading_and_writing_assessments():
    source_package, first_unit, item_index, baseline, projection = baseline_bundle()
    source = retention_source(first_unit, item_index)
    source["responses"] = source["responses"][:1]

    _, report = build_retention_artifact(
        source,
        source_package,
        baseline,
        projection,
        template(),
    )

    assert report["validation_status"] == "FAIL"
    assert any(
        error.startswith("retention_assessment_items_missing")
        for error in report["errors"]
    )


def test_failed_retention_is_valid_evidence_and_routes_to_review():
    source_package, first_unit, item_index, baseline, projection = baseline_bundle()
    source = retention_source(
        first_unit,
        item_index,
        reading_text="definitely not the accepted answer",
    )

    artifact, report = build_retention_artifact(
        source,
        source_package,
        baseline,
        projection,
        template(),
    )

    assert report["validation_status"] == "PASS"
    assert report["retention_status"] == "RETENTION_FAILED_REVIEW_REQUIRED"
    assert report["next_task"] == NEXT_REVIEW_TASK
    assert artifact["coverage_summary"]["failed_unit_count"] == 1
    result = artifact["by_grammar_unit_id"][first_unit["grammar_unit_id"]]
    assert result["reading_assessment_pass"] is False
    assert result["retention_confirmed"] is False
    assert result["failed_assessment_item_ids"]
    assert artifact["release_gates"]["final_mastery_projection_gate"] == (
        "BLOCKED_REVIEW_REQUIRED"
    )


def test_non_candidate_unit_cannot_be_imported_as_retention():
    source_package, first_unit, item_index, baseline, projection = baseline_bundle()
    non_candidate = next(
        unit
        for unit in source_package["learning_units"]
        if unit["grammar_unit_id"] != first_unit["grammar_unit_id"]
    )
    source = retention_source(first_unit, item_index)
    source["grammar_unit_ids"] = [non_candidate["grammar_unit_id"]]

    _, report = build_retention_artifact(
        source,
        source_package,
        baseline,
        projection,
        template(),
    )

    assert report["validation_status"] == "FAIL"
    assert any(
        error.startswith("retention_units_not_current_candidates")
        for error in report["errors"]
    )


def test_retention_attempt_sequence_advances_from_baseline():
    source_package, first_unit, item_index, baseline, projection = baseline_bundle()
    artifact, report = build_retention_artifact(
        retention_source(first_unit, item_index),
        source_package,
        baseline,
        projection,
        template(),
    )

    assert report["validation_status"] == "PASS"
    assert {
        attempt["attempt_sequence"]
        for attempt in artifact["accepted_retention_attempts"]
    } == {2}
    assert all(
        attempt["synthetic_fixture"] is False
        for attempt in artifact["accepted_retention_attempts"]
    )
    assert all(
        attempt["persistent_learner_state_write"] is False
        for attempt in artifact["accepted_retention_attempts"]
    )


def test_retention_builder_is_deterministic_and_does_not_mutate_inputs():
    source_package, first_unit, item_index, baseline, projection = baseline_bundle()
    source = retention_source(first_unit, item_index)
    inputs = (source, source_package, baseline, projection, template())
    before = copy.deepcopy(inputs)

    first = build_retention_artifact(*inputs)
    second = build_retention_artifact(*inputs)

    assert first == second
    assert inputs == before


def test_retention_private_paths_must_remain_local_or_outside_repo(tmp_path):
    assert _private_path_error(
        REPO_ROOT / ".local/a1_private_pilot_retention_responses.json"
    ) is None
    assert _private_path_error(tmp_path / "retention.json") is None
    assert _private_path_error(
        REPO_ROOT / "ulga/evidence/private_retention.json"
    ) is not None
