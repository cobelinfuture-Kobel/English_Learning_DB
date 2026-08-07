from __future__ import annotations

from ulga.builders import _u01qb16b_task_angle_progression_adapter as u16b
from ulga.builders import build_a1fs_v1_u01qb12_unit01_reference_evidence_and_phrase_construction_partial_coverage_fullfix as u12
from ulga.validators import validate_a1fs_v1_u01qb17b_unit01_twelve_form_learner_visible_production_quality as validator


def test_u01qb17b_whole_product_quality_gate_passes() -> None:
    report = validator.validate()

    assert report["validation_status"] == validator.PASS_STATUS
    assert report["runtime_item_count"] == 474
    assert report["real62_extension_count"] == 186
    assert report["form_count"] == 12
    assert report["activity_count"] == 240
    assert report["scored_activity_count"] == 192
    assert report["speaking_practice_activity_count"] == 48
    assert report["scored_exact_binding_gap_count"] == 0
    assert report["bound_form_rewrite_allowed"] is False
    assert report["same_item_retry_allowed"] is False
    assert report["questionbank_expanded"] is False
    assert report["second_runtime_created"] is False
    assert report["a2_unlocked"] is False


def test_support_withdrawal_is_exactly_four_three_form_bands() -> None:
    report = validator.validate()
    assert report["support_form_counts"] == {
        "GUIDED": 3,
        "INDEPENDENT": 3,
        "REDUCED_SUPPORT": 3,
        "TRANSFER": 3,
    }
    assert report["assessment_form_ordinals"] == [10, 11, 12]


def test_reference_evidence_and_phrase_construction_are_canonical_not_partial_aliases() -> None:
    report = validator.validate()
    assert report["reference_evidence_family"] == u12.PF16
    assert report["phrase_construction_family"] == u12.PF17
    assert report["scored_exact_binding_gap_count"] == 0


def test_reading_diversity_counts_capability_not_labels() -> None:
    report = validator.validate()
    assert report["reading_capability_class_count"] >= 4
    assert u16b.capability_class("READING", "ARTICLE_CONTROL") == u16b.FIRST_MENTION_SELECTION
    assert u16b.capability_class("READING", "FIRST_MENTION_CONTEXT") == u16b.FIRST_MENTION_SELECTION
    assert u16b.capability_class("READING", "TRANSFER_DECISION") == u16b.FIRST_MENTION_SELECTION
    assert u16b.capability_class("READING", "KNOWN_REFERENCE_CONTEXT") == u16b.KNOWN_REFERENCE_USE
    assert u16b.capability_class("READING", "ERROR_CHECK") == u16b.ERROR_DISCRIMINATION
    assert u16b.capability_class("READING", "REFERENCE_EVIDENCE") == u16b.REFERENCE_EVIDENCE


def test_frozen_boundaries_and_next_step() -> None:
    report = validator.validate()
    assert report["speaking_scoring_enabled"] is False
    assert report["audio_enabled"] is False
    assert report["unit02_to_unit24_modified"] is False
    assert report["a2_unlocked"] is False
    assert report["next_short_step"] == validator.NEXT_SHORT_STEP
