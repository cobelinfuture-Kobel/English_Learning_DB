#!/usr/bin/env python3
"""Discover private local evidence/production artifacts and run R8 reconciliation once.

Discovery is content-addressed. Legacy evidence files may be renamed or moved, and
current deterministic R4 artifacts are rematerialized from the exact legacy M1/M2
chain when they do not yet exist locally. Private files never leave ``.local``.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import build_a1fs_v1_r2_complete_breadth_ontology_deployment_contract as r2
from ulga.builders import build_a1fs_v1_r3r4_authority_reviewed_production_population as population
from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4
from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5
from ulga.builders import build_a1fs_v1_r8_legacy_real_evidence_deterministic_production_reconciliation as reconciliation
from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as m08
from ulga.builders import build_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge as legacy
from ulga.validators import validate_a1fs_v1_r3r4_authority_reviewed_production_population as population_validator
from ulga.validators import validate_a1fs_v1_r8_legacy_real_evidence_deterministic_production_reconciliation as validator

TASK_ID = "A1FS-V1-R8_LegacyRealEvidenceReconciliationLocalRunner"
SCHEMA_VERSION = "a1fs.v1.r8.legacy_real_evidence_local_runner.v2"
STATUS = "PASS_A1FS_V1_R8_LOCAL_RECONCILIATION_EXECUTED_AND_VALIDATED"
BLOCKED = "BLOCKED_A1FS_V1_R8_LOCAL_RECONCILIATION_DISCOVERY"
REPORT_NAME = "a1fs_v1_r8_reconciliation_local_runner.safe.json"
NEXT_SHORT_STEP = reconciliation.NEXT_SHORT_STEP
MATERIALIZATION_REVIEWED_AT = "2000-01-01T00:00:00Z"


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
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


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


def _choose_path(paths: list[Path]) -> Path:
    return min(paths, key=lambda path: (len(path.parts), str(path).casefold()))


def _outcome_counts(entries: list[Mapping[str, Any]]) -> dict[str, int]:
    counts = Counter(str(row.get("outcome")) for row in entries)
    return {name: counts[name] for name in m08.OUTCOMES}


def _report_matches_counts(report: Mapping[str, Any], expected: Mapping[str, int]) -> bool:
    value = report.get("outcome_counts")
    if not isinstance(value, Mapping):
        return True
    return all(int(value.get(name, 0)) == int(expected.get(name, 0)) for name in m08.OUTCOMES)


def _discover_legacy(
    files: list[Path],
    *,
    staging_root: Path,
) -> tuple[list[dict[str, Path]], dict[str, int]]:
    values: dict[Path, dict[str, Any]] = {}
    file_hashes: dict[str, list[Path]] = defaultdict(list)
    banks: dict[str, list[Path]] = defaultdict(list)
    registries: list[tuple[Path, dict[str, Any]]] = []
    ledgers: list[tuple[Path, dict[str, Any]]] = []
    consumers: list[tuple[Path, dict[str, Any]]] = []
    review_reports: list[tuple[Path, dict[str, Any]]] = []

    for path in files:
        value = _read(path)
        if value is None:
            continue
        values[path] = value
        try:
            file_hashes[legacy.file_sha(path)].append(path)
        except OSError:
            pass
        items = value.get("items")
        if (
            value.get("task_id") == m08.TASK_ID
            and value.get("schema_version") == m08.SESSION_SCHEMA_VERSION
            and value.get("private_local_only") is True
            and isinstance(items, list)
            and isinstance(value.get("item_count"), int)
            and value.get("item_count") == len(items)
            and len(items) >= legacy.EXPECTED_ATTEMPTS
            and len({
                str(item.get("item_id"))
                for item in items
                if isinstance(item, Mapping) and isinstance(item.get("item_id"), str)
            }) == len(items)
            and (
                "items_sha256" not in value
                or value.get("items_sha256") == m08.sha256_value(items)
            )
        ):
            banks[m08.sha256_value(value)].append(path)
        if (
            value.get("task_id") == m08.TASK_ID
            and value.get("schema_version") == m08.ATTEMPT_SCHEMA_VERSION
            and value.get("private_local_only") is True
            and isinstance(value.get("attempts"), list)
            and len(value["attempts"]) == legacy.EXPECTED_ATTEMPTS
        ):
            registries.append((path, value))
        if (
            value.get("task_id") == m08.TASK_ID
            and value.get("schema_version") == m08.LEDGER_SCHEMA_VERSION
            and value.get("private_local_only") is True
            and isinstance(value.get("entries"), list)
            and len(value["entries"]) == legacy.EXPECTED_ATTEMPTS
        ):
            ledgers.append((path, value))
        if (
            value.get("task_id") == "A1FS-V1-M2_FourSkillAssetBodyConsumerAndQuery"
            and value.get("validation_status") == legacy.CONSUMER_STATUS
            and isinstance(value.get("asset_records"), list)
        ):
            consumers.append((path, value))
        if (
            value.get("task_id") == legacy.M12E1_TASK_ID
            and value.get("validation_status") == legacy.M12E1_STATUS
            and value.get("remaining_pending_count") == 0
            and value.get("stop_reason") == "NONE"
        ):
            review_reports.append((path, value))

    unique_semantic: dict[tuple[str, ...], dict[str, Any]] = {}
    for registry_path, registry in registries:
        bank_paths = banks.get(str(registry.get("session_bank_sha256")), [])
        if not bank_paths:
            continue
        registry_hash = m08.sha256_value(registry)
        matching_ledgers = [
            (path, value)
            for path, value in ledgers
            if value.get("session_bank_sha256") == registry.get("session_bank_sha256")
            and value.get("attempt_registry_sha256") == registry_hash
            and int(value.get("attempt_count", len(value.get("entries", [])))) == legacy.EXPECTED_ATTEMPTS
        ]
        for ledger_path, ledger in matching_ledgers:
            expected_counts = _outcome_counts(ledger["entries"])
            matching_reports = [
                (path, value)
                for path, value in review_reports
                if _report_matches_counts(value, expected_counts)
            ]
            for report_path, report in matching_reports:
                for consumer_path, consumer in consumers:
                    matching_assets = 0
                    for asset in consumer.get("asset_records", []):
                        payload = asset.get("payload") if isinstance(asset, Mapping) else None
                        if (
                            isinstance(payload, Mapping)
                            and payload.get("m12_session_bank_sha256") == registry.get("session_bank_sha256")
                            and isinstance(payload.get("m12_item_id"), str)
                        ):
                            matching_assets += 1
                    if matching_assets != legacy.EXPECTED_ATTEMPTS:
                        continue
                    graph_paths = file_hashes.get(str(consumer.get("source_graph_sha256")), [])
                    for graph_path in graph_paths:
                        graph = values.get(graph_path) or _read(graph_path)
                        if not graph or graph.get("validation_status") != legacy.GRAPH_STATUS:
                            continue
                        identity = (
                            m08.sha256_value(registry),
                            m08.sha256_value(ledger),
                            m08.sha256_value(report),
                            m08.sha256_value(consumer),
                            m08.sha256_value(graph),
                            str(registry.get("session_bank_sha256")),
                        )
                        unique_semantic.setdefault(identity, {
                            "source_bank_path": _choose_path(bank_paths),
                            "registry": registry,
                            "ledger": ledger,
                            "report": report,
                            "consumer_path": consumer_path,
                            "graph_path": graph_path,
                        })

    chains: list[dict[str, Path]] = []
    staging_root.mkdir(parents=True, exist_ok=True)
    for index, row in enumerate(unique_semantic.values(), start=1):
        root = staging_root / f"legacy_{index:03d}"
        resolved_root = root / "resolved"
        m12e1_root = root / "m12e1"
        _write(resolved_root / "cumulative_attempt_registry.private.json", row["registry"])
        _write(resolved_root / "cumulative_progress_ledger.private.json", row["ledger"])
        _write(
            resolved_root / "cumulative_progress_query_index.json",
            {
                "task_id": m08.TASK_ID,
                "attempt_count": legacy.EXPECTED_ATTEMPTS,
                "items": [],
                "compatibility_layout_only": True,
            },
        )
        _write(m12e1_root / "human_review_materialization_safe_report.json", row["report"])
        chains.append({
            "source_bank_path": row["source_bank_path"],
            "resolved_root": resolved_root,
            "m12e1_root": m12e1_root,
            "consumer_path": row["consumer_path"],
            "graph_path": row["graph_path"],
        })

    diagnostics = {
        "legacy_bank_candidate_count": len(banks),
        "legacy_registry_candidate_count": len(registries),
        "legacy_ledger_candidate_count": len(ledgers),
        "legacy_consumer_candidate_count": len(consumers),
        "legacy_review_report_candidate_count": len(review_reports),
        "legacy_semantic_chain_count": len(chains),
    }
    return chains, diagnostics



def _nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return bool(value) and any(_nonempty(child) for child in value.values())
    if isinstance(value, list):
        return bool(value) and any(_nonempty(child) for child in value)
    return value is not None


def _stage_feature_context_compatibility(
    chains: list[dict[str, Path]],
    *,
    staging_root: Path,
) -> tuple[list[dict[str, Path]], dict[str, int]]:
    """Reuse only hash-bound M08 learner-visible context/options in a staged consumer."""
    staging_root.mkdir(parents=True, exist_ok=True)
    staged: list[dict[str, Path]] = []
    counts: Counter[str] = Counter()

    for index, chain in enumerate(chains, start=1):
        bank = _read(chain["source_bank_path"])
        consumer = _read(chain["consumer_path"])
        if bank is None or consumer is None:
            raise LocalRunnerError("learner_contract_compatibility_source_unreadable")

        bank_hash = m08.sha256_value(bank)
        bank_items = {
            str(row.get("item_id")): row
            for row in bank.get("items", [])
            if isinstance(row, Mapping) and isinstance(row.get("item_id"), str)
        }
        projected = deepcopy(consumer)
        feature_join_count = 0
        context_backfill_count = 0
        source_context_missing_count = 0
        existing_context_preserved_count = 0
        context_conflict_count = 0
        option_join_count = 0
        option_backfill_count = 0
        source_options_missing_count = 0
        existing_options_preserved_count = 0
        options_conflict_count = 0
        option_scoring_mismatch_count = 0

        for asset in projected.get("asset_records", []):
            if not isinstance(asset, Mapping):
                continue
            payload = asset.get("payload")
            if not isinstance(payload, Mapping):
                continue
            if payload.get("m12_session_bank_sha256") != bank_hash:
                continue
            item_id = payload.get("m12_item_id")
            if not isinstance(item_id, str):
                continue
            source_item = bank_items.get(item_id)
            if not isinstance(source_item, Mapping):
                continue
            try:
                derived = m6.derive_contract(asset)
            except (KeyError, TypeError, ValueError):
                continue

            source_contract = source_item.get("learner_contract")
            source_contract = source_contract if isinstance(source_contract, Mapping) else {}
            mode = str(derived.get("scoring_mode") or "")

            if mode == "FEATURE_RUBRIC":
                feature_join_count += 1
                source_context = source_contract.get("context")
                existing_context = population._context(payload)
                if existing_context:
                    existing_context_preserved_count += 1
                    if _nonempty(source_context) and existing_context != source_context:
                        context_conflict_count += 1
                    continue
                if not _nonempty(source_context):
                    source_context_missing_count += 1
                    continue
                payload["context"] = deepcopy(source_context)
                payload["compatibility_context_binding"] = {
                    "mode": "M08_HASH_BOUND_LEARNER_CONTEXT_REUSE",
                    "source_session_bank_sha256": bank_hash,
                    "source_item_id": item_id,
                    "source_context_sha256": m08.sha256_value(source_context),
                    "canonical_m2_modified": False,
                }
                asset["content_digest"] = population.digest(payload)
                context_backfill_count += 1
                continue

            if mode != "EXACT_OPTION":
                continue

            option_join_count += 1
            raw_source_options = source_contract.get("options")
            source_options = (
                [row.strip() for row in raw_source_options]
                if isinstance(raw_source_options, list)
                and all(isinstance(row, str) and row.strip() for row in raw_source_options)
                else []
            )
            source_options_valid = (
                len(source_options) >= 2
                and len(source_options) == len(set(source_options))
                and source_contract.get("response_mode") == "select_one"
            )
            accepted = [
                row.strip()
                for row in derived.get("accepted_texts", [])
                if isinstance(row, str) and row.strip()
            ]
            existing_options = population._options(payload)

            if existing_options:
                existing_options_preserved_count += 1
                if source_options_valid and existing_options != source_options:
                    options_conflict_count += 1
                if not accepted or any(answer not in existing_options for answer in accepted):
                    option_scoring_mismatch_count += 1
                continue

            if not source_options_valid:
                source_options_missing_count += 1
                continue
            if not accepted or any(answer not in source_options for answer in accepted):
                option_scoring_mismatch_count += 1
                continue

            payload["options"] = deepcopy(source_options)
            payload["compatibility_options_binding"] = {
                "mode": "M08_HASH_BOUND_LEARNER_OPTIONS_REUSE",
                "source_session_bank_sha256": bank_hash,
                "source_item_id": item_id,
                "source_options_sha256": m08.sha256_value(source_options),
                "canonical_m2_modified": False,
            }
            asset["content_digest"] = population.digest(payload)
            option_backfill_count += 1

        if context_conflict_count:
            raise LocalRunnerError("feature_context_source_m2_conflict")
        if options_conflict_count:
            raise LocalRunnerError("exact_option_source_m2_conflict")
        if option_scoring_mismatch_count:
            raise LocalRunnerError("exact_option_source_scoring_mismatch")

        projected["compatibility_projection"] = {
            "mode": "M08_HASH_BOUND_LEARNER_CONTRACT_BACKFILL",
            "source_consumer_sha256": legacy.file_sha(chain["consumer_path"]),
            "source_session_bank_sha256": bank_hash,
            "feature_rubric_exact_join_count": feature_join_count,
            "context_backfill_count": context_backfill_count,
            "source_context_missing_count": source_context_missing_count,
            "existing_context_preserved_count": existing_context_preserved_count,
            "exact_option_exact_join_count": option_join_count,
            "option_backfill_count": option_backfill_count,
            "source_options_missing_count": source_options_missing_count,
            "existing_options_preserved_count": existing_options_preserved_count,
            "canonical_m2_modified": False,
            "new_context_created": False,
            "new_options_created": False,
        }
        staged_path = staging_root / f"compatibility_consumer_{index:03d}.private.json"
        _write(staged_path, projected)
        staged_chain = dict(chain)
        staged_chain["consumer_path"] = staged_path
        staged.append(staged_chain)

        counts["compatibility_consumer_count"] += 1
        counts["compatibility_feature_rubric_exact_join_count"] += feature_join_count
        counts["compatibility_context_backfill_count"] += context_backfill_count
        counts["compatibility_source_context_missing_count"] += source_context_missing_count
        counts["compatibility_existing_context_preserved_count"] += existing_context_preserved_count
        counts["compatibility_context_conflict_count"] += context_conflict_count
        counts["compatibility_exact_option_exact_join_count"] += option_join_count
        counts["compatibility_option_backfill_count"] += option_backfill_count
        counts["compatibility_source_options_missing_count"] += source_options_missing_count
        counts["compatibility_existing_options_preserved_count"] += existing_options_preserved_count
        counts["compatibility_options_conflict_count"] += options_conflict_count
        counts["compatibility_option_scoring_mismatch_count"] += option_scoring_mismatch_count

    for key in (
        "compatibility_consumer_count",
        "compatibility_feature_rubric_exact_join_count",
        "compatibility_context_backfill_count",
        "compatibility_source_context_missing_count",
        "compatibility_existing_context_preserved_count",
        "compatibility_context_conflict_count",
        "compatibility_exact_option_exact_join_count",
        "compatibility_option_backfill_count",
        "compatibility_source_options_missing_count",
        "compatibility_existing_options_preserved_count",
        "compatibility_options_conflict_count",
        "compatibility_option_scoring_mismatch_count",
    ):
        counts.setdefault(key, 0)
    return staged, dict(counts)


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
        if (
            value.get("task_id") == r4.TASK_ID
            and value.get("schema_version") == r4.SCHEMA_VERSION
            and value.get("validation_status") == r4.STATUS
        ):
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
            if previous is None or (
                len(bank_path.parts) + len(supply_path.parts),
                str(bank_path).casefold(),
            ) < (
                len(previous["current_bank_path"].parts) + len(previous["current_supply_path"].parts),
                str(previous["current_bank_path"]).casefold(),
            ):
                pairs[identity] = candidate
    return list(pairs.values())


def _merge_pairs(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for group in groups:
        for row in group:
            identity = (str(row["current_bank_sha256"]), str(row["current_supply_sha256"]))
            merged.setdefault(identity, row)
    return list(merged.values())


def _materialize_current(
    chains: list[dict[str, Path]],
    *,
    staging_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    staging_root.mkdir(parents=True, exist_ok=True)
    ontology_path = staging_root / "a1fs_v1_r2_complete_breadth_ontology.generated.json"
    _write(ontology_path, r2.build_ontology())
    attempted = validated = failed = 0
    for index, chain in enumerate(chains, start=1):
        attempted += 1
        output_root = staging_root / f"production_{index:03d}"
        try:
            population.materialize(
                ontology_path=ontology_path,
                graph_path=chain["graph_path"],
                consumer_path=chain["consumer_path"],
                output_root=output_root,
                reviewed_at=MATERIALIZATION_REVIEWED_AT,
            )
            checked = population_validator.validate(
                ontology_path=ontology_path,
                graph_path=chain["graph_path"],
                consumer_path=chain["consumer_path"],
                output_root=output_root,
            )
            if checked.get("error_count") != 0:
                failed += 1
                continue
            validated += 1
        except (OSError, KeyError, TypeError, ValueError):
            failed += 1
            continue
    pairs = _discover_current(_json_files(staging_root))
    return pairs, {
        "deterministic_materialization_attempt_count": attempted,
        "deterministic_materialization_validated_count": validated,
        "deterministic_materialization_failed_count": failed,
        "deterministic_materialized_pair_count": len(pairs),
    }


def _inspect(
    chains: list[dict[str, Path]],
    pairs: list[dict[str, Any]],
    *,
    staging_root: Path,
) -> tuple[dict[tuple[str, str, str], dict[str, Any]], int, dict[str, Any]]:
    ready: dict[tuple[str, str, str], dict[str, Any]] = {}
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
            identity = (
                registry_sha,
                str(pair["current_bank_sha256"]),
                str(pair["current_supply_sha256"]),
            )
            ready.setdefault(identity, {"chain": chain, "pair": pair, "inspect": result})
    diagnostics = {
        "inspect_exception_count": inspect_exception_count,
        "inspect_status_counts": dict(sorted(status_counts.items())),
        "issue_combination_counts": dict(sorted(issue_combination_counts.items())),
        "issue_item_counts": dict(sorted(issue_item_counts.items())),
        "max_exact_mapped_attempt_count": max_exact_mapped_attempt_count,
        "max_mapped_breadth_cell_count": max_mapped_breadth_cell_count,
        "max_pass_count": max_pass_count,
        "max_failure_count": max_failure_count,
    }
    return ready, inspected_count, diagnostics


def _blocked_report(
    *,
    local: Path,
    files: list[Path],
    legacy_chains: list[dict[str, Path]],
    current_pairs: list[dict[str, Any]],
    inspected_count: int,
    ready_count: int,
    legacy_diagnostics: Mapping[str, int],
    materialization_diagnostics: Mapping[str, int],
    reconciliation_diagnostics: Mapping[str, Any],
) -> dict[str, Any]:
    reason = (
        "NO_UNIQUE_EXACT_RECONCILIATION_CHAIN"
        if ready_count == 0
        else "MULTIPLE_DISTINCT_EXACT_RECONCILIATION_CHAINS"
    )
    core = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": BLOCKED,
        "discovery_counts": {
            "json_file_count": len(files),
            "legacy_chain_count": len(legacy_chains),
            "deterministic_current_pair_count": len(current_pairs),
            "inspected_combination_count": inspected_count,
            "exact_ready_identity_count": ready_count,
            **dict(legacy_diagnostics),
            **dict(materialization_diagnostics),
        },
        "reconciliation_diagnostics": dict(reconciliation_diagnostics),
        "claim_boundaries": {
            "private_path_exposed": False,
            "private_response_exposed": False,
            "learner_outcome_modified": False,
            "new_evidence_created": False,
            "new_context_created": False,
            "new_options_created": False,
            "canonical_m2_modified": False,
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


def run(*, local_root: Path, output_root: Path | None = None) -> dict[str, Any]:
    local = _local_root(local_root)
    output = Path(
        output_root or (local / "a1fs_v1/r8_legacy_real_evidence_reconciliation")
    ).resolve()
    if not output.is_relative_to((REPO_ROOT / ".local").resolve()):
        raise LocalRunnerError("output_outside_local")

    discovery_root = local / ".r8_reconciliation_discovery"
    shutil.rmtree(discovery_root, ignore_errors=True)
    discovery_root.mkdir(parents=True, exist_ok=True)
    try:
        files = _json_files(local)
        legacy_chains, legacy_diagnostics = _discover_legacy(
            files,
            staging_root=discovery_root / "legacy",
        )
        legacy_chains, compatibility_diagnostics = _stage_feature_context_compatibility(
            legacy_chains,
            staging_root=discovery_root / "compatibility_consumers",
        )
        legacy_diagnostics = {**legacy_diagnostics, **compatibility_diagnostics}
        current_pairs = _discover_current(files)
        ready, inspected_count, reconciliation_diagnostics = _inspect(
            legacy_chains,
            current_pairs,
            staging_root=discovery_root / "existing_probes",
        )
        materialization_diagnostics = {
            "deterministic_materialization_attempt_count": 0,
            "deterministic_materialization_validated_count": 0,
            "deterministic_materialization_failed_count": 0,
            "deterministic_materialized_pair_count": 0,
        }
        if not ready and legacy_chains:
            generated_pairs, materialization_diagnostics = _materialize_current(
                legacy_chains,
                staging_root=discovery_root / "materialized",
            )
            current_pairs = _merge_pairs(current_pairs, generated_pairs)
            ready, inspected_count, reconciliation_diagnostics = _inspect(
                legacy_chains,
                current_pairs,
                staging_root=discovery_root / "all_probes",
            )

        if len(ready) != 1:
            return _blocked_report(
                local=local,
                files=files,
                legacy_chains=legacy_chains,
                current_pairs=current_pairs,
                inspected_count=inspected_count,
                ready_count=len(ready),
                legacy_diagnostics=legacy_diagnostics,
                materialization_diagnostics=materialization_diagnostics,
                reconciliation_diagnostics=reconciliation_diagnostics,
            )

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
        if (
            project.get("validation_status") != reconciliation.PROJECTED_STATUS
            or checked.get("error_count") != 0
        ):
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
                **legacy_diagnostics,
                **materialization_diagnostics,
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
                "new_context_created": False,
                "new_options_created": False,
                "canonical_m2_modified": False,
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
    except (
        LocalRunnerError,
        reconciliation.ReconciliationError,
        legacy.BridgeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
