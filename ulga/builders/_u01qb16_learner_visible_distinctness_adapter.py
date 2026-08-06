"""Learner-visible distinctness guard for the existing U01QB13 matcher.

U01QB15 already prevents duplicate runtime item identities inside one form/skill
session. Real learner use exposed a stricter pedagogical defect: two different
item IDs can still render the exact same stimulus, prompt, and option set. This
adapter preserves the existing 474-item QuestionBank, U01QB13 blueprint,
response/scoring contracts, learner database and form order, but requires the
whole-form matcher to reserve learner-visible-distinct questions as well as
distinct item IDs.

Speaking is excluded from the private-item visible-signature rule because its
learner-facing prompt is scene-projected from the U01QB13 blueprint rather than
from ``private_item_json``. Its existing distinct-item rule remains unchanged.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from ulga.builders import _u01qb13_distinct_item_matching_adapter as matching

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Runtime pedagogical-quality adapter over the existing U01QB13 whole-form matcher; it rejects learner-visible duplicate question assignments without creating or mutating QuestionBank content, forms, scoring, learner state, Unit02-24 content, audio, or A2 content."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB16_Unit01LearnerVisibleQuestionDistinctnessFullFix"
PASS_STATUS = "PASS_A1FS_V1_U01QB16_UNIT01_LEARNER_VISIBLE_QUESTION_DISTINCTNESS_FULLFIX"
NEXT_SHORT_STEP = "A1FS-V1-U01QB16B_Unit01TwelveFormTaskAngleAndSupportProgressionReconciliation"

_ORIGINAL_SOLVER = matching.solve_distinct_activity_assignment
_INSTALLED = False


class LearnerVisibleDistinctnessError(matching.DistinctItemMatchingError):
    pass


def _normalized_text(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def learner_visible_signature(row: Mapping[str, Any]) -> str:
    """Return a stable signature for what a learner actually sees.

    Option order is intentionally ignored. Reordering the same choices is not a
    pedagogically distinct question. Speaking uses item identity because its
    real prompt comes from the blueprint scene projection, not the catalog row.
    """
    item_id = str(row.get("item_id") or "")
    skill = str(row.get("skill") or "").upper()
    if skill == "SPEAKING":
        return f"SPEAKING_ITEM:{item_id}"
    try:
        item = json.loads(str(row.get("private_item_json") or "{}"))
    except json.JSONDecodeError as exc:
        raise LearnerVisibleDistinctnessError(
            f"LEARNER_VISIBLE_PRIVATE_ITEM_JSON_INVALID:{item_id}"
        ) from exc
    if not isinstance(item, Mapping):
        raise LearnerVisibleDistinctnessError(
            f"LEARNER_VISIBLE_PRIVATE_ITEM_OBJECT_REQUIRED:{item_id}"
        )
    options = sorted(_normalized_text(value) for value in (item.get("options") or []))
    visible = {
        "stimulus": _normalized_text(item.get("stimulus")),
        "prompt": _normalized_text(item.get("prompt")),
        "options": options,
    }
    raw = json.dumps(visible, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def solve_learner_visible_distinct_activity_assignment(
    candidate_pairs_by_activity: Mapping[
        str, Sequence[tuple[tuple[Any, ...], Mapping[str, Any]]]
    ],
) -> dict[str, tuple[Mapping[str, Any], tuple[Any, ...]]]:
    """Assign one item per activity with unique item and visible signatures."""
    normalized: dict[str, list[tuple[tuple[Any, ...], Mapping[str, Any], str]]] = {}
    for activity_id, pairs in candidate_pairs_by_activity.items():
        rows = sorted(
            [
                (tuple(rank), row, learner_visible_signature(row))
                for rank, row in pairs
            ],
            key=lambda pair: (pair[0], str(pair[1]["item_id"])),
        )
        if not rows:
            raise LearnerVisibleDistinctnessError(
                f"ACTIVITY_RUNTIME_CANDIDATES_EMPTY:{activity_id}"
            )
        normalized[str(activity_id)] = rows

    order = sorted(
        normalized,
        key=lambda activity_id: (
            len({signature for _rank, _row, signature in normalized[activity_id]}),
            len(normalized[activity_id]),
            activity_id,
        ),
    )
    assignment: dict[str, tuple[Mapping[str, Any], tuple[Any, ...]]] = {}
    used_items: set[str] = set()
    used_signatures: set[str] = set()

    def solve(index: int) -> bool:
        if index == len(order):
            return True
        activity_id = order[index]
        for rank, row, signature in normalized[activity_id]:
            item_id = str(row["item_id"])
            if item_id in used_items or signature in used_signatures:
                continue
            used_items.add(item_id)
            used_signatures.add(signature)
            assignment[activity_id] = (row, rank)
            if solve(index + 1):
                return True
            assignment.pop(activity_id, None)
            used_signatures.remove(signature)
            used_items.remove(item_id)
        return False

    if not solve(0):
        detail = ";".join(
            f"{activity_id}=items:{len(normalized[activity_id])},visible:"
            f"{len({signature for _rank, _row, signature in normalized[activity_id]})}"
            for activity_id in order
        )
        raise LearnerVisibleDistinctnessError(
            "FORM_COMPONENT_LEARNER_VISIBLE_DISTINCTNESS_UNSAT:" + detail
        )

    if len(assignment) != len(normalized):
        raise LearnerVisibleDistinctnessError(
            f"FORM_COMPONENT_LEARNER_VISIBLE_MATCHING_COUNT_INVALID:{len(assignment)}:{len(normalized)}"
        )
    item_ids = [str(row["item_id"]) for row, _rank in assignment.values()]
    signatures = [learner_visible_signature(row) for row, _rank in assignment.values()]
    if len(item_ids) != len(set(item_ids)):
        raise LearnerVisibleDistinctnessError("FORM_COMPONENT_DISTINCT_ITEM_MATCHING_DUPLICATE")
    if len(signatures) != len(set(signatures)):
        raise LearnerVisibleDistinctnessError(
            "FORM_COMPONENT_LEARNER_VISIBLE_SIGNATURE_DUPLICATE"
        )
    return assignment


def install() -> None:
    """Patch only the existing matcher decision function, idempotently."""
    global _INSTALLED
    current = matching.solve_distinct_activity_assignment
    if current is solve_learner_visible_distinct_activity_assignment:
        _INSTALLED = True
        return
    if current is not _ORIGINAL_SOLVER:
        raise LearnerVisibleDistinctnessError(
            "U01QB13_MATCHING_SOLVER_ALREADY_PATCHED_BY_OTHER_AUTHORITY"
        )
    matching.solve_distinct_activity_assignment = (
        solve_learner_visible_distinct_activity_assignment
    )
    _INSTALLED = True


def installed() -> bool:
    return (
        _INSTALLED
        and matching.solve_distinct_activity_assignment
        is solve_learner_visible_distinct_activity_assignment
    )
