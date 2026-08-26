from functools import lru_cache

from ulga.builders import (
    build_a1fs_v1_u02qb03_unit02_cumulative_questionbank_runtime_integration as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u02qb03_unit02_cumulative_questionbank_runtime_integration as validator,
)


@lru_cache(maxsize=1)
def _report():
    return builder.build_report()


def test_u02qb03_runtime_integration_validates():
    report = _report()
    result = validator.validate_report(report)
    assert result["error_count"] == 0, result["errors"]


def test_u02qb03_preserves_cumulative_catalog_and_materializes_640_runtime_occurrences():
    report = _report()
    catalog = report["cumulative_questionbank_catalog"]
    runtime = report["runtime_form_contract"]
    assert catalog["unit01_reference_only_item_count"] == 474
    assert catalog["unit02_approved_item_count"] == 994
    assert catalog["cumulative_catalog_item_count"] == 1468
    assert runtime["form_count"] == 16
    assert runtime["activities_per_form"] == 40
    assert runtime["runtime_occurrence_count"] == 640
    assert runtime["runtime_connected"] is True


def test_u02qb03_reconciles_legacy_pattern_lineage_and_child_safe_runtime_filter():
    report = _report()
    assert report["pattern_reconciliation"]["raw_pattern_ids_runtime_authoritative"] is False
    assert report["runtime_eligibility"]["restricted_target_surfaces"] == ["beer"]
    assert all(row["target_singular"] != "beer" for row in report["runtime_occurrences"])
    assert all(
        row["runtime_pattern_lineage"]["runtime_may_consume_raw_pattern_ids"] is False
        for row in report["runtime_occurrences"]
    )


def test_u02qb03_binds_sentence_bearing_tasks_to_q6_sentence_assets():
    report = _report()
    required = {"PRODUCTIVE_RESPONSE", "TRANSFER"}
    rows = [row for row in report["runtime_occurrences"] if row["task_family"] in required]
    assert len(rows) == 128
    assert all(
        row["sentence_asset_binding"]["status"] == "BOUND_CANONICAL_Q6_SENTENCE_ASSET"
        and row["sentence_asset_binding"]["sentence_asset_id"]
        for row in rows
    )
    assert report["sentence_asset_integration"]["q6_assets_mutated"] is False
