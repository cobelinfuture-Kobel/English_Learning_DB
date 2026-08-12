from __future__ import annotations

import sqlite3

from product import a1fs_v1_2_1 as product_package  # noqa: F401
from ulga.builders import _u01qb18f_r4r3_runtime_capacity_aware_reuse_scene_migration as r4r3
from ulga.builders import _u01qb18f_r4r3r1_support_stage_scene_swap_fullfix as r4r3r1
from ulga.builders import _u01qb18f_r4r3r3r2_formal_probe_row_schema_parity_adapter as r4r3r3r2


def _row(*, activity_id: str, form: int, ref: str, scored: int, assessment: int) -> dict[str, object]:
    return {
        "activity_id": activity_id,
        "form_id": f"U01-FORM-{form:02d}",
        "form_ordinal": form,
        "scene_ref_id": ref,
        "situation_family": "SHOPPING",
        "setting": f"SETTING-{ref}",
        "skill": "READING",
        "task_angle": "ERROR_CHECK",
        "support_level": "INDEPENDENT",
        "scored": scored,
        "assessment_candidate": assessment,
        "pattern_family_ids_json": "[]",
        "scene_anchors_json": "[\"toy\"]",
        "practice_projection_json": "{}",
        "activity_digest": f"DIGEST-{activity_id}",
    }


def test_all_rows_projection_preserves_scored_and_assessment_candidate() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(
        """CREATE TABLE u01qb13_blueprint_activities(
             activity_id TEXT, form_id TEXT, form_ordinal INTEGER,
             scene_ref_id TEXT, situation_family TEXT, setting TEXT,
             skill TEXT, task_angle TEXT, support_level TEXT,
             scored INTEGER, assessment_candidate INTEGER,
             pattern_family_ids_json TEXT, scene_anchors_json TEXT,
             practice_projection_json TEXT, activity_digest TEXT
           )"""
    )
    source = _row(
        activity_id="U01-FORM-08-S01-A01",
        form=8,
        ref="U01-MA-SHOP-04",
        scored=1,
        assessment=0,
    )
    connection.execute(
        """INSERT INTO u01qb13_blueprint_activities VALUES(
             :activity_id,:form_id,:form_ordinal,:scene_ref_id,:situation_family,:setting,
             :skill,:task_angle,:support_level,:scored,:assessment_candidate,
             :pattern_family_ids_json,:scene_anchors_json,:practice_projection_json,
             :activity_digest
           )""",
        source,
    )
    rows = r4r3._all_rows(connection)
    connection.close()

    assert len(rows) == 1
    assert rows[0]["scored"] == 1
    assert rows[0]["assessment_candidate"] == 0
    assert rows[0]["form_id"] == "U01-FORM-08"


def test_scene_swap_keeps_formal_flags_byte_for_byte() -> None:
    rows: list[dict[str, object]] = []
    skills = ("READING", "READING", "WRITING", "WRITING", "SPEAKING")
    for form, ref, assessment in ((8, "U01-MA-SHOP-04", 0), (12, "U01-MA-SHOP-01", 1)):
        for index, skill in enumerate(skills, 1):
            row = _row(
                activity_id=f"U01-FORM-{form:02d}-S01-A{index:02d}",
                form=form,
                ref=ref,
                scored=int(skill != "SPEAKING"),
                assessment=int(assessment and skill != "SPEAKING"),
            )
            row["skill"] = skill
            rows.append(row)

    before = {
        str(row["activity_id"]): (int(row["scored"]), int(row["assessment_candidate"]))
        for row in rows
    }
    swapped = r4r3r1._swap_scene_packages_in_memory(
        rows,
        current_form=8,
        failing_ref="U01-MA-SHOP-04",
        donor_form=12,
        donor_ref="U01-MA-SHOP-01",
    )
    after = {
        str(row["activity_id"]): (int(row["scored"]), int(row["assessment_candidate"]))
        for row in swapped
    }
    assert after == before


def test_r4r3r3r2_installed_without_changing_public_owners() -> None:
    assert r4r3r3r2.installed() is True
    assert r4r3._all_rows is r4r3r3r2._formal_complete_all_rows


def test_r4r3r3r2_scope_is_non_content_projection_only() -> None:
    assert r4r3r3r2.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert "authors no content" in r4r3r3r2.A1FS_CONTENT_POLICY_EXEMPTION
    assert r4r3r3r2.NEXT_SHORT_STEP == r4r3.NEXT_SHORT_STEP
