"""Build ReadingV1 P3 local records from P2 review tags."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Mapping

SCHEMA_VERSION = "reading_v1_p3_unit.v1"

TAG_TO_GROUP = {
    "literal_detail_miss": "review_literal_detail",
    "who_what_where_when_confusion": "review_wh_question_family",
    "vocabulary_context_miss": "review_vocabulary_context",
    "sequence_order_miss": "review_sequence_order",
    "yes_no_mismatch": "review_yes_no_evidence",
    "true_false_mismatch": "review_true_false_evidence",
    "unanswered": "review_unanswered",
}


def make_record(source: Mapping[str, Any], package_id: str) -> Dict[str, Any]:
    tag = source.get("review_tag")
    group_key = TAG_TO_GROUP.get(str(tag), "review_operator_needed")
    return {
        "schema_version": SCHEMA_VERSION,
        "item_id": source.get("item_id"),
        "package_id": package_id,
        "group_key": group_key,
        "source_review_tag": tag,
        "source_question_type": source.get("question_type"),
        "source_pattern_family": source.get("pattern_family"),
        "private_homework_only": True,
        "public_ready": False,
        "learner_state_write": False,
        "source_copy": deepcopy(dict(source)),
    }


def make_records(sources: Iterable[Mapping[str, Any]], package_id: str) -> List[Dict[str, Any]]:
    return [make_record(source, package_id) for source in sources]


def make_synthetic_record() -> Dict[str, Any]:
    return make_record(
        {
            "item_id": "p2_item_001",
            "review_tag": "literal_detail_miss",
            "question_type": "literal_who",
            "pattern_family": "literal_comprehension",
        },
        "p2_package_001",
    )
