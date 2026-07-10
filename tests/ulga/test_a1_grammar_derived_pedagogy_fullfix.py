from __future__ import annotations

import copy

from ulga.builders.build_a1_grammar_derived_pedagogy_fullfix import (
    ARTICLE_NUMBER_VALIDATOR_GAP,
    DERIVED_META,
    PRESERVED_PILOTS,
    build_artifact,
    validate_artifact,
)
from ulga.builders.build_a1_grammar_text_mode_practice_item_fullfix import (
    build_and_validate_from_repo as build_practice_source,
)


def built():
    source, source_report = build_practice_source()
    assert source_report["validation_status"] == "PASS"
    artifact = build_artifact(source)
    report = validate_artifact(artifact, source)
    return artifact, report, source


def by_id(artifact):
    return {
        unit["grammar_unit_id"]: unit
        for unit in artifact["learning_units"]
    }


def test_fullfix_covers_24_units_109_rows_and_192_items():
    artifact, report, _ = built()
    summary = artifact["coverage_summary"]

    assert report["validation_status"] == "PASS"
    assert len(artifact["learning_units"]) == 24
    assert len(artifact["by_egp_row_id"]) == 109
    assert len(artifact["item_bank"]) == 192
    assert summary["derived_unit_fullfix_count"] == 18
    assert summary["article_context_fullfix_count"] == 1
    assert summary["preserved_curated_pilot_count"] == 5


def test_all_18_derived_units_have_unit_specific_objectives():
    artifact, _, _ = built()
    units = by_id(artifact)

    assert set(DERIVED_META).issubset(units)
    for grammar_id in DERIVED_META:
        unit = units[grammar_id]
        assert unit["learning_objectives"] == DERIVED_META[grammar_id]["objectives"]
        assert unit["pedagogy_fullfix_status"] == (
            "UNIT_SPECIFIC_FULLFIX_APPLIED"
        )
        assert unit["content_authority_status"] == (
            "PROJECT_AUTHORED_FULLFIX_CANDIDATE"
        )
        assert not any(
            objective.startswith("Recognize the form and meaning of")
            for objective in unit["learning_objectives"]
        )


def test_derived_positive_explanations_are_not_generic():
    artifact, _, _ = built()
    units = by_id(artifact)

    for grammar_id in DERIVED_META:
        for example in units[grammar_id]["positive_examples"]:
            assert example["explanation"].startswith("This example realizes ")
            assert not example["explanation"].startswith(
                "Validated example of"
            )


def test_derived_error_diagnoses_are_unit_specific():
    artifact, _, _ = built()
    units = by_id(artifact)

    for grammar_id, meta in DERIVED_META.items():
        diagnoses = {
            error["diagnosis"]
            for error in units[grammar_id]["common_error_tags"]
        }
        assert diagnoses.issubset(set(meta["diagnoses"]))
        assert not any(
            "does not satisfy the canonical target pattern" in value.lower()
            for value in diagnoses
        )


def test_articles_have_contextualized_examples_and_number_gap_registration():
    artifact, report, _ = built()
    articles = by_id(artifact)["GRAMMAR_ARTICLES_BASIC"]
    negative = next(
        item for item in articles["negative_examples"]
        if item["text"] == "a books"
    )

    assert all(example.get("context") for example in articles["positive_examples"])
    assert negative["validator_limit"] == ARTICLE_NUMBER_VALIDATOR_GAP
    assert artifact["known_validator_gaps"] == [
        {
            "grammar_unit_id": "GRAMMAR_ARTICLES_BASIC",
            "gap_id": ARTICLE_NUMBER_VALIDATOR_GAP,
            "affected_example": "a books",
            "current_dispatcher_result": "FALSE_POSITIVE_MATCH_EXPECTED",
            "promotion_effect": (
                "BLOCKS_AUTOMATIC_NEGATIVE_EXAMPLE_CERTIFICATION_ONLY"
            ),
            "required_followup": (
                "Add article-number agreement to the canonical executable validator."
            ),
        }
    ]
    assert report["validation_counts"]["known_validator_gap_count"] == 1
    assert artifact["claim_boundaries"][
        "all_negative_examples_automatically_certified"
    ] is False


def test_preserved_pilots_remain_identified_and_refresh_items():
    artifact, _, _ = built()
    units = by_id(artifact)

    for grammar_id in PRESERVED_PILOTS:
        unit = units[grammar_id]
        assert unit["pedagogy_fullfix_status"] == "CURATED_PILOT_PRESERVED"
        assert len(unit["practice_items"]) == 6
        assert len(unit["assessment_items"]) == 2


def test_regenerated_contexts_are_grammatical_and_specific():
    artifact, _, _ = built()

    contexts = [
        item["context"]["situation"]
        for item in artifact["item_bank"]
        if isinstance(item.get("context"), dict)
    ]
    assert contexts
    assert all(
        value.startswith("A learner is writing a short A1 message.")
        for value in contexts
    )
    assert not any("needs to identification" in value for value in contexts)


def test_all_192_practice_item_grammar_gates_pass():
    _, report, _ = built()

    assert report["validation_counts"][
        "practice_item_grammar_gate_target_count"
    ] == 192
    assert report["validation_counts"]["unique_item_id_count"] == 192
    assert report["gate_checks"][
        "all_practice_item_grammar_gates_pass"
    ] is True


def test_builder_is_deterministic_and_does_not_mutate_source():
    _, _, source = built()
    before = copy.deepcopy(source)

    first = build_artifact(source)
    second = build_artifact(source)

    assert first == second
    assert source == before


def test_generic_objective_tamper_fails_closed():
    artifact, _, source = built()
    unit = next(
        unit for unit in artifact["learning_units"]
        if unit["grammar_unit_id"] in DERIVED_META
    )
    unit["learning_objectives"][0] = (
        "Recognize the form and meaning of a generic unit."
    )

    report = validate_artifact(artifact, source)

    assert report["validation_status"] == "FAIL"
    assert any(
        error.startswith("generic_objective_remains")
        for error in report["errors"]
    )


def test_unregistered_article_validator_false_positive_fails_closed():
    artifact, _, source = built()
    articles = by_id(artifact)["GRAMMAR_ARTICLES_BASIC"]
    negative = next(
        item for item in articles["negative_examples"]
        if item["text"] == "a books"
    )
    del negative["validator_limit"]

    report = validate_artifact(artifact, source)

    assert report["validation_status"] == "FAIL"
    assert any(
        error.startswith("negative_example_gate_fail")
        for error in report["errors"]
    )


def test_operator_audio_and_a2_boundaries_remain_closed():
    artifact, _, _ = built()
    boundaries = artifact["claim_boundaries"]

    assert boundaries["derived_pedagogy_fullfix_complete"] is True
    assert boundaries["article_context_fullfix_complete"] is True
    assert boundaries["operator_review_complete"] is False
    assert boundaries["text_mode_private_pilot_eligible"] is False
    assert boundaries["audio_scope_deferred"] is True
    assert boundaries["audio_scope_complete"] is False
    assert boundaries["no_a2_a2plus_expansion"] is True
    assert boundaries["no_persistent_learner_state_write"] is True
