from __future__ import annotations

import json
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4
from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5
from ulga.builders import build_a1fs_v1_shared_learner_stimulus_contract_renderer as stimulus
from ulga.builders import build_e4s_a1v1_m12g_learner_contract_assessment_validity_fullfix as assessment
from ulga.validators.validate_a1fs_v1_learner_answerability_gate import validate_bank


def _scoring() -> dict:
    return {
        "scoring_mode": "NORMALIZED_TEXT",
        "response_type": "string",
        "accepted_texts": ["the park"],
        "case_insensitive": True,
        "punctuation_tolerance": True,
        "human_review_fallback": False,
    }


def _item(learner: dict) -> dict:
    return {
        "item_id": "R4_ITEM_TEXT",
        "breadth_cell_id": "BREADTH_CELL_TEXT",
        "capability_id": "CAP_TEXT",
        "life_task_id": "LIFE_TASK_TEXT",
        "domain": "SCHOOL_CLASSROOM",
        "level": "A1",
        "skill": "READING",
        "purpose": "CORE_PRACTICE",
        "task_type": "GUIDED_RESPONSE",
        "support_level": "S2_FRAME",
        "initiative_level": "RESPOND_ONLY",
        "interaction_variation": "EXPECTED_SCRIPT",
        "transfer_distance": "NONE",
        "template_family": "TEXT_LOCATION",
        "stimulus_fingerprint": "f" * 64,
        "media_payload_state": "NOT_REQUIRED",
        "learner_contract": learner,
        "private_scoring_contract": _scoring(),
        "admission": {"status": "APPROVED"},
    }


def test_assessment_rejects_original_defect_pattern() -> None:
    with pytest.raises(assessment.AssessmentValidityError, match="learner_answerability_failed"):
        assessment.validate_learner_contract(
            item_id="missing-text",
            task_type="guided_response",
            learner={"prompt": "文本中提到了哪個地點？", "response_mode": "short_text"},
            scoring=_scoring(),
        )


def test_assessment_attaches_shared_manifest_when_text_exists() -> None:
    learner, _ = assessment.validate_learner_contract(
        item_id="text-present",
        task_type="guided_response",
        learner={
            "prompt": "文本中提到了哪個地點？",
            "response_mode": "short_text",
            "context": {"source_text": "Mia is at the park."},
        },
        scoring=_scoring(),
    )
    assert learner["stimulus_validation"]["answerability_pass"] is True
    assert learner["stimulus_render_manifest"][0]["payload"] == "Mia is at the park."


def test_r5_safe_item_fails_closed_without_required_text() -> None:
    with pytest.raises(r5.LocalEdgeRuntimeError, match="SESSION_ITEM_NOT_ANSWERABLE"):
        r5._safe_item(_item({
            "prompt": "文本中提到了哪個地點？",
            "response_mode": "short_text",
        }))


def test_r5_safe_item_keeps_shared_render_manifest() -> None:
    learner = stimulus.ensure_learner_contract(
        item_id="R4_ITEM_TEXT",
        task_type="guided_response",
        learner={
            "prompt": "文本中提到了哪個地點？",
            "response_mode": "short_text",
            "context": {"source_text": "Mia is at the park."},
        },
        scoring=_scoring(),
    )
    safe = r5._safe_item(_item(learner))
    assert safe["learner_contract"]["stimulus_render_manifest"][0]["payload"] == "Mia is at the park."


def test_r5_html_consumes_shared_renderer() -> None:
    html = r5.learner_html()
    assert "renderA1FSStimulus" in html
    assert "stimulus_render_manifest" in html
    assert "renderA1FSStimulus(box,l)" in html


def test_production_bank_gate_rejects_missing_text(tmp_path: Path) -> None:
    bad = _item({
        "prompt": "文本中提到了哪個地點？",
        "response_mode": "short_text",
    })
    bank_core = {
        "task_id": r4.TASK_ID,
        "schema_version": r4.BANK_SCHEMA_VERSION,
        "validation_status": r4.STATUS,
        "private_local_only": True,
        "source_bindings": {},
        "item_count": 1,
        "items": [bad],
    }
    bank = {**bank_core, "bank_sha256": r4.digest(bank_core)}
    path = tmp_path / "bank.json"
    path.write_text(json.dumps(bank), encoding="utf-8")
    report = validate_bank(path)
    assert report["error_count"] > 0
    assert report["counts"]["answerability_failed"] == 1
    assert report["counts"]["payload_missing"] == 1


def test_production_bank_gate_passes_visible_text(tmp_path: Path) -> None:
    learner = stimulus.ensure_learner_contract(
        item_id="R4_ITEM_TEXT",
        task_type="guided_response",
        learner={
            "prompt": "文本中提到了哪個地點？",
            "response_mode": "short_text",
            "context": {"source_text": "Mia is at the park."},
        },
        scoring=_scoring(),
    )
    good = _item(learner)
    bank_core = {
        "task_id": r4.TASK_ID,
        "schema_version": r4.BANK_SCHEMA_VERSION,
        "validation_status": r4.STATUS,
        "private_local_only": True,
        "source_bindings": {},
        "item_count": 1,
        "items": [good],
    }
    bank = {**bank_core, "bank_sha256": r4.digest(bank_core)}
    path = tmp_path / "bank.json"
    path.write_text(json.dumps(bank), encoding="utf-8")
    report = validate_bank(path)
    assert report["error_count"] == 0
    assert report["counts"]["ready_for_local_selection"] == 1
