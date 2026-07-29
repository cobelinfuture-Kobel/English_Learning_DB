#!/usr/bin/env python3
"""Strengthen UPG01 shutdown verification without changing migration authority."""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_ops_v1_upg01_portable_resumable_universal_upgrade_orchestrator_fullfix as core,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Wraps the existing UPG01 orchestrator only to make Windows runtime shutdown "
    "identity-aware, retried, and port-verified before any migration begins. It "
    "creates no migration, curriculum, content, answer, scoring/mastery authority, "
    "learner attempt, audio, A2 unlock, external route, or parallel runtime."
)
PROGRAM_ID = core.PROGRAM_ID
TASK_ID = core.TASK_ID
SCHEMA_VERSION = core.SCHEMA_VERSION
PASS_STATUS = core.PASS_STATUS
DEFAULT_PORT = core.DEFAULT_PORT
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
SYNCHRONIZE = 0x00100000
ERROR_INVALID_PARAMETER = 87
ERROR_ACCESS_DENIED = 5
_EXTENDED_WAIT_SECONDS = 30.0
_RETRY_WAIT_SECONDS = 15.0
_POLL_SECONDS = 0.25
_BASE_STOP = core.r01.stop


class RuntimeShutdownFullFixError(core.UpgradeOrchestratorError):
    pass


def _port_open(port: int, timeout: float = 0.25) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(timeout)
        return probe.connect_ex(("127.0.0.1", int(port))) == 0


def _windows_creation_token(pid: int) -> int | None:
    if os.name != "nt":
        return None
    kernel32 = ctypes.windll.kernel32
    kernel32.OpenProcess.restype = ctypes.c_void_p
    handle = kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE,
        False,
        int(pid),
    )
    if not handle:
        error = int(kernel32.GetLastError())
        if error == ERROR_INVALID_PARAMETER:
            return None
        if error == ERROR_ACCESS_DENIED:
            return -1
        return None
    try:
        creation = ctypes.c_ulonglong()
        exit_time = ctypes.c_ulonglong()
        kernel_time = ctypes.c_ulonglong()
        user_time = ctypes.c_ulonglong()
        ok = kernel32.GetProcessTimes(
            ctypes.c_void_p(handle),
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(kernel_time),
            ctypes.byref(user_time),
        )
        if not ok:
            return -1
        return int(creation.value)
    finally:
        kernel32.CloseHandle(ctypes.c_void_p(handle))


def _same_process_alive(pid: int, creation_token: int | None) -> bool:
    if os.name != "nt":
        return bool(core.r01._pid_alive(int(pid)))
    current = _windows_creation_token(int(pid))
    if creation_token is None:
        return current is not None
    if creation_token == -1:
        return current is not None
    return current == creation_token


def _wait_for_shutdown(
    *,
    pid: int,
    creation_token: int | None,
    port: int,
    timeout: float,
) -> dict[str, Any] | None:
    deadline = time.monotonic() + float(timeout)
    polls = 0
    while True:
        polls += 1
        process_alive = _same_process_alive(pid, creation_token)
        health_alive = bool(core.r01._health(int(port), 0.25))
        port_open = _port_open(int(port), 0.25)
        if not process_alive and not health_alive and not port_open:
            return {
                "process_identity_exited": True,
                "health_endpoint_closed": True,
                "port_closed": True,
                "poll_count": polls,
            }
        if time.monotonic() >= deadline:
            return None
        time.sleep(_POLL_SECONDS)


def _taskkill(pid: int) -> dict[str, Any]:
    result = subprocess.run(
        ["taskkill", "/PID", str(int(pid)), "/T", "/F"],
        check=False,
        text=True,
        capture_output=True,
        creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
    )
    return {
        "returncode": int(result.returncode),
        "stdout": result.stdout.strip()[-500:],
        "stderr": result.stderr.strip()[-500:],
    }


def robust_stop(*, product_root: Path, port: int) -> dict[str, Any]:
    root = Path(product_root).resolve()
    pid_path = root / "shared/a1fs_v1.pid"
    if not pid_path.is_file():
        return {
            "status": "PASS_A1FS_V1_ALREADY_STOPPED",
            "pid": None,
            "shutdown_mode": "PID_FILE_ABSENT",
        }
    try:
        pid = int(pid_path.read_text(encoding="ascii").strip())
    except (OSError, ValueError) as exc:
        raise RuntimeShutdownFullFixError(
            f"INVALID_RUNTIME_PID_FILE={pid_path}"
        ) from exc
    creation_token = _windows_creation_token(pid)
    try:
        result = _BASE_STOP(product_root=root, port=int(port))
        return {
            **dict(result),
            "shutdown_mode": "BASE_STOP",
            "process_identity_verified": True,
        }
    except core.r01.ProductRootError as exc:
        if not str(exc).startswith("PROCESS_STILL_RUNNING="):
            raise
    extended = _wait_for_shutdown(
        pid=pid,
        creation_token=creation_token,
        port=int(port),
        timeout=_EXTENDED_WAIT_SECONDS,
    )
    retry_result: dict[str, Any] | None = None
    if extended is None:
        if os.name == "nt":
            retry_result = _taskkill(pid)
        else:
            try:
                os.kill(pid, 9)
                retry_result = {"returncode": 0, "stdout": "SIGKILL", "stderr": ""}
            except OSError as kill_exc:
                retry_result = {
                    "returncode": 1,
                    "stdout": "",
                    "stderr": str(kill_exc),
                }
        extended = _wait_for_shutdown(
            pid=pid,
            creation_token=creation_token,
            port=int(port),
            timeout=_RETRY_WAIT_SECONDS,
        )
    if extended is None:
        raise RuntimeShutdownFullFixError(
            "RUNTIME_SHUTDOWN_TIMEOUT;"
            f"PID={pid};PORT={port};RETRY={json.dumps(retry_result, ensure_ascii=False)}"
        )
    pid_path.unlink(missing_ok=True)
    return {
        "status": "PASS_A1FS_V1_STOPPED_EXTENDED_VERIFIED",
        "pid": pid,
        "shutdown_mode": (
            "EXTENDED_WAIT_AFTER_BASE_TASKKILL"
            if retry_result is None
            else "SECOND_TASKKILL_AND_EXTENDED_WAIT"
        ),
        "process_creation_token_captured": creation_token not in (None, -1),
        "retry_taskkill": retry_result,
        **extended,
    }


def activate() -> None:
    core.r01.stop = robust_stop


def build_plan(**kwargs: Any) -> dict[str, Any]:
    return core.build_plan(**kwargs)


def upgrade(**kwargs: Any) -> dict[str, Any]:
    activate()
    result = core.upgrade(**kwargs)
    result["runtime_shutdown_fullfix"] = {
        "enabled": True,
        "identity_aware_windows_shutdown": True,
        "extended_wait_seconds": _EXTENDED_WAIT_SECONDS,
        "retry_wait_seconds": _RETRY_WAIT_SECONDS,
    }
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "upgrade"):
        command = commands.add_parser(name)
        command.add_argument("--code-root", type=Path)
        command.add_argument("--product-root", type=Path)
        command.add_argument("--output-root", type=Path)
        command.add_argument("--journal-path", type=Path)
        command.add_argument("--target-version", default="latest")
        command.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    kwargs = {
        "code_root": args.code_root,
        "product_root": args.product_root,
        "output_root": args.output_root,
        "journal_path": args.journal_path,
        "target_version": args.target_version,
        "port": args.port,
    }
    try:
        result = build_plan(**kwargs) if args.command == "plan" else upgrade(**kwargs)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (
        RuntimeShutdownFullFixError,
        core.UpgradeOrchestratorError,
        core.r01.ProductRootError,
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
