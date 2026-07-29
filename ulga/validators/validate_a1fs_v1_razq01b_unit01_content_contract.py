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

    vocabulary = contract.get("vocabulary_contract", {})
    active = vocabulary.get("active_vocabulary", [])
    _require(isinstance(active, list) and len(active) == 16, "active_vocabulary_count_invalid")
    active_lemmas = [str(row.get("lemma") or "") for row in active if isinstance(row, Mapping)]
    _require(len(active_lemmas) == len(set(active_lemmas)) == 16, "active_vocabulary_not_unique")
    _require(all(row.get("cefr_level") == "A1" for row in active), "active_vocabulary_not_all_a1")
    _require(all(row.get("part_of_speech") == "noun" for row in active), "active_vocabulary_pos_invalid")
    _require(all(row.get("production_required") is True for row in active), "active_vocabulary_production_invalid")
    _require(all(str(row.get("evp_sense_id") or "").startswith("vocabulary:") for row in active), "active_vocabulary_evp_ref_invalid")
    _require("toy" not in set(active_lemmas), "a2_toy_must_not_be_active")
    for row in active:
        lemma = str(row["lemma"])
        indefinite = str(row.get("memory_form_indefinite") or "")
        definite = str(row.get("memory_form_definite") or "")
        _require(indefinite.endswith(lemma), f"indefinite_memory_form_invalid:{lemma}")
        _require(definite == f"the {lemma}", f"definite_memory_form_invalid:{lemma}")
    memory_sets = vocabulary.get("memory_sets", [])
    _require(len(memory_sets) == 4, "memory_set_count_invalid")
    flattened = [lemma for group in memory_sets for lemma in group.get("lemmas", [])]
    _require(len(flattened) == 16 and set(flattened) == set(active_lemmas), "memory_sets_do_not_partition_active_vocabulary")
    _require(all(len(group.get("lemmas", [])) == 4 for group in memory_sets), "memory_set_size_invalid")
    receptive = vocabulary.get("receptive_vocabulary", [])
    toy = next((row for row in receptive if row.get("lemma") == "toy"), None)
    _require(isinstance(toy, Mapping), "toy_receptive_bridge_missing")
    _require(toy.get("cefr_level") == "A2" and toy.get("role") == "PICTURE_SUPPORTED_RECEPTIVE_BRIDGE", "toy_bridge_policy_invalid")
    _require(toy.get("production_required") is False, "toy_production_forbidden")

    chunks = contract.get("chunk_contract", {})
    canonical_chunks = chunks.get("canonical_chunks", [])
    _require([row.get("chunk_id") for row in canonical_chunks] == [row[0] for row in builder.CANONICAL_CHUNKS], "canonical_chunk_ids_invalid")
    _require(all(row.get("cefr_level") == "A1" for row in canonical_chunks), "canonical_chunk_level_invalid")
    phrases = chunks.get("instructional_phrases", [])
    _require(len(phrases) == len(builder.INSTRUCTIONAL_PHRASES), "instructional_phrase_count_invalid")
    _require(all(row.get("canonical_chunk_claimed") is False for row in phrases), "instructional_phrase_false_canonical_claim")

    frames = contract.get("sentence_frame_contract", {})
    _require(len(frames.get("core_frames", [])) == 6, "core_frame_count_invalid")
    _require(len(frames.get("scaffold_only_frames", [])) == 2, "scaffold_frame_count_invalid")
    _require(all("SCAFFOLD_ONLY" in str(row.get("role") or "") for row in frames.get("scaffold_only_frames", [])), "scaffold_boundary_invalid")

    material = contract.get("material_contract", {})
    source = material.get("source_policy", {})
    _require(source.get("direct_use_raz_levels") == list("ABCDEFGHI"), "direct_level_policy_invalid")
    _require(source.get("rewrite_only_raz_levels") == list("JKLMNOPQRSTUVW"), "rewrite_level_policy_invalid")
    _require(source.get("raw_raz_text_learner_facing_copy_allowed") is False, "raw_raz_copy_forbidden")
    gate = material.get("window_gate", {})
    expected_gate = {
        "sentence_count_max": 3,
        "word_count_max": 45,
        "target_article_hit_min": 1,
        "active_vocabulary_hit_min": 1,
        "known_content_word_ratio_min": 0.85,
        "unknown_content_word_unique_max": 2,
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
        "A cat is near the door.", contract=contract, known_lexicon=["is"],
        source_level="A", lineage_complete=True,
    )
    _require(positive["classification"] == "PASS", "positive_material_gate_failed")
    blocked = builder.evaluate_material_window(
        "A cat was called a predator.", contract=contract,
        known_lexicon=["was", "called", "predator"],
        blocked_features=["past_simple", "passive"], source_level="A",
        lineage_complete=True,
    )
    _require(blocked["classification"] != "PASS", "blocked_material_false_pass")
    no_active = builder.evaluate_material_window(
        "A friend is here.", contract=contract, known_lexicon=["friend", "is"],
        source_level="A", lineage_complete=True,
    )
    _require(no_active["classification"] != "PASS", "active_vocabulary_gate_missing")

    return {
        "validator_id": VALIDATOR_ID,
        "validation_status": PASS_STATUS,
        "error_count": 0,
        "unit_id": builder.UNIT_ID,
        "active_vocabulary_count": len(active),
        "receptive_vocabulary_count": len(receptive),
        "canonical_chunk_count": len(canonical_chunks),
        "instructional_phrase_count": len(phrases),
        "core_sentence_frame_count": len(frames.get("core_frames", [])),
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
    print(f"ACTIVE_VOCABULARY={report['active_vocabulary_count']}")
    print(f"OPERATOR_REVIEW_STATUS={report['operator_review_status']}")
    print(f"NEXT_SHORT_STEP={report['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
