#!/usr/bin/env python3
"""U01QB15-aware A1FS V1.2.1 product runtime.

This module cuts the already-approved Unit01 U01QB15-R1 / Actual Real62 474-item
QuestionBank into the existing pull-to-run product without replacing the 24-unit
bundle registry, M3 learner state, M6 scoring, M7/M8 learning state, or the
existing learner SQLite database.  The static 277-asset release denominator
remains a product-package denominator; the Unit01 QuestionBank is an additive
runtime catalog consumed through the existing U01QB02/U01QB13 authorities.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
import uuid
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from product.a1fs_v1_2_1 import runtime_server as base
from ulga.builders import _u01qb13_distinct_item_matching_adapter as matching
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_razq01e_unit01_approved_content_existing_qb_learner_stimulus_runtime as razq01e
from ulga.builders import build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u13
from ulga.builders import build_a1fs_v1_u01qb15_actual_real62_fresh474_r2_distinct_matching_acceptance_runner as accepted_runner
from ulga.builders import build_a1fs_v1_u01qb15_actual_real62_fresh474_r2_private_acceptance_runner as private_runner

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Cuts the already-approved U01QB15-R1 Actual Real62 QuestionBank and U01QB13 twelve-form consumer into the existing A1FS V1.2.1 learner SQLite and authenticated localhost runtime; it creates no new learner content, QuestionBank authority, planner, learner database, response capture, scoring engine, Unit02-24 content, audio, or A2 content."

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB15_ProductionConsumerCutoverAndLearnerRuntimeIntegration"
PASS_STATUS = "PASS_A1FS_V1_U01QB15_PRODUCTION_CONSUMER_CUTOVER_AND_LEARNER_RUNTIME_INTEGRATION"
MODULE = "product.a1fs_v1_2_1.u01qb15_runtime_server"
NEXT_SHORT_STEP = "A1FS-V1-U01QB15_LearnerFacingE2EAcceptance"
EXPECTED_REAL62_ARTIFACT_SHA256 = private_runner.EXPECTED_REAL62_ARTIFACT_SHA256
EXPECTED_RUNTIME_ITEMS = 474
EXPECTED_EXTENSION_ITEMS = 186
EXPECTED_FORMS = 12
EXPECTED_BLUEPRINT_ACTIVITIES = 240
CUTOVER_TABLE = "u01qb15_product_consumer_cutover"

core = base.operator.s05._core
base.MODULE = MODULE

CUTOVER_SQL = f"""
CREATE TABLE IF NOT EXISTS {CUTOVER_TABLE}(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""


class ProductCutoverError(ValueError):
    """Fail-closed U01QB15 product-cutover error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _table_digest(connection: sqlite3.Connection, table: str) -> str | None:
    if not _table_exists(connection, table):
        return None
    rows = [tuple(row) for row in connection.execute(f"SELECT * FROM {table}").fetchall()]
    rows.sort(key=repr)
    return digest(rows)


def _learner_owned_snapshot(connection: sqlite3.Connection) -> dict[str, str | None]:
    return {
        table: _table_digest(connection, table)
        for table in (
            "learner_profiles",
            "learning_sessions",
            "state_events",
            "response_attempts",
            "scoring_results",
            "human_review_queue",
        )
    }


def _existing_keyed_rows(connection: sqlite3.Connection, table: str) -> dict[str, tuple[Any, ...]]:
    if not _table_exists(connection, table):
        return {}
    rows = connection.execute(f"SELECT * FROM {table}").fetchall()
    return {str(row[0]): tuple(row) for row in rows}


def _assert_existing_rows_preserved(
    connection: sqlite3.Connection,
    table: str,
    before: Mapping[str, tuple[Any, ...]],
) -> None:
    after = _existing_keyed_rows(connection, table)
    for key, row in before.items():
        if after.get(key) != row:
            raise ProductCutoverError(f"PREEXISTING_{table.upper()}_ROW_CHANGED:{key}")


def _product_database_preflight(database: Path) -> None:
    if not Path(database).is_file():
        raise ProductCutoverError("PRODUCT_LEARNER_DATABASE_MISSING")
    with closing(sqlite3.connect(database)) as connection:
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        if metadata.get("validation_status") != m3.STATUS:
            raise ProductCutoverError("M3_DATABASE_STATUS_INVALID")
        rows = connection.execute(
            "SELECT lesson_id,skill,level,payload_access_allowed FROM lesson_catalog WHERE lesson_id IN (?,?,?)",
            tuple(qb02.UNIT01_LESSONS.values()),
        ).fetchall()
        if len(rows) != 3:
            raise ProductCutoverError("UNIT01_LESSON_CATALOG_INCOMPLETE")
        for lesson_id, skill, level, allowed in rows:
            expected_skill = qb02.LESSON_TO_SKILL[str(lesson_id)]
            if str(skill) != expected_skill or str(level) != "A1" or int(allowed) != 1:
                raise ProductCutoverError(f"UNIT01_LESSON_CONTRACT_INVALID:{lesson_id}")


def cutover_status(database: Path) -> dict[str, Any]:
    path = Path(database)
    if not path.is_file():
        return {"active": False, "reason": "DATABASE_MISSING"}
    with closing(sqlite3.connect(path)) as connection:
        connection.row_factory = sqlite3.Row
        if not _table_exists(connection, CUTOVER_TABLE):
            return {"active": False, "reason": "CUTOVER_METADATA_MISSING"}
        metadata = dict(connection.execute(f"SELECT key,value FROM {CUTOVER_TABLE}"))
        if metadata.get("validation_status") != PASS_STATUS:
            return {"active": False, "reason": "CUTOVER_STATUS_NOT_PASS", "metadata": metadata}
        counts = {
            "runtime_item_count": int(connection.execute("SELECT COUNT(*) FROM u01qb02_item_catalog").fetchone()[0]),
            "extension_item_count": int(connection.execute("SELECT COUNT(*) FROM razq01e_extension_items").fetchone()[0]),
            "blueprint_activity_count": int(connection.execute("SELECT COUNT(*) FROM u01qb13_blueprint_activities").fetchone()[0]),
            "form_count": int(connection.execute("SELECT COUNT(DISTINCT form_ordinal) FROM u01qb13_blueprint_activities").fetchone()[0]),
        }
    active = counts == {
        "runtime_item_count": EXPECTED_RUNTIME_ITEMS,
        "extension_item_count": EXPECTED_EXTENSION_ITEMS,
        "blueprint_activity_count": EXPECTED_BLUEPRINT_ACTIVITIES,
        "form_count": EXPECTED_FORMS,
    }
    return {
        "active": active,
        "reason": "PASS" if active else "CUTOVER_DENOMINATOR_DRIFT",
        "real62_artifact_sha256": metadata.get("real62_artifact_sha256"),
        "questionbank_revision": metadata.get("questionbank_revision"),
        "runtime_consumer": metadata.get("runtime_consumer"),
        **counts,
    }


def require_cutover(database: Path) -> dict[str, Any]:
    status = cutover_status(database)
    if status.get("active") is not True:
        raise ProductCutoverError(f"U01QB15_PRODUCTION_CONSUMER_NOT_ACTIVE:{status.get('reason')}")
    return status


def cutover_database(*, database: Path, real62_path: Path) -> dict[str, Any]:
    database = Path(database).resolve()
    real62_path = Path(real62_path).resolve(strict=True)
    _product_database_preflight(database)
    approved_content, artifact_sha, raw_file_sha = private_runner._real62_identity(real62_path)
    if artifact_sha != EXPECTED_REAL62_ARTIFACT_SHA256:
        raise ProductCutoverError(
            f"REAL62_ARTIFACT_SHA256_INVALID:{artifact_sha}:{EXPECTED_REAL62_ARTIFACT_SHA256}"
        )

    existing_status = cutover_status(database)
    if existing_status.get("active") is True:
        if existing_status.get("real62_artifact_sha256") != artifact_sha:
            raise ProductCutoverError("ACTIVE_CUTOVER_REAL62_IDENTITY_DRIFT")
        return {
            "status": PASS_STATUS,
            "idempotent_reuse": True,
            "real62_artifact_sha256": artifact_sha,
            "real62_file_sha256": raw_file_sha,
            "cutover": existing_status,
            "learner_owned_state_unchanged": True,
            "preexisting_product_rows_unchanged": True,
            "next_short_step": NEXT_SHORT_STEP,
        }

    with closing(sqlite3.connect(database)) as connection:
        learner_before = _learner_owned_snapshot(connection)
        lesson_assets_before = _existing_keyed_rows(connection, "lesson_assets")
        response_contracts_before = _existing_keyed_rows(connection, "response_contracts")

    qb02_result = qb02.Unit01ApprovedVariantSessionRuntime(database).initialize()
    candidate = razq01e.build_candidate(approved_content)
    approved_extension = razq01e.admit_candidate(candidate)
    extension = razq01e.materialize_runtime(database, approved_extension)
    counts = (
        int(qb02_result["registered_item_count"]),
        int(extension["extension_item_count"]),
        int(extension["combined_runtime_item_count"]),
    )
    if counts != (288, EXPECTED_EXTENSION_ITEMS, EXPECTED_RUNTIME_ITEMS):
        raise ProductCutoverError(f"FRESH474_DENOMINATOR_INVALID:{counts}")

    matching.install()
    with tempfile.TemporaryDirectory(prefix="a1fs_u01qb15_cutover_") as temporary:
        paths = private_runner._paths(Path(temporary))
        migration, _approved_u15 = private_runner._migrate_u01qb15(database, paths)
        rotation, allocation = private_runner._materialize_r2_and_allocation(database, paths, migration)
        blueprint_candidate = u13.build_candidate(rotation, allocation)
        blueprint_approved = u13.admit_candidate(blueprint_candidate)
        installed = u13.install_blueprint(database, blueprint_approved)

    if installed.get("runtime_item_count") != EXPECTED_RUNTIME_ITEMS:
        raise ProductCutoverError("U01QB13_RUNTIME_DENOMINATOR_INVALID")

    with closing(sqlite3.connect(database)) as connection:
        connection.row_factory = sqlite3.Row
        _assert_existing_rows_preserved(connection, "lesson_assets", lesson_assets_before)
        _assert_existing_rows_preserved(connection, "response_contracts", response_contracts_before)
        learner_after = _learner_owned_snapshot(connection)
        if learner_after != learner_before:
            raise ProductCutoverError("LEARNER_OWNED_STATE_CHANGED_DURING_CUTOVER")
        connection.executescript(CUTOVER_SQL)
        metadata = {
            "task_id": TASK_ID,
            "validation_status": PASS_STATUS,
            "real62_artifact_sha256": artifact_sha,
            "questionbank_revision": "U01QB15-R1",
            "runtime_consumer": u13.TASK_ID,
            "runtime_item_count": str(EXPECTED_RUNTIME_ITEMS),
            "extension_item_count": str(EXPECTED_EXTENSION_ITEMS),
            "form_count": str(EXPECTED_FORMS),
            "blueprint_activity_count": str(EXPECTED_BLUEPRINT_ACTIVITIES),
            "static_product_asset_denominator_unchanged": "true",
            "learner_owned_state_unchanged": "true",
            "unit02_to_unit24_modified": "false",
            "a2_unlocked": "false",
            "next_short_step": NEXT_SHORT_STEP,
        }
        connection.executemany(
            f"INSERT OR REPLACE INTO {CUTOVER_TABLE}(key,value) VALUES(?,?)",
            metadata.items(),
        )
        connection.commit()

    status = require_cutover(database)
    return {
        "status": PASS_STATUS,
        "idempotent_reuse": False,
        "real62_artifact_sha256": artifact_sha,
        "real62_file_sha256": raw_file_sha,
        "cutover": status,
        "learner_owned_state_unchanged": True,
        "preexisting_product_rows_unchanged": True,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
        "next_short_step": NEXT_SHORT_STEP,
    }


def _session_version(database: Path, session_id: str) -> int:
    with closing(sqlite3.connect(database)) as connection:
        row = connection.execute(
            "SELECT session_version FROM learning_sessions WHERE session_id=?", (session_id,)
        ).fetchone()
    if not row:
        raise ProductCutoverError("SESSION_NOT_FOUND")
    return int(row[0])


def _response_mode(item: Mapping[str, Any]) -> str:
    if item.get("capture_enabled") is not True:
        return "practice_only"
    if item.get("options"):
        return "select_one"
    if str(item.get("task_angle") or "") == "WORD_ORDER":
        return "ordered_tokens"
    return "short_text"


def learner_form_payload(database: Path, component: Mapping[str, Any]) -> dict[str, Any]:
    items = []
    for source in component.get("items", []):
        row = dict(source)
        row["response_mode"] = _response_mode(row)
        items.append(row)
    return {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "session_id": str(component["session_id"]),
        "session_version": _session_version(database, str(component["session_id"])),
        "form_id": str(component["form_id"]),
        "form_ordinal": int(component["form_ordinal"]),
        "skill": str(component["skill"]),
        "blueprint_activity_count": int(component["blueprint_activity_count"]),
        "runtime_session_item_count": int(component["runtime_session_item_count"]),
        "support_filler_count": int(component["support_filler_count"]),
        "support_fillers_exposed_to_learner": False,
        "items": items,
        "questionbank_revision": "U01QB15-R1",
        "runtime_item_count": EXPECTED_RUNTIME_ITEMS,
        "next_short_step": NEXT_SHORT_STEP,
    }


def u01qb15_completion_readiness(database: Path, session_id: str) -> dict[str, Any]:
    database = Path(database)
    with closing(sqlite3.connect(database)) as connection:
        connection.row_factory = sqlite3.Row
        session = connection.execute(
            "SELECT session_id,lesson_id,skill,session_state,session_version FROM learning_sessions WHERE session_id=?",
            (session_id,),
        ).fetchone()
        if not session:
            raise ProductCutoverError("SESSION_NOT_FOUND")
        bindings = connection.execute(
            "SELECT item_id,item_position FROM u01qb13_session_bindings WHERE session_id=? ORDER BY item_position",
            (session_id,),
        ).fetchall()
        if not bindings:
            raise ProductCutoverError("U01QB15_SESSION_BINDINGS_NOT_FOUND")
        item_ids = [str(row["item_id"]) for row in bindings]
        exposed = {
            str(row[0])
            for row in connection.execute(
                "SELECT item_id FROM u01qb02_item_exposures WHERE session_id=?", (session_id,)
            ).fetchall()
        }
        skill = str(session["skill"]).upper()
        if skill == "SPEAKING":
            assets = [
                {
                    "item_index": index,
                    "item_id": item_id,
                    "completion_state": "EXPOSED" if item_id in exposed else "NOT_EXPOSED",
                }
                for index, item_id in enumerate(item_ids, 1)
            ]
            completed = sum(row["completion_state"] == "EXPOSED" for row in assets)
            return {
                "session_id": session_id,
                "lesson_id": str(session["lesson_id"]),
                "skill": skill,
                "session_state": str(session["session_state"]),
                "session_version": int(session["session_version"]),
                "gate_mode": "U01QB15_BLUEPRINT_PRACTICE_EXPOSURE",
                "required_response_count": 0,
                "required_exposure_count": len(item_ids),
                "completed_exposure_count": completed,
                "completion_allowed": completed == len(item_ids),
                "assets": assets,
                "mastery_claimed": False,
            }
        placeholders = ",".join("?" for _ in item_ids)
        latest_rows = connection.execute(
            f"""SELECT c.item_id,a.attempt_sequence,s.outcome
                FROM response_attempts a
                JOIN scoring_results s USING(attempt_id)
                JOIN u01qb02_item_catalog c ON c.asset_key=a.asset_key
                WHERE a.session_id=? AND c.item_id IN ({placeholders})
                ORDER BY c.item_id,a.attempt_sequence DESC""",
            (session_id, *item_ids),
        ).fetchall()
        latest: dict[str, sqlite3.Row] = {}
        for row in latest_rows:
            latest.setdefault(str(row["item_id"]), row)
        attempt_counts = {
            str(row["item_id"]): int(row["count"])
            for row in connection.execute(
                f"""SELECT c.item_id,COUNT(*) AS count
                    FROM response_attempts a
                    JOIN u01qb02_item_catalog c ON c.asset_key=a.asset_key
                    WHERE a.session_id=? AND c.item_id IN ({placeholders})
                    GROUP BY c.item_id""",
                (session_id, *item_ids),
            ).fetchall()
        }
    passed = pending = retry = attempted = not_attempted = 0
    assets = []
    for index, item_id in enumerate(item_ids, 1):
        row = latest.get(item_id)
        outcome = None if row is None else str(row["outcome"])
        if row is None:
            state = "NOT_ATTEMPTED"
            not_attempted += 1
        elif outcome in {"AUTO_PASS", "HUMAN_APPROVE"}:
            state = "PASSED"
            attempted += 1
            passed += 1
        elif outcome in {"AUTO_FAIL", "HUMAN_REJECT"}:
            state = "RETRY_REQUIRED"
            attempted += 1
            retry += 1
        elif outcome in {"PENDING_HUMAN_REVIEW", "HUMAN_DEFER"}:
            state = "PENDING_HUMAN_REVIEW"
            attempted += 1
            pending += 1
        else:
            raise ProductCutoverError(f"UNSUPPORTED_SCORING_OUTCOME:{outcome}")
        assets.append(
            {
                "item_index": index,
                "item_id": item_id,
                "attempt_count": attempt_counts.get(item_id, 0),
                "latest_outcome": outcome,
                "completion_state": state,
            }
        )
    return {
        "session_id": session_id,
        "skill": skill,
        "gate_mode": "U01QB15_BLUEPRINT_LATEST_ATTEMPT_PASS_OR_HUMAN_APPROVAL",
        "required_response_count": len(item_ids),
        "attempted_response_count": attempted,
        "passed_response_count": passed,
        "not_attempted_count": not_attempted,
        "retry_required_count": retry,
        "pending_human_review_count": pending,
        "completion_allowed": passed == len(item_ids),
        "assets": assets,
        "mastery_claimed": False,
    }


def _is_u01qb15_session(database: Path, session_id: str) -> bool:
    with closing(sqlite3.connect(database)) as connection:
        if not _table_exists(connection, "u01qb13_session_bindings"):
            return False
        return connection.execute(
            "SELECT 1 FROM u01qb13_session_bindings WHERE session_id=? LIMIT 1", (session_id,)
        ).fetchone() is not None


class U01QB15ProductApplication(core.V12Application):
    """Existing V1.2.1 app plus the admitted U01QB15 form consumer."""

    def bootstrap(self) -> dict[str, Any]:
        value = super().bootstrap()
        status = cutover_status(self.database_path)
        value.setdefault("learner_product_semantics", {}).update(
            {
                "unit01_u01qb15_consumer_cutover_active": status.get("active") is True,
                "unit01_questionbank_revision": "U01QB15-R1" if status.get("active") else None,
                "unit01_questionbank_runtime_item_count": status.get("runtime_item_count", 0),
                "unit01_questionbank_form_count": status.get("form_count", 0),
                "unit01_questionbank_api": "/api/u01qb15",
            }
        )
        return value

    def u01qb15_status(self) -> dict[str, Any]:
        return {"task_id": TASK_ID, "validation_status": PASS_STATUS, **require_cutover(self.database_path)}

    def start_u01qb15_form(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        require_cutover(self.database_path)
        skill = str(payload.get("skill") or "").upper()
        if skill not in qb02.UNIT01_LESSONS:
            raise ProductCutoverError(f"UNIT01_SKILL_INVALID:{skill}")
        form_ordinal = int(payload.get("form_ordinal") or 0)
        if form_ordinal < 1 or form_ordinal > EXPECTED_FORMS:
            raise ProductCutoverError("FORM_ORDINAL_INVALID")
        session_id = str(payload.get("session_id") or f"U01QB15:{skill}:{uuid.uuid4().hex}")
        session = super().start_session(
            {
                "lesson_id": qb02.UNIT01_LESSONS[skill],
                "session_id": session_id,
                **({"at": str(payload["at"])} if payload.get("at") else {}),
            }
        )
        matching.install()
        component = u13.assemble_form_component(
            self.database_path,
            learner_id=self.default_learner_id,
            session_id=str(session["session_id"]),
            form_ordinal=form_ordinal,
        )
        result = learner_form_payload(self.database_path, component)
        result["completion_gate"] = u01qb15_completion_readiness(self.database_path, session_id)
        return result

    def active_u01qb15_form(self) -> dict[str, Any]:
        require_cutover(self.database_path)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """SELECT DISTINCT s.session_id
                   FROM learning_sessions s
                   JOIN u01qb13_session_bindings b USING(session_id)
                   WHERE s.learner_id=? AND s.session_state='ACTIVE'
                   ORDER BY s.rowid DESC LIMIT 1""",
                (self.default_learner_id,),
            ).fetchone()
            if not row:
                return {"active": False}
            session_id = str(row["session_id"])
            component = u13.form_component_payload(connection, session_id=session_id)
        return {
            "active": True,
            "form": learner_form_payload(self.database_path, component),
            "completion_gate": u01qb15_completion_readiness(self.database_path, session_id),
        }

    def record_u01qb15_exposure(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        require_cutover(self.database_path)
        session_id = str(payload.get("session_id") or "")
        item_id = str(payload.get("item_id") or "")
        if not session_id or not item_id:
            raise ProductCutoverError("SESSION_AND_ITEM_REQUIRED")
        runtime = qb02.Unit01ApprovedVariantSessionRuntime(self.database_path)
        result = runtime.record_item_exposure(
            session_id=session_id,
            item_id=item_id,
            expected_session_version=int(payload.get("expected_session_version")),
        )
        result["completion_gate"] = u01qb15_completion_readiness(self.database_path, session_id)
        return result

    def submit_u01qb15_response(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        require_cutover(self.database_path)
        session_id = str(payload.get("session_id") or "")
        item_id = str(payload.get("item_id") or "")
        if not session_id or not item_id:
            raise ProductCutoverError("SESSION_AND_ITEM_REQUIRED")
        runtime = qb02.Unit01ApprovedVariantSessionRuntime(self.database_path)
        result = runtime.capture_response(
            learner_id=self.default_learner_id,
            session_id=session_id,
            item_id=item_id,
            response=payload.get("response"),
            expected_session_version=int(payload.get("expected_session_version")),
        )
        return {
            **result,
            "session_version": _session_version(self.database_path, session_id),
            "completion_gate": u01qb15_completion_readiness(self.database_path, session_id),
        }

    def completion_readiness(self, session_id: str) -> dict[str, Any]:
        if _is_u01qb15_session(self.database_path, str(session_id)):
            return u01qb15_completion_readiness(self.database_path, str(session_id))
        return super().completion_readiness(session_id)


class U01QB15ProductHandler(core.V12Handler):
    @property
    def u01qb15_app(self) -> U01QB15ProductApplication:
        return self.server.app  # type: ignore[attr-defined]

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path not in {"/api/u01qb15/status", "/api/u01qb15/form/active"}:
            super().do_GET()
            return
        if not self._transport_valid():
            return
        claims = self._claims()
        if claims is None:
            self._json(401, {"error": "authentication_required"})
            return
        try:
            value = (
                self.u01qb15_app.u01qb15_status()
                if path.endswith("/status")
                else self.u01qb15_app.active_u01qb15_form()
            )
            self._json(200, value)
        except (ProductCutoverError, ValueError, sqlite3.Error) as exc:
            self._json(409, {"error": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        routes = {
            "/api/u01qb15/form/start": self.u01qb15_app.start_u01qb15_form,
            "/api/u01qb15/exposure": self.u01qb15_app.record_u01qb15_exposure,
            "/api/u01qb15/response": self.u01qb15_app.submit_u01qb15_response,
        }
        action = routes.get(path)
        if action is None:
            super().do_POST()
            return
        if not self._transport_valid() or not self._origin_valid():
            return
        claims = self._claims()
        if claims is None:
            self._json(401, {"error": "authentication_required"})
            return
        if not self._csrf_valid(claims):
            return
        try:
            value = action(self._read_json_body())
            self._json(200, value)
        except (ProductCutoverError, qb02.SessionRuntimeError, u13.BlueprintIntegrationError, ValueError, sqlite3.Error, json.JSONDecodeError) as exc:
            self._json(409, {"error": str(exc)})


class U01QB15ProductServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], app: U01QB15ProductApplication, static_root: Path, config: Any):
        if not core.s17.s16.s15.s11._is_loopback(address[0]):
            raise ProductCutoverError(f"NON_LOOPBACK_HOST_FORBIDDEN:{address[0]}")
        self.app = app
        self.static_root = Path(static_root)
        self.secure_static_root = Path(static_root)
        self.config = config
        ThreadingHTTPServer.__init__(self, address, U01QB15ProductHandler)
        self.config.bind_local_port(int(self.server_address[1]))


def _app() -> U01QB15ProductApplication:
    manifest, bundles, sequence, registry, state = base._load_runtime()
    require_cutover(state["database"])
    matching.install()
    return U01QB15ProductApplication(
        database_path=state["database"],
        bundles=bundles,
        sequence_by_grammar=sequence,
        graph_path=base._resolve_product(str(manifest["graph_path"])),
        state_root=state["learner_state"],
        default_learner_id=base.DEFAULT_LEARNER_ID,
        target_registry=registry,
    )


def serve(*, host: str, port: int) -> None:
    if not core.s17.s16.s15.s11._is_loopback(host):
        raise ProductCutoverError(f"NON_LOOPBACK_HOST_FORBIDDEN:{host}")
    manifest, _bundles, _sequence, _registry, state = base._load_runtime()
    require_cutover(state["database"])
    config = core.s17.s16.s15.s13.PersistentBoundaryConfig.from_environment(
        host=host,
        port=port,
        revocation_db_path=state["auth"],
    )
    server = U01QB15ProductServer(
        (host, port),
        _app(),
        base._resolve_product(str(manifest["secure_static_root"])),
        config,
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()


def start(*, host: str, port: int) -> dict[str, Any]:
    state = base._ensure_state()
    require_cutover(state["database"])
    base.MODULE = MODULE
    return base.start(host=host, port=port)


def stop(*, port: int) -> dict[str, Any]:
    return base.stop(port=port)


def status(*, port: int) -> dict[str, Any]:
    result = base.status(port=port)
    result["u01qb15_consumer"] = cutover_status(base._ensure_state()["database"])
    return result


def readback() -> dict[str, Any]:
    result = base.readback()
    result.update(
        {
            "task_id": TASK_ID,
            "serve_module": MODULE,
            "u01qb15_consumer": cutover_status(base._ensure_state()["database"]),
            "next_short_step": NEXT_SHORT_STEP,
        }
    )
    return result


def cutover(*, real62_path: Path) -> dict[str, Any]:
    state = base._ensure_state()
    pid_path = state["pid"]
    if pid_path.is_file():
        try:
            pid = int(pid_path.read_text(encoding="ascii").strip())
        except ValueError:
            pid = 0
        if pid and base._pid_alive(pid):
            raise ProductCutoverError(f"STOP_PRODUCT_BEFORE_CUTOVER_PID={pid}")
    return cutover_database(database=state["database"], real62_path=real62_path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    cut = commands.add_parser("cutover")
    cut.add_argument("--real62", type=Path, required=True)
    start_cmd = commands.add_parser("start")
    start_cmd.add_argument("--host", default=base.DEFAULT_HOST)
    start_cmd.add_argument("--port", type=int, default=base.DEFAULT_PORT)
    serve_cmd = commands.add_parser("serve")
    serve_cmd.add_argument("--host", default=base.DEFAULT_HOST)
    serve_cmd.add_argument("--port", type=int, default=base.DEFAULT_PORT)
    stop_cmd = commands.add_parser("stop")
    stop_cmd.add_argument("--port", type=int, default=base.DEFAULT_PORT)
    status_cmd = commands.add_parser("status")
    status_cmd.add_argument("--port", type=int, default=base.DEFAULT_PORT)
    commands.add_parser("readback")
    args = parser.parse_args(argv)
    try:
        if args.command == "cutover":
            print(json.dumps(cutover(real62_path=args.real62), ensure_ascii=False, indent=2))
        elif args.command == "serve":
            serve(host=args.host, port=args.port)
            return 0
        elif args.command == "start":
            print(json.dumps(start(host=args.host, port=args.port), ensure_ascii=False, indent=2))
        elif args.command == "stop":
            print(json.dumps(stop(port=args.port), ensure_ascii=False, indent=2))
        elif args.command == "status":
            print(json.dumps(status(port=args.port), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(readback(), ensure_ascii=False, indent=2))
        return 0
    except (
        ProductCutoverError,
        qb02.SessionRuntimeError,
        u13.BlueprintIntegrationError,
        private_runner.ActualReal62AcceptanceError,
        base.PullToRunError,
        sqlite3.Error,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"FAIL:{exc}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
