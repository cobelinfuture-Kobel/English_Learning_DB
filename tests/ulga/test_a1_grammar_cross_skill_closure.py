from __future__ import annotations

import copy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_cross_skill_closure import (  # noqa: E402
    SKILLS,
    build_artifact,
    validate_artifact,
)
from ulga.builders.build_a1_grammar_full_teachable_candidate_coverage import (  # noqa: E402
    build_and_validate_from_repo as build_candidate_source,
)
from ulga.builders.build_a1_grammar_listening_integration import (  # noqa: E402
    build_and_validate_from_repo as build_listening_source,
)
from ulga.builders.build_a1_grammar_mastery_review_loop import (  # noqa: E402
    build_and_validate_from_repo as build_mastery_source,
)
from ulga.builders.build_a1_grammar_reading_writing_closed_loop import (  # noqa: E402
    build_and_validate_from_repo as build_reading_writing_source,
)
from ulga.builders.build_a1_grammar_speaking_integration import (  # noqa: E402
    build_and_validate_from_repo as build_speaking_source,
)


def sources():
    candidate, candidate_report = build_candidate_source()
    reading_writing, reading_writing_report = (
        build_reading_writing_source()
    )
    mastery, mastery_report = build_mastery_source()
    listening, listening_report = build_listening_source()
    speaking, speaking_report = build_speaking_source()
    for report in (
        candidate_report,
        reading_writing_report,
        mastery_report,
        listening_report,
        speaking_report,
    ):
        assert report["validation_status"] == "PASS"
    return candidate, reading_writing, mastery, listening, speaking


def built():
    payloads = sources()
    artifact = build_artifact(*payloads)
    report = validate_artifact(artifact, *payloads)
    return artifact, report, payloads


def test_cross_skill_candidate_closure_passes_for_24_units_and_109_rows():
    artifact, report, _ = built()
    summary = artifact["coverage_summary"]

    assert report["validation_status"] == "PASS"
    assert len(artifact["by_grammar_unit_id"]) == 24
    assert len(artifact["by_egp_row_id"]) == 109
    assert summary["candidate_cross_skill_closed_row_count"] == 109
    assert summary["candidate_cross_skill_missing_row_count"] == 0
    assert summary["candidate_cross_skill_row_coverage_percent"] == 100.0


def test_each_unit_has_four_skill_paths_and_assessments():
    artifact, _, _ = built()

    for unit in artifact["by_grammar_unit_id"].values():
        assert set(unit["skill_paths"]) == set(SKILLS)
        for path in unit["skill_paths"].values():
            assert len(path["activity_ids"]) == 4
            assert len(path["assessment_ids"]) == 1
        assert unit["candidate_cross_skill_status"] == "CLOSED"
        assert unit["operator_review_status"] == "NOT_COMPLETED"
        assert unit["private_learning_promotion_status"] == "NOT_PROMOTED"


def test_each_row_has_four_skill_paths_and_assessments():
    artifact, _, _ = built()

    for row in artifact["by_egp_row_id"].values():
        assert set(row["skill_paths"]) == set(SKILLS)
        for path in row["skill_paths"].values():
            assert path["activity_ids"]
            assert path["assessment_ids"]
            assert path["candidate_path_ready"] is True
        assert row["candidate_cross_skill_status"] == "CLOSED"
        assert row["actual_mastery_status"] == "NOT_MEASURED"


def test_all_24_synthetic_journeys_have_required_steps():
    artifact, _, _ = built()
    required_steps = {
        "LEARN",
        "GUIDED_PRACTICE",
        "READING",
        "WRITING",
        "LISTENING",
        "SPEAKING",
        "ASSESSMENT",
        "MASTERY_PROJECTION",
        "REVIEW_AND_RETENTION",
    }

    assert len(artifact["synthetic_unit_journeys"]) == 24
    for journey in artifact["synthetic_unit_journeys"]:
        assert {step["step"] for step in journey["steps"]} == required_steps
        assert journey["actual_learner_journey_completed"] is False
        assert journey["production_runtime_journey"] is False


def test_candidate_gates_pass_and_real_release_gates_remain_blocked():
    artifact, _, _ = built()
    gates = artifact["release_gates"]

    assert gates["canonical_authority_gate"]["status"] == "PASS"
    assert gates["candidate_teaching_gate"]["status"] == "PASS"
    assert gates["candidate_cross_skill_path_gate"]["status"] == "PASS"
    assert gates["offline_mastery_review_gate"]["status"] == "PASS"
    assert gates["operator_review_gate"]["status"] == "BLOCKED"
    assert gates["real_listening_audio_gate"]["status"] == "BLOCKED"
    assert gates["real_speaking_evidence_gate"]["status"] == "BLOCKED"
    assert gates["real_learner_evidence_gate"]["status"] == "BLOCKED"
    assert gates["private_learning_promotion_gate"]["status"] == "BLOCKED"
    assert gates["production_runtime_gate"]["status"] == "BLOCKED"


def test_program_status_distinguishes_candidate_closure_from_release():
    artifact, report, _ = built()

    assert artifact["program_status"]["candidate_closed_loop_status"] == (
        "A1_A1PLUS_GRAMMAR_CANDIDATE_CLOSED_LOOP_COMPLETE"
    )
    assert artifact["program_status"]["release_status"] == (
        "BLOCKED_PENDING_OPERATOR_REVIEW_AND_REAL_SKILL_EVIDENCE"
    )
    assert report["stop_reason"] == (
        "OPERATOR_REVIEW_AND_REAL_SKILL_EVIDENCE_REQUIRED"
    )


def test_builder_is_deterministic_and_does_not_mutate_sources():
    payloads = sources()
    before = copy.deepcopy(payloads)

    first = build_artifact(*payloads)
    second = build_artifact(*payloads)

    assert first == second
    assert payloads == before


def test_missing_skill_row_fails_closed():
    artifact, _, payloads = built()
    row_id = next(iter(artifact["by_egp_row_id"]))
    artifact["by_egp_row_id"][row_id]["skill_paths"].pop("speaking")

    report = validate_artifact(artifact, *payloads)

    assert report["validation_status"] == "FAIL"
    assert f"row_skill_set_mismatch:{row_id}" in report["errors"]


def test_false_review_promotion_or_actual_mastery_claim_fails_closed():
    artifact, _, payloads = built()
    artifact["claim_boundaries"]["operator_review_complete"] = True
    artifact["claim_boundaries"]["private_learning_promotion_complete"] = True
    artifact["claim_boundaries"]["actual_learner_evidence_complete"] = True

    report = validate_artifact(artifact, *payloads)

    assert report["validation_status"] == "FAIL"
    assert "false_completion_claim:operator_review_complete" in report["errors"]
    assert (
        "false_completion_claim:private_learning_promotion_complete"
        in report["errors"]
    )
    assert (
        "false_completion_claim:actual_learner_evidence_complete"
        in report["errors"]
    )


def test_release_gate_cannot_be_forged_open():
    artifact, _, payloads = built()
    artifact["release_gates"]["real_speaking_evidence_gate"]["status"] = "PASS"

    report = validate_artifact(artifact, *payloads)

    assert report["validation_status"] == "FAIL"
    assert (
        "required_release_gate_not_blocked:real_speaking_evidence_gate"
        in report["errors"]
    )


def test_scope_remains_a1_only_without_persistent_writes_or_nlp():
    artifact, _, _ = built()
    boundaries = artifact["claim_boundaries"]

    assert boundaries["candidate_four_skill_closure_complete"] is True
    assert boundaries["candidate_109_row_coverage_complete"] is True
    assert boundaries["operator_review_complete"] is False
    assert boundaries["real_listening_audio_complete"] is False
    assert boundaries["real_speaking_evidence_complete"] is False
    assert boundaries["actual_learner_evidence_complete"] is False
    assert boundaries["a1_a1plus_grammar_release_complete"] is False
    assert boundaries["no_a2_a2plus_expansion"] is True
    assert boundaries["no_persistent_learner_state_write"] is True
    assert boundaries["no_external_nlp_dependency"] is True
