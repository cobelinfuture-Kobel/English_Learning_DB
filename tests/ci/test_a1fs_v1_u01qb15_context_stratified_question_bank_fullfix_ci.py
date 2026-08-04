from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u01qb15_unit01_context_stratified_question_bank_replacement_and_per_scene_runtime_capacity_fullfix as builder
from ulga.validators import validate_a1fs_v1_u01qb15_unit01_context_stratified_question_bank_replacement_and_per_scene_runtime_capacity_fullfix as validator


def _context_counts(rows: list[dict]) -> dict[str, int]:
    result = {context: 0 for context in builder.u01qb10.seed.CONTEXT_IDS}
    for row in rows:
        result[builder._pair_key(row)[0]] += 1
    return result


def test_solved_context_quotas_are_bounded_count_preserving_and_overlap_is_intentional() -> None:
    payload = builder.build_payload()
    replacement = payload["u01qb10_context_stratified_replacement"]
    quotas = replacement["context_quota_by_family"]
    assert set(quotas) == set(builder.REPLACEMENT_FAMILIES)

    _approved, seed_items = builder.u01qb10.seed_bank()
    replacements = builder.context_stratified_u01qb10_replacement_sources(seed_items)
    for family in builder.REPLACEMENT_FAMILIES:
        assert set(quotas[family]) == set(builder.u01qb10.seed.CONTEXT_IDS)
        assert sum(quotas[family].values()) == 12
        assert all(
            builder.MIN_CONTEXT_QUOTA <= value <= builder.MAX_CONTEXT_QUOTA
            for value in quotas[family].values()
        )
        assert len(replacements[family]) == 12
        assert _context_counts(replacements[family]) == quotas[family]

    reading_pairs = [
        builder._pair_key(row)
        for family in builder.READING_REPLACEMENT_FAMILIES
        for row in replacements[family]
    ]
    assert len(reading_pairs) == 36
    assert len(set(reading_pairs)) < 36
    assert replacement["reading_retired_selection_count"] == 36
    assert replacement["reading_retired_unique_pair_count"] == len(set(reading_pairs))
    assert replacement["reading_retired_context_noun_pair_overlap_allowed"] is True
    assert replacement["exact_scene_capacity_is_authoritative"] is True

    # C3/egg is the concrete structural witness: PF04 and PF05 both retire it,
    # creating PF13+PF14 production angles while PF08 remains available for
    # Reading transfer.  This is why blanket pair-disjointness is invalid.
    c3 = "U01-C3-PICNIC-FOOD"
    egg = (c3, "egg")
    by_family = {
        family: {builder._pair_key(row) for row in replacements[family]}
        for family in builder.READING_REPLACEMENT_FAMILIES
    }
    assert egg in by_family[builder.READING_REPLACEMENT_FAMILIES[0]]
    assert egg in by_family[builder.READING_REPLACEMENT_FAMILIES[1]]
    assert egg not in by_family[builder.READING_REPLACEMENT_FAMILIES[2]]


def test_u01qb12_reference_replacement_remains_fixed_context_stratified() -> None:
    intermediate = builder.build_context_stratified_u01qb10_items()[1]
    rows = builder.context_stratified_u01qb12_reference_sources(intermediate)
    assert len(rows) == 24
    assert _context_counts(rows) == {
        "U01-C1-CLASSROOM-BAG": 5,
        "U01-C2-HOME-TOY-BOX": 5,
        "U01-C3-PICNIC-FOOD": 5,
        "U01-C4-TOY-SHOP": 5,
        "U01-C5-PARK-BIRTHDAY": 4,
    }


def test_final_288_base_proves_all_31_scene_36_session_capacity_without_real62() -> None:
    payload = builder.build_payload()
    assert payload["count_preservation"] == {
        "base_item_count": 288,
        "u01qb10_retired_and_added": 48,
        "u01qb12_retired_and_added": 36,
        "unchanged_real62_extension_count": 186,
        "projected_runtime_total_count": 474,
    }
    survival = payload["reading_context_noun_survival"]
    assert survival["approved_context_noun_pair_count"] == 47
    assert survival["diagnostic_only_not_acceptance_gate"] is True
    assert survival["authoritative_acceptance_gate"] == "PER_SCENE_RUNTIME_CAPACITY"

    capacity = payload["per_scene_runtime_capacity"]
    assert capacity["proof_mode"] == "FINAL_288_BASE_ONLY_NO_REAL62_ASSISTANCE"
    assert capacity["cumulative_scene_world_count"] == 32
    assert capacity["runtime_bindable_scene_count"] == 31
    assert capacity["deferred_scene_refs"] == ["U01-MA-FOOD-04"]
    assert capacity["form_count"] == 12
    assert capacity["skill_session_count"] == 36
    assert capacity["verified_activity_count"] == 240
    assert capacity["all_36_skill_sessions_distinct_item_capacity_proven"] is True
    assert capacity["real62_used_for_capacity_proof"] is False


def test_candidate_and_approved_validate_and_quota_tamper_fails_closed() -> None:
    candidate = builder.build_candidate()
    receipt = validator.validate_candidate(candidate)
    assert receipt["status"] == "PASS"
    approved = builder.admit_candidate(candidate)
    report = validator.validate_approved(candidate, approved)
    assert report["error_count"] == 0

    tampered = deepcopy(candidate["payload"])
    family = builder.READING_REPLACEMENT_FAMILIES[0]
    tampered["u01qb10_context_stratified_replacement"]["context_quota_by_family"][family]["U01-C1-CLASSROOM-BAG"] = 12
    unsigned = dict(tampered)
    unsigned.pop("reconciliation_sha256", None)
    tampered["reconciliation_sha256"] = policy_artifact.digest(unsigned)
    with pytest.raises(validator.U01QB15ValidationError, match="QUOTA_"):
        validator.validate_payload(tampered)
