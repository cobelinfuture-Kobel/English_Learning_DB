"""Build ReadingV1 P4 local review plans from P3 summaries."""

from __future__ import annotations

from typing import Any, Dict, Mapping

SCHEMA_VERSION = "reading_v1_p4_plan.v1"


def make_plan(summary: Mapping[str, Any], max_groups: int = 3, operator_note: str = "") -> Dict[str, Any]:
    counts = summary.get("group_counts", {})
    if not isinstance(counts, Mapping):
        counts = {}
    ranked = sorted(counts.items(), key=lambda item: (-int(item[1]), str(item[0])))
    focus_groups = [str(group) for group, count in ranked if int(count) > 0][:max_groups]
    return {
        "schema_version": SCHEMA_VERSION,
        "package_id": summary.get("package_id"),
        "source_item_count": summary.get("item_count", 0),
        "focus_groups": focus_groups,
        "operator_note": operator_note,
        "local_only": True,
        "private_homework_only": True,
        "public_ready": False,
        "learner_state_write": False,
    }


def make_synthetic_plan() -> Dict[str, Any]:
    return make_plan(
        {
            "package_id": "p2_package_001",
            "item_count": 2,
            "group_counts": {"review_literal_detail": 1, "review_unanswered": 1},
        },
        operator_note="local review",
    )
