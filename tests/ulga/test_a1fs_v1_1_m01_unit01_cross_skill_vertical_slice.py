from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_1_m01_unit01_cross_skill_vertical_slice as builder,
)
from ulga.validators import (
    validate_a1fs_v1_1_m01_unit01_cross_skill_vertical_slice as validator,
)


def _asset(key: str, role: str, *, capture: bool = True) -> dict:
    return {
        "asset_key": key,
        "role": role,
        "learner_payload": {
            "prompt": "legacy",
            "response_capture_enabled": capture,
            "options": ["a cat", "apple", "a apple"] if "R" in key else [],
        },
    }


def _bundles() -> dict[str, dict]:
    bundles: dict[str, dict] = {
        builder.LESSON_IDS["READING"]: {
            "lesson": {
                "lesson_id": builder.LESSON_IDS["READING"],
                "skill": "READING",
                "level": "A1",
            },
            "assets": [
                _asset("R-a-cat-prd", "PRD"),
                _asset("R-the-book-prd", "PRD"),
                _asset("R-an-apple-prd", "PRD"),
                _asset("R-a-cat-chk", "CHK"),
            ],
        },
        builder.LESSON_IDS["WRITING"]: {
            "lesson": {
                "lesson_id": builder.LESSON_IDS["WRITING"],
                "skill": "WRITING",
                "level": "A1",
            },
            "assets": [
                _asset("W-phrase", "PRD"),
                _asset("W-sequence", "PRD"),
                _asset("W-rubric", "PRD"),
                _asset("W-check", "CHK"),
            ],
        },
        builder.LESSON_IDS["SPEAKING"]: {
            "lesson": {
                "lesson_id": builder.LESSON_IDS["SPEAKING"],
                "skill": "SPEAKING",
                "level": "A1",
            },
            "assets": [
                _asset("S-1", "PRD", capture=False),
                _asset("S-2", "PRD", capture=False),
                _asset("S-3", "PRD", capture=False),
            ],
        },
    }
    # Preserve the real 72-lesson / 264-asset denominator.
    for index in range(69):
        lesson_id = f"DUMMY:{index:02d}"
        count = 3 if index < 23 else 4
        bundles[lesson_id] = {
            "lesson": {"lesson_id": lesson_id, "skill": "READING", "level": "A1"},
            "assets": [
                _asset(f"D-{index:02d}-{asset}", "PRD")
                for asset in range(count)
            ],
        }
    assert len(bundles) == 72
    assert sum(len(bundle["assets"]) for bundle in bundles.values()) == 264
    return bundles


def _contracts() -> dict[str, dict]:
    return {
        "R-a-cat-prd": {"scoring_mode": "EXACT_OPTION", "accepted_texts": ["a cat"]},
        "R-the-book-prd": {"scoring_mode": "EXACT_OPTION", "accepted_texts": ["the book"]},
        "R-an-apple-prd": {"scoring_mode": "EXACT_OPTION", "accepted_texts": ["an apple"]},
        "R-a-cat-chk": {"scoring_mode": "EXACT_OPTION", "accepted_texts": ["a cat"]},
        "W-phrase": {"scoring_mode": "NORMALIZED_TEXT", "accepted_texts": ["a cat"]},
        "W-sequence": {"scoring_mode": "EXACT_SEQUENCE", "accepted_sequence": ["the", "book"]},
        "W-rubric": {
            "scoring_mode": "FEATURE_RUBRIC",
            "rubric": {"grammar_target_match": True},
        },
        "W-check": {
            "scoring_mode": "FEATURE_RUBRIC",
            "rubric": {"complete_response": True},
        },
    }


def _approved() -> tuple[dict, dict]:
    candidate = builder.build_candidate(
        {
            "grammar_unit_id": builder.UNIT_ID,
            "operator_decision_ref": builder.DECISION_REF,
        }
    )
    approved = builder.admit_candidate(candidate)
    return candidate, approved


def test_policy_bound_candidate_admission_and_three_skill_projections() -> None:
    candidate, approved = _approved()
    assert candidate["artifact_role"] == policy_artifact.CANDIDATE_ROLE
    assert candidate["learner_facing"] is False
    assert approved["artifact_role"] == policy_artifact.APPROVED_ROLE
    assert approved["admission"]["decision_ref"] == builder.DECISION_REF
    projections = builder.build_projections(approved)
    assert set(projections) == {"READING", "WRITING", "SPEAKING"}
    assert all(
        row["artifact_role"] == policy_artifact.PROJECTION_ROLE
        for row in projections.values()
    )
    assert all(row["learner_facing"] is True for row in projections.values())


def test_candidate_contains_real_reading_and_shared_cross_skill_context() -> None:
    receipt = validator.validate_payload(builder.candidate_payload())
    assert receipt["status"] == "PASS"
    payload = builder.candidate_payload()
    assert payload["shared_situation"]["sentence_count"] == 6
    assert payload["reading"]["real_passage_required"] is True
    assert payload["cross_skill_reconciliation"]["shared_situation"] is True
    assert payload["source_policy"]["raw_raz_text_copied"] is False
    assert payload["source_policy"]["raw_ket_text_copied"] is False


def test_overlay_changes_only_unit01_and_preserves_asset_identities() -> None:
    source = _bundles()
    _, approved = _approved()
    overlaid = builder.overlay_bundles(
        bundles=source,
        approved=approved,
        contracts=_contracts(),
    )
    report = validator.validate_overlay(
        source_bundles=source,
        overlaid_bundles=overlaid,
        approved=approved,
    )
    assert report["modified_lesson_count"] == 3
    assert report["other_lesson_count_preserved"] == 69
    assert report["unit01_activity_count"] == 11
    reading = overlaid[builder.LESSON_IDS["READING"]]["assets"]
    assert all(
        asset["learner_payload"]["stimulus"]["body"] == builder.PASSAGE
        for asset in reading
    )
    assert {asset["learner_payload"]["prompt"] for asset in reading} != {"legacy"}
    speaking = overlaid[builder.LESSON_IDS["SPEAKING"]]["assets"]
    assert all(
        asset["learner_payload"]["response_capture_enabled"] is False
        for asset in speaking
    )
    assert all(asset["learner_payload"]["model_language"] for asset in speaking)


def test_reading_assignment_is_answer_and_role_bound() -> None:
    assets = _bundles()[builder.LESSON_IDS["READING"]]["assets"]
    assignments = builder.assign_reading_specs(assets, _contracts())
    assert assignments["R-a-cat-prd"]["spec_id"] == "M01A-R01"
    assert assignments["R-a-cat-chk"]["spec_id"] == "M01A-R04"
    broken = deepcopy(_contracts())
    broken["R-an-apple-prd"]["accepted_texts"] = ["a banana"]
    with pytest.raises(builder.Unit01SliceError, match="reading_spec_match_invalid"):
        builder.assign_reading_specs(assets, broken)


def test_validator_rejects_parallel_curriculum_or_passage_drift() -> None:
    payload = builder.candidate_payload()
    payload["cross_skill_reconciliation"]["parallel_curriculum_created"] = True
    with pytest.raises(
        validator.Unit01ValidationError,
        match="parallel_curriculum_forbidden",
    ):
        validator.validate_payload(payload)
    payload = builder.candidate_payload()
    payload["shared_situation"]["passage"] = "A disconnected placeholder."
    with pytest.raises(
        validator.Unit01ValidationError,
        match="approved_passage_identity_invalid",
    ):
        validator.validate_payload(payload)


def test_overlay_validator_rejects_non_unit01_change() -> None:
    source = _bundles()
    _, approved = _approved()
    overlaid = builder.overlay_bundles(
        bundles=source,
        approved=approved,
        contracts=_contracts(),
    )
    overlaid["DUMMY:00"]["assets"][0]["learner_payload"]["prompt"] = "changed"
    with pytest.raises(
        validator.Unit01ValidationError,
        match="non_unit01_bundle_changed",
    ):
        validator.validate_overlay(
            source_bundles=source,
            overlaid_bundles=overlaid,
            approved=approved,
        )


def test_static_patch_renders_stimulus_support_model_and_frame(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    marker = "card.append(prompt);const options=asset.learner_payload.options||[];"
    (source / "app.js").write_text(marker, encoding="utf-8")
    (source / "styles.css").write_text("body{}", encoding="utf-8")
    (source / "index.html").write_text("<html></html>", encoding="utf-8")
    builder.patch_static(source, target)
    app = (target / "app.js").read_text(encoding="utf-8")
    assert "learner_payload.stimulus" in app
    assert "learner_payload.support_text" in app
    assert "learner_payload.model_language" in app
    assert "learner_payload.sentence_frame" in app
