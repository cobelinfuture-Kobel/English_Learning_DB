#!/usr/bin/env python3
"""Upgrade the local A1FS product through the canonical Python UPG01 entry.

Compatibility chain retained by the top-level runner:
- build_a1fs_ops_v1_upg01_python_upgrade_fullfix
- build_a1fs_ops_v1_upg01_python_upgrade_fullfix_residual_canonical_rebase
- build_a1fs_ops_v1_upg01_release_residual_reconciliation_fullfix
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from ulga.builders import (  # noqa: E402
    build_a1fs_ops_v1_upg01_release_residual_reconciliation_fullfix as runner,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--code-root", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument("--product-root", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--journal-path", type=Path)
    parser.add_argument("--target-version", default="latest")
    parser.add_argument("--port", type=int, default=runner.DEFAULT_PORT)
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
        result = runner.build_plan(**kwargs) if args.plan_only else runner.upgrade(**kwargs)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (
        runner.PythonUpgradeFullFixError,
        runner.runtime.RuntimeShutdownFullFixError,
        runner.runtime.core.UpgradeOrchestratorError,
        runner.r01.ProductRootError,
        runner.s01.S01AdmissionError,
        runner.s05._core.S05ReleaseError,
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
