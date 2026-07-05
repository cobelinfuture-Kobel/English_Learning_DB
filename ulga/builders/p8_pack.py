from __future__ import annotations


def pack(cards):
    cards = list(cards)
    return {
        "schema_version": "p8_pack.v1",
        "count": len(cards),
        "items": [str(card.get("page_id", "")) for card in cards],
        "local_only": True,
    }
