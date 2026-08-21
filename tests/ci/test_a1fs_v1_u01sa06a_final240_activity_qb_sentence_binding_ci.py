from __future__ import annotations

import pytest

from product.a1fs_v1_2_1 import (
    u01sa06a_unit01_final240_activity_questionbank_sentence_asset_binding as s06a,
)


def _profile(sentence_id: str, noun: str, entity: str) -> dict:
    return {
        "sentence_id": sentence_id,
        "canonical_admission_status": "ADMITTED",
        "np_slots": [
            {
                "entity_id": entity,
                "canonical_surface": noun,
                "np_surface": f"a {noun}",
                "determiner": "a",
                "modifiers": [],
                "structure": "NOUN",
            }
        ],
    }


def _legacy_binding(
    *,
    item_id: str,
    noun: str,
    determiner: str,
    task_angle: str,
    primary: str,
    antecedent: str | None = None,
    scene_ref: str = "U01-C1-CLASSROOM-BAG",
    scene_mode: str = "GENERIC_SCENE_NEUTRAL",
) -> dict:
    return {
        "item_id": item_id,
        "disposition": "BOUND",
        "primary_sentence_ref": primary,
        "antecedent_sentence_ref": antecedent,
        "support_sentence_refs": [],
        "task_angle": task_angle,
        "target_np": {
            "entity_id": noun.upper(),
            "canonical_surface": noun,
            "np_surface": f"{determiner} {noun}",
            "determiner": determiner,
            "modifiers": [],
            "structure": "NOUN",
        },
        "compatibility": {
            "candidate_compatible": True,
            "scene_ref": scene_ref,
            "scene_binding_mode": scene_mode,
        },
    }


def test_sa06a_contract_is_read_only_unit01_closeout() -> None:
    assert s06a.EXPECTED_POOL_TOTAL == 3805
    assert s06a.EXPECTED_RUNTIME_ITEMS == 474
    assert s06a.EXPECTED_FORMS == 12
    assert s06a.EXPECTED_SCENE_EXPOSURES == 48
    assert s06a.EXPECTED_ACTIVITY_BINDINGS == 240
    assert s06a.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert "Unit01Final240ActivityQuestionBankAndSentenceAssetBinding" in s06a.TASK_ID


def test_exact_sa05r2_item_binding_is_reused_without_rematching() -> None:
    pool = {"S1": _profile("S1", "cat", "CAT")}
    legacy = _legacy_binding(
        item_id="LEGACY-CAT",
        noun="cat",
        determiner="a",
        task_angle="FIRST_MENTION",
        primary="S1",
    )
    result = s06a._resolve_sentence_binding(
        item_id="LEGACY-CAT",
        catalog_row={
            "pattern_family_id": "U01-PF04-FIRST-MENTION-CONTEXT",
            "private_item": {"lexical_slots": {"noun": "cat"}},
        },
        sa05r2_by_id={"LEGACY-CAT": legacy},
        pool=pool,
    )
    assert result["binding_source"] == "SA05R2_EXACT_ITEM_ID"
    assert result["primary_sentence_ref"] == "S1"
    assert result["antecedent_sentence_ref"] is None


def test_r2r2_inline_lineage_binds_exact_sentence_and_context_antecedent() -> None:
    pool = {"S1": _profile("S1", "door", "DOOR")}
    result = s06a._resolve_sentence_binding(
        item_id="U01QB18H-R2R2-PF09-ACTIVITY",
        catalog_row={
            "pattern_family_id": "U01-PF09-TRANSFER-KNOWN-REFERENCE",
            "private_item": {
                "lexical_slots": {"noun": "door"},
                "sentence_pool_source_task_id": s06a.SA05R2_TASK_ID,
                "sentence_pool_target_entity_id": "DOOR",
                "source_sentence_ids": ["S1"],
                "contextual_reference_source_sentence_id": "S1",
            },
        },
        sa05r2_by_id={},
        pool=pool,
    )
    assert result["binding_source"] == "R2R2_INLINE_SENTENCE_LINEAGE"
    assert result["primary_sentence_ref"] == "S1"
    assert result["antecedent_sentence_ref"] == "S1"


def test_post_sa05r2_identity_bridge_prefers_same_scene_existing_evidence() -> None:
    pool = {
        "S1": _profile("S1", "door", "DOOR"),
        "S2": _profile("S2", "door", "DOOR"),
        "S3": _profile("S3", "door", "DOOR"),
        "S4": _profile("S4", "door", "DOOR"),
    }
    same_scene = _legacy_binding(
        item_id="OLD-PF05-DOOR",
        noun="door",
        determiner="the",
        task_angle="KNOWN_REFERENCE",
        primary="S1",
        antecedent="S2",
        scene_ref="U01-C1-CLASSROOM-BAG",
        scene_mode="RELATION_BACKED",
    )
    other_scene = _legacy_binding(
        item_id="OLD-PF05-DOOR-OTHER",
        noun="door",
        determiner="the",
        task_angle="KNOWN_REFERENCE",
        primary="S3",
        antecedent="S4",
        scene_ref="U01-C4-TOY-SHOP",
        scene_mode="RELATION_BACKED",
    )
    result = s06a._resolve_sentence_binding(
        item_id="NEW-PF05-C1-DOOR",
        catalog_row={
            "pattern_family_id": "U01-PF05-KNOWN-REFERENCE-CONTEXT",
            "private_item": {
                "context_id": "U01-C1-CLASSROOM-BAG",
                "lexical_slots": {"noun": "door"},
                "correct_answer": "the",
            },
        },
        sa05r2_by_id={
            same_scene["item_id"]: same_scene,
            other_scene["item_id"]: other_scene,
        },
        pool=pool,
    )
    assert result["binding_source"] == "POST_SA05R2_IDENTITY_BRIDGE"
    assert result["legacy_evidence_item_id"] == "OLD-PF05-DOOR"
    assert result["primary_sentence_ref"] == "S1"
    assert result["antecedent_sentence_ref"] == "S2"


def test_post_sa05r2_bridge_fails_when_top_semantic_rank_has_different_evidence() -> None:
    a = _legacy_binding(
        item_id="OLD-A",
        noun="door",
        determiner="the",
        task_angle="KNOWN_REFERENCE",
        primary="S1",
        antecedent="S2",
        scene_ref="U01-C1-CLASSROOM-BAG",
    )
    b = _legacy_binding(
        item_id="OLD-B",
        noun="door",
        determiner="the",
        task_angle="KNOWN_REFERENCE",
        primary="S3",
        antecedent="S4",
        scene_ref="U01-C1-CLASSROOM-BAG",
    )
    with pytest.raises(s06a.Final240BindingError, match="POST_SA05R2_BRIDGE_AMBIGUOUS"):
        s06a._bridge_binding(
            item_id="NEW",
            family="U01-PF05-KNOWN-REFERENCE-CONTEXT",
            private={
                "context_id": "U01-C1-CLASSROOM-BAG",
                "lexical_slots": {"noun": "door"},
                "correct_answer": "the",
            },
            sa05r2_rows=[a, b],
        )


def test_sentence_evidence_must_exist_in_admitted_pool_and_match_referent() -> None:
    pool = {"S1": _profile("S1", "cat", "CAT")}
    with pytest.raises(s06a.Final240BindingError, match="SENTENCE_REF_NOT_IN_3805_POOL"):
        s06a._validate_refs(
            item_id="ITEM",
            refs=["MISSING"],
            pool=pool,
            noun="cat",
            entity="CAT",
        )
    with pytest.raises(s06a.Final240BindingError, match="SENTENCE_TARGET_REFERENT_MISMATCH"):
        s06a._validate_refs(
            item_id="ITEM",
            refs=["S1"],
            pool=pool,
            noun="door",
            entity="DOOR",
        )