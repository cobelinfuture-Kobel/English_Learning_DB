#!/usr/bin/env python3
"""Materialize, validate, accept, and serve the Unit01 learner package locally.

This is the single pull-to-run operator entry for an existing Real62 disposable
A1FS V1.2.1 product. It reuses the merged Chromium materializer and validator,
then serves the resulting Pre-learning and QuestionBank routes through the real
V1.2.1 learner application, authentication boundary, APIs, state, and database.
No release version, production root, question authority, or learner state engine
is created.
"""
from __future__ import annotations

import argparse
import json
import os
import threading
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from ulga.builders import (
    build_a1fs_online_v1_2_1_u01f_patch_release as v121,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_student_package_chromium_main_product_entry_acceptance
    as entry_builder,
)
from ulga.validators import (
    validate_a1fs_ops_v1_unit01_student_package_chromium_main_product_entry_acceptance
    as entry_validator,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Runs the merged learner-only Unit01 materializer and independent validator "
    "against an existing disposable V1.2.1 product, then adds authenticated nested "
    "static routes to the real V1.2.1 local runtime. It creates no content, answer, "
    "bank, planner, learner-state engine, scoring authority, release version, audio, "
    "A2 content, production activation, or Unit02-Unit24 artifact."
)
PROGRAM_ID = "A1FS-OPS-V1"
TASK_ID = (
    "A1FS-OPS-V1_"
    "Unit01StudentPackageLocalPrivateMaterializationAndOperatorReadback"
)
SCHEMA_VERSION = "a1fs.ops.v1.unit01_student_local_private_operator.v1"
PASS_STATUS = "PASS_A1FS_OPS_V1_UNIT01_STUDENT_LOCAL_PRIVATE_OPERATOR"
REPORT_NAME = "unit01_student_package_operator_readback.safe.json"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
NEXT_SHORT_STEP = (
    "A1FS-OPS-V1_"
    "Unit01StudentPackageLocalPrivateOperatorVisualReadbackAndV121ReleaseDecision"
)


class LocalPrivateOperatorError(ValueError):
    """Fail-closed local operator materialization or runtime error."""


def _safe_report_path(product_root: Path, output_path: Path | None = None) -> Path:
    if output_path is not None:
        return Path(output_path).resolve()
    return Path(product_root).resolve() / "shared/reports" / REPORT_NAME


def _relative(product_root: Path, path: Path) -> str:
    root = Path(product_root).resolve()
    candidate = Path(path).resolve()
    try:
        return candidate.relative_to(root).as_posix()
    except ValueError as exc:
        raise LocalPrivateOperatorError(
            f"operator_path_outside_product:{candidate.name}"
        ) from exc


class OperatorV121Handler(v121.V121Handler):
    """V1.2.1 handler plus authenticated learner-package static routes."""

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        route = entry_builder.ENTRY_CONTENT_TYPES.get(path)
        if route is None:
            super().do_GET()
            return
        if not self._transport_valid():
            return
        claims = self._claims()
        if claims is None:
            self._json(401, {"error": "authentication_required"})
            return
        relative_name, content_type = route
        self._static(
            self.secure_static_root
            / entry_builder.ENTRY_DIRECTORY
            / relative_name,
            content_type,
        )


class OperatorV121Server(ThreadingHTTPServer):
    """Real V1.2.1 application server with the accepted nested static routes."""

    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        app: v121.V121Application,
        static_root: Path,
        config: Any,
    ):
        if not v121.v12._core.s17.s16.s15.s11._is_loopback(address[0]):
            raise LocalPrivateOperatorError(
                f"non_loopback_host_forbidden:{address[0]}"
            )
        self.app = app
        self.static_root = Path(static_root)
        self.secure_static_root = Path(static_root)
        self.config = config
        super().__init__(address, OperatorV121Handler)
        self.config.bind_local_port(int(self.server_address[1]))


def load_operator_runtime(product_root: Path) -> dict[str, Any]:
    """Load the actual installed V1.2.1 runtime without changing its release."""
    v121.activate_runtime_patch()
    (
        root,
        manifest,
        bundles,
        sequence,
        database,
        auth,
        state,
        graph,
        static,
        registry,
    ) = v121._load_v121(Path(product_root).resolve())
    learner_id, learner_selection = v121.v12_operator._active_learner_id(database)
    entry_result = entry_builder.validate_main_entry(static)
    release_root = root / "releases" / v121.TARGET_VERSION
    release_manifest = v121.r01.validate_release(release_root)
    if release_manifest.get("product_version") != v121.TARGET_VERSION:
        raise LocalPrivateOperatorError("operator_release_version_invalid")
    return {
        "root": root,
        "manifest": manifest,
        "bundles": bundles,
        "sequence": sequence,
        "database": database,
        "auth": auth,
        "state": state,
        "graph": graph,
        "static": static,
        "registry": registry,
        "learner_id": learner_id,
        "learner_selection": learner_selection,
        "entry_result": entry_result,
        "release_manifest": release_manifest,
    }


def make_operator_server(
    *,
    product_root: Path,
    host: str = DEFAULT_HOST,
    port: int = 0,
    config: Any | None = None,
) -> tuple[OperatorV121Server, dict[str, Any]]:
    runtime = load_operator_runtime(product_root)
    if config is None:
        config = (
            v121.v12._core.s17.s16.s15.s13.PersistentBoundaryConfig.from_environment(
                host=host,
                port=int(port),
                revocation_db_path=runtime["auth"],
            )
        )
    app = v121.make_app(
        database=runtime["database"],
        bundles=runtime["bundles"],
        sequence=runtime["sequence"],
        graph_path=runtime["graph"],
        state_root=runtime["state"],
        registry=runtime["registry"],
        learner_id=runtime["learner_id"],
    )
    server = OperatorV121Server(
        (host, int(port)),
        app,
        runtime["static"],
        config,
    )
    return server, runtime


def _credentials_from_environment() -> dict[str, str]:
    value = v121.v12_operator._required_environment()
    username = str(value.get("A1FS_S11_AUTH_USERNAME") or "")
    password = str(value.get("A1FS_S11_AUTH_PASSWORD") or "")
    if not username or not password:
        raise LocalPrivateOperatorError("operator_credentials_missing")
    return {"username": username, "password": password}


def real_runtime_http_readback(
    *,
    server: OperatorV121Server,
    credentials: Mapping[str, str],
) -> dict[str, Any]:
    """Prove the new routes coexist with the real V1.2.1 learner APIs."""
    request = v121.v12._core.s17.s16.s15.s11._request
    port = int(server.server_address[1])
    origin = f"http://127.0.0.1:{port}"
    prelearning_path = (
        f"/{entry_builder.ENTRY_DIRECTORY}/prelearning.html"
    )
    questionbank_path = (
        f"/{entry_builder.ENTRY_DIRECTORY}/questionbank.html"
    )
    unauthenticated, unauth_headers = request(
        port,
        "GET",
        prelearning_path,
        expected_status=401,
    )
    if unauthenticated.get("error") != "authentication_required":
        raise LocalPrivateOperatorError(
            "operator_unauthenticated_entry_not_blocked"
        )
    login, login_headers = request(
        port,
        "POST",
        "/auth/login",
        {
            "username": str(credentials.get("username") or ""),
            "password": str(credentials.get("password") or ""),
        },
        origin=origin,
    )
    cookie = str(login_headers.get("Set-Cookie") or "").split(";", 1)[0]
    if not cookie or not login.get("csrf_token"):
        raise LocalPrivateOperatorError("operator_login_invalid")
    bootstrap, bootstrap_headers = request(
        port,
        "GET",
        "/api/bootstrap",
        cookie=cookie,
    )
    progress, progress_headers = request(
        port,
        "GET",
        "/api/progress",
        cookie=cookie,
    )
    prelearning, prelearning_headers = request(
        port,
        "GET",
        prelearning_path,
        cookie=cookie,
        expect_json=False,
    )
    questionbank, questionbank_headers = request(
        port,
        "GET",
        questionbank_path,
        cookie=cookie,
        expect_json=False,
    )
    if len(bootstrap.get("units", [])) != v121.EXPECTED_UNIT_COUNT:
        raise LocalPrivateOperatorError("operator_bootstrap_unit_count_invalid")
    if progress.get("product_version") != v121.TARGET_VERSION:
        raise LocalPrivateOperatorError("operator_progress_version_invalid")
    if "Part 1" not in prelearning or "Part 6" not in prelearning:
        raise LocalPrivateOperatorError("operator_prelearning_content_invalid")
    if "Phrase 1" not in questionbank or "connected sentences" not in questionbank:
        raise LocalPrivateOperatorError("operator_questionbank_content_invalid")
    headers = (
        unauth_headers,
        bootstrap_headers,
        progress_headers,
        prelearning_headers,
        questionbank_headers,
    )
    if any(row.get("X-Frame-Options") != "DENY" for row in headers):
        raise LocalPrivateOperatorError("operator_security_headers_invalid")
    return {
        "loopback_only": True,
        "port": port,
        "unauthenticated_prelearning_status": 401,
        "authenticated_login_pass": True,
        "authenticated_bootstrap_status": 200,
        "authenticated_progress_status": 200,
        "authenticated_prelearning_status": 200,
        "authenticated_questionbank_status": 200,
        "unit_count": len(bootstrap.get("units", [])),
        "product_version": str(progress.get("product_version") or ""),
        "prelearning_marker_pass": True,
        "questionbank_marker_pass": True,
        "security_headers_pass": True,
        "cookie_http_only": "HttpOnly"
        in str(login_headers.get("Set-Cookie") or ""),
        "cookie_same_site_strict": "SameSite=Strict"
        in str(login_headers.get("Set-Cookie") or ""),
        "real_v121_application_used": True,
        "real_learner_database_used": True,
        "real_progress_api_used": True,
    }


def materialize_and_accept(
    *,
    product_root: Path,
    approved_content: Mapping[str, Any],
    chromium_path: Path | None = None,
    output_path: Path | None = None,
    config: Any | None = None,
    credentials: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Materialize, independently validate, and probe the real local runtime."""
    root = Path(product_root).resolve()
    entry_report = entry_builder.build_acceptance(
        disposable_product_root=root,
        approved_content=approved_content,
        chromium_path=chromium_path,
    )
    entry_validation = entry_validator.validate(
        disposable_product_root=root,
        approved_content=approved_content,
    )
    if entry_validation.get("validation_status") != entry_validator.PASS_STATUS:
        raise LocalPrivateOperatorError(
            "entry_validation_failed:"
            + "|".join(str(row) for row in entry_validation.get("errors") or [])
        )
    server, runtime = make_operator_server(
        product_root=root,
        host=DEFAULT_HOST,
        port=0,
        config=config,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        http = real_runtime_http_readback(
            server=server,
            credentials=credentials or _credentials_from_environment(),
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)
        if thread.is_alive():
            raise LocalPrivateOperatorError(
                "operator_acceptance_server_thread_did_not_stop"
            )
    package_root = root / entry_builder.master.DEFAULT_RELATIVE_OUTPUT
    entry_report_path = package_root / entry_builder.REPORT_NAME
    release_root = root / "releases" / v121.TARGET_VERSION
    core = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "product_version": v121.TARGET_VERSION,
        "runtime_item_count": int(entry_report["runtime_item_count"]),
        "entry_acceptance_status": str(entry_report["status"]),
        "entry_acceptance_readback_sha256": str(
            entry_report["readback_sha256"]
        ),
        "entry_validation_status": str(entry_validation["validation_status"]),
        "entry_report_path": _relative(root, entry_report_path),
        "operator_report_path": _relative(
            root,
            _safe_report_path(root, output_path),
        ),
        "release_manifest_path": _relative(
            root,
            release_root / "release_manifest.json",
        ),
        "release_checksums_path": _relative(
            root,
            release_root / "checksums.json",
        ),
        "learner_entry_root": _relative(
            root,
            runtime["static"] / entry_builder.ENTRY_DIRECTORY,
        ),
        "runtime_http_readback": http,
        "real_v121_application_used": True,
        "real_learner_database_used": True,
        "existing_auth_boundary_reused": True,
        "existing_progress_api_reused": True,
        "existing_question_bank_reused": True,
        "second_question_bank_created": False,
        "formal_production_activation_approved": False,
        "production_root_mutated": False,
        "public_delivery": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
        "secrets_serialized": False,
        "absolute_local_paths_serialized": False,
        "next_short_step": NEXT_SHORT_STEP,
    }
    report = {**core, "readback_sha256": entry_builder.digest(core)}
    report_path = _safe_report_path(root, output_path)
    entry_builder.atomic_json(report_path, report)
    return report


def serve(
    *,
    product_root: Path,
    approved_content: Mapping[str, Any],
    host: str,
    port: int,
    open_browser: bool = False,
) -> None:
    """Serve the already materialized package through the real local runtime."""
    validation = entry_validator.validate(
        disposable_product_root=Path(product_root),
        approved_content=approved_content,
    )
    if validation.get("validation_status") != entry_validator.PASS_STATUS:
        raise LocalPrivateOperatorError(
            "serve_validation_failed:"
            + "|".join(str(row) for row in validation.get("errors") or [])
        )
    server, _runtime = make_operator_server(
        product_root=Path(product_root),
        host=host,
        port=int(port),
    )
    actual_port = int(server.server_address[1])
    url = f"http://127.0.0.1:{actual_port}/"
    print(f"STATUS={PASS_STATUS}")
    print(f"LOCAL_URL={url}")
    print(
        "PRELEARNING_URL="
        f"http://127.0.0.1:{actual_port}/"
        f"{entry_builder.ENTRY_DIRECTORY}/prelearning.html"
    )
    print(
        "QUESTIONBANK_URL="
        f"http://127.0.0.1:{actual_port}/"
        f"{entry_builder.ENTRY_DIRECTORY}/questionbank.html"
    )
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    accept = subparsers.add_parser("accept")
    accept.add_argument("--product-root", type=Path, required=True)
    accept.add_argument("--approved-content", type=Path, required=True)
    accept.add_argument("--chromium-path", type=Path)
    accept.add_argument("--output-path", type=Path)

    local_serve = subparsers.add_parser("serve")
    local_serve.add_argument("--product-root", type=Path, required=True)
    local_serve.add_argument("--approved-content", type=Path, required=True)
    local_serve.add_argument("--host", default=DEFAULT_HOST)
    local_serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    local_serve.add_argument("--open-browser", action="store_true")

    run = subparsers.add_parser("run")
    run.add_argument("--product-root", type=Path, required=True)
    run.add_argument("--approved-content", type=Path, required=True)
    run.add_argument("--chromium-path", type=Path)
    run.add_argument("--output-path", type=Path)
    run.add_argument("--host", default=DEFAULT_HOST)
    run.add_argument("--port", type=int, default=DEFAULT_PORT)
    run.add_argument("--open-browser", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    approved_content = entry_builder.load(args.approved_content)
    if args.command in {"accept", "run"}:
        report = materialize_and_accept(
            product_root=args.product_root,
            approved_content=approved_content,
            chromium_path=args.chromium_path,
            output_path=args.output_path,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"STATUS={report['status']}")
        print(f"NEXT_SHORT_STEP={report['next_short_step']}")
    if args.command in {"serve", "run"}:
        serve(
            product_root=args.product_root,
            approved_content=approved_content,
            host=args.host,
            port=args.port,
            open_browser=bool(args.open_browser),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
