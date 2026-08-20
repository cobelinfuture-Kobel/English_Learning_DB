from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy

import pytest

from product.a1fs_v1_2_1 import (
    u01qb18h_r2r1_unit01_systemic_learner_facing_fullfix as r2r1,
)
from product.a1fs_v1_2_1 import (
    u01qb18h_r2r2_unit01_sentence_pool_driven_full240_closeout as product,
)
from ulga.builders import (
    build_a1fs_v1_u01qb18h_r2r2_unit01_sentence_pool_driven_production_capacity_reconciliation
    as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u01qb18h_r2r2_unit01_sentence_pool_driven_production_capacity_reconciliation
    as validator,
)


def _blueprint() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    plan = [
        *("ERROR_CHECK" for _ in range(12)),
        *("COMPLETE_SENTENCE_PRODUCTION" for _ in range(24)),
        *("CONNECTED_SENTENCE_PRODUCTION" for _ in range(12)),
    ]
    for index, angle in enumerate(plan, start=1):
        family = builder.PRODUCTION_ANGLE_TO_FAMILY[angle]
        rows.append(
            {
                "activity_id": f"U01-FORM-{((index - 1) // 4) + 1:02d}-P{index:03d}",
                "form_id": f"U01-FORM-{((index - 1) // 4) + 1:02d}",
                "form_ordinal": ((index - 1) // 4) + 1,
                "scene_ref_id": f"R2R2-SCENE-{index:03d}",
                "situation_family": "HOME",
                "setting": "HOME",
                "skill": "WRITING",
                "task_angle": angle,
                "support_level": "TRANSFER" if index > 36 else "INDEPENDENT",
                "assessment_candidate": index > 36,
                "pattern_family_ids_json": json.dumps([family]),
            }
        )
    for index in range(49, builder.EXPECTED_BLUEPRINT_ACTIVITY_COUNT + 1):
        rows.append(
            {
                "activity_id": f"U01-FILLER-{index:03d}",
                "form_id": f"U01-FORM-{((index - 1) % 12) + 1:02d}",
                "form_ordinal": ((index - 1) % 12) + 1,
                "scene_ref_id": f"R2R2-FILLER-SCENE-{index:03d}",
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


def _slot(*, determiner: str) -> dict[str, object]:
    return {
        "entity_id": "book",
        "canonical_surface": "book",
        "np_surface": f"{determiner} book",
        "surface": f"{determiner} book",
        "determiner": determiner,
        "modifiers": [],
        "very": False,
        "structure": "NOUN",
        "char_start": 0,
        "char_end": len(f"{determiner} book"),
        "syntactic_role": "SUBJECT",
        "semantic_role": "TARGET",
    }


def _sentence_pool() -> dict[str, object]:
    profiles: list[dict[str, object]] = []
    for index in range(1, builder.EXPECTED_PRODUCTION_REQUIREMENT_COUNT + 1):
        scene = f"R2R2-SCENE-{index:03d}"
        profiles.extend(
            [
                {
                    "sentence_id": f"R2R2-FIRST-{index:03d}",
                    "text": "A book is on the desk.",
                    "canonical_admission_status": "ADMITTED",
                    "np_slots": [_slot(determiner="a")],
                    "structure_capability": ["NOUN"],
                    "article_capability": ["a"],
                    "discourse_capability": ["FIRST_MENTION"],
                    "scene_capability": ["SOURCE_BACKED"],
                    "relation_capability": ["on"],
                    "task_use_capability": [
                        "ERROR_CHECK",
                        "PHRASE_PRODUCTION",
                        "WORD_ORDER",
                        "WRITING",
                    ],
                    "source_scene_ref": scene,
                    "source_kind": "CANONICAL_SCENE_DERIVED",
                    "legacy_unnormalized": False,
                },
                {
                    "sentence_id": f"R2R2-KNOWN-{index:03d}",
                    "text": "The book is on the desk.",
                    "canonical_admission_status": "ADMITTED",
                    "np_slots": [_slot(determiner="the")],
                    "structure_capability": ["NOUN"],
                    "article_capability": ["the"],
                    "discourse_capability": ["KNOWN_REFERENCE_TARGET"],
                    "scene_capability": ["SOURCE_BACKED"],
                    "relation_capability": ["on"],
                    "task_use_capability": ["WRITING"],
                    "source_scene_ref": scene,
                    "source_kind": "CANONICAL_SCENE_DERIVED",
                    "legacy_unnormalized": False,
                },
            ]
        )
    # The production builder validates the canonical 3805 denominator. Fill the
    # unused admitted capacity with scene-neutral profiles that are not selected.
    for index in range(
        len(profiles) + 1,
        builder.EXPECTED_SENTENCE_POOL_TOTAL + 1,
    ):
        profiles.append(
            {
                "sentence_id": f"R2R2-UNUSED-{index:04d}",
                "text": "A book is here.",
                "canonical_admission_status": "ADMITTED",
                "np_slots": [_slot(determiner="a")],
                "structure_capability": ["NOUN"],
                "article_capability": ["a"],
                "discourse_capability": ["FIRST_MENTION"],
                "scene_capability": ["GENERIC_SCENE_NEUTRAL"],
                "relation_capability": [],
                "task_use_capability": ["WRITING"],
                "source_scene_ref": "",
                "source_kind": "MODEL/TEMPLATE_DERIVED",
                "legacy_unnormalized": False,
            }
        )
    return {
        "task_id": builder.SOURCE_TASK_ID,
        "status": builder.SOURCE_STATUS,
        "sentence_pool_total": builder.EXPECTED_SENTENCE_POOL_TOTAL,
        "profiles": profiles,
    }


def _scene_resolver(scene_ref_id: str) -> dict[str, object]:
    assert scene_ref_id.startswith("R2R2-SCENE-")
    return {
        "scene_ref_id": scene_ref_id,
        "unit_language_projection": {
            "eligible_pattern_refs": ["SP_000016", "SP_000017"]
        },
    }


def test_full240_blueprint_materializes_exact_48_sentence_backed_production_items() -> None:
    payload = builder.build_reconciliation_payload(
        blueprint=_blueprint(),
        sentence_pool=_sentence_pool(),
        sentence_pool_sha256="sentence-pool-sha",
        scene_resolver=_scene_resolver,
    )
    assert payload["production_requirements"]["requirement_count"] == 48
    assert payload["production_requirements"]["family_counts"] == {
        builder.u10.PF13: 12,
        builder.u10.PF14: 24,
        builder.u10.PF15: 12,
    }
    items = payload["materialized_items"]
    assert len(items) == 48
    assert Counter(row["pattern_family_id"] for row in items) == Counter(
        builder.EXPECTED_PRODUCTION_FAMILY_COUNTS
    )
    assert all(row["production_scene_ref_id"] for row in items)
    assert all(row["production_activity_id"] for row in items)
    assert all(row["target_pattern_ids"] == ["SP_000016", "SP_000017"] for row in items)
    assert all(row["source_sentence_ids"] for row in items)
    assert payload["count_preservation"] == {
        "base_count_before": 288,
        "retired_production_item_count": 48,
        "materialized_production_item_count": 48,
        "base_count_after": 288,
        "real62_extension_count": 186,
        "runtime_count_after": 474,
        "question_bank_total_expanded": False,
    }


def test_policy_admission_validates_sentence_pool_materialized_payload() -> None:
    payload = builder.build_reconciliation_payload(
        blueprint=_blueprint(),
        sentence_pool=_sentence_pool(),
        sentence_pool_sha256="sentence-pool-sha",
        scene_resolver=_scene_resolver,
    )
    candidate = builder.build_candidate(payload)
    approved = builder.admit_candidate(candidate)
    report = validator.validate_approved(candidate, approved)
    assert report["status"] == "PASS"
    assert report["error_count"] == 0
    assert report["production_requirement_count"] == 48
    assert report["materialized_item_count"] == 48
    assert report["runtime_count_after"] == 474


def test_connected_sentence_requirement_fails_closed_without_same_referent_known_reference() -> None:
    pool = _sentence_pool()
    profiles = list(pool["profiles"])
    target_scene = "R2R2-SCENE-037"
    pool["profiles"] = [
        profile
        for profile in profiles
        if not (
            profile.get("source_scene_ref") == target_scene
            and "KNOWN_REFERENCE_TARGET" in profile.get("discourse_capability", [])
        )
    ]
    # Preserve the authoritative 3805 denominator with an admitted unrelated row.
    pool["profiles"].append(
        {
            **deepcopy(profiles[-1]),
            "sentence_id": "R2R2-UNRELATED-REPLACEMENT",
        }
    )
    assert len(pool["profiles"]) == builder.EXPECTED_SENTENCE_POOL_TOTAL
    with pytest.raises(
        builder.SentencePoolCapacityError,
        match="CONNECTED_SENTENCE_PAIR_SUPPLY_GAP",
    ):
        builder.build_reconciliation_payload(
            blueprint=_blueprint(),
            sentence_pool=pool,
            sentence_pool_sha256="sentence-pool-sha",
            scene_resolver=_scene_resolver,
        )


def test_r2r2_candidate_hook_enforces_exact_scene_and_canonical_pf13_identity() -> None:
    scene_ref = "U01-C4-TOY-SHOP"
    package = r2r1.r4.cross_layer.authority.canonical_scene_package(scene_ref)
    target_pattern = package["unit_language_projection"]["eligible_pattern_refs"][0]
    item = {
        "item_id": "R2R2-PF13-TOY-SHOP",
        "pattern_family_id": builder.u10.PF13,
        "production_scene_ref_id": scene_ref,
        "target_pattern_ids": [target_pattern],
        "lexical_slots": {"noun": "book", "context_id": scene_ref},
        "stimulus": "an book",
        "prompt": "Correct the article error in the noun phrase.",
        "options": [],
    }
    assert builder.u10.PF13 not in r2r1._ANGLE_FAMILIES["ERROR_CHECK"]
    with product.r2r2_candidate_compatibility_hooks():
        assert builder.u10.PF13 in r2r1._ANGLE_FAMILIES["ERROR_CHECK"]
        assert (
            r2r1.candidate_guard(
                item,
                task_angle="ERROR_CHECK",
                scene_ref_id=scene_ref,
                situation_family="SHOPPING",
            )
            is True
        )
        assert (
            r2r1.candidate_guard(
                item,
                task_angle="ERROR_CHECK",
                scene_ref_id="U01-MA-SHOP-03",
                situation_family="SHOPPING",
            )
            is False
        )
    assert builder.u10.PF13 not in r2r1._ANGLE_FAMILIES["ERROR_CHECK"]
