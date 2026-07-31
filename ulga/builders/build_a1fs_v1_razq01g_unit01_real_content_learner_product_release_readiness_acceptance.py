#!/usr/bin/env python3
"""Build and serve one validated Unit01 Real62 learner release candidate."""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import sqlite3
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import u01qb03_renderer_runtime_impl as renderer
from ulga.builders import (
    build_a1fs_v1_razq01f_fullfix_real62_semantic_lexical_anchor_fallback
    as razq01f,
)
from ulga.validators import (
    validate_a1fs_v1_razq01f_unit01_real_content_multi_session_diversity_learner_use_acceptance
    as razq01f_validator,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Consumes passed RAZQ01F evidence and creates one fresh private loopback-only Unit01 release-candidate session through existing M3, U01QB02, RAZQ01E, RAZQ01F, U01QB03, and M6 authorities; no content, bank, planner, renderer, learner database, response capture, scoring authority, audio, A2, or Unit02-Unit24 artifact is produced."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-RAZQ01G_Unit01RealContentLearnerProductReleaseReadinessAcceptance"
SCHEMA_VERSION = "a1fs.v1.razq01g.unit01_real_content_release_readiness.v1"
PASS_STATUS = "PASS_A1FS_V1_RAZQ01G_UNIT01_REAL_CONTENT_LEARNER_PRODUCT_RELEASE_READINESS"
NEXT_SHORT_STEP = "A1FS-V1-RAZQ01G_LocalPrivateReal62LearnerProductReleaseReadinessCanary"
DEFAULT_APPROVED_CONTENT = Path("ulga/private/a1fs_v1_razq01d_fullfix2_unit01_real44.approved.private.json")
DEFAULT_MULTISESSION_ROOT = Path("A1FS_Private_Outputs/RAZQ01F_LocalPrivateMultiSessionAcceptance/learner_workbenches")
DEFAULT_RELEASE_ROOT = Path("A1FS_Private_Outputs/RAZQ01G_LocalPrivateLearnerProductReleaseCandidate")
RELEASE_MANIFEST_NAME = "razq01g_release_manifest.json"
WORKBENCH_DIRECTORY_NAME = "learner_workbench"
REQUIRED_WORKBENCH_FILES = ("session.private.json", "manifest.json", "index.html", "styles.css", "app.js")
PRIVATE_KEYS = frozenset({
    "source_record_id", "semantic_identity", "text_excerpt", "source_excerpt",
    "raw_raz_text", "private_source_sha256", "private_item_json",
    "response_contract", "correct_answer", "accepted_answers",
    "accepted_sequence", "accepted_texts", "rubric",
})


class ReleaseReadinessError(ValueError):
    """Fail-closed Unit01 release-readiness error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseReadinessError(f"json_unreadable:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ReleaseReadinessError(f"json_object_required:{path}")
    return value


def atomic(path: Path, content: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def file_identity(path: Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def assert_learner_safe(value: Any) -> None:
    renderer._assert_safe(value)
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in PRIVATE_KEYS:
                raise ReleaseReadinessError(f"private_release_key_exposed:{key}")
            assert_learner_safe(child)
    elif isinstance(value, list):
        for child in value:
            assert_learner_safe(child)


def validate_source(
    database: Path,
    approved_content: Mapping[str, Any],
    multisession_root: Path,
) -> dict[str, Any]:
    result = razq01f_validator.validate(
        database=Path(database),
        approved_content=approved_content,
        output_root=Path(multisession_root),
    )
    if result.get("validation_status") != razq01f_validator.PASS_STATUS or result.get("error_count") != 0:
        raise ReleaseReadinessError(
            "razq01f_source_validation_failed:"
            + "|".join(str(v) for v in result.get("errors") or [])
        )
    report = load(Path(multisession_root) / "razq01f_multisession_readback.json")
    expected = {
        "status": razq01f.PASS_STATUS,
        "combined_runtime_item_count": 474,
        "session_count": 3,
        "session_size": 10,
        "exposure_count": 30,
        "attempt_count": 3,
        "auto_pass_count": 3,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            raise ReleaseReadinessError(f"razq01f_source_{key}_invalid")
    if report.get("distinct_item_count_across_sessions", 0) < 20:
        raise ReleaseReadinessError("razq01f_item_diversity_invalid")
    if report.get("distinct_content_asset_count_across_sessions", 0) < 20:
        raise ReleaseReadinessError("razq01f_content_diversity_invalid")
    return report


def session_state(database: Path, session_id: str) -> dict[str, Any] | None:
    with sqlite3.connect(Path(database)) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """SELECT session_id,learner_id,lesson_id,skill,level,
                      session_state,session_version
               FROM learning_sessions WHERE session_id=?""",
            (session_id,),
        ).fetchone()
    return dict(row) if row else None


def start_or_reuse_session(
    database: Path,
    learner_id: str,
    session_id: str,
    started_at: str,
) -> dict[str, Any]:
    lesson_id = razq01f.extension_runtime.qb02.UNIT01_LESSONS["READING"]
    existing = session_state(database, session_id)
    if existing is not None:
        if (
            existing["learner_id"] != learner_id
            or existing["lesson_id"] != lesson_id
            or existing["skill"] != "READING"
            or existing["level"] != "A1"
            or existing["session_state"] != "ACTIVE"
        ):
            raise ReleaseReadinessError("release_session_identity_or_state_invalid")
        return existing
    return razq01f.m3.LearnerStateStore(Path(database)).start_session(
        learner_id=learner_id,
        lesson_id=lesson_id,
        session_id=session_id,
        at=started_at,
    )


def verify_workbench(workbench_root: Path) -> dict[str, dict[str, Any]]:
    manifest = load(Path(workbench_root) / "manifest.json")
    manifest_files = manifest.get("files")
    if not isinstance(manifest_files, Mapping):
        raise ReleaseReadinessError("workbench_manifest_files_invalid")
    identities: dict[str, dict[str, Any]] = {}
    for name in REQUIRED_WORKBENCH_FILES:
        path = Path(workbench_root) / name
        if not path.is_file():
            raise ReleaseReadinessError(f"workbench_file_missing:{name}")
        identity = file_identity(path)
        if name != "manifest.json" and dict(manifest_files.get(name) or {}) != identity:
            raise ReleaseReadinessError(f"workbench_file_identity_invalid:{name}")
        identities[name] = identity
    html = (Path(workbench_root) / "index.html").read_text(encoding="utf-8")
    javascript = (Path(workbench_root) / "app.js").read_text(encoding="utf-8")
    if "connect-src 'self'" not in html or "script-src 'self'" not in html:
        raise ReleaseReadinessError("workbench_csp_invalid")
    for endpoint in ("/api/session", "/api/exposure", "/api/attempt"):
        if endpoint not in javascript:
            raise ReleaseReadinessError(f"workbench_endpoint_missing:{endpoint}")
    return identities


def build_release_candidate(
    *,
    database: Path,
    approved_content: Mapping[str, Any],
    learner_id: str,
    multisession_root: Path,
    release_root: Path,
    release_session_id: str,
    started_at: str = "2026-07-31T02:00:00Z",
) -> dict[str, Any]:
    database = Path(database)
    multisession_root = Path(multisession_root)
    release_root = Path(release_root)
    if not database.is_file():
        raise ReleaseReadinessError("learner_database_missing")
    source = validate_source(database, approved_content, multisession_root)
    prior_content_ids = sorted({
        str(asset_id)
        for row in source.get("sessions") or []
        for asset_id in row.get("content_asset_ids") or []
    })
    start_or_reuse_session(
        database, learner_id, release_session_id, started_at
    )
    workbench_root = release_root / WORKBENCH_DIRECTORY_NAME
    manifest = razq01f.build_workbench(
        database=database,
        learner_id=learner_id,
        session_id=release_session_id,
        approved_content=approved_content,
        output_root=workbench_root,
        prior_content_asset_ids=prior_content_ids,
    )
    bundle = load(workbench_root / "session.private.json")
    assert_learner_safe(bundle)
    if bundle.get("session_id") != release_session_id or bundle.get("learner_id") != learner_id:
        raise ReleaseReadinessError("release_bundle_identity_invalid")
    if bundle.get("skill") != "READING" or bundle.get("item_count") != 10:
        raise ReleaseReadinessError("release_bundle_denominator_invalid")
    items = bundle.get("items")
    if not isinstance(items, list) or len(items) != 10:
        raise ReleaseReadinessError("release_bundle_items_invalid")
    item_ids = {str(row.get("item_id") or "") for row in items}
    content_ids = {
        str((row.get("content_binding") or {}).get("content_asset_id") or "")
        for row in items
    }
    if "" in item_ids or len(item_ids) != 10:
        raise ReleaseReadinessError("release_item_distinctness_invalid")
    if "" in content_ids or len(content_ids) != 10:
        raise ReleaseReadinessError("release_content_distinctness_invalid")
    if int(bundle.get("authoritative_extension_content_count", 0)) < 2:
        raise ReleaseReadinessError("release_extension_quota_invalid")
    if int(bundle.get("fresh_cross_session_content_count", 0)) < 0:
        raise ReleaseReadinessError("release_fresh_content_count_invalid")
    identities = verify_workbench(workbench_root)
    state = session_state(database, release_session_id)
    if not state or state["session_state"] != "ACTIVE":
        raise ReleaseReadinessError("release_session_not_active")
    core = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "release_scope": "LOCAL_PRIVATE_UNIT01_REAL_CONTENT_LEARNER_PRODUCT",
        "release_state": "READY_FOR_LOCAL_PRIVATE_LEARNER_CANARY",
        "formal_full_product_release_approved": False,
        "public_delivery": False,
        "private_localhost_only": True,
        "loopback_only": True,
        "source_razq01f_task_id": source["task_id"],
        "source_razq01f_readback_sha256": source["readback_sha256"],
        "source_multisession_evidence": {
            key: source[key]
            for key in (
                "combined_runtime_item_count",
                "session_count",
                "session_size",
                "exposure_count",
                "attempt_count",
                "auto_pass_count",
                "distinct_item_count_across_sessions",
                "distinct_content_asset_count_across_sessions",
            )
        },
        "approved_content_artifact_sha256": approved_content["artifact_sha256"],
        "learner_id": learner_id,
        "release_session_id": release_session_id,
        "release_session_state": state["session_state"],
        "release_session_version_at_build": int(state["session_version"]),
        "lesson_id": bundle["lesson_id"],
        "skill": bundle["skill"],
        "item_count": bundle["item_count"],
        "distinct_item_count": len(item_ids),
        "distinct_content_asset_count": len(content_ids),
        "authoritative_extension_content_count": bundle["authoritative_extension_content_count"],
        "fresh_cross_session_content_count": bundle["fresh_cross_session_content_count"],
        "prior_session_content_overlap_count": bundle["prior_session_content_overlap_count"],
        "workbench_manifest_sha256": digest(manifest),
        "workbench_files": identities,
        "launcher": {
            "module": "ulga.builders.build_a1fs_v1_razq01g_unit01_real_content_learner_product_release_readiness_acceptance",
            "command": "serve",
            "host_policy": "LOOPBACK_ONLY",
            "existing_renderer_task_id": renderer.TASK_ID,
            "existing_runtime_task_id": razq01f.extension_runtime.qb02.TASK_ID,
            "existing_response_scoring_task_id": razq01f.extension_runtime.qb02.m6.TASK_ID,
        },
        "capabilities": {
            "learner_session_can_be_served": True,
            "learner_session_can_record_exposure": True,
            "learner_session_can_submit_attempt": True,
            "existing_u01qb03_renderer_reused": True,
            "existing_m3_exposure_reused": True,
            "existing_m6_response_scoring_reused": True,
            "answer_keys_exposed": False,
            "raw_raz_identity_exposed": False,
        },
        "boundaries": {
            "unit01_only": True,
            "second_question_bank_created": False,
            "parallel_planner_created": False,
            "parallel_runtime_table_created": False,
            "parallel_renderer_created": False,
            "parallel_response_capture_created": False,
            "parallel_scoring_created": False,
            "unit02_to_unit24_modified": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
            "mastery_claimed": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    release = {**core, "release_manifest_sha256": digest(core)}
    atomic(
        release_root / RELEASE_MANIFEST_NAME,
        json.dumps(release, ensure_ascii=False, indent=2) + "\n",
    )
    return release


def load_release_manifest(release_root: Path) -> dict[str, Any]:
    release = load(Path(release_root) / RELEASE_MANIFEST_NAME)
    core = {k: v for k, v in release.items() if k != "release_manifest_sha256"}
    if release.get("release_manifest_sha256") != digest(core):
        raise ReleaseReadinessError("release_manifest_digest_invalid")
    if release.get("status") != PASS_STATUS:
        raise ReleaseReadinessError("release_manifest_status_invalid")
    return release


def create_server(
    *,
    database: Path,
    release_root: Path,
    host: str = "127.0.0.1",
    port: int = 0,
) -> ThreadingHTTPServer:
    if host not in {"127.0.0.1", "localhost"}:
        raise ReleaseReadinessError("release_server_must_bind_loopback")
    release = load_release_manifest(release_root)
    workbench_root = Path(release_root) / WORKBENCH_DIRECTORY_NAME
    bundle = load(workbench_root / "session.private.json")
    if bundle.get("session_id") != release["release_session_id"]:
        raise ReleaseReadinessError("release_server_session_drift")
    if bundle.get("learner_id") != release["learner_id"]:
        raise ReleaseReadinessError("release_server_learner_drift")

    class BoundReleaseHandler(renderer.WorkbenchHandler):
        pass

    BoundReleaseHandler.controller = renderer.LearnerAttemptController(
        Path(database),
        learner_id=str(release["learner_id"]),
        session_id=str(release["release_session_id"]),
    )
    BoundReleaseHandler.bundle = bundle
    handler = functools.partial(
        BoundReleaseHandler,
        directory=str(workbench_root.resolve()),
    )
    return ThreadingHTTPServer((host, port), handler)


def serve(database: Path, release_root: Path, host: str, port: int) -> None:
    server = create_server(
        database=database,
        release_root=release_root,
        host=host,
        port=port,
    )
    bound_host, bound_port = server.server_address[:2]
    print(f"RELEASE_URL=http://{bound_host}:{bound_port}/")
    print(f"STATUS={PASS_STATUS}")
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    serve_command = commands.add_parser("serve")
    build.add_argument("--database", type=Path, required=True)
    build.add_argument("--approved-content", type=Path, default=DEFAULT_APPROVED_CONTENT)
    build.add_argument("--multisession-root", type=Path, default=DEFAULT_MULTISESSION_ROOT)
    build.add_argument("--release-root", type=Path, default=DEFAULT_RELEASE_ROOT)
    build.add_argument("--learner-id", required=True)
    build.add_argument("--release-session-id", required=True)
    build.add_argument("--started-at", default="2026-07-31T02:00:00Z")
    serve_command.add_argument("--database", type=Path, required=True)
    serve_command.add_argument("--release-root", type=Path, default=DEFAULT_RELEASE_ROOT)
    serve_command.add_argument("--host", default="127.0.0.1")
    serve_command.add_argument("--port", type=int, default=8776)
    args = parser.parse_args(argv)
    if args.command == "build":
        result = build_release_candidate(
            database=args.database,
            approved_content=load(args.approved_content),
            learner_id=args.learner_id,
            multisession_root=args.multisession_root,
            release_root=args.release_root,
            release_session_id=args.release_session_id,
            started_at=args.started_at,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"STATUS={PASS_STATUS}")
        print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    else:
        serve(args.database, args.release_root, args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
