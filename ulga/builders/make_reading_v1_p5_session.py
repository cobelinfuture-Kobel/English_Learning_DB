"""Build ReadingV1 P5 local review sessions from P4 plans."""

from __future__ import annotations

from typing import Any, Dict, Mapping

SCHEMA_VERSION = "reading_v1_p5_session.v1"


def make_session(plan: Mapping[str, Any], session_id: str = "p5_session_001", operator_note: str = "") -> Dict[str, Any]:
    focus_groups = plan.get("focus_groups", [])
    if not isinstance(focus_groups, list):
        focus_groups = []
    return {
        "schema_version": SCHEMA_VERSION,
        "session_id": session_id,
        "package_id": plan.get("package_id"),
        "source_plan_version": plan.get("schema_version"),
        "focus_groups": [str(group) for group in focus_groups],
        "operator_note": operator_note,
        "local_only": True,
        "private_homework_only": True,
        "public_ready": False,
        "learner_state_write": False,
    }


def make_synthetic_session() -> Dict[str, Any]:
    return make_session(
        {
            "schema_version": "reading_v1_p4_plan.v1",
            "package_id": "p2_package_001",
            "focus_groups": ["review_literal_detail", "review_unanswered"],
        },
        operator_note="local session",
    )
