#!/usr/bin/env python3
"""Run CP06 with the real CP05/CP04/S05 inputs and rebuilt 24-unit contract."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1_a1plus_cross_skill_learning_units as m02  # noqa: E402
from ulga.builders import build_a1fs_v1_cp06_grammar_spiral_role_population_and_content_capacity as builder  # noqa: E402
from ulga.validators import validate_a1fs_v1_cp06_grammar_spiral_role_population_and_content_capacity as validator  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Private production orchestration for metadata-only CP06 output; the committed "
    "M02 builder is replayed because its generated graph is not a tracked input."
)

TASK_ID = builder.TASK_ID
PASS_STATUS = builder.PASS_STATUS


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def run(
    cp05_approved: Mapping[str, Any],
    cp04_artifact: Mapping[str, Any],
    registry_package: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    unit_contract = m02.build_artifact()
    artifact = builder.build_artifact(
        cp05_approved,
        cp04_artifact,
        registry_package,
        unit_contract,
    )
    report = validator.validate_artifact(
        artifact,
        cp05_approved=cp05_approved,
        cp04_artifact=cp04_artifact,
        registry_package=registry_package,
        unit_contract_artifact=unit_contract,
    )
    return artifact, report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cp05-approved", type=Path, default=builder.DEFAULT_CP05_APPROVED)
    parser.add_argument("--cp04", type=Path, default=builder.DEFAULT_CP04)
    parser.add_argument("--raz-registry", type=Path, default=builder.DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, default=builder.DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=builder.DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        artifact, report = run(
            _read(args.cp05_approved),
            _read(args.cp04),
            _read(args.raz_registry),
        )
        builder._write_atomic(args.output, artifact)
        builder._write_atomic(args.report, report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["validation_status"] == PASS_STATUS else 1
    except (builder.CP06BuildError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
