from __future__ import annotations

import json
from pathlib import Path

import pytest

from product import a1fs_v1_2_1 as product_package  # noqa: F401
from ulga.builders import _u01qb13_distinct_item_matching_adapter as matching
from ulga.builders import _u01qb16_learner_visible_distinctness_adapter as visible
from ulga.builders import _u01qb16c_unbound_form_progression_overlay as u16c
from ulga.builders import _u01qb18f_r4r2_r1_preserve_u16c_public_ownership_adapter as owner
from ulga.builders import _u01qb18f_r4r3r1_support_stage_scene_swap_fullfix as r4r3r1
from ulga.builders import _u01qb18f_r4r3r3_formal_learner_visible_donor_admission_fullfix as r4r3r3


def _package(form: int, slot: int, ref: str, family: str, noun: str) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for activity, skill in enumerate(("READING", "READING", "WRITING", "WRITING", "SPEAKING"), 1):
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


def _production_donor_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    rows += _package(4, 1, "U01-C4-TOY-SHOP", "SHOPPING", "toy")
    rows += _package(5, 1, "U01-MA-SHOP-01", "SHOPPING", "book")
    rows += _package(6, 1, "U01-MA-SHOP-02", "SHOPPING", "bag")
    rows += _package(8, 1, "U01-MA-SHOP-04", "SHOPPING", "robot")
    rows += _package(11, 1, "U01-C4-TOY-SHOP", "SHOPPING", "toy")
    rows += _package(12, 1, "U01-MA-SHOP-01", "SHOPPING", "book")
    rows += _package(12, 2, "U01-MA-SHOP-02", "SHOPPING", "bag")
    return rows


def _install_capacity_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(r4r3r3, "_formal_schema_present", lambda _db: True)
    monkeypatch.setattr(r4r3r3.runtime_allocation, "_catalog", lambda _db: {})
    monkeypatch.setattr(r4r3r3, "_formal_runtime_state", lambda _db: ([], {}))

    def fake_choices(*, all_rows, form_ordinal: int, skill: str, catalog):
        refs = {
            str(row["scene_ref_id"])
            for row in all_rows
            if int(row["form_ordinal"]) == int(form_ordinal)
        }
        return {
            ref: (("SCENE_DESCRIPTION",) if skill == "SPEAKING" else ("A", "B"))
            for ref in refs
        }

    monkeypatch.setattr(r4r3r1, "_form_skill_choices", fake_choices)


def test_r4r3r3_rejects_nearest_task_capacity_donor_when_formal_visible_unsat_and_uses_next(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = _production_donor_rows()
    _install_capacity_stubs(monkeypatch)
    attempted_current_refs: list[set[str]] = []

    def formal_pair(**kwargs) -> bool:
        current_refs = {
            str(row["scene_ref_id"])
            for row in kwargs["simulated"]
            if int(row["form_ordinal"]) == 8
        }
        attempted_current_refs.append(current_refs)
        # Production-shaped expectation: F11 TOY-SHOP is formally visible-UNSAT;
        # F12 SHOP-01 is the next legal pair and passes. SHOP-02 is gap=2 and
        # must be rejected before this formal probe is called.
        return "U01-MA-SHOP-01" in current_refs

    monkeypatch.setattr(r4r3r3, "_formal_pair_passes", formal_pair)
    selected = r4r3r3._formal_learner_visible_candidate_swap(
        Path("ignored.sqlite3"),
        current_form=8,
        failing_ref="U01-MA-SHOP-04",
        all_rows=rows,
        frozen_forms=set(),
    )
    assert selected is not None
    donor_form, donor_ref, simulated, _current_speaking, _donor_speaking = selected
    assert donor_form == 12
    assert donor_ref == "U01-MA-SHOP-01"
    assert any("U01-C4-TOY-SHOP" in refs for refs in attempted_current_refs)
    assert any("U01-MA-SHOP-01" in refs for refs in attempted_current_refs)
    assert not any("U01-MA-SHOP-02" in refs for refs in attempted_current_refs)
    assert {
        str(row["scene_ref_id"])
        for row in simulated
        if int(row["form_ordinal"]) == 8
    } == {"U01-MA-SHOP-01"}


def test_r4r3r3_filters_formally_bad_single_exposure_before_preserving_legacy_priority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows: list[dict[str, object]] = []
    rows += _package(4, 1, "REUSED-LEGAL", "SHOPPING", "toy")
    rows += _package(8, 1, "FAIL", "SHOPPING", "robot")
    rows += _package(9, 1, "SINGLE-BUT-FORMAL-BAD", "SHOPPING", "book")
    rows += _package(11, 1, "REUSED-LEGAL", "SHOPPING", "toy")
    _install_capacity_stubs(monkeypatch)

    def formal_pair(**kwargs) -> bool:
        current_refs = {
            str(row["scene_ref_id"])
            for row in kwargs["simulated"]
            if int(row["form_ordinal"]) == 8
        }
        return "REUSED-LEGAL" in current_refs

    monkeypatch.setattr(r4r3r3, "_formal_pair_passes", formal_pair)
    selected = r4r3r3._formal_learner_visible_candidate_swap(
        Path("ignored.sqlite3"),
        current_form=8,
        failing_ref="FAIL",
        all_rows=rows,
        frozen_forms=set(),
    )
    assert selected is not None
    assert selected[0] == 11
    assert selected[1] == "REUSED-LEGAL"


def test_r4r3r3_install_keeps_u16c_public_owner_and_uses_installed_visible_matcher() -> None:
    assert r4r3r3.installed() is True
    assert r4r3r1._candidate_swap is r4r3r3._formal_learner_visible_candidate_swap
    assert matching.solve_distinct_activity_assignment is visible.solve_learner_visible_distinct_activity_assignment
    assert owner.installed() is True
    assert matching.assemble_form_component is u16c.assemble_form_component
    assert u16c.migrate_unbound_reading_form is owner._ORIGINAL_U16C_READING_MIGRATION


def test_r4r3r3_scope_is_read_only_non_content_producer() -> None:
    assert r4r3r3.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert "474-item QuestionBank" in r4r3r3.A1FS_CONTENT_POLICY_EXEMPTION
    assert "authors no content" in r4r3r3.A1FS_CONTENT_POLICY_EXEMPTION
    assert r4r3r3.NEXT_SHORT_STEP == r4r3r3.r4r3r2.NEXT_SHORT_STEP
