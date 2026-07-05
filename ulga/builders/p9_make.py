from __future__ import annotations


def make_ok(qa_id, card):
    q = len(card.get("items", []))
    k = len(card.get("keys", []))
    return {
        "schema_version": "p9_ok.v1",
        "qa_id": qa_id,
        "source_page": card.get("page_id", ""),
        "q": q,
        "k": k,
        "aligned": q == k and q > 0,
        "local_only": True,
        "public_ready": False,
    }


def make_synthetic_ok():
    return make_ok(
        "p9_qa_001",
        {
            "page_id": "p8_page_001",
            "items": ["Where is the cat?", "Where is the book?", "What does Tom put in the bag?"],
            "keys": ["on the mat", "on the desk", "a book"],
        },
    )
