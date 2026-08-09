from __future__ import annotations

from copy import deepcopy

from product import a1fs_v1_2_1 as product_package  # noqa: F401
from ulga.builders import _u01qb18c_form01_learner_quality_adapter as quality
from ulga.builders import _u01qb18e_micro_scene_semantic_lineage_e2e_adapter as semantic
from ulga.builders import (
    build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration
    as u13,
)


def _scene_semantics() -> dict:
    return {
        "scene_ref_id": "U01-MA-OUT-02",
        "objects": ["cat", "tree"],
        "anchors": ["cat", "tree"],
        "setting": "GARDEN",
        "source": "MODEL_AUTHORED_APPROVED_SCENE",
        "event": "SEE_CAT_NEAR_TREE",
        "action": ["SEE"],
        "relations": ["NEAR"],
        "communicative_goal": "introduce a cat and refer to it near a tree",
    }


def _item(*, content: bool, stimulus: str) -> dict:
    value = {
        "item_id": "ITEM-CAT",
        "lexical_slots": {"noun": "cat"},
        "stimulus": stimulus,
        "prompt": "Choose the correct article.",
        "target_evp_sense_ids": ["EVP:CAT"],
        "unit_pattern_ids": ["U01-NP-ARTICLE-NOUN"],
    }
    if content:
        value["content_asset_id"] = "U01-CONTENT-CAT-GARDEN"
    return value


def test_semantic_fidelity_distinguishes_scene_language_asset_from_anchor_only() -> None:
    semantics = _scene_semantics()
    rich = semantic.semantic_fidelity(
        scene_ref_id="U01-MA-OUT-02",
        semantics=semantics,
        item=_item(
            content=True,
            stimulus="A cat is near a tree in the garden.",
        ),
    )
    anchor_only = semantic.semantic_fidelity(
        scene_ref_id="U01-MA-OUT-02",
        semantics=semantics,
        item=_item(content=False, stimulus="Complete with a or an: ___ cat"),
    )
    exact_item = _item(content=True, stimulus="A cat is near a tree in the garden.")
    exact_item["content_asset_id"] = "U01-MA-OUT-02"
    exact = semantic.semantic_fidelity(
        scene_ref_id="U01-MA-OUT-02",
        semantics=semantics,
        item=exact_item,
    )

    assert rich["mode"] == "SCENE_SEMANTIC_AND_LANGUAGE_ASSET_COMPATIBLE"
    assert rich["tier"] == 1
    assert rich["noun_bound"] is True
    assert rich["relation_hits"] == ["near"]
    assert rich["setting_hits"] == ["garden"]
    assert rich["richer_language_asset_present"] is True
    assert anchor_only["mode"] == "LEXICAL_ANCHOR_ONLY"
    assert anchor_only["tier"] == 4
    assert exact["mode"] == "EXACT_SCENE_LINEAGE"
    assert exact["tier"] == 0


def test_scene_context_card_projects_existing_scene_semantics_without_answer_content() -> None:
    card = semantic._scene_context_card(semantics=_scene_semantics(), form_ordinal=1)
    assert "Scene: Garden" in card
    assert "Scene words: cat, tree" in card
    assert "Relationship: near" in card
    assert "a cat" not in card.casefold()
    assert "the cat" not in card.casefold()


def _lineage(
    *,
    ref: str,
    noun: str,
    signal_count: int,
    richer: bool,
) -> dict:
    assets = {
        "vocabulary_refs": [f"EVP:{noun.upper()}"],
        "chunk_refs": [],
        "sentence_refs": [],
        "pattern_refs": ["U01-NP-ARTICLE-NOUN"],
        "content_asset_ids": [f"CONTENT:{ref}"] if richer else [],
    }
    return {
        "scene_ref_id": ref,
        "scene_source": "MODEL_AUTHORED_APPROVED_SCENE",
        "scene_event": "EVENT",
        "scene_objects": [noun, "other"],
        "scene_actions": ["SEE"],
        "scene_relations": ["NEAR"],
        "communicative_goal": "goal",
        "selection_fidelity": {
            "mode": (
                "SCENE_SEMANTIC_AND_LANGUAGE_ASSET_COMPATIBLE"
                if signal_count and richer
                else "LEXICAL_ANCHOR_ONLY"
            ),
            "noun": noun,
            "noun_bound": True,
            "semantic_signal_hit_count": signal_count,
            "richer_language_asset_present": richer,
            "language_asset_lineage": assets,
        },
        "language_asset_lineage": assets,
        "learner_scene_context_card": f"Scene: {ref}",
        "scene_context_preserved": True,
    }


def _form_payloads() -> dict[str, dict]:
    payloads = {
        skill: {
            "form_id": "U01-FORM-01",
            "form_ordinal": 1,
            "skill": skill,
            "items": [],
        }
        for skill in ("READING", "WRITING", "SPEAKING")
    }
    activity = 0
    for scene_number in range(1, 5):
        ref = f"SCENE-{scene_number:02d}"
        for local_index, skill in enumerate(
            ("READING", "READING", "WRITING", "WRITING", "SPEAKING"), start=1
        ):
            activity += 1
            noun = "cat" if local_index <= 2 else "tree"
            richer = local_index == 3
            signal = 1 if local_index == 3 else 0
            payloads[skill]["items"].append(
                {
                    "activity_id": f"U01-FORM-01-S{scene_number:02d}-A{local_index:02d}",
                    "item_id": f"ITEM-{activity:02d}",
                    "scene_ref_id": ref,
                    "skill": skill,
                    "stimulus": f"Scene: {ref} | unique stimulus {activity}",
                    "prompt": f"Prompt {activity}",
                    "options": [],
                    "semantic_lineage": _lineage(
                        ref=ref,
                        noun=noun,
                        signal_count=signal,
                        richer=richer,
                    ),
                }
            )
    return payloads


def test_logical_form_semantic_e2e_requires_scene_semantics_and_richer_language_asset() -> None:
    payloads = _form_payloads()
    report = semantic.validate_form_components(payloads)
    assert report["validation_status"] == semantic.PASS_STATUS
    assert report["error_count"] == 0
    assert report["activity_count"] == 20
    assert report["scene_count"] == 4
    assert all(row["richer_language_asset_activity_count"] == 1 for row in report["scene_reports"])
    assert all(row["vocabulary_ref_count"] >= 1 for row in report["scene_reports"])
    assert all(row["content_asset_count"] == 1 for row in report["scene_reports"])


def test_logical_form_semantic_e2e_fails_anchor_only_scene_and_surface_duplicate() -> None:
    payloads = _form_payloads()
    broken = deepcopy(payloads)
    rows = [
        row
        for payload in broken.values()
        for row in payload["items"]
        if row["scene_ref_id"] == "SCENE-03"
    ]
    for row in rows:
        row["semantic_lineage"] = _lineage(
            ref="SCENE-03",
            noun="tree",
            signal_count=0,
            richer=False,
        )
    rows[1]["stimulus"] = rows[0]["stimulus"]

    report = semantic.validate_form_components(broken)
    assert report["validation_status"] == semantic.FAIL_STATUS
    assert "GUIDED_SCENE_SEMANTIC_SIGNAL_MISSING:SCENE-03" in report["errors"]
    assert "GUIDED_SCENE_LANGUAGE_ASSET_CONSUMPTION_MISSING:SCENE-03" in report["errors"]
    assert any(
        error.startswith("LEARNER_VISIBLE_STIMULUS_DUPLICATE_WITHIN_SCENE:SCENE-03:")
        for error in report["errors"]
    )


def test_language_asset_lineage_reads_existing_item_refs_without_authoring() -> None:
    item = {
        "target_evp_sense_ids": ["EVP:CAT"],
        "target_chunk_ids": ["CHUNK:NEAR_THE_TREE"],
        "target_sentence_ids": ["SENTENCE:CAT_NEAR_TREE"],
        "unit_pattern_ids": ["U01-NP-ARTICLE-NOUN"],
        "content_asset_id": "CONTENT:CAT-GARDEN",
    }
    assert semantic.language_asset_lineage(item) == {
        "vocabulary_refs": ["EVP:CAT"],
        "chunk_refs": ["CHUNK:NEAR_THE_TREE"],
        "sentence_refs": ["SENTENCE:CAT_NEAR_TREE"],
        "pattern_refs": ["U01-NP-ARTICLE-NOUN"],
        "content_asset_ids": ["CONTENT:CAT-GARDEN"],
    }


def test_u01qb18e_installs_as_internal_delegate_without_replacing_prior_owners() -> None:
    assert quality.installed() is True
    assert semantic.u16c.installed() is True
    assert semantic.installed() is True
    assert u13.form_component_payload is quality.form_component_payload_with_learner_quality
    assert semantic.u16c._ORIGINAL_ASSEMBLE is semantic.assemble_form_component_with_semantic_rank
    assert (
        quality._ORIGINAL_FORM_COMPONENT_PAYLOAD
        is semantic.base_form_component_payload_with_semantic_lineage
    )
    assert quality.repair_learner_item is semantic.repair_learner_item_with_semantic_lineage
    assert semantic.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert semantic.A1FS_CONTENT_POLICY_EXEMPTION
    assert semantic.NEXT_SHORT_STEP.startswith("A1FS-V1-U01QB18F_")
