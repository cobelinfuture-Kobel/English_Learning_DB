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


def candidate(
    source,
    semantic,
    classification,
    text,
    nouns,
    adjectives=(),
    *,
    flags=(),
):
    return {
        "source_record_id": source,
        "semantic_identity": semantic,
        "source_level": "B",
        "source_type": "page_unit",
        "text_excerpt": text,
        "selection_class": classification,
        "selection_reasons": ["FIXTURE"],
        "structural_flags": list(flags),
        "matched_sentence_frame_ids": [],
        "direct_task_candidate_roles": [
            "READING_TASK_CANDIDATE",
            "WRITING_TASK_CANDIDATE",
            "SPEAKING_TASK_CANDIDATE",
        ],
        "active_noun_hits": list(nouns),
        "active_adjective_hits": list(adjectives),
        "direct_noun_phrases": [f"a {nouns[0]}"] if nouns else [],
        "adjective_noun_phrases": (
            [f"a {adjectives[0]} {nouns[0]}"]
            if adjectives and nouns
            else []
        ),
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
                "SRC-DIRECT",
                "SEM-DIRECT",
                "DIRECT_MODEL",
                "This is a small cat.",
                ["cat"],
                ["small"],
            ),
            candidate(
                "SRC-CONTEXT",
                "SEM-CONTEXT",
                "CONTEXT_SOURCE",
                (
                    "There is a red book on a desk. "
                    "The book is near a bag."
                ),
                ["book", "desk", "bag"],
                ["red"],
            ),
            candidate(
                "SRC-AMBIGUOUS",
                "SEM-AMBIGUOUS",
                "CONTEXT_SOURCE",
                "The cat sits by a box.",
                ["cat", "box"],
            ),
            candidate(
                "SRC-REJECT",
                "SEM-REJECT",
                "REJECT",
                '"Do not eat the tree!',
                ["tree"],
                flags=("UNBALANCED_QUOTATION",),
            ),
        ],
    }


def exception_scene():
    return {
        "setting": "PET_SHOP",
        "participants": [],
        "objects": ["CAT", "BOX"],
        "actions": ["LOCATE"],
        "information_structure": [
            "FIRST_MENTION",
            "KNOWN_REFERENCE",
        ],
        "communicative_function_ids": ["LOCATE"],
    }


def exception_override(*, raw_copy=False):
    return {
        "decisions": [
            {
                "source_record_id": "SRC-AMBIGUOUS",
                "semantic_identity": "SEM-AMBIGUOUS",
                "decision_ref": (
                    builder.HUMAN_DECISION_REF_PREFIX
                    + "2026-07-30:SRC-AMBIGUOUS"
                ),
                "review_status": "APPROVED",
                "content_kind": "MICRO_SCENE",
                "title": "A cat near a box",
                "adapted_sentences": [
                    (
                        "The cat sits by a box."
                        if raw_copy
                        else "A cat is near a box."
                    )
                ],
                "dialogue_turns": [],
                "scene_profile": exception_scene(),
                "adjacency_pair_types": [],
                "theme_id": "ANIMALS",
                "situation_family_id": "PET_SHOP",
                "micro_situation_id": "CAT_NEAR_BOX",
                "review_dimensions": {
                    key: "PASS" for key in builder.REVIEW_DIMENSIONS
                },
                "adaptation_mode": "HUMAN_EXCEPTION_REWRITE",
                "adaptation_reason_codes": [
                    "SEMANTIC_EXCEPTION_RESOLVED"
                ],
                "template_only": False,
                "rejection_reason_codes": [],
            }
        ]
    }


def build(human_decisions=None):
    return builder.build_admission(
        report(),
        human_decisions,
        contract_builder.build_contract(),
    )


def test_auto_admits_rule_rewrites_without_complete_manual_manifest():
    candidate_artifact, approved, safe = build()
    payload = approved["payload"]
    coverage = payload["coverage_readback"]

    assert candidate_artifact["artifact_role"] == policy_artifact.CANDIDATE_ROLE
    assert approved["artifact_role"] == policy_artifact.APPROVED_ROLE
    assert approved["admission"]["decision_ref"] == builder.AUTO_DECISION_REF
    assert payload["scope"]["human_review_scope"] == "EXCEPTION_ONLY"
    assert (
        payload["scope"]["complete_manual_decision_manifest_required"]
        is False
    )

    assert coverage["upstream_candidate_count"] == 4
    assert coverage["auto_approve_direct_count"] == 1
    assert coverage["auto_approve_rule_rewrite_count"] == 1
    assert coverage["auto_reject_count"] == 1
    assert coverage["human_review_required_count"] == 1
    assert coverage["human_review_resolved_count"] == 0
    assert coverage["human_review_pending_count"] == 1
    assert coverage["approved_content_asset_count"] == 4
    assert coverage["distinct_semantic_scene_count"] == 2
    assert coverage["distinct_micro_scene_count"] == 1
    assert coverage["distinct_short_passage_count"] == 1
    assert coverage["distinct_dialogue_count"] == 2
    assert coverage["three_skill_shared_content_count"] == 4

    assert {
        row["resolution_class"]
        for row in payload["resolution_ledger"]
    } == {
        "AUTO_APPROVE_DIRECT",
        "AUTO_APPROVE_RULE_REWRITE",
        "AUTO_REJECT",
        "HUMAN_REVIEW_REQUIRED",
    }
    assert payload["human_review_queue"] == [
        {
            "source_record_id": "SRC-AMBIGUOUS",
            "semantic_identity": "SEM-AMBIGUOUS",
            "source_excerpt_sha256": payload["human_review_queue"][0][
                "source_excerpt_sha256"
            ],
            "reason_codes": [
                "UNSUPPORTED_SEMANTIC_SENTENCE_PATTERN"
            ],
            "allowed_human_outcomes": [
                "HUMAN_APPROVE_EXCEPTION",
                "HUMAN_REJECT_EXCEPTION",
            ],
        }
    ]
    assert "text_excerpt" not in payload["human_review_queue"][0]
    assert all(
        {
            projection["skill"]
            for projection in asset["skill_projections"]
        }
        == set(builder.SKILLS)
        for asset in payload["content_assets"]
    )
    assert all(
        "content" not in asset for asset in safe["content_assets"]
    )


def test_exception_only_human_override_resolves_one_ambiguous_candidate():
    _, approved, safe = build(exception_override())
    payload = approved["payload"]
    coverage = payload["coverage_readback"]

    assert coverage["human_review_required_count"] == 1
    assert coverage["human_review_resolved_count"] == 1
    assert coverage["human_review_pending_count"] == 0
    assert coverage["human_approve_exception_count"] == 1
    assert coverage["approved_content_asset_count"] == 5
    assert payload["human_review_queue"] == []
    human_assets = [
        asset
        for asset in payload["content_assets"]
        if asset["admission"]["human_review_used"]
    ]
    assert len(human_assets) == 1
    assert (
        human_assets[0]["admission"]["resolution_class"]
        == "HUMAN_APPROVE_EXCEPTION"
    )

    result = validator.validate_package(approved, safe)
    assert result["validation_status"] == validator.PASS_STATUS
    assert result["human_review_pending_count"] == 0


def test_human_override_is_forbidden_for_auto_or_reject_records():
    decisions = exception_override()
    decisions["decisions"][0]["source_record_id"] = "SRC-DIRECT"
    decisions["decisions"][0]["semantic_identity"] = "SEM-DIRECT"
    with pytest.raises(
        builder.AdmissionBuildError,
        match="HUMAN_OVERRIDE_ONLY_ALLOWED_FOR_EXCEPTION_QUEUE",
    ):
        build(decisions)

    decisions = exception_override()
    decisions["decisions"][0]["source_record_id"] = "SRC-REJECT"
    decisions["decisions"][0]["semantic_identity"] = "SEM-REJECT"
    with pytest.raises(
        builder.AdmissionBuildError,
        match="AUTO_REJECT_OVERRIDE_FORBIDDEN",
    ):
        build(decisions)


def test_raw_copy_and_invalid_dialogue_fail_closed_for_exception_override():
    with pytest.raises(
        builder.AdmissionBuildError,
        match="RAW_RAZ_TEXT_COPY",
    ):
        build(exception_override(raw_copy=True))

    decisions = exception_override()
    row = decisions["decisions"][0]
    row["content_kind"] = "SHORT_DIALOGUE"
    row["adapted_sentences"] = []
    row["dialogue_turns"] = [
        {"speaker_id": "CHILD", "utterance": "I see a cat."},
        {"speaker_id": "CHILD", "utterance": "The cat is near a box."},
    ]
    with pytest.raises(
        builder.AdmissionBuildError,
        match="SHORT_DIALOGUE_STRUCTURE_INVALID",
    ):
        build(decisions)


def test_validator_reconciles_auto_resolution_and_rejects_boundary_drift():
    candidate_artifact, approved, safe = build()
    receipt = validator.validate_candidate(candidate_artifact)
    assert receipt["status"] == policy_artifact.PASS_STATUS
    result = validator.validate_package(approved, safe)
    assert result["validation_status"] == validator.PASS_STATUS
    assert result["content_kind_counts"] == {
        "MICRO_SCENE": 1,
        "SHORT_PASSAGE": 1,
        "SHORT_DIALOGUE": 2,
    }
    assert result["resolution_counts"] == {
        "AUTO_APPROVE_DIRECT": 1,
        "AUTO_APPROVE_RULE_REWRITE": 1,
        "AUTO_REJECT": 1,
        "HUMAN_REVIEW_REQUIRED": 1,
        "HUMAN_APPROVE_EXCEPTION": 0,
        "HUMAN_REJECT_EXCEPTION": 0,
    }

    drifted = deepcopy(approved)
    drifted["payload"]["scope"][
        "complete_manual_decision_manifest_required"
    ] = True
    drifted["artifact_sha256"] = policy_artifact.digest(
        {
            key: value
            for key, value in drifted.items()
            if key != "artifact_sha256"
        }
    )
    with pytest.raises(
        validator.AdmissionValidationError,
        match="scope_invalid",
    ):
        validator.validate_package(drifted, safe)


def test_semantic_parser_preserves_facts_and_uses_controlled_templates():
    contract = contract_builder.build_contract()
    direct, context, ambiguous, _ = report()["selected_candidates"]

    direct_resolution = builder.classify_resolution(direct, contract)
    assert direct_resolution["resolution_class"] == "AUTO_APPROVE_DIRECT"
    assert direct_resolution["facts"][0]["fact_type"] == "IDENTIFY"
    direct_decisions = builder._automatic_decisions(
        direct,
        direct_resolution["facts"],
        direct_resolution["resolution_class"],
    )
    assert direct_decisions[0]["adapted_sentences"] == [
        "I can see a small cat."
    ]

    context_resolution = builder.classify_resolution(context, contract)
    assert (
        context_resolution["resolution_class"]
        == "AUTO_APPROVE_RULE_REWRITE"
    )
    assert [
        fact["fact_type"] for fact in context_resolution["facts"]
    ] == ["EXISTS", "LOCATE"]
    assert builder.classify_resolution(
        ambiguous, contract
    )["resolution_class"] == "HUMAN_REVIEW_REQUIRED"
