#!/usr/bin/env python3
"""Independently validate the Unit01 Real62 learner release candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import u01qb03_renderer_runtime_impl as renderer
from ulga.builders import (
    build_a1fs_v1_razq01g_unit01_real_content_learner_product_release_readiness_acceptance
    as builder,
)
from ulga.validators import (
    validate_a1fs_v1_razq01f_unit01_real_content_multi_session_diversity_learner_use_acceptance
    as razq01f_validator,
)

PASS_STATUS = "PASS_A1FS_V1_RAZQ01G_RELEASE_READINESS_VALIDATION"
FAIL_STATUS = "FAIL_A1FS_V1_RAZQ01G_RELEASE_READINESS_VALIDATION"


class ReleaseValidationError(ValueError):
    """Fail-closed RAZQ01G validation error."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReleaseValidationError(message)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"json_object_required:{path}")
    return value


def file_identity(path: Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def assert_safe(value: Any) -> None:
    renderer._assert_safe(value)
    if isinstance(value, Mapping):
        for key, child in value.items():
            require(str(key) not in builder.PRIVATE_KEYS, f"private_release_key_exposed:{key}")
            assert_safe(child)
    elif isinstance(value, list):
        for child in value:
            assert_safe(child)


def validate(
    *,
    database: Path,
    approved_content: Mapping[str, Any],
    multisession_root: Path,
    release_root: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    details: dict[str, Any] = {}
    try:
        database = Path(database)
        multisession_root = Path(multisession_root)
        release_root = Path(release_root)
        require(database.is_file(), "learner_database_missing")
        source_result = razq01f_validator.validate(
            database=database,
            approved_content=approved_content,
            output_root=multisession_root,
        )
        require(
            source_result.get("validation_status") == razq01f_validator.PASS_STATUS
            and source_result.get("error_count") == 0,
            "razq01f_source_validation_failed",
        )
        source = load(multisession_root / "razq01f_multisession_readback.json")
        release = load(release_root / builder.RELEASE_MANIFEST_NAME)
        release_core = {
            key: value
            for key, value in release.items()
            if key != "release_manifest_sha256"
        }
        require(
            release.get("release_manifest_sha256") == digest(release_core),
            "release_manifest_digest_invalid",
        )
        require(release.get("task_id") == builder.TASK_ID, "release_task_invalid")
        require(release.get("schema_version") == builder.SCHEMA_VERSION, "release_schema_invalid")
        require(release.get("status") == builder.PASS_STATUS, "release_status_invalid")
        require(
            release.get("release_scope")
            == "LOCAL_PRIVATE_UNIT01_REAL_CONTENT_LEARNER_PRODUCT",
            "release_scope_invalid",
        )
        require(
            release.get("release_state") == "READY_FOR_LOCAL_PRIVATE_LEARNER_CANARY",
            "release_state_invalid",
        )
        require(release.get("formal_full_product_release_approved") is False, "full_release_overclaimed")
        require(release.get("public_delivery") is False, "public_delivery_enabled")
        require(release.get("private_localhost_only") is True, "private_localhost_boundary_invalid")
        require(release.get("loopback_only") is True, "loopback_boundary_invalid")
        require(
            release.get("source_razq01f_readback_sha256") == source.get("readback_sha256"),
            "source_readback_binding_invalid",
        )
        require(
            release.get("approved_content_artifact_sha256")
            == approved_content.get("artifact_sha256"),
            "approved_content_binding_invalid",
        )
        source_evidence = release.get("source_multisession_evidence") or {}
        expected_source = {
            "combined_runtime_item_count": 474,
            "session_count": 3,
            "session_size": 10,
            "exposure_count": 30,
            "attempt_count": 3,
            "auto_pass_count": 3,
        }
        for key, value in expected_source.items():
            require(source_evidence.get(key) == value, f"source_evidence_{key}_invalid")
        require(
            source_evidence.get("distinct_item_count_across_sessions", 0) >= 20,
            "source_item_diversity_invalid",
        )
        require(
            source_evidence.get("distinct_content_asset_count_across_sessions", 0) >= 20,
            "source_content_diversity_invalid",
        )
        require(release.get("skill") == "READING", "release_skill_invalid")
        require(release.get("item_count") == 10, "release_item_count_invalid")
        require(release.get("distinct_item_count") == 10, "release_item_distinctness_invalid")
        require(
            release.get("distinct_content_asset_count") == 10,
            "release_content_distinctness_invalid",
        )
        require(
            release.get("authoritative_extension_content_count", 0) >= 2,
            "release_extension_quota_invalid",
        )
        require(
            release.get("fresh_cross_session_content_count", 0) >= 0,
            "release_fresh_content_count_invalid",
        )
        capabilities = release.get("capabilities") or {}
        for key in (
            "learner_session_can_be_served",
            "learner_session_can_record_exposure",
            "learner_session_can_submit_attempt",
            "existing_u01qb03_renderer_reused",
            "existing_m3_exposure_reused",
            "existing_m6_response_scoring_reused",
        ):
            require(capabilities.get(key) is True, f"release_capability_missing:{key}")
        require(capabilities.get("answer_keys_exposed") is False, "answer_keys_exposed")
        require(capabilities.get("raw_raz_identity_exposed") is False, "raw_raz_identity_exposed")
        boundaries = release.get("boundaries") or {}
        require(boundaries.get("unit01_only") is True, "unit01_boundary_invalid")
        for key in (
            "second_question_bank_created",
            "parallel_planner_created",
            "parallel_runtime_table_created",
            "parallel_renderer_created",
            "parallel_response_capture_created",
            "parallel_scoring_created",
            "unit02_to_unit24_modified",
            "audio_enabled",
            "speaking_capture_enabled",
            "a2_unlocked",
            "mastery_claimed",
        ):
            require(boundaries.get(key) is False, f"release_boundary_invalid:{key}")

        workbench_root = release_root / builder.WORKBENCH_DIRECTORY_NAME
        bundle = load(workbench_root / "session.private.json")
        workbench_manifest = load(workbench_root / "manifest.json")
        assert_safe(bundle)
        require(bundle.get("session_id") == release.get("release_session_id"), "bundle_session_invalid")
        require(bundle.get("learner_id") == release.get("learner_id"), "bundle_learner_invalid")
        require(bundle.get("item_count") == 10, "bundle_item_count_invalid")
        items = bundle.get("items") or []
        require(len(items) == 10, "bundle_items_invalid")
        item_ids = {str(row.get("item_id") or "") for row in items}
        content_ids = {
            str((row.get("content_binding") or {}).get("content_asset_id") or "")
            for row in items
        }
        require("" not in item_ids and len(item_ids) == 10, "bundle_item_distinctness_invalid")
        require("" not in content_ids and len(content_ids) == 10, "bundle_content_distinctness_invalid")
        release_files = release.get("workbench_files") or {}
        manifest_files = workbench_manifest.get("files") or {}
        for name in builder.REQUIRED_WORKBENCH_FILES:
            path = workbench_root / name
            require(path.is_file(), f"workbench_file_missing:{name}")
            identity = file_identity(path)
            require(dict(release_files.get(name) or {}) == identity, f"release_file_identity_invalid:{name}")
            if name != "manifest.json":
                require(dict(manifest_files.get(name) or {}) == identity, f"workbench_manifest_identity_invalid:{name}")
        require(
            release.get("workbench_manifest_sha256") == digest(workbench_manifest),
            "workbench_manifest_digest_invalid",
        )
        html = (workbench_root / "index.html").read_text(encoding="utf-8")
        javascript = (workbench_root / "app.js").read_text(encoding="utf-8")
        require("connect-src 'self'" in html and "script-src 'self'" in html, "workbench_csp_invalid")
        for endpoint in ("/api/session", "/api/exposure", "/api/attempt"):
            require(endpoint in javascript, f"workbench_endpoint_missing:{endpoint}")

        with sqlite3.connect(database) as connection:
            connection.row_factory = sqlite3.Row
            session = connection.execute(
                """SELECT learner_id,lesson_id,skill,level,session_state,session_version
                   FROM learning_sessions WHERE session_id=?""",
                (release["release_session_id"],),
            ).fetchone()
            require(session is not None, "release_session_missing")
            require(session["learner_id"] == release["learner_id"], "release_session_learner_invalid")
            require(session["lesson_id"] == release["lesson_id"], "release_session_lesson_invalid")
            require(session["skill"] == "READING" and session["level"] == "A1", "release_session_scope_invalid")
            require(session["session_state"] == "ACTIVE", "release_session_not_active")
            plan_count = connection.execute(
                "SELECT COUNT(*) FROM u01qb02_session_items WHERE session_id=?",
                (release["release_session_id"],),
            ).fetchone()[0]
            exposure_count = connection.execute(
                "SELECT COUNT(*) FROM u01qb02_item_exposures WHERE session_id=?",
                (release["release_session_id"],),
            ).fetchone()[0]
            attempt_count = connection.execute(
                "SELECT COUNT(*) FROM response_attempts WHERE session_id=?",
                (release["release_session_id"],),
            ).fetchone()[0]
            parallel_tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'razq01g%'"
            ).fetchall()
        require(plan_count == 10, "release_session_plan_count_invalid")
        require(0 <= attempt_count <= exposure_count <= 10, "release_runtime_count_invalid")
        require(parallel_tables == [], "parallel_razq01g_runtime_table_created")
        details = {
            "release_session_id": release["release_session_id"],
            "release_session_version": int(session["session_version"]),
            "item_count": 10,
            "distinct_content_asset_count": 10,
            "authoritative_extension_content_count": release[
                "authoritative_extension_content_count"
            ],
            "fresh_cross_session_content_count": release[
                "fresh_cross_session_content_count"
            ],
            "exposure_count": exposure_count,
            "attempt_count": attempt_count,
            "release_manifest_sha256": release["release_manifest_sha256"],
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
    return {
        "validation_status": PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        **details,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--approved-content", type=Path, default=builder.DEFAULT_APPROVED_CONTENT)
    parser.add_argument("--multisession-root", type=Path, default=builder.DEFAULT_MULTISESSION_ROOT)
    parser.add_argument("--release-root", type=Path, default=builder.DEFAULT_RELEASE_ROOT)
    args = parser.parse_args(argv)
    result = validate(
        database=args.database,
        approved_content=builder.load(args.approved_content),
        multisession_root=args.multisession_root,
        release_root=args.release_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
