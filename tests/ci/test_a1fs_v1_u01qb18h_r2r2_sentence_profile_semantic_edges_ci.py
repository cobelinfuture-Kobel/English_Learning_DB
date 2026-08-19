from __future__ import annotations

from collections import Counter

from ulga.builders import (
    build_a1fs_v1_u01qb18h_r2r2_unit01_sentence_pool_driven_production_capacity_reconciliation
    as builder,
)


def _slot(*, entity_id: str, surface: str, determiner: str, semantic_role: str) -> dict[str, object]:
    return {
        "entity_id": entity_id,
        "canonical_surface": surface,
        "np_surface": f"{determiner} {surface}",
        "surface": f"{determiner} {surface}",
        "determiner": determiner.casefold(),
        "modifiers": [],
        "very": False,
        "structure": "NOUN",
        "char_start": 0,
        "char_end": len(surface),
        "syntactic_role": semantic_role,
        "semantic_role": semantic_role,
    }


def test_sentence_entity_lineage_does_not_invent_missing_vocabulary_authority() -> None:
    vocabulary = builder._unit01_vocabulary_authority()
    slot = _slot(
        entity_id="ROBOT",
        surface="robot",
        determiner="A",
        semantic_role="RELATION_SUBJECT",
    )
    target = builder._slot_target(slot, vocabulary)
    assert target is not None
    noun, vocabulary_ref, entity_id = target
    assert noun == "robot"
    assert entity_id == "ROBOT"
    assert vocabulary_ref == vocabulary.get("robot", "")


def test_relation_object_is_not_misidentified_as_known_referent() -> None:
    vocabulary = builder._unit01_vocabulary_authority()
    first = {
        "sentence_id": "FIRST-ROBOT",
        "text": "A robot is in the shop window.",
        "canonical_admission_status": "ADMITTED",
        "np_slots": [
            _slot(entity_id="ROBOT", surface="robot", determiner="A", semantic_role="RELATION_SUBJECT"),
            _slot(entity_id="SHOP_WINDOW", surface="shop window", determiner="the", semantic_role="RELATION_OBJECT"),
        ],
        "discourse_capability": ["FIRST_MENTION"],
        "task_use_capability": ["WRITING"],
        "source_kind": "CANONICAL_SCENE_DERIVED",
        "relation_capability": ["IN"],
        "legacy_unnormalized": False,
    }
    known = {
        "sentence_id": "KNOWN-ROBOT",
        "text": "The robot is in the shop window.",
        "canonical_admission_status": "ADMITTED",
        "np_slots": [
            _slot(entity_id="ROBOT", surface="robot", determiner="The", semantic_role="RELATION_SUBJECT"),
            _slot(entity_id="SHOP_WINDOW", surface="shop window", determiner="the", semantic_role="RELATION_OBJECT"),
        ],
        "discourse_capability": ["KNOWN_REFERENCE_TARGET"],
        "task_use_capability": ["WRITING"],
        "source_kind": "CANONICAL_SCENE_DERIVED",
        "relation_capability": ["IN"],
        "legacy_unnormalized": False,
    }
    first_options = builder._first_mention_options([first, known], vocabulary)
    known_options = builder._known_reference_options([first, known], vocabulary)
    assert [(slot["_noun"], slot["_entity_id"]) for _p, slot in first_options] == [("robot", "ROBOT")]
    assert [(slot["_noun"], slot["_entity_id"]) for _p, slot in known_options] == [("robot", "ROBOT")]
    pair = builder._choose_pair(
        first_options,
        known_options,
        Counter(),
        scene_ref_id="U01-MA-SHOP-04",
        activity_id="U01-FORM-08-S03-A04",
    )
    assert pair[1]["_entity_id"] == "ROBOT"
    assert pair[3]["_entity_id"] == "ROBOT"


def test_compound_toy_shop_uses_head_noun_without_faking_authority() -> None:
    vocabulary = builder._unit01_vocabulary_authority()
    slot = _slot(
        entity_id="TOY_SHOP",
        surface="toy shop",
        determiner="a",
        semantic_role="RELATION_SUBJECT",
    )
    target = builder._slot_target(slot, vocabulary)
    assert target is not None
    noun, vocabulary_ref, entity_id = target
    assert noun == "shop"
    assert entity_id == "TOY_SHOP"
    assert vocabulary_ref == vocabulary.get("shop", "")
