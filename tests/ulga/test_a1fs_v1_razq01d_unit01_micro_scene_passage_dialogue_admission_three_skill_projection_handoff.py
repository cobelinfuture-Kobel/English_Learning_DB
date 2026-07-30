from copy import deepcopy

import pytest

from ulga.builders import (
    build_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_handoff as builder,
)
from ulga.validators import (
    validate_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_handoff as validator,
)


def selection_report():
    return {
        "task_id": "A1FS-V1-RAZQ01C_Unit01ThreeSkillCandidateSelectionCoverageBalancing",
        "status": "PASS_A1FS_V1_RAZQ01C_UNIT01_THREE_SKILL_CANDIDATE_SELECTION",
        "scope": {"allowed_units": [builder.UNIT_ID]},
        "selected_candidates": [
            {
                "source_record_id": "RAZ-A-001",
                "semantic_identity": "scene-cat-box",
                "source_level": "A",
                "source_type": "page_unit",
                "text_excerpt": "A child sees a cat. The cat is in a box.",
                "selection_class": "CONTEXT_SOURCE",
                "active_noun_hits": ["cat", "box"],
                "active_adjective_hits": ["small"],
                "matched_sentence_frame_ids": ["U01-F01", "U01-F05"],
            },
            {
                "source_record_id": "RAZ-B-002",
                "semantic_identity": "passage-book-bag",
                "source_level": "B",
                "source_type": "page_unit",
                "text_excerpt": "A book is near a bag. The book is new.",
                "selection_class": "CONTEXT_SOURCE",
                "active_noun_hits": ["book", "bag"],
                "active_adjective_hits": ["new"],
                "matched_sentence_frame_ids": ["U01-F04"],
            },
            {
                "source_record_id": "RAZ-C-003",
                "semantic_identity": "shop-dialogue",
                "source_level": "C",
                "source_type": "page_unit",
                "text_excerpt": "A child asks about a toy in a shop.",
                "selection_class": "REWRITE_REQUIRED",
                "active_noun_hits": ["shop", "box"],
                "active_adjective_hits": [],
                "matched_sentence_frame_ids": ["U01-F06"],
            },
        ],
    }


def review_decisions():
    return {
        "decision_set_id": "U01-RAZQ01D-REVIEW-001",
        "decisions": [
            {
                "source_record_id": "RAZ-A-001",
                "content_asset_id": "U01-MS-PET-SHOP-001",
                "content_kind": "MICRO_SCENE",
                "review_status": "APPROVED",
                "decision_ref": "HUMAN_REVIEW:U01:001",
                "adapted_text": "A girl sees a small cat. The cat is in a box.",
                "setting": "PET_SHOP",
                "participants": ["CHILD"],
                "objects": ["CAT", "BOX"],
                "actions": ["SEE", "LOCATE"],
                "vocabulary_lemmas": ["cat", "box"],
                "adjective_lemmas": ["small"],
                "theme_id": "A1_SHOPPING",
                "situation_family_id": "SHOPPING_FOR_A_PET",
                "micro_situation_id": "SEEING_A_CAT_IN_A_BOX",
            },
            {
                "source_record_id": "RAZ-B-002",
                "content_asset_id": "U01-SP-SCHOOL-BAG-001",
                "content_kind": "SHORT_PASSAGE",
                "review_status": "APPROVED",
                "decision_ref": "HUMAN_REVIEW:U01:002",
                "adapted_text": "A book is near a bag. The book is new. A child has the bag.",
                "setting": "CLASSROOM",
                "participants": ["CHILD"],
                "objects": ["BOOK", "BAG"],
                "actions": ["LOCATE", "HAVE"],
                "vocabulary_lemmas": ["book", "bag"],
                "adjective_lemmas": ["new"],
                "theme_id": "A1_SCHOOL",
                "situation_family_id": "CLASSROOM_OBJECTS",
                "micro_situation_id": "FINDING_A_BOOK_AND_BAG",
            },
            {
                "source_record_id": "RAZ-C-003",
                "content_asset_id": "U01-SD-TOY-SHOP-001",
                "content_kind": "SHORT_DIALOGUE",
                "review_status": "APPROVED",
                "decision_ref": "HUMAN_REVIEW:U01:003",
                "turns": [
                    {"speaker_id": "SHOPKEEPER", "text": "Can I help you?"},
                    {"speaker_id": "CHILD", "text": "Yes. I can see a small cat."},
                    {"speaker_id": "SHOPKEEPER", "text": "Where is the cat?"},
                    {"speaker_id": "CHILD", "text": "The cat is in a box."},
                ],
                "setting": "TOY_SHOP",
                "participants": ["CHILD", "SHOPKEEPER"],
                "objects": ["CAT", "BOX"],
                "actions": ["ASK", "ANSWER", "LOCATE"],
                "vocabulary_lemmas": ["cat", "box", "shop"],
                "theme_id": "A1_SHOPPING",
                "situation_family_id": "ASKING_IN_A_SHOP",
                "micro_situation_id": "ASKING_WHERE_AN_ITEM_IS",
                "communicative_function_ids": [
                    "OFFER_HELP",
                    "ASK_LOCATION",
                    "ANSWER_LOCATION",
                ],
                "adjacency_pair_types": ["OFFER_RESPONSE", "QUESTION_ANSWER"],
            },
        ],
    }


def test_razq01d_builds_three_content_kinds_and_shared_three_skill_projections():
    report = builder.build_handoff(selection_report(), review_decisions())
    coverage = report["coverage_readback"]
    assert coverage == {
        "admitted_content_asset_count": 3,
        "distinct_micro_scene_count": 1,
        "distinct_short_passage_count": 1,
        "distinct_dialogue_count": 1,
        "distinct_scene_signature_count": 3,
        "raz_grounded_content_count": 3,
        "project_authored_rewrite_count": 3,
        "source_record_coverage_count": 3,
        "reading_projection_count": 3,
        "writing_projection_count": 3,
        "speaking_projection_count": 3,
        "three_skill_shared_content_count": 3,
        "template_only_task_count": 0,
        "template_only_task_ratio": 0.0,
        "unit02_reusable_asset_count": 3,
    }
    assert {row["content_kind"] for row in report["content_assets"]} == {
        "MICRO_SCENE",
        "SHORT_PASSAGE",
        "SHORT_DIALOGUE",
    }
    for asset in report["content_assets"]:
        projections = asset["skill_projections"]
        assert projections["three_skill_projection_complete"] is True
        assert projections["shared_scene_across_skills"] is True
        assert projections["reading"][0]["content_asset_id"] == asset["content_asset_id"]
        assert projections["writing"][0]["content_asset_id"] == asset["content_asset_id"]
        assert projections["speaking"][0]["content_asset_id"] == asset["content_asset_id"]
        assert projections["listening"] == []


def test_razq01d_records_the_cross_turn_inspection_findings():
    report = builder.build_handoff(selection_report(), review_decisions())
    findings = {row["finding"] for row in report["inspection_findings"]}
    assert (
        "FIVE_FIXED_CONTEXT_LABELS_ARE_INSUFFICIENT_FOR_UNIT01_SCENE_BREADTH"
        in findings
    )
    assert (
        "RAZQ01C_CANDIDATES_ARE_NOT_CONSUMED_BY_THE_EXISTING_288_ITEM_U01QB_POOL"
        in findings
    )
    assert (
        "A_THIRD_PERSON_NARRATIVE_WITHOUT_SPEAKER_TURNS_IS_NOT_A_SHORT_DIALOGUE"
        in findings
    )
    assert (
        "ONE_STABLE_CONTENT_ASSET_MUST_BE_SHARED_ACROSS_READING_WRITING_AND_SPEAKING"
        in findings
    )


def test_razq01d_validator_accepts_safe_handoff_and_unit02_reference_only_contract():
    report = builder.build_handoff(selection_report(), review_decisions())
    result = validator.validate(report)
    assert result["status"] == builder.PASS_STATUS
    assert result["content_asset_count"] == 3
    assert result["unit02_reusable_asset_count"] == 3
    assert (
        report["unit02_reusable_handoff"]["handoff_mode"]
        == "REFERENCE_ONLY_NO_CONTENT_COPY"
    )
    assert report["unit02_reusable_handoff"]["unit02_content_modified"] is False
    assert report["question_bank_integration"]["second_bank_created"] is False


def test_razq01d_requires_real_dialogue_turns_and_two_speakers():
    decisions = review_decisions()
    decisions["decisions"][2]["turns"] = [
        {"speaker_id": "NARRATOR", "text": "A child sees a cat in a shop."},
        {"speaker_id": "NARRATOR", "text": "The cat is in a box."},
    ]
    with pytest.raises(builder.ContentHandoffBuildError, match="TWO_DISTINCT_SPEAKERS"):
        builder.build_handoff(selection_report(), decisions)


def test_razq01d_validator_rejects_raw_source_leak_and_identity_copy_drift():
    report = builder.build_handoff(selection_report(), review_decisions())
    broken = deepcopy(report)
    broken["content_assets"][0]["source_lineage"]["original_excerpt"] = "private text"
    broken["artifact_sha256"] = builder.digest(
        {key: value for key, value in broken.items() if key != "artifact_sha256"}
    )
    with pytest.raises(
        validator.ContentHandoffValidationError,
        match="RAW_SOURCE_KEY_FORBIDDEN",
    ):
        validator.validate(broken)

    broken = deepcopy(report)
    broken["content_assets"][0]["later_unit_reuse"]["copy_on_reuse"] = True
    asset = broken["content_assets"][0]
    asset["content_asset_sha256"] = builder.digest(
        {key: value for key, value in asset.items() if key != "content_asset_sha256"}
    )
    broken["artifact_sha256"] = builder.digest(
        {key: value for key, value in broken.items() if key != "artifact_sha256"}
    )
    with pytest.raises(
        validator.ContentHandoffValidationError,
        match="reuse_copy_forbidden",
    ):
        validator.validate(broken)


def test_razq01d_requires_explicit_approved_human_decision():
    decisions = review_decisions()
    decisions["decisions"][0]["review_status"] = "PENDING"
    with pytest.raises(builder.ContentHandoffBuildError, match="ONLY_APPROVED"):
        builder.build_handoff(selection_report(), decisions)
