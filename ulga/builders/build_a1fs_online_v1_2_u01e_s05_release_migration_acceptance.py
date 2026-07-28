#!/usr/bin/env python3
"""S05 public facade with deterministic runtime-role derivation.

The S03 approved candidate schema intentionally records pedagogical learning_role
and question_type rather than an M6 transport role. This facade derives the M6
role without changing the approved item identity, then delegates every other S05
operation to the frozen core implementation.
"""
from __future__ import annotations

from typing import Any, Mapping

from ulga.builders import (
    _a1fs_online_v1_2_u01e_s05_release_migration_acceptance_core as _core,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Derives the existing M6 PRD/CHK/XFR transport role from approved S03 metadata. "
    "It creates no content, answer, scoring rule, learner state, mastery, audio, A2, "
    "external route, or parallel authority."
)


def runtime_role(item: Mapping[str, Any]) -> str:
    question_type = str(item.get("question_type") or "")
    learning_role = str(item.get("learning_role") or "")
    if question_type in {"checkpoint_choice", "checkpoint_write"}:
        return "CHK"
    if learning_role == "TRANSFER":
        return "XFR"
    return "PRD"


def runtime_asset(item: Mapping[str, Any], approved_sha: str) -> dict[str, Any]:
    key = str(item["candidate_item_id"])
    return {
        "asset_key": key,
        "asset_id": key,
        "lesson_id": _core.lesson_for_skill(str(item["skill"])),
        "skill": str(item["skill"]),
        "level": "A1",
        "role": runtime_role(item),
        "learner_payload": _core.learner_payload(item, approved_sha),
        "content_digest": _core.digest(
            {
                "candidate_item_id": key,
                "semantic_signature": item["semantic_signature"],
                "approved_sha": approved_sha,
            }
        ),
    }


_core.runtime_asset = runtime_asset
_core.MODULE = __name__

for _name, _value in vars(_core).items():
    if not _name.startswith("__") and _name not in globals():
        globals()[_name] = _value

MODULE = __name__
