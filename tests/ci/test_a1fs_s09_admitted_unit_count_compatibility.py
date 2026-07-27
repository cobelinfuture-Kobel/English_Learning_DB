from __future__ import annotations

import pytest

from ulga.builders import build_a1fs_online_v1_s09_twentyfour_unit_production_population as s09


def _admission() -> dict:
    return {
        "task_id": s09.TASK_ID,
        "population_summary": {
            "canonical_unit_denominator": 24,
            "populated_unit_count": 24,
            "reading_item_count": 96,
            "writing_item_count": 96,
            "speaking_practice_card_count": 72,
            "admitted_nonaudio_item_count": 264,
            "runtime_lesson_count": 72,
        },
    }


def test_s09_maps_populated_unit_count_to_exact_s07_legacy_key(monkeypatch) -> None:
    admission = _admission()
    captured: dict = {}

    def strict_s07_build_consumer(compatible, _m03):
        summary = compatible["admission_summary"]
        captured.update(summary)
        admitted_unit_count = summary["admitted_unit_count"]
        assert admitted_unit_count == 24
        assert summary["populated_unit_count"] == 24
        return {
            "asset_records": [],
            "lesson_catalog": [],
            "counts": {"lesson_count": 72, "asset_record_count": 264},
            "s07_runtime_projection": {
                "admitted_unit_count": admitted_unit_count,
            },
            "next_short_step": "S07_LEGACY_NEXT",
        }

    monkeypatch.setattr(s09.s07, "build_consumer", strict_s07_build_consumer)
    consumer = s09.build_consumer(admission, {})

    assert "admission_summary" not in admission
    assert "admitted_unit_count" not in admission["population_summary"]
    assert captured["admitted_unit_count"] == 24
    assert consumer["counts"] == {"lesson_count": 72, "asset_record_count": 264}
    assert consumer["s09_runtime_projection"]["admitted_unit_count"] == 24


def test_s09_compatibility_projection_fails_closed_without_populated_count() -> None:
    with pytest.raises(
        s09.PopulationError,
        match="population_summary_populated_unit_count_invalid:None",
    ):
        s09._s07_compatible_admission({"population_summary": {}})


def test_s09_compatibility_projection_rejects_legacy_namespace_collision() -> None:
    admission = _admission()
    admission["population_summary"]["admitted_unit_count"] = 24
    with pytest.raises(
        s09.PopulationError,
        match="population_summary_legacy_namespace_collision",
    ):
        s09._s07_compatible_admission(admission)
