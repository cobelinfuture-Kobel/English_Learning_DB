from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as builder
from ulga.validators import validate_a1fs_v1_razq01b_unit01_content_contract as validator


def test_committed_contract_is_deterministic_and_valid() -> None:
    root = Path(__file__).resolve().parents[2]
    path = root / builder.DEFAULT_OUTPUT
    committed = json.loads(path.read_text(encoding="utf-8"))
    assert committed == builder.build_contract()
    report = validator.validate_contract(committed)
    assert report["validation_status"] == validator.PASS_STATUS
    assert report["operator_review_status"] == "PENDING"


def test_active_nouns_are_memorizable_a1_partition() -> None:
    contract = builder.build_contract()
    vocabulary = contract["vocabulary_contract"]
    active = vocabulary["active_vocabulary"]
    lemmas = {row["lemma"] for row in active}
    assert len(active) == 16
    assert all(row["cefr_level"] == "A1" for row in active)
    assert all(row["part_of_speech"] == "noun" for row in active)
    assert all(row["production_required"] and row["spelling_required"] for row in active)
    assert all(row["memory_form_definite"] == f"the {row['lemma']}" for row in active)
    assert "toy" not in lemmas
    noun_sets = [row for row in vocabulary["memory_sets"] if row["part_of_speech"] == "noun"]
    assert len(noun_sets) == 4
    assert all(len(row["lemmas"]) == 4 for row in noun_sets)
    assert {lemma for row in noun_sets for lemma in row["lemmas"]} == lemmas


def test_active_adjectives_are_exact_verified_evp_a1_senses() -> None:
    adjectives = builder.build_contract()["vocabulary_contract"]["active_adjectives"]
    by_lemma = {row["lemma"]: row for row in adjectives}
    assert set(by_lemma) == {"big", "small", "red", "blue", "new", "old"}
    assert by_lemma["big"]["evp_sense_id"] == "vocabulary:big:v_1389"
    assert by_lemma["blue"]["evp_sense_id"] == "vocabulary:blue:v_1396"
    assert by_lemma["new"]["evp_sense_id"] == "vocabulary:new:v_6046"
    assert by_lemma["old"]["evp_sense_id"] == "vocabulary:old:v_6073"
    assert by_lemma["red"]["evp_sense_id"] == "vocabulary:red:v_7741"
    assert by_lemma["small"]["evp_sense_id"] == "vocabulary:small:v_9335"
    assert all(row["cefr_level"] == "A1" for row in adjectives)
    assert all(row["part_of_speech"] == "adjective" for row in adjectives)
    assert all(row["production_required"] and row["spelling_required"] for row in adjectives)
    assert by_lemma["old"]["memory_phrase"] == "an old book"


def test_total_memorization_count_and_adjective_set() -> None:
    vocabulary = builder.build_contract()["vocabulary_contract"]
    assert vocabulary["active_noun_memorization_count"] == 16
    assert vocabulary["active_adjective_memorization_count"] == 6
    assert vocabulary["active_memorization_count"] == 22
    adjective_sets = [row for row in vocabulary["memory_sets"] if row["part_of_speech"] == "adjective"]
    assert len(adjective_sets) == 1
    assert set(adjective_sets[0]["lemmas"]) == {"big", "small", "red", "blue", "new", "old"}


def test_a2_toy_is_receptive_bridge_only() -> None:
    contract = builder.build_contract()
    receptive = contract["vocabulary_contract"]["receptive_vocabulary"]
    toy = next(row for row in receptive if row["lemma"] == "toy")
    assert toy["cefr_level"] == "A2"
    assert toy["role"] == "PICTURE_SUPPORTED_RECEPTIVE_BRIDGE"
    assert toy["production_required"] is False
    assert "toy" not in builder.active_lemmas(contract)
    assert "toy" not in builder.receptive_lemmas(contract)
    assert "toy" in builder.receptive_lemmas(contract, include_a2_bridge=True)


def test_chunks_and_instructional_phrases_preserve_authority_boundaries() -> None:
    chunks = builder.build_contract()["chunk_contract"]
    assert [row["chunk_id"] for row in chunks["canonical_chunks"]] == [
        "EVP_CHUNK_000003",
        "EVP_CHUNK_000054",
        "EVP_CHUNK_000075",
    ]
    ice_cream = next(row for row in chunks["canonical_chunks"] if row["chunk_id"] == "EVP_CHUNK_000054")
    assert ice_cream["direct_unit01_use_allowed"] is False
    assert ice_cream["unit01_role"] == "COUNTABILITY_SENSITIVE_RECEPTIVE_ONLY"
    assert all(row["canonical_chunk_claimed"] is False for row in chunks["instructional_phrases"])
    assert all(row["canonical_chunk_claimed"] is False for row in chunks["adjective_instructional_phrases"])
    forms = {row["surface_form"] for row in chunks["adjective_instructional_phrases"]}
    assert {"a big box", "an old book", "a very old book"} <= forms


def test_egp_rows_have_operational_adjective_support() -> None:
    contract = builder.build_contract()
    grammar = contract["grammar_contract"]
    assert len(grammar["core_focus_egp_row_ids"]) == 2
    assert len(grammar["guided_extension_egp_row_ids"]) == 1
    assert len(grammar["deferred_not_assessed_egp_row_ids"]) == 7
    assert grammar["guided_functions"] == ["a + very + adjective + singular countable noun"]
    assert "an old book" in grammar["article_selection_rule"]
    assert "a very old book" in grammar["article_selection_rule"]
    assert len(contract["sentence_frame_contract"]["adjective_expansion_frames"]) == 3


def test_context_families_separate_nouns_adjectives_and_receptive_words() -> None:
    contract = builder.build_contract()
    nouns = builder.active_noun_lemmas(contract)
    adjectives = builder.active_adjective_lemmas(contract)
    receptive = builder.receptive_lemmas(contract)
    contexts = contract["material_contract"]["context_families"]
    assert len(contexts) == 4
    assert all(set(row["active_lemmas"]) <= nouns for row in contexts)
    assert all(set(row["active_adjectives"]) <= adjectives for row in contexts)
    assert all(set(row["receptive_lemmas"]) <= receptive for row in contexts)
    home = next(row for row in contexts if row["context_id"] == "U01-C2-HOME-ROOM")
    assert "home" in home["receptive_lemmas"]
    assert "home" not in home["active_lemmas"]


def test_core_and_adjective_frames_declare_scaffold_grammar() -> None:
    frames = builder.build_contract()["sentence_frame_contract"]
    assert all(row["scaffold_grammar_refs"] for row in frames["core_frames"])
    assert all(row["assessment_scope"] == "ARTICLE_SELECTION_AND_NOUN_PHRASE_ONLY" for row in frames["core_frames"])
    assert all(row["scaffold_grammar_refs"] for row in frames["adjective_expansion_frames"])
    assert all(
        row["assessment_scope"] == "ARTICLE_SELECTION_BEFORE_ADJECTIVE_AND_ADJECTIVE_NOUN_PHRASE"
        for row in frames["adjective_expansion_frames"]
    )


@pytest.mark.parametrize(
    ("text", "expected_phrase"),
    [
        ("A red book is on the desk.", "a red book"),
        ("An old book is on the desk.", "an old book"),
    ],
)
def test_material_gate_passes_direct_adjective_noun_windows(text: str, expected_phrase: str) -> None:
    result = builder.evaluate_material_window(
        text,
        contract=builder.build_contract(),
        known_lexicon=["is"],
        source_level="A",
        lineage_complete=True,
    )
    assert result["classification"] == "PASS"
    assert expected_phrase in result["adjective_noun_phrases"]
    assert "ADJECTIVE_NOUN_PHRASE_SOURCE" in result["material_roles"]


def test_material_gate_applies_pronounced_sound_to_a_an() -> None:
    contract = builder.build_contract()
    wrong = builder.evaluate_material_window(
        "A old book is on the desk.",
        contract=contract,
        known_lexicon=["is"],
        source_level="A",
        lineage_complete=True,
    )
    assert wrong["classification"] == "REJECT"
    assert "INDEFINITE_ARTICLE_SOUND_MISMATCH" in wrong["reasons"]
    right = builder.evaluate_material_window(
        "A very old book is on the desk.",
        contract=contract,
        known_lexicon=["is"],
        source_level="A",
        lineage_complete=True,
    )
    assert right["classification"] == "PASS"
    assert right["very_adjective_noun_phrases"] == ["a very old book"]
    assert "GUIDED_VERY_ADJECTIVE_SOURCE" in right["material_roles"]


def test_material_gate_rejects_theme_only_or_blocked_grammar() -> None:
    contract = builder.build_contract()
    theme_only = builder.evaluate_material_window(
        "A friend is here.",
        contract=contract,
        known_lexicon=["friend", "is"],
        source_level="A",
        lineage_complete=True,
    )
    assert theme_only["classification"] == "REJECT"
    assert "ACTIVE_NOUN_HIT_MISSING" in theme_only["reasons"]
    blocked = builder.evaluate_material_window(
        "A red book was called important.",
        contract=contract,
        known_lexicon=["was", "called", "important"],
        blocked_features=["past_simple", "passive"],
        source_level="A",
        lineage_complete=True,
    )
    assert blocked["classification"] == "REJECT"
    assert "BLOCKED_GRAMMAR_PRESENT" in blocked["reasons"]


def test_rewrite_levels_never_pass_directly_but_need_target_and_lineage() -> None:
    contract = builder.build_contract()
    candidate = builder.evaluate_material_window(
        "A red book is on the desk.",
        contract=contract,
        known_lexicon=["is"],
        source_level="J",
        lineage_complete=True,
    )
    assert candidate["classification"] == "BORDERLINE"
    assert "REWRITE_ONLY_SOURCE_LEVEL" in candidate["reasons"]
    missing_lineage = builder.evaluate_material_window(
        "A red book is on the desk.",
        contract=contract,
        known_lexicon=["is"],
        source_level="J",
        lineage_complete=False,
    )
    assert missing_lineage["classification"] == "REJECT"


def test_validator_fails_closed_on_digest_or_boundary_drift() -> None:
    contract = builder.build_contract()
    drifted = deepcopy(contract)
    drifted["boundaries"]["a2_unlocked"] = True
    with pytest.raises(ValueError, match="contract_digest_invalid"):
        validator.validate_contract(drifted)
    drifted_core = {key: deepcopy(value) for key, value in drifted.items() if key != "contract_sha256"}
    drifted["contract_sha256"] = builder.digest(drifted_core)
    with pytest.raises(validator.ContractValidationError, match="boundary_invalid:a2_unlocked"):
        validator.validate_contract(drifted)
