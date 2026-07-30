#!/usr/bin/env python3
"""Pull-to-run A1FS V1.2.1 local runtime.

This module starts the repository-packaged product directly. It initializes
blank local state from clean seeds on first run; it does not install, upgrade,
rebuild, migrate, activate, or rename a product root.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.request import urlopen

from ulga.builders import (
    build_a1fs_online_v1_2_u01e_local_production_operator_acceptance as operator,
)

TASK_ID = "A1FS-V1.2.1_WorkingV120GoldenRuntimeInspectionAndPullToRunRebuild"
PRODUCT_VERSION = "1.2.1"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_LEARNER_ID = "A1FS_V121_LOCAL_LEARNER"
PRODUCT_ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = PRODUCT_ROOT / "product_manifest.json"
MODULE = "product.a1fs_v1_2_1.runtime_server"


class PullToRunError(ValueError):
    """Fail-closed pull-to-run product error."""


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PullToRunError(f"json_not_object:{path}")
    return value


def _relative(value: str) -> str:
    normalized = str(value).replace("\\", "/")
    path = Path(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts or ":" in normalized:
        raise PullToRunError(f"manifest_path_not_relative:{value}")
    return normalized


def _resolve_product(relative: str) -> Path:
    candidate = (PRODUCT_ROOT / _relative(relative)).resolve()
    try:
        candidate.relative_to(PRODUCT_ROOT)
    except ValueError as exc:
        raise PullToRunError(f"product_path_escape:{relative}") from exc
    return candidate


def _state_root() -> Path:
    configured = str(os.environ.get("A1FS_V121_STATE_ROOT") or "").strip()
    return Path(configured).resolve() if configured else (PRODUCT_ROOT / "local_state").resolve()


def _resolve_state(relative: str) -> Path:
    manifest = _read_json(MANIFEST_PATH)
    default_state = (PRODUCT_ROOT / "local_state").resolve()
    configured = _state_root()
    relative_path = Path(_relative(relative))
    try:
        suffix = relative_path.relative_to("local_state")
    except ValueError:
        return _resolve_product(relative)
    candidate = (configured / suffix).resolve()
    if configured == default_state:
        try:
            candidate.relative_to(PRODUCT_ROOT)
        except ValueError as exc:
            raise PullToRunError(f"state_path_escape:{relative}") from exc
    return candidate


def _copy_seed(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(source, target)


def _ensure_state() -> dict[str, Path]:
    manifest = _read_json(MANIFEST_PATH)
    database = _resolve_state(str(manifest["shared_database_path"]))
    auth = _resolve_state(str(manifest["shared_auth_state_path"]))
    learner_state = _resolve_state(str(manifest["shared_learner_state_root"]))
    logs = _resolve_state(str(manifest["logs_path"]))
    pid = _resolve_state(str(manifest["pid_path"]))
    _copy_seed(_resolve_product(str(manifest["database_seed_path"])), database)
    _copy_seed(_resolve_product(str(manifest["auth_seed_path"])), auth)
    learner_state.mkdir(parents=True, exist_ok=True)
    (learner_state / DEFAULT_LEARNER_ID).mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    return {
        "database": database,
        "auth": auth,
        "learner_state": learner_state,
        "logs": logs,
        "pid": pid,
    }


def _load_runtime() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, int], list[dict[str, Any]], dict[str, Path]]:
    manifest = _read_json(MANIFEST_PATH)
    state = _ensure_state()
    bundles = _read_json(_resolve_product(str(manifest["bundle_registry_path"])))
    raw_sequence = _read_json(_resolve_product(str(manifest["sequence_path"])))
    sequence = {str(key): int(value) for key, value in raw_sequence.items()}
    registry = operator.s05._core.load_registry(PRODUCT_ROOT, manifest)
    asset_count = sum(len(bundle.get("assets", [])) for bundle in bundles.values())
    expected = (
        int(manifest["unit_count"]),
        int(manifest["lesson_count"]),
        int(manifest["asset_count"]),
    )
    actual = (len(sequence), len(bundles), asset_count)
    if actual != expected:
        raise PullToRunError(f"runtime_denominator_invalid:{actual}")
    return manifest, bundles, sequence, registry, state


def _app() -> Any:
    manifest, bundles, sequence, registry, state = _load_runtime()
    return operator.s05._core.make_app(
        database=state["database"],
        bundles=bundles,
        sequence=sequence,
        graph_path=_resolve_product(str(manifest["graph_path"])),
        state_root=state["learner_state"],
        registry=registry,
        learner_id=DEFAULT_LEARNER_ID,
    )


def serve(*, host: str, port: int) -> None:
    if not operator.s05._core.s17.s16.s15.s11._is_loopback(host):
        raise PullToRunError(f"non_loopback_host_forbidden:{host}")
    manifest, _bundles, _sequence, _registry, state = _load_runtime()
    config = operator.s05._core.s17.s16.s15.s13.PersistentBoundaryConfig.from_environment(
        host=host,
        port=port,
        revocation_db_path=state["auth"],
    )
    server = operator.s05._core.V12Server(
        (host, port),
        _app(),
        _resolve_product(str(manifest["secure_static_root"])),
        config,
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return pid > 0


def _health(port: int, timeout: float = 2.0) -> bool:
    try:
        with urlopen(f"http://127.0.0.1:{int(port)}/api/health", timeout=timeout) as response:
            value = json.loads(response.read().decode("utf-8"))
        return value.get("status") == "PASS" and value.get("authentication_required") is True
    except Exception:
        return False


def _required_environment() -> None:
    missing = [
        name
        for name in ("A1FS_S11_AUTH_USERNAME", "A1FS_S11_AUTH_PASSWORD", "A1FS_S11_SESSION_SECRET")
        if not str(os.environ.get(name) or "").strip()
    ]
    if missing:
        raise PullToRunError(f"MISSING_ENV={missing[0]}")


def start(*, host: str, port: int) -> dict[str, Any]:
    _required_environment()
    state = _ensure_state()
    pid_path = state["pid"]
    if pid_path.exists():
        pid = int(pid_path.read_text(encoding="ascii").strip())
        if _pid_alive(pid) and _health(port):
            return {"status": "ALREADY_RUNNING", "pid": pid, "version": PRODUCT_VERSION, "url": f"http://127.0.0.1:{port}"}
        pid_path.unlink(missing_ok=True)
    with socket.socket() as probe:
        if probe.connect_ex((host, int(port))) == 0:
            raise PullToRunError(f"PORT_IN_USE={port}")
    env = os.environ.copy()
    repo_root = str(PRODUCT_ROOT.parents[1])
    env["PYTHONPATH"] = repo_root + os.pathsep + env.get("PYTHONPATH", "")
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    with (state["logs"] / "a1fs_v1_2_1.stdout.log").open("ab") as stdout, (
        state["logs"] / "a1fs_v1_2_1.stderr.log"
    ).open("ab") as stderr:
        process = subprocess.Popen(
            [sys.executable, "-m", MODULE, "serve", "--host", host, "--port", str(port)],
            cwd=repo_root,
            env=env,
            stdout=stdout,
            stderr=stderr,
            stdin=subprocess.DEVNULL,
            creationflags=flags,
            close_fds=True,
        )
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(str(process.pid) + "\n", encoding="ascii")
    for _ in range(40):
        if process.poll() is not None:
            pid_path.unlink(missing_ok=True)
            raise PullToRunError(f"PROCESS_EXITED={process.returncode}")
        if _health(port, 1.0):
            return {
                "status": "PASS_A1FS_V121_STARTED",
                "pid": process.pid,
                "version": PRODUCT_VERSION,
                "url": f"http://127.0.0.1:{port}",
            }
        time.sleep(0.5)
    process.terminate()
    pid_path.unlink(missing_ok=True)
    raise PullToRunError("READINESS_TIMEOUT")


def stop(*, port: int) -> dict[str, Any]:
    state = _ensure_state()
    pid_path = state["pid"]
    if not pid_path.is_file():
        raise PullToRunError("PID_FILE_MISSING")
    pid = int(pid_path.read_text(encoding="ascii").strip())
    if _pid_alive(pid):
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            os.kill(pid, signal.SIGTERM)
        for _ in range(20):
            if not _pid_alive(pid):
                break
            time.sleep(0.25)
    if _pid_alive(pid):
        raise PullToRunError(f"PROCESS_STILL_RUNNING={pid}")
    pid_path.unlink(missing_ok=True)
    if _health(port, 0.5):
        raise PullToRunError(f"PORT_STILL_LISTENING={port}")
    return {"status": "PASS_A1FS_V121_STOPPED", "pid": pid}


def status(*, port: int) -> dict[str, Any]:
    state = _ensure_state()
    pid_path = state["pid"]
    if not pid_path.is_file():
        raise PullToRunError("A1FS_V121_STATUS=STOPPED")
    pid = int(pid_path.read_text(encoding="ascii").strip())
    if not _pid_alive(pid):
        raise PullToRunError("A1FS_V121_STATUS=STALE_PID")
    if not _health(port):
        raise PullToRunError("A1FS_V121_STATUS=UNHEALTHY")
    return {"status": "A1FS_V121_STATUS=RUNNING", "pid": pid, "version": PRODUCT_VERSION, "url": f"http://127.0.0.1:{port}"}


def readback() -> dict[str, Any]:
    manifest, bundles, sequence, _registry, state = _load_runtime()
    with closing(sqlite3.connect(state["database"])) as connection:
        profile_count = int(connection.execute("SELECT COUNT(*) FROM learner_profiles").fetchone()[0])
        attempt_count = int(connection.execute("SELECT COUNT(*) FROM response_attempts").fetchone()[0])
    return {
        "task_id": TASK_ID,
        "product_version": PRODUCT_VERSION,
        "serve_module": MODULE,
        "module_file": __file__,
        "sys_executable": sys.executable,
        "cwd": os.getcwd(),
        "unit_count": len(sequence),
        "lesson_count": len(bundles),
        "asset_count": sum(len(bundle.get("assets", [])) for bundle in bundles.values()),
        "database_path": str(state["database"]),
        "auth_path": str(state["auth"]),
        "learner_state_path": str(state["learner_state"]),
        "logs_path": str(state["logs"]),
        "static_root": str(_resolve_product(str(manifest["secure_static_root"]))),
        "profile_count": profile_count,
        "attempt_count": attempt_count,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    start_cmd = commands.add_parser("start")
    start_cmd.add_argument("--host", default=DEFAULT_HOST)
    start_cmd.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve_cmd = commands.add_parser("serve")
    serve_cmd.add_argument("--host", default=DEFAULT_HOST)
    serve_cmd.add_argument("--port", type=int, default=DEFAULT_PORT)
    stop_cmd = commands.add_parser("stop")
    stop_cmd.add_argument("--port", type=int, default=DEFAULT_PORT)
    status_cmd = commands.add_parser("status")
    status_cmd.add_argument("--port", type=int, default=DEFAULT_PORT)
    commands.add_parser("readback")
    args = parser.parse_args(argv)
    try:
        if args.command == "serve":
            serve(host=args.host, port=args.port)
            return 0
        if args.command == "start":
            print(json.dumps(start(host=args.host, port=args.port), indent=2))
        elif args.command == "stop":
            print(json.dumps(stop(port=args.port), indent=2))
        elif args.command == "status":
            print(json.dumps(status(port=args.port), indent=2))
        else:
            print(json.dumps(readback(), indent=2))
        return 0
    except (
        PullToRunError,
        operator.LocalProductionAcceptanceError,
        operator.s05._core.S05ReleaseError,
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
