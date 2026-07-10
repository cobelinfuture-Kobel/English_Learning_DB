from __future__ import annotations

import copy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_full_teachable_candidate_coverage import (  # noqa: E402
    build_and_validate_from_repo as build_candidate_source,
)
from ulga.builders.build_a1_grammar_listening_integration import (  # noqa: E402
    LISTENING_DIMENSIONS,
    adapt_listening_attempt,
    build_artifact,
    validate_artifact,
    validate_listening_attempt,
)


def built():
    candidate, candidate_report = build_candidate_source()
    assert candidate_report["validation_status"] == "PASS"
    artifact = build_artifact(candidate)
    report = validate_artifact(artifact, candidate)
    return artifact, report, candidate


def activity_map(artifact):
    return {item["activity_id"]: item for item in artifact["listening_activity_bank"]}


def test_listening_candidate_coverage_passes_for_24_units_and_109_rows():
    artifact, report, _ = built()
    summary = artifact["coverage_summary"]

    assert report["validation_status"] == "PASS"
    assert len(artifact["by_grammar_unit_id"]) == 24
    assert len(artifact["by_egp_row_id"]) == 109
    assert summary["listening_activity_count"] == 96
    assert summary["listening_practice_count"] == 72
    assert summary["listening_assessment_count"] == 24
    assert summary["candidate_listening_row_coverage_percent"] == 100.0
    assert summary["rendered_audio_asset_count"] == 0


def test_each_unit_and_row_has_listening_assessment_path():
    artifact, _, _ = built()

    for unit in artifact["by_grammar_unit_id"].values():
        assert len(unit["listening_activity_ids"]) == 4
        assert len(unit["listening_assessment_ids"]) == 1
        assert unit["audio_asset_status"] == "NOT_RENDERED"
    for row in artifact["by_egp_row_id"].values():
        assert row["listening_activity_ids"]
        assert row["listening_assessment_ids"]
        assert set(row["listening_evidence_dimensions"]) == set(LISTENING_DIMENSIONS)
        assert row["grammar_mastery_status"] == "NOT_MEASURED"


def test_all_96_transcripts_are_grammar_gated_and_source_safe():
    artifact, report, _ = built()

    assert report["gate_checks"]["all_transcripts_grammar_gated"] is True
    for item in artifact["listening_activity_bank"]:
        transcript = item["transcript_contract"]
        audio = item["audio_contract"]
        assert transcript["transcript_text"]
        assert transcript["raw_external_source_text_copied"] is False
        assert transcript["restricted_source_payload_persisted"] is False
        assert audio["audio_asset_status"] == "NOT_RENDERED"
        assert audio["actual_audio_bytes_persisted"] is False


def test_listening_attempt_adapter_pass_event_is_grammar_eligible():
    artifact, _, _ = built()
    activities = activity_map(artifact)
    activity = next(iter(activities.values()))
    event = adapt_listening_attempt(
        activity,
        learner_ref="SYNTHETIC_LISTENER_A1",
        attempt_sequence=1,
        outcome="PASS",
        failure_domain="none",
        synthetic_fixture=True,
    )

    assert validate_listening_attempt(event, activities) == []
    assert event["grammar_mastery_eligible"] is True


def test_audio_quality_confound_is_not_grammar_failure():
    artifact, _, _ = built()
    activities = activity_map(artifact)
    activity = next(iter(activities.values()))
    event = adapt_listening_attempt(
        activity,
        learner_ref="SYNTHETIC_LISTENER_A1",
        attempt_sequence=1,
        outcome="UNRESOLVED",
        failure_domain="audio_quality",
        synthetic_fixture=True,
    )

    assert validate_listening_attempt(event, activities) == []
    assert event["grammar_mastery_eligible"] is False
    assert event["grammar_error_tags"] == []


def test_confound_domain_with_grammar_tag_fails_closed():
    artifact, _, _ = built()
    activities = activity_map(artifact)
    activity = next(iter(activities.values()))
    event = adapt_listening_attempt(
        activity,
        learner_ref="SYNTHETIC_LISTENER_A1",
        attempt_sequence=1,
        outcome="FAIL",
        failure_domain="vocabulary",
        grammar_error_tags=["ERR_UNCLASSIFIED_GRAMMAR_FAILURE"],
        synthetic_fixture=True,
    )

    errors = validate_listening_attempt(event, activities)

    assert any(error.startswith("confound_domain_has_grammar_tags") for error in errors)


def test_transcript_or_grammar_target_tamper_fails_closed():
    artifact, _, candidate = built()
    item = artifact["listening_activity_bank"][0]
    item["transcript_contract"]["transcript_text"] = ""
    item["grammar_gate"]["validation_targets"][0]["text"] = "Not a matching target."

    report = validate_artifact(artifact, candidate)

    assert report["validation_status"] == "FAIL"
    assert any(error.startswith("transcript_missing") for error in report["errors"])
    assert any(error.startswith("listening_grammar_gate_fail") for error in report["errors"])


def test_builder_is_deterministic_and_does_not_mutate_source():
    _, _, candidate = built()
    before = copy.deepcopy(candidate)

    first = build_artifact(candidate)
    second = build_artifact(candidate)

    assert first == second
    assert candidate == before


def test_false_audio_or_actual_mastery_claim_fails_closed():
    artifact, _, candidate = built()
    artifact["claim_boundaries"]["audio_rendering_complete"] = True
    artifact["claim_boundaries"]["actual_listening_mastery_complete"] = True

    report = validate_artifact(artifact, candidate)

    assert report["validation_status"] == "FAIL"
    assert "false_completion_claim:audio_rendering_complete" in report["errors"]
    assert "false_completion_claim:actual_listening_mastery_complete" in report["errors"]


def test_scope_remains_a1_only_without_persistent_writes_or_nlp():
    artifact, _, _ = built()
    boundaries = artifact["claim_boundaries"]

    assert boundaries["candidate_listening_contract_complete"] is True
    assert boundaries["candidate_transcript_coverage_complete"] is True
    assert boundaries["audio_rendering_complete"] is False
    assert boundaries["actual_listening_attempt_collection_complete"] is False
    assert boundaries["production_runtime_integration_complete"] is False
    assert boundaries["no_a2_a2plus_expansion"] is True
    assert boundaries["no_persistent_learner_state_write"] is True
    assert boundaries["no_external_nlp_dependency"] is True
