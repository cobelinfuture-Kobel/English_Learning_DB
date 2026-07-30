from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as contract_builder
from ulga.builders import (
    build_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_unit02_handoff as builder,
)
from ulga.validators import (
    validate_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_unit02_handoff as validator,
)


def candidate(source, semantic, classification, text, nouns, adjectives=()):
    return {
        "source_record_id": source,
        "semantic_identity": semantic,
        "source_level": "B",
        "source_type": "page_unit",
        "text_excerpt": text,
        "selection_class": classification,
        "selection_reasons": ["FIXTURE"],
        "structural_flags": [],
        "matched_sentence_frame_ids": [],
        "direct_task_candidate_roles": [
            "READING_TASK_CANDIDATE",
            "WRITING_TASK_CANDIDATE",
            "SPEAKING_TASK_CANDIDATE",
        ],
        "active_noun_hits": list(nouns),
        "active_adjective_hits": list(adjectives),
        "direct_noun_phrases": [f"a {nouns[0]}"],
        "adjective_noun_phrases": [f"a {adjectives[0]} {nouns[0]}"] if adjectives else [],
        "very_adjective_noun_phrases": [],
        "source_skill_eligibility": [],
        "canonical_admission": False,
        "human_review_required": classification != "REJECT",
    }


def report():
    return {
        "schema_version": builder.upstream.SCHEMA_VERSION,
        "task_id": builder.upstream.TASK_ID,
        "status": builder.upstream.PASS_STATUS,
        "scope": {
            "allowed_units": [builder.UNIT_ID],
            "canonical_promotion": False,
            "a2_status": "LOCKED",
        },
        "selected_candidates": [
            candidate(
                "SRC-MS",
                "SEM-MS",
                "CONTEXT_SOURCE",
                "The cat sits by a box.",
                ["cat", "box"],
                ["small"],
            ),
            candidate(
                "SRC-SP",
                "SEM-SP",
                "CONTROLLED_PRACTICE_SOURCE",
                "A book is on a desk.",
                ["book", "desk"],
                ["red"],
            ),
            candidate(
                "SRC-DLG",
                "SEM-DLG",
                "DIRECT_MODEL",
                "This is a bag.",
                ["bag"],
                ["blue"],
            ),
            candidate(
                "SRC-X",
                "SEM-X",
                "REJECT",
                '"Do not eat the tree!',
                ["tree"],
            ),
        ],
    }


def checks():
    return {key: "PASS" for key in builder.REVIEW_DIMENSIONS}


def scene(setting, participants, objects, actions, information, functions):
    return {
        "setting": setting,
        "participants": participants,
        "objects": objects,
        "actions": actions,
        "information_structure": information,
        "communicative_function_ids": functions,
    }


def decisions():
    common = {
        "review_status": "APPROVED",
        "decision_ref": builder.DECISION_REF,
        "adaptation_mode": "PROJECT_AUTHORED_REWRITE",
        "adaptation_reason_codes": ["RAZ_GROUNDED_A1_REWRITE"],
        "review_dimensions": checks(),
        "template_only": False,
        "rejection_reason_codes": [],
    }
    return {
        "decisions": [
            {
                **common,
                "source_record_id": "SRC-MS",
                "semantic_identity": "SEM-MS",
                "content_kind": "MICRO_SCENE",
                "title": "A cat in a pet shop",
                "adapted_sentences": [
                    "A girl is in a pet shop.",
                    "She sees a small cat.",
                    "The cat is in a box.",
                ],
                "dialogue_turns": [],
                "scene_profile": scene(
                    "PET_SHOP",
                    ["GIRL"],
                    ["CAT", "BOX"],
                    ["SEE", "LOCATE"],
                    ["FIRST_MENTION", "KNOWN_REFERENCE"],
                    ["IDENTIFY", "LOCATE"],
                ),
                "adjacency_pair_types": [],
                "theme_id": "ANIMALS",
                "situation_family_id": "SHOPPING",
                "micro_situation_id": "PET_SHOP_CAT",
            },
            {
                **common,
                "source_record_id": "SRC-SP",
                "semantic_identity": "SEM-SP",
                "content_kind": "SHORT_PASSAGE",
                "title": "A red book",
                "adapted_sentences": [
                    "Mia has a red book.",
                    "The book is on a desk.",
                    "She puts the book in a bag.",
                ],
                "dialogue_turns": [],
                "scene_profile": scene(
                    "CLASSROOM",
                    ["MIA"],
                    ["BOOK", "DESK", "BAG"],
                    ["HAVE", "PUT"],
                    ["FIRST_MENTION", "KNOWN_REFERENCE"],
                    ["DESCRIBE", "LOCATE"],
                ),
                "adjacency_pair_types": [],
                "theme_id": "SCHOOL",
                "situation_family_id": "CLASSROOM",
                "micro_situation_id": "BOOK_ON_DESK",
            },
            {
                **common,
                "source_record_id": "SRC-DLG",
                "semantic_identity": "SEM-DLG",
                "content_kind": "SHORT_DIALOGUE",
                "title": "A bag in the classroom",
                "adapted_sentences": [],
                "dialogue_turns": [
                    {"speaker_id": "TEACHER", "utterance": "What is in the classroom?"},
                    {"speaker_id": "CHILD", "utterance": "I can see a blue bag."},
                    {"speaker_id": "TEACHER", "utterance": "Where is the bag?"},
                    {"speaker_id": "CHILD", "utterance": "The bag is near the door."},
                ],
                "scene_profile": scene(
                    "CLASSROOM",
                    ["TEACHER", "CHILD"],
                    ["BAG", "DOOR"],
                    ["SEE", "LOCATE"],
                    ["QUESTION_ANSWER", "KNOWN_REFERENCE"],
                    ["ASK", "ANSWER", "LOCATE"],
                ),
                "adjacency_pair_types": ["QUESTION_ANSWER"],
                "theme_id": "SCHOOL",
                "situation_family_id": "CLASSROOM_DIALOGUE",
                "micro_situation_id": "FIND_THE_BAG",
            },
        ]
    }


def build():
    return builder.build_admission(
        report(),
        decisions(),
        contract_builder.build_contract(),
    )


def test_builds_policy_bound_shared_three_skill_content_and_unit02_handoff():
    candidate_artifact, approved, safe = build()
    payload = approved["payload"]
    coverage = payload["coverage_readback"]
    assert candidate_artifact["artifact_role"] == policy_artifact.CANDIDATE_ROLE
    assert approved["artifact_role"] == policy_artifact.APPROVED_ROLE
    assert approved["admission"]["decision_ref"] == builder.DECISION_REF
    assert coverage["approved_content_asset_count"] == 3
    assert coverage["three_skill_shared_content_count"] == 3
    assert coverage["distinct_micro_scene_count"] == 1
    assert coverage["distinct_short_passage_count"] == 1
    assert coverage["distinct_dialogue_count"] == 1
    assert all(
        {projection["skill"] for projection in asset["skill_projections"]}
        == set(builder.SKILLS)
        for asset in payload["content_assets"]
    )
    assert all("content" not in asset for asset in safe["content_assets"])
    assert all(
        asset["unit02_reusable_handoff"]["binding_status"] == "AVAILABLE_NOT_BOUND"
        and asset["later_unit_reuse"]["copy_on_reuse"] is False
        for asset in payload["content_assets"]
    )


def test_records_all_handshake_findings():
    _, approved, _ = build()
    assert {
        row["finding_code"]
        for row in approved["payload"]["inspection_record"]["findings"]
    } == {code for code, _ in builder.FINDINGS}


def test_dialogue_and_raw_copy_fail_closed():
    decision_bundle = decisions()
    decision_bundle["decisions"][2]["dialogue_turns"] = [
        {"speaker_id": "CHILD", "utterance": "I see a bag."},
        {"speaker_id": "CHILD", "utterance": "The bag is blue."},
    ]
    with pytest.raises(builder.AdmissionBuildError, match="SHORT_DIALOGUE_STRUCTURE_INVALID"):
        builder.build_admission(report(), decision_bundle, contract_builder.build_contract())

    decision_bundle = decisions()
    decision_bundle["decisions"][0]["adapted_sentences"] = ["The cat sits by a box."]
    with pytest.raises(builder.AdmissionBuildError, match="RAW_RAZ_TEXT_COPY"):
        builder.build_admission(report(), decision_bundle, contract_builder.build_contract())


def test_incomplete_decisions_and_parallel_bank_drift_fail_closed():
    decision_bundle = decisions()
    decision_bundle["decisions"].pop()
    with pytest.raises(builder.AdmissionBuildError, match="COMPLETE_REVIEWABLE"):
        builder.build_admission(report(), decision_bundle, contract_builder.build_contract())

    candidate_artifact, approved, safe = build()
    receipt = validator.validate_candidate(candidate_artifact)
    assert receipt["status"] == policy_artifact.PASS_STATUS
    result = validator.validate_package(approved, safe)
    assert result["validation_status"] == validator.PASS_STATUS
    assert result["content_kind_counts"] == {
        "MICRO_SCENE": 1,
        "SHORT_PASSAGE": 1,
        "SHORT_DIALOGUE": 1,
    }

    drifted = deepcopy(approved)
    drifted["payload"]["boundaries"]["parallel_question_bank_created"] = True
    drifted["artifact_sha256"] = policy_artifact.digest(
        {key: value for key, value in drifted.items() if key != "artifact_sha256"}
    )
    with pytest.raises(validator.AdmissionValidationError, match="authority_boundary_invalid"):
        validator.validate_package(drifted, safe)
