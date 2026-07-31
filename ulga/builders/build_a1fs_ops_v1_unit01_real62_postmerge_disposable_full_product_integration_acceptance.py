#!/usr/bin/env python3
"""Validate Real62 Unit01 integration in a disposable full-product copy."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import shutil
import sqlite3
import threading
import urllib.request
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_v1_razq01e_unit01_approved_content_existing_qb_learner_stimulus_runtime
    as razq01e,
)
from ulga.builders import (
    build_a1fs_v1_razq01f_fullfix_real62_semantic_lexical_anchor_fallback
    as razq01f,
)
from ulga.builders import (
    build_a1fs_v1_razq01g_unit01_real_content_learner_product_release_readiness_acceptance
    as razq01g,
)
from ulga.validators import (
    validate_a1fs_v1_razq01e_unit01_approved_content_existing_qb_learner_stimulus_runtime
    as razq01e_validator,
)
from ulga.validators import (
    validate_a1fs_v1_razq01g_unit01_real_content_learner_product_release_readiness_acceptance
    as razq01g_validator,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Copies an existing accepted A1FS product root to a disposable sibling, materializes an already approved private Unit01 Real62 artifact through the existing U01QB02/U01QB03/M3/M6 authorities, runs loopback acceptance, verifies preservation and rollback simulation, and never mutates or activates the source product root; no content, second bank, planner, renderer, learner database, scoring authority, audio, A2, or Unit02-Unit24 artifact is produced."
PROGRAM_ID = "A1FS-OPS-V1"
TASK_ID = "A1FS-OPS-V1_Unit01Real62PostMergeDisposableFullProductIntegrationAcceptance"
SCHEMA_VERSION = "a1fs.ops.v1.unit01_real62_disposable_product_integration.v1"
PASS_STATUS = "PASS_A1FS_OPS_V1_UNIT01_REAL62_DISPOSABLE_FULL_PRODUCT_INTEGRATION"
RAZQ01E_PACKAGE_PASS_STATUS = "PASS_A1FS_V1_RAZQ01E_PACKAGE_VALIDATION"
REPORT_NAME = "a1fs_ops_v1_unit01_real62_disposable_integration.safe.json"
TARGET_PRODUCT_VERSION = "1.2.1"
NEXT_SHORT_STEP = "A1FS-OPS-V1_Unit01CanonicalQuestionBankVocabularyChunkSentencePrintableMasterPackage"

INTEGRATION_TABLES = frozenset({
    "lesson_assets", "response_contracts",
    "u01e_coverage_denominators", "u01e_asset_target_bindings",
    "u01qb02_metadata", "u01qb02_item_catalog", "u01qb02_session_plans",
    "u01qb02_session_items", "u01qb02_item_exposures",
    "razq01e_metadata", "razq01e_extension_items",
})


class DisposableIntegrationError(ValueError):
    """Fail-closed disposable product integration error."""


def _upg02():
    return importlib.import_module(
        "ulga.builders.build_a1fs_ops_v1_upg02_side_by_side_rebuild_atomic_activation"
    )


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DisposableIntegrationError(f"json_object_required:{path}")
    return value


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def file_digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def database_projection(database: Path) -> dict[str, Any]:
    database = Path(database)
    with sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True) as connection:
        names = [
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
            if str(row[0]) not in INTEGRATION_TABLES
        ]
        tables: dict[str, Any] = {}
        for name in names:
            columns = [
                str(row[1])
                for row in connection.execute(f'PRAGMA table_info("{name}")')
            ]
            rows = [list(row) for row in connection.execute(f'SELECT * FROM "{name}"')]
            rows.sort(key=lambda row: canonical(row))
            tables[name] = {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
            }
    return {
        "table_count": len(tables),
        "tables": {name: value["row_count"] for name, value in tables.items()},
        "sha256": digest(tables),
    }


def _product_identity(root: Path) -> dict[str, Any]:
    upg02 = _upg02()
    root = Path(root).resolve()
    version = upg02.r01._current_version(root)
    if version != TARGET_PRODUCT_VERSION:
        raise DisposableIntegrationError(f"source_product_version_invalid:{version}")
    release = root / "releases" / version
    manifest = upg02.r01.validate_release(release)
    database = root / "shared/database/learner_runtime.sqlite3"
    if not database.is_file():
        raise DisposableIntegrationError("source_learner_database_missing")
    return {
        "root": str(root),
        "version": version,
        "release_manifest_sha256": file_digest(release / "release_manifest.json"),
        "database_projection": database_projection(database),
        "product_id": manifest.get("product_id"),
        "release_id": manifest.get("release_id"),
    }


def _copy_disposable(source: Path, target: Path) -> None:
    upg02 = _upg02()
    source, target = Path(source).resolve(), Path(target).resolve()
    if source == target or source in target.parents:
        raise DisposableIntegrationError("disposable_root_must_be_outside_source")
    if target.exists():
        raise DisposableIntegrationError(f"disposable_root_already_exists:{target}")
    shutil.copytree(
        upg02.r01._win32_long_path(source),
        upg02.r01._win32_long_path(target),
        ignore=upg02._COPY_IGNORE,
    )


def _simulate_activation_rollback(disposable_root: Path) -> dict[str, Any]:
    root = Path(disposable_root).resolve()
    probe = root.with_name(root.name + ".activation-probe")
    if probe.exists():
        shutil.rmtree(probe)
    os.replace(root, probe)
    activated = probe.is_dir() and not root.exists()
    os.replace(probe, root)
    rolled_back = root.is_dir() and not probe.exists()
    if not (activated and rolled_back):
        raise DisposableIntegrationError("activation_rollback_simulation_failed")
    return {"activation_simulation_pass": True, "rollback_simulation_pass": True}


def _runtime_counts(database: Path) -> dict[str, int]:
    with sqlite3.connect(Path(database)) as connection:
        def count(table: str) -> int:
            return int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])

        return {
            "u01qb02_item_catalog": count("u01qb02_item_catalog"),
            "razq01e_extension_items": count("razq01e_extension_items"),
            "u01qb02_session_plans": count("u01qb02_session_plans"),
            "u01qb02_item_exposures": count("u01qb02_item_exposures"),
        }


def _post_json(url: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(dict(payload)).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _private_answer(database: Path, item_id: str) -> Any:
    with sqlite3.connect(Path(database)) as connection:
        row = connection.execute(
            "SELECT private_item_json FROM u01qb02_item_catalog WHERE item_id=?",
            (item_id,),
        ).fetchone()
    if row is None:
        raise DisposableIntegrationError(f"private_item_missing:{item_id}")
    return json.loads(row[0])["correct_answer"]


def run_http_canary(*, database: Path, release_root: Path) -> dict[str, Any]:
    server = razq01g.create_server(
        database=Path(database),
        release_root=Path(release_root),
        host="127.0.0.1",
        port=0,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    base = f"http://{host}:{port}"
    try:
        with urllib.request.urlopen(f"{base}/api/session", timeout=15) as response:
            session = json.loads(response.read().decode("utf-8"))
        with urllib.request.urlopen(f"{base}/index.html", timeout=15) as response:
            html_status = int(response.status)
            html_bytes = len(response.read())
        item = next(row for row in session["items"] if row["capture_enabled"] is True)
        exposed = _post_json(
            f"{base}/api/exposure",
            {
                "item_id": item["item_id"],
                "expected_session_version": session["session_version"],
            },
        )
        attempted = _post_json(
            f"{base}/api/attempt",
            {
                "item_id": item["item_id"],
                "response": _private_answer(database, item["item_id"]),
                "expected_session_version": exposed["session_version"],
            },
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=15)
    result = {
        "loopback_url": base,
        "html_status": html_status,
        "html_bytes": html_bytes,
        "session_id": session["session_id"],
        "session_item_count": session["item_count"],
        "attempted_item_id": item["item_id"],
        "attempt_outcome": attempted["outcome"],
        "m3_exposure_reused": attempted["m3_exposure_reused"],
        "m6_response_scoring_reused": attempted["m6_response_scoring_reused"],
    }
    if (
        result["html_status"] != 200
        or result["session_item_count"] != 10
        or result["attempt_outcome"] != "AUTO_PASS"
        or result["m3_exposure_reused"] is not True
        or result["m6_response_scoring_reused"] is not True
    ):
        raise DisposableIntegrationError("disposable_http_canary_failed")
    return result


def integrate_disposable_product(
    *,
    source_product_root: Path,
    disposable_product_root: Path,
    approved_content: Mapping[str, Any],
    multisession_root: Path,
    learner_id: str,
    release_session_id: str = "a1fs-ops-real62-disposable-session",
) -> dict[str, Any]:
    source_product_root = Path(source_product_root).resolve()
    disposable_product_root = Path(disposable_product_root).resolve()
    source_before = _product_identity(source_product_root)
    _copy_disposable(source_product_root, disposable_product_root)
    activation = _simulate_activation_rollback(disposable_product_root)
    disposable_identity = _product_identity(disposable_product_root)
    if disposable_identity["release_manifest_sha256"] != source_before["release_manifest_sha256"]:
        raise DisposableIntegrationError("disposable_release_identity_drift_after_copy")

    database = disposable_product_root / "shared/database/learner_runtime.sqlite3"
    before_materialization = database_projection(database)
    razq01f.install_fullfix()
    _candidate, approved_extension, initial_safe = razq01e.build_extension_package(
        approved_content
    )
    package_result = razq01e_validator.validate_package(
        approved_extension, initial_safe
    )
    if package_result.get("validation_status") != RAZQ01E_PACKAGE_PASS_STATUS:
        raise DisposableIntegrationError("razq01e_package_validation_failed")
    razq01e.materialize_runtime(database, approved_extension)
    replay = razq01e.materialize_runtime(database, approved_extension)
    after_materialization = database_projection(database)
    if after_materialization != before_materialization:
        raise DisposableIntegrationError("learner_owned_state_changed_during_materialization")
    counts = _runtime_counts(database)
    if (
        counts["u01qb02_item_catalog"] != 474
        or counts["razq01e_extension_items"] != 186
    ):
        raise DisposableIntegrationError(f"runtime_denominator_invalid:{counts}")

    release_root = disposable_product_root / "shared/real62_unit01_release_candidate"
    release = razq01g.build_release_candidate(
        database=database,
        approved_content=approved_content,
        learner_id=learner_id,
        multisession_root=Path(multisession_root),
        release_root=release_root,
        release_session_id=release_session_id,
    )
    pre = razq01g_validator.validate(
        database=database,
        approved_content=approved_content,
        multisession_root=Path(multisession_root),
        release_root=release_root,
    )
    if pre.get("validation_status") != razq01g_validator.PASS_STATUS:
        raise DisposableIntegrationError("razq01g_pre_canary_validation_failed")
    http = run_http_canary(database=database, release_root=release_root)
    post = razq01g_validator.validate(
        database=database,
        approved_content=approved_content,
        multisession_root=Path(multisession_root),
        release_root=release_root,
    )
    if (
        post.get("validation_status") != razq01g_validator.PASS_STATUS
        or post.get("exposure_count") != 1
        or post.get("attempt_count") != 1
    ):
        raise DisposableIntegrationError("razq01g_post_canary_validation_failed")

    source_after = _product_identity(source_product_root)
    if source_after != source_before:
        raise DisposableIntegrationError("source_product_root_changed")
    core = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "source_product_root": str(source_product_root),
        "disposable_product_root": str(disposable_product_root),
        "source_product_version": source_before["version"],
        "source_release_manifest_sha256": source_before["release_manifest_sha256"],
        "source_database_projection_sha256": source_before["database_projection"]["sha256"],
        "source_product_root_unchanged": True,
        "disposable_copy_validated": True,
        **activation,
        "approved_content_artifact_sha256": approved_content["artifact_sha256"],
        "approved_extension_artifact_sha256": approved_extension["artifact_sha256"],
        "base_runtime_item_count": 288,
        "extension_item_count": counts["razq01e_extension_items"],
        "combined_runtime_item_count": counts["u01qb02_item_catalog"],
        "idempotent_materialization_reused": bool(
            replay.get("base_runtime_readback", {}).get(
                "existing_materialization_reused"
            )
        ),
        "learner_owned_state_preserved_during_materialization": True,
        "release_manifest_sha256": release["release_manifest_sha256"],
        "release_session_id": release_session_id,
        "release_session_item_count": release["item_count"],
        "authoritative_extension_content_count": release[
            "authoritative_extension_content_count"
        ],
        "http_canary": http,
        "post_canary_validation_status": post["validation_status"],
        "post_canary_exposure_count": post["exposure_count"],
        "post_canary_attempt_count": post["attempt_count"],
        "formal_production_activation_approved": False,
        "production_root_mutated": False,
        "public_delivery": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
        "next_short_step": NEXT_SHORT_STEP,
    }
    report = {**core, "readback_sha256": digest(core)}
    atomic_json(
        disposable_product_root / "shared/reports" / REPORT_NAME,
        report,
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-product-root", type=Path, required=True)
    parser.add_argument("--disposable-product-root", type=Path, required=True)
    parser.add_argument("--approved-content", type=Path, required=True)
    parser.add_argument("--multisession-root", type=Path, required=True)
    parser.add_argument("--learner-id", required=True)
    parser.add_argument(
        "--release-session-id",
        default="a1fs-ops-real62-disposable-session",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = integrate_disposable_product(
        source_product_root=args.source_product_root,
        disposable_product_root=args.disposable_product_root,
        approved_content=load(args.approved_content),
        multisession_root=args.multisession_root,
        learner_id=args.learner_id,
        release_session_id=args.release_session_id,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"STATUS={PASS_STATUS}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
