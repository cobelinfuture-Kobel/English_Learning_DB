from copy import deepcopy
import json

import pytest

from ulga.builders import build_a1_a1plus_shared_item_contract as builder
from ulga.validators import validate_a1_a1plus_shared_item_contract as validator


@pytest.fixture(scope="module")
def artifact():
    return builder.build_artifact()


def test_m03_builds_384_items_with_balanced_four_skill_coverage(artifact):
    assert artifact["task_id"] == builder.TASK_ID
    assert artifact["scope"] == "A1_A1_PLUS_ONLY"
    assert artifact["coverage_summary"] == {
        "learning_unit_count": 24,
        "canonical_egp_row_count": 109,
        "direct_canonical_unit_count": 23,
        "rowless_structural_unit_count": 1,
        "shared_item_count": 384,
        "items_per_unit": 16,
        "skill_item_counts": {skill: 96 for skill in builder.SKILLS},
        "skill_practice_counts": {skill: 72 for skill in builder.SKILLS},
        "skill_assessment_counts": {skill: 24 for skill in builder.SKILLS},
        "rendered_listening_audio_count": 0,
        "captured_speaking_audio_count": 0,
        "collected_speaking_transcript_count": 0,
    }
    assert len(artifact["shared_items"]) == 384
    assert len(artifact["by_grammar_unit_id"]) == 24
    assert set(map(len, artifact["by_grammar_unit_id"].values())) == {16}
    assert {skill: len(ids) for skill, ids in artifact["by_skill"].items()} == {
        skill: 96 for skill in builder.SKILLS
    }
    assert len(artifact["by_source_item_id"]) == 384


def test_m03_schema_is_closed_and_matches_shared_item_envelope(artifact):
    schema = json.loads(builder.SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == validator.REQUIRED_FIELDS
    assert schema["x_policy"]["a1_a1plus_only"] is True
    assert schema["x_policy"][
        "listening_audio_may_be_claimed_ready_without_rendered_asset"
    ] is False
    assert schema["x_policy"][
        "speaking_scoring_may_be_claimed_ready_without_capture_or_transcript"
    ] is False
    assert schema["x_policy"]["a2_a2plus_progression_allowed"] is False
    assert set(artifact["shared_items"][0]) == validator.REQUIRED_FIELDS


def test_m03_text_items_keep_deterministic_or_reviewable_text_contracts(artifact):
    text_items = [
        item
        for item in artifact["shared_items"]
        if item["skill"] in {"reading", "writing"}
    ]
    assert len(text_items) == 192
    for item in text_items:
        mode = item["answer_contract"]["answer_mode"]
        assert mode in validator.TEXT_MODES
        assert item["source_trace"]["source_kind"] == "READING_WRITING_TEXT_MODE"
        assert item["media_contract"] == {
            "text_status": "AVAILABLE",
            "audio_required": False,
            "audio_status": "NOT_REQUIRED",
            "transcript_required": False,
            "transcript_status": "NOT_REQUIRED",
            "image_required": False,
            "image_status": "NOT_REQUIRED",
            "learner_capture_required": False,
            "learner_capture_status": "NOT_REQUIRED",
        }
        if mode == "FEATURE_RUBRIC_CANDIDATE":
            assert item["scoring_contract"]["deterministic_candidate"] is False
            assert item["scoring_contract"]["human_review_fallback"] is True
        else:
            assert item["scoring_contract"]["deterministic_candidate"] is True


def test_m03_listening_contract_does_not_claim_unrendered_audio_ready(artifact):
    listening = artifact["shared_items"]
    listening = [item for item in listening if item["skill"] == "listening"]
    assert len(listening) == 96
    for item in listening:
        assert item["answer_contract"]["answer_mode"] == (
            "TRANSCRIPT_BACKED_CANDIDATE"
        )
        assert item["answer_contract"]["transcript_text"]
        assert item["scoring_contract"]["real_skill_scoring_ready"] is False
        assert item["scoring_contract"]["human_review_fallback"] is True
        assert item["media_contract"] == {
            "text_status": "AVAILABLE",
            "audio_required": True,
            "audio_status": "NOT_RENDERED",
            "transcript_required": True,
            "transcript_status": "CANDIDATE_AVAILABLE",
            "image_required": False,
            "image_status": "NOT_REQUIRED",
            "learner_capture_required": False,
            "learner_capture_status": "NOT_REQUIRED",
        }


def test_m03_speaking_contract_requires_capture_transcript_and_human_fallback(artifact):
    speaking = [item for item in artifact["shared_items"] if item["skill"] == "speaking"]
    assert len(speaking) == 96
    for item in speaking:
        assert item["answer_contract"]["answer_mode"] == "FEATURE_RUBRIC_CANDIDATE"
        assert item["answer_contract"]["exact_text_match_required"] is False
        assert item["answer_contract"]["model_texts"]
        assert item["scoring_contract"] == {
            "scoring_mode": "FEATURE_RUBRIC_CANDIDATE",
            "deterministic_candidate": False,
            "real_skill_scoring_ready": False,
            "human_review_fallback": True,
            "required_evidence": [
                "learner_audio_capture",
                "learner_transcript",
                "grammar_feature_evaluation",
            ],
        }
        assert item["media_contract"] == {
            "text_status": "MODEL_TEXT_AVAILABLE",
            "audio_required": True,
            "audio_status": "NOT_IMPLEMENTED",
            "transcript_required": True,
            "transcript_status": "NOT_COLLECTED",
            "image_required": False,
            "image_status": "NOT_REQUIRED",
            "learner_capture_required": True,
            "learner_capture_status": "NOT_IMPLEMENTED",
        }


def test_m03_preserves_23_plus_1_coverage_without_fake_row(artifact):
    rowless = [
        item
        for item in artifact["shared_items"]
        if item["content_binding"]["coverage_mode"]
        == "ROWLESS_STRUCTURAL_PACKAGE_GATE"
    ]
    assert len(rowless) == 16
    assert {item["grammar_unit_id"] for item in rowless} == {
        "GRAMMAR_DEMONSTRATIVES_CONTRAST"
    }
    assert all(item["content_binding"]["canonical_egp_row_ids"] == [] for item in rowless)


def test_m03_validator_passes_and_routes_to_reading_v1(artifact):
    report = validator.validate_artifact(artifact)
    assert report["validation_status"] == validator.PASS_STATUS
    assert report["errors"] == []
    assert report["validation_counts"] == {
        "shared_item_count": 384,
        "learning_unit_count": 24,
        "skill_item_counts": {skill: 96 for skill in builder.SKILLS},
        "direct_canonical_unit_count": 23,
        "rowless_structural_unit_count": 1,
    }
    assert report["stop_reason"] == "NONE"
    assert report["next_short_step"] == builder.NEXT_SHORT_STEP


def test_m03_validator_fails_closed_on_false_listening_audio_readiness(artifact):
    tampered = deepcopy(artifact)
    item = next(item for item in tampered["shared_items"] if item["skill"] == "listening")
    item["media_contract"]["audio_status"] = "NOT_REQUIRED"
    item["scoring_contract"]["real_skill_scoring_ready"] = True
    report = validator.validate_artifact(tampered)
    assert report["validation_status"] == "FAIL"
    assert any("listening_false_real_scoring_ready" in error for error in report["errors"])
    assert any("listening_media_contract_mismatch" in error for error in report["errors"])
    assert report["next_short_step"] is None


def test_m03_validator_fails_closed_on_false_speaking_capture_readiness(artifact):
    tampered = deepcopy(artifact)
    item = next(item for item in tampered["shared_items"] if item["skill"] == "speaking")
    item["media_contract"]["learner_capture_status"] = "NOT_REQUIRED"
    item["scoring_contract"]["deterministic_candidate"] = True
    report = validator.validate_artifact(tampered)
    assert report["validation_status"] == "FAIL"
    assert any("speaking_false_deterministic" in error for error in report["errors"])
    assert any("speaking_media_contract_mismatch" in error for error in report["errors"])
    assert report["next_short_step"] is None
