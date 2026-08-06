from __future__ import annotations

import pytest

from product import a1fs_v1_2_1 as product_package
from ulga.builders import _u01qb16b_task_angle_progression_adapter as u16b
from ulga.builders import (
    build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u09,
)
from ulga.builders import (
    build_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as runtime_allocation,
)


def test_product_installs_u01qb16b_without_second_authority() -> None:
    assert product_package is not None
    assert u16b.installed() is True
    assert u09.choose_angles is u16b.choose_angles
    assert runtime_allocation._scene_options is u16b.scene_options
    assert u16b.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert u16b.A1FS_CONTENT_POLICY_EXEMPTION


def test_guided_reading_prefers_two_distinct_capability_classes() -> None:
    selected = u16b.choose_angles("GUIDED", "READING", set(), 2)
    assert selected == ["ARTICLE_CONTROL", "KNOWN_REFERENCE_CONTEXT"]
    classes = [u16b.capability_class("READING", angle) for angle in selected]
    assert len(classes) == len(set(classes)) == 2
    assert "FIRST_MENTION_CONTEXT" not in selected


def test_reused_scene_keeps_exact_angle_no_replay_when_distinct_classes_exist() -> None:
    previous = {"ARTICLE_CONTROL", "KNOWN_REFERENCE_CONTEXT"}
    selected = u16b.choose_angles("TRANSFER", "READING", previous, 2)
    assert not (set(selected) & previous)
    classes = [u16b.capability_class("READING", angle) for angle in selected]
    assert len(classes) == len(set(classes)) == 2


def test_nonreading_allocation_preserves_existing_policy() -> None:
    selected = u16b.choose_angles("GUIDED", "WRITING", set(), 2)
    assert selected == u16b._ORIGINAL_CHOOSE_ANGLES("GUIDED", "WRITING", set(), 2)


def test_runtime_scene_options_prefer_distinct_reading_capabilities(monkeypatch: pytest.MonkeyPatch) -> None:
    same_class = (
        ("ARTICLE_CONTROL", "FIRST_MENTION_CONTEXT"),
        (("I1",), ("I2",)),
    )
    diverse = (
        ("ARTICLE_CONTROL", "KNOWN_REFERENCE_CONTEXT"),
        (("I1",), ("I3",)),
    )
    monkeypatch.setattr(
        u16b,
        "_ORIGINAL_SCENE_OPTIONS",
        lambda *args, **kwargs: [same_class, diverse],
    )
    result = u16b.scene_options(
        support="GUIDED",
        skill="READING",
        previous=set(),
        count=2,
        anchors={"tree"},
        situation_family="OUTDOORS",
        catalog={},
        scene_ref_id="SCENE-1",
    )
    assert result == [diverse]


def test_runtime_scene_options_preserve_existing_distinct_capacity(monkeypatch: pytest.MonkeyPatch) -> None:
    proven_capacity = (
        ("TRANSFER_DECISION", "ERROR_CHECK"),
        (("I1",), ("I2",)),
    )
    monkeypatch.setattr(
        u16b,
        "_ORIGINAL_SCENE_OPTIONS",
        lambda *args, **kwargs: [proven_capacity],
    )
    result = u16b.scene_options(
        support="TRANSFER",
        skill="READING",
        previous={"ERROR_CHECK", "REFERENCE_EVIDENCE"},
        count=2,
        anchors={"tree"},
        situation_family="OUTDOORS",
        catalog={},
        scene_ref_id="SCENE-2",
    )
    assert result == [proven_capacity]


def test_runtime_scene_options_fall_back_when_only_same_capability_pair_is_runtime_capable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    same_class_only = (
        ("ARTICLE_CONTROL", "TRANSFER_DECISION"),
        (("I1",), ("I2",)),
    )
    monkeypatch.setattr(
        u16b,
        "_ORIGINAL_SCENE_OPTIONS",
        lambda *args, **kwargs: [same_class_only],
    )
    result = u16b.scene_options(
        support="TRANSFER",
        skill="READING",
        previous=set(),
        count=2,
        anchors={"tree"},
        situation_family="OUTDOORS",
        catalog={},
        scene_ref_id="SCENE-3",
    )
    assert result == [same_class_only]
