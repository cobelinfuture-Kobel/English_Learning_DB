from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "ulga" / "contracts" / "a1fs_v1_u05_q02_vocabulary_carrier_authority.json"
VOCAB = ROOT / "vocabulary" / "json" / "vocabulary.json"
U04_Q02 = ROOT / "ulga" / "contracts" / "a1fs_v1_u04_q02_vocabulary_authority.json"
U05_Q01 = ROOT / "ulga" / "contracts" / "a1fs_v1_u05_q01_canonical_target_gap_projection.json"
U05_Q00 = ROOT / "ulga" / "contracts" / "a1fs_v1_u05_q00_unit04_successor_baseline.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _bucket(status: str) -> str:
    if status.startswith("BLOCKED_"):
        return "BLOCKED"
    if status.startswith("REVIEW_REQUIRED"):
        return "REVIEW_REQUIRED"
    return "ADMITTED"


def test_u05_q02_vocabulary_carrier_authority() -> None:
    data = _load(ARTIFACT)
    vocab = {row["vocab_id"]: row for row in _load(VOCAB)}
    u04 = _load(U04_Q02)
    q01 = _load(U05_Q01)
    q00 = _load(U05_Q00)

    assert data["status"] == "PASS_A1FS_V1_U05Q02_VOCABULARY_AUTHORITY_AND_REUSABLE_CARRIER_ADMISSION"
    assert data["unit_number"] == 5
    assert data["unit_id"] == "GRAMMAR_BE_VERB_BASIC"
    assert q01["status"] == "PASS_A1FS_V1_U05Q01_UNIT05_CANONICAL_TARGET_AND_GAP_PROJECTION"
    assert q00["archive_audit"]["content_files_readable"] == 69

    rows = data["matrix"]
    assert len(rows) == 123
    assert len({(row["carrier_class"], row["canonical_vocab_id"]) for row in rows}) == 123
    assert set(row["carrier_class"] for row in rows) == {
        "NOUN", "ADJECTIVE", "PLACE", "PERSON", "ROLE", "AGE_STATE", "ACTION_SUPPORT"
    }

    for row in rows:
        canonical = vocab[row["canonical_vocab_id"]]
        assert row["surface"] == canonical["word"]
        assert row["guideword"] == canonical["guideword"]
        assert row["evp_level"] == canonical["level"]
        assert row["part_of_speech"] == canonical["part_of_speech"]
        assert row["topic"] == canonical["topic"]
        assert row["canonical_active"] is bool(canonical["active"])
        assert row["ket_reference_role"] == "REFERENCE_ONLY_NOT_USED_FOR_LEXICAL_ADMISSION"

    admitted = [row for row in rows if _bucket(row["unit05_admission_status"]) == "ADMITTED"]
    review = [row for row in rows if _bucket(row["unit05_admission_status"]) == "REVIEW_REQUIRED"]
    blocked = [row for row in rows if _bucket(row["unit05_admission_status"]) == "BLOCKED"]

    assert len(admitted) == 106
    assert len(review) == 8
    assert len(blocked) == 9
    assert len({row["surface"].casefold() for row in admitted}) == 105
    assert sum(row["predecessor_reader_observed"] for row in admitted) >= 69

    overall = data["summary"]["overall"]
    assert overall["candidate_identity_count"] == 123
    assert overall["admitted_identity_count"] == 106
    assert overall["review_required_identity_count"] == 8
    assert overall["blocked_identity_count"] == 9
    assert overall["admission_rate"] == 0.8618
    assert overall["new_global_vocabulary_identity_count"] == 0
    assert overall["admitted_unique_surface_count"] == 105
    assert overall["predecessor_reader_observed_unique_surface_count"] == 69
    assert overall["predecessor_reader_observed_surface_rate"] == 0.6571
    assert overall["predecessor_reader_surface_occurrence_total"] == 6409
    assert overall["evp_a1_candidate_count"] == 109
    assert overall["evp_a2_candidate_count"] == 14
    assert overall["yle_pre_a1_a1_override_admitted_count"] == 5
    assert overall["yle_a2_flyers_blocked_count"] == 3
    assert overall["ket_lexical_admission_count"] == 0
    assert overall["actual_unit05_learner_usage_rate"] is None

    by_class = data["summary"]["by_carrier_class"]
    assert by_class["NOUN"]["admitted_identity_count"] == 25
    assert by_class["ADJECTIVE"]["admitted_identity_count"] == 15
    assert by_class["PLACE"]["admitted_identity_count"] == 29
    assert by_class["PERSON"]["admitted_identity_count"] == 14
    assert by_class["ROLE"]["admitted_identity_count"] == 3
    assert by_class["AGE_STATE"]["admitted_identity_count"] == 8
    assert by_class["ACTION_SUPPORT"]["admitted_identity_count"] == 12

    assert by_class["PLACE"]["exact_prior_authority_reuse_rate"] == 1.0
    assert by_class["PERSON"]["exact_prior_authority_reuse_identity_count"] == 13
    assert by_class["ROLE"]["review_required_identity_count"] == 4
    assert by_class["NOUN"]["review_required_identity_count"] == 1
    assert by_class["ADJECTIVE"]["review_required_identity_count"] == 1
    assert by_class["AGE_STATE"]["review_required_identity_count"] == 2
    assert by_class["ACTION_SUPPORT"]["blocked_identity_count"] == 1

    u04_overrides = {
        item["surface"]: item["yle_stage"]
        for item in u04["life_skill_place_carrier_pool"]["provenance"]["yle_active_eligible_extensions"]
    }
    assert u04_overrides == {
        "playground": "PRE_A1_STARTERS",
        "bus stop": "A1_MOVERS",
        "library": "A1_MOVERS",
        "market": "A1_MOVERS",
        "sports centre": "A1_MOVERS",
    }
    admitted_a2 = {
        row["surface"]: row["yle_stage"]
        for row in admitted
        if row["evp_level"] == "A2"
    }
    assert admitted_a2 == u04_overrides

    u04_blocked = {
        item["surface"]: item["yle_stage"]
        for item in u04["not_yet_allowed_life_place_examples"]["examples"]
    }
    assert u04_blocked == {
        "airport": "A2_FLYERS",
        "office": "A2_FLYERS",
        "police station": "A2_FLYERS",
    }
    blocked_flyers = {
        row["surface"]: row["yle_stage"]
        for row in blocked
        if row["yle_stage"] == "A2_FLYERS"
    }
    assert blocked_flyers == u04_blocked

    review_surfaces = {row["surface"] for row in review}
    assert review_surfaces == {
        "ticket", "easy", "doctor", "driver", "waiter", "waitress", "cold", "ready"
    }

    blocked_surfaces = {row["surface"] for row in blocked}
    assert blocked_surfaces == {
        "dirty", "open", "airport", "office", "police station",
        "ill", "sick", "thirsty", "stand"
    }

    assert data["claim_boundaries"]["reader360_observation_is_not_unit05_learner_exposure"] is True
    assert data["claim_boundaries"]["canonical_inactive_without_prior_authority_is_not_silently_activated"] is True
    assert data["claim_boundaries"]["action_support_does_not_unlock_present_continuous"] is True
    assert data["claim_boundaries"]["a2_a2plus_unlocked"] is False
    assert data["acceptance"]["actual_unit05_learner_usage_rate_materialized"] is False
    assert data["next_short_step"] == "A1FS-V1-U05Q03_Unit05BeFormMeaningAndAuxiliaryBoundaryAuthority"
