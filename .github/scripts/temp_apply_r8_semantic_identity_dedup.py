#!/usr/bin/env python3
"""Apply and verify the focused R8 semantic-ready-identity deduplication fix.

Temporary operator script. It edits only the existing R8 local runner and its focused
regression test, then runs py_compile and the focused pytest file. Remove before merge.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "ulga/builders/run_a1fs_v1_r8_legacy_real_evidence_reconciliation_local.py"
TEST = ROOT / "tests/ulga/test_a1fs_v1_r8_legacy_real_evidence_reconciliation_local_runner.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}:expected_one_match:actual={count}")
    return text.replace(old, new, 1)


def patch_runner() -> None:
    text = RUNNER.read_text(encoding="utf-8")

    helper_anchor = "\n\ndef _inspect(\n"
    helper = r'''

def _semantic_rows(value: Any, *, fields: tuple[str, ...]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise LocalRunnerError("ready_semantic_rows_invalid")
    rows: list[dict[str, Any]] = []
    for row in value:
        if not isinstance(row, Mapping):
            raise LocalRunnerError("ready_semantic_row_invalid")
        rows.append({field: deepcopy(row.get(field)) for field in fields})
    return sorted(
        rows,
        key=lambda row: (
            str(row.get("item_id") or ""),
            int(row.get("attempt_sequence") or 0),
            str(row.get("submitted_at") or ""),
            r5.digest(row),
        ),
    )


def _ready_semantic_identity(
    chain: Mapping[str, Path],
    result: Mapping[str, Any],
) -> tuple[str, str]:
    registry = _read(
        chain["resolved_root"] / "cumulative_attempt_registry.private.json"
    )
    ledger = _read(
        chain["resolved_root"] / "cumulative_progress_ledger.private.json"
    )
    mapping = result.get("mapping")
    if registry is None or ledger is None or not isinstance(mapping, list):
        raise LocalRunnerError("ready_semantic_identity_source_invalid")

    attempts = _semantic_rows(
        registry.get("attempts"),
        fields=(
            "item_id",
            "attempt_sequence",
            "response",
            "submitted_at",
            "operator_review",
        ),
    )
    entries = _semantic_rows(
        ledger.get("entries"),
        fields=(
            "evidence_id",
            "item_id",
            "attempt_sequence",
            "submitted_at",
            "scoring_mode",
            "outcome",
            "score",
            "operator_review",
        ),
    )
    mapping_rows = sorted(
        [
            {
                "legacy_item_id_sha256": row.get("legacy_item_id_sha256"),
                "current_item_id": row.get("current_item_id"),
                "breadth_cell_id": row.get("breadth_cell_id"),
                "contract_sha256": row.get("contract_sha256"),
            }
            for row in mapping
            if isinstance(row, Mapping)
        ],
        key=lambda row: (
            str(row.get("legacy_item_id_sha256") or ""),
            str(row.get("current_item_id") or ""),
            str(row.get("breadth_cell_id") or ""),
            str(row.get("contract_sha256") or ""),
        ),
    )
    if len(mapping_rows) != legacy.EXPECTED_ATTEMPTS:
        raise LocalRunnerError("ready_semantic_mapping_denominator_invalid")

    evidence_identity = r5.digest({
        "learner_ref": registry.get("learner_ref"),
        "session_id": registry.get("session_id"),
        "attempts": attempts,
        "entries": entries,
    })
    mapping_identity = r5.digest(mapping_rows)
    return evidence_identity, mapping_identity


def _ready_candidate_rank(
    chain: Mapping[str, Path],
    pair: Mapping[str, Any],
) -> tuple[str, ...]:
    return (
        legacy.file_sha(
            chain["resolved_root"] / "cumulative_attempt_registry.private.json"
        ),
        legacy.file_sha(
            chain["resolved_root"] / "cumulative_progress_ledger.private.json"
        ),
        legacy.file_sha(chain["source_bank_path"]),
        legacy.file_sha(chain["consumer_path"]),
        legacy.file_sha(chain["graph_path"]),
        str(pair["current_bank_sha256"]),
        str(pair["current_supply_sha256"]),
    )
'''
    if "def _ready_semantic_identity(" not in text:
        text = replace_once(text, helper_anchor, helper + helper_anchor, "runner_helper_anchor")

    start = text.index("def _inspect(\n")
    end = text.index("\n\ndef _blocked_report(\n", start)
    new_inspect = r'''def _inspect(
    chains: list[dict[str, Path]],
    pairs: list[dict[str, Any]],
    *,
    staging_root: Path,
) -> tuple[dict[tuple[str, str], dict[str, Any]], int, dict[str, Any]]:
    ready: dict[tuple[str, str], dict[str, Any]] = {}
    ready_artifact_identities: set[tuple[str, str, str]] = set()
    ready_combination_count = 0
    inspected_count = 0
    inspect_exception_count = 0
    status_counts: Counter[str] = Counter()
    issue_combination_counts: Counter[str] = Counter()
    issue_item_counts: Counter[str] = Counter()
    max_exact_mapped_attempt_count = 0
    max_mapped_breadth_cell_count = 0
    max_pass_count = 0
    max_failure_count = 0
    for chain_index, chain in enumerate(chains, start=1):
        registry_sha = legacy.file_sha(
            chain["resolved_root"] / "cumulative_attempt_registry.private.json"
        )
        for pair_index, pair in enumerate(pairs, start=1):
            inspected_count += 1
            probe = staging_root / f"chain_{chain_index:03d}_pair_{pair_index:03d}"
            try:
                result = reconciliation.reconcile(
                    **chain,
                    current_bank_path=pair["current_bank_path"],
                    current_supply_path=pair["current_supply_path"],
                    output_root=probe,
                    mode="inspect",
                )["report"]
            except (OSError, KeyError, TypeError, ValueError):
                inspect_exception_count += 1
                continue
            status = str(result.get("validation_status") or "UNKNOWN")
            status_counts[status] += 1
            counts = result.get("counts")
            if isinstance(counts, Mapping):
                max_exact_mapped_attempt_count = max(
                    max_exact_mapped_attempt_count,
                    int(counts.get("exact_mapped_attempt_count", 0)),
                )
                max_mapped_breadth_cell_count = max(
                    max_mapped_breadth_cell_count,
                    int(counts.get("mapped_breadth_cell_count", 0)),
                )
                max_pass_count = max(max_pass_count, int(counts.get("pass_count", 0)))
                max_failure_count = max(
                    max_failure_count,
                    int(counts.get("failure_count", 0)),
                )
            issues = result.get("issues")
            if isinstance(issues, Mapping):
                for code, rows in issues.items():
                    if isinstance(rows, list) and rows:
                        issue_combination_counts[str(code)] += 1
                        issue_item_counts[str(code)] += len(rows)
            if status != reconciliation.READY_STATUS:
                continue

            ready_combination_count += 1
            ready_artifact_identities.add((
                registry_sha,
                str(pair["current_bank_sha256"]),
                str(pair["current_supply_sha256"]),
            ))
            semantic_identity = _ready_semantic_identity(chain, result)
            candidate = {
                "chain": chain,
                "pair": pair,
                "inspect": result,
                "rank": _ready_candidate_rank(chain, pair),
            }
            previous = ready.get(semantic_identity)
            if previous is None or candidate["rank"] < previous["rank"]:
                ready[semantic_identity] = candidate
    diagnostics = {
        "inspect_exception_count": inspect_exception_count,
        "inspect_status_counts": dict(sorted(status_counts.items())),
        "issue_combination_counts": dict(sorted(issue_combination_counts.items())),
        "issue_item_counts": dict(sorted(issue_item_counts.items())),
        "ready_combination_count": ready_combination_count,
        "ready_artifact_identity_count": len(ready_artifact_identities),
        "ready_semantic_identity_count": len(ready),
        "ready_equivalent_variant_count": max(0, ready_combination_count - len(ready)),
        "max_exact_mapped_attempt_count": max_exact_mapped_attempt_count,
        "max_mapped_breadth_cell_count": max_mapped_breadth_cell_count,
        "max_pass_count": max_pass_count,
        "max_failure_count": max_failure_count,
    }
    return ready, inspected_count, diagnostics'''
    text = text[:start] + new_inspect + text[end:]

    success_anchor = '''                **legacy_diagnostics,
                **materialization_diagnostics,
            },
            "reconciliation": {
'''
    success_replacement = '''                **legacy_diagnostics,
                **materialization_diagnostics,
            },
            "reconciliation_diagnostics": dict(reconciliation_diagnostics),
            "reconciliation": {
'''
    if '"reconciliation_diagnostics": dict(reconciliation_diagnostics),' not in text:
        text = replace_once(
            text,
            success_anchor,
            success_replacement,
            "success_diagnostics_anchor",
        )
    RUNNER.write_text(text, encoding="utf-8")


def patch_test() -> None:
    text = TEST.read_text(encoding="utf-8")
    pattern = re.compile(
        r"def test_runner_blocks_multiple_distinct_exact_production_identities\(fixture: dict\) -> None:\n.*?\n\ndef test_runner_safe_report_contains_no_absolute_path",
        re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        raise RuntimeError("identity_regression_block_not_found")

    replacement = r'''def _write_second_current_identity(
    fixture: dict,
    *,
    semantic_mapping_change: bool,
) -> None:
    bank = json.loads(fixture["current_bank_path"].read_text(encoding="utf-8"))
    supply = json.loads(fixture["current_supply_path"].read_text(encoding="utf-8"))
    bank["selection_contract"]["fixture_variant"] = "SECOND_ARTIFACT_IDENTITY"
    supply["fixture_variant"] = "SECOND_ARTIFACT_IDENTITY"

    if semantic_mapping_change:
        target = bank["items"][0]
        original_item_id = str(target["item_id"])
        replacement_item_id = original_item_id + ":SEMANTIC_VARIANT"
        target["item_id"] = replacement_item_id
        replaced = 0
        for cell in supply["cell_supply"]:
            approved = cell.get("approved_item_ids", [])
            if original_item_id in approved:
                cell["approved_item_ids"] = [
                    replacement_item_id if item_id == original_item_id else item_id
                    for item_id in approved
                ]
                replaced += 1
        assert replaced == 1

    bank_core = {key: value for key, value in bank.items() if key != "bank_sha256"}
    bank["bank_sha256"] = r4.digest(bank_core)
    supply_core = {key: value for key, value in supply.items() if key != "report_sha256"}
    supply["report_sha256"] = r4.digest(supply_core)
    second = fixture["local_root"] / (
        "second_semantic_identity" if semantic_mapping_change
        else "second_equivalent_artifact_identity"
    )
    second.mkdir(parents=True)
    (second / "a1fs_v1_r4_approved_practice_bank.private.json").write_text(
        json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (second / "a1fs_v1_r4_supply_report.safe.json").write_text(
        json.dumps(supply, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def test_runner_collapses_equivalent_current_artifact_variants(fixture: dict) -> None:
    _write_second_current_identity(fixture, semantic_mapping_change=False)
    report = runner.run(local_root=fixture["local_root"], output_root=fixture["output_root"])
    assert report["validation_status"] == runner.STATUS, report
    diagnostics = report["reconciliation_diagnostics"]
    assert diagnostics["ready_combination_count"] == 2
    assert diagnostics["ready_artifact_identity_count"] == 2
    assert diagnostics["ready_semantic_identity_count"] == 1


def test_runner_collapses_equivalent_registry_ledger_copies(fixture: dict) -> None:
    source_resolved = fixture["resolved_root"]
    registry = json.loads(
        (source_resolved / "cumulative_attempt_registry.private.json").read_text(
            encoding="utf-8"
        )
    )
    ledger = json.loads(
        (source_resolved / "cumulative_progress_ledger.private.json").read_text(
            encoding="utf-8"
        )
    )
    registry["copy_metadata"] = "NON_SEMANTIC_REGISTRY_COPY"
    ledger["attempt_registry_sha256"] = m08.sha256_value(registry)
    ledger["copy_metadata"] = "NON_SEMANTIC_LEDGER_COPY"
    duplicate = fixture["local_root"] / "duplicate_evidence_copy"
    duplicate.mkdir(parents=True)
    (duplicate / "cumulative_attempt_registry.private.json").write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (duplicate / "cumulative_progress_ledger.private.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    report = runner.run(local_root=fixture["local_root"], output_root=fixture["output_root"])
    assert report["validation_status"] == runner.STATUS, report
    assert report["discovery_counts"]["legacy_semantic_chain_count"] == 2
    diagnostics = report["reconciliation_diagnostics"]
    assert diagnostics["ready_artifact_identity_count"] == 2
    assert diagnostics["ready_semantic_identity_count"] == 1


def test_runner_blocks_semantically_distinct_exact_mapping(fixture: dict) -> None:
    _write_second_current_identity(fixture, semantic_mapping_change=True)
    report = runner.run(local_root=fixture["local_root"], output_root=fixture["output_root"])
    assert report["validation_status"] == runner.BLOCKED
    diagnostics = report["reconciliation_diagnostics"]
    assert diagnostics["ready_artifact_identity_count"] == 2
    assert diagnostics["ready_semantic_identity_count"] == 2
    assert report["stop_reason"] == "MULTIPLE_DISTINCT_EXACT_RECONCILIATION_CHAINS"


def test_runner_safe_report_contains_no_absolute_path'''
    text = text[:match.start()] + replacement + text[match.end():]

    old_assertions = '''    assert diagnostics["max_failure_count"] == 1
    assert not any(secret in json.dumps(diagnostics) for secret in secret_ids)
'''
    new_assertions = '''    assert diagnostics["ready_combination_count"] == 0
    assert diagnostics["ready_artifact_identity_count"] == 0
    assert diagnostics["ready_semantic_identity_count"] == 0
    assert diagnostics["ready_equivalent_variant_count"] == 0
    assert diagnostics["max_failure_count"] == 1
    assert not any(secret in json.dumps(diagnostics) for secret in secret_ids)
'''
    text = replace_once(text, old_assertions, new_assertions, "diagnostic_assertion_anchor")
    TEST.write_text(text, encoding="utf-8")


def run_checks() -> None:
    commands = [
        [sys.executable, "-m", "py_compile", str(RUNNER)],
        [sys.executable, "-m", "pytest", "-q", str(TEST)],
    ]
    for command in commands:
        subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    patch_runner()
    patch_test()
    run_checks()
    print("PASS:R8_SEMANTIC_IDENTITY_DEDUP_PATCH_AND_FOCUSED_TESTS")


if __name__ == "__main__":
    main()
