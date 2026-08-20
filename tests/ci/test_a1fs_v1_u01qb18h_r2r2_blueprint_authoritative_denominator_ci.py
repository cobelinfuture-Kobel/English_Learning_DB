from __future__ import annotations

import json
from collections import Counter

from ulga.builders import (
    build_a1fs_v1_u01qb18h_r2r2_unit01_sentence_pool_driven_production_capacity_reconciliation
    as builder,
)


def _blueprint_43() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    plan = [
        *("ERROR_CHECK" for _ in range(10)),
        *("COMPLETE_SENTENCE_PRODUCTION" for _ in range(22)),
        *("CONNECTED_SENTENCE_PRODUCTION" for _ in range(11)),
    ]
    for index, angle in enumerate(plan, start=1):
        family = builder.PRODUCTION_ANGLE_TO_FAMILY[angle]
        rows.append(
            {
                "activity_id": f"U01-R2R2-DYNAMIC-{index:03d}",
                "form_id": f"U01-FORM-{((index - 1) % 12) + 1:02d}",
                "form_ordinal": ((index - 1) % 12) + 1,
                "scene_ref_id": f"R2R2-DYNAMIC-SCENE-{index:03d}",
                "situation_family": "HOME",
                "setting": "HOME",
                "skill": "WRITING",
                "task_angle": angle,
                "support_level": "INDEPENDENT",
                "assessment_candidate": False,
                "pattern_family_ids_json": json.dumps([family]),
            }
        )
    for index in range(len(rows) + 1, builder.EXPECTED_BLUEPRINT_ACTIVITY_COUNT + 1):
        rows.append(
            {
                "activity_id": f"U01-R2R2-FILLER-{index:03d}",
                "form_id": f"U01-FORM-{((index - 1) % 12) + 1:02d}",
                "form_ordinal": ((index - 1) % 12) + 1,
                "scene_ref_id": f"R2R2-FILLER-{index:03d}",
                "situation_family": "HOME",
                "setting": "HOME",
                "skill": "READING",
                "task_angle": "ARTICLE_CONTROL",
                "support_level": "GUIDED",
                "assessment_candidate": False,
                "pattern_family_ids_json": json.dumps(["U01-PF04-FIRST-MENTION-CONTEXT"]),
            }
        )
    assert len(rows) == 240
    return rows


def test_blueprint_requirement_denominator_is_dynamic_not_hardcoded_48() -> None:
    requirements = builder.production_requirements(_blueprint_43())
    assert len(requirements) == 43
    assert builder._normalized_family_counts(
        Counter(row["pattern_family_id"] for row in requirements)
    ) == {
        builder.u10.PF13: 10,
        builder.u10.PF14: 22,
        builder.u10.PF15: 11,
    }
    assert builder.count_preservation(43) == {
        "base_count_before": 288,
        "retired_production_item_count": 43,
        "materialized_production_item_count": 43,
        "base_count_after": 288,
        "real62_extension_count": 186,
        "runtime_count_after": 474,
        "question_bank_total_expanded": False,
    }


def test_blueprint_requirement_family_may_not_exceed_historical_inventory_capacity() -> None:
    rows = _blueprint_43()
    for index in range(11):
        rows[index]["task_angle"] = "ERROR_CHECK"
        rows[index]["pattern_family_ids_json"] = json.dumps([builder.u10.PF13])
    # Add two more PF13 rows by converting PF14 rows, pushing PF13 to 13 > 12.
    for index in (11, 12):
        rows[index]["task_angle"] = "ERROR_CHECK"
        rows[index]["pattern_family_ids_json"] = json.dumps([builder.u10.PF13])
    try:
        builder.production_requirements(rows)
    except builder.SentencePoolCapacityError as exc:
        assert "BLUEPRINT_PRODUCTION_FAMILY_CAPACITY_EXCEEDED" in str(exc)
    else:
        raise AssertionError("family capacity overflow must fail closed")
