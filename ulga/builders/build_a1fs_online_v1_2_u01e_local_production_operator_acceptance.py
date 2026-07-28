#!/usr/bin/env python3
"""Install A1FS V1.2 Unit 01 into the local product root and prove it read-only.

This milestone reuses the accepted S05 release builder, R01 atomic update/rollback
channel, S11 authentication boundary, and V1.2 runtime. It adds an executable
entrypoint for the generated installer, selects an existing active learner
profile instead of the S05 canary identity, and writes a redacted operator
acceptance readback after authenticated GET-only product checks.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import Counter
from contextlib import closing
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s05_release_migration_acceptance as s05,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Installs the already-approved S05 V1.2 candidate through the existing R01 "
    "atomic migration channel, selects an existing active learner profile, starts "
    "the existing authenticated localhost runtime, and performs GET-only operator "
    "acceptance. It creates no curriculum, learner content, answer, scoring rule, "
    "learner attempt, mastery decision, audio, A2 unlock, external route, or "
    "parallel state/runtime authority."
)

PROGRAM_ID = "A1FS-ONLINE-V1.2-U01E"
TASK_ID = "A1FS-ONLINE-V1.2-U01E_LocalProductionInstallAndOperatorAcceptance"
SCHEMA_VERSION = "a1fs.online.v1_2.u01e.local_production_operator_acceptance.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_2_U01E_LOCAL_PRODUCTION_INSTALL_AND_OPERATOR_ACCEPTANCE"
PRODUCT_STATUS = "A1FS_V1_2_UNIT01_LOCAL_PRODUCTION_INSTALLED_AND_OPERATOR_ACCEPTED"
NEXT_SHORT_STEP = "A1FS-ONLINE-V1.2-U01E_LocalProductionAcceptanceReadback"
DEFAULT_READBACK_NAME = "a1fs_v1_2_u01e_operator_acceptance.safe.json"
LOCAL_LEARNER_ENV = "A1FS_LOCAL_LEARNER_ID"


class LocalProductionAcceptanceError(ValueError):
    """Fail-closed local installation or operator acceptance error."""


# The accepted S05 core launches the module named here. Point it at this
# executable facade so generated installers and detached production starts run.
MODULE = "ulga.builders.build_a1fs_online_v1_2_u01e_local_production_operator_acceptance"
s05._core.MODULE = MODULE


def _required_environment() -> dict[str, str]:
    values: dict[str, str] = {}
    for name in s05._core.r01.REQUIRED_ENV:
        value = str(os.environ.get(name) or "").strip()
        if not value:
            raise LocalProductionAcceptanceError(f"MISSING_ENV={name}")
        values[name] = value
    return values


def _active_learner_id(database: Path) -> tuple[str, str]:
    requested = str(os.environ.get(LOCAL_LEARNER_ENV) or "").strip()
    with closing(sqlite3.connect(database)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT learner_id FROM learner_profiles "
            "WHERE profile_state='ACTIVE' ORDER BY learner_id"
        ).fetchall()
    active = [str(row["learner_id"]) for row in rows]
    if requested:
        if requested not in active:
            raise LocalProductionAcceptanceError(
                f"CONFIGURED_ACTIVE_LEARNER_NOT_FOUND={requested}"
            )
        return requested, "EXPLICIT_ENV_SELECTION"
    if len(active) == 1:
        return active[0], "SINGLE_ACTIVE_PROFILE_SELECTION"
    if not active:
        raise LocalProductionAcceptanceError(
            "ACTIVE_LEARNER_PROFILE_REQUIRED;SET_A1FS_LOCAL_LEARNER_ID_AFTER_ENROLLMENT"
        )
    raise LocalProductionAcceptanceError(
        "MULTIPLE_ACTIVE_LEARNERS_REQUIRE_A1FS_LOCAL_LEARNER_ID"
    )


def installed_product_readback(product_root: Path) -> dict[str, Any]:
    (
        root,
        manifest,
        bundles,
        sequence,
        database,
        _auth,
        _state,
        _graph,
        _static,
        registry,
    ) = s05._core._load_v12(product_root)
    unit01_counts = {
        skill: len(bundles[s05._core.m01.LESSON_IDS[skill]]["assets"])
        for skill in s05._core.EXPECTED_UNIT01_COUNTS
    }
    if unit01_counts != s05._core.EXPECTED_UNIT01_COUNTS:
        raise LocalProductionAcceptanceError(
            f"UNIT01_RUNTIME_COUNTS_INVALID={unit01_counts}"
        )
    asset_count = sum(len(bundle.get("assets", [])) for bundle in bundles.values())
    if asset_count != s05._core.EXPECTED_TARGET_ASSET_COUNT:
        raise LocalProductionAcceptanceError(
            f"PRODUCT_ASSET_COUNT_INVALID={asset_count}"
        )
    if len(bundles) != s05._core.EXPECTED_LESSON_COUNT or len(sequence) != s05._core.EXPECTED_UNIT_COUNT:
        raise LocalProductionAcceptanceError("PRODUCT_DENOMINATOR_INVALID")
    status_counts = Counter(str(row.get("runtime_status") or "") for row in registry)
    if len(registry) != s05._core.s04.EXPECTED_TOTAL_COUNT or status_counts != Counter({"RUNTIME_ACTIVE": 24}):
        raise LocalProductionAcceptanceError(
            f"TARGET_REGISTRY_RUNTIME_INVALID={dict(status_counts)}"
        )
    with closing(sqlite3.connect(database)) as connection:
        names = s05._core.s04.table_names(connection)
        required = {
            "lesson_assets",
            "response_contracts",
            "u01e_asset_target_bindings",
            "learner_profiles",
        }
        missing = sorted(required - names)
        if missing:
            raise LocalProductionAcceptanceError(
                f"PRODUCTION_DATABASE_TABLE_MISSING={missing[0]}"
            )
        new_assets = int(
            connection.execute(
                "SELECT COUNT(*) FROM lesson_assets WHERE asset_key LIKE 'U01E-S03-%'"
            ).fetchone()[0]
        )
        new_contracts = int(
            connection.execute(
                "SELECT COUNT(*) FROM response_contracts WHERE asset_key LIKE 'U01E-S03-%'"
            ).fetchone()[0]
        )
        target_bindings = int(
            connection.execute(
                "SELECT COUNT(*) FROM u01e_asset_target_bindings"
            ).fetchone()[0]
        )
        active_profiles = int(
            connection.execute(
                "SELECT COUNT(*) FROM learner_profiles WHERE profile_state='ACTIVE'"
            ).fetchone()[0]
        )
    if (new_assets, new_contracts, target_bindings) != (13, 13, 24):
        raise LocalProductionAcceptanceError(
            "PRODUCTION_MIGRATION_ROWS_INVALID="
            f"assets:{new_assets},contracts:{new_contracts},bindings:{target_bindings}"
        )
    return {
        "product_version": s05._core.TARGET_VERSION,
        "release_id": str(manifest.get("release_id") or s05._core.RELEASE_ID),
        "release_checksums_valid": True,
        "unit_count": len(sequence),
        "lesson_count": len(bundles),
        "asset_count": asset_count,
        "unit01_activity_count": len(registry),
        "unit01_counts": unit01_counts,
        "new_asset_row_count": new_assets,
        "new_response_contract_count": new_contracts,
        "target_binding_count": target_bindings,
        "active_learner_profile_count": active_profiles,
        "product_root_present": root.is_dir(),
    }


def authenticated_http_readback(
    *,
    port: int,
    request_runner: Callable[..., tuple[Any, Mapping[str, str]]] | None = None,
) -> dict[str, Any]:
    environment = _required_environment()
    request = request_runner or s05._core.s17.s16.s15.s11._request
    origin = f"http://127.0.0.1:{int(port)}"
    login, headers = request(
        int(port),
        "POST",
        "/auth/login",
        {
            "username": environment["A1FS_S11_AUTH_USERNAME"],
            "password": environment["A1FS_S11_AUTH_PASSWORD"],
        },
        origin=origin,
    )
    cookie = str(headers.get("Set-Cookie") or "").split(";", 1)[0]
    if not cookie or not isinstance(login, Mapping) or not login.get("csrf_token"):
        raise LocalProductionAcceptanceError("OPERATOR_LOGIN_INVALID")
    bootstrap, _ = request(int(port), "GET", "/api/bootstrap", cookie=cookie)
    progress, _ = request(int(port), "GET", "/api/progress", cookie=cookie)
    coverage, _ = request(int(port), "GET", "/api/unit01-coverage", cookie=cookie)
    rendered = json.dumps(bootstrap, ensure_ascii=False, sort_keys=True)
    if len(bootstrap.get("units", [])) != 24 or "U01E-S03-C05-W01" not in rendered:
        raise LocalProductionAcceptanceError("OPERATOR_BOOTSTRAP_V12_ITEM_BANK_MISSING")
    if progress.get("product_version") != s05._core.TARGET_VERSION:
        raise LocalProductionAcceptanceError("OPERATOR_PROGRESS_VERSION_INVALID")
    if coverage.get("curriculum_item_count") != s05._core.s04.EXPECTED_TOTAL_COUNT:
        raise LocalProductionAcceptanceError("OPERATOR_COVERAGE_DENOMINATOR_INVALID")
    practised = int(
        coverage.get("learner_evidence_summary", {}).get(
            "distinct_attempted_item_count", 0
        )
    )
    return {
        "authenticated_login_pass": True,
        "bootstrap_pass": True,
        "progress_pass": True,
        "coverage_endpoint_pass": True,
        "unit_count": len(bootstrap.get("units", [])),
        "unit01_activity_count": int(coverage["curriculum_item_count"]),
        "practised_item_count": practised,
        "get_only_operator_acceptance": True,
        "raw_response_exported": False,
        "credential_exported": False,
    }


def serve(*, product_root: Path, host: str, port: int) -> None:
    if not s05._core.s17.s16.s15.s11._is_loopback(host):
        raise LocalProductionAcceptanceError(f"NON_LOOPBACK_HOST_FORBIDDEN={host}")
    (
        _root,
        _manifest,
        bundles,
        sequence,
        database,
        auth,
        state,
        graph,
        static,
        registry,
    ) = s05._core._load_v12(product_root)
    learner_id, _selection = _active_learner_id(database)
    config = s05._core.s17.s16.s15.s13.PersistentBoundaryConfig.from_environment(
        host=host,
        port=port,
        revocation_db_path=auth,
    )
    server = s05._core.V12Server(
        (host, port),
        s05._core.make_app(
            database=database,
            bundles=bundles,
            sequence=sequence,
            graph_path=graph,
            state_root=state,
            registry=registry,
            learner_id=learner_id,
        ),
        static,
        config,
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()


def install_candidate(*, product_root: Path, candidate: Path) -> dict[str, Any]:
    source = s05._core.source_product(product_root)
    overlay = s05._core.build_runtime_overlay(source)
    return s05._core.install_with_migration(
        product_root=product_root,
        candidate=Path(candidate).resolve(),
        overlay=overlay,
    )


def operator_acceptance(
    *,
    product_root: Path,
    port: int,
    output_path: Path,
) -> dict[str, Any]:
    installed = installed_product_readback(product_root)
    start_result = s05._core.start(product_root=product_root, port=int(port))
    http = authenticated_http_readback(port=int(port))
    readback_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "installed_product": installed,
        "runtime_start": {
            "status": str(start_result.get("status") or ""),
            "version": str(start_result.get("version") or ""),
            "localhost_only": True,
        },
        "operator_http_acceptance": http,
        "boundaries": {
            "operator_acceptance_get_only": True,
            "learner_attempt_created": False,
            "mastery_write_enabled": False,
            "listening_enabled": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
            "external_binding_enabled": False,
            "unit02_modified": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    readback = {
        **readback_core,
        "report_sha256": s05._core.digest(readback_core),
    }
    s05._core.write_json(Path(output_path).resolve(), readback)
    return readback


def install_and_accept(
    *,
    product_root: Path,
    code_root: Path,
    output_root: Path,
    port: int,
    candidate: Path | None = None,
) -> dict[str, Any]:
    root = Path(product_root).resolve()
    output_root = Path(output_root).resolve()
    try:
        output_root.relative_to(root)
    except ValueError:
        pass
    else:
        raise LocalProductionAcceptanceError(
            "OUTPUT_ROOT_MUST_BE_OUTSIDE_PRODUCT_ROOT"
        )
    _required_environment()
    current = s05._core.r01._current_version(root)
    if current == s05._core.TARGET_VERSION:
        return operator_acceptance(
            product_root=root,
            port=port,
            output_path=root / "shared/operator_readbacks" / DEFAULT_READBACK_NAME,
        )
    if current != s05._core.SOURCE_VERSION:
        raise LocalProductionAcceptanceError(
            f"SOURCE_VERSION_REQUIRED={s05._core.SOURCE_VERSION};ACTUAL={current}"
        )
    pid_path = root / "shared/a1fs_v1.pid"
    if pid_path.is_file():
        pid = int(pid_path.read_text(encoding="ascii").strip())
        if s05._core.r01._pid_alive(pid):
            raise LocalProductionAcceptanceError(
                f"STOP_A1FS_BEFORE_UPDATE_PID={pid}"
            )
        pid_path.unlink(missing_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)
    if candidate is None:
        receipt, _safe = s05.materialize(
            product_root=root,
            code_root=Path(code_root).resolve(),
            output_path=output_root / "s05.private.json",
            report_path=output_root / "s05.safe.json",
        )
        candidate = Path(receipt["runtime_outputs"]["candidate_root"])
    install_result = install_candidate(product_root=root, candidate=candidate)
    try:
        acceptance = operator_acceptance(
            product_root=root,
            port=port,
            output_path=root / "shared/operator_readbacks" / DEFAULT_READBACK_NAME,
        )
    except Exception as exc:
        rollback_notes: list[str] = []
        try:
            if (root / "shared/a1fs_v1.pid").is_file():
                s05._core.r01.stop(product_root=root, port=port)
            rollback_notes.append("runtime_stopped")
        except Exception as stop_exc:
            rollback_notes.append(f"stop_failed:{stop_exc}")
        try:
            result = s05._core.r01.rollback(
                product_root=root,
                version=s05._core.SOURCE_VERSION,
            )
            rollback_notes.append(str(result.get("status") or "rollback_complete"))
        except Exception as rollback_exc:
            rollback_notes.append(f"rollback_failed:{rollback_exc}")
        raise LocalProductionAcceptanceError(
            "POST_INSTALL_OPERATOR_ACCEPTANCE_FAILED;"
            + ";".join(rollback_notes)
            + f";cause={exc}"
        ) from exc
    return {
        **acceptance,
        "installation": {
            "status": str(install_result.get("status") or "PASS"),
            "source_version": s05._core.SOURCE_VERSION,
            "target_version": s05._core.TARGET_VERSION,
            "atomic_migration_channel_reused": True,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    install = commands.add_parser("install")
    install.add_argument("--product-root", type=Path, required=True)
    install.add_argument("--candidate", type=Path, required=True)

    server = commands.add_parser("serve")
    server.add_argument("--product-root", type=Path, required=True)
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=s05._core.r01.DEFAULT_PORT)

    accept = commands.add_parser("operator-acceptance")
    accept.add_argument("--product-root", type=Path, required=True)
    accept.add_argument("--port", type=int, default=s05._core.r01.DEFAULT_PORT)
    accept.add_argument("--output", type=Path)

    run = commands.add_parser("install-and-accept")
    run.add_argument("--product-root", type=Path, required=True)
    run.add_argument("--code-root", type=Path, default=Path(__file__).resolve().parents[2])
    run.add_argument("--output-root", type=Path, required=True)
    run.add_argument("--port", type=int, default=s05._core.r01.DEFAULT_PORT)
    run.add_argument("--candidate", type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "install":
            print(
                json.dumps(
                    install_candidate(
                        product_root=args.product_root,
                        candidate=args.candidate,
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif args.command == "serve":
            serve(
                product_root=args.product_root,
                host=args.host,
                port=args.port,
            )
        elif args.command == "operator-acceptance":
            output = args.output or (
                Path(args.product_root).resolve()
                / "shared/operator_readbacks"
                / DEFAULT_READBACK_NAME
            )
            print(
                json.dumps(
                    operator_acceptance(
                        product_root=args.product_root,
                        port=args.port,
                        output_path=output,
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(
                json.dumps(
                    install_and_accept(
                        product_root=args.product_root,
                        code_root=args.code_root,
                        output_root=args.output_root,
                        port=args.port,
                        candidate=args.candidate,
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        return 0
    except (
        LocalProductionAcceptanceError,
        s05._core.S05ReleaseError,
        s05._core.static_adapter.S05StaticError,
        s05._core.s03.S03ItemBankError,
        s05._core.s04.S04CoverageError,
        s05._core.r01.ProductRootError,
        sqlite3.Error,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
