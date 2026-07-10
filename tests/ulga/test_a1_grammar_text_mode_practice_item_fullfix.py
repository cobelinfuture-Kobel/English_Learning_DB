from __future__ import annotations

import copy

from ulga.builders.build_a1_grammar_full_teachable_candidate_coverage import (
    build_and_validate_from_repo as build_candidate_source,
)
from ulga.builders.build_a1_grammar_text_mode_practice_item_fullfix import (
    GENERIC_PROMPTS,
    PLACEHOLDER_OPTIONS,
    build_artifact,
    build_unit_items,
    load_json,
    validate_artifact,
    DECISIONS_PATH,
)


def built():
    candidate, candidate_report = build_candidate_source()
    assert candidate_report["validation_status"] == "PASS"
    decisions = load_json(DECISIONS_PATH)
    artifact = build_artifact(candidate, decisions)
    report = validate_artifact(artifact, candidate)
    return artifact, report, candidate, decisions


def test_fullfix_covers_24_units_109_rows_and_192_items():
    artifact, report, _, _ = built()
    summary = artifact["coverage_summary"]

    assert report["validation_status"] == "PASS"
    assert len(artifact["learning_units"]) == 24
    assert len(artifact["by_egp_row_id"]) == 109
    assert len(artifact["item_bank"]) == 192
    assert summary["practice_item_count"] == 144
    assert summary["assessment_item_count"] == 48
    assert summary["reading_item_count"] == 96
    assert summary["writing_item_count"] == 96


def test_placeholder_prompts_and_options_are_removed():
    artifact, _, _, _ = built()

    for item in artifact["item_bank"]:
        assert item["prompt"] not in GENERIC_PROMPTS
        assert not PLACEHOLDER_OPTIONS.intersection(item.get("options", []))
        assert item["review_remediation"]["placeholder_prompt_removed"] is True
        assert item["review_remediation"]["placeholder_distractor_removed"] is True


def test_reading_items_have_real_options_rationales_and_context_when_required():
    artifact, _, _, _ = built()

    for item in artifact["item_bank"]:
        if item["skill"] != "reading":
            continue
        assert len(item["options"]) == 3
        assert len(set(item["options"])) == 3
        assert set(item["option_rationales"]) == set(item["options"])
        assert len(item["distractor_error_tags"]) == 2
        if item["task_type"] == "context_choice":
            assert item["context"]["situation"]
            assert item["context"]["communicative_goal"]
            assert item["context"]["grammar_clue"]


def test_gap_fill_word_order_and_productive_payloads_are_structured():
    artifact, _, _, _ = built()

    for item in artifact["item_bank"]:
        if item["task_type"] == "structured_gap_fill":
            gap = item["gap_spec"]
            assert "____" in gap["display_tokens"]
            assert gap["accepted_missing_tokens"]
            assert gap["full_answer_tokens"]
        if item["task_type"] == "structured_word_order":
            assert item["token_sequence"]
            assert item["correct_token_sequence"]
            assert item["token_sequence"] != item["correct_token_sequence"]
        if item["task_type"] in {
            "guided_contextual_writing",
            "text_mode_writing_checkpoint",
        }:
            assert item["context"]["communicative_goal"]
            assert item["scoring_rubric"]["minimum_score"] == 0.8
            assert item["accepted_variation_policy"][
                "target_grammar_must_remain_detectable"
            ] is True


def test_all_items_preserve_canonical_grammar_gate_and_safe_source_boundary():
    artifact, report, _, _ = built()

    assert report["validation_counts"]["grammar_gate_target_count"] == 192
    assert report["gate_checks"]["all_grammar_gates_pass"] is True
    for item in artifact["item_bank"]:
        assert item["content_binding"]["grammar_focus"] == [
            item["grammar_gate"]["validation_targets"][0]["grammar_id"]
        ]
        assert item["source_trace"]["raw_external_source_text_copied"] is False
        assert item["source_trace"]["restricted_source_payload_persisted"] is False


def test_each_unit_has_six_practice_and_two_assessment_items():
    artifact, _, _, _ = built()

    for unit in artifact["learning_units"]:
        assert len(unit["practice_items"]) == 6
        assert len(unit["assessment_items"]) == 2
        assert {item["skill"] for item in unit["practice_items"]} == {
            "reading",
            "writing",
        }
        assert {item["item_role"] for item in unit["assessment_items"]} == {
            "assessment"
        }


def test_each_row_has_reading_writing_and_assessment_paths():
    artifact, _, _, _ = built()

    for row in artifact["by_egp_row_id"].values():
        assert row["reading_item_ids"]
        assert row["writing_item_ids"]
        assert row["assessment_item_ids"]
        assert row["text_mode_practice_fullfix_status"] == (
            "READY_FOR_PEDAGOGY_REVIEW"
        )


def test_builder_is_deterministic_and_does_not_mutate_sources():
    _, _, candidate, decisions = built()
    before = copy.deepcopy((candidate, decisions))

    first = build_artifact(candidate, decisions)
    second = build_artifact(candidate, decisions)

    assert first == second
    assert (candidate, decisions) == before


def test_generic_prompt_tamper_fails_closed():
    artifact, _, candidate, _ = built()
    artifact["item_bank"][0]["prompt"] = next(iter(GENERIC_PROMPTS))

    report = validate_artifact(artifact, candidate)

    assert report["validation_status"] == "FAIL"
    assert any(error.startswith("generic_prompt_remains") for error in report["errors"])


def test_missing_rubric_and_gap_spec_fail_closed():
    artifact, _, candidate, _ = built()
    gap = next(item for item in artifact["item_bank"] if item["task_type"] == "structured_gap_fill")
    productive = next(
        item
        for item in artifact["item_bank"]
        if item["task_type"] == "guided_contextual_writing"
    )
    del gap["gap_spec"]
    del productive["scoring_rubric"]

    report = validate_artifact(artifact, candidate)

    assert report["validation_status"] == "FAIL"
    assert any(error.startswith("gap_spec_missing") for error in report["errors"])
    assert any(error.startswith("scoring_rubric_missing") for error in report["errors"])


def test_operator_review_audio_and_a2_boundaries_remain_closed():
    artifact, _, _, _ = built()
    boundaries = artifact["claim_boundaries"]

    assert boundaries["text_mode_practice_item_fullfix_complete"] is True
    assert boundaries["derived_pedagogy_fullfix_complete"] is False
    assert boundaries["operator_review_complete"] is False
    assert boundaries["text_mode_private_pilot_eligible"] is False
    assert boundaries["audio_scope_deferred"] is True
    assert boundaries["audio_scope_complete"] is False
    assert boundaries["no_a2_a2plus_expansion"] is True
    assert boundaries["no_persistent_learner_state_write"] is True
