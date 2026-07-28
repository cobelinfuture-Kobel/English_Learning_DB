#!/usr/bin/env python3
'''Materialize R01 with an explicit governed V1 product-root authority.'''
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

from ulga.builders import build_a1fs_online_v1_r01_self_contained_product_root_update_channel as r01
from ulga.validators.validate_a1fs_online_v1_r01_self_contained_product_root_update_channel import validate_outputs

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Resolves the approved A1FS_V1_PRODUCT_ROOT and invokes the authoritative R01 packager and "
    "independent validator. The builder itself owns the Windows-safe SQLite lifecycle. This "
    "runner creates no curriculum, learner content, scoring, mastery, dashboard, audio, A2, "
    "Cloudflare route, external binding, monkeypatch authority, or parallel runtime."
)
PRODUCT_ROOT_ENV = "A1FS_V1_PRODUCT_ROOT"


def resolve_product_root(*, explicit: Path | None, output_path: Path) -> Path:
    if explicit is not None:
        return explicit.resolve()
    configured = str(os.environ.get(PRODUCT_ROOT_ENV) or "").strip()
    if configured:
        return Path(configured).resolve()
    return (Path(output_path).resolve().parent / "A1FS_V1").resolve()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("materialize", nargs="?")
    parser.add_argument("--s19", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--product-root", type=Path)
    parser.add_argument("--code-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--version", default=r01.PRODUCT_VERSION)
    args = parser.parse_args(argv)
    try:
        product_root = resolve_product_root(explicit=args.product_root, output_path=args.output)
        receipt, safe = r01.materialize(
            s19_path=args.s19,
            output_path=args.output,
            report_path=args.report,
            product_root=product_root,
            code_root=args.code_root,
            version=args.version,
        )
        validation = validate_outputs(
            receipt=receipt,
            safe_report=safe,
            output_root=product_root.parent,
            s19_path=args.s19,
        )
        if validation["error_count"]:
            raise r01.ProductRootError("validation_failed:" + "|".join(validation["errors"]))
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (
        r01.ProductRootError,
        r01.s19.ReleaseCandidateError,
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
