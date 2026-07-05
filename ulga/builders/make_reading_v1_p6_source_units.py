"""Build ReadingV1 P6 local reviewed source units."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping

SCHEMA_VERSION = "reading_v1_p6_source_unit.v1"


def make_source_unit(
    source_unit_id: str,
    source_type: str,
    source_text: str,
    level: str,
    topic: str,
    reading_skill: str,
    source_ref: str = "operator_reviewed_seed",
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source_unit_id": source_unit_id,
        "source_type": source_type,
        "source_text": source_text,
        "level": level,
        "topic": topic,
        "reading_skill": reading_skill,
        "source_ref": source_ref,
        "reviewed": True,
        "local_only": True,
        "public_ready": False,
    }


def make_source_units(rows: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    units: List[Dict[str, Any]] = []
    for row in rows:
        units.append(
            make_source_unit(
                source_unit_id=str(row.get("source_unit_id")),
                source_type=str(row.get("source_type")),
                source_text=str(row.get("source_text")),
                level=str(row.get("level")),
                topic=str(row.get("topic")),
                reading_skill=str(row.get("reading_skill")),
                source_ref=str(row.get("source_ref", "operator_reviewed_seed")),
            )
        )
    return units


def make_synthetic_source_units() -> List[Dict[str, Any]]:
    return make_source_units(
        [
            {
                "source_unit_id": "p6_sentence_001",
                "source_type": "sentence",
                "source_text": "The cat is on the mat.",
                "level": "A1",
                "topic": "animals",
                "reading_skill": "literal_detail",
            },
            {
                "source_unit_id": "p6_dialogue_001",
                "source_type": "dialogue",
                "source_text": "A: Where is my book? B: It is on the desk.",
                "level": "A1",
                "topic": "classroom",
                "reading_skill": "wh_question",
            },
            {
                "source_unit_id": "p6_passage_001",
                "source_type": "passage",
                "source_text": "Tom has a red bag. He puts a book in the bag.",
                "level": "A1",
                "topic": "school",
                "reading_skill": "sequence",
            },
        ]
    )
