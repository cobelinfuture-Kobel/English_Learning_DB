from __future__ import annotations

import json
from collections import Counter

import pytest

from product import a1fs_v1_2_1 as product_package  # noqa: F401
from ulga.builders import _u01qb13_distinct_item_matching_adapter as matching
from ulga.builders import _u01qb16c_unbound_form_progression_overlay as u16c
from ulga.builders import _u01qb18f_r4r2_r1_preserve_u16c_public_ownership_adapter as owner
from ulga.builders import _u01qb18f_r4r3r1_support_stage_scene_swap_fullfix as r4r3r1


def _package(form: int, slot: int, ref: str, family: str, noun: str) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    skills = ("READING", "READING", "WRITING", "WRITING", "SPEAKING")
    for activity, skill in enumerate(skills, 1):
        result.append(
            {
                "activity_id": f"U01-FORM-{form:02d}-S{slot:02d}-A{activity:02d}",
                "form_id": f"U01-FORM-{form:02d}",
                "form_ordinal": form,
                "scene_ref_id": ref,
                "situation_family": family,
                "setting": f"SETTING-{ref}",
                "skill": skill,
                "task_angle": "SCENE_DESCRIPTION" if skill == "SPEAKING" else "ERROR_CHECK",
                "support_level": "INDEPENDENT" if form <= 9 else "TRANSFER",
                "scored": int(skill != "SPEAKING"),
                "assessment_candidate": int(form >= 10 and skill != "SPEAKING"),
                "pattern_family_ids_json": json.dumps(["PF"]),
                "scene_anchors_json": json.dumps([noun]),
                "practice_projection_json": "{}",
                "activity_digest": f"DIGEST-{form}-{slot}-{activity}-{ref}",
            }
        )
    return result


def test_single_exposure_same_family_swap_preserves_scene_and_family_denominators() -> None:
    rows = []
    rows += _package(8, 1, "U01-MA-SHOP-04", "SHOPPING", "robot")
    rows += _package(8, 2, "CURRENT-HOME", "HOME", "cat")
    rows += _package(8, 3, "CURRENT-SCHOOL", "SCHOOL", "book")
    rows += _package(8, 4, "CURRENT-OUT", "OUTDOORS", "tree")
    rows += _package(10, 1, "U01-MA-SHOP-01", "SHOPPING", "book")
    rows += _package(10, 2, "DONOR-HOME", "HOME", "bed")
    rows += _package(10, 3, "DONOR-SCHOOL", "SCHOOL", "bag")
    rows += _package(10, 4, "DONOR-OUT", "OUTDOORS", "dog")

    before_refs = Counter(str(row["scene_ref_id"]) for row in rows)
    before_families = {
        form: Counter(str(row["situation_family"]) for row in rows if int(row["form_ordinal"]) == form)
        for form in (8, 10)
    }
    swapped = r4r3r1._swap_scene_packages_in_memory(
        rows,
        current_form=8,
        failing_ref="U01-MA-SHOP-04",
        donor_form=10,
        donor_ref="U01-MA-SHOP-01",
    )
    assert Counter(str(row["scene_ref_id"]) for row in swapped) == before_refs
    for form in (8, 10):
        assert Counter(
            str(row["situation_family"])
            for row in swapped
            if int(row["form_ordinal"]) == form
        ) == before_families[form]
    assert {
        str(row["scene_ref_id"])
        for row in swapped
        if int(row["form_ordinal"]) == 8 and str(row["activity_id"]).startswith("U01-FORM-08-S01")
    } == {"U01-MA-SHOP-01"}
    assert {
        str(row["scene_ref_id"])
        for row in swapped
        if int(row["form_ordinal"]) == 10 and str(row["activity_id"]).startswith("U01-FORM-10-S01")
    } == {"U01-MA-SHOP-04"}


def test_candidate_swap_requires_later_same_family_single_exposure_and_all_skill_capacity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = []
    rows += _package(8, 1, "U01-MA-SHOP-04", "SHOPPING", "robot")
    rows += _package(8, 2, "CURRENT-HOME", "HOME", "cat")
    rows += _package(8, 3, "CURRENT-SCHOOL", "SCHOOL", "book")
    rows += _package(8, 4, "CURRENT-OUT", "OUTDOORS", "tree")
    rows += _package(9, 1, "DONOR-WRONG-FAMILY", "HOME", "bed")
    rows += _package(9, 2, "DONOR9-SCHOOL", "SCHOOL", "bag")
    rows += _package(9, 3, "DONOR9-OUT", "OUTDOORS", "dog")
    rows += _package(9, 4, "DONOR9-FOOD", "FOOD_SOCIAL", "apple")
    rows += _package(10, 1, "U01-MA-SHOP-01", "SHOPPING", "book")
    rows += _package(10, 2, "DONOR-HOME", "HOME", "bed")
    rows += _package(10, 3, "DONOR-SCHOOL", "SCHOOL", "bag")
    rows += _package(10, 4, "DONOR-OUT", "OUTDOORS", "dog")

    monkeypatch.setattr(r4r3r1.runtime_allocation, "_catalog", lambda _db: {})

    calls: list[tuple[int, str]] = []

    def fake_choices(*, all_rows, form_ordinal: int, skill: str, catalog):
        calls.append((form_ordinal, skill))
        refs = {
            str(row["scene_ref_id"])
            for row in all_rows
            if int(row["form_ordinal"]) == form_ordinal
        }
        return {ref: (("SCENE_DESCRIPTION",) if skill == "SPEAKING" else ("A", "B")) for ref in refs}

    monkeypatch.setattr(r4r3r1, "_form_skill_choices", fake_choices)
    selected = r4r3r1._candidate_swap(
        __import__("pathlib").Path("ignored.sqlite3"),
        current_form=8,
        failing_ref="U01-MA-SHOP-04",
        all_rows=rows,
        frozen_forms=set(),
    )
    assert selected is not None
    donor_form, donor_ref, _simulated, current_speaking, donor_speaking = selected
    assert donor_form == 10
    assert donor_ref == "U01-MA-SHOP-01"
    assert current_speaking["U01-MA-SHOP-01"] == ("SCENE_DESCRIPTION",)
    assert donor_speaking["U01-MA-SHOP-04"] == ("SCENE_DESCRIPTION",)
    assert set(calls) == {
        (8, "READING"), (8, "WRITING"), (8, "SPEAKING"),
        (10, "READING"), (10, "WRITING"), (10, "SPEAKING"),
    }


def test_reused_scene_case_is_not_reclassified_as_single_exposure_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = []
    rows += _package(2, 1, "REUSED-SHOP", "SHOPPING", "robot")
    rows += _package(8, 1, "REUSED-SHOP", "SHOPPING", "robot")
    rows += _package(8, 2, "CURRENT-HOME", "HOME", "cat")
    rows += _package(8, 3, "CURRENT-SCHOOL", "SCHOOL", "book")
    rows += _package(8, 4, "CURRENT-OUT", "OUTDOORS", "tree")
    monkeypatch.setattr(r4r3r1.runtime_allocation, "_catalog", lambda _db: {})
    assert r4r3r1._candidate_swap(
        __import__("pathlib").Path("ignored.sqlite3"),
        current_form=8,
        failing_ref="REUSED-SHOP",
        all_rows=rows,
        frozen_forms=set(),
    ) is None


def test_owner_keeps_u16c_public_ownership_and_r4r3r1_is_pre_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert owner.installed() is True
    assert matching.assemble_form_component is u16c.assemble_form_component
    assert u16c.migrate_unbound_reading_form is owner._ORIGINAL_U16C_READING_MIGRATION

    calls: list[str] = []
    monkeypatch.setattr(
        owner.r4r3r1,
        "migrate_unbound_support_stage_scene_assignment",
        lambda *args, **kwargs: calls.append("support-stage") or {"status": r4r3r1.PASS_STATUS},
    )
    monkeypatch.setattr(
        owner.r4r3,
        "migrate_unbound_form_reuse_scene",
        lambda *args, **kwargs: calls.append("reuse") or {"status": owner.r4r3.PASS_STATUS},
    )
    monkeypatch.setattr(
        owner.r4r2,
        "migrate_unbound_writing_form",
        lambda *args, **kwargs: calls.append("writing") or {"status": owner.r4r2.PASS_STATUS},
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
    assert calls == ["support-stage", "reuse", "writing", "u16c"]


def test_r4r3r1_content_and_scope_boundaries_are_fail_closed() -> None:
    assert r4r3r1.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert "authors no content" in r4r3r1.A1FS_CONTENT_POLICY_EXEMPTION
    assert "QuestionBank" in r4r3r1.A1FS_CONTENT_POLICY_EXEMPTION
    assert r4r3r1.NEXT_SHORT_STEP == owner.r4r3.NEXT_SHORT_STEP
