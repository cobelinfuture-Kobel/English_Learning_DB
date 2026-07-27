#!/usr/bin/env python3
"""Runtime core for A1FS Online V1 S15 scored journeys and completion gates."""
from __future__ import annotations

import json
import sqlite3
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_online_v1_s14_learner_facing_curriculum_progress_semantics as s14  # noqa: E402
from ulga.builders import build_a1fs_online_v1_s05_private_learner_identity_progress_persistence as s05  # noqa: E402
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6  # noqa: E402

s13 = s14.s13
s11 = s14.s11

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Connects the existing S14 authenticated learner surface to the existing M6 response, scoring, "
    "attempt-history, and human-review authorities, and gates Reading/Writing session completion on "
    "passing or approved latest attempts. It creates no curriculum, learner content, answers, scoring "
    "engine, review engine, mastery state, audio, A2 unlock, Cloudflare route, or parallel runtime."
)

PROGRAM_ID = "A1FS-ONLINE-V1"
TASK_ID = "A1FS-ONLINE-V1-S15_ReadingWritingScoredJourneyAndCompletionGate_NoAudio"
SCHEMA_VERSION = "a1fs.online.v1.s15.reading_writing_scored_journey_completion_gate.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_S15_READING_WRITING_SCORED_JOURNEY_READY"
PRODUCT_STATUS = "LOCALHOST_NONAUDIO_READING_WRITING_SCORED_JOURNEY_READY_NOT_UNIT_COMPLETE"
RELEASE_PROFILE = "ONLINE_V1_AUDIO_DEFERRED"
NEXT_SHORT_STEP = "A1FS-ONLINE-V1-S16_CanonicalMasteryRemediationReassessmentReviewIntegration_NoAudio"
DEFAULT_PORT = 8765

CANARY_LEARNER_ID = "A1FS_ONLINE_V1_S15_SCORED_JOURNEY_CANARY"
CANARY_SUBJECT_KEY = "A1FS_ONLINE_V1_S15_PRIVATE_SLOT"
CANARY_READING_SESSION_ID = "A1FS_ONLINE_V1_S15_SESSION:READING"
CANARY_WRITING_SESSION_ID = "A1FS_ONLINE_V1_S15_SESSION:WRITING"
CANARY_PASSWORD = "S15-Local-Canary-Password-Only-For-Isolated-Acceptance-2026!"
CANARY_SESSION_SECRET = "S15-Local-Canary-Session-Signing-Secret-For-Isolated-Acceptance-2026!"

PASSING_OUTCOMES = {"AUTO_PASS", "HUMAN_APPROVE"}
RETRY_OUTCOMES = {"AUTO_FAIL", "HUMAN_REJECT"}
PENDING_OUTCOMES = {"PENDING_HUMAN_REVIEW", "HUMAN_DEFER"}
SCORED_SKILLS = {"READING", "WRITING"}

FORBIDDEN_SAFE_KEYS = set(s14.FORBIDDEN_SAFE_KEYS)


class ScoredJourneyError(ValueError):
    """Fail-closed S15 scored-journey or completion-gate error."""


def digest(value: Any) -> str:
    return s14.digest(value)


def file_digest(path: Path) -> str:
    return s14.file_digest(path)


def read_json(path: Path, code: str) -> dict[str, Any]:
    return s14.read_json(path, code)


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    s14.write_json(path, value, private=private)


def safe_scan(value: Any) -> None:
    s14.safe_scan(value)


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=5000")
    return connection


def _verify_s14(
    receipt_path: Path,
) -> tuple[dict[str, Any], Path, Path, dict[str, dict[str, Any]], dict[str, int]]:
    receipt_path = Path(receipt_path).resolve()
    receipt = read_json(receipt_path, "s14_receipt")
    identity = (
        receipt.get("task_id"),
        receipt.get("schema_version"),
        receipt.get("validation_status"),
        receipt.get("product_status"),
        receipt.get("stop_reason"),
    )
    if identity != (s14.TASK_ID, s14.SCHEMA_VERSION, s14.PASS_STATUS, s14.PRODUCT_STATUS, "NONE"):
        raise ScoredJourneyError("s14_receipt_contract_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest(core):
        raise ScoredJourneyError("s14_receipt_digest_invalid")
    _, database, auth_state, bundles, sequence, _ = s14._source(receipt_path)
    if len(sequence) != 24 or len(bundles) != 72:
        raise ScoredJourneyError("s14_runtime_denominator_invalid")
    return receipt, database, auth_state, bundles, sequence


def _latest_attempt_rows(connection: sqlite3.Connection, session_id: str) -> dict[str, sqlite3.Row]:
    rows = connection.execute(
        """SELECT a.asset_key,a.attempt_sequence,a.submitted_at,
                  r.outcome,r.score,r.human_review_required
           FROM response_attempts a
           JOIN scoring_results r USING(attempt_id)
           WHERE a.session_id=?
           ORDER BY a.asset_key,a.attempt_sequence DESC""",
        (session_id,),
    ).fetchall()
    result: dict[str, sqlite3.Row] = {}
    for row in rows:
        result.setdefault(str(row["asset_key"]), row)
    return result


def _attempt_counts(connection: sqlite3.Connection, session_id: str) -> dict[str, int]:
    return {
        str(row["asset_key"]): int(row["attempt_count"])
        for row in connection.execute(
            """SELECT asset_key,COUNT(*) AS attempt_count
               FROM response_attempts WHERE session_id=? GROUP BY asset_key""",
            (session_id,),
        ).fetchall()
    }


class ScoredJourneyApplication(s14.LearnerFacingApplication):
    """S14 learner application with M6-backed Reading/Writing completion gates."""

    def bootstrap(self) -> dict[str, Any]:
        value = super().bootstrap()
        value.update({
            "task_id": TASK_ID,
            "schema_version": SCHEMA_VERSION,
            "validation_status": PASS_STATUS,
            "product_status": PRODUCT_STATUS,
            "release_profile": RELEASE_PROFILE,
        })
        for unit in value["units"]:
            for lane in unit["lanes"]:
                skill = str(lane["skill"]).upper()
                if skill in SCORED_SKILLS:
                    lane.update({
                        "completion_scope": "SCORED_SESSION_COMPLETION_GATE",
                        "completion_gate_required": True,
                        "all_required_responses_must_pass_or_be_approved": True,
                        "retry_supported": True,
                        "attempt_history_visible": True,
                        "human_review_supported": skill == "WRITING",
                    })
                else:
                    lane.update({
                        "completion_gate_required": False,
                        "all_required_responses_must_pass_or_be_approved": False,
                        "retry_supported": False,
                        "attempt_history_visible": False,
                        "human_review_supported": False,
                    })
        value["learner_product_semantics"].update({
            "reading_writing_scored_journey_connected": True,
            "reading_writing_completion_gate_enabled": True,
            "retry_creates_new_attempt": True,
            "latest_attempt_controls_completion": True,
            "pending_human_review_blocks_completion": True,
            "session_completion_implies_unit_completion": False,
            "session_completion_implies_mastery": False,
        })
        return value

    def completion_readiness(self, session_id: str) -> dict[str, Any]:
        session_id = str(session_id)
        with _connect(self.database_path) as connection:
            session = connection.execute(
                """SELECT session_id,learner_id,lesson_id,skill,level,session_state,session_version
                   FROM learning_sessions WHERE session_id=?""",
                (session_id,),
            ).fetchone()
            if not session:
                raise ScoredJourneyError("session_not_found")
            lesson_id = str(session["lesson_id"])
            bundle = self.lesson_bundles.get(lesson_id)
            if not bundle:
                raise ScoredJourneyError("session_bundle_missing")
            skill = str(session["skill"]).upper()
            if skill not in {"READING", "WRITING", "SPEAKING"}:
                raise ScoredJourneyError("session_skill_not_allowed")
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
                    "mastery_claimed": False,
                }

            bundle_keys = [str(row["asset_key"]) for row in bundle["assets"]]
            placeholders = ",".join("?" for _ in bundle_keys)
            contract_rows = connection.execute(
                f"""SELECT asset_key,contract_json
                    FROM response_contracts
                    WHERE capture_enabled=1 AND asset_key IN ({placeholders})
                    ORDER BY asset_key""",
                bundle_keys,
            ).fetchall()
            contract_by_asset: dict[str, dict[str, Any]] = {}
            for row in contract_rows:
                contract = json.loads(str(row["contract_json"]))
                if not isinstance(contract, dict):
                    raise ScoredJourneyError(f"response_contract_not_object:{row['asset_key']}")
                contract_by_asset[str(row["asset_key"])] = contract
            required_keys = [key for key in bundle_keys if key in contract_by_asset]
            if len(required_keys) != len(bundle_keys) or len(required_keys) != 4:
                raise ScoredJourneyError(f"scored_lane_contract_denominator_invalid:{lesson_id}")
            latest = _latest_attempt_rows(connection, session_id)
            counts = _attempt_counts(connection, session_id)

        assets: list[dict[str, Any]] = []
        blockers: list[str] = []
        passed = pending = retry = not_attempted = attempted = 0
        for index, asset_key in enumerate(required_keys, start=1):
            contract = contract_by_asset[asset_key]
            row = latest.get(asset_key)
            if row is None:
                state = "NOT_ATTEMPTED"
                outcome = None
                not_attempted += 1
                blockers.append("REQUIRED_RESPONSE_NOT_ATTEMPTED")
            else:
                attempted += 1
                outcome = str(row["outcome"])
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
                    raise ScoredJourneyError(f"unsupported_scoring_outcome:{outcome}")
            assets.append({
                "asset_index": index,
                "asset_key": asset_key,
                "scoring_mode": str(contract.get("scoring_mode") or ""),
                "human_review_fallback": bool(contract.get("human_review_fallback")),
                "attempt_count": int(counts.get(asset_key, 0)),
                "latest_outcome": outcome,
                "completion_state": state,
            })
        blockers = list(dict.fromkeys(blockers))
        allowed = not blockers and passed == len(required_keys)
        return {
            "session_id": session_id,
            "lesson_id": lesson_id,
            "skill": skill,
            "session_state": str(session["session_state"]),
            "session_version": int(session["session_version"]),
            "gate_mode": "LATEST_ATTEMPT_PASS_OR_HUMAN_APPROVAL",
            "required_response_count": len(required_keys),
            "attempted_response_count": attempted,
            "passed_response_count": passed,
            "not_attempted_count": not_attempted,
            "retry_required_count": retry,
            "pending_human_review_count": pending,
            "completion_allowed": allowed,
            "blocking_reason_codes": blockers,
            "assets": assets,
            "mastery_claimed": False,
        }

    def submit_response(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        value = dict(payload)
        value.setdefault("learner_id", self.default_learner_id)
        scored = super().submit_response(value)
        readiness = self.completion_readiness(str(payload["session_id"]))
        return {**scored, "completion_gate": readiness}

    def complete_session(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        readiness = self.completion_readiness(str(payload["session_id"]))
        if readiness["skill"] in SCORED_SKILLS and readiness["completion_allowed"] is not True:
            reasons = ",".join(readiness["blocking_reason_codes"]) or "UNKNOWN"
            raise ScoredJourneyError(f"completion_gate_blocked:{reasons}")
        completed = super().complete_session(payload)
        return {
            **completed,
            "completion_gate": {
                "gate_mode": readiness["gate_mode"],
                "required_response_count": readiness["required_response_count"],
                "passed_response_count": readiness["passed_response_count"],
                "completion_allowed": True,
                "mastery_claimed": False,
            },
        }

    def progress_readback(self) -> dict[str, Any]:
        value = super().progress_readback()
        active = self.active_session_readback()
        active_gate = self.completion_readiness(active["session"]["session_id"]) if active.get("active") else None
        completed_scored = 0
        completed_reading = 0
        completed_writing = 0
        human_approve_count = 0
        human_reject_count = 0
        with _connect(self.database_path) as connection:
            completed_rows = connection.execute(
                """SELECT session_id,skill FROM learning_sessions
                   WHERE learner_id=? AND session_state='COMPLETED' AND skill IN('READING','WRITING')
                   ORDER BY started_at,session_id""",
                (self.default_learner_id,),
            ).fetchall()
            outcome_rows = connection.execute(
                """SELECT r.outcome,COUNT(*) AS total
                   FROM scoring_results r JOIN response_attempts a USING(attempt_id)
                   WHERE a.learner_id=? AND r.outcome IN('HUMAN_APPROVE','HUMAN_REJECT')
                   GROUP BY r.outcome""",
                (self.default_learner_id,),
            ).fetchall()
        for row in completed_rows:
            readiness = self.completion_readiness(str(row["session_id"]))
            if readiness["completion_allowed"]:
                completed_scored += 1
                if str(row["skill"]).upper() == "READING":
                    completed_reading += 1
                else:
                    completed_writing += 1
        for row in outcome_rows:
            if row["outcome"] == "HUMAN_APPROVE":
                human_approve_count = int(row["total"])
            elif row["outcome"] == "HUMAN_REJECT":
                human_reject_count = int(row["total"])
        value.update({
            "task_id": TASK_ID,
            "schema_version": SCHEMA_VERSION,
            "validation_status": PASS_STATUS,
            "product_status": PRODUCT_STATUS,
            "active_scored_journey": active_gate,
            "scored_journey_summary": {
                "completed_scored_session_count": completed_scored,
                "completed_reading_scored_session_count": completed_reading,
                "completed_writing_scored_session_count": completed_writing,
                "human_approve_count": human_approve_count,
                "human_reject_count": human_reject_count,
                "active_completion_blocked": bool(active_gate and not active_gate["completion_allowed"]),
            },
        })
        value["semantic_boundaries"].update({
            "reading_writing_session_completion_requires_all_required_responses_passed": True,
            "writing_human_review_approval_satisfies_completion_gate": True,
            "pending_human_review_blocks_completion": True,
            "latest_attempt_controls_completion": True,
            "retry_creates_new_attempt": True,
            "session_completed_implies_unit_completed": False,
            "session_completed_implies_mastery": False,
        })
        return value


def _app(
    database: Path,
    bundles: Mapping[str, Mapping[str, Any]],
    sequence: Mapping[str, int],
    *,
    default_learner_id: str = s05.DEFAULT_LEARNER_ID,
) -> ScoredJourneyApplication:
    return ScoredJourneyApplication(
        database_path=database,
        bundles=bundles,
        sequence_by_grammar=sequence,
        default_learner_id=default_learner_id,
    )
