from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_a1fs_v1_u01qb15_unit01_context_stratified_question_bank_replacement_and_per_scene_runtime_capacity_fullfix as builder
from ulga.validators import validate_a1fs_v1_u01qb15_unit01_context_stratified_question_bank_replacement_and_per_scene_runtime_capacity_fullfix as validator


def test_u01qb10_replacement_is_context_stratified_and_reading_pairs_do_not_overlap() -> None:
    _approved, seed_items = builder.u01qb10.seed_bank()
    replacements = builder.context_stratified_u01qb10_replacement_sources(seed_items)
    assert builder.U01QB10_CONTEXT_QUOTA == {
        "U01-C1-CLASSROOM-BAG": 3,
        "U01-C2-HOME-TOY-BOX": 3,
        "U01-C3-PICNIC-FOOD": 2,
        "U01-C4-TOY-SHOP": 2,
        "U01-C5-PARK-BIRTHDAY": 2,
    }
    reading_pairs = []
    for family in builder.READING_REPLACEMENT_FAMILIES:
        rows = replacements[family]
        counts = {context: 0 for context in builder.u01qb10.seed.CONTEXT_IDS}
        for row in rows:
            context, noun = builder._pair_key(row)
            counts[context] += 1
            reading_pairs.append((context, noun))
        assert counts == builder.U01QB10_CONTEXT_QUOTA
    assert len(reading_pairs) == 36
    assert len(set(reading_pairs)) == 36


def test_u01qb12_reference_replacement_is_explicitly_context_stratified() -> None:
    intermediate = builder.build_context_stratified_u01qb10_items()[1]
    rows = builder.context_stratified_u01qb12_reference_sources(intermediate)
    counts = {context: 0 for context in builder.u01qb10.seed.CONTEXT_IDS}
    for row in rows:
        counts[builder._pair_key(row)[0]] += 1
    assert counts == {
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
    assert survival["minimum_surviving_context_bound_reading_identities_per_pair"] >= 2
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


def test_candidate_and_approved_validate_fail_closed_on_context_quota_tamper() -> None:
    candidate = builder.build_candidate()
    receipt = validator.validate_candidate(candidate)
    assert receipt["status"] == "PASS"
    approved = builder.admit_candidate(candidate)
    report = validator.validate_approved(candidate, approved)
    assert report["error_count"] == 0

    tampered = deepcopy(candidate)
    tampered["payload"]["u01qb10_context_stratified_replacement"]["context_quota"]["U01-C1-CLASSROOM-BAG"] = 12
    with pytest.raises(validator.U01QB15ValidationError, match="U01QB10_CONTEXT_QUOTA_INVALID"):
        validator.validate_payload(tampered["payload"])
