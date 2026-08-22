from ulga.builders import (
    build_a1fs_v1_u02sc01_unit02_vocabulary_scene_coverage_matrix as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u02sc01_unit02_vocabulary_scene_coverage_matrix as validator,
)


def validated_payload():
    payload = builder.payload()
    report = validator.validate_payload(payload)
    assert report["error_count"] == 0
    return payload


def test_u02sc01_assigns_all_162_plain_s_nouns_to_one_primary_scene_family():
    payload = validated_payload()
    rows = payload["rows"]
    counts = payload["coverage_denominators"]

    assert len(rows) == 162
    assert len({row["singular"] for row in rows}) == 162
    assert counts["exact_vocabulary_ref_count"] == 171
    assert counts["primary_scene_family_count"] == 18
    assert counts["primary_scene_family_counts"] == dict(
        sorted(builder.EXPECTED_FAMILY_COUNTS.items())
    )


def test_u02sc01_keeps_primary_identity_distinct_from_secondary_contexts():
    rows = {row["singular"]: row for row in validated_payload()["rows"]}

    assert rows["book"]["primary_scene_family"] == "SCHOOL_CLASSROOM_LEARNING"
    assert rows["book"]["secondary_scene_families"] == [
        "SHOP_MONEY_SERVICES",
        "HOME_BEDROOM_LIVING",
    ]
    assert rows["apple"]["primary_scene_family"] == "FOOD_CAFE_PICNIC"
    assert "KITCHEN_DINING" in rows["apple"]["secondary_scene_families"]
    assert rows["train"]["primary_scene_family"] == "TRANSPORT_TRAVEL"
    assert rows["train"]["secondary_scene_families"] == ["TOWN_PUBLIC_PLACES"]


def test_u02sc01_exposes_unit02_pattern_eligibility_without_cartesian_product():
    rows = {row["singular"]: row for row in validated_payload()["rows"]}

    assert rows["book"]["pattern_eligibility"] == {
        "observation": True,
        "possession": True,
        "preference_positive": True,
        "preference_negative": True,
        "request": True,
        "governed_adjective_contrast": True,
    }
    assert rows["bag"]["pattern_eligibility"]["governed_adjective_contrast"] is True
    assert rows["cat"]["pattern_eligibility"]["preference_positive"] is True
    assert rows["cat"]["pattern_eligibility"]["request"] is False
    assert rows["train"]["pattern_eligibility"]["observation"] is True
    assert rows["train"]["pattern_eligibility"]["request"] is False

    adjective_enabled = {
        row["singular"]
        for row in rows.values()
        if row["pattern_eligibility"]["governed_adjective_contrast"]
    }
    assert adjective_enabled == {"bag", "book"}


def test_u02sc01_fails_closed_on_child_suitability_and_plural_sense_risks():
    rows = {row["singular"]: row for row in validated_payload()["rows"]}

    assert rows["beer"]["scene_gate"] == "PEDAGOGICAL_DEFER"
    assert rows["beer"]["child_suitable"] is False
    assert not any(rows["beer"]["pattern_eligibility"].values())

    assert rows["bar"]["scene_gate"] == "PEDAGOGICAL_DEFER"
    assert rows["bar"]["child_suitable"] is False
    assert rows["bar"]["sense_check_required"] is True

    for singular in ("coffee", "fruit", "ice cream", "juice", "soup", "tea"):
        assert rows[singular]["scene_gate"] == "SENSE_CHECK_REQUIRED"
        assert rows[singular]["sense_check_required"] is True

    assert rows["sun"]["scene_gate"] == "PEDAGOGICAL_DEFER"


def test_u02sc01_marks_meta_language_as_support_not_scene_driver():
    rows = {row["singular"]: row for row in validated_payload()["rows"]}

    for singular in (
        "answer", "conversation", "course", "language", "lesson",
        "question", "sentence", "subject", "test", "word",
    ):
        assert rows[singular]["scene_gate"] == "SUPPORT_ONLY"


def test_u02sc01_is_projection_only_and_does_not_create_scenes():
    payload = validated_payload()

    assert payload["projection_contract"][
        "unit01_scene_identity_reuse_preferred_before_unit02_scene_creation"
    ] is True
    assert payload["projection_contract"][
        "unit02_new_scene_count_is_coverage_gap_driven_not_preallocated"
    ] is True
    assert payload["claim_boundaries"] == {
        "canonical_scene_authority_mutated": False,
        "unit01_scene_authority_mutated": False,
        "vocabulary_authority_mutated": False,
        "chunk_authority_mutated": False,
        "questionbank_mutated": False,
        "learner_runtime_connected": False,
        "new_scene_created": False,
        "a2_unlocked": False,
    }
    assert payload["next_short_step"] == (
        "A1FS-V1-U02SC02_Unit01CanonicalSceneToUnit02ApplicabilityProjection"
    )
