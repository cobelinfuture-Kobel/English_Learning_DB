"""Builder for ReadingV1 P2 private-practice packages."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, Mapping

PACKAGE_VERSION = "reading_v1_p2_assessment_package.v1"


def build_assessment_package(package_id: str, items: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """Build a P2 package from prepared P2 items.

    This function only returns an in-memory dictionary.
    """
    return {
        "schema_version": PACKAGE_VERSION,
        "package_id": package_id,
        "items": [deepcopy(dict(item)) for item in items],
        "private_homework_only": True,
        "public_ready": False,
        "not_for_public_export": True,
        "not_for_commercial_distribution": True,
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
        "feedback_boundary": "local_private_practice_only",
        "learner_state_write": False,
    }


def build_synthetic_assessment_item(item_id: str = "p2_item_001") -> Dict[str, Any]:
    """Return a deterministic synthetic item for tests."""
    return {
        "schema_version": "reading_v1_p2_assessment_item.v1",
        "item_id": item_id,
        "level_stage": "RV1-S1",
        "pattern_family": "literal_comprehension",
        "question_type": "literal_who",
        "display_payload": {
            "prompt": "Who is in the story?",
            "learner_visible_text": "Tom is in the story.",
            "source_payload_visible": False,
        },
        "answer_model": {
            "answer_key": "Tom",
            "accepted_answers": ["Tom"],
            "answer_visible_to_student": False,
        },
        "feedback_policy": {
            "feedback_boundary": "local_private_practice_only",
            "learner_state_write": False,
            "allowed_labels": ["correct", "incorrect", "needs_review", "not_answered"],
        },
        "source_trace": {
            "source_unit_ref": f"operator_reviewed_seed:{item_id}",
            "source_payload_persisted": False,
        },
        "private_homework_only": True,
        "public_ready": False,
        "not_for_public_export": True,
        "not_for_commercial_distribution": True,
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
    }


def build_synthetic_assessment_package() -> Dict[str, Any]:
    """Return a deterministic synthetic package for tests."""
    item_one = build_synthetic_assessment_item("p2_item_001")
    item_two = build_synthetic_assessment_item("p2_item_002")
    item_two["question_type"] = "literal_what"
    item_two["display_payload"]["prompt"] = "What is in the story?"
    item_two["answer_model"]["answer_key"] = "a ball"
    item_two["answer_model"]["accepted_answers"] = ["a ball", "ball"]
    return build_assessment_package("p2_package_001", [item_one, item_two])
