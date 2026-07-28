#!/usr/bin/env python3
"""Reconcile Unit 01 multi-standard denominators and current learner lineage.

S00 is metadata-only. It reads existing canonical authorities, the frozen M1
private prerequisite graph, and the existing learner database. It never writes
canonical content, learner state, attempts, scores, mastery, or A2 state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_1_m01_unit01_cross_skill_vertical_slice as m01
from ulga.builders import build_a1fs_v1_cp02_per_unit_authority_bindings as cp02
from ulga.query.a1_a1plus_authority_scope_query import build_scope

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Reads existing authority metadata, the frozen M1 prerequisite graph, and "
    "existing Unit 01 response/attempt identities to calculate denominators and "
    "explicit lineage gaps. It creates no content, answer, scoring rule, learner "
    "state, mastery decision, audio, A2 unlock, external route, or parallel authority."
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PROGRAM_ID = "A1FS-ONLINE-V1.2-U01E"
TASK_ID = (
    "A1FS-ONLINE-V1.2-U01E-S00_"
    "MultiStandardDenominatorAndCurrentLineageReconciliation"
)
SCHEMA_VERSION = "a1fs.online.v1_2.u01e.s00.multistandard_denominator_lineage.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_2_U01E_S00_MULTISTANDARD_DENOMINATOR_AND_LINEAGE"
NEXT_SHORT_STEP = (
    "A1FS-ONLINE-V1.2-U01E-S01_"
    "Unit01FiveContextMaterialFirstAuthorityAdmission"
)

CAMBRIDGE_POLICY_PATH = (
    REPO_ROOT / "ulga/evidence/e4s_a1v1_m11a_cambridge_alignment_policy.json"
)
EXPECTED_AUTHORITY_COUNTS = {
    "evp_a1_sense_count": 784,
    "egp_a1_row_count": 109,
    "a1_generator_safe_chunk_count": 76,
    "a1_generator_safe_pattern_count": 27,
}
EXPECTED_KET_REQUIRED_MASTERY_NODE_COUNT = 553
EXPECTED_KET_A2_HANDOFF_LESSON_COUNT = 165
EXPECTED_UNIT01_ACTIVITY_COUNT = 11
EXPECTED_UNIT01_SKILL_COUNTS = {"READING": 4, "WRITING": 4, "SPEAKING": 3}


class S00ReconciliationError(ValueError):
    """Fail-closed S00 source, denominator, or lineage error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise S00ReconciliationError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise S00ReconciliationError(f"{code}_not_object")
    return value


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    if private:
        try:
            path.chmod(0o600)
        except OSError:
            pass


def normalized_lemma(value: str) -> str:
    return " ".join(re.findall(r"[a-z]+(?:'[a-z]+)?", str(value).casefold()))


def authority_denominators() -> tuple[dict[str, Any], dict[str, Any]]:
    scope = build_scope("A1")
    if scope.get("validation_status") != "PASS_AUTHORITY_SCOPE_QUERY_COMPLETE":
        raise S00ReconciliationError("authority_scope_status_invalid")
    authorities = scope.get("authorities")
    counts = scope.get("counts")
    if not isinstance(authorities, Mapping) or not isinstance(counts, Mapping):
        raise S00ReconciliationError("authority_scope_shape_invalid")
    vocabulary = authorities.get("vocabulary")
    if not isinstance(vocabulary, list):
        raise S00ReconciliationError("vocabulary_authority_missing")
    lemmas = {
        normalized_lemma(str(row.get("label") or ""))
        for row in vocabulary
        if isinstance(row, Mapping) and normalized_lemma(str(row.get("label") or ""))
    }
    result = {
        "evp_a1_sense_count": int(counts.get("vocabulary") or 0),
        "evp_a1_unique_lemma_count": len(lemmas),
        "egp_a1_row_count": int(counts.get("grammar") or 0),
        "a1_generator_safe_chunk_count": int(counts.get("chunk") or 0),
        "a1_generator_safe_pattern_count": int(counts.get("pattern") or 0),
        "current_question_type_inventory_count": int(counts.get("question_type") or 0),
        "authority_scope_task_id": scope.get("task_id"),
        "authority_scope_policy": scope.get("scope", {}).get("source_cefr_policy"),
    }
    for key, expected in EXPECTED_AUTHORITY_COUNTS.items():
        if result[key] != expected:
            raise S00ReconciliationError(f"authority_denominator_drift:{key}:{result[key]}:{expected}")
    return result, scope


def cambridge_denominators() -> tuple[dict[str, Any], dict[str, Any]]:
    policy = read_json(CAMBRIDGE_POLICY_PATH, "cambridge_alignment_policy")
    alignment = policy.get("unit_alignment")
    task_patterns = policy.get("task_compatibility")
    if not isinstance(alignment, list) or len(alignment) != 24:
        raise S00ReconciliationError("cambridge_unit_alignment_denominator_invalid")
    if not isinstance(task_patterns, Mapping) or not task_patterns:
        raise S00ReconciliationError("cambridge_assessment_pattern_denominator_invalid")
    stage_counts = Counter(str(row.get("cambridge_stage") or "") for row in alignment if isinstance(row, Mapping))
    unit01 = next(
        (row for row in alignment if isinstance(row, Mapping) and row.get("grammar_unit_id") == m01.UNIT_ID),
        None,
    )
    if not isinstance(unit01, Mapping) or unit01.get("cambridge_stage") != "STARTERS":
        raise S00ReconciliationError("unit01_cambridge_stage_not_starters")
    handoff = [
        row for row in alignment
        if isinstance(row, Mapping) and str(row.get("cambridge_stage") or "") == "FLYERS"
    ]
    current = [
        row for row in alignment
        if isinstance(row, Mapping) and str(row.get("cambridge_stage") or "") != "FLYERS"
    ]
    result = {
        "unit_alignment_count": len(alignment),
        "required_current_path_unit_alignment_count": len(current),
        "flyers_handoff_only_unit_alignment_count": len(handoff),
        "stage_counts": dict(sorted(stage_counts.items())),
        "assessment_pattern_count": len(task_patterns),
        "assessment_pattern_ids": sorted(str(key) for key in task_patterns),
        "unit01_cambridge_stage": str(unit01["cambridge_stage"]),
        "unit01_policy_decision": str(unit01.get("policy_decision") or ""),
        "granular_capability_denominator_status": "NOT_MATERIALIZED_IN_COMMITTED_POLICY",
        "denominator_role": "UNIT_LEVEL_STAGE_ALIGNMENT_AND_TASK_PATTERN_BASELINE",
    }
    return result, policy


def ket_denominators(m1_graph_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    graph = read_json(m1_graph_path, "m1_prerequisite_graph")
    counts = graph.get("counts")
    lock = graph.get("a2_lock_contract")
    nodes = graph.get("nodes")
    if not isinstance(counts, Mapping) or not isinstance(lock, Mapping) or not isinstance(nodes, list):
        raise S00ReconciliationError("m1_graph_shape_invalid")
    required_ids = lock.get("required_mastery_node_ids")
    if not isinstance(required_ids, list) or len(set(required_ids)) != len(required_ids):
        raise S00ReconciliationError("m1_required_mastery_identity_invalid")
    required_count = int(counts.get("required_mastery_node_count") or 0)
    if required_count != len(required_ids):
        raise S00ReconciliationError("m1_required_mastery_count_mismatch")
    if required_count != EXPECTED_KET_REQUIRED_MASTERY_NODE_COUNT:
        raise S00ReconciliationError(f"m1_required_mastery_denominator_drift:{required_count}")
    handoff_count = int(counts.get("a2_handoff_lesson_count") or 0)
    if handoff_count != EXPECTED_KET_A2_HANDOFF_LESSON_COUNT:
        raise S00ReconciliationError(f"m1_a2_handoff_denominator_drift:{handoff_count}")
    if int(counts.get("uncovered_required_node_count") or 0) != 0:
        raise S00ReconciliationError("m1_required_node_uncovered")
    if lock.get("state") != "LOCKED_BY_DESIGN" or lock.get("runtime_unlock_implemented") is not False:
        raise S00ReconciliationError("m1_a2_lock_boundary_invalid")
    by_id = {
        str(row.get("node_id") or ""): row
        for row in nodes
        if isinstance(row, Mapping) and row.get("node_id")
    }
    missing = sorted(set(str(row) for row in required_ids) - set(by_id))
    if missing:
        raise S00ReconciliationError(f"m1_required_nodes_missing:{missing[0]}")
    by_skill = Counter(str(by_id[str(node_id)].get("skill") or "UNKNOWN") for node_id in required_ids)
    result = {
        "required_a1_a1plus_mastery_node_count": required_count,
        "required_mastery_node_count_by_skill": dict(sorted(by_skill.items())),
        "a2_handoff_lesson_count": handoff_count,
        "uncovered_required_node_count": 0,
        "a2_lock_state": "LOCKED_BY_DESIGN",
        "flyers_and_a2_handoff_excluded_from_current_completion": True,
        "source_task_id": graph.get("task_id"),
        "source_validation_status": graph.get("validation_status"),
    }
    return result, graph


def table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }


def inspect_unit01_database(database_path: Path) -> dict[str, Any]:
    database_path = Path(database_path)
    if not database_path.is_file():
        raise S00ReconciliationError(f"learner_database_missing:{database_path}")
    lesson_ids = list(m01.LESSON_IDS.values())
    placeholders = ",".join("?" for _ in lesson_ids)
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        required_tables = {"response_contracts", "response_attempts", "scoring_results"}
        missing_tables = required_tables - table_names(connection)
        if missing_tables:
            raise S00ReconciliationError(f"learner_database_tables_missing:{sorted(missing_tables)[0]}")
        contracts = connection.execute(
            "SELECT asset_key,lesson_id,skill,role,capture_enabled,contract_json,contract_digest "
            f"FROM response_contracts WHERE lesson_id IN ({placeholders}) ORDER BY lesson_id,asset_key",
            tuple(lesson_ids),
        ).fetchall()
        attempts = connection.execute(
            "SELECT a.attempt_id,a.asset_key,a.lesson_id,a.submitted_at,s.outcome "
            "FROM response_attempts a LEFT JOIN scoring_results s ON s.attempt_id=a.attempt_id "
            f"WHERE a.lesson_id IN ({placeholders}) ORDER BY a.submitted_at,a.attempt_id",
            tuple(lesson_ids),
        ).fetchall()
    if len(contracts) != EXPECTED_UNIT01_ACTIVITY_COUNT:
        raise S00ReconciliationError(f"unit01_contract_denominator_invalid:{len(contracts)}")
    skill_counts = Counter(str(row["skill"]) for row in contracts)
    if dict(skill_counts) != EXPECTED_UNIT01_SKILL_COUNTS:
        raise S00ReconciliationError(f"unit01_skill_contract_denominator_invalid:{dict(skill_counts)}")
    attempts_by_asset: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    outcome_counts: Counter[str] = Counter()
    for row in attempts:
        outcome = str(row["outcome"] or "UNSCORED")
        outcome_counts[outcome] += 1
        attempts_by_asset[str(row["asset_key"])].append(
            {
                "attempt_id": str(row["attempt_id"]),
                "submitted_at": str(row["submitted_at"]),
                "outcome": outcome,
            }
        )
    distinct_attempted_asset_count = len(attempts_by_asset)
    assets = []
    for row in contracts:
        try:
            contract = json.loads(str(row["contract_json"]))
        except json.JSONDecodeError as exc:
            raise S00ReconciliationError(f"response_contract_json_invalid:{row['asset_key']}") from exc
        if not isinstance(contract, Mapping):
            raise S00ReconciliationError(f"response_contract_not_object:{row['asset_key']}")
        asset_key = str(row["asset_key"])
        attempt_evidence = attempts_by_asset.get(asset_key, [])
        assets.append(
            {
                "asset_key": asset_key,
                "lesson_id": str(row["lesson_id"]),
                "skill": str(row["skill"]),
                "role": str(row["role"]),
                "capture_enabled": bool(row["capture_enabled"]),
                "scoring_mode": str(contract.get("scoring_mode") or ""),
                "response_type": str(contract.get("response_type") or ""),
                "contract_digest": str(row["contract_digest"]),
                "attempt_count": len(attempt_evidence),
                "attempt_evidence": attempt_evidence,
                "asset_target_binding_status": "UNIT_LEVEL_ONLY_ASSET_TARGET_UNRESOLVED",
                "target_evp_sense_ids": [],
                "target_egp_row_ids": [],
                "target_chunk_ids": [],
                "target_sentence_ids": [],
                "target_pattern_ids": [],
                "target_ket_prerequisite_node_ids": [],
                "assessment_pattern_ref": None,
            }
        )
    return {
        "response_contract_count": len(assets),
        "response_contract_count_by_skill": dict(skill_counts),
        "attempt_count": len(attempts),
        "distinct_attempted_asset_count": distinct_attempted_asset_count,
        "outcome_counts": dict(sorted(outcome_counts.items())),
        "asset_target_binding_gap_count": sum(
            row["asset_target_binding_status"] != "RESOLVED_AUTHORITY_TARGET_BINDING"
            for row in assets
        ),
        "assets": assets,
    }


def current_unit_authority_context() -> dict[str, Any]:
    artifact = cp02.build_artifact()
    row = next(
        (
            item for item in artifact.get("learning_units", [])
            if isinstance(item, Mapping) and item.get("grammar_unit_id") == m01.UNIT_ID
        ),
        None,
    )
    if not isinstance(row, Mapping):
        raise S00ReconciliationError("unit01_cp02_binding_missing")
    bindings = row.get("authority_bindings")
    if not isinstance(bindings, Mapping):
        raise S00ReconciliationError("unit01_cp02_binding_shape_invalid")
    return {
        "grammar_unit_id": m01.UNIT_ID,
        "learning_unit_id": row.get("learning_unit_id"),
        "canonical_egp_row_ids": list(row.get("canonical_egp_row_ids", [])),
        "unit_level_authority_bindings": {
            name: {
                "selection_status": binding.get("selection_status"),
                "selected_refs": list(binding.get("selected_refs", [])),
                "reason": binding.get("reason"),
            }
            for name, binding in bindings.items()
            if isinstance(binding, Mapping)
        },
        "cambridge_stage": "STARTERS",
        "unit_level_bindings_are_not_asset_target_bindings": True,
    }


def build_artifact(*, m1_graph_path: Path, database_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    authorities, authority_scope = authority_denominators()
    cambridge, cambridge_policy = cambridge_denominators()
    ket, m1_graph = ket_denominators(m1_graph_path)
    database = inspect_unit01_database(database_path)
    unit_context = current_unit_authority_context()
    gaps = [
        {
            "gap_code": "UNIT01_ASSET_LEVEL_AUTHORITY_TARGET_INDEX_MISSING",
            "affected_asset_count": database["asset_target_binding_gap_count"],
            "resolution_task": NEXT_SHORT_STEP,
        },
        {
            "gap_code": "CAMBRIDGE_GRANULAR_CAPABILITY_DENOMINATOR_NOT_MATERIALIZED",
            "affected_unit_count": cambridge["required_current_path_unit_alignment_count"],
            "resolution_task": "FUTURE_SHARED_CAMBRIDGE_CAPABILITY_AUTHORITY_MILESTONE",
        },
    ]
    source_identity = {
        "authority_scope_task_id": authority_scope.get("task_id"),
        "cp02_task_id": cp02.TASK_ID,
        "unit01_content_task_id": m01.TASK_ID,
        "m1_graph_path": str(Path(m1_graph_path).resolve()),
        "m1_graph_sha256": file_digest(m1_graph_path),
        "learner_database_path": str(Path(database_path).resolve()),
        "learner_database_sha256": file_digest(database_path),
        "cambridge_policy_path": str(CAMBRIDGE_POLICY_PATH.relative_to(REPO_ROOT)),
        "cambridge_policy_sha256": file_digest(CAMBRIDGE_POLICY_PATH),
        "m1_graph_task_id": m1_graph.get("task_id"),
        "cambridge_policy_task_id": cambridge_policy.get("task_id"),
    }
    core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "unit_scope": m01.UNIT_ID,
        "level_scope": ["PRE_A1_PREREQUISITE", "A1", "A1_PLUS_INTERNAL"],
        "source_identity": source_identity,
        "denominators": {
            "authority": authorities,
            "ket_prerequisite": ket,
            "cambridge": cambridge,
        },
        "unit01_current_authority_context": unit_context,
        "unit01_current_runtime_lineage": database,
        "explicit_gaps": gaps,
        "claim_boundaries": {
            "metadata_only": True,
            "canonical_authority_written": False,
            "learner_database_written": False,
            "response_contract_changed": False,
            "response_attempt_changed": False,
            "mastery_inferred": False,
            "flyers_or_a2_in_required_completion": False,
            "unit02_modified": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    artifact = {**core, "artifact_sha256": digest(core)}
    safe_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "unit_scope": m01.UNIT_ID,
        "denominators": core["denominators"],
        "unit01_runtime_summary": {
            key: database[key]
            for key in (
                "response_contract_count",
                "response_contract_count_by_skill",
                "attempt_count",
                "distinct_attempted_asset_count",
                "outcome_counts",
                "asset_target_binding_gap_count",
            )
        },
        "explicit_gap_codes": [row["gap_code"] for row in gaps],
        "claim_boundaries": core["claim_boundaries"],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    return artifact, safe


def materialize(
    *, m1_graph_path: Path, database_path: Path, output_path: Path, report_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    artifact, safe = build_artifact(m1_graph_path=m1_graph_path, database_path=database_path)
    from ulga.validators import (
        validate_a1fs_online_v1_2_u01e_s00_multistandard_denominator_and_lineage as validator,
    )

    validation = validator.validate_artifact(artifact, safe)
    if validation["error_count"]:
        raise S00ReconciliationError("validation_failed:" + "|".join(validation["errors"]))
    write_json(output_path, artifact, private=True)
    write_json(report_path, safe)
    return artifact, safe


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m1-graph", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        _, safe = materialize(
            m1_graph_path=args.m1_graph,
            database_path=args.database,
            output_path=args.output,
            report_path=args.report,
        )
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (S00ReconciliationError, OSError, sqlite3.Error, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
