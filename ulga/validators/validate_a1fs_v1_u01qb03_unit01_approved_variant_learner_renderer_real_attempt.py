#!/usr/bin/env python3
"""Validate the U01QB03 private learner workbench and real-attempt lineage."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import (
    build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02,
)
from ulga.builders import (
    build_a1fs_v1_u01qb03_unit01_approved_variant_learner_renderer_real_attempt as builder,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validates U01QB03 renderer outputs and existing M3/M6 attempt lineage only; "
    "no learner content or runtime authority is produced."
)
TASK_ID = builder.TASK_ID + "Validator"
PASS_STATUS = builder.PASS_STATUS


class LearnerRendererValidationError(ValueError):
    pass


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LearnerRendererValidationError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise LearnerRendererValidationError(f"{code}_not_object")
    return value


def walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            keys.add(str(key))
            keys.update(walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(walk_keys(child))
    return keys


def validate(*, database: Path, output_root: Path, require_attempts: bool = True) -> dict[str, Any]:
    errors: list[str] = []
    root = Path(output_root)
    try:
        bundle = read_json(root / "session.private.json", "bundle")
        manifest = read_json(root / "manifest.json", "manifest")
    except LearnerRendererValidationError as exc:
        return {"status": "FAIL", "error_count": 1, "errors": [str(exc)]}

    if bundle.get("validation_status") != builder.PASS_STATUS:
        errors.append("bundle_status_invalid")
    if bundle.get("renderer_authority_task_id") != builder.m5.TASK_ID:
        errors.append("m5_renderer_authority_missing")
    if bundle.get("runtime_authority_task_id") != qb02.TASK_ID:
        errors.append("qb02_runtime_authority_missing")
    if bundle.get("item_count") != qb02.SESSION_SIZE or len(bundle.get("items", [])) != qb02.SESSION_SIZE:
        errors.append("bundle_item_count_invalid")
    if bundle.get("skill") not in {"READING", "WRITING", "SPEAKING"}:
        errors.append("bundle_skill_invalid")
    if not isinstance(bundle.get("session_version"), int) or bundle["session_version"] < 1:
        errors.append("bundle_session_version_invalid")
    exposed = walk_keys(bundle).intersection(builder.BLOCKED_LEARNER_KEYS)
    if exposed:
        errors.append("private_keys_exposed:" + ",".join(sorted(exposed)))
    for item in bundle.get("items", []):
        expected = builder.response_mode(item)
        if item.get("response_mode") != expected:
            errors.append(f"response_mode_invalid:{item.get('item_id')}")
        if bundle.get("skill") == "SPEAKING" and item.get("capture_enabled") is not False:
            errors.append(f"speaking_capture_enabled:{item.get('item_id')}")

    expected_files = {"session.private.json", "index.html", "styles.css", "app.js"}
    if set(manifest.get("files", {})) != expected_files:
        errors.append("manifest_file_set_invalid")
    if manifest.get("validation_status") != builder.PASS_STATUS:
        errors.append("manifest_status_invalid")
    if manifest.get("private_localhost_only") is not True:
        errors.append("private_localhost_boundary_missing")
    for name in expected_files:
        path = root / name
        if not path.is_file():
            errors.append(f"output_missing:{name}")
            continue
        raw = path.read_bytes()
        recorded = manifest.get("files", {}).get(name, {})
        if recorded.get("sha256") != hashlib.sha256(raw).hexdigest():
            errors.append(f"output_digest_invalid:{name}")
        if recorded.get("bytes") != len(raw):
            errors.append(f"output_size_invalid:{name}")

    counts = {
        "session_plan_count": 0,
        "session_item_count": 0,
        "item_exposure_count": 0,
        "attempt_count": 0,
        "scoring_result_count": 0,
        "auto_pass_count": 0,
        "auto_fail_count": 0,
    }
    try:
        with sqlite3.connect(database) as connection:
            session_id = bundle.get("session_id")
            lesson_id = bundle.get("lesson_id")
            counts["session_plan_count"] = connection.execute(
                "SELECT COUNT(*) FROM u01qb02_session_plans WHERE session_id=?", (session_id,)
            ).fetchone()[0]
            counts["session_item_count"] = connection.execute(
                "SELECT COUNT(*) FROM u01qb02_session_items WHERE session_id=?", (session_id,)
            ).fetchone()[0]
            counts["item_exposure_count"] = connection.execute(
                "SELECT COUNT(*) FROM u01qb02_item_exposures WHERE session_id=?", (session_id,)
            ).fetchone()[0]
            counts["attempt_count"] = connection.execute(
                "SELECT COUNT(*) FROM response_attempts WHERE session_id=?", (session_id,)
            ).fetchone()[0]
            counts["scoring_result_count"] = connection.execute(
                """SELECT COUNT(*) FROM scoring_results r JOIN response_attempts a USING(attempt_id)
                   WHERE a.session_id=?""", (session_id,)
            ).fetchone()[0]
            counts["auto_pass_count"] = connection.execute(
                """SELECT COUNT(*) FROM scoring_results r JOIN response_attempts a USING(attempt_id)
                   WHERE a.session_id=? AND r.outcome='AUTO_PASS'""", (session_id,)
            ).fetchone()[0]
            counts["auto_fail_count"] = connection.execute(
                """SELECT COUNT(*) FROM scoring_results r JOIN response_attempts a USING(attempt_id)
                   WHERE a.session_id=? AND r.outcome='AUTO_FAIL'""", (session_id,)
            ).fetchone()[0]
            invalid_assets = connection.execute(
                """SELECT COUNT(*) FROM response_attempts a
                   LEFT JOIN u01qb02_item_catalog c ON c.asset_key=a.asset_key
                   WHERE a.session_id=? AND (c.item_id IS NULL OR c.lesson_id<>?)""",
                (session_id, lesson_id),
            ).fetchone()[0]
            if invalid_assets:
                errors.append(f"attempt_asset_lineage_invalid:{invalid_assets}")
            session = connection.execute(
                "SELECT skill,level,session_version FROM learning_sessions WHERE session_id=?", (session_id,)
            ).fetchone()
            if not session or session[0] != bundle.get("skill") or session[1] != "A1":
                errors.append("session_identity_invalid")
    except sqlite3.Error as exc:
        errors.append(f"database_validation_failed:{exc}")

    if counts["session_plan_count"] != 1:
        errors.append(f"session_plan_count_invalid:{counts['session_plan_count']}")
    if counts["session_item_count"] != qb02.SESSION_SIZE:
        errors.append(f"session_item_count_invalid:{counts['session_item_count']}")
    if counts["attempt_count"] != counts["scoring_result_count"]:
        errors.append("attempt_scoring_count_mismatch")
    if require_attempts and counts["attempt_count"] < 1:
        errors.append("real_attempt_evidence_missing")
    if require_attempts and counts["item_exposure_count"] < 1:
        errors.append("real_exposure_evidence_missing")

    return {
        "status": builder.PASS_STATUS if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        **counts,
        "lesson_id": bundle.get("lesson_id"),
        "skill": bundle.get("skill"),
        "claim_boundaries": {
            "existing_m5_renderer_reused": True,
            "existing_m3_exposure_reused": True,
            "existing_m6_response_scoring_reused": True,
            "parallel_renderer_created": False,
            "parallel_response_capture_created": False,
            "parallel_scoring_created": False,
            "speaking_capture_enabled": False,
            "mastery_claimed": False,
            "a2_unlocked": False,
        },
        "next_short_step": builder.NEXT_SHORT_STEP,
    }
