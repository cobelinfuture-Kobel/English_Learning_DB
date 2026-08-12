from __future__ import annotations

import json
from copy import deepcopy

import pytest

from product import a1fs_v1_2_1 as product_package  # noqa: F401
from ulga.builders import _u01qb13_distinct_item_matching_adapter as matching
from ulga.builders import _u01qb16c_unbound_form_progression_overlay as u16c
from ulga.builders import _u01qb18f_r4r2_r1_preserve_u16c_public_ownership_adapter as owner
from ulga.builders import _u01qb18f_r4r2_unbound_writing_selector_parity_fullfix as r4r2
from ulga.builders import _u01qb18f_r4r3_runtime_capacity_aware_reuse_scene_migration as r4r3
from ulga.builders import build_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as u08
from ulga.builders import build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u09
from ulga.validators import validate_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u09_validator


def _scene_rows(ref: str, family: str = "SHOPPING") -> list[dict[str, object]]:
    result = []
    for ordinal, skill in enumerate(("READING", "READING", "WRITING", "WRITING", "SPEAKING"), 1):
        result.append(
            {
                "activity_id": f"U01-FORM-08-S01-A{ordinal:02d}",
                "form_ordinal": 8,
                "scene_ref_id": ref,
                "situation_family": family,
                "setting": "TOY_SHOP",
                "skill": skill,
                "task_angle": (
                    "ERROR_CHECK"
                    if skill == "READING"
                    else "WORD_ORDER"
                    if skill == "WRITING"
                    else "SCENE_DESCRIPTION"
                ),
                "support_level": "INDEPENDENT",
                "pattern_family_ids_json": json.dumps(["PF"]),
                "scene_anchors_json": json.dumps(["robot"]),
                "practice_projection_json": "{}",
                "activity_digest": f"DIGEST-{ordinal}",
            }
        )
    return result


def test_frozen_u09_still_forbids_same_scene_skill_task_angle_replay() -> None:
    assert (
        u09_validator.EXPECTED_ALLOCATION_POLICY[
            "same_scene_same_skill_same_task_angle_repeat_allowed"
        ]
        is False
    )
    assert u08.MIN_REPEAT_FORM_DELTA == 3


def test_replacement_is_same_family_single_exposure_prior_scene_with_runtime_capacity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    form_rows = _scene_rows("U01-MA-SHOP-04")
    # Add the other three current-form scenes so they cannot be selected.
    for slot, ref in enumerate(("CURRENT-A", "CURRENT-B", "CURRENT-C"), 2):
        for row in _scene_rows(ref):
            value = deepcopy(row)
            value["activity_id"] = str(value["activity_id"]).replace("S01", f"S{slot:02d}")
            form_rows.append(value)

    usage = {
        "U01-MA-SHOP-04": {
            "scene_ref_id": "U01-MA-SHOP-04",
            "situation_family": "SHOPPING",
            "setting": "TOY_SHOP",
            "scene_anchors_json": json.dumps(["robot"]),
            "form_ordinals": [3, 8],
            "exposure_count": 2,
        },
        "U01-MA-SHOP-01": {
            "scene_ref_id": "U01-MA-SHOP-01",
            "situation_family": "SHOPPING",
            "setting": "BOOKSHOP",
            "scene_anchors_json": json.dumps(["book", "bag"]),
            "form_ordinals": [1],
            "exposure_count": 1,
        },
        # Same family but repeat gap 1: must be rejected.
        "U01-MA-SHOP-02": {
            "scene_ref_id": "U01-MA-SHOP-02",
            "situation_family": "SHOPPING",
            "setting": "FOOD_SHOP",
            "scene_anchors_json": json.dumps(["apple", "bag"]),
            "form_ordinals": [7],
            "exposure_count": 1,
        },
        # Wrong family: must be rejected even with capacity.
        "U01-MA-HOME-01": {
            "scene_ref_id": "U01-MA-HOME-01",
            "situation_family": "HOME",
            "setting": "BEDROOM",
            "scene_anchors_json": json.dumps(["cat", "bed"]),
            "form_ordinals": [1],
            "exposure_count": 1,
        },
    }

    def fake_options(*, skill: str, replacement, **_kwargs):
        ref = str(replacement["scene_ref_id"])
        if ref != "U01-MA-SHOP-01":
            raise r4r3.runtime_allocation.RuntimeTaskAwareAllocationError("NO_CAPACITY")
        if skill == "SPEAKING":
            return [(('CONNECTED_SENTENCE_PRODUCTION',), (('S1',),))]
        return [
            (("ERROR_CHECK", "TRANSFER_DECISION"), (("A",), ("B",))),
            (("ARTICLE_CONTROL", "ERROR_CHECK"), (("C",), ("D",))),
        ]

    monkeypatch.setattr(r4r3, "_raw_skill_options", fake_options)
    candidates = r4r3._candidate_replacements(
        failing_ref="U01-MA-SHOP-04",
        form_ordinal=8,
        form_rows=form_rows,
        usage=usage,
        prior={},
        catalog={},
    )
    assert len(candidates) == 1
    selected = candidates[0][1]
    assert selected["scene_ref_id"] == "U01-MA-SHOP-01"
    assert selected["situation_family"] == "SHOPPING"
    assert selected["prior_form_ordinal"] == 1
    assert selected["repeat_form_delta"] == 7
    assert selected["speaking_effective_angle"] == "CONNECTED_SENTENCE_PRODUCTION"


def test_scene_swap_changes_exactly_one_five_activity_scene_package() -> None:
    rows = _scene_rows("U01-MA-SHOP-04")
    replacement = {
        "scene_ref_id": "U01-MA-SHOP-01",
        "situation_family": "SHOPPING",
        "setting": "BOOKSHOP",
        "scene_anchors_json": json.dumps(["book", "bag"]),
    }
    values = r4r3._replace_scene_in_memory(
        rows,
        original_ref="U01-MA-SHOP-04",
        replacement=replacement,
    )
    assert len(values) == 5
    assert {row["scene_ref_id"] for row in values} == {"U01-MA-SHOP-01"}
    assert {row["situation_family"] for row in values} == {"SHOPPING"}
    assert {row["setting"] for row in values} == {"BOOKSHOP"}
    assert all(json.loads(str(row["scene_anchors_json"])) == ["book", "bag"] for row in values)


def test_r4r3_does_not_relax_rotation_or_content_boundaries() -> None:
    assert r4r3.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert "QuestionBank" in r4r3.A1FS_CONTENT_POLICY_EXEMPTION
    assert "no content is authored" in r4r3.A1FS_CONTENT_POLICY_EXEMPTION
    assert u08.MAX_EXPOSURES == 2
    assert u08.REUSED_SCENE_CHANGED_DIMENSIONS_MIN == 2


def test_u16c_public_owner_and_direct_reading_api_remain_preserved() -> None:
    assert owner.installed() is True
    assert matching.assemble_form_component is u16c.assemble_form_component
    assert u16c.migrate_unbound_reading_form is owner._ORIGINAL_U16C_READING_MIGRATION
    assert r4r2.installed() is True


def test_owner_pre_hook_runs_reuse_repair_before_writing_and_u16c(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        owner.r4r3,
        "migrate_unbound_form_reuse_scene",
        lambda *args, **kwargs: calls.append("reuse") or {"status": r4r3.PASS_STATUS},
    )
    monkeypatch.setattr(
        owner.r4r2,
        "migrate_unbound_writing_form",
        lambda *args, **kwargs: calls.append("writing") or {"status": r4r2.PASS_STATUS},
    )
    monkeypatch.setattr(
        owner,
        "_ORIGINAL_U16C_ASSEMBLER",
        lambda *args, **kwargs: calls.append("u16c") or {"ok": True},
    )
    result = owner.assemble_form_component_with_writing_parity(
        "ignored.sqlite3",
        learner_id="L",
        session_id="S",
        form_ordinal=8,
    )
    assert result == {"ok": True}
    assert calls == ["reuse", "writing", "u16c"]
