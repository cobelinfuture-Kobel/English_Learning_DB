#!/usr/bin/env python3
"""Windows race-safe output cleanup for U01QB15 Edge private replay."""
from __future__ import annotations

import os
import stat
import time
from pathlib import Path
from typing import Callable


def race_safe_rmtree(original_rmtree: Callable, path, *args, **kwargs) -> None:
    """Remove a disposable tree while tolerating browser-extension file churn.

    Python 3.12 can surface FileNotFoundError when a browser extension deletes a
    file after rmtree enumerates it but before unlink.  Missing descendants are
    benign for disposable acceptance output. Permission/read-only cases are
    retried after making the path writable. The top-level directory must be gone
    before this function returns.
    """
    root = Path(path)
    if not root.exists():
        return

    def _onerror(func, target, exc_info):
        exc = exc_info[1]
        if isinstance(exc, FileNotFoundError):
            return
        if isinstance(exc, PermissionError):
            try:
                os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
            except OSError:
                pass
            try:
                func(target)
                return
            except FileNotFoundError:
                return
        raise exc

    last_exc: BaseException | None = None
    for _attempt in range(12):
        if not root.exists():
            return
        try:
            # Do not forward caller onerror/onexc; this function owns cleanup
            # semantics for a strictly disposable local acceptance directory.
            original_rmtree(root, onerror=_onerror)
        except FileNotFoundError:
            pass
        except OSError as exc:
            last_exc = exc
        if not root.exists():
            return
        time.sleep(0.15)

    detail = f":{last_exc}" if last_exc is not None else ""
    raise OSError(f"DISPOSABLE_OUTPUT_CLEANUP_FAILED:{root}{detail}")
