from ulga.builders import (
    build_a1fs_v1_u02qb02_unit02_plain_s_questionbank_candidate_pool as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u02qb02_unit02_plain_s_questionbank_candidate_pool as validator,
)


def test_u02qb02_builds_exact_governed_candidate_and_approved_pool():
    candidate = builder.build_candidate()
    receipt = validator.validate_candidate(candidate)
    assert receipt["status"] == "PASS"

    approved = builder.admit_candidate(candidate)
    report = validator.validate_approved(candidate, approved)
    assert report["error_count"] == 0
    assert report["candidate_count"] == 660
    assert report["approved_count"] == 658
    assert report["rejected_count"] == 2
    assert report["plain_s_noun_surface_count"] == 162
    assert report["covered_target_egp_row_count"] == 4


def test_u02qb02_preserves_cumulative_runtime_boundaries_and_exact_egp_scope():
    approved = builder.admit_candidate(builder.build_candidate())
    payload = approved["payload"]

    assert payload["bank_identity"]["unit01_runtime_base_item_count"] == 474
    assert payload["bank_identity"]["unit01_runtime_base_reused"] is True
    assert payload["bank_identity"]["parallel_questionbank_created"] is False
    assert payload["bank_identity"]["runtime_status"] == "NOT_CONNECTED"

    assert set(payload["coverage_denominators"]["covered_target_egp_row_ids"]) == set(
        builder.TARGET_EGP_ROWS
    )
    assert payload["coverage_denominators"]["plain_s_noun_surface_count"] == 162
    assert payload["coverage_denominators"]["plain_s_exact_active_vocabulary_ref_count"] == 171

    boundaries = payload["claim_boundaries"]
    assert boundaries["unit01_questionbank_mutated"] is False
    assert boundaries["unit01_item_identity_mutated"] is False
    assert boundaries["runtime_connected"] is False
    assert boundaries["parallel_runtime_created"] is False
    assert boundaries["a2_unlocked"] is False


def test_u02qb02_rejects_box_pair_instead_of_leaking_es_morphology():
    approved = builder.admit_candidate(builder.build_candidate())
    payload = approved["payload"]
    rejected = [
        row
        for row in payload["candidate_items"]
        if row["admission_proposal"]["status"] == "AUTO_REJECTED"
    ]

    assert len(rejected) == 2
    assert {row["lexical_slots"]["singular_noun"] for row in rejected} == {"box"}
    assert all(
        row["admission_proposal"]["reason_codes"]
        == [builder.REJECT_OUTSIDE_PLAIN_S]
        for row in rejected
    )
    assert all(row["learner_visible_capable"] is False for row in rejected)
    assert all(row["item_id"] not in {a["item_id"] for a in payload["approved_items"]} for row in rejected)


def test_u02qb02_all_approved_noun_targets_are_plain_s_and_deduplicated():
    approved = builder.admit_candidate(builder.build_candidate())
    rows = approved["payload"]["approved_items"]

    assert len({row["item_id"] for row in rows}) == 658
    assert len({row["semantic_signature"] for row in rows}) == 658

    for row in rows:
        singular = row["lexical_slots"]["singular_noun"]
        plural = row["lexical_slots"]["plural_noun"]
        assert plural == singular + "s"
        assert row["unit_pattern_ids"] == [builder.DIRECT_PATTERN_ID]
        assert row["target_egp_row_ids"][0] in builder.TARGET_EGP_ROWS
