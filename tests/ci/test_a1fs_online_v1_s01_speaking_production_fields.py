from __future__ import annotations

import json

from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import build_a1fs_v1_r3r4_authority_reviewed_production_population as population
from ulga.builders import build_e4s_a1v1_m12g_learner_contract_assessment_validity_fullfix as assessment


def _production_shaped_consumer() -> dict:
    return {
        "asset_records": [
            {
                "asset_key": "SPEAKING:CTX",
                "lesson_id": "S001",
                "skill": "SPEAKING",
                "role": "CTX",
                "payload": {
                    "scenario_zh": "PRIVATE-OR-GARBLED-OPERATOR-CONTEXT",
                    "communicative_context": "meeting a new classmate",
                    "candidate_role": "young learner speaking as themself",
                    "partner_role": "peer candidate",
                    "purpose": "exchange basic personal information",
                    "launch_cue": "Ask and answer one personal question.",
                    "visible_support_boundary": "Use only the visible topic card.",
                },
            },
            {
                "asset_key": "SPEAKING:MOD",
                "lesson_id": "S001",
                "skill": "SPEAKING",
                "role": "MOD",
                "payload": {
                    "model_text": "PRIVATE-MODEL-REFERENCE",
                    "audio_state": "SCRIPT_ONLY_NO_AUDIO_BYTES",
                },
            },
            {
                "asset_key": "SPEAKING:EVD",
                "lesson_id": "S001",
                "skill": "SPEAKING",
                "role": "EVD",
                "payload": {
                    "capture": ["raw first spoken response", "support state"],
                    "exit_rule": "The response completes the intended exchange.",
                    "mastery_boundary": "Completion alone does not advance mastery.",
                    "release_state": "INTERNAL_EVIDENCE_DESIGN_HUMAN_PILOT_REQUIRED",
                },
            },
            {
                "asset_key": "SPEAKING:CHK",
                "lesson_id": "S001",
                "skill": "SPEAKING",
                "role": "CHK",
                "payload": {
                    "fresh_check": "Ask a new classmate one clear question.",
                    "success_indicators": [
                        "response addresses the actual prompt",
                        "meaning is understandable",
                    ],
                    "remediation_route": ["Return to question focus if relevance fails."],
                },
            },
            {
                "asset_key": "SPEAKING:PRD",
                "lesson_id": "S001",
                "skill": "SPEAKING",
                "role": "PRD",
                "payload": {
                    "learner_instruction": "Give one relevant answer and add one detail.",
                    "required_performance": "one task-focused spoken response",
                    "scaffold_and_fade": "Teacher clarifies the task but does not supply an answer.",
                    "prohibitions": ["no teacher-completed answer"],
                    "authorship_required": "LEARNER_AUTHORED_ORAL_RESPONSE",
                },
            },
        ]
    }


def _project(consumer: dict, asset_key: str):
    normalized = population._projection_consumer(consumer)
    asset = next(row for row in normalized["asset_records"] if row["asset_key"] == asset_key)
    derived = m6.derive_contract(asset)
    learner, scoring, task_type, *_ = population._task_projection(asset, derived)
    validated_learner, validated_scoring = assessment.validate_learner_contract(
        item_id=asset_key,
        task_type=task_type.casefold(),
        learner=learner,
        scoring=scoring,
    )
    return asset, derived, validated_learner, validated_scoring


def test_production_speaking_prd_fields_create_answerable_private_review_item() -> None:
    asset, derived, learner, scoring = _project(_production_shaped_consumer(), "SPEAKING:PRD")

    assert derived["capture_enabled"] is True
    assert derived["prompt"] == "Give one relevant answer and add one detail."
    assert learner["context"] == {"source_text": "meeting a new classmate"}
    assert learner["stimulus_validation"]["actual_dependency_kinds"] == ["TEXT"]
    assert scoring["scoring_mode"] == "FEATURE_RUBRIC"
    assert "capture" in scoring["rubric"]["criteria"]
    assert "exit_rule" in scoring["rubric"]["criteria"]
    assert "private_scoring_contract" in asset["payload"]

    rendered = json.dumps(learner, ensure_ascii=False)
    assert "PRIVATE-OR-GARBLED" not in rendered
    assert "PRIVATE-MODEL-REFERENCE" not in rendered
    assert "exit_rule" not in rendered


def test_production_speaking_chk_uses_fresh_check_and_private_success_criteria() -> None:
    _asset, derived, learner, scoring = _project(_production_shaped_consumer(), "SPEAKING:CHK")

    assert derived["capture_enabled"] is True
    assert derived["prompt"] == "Ask a new classmate one clear question."
    assert learner["context"] == {"source_text": "meeting a new classmate"}
    assert scoring["scoring_mode"] == "FEATURE_RUBRIC"
    assert "success_indicators" in scoring["rubric"]["criteria"]
    assert "remediation_route" in scoring["rubric"]["criteria"]


def test_speaking_evd_without_learner_prompt_stays_non_captureable() -> None:
    normalized = population._projection_consumer(_production_shaped_consumer())
    evd = next(row for row in normalized["asset_records"] if row["asset_key"] == "SPEAKING:EVD")
    derived = m6.derive_contract(evd)

    assert derived["capture_enabled"] is False
    assert evd["payload"]["response_capture_enabled"] is False
