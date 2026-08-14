from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from product import a1fs_v1_2_1 as product_package  # noqa: F401
from ulga.builders import _u01qb13_distinct_item_matching_adapter as matching
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u13
from ulga.builders import _u01qb16c_unbound_form_progression_overlay as u16c
from ulga.builders import _u01qb18f_r4r2_r1_preserve_u16c_public_ownership_adapter as owner
from ulga.builders import _u01qb18f_r4r3r4_unbound_reading_formal_selector_parity_fullfix as r4r3r4


def _rows() -> list[dict[str, object]]:
    values: list[dict[str, object]] = []
    for slot in range(1, 5):
        ref = f"SCENE-{slot}"
        for activity, angle in ((1, "TRANSFER_DECISION"), (2, "REFERENCE_EVIDENCE")):
            values.append(
                {
                    "activity_id": f"U01-FORM-12-S{slot:02d}-A{activity:02d}",
                    "form_ordinal": 12,
                    "scene_ref_id": ref,
                    "situation_family": "SHOPPING",
                    "skill": "READING",
                    "task_angle": angle,
                    "support_level": "TRANSFER",
                    "scored": 1,
                    "assessment_candidate": 1,
                    "pattern_family_ids_json": "[]",
                    "scene_anchors_json": '["robot"]',
                    "activity_digest": f"D-{slot}-{activity}",
                }
            )
    return values


def test_r4r3r4_formal_reading_chooser_can_reject_raw_first_angle_and_select_next(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = _rows()

    def formal_exists(activities, **_kwargs) -> bool:
        # Model the production defect: raw task capacity selected TRANSFER_DECISION,
        # but the installed formal selector has no executable candidate for that
        # activity. Other ordinary TRANSFER Reading angles remain executable.
        return all(str(row["task_angle"]) != "TRANSFER_DECISION" for row in activities)

    monkeypatch.setattr(r4r3r4, "_formal_assignment_exists", formal_exists)
    selected = r4r3r4.choose_form_rows(
        rows,
        prior={},
        catalog=[],
        scoring={},
        session_id="TEST",
    )
    assert len(selected) == 8
    assert all(str(row["task_angle"]) != "TRANSFER_DECISION" for row in selected)
    by_scene: dict[str, set[str]] = {}
    for row in selected:
        by_scene.setdefault(str(row["scene_ref_id"]), set()).add(str(row["task_angle"]))
    assert len(by_scene) == 4
    assert all(len(angles) == 2 for angles in by_scene.values())


def test_r4r3r4_historical_schema_falls_back_to_original_u16c_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = [{"activity_id": "SENTINEL"}]
    monkeypatch.setattr(r4r3r4.r4r3r3, "_formal_schema_present", lambda _db: False)
    monkeypatch.setattr(
        r4r3r4,
        "_ORIGINAL_U16C_MIGRATION_PLAN",
        lambda *_args, **_kwargs: sentinel,
    )
    result = r4r3r4._formal_reading_migration_plan(
        Path("ignored.sqlite3"),
        form_ordinal=12,
        rows=_rows(),
        prior={},
    )
    assert result is sentinel


def test_r4r3r4_formal_pair_uses_reading_parity_chooser_not_raw_reading_choices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = _rows()
    donor_rows = [dict(row, form_ordinal=11, activity_id=str(row["activity_id"]).replace("12", "11", 1)) for row in rows]
    simulated = rows + donor_rows
    calls: list[int] = []

    def choose(reading_rows, **_kwargs):
        calls.append(int(reading_rows[0]["form_ordinal"]))
        return list(reading_rows)

    monkeypatch.setattr(r4r3r4, "choose_form_rows", choose)
    monkeypatch.setattr(r4r3r4.r4r3r3, "_writing_form_exists", lambda *_args, **_kwargs: True)
    assert r4r3r4._formal_pair_passes_with_reading_parity(
        simulated=simulated,
        current_form=12,
        donor_form=11,
        current_choices={"READING": {}},
        donor_choices={"READING": {}},
        catalog={"READING": [], "WRITING": []},
        scoring={"READING": {}, "WRITING": {}},
    ) is True
    assert calls == [12, 11]


def test_r4r3r4_preserves_u16c_public_owner_and_direct_migration_api() -> None:
    assert r4r3r4.installed() is True
    assert u16c._migration_plan is r4r3r4._formal_reading_migration_plan
    assert u16c.migrate_unbound_reading_form is owner._ORIGINAL_U16C_READING_MIGRATION
    assert matching.assemble_form_component is u16c.assemble_form_component
    assert owner.installed() is True


def test_r4r3r4_is_non_content_producer() -> None:
    assert r4r3r4.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert "474-item QuestionBank" in r4r3r4.A1FS_CONTENT_POLICY_EXEMPTION
    assert "authors no content" in r4r3r4.A1FS_CONTENT_POLICY_EXEMPTION


def test_context_classification_and_priority_are_explicit_and_fail_closed() -> None:
    neutral = {
        "pattern_family_id": "U01-PF04-FIRST-MENTION-CONTEXT",
        "skill": "READING",
        "content_kind": "MICRO_SCENE",
        "content_lineage_mode": "SEMANTIC_ANCHOR_A1_IMITATION",
        "content_asset_id": "U01-MS-SHOP",
        "lexical_slots": {"noun": "shop"},
        "source_refs": [{"source_type": "RAZQ01D_APPROVED_CONTENT_ASSET"}],
    }
    explicit = {
        "pattern_family_id": "U01-PF04-FIRST-MENTION-CONTEXT",
        "skill": "READING",
        "context_id": "U01-C4-TOY-SHOP",
        "lexical_slots": {"noun": "shop"},
    }
    mismatched = {**explicit, "context_id": "U01-C1-CLASSROOM-BAG"}

    assert u13._context_classification(
        explicit, "SHOPPING", scene_ref_id="U01-C4-TOY-SHOP"
    ) == u13.EXACT_CONTEXT
    assert u13._context_classification(
        neutral, "SHOPPING", scene_ref_id="U01-C4-TOY-SHOP"
    ) == u13.NEUTRAL_COMPATIBLE
    assert u13._context_classification(
        neutral, "SCHOOL", scene_ref_id="U01-C1-CLASSROOM-BAG"
    ) == u13.INCOMPATIBLE
    assert u13._context_classification(
        neutral, "SHOPPING", scene_ref_id="U01-C4-TOY-SHOP"
    ) != u13.INCOMPATIBLE
    assert u13._context_classification(
        neutral, "SHOPPING", scene_ref_id="U01-MA-SHOP-02"
    ) == u13.NEUTRAL_COMPATIBLE
    assert u13._context_classification(
        mismatched, "SHOPPING", scene_ref_id="U01-C4-TOY-SHOP"
    ) == u13.INCOMPATIBLE

    def row(item: dict[str, object], item_id: str) -> dict[str, object]:
        return {
            "private_item_json": json.dumps(item),
            "pattern_family_id": "U01-PF04-FIRST-MENTION-CONTEXT",
            "skill": "READING",
            "item_id": item_id,
        }

    rank_kwargs = {
        "anchors": {"shop"},
        "situation_family": "SHOPPING",
        "learner_id": "L",
        "session_id": "S",
        "activity_id": "A",
        "exposed": set(),
        "recent": set(),
        "assessment": False,
        "scene_ref_id": "U01-C4-TOY-SHOP",
    }
    exact_rank = u13._candidate_rank(row=row(explicit, "EXACT"), **rank_kwargs)
    neutral_rank = u13._candidate_rank(row=row(neutral, "NEUTRAL"), **rank_kwargs)
    assert exact_rank is not None and neutral_rank is not None
    assert exact_rank < neutral_rank

    exact_recent_rank = u13._candidate_rank(
        row=row(explicit, "EXACT"), **{**rank_kwargs, "recent": {"EXACT"}}
    )
    assert exact_recent_rank is not None
    assert exact_recent_rank < neutral_rank
    assert u13._candidate_rank(row=row(mismatched, "WRONG"), **rank_kwargs) is None


def test_prior_reading_item_lookup_excludes_current_form(tmp_path: Path) -> None:
    database = tmp_path / "bindings.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE u01qb13_blueprint_activities(
                activity_id TEXT PRIMARY KEY,
                form_ordinal INTEGER NOT NULL,
                scene_ref_id TEXT NOT NULL,
                skill TEXT NOT NULL
            );
            CREATE TABLE u01qb13_session_bindings(
                session_id TEXT NOT NULL,
                activity_id TEXT NOT NULL,
                item_id TEXT NOT NULL,
                item_position INTEGER NOT NULL
            );
            """
        )
        connection.executemany(
            "INSERT INTO u01qb13_blueprint_activities VALUES(?,?,?,?)",
            [
                ("F1-A", 1, "SCENE", "READING"),
                ("F2-A", 2, "SCENE", "READING"),
                ("F2-W", 2, "SCENE", "WRITING"),
            ],
        )
        connection.executemany(
            "INSERT INTO u01qb13_session_bindings VALUES(?,?,?,?)",
            [("S1", "F1-A", "ITEM-F1", 1), ("S2", "F2-A", "ITEM-F2", 1)],
        )

    assert r4r3r4._prior_reading_item_ids(database, 2) == {"SCENE": {"ITEM-F1"}}
    assert r4r3r4._prior_reading_item_ids(database, 3) == {
        "SCENE": {"ITEM-F1", "ITEM-F2"}
    }


def test_bound_current_reading_form_is_frozen_before_formal_migration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(r4r3r4.r4r3r3, "_formal_schema_present", lambda _db: True)
    monkeypatch.setattr(r4r3r4, "_form_has_reading_bindings", lambda *_args: True)
    monkeypatch.setattr(
        r4r3r4,
        "_reading_state",
        lambda _db: pytest.fail("BOUND_FORM_MUST_NOT_LOAD_MIGRATION_STATE"),
    )

    assert (
        r4r3r4._formal_reading_migration_plan(
            Path("ignored.sqlite3"),
            form_ordinal=2,
            rows=[],
            prior={},
        )
        == []
    )
