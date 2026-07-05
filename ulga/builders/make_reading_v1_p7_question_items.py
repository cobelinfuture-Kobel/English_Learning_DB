"""Build ReadingV1 P7 local question items from P6 source units."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping

SCHEMA_VERSION = "reading_v1_p7_question_item.v1"


def make_question_item(
    question_id: str,
    source_unit_ref: str,
    question_type: str,
    question_text: str,
    answer: str,
    options: List[str] | None = None,
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "question_id": question_id,
        "source_unit_ref": source_unit_ref,
        "question_type": question_type,
        "question_text": question_text,
        "answer": answer,
        "options": list(options or []),
        "print_eligible": True,
        "local_only": True,
        "public_ready": False,
    }


def make_question_items(rows: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for row in rows:
        items.append(
            make_question_item(
                question_id=str(row.get("question_id")),
                source_unit_ref=str(row.get("source_unit_ref")),
                question_type=str(row.get("question_type")),
                question_text=str(row.get("question_text")),
                answer=str(row.get("answer")),
                options=list(row.get("options", [])),
            )
        )
    return items


def make_synthetic_question_items() -> List[Dict[str, Any]]:
    return make_question_items(
        [
            {
                "question_id": "p7_q_001",
                "source_unit_ref": "p6_sentence_001",
                "question_type": "literal_detail",
                "question_text": "Where is the cat?",
                "answer": "on the mat",
                "options": ["on the mat", "under the bed", "in the box"],
            },
            {
                "question_id": "p7_q_002",
                "source_unit_ref": "p6_dialogue_001",
                "question_type": "wh_question",
                "question_text": "Where is the book?",
                "answer": "on the desk",
                "options": ["on the desk", "in the bag", "under the chair"],
            },
            {
                "question_id": "p7_q_003",
                "source_unit_ref": "p6_passage_001",
                "question_type": "sequence",
                "question_text": "What does Tom put in the bag?",
                "answer": "a book",
                "options": ["a book", "a pencil", "a toy"],
            },
        ]
    )
