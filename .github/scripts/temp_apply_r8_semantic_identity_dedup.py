#!/usr/bin/env python3
"""Resume and verify the focused R8 semantic-ready-identity deduplication fix.

Temporary operator script. The prior run already patched the existing R8 runner and
focused regression test. This resume step corrects the equivalent-artifact cross-product
expectation, verifies the required production patch is present, and runs focused checks.
Remove before merge.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "ulga/builders/run_a1fs_v1_r8_legacy_real_evidence_reconciliation_local.py"
TEST = ROOT / "tests/ulga/test_a1fs_v1_r8_legacy_real_evidence_reconciliation_local_runner.py"


def patch_cross_product_expectation() -> None:
    runner_text = RUNNER.read_text(encoding="utf-8")
    required_runner_markers = (
        "def _ready_semantic_identity(",
        '"ready_artifact_identity_count": len(ready_artifact_identities)',
        '"ready_semantic_identity_count": len(ready)',
        '"reconciliation_diagnostics": dict(reconciliation_diagnostics)',
    )
    missing = [marker for marker in required_runner_markers if marker not in runner_text]
    if missing:
        raise RuntimeError(f"semantic_dedup_runner_patch_missing:{missing}")

    text = TEST.read_text(encoding="utf-8")
    old = '''    assert diagnostics["ready_combination_count"] == 2
    assert diagnostics["ready_artifact_identity_count"] == 2
    assert diagnostics["ready_semantic_identity_count"] == 1
'''
    new = '''    assert diagnostics["ready_combination_count"] == 4
    assert diagnostics["ready_artifact_identity_count"] == 4
    assert diagnostics["ready_semantic_identity_count"] == 1
    assert diagnostics["ready_equivalent_variant_count"] == 3
'''
    if new not in text:
        count = text.count(old)
        if count != 1:
            raise RuntimeError(
                f"equivalent_artifact_cross_product_anchor:expected_one_match:actual={count}"
            )
        text = text.replace(old, new, 1)
        TEST.write_text(text, encoding="utf-8")


def run_checks() -> None:
    commands = [
        [sys.executable, "-m", "py_compile", str(RUNNER)],
        [sys.executable, "-m", "pytest", "-q", str(TEST)],
    ]
    for command in commands:
        subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    patch_cross_product_expectation()
    run_checks()
    print("PASS:R8_SEMANTIC_IDENTITY_DEDUP_PATCH_AND_FOCUSED_TESTS")


if __name__ == "__main__":
    main()
