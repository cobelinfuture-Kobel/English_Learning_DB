from __future__ import annotations

from copy import deepcopy

from ulga.builders import (
    build_a1fs_v1_razq01e_unit01_admitted_content_asset_qb_consumer_workbench
    as binding_consumer,
)
from ulga.builders import (
    build_a1fs_v1_razq01f_fullfix_real62_semantic_lexical_anchor_fallback
    as fullfix,
)
from ulga.validators import (
    validate_a1fs_v1_razq01f_fullfix_real62_semantic_lexical_anchor_fallback
    as fullfix_validator,
)


def learner_item() -> dict:
    return {
        "item_id": "U01QB01-U01-PF06-ERROR-DISCRIMINATION-VERY-BIG-BOX",
        "skill": "READING",
        "pattern_family_id": "U01-PF06-ERROR-DISCRIMINATION",
        "unit_pattern_id": "U01-PF06-VERY-ADJ-NOUN",
    }


def private_item() -> dict:
    return {
        "lexical_slots": {
            "noun": "box",
            "adjective": "big",
        }
    }


def approved_asset() -> dict:
    return {
        "content_asset_id": "U01-CONTENT-BIG-BOX",
        "content_kind": "MICRO_SCENE",
        "content_sha256": "a" * 64,
        "target_alignment": {
            "active_nouns": ["box"],
            "active_adjectives": ["big"],
            "grammar_target_ids": [],
        },
        "skill_projections": [
            {
                "skill": "READING",
                "existing_family_ids": [
                    "U01-PF04-FIRST-MENTION-CONTEXT"
                ],
                "projection_status": "READY_FOR_EXISTING_QB_MATERIALIZATION",
            }
        ],
        "source_lineage": {
            "source_authority": "PROJECT_AUTHORED_CONTRACT_COMPLETION"
        },
    }


def test_real62_pf06_very_big_box_uses_complete_lexical_anchor_fallback():
    item = learner_item()
    private = private_item()
    asset = approved_asset()

    # The original RAZQ01E consumer rejects this because neither family nor
    # Unit01 pattern is directly listed by the approved content projection.
    original = binding_consumer._razq01f_pre_fullfix_compatibility(
        item, private, asset
    )
    assert original is None

    match = fullfix.semantic_lexical_anchor_compatibility(item, private, asset)
    assert match is not None
    assert match["mode"] == "SEMANTIC_LEXICAL_ANCHOR_EXACT"
    assert match["exact_family"] is False
    assert match["pattern_match"] is False
    assert match["noun_match"] is True
    assert match["adjective_match"] is True
    assert match["semantic_anchor_fallback"] is True

    safe = binding_consumer._safe_binding(
        asset=asset,
        learner_item=item,
        match=match,
    )
    assert safe["content_asset_id"] == "U01-CONTENT-BIG-BOX"
    assert safe["compatibility_mode"] == "SEMANTIC_LEXICAL_ANCHOR_EXACT"


def test_real62_lexical_anchor_fallback_rejects_partial_or_cross_skill_matches():
    item = learner_item()
    private = private_item()

    wrong_noun = approved_asset()
    wrong_noun["target_alignment"]["active_nouns"] = ["bag"]
    assert (
        fullfix.semantic_lexical_anchor_compatibility(
            item, private, wrong_noun
        )
        is None
    )

    wrong_adjective = approved_asset()
    wrong_adjective["target_alignment"]["active_adjectives"] = ["small"]
    assert (
        fullfix.semantic_lexical_anchor_compatibility(
            item, private, wrong_adjective
        )
        is None
    )

    cross_skill = approved_asset()
    cross_skill["skill_projections"][0]["skill"] = "WRITING"
    assert (
        fullfix.semantic_lexical_anchor_compatibility(
            item, private, cross_skill
        )
        is None
    )


def test_existing_direct_compatibility_and_shared_validator_patch_are_preserved():
    item = learner_item()
    private = private_item()
    direct = approved_asset()
    direct["skill_projections"][0]["existing_family_ids"] = [
        item["pattern_family_id"]
    ]

    match = fullfix.semantic_lexical_anchor_compatibility(item, private, direct)
    assert match is not None
    assert match["exact_family"] is True
    assert match["mode"] != "SEMANTIC_LEXICAL_ANCHOR_EXACT"

    fullfix.install_fullfix()
    assert binding_consumer.compatibility is fullfix.semantic_lexical_anchor_compatibility
    assert (
        fullfix_validator._core.binding_consumer.compatibility
        is fullfix.semantic_lexical_anchor_compatibility
    )

    # Re-installation is idempotent and does not wrap the fallback recursively.
    fullfix.install_fullfix()
    repeated = binding_consumer.compatibility(
        learner_item(), private_item(), deepcopy(approved_asset())
    )
    assert repeated is not None
    assert repeated["mode"] == "SEMANTIC_LEXICAL_ANCHOR_EXACT"
