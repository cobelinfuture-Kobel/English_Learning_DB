from ulga.builders import (
    build_a1fs_v1_u02ch02_unit01_unit02_cumulative_chunk_coverage_recheck as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u02ch02_unit01_unit02_cumulative_chunk_coverage_recheck as validator,
)


def report():
    value = builder.build_report()
    validation = validator.validate_report(value)
    assert validation["error_count"] == 0
    return value


def test_u02ch02_reconciles_current_unit01_and_unit02_chunk_phrase_denominators():
    counts = report()["coverage_denominators"]
    assert counts["unit01_reference_inventory_rows"] == 24
    assert counts["unit01_canonical_chunk_rows"] == 3
    assert counts["unit01_instructional_phrase_rows"] == 21
    assert counts["unit01_direct_or_instructional_surface_rows"] == 23
    assert counts["unit01_receptive_only_surface_rows"] == 1
    assert counts["unit02_native_surface_rows"] == 26
    assert counts["unit02_unit_admitted_phrase_rows"] == 23
    assert counts["unit02_derived_unit_form_rows"] == 3


def test_u02ch02_closes_exact_cumulative_surface_count_without_double_counting():
    value = report()
    counts = value["coverage_denominators"]
    assert counts["cross_unit_exact_surface_overlap_count"] == 0
    assert counts["cumulative_distinct_surface_rows"] == 50
    assert counts["cumulative_direct_or_instructional_surface_rows"] == 49
    assert counts["cumulative_receptive_only_surface_rows"] == 1
    assert value["surface_reconciliation"]["unit01_receptive_only_surfaces"] == ["ice cream"]


def test_u02ch02_preserves_canonical_identity_without_promoting_derived_forms():
    value = report()
    assert value["coverage_denominators"]["referenced_global_canonical_parent_id_count"] == 4
    assert value["surface_reconciliation"]["referenced_global_canonical_parent_ids"] == [
        "EVP_CHUNK_000003",
        "EVP_CHUNK_000030",
        "EVP_CHUNK_000054",
        "EVP_CHUNK_000075",
    ]
    assert value["claim_boundaries"]["global_chunk_authority_mutated"] is False
    assert value["claim_boundaries"]["unit01_assets_auto_admitted_to_unit02"] is False
    assert value["claim_boundaries"]["questionbank_mutated"] is False
