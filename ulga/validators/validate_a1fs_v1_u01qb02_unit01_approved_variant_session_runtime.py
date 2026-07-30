#!/usr/bin/env python3
"""Independently validate U01QB02 against existing M3/M6 authorities."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import (
    build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as bank,
)
from ulga.builders import (
    build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U01QB02_UNIT01_APPROVED_VARIANT_SESSION_RUNTIME_VALIDATOR"
EXPECTED_SKILLS = {"READING": 166, "SPEAKING": 25, "WRITING": 97}


class SessionRuntimeValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise SessionRuntimeValidationError(code)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return bool(
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
    )


def validate_plan(connection: sqlite3.Connection, plan: sqlite3.Row) -> None:
    session_id = plan["session_id"]
    session = connection.execute(
        "SELECT * FROM learning_sessions WHERE session_id=?", (session_id,)
    ).fetchone()
    require(session is not None, f"plan_session_missing:{session_id}")
    require(plan["learner_id"] == session["learner_id"], f"plan_learner_mismatch:{session_id}")
    require(plan["lesson_id"] == session["lesson_id"], f"plan_lesson_mismatch:{session_id}")
    require(plan["skill"] == session["skill"], f"plan_skill_mismatch:{session_id}")
    require(plan["lesson_id"] in builder.LESSON_TO_SKILL, f"plan_outside_unit01:{session_id}")
    rows = connection.execute(
        "SELECT * FROM u01qb02_session_items WHERE session_id=? ORDER BY item_position",
        (session_id,),
    ).fetchall()
    require(len(rows) == builder.SESSION_SIZE, f"plan_item_count_invalid:{session_id}:{len(rows)}")
    require([row["item_position"] for row in rows] == list(range(1, 11)), f"plan_positions_invalid:{session_id}")
    require(len({row["item_id"] for row in rows}) == 10, f"plan_duplicate_item:{session_id}")
    core = {
        "session_id": session_id,
        "learner_id": plan["learner_id"],
        "lesson_id": plan["lesson_id"],
        "skill": plan["skill"],
        "selected_at": plan["selected_at"],
        "recent_exposure_window": plan["recent_exposure_window"],
        "items": [
            {
                "position": row["item_position"],
                "item_id": row["item_id"],
                "reason": row["selection_reason"],
            }
            for row in rows
        ],
        "source_bank_sha256": plan["source_bank_sha256"],
    }
    require(digest(core) == plan["plan_digest"], f"plan_digest_invalid:{session_id}")
    for row in rows:
        item = connection.execute(
            "SELECT lesson_id,skill FROM u01qb02_item_catalog WHERE item_id=?", (row["item_id"],)
        ).fetchone()
        require(item is not None, f"plan_item_missing:{session_id}:{row['item_id']}")
        require(item["lesson_id"] == plan["lesson_id"], f"plan_item_lesson_mismatch:{session_id}:{row['item_id']}")
        require(item["skill"] == plan["skill"], f"plan_item_skill_mismatch:{session_id}:{row['item_id']}")
        require(row["selection_reason"] in builder.SELECTION_REASONS, f"selection_reason_invalid:{session_id}")


def validate_exposure_chain(connection: sqlite3.Connection) -> int:
    previous = "0" * 64
    count = 0
    for row in connection.execute(
        "SELECT * FROM u01qb02_item_exposures ORDER BY exposure_seq"
    ):
        count += 1
        core = {
            "exposure_id": row["exposure_id"],
            "learner_id": row["learner_id"],
            "session_id": row["session_id"],
            "item_id": row["item_id"],
            "selection_reason": row["selection_reason"],
            "exposure_at": row["exposure_at"],
        }
        expected = hashlib.sha256((previous + canonical(core)).encode("utf-8")).hexdigest()
        require(row["previous_hash"] == previous, f"exposure_previous_hash_invalid:{row['exposure_id']}")
        require(row["exposure_hash"] == expected, f"exposure_hash_invalid:{row['exposure_id']}")
        selected = connection.execute(
            "SELECT selection_reason FROM u01qb02_session_items WHERE session_id=? AND item_id=?",
            (row["session_id"], row["item_id"]),
        ).fetchone()
        require(selected is not None, f"exposure_item_not_selected:{row['exposure_id']}")
        require(selected[0] == row["selection_reason"], f"exposure_reason_drift:{row['exposure_id']}")
        asset = connection.execute(
            "SELECT asset_key FROM u01qb02_item_catalog WHERE item_id=?", (row["item_id"],)
        ).fetchone()
        require(asset is not None, f"exposure_catalog_missing:{row['exposure_id']}")
        state_event_match = False
        for event in connection.execute(
            "SELECT payload_json FROM state_events WHERE session_id=? AND event_type='ASSET_EXPOSED'",
            (row["session_id"],),
        ):
            payload = json.loads(event[0])
            if payload.get("asset_key") == asset[0]:
                state_event_match = True
                break
        require(state_event_match, f"m3_exposure_event_missing:{row['exposure_id']}")
        previous = row["exposure_hash"]
    return count


def validate(database_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    counts: dict[str, Any] = {}
    try:
        path = Path(database_path)
        require(path.is_file(), "database_missing")
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            for table in (
                "metadata",
                "lesson_catalog",
                "lesson_assets",
                "learner_profiles",
                "learning_sessions",
                "state_events",
                "response_contracts",
                "response_attempts",
                "scoring_results",
                "u01qb02_metadata",
                "u01qb02_item_catalog",
                "u01qb02_session_plans",
                "u01qb02_session_items",
                "u01qb02_item_exposures",
            ):
                require(table_exists(connection, table), f"required_table_missing:{table}")
            metadata = dict(connection.execute("SELECT key,value FROM metadata"))
            runtime_metadata = dict(connection.execute("SELECT key,value FROM u01qb02_metadata"))
            require(metadata.get("validation_status") == m3.STATUS, "m3_status_invalid")
            require(runtime_metadata.get("validation_status") == builder.PASS_STATUS, "runtime_status_invalid")
            require(runtime_metadata.get("task_id") == builder.TASK_ID, "runtime_task_invalid")
            require(runtime_metadata.get("schema_version") == builder.SCHEMA_VERSION, "runtime_schema_invalid")
            require(runtime_metadata.get("approved_item_count") == "288", "approved_count_metadata_invalid")
            require(runtime_metadata.get("m4_remains_lesson_planner") == "true", "m4_authority_not_preserved")
            require(runtime_metadata.get("m3_exposure_authority_reused") == "true", "m3_authority_not_reused")
            require(runtime_metadata.get("m6_attempt_scoring_authority_reused") == "true", "m6_authority_not_reused")
            require(runtime_metadata.get("parallel_runtime_created") == "false", "parallel_runtime_created")
            require(runtime_metadata.get("a2_unlocked") == "false", "a2_unlocked")
            require(
                isinstance(runtime_metadata.get("source_bank_artifact_sha256"), str)
                and len(runtime_metadata["source_bank_artifact_sha256"]) == 64,
                "source_bank_digest_invalid",
            )
            catalog = connection.execute(
                "SELECT * FROM u01qb02_item_catalog ORDER BY item_id"
            ).fetchall()
            require(len(catalog) == bank.EXPECTED_APPROVED_COUNT, f"catalog_count_invalid:{len(catalog)}")
            skill_counts = dict(sorted(Counter(row["skill"] for row in catalog).items()))
            require(skill_counts == EXPECTED_SKILLS, f"catalog_skill_distribution_invalid:{skill_counts}")
            for row in catalog:
                item = json.loads(row["private_item_json"])
                require(digest(item) == row["item_digest"], f"item_digest_invalid:{row['item_id']}")
                require(item.get("item_id") == row["item_id"], f"item_identity_invalid:{row['item_id']}")
                require(item.get("skill") == row["skill"], f"item_skill_invalid:{row['item_id']}")
                require(item.get("admission_proposal", {}).get("status") == "AUTO_APPROVED", f"unapproved_item_registered:{row['item_id']}")
                require(row["lesson_id"] == builder.UNIT01_LESSONS[row["skill"]], f"item_lesson_invalid:{row['item_id']}")
                require(row["lesson_id"] in builder.LESSON_TO_SKILL, f"item_outside_unit01:{row['item_id']}")
                asset = connection.execute(
                    "SELECT * FROM lesson_assets WHERE asset_key=?", (row["asset_key"],)
                ).fetchone()
                require(asset is not None, f"lesson_asset_missing:{row['item_id']}")
                require(asset["asset_id"] == row["item_id"], f"lesson_asset_identity_invalid:{row['item_id']}")
                require(asset["lesson_id"] == row["lesson_id"], f"lesson_asset_lesson_invalid:{row['item_id']}")
                require(asset["content_digest"] == row["item_digest"], f"lesson_asset_digest_invalid:{row['item_id']}")
                response = connection.execute(
                    "SELECT * FROM response_contracts WHERE asset_key=?", (row["asset_key"],)
                ).fetchone()
                require(response is not None, f"response_contract_missing:{row['item_id']}")
                contract = json.loads(response["contract_json"])
                require(m6.sha(contract) == response["contract_digest"], f"response_contract_digest_invalid:{row['item_id']}")
                require(contract.get("m12_item_id") == row["item_id"], f"response_item_identity_invalid:{row['item_id']}")
                require(contract.get("lesson_id") == row["lesson_id"], f"response_lesson_invalid:{row['item_id']}")
                require(contract.get("skill") == row["skill"], f"response_skill_invalid:{row['item_id']}")
                require(bool(contract.get("capture_enabled")) is bool(row["capture_enabled"]), f"capture_flag_invalid:{row['item_id']}")
            plan_count = 0
            for plan in connection.execute("SELECT * FROM u01qb02_session_plans ORDER BY session_id"):
                validate_plan(connection, plan)
                plan_count += 1
            exposure_count = validate_exposure_chain(connection)
            for attempt in connection.execute(
                """SELECT a.attempt_id,a.session_id,a.asset_key,c.item_id
                FROM response_attempts a LEFT JOIN u01qb02_item_catalog c ON c.asset_key=a.asset_key
                WHERE a.asset_key LIKE 'U01QB02:%'"""
            ):
                require(attempt["item_id"] is not None, f"attempt_catalog_missing:{attempt['attempt_id']}")
                require(
                    connection.execute(
                        "SELECT 1 FROM u01qb02_session_items WHERE session_id=? AND item_id=?",
                        (attempt["session_id"], attempt["item_id"]),
                    ).fetchone()
                    is not None,
                    f"attempt_item_not_selected:{attempt['attempt_id']}",
                )
                require(
                    connection.execute(
                        "SELECT 1 FROM u01qb02_item_exposures WHERE session_id=? AND item_id=?",
                        (attempt["session_id"], attempt["item_id"]),
                    ).fetchone()
                    is not None,
                    f"attempt_before_exposure:{attempt['attempt_id']}",
                )
            counts = {
                "registered_item_count": len(catalog),
                "response_contract_count": connection.execute(
                    "SELECT COUNT(*) FROM response_contracts WHERE asset_key LIKE 'U01QB02:%'"
                ).fetchone()[0],
                "session_plan_count": plan_count,
                "item_exposure_count": exposure_count,
                "attempt_count": connection.execute(
                    "SELECT COUNT(*) FROM response_attempts WHERE asset_key LIKE 'U01QB02:%'"
                ).fetchone()[0],
                "skill_distribution": skill_counts,
            }
        finally:
            connection.close()
    except (
        SessionRuntimeValidationError,
        sqlite3.Error,
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(str(exc))
    return {
        "validator_id": VALIDATOR_ID,
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        **counts,
        "claim_boundaries": {
            "parallel_planner_created": False,
            "parallel_learner_database_created": False,
            "parallel_response_capture_created": False,
            "parallel_scoring_created": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
            "mastery_claimed": False,
        },
    }
