#!/usr/bin/env python3
"""Validate the executable Unit01 vocabulary/chunk/frame/material contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as builder

VALIDATOR_ID = "A1FS_V1_RAZQ01B_UNIT01_CONTENT_CONTRACT_VALIDATOR"
PASS_STATUS = "PASS_A1FS_V1_RAZQ01B_UNIT01_CONTENT_CONTRACT"


class ContractValidationError(ValueError):
    pass


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ContractValidationError(code)


def validate_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(contract, Mapping), "contract_object_required")
    builder.verify_contract_digest(contract)
    _require(contract.get("schema_version") == builder.SCHEMA_VERSION, "schema_version_invalid")
    _require(contract.get("task_id") == builder.TASK_ID, "task_id_invalid")
    _require(contract.get("unit_id") == builder.UNIT_ID, "unit_id_invalid")
    _require(contract.get("level_scope") == ["A1"], "level_scope_invalid")
    review = contract.get("operator_review", {})
    _require(review.get("required") is True, "operator_review_required")
    _require(review.get("decision_status") == "PENDING", "candidate_contract_must_remain_pending")
    _require("ACTIVE_ADJECTIVES" in set(review.get("review_dimensions", [])), "active_adjective_review_dimension_missing")

    grammar = contract.get("grammar_contract", {})
    core = set(grammar.get("core_focus_egp_row_ids", []))
    guided = set(grammar.get("guided_extension_egp_row_ids", []))
    deferred = set(grammar.get("deferred_not_assessed_egp_row_ids", []))
    expected = set(builder.CORE_EGP_ROWS) | set(builder.GUIDED_EGP_ROWS) | set(builder.DEFERRED_EGP_ROWS)
    _require(core == set(builder.CORE_EGP_ROWS), "core_egp_rows_invalid")
    _require(guided == set(builder.GUIDED_EGP_ROWS), "guided_egp_rows_invalid")
    _require(deferred == set(builder.DEFERRED_EGP_ROWS), "deferred_egp_rows_invalid")
    _require(not (core & guided or core & deferred or guided & deferred), "egp_stages_overlap")
    _require(core | guided | deferred == expected, "egp_stage_coverage_invalid")
    _require("DOES_NOT_CLAIM" in str(grammar.get("claim_boundary") or ""), "egp_claim_boundary_missing")
    _require(
        grammar.get("article_selection_rule")
        == "Select a/an from the first pronounced sound after the article: an old book, but a very old book.",
        "article_selection_rule_invalid",
    )
    _require(grammar.get("guided_functions") == ["a + very + adjective + singular countable noun"], "guided_function_invalid")

    vocabulary = contract.get("vocabulary_contract", {})
    active_nouns = vocabulary.get("active_vocabulary", [])
    _require(isinstance(active_nouns, list) and len(active_nouns) == 16, "active_noun_count_invalid")
    noun_lemmas = [str(row.get("lemma") or "") for row in active_nouns if isinstance(row, Mapping)]
    _require(len(noun_lemmas) == len(set(noun_lemmas)) == 16, "active_nouns_not_unique")
    _require(all(row.get("cefr_level") == "A1" for row in active_nouns), "active_nouns_not_all_a1")
    _require(all(row.get("part_of_speech") == "noun" for row in active_nouns), "active_noun_pos_invalid")
    _require(all(row.get("production_required") is True for row in active_nouns), "active_noun_production_invalid")
    _require(all(str(row.get("evp_sense_id") or "").startswith("vocabulary:") for row in active_nouns), "active_noun_evp_ref_invalid")
    _require("toy" not in set(noun_lemmas), "a2_toy_must_not_be_active")
    for row in active_nouns:
        lemma = str(row["lemma"])
        _require(str(row.get("memory_form_indefinite") or "").endswith(lemma), f"indefinite_memory_form_invalid:{lemma}")
        _require(row.get("memory_form_definite") == f"the {lemma}", f"definite_memory_form_invalid:{lemma}")

    active_adjectives = vocabulary.get("active_adjectives", [])
    _require(isinstance(active_adjectives, list) and len(active_adjectives) == 6, "active_adjective_count_invalid")
    adjective_lemmas = [str(row.get("lemma") or "") for row in active_adjectives if isinstance(row, Mapping)]
    _require(set(adjective_lemmas) == {"big", "small", "red", "blue", "new", "old"}, "active_adjective_set_invalid")
    _require(all(row.get("cefr_level") == "A1" for row in active_adjectives), "active_adjectives_not_all_a1")
    _require(all(row.get("part_of_speech") == "adjective" for row in active_adjectives), "active_adjective_pos_invalid")
    _require(all(row.get("production_required") is True for row in active_adjectives), "active_adjective_production_invalid")
    expected_adjectives = {
        "big": ("vocabulary:big:v_1389", "SIZE", 1389, "a big box"),
        "blue": ("vocabulary:blue:v_1396", "COLOUR", 1396, "a blue bag"),
        "new": ("vocabulary:new:v_6046", "RECENTLY CREATED", 6046, "a new book"),
        "old": ("vocabulary:old:v_6073", "EXISTED MANY YEARS", 6073, "an old book"),
        "red": ("vocabulary:red:v_7741", "COLOUR", 7741, "a red book"),
        "small": ("vocabulary:small:v_9335", "LITTLE", 9335, "a small bag"),
    }
    for row in active_adjectives:
        lemma = str(row["lemma"])
        expected_sense, expected_guideword, expected_row, expected_phrase = expected_adjectives[lemma]
        _require(row.get("evp_sense_id") == expected_sense, f"adjective_evp_id_invalid:{lemma}")
        _require(row.get("evp_guideword") == expected_guideword, f"adjective_guideword_invalid:{lemma}")
        _require(row.get("evp_source_sheet") == "total(15696)", f"adjective_source_sheet_invalid:{lemma}")
        _require(row.get("evp_source_row") == expected_row, f"adjective_source_row_invalid:{lemma}")
        _require(row.get("memory_phrase") == expected_phrase, f"adjective_memory_phrase_invalid:{lemma}")

    _require(vocabulary.get("active_noun_memorization_count") == 16, "active_noun_memorization_count_invalid")
    _require(vocabulary.get("active_adjective_memorization_count") == 6, "active_adjective_memorization_count_invalid")
    _require(vocabulary.get("active_memorization_count") == 22, "active_total_memorization_count_invalid")
    memory_sets = vocabulary.get("memory_sets", [])
    _require(len(memory_sets) == 5, "memory_set_count_invalid")
    noun_sets = [row for row in memory_sets if row.get("part_of_speech") == "noun"]
    adjective_sets = [row for row in memory_sets if row.get("part_of_speech") == "adjective"]
    _require(len(noun_sets) == 4 and all(len(row.get("lemmas", [])) == 4 for row in noun_sets), "noun_memory_sets_invalid")
    _require({lemma for row in noun_sets for lemma in row.get("lemmas", [])} == set(noun_lemmas), "noun_memory_sets_do_not_partition")
    _require(len(adjective_sets) == 1 and set(adjective_sets[0].get("lemmas", [])) == set(adjective_lemmas), "adjective_memory_set_invalid")

    receptive = vocabulary.get("receptive_vocabulary", [])
    toy = next((row for row in receptive if row.get("lemma") == "toy"), None)
    _require(isinstance(toy, Mapping), "toy_receptive_bridge_missing")
    _require(toy.get("cefr_level") == "A2" and toy.get("role") == "PICTURE_SUPPORTED_RECEPTIVE_BRIDGE", "toy_bridge_policy_invalid")
    _require(toy.get("production_required") is False, "toy_production_forbidden")

    chunks = contract.get("chunk_contract", {})
    canonical_chunks = chunks.get("canonical_chunks", [])
    _require([row.get("chunk_id") for row in canonical_chunks] == [row[0] for row in builder.CANONICAL_CHUNKS], "canonical_chunk_ids_invalid")
    _require(all(row.get("cefr_level") == "A1" for row in canonical_chunks), "canonical_chunk_level_invalid")
    ice_cream = next(row for row in canonical_chunks if row.get("chunk_id") == "EVP_CHUNK_000054")
    _require(ice_cream.get("direct_unit01_use_allowed") is False, "ice_cream_countability_boundary_missing")
    _require(ice_cream.get("unit01_role") == "COUNTABILITY_SENSITIVE_RECEPTIVE_ONLY", "ice_cream_role_invalid")
    phrases = chunks.get("instructional_phrases", [])
    _require(len(phrases) == len(builder.INSTRUCTIONAL_PHRASES), "instructional_phrase_count_invalid")
    _require(all(row.get("canonical_chunk_claimed") is False for row in phrases), "instructional_phrase_false_canonical_claim")
    adjective_phrases = chunks.get("adjective_instructional_phrases", [])
    _require(len(adjective_phrases) == len(builder.ADJECTIVE_INSTRUCTIONAL_PHRASES), "adjective_phrase_count_invalid")
    _require(all(row.get("canonical_chunk_claimed") is False for row in adjective_phrases), "adjective_phrase_false_canonical_claim")
    _require("an old book" in {row.get("surface_form") for row in adjective_phrases}, "old_article_memory_phrase_missing")
    _require("a very old book" in {row.get("surface_form") for row in adjective_phrases}, "very_old_article_memory_phrase_missing")

    frames = contract.get("sentence_frame_contract", {})
    core_frames = frames.get("core_frames", [])
    adjective_frames = frames.get("adjective_expansion_frames", [])
    _require(len(core_frames) == 6, "core_frame_count_invalid")
    _require(all(row.get("scaffold_grammar_refs") for row in core_frames), "core_frame_scaffold_refs_missing")
    _require(all(row.get("assessment_scope") == "ARTICLE_SELECTION_AND_NOUN_PHRASE_ONLY" for row in core_frames), "core_frame_assessment_scope_invalid")
    _require(len(adjective_frames) == 3, "adjective_frame_count_invalid")
    _require(all(row.get("scaffold_grammar_refs") for row in adjective_frames), "adjective_frame_scaffold_refs_missing")
    _require(all(row.get("assessment_scope") == "ARTICLE_SELECTION_BEFORE_ADJECTIVE_AND_ADJECTIVE_NOUN_PHRASE" for row in adjective_frames), "adjective_frame_assessment_scope_invalid")
    _require({row.get("egp_role") for row in adjective_frames} == {"DIRECT_ADJECTIVE_NOUN", "GUIDED_VERY_ADJECTIVE_NOUN"}, "adjective_frame_egp_roles_invalid")
    _require(len(frames.get("scaffold_only_frames", [])) == 2, "scaffold_frame_count_invalid")
    _require(all("SCAFFOLD_ONLY" in str(row.get("role") or "") for row in frames.get("scaffold_only_frames", [])), "scaffold_boundary_invalid")

    material = contract.get("material_contract", {})
    noun_set = set(noun_lemmas)
    adjective_set = set(adjective_lemmas)
    receptive_set = {str(row.get("lemma") or "") for row in receptive if row.get("cefr_level") == "A1"}
    contexts = material.get("context_families", [])
    _require(len(contexts) == 4, "context_family_count_invalid")
    for context in contexts:
        _require(set(context.get("active_lemmas", [])) <= noun_set, f"context_active_noun_invalid:{context.get('context_id')}")
        _require(set(context.get("active_adjectives", [])) <= adjective_set, f"context_active_adjective_invalid:{context.get('context_id')}")
        _require(set(context.get("receptive_lemmas", [])) <= receptive_set, f"context_receptive_lemma_invalid:{context.get('context_id')}")
    source = material.get("source_policy", {})
    _require(source.get("direct_use_raz_levels") == list("ABCDEFGHI"), "direct_level_policy_invalid")
    _require(source.get("rewrite_only_raz_levels") == list("JKLMNOPQRSTUVW"), "rewrite_level_policy_invalid")
    _require(source.get("raw_raz_text_learner_facing_copy_allowed") is False, "raw_raz_copy_forbidden")
    gate = material.get("window_gate", {})
    expected_gate = {
        "sentence_count_max": 3,
        "word_count_max": 45,
        "target_article_phrase_hit_min": 1,
        "active_noun_hit_min": 1,
        "known_content_word_ratio_min": 0.85,
        "unknown_content_word_unique_max": 2,
        "indefinite_article_sound_error_max": 0,
        "blocked_grammar_feature_max": 0,
        "semantic_group_lineage_required": True,
        "theme_only_match_is_pass": False,
    }
    for key, value in expected_gate.items():
        _require(gate.get(key) == value, f"material_gate_invalid:{key}")

    boundaries = contract.get("boundaries", {})
    for key in (
        "unit02_to_unit24_modified",
        "canonical_question_bank_written",
        "learner_facing_content_written",
        "audio_enabled",
        "speaking_capture_enabled",
        "a2_unlocked",
        "parallel_curriculum_created",
    ):
        _require(boundaries.get(key) is False, f"boundary_invalid:{key}")

    positive = builder.evaluate_material_window(
        "A red book is on the desk.",
        contract=contract,
        known_lexicon=["is"],
        source_level="A",
        lineage_complete=True,
    )
    _require(positive["classification"] == "PASS", "positive_adjective_material_gate_failed")
    _require(positive["adjective_noun_phrases"] == ["a red book"], "adjective_phrase_detection_failed")
    old = builder.evaluate_material_window(
        "An old book is on the desk.",
        contract=contract,
        known_lexicon=["is"],
        source_level="A",
        lineage_complete=True,
    )
    _require(old["classification"] == "PASS", "old_article_sound_gate_failed")
    wrong_old = builder.evaluate_material_window(
        "A old book is on the desk.",
        contract=contract,
        known_lexicon=["is"],
        source_level="A",
        lineage_complete=True,
    )
    _require(wrong_old["classification"] != "PASS", "wrong_old_article_false_pass")
    _require("INDEFINITE_ARTICLE_SOUND_MISMATCH" in wrong_old["reasons"], "old_article_error_not_reported")
    very_old = builder.evaluate_material_window(
        "A very old book is on the desk.",
        contract=contract,
        known_lexicon=["is"],
        source_level="A",
        lineage_complete=True,
    )
    _require(very_old["classification"] == "PASS", "very_old_article_gate_failed")
    _require(very_old["very_adjective_noun_phrases"] == ["a very old book"], "very_adjective_phrase_detection_failed")
    blocked = builder.evaluate_material_window(
        "A red book was called important.",
        contract=contract,
        known_lexicon=["was", "called", "important"],
        blocked_features=["past_simple", "passive"],
        source_level="A",
        lineage_complete=True,
    )
    _require(blocked["classification"] != "PASS", "blocked_material_false_pass")
    no_active = builder.evaluate_material_window(
        "A friend is here.",
        contract=contract,
        known_lexicon=["friend", "is"],
        source_level="A",
        lineage_complete=True,
    )
    _require(no_active["classification"] != "PASS", "active_noun_gate_missing")

    return {
        "validator_id": VALIDATOR_ID,
        "validation_status": PASS_STATUS,
        "error_count": 0,
        "unit_id": builder.UNIT_ID,
        "active_noun_count": len(active_nouns),
        "active_adjective_count": len(active_adjectives),
        "active_memorization_count": vocabulary.get("active_memorization_count"),
        "receptive_vocabulary_count": len(receptive),
        "canonical_chunk_count": len(canonical_chunks),
        "instructional_phrase_count": len(phrases),
        "adjective_instructional_phrase_count": len(adjective_phrases),
        "core_sentence_frame_count": len(core_frames),
        "adjective_sentence_frame_count": len(adjective_frames),
        "contract_sha256": contract["contract_sha256"],
        "operator_review_status": review["decision_status"],
        "next_short_step": builder.NEXT_SHORT_STEP,
    }


def load_and_validate(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractValidationError(f"contract_unreadable:{exc}") from exc
    return validate_contract(value)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=builder.DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        report = load_and_validate(args.contract)
    except (ContractValidationError, ValueError, KeyError, TypeError) as exc:
        print("STATUS=FAIL_A1FS_V1_RAZQ01B_UNIT01_CONTENT_CONTRACT")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={report['validation_status']}")
    print(f"ACTIVE_NOUNS={report['active_noun_count']}")
    print(f"ACTIVE_ADJECTIVES={report['active_adjective_count']}")
    print(f"ACTIVE_TOTAL={report['active_memorization_count']}")
    print(f"OPERATOR_REVIEW_STATUS={report['operator_review_status']}")
    print(f"NEXT_SHORT_STEP={report['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
