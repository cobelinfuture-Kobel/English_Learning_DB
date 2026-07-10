from __future__ import annotations

import copy

from ulga.builders.build_a1_grammar_operator_review_decision_intake import (
    _activity_findings,
    _content_findings,
    build_artifact,
    review_unit,
    validate_artifact,
)


PILOTS = {
    "GRAMMAR_BE_VERB_BASIC",
    "GRAMMAR_ARTICLES_BASIC",
    "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS",
    "GRAMMAR_PRESENT_SIMPLE_NEGATIVES",
    "GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS",
    "GRAMMAR_PAST_SIMPLE_A1",
}


def generic_items(grammar_id: str):
    prompts = [
        ("P01", "reading", "recognition", "multiple_choice", "Choose the option that uses the target grammar correctly.", "select_one", ["Target.", "Not the target form"]),
        ("P02", "reading", "meaning", "context_match", "Choose the target form that matches the short context.", "select_one", ["Target.", "Other."]),
        ("P03", "reading", "contrast", "error_discrimination", "Identify the correctly formed target example.", "select_one", ["Target.", "Incorrect contrast"]),
        ("P04", "writing", "controlled_production", "gap_fill", "Complete the target form.", "short_text", []),
        ("P05", "writing", "controlled_production", "word_order", "Put the words in the correct order.", "short_text", []),
        ("P06", "writing", "contextual_production", "guided_sentence", "Write a sentence for the context using the target grammar.", "short_text", []),
        ("A01", "reading", "receptive_checkpoint", "checkpoint_choice", "Select the correct target sentence or phrase.", "select_one", ["Target.", "Incorrect form"]),
        ("A02", "writing", "productive_checkpoint", "checkpoint_write", "Produce one sentence or phrase with the target grammar.", "short_text", []),
    ]
    return [
        {
            "item_id": f"{grammar_id}__{code}",
            "skill": skill,
            "evidence_dimension": dimension,
            "task_type": task_type,
            "prompt": prompt,
            "response_mode": response_mode,
            "options": options,
        }
        for code, skill, dimension, task_type, prompt, response_mode, options in prompts
    ]


def fixtures():
    unit_ids = sorted(PILOTS) + [f"GRAMMAR_DERIVED_{index:02d}" for index in range(18)]
    row_ids = [f"ROW_{index:03d}" for index in range(109)]
    assignments = {unit_id: [] for unit_id in unit_ids}
    for index, row_id in enumerate(row_ids):
        assignments[unit_ids[index % 24]].append(row_id)
    units = []
    for unit_id in unit_ids:
        derived = unit_id not in PILOTS
        items = generic_items(unit_id)
        units.append(
            {
                "grammar_unit_id": unit_id,
                "internal_stage": "A1",
                "canonical_egp_row_ids": assignments[unit_id],
                "learning_objectives": (
                    [
                        f"Recognize the form and meaning of {unit_id}.",
                        f"Produce a controlled A1/A1+ example of {unit_id}.",
                    ]
                    if derived
                    else ["Use the target form accurately.", "Explain its basic meaning."]
                ),
                "positive_examples": (
                    [{"text": "Target.", "explanation": f"Validated example of {unit_id}."}]
                    if derived
                    else [{"text": "Target.", "explanation": "Specific explanation."}]
                ),
                "negative_examples": [{"text": "Non-target."}],
                "common_error_tags": (
                    [{"tag": "ERR_X", "diagnosis": "The response does not satisfy the canonical target pattern."}]
                    if derived
                    else [{"tag": "ERR_X", "diagnosis": "Specific diagnosis."}]
                ),
                "practice_items": items[:6],
                "assessment_items": items[6:],
            }
        )
    candidate = {
        "learning_units": units,
        "by_egp_row_id": {row_id: {} for row_id in row_ids},
    }
    review_gate = {
        "review_queue": [
            {
                "grammar_unit_id": unit_id,
                "canonical_egp_row_ids": assignments[unit_id],
                "review_dimensions": {},
            }
            for unit_id in unit_ids
        ],
        "coverage_summary": {
            "pending_operator_review_unit_count": 24,
            "approved_text_mode_unit_count": 0,
            "needs_revision_unit_count": 0,
            "rejected_unit_count": 0,
            "text_mode_pilot_eligible_unit_count": 0,
            "text_mode_pilot_eligible_row_count": 0,
        },
        "release_gates": {
            "operator_text_review_gate": {"status": "BLOCKED_PENDING_DECISIONS"},
            "text_mode_private_pilot_gate": {"status": "BLOCKED_PENDING_REVIEW"},
            "audio_scope_gate": {"status": "DEFERRED_NON_BLOCKING_FOR_TEXT_MODE"},
        },
        "claim_boundaries": {
            "operator_text_review_complete": False,
            "text_mode_private_pilot_eligible": False,
            "full_four_skill_release_complete": False,
        },
    }
    return candidate, review_gate


def test_decision_intake_blocks_all_24_units_and_109_rows():
    candidate, review_gate = fixtures()
    artifact = build_artifact(candidate, review_gate)
    report = validate_artifact(artifact, candidate)

    assert report["validation_status"] == "PASS"
    assert artifact["coverage_summary"]["reviewed_unit_count"] == 24
    assert artifact["coverage_summary"]["needs_revision_unit_count"] == 24
    assert artifact["coverage_summary"]["blocked_row_count"] == 109
    assert artifact["coverage_summary"]["text_mode_pilot_eligible_row_count"] == 0


def test_all_decisions_are_recommendations_not_operator_approvals():
    candidate, review_gate = fixtures()
    artifact = build_artifact(candidate, review_gate)

    for item in artifact["decisions"]:
        assert item["decision"] == "NEEDS_REVISION"
        assert item["operator_confirmation_required"] is True
        assert item["decision_origin"] == (
            "DELEGATED_PEDAGOGICAL_QA_RECOMMENDATION_NOT_OPERATOR_APPROVAL"
        )
    assert artifact["claim_boundaries"]["operator_review_complete"] is False
    assert artifact["claim_boundaries"]["operator_approval_fabricated"] is False


def test_generic_activity_templates_are_detected():
    candidate, _ = fixtures()
    findings = _activity_findings(candidate["learning_units"][0])

    assert "RW_PROMPT_IS_GENERIC_TEMPLATE" in findings
    assert "RW_OPTIONS_CONTAIN_PLACEHOLDER_DISTRACTORS" in findings
    assert "RW_CONTEXT_MATCH_HAS_NO_CONTEXT_PAYLOAD" in findings
    assert "RW_GAP_FILL_HAS_NO_GAP_SPEC" in findings
    assert "RW_WORD_ORDER_HAS_NO_TOKEN_SEQUENCE" in findings
    assert "RW_PRODUCTIVE_TASK_HAS_NO_SCORING_RUBRIC" in findings
    assert "RW_SHORT_TEXT_HAS_NO_ACCEPTED_VARIATION_POLICY" in findings


def test_derived_units_receive_content_rewrite_findings():
    candidate, _ = fixtures()
    unit = next(item for item in candidate["learning_units"] if item["grammar_unit_id"] not in PILOTS)
    findings = _content_findings(unit)

    assert "DERIVED_UNIT_REQUIRES_UNIT_SPECIFIC_PEDAGOGICAL_REWRITE" in findings
    assert "LEARNING_OBJECTIVES_ARE_GENERIC_DERIVATIONS" in findings
    assert "POSITIVE_EXPLANATIONS_ARE_GENERIC_DERIVATIONS" in findings
    assert "ERROR_DIAGNOSIS_IS_GENERIC_NON_MATCH" in findings


def test_articles_receive_context_specific_findings():
    candidate, _ = fixtures()
    unit = next(item for item in candidate["learning_units"] if item["grammar_unit_id"] == "GRAMMAR_ARTICLES_BASIC")
    findings = _content_findings(unit)

    assert "ARTICLE_NEGATIVE_EXAMPLES_REQUIRE_DISCOURSE_CONTEXT" in findings
    assert "DEFINITE_ARTICLE_USE_REQUIRES_IDENTIFIABILITY_CONTEXT" in findings


def test_review_unit_can_approve_only_when_no_blocking_findings():
    unit = {
        "grammar_unit_id": "GRAMMAR_BE_VERB_BASIC",
        "learning_objectives": ["Specific objective."],
        "positive_examples": [{"text": "I am happy.", "explanation": "Specific."}],
        "negative_examples": [],
        "common_error_tags": [],
        "practice_items": [],
        "assessment_items": [],
    }
    result = review_unit(unit)

    assert result["decision"] == "NEEDS_REVISION"
    assert "RW_ACTIVITY_SET_NOT_6_PRACTICE_PLUS_2_ASSESSMENT" in result["blocking_findings"]


def test_builder_does_not_mutate_sources():
    candidate, review_gate = fixtures()
    before = copy.deepcopy((candidate, review_gate))

    build_artifact(candidate, review_gate)

    assert (candidate, review_gate) == before


def test_forged_approval_fails_closed():
    candidate, review_gate = fixtures()
    artifact = build_artifact(candidate, review_gate)
    artifact["decisions"][0]["decision"] = "APPROVE_TEXT_MODE"
    artifact["coverage_summary"]["approved_text_mode_unit_count"] = 1
    artifact["coverage_summary"]["needs_revision_unit_count"] = 23

    report = validate_artifact(artifact, candidate)

    assert report["validation_status"] == "FAIL"
    assert "unexpected_text_mode_approval" in report["errors"]


def test_audio_remains_deferred_and_full_release_false():
    candidate, review_gate = fixtures()
    artifact = build_artifact(candidate, review_gate)

    assert artifact["decision_application_preview"]["audio_scope_gate"] == (
        "DEFERRED_NON_BLOCKING_FOR_TEXT_MODE"
    )
    assert artifact["decision_application_preview"]["full_four_skill_release_complete"] is False
    assert artifact["claim_boundaries"]["audio_scope_complete"] is False


def test_missing_canonical_unit_fails_closed():
    candidate, review_gate = fixtures()
    candidate["learning_units"].pop()

    try:
        build_artifact(candidate, review_gate)
    except ValueError as exc:
        assert str(exc) == "source_review_unit_count_not_24"
    else:
        raise AssertionError("missing canonical unit should fail closed")
