"""Build ReadingV1 P3 local operator summaries."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, Mapping

SUMMARY_VERSION = "reading_v1_p3_local_summary.v1"


def make_summary(package_id: str, records: Iterable[Mapping[str, Any]], operator_note: str = "") -> Dict[str, Any]:
    rows = list(records)
    group_counts = Counter(str(row.get("group_key")) for row in rows)
    question_counts = Counter(str(row.get("source_question_type")) for row in rows if row.get("source_question_type"))
    pattern_counts = Counter(str(row.get("source_pattern_family")) for row in rows if row.get("source_pattern_family"))
    return {
        "schema_version": SUMMARY_VERSION,
        "package_id": package_id,
        "item_count": len(rows),
        "group_counts": dict(sorted(group_counts.items())),
        "question_type_counts": dict(sorted(question_counts.items())),
        "pattern_family_counts": dict(sorted(pattern_counts.items())),
        "operator_note": operator_note,
        "private_homework_only": True,
        "public_ready": False,
        "learner_state_write": False,
    }
