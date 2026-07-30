from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_razq01b_unit01_content_contract as contract_builder,
)
from ulga.builders import (
    build_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_unit02_handoff
    as builder,
)
from ulga.validators import (
    validate_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_unit02_handoff
    as validator,
)


def candidate(
    source: str,
    semantic: str,
    selection_class: str,
    text: str,
    nouns: list[str],
    adjectives: list[str] | None = None,
    *,
    flags: list[str] | None = None,
    roles: list[str] | None = None,
) -> dict:
    return {
        "source_record_id": source,
        "semantic_identity": semantic,
        "source_level": "B",
        "source_type": "page_unit",
        "text_excerpt": text,
        "selection_class": selection_class,
        "selection_reasons": ["FOCUSED_FIXTURE"],
        "structural_flags": list(flags or []),
        "matched_sentence_frame_ids": [],
        "direct_task_candidate_roles": roles
        or [
            "READING_TASK_CANDIDATE",
            "WRITING_TASK_CANDIDATE",
            "SPEAKING_TASK_CANDIDATE",
        ],
        "active_noun_hits": nouns,
        "active_adjective_hits": list(adjectives or []),
        "direct_noun_phrases": [],
        "adjective_noun_phrases": [],
        "very_adjective_noun_phrases": [],
        "canonical_admission": False,
        "human_review_required": selection_class != "REJECT",
    }


def gap_specs() -> list[dict]:
    rows = []
    noun_forms = {
        "apple": ["an apple", "the apple"],
        "bag": ["a bag", "the bag"],
        "bed": ["a bed", "the bed"],
        "book": ["a book", "the book"],
        "box": ["a box", "the box"],
        "cat": ["a cat", "the cat"],
        "classroom": ["a classroom", "the classroom"],
        "desk": ["a desk", "the desk"],
        "dog": ["a dog", "the dog"],
        "door": ["a door", "the door"],
        "egg": ["an egg", "the egg"],
        "park": ["a park", "the park"],
        "room": ["a room", "the room"],
        "shop": ["a shop", "the shop"],
        "tree": ["a tree", "the tree"],
        "window": ["a window", "the window"],
    }
    for noun, forms in noun_forms.items():
        rows.append(
            {
                "gap_spec_id": f"U01-GAP-NOUN-{noun.upper()}",
                "gap_dimension": "ACTIVE_NOUN",
                "target_lemmas": [noun],
                "required_memory_forms": forms,
                "candidate_only": True,
                "generated": True,
            }
        )
    adjective_forms = {
        "big": "a big box",
        "blue": "a blue bag",
        "new": "a new book",
        "old": "an old book",
        "red": "a red book",
        "small": "a small bag",
    }
    for adjective, phrase in adjective_forms.items():
        rows.append(
            {
                "gap_spec_id": f"U01-GAP-ADJECTIVE-{adjective.upper()}",
                "gap_dimension": "ACTIVE_ADJECTIVE",
                "target_lemmas": [adjective],
                "required_memory_forms": [phrase],
                "candidate_only": True,
                "generated": True,
            }
        )
    rows.append(
        {
            "gap_spec_id": "U01-GAP-ARTICLE-AN",
            "gap_dimension": "ARTICLE_FORM",
            "target_articles": ["an"],
            "candidate_only": True,
            "generated": True,
        }
    )
    for frame_id in (
        "U01-AF01",
        "U01-AF02",
        "U01-AF03",
        "U01-F01",
        "U01-F02",
        "U01-F03",
        "U01-F04",
        "U01-F05",
        "U01-F06",
    ):
        rows.append(
            {
                "gap_spec_id": f"U01-GAP-FRAME-{frame_id}",
                "gap_dimension": "SENTENCE_FRAME",
                "target_sentence_frame_ids": [frame_id],
                "candidate_only": True,
                "generated": True,
            }
        )
    return rows


def report() -> dict:
    selected = [
        candidate(
            "SRC-SHARED",
            "SEM-DIRECT",
            "DIRECT_MODEL",
            "This is a tree.",
            ["tree"],
        ),
        candidate(
            "SRC-SHARED",
            "SEM-ACTION",
            "CONTROLLED_PRACTICE_SOURCE",
            "The big cat runs.",
            ["cat"],
            ["big"],
        ),
        candidate(
            "SRC-REWRITE",
            "SEM-IMITATE",
            "REWRITE_REQUIRED",
            "They can be as big as a room.",
            ["room"],
            ["big"],
            flags=["COMPARATIVE_PRESENT", "UNAPPROVED_MODAL_SCAFFOLD"],
        ),
        candidate(
            "SRC-CONTEXT",
            "SEM-DIALOGUE",
            "CONTEXT_SOURCE",
            "Would you like to come to the park with us?",
            ["park"],
        ),
        candidate(
            "SRC-REJECT",
            "SEM-REJECT",
            "REJECT",
            '"Do not eat the tree!',
            ["tree"],
            flags=["UNBALANCED_QUOTATION", "NEGATIVE_IMPERATIVE_PRESENT"],
        ),
    ]
    return {
        "schema_version": builder.upstream.SCHEMA_VERSION,
        "task_id": builder.upstream.TASK_ID,
        "status": builder.upstream.PASS_STATUS,
        "scope": {
            "allowed_units": [builder.UNIT_ID],
            "canonical_promotion": False,
            "a2_status": "LOCKED",
        },
        "selection_summary": {"strict_candidate_count": len(selected)},
        "selected_candidates": selected,
        "coverage": {"project_authored_gap_specs": gap_specs()},
    }


def build():
    return builder.build_admission(
        report(), contract=contract_builder.build_contract()
    )


def test_composite_identity_allows_repeated_source_record_id():
    payload = builder.build_payload(
        report(), contract=contract_builder.build_contract()
    )
    source_rows = payload["resolution_ledger"][:5]
    assert source_rows[0]["source_record_id"] == source_rows[1]["source_record_id"]
    assert source_rows[0]["semantic_identity"] != source_rows[1]["semantic_identity"]
    assert len(
        {row["candidate_composite_key"] for row in payload["resolution_ledger"]}
    ) == len(payload["resolution_ledger"])


def test_rewrite_required_uses_a1_imitation_instead_of_human_review():
    payload = builder.build_payload(
        report(), contract=contract_builder.build_contract()
    )
    row = next(
        value
        for value in payload["resolution_ledger"]
        if value["semantic_identity"] == "SEM-IMITATE"
    )
    assert row["resolution_class"] == "AUTO_APPROVE_A1_IMITATION"
    asset = next(
        value
        for value in payload["content_assets"]
        if value["source_lineage"]["semantic_identity"] == "SEM-IMITATE"
    )
    assert (
        asset["source_lineage"]["lineage_mode"]
        == "SEMANTIC_ANCHOR_A1_IMITATION"
    )
    assert asset["source_lineage"]["equivalence_claimed"] is False


def test_semantic_equivalent_and_imitation_lineage_are_not_mixed():
    payload = builder.build_payload(
        report(), contract=contract_builder.build_contract()
    )
    modes = {
        value["source_lineage"]["semantic_identity"]: value["source_lineage"][
            "lineage_mode"
        ]
        for value in payload["content_assets"]
        if value["source_lineage"]["source_authority"]
        == "RAZ_READING_AUTHORITY"
    }
    assert modes["SEM-DIRECT"] == "SEMANTIC_EQUIVALENT_REWRITE"
    assert modes["SEM-ACTION"] == "SEMANTIC_EQUIVALENT_REWRITE"
    assert modes["SEM-IMITATE"] == "SEMANTIC_ANCHOR_A1_IMITATION"
    assert modes["SEM-DIALOGUE"] == "SEMANTIC_ANCHOR_A1_IMITATION"


def test_project_authored_completion_closes_every_unit01_contract_dimension():
    payload = builder.build_payload(
        report(), contract=contract_builder.build_contract()
    )
    coverage = payload["coverage_readback"]
    matrix = coverage["unit01_coverage"]
    assert matrix["complete"] is True
    assert all(not matrix[key]["missing"] for key in (
        "active_nouns",
        "active_adjectives",
        "article_forms",
        "sentence_frames",
    ))
    assert (
        coverage["auto_approve_project_authored_completion_count"]
        == len(gap_specs())
    )
    project_assets = [
        value
        for value in payload["content_assets"]
        if value["source_lineage"]["lineage_mode"]
        == "PROJECT_AUTHORED_CONTRACT_COMPLETION"
    ]
    assert len(project_assets) == len(gap_specs())
    assert all(
        value["source_lineage"]["source_authority"]
        == "PROJECT_AUTHORED_UNIT01_CONTRACT"
        for value in project_assets
    )


def test_true_uncertainty_queue_is_composite_key_bound():
    uncertain = candidate(
        "SRC-SHARED",
        "SEM-NO-ANCHOR",
        "CONTEXT_SOURCE",
        "What happens next?",
        [],
    )
    value = report()
    value["selected_candidates"].append(uncertain)
    value["selection_summary"]["strict_candidate_count"] += 1

    payload = builder.build_payload(
        value, contract=contract_builder.build_contract()
    )
    assert payload["human_review_queue"] == [
        {
            "source_record_id": "SRC-SHARED",
            "semantic_identity": "SEM-NO-ANCHOR",
            "candidate_composite_key": "SRC-SHARED::SEM-NO-ANCHOR",
            "source_excerpt_sha256": payload["human_review_queue"][0][
                "source_excerpt_sha256"
            ],
            "reason_codes": ["NO_RELIABLE_UNIT01_SEMANTIC_ANCHOR"],
            "allowed_human_outcomes": [
                "HUMAN_APPROVE_EXCEPTION",
                "HUMAN_REJECT_EXCEPTION",
            ],
        }
    ]

    wrong_override = {
        "decisions": [
            {
                "source_record_id": "SRC-SHARED",
                "semantic_identity": "SEM-DIRECT",
                "decision_ref": (
                    builder.HUMAN_DECISION_REF_PREFIX + "WRONG-SEMANTIC"
                ),
                "review_status": "REJECTED",
            }
        ]
    }
    with pytest.raises(
        builder.AdmissionBuildError,
        match="HUMAN_OVERRIDE_ONLY_ALLOWED_FOR_EXCEPTION_QUEUE",
    ):
        builder.build_payload(
            value,
            wrong_override,
            contract=contract_builder.build_contract(),
        )


def test_policy_bound_package_validator_and_safe_readback():
    candidate_artifact, approved, safe = build()
    assert candidate_artifact["artifact_role"] == policy_artifact.CANDIDATE_ROLE
    assert approved["artifact_role"] == policy_artifact.APPROVED_ROLE
    result = validator.validate_package(approved, safe)
    assert result["validation_status"] == validator.PASS_STATUS
    assert result["unit01_coverage_complete"] is True
    assert all("content" not in value for value in safe["content_assets"])

    drifted = deepcopy(approved)
    drifted["payload"]["scope"]["unit02_to_unit24_modified"] = True
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


def test_real44_threshold_gate_with_private_safe_shape():
    value = report()
    base = value["selected_candidates"]
    synthetic = []
    for index in range(41):
        template = deepcopy(base[index % 4])
        template["source_record_id"] = f"SRC-{index // 2:02d}"
        template["semantic_identity"] = f"SEM-{index:02d}"
        synthetic.append(template)
    for index in range(3):
        template = deepcopy(base[4])
        template["source_record_id"] = f"SRC-REJECT-{index}"
        template["semantic_identity"] = f"SEM-REJECT-{index}"
        synthetic.append(template)
    value["selected_candidates"] = synthetic
    value["selection_summary"]["strict_candidate_count"] = 44

    payload = builder.build_payload(
        value, contract=contract_builder.build_contract()
    )
    coverage = payload["coverage_readback"]
    assert coverage["source_candidate_count"] == 44
    assert coverage["auto_transformed_source_count"] == 41
    assert coverage["auto_reject_count"] == 3
    assert coverage["human_review_pending_count"] == 0
    assert coverage["real44_acceptance_pass"] is True
