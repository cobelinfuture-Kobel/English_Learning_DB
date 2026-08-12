from __future__ import annotations

import json
from pathlib import Path

import pytest

from product import a1fs_v1_2_1 as product_package  # noqa: F401
from ulga.builders import _u01qb13_distinct_item_matching_adapter as matching
from ulga.builders import _u01qb16c_unbound_form_progression_overlay as u16c
from ulga.builders import _u01qb18f_r4r2_r1_preserve_u16c_public_ownership_adapter as owner
from ulga.builders import _u01qb18f_r4r3r1_support_stage_scene_swap_fullfix as r4r3r1
from ulga.builders import _u01qb18f_r4r3r2_broaden_pairwise_donor_eligibility_fullfix as r4r3r2


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


def _rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    # Exact production-shaped SHOPPING exposure identities from the R4R3R1 diagnostic.
    rows += _package(4, 1, "U01-C4-TOY-SHOP", "SHOPPING", "toy")
    rows += _package(5, 1, "U01-MA-SHOP-01", "SHOPPING", "book")
    rows += _package(6, 1, "U01-MA-SHOP-02", "SHOPPING", "bag")
    rows += _package(8, 1, "U01-MA-SHOP-04", "SHOPPING", "robot")
    rows += _package(11, 1, "U01-C4-TOY-SHOP", "SHOPPING", "toy")
    rows += _package(12, 1, "U01-MA-SHOP-01", "SHOPPING", "book")
    rows += _package(12, 2, "U01-MA-SHOP-02", "SHOPPING", "bag")
    return rows


def test_r4r3r2_selects_nearest_legal_reused_scene_donor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = _rows()
    monkeypatch.setattr(r4r3r2, "_ORIGINAL_CANDIDATE_SWAP", lambda *args, **kwargs: None)
    monkeypatch.setattr(r4r3r2.runtime_allocation, "_catalog", lambda _db: {})

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
    selected = r4r3r2._broadened_candidate_swap(
        Path("ignored.sqlite3"),
        current_form=8,
        failing_ref="U01-MA-SHOP-04",
        all_rows=rows,
        frozen_forms=set(),
    )
    assert selected is not None
    donor_form, donor_ref, simulated, current_speaking, donor_speaking = selected
    assert donor_form == 11
    assert donor_ref == "U01-C4-TOY-SHOP"
    assert current_speaking["U01-C4-TOY-SHOP"] == ("SCENE_DESCRIPTION",)
    assert donor_speaking["U01-MA-SHOP-04"] == ("SCENE_DESCRIPTION",)

    # Donor exposure moves from F11 to F08; F04/F08 gap remains four Forms.
    effective_toy_forms = sorted(
        {
            int(row["form_ordinal"])
            for row in simulated
            if str(row["scene_ref_id"]) == "U01-C4-TOY-SHOP"
        }
    )
    assert effective_toy_forms == [4, 8]


def test_r4r3r2_rejects_exposure_two_donor_when_post_swap_gap_is_too_small(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = []
    rows += _package(6, 1, "U01-MA-SHOP-02", "SHOPPING", "bag")
    rows += _package(8, 1, "U01-MA-SHOP-04", "SHOPPING", "robot")
    rows += _package(12, 1, "U01-MA-SHOP-02", "SHOPPING", "bag")
    monkeypatch.setattr(r4r3r2, "_ORIGINAL_CANDIDATE_SWAP", lambda *args, **kwargs: None)
    monkeypatch.setattr(r4r3r2.runtime_allocation, "_catalog", lambda _db: {})

    called = False

    def should_not_reach_capacity(**_kwargs):
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(r4r3r1, "_form_skill_choices", should_not_reach_capacity)
    assert r4r3r2._broadened_candidate_swap(
        Path("ignored.sqlite3"),
        current_form=8,
        failing_ref="U01-MA-SHOP-04",
        all_rows=rows,
        frozen_forms=set(),
    ) is None
    assert called is False


def test_r4r3r2_preserves_legacy_candidate_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = (9, "LEGACY", [], {}, {})
    monkeypatch.setattr(r4r3r2, "_ORIGINAL_CANDIDATE_SWAP", lambda *args, **kwargs: sentinel)
    assert r4r3r2._broadened_candidate_swap(
        Path("ignored.sqlite3"),
        current_form=8,
        failing_ref="U01-MA-SHOP-04",
        all_rows=[],
        frozen_forms=set(),
    ) is sentinel


def test_r4r3r2_is_installed_without_changing_u16c_public_owner() -> None:
    assert r4r3r2.installed() is True
    assert r4r3r1._candidate_swap is r4r3r2._broadened_candidate_swap
    assert owner.installed() is True
    assert matching.assemble_form_component is u16c.assemble_form_component
    assert u16c.migrate_unbound_reading_form is owner._ORIGINAL_U16C_READING_MIGRATION


def test_r4r3r2_scope_is_non_content_producer() -> None:
    assert r4r3r2.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert "474-item runtime" in r4r3r2.A1FS_CONTENT_POLICY_EXEMPTION
    assert "authors no content" in r4r3r2.A1FS_CONTENT_POLICY_EXEMPTION
    assert r4r3r2.NEXT_SHORT_STEP == r4r3r1.NEXT_SHORT_STEP
