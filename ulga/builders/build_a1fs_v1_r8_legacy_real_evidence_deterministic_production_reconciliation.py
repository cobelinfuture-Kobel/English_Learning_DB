#!/usr/bin/env python3
"""Reconcile resolved M12E1 real evidence with the deterministic R4/R5 production line.

This adapter does not alter learner outcomes or invent new evidence. It proves an
exact compatibility mapping from the legacy M12 item through its M2 asset and M1
node to one current R4-admitted item and breadth cell. Only a fully exact mapping
may be projected into the existing R5 private/safe evidence export schema.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import build_a1fs_v1_r3r4_authority_reviewed_production_population as production
from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4
from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5
from ulga.builders import build_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge as legacy
from ulga.builders import build_e4s_a1v1_m12g_learner_contract_assessment_validity_fullfix as assessment

TASK_ID = "A1FS-V1-R8_LegacyRealEvidenceToDeterministicProductionReconciliation"
SCHEMA_VERSION = "a1fs.v1.r8.legacy_real_evidence_reconciliation.v1"
READY_STATUS = "PASS_A1FS_V1_R8_LEGACY_REAL_EVIDENCE_RECONCILIATION_READY"
PROJECTED_STATUS = "PASS_A1FS_V1_R8_LEGACY_REAL_EVIDENCE_PROJECTED_TO_R5_EXPORT"
BLOCKED_STATUS = "BLOCKED_A1FS_V1_R8_LEGACY_REAL_EVIDENCE_RECONCILIATION"
NEXT_SHORT_STEP = "A1FS-V1-R8_CollectRealLearnerAttestationForReconciledEvidence"
REPORT_NAME = "a1fs_v1_r8_legacy_real_evidence_reconciliation.safe.json"
PACKAGE_NAME = "a1fs_v1_r5_edge_evidence.reconciled.private.json"
SAFE_NAME = "a1fs_v1_r5_edge_evidence.reconciled.safe.json"
JSONL_NAME = "a1fs_v1_r5_edge_events.reconciled.private.jsonl"


class ReconciliationError(ValueError):
    """Fail-closed reconciliation error."""


def _safe_root(path: Path) -> Path:
    resolved = Path(path).resolve()
    approved = (REPO_ROOT / ".local").resolve()
    if not resolved.is_relative_to(approved):
        raise ReconciliationError(f"path_outside_local:{resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _read(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReconciliationError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise ReconciliationError(f"{code}_not_object")
    return value


def _write(path: Path, value: Mapping[str, Any], *, private: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    if private:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


def _file_sha(path: Path) -> str:
    return r5.file_digest(Path(path))


def _load_current(bank_path: Path, supply_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    bank = _read(bank_path, "current_bank")
    supply = _read(supply_path, "current_supply")
    bank_core = {key: value for key, value in bank.items() if key != "bank_sha256"}
    supply_core = {key: value for key, value in supply.items() if key != "report_sha256"}
    if bank.get("task_id") != r4.TASK_ID or bank.get("schema_version") != r4.BANK_SCHEMA_VERSION:
        raise ReconciliationError("current_bank_identity_invalid")
    if supply.get("task_id") != r4.TASK_ID or supply.get("schema_version") != r4.SCHEMA_VERSION:
        raise ReconciliationError("current_supply_identity_invalid")
    if bank.get("validation_status") != r4.STATUS or supply.get("validation_status") != r4.STATUS:
        raise ReconciliationError("current_r4_status_invalid")
    if bank.get("private_local_only") is not True:
        raise ReconciliationError("current_bank_privacy_invalid")
    if bank.get("bank_sha256") != r4.digest(bank_core):
        raise ReconciliationError("current_bank_digest_invalid")
    if supply.get("report_sha256") != r4.digest(supply_core):
        raise ReconciliationError("current_supply_digest_invalid")
    if bank.get("source_bindings") != supply.get("source_bindings"):
        raise ReconciliationError("current_bank_supply_binding_mismatch")
    if not isinstance(bank.get("items"), list) or bank.get("item_count") != len(bank["items"]):
        raise ReconciliationError("current_bank_item_denominator_invalid")
    if not isinstance(supply.get("cell_supply"), list):
        raise ReconciliationError("current_supply_cells_invalid")
    return bank, supply


def _expected_contract(asset: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str]:
    derived = m6.derive_contract(asset)
    learner, scoring, task_type, *_ = production._task_projection(asset, derived)
    validated_learner, validated_scoring = assessment.validate_learner_contract(
        item_id=str(asset["asset_key"]),
        task_type=task_type.casefold(),
        learner=learner,
        scoring=scoring,
    )
    return validated_learner, validated_scoring, task_type


def _review_outcome(scoring: Mapping[str, Any], response: Any, review: Mapping[str, Any]) -> tuple[str, float | None]:
    outcome, score = m6.ResponseEvidenceStore.score(dict(scoring), response)
    if scoring.get("scoring_mode") == "FEATURE_RUBRIC" and review.get("decision") != "PENDING":
        decision = str(review.get("decision"))
        if decision not in {"APPROVE", "REJECT", "DEFER"}:
            raise ReconciliationError("legacy_operator_review_decision_invalid")
        outcome = {"APPROVE": "HUMAN_APPROVE", "REJECT": "HUMAN_REJECT", "DEFER": "HUMAN_DEFER"}[decision]
        score = 1.0 if decision == "APPROVE" else 0.0 if decision == "REJECT" else None
    return outcome, score


def _safe_scan(value: Any) -> None:
    forbidden = {
        "response", "operator_review", "learner_id", "learner_ref", "display_label",
        "reviewer_id", "notes", "prompt", "context", "accepted_texts",
        "accepted_sequence", "private_scoring_contract", "learner_contract",
    }

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in forbidden:
                    raise ReconciliationError(f"safe_private_field:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            if Path(node).is_absolute() or (len(node) > 2 and node[1:3] in {":/", ":\\"}):
                raise ReconciliationError("safe_absolute_path")

    walk(value)


def _map_current(
    *, source: Mapping[str, Any], legacy_mapping: Mapping[str, Any],
    bank: Mapping[str, Any], supply: Mapping[str, Any],
) -> dict[str, Any]:
    assets = {str(row.get("asset_key")): row for row in source["consumer"].get("asset_records", [])}
    supply_by_cell = {
        str(row.get("breadth_cell_id")): row
        for row in supply["cell_supply"] if isinstance(row, Mapping)
    }
    current_items = [row for row in bank["items"] if isinstance(row, Mapping)]
    mapped: list[dict[str, Any]] = []
    issues: dict[str, list[str]] = {
        "legacy_mapping_issue_codes": [],
        "multi_node_legacy_item_ids": [],
        "current_item_missing_ids": [],
        "current_contract_drift_ids": [],
        "current_item_ambiguous_ids": [],
        "current_supply_not_ready_ids": [],
        "duplicate_current_item_ids": [],
        "outcome_rebuild_drift_ids": [],
    }
    for code, rows in legacy_mapping["issues"].items():
        if rows:
            issues["legacy_mapping_issue_codes"].append(code)
    attempts_by_id = {str(row["item_id"]): row for row in source["attempts"]}
    seen_current: set[str] = set()
    for legacy_row in legacy_mapping["mapped"]:
        legacy_item_id = str(legacy_row["item_id"])
        node_ids = list(legacy_row["required_node_ids"])
        if len(node_ids) != 1:
            issues["multi_node_legacy_item_ids"].append(legacy_item_id)
            continue
        node_id = str(node_ids[0])
        asset_key = str(legacy_row["asset_key"])
        asset = assets.get(asset_key)
        if not asset:
            issues["current_item_missing_ids"].append(legacy_item_id)
            continue
        expected_learner, expected_scoring, expected_task_type = _expected_contract(asset)
        source_refs = {f"M2_ASSET:{asset_key}", f"M1_NODE:{node_id}"}
        structural = [
            row for row in current_items
            if source_refs.issubset(set(row.get("source_refs", [])))
            and row.get("admission", {}).get("status") == "APPROVED"
            and row.get("level") in {"A1", "A1_PLUS"}
        ]
        if not structural:
            issues["current_item_missing_ids"].append(legacy_item_id)
            continue
        exact = [
            row for row in structural
            if row.get("task_type") == expected_task_type
            and row.get("learner_contract") == expected_learner
            and row.get("private_scoring_contract") == expected_scoring
        ]
        if not exact:
            issues["current_contract_drift_ids"].append(legacy_item_id)
            continue
        if len(exact) != 1:
            issues["current_item_ambiguous_ids"].append(legacy_item_id)
            continue
        current = exact[0]
        current_item_id = str(current["item_id"])
        if current_item_id in seen_current:
            issues["duplicate_current_item_ids"].append(legacy_item_id)
            continue
        cell = supply_by_cell.get(str(current["breadth_cell_id"]))
        if not cell or cell.get("supply_status") != r5.ASSIGNABLE_CELL_STATUS or current_item_id not in cell.get("approved_item_ids", []):
            issues["current_supply_not_ready_ids"].append(legacy_item_id)
            continue
        source_attempt = attempts_by_id[legacy_item_id]
        source_entry = source["entries_by_id"][legacy_item_id]
        outcome, score = _review_outcome(
            expected_scoring,
            source_attempt.get("response"),
            source_attempt.get("operator_review") or {},
        )
        if outcome != source_entry.get("outcome") or score != source_entry.get("score"):
            issues["outcome_rebuild_drift_ids"].append(legacy_item_id)
            continue
        seen_current.add(current_item_id)
        mapped.append({
            "legacy_item_id": legacy_item_id,
            "legacy_evidence_id": str(source_entry.get("evidence_id") or ""),
            "asset_key": asset_key,
            "node_id": node_id,
            "current_item_id": current_item_id,
            "breadth_cell_id": str(current["breadth_cell_id"]),
            "current_item": deepcopy(dict(current)),
            "contract_sha256": r5.digest({
                "learner_contract": expected_learner,
                "private_scoring_contract": expected_scoring,
            }),
        })
    ready = (
        legacy_mapping.get("ready") is True
        and len(mapped) == legacy.EXPECTED_ATTEMPTS
        and not any(issues.values())
    )
    return {"ready": ready, "mapped": mapped, "issues": issues}


def _build_exports(
    *, source: Mapping[str, Any], current: Mapping[str, Any],
    bank: Mapping[str, Any], supply: Mapping[str, Any], source_bindings: Mapping[str, str],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    attempts_by_id = {str(row["item_id"]): row for row in source["attempts"]}
    learner_id = str(source["registry"].get("learner_ref") or "")
    if not learner_id:
        raise ReconciliationError("legacy_learner_ref_missing")
    entries: list[dict[str, Any]] = []
    previous_hash = "0" * 64
    for row in sorted(current["mapped"], key=lambda value: (source["entries_by_id"][value["legacy_item_id"]]["submitted_at"], value["legacy_item_id"])):
        source_attempt = attempts_by_id[row["legacy_item_id"]]
        source_entry = source["entries_by_id"][row["legacy_item_id"]]
        item = row["current_item"]
        response = deepcopy(source_attempt.get("response"))
        session_id = "R8_RECON_SESSION:" + r5.digest({
            "legacy_session_id": source["registry"].get("session_id"),
            "breadth_cell_id": row["breadth_cell_id"],
        })[:24]
        attempt_id = "R8_RECON_ATTEMPT:" + r5.digest({
            "legacy_registry_sha256": source_bindings["legacy_registry_sha256"],
            "legacy_item_id": row["legacy_item_id"],
            "current_item_id": row["current_item_id"],
        })[:24]
        submitted_at = r5.utc(str(source_entry["submitted_at"]))
        attempt_core = {
            "attempt_id": attempt_id,
            "session_id": session_id,
            "learner_id": learner_id,
            "item_id": row["current_item_id"],
            "response": response,
            "response_time_ms": 0,
            "hint_count": 0,
            "revision_count": 0,
            "submitted_at": submitted_at,
        }
        attempt_hash = r5.digest(previous_hash + r5.canonical(attempt_core))
        previous_hash = attempt_hash
        entries.append({
            "attempt_id": attempt_id,
            "session_id": session_id,
            "item_id": row["current_item_id"],
            "breadth_cell_id": row["breadth_cell_id"],
            "capability_id": item["capability_id"],
            "life_task_id": item["life_task_id"],
            "domain": item["domain"],
            "level": item["level"],
            "skill": item["skill"],
            "purpose": item["purpose"],
            "task_type": item["task_type"],
            "support_level": item["support_level"],
            "initiative_level": item["initiative_level"],
            "interaction_variation": item["interaction_variation"],
            "transfer_distance": item["transfer_distance"],
            "template_family": item["template_family"],
            "stimulus_fingerprint": item["stimulus_fingerprint"],
            "response": response,
            "response_sha256": r5.digest(response),
            "response_time_ms": 0,
            "hint_count": 0,
            "revision_count": 0,
            "submitted_at": submitted_at,
            "session_state": "COMPLETED",
            "scoring_mode": source_entry["scoring_mode"],
            "outcome": source_entry["outcome"],
            "score": source_entry.get("score"),
            "human_review_required": item["private_scoring_contract"].get("scoring_mode") == "FEATURE_RUBRIC",
            "operator_review": deepcopy(source_attempt.get("operator_review") or {}),
            "validity_status": "VALID",
            "attempt_hash": attempt_hash,
            "telemetry_status": "NOT_CAPTURED_LEGACY_ZERO_FILLED",
            "compatibility_projection": {
                "source_task_id": legacy.TASK_ID,
                "source_item_id": row["legacy_item_id"],
                "source_evidence_id": row["legacy_evidence_id"],
                "asset_key_sha256": r5.digest(row["asset_key"]),
                "node_id_sha256": r5.digest(row["node_id"]),
                "contract_sha256": row["contract_sha256"],
                "mapping_basis": "EXACT_M2_ASSET_M1_NODE_AND_NORMALIZED_CONTRACT",
            },
        })
    exported_at = max(row["submitted_at"] for row in entries)
    valid = [row for row in entries if row["validity_status"] == "VALID"]
    resolved = [row for row in valid if row["outcome"] in r5.RESOLVED_OUTCOMES]
    objective_summary: dict[str, dict[str, int]] = {}
    for cell_id in sorted({row["breadth_cell_id"] for row in valid}):
        rows = [row for row in valid if row["breadth_cell_id"] == cell_id]
        objective_summary[cell_id] = {
            "attempts": len(rows),
            "passes": sum(row["outcome"] in r5.PASS_OUTCOMES for row in rows),
            "failures": sum(row["outcome"] in r5.FAIL_OUTCOMES for row in rows),
            "unresolved": sum(row["outcome"] in r5.UNRESOLVED_OUTCOMES for row in rows),
        }
    projection_binding = {
        **source_bindings,
        "current_bank_sha256": bank["bank_sha256"],
        "current_supply_sha256": supply["report_sha256"],
        "mapping_sha256": r5.digest([{key: row[key] for key in ("legacy_item_id", "current_item_id", "breadth_cell_id", "contract_sha256")} for row in current["mapped"]]),
    }
    boundaries = {
        "mastery_written": False,
        "retention_confirmed": False,
        "gpt_analysis_performed": False,
        "qwen_used": False,
        "a2_unlocked": False,
        "public_delivery": False,
    }
    package_core = {
        "task_id": r5.TASK_ID,
        "schema_version": r5.PACKAGE_SCHEMA_VERSION,
        "validation_status": r5.STATUS,
        "private_local_only": True,
        "learner_id": learner_id,
        "exported_at": exported_at,
        "database_binding_sha256": r5.digest(projection_binding),
        "database_binding_type": "LEGACY_COMPATIBILITY_PROJECTION_RECEIPT",
        "projection_binding": projection_binding,
        "attempt_count": len(entries),
        "valid_attempt_count": len(valid),
        "resolved_valid_attempt_count": len(resolved),
        "entries": entries,
        "entries_sha256": r5.digest(entries),
        "objective_summary": objective_summary,
        "claim_boundaries": boundaries,
        "next_short_step": r5.NEXT_SHORT_STEP,
    }
    package = {**package_core, "package_sha256": r5.digest(package_core)}
    safe_entries = [
        {key: value for key, value in row.items() if key not in {"response", "operator_review"}}
        for row in entries
    ]
    safe_core = {
        "task_id": r5.TASK_ID,
        "schema_version": r5.SAFE_SCHEMA_VERSION,
        "validation_status": r5.STATUS,
        "learner_ref_sha256": r5.digest(learner_id),
        "exported_at": exported_at,
        "attempt_count": len(entries),
        "valid_attempt_count": len(valid),
        "resolved_valid_attempt_count": len(resolved),
        "outcome_counts": dict(sorted(Counter(row["outcome"] for row in entries).items())),
        "validity_counts": dict(sorted(Counter(row["validity_status"] for row in entries).items())),
        "objective_summary": objective_summary,
        "entries": safe_entries,
        "entries_sha256": r5.digest(safe_entries),
        "projection_binding": projection_binding,
        "claim_boundaries": boundaries,
        "next_short_step": r5.NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "summary_sha256": r5.digest(safe_core)}
    return package, safe, entries


def reconcile(
    *, source_bank_path: Path, resolved_root: Path, m12e1_root: Path,
    consumer_path: Path, graph_path: Path, current_bank_path: Path,
    current_supply_path: Path, output_root: Path, mode: str = "project",
) -> dict[str, Any]:
    if mode not in {"inspect", "project"}:
        raise ReconciliationError("mode_invalid")
    root = _safe_root(output_root)
    source = legacy._load_sources(
        source_bank_path=source_bank_path,
        resolved_root=resolved_root,
        m12e1_root=m12e1_root,
        consumer_path=consumer_path,
        graph_path=graph_path,
    )
    legacy_mapping = legacy._mapping(source)
    bank, supply = _load_current(current_bank_path, current_supply_path)
    current = _map_current(source=source, legacy_mapping=legacy_mapping, bank=bank, supply=supply)
    source_bindings = {
        "legacy_source_bank_sha256": _file_sha(source_bank_path),
        "legacy_registry_sha256": _file_sha(resolved_root / "cumulative_attempt_registry.private.json"),
        "legacy_ledger_sha256": _file_sha(resolved_root / "cumulative_progress_ledger.private.json"),
        "legacy_consumer_sha256": _file_sha(consumer_path),
        "legacy_graph_sha256": _file_sha(graph_path),
    }
    status = READY_STATUS if current["ready"] else BLOCKED_STATUS
    report_core: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": mode.upper(),
        "validation_status": status,
        "source_bindings": {
            **source_bindings,
            "current_bank_sha256": bank["bank_sha256"],
            "current_supply_sha256": supply["report_sha256"],
        },
        "counts": {
            "legacy_real_attempt_count": len(source["attempts"]),
            "exact_mapped_attempt_count": len(current["mapped"]),
            "mapped_breadth_cell_count": len({row["breadth_cell_id"] for row in current["mapped"]}),
            "pass_count": sum(source["entries_by_id"][row["legacy_item_id"]]["outcome"] in r5.PASS_OUTCOMES for row in current["mapped"]),
            "failure_count": sum(source["entries_by_id"][row["legacy_item_id"]]["outcome"] in r5.FAIL_OUTCOMES for row in current["mapped"]),
        },
        "mapping": [{
            "legacy_item_id_sha256": r5.digest(row["legacy_item_id"]),
            "current_item_id": row["current_item_id"],
            "breadth_cell_id": row["breadth_cell_id"],
            "contract_sha256": row["contract_sha256"],
        } for row in current["mapped"]],
        "issues": current["issues"],
        "export": None,
        "claim_boundaries": {
            "legacy_outcomes_modified": False,
            "new_learner_evidence_created": False,
            "compatibility_projection_only": True,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "a2_unlocked": False,
            "public_delivery": False,
            "audio_or_recording_processed": False,
        },
        "stop_reason": "MAPPING_OR_CONTRACT_DRIFT" if not current["ready"] else "NONE",
        "next_short_step": TASK_ID if not current["ready"] else NEXT_SHORT_STEP,
    }
    if mode == "project" and current["ready"]:
        package, safe, entries = _build_exports(
            source=source,
            current=current,
            bank=bank,
            supply=supply,
            source_bindings=source_bindings,
        )
        _write(root / PACKAGE_NAME, package)
        _write(root / SAFE_NAME, safe, private=False)
        jsonl = root / JSONL_NAME
        jsonl.write_text("".join(r5.canonical(row) + "\n" for row in entries), encoding="utf-8")
        try:
            os.chmod(jsonl, 0o600)
        except OSError:
            pass
        report_core["validation_status"] = PROJECTED_STATUS
        report_core["export"] = {
            "package_sha256": package["package_sha256"],
            "safe_summary_sha256": safe["summary_sha256"],
            "attempt_count": len(entries),
            "resolved_valid_attempt_count": safe["resolved_valid_attempt_count"],
        }
        report_core["stop_reason"] = "REAL_LEARNER_ATTESTATION_REQUIRED"
    report = {**report_core, "report_sha256": r5.digest(report_core)}
    _safe_scan(report)
    _write(root / REPORT_NAME, report, private=False)
    return {"report": report, "output_root": root}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("inspect", "project"))
    parser.add_argument("--source-bank", type=Path, required=True)
    parser.add_argument("--resolved-root", type=Path, required=True)
    parser.add_argument("--m12e1-root", type=Path, required=True)
    parser.add_argument("--consumer", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--current-bank", type=Path, required=True)
    parser.add_argument("--current-supply", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = reconcile(
            source_bank_path=args.source_bank,
            resolved_root=args.resolved_root,
            m12e1_root=args.m12e1_root,
            consumer_path=args.consumer,
            graph_path=args.graph,
            current_bank_path=args.current_bank,
            current_supply_path=args.current_supply,
            output_root=args.output_root,
            mode=args.mode,
        )
        report = result["report"]
        print(json.dumps({
            "validation_status": report["validation_status"],
            "legacy_real_attempt_count": report["counts"]["legacy_real_attempt_count"],
            "exact_mapped_attempt_count": report["counts"]["exact_mapped_attempt_count"],
            "mapped_breadth_cell_count": report["counts"]["mapped_breadth_cell_count"],
            "stop_reason": report["stop_reason"],
            "next_short_step": report["next_short_step"],
        }, ensure_ascii=False, indent=2))
        return 0 if report["validation_status"] != BLOCKED_STATUS else 2
    except (ReconciliationError, legacy.BridgeError, r5.LocalEdgeRuntimeError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
