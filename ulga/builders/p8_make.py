from __future__ import annotations


def make_card(page_id, title, rows):
    rows = list(rows)
    return {
        "schema_version": "p8_card.v1",
        "page_id": page_id,
        "title": title,
        "items": [row.get("question_text", "") for row in rows],
        "keys": [row.get("answer", "") for row in rows],
        "source_ids": [row.get("question_id", "") for row in rows],
        "local_only": True,
        "public_ready": False,
    }


def make_synthetic_card():
    return make_card(
        "p8_page_001",
        "Reading Practice 1",
        [
            {"question_id": "p7_q_001", "question_text": "Where is the cat?", "answer": "on the mat"},
            {"question_id": "p7_q_002", "question_text": "Where is the book?", "answer": "on the desk"},
            {"question_id": "p7_q_003", "question_text": "What does Tom put in the bag?", "answer": "a book"},
        ],
    )
