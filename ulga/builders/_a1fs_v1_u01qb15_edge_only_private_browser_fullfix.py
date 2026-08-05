#!/usr/bin/env python3
"""Edge-only browser bootstrap for the U01QB15 private learner readback.

This helper deliberately refuses Chrome/Chromium executables.  On Windows it
identifies Microsoft Edge from the executable's file VersionInfo instead of
relying on ``msedge.exe --version`` (a GUI executable can return code 0 with no
stdout/stderr).  It tolerates the Windows launcher process exiting with code 0
while a child Edge process owns the DevTools port, and keeps diagnostics in the
acceptance output directory.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import quote

EDGE_ENV = "A1FS_EDGE_PATH"
EDGE_BASENAMES = {"msedge", "msedge.exe", "microsoft-edge", "microsoft-edge-stable"}


def _error(message: str) -> Exception:
    from ulga.builders import (
        _a1fs_v1_u01qb15_learner_facing_e2e_private_browser_readback_impl as impl,
    )

    return impl.PrivateBrowserReadbackError(message)


def _is_edge_path(path: Path) -> bool:
    return path.name.casefold() in EDGE_BASENAMES


def _candidate_paths() -> list[Path]:
    candidates: list[Path] = []
    configured = str(os.environ.get(EDGE_ENV) or "").strip()
    if configured:
        candidates.append(Path(configured))
    for command in ("msedge", "microsoft-edge-stable", "microsoft-edge"):
        found = shutil.which(command)
        if found:
            candidates.append(Path(found))
    for variable, relative in (
        ("PROGRAMFILES(X86)", "Microsoft/Edge/Application/msedge.exe"),
        ("PROGRAMFILES", "Microsoft/Edge/Application/msedge.exe"),
        ("LOCALAPPDATA", "Microsoft/Edge/Application/msedge.exe"),
    ):
        base = str(os.environ.get(variable) or "").strip()
        if base:
            candidates.append(Path(base) / relative)
    return candidates


def _cli_version_probe(resolved: Path) -> tuple[int, str]:
    probe = subprocess.run(
        [str(resolved), "--version"],
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    return int(probe.returncode), (probe.stdout + "\n" + probe.stderr).strip()


def _windows_version_info_probe(resolved: Path) -> tuple[int, str]:
    """Read Windows executable identity without launching the browser itself."""
    shell = (
        shutil.which("powershell.exe")
        or shutil.which("powershell")
        or shutil.which("pwsh")
    )
    if not shell:
        return 127, "WINDOWS_POWERSHELL_MISSING"
    command = (
        "$v=(Get-Item -LiteralPath $env:A1FS_EDGE_PROBE_PATH).VersionInfo;"
        "$parts=@($v.ProductName,$v.FileDescription,$v.ProductVersion) | "
        "Where-Object { $_ -ne $null -and $_.ToString().Trim() -ne '' };"
        "[Console]::Out.Write(($parts -join '|'))"
    )
    env = os.environ.copy()
    env["A1FS_EDGE_PROBE_PATH"] = str(resolved)
    probe = subprocess.run(
        [shell, "-NoProfile", "-NonInteractive", "-Command", command],
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
        env=env,
    )
    text = (probe.stdout + "\n" + probe.stderr).strip()
    return int(probe.returncode), text


def _identity_is_microsoft_edge(text: str) -> bool:
    folded = " ".join(str(text).casefold().split())
    return "microsoft edge" in folded


def _validate_edge_identity(resolved: Path, *, platform_name: str | None = None) -> str:
    """Return validated identity text or fail closed.

    Windows Edge is a GUI executable and can legally return code 0 with empty
    output for ``--version``.  File VersionInfo is the primary Windows authority.
    Non-Windows installs retain the CLI version probe.
    """
    platform_name = platform_name or os.name
    if platform_name == "nt":
        info_code, info_text = _windows_version_info_probe(resolved)
        if info_code == 0 and _identity_is_microsoft_edge(info_text):
            return info_text

        # Diagnostic fallback only. This keeps compatibility with unusual Windows
        # packaging while never accepting an empty probe or a non-Edge identity.
        cli_code, cli_text = _cli_version_probe(resolved)
        if cli_code == 0 and _identity_is_microsoft_edge(cli_text):
            return cli_text
        if info_code not in (0, 127) and not info_text:
            raise _error(f"EDGE_VERSIONINFO_PROBE_FAILED:{info_code}")
        detail = (
            f"versioninfo_rc={info_code}:versioninfo={info_text[-300:]}:"
            f"cli_rc={cli_code}:cli={cli_text[-300:]}"
        )
        raise _error(f"EDGE_VERSION_IDENTITY_INVALID:{detail}")

    cli_code, cli_text = _cli_version_probe(resolved)
    if cli_code != 0:
        raise _error(f"EDGE_VERSION_PROBE_FAILED:{cli_code}:{cli_text[-500:]}")
    if not _identity_is_microsoft_edge(cli_text):
        raise _error(f"EDGE_VERSION_IDENTITY_INVALID:{cli_text[-500:]}")
    return cli_text


def discover_edge_only(explicit: Path | None = None) -> Path:
    candidates = [Path(explicit)] if explicit is not None else _candidate_paths()
    rejected_non_edge: list[str] = []
    for candidate in candidates:
        candidate = candidate.expanduser()
        if not candidate.is_file():
            continue
        resolved = candidate.resolve()
        if not _is_edge_path(resolved):
            rejected_non_edge.append(str(resolved))
            continue
        _validate_edge_identity(resolved)
        return resolved
    if explicit is not None and rejected_non_edge:
        raise _error("NON_EDGE_BROWSER_FORBIDDEN:" + rejected_non_edge[0])
    if rejected_non_edge:
        raise _error("NON_EDGE_BROWSER_FORBIDDEN:" + rejected_non_edge[0])
    raise _error("MICROSOFT_EDGE_EXECUTABLE_MISSING")


def _tail(path: Path, limit: int = 1200) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[-limit:].replace("\r", " ").replace("\n", " ").strip()


class _EdgeCDP:
    """Proxy that closes the actual Edge browser, including launcher handoff cases."""

    def __init__(self, inner: Any):
        self._inner = inner

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    def close(self) -> None:
        try:
            self._inner.call("Browser.close")
        except Exception:
            pass
        try:
            self._inner.close()
        except Exception:
            pass


def launch_edge_only(edge: Path, start_url: str, profile: Path):
    from ulga.builders import (
        _a1fs_v1_u01qb15_learner_facing_e2e_private_browser_readback_impl as impl,
    )

    edge = Path(edge).resolve()
    if not _is_edge_path(edge):
        raise _error(f"NON_EDGE_BROWSER_FORBIDDEN:{edge}")

    profile.mkdir(parents=True, exist_ok=True)
    stdout_path = profile.parent / "edge.stdout.log"
    stderr_path = profile.parent / "edge.stderr.log"
    command = [
        str(edge),
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--disable-background-mode",
        "--no-first-run",
        "--no-default-browser-check",
        "--hide-scrollbars",
        "--window-size=1440,1200",
        "--remote-debugging-port=0",
        f"--user-data-dir={profile}",
        "about:blank",
    ]
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr)

    port_file = profile / "DevToolsActivePort"
    deadline = time.monotonic() + 25
    launcher_exit: int | None = None
    debug_port: int | None = None
    while time.monotonic() < deadline:
        # Check the authority signal first. On Windows the bootstrap process may
        # exit 0 after handing ownership to a child Edge process.
        if port_file.is_file():
            try:
                lines = port_file.read_text(encoding="utf-8").splitlines()
            except OSError:
                lines = []
            if lines and lines[0].isdigit():
                debug_port = int(lines[0])
                break
        code = process.poll()
        if code is not None:
            launcher_exit = int(code)
            if code != 0:
                raise _error(
                    f"EDGE_PROCESS_EXITED:{code}:stderr={_tail(stderr_path)}"
                )
            # exit 0 is not a failure; keep waiting for the child-owned CDP port.
        time.sleep(0.1)

    if debug_port is None:
        if process.poll() is None:
            process.terminate()
        raise _error(
            "EDGE_DEVTOOLS_PORT_TIMEOUT:"
            f"launcher_exit={launcher_exit}:stderr={_tail(stderr_path)}"
        )

    target_url = (
        f"http://127.0.0.1:{debug_port}/json/new?"
        + quote(start_url, safe=":/?=&")
    )
    try:
        request = urllib.request.Request(target_url, method="PUT")
        with urllib.request.urlopen(request, timeout=5) as response:
            target = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise _error(
            f"EDGE_CDP_TARGET_CREATE_FAILED:{exc}:stderr={_tail(stderr_path)}"
        ) from exc

    websocket_url = str(target.get("webSocketDebuggerUrl") or "")
    if not websocket_url:
        raise _error("EDGE_TARGET_WEBSOCKET_MISSING")
    cdp = impl._CDP(websocket_url)
    cdp.call("Page.enable")
    cdp.call("Runtime.enable")
    return process, _EdgeCDP(cdp)
