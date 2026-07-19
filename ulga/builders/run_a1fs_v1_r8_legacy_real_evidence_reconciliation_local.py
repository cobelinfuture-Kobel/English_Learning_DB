#!/usr/bin/env python3
"""Discover private local evidence/production artifacts and run R8 reconciliation once.

The runner accepts only a unique semantic source chain and a unique deterministic
R4 bank/supply identity that produces the full nine-attempt exact mapping. It
never uploads private files and emits only a safe discovery/execution readback.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_r3r4_authority_reviewed_production_population as population
from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4
from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5
from ulga.builders import build_a1fs_v1_r8_legacy_real_evidence_deterministic_production_reconciliation as reconciliation
from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as m08
from ulga.builders import build_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge as legacy
from ulga.validators import validate_a1fs_v1_r8_legacy_real_evidence_deterministic_production_reconciliation as validator

TASK_ID = "A1FS-V1-R8_LegacyRealEvidenceReconciliationLocalRunner"
SCHEMA_VERSION = "a1fs.v1.r8.legacy_real_evidence_local_runner.v1"
STATUS = "PASS_A1FS_V1_R8_LOCAL_RECONCILIATION_EXECUTED_AND_VALIDATED"
BLOCKED = "BLOCKED_A1FS_V1_R8_LOCAL_RECONCILIATION_DISCOVERY"
REPORT_NAME = "a1fs_v1_r8_reconciliation_local_runner.safe.json"
NEXT_SHORT_STEP = reconciliation.NEXT_SHORT_STEP


class LocalRunnerError(ValueError):
    """Fail-closed local discovery or execution error."""


def _read(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _local_root(path: Path) -> Path:
    resolved = Path(path).resolve()
    approved = (REPO_ROOT / ".local").resolve()
    if not resolved.is_relative_to(approved):
        raise LocalRunnerError(f"path_outside_local:{resolved}")
    if not resolved.is_dir():
        raise LocalRunnerError(f"local_root_missing:{resolved}")
    return resolved


def _json_files(root: Path) -> list[Path]:
    result: list[Path] = []
    for path in root.rglob("*.json"):
        try:
            if path.is_file() and path.stat().st_size <= 64 * 1024 * 1024:
                result.append(path.resolve())
        except OSError:
            continue
    return sorted(result, key=lambda path: str(path).casefold())


def _discover_legacy(files: list[Path]) -> list[dict[str, Path]]:
    values: dict[Path, dict[str, Any]] = {}
    hashes: dict[str, list[Path]] = defaultdict(list)
    for path in files:
        value = _read(path)
        if value is None:
            continue
        values[path] = value
        try:
            hashes[legacy.file_sha(path)].append(path)
        except OSError:
            continue
    banks: dict[str, Path] = {}
    registries: list[tuple[Path, dict[str, Any]]] = []
    consumers: list[tuple[Path, dict[str, Any]]] = []
    for path, value in values.items():
        if (
            value.get("task_id") == m08.TASK_ID
            and value.get("schema_version") == m08.SESSION_SCHEMA_VERSION
            and value.get("private_local_only") is True
            and value.get("item_count") == legacy.EXPECTED_ATTEMPTS
        ):
            banks[m08.sha256_value(value)] = path
        if path.name == "cumulative_attempt_registry.private.json" and value.get("task_id") == m08.TASK_ID:
            registries.append((path, value))
        if value.get("task_id") == "A1FS-V1-M2_FourSkillAssetBodyConsumerAndQuery" and value.get("validation_status") == legacy.CONSUMER_STATUS:
            consumers.append((path, value))
    chains: list[dict[str, Path]] = []
    for registry_path, registry in registries:
        bank_path = banks.get(str(registry.get("session_bank_sha256")))
        if bank_path is None:
            continue
        resolved_root = registry_path.parent
        required_resolved = (
            resolved_root / "cumulative_progress_ledger.private.json",
            resolved_root / "cumulative_progress_query_index.json",
        )
        if not all(path.is_file() for path in required_resolved):
            continue
        m12e1_root = resolved_root.parent
        if not (m12e1_root / "human_review_materialization_safe_report.json").is_file():
            continue
        for consumer_path, consumer in consumers:
            matching_assets = 0
            for asset in consumer.get("asset_records", []):
                payload = asset.get("payload") if isinstance(asset, Mapping) else None
                if isinstance(payload, Mapping) and payload.get("m12_session_bank_sha256") == registry.get("session_bank_sha256") and isinstance(payload.get("m12_item_id"), str):
                    matching_assets += 1
            if matching_assets != legacy.EXPECTED_ATTEMPTS:
                continue
            graph_paths = hashes.get(str(consumer.get("source_graph_sha256")), [])
            for graph_path in graph_paths:
                graph = values.get(graph_path) or _read(graph_path)
                if graph and graph.get("validation_status") == legacy.GRAPH_STATUS:
                    chains.append({
                        "source_bank_path": bank_path,
                        "resolved_root": resolved_root,
                        "m12e1_root": m12e1_root,
                        "consumer_path": consumer_path,
                        "graph_path": graph_path,
                    })
    unique: dict[tuple[str, ...], dict[str, Path]] = {}
    for row in chains:
        identity = tuple(legacy.file_sha(row[key]) if row[key].is_file() else str(row[key]) for key in ("source_bank_path", "consumer_path", "graph_path"))
        identity += (legacy.file_sha(row["resolved_root"] / "cumulative_attempt_registry.private.json"),)
        unique.setdefault(identity, row)
    return list(unique.values())


def _discover_current(files: list[Path]) -> list[dict[str, Any]]:
    banks: list[tuple[Path, dict[str, Any]]] = []
    supplies: list[tuple[Path, dict[str, Any]]] = []
    for path in files:
        value = _read(path)
        if value is None:
            continue
        if (
            value.get("task_id") == r4.TASK_ID
            and value.get("schema_version") == r4.BANK_SCHEMA_VERSION
            and value.get("validation_status") == r4.STATUS
            and value.get("private_local_only") is True
            and value.get("selection_contract", {}).get("authority_review_timestamp_externalized") is True
        ):
            core = {key: child for key, child in value.items() if key != "bank_sha256"}
            if value.get("bank_sha256") == r4.digest(core):
                banks.append((path, value))
        if value.get("task_id") == r4.TASK_ID and value.get("schema_version") == r4.SCHEMA_VERSION and value.get("validation_status") == r4.STATUS:
            core = {key: child for key, child in value.items() if key != "report_sha256"}
            if value.get("report_sha256") == r4.digest(core):
                supplies.append((path, value))
    pairs: dict[tuple[str, str], dict[str, Any]] = {}
    for bank_path, bank in banks:
        for supply_path, supply in supplies:
            if bank.get("source_bindings") != supply.get("source_bindings"):
                continue
            identity = (str(bank["bank_sha256"]), str(supply["report_sha256"]))
            candidate = {
                "current_bank_path": bank_path,
                "current_supply_path": supply_path,
                "current_bank_sha256": bank["bank_sha256"],
                "current_supply_sha256": supply["report_sha256"],
            }
            previous = pairs.get(identity)
            if previous is None or (len(bank_path.parts) + len(supply_path.parts), str(bank_path).casefold()) < (
                len(previous["current_bank_path"].parts) + len(previous["current_supply_path"].parts),
                str(previous["current_bank_path"]).casefold(),
            ):
                pairs[identity] = candidate
    return list(pairs.values())


def run(*, local_root: Path, output_root: Path | None = None) -> dict[str, Any]:
    local = _local_root(local_root)
    output = Path(output_root or (local / "a1fs_v1/r8_legacy_real_evidence_reconciliation")).resolve()
    if not output.is_relative_to((REPO_ROOT / ".local").resolve()):
        raise LocalRunnerError("output_outside_local")
    files = _json_files(local)
    legacy_chains = _discover_legacy(files)
    current_pairs = _discover_current(files)
    discovery_root = local / ".r8_reconciliation_discovery"
    shutil.rmtree(discovery_root, ignore_errors=True)
    ready: dict[tuple[str, str, str], dict[str, Any]] = {}
    inspected_count = 0
    try:
        for chain_index, chain in enumerate(legacy_chains, start=1):
            registry_sha = legacy.file_sha(chain["resolved_root"] / "cumulative_attempt_registry.private.json")
            for pair_index, pair in enumerate(current_pairs, start=1):
                inspected_count += 1
                probe = discovery_root / f"chain_{chain_index:03d}_pair_{pair_index:03d}"
                result = reconciliation.reconcile(
                    **chain,
                    current_bank_path=pair["current_bank_path"],
                    current_supply_path=pair["current_supply_path"],
                    output_root=probe,
                    mode="inspect",
                )["report"]
                if result.get("validation_status") != reconciliation.READY_STATUS:
                    continue
                identity = (registry_sha, pair["current_bank_sha256"], pair["current_supply_sha256"])
                ready.setdefault(identity, {"chain": chain, "pair": pair, "inspect": result})
        if len(ready) != 1:
            reason = "NO_UNIQUE_EXACT_RECONCILIATION_CHAIN" if not ready else "MULTIPLE_DISTINCT_EXACT_RECONCILIATION_CHAINS"
            core = {
                "task_id": TASK_ID,
                "schema_version": SCHEMA_VERSION,
                "validation_status": BLOCKED,
                "discovery_counts": {
                    "json_file_count": len(files),
                    "legacy_chain_count": len(legacy_chains),
                    "deterministic_current_pair_count": len(current_pairs),
                    "inspected_combination_count": inspected_count,
                    "exact_ready_identity_count": len(ready),
                },
                "claim_boundaries": {
                    "private_path_exposed": False,
                    "private_response_exposed": False,
                    "learner_outcome_modified": False,
                    "new_evidence_created": False,
                    "mastery_claimed": False,
                    "retention_confirmed": False,
                    "a2_unlocked": False,
                },
                "stop_reason": reason,
                "next_short_step": TASK_ID,
            }
            report = {**core, "report_sha256": r5.digest(core)}
            _write(local / REPORT_NAME, report)
            return report
        selected = next(iter(ready.values()))
        project = reconciliation.reconcile(
            **selected["chain"],
            current_bank_path=selected["pair"]["current_bank_path"],
            current_supply_path=selected["pair"]["current_supply_path"],
            output_root=output,
            mode="project",
        )["report"]
        checked = validator.validate(
            **selected["chain"],
            current_bank_path=selected["pair"]["current_bank_path"],
            current_supply_path=selected["pair"]["current_supply_path"],
            output_root=output,
            mode="project",
        )
        if project.get("validation_status") != reconciliation.PROJECTED_STATUS or checked.get("error_count") != 0:
            raise LocalRunnerError("reconciliation_projection_or_validation_failed")
        core = {
            "task_id": TASK_ID,
            "schema_version": SCHEMA_VERSION,
            "validation_status": STATUS,
            "discovery_counts": {
                "json_file_count": len(files),
                "legacy_chain_count": len(legacy_chains),
                "deterministic_current_pair_count": len(current_pairs),
                "inspected_combination_count": inspected_count,
                "exact_ready_identity_count": 1,
            },
            "reconciliation": {
                "legacy_real_attempt_count": project["counts"]["legacy_real_attempt_count"],
                "exact_mapped_attempt_count": project["counts"]["exact_mapped_attempt_count"],
                "mapped_breadth_cell_count": project["counts"]["mapped_breadth_cell_count"],
                "pass_count": project["counts"]["pass_count"],
                "failure_count": project["counts"]["failure_count"],
                "package_sha256": project["export"]["package_sha256"],
                "safe_summary_sha256": project["export"]["safe_summary_sha256"],
            },
            "claim_boundaries": {
                "private_path_exposed": False,
                "private_response_exposed": False,
                "learner_outcome_modified": False,
                "new_evidence_created": False,
                "mastery_claimed": False,
                "retention_confirmed": False,
                "a2_unlocked": False,
            },
            "stop_reason": "REAL_LEARNER_ATTESTATION_REQUIRED",
            "next_short_step": NEXT_SHORT_STEP,
        }
        report = {**core, "report_sha256": r5.digest(core)}
        _write(output / REPORT_NAME, report)
        return report
    finally:
        shutil.rmtree(discovery_root, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-root", type=Path, default=REPO_ROOT / ".local")
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    try:
        report = run(local_root=args.local_root, output_root=args.output_root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["validation_status"] == STATUS else 2
    except (LocalRunnerError, reconciliation.ReconciliationError, legacy.BridgeError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
