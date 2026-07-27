#!/usr/bin/env python3
"""Canonical M7/M8 integration core for A1FS Online V1 S16."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_online_v1_s09_twentyfour_unit_production_population as s09  # noqa: E402
from ulga.builders import build_a1fs_online_v1_s15_reading_writing_scored_journey_completion_gate as s15  # noqa: E402
from ulga.builders import build_a1fs_v1_m7_mastery_error_remediation_reassessment as m7  # noqa: E402
from ulga.builders import build_a1fs_v1_m8_review_scheduling_retention_spaced_practice as m8  # noqa: E402
from ulga.validators.validate_a1fs_v1_m7_mastery_error_remediation_reassessment import validate as validate_m7  # noqa: E402
from ulga.validators.validate_a1fs_v1_m8_review_scheduling_retention_spaced_practice import validate as validate_m8  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Builds a runtime-only mastery graph projection from the existing CP01 24-unit authority and the existing "
    "S15 lesson/asset identities, then connects the existing M7 mastery/remediation/reassessment and M8 spaced-review "
    "engines. It creates no curriculum, learner item, answer authority, scoring engine, mastery engine, dashboard, "
    "audio, A2 payload access, Cloudflare route, or parallel learner-state system."
)

PROGRAM_ID = "A1FS-ONLINE-V1"
TASK_ID = "A1FS-ONLINE-V1-S16_CanonicalMasteryRemediationReassessmentReviewIntegration_NoAudio"
SCHEMA_VERSION = "a1fs.online.v1.s16.canonical_mastery_remediation_reassessment_review.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_S16_CANONICAL_LEARNING_INTEGRATION_READY"
PRODUCT_STATUS = "LOCALHOST_NONAUDIO_CANONICAL_LEARNING_INTEGRATION_READY_NOT_DASHBOARD_COMPLETE"
RELEASE_PROFILE = "ONLINE_V1_AUDIO_DEFERRED"
NEXT_SHORT_STEP = "A1FS-ONLINE-V1-S17_LearnerParentTeacherDashboardAndHumanReview_NoAudio"
DEFAULT_PORT = 8765
CANARY_LEARNER_ID = s15.CANARY_LEARNER_ID
CANARY_REMEDIATION_SESSION_ID = "A1FS_ONLINE_V1_S16_SESSION:OPEN_REMEDIATION"
CANARY_CREATED_AT = "2026-01-16T00:00:00Z"
CANARY_REVIEW_AS_OF = "2026-01-17T00:00:00Z"

REQUIRED_UNIT_COUNT = 24
REQUIRED_SCORED_LESSON_COUNT = 48
REQUIRED_MASTERY_NODE_COUNT = 72
SKILLS = ("READING", "WRITING")
PASS_OUTCOMES = m7.PASS_OUTCOMES

FORBIDDEN_SAFE_KEYS = set(s15.s14.FORBIDDEN_SAFE_KEYS) | {
    "mastered_node_ids", "missing_mastery_node_ids", "node_id", "node_ids",
    "lesson_ids", "asset_keys", "source_attempt_ids", "attempt_id",
}


class CanonicalLearningError(ValueError):
    """Fail-closed S16 integration error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return s15.digest(value)


def file_digest(path: Path) -> str:
    return s15.file_digest(path)


def read_json(path: Path, code: str) -> dict[str, Any]:
    return s15.read_json(path, code)


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    s15.write_json(path, value, private=private)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_scan(value: Any) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in {item.casefold() for item in FORBIDDEN_SAFE_KEYS}:
                    raise CanonicalLearningError(f"private_content_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(value)


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=5000")
    return connection


def _verify_cp01(path: Path) -> tuple[dict[str, Any], dict[str, Mapping[str, Any]]]:
    artifact = read_json(path, "cp01")
    try:
        units = s09._verify_cp01_with_resolved_prerequisites(artifact)
    except (s09.PopulationError, KeyError, TypeError, ValueError) as exc:
        raise CanonicalLearningError(f"cp01_contract_invalid:{exc}") from exc
    if len(units) != REQUIRED_UNIT_COUNT:
        raise CanonicalLearningError("cp01_unit_denominator_invalid")
    return artifact, units


def _source(
    *, s15_receipt_path: Path, cp01_path: Path,
) -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Mapping[str, Any]], Path, Path,
    dict[str, dict[str, Any]], dict[str, int], Path, Path,
]:
    receipt, production_database, auth_state, bundles, sequence, secure_static = s15._source(s15_receipt_path)
    cp01, units = _verify_cp01(cp01_path)
    outputs = receipt.get("runtime_outputs", {})
    acceptance_database = Path(str(outputs.get("acceptance_database_path") or "")).resolve()
    if not acceptance_database.is_file():
        raise CanonicalLearningError("s15_acceptance_database_missing")
    if len(bundles) != 72 or len(sequence) != REQUIRED_UNIT_COUNT:
        raise CanonicalLearningError("s15_runtime_denominator_invalid")
    return (
        receipt, cp01, units, production_database, auth_state, bundles, sequence,
        secure_static, acceptance_database,
    )


def _lesson_rows(database: Path) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    with _connect(database) as connection:
        lessons = {
            str(row["lesson_id"]): dict(row)
            for row in connection.execute(
                """SELECT lesson_id,skill,level FROM lesson_catalog
                   WHERE skill IN('READING','WRITING') ORDER BY lesson_id"""
            ).fetchall()
        }
        assets: dict[str, list[dict[str, Any]]] = {}
        for row in connection.execute(
            """SELECT lesson_id,asset_id,asset_key,role FROM lesson_assets
               WHERE lesson_id IN (SELECT lesson_id FROM lesson_catalog WHERE skill IN('READING','WRITING'))
               ORDER BY lesson_id,asset_key"""
        ).fetchall():
            assets.setdefault(str(row["lesson_id"]), []).append(dict(row))
    return lessons, assets


def build_runtime_mastery_graph(
    *,
    cp01_artifact: Mapping[str, Any],
    units: Mapping[str, Mapping[str, Any]],
    database: Path,
    sequence: Mapping[str, int],
) -> dict[str, Any]:
    lessons, assets_by_lesson = _lesson_rows(database)
    if len(lessons) != REQUIRED_SCORED_LESSON_COUNT:
        raise CanonicalLearningError(f"scored_lesson_denominator_invalid:{len(lessons)}")
    learning_to_grammar = {
        str(unit["learning_unit_id"]): str(grammar_id)
        for grammar_id, unit in units.items()
    }
    ordered = sorted(units.items(), key=lambda row: int(row[1]["sequence_index"]))
    if [int(row[1]["sequence_index"]) for row in ordered] != list(range(1, 25)):
        raise CanonicalLearningError("canonical_unit_sequence_invalid")
    if {grammar_id for grammar_id, _ in ordered} != set(sequence):
        raise CanonicalLearningError("cp01_s15_grammar_identity_mismatch")

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    coverage: list[dict[str, Any]] = []
    required: list[str] = []
    lesson_count_by_level = {"A1": 0, "A1+": 0, "A2": 0}
    gate_id = "GATE:A1FS:ONLINE_V1_S16:A2_LOCK"

    for grammar_id, unit in ordered:
        grammar_id = str(grammar_id)
        grammar_node = f"CAPABILITY:GRAMMAR:{grammar_id}"
        grammar_level = "A1+" if str(unit.get("internal_stage") or "").upper() in {"A1+", "A1_PLUS", "A1_PLUS_EXTENSION"} else "A1"
        nodes.append({
            "node_id": grammar_node,
            "node_type": "CAPABILITY",
            "skill": "READING_WRITING",
            "level": grammar_level,
            "source_ref": grammar_id,
            "mastery_required_before_a2": True,
            "runtime_projection_only": True,
        })
        required.append(grammar_node)
        unit_lesson_ids: list[str] = []
        unit_asset_ids: list[str] = []
        unit_roles: list[str] = []
        for skill in SKILLS:
            lesson_id = f"A1FS_ONLINE_V1:{grammar_id}:{skill}"
            row = lessons.get(lesson_id)
            if not row or str(row["skill"]) != skill:
                raise CanonicalLearningError(f"runtime_lesson_missing:{lesson_id}")
            lesson_assets = assets_by_lesson.get(lesson_id, [])
            if len(lesson_assets) != 4:
                raise CanonicalLearningError(f"runtime_lesson_asset_denominator_invalid:{lesson_id}")
            lesson_node = f"LESSON:{skill}:{lesson_id}"
            level = str(row["level"])
            if level not in lesson_count_by_level:
                raise CanonicalLearningError(f"runtime_lesson_level_invalid:{lesson_id}:{level}")
            lesson_count_by_level[level] += 1
            nodes.append({
                "node_id": lesson_node,
                "node_type": "LESSON",
                "skill": skill,
                "level": level,
                "source_ref": lesson_id,
                "mastery_required_before_a2": True,
                "runtime_projection_only": True,
            })
            required.append(lesson_node)
            unit_lesson_ids.append(lesson_id)
            unit_asset_ids.extend(str(asset["asset_id"]) for asset in lesson_assets)
            unit_roles.extend(str(asset["role"]) for asset in lesson_assets)
            edges.append({"from_node_id": grammar_node, "to_node_id": lesson_node, "edge_type": "TAUGHT_BY"})
        coverage.append({
            "node_id": grammar_node,
            "skill": "READING_WRITING",
            "source_ref": grammar_id,
            "coverage_class": "MASTERY",
            "levels": [grammar_level],
            "lesson_ids": sorted(unit_lesson_ids),
            "asset_body_ids": sorted(unit_asset_ids),
            "roles": sorted(set(unit_roles)),
            "coverage_status": "COVERED",
        })
        for prerequisite_learning_id in unit.get("prerequisite_unit_ids", []):
            prerequisite_grammar = learning_to_grammar.get(str(prerequisite_learning_id))
            if prerequisite_grammar is None:
                raise CanonicalLearningError(f"cp01_prerequisite_learning_identity_unknown:{prerequisite_learning_id}")
            edges.append({
                "from_node_id": f"CAPABILITY:GRAMMAR:{prerequisite_grammar}",
                "to_node_id": grammar_node,
                "edge_type": "PREREQUISITE_OF",
            })

    if len(required) != REQUIRED_MASTERY_NODE_COUNT or len(set(required)) != REQUIRED_MASTERY_NODE_COUNT:
        raise CanonicalLearningError("required_mastery_node_denominator_invalid")
    nodes.append({
        "node_id": gate_id,
        "node_type": "A2_LOCK",
        "skill": "FOUR_SKILL",
        "level": "A2",
        "source_ref": "A2_ENTRY_DEFERRED",
        "mastery_required_before_a2": False,
        "runtime_projection_only": True,
    })
    edges.extend(
        {"from_node_id": node_id, "to_node_id": gate_id, "edge_type": "UNLOCK_REQUIRES"}
        for node_id in required
    )
    graph = {
        "task_id": "A1FS-V1-M1_A1A1PlusPrerequisiteGraphAndCoverage",
        "schema_version": "a1fs.v1.m1.prerequisite_graph_and_coverage.runtime_projection.v1",
        "validation_status": m7.GRAPH_STATUS,
        "source_baseline_sha256": digest(cp01_artifact),
        "projection_identity": {
            "task_id": TASK_ID,
            "source_authority": s09.s02.CP01_TASK_ID if hasattr(s09.s02, "CP01_TASK_ID") else "A1FS-V1-CP01_Existing24UnitCurriculumContractAndContentBackfill",
            "source_unit_count": REQUIRED_UNIT_COUNT,
            "source_s15_scored_lesson_count": REQUIRED_SCORED_LESSON_COUNT,
            "new_curriculum_created": False,
            "runtime_projection_only": True,
        },
        "nodes": nodes,
        "edges": edges,
        "coverage": coverage,
        "counts": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "coverage_record_count": len(coverage),
            "lesson_count": REQUIRED_SCORED_LESSON_COUNT,
            "lesson_count_by_level": lesson_count_by_level,
            "required_mastery_node_count": REQUIRED_MASTERY_NODE_COUNT,
            "a2_handoff_lesson_count": 0,
            "uncovered_required_node_count": 0,
        },
        "a2_lock_contract": {
            "gate_node_id": gate_id,
            "state": "LOCKED_BY_DESIGN",
            "required_mastery_node_ids": sorted(required),
            "a2_handoff_lesson_node_ids": [],
            "unlock_rule": "ALL_REQUIRED_MASTERY_NODES_MUST_BE_MASTERED",
            "runtime_unlock_implemented": False,
        },
        "claim_boundaries": {
            "source_packages_committed": False,
            "asset_body_content_modified": False,
            "learner_release_approved": False,
            "mastery_claimed": False,
            "a2_unlocked": False,
            "runtime_planner_implemented": False,
            "human_pilot_claimed": False,
            "listening_audio_complete": False,
        },
        "errors": [],
        "next_short_step": m7.TASK_ID,
    }
    return graph


def _latest_learning_projection(database: Path, learner_id: str) -> dict[str, Any]:
    with _connect(database) as connection:
        mastery_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='mastery_snapshots'"
        ).fetchone()
        if not mastery_exists:
            return {
                "evaluation_state": "NOT_EVALUATED",
                "required_mastery_node_count": REQUIRED_MASTERY_NODE_COUNT,
                "mastered_required_count": 0,
                "missing_mastery_count": REQUIRED_MASTERY_NODE_COUNT,
                "open_remediation_count": 0,
                "pending_reassessment_count": 0,
                "due_review_count": 0,
                "overdue_review_count": 0,
                "retained_required_count": 0,
                "retention_confirmed": False,
                "a2_unlocked": False,
            }
        row = connection.execute(
            """SELECT snapshot_json FROM mastery_snapshots
               WHERE learner_id=? ORDER BY created_at DESC,rowid DESC LIMIT 1""",
            (learner_id,),
        ).fetchone()
        if not row:
            return {
                "evaluation_state": "NOT_EVALUATED",
                "required_mastery_node_count": REQUIRED_MASTERY_NODE_COUNT,
                "mastered_required_count": 0,
                "missing_mastery_count": REQUIRED_MASTERY_NODE_COUNT,
                "open_remediation_count": 0,
                "pending_reassessment_count": 0,
                "due_review_count": 0,
                "overdue_review_count": 0,
                "retained_required_count": 0,
                "retention_confirmed": False,
                "a2_unlocked": False,
            }
        snapshot = json.loads(str(row["snapshot_json"]))
        schedules = {"DUE": 0, "OVERDUE": 0}
        retained = 0
        if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='review_schedules'").fetchone():
            for state, total in connection.execute(
                """SELECT schedule_state,COUNT(*) FROM review_schedules
                   WHERE learner_id=? AND schedule_state IN('DUE','OVERDUE') GROUP BY schedule_state""",
                (learner_id,),
            ).fetchall():
                schedules[str(state)] = int(total)
        if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='retention_states'").fetchone():
            retained = int(connection.execute(
                "SELECT COUNT(*) FROM retention_states WHERE learner_id=? AND retention_state='RETAINED'",
                (learner_id,),
            ).fetchone()[0])
        remediation = snapshot.get("remediation_assignments", [])
        reassessment = snapshot.get("reassessment_queue", [])
        required_count = int(snapshot.get("required_mastery_node_count") or REQUIRED_MASTERY_NODE_COUNT)
        mastered_count = int(snapshot.get("mastered_required_count") or 0)
        return {
            "evaluation_state": "EVALUATED",
            "required_mastery_node_count": required_count,
            "mastered_required_count": mastered_count,
            "missing_mastery_count": required_count - mastered_count,
            "open_remediation_count": sum(row.get("assignment_state") == "OPEN" for row in remediation),
            "pending_reassessment_count": sum(row.get("queue_state") == "PENDING" for row in reassessment),
            "due_review_count": schedules["DUE"],
            "overdue_review_count": schedules["OVERDUE"],
            "retained_required_count": retained,
            "retention_confirmed": retained == required_count,
            "a2_unlocked": False,
        }


class CanonicalLearningApplication(s15.ScoredJourneyApplication):
    """S15 application that refreshes existing M7/M8 state after scored completion."""

    def __init__(
        self,
        *,
        database_path: Path,
        bundles: Mapping[str, Mapping[str, Any]],
        sequence_by_grammar: Mapping[str, int],
        graph_path: Path,
        state_root: Path,
        default_learner_id: str = s15.s14.s13.s11.s10.s09.s05.DEFAULT_LEARNER_ID,
    ):
        super().__init__(
            database_path=database_path,
            bundles=bundles,
            sequence_by_grammar=sequence_by_grammar,
            default_learner_id=default_learner_id,
        )
        self.graph_path = Path(graph_path)
        self.state_root = Path(state_root)

    def bootstrap(self) -> dict[str, Any]:
        value = super().bootstrap()
        value.update({
            "task_id": TASK_ID,
            "schema_version": SCHEMA_VERSION,
            "validation_status": PASS_STATUS,
            "product_status": PRODUCT_STATUS,
            "release_profile": RELEASE_PROFILE,
        })
        value["learner_product_semantics"].update({
            "canonical_m7_mastery_connected": True,
            "canonical_m7_remediation_connected": True,
            "canonical_m7_reassessment_connected": True,
            "canonical_m8_review_schedule_connected": True,
            "mastery_requires_two_resolved_passes_and_eighty_percent_pass_rate": True,
            "pending_human_review_blocks_mastery": True,
            "a2_unlock_enabled": False,
        })
        return value

    def refresh_canonical_learning(self, *, learner_id: str, at: str | None = None) -> dict[str, Any]:
        created_at = at or utc_now()
        learner_root = self.state_root / learner_id
        engine = m7.MasteryRemediationEngine(database_path=self.database_path, graph_path=self.graph_path)
        engine.initialize()
        m7_result = engine.build_snapshot(
            learner_id=learner_id,
            output_root=learner_root / "m7",
            created_at=created_at,
        )
        m7_path = Path(str(m7_result["snapshot_path"]))
        review = m8.ReviewRetentionEngine(
            database_path=self.database_path,
            graph_path=self.graph_path,
            m7_snapshot_path=m7_path,
        )
        review.initialize()
        m8_snapshot = review.build_schedule(learner_id=learner_id, as_of=created_at)
        with _connect(self.database_path) as connection:
            connection.executemany(
                "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
                {
                    "s16_task_id": TASK_ID,
                    "s16_schema_version": SCHEMA_VERSION,
                    "s16_validation_status": PASS_STATUS,
                    "mastery_write_enabled": "true",
                    "remediation_enabled": "true",
                    "reassessment_enabled": "true",
                    "review_scheduling_enabled": "true",
                    "a2_session_enabled": "false",
                    "audio_enabled": "false",
                }.items(),
            )
            connection.commit()
        return {
            "m7": {
                "mastered_required_count": int(m7_result["mastered_required_count"]),
                "missing_mastery_count": int(m7_result["missing_mastery_count"]),
                "open_remediation_count": int(m7_result["open_remediation_count"]),
                "pending_reassessment_count": int(m7_result["pending_reassessment_count"]),
                "a2_lock_state": str(m7_result["a2_lock_state"]),
            },
            "m8": {
                "scheduled_node_count": int(m8_snapshot.get("scheduled_node_count") or 0),
                "due_or_overdue_count": sum(
                    row.get("schedule_state") in {"DUE", "OVERDUE"}
                    for row in m8_snapshot.get("review_schedules", [])
                ),
                "retained_required_count": int(m8_snapshot.get("retained_required_count") or 0),
                "retention_confirmed": bool(m8_snapshot.get("retention_confirmed")),
            },
            "a2_unlocked": False,
        }

    def complete_session(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        completed = super().complete_session(payload)
        learner_id = str(completed["learner_id"])
        learning = self.refresh_canonical_learning(learner_id=learner_id)
        return {**completed, "canonical_learning_refresh": learning}

    def progress_readback(self) -> dict[str, Any]:
        value = super().progress_readback()
        value.update({
            "task_id": TASK_ID,
            "schema_version": SCHEMA_VERSION,
            "validation_status": PASS_STATUS,
            "product_status": PRODUCT_STATUS,
            "canonical_learning": _latest_learning_projection(self.database_path, self.default_learner_id),
        })
        value["semantic_boundaries"].update({
            "mastery_is_m7_policy_projection": True,
            "remediation_is_m7_assignment_projection": True,
            "reassessment_is_m7_queue_projection": True,
            "review_is_m8_spaced_schedule_projection": True,
            "a2_payload_access_granted": False,
            "a2_session_start_granted": False,
            "listening_is_audio_deferred": True,
            "speaking_is_practice_only": True,
        })
        return value


def _app(
    *,
    database: Path,
    bundles: Mapping[str, Mapping[str, Any]],
    sequence: Mapping[str, int],
    graph_path: Path,
    state_root: Path,
    default_learner_id: str = s15.s14.s13.s11.s10.s09.s05.DEFAULT_LEARNER_ID,
) -> CanonicalLearningApplication:
    return CanonicalLearningApplication(
        database_path=database,
        bundles=bundles,
        sequence_by_grammar=sequence,
        graph_path=graph_path,
        state_root=state_root,
        default_learner_id=default_learner_id,
    )


def _run_high_failure_completed_session(
    *,
    app: CanonicalLearningApplication,
    bundles: Mapping[str, Mapping[str, Any]],
    sequence: Mapping[str, int],
) -> dict[str, Any]:
    grammar_ids = [row[0] for row in sorted(sequence.items(), key=lambda row: row[1])]
    if len(grammar_ids) < 2:
        raise CanonicalLearningError("second_grammar_unit_missing")
    lesson_id = f"A1FS_ONLINE_V1:{grammar_ids[1]}:READING"
    contracts = s15._contracts_for_lesson(app.database_path, lesson_id)
    if len(contracts) != 4 or any(row.get("scoring_mode") == "FEATURE_RUBRIC" for row in contracts):
        raise CanonicalLearningError("remediation_canary_contract_invalid")
    session = app.start_session({
        "lesson_id": lesson_id,
        "session_id": CANARY_REMEDIATION_SESSION_ID,
        "at": "2026-01-15T01:00:00Z",
    })
    first = contracts[0]
    exposure = app.record_exposure({
        "session_id": CANARY_REMEDIATION_SESSION_ID,
        "asset_key": first["asset_key"],
        "expected_session_version": session["session_version"],
        "at": "2026-01-15T01:00:10Z",
    })
    current: Mapping[str, Any] = exposure
    for index in range(5):
        current = app.submit_response({
            "session_id": CANARY_REMEDIATION_SESSION_ID,
            "asset_key": first["asset_key"],
            "response": s15._wrong_response(first),
            "expected_session_version": current["session_version"],
            "attempt_id": f"A1FS_ONLINE_V1_S16_ATTEMPT:FAIL:{index + 1}",
            "submitted_at": f"2026-01-15T01:01:{index:02d}Z",
        })
    current = app.submit_response({
        "session_id": CANARY_REMEDIATION_SESSION_ID,
        "asset_key": first["asset_key"],
        "response": s15._passing_response(first),
        "expected_session_version": current["session_version"],
        "attempt_id": "A1FS_ONLINE_V1_S16_ATTEMPT:RECOVERY:1",
        "submitted_at": "2026-01-15T01:02:00Z",
    })
    for index, contract in enumerate(contracts[1:], start=2):
        exposed = app.record_exposure({
            "session_id": CANARY_REMEDIATION_SESSION_ID,
            "asset_key": contract["asset_key"],
            "expected_session_version": current["session_version"],
            "at": f"2026-01-15T01:02:{index:02d}Z",
        })
        current = app.submit_response({
            "session_id": CANARY_REMEDIATION_SESSION_ID,
            "asset_key": contract["asset_key"],
            "response": s15._passing_response(contract),
            "expected_session_version": exposed["session_version"],
            "attempt_id": f"A1FS_ONLINE_V1_S16_ATTEMPT:PASS:{index}",
            "submitted_at": f"2026-01-15T01:03:{index:02d}Z",
        })
    readiness = app.completion_readiness(CANARY_REMEDIATION_SESSION_ID)
    if readiness.get("completion_allowed") is not True:
        raise CanonicalLearningError("remediation_canary_latest_attempt_gate_not_ready")
    completed = s15.ScoredJourneyApplication.complete_session(app, {
        "session_id": CANARY_REMEDIATION_SESSION_ID,
        "expected_session_version": current["session_version"],
        "at": "2026-01-15T01:04:00Z",
    })
    if completed.get("session_state") != "COMPLETED":
        raise CanonicalLearningError("remediation_canary_session_not_completed")
    return {"lesson_id": lesson_id, "failure_attempt_count": 5, "latest_attempt_gate_passed": True}


def run_isolated_acceptance(
    *,
    source_acceptance_database: Path,
    production_database: Path,
    bundles: Mapping[str, Mapping[str, Any]],
    sequence: Mapping[str, int],
    graph_path: Path,
    acceptance_database: Path,
    state_root: Path,
) -> dict[str, Any]:
    production_before = file_digest(production_database)
    acceptance_database.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_acceptance_database, acceptance_database)
    app = _app(
        database=acceptance_database,
        bundles=bundles,
        sequence=sequence,
        graph_path=graph_path,
        state_root=state_root,
        default_learner_id=CANARY_LEARNER_ID,
    )
    remediation_session = _run_high_failure_completed_session(app=app, bundles=bundles, sequence=sequence)
    refresh = app.refresh_canonical_learning(learner_id=CANARY_LEARNER_ID, at=CANARY_CREATED_AT)
    m7_path = state_root / CANARY_LEARNER_ID / "m7" / "a1fs_v1_m7_mastery_snapshot.private.json"
    if not m7_path.is_file():
        raise CanonicalLearningError("m7_acceptance_snapshot_missing")
    review = m8.ReviewRetentionEngine(
        database_path=acceptance_database,
        graph_path=graph_path,
        m7_snapshot_path=m7_path,
    )
    review.initialize()
    review.build_schedule(learner_id=CANARY_LEARNER_ID, as_of=CANARY_REVIEW_AS_OF)
    m8_result = review.export_snapshot(
        learner_id=CANARY_LEARNER_ID,
        output_root=state_root / CANARY_LEARNER_ID / "m8",
        as_of=CANARY_REVIEW_AS_OF,
    )
    m8_path = Path(str(m8_result["snapshot_path"]))
    m7_validation = validate_m7(acceptance_database, graph_path, m7_path)
    m8_validation = validate_m8(acceptance_database, graph_path, m7_path, m8_path)
    if m7_validation["error_count"] or m8_validation["error_count"]:
        raise CanonicalLearningError(
            "canonical_engine_validation_failed:"
            + "|".join(m7_validation["errors"] + m8_validation["errors"])
        )
    m7_snapshot = read_json(m7_path, "m7_acceptance_snapshot")
    m8_snapshot = read_json(m8_path, "m8_acceptance_snapshot")
    open_remediation = sum(row.get("assignment_state") == "OPEN" for row in m7_snapshot["remediation_assignments"])
    pending_reassessment = sum(row.get("queue_state") == "PENDING" for row in m7_snapshot["reassessment_queue"])
    resolved_diagnoses = sum(row.get("diagnosis_state") == "RESOLVED_BY_REASSESSMENT" for row in m7_snapshot["error_diagnoses"])
    due_reviews = sum(row.get("schedule_state") == "DUE" for row in m8_snapshot["review_schedules"])
    with _connect(acceptance_database) as connection:
        human_approve_count = int(connection.execute(
            """SELECT COUNT(*) FROM scoring_results r JOIN response_attempts a USING(attempt_id)
               WHERE a.learner_id=? AND r.outcome='HUMAN_APPROVE'""",
            (CANARY_LEARNER_ID,),
        ).fetchone()[0])
    if (
        int(m7_snapshot["mastered_required_count"]) < 3
        or open_remediation < 2
        or pending_reassessment < 2
        or resolved_diagnoses < 1
        or due_reviews < 3
        or human_approve_count < 1
    ):
        raise CanonicalLearningError("canonical_acceptance_denominator_invalid")
    if file_digest(production_database) != production_before:
        raise CanonicalLearningError("production_database_mutated_by_s16_acceptance")
    progress = app.progress_readback()
    return {
        "unit_count": REQUIRED_UNIT_COUNT,
        "scored_lesson_count": REQUIRED_SCORED_LESSON_COUNT,
        "required_mastery_node_count": REQUIRED_MASTERY_NODE_COUNT,
        "mastered_required_count": int(m7_snapshot["mastered_required_count"]),
        "missing_mastery_count": int(m7_snapshot["required_mastery_node_count"]) - int(m7_snapshot["mastered_required_count"]),
        "open_remediation_count": open_remediation,
        "pending_reassessment_count": pending_reassessment,
        "resolved_diagnosis_count": resolved_diagnoses,
        "due_review_count": due_reviews,
        "retained_required_count": int(m8_snapshot["retained_required_count"]),
        "retention_confirmed": bool(m8_snapshot["retention_confirmed"]),
        "human_approved_attempt_count": human_approve_count,
        "latest_attempt_completion_gate_preserved": remediation_session["latest_attempt_gate_passed"],
        "high_failure_completed_session_count": 1,
        "m7_validation_pass": True,
        "m8_validation_pass": True,
        "learner_progress_projection_pass": progress.get("canonical_learning", {}).get("evaluation_state") == "EVALUATED",
        "production_database_unchanged": True,
        "acceptance_used_isolated_database_clone": True,
        "mastery_write_connected": True,
        "remediation_connected": True,
        "reassessment_connected": True,
        "review_schedule_connected": True,
        "a2_unlocked": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "speaking_capture_enabled": False,
    }
