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
    assert report["context_family_count"] == 4


def test_active_vocabulary_is_memorizable_a1_partition() -> None:
    contract = builder.build_contract()
    vocabulary = contract["vocabulary_contract"]
    active = vocabulary["active_vocabulary"]
    lemmas = {row["lemma"] for row in active}
    assert len(active) == 16
    assert all(row["cefr_level"] == "A1" for row in active)
    assert all(row["production_required"] and row["spelling_required"] for row in active)
    assert all(row["memory_form_definite"] == f"the {row['lemma']}" for row in active)
    assert "toy" not in lemmas
    assert "home" not in lemmas
    memory_sets = vocabulary["memory_sets"]
    assert len(memory_sets) == 4
    assert all(len(row["lemmas"]) == 4 for row in memory_sets)
    assert {lemma for row in memory_sets for lemma in row["lemmas"]} == lemmas


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


def test_chunks_and_instructional_phrases_do_not_create_false_authority() -> None:
    contract = builder.build_contract()
    chunks = contract["chunk_contract"]
    assert [row["chunk_id"] for row in chunks["canonical_chunks"]] == [
        "EVP_CHUNK_000003",
        "EVP_CHUNK_000054",
        "EVP_CHUNK_000075",
    ]
    assert all(row["cefr_level"] == "A1" for row in chunks["canonical_chunks"])
    assert all(row["canonical_chunk_claimed"] is False for row in chunks["instructional_phrases"])


def test_egp_rows_are_staged_without_unsupported_guided_claim() -> None:
    grammar = builder.build_contract()["grammar_contract"]
    core = set(grammar["core_focus_egp_row_ids"])
    guided = set(grammar["guided_extension_egp_row_ids"])
    deferred = set(grammar["deferred_not_assessed_egp_row_ids"])
    assert len(core) == 2
    assert len(guided) == 1
    assert len(deferred) == 7
    assert "1741163708789x819248395543273500" not in guided
    assert "1741163708789x819248395543273500" in deferred
    assert not (core & guided or core & deferred or guided & deferred)
    assert "DOES_NOT_CLAIM" in grammar["claim_boundary"]


def test_core_frames_declare_scaffold_grammar_and_article_only_assessment() -> None:
    frames = builder.build_contract()["sentence_frame_contract"]["core_frames"]
    assert len(frames) == 6
    assert all(row["scaffold_grammar_refs"] for row in frames)
    assert all(row["assessment_scope"] == "ARTICLE_SELECTION_AND_NOUN_PHRASE_ONLY" for row in frames)
    by_id = {row["frame_id"]: row for row in frames}
    assert "GRAMMAR_DEMONSTRATIVES_CONTRAST" in by_id["U01-F01"]["scaffold_grammar_refs"]
    assert "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS" in by_id["U01-F02"]["scaffold_grammar_refs"]
    assert "GRAMMAR_CAN_STATEMENT" in by_id["U01-F06"]["scaffold_grammar_refs"]


def test_context_families_separate_active_and_receptive_lemmas() -> None:
    contract = builder.build_contract()
    active = builder.active_lemmas(contract)
    receptive = builder.receptive_lemmas(contract)
    contexts = contract["material_contract"]["context_families"]
    assert len(contexts) == 4
    for context in contexts:
        assert set(context["active_lemmas"]) <= active
        assert set(context["receptive_lemmas"]) <= receptive
        assert not (set(context["active_lemmas"]) & set(context["receptive_lemmas"]))
    home = next(row for row in contexts if row["context_id"] == "U01-C2-HOME-ROOM")
    assert "home" not in home["active_lemmas"]
    assert "home" in home["receptive_lemmas"]


def test_material_gate_passes_simple_active_vocabulary_window() -> None:
    result = builder.evaluate_material_window(
        "A cat is near the door.",
        contract=builder.build_contract(),
        known_lexicon=["is"],
        source_level="A",
        lineage_complete=True,
    )
    assert result["classification"] == "PASS"
    assert result["active_vocabulary_hits"] == ["cat", "door"]
    assert result["article_hit_count"] == 2


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
    assert "ACTIVE_VOCABULARY_HIT_MISSING" in theme_only["reasons"]
    blocked = builder.evaluate_material_window(
        "A cat was called a predator.",
        contract=contract,
        known_lexicon=["was", "called", "predator"],
        blocked_features=["past_simple", "passive"],
        source_level="A",
        lineage_complete=True,
    )
    assert blocked["classification"] == "REJECT"
    assert "BLOCKED_GRAMMAR_PRESENT" in blocked["reasons"]


def test_rewrite_levels_never_pass_directly() -> None:
    result = builder.evaluate_material_window(
        "A cat is near the door.",
        contract=builder.build_contract(),
        known_lexicon=["is"],
        source_level="J",
        lineage_complete=True,
    )
    assert result["classification"] == "BORDERLINE"
    assert "REWRITE_ONLY_SOURCE_LEVEL" in result["reasons"]


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
