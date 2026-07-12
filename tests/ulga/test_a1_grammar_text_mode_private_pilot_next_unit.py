from __future__ import annotations

import json

import pytest

from ulga.builders.run_a1_grammar_text_mode_private_pilot_next_unit import (
    build_preview_report,
    discover_execution_state,
    projection_state,
    select_next_unit,
)


def package_fixture():
    return {
        "artifact_id": "package:test",
        "learning_units": [
            {
                "sequence_index": 1,
                "grammar_unit_id": "UNIT_A",
                "prerequisite_unit_ids": [],
                "learning_content": {"title_en": "Unit A"},
                "delivery_plan": {
                    "practice_item_ids": [f"A_P{i}" for i in range(6)],
                    "assessment_item_ids": ["A_R", "A_W"],
                },
            },
            {
                "sequence_index": 2,
                "grammar_unit_id": "UNIT_B",
                "prerequisite_unit_ids": ["UNIT_A"],
                "learning_content": {"title_en": "Unit B"},
                "delivery_plan": {
                    "practice_item_ids": [f"B_P{i}" for i in range(6)],
                    "assessment_item_ids": ["B_R", "B_W"],
                },
            },
            {
                "sequence_index": 3,
                "grammar_unit_id": "UNIT_C",
                "prerequisite_unit_ids": [],
                "learning_content": {"title_en": "Unit C"},
                "delivery_plan": {
                    "practice_item_ids": [f"C_P{i}" for i in range(6)],
                    "assessment_item_ids": ["C_R", "C_W"],
                },
            },
        ],
    }


def projection_fixture(*, status_a="MASTERY_CANDIDATE_PENDING_RETENTION"):
    return {
        "by_grammar_unit_id": {
            "UNIT_A": {
                "attempted_item_count": 8,
                "required_item_count": 8,
                "projection_status": status_a,
            },
            "UNIT_B": {
                "attempted_item_count": 0,
                "required_item_count": 8,
                "projection_status": "NOT_MEASURED",
            },
        }
    }


def test_projection_state_separates_execution_from_progression_readiness():
    executed, ready = projection_state(
        projection_fixture(status_a="REVIEW_REQUIRED")
    )

    assert executed == {"UNIT_A"}
    assert ready == set()


def test_next_unit_uses_progression_ready_prerequisite():
    unit = select_next_unit(
        package_fixture(),
        executed_unit_ids={"UNIT_A"},
        progression_ready_unit_ids={"UNIT_A"},
    )

    assert unit["grammar_unit_id"] == "UNIT_B"


def test_failed_executed_unit_does_not_unlock_dependent_but_allows_independent():
    unit = select_next_unit(
        package_fixture(),
        executed_unit_ids={"UNIT_A"},
        progression_ready_unit_ids=set(),
    )

    assert unit["grammar_unit_id"] == "UNIT_C"


def test_requested_unit_fails_closed_when_prerequisite_not_ready():
    with pytest.raises(
        ValueError,
        match="private_pilot_requested_unit_prerequisites_not_ready",
    ):
        select_next_unit(
            package_fixture(),
            executed_unit_ids={"UNIT_A"},
            progression_ready_unit_ids=set(),
            requested_unit_id="UNIT_B",
        )


def test_all_executed_returns_none():
    unit = select_next_unit(
        package_fixture(),
        executed_unit_ids={"UNIT_A", "UNIT_B", "UNIT_C"},
        progression_ready_unit_ids={"UNIT_A", "UNIT_B", "UNIT_C"},
    )

    assert unit is None


def test_discovery_combines_legacy_and_isolated_projection_snapshots(tmp_path):
    local_root = tmp_path / ".local" / "units"
    snapshot = local_root / "UNIT_C" / "20260712T120000+0800"
    snapshot.mkdir(parents=True)
    legacy = tmp_path / ".local" / "legacy_projection.json"
    legacy.parent.mkdir(parents=True, exist_ok=True)

    legacy.write_text(
        json.dumps(projection_fixture()),
        encoding="utf-8",
    )
    (snapshot / "projection.json").write_text(
        json.dumps(
            {
                "by_grammar_unit_id": {
                    "UNIT_C": {
                        "attempted_item_count": 8,
                        "required_item_count": 8,
                        "projection_status": "REVIEW_REQUIRED",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    executed, ready, sources = discover_execution_state(
        local_root=local_root,
        legacy_projection_path=legacy,
    )

    assert executed == {"UNIT_A", "UNIT_C"}
    assert ready == {"UNIT_A"}
    assert len(sources) == 2


def test_preview_does_not_claim_evidence_or_persistent_state():
    unit = package_fixture()["learning_units"][1]

    report = build_preview_report(
        unit=unit,
        executed_unit_ids={"UNIT_A"},
        progression_ready_unit_ids={"UNIT_A"},
    )

    assert report["validation_status"] == "PASS"
    assert report["execution_status"] == "NEXT_UNIT_READY"
    assert report["grammar_unit_id"] == "UNIT_B"
    assert report["required_item_count"] == 8
    assert report["real_learner_evidence_created"] is False
    assert report["persistent_learner_state_write"] is False
