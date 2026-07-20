#!/usr/bin/env python3
"""Probe the focused EXACT_OPTION fixture's swallowed reconciliation exception.

Temporary operator script. It prints only exception class/code and aggregate counts,
uses generated test fixtures under .local, and must be removed before merge.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import uuid
from collections import Counter
from pathlib import Path

from ulga.builders import (
    run_a1fs_v1_r8_legacy_real_evidence_reconciliation_local as runner,
)
from ulga.builders import (
    build_a1fs_v1_r8_legacy_real_evidence_deterministic_production_reconciliation
    as reconciliation,
)

ROOT = Path(__file__).resolve().parents[2]
TEST_PATH = ROOT / "tests/ulga/test_a1fs_v1_r8_legacy_real_evidence_reconciliation_local_runner.py"


def load_test_module():
    spec = importlib.util.spec_from_file_location("r8_exact_option_fixture_probe", TEST_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("test_module_load_failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_code(exc: BaseException) -> str:
    raw = str(exc).split(":", 1)[0].strip().casefold()
    if re.fullmatch(r"[a-z][a-z0-9_]{2,95}", raw):
        return raw
    return f"unclassified_{type(exc).__name__.casefold()}"


def main() -> None:
    module = load_test_module()
    root = ROOT / ".local" / f"r8-exact-option-fixture-probe-{uuid.uuid4().hex}"
    discovery = root / ".probe"
    exception_classes: Counter[str] = Counter()
    exception_codes: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()

    try:
        data = module.build_local_fixture(root)
        data["local_root"] = root
        data["output_root"] = root / "output"
        exact_count = module._prepare_hash_bound_source_options_case(
            data,
            include_source_options=True,
        )

        files = runner._json_files(root)
        chains, legacy_counts = runner._discover_legacy(
            files,
            staging_root=discovery / "legacy",
        )
        chains, compatibility_counts = runner._stage_feature_context_compatibility(
            chains,
            staging_root=discovery / "compatibility",
        )
        generated_pairs, materialization_counts = runner._materialize_current(
            chains,
            staging_root=discovery / "materialized",
        )
        pairs = runner._merge_pairs(runner._discover_current(files), generated_pairs)

        inspected = 0
        for chain_index, chain in enumerate(chains, start=1):
            for pair_index, pair in enumerate(pairs, start=1):
                inspected += 1
                try:
                    report = reconciliation.reconcile(
                        **chain,
                        current_bank_path=pair["current_bank_path"],
                        current_supply_path=pair["current_supply_path"],
                        output_root=(
                            discovery
                            / "inspect"
                            / f"chain_{chain_index:03d}_pair_{pair_index:03d}"
                        ),
                        mode="inspect",
                    )["report"]
                    status_counts[str(report.get("validation_status") or "UNKNOWN")] += 1
                except (OSError, KeyError, TypeError, ValueError) as exc:
                    exception_classes[type(exc).__name__] += 1
                    exception_codes[safe_code(exc)] += 1

        print(json.dumps({
            "exact_option_fixture_count": exact_count,
            "legacy_counts": legacy_counts,
            "compatibility_counts": compatibility_counts,
            "materialization_counts": materialization_counts,
            "inspected_combination_count": inspected,
            "inspect_status_counts": dict(sorted(status_counts.items())),
            "exception_class_counts": dict(sorted(exception_classes.items())),
            "exception_code_counts": dict(sorted(exception_codes.items())),
            "claim_boundaries": {
                "private_content_exposed": False,
                "learner_response_exposed": False,
                "production_artifact_modified": False,
                "canonical_m2_modified": False,
                "mastery_claimed": False,
                "retention_confirmed": False,
                "a2_unlocked": False,
            },
        }, ensure_ascii=False, indent=2))
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
