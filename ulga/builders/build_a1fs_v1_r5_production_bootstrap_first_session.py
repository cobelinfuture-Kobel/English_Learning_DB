#!/usr/bin/env python3
"""Bootstrap the production R3/R4 population into the existing R5 local runtime.

The command binds the M3 database to its exact M2 consumer, materializes and
independently validates R3/R4 production artifacts, initializes the existing R5
runtime, creates an anonymous learner profile when needed, selects one admitted
breadth cell deterministically, and creates a learner-safe first session.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_r3r4_authority_reviewed_production_population as population
from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5
from ulga.validators.validate_a1fs_v1_r3r4_authority_reviewed_production_population import validate as validate_population
from ulga.validators.validate_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector import validate_database
from ulga.validators.validate_a1fs_v1_learner_answerability_gate import validate_bank as validate_answerability_bank

TASK_ID = "A1FS-V1-R5_ProductionBootstrapAndFirstLearnerSession"
SCHEMA_VERSION = "a1fs.v1.r5.production_bootstrap.v1"
STATUS = "PASS_A1FS_V1_R5_PRODUCTION_BOOTSTRAP_FIRST_SESSION_READY"
NEXT_SHORT_STEP = "A1FS-V1-R5_RealLearnerSessionExecutionAndEvidenceExport"
PRIVATE_RECEIPT = "a1fs_v1_r5_production_bootstrap.private.json"
SAFE_REPORT = "a1fs_v1_r5_production_bootstrap.safe.json"
SESSION_PAYLOAD = "a1fs_v1_r5_first_session.private.json"
WINDOWS_LAUNCHER = "launch_a1fs_v1_r5_first_session.cmd"


class ProductionBootstrapError(ValueError):
    """Fail-closed production-bootstrap error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc(value: str | None = None) -> str:
    raw = value or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProductionBootstrapError("timestamp_invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ProductionBootstrapError("timestamp_timezone_required")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductionBootstrapError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise ProductionBootstrapError(f"{code}_not_object")
    return value


def write_private(path: Path, value: Mapping[str, Any]) -> None:
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
        raise ProductionBootstrapError(f"path_outside_local:{resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _database_metadata(database_path: Path) -> dict[str, str]:
    try:
        with sqlite3.connect(database_path) as connection:
            metadata = dict(connection.execute("SELECT key,value FROM metadata"))
    except sqlite3.Error as exc:
        raise ProductionBootstrapError(f"m3_database_unreadable:{exc}") from exc
    if metadata.get("validation_status") != m3.STATUS:
        raise ProductionBootstrapError("m3_database_status_invalid")
    if not metadata.get("consumer_sha256"):
        raise ProductionBootstrapError("m3_consumer_binding_missing")
    return metadata


def discover_consumer(*, database_path: Path, graph_path: Path, search_root: Path) -> Path:
    metadata = _database_metadata(database_path)
    expected_sha = metadata["consumer_sha256"]
    graph_sha = file_digest(graph_path)
    root = _local_root(search_root)
    matches: list[Path] = []
    for path in root.rglob("*.json"):
        try:
            if file_digest(path) != expected_sha:
                continue
            value = read_json(path, "consumer_candidate")
        except (OSError, ProductionBootstrapError):
            continue
        if (
            value.get("task_id") == m2.TASK_ID
            and value.get("schema_version") == m2.SCHEMA_VERSION
            and value.get("validation_status") == m2.STATUS
            and value.get("source_graph_sha256") == graph_sha
        ):
            matches.append(path.resolve())
    if not matches:
        raise ProductionBootstrapError(f"hash_bound_m2_consumer_not_found:{expected_sha}")
    matches.sort(key=lambda path: (len(path.parts), str(path).casefold()))
    return matches[0]


def _ensure_profile(*, database_path: Path, learner_id: str, display_label: str) -> bool:
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT profile_state FROM learner_profiles WHERE learner_id=?", (learner_id,)
        ).fetchone()
    if row:
        if row[0] != "ACTIVE":
            raise ProductionBootstrapError("learner_profile_not_active")
        return False
    store = m3.LearnerStateStore(database_path)
    store.create_profile(
        learner_id=learner_id,
        display_label=display_label,
        locale="zh-TW",
        timezone_name="Asia/Taipei",
    )
    return True


def _select_cell(*, supply: Mapping[str, Any], purpose: str, count: int, requested_cell_id: str | None) -> dict[str, Any]:
    if purpose not in r5.r4.PURPOSES:
        raise ProductionBootstrapError("purpose_invalid")
    if count < 1:
        raise ProductionBootstrapError("planned_item_count_invalid")
    eligible: list[dict[str, Any]] = []
    for raw in supply.get("cell_supply", []):
        if not isinstance(raw, Mapping):
            continue
        row = dict(raw)
        if row.get("supply_status") != r5.ASSIGNABLE_CELL_STATUS:
            continue
        if requested_cell_id and row.get("breadth_cell_id") != requested_cell_id:
            continue
        capacity = row.get("purpose_capacity", {}).get(purpose)
        if not isinstance(capacity, Mapping) or capacity.get("capacity_pass") is not True:
            continue
        if int(capacity.get("counts", {}).get("approved_items", 0)) < count:
            continue
        eligible.append(row)
    if not eligible:
        code = "requested_cell_not_assignable" if requested_cell_id else "no_assignable_cell_for_purpose"
        raise ProductionBootstrapError(f"{code}:{purpose}:{count}")
    eligible.sort(
        key=lambda row: (
            str(row.get("domain") or ""),
            str(row.get("capability_id") or ""),
            str(row.get("breadth_cell_id") or ""),
        )
    )
    return eligible[0]


def _safe_session_projection(session: Mapping[str, Any]) -> dict[str, Any]:
    assignments = session.get("assignments", [])
    skill_counts: dict[str, int] = {}
    for assignment in assignments:
        item = assignment.get("item", {})
        skill = str(item.get("skill") or "UNKNOWN")
        skill_counts[skill] = skill_counts.get(skill, 0) + 1
    return {
        "session_id_sha256": digest(session.get("session", {}).get("session_id", "")),
        "learner_ref_sha256": digest(session.get("session", {}).get("learner_id", "")),
        "breadth_cell_id": session.get("session", {}).get("breadth_cell_id"),
        "purpose": session.get("session", {}).get("purpose"),
        "session_state": session.get("session", {}).get("session_state"),
        "planned_item_count": session.get("session", {}).get("planned_item_count"),
        "assignment_count": len(assignments),
        "skill_counts": dict(sorted(skill_counts.items())),
    }


def bootstrap(
    *, database_path: Path, ontology_path: Path, graph_path: Path, output_root: Path,
    learner_id: str, display_label: str = "A1 Learner", purpose: str = "CORE_PRACTICE",
    planned_item_count: int = 1, consumer_path: Path | None = None,
    consumer_search_root: Path | None = None, cell_id: str | None = None,
    reviewed_at: str | None = None, port: int = r5.DEFAULT_PORT,
) -> dict[str, Any]:
    root = _local_root(output_root)
    database_path = Path(database_path).resolve()
    ontology_path = Path(ontology_path).resolve()
    graph_path = Path(graph_path).resolve()
    reviewed_at = utc(reviewed_at)
    if not database_path.is_file():
        raise ProductionBootstrapError("m3_database_missing")
    if not ontology_path.is_file() or not graph_path.is_file():
        raise ProductionBootstrapError("ontology_or_graph_missing")
    if consumer_path is None:
        consumer_path = discover_consumer(
            database_path=database_path,
            graph_path=graph_path,
            search_root=consumer_search_root or (REPO_ROOT / ".local"),
        )
    else:
        consumer_path = Path(consumer_path).resolve()
        metadata = _database_metadata(database_path)
        if file_digest(consumer_path) != metadata["consumer_sha256"]:
            raise ProductionBootstrapError("explicit_consumer_m3_binding_mismatch")

    population_root = root / "r3r4"
    population_report = population.materialize(
        ontology_path=ontology_path,
        graph_path=graph_path,
        consumer_path=consumer_path,
        output_root=population_root,
        reviewed_at=reviewed_at,
    )
    population_validation = validate_population(
        ontology_path=ontology_path,
        graph_path=graph_path,
        consumer_path=consumer_path,
        output_root=population_root,
    )
    if population_validation.get("error_count") != 0:
        raise ProductionBootstrapError(
            "population_validation_failed:" + "|".join(population_validation.get("errors", []))
        )
    if population_report.get("counts", {}).get("ready_for_local_selection_cell_count", 0) < 1:
        raise ProductionBootstrapError("production_population_has_no_ready_cell")

    bank_path = population_root / population.BANK_OUTPUT
    supply_path = population_root / population.SUPPLY_OUTPUT
    answerability_report = validate_answerability_bank(bank_path)
    write_private(root / "a1fs_v1_learner_answerability_gate.safe.json", answerability_report)
    if answerability_report.get("error_count") != 0:
        raise ProductionBootstrapError(
  "production_bank_answerability_failed:" + "|".join(answerability_report.get("errors", []))
        )
    supply = read_json(supply_path, "supply_report")
    selected_cell = _select_cell(
        supply=supply,
        purpose=purpose,
        count=planned_item_count,
        requested_cell_id=cell_id,
    )

    runtime = r5.LocalEdgeRuntime(database_path)
    init_result = runtime.initialize(bank_path=bank_path, supply_report_path=supply_path)
    database_validation = validate_database(database_path)
    if database_validation.get("error_count") != 0:
        raise ProductionBootstrapError(
            "r5_database_validation_failed:" + "|".join(database_validation.get("errors", []))
        )
    profile_created = _ensure_profile(
        database_path=database_path,
        learner_id=learner_id,
        display_label=display_label,
    )
    session = runtime.start_session(
        learner_id=learner_id,
        breadth_cell_id=str(selected_cell["breadth_cell_id"]),
        purpose=purpose,
        planned_item_count=planned_item_count,
        started_at=reviewed_at,
    )
    access_token = str(session.pop("access_token"))
    session_path = root / SESSION_PAYLOAD
    write_private(session_path, session)
    launcher_path = r5.write_windows_launcher(
        path=root / WINDOWS_LAUNCHER,
        database_path=database_path,
        session_id=str(session["session"]["session_id"]),
        access_token=access_token,
        port=port,
    )

    private_core = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": STATUS,
        "private_local_only": True,
        "created_at": reviewed_at,
        "learner_id": learner_id,
        "profile_created": profile_created,
        "session_id": session["session"]["session_id"],
        "access_token": access_token,
        "selected_cell": {
            "breadth_cell_id": selected_cell["breadth_cell_id"],
            "capability_id": selected_cell.get("capability_id"),
            "life_task_id": selected_cell.get("life_task_id"),
            "domain": selected_cell.get("domain"),
            "purpose": purpose,
            "planned_item_count": planned_item_count,
        },
        "source_bindings": {
            "ontology_sha256": file_digest(ontology_path),
            "graph_sha256": file_digest(graph_path),
            "consumer_sha256": file_digest(consumer_path),
            "population_report_sha256": population_report["report_sha256"],
            "practice_bank_sha256": read_json(bank_path, "bank")["bank_sha256"],
            "supply_report_sha256": supply["report_sha256"],
            "database_sha256_after_start": file_digest(database_path),
            "session_payload_sha256": file_digest(session_path),
            "launcher_sha256": file_digest(launcher_path),
        },
        "claim_boundaries": {
            "real_learner_evidence_claimed": False,
            "mastery_written": False,
            "retention_confirmed": False,
            "a2_unlocked": False,
            "public_delivery": False,
            "network_submission_enabled": False,
            "audio_or_recording_completed": False,
            "qwen_required": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    private_receipt = {**private_core, "receipt_sha256": digest(private_core)}
    write_private(root / PRIVATE_RECEIPT, private_receipt)

    safe_core = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": STATUS,
        "created_at": reviewed_at,
        "profile_created": profile_created,
        "session": _safe_session_projection(session),
        "population_counts": dict(population_report["counts"]),
        "runtime_init": {
            "item_count": init_result["item_count"],
            "assignable_cell_count": init_result["assignable_cell_count"],
        },
        "source_bindings": {
            "population_report_sha256": population_report["report_sha256"],
            "practice_bank_sha256": private_core["source_bindings"]["practice_bank_sha256"],
            "supply_report_sha256": supply["report_sha256"],
            "private_receipt_sha256": private_receipt["receipt_sha256"],
        },
        "claim_boundaries": private_core["claim_boundaries"],
        "stop_reason": "REAL_LEARNER_SESSION_EXECUTION_REQUIRED",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe_report = {**safe_core, "report_sha256": digest(safe_core)}
    write_private(root / SAFE_REPORT, safe_report)
    return safe_report


def safe_scan(value: Any) -> None:
    forbidden = {
        "learner_id", "session_id", "access_token", "prompt", "response", "answer",
        "answer_key", "accepted_texts", "accepted_sequence", "learner_contract",
        "private_scoring_contract", "operator_review", "options", "context",
    }
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in forbidden:
                raise ProductionBootstrapError(f"safe_private_field:{key}")
            safe_scan(child)
    elif isinstance(value, list):
        for child in value:
            safe_scan(child)
    elif isinstance(value, str):
        if Path(value).is_absolute() or (len(value) > 2 and value[1:3] in {":/", ":\\"}):
            raise ProductionBootstrapError("safe_absolute_path")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--ontology", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--learner-id", required=True)
    parser.add_argument("--display-label", default="A1 Learner")
    parser.add_argument("--purpose", default="CORE_PRACTICE")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--consumer", type=Path)
    parser.add_argument("--consumer-search-root", type=Path)
    parser.add_argument("--cell-id")
    parser.add_argument("--reviewed-at")
    parser.add_argument("--port", type=int, default=r5.DEFAULT_PORT)
    args = parser.parse_args()
    try:
        report = bootstrap(
            database_path=args.database,
            ontology_path=args.ontology,
            graph_path=args.graph,
            output_root=args.output_root,
            learner_id=args.learner_id,
            display_label=args.display_label,
            purpose=args.purpose,
            planned_item_count=args.count,
            consumer_path=args.consumer,
            consumer_search_root=args.consumer_search_root,
            cell_id=args.cell_id,
            reviewed_at=args.reviewed_at,
            port=args.port,
        )
        safe_scan(report)
        print(json.dumps({
            "validation_status": report["validation_status"],
            "profile_created": report["profile_created"],
            "planned_item_count": report["session"]["planned_item_count"],
            "stop_reason": report["stop_reason"],
            "next_short_step": report["next_short_step"],
        }, ensure_ascii=False, indent=2))
        return 0
    except (
        ProductionBootstrapError, population.ProductionPopulationError,
        r5.LocalEdgeRuntimeError, m3.StateStoreError, OSError, sqlite3.Error,
        KeyError, TypeError, ValueError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
