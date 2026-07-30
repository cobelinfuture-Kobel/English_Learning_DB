#!/usr/bin/env python3
"""Connect U01QB02 dynamic sessions to the existing A1FS V1.2.1 product.

The product keeps its authenticated HTTP routes, V12 learner application,
M3 state authority, M6 scoring authority, completion gate, dashboard, and
static learner surface. This adapter only changes the Unit01 session payload:
start/resume return the ten U01QB02 selected items, exposure is recorded through
U01QB02+M3, and completion readiness uses the selected ten-item denominator.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    _a1fs_online_v1_2_u01e_s05_release_migration_acceptance_core as product_core,
)
from ulga.builders import (
    build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as session_runtime,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Adapts the existing authenticated A1FS V1.2.1 learner product to consume the already-approved U01QB02 session plan through existing start, active-session, exposure, response, completion, progress, and dashboard interfaces; no new content, API authority, UI authority, planner, learner database, scoring engine, mastery claim, audio, A2 content, or Unit02-Unit24 content is created."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB03_Unit01ApprovedVariantLearnerRendererAndRealAttemptAcceptance"
SCHEMA_VERSION = "a1fs.v1.u01qb03.unit01_approved_variant_product_surface.v1"
PASS_STATUS = "PASS_A1FS_V1_U01QB03_UNIT01_APPROVED_VARIANT_PRODUCT_SURFACE"
NEXT_SHORT_STEP = "A1FS-V1-U01QB04_Unit01ApprovedVariantProductionDatabaseMigrationAndBrowserAcceptance"
DYNAMIC_SESSION_ITEM_COUNT = 10
PASSING_OUTCOMES = frozenset({"AUTO_PASS", "HUMAN_APPROVE"})
RETRY_OUTCOMES = frozenset({"AUTO_FAIL", "HUMAN_REJECT"})
PENDING_OUTCOMES = frozenset({"PENDING_HUMAN_REVIEW", "HUMAN_DEFER"})


class ProductSurfaceError(ValueError):
    """Fail-closed Unit01 dynamic-product integration error."""


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=5000")
    return connection


def _unit01_lesson(lesson_id: str) -> bool:
    return str(lesson_id) in session_runtime.LESSON_TO_SKILL


def _stimulus(value: Any) -> dict[str, str] | None:
    text = str(value or "").strip()
    return {"title": "題目內容", "body": text} if text else None


def _learner_asset(
    *,
    catalog: Mapping[str, Any],
    item: Mapping[str, Any],
    position: int,
    selection_reason: str,
) -> dict[str, Any]:
    scoring_mode = str(item.get("scoring_mode") or "")
    raw_options = list(item.get("options") or [])
    sequence = scoring_mode == "EXACT_SEQUENCE"
    learner_payload = {
        "prompt": str(item.get("prompt") or ""),
        "stimulus": _stimulus(item.get("stimulus")),
        "support_text": f"本題來源：{selection_reason}",
        "model_language": None,
        "sentence_frame": None,
        "options": [] if sequence else raw_options,
        "token_bank": raw_options if sequence else [],
        "response_capture_enabled": bool(catalog["capture_enabled"]),
        "response_type": "sequence" if sequence else "text",
        "writing_stage": "CONTROLLED_SEQUENCE" if sequence else None,
        "question_type": str(item.get("question_type") or ""),
        "support_level": str(catalog["support_level"]),
        "item_position": int(position),
        "selection_reason": str(selection_reason),
    }
    return {
        "asset_key": str(catalog["asset_key"]),
        "role": "DYNAMIC_APPROVED_VARIANT",
        "item_id": str(catalog["item_id"]),
        "learner_payload": learner_payload,
    }


class Unit01VariantProductApplication(product_core.V12Application):
    """Existing product application with Unit01 dynamic approved-item sessions."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.unit01_variant_runtime = session_runtime.Unit01ApprovedVariantSessionRuntime(
            self.database_path
        )
        self.unit01_variant_initialization = self.unit01_variant_runtime.initialize()

    def bootstrap(self) -> dict[str, Any]:
        value = super().bootstrap()
        for unit in value.get("units", []):
            if unit.get("internal_grammar_unit_id") != session_runtime.m01.UNIT_ID and unit.get("grammar_unit_id") != session_runtime.m01.UNIT_ID:
                continue
            for lane in unit.get("lanes", []):
                if _unit01_lesson(str(lane.get("lesson_id") or "")):
                    lane.update(
                        {
                            "session_item_source": "U01QB02_VALIDATOR_APPROVED_DYNAMIC_SESSION",
                            "session_item_count": DYNAMIC_SESSION_ITEM_COUNT,
                            "static_assets_are_regression_baseline_only": True,
                        }
                    )
        semantics = value.setdefault("learner_product_semantics", {})
        semantics.update(
            {
                "unit01_dynamic_approved_variant_sessions_connected": True,
                "unit01_registered_approved_item_count": int(
                    self.unit01_variant_initialization["registered_item_count"]
                ),
                "unit01_session_item_count": DYNAMIC_SESSION_ITEM_COUNT,
                "unit01_exposure_history_connected": True,
                "unit01_existing_response_scoring_reused": True,
                "unit01_runtime_free_generation_allowed": False,
            }
        )
        value.update(
            {
                "u01qb03_task_id": TASK_ID,
                "u01qb03_schema_version": SCHEMA_VERSION,
                "u01qb03_validation_status": PASS_STATUS,
            }
        )
        return value

    def _dynamic_assets(self, session_id: str) -> list[dict[str, Any]]:
        with closing(_connect(self.database_path)) as connection:
            rows = connection.execute(
                """SELECT s.item_position,s.selection_reason,c.*,c.private_item_json
                FROM u01qb02_session_items s
                JOIN u01qb02_item_catalog c USING(item_id)
                WHERE s.session_id=? ORDER BY s.item_position""",
                (str(session_id),),
            ).fetchall()
        if len(rows) != DYNAMIC_SESSION_ITEM_COUNT:
            raise ProductSurfaceError(
                f"dynamic_session_item_count_invalid:{session_id}:{len(rows)}"
            )
        assets: list[dict[str, Any]] = []
        for row in rows:
            item = json.loads(str(row["private_item_json"]))
            if not isinstance(item, dict):
                raise ProductSurfaceError(
                    f"dynamic_item_not_object:{row['item_id']}"
                )
            assets.append(
                _learner_asset(
                    catalog=row,
                    item=item,
                    position=int(row["item_position"]),
                    selection_reason=str(row["selection_reason"]),
                )
            )
        return assets

    def _attach_dynamic_plan(self, session: Mapping[str, Any]) -> dict[str, Any]:
        value = dict(session)
        lesson_id = str(value.get("lesson_id") or "")
        if not _unit01_lesson(lesson_id):
            return value
        plan = self.unit01_variant_runtime.assemble_session(
            learner_id=str(value.get("learner_id") or self.default_learner_id),
            session_id=str(value["session_id"]),
        )
        assets = self._dynamic_assets(str(value["session_id"]))
        return {
            **value,
            "assets": assets,
            "item_count": len(assets),
            "dynamic_item_session": True,
            "answer_keys_exposed": False,
            "source_bank_sha256": plan["source_bank_sha256"],
            "plan_digest": plan["plan_digest"],
            "u01qb03_task_id": TASK_ID,
        }

    def start_session(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._attach_dynamic_plan(super().start_session(payload))

    def active_session_readback(self) -> dict[str, Any]:
        value = super().active_session_readback()
        if not value.get("active"):
            return value
        session = value.get("session")
        if not isinstance(session, Mapping) or not _unit01_lesson(
            str(session.get("lesson_id") or "")
        ):
            return value
        attached = self._attach_dynamic_plan(session)
        value.update(
            {
                "session": {
                    key: attached[key]
                    for key in (
                        "session_id",
                        "lesson_id",
                        "skill",
                        "level",
                        "session_state",
                        "session_version",
                        "started_at",
                    )
                    if key in attached
                },
                "assets": attached["assets"],
                "item_count": attached["item_count"],
                "dynamic_item_session": True,
                "answer_keys_exposed": False,
                "source_bank_sha256": attached["source_bank_sha256"],
                "plan_digest": attached["plan_digest"],
                "u01qb03_task_id": TASK_ID,
            }
        )
        return value

    def record_exposure(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        asset_key = str(payload.get("asset_key") or "")
        with closing(_connect(self.database_path)) as connection:
            row = connection.execute(
                "SELECT item_id FROM u01qb02_item_catalog WHERE asset_key=?",
                (asset_key,),
            ).fetchone()
        if not row:
            return super().record_exposure(payload)
        result = self.unit01_variant_runtime.record_item_exposure(
            session_id=str(payload["session_id"]),
            item_id=str(row["item_id"]),
            expected_session_version=int(payload["expected_session_version"]),
            exposure_id=str(payload["exposure_id"])
            if payload.get("exposure_id")
            else None,
            at=str(payload["at"]) if payload.get("at") else None,
        )
        return {
            **result,
            "dynamic_item_session": True,
            "u01qb03_task_id": TASK_ID,
        }

    def completion_readiness(self, session_id: str) -> dict[str, Any]:
        session_id = str(session_id)
        with closing(_connect(self.database_path)) as connection:
            session = connection.execute(
                """SELECT session_id,lesson_id,skill,session_state,session_version
                FROM learning_sessions WHERE session_id=?""",
                (session_id,),
            ).fetchone()
            if not session:
                raise ProductSurfaceError("session_not_found")
            lesson_id = str(session["lesson_id"])
            if not _unit01_lesson(lesson_id):
                return super().completion_readiness(session_id)
            skill = str(session["skill"]).upper()
            if skill == "SPEAKING":
                return {
                    "session_id": session_id,
                    "lesson_id": lesson_id,
                    "skill": skill,
                    "session_state": str(session["session_state"]),
                    "session_version": int(session["session_version"]),
                    "gate_mode": "PRACTICE_SESSION_NO_SCORE",
                    "required_response_count": 0,
                    "attempted_response_count": 0,
                    "passed_response_count": 0,
                    "not_attempted_count": 0,
                    "retry_required_count": 0,
                    "pending_human_review_count": 0,
                    "completion_allowed": True,
                    "blocking_reason_codes": [],
                    "assets": [],
                    "dynamic_item_session": True,
                    "mastery_claimed": False,
                }
            selected = connection.execute(
                """SELECT s.item_position,c.asset_key,r.contract_json
                FROM u01qb02_session_items s
                JOIN u01qb02_item_catalog c USING(item_id)
                JOIN response_contracts r USING(asset_key)
                WHERE s.session_id=? AND r.capture_enabled=1
                ORDER BY s.item_position""",
                (session_id,),
            ).fetchall()
            if len(selected) != DYNAMIC_SESSION_ITEM_COUNT:
                raise ProductSurfaceError(
                    f"dynamic_completion_denominator_invalid:{lesson_id}:{len(selected)}"
                )
            latest_rows = connection.execute(
                """SELECT a.asset_key,a.attempt_sequence,r.outcome
                FROM response_attempts a JOIN scoring_results r USING(attempt_id)
                WHERE a.session_id=? ORDER BY a.asset_key,a.attempt_sequence DESC""",
                (session_id,),
            ).fetchall()
            latest: dict[str, sqlite3.Row] = {}
            for row in latest_rows:
                latest.setdefault(str(row["asset_key"]), row)
            attempt_counts = {
                str(row["asset_key"]): int(row["total"])
                for row in connection.execute(
                    """SELECT asset_key,COUNT(*) AS total FROM response_attempts
                    WHERE session_id=? GROUP BY asset_key""",
                    (session_id,),
                ).fetchall()
            }

        assets: list[dict[str, Any]] = []
        blockers: list[str] = []
        passed = pending = retry = attempted = not_attempted = 0
        for selected_row in selected:
            asset_key = str(selected_row["asset_key"])
            contract = json.loads(str(selected_row["contract_json"]))
            row = latest.get(asset_key)
            outcome = None if row is None else str(row["outcome"])
            if row is None:
                state = "NOT_ATTEMPTED"
                not_attempted += 1
                blockers.append("REQUIRED_RESPONSE_NOT_ATTEMPTED")
            else:
                attempted += 1
                if outcome in PASSING_OUTCOMES:
                    state = "PASSED"
                    passed += 1
                elif outcome in RETRY_OUTCOMES:
                    state = "RETRY_REQUIRED"
                    retry += 1
                    blockers.append("LATEST_ATTEMPT_RETRY_REQUIRED")
                elif outcome in PENDING_OUTCOMES:
                    state = "PENDING_HUMAN_REVIEW"
                    pending += 1
                    blockers.append("HUMAN_REVIEW_PENDING")
                else:
                    raise ProductSurfaceError(
                        f"unsupported_scoring_outcome:{outcome}"
                    )
            assets.append(
                {
                    "asset_index": int(selected_row["item_position"]),
                    "asset_key": asset_key,
                    "scoring_mode": str(contract.get("scoring_mode") or ""),
                    "human_review_fallback": bool(
                        contract.get("human_review_fallback")
                    ),
                    "attempt_count": int(attempt_counts.get(asset_key, 0)),
                    "latest_outcome": outcome,
                    "completion_state": state,
                }
            )
        blockers = list(dict.fromkeys(blockers))
        allowed = not blockers and passed == DYNAMIC_SESSION_ITEM_COUNT
        return {
            "session_id": session_id,
            "lesson_id": lesson_id,
            "skill": skill,
            "session_state": str(session["session_state"]),
            "session_version": int(session["session_version"]),
            "gate_mode": "U01QB02_DYNAMIC_SESSION_LATEST_ATTEMPT_PASS_OR_HUMAN_APPROVAL",
            "required_response_count": DYNAMIC_SESSION_ITEM_COUNT,
            "attempted_response_count": attempted,
            "passed_response_count": passed,
            "not_attempted_count": not_attempted,
            "retry_required_count": retry,
            "pending_human_review_count": pending,
            "completion_allowed": allowed,
            "blocking_reason_codes": blockers,
            "assets": assets,
            "dynamic_item_session": True,
            "mastery_claimed": False,
        }


def make_app(
    *,
    database: Path,
    bundles: Mapping[str, Mapping[str, Any]],
    sequence: Mapping[str, int],
    graph_path: Path,
    state_root: Path,
    registry: Sequence[Mapping[str, Any]],
    learner_id: str,
) -> Unit01VariantProductApplication:
    return Unit01VariantProductApplication(
        database_path=database,
        bundles=bundles,
        sequence_by_grammar=sequence,
        graph_path=graph_path,
        state_root=state_root,
        default_learner_id=learner_id,
        target_registry=registry,
    )
