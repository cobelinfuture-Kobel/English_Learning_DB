from __future__ import annotations

import json

from ulga.builders import (
    build_a1fs_v1_u01qb18h_r2r2_unit01_sentence_pool_driven_production_capacity_reconciliation
    as builder,
)


def _blueprint_with_pf09(count: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(1, count + 1):
        rows.append(
            {
                "activity_id": f"U01-PF09-DYNAMIC-{index:03d}",
                "form_id": f"U01-FORM-{((index - 1) % 12) + 1:02d}",
                "form_ordinal": ((index - 1) % 12) + 1,
                "scene_ref_id": f"PF09-SCENE-{index:03d}",
                "situation_family": "HOME",
                "setting": "HOME",
                "skill": "WRITING",
                "task_angle": builder.PF09_TASK_ANGLE,
                "support_level": "INDEPENDENT",
                "assessment_candidate": False,
                "pattern_family_ids_json": json.dumps([builder.PF09_FAMILY]),
            }
        )
    for index in range(count + 1, builder.EXPECTED_BLUEPRINT_ACTIVITY_COUNT + 1):
        rows.append(
            {
                "activity_id": f"U01-PF09-FILLER-{index:03d}",
                "form_id": f"U01-FORM-{((index - 1) % 12) + 1:02d}",
                "form_ordinal": ((index - 1) % 12) + 1,
                "scene_ref_id": f"PF09-FILLER-{index:03d}",
                "situation_family": "HOME",
                "setting": "HOME",
                "skill": "READING",
                "task_angle": "ARTICLE_CONTROL",
                "support_level": "GUIDED",
                "assessment_candidate": False,
                "pattern_family_ids_json": json.dumps(
                    ["U01-PF04-FIRST-MENTION-CONTEXT"]
                ),
            }
        )
    assert len(rows) == builder.EXPECTED_BLUEPRINT_ACTIVITY_COUNT
    return rows


def test_pf09_requirement_denominator_is_blueprint_dynamic() -> None:
    rows = builder.contextual_reference_requirements(_blueprint_with_pf09(7))
    assert len(rows) == 7
    assert {row["pattern_family_id"] for row in rows} == {builder.PF09_FAMILY}
    assert {row["task_angle"] for row in rows} == {builder.PF09_TASK_ANGLE}


def test_pf09_exact_scene_item_uses_admitted_antecedent_not_legacy_location() -> None:
    requirement = {
        "activity_id": "U01-FORM-11-S02-A04",
        "form_id": "U01-FORM-11",
        "form_ordinal": 11,
        "scene_ref_id": "U01-MA-OUT-05",
        "situation_family": "HOME",
        "setting": "GARDEN",
        "support_level": "TRANSFER",
        "assessment_candidate": True,
        "task_angle": builder.PF09_TASK_ANGLE,
        "pattern_family_id": builder.PF09_FAMILY,
    }
    first_profile = {
        "sentence_id": "U01-SA-TEST-GARDEN-EGG",
        "text": "I can see an egg near the flower.",
    }
    first_slot = {
        "_noun": "egg",
        "_entity_id": "ENTITY_EGG",
        "_vocabulary_ref": "EVP_EGG_A1",
        "determiner": "an",
        "structure": "NOUN",
        "modifiers": [],
    }
    item = builder._contextual_reference_item(
        requirement,
        first_profile,
        first_slot,
        source_pool_sha256="a" * 64,
        scene_pattern_refs=["U01-NP-ARTICLE-NOUN"],
    )
    assert item["production_scene_ref_id"] == "U01-MA-OUT-05"
    assert item["production_activity_id"] == "U01-FORM-11-S02-A04"
    assert item["contextual_reference_scene_ref_id"] == "U01-MA-OUT-05"
    assert item["target_sentence_ids"] == ["U01-SA-TEST-GARDEN-EGG"]
    assert item["target_pattern_ids"] == ["U01-NP-ARTICLE-NOUN"]
    assert item["correct_answer"] == "the"
    assert item["accepted_answers"] == ["the"]
    assert item["stimulus"] == (
        "First mention: I can see an egg near the flower. | "
        "Second mention: ___ egg"
    )
    assert "in the park" not in item["stimulus"].casefold()
    assert "in the classroom" not in item["stimulus"].casefold()


def test_pf09_retirement_is_count_preserving_and_base_only() -> None:
    catalog = [
        {
            "item_id": f"PF09-BASE-{index:02d}",
            "pattern_family_id": builder.PF09_FAMILY,
        }
        for index in range(builder.HISTORICAL_CONTEXTUAL_REFERENCE_BASE_CAPACITY)
    ]
    catalog.extend(
        {
            "item_id": f"OTHER-{index:02d}",
            "pattern_family_id": "U01-PF07-WORD-ORDER",
        }
        for index in range(5)
    )
    retired = builder._select_contextual_reference_retired_ids(
        catalog,
        extension_ids=set(),
        desired_count=12,
    )
    assert len(retired) == 12
    assert all(value.startswith("PF09-BASE-") for value in retired)
