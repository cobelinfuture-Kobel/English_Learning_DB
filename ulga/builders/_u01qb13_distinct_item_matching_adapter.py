"""Whole-form distinct-item matcher for the existing U01QB13 runtime selector.

U01QB14R1 proves per-form/skill bipartite capacity across the active Unit01
QuestionBank. Historical U01QB13 selection consumed the same candidate rules but
picked one activity at a time, so a locally best item could strand a later
activity even when a valid whole-form matching existed. This adapter preserves
all existing U01QB13 candidate/rank/session/scoring/database contracts and only
replaces that greedy assignment step with deterministic augmenting-path matching.

Scoring compatibility is derived from the same canonical response_contracts
table consumed by U01QB14 replay. The matcher may reroute item identity to achieve
whole-form distinctness, but it may not infer scoring semantics from private item
JSON or silently change a scored activity between auto-score and human review.
"""
from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration
    as target,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Execution adapter over the existing U01QB13 candidate/rank/session path; replaces greedy item assignment with deterministic whole-form distinct matching while preserving canonical response_contracts scoring semantics, and creates no content, QuestionBank, planner, runtime, scoring, or learner-state authority."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB13_CanonicalResponseContractScoringClassPreservationFullFix"
PASS_STATUS = "PASS_A1FS_V1_U01QB13_CANONICAL_RESPONSE_CONTRACT_SCORING_CLASS_PRESERVATION_FULLFIX"

ORIGINAL_ASSEMBLE_FORM_COMPONENT = target.assemble_form_component
HUMAN_REVIEW_WRITING_ANGLES = frozenset(
    {
        "COMPLETE_SENTENCE_PRODUCTION",
        "CONNECTED_SENTENCE_PRODUCTION",
    }
)
SCORING_CLASS_AUTO = "AUTO"
SCORING_CLASS_HUMAN_REVIEW = "HUMAN_REVIEW"
SCORING_CLASS_PRACTICE_ONLY = "PRACTICE_ONLY"
SCORING_CLASS_UNKNOWN = "UNKNOWN"


class DistinctItemMatchingError(ValueError):
    pass


def required_activity_scoring_class(activity: Mapping[str, Any]) -> str:
    """Return the scoring class already implied by the U01QB13 activity contract."""
    if not bool(activity.get("scored")):
        return SCORING_CLASS_PRACTICE_ONLY
    skill = str(activity.get("skill") or "")
    angle = str(activity.get("task_angle") or "")
    if skill == "WRITING" and angle in HUMAN_REVIEW_WRITING_ANGLES:
        return SCORING_CLASS_HUMAN_REVIEW
    return SCORING_CLASS_AUTO


def scoring_class_from_contract_json(
    contract_json: str | None,
    *,
    capture_enabled: bool,
) -> str:
    """Classify from the canonical response_contracts contract JSON."""
    if not capture_enabled:
        return SCORING_CLASS_PRACTICE_ONLY
    if contract_json is None:
        return SCORING_CLASS_UNKNOWN
    try:
        contract = json.loads(str(contract_json))
    except (TypeError, json.JSONDecodeError):
        return SCORING_CLASS_UNKNOWN
    if not isinstance(contract, Mapping):
        return SCORING_CLASS_UNKNOWN
    mode = str(contract.get("scoring_mode") or "")
    if mode == "FEATURE_RUBRIC":
        return SCORING_CLASS_HUMAN_REVIEW
    if mode:
        return SCORING_CLASS_AUTO
    return SCORING_CLASS_UNKNOWN


def load_runtime_item_scoring_classes(
    connection,
    *,
    lesson_id: str,
) -> dict[str, str]:
    """Load scoring classes through the same catalog-to-response-contract join as U01QB14."""
    rows = connection.execute(
        """SELECT c.item_id,c.capture_enabled,r.contract_json
           FROM u01qb02_item_catalog c
           LEFT JOIN response_contracts r ON r.asset_key=c.asset_key
           WHERE c.lesson_id=?
           ORDER BY c.item_id""",
        (lesson_id,),
    ).fetchall()
    return {
        str(row["item_id"]): scoring_class_from_contract_json(
            row["contract_json"],
            capture_enabled=bool(row["capture_enabled"]),
        )
        for row in rows
    }


def candidate_preserves_scoring_class(
    activity: Mapping[str, Any],
    row: Mapping[str, Any],
    runtime_scoring_classes: Mapping[str, str],
) -> bool:
    """Fail closed when a scored activity would drift to another scoring class."""
    required = required_activity_scoring_class(activity)
    if required == SCORING_CLASS_PRACTICE_ONLY:
        return True
    return runtime_scoring_classes.get(
        str(row["item_id"]), SCORING_CLASS_UNKNOWN
    ) == required


def solve_distinct_activity_assignment(
    candidate_pairs_by_activity: Mapping[
        str, Sequence[tuple[tuple[Any, ...], Mapping[str, Any]]]
    ],
) -> dict[str, tuple[Mapping[str, Any], tuple[Any, ...]]]:
    """Assign one distinct item to every activity using deterministic Kuhn matching."""
    normalized: dict[str, list[tuple[tuple[Any, ...], Mapping[str, Any]]]] = {}
    for activity_id, pairs in candidate_pairs_by_activity.items():
        rows = sorted(
            [(tuple(rank), row) for rank, row in pairs],
            key=lambda pair: (pair[0], str(pair[1]["item_id"])),
        )
        if not rows:
            raise DistinctItemMatchingError(
                f"ACTIVITY_RUNTIME_CANDIDATES_EMPTY:{activity_id}"
            )
        normalized[str(activity_id)] = rows

    order = sorted(
        normalized,
        key=lambda activity_id: (len(normalized[activity_id]), activity_id),
    )
    owner_by_item: dict[str, str] = {}
    assignment: dict[str, tuple[Mapping[str, Any], tuple[Any, ...]]] = {}

    def augment(activity_id: str, seen_items: set[str]) -> bool:
        for rank, row in normalized[activity_id]:
            item_id = str(row["item_id"])
            if item_id in seen_items:
                continue
            seen_items.add(item_id)
            previous = owner_by_item.get(item_id)
            if previous is None or augment(previous, seen_items):
                owner_by_item[item_id] = activity_id
                assignment[activity_id] = (row, rank)
                return True
        return False

    for activity_id in order:
        if not augment(activity_id, set()):
            raise DistinctItemMatchingError(
                "FORM_COMPONENT_DISTINCT_ITEM_MATCHING_UNSAT:"
                + activity_id
            )

    if len(assignment) != len(normalized):
        raise DistinctItemMatchingError(
            f"FORM_COMPONENT_DISTINCT_ITEM_MATCHING_COUNT_INVALID:{len(assignment)}:{len(normalized)}"
        )
    item_ids = [str(row["item_id"]) for row, _rank in assignment.values()]
    if len(item_ids) != len(set(item_ids)):
        raise DistinctItemMatchingError("FORM_COMPONENT_DISTINCT_ITEM_MATCHING_DUPLICATE")
    return assignment


def assemble_form_component(
    database,
    *,
    learner_id: str,
    session_id: str,
    form_ordinal: int,
    selected_at: str | None = None,
) -> dict[str, Any]:
    if form_ordinal < 1 or form_ordinal > target.FORM_COUNT:
        raise target.BlueprintIntegrationError("FORM_ORDINAL_INVALID")
    selected_at = target.timestamp(selected_at)
    runtime = target.qb02.Unit01ApprovedVariantSessionRuntime(database)
    with runtime.write() as connection:
        connection.row_factory = target.sqlite3.Row
        for table in (
            "u01qb13_metadata",
            "u01qb13_blueprint_activities",
            "u01qb13_session_bindings",
            "response_contracts",
        ):
            target._require_table(connection, table)
        metadata = dict(
            connection.execute("SELECT key,value FROM u01qb13_metadata")
        )
        if metadata.get("validation_status") != target.PASS_STATUS:
            raise target.BlueprintIntegrationError("U01QB13_BLUEPRINT_NOT_INSTALLED")
        session = runtime._active_session(
            connection,
            learner_id=learner_id,
            session_id=session_id,
        )
        skill = str(session["skill"])
        existing = connection.execute(
            "SELECT 1 FROM u01qb13_session_bindings WHERE session_id=? LIMIT 1",
            (session_id,),
        ).fetchone()
        if existing:
            return target.form_component_payload(connection, session_id=session_id)
        if connection.execute(
            "SELECT 1 FROM u01qb02_session_plans WHERE session_id=?",
            (session_id,),
        ).fetchone():
            raise target.BlueprintIntegrationError(
                "SESSION_ALREADY_PLANNED_WITHOUT_U01QB13_BINDING"
            )

        activities = [
            dict(row)
            for row in connection.execute(
                """SELECT * FROM u01qb13_blueprint_activities
                   WHERE form_ordinal=? AND skill=? ORDER BY activity_id""",
                (form_ordinal, skill),
            )
        ]
        expected_count = {
            "READING": target.READING_PER_FORM,
            "WRITING": target.WRITING_PER_FORM,
            "SPEAKING": target.SPEAKING_PER_FORM,
        }[skill]
        if len(activities) != expected_count:
            raise target.BlueprintIntegrationError(
                f"FORM_COMPONENT_ACTIVITY_COUNT_INVALID:{skill}:{len(activities)}"
            )

        catalog = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM u01qb02_item_catalog WHERE lesson_id=? ORDER BY item_id",
                (session["lesson_id"],),
            )
        ]
        runtime_scoring_classes = load_runtime_item_scoring_classes(
            connection,
            lesson_id=str(session["lesson_id"]),
        )
        if set(runtime_scoring_classes) != {
            str(row["item_id"]) for row in catalog
        }:
            raise target.BlueprintIntegrationError(
                "RUNTIME_SCORING_CLASS_CATALOG_IDENTITY_MISMATCH"
            )
        exposed = {
            str(row[0])
            for row in connection.execute(
                "SELECT DISTINCT item_id FROM u01qb02_item_exposures WHERE learner_id=?",
                (learner_id,),
            )
        }
        recent = {
            str(row[0])
            for row in connection.execute(
                "SELECT item_id FROM u01qb02_item_exposures WHERE learner_id=? ORDER BY exposure_seq DESC LIMIT ?",
                (learner_id, target.qb02.RECENT_EXPOSURE_WINDOW),
            )
        }

        candidate_pairs_by_activity: dict[
            str, list[tuple[tuple[Any, ...], Mapping[str, Any]]]
        ] = {}
        for activity in activities:
            activity_id = str(activity["activity_id"])
            allowed = set(json.loads(str(activity["pattern_family_ids_json"])))
            anchors = {
                str(row).casefold()
                for row in json.loads(str(activity["scene_anchors_json"]))
            }
            candidates: list[tuple[tuple[Any, ...], Mapping[str, Any]]] = []
            for row in catalog:
                if str(row["pattern_family_id"]) not in allowed:
                    continue
                if not candidate_preserves_scoring_class(
                    activity,
                    row,
                    runtime_scoring_classes,
                ):
                    continue
                rank = target._candidate_rank(
                    row=row,
                    anchors=anchors,
                    situation_family=str(activity["situation_family"]),
                    learner_id=learner_id,
                    session_id=session_id,
                    activity_id=activity_id,
                    exposed=exposed,
                    recent=recent,
                    assessment=bool(activity["assessment_candidate"]),
                )
                if rank is not None:
                    candidates.append((rank, row))
            if not candidates:
                required_class = required_activity_scoring_class(activity)
                raise target.BlueprintIntegrationError(
                    f"SCENE_TASK_RUNTIME_BINDING_GAP:{activity_id}:SCORING_CLASS={required_class}"
                )
            candidate_pairs_by_activity[activity_id] = candidates

        try:
            matched = solve_distinct_activity_assignment(candidate_pairs_by_activity)
        except DistinctItemMatchingError as exc:
            raise target.BlueprintIntegrationError(str(exc)) from exc

        selected: list[tuple[Mapping[str, Any], str, str | None, str | None]] = []
        selected_ids: set[str] = set()
        for activity in activities:
            activity_id = str(activity["activity_id"])
            row, _rank = matched[activity_id]
            item_id = str(row["item_id"])
            item = json.loads(str(row["private_item_json"]))
            quality = "LEXICAL_ANCHOR"
            if target._context_matches(item, str(activity["situation_family"])):
                quality = "LEXICAL_ANCHOR_AND_CONTEXT_FAMILY"
            reason = target._selection_reason(
                item_id=item_id,
                exposed=exposed,
                recent=recent,
                assessment=bool(activity["assessment_candidate"]),
                skill=skill,
            )
            selected.append((row, reason, activity_id, quality))
            selected_ids.add(item_id)

        filler_needed = target.qb02.SESSION_SIZE - len(selected)
        if filler_needed != target.SUPPORT_FILLER_COUNTS[skill]:
            raise target.BlueprintIntegrationError(
                f"SUPPORT_FILLER_COUNT_INVALID:{skill}:{filler_needed}"
            )
        filler = [
            row
            for row in catalog
            if str(row["item_id"]) not in selected_ids
            and str(row["item_id"]) not in recent
        ]
        filler = runtime._stable_order(
            learner_id, session_id, "FALLBACK", filler
        )
        if len(filler) < filler_needed:
            filler = runtime._stable_order(
                learner_id,
                session_id,
                "FALLBACK",
                [
                    row
                    for row in catalog
                    if str(row["item_id"]) not in selected_ids
                ],
            )
        for row in filler[:filler_needed]:
            selected.append((row, "FALLBACK", None, None))
            selected_ids.add(str(row["item_id"]))
        if len(selected) != target.qb02.SESSION_SIZE:
            raise target.BlueprintIntegrationError(
                f"SESSION_CONTAINER_COUNT_INVALID:{len(selected)}"
            )

        plan_core = {
            "session_id": session_id,
            "learner_id": learner_id,
            "lesson_id": session["lesson_id"],
            "skill": skill,
            "selected_at": selected_at,
            "recent_exposure_window": target.qb02.RECENT_EXPOSURE_WINDOW,
            "items": [
                {"position": index, "item_id": row["item_id"], "reason": reason}
                for index, (row, reason, _activity_id, _quality) in enumerate(
                    selected, 1
                )
            ],
            "source_bank_sha256": dict(
                connection.execute("SELECT key,value FROM u01qb02_metadata")
            )["source_bank_artifact_sha256"],
        }
        plan_digest = target.qb02.digest(plan_core)
        connection.execute(
            "INSERT INTO u01qb02_session_plans VALUES(?,?,?,?,?,?,?,?,?)",
            (
                session_id,
                learner_id,
                session["lesson_id"],
                skill,
                target.qb02.SESSION_SIZE,
                selected_at,
                target.qb02.RECENT_EXPOSURE_WINDOW,
                plan_core["source_bank_sha256"],
                plan_digest,
            ),
        )
        connection.executemany(
            "INSERT INTO u01qb02_session_items(session_id,item_position,item_id,selection_reason) VALUES(?,?,?,?)",
            [
                (session_id, index, row["item_id"], reason)
                for index, (row, reason, _activity, _quality) in enumerate(selected, 1)
            ],
        )
        activity_by_id = {
            str(item["activity_id"]): item for item in activities
        }
        for index, (row, _reason, activity_id, quality) in enumerate(selected, 1):
            if activity_id is None:
                continue
            activity = activity_by_id[activity_id]
            connection.execute(
                """INSERT INTO u01qb13_session_bindings
                (session_id,activity_id,item_id,item_position,binding_quality,is_assessment_evidence)
                VALUES(?,?,?,?,?,?)""",
                (
                    session_id,
                    activity_id,
                    row["item_id"],
                    index,
                    quality,
                    int(activity["assessment_candidate"]),
                ),
            )
        return target.form_component_payload(connection, session_id=session_id)


def install() -> None:
    """Install idempotently into the canonical U01QB13 module object."""
    if target.assemble_form_component is not assemble_form_component:
        target.assemble_form_component = assemble_form_component
