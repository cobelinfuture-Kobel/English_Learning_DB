from ulga.builders import build_a1fs_v1_u02ch01_unit02_native_chunk_assets as builder
from ulga.validators import validate_a1fs_v1_u02ch01_unit02_native_chunk_assets as validator


def approved_payload():
    candidate = builder.build_candidate()
    approved = builder.admit_candidate(candidate)
    report = validator.validate_approved(candidate, approved)
    assert report["error_count"] == 0
    return approved["payload"]


def test_u02ch01_materializes_exact_unit02_native_chunk_asset_core():
    payload = approved_payload()
    coverage = payload["coverage_denominators"]

    assert coverage["unit02_native_chunk_asset_count"] == 26
    assert coverage["unit_admitted_phrase_count"] == 23
    assert coverage["derived_unit_form_count"] == 3
    assert coverage["family_counts"] == {
        builder.FAMILY_NUM_PLURAL: 13,
        builder.FAMILY_ADJ_PLURAL: 5,
        builder.FAMILY_NUM_ADJ_PLURAL: 5,
        builder.FAMILY_CANONICAL_DERIVED: 3,
    }


def test_u02ch01_unit01_is_baseline_not_unit02_substitute():
    payload = approved_payload()
    inheritance = payload["inheritance_contract"]

    assert inheritance["unit01_used_as_lexical_semantic_baseline"] is True
    assert inheritance["unit01_assets_auto_admitted_to_unit02"] is False
    assert inheritance["unit02_requires_native_assets"] is True

    surfaces = {row["surface"] for row in payload["unit02_native_assets"]}
    assert {
        "two apples", "two bags", "two beds", "two books", "two cats",
        "two desks", "two dogs", "two doors", "two eggs", "two parks",
        "two rooms", "two trees", "two windows",
    }.issubset(surfaces)


def test_u02ch01_has_governed_adjective_and_number_adjective_chunks():
    surfaces = {row["surface"] for row in approved_payload()["unit02_native_assets"]}

    assert {
        "small bags", "red books", "blue bags", "new books", "old books",
    }.issubset(surfaces)
    assert {
        "two small bags", "two red books", "two blue bags",
        "two new books", "two old books",
    }.issubset(surfaces)
    assert "big boxes" not in surfaces
    assert "two big boxes" not in surfaces


def test_u02ch01_derives_plural_forms_without_promoting_new_global_chunks():
    rows = approved_payload()["unit02_native_assets"]
    derived = {
        row["surface"]: row
        for row in rows
        if row["authority_scope"] == "DERIVED_UNIT_FORM"
    }

    assert set(derived) == {"CD players", "dining rooms", "living rooms"}
    assert derived["CD players"]["parent_canonical_chunk_id"] == "EVP_CHUNK_000003"
    assert derived["dining rooms"]["parent_canonical_chunk_id"] == "EVP_CHUNK_000030"
    assert derived["living rooms"]["parent_canonical_chunk_id"] == "EVP_CHUNK_000075"
    assert all(row["global_canonical_created"] is False for row in derived.values())
    assert "ice creams" not in derived


def test_u02ch01_does_not_confuse_vocabulary_or_questionbank_capacity_with_chunks():
    coverage = approved_payload()["coverage_denominators"]

    assert coverage["u02qb01_plain_s_noun_surface_count_not_chunk_denominator"] == 162
    assert coverage["u02qb02_approved_question_count_not_chunk_denominator"] == 658
    assert coverage["unit02_native_chunk_asset_count"] == 26
