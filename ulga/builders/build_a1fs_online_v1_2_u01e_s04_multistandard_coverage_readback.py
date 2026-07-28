#!/usr/bin/env python3
"""Build Unit 01 multi-standard learner coverage readback and additive staging.

S04 joins the approved fixed 24-item Unit 01 target registry to existing M3/M6
learner evidence. A target is PRACTISED only when it is a formal item target and
there is a persisted learner attempt. The source learner database is read-only;
optional staging uses SQLite backup plus three additive tables and never alters
legacy table shapes. Stable/mastered/transfer claims remain unavailable until an
item-level M7/M8 bridge exists.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s00_multistandard_denominator_and_lineage as s00,
)
from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s02_question_generation_context_pack as s02,
)
from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s03_fixed_multitype_item_bank as s03,
)
from ulga.query.a1_a1plus_authority_scope_query import build_scope

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Reads an already-approved Unit 01 item bank and existing learner evidence to "
    "calculate coverage and stage an additive readback overlay. It creates no learner "
    "content, answer, scoring rule, learner attempt, mastery decision, audio, A2 unlock, "
    "external route, or parallel curriculum/state/scoring/mastery authority."
)

PROGRAM_ID = "A1FS-ONLINE-V1.2-U01E"
TASK_ID = (
    "A1FS-ONLINE-V1.2-U01E-S04_"
    "Unit01MultiStandardLearnerCoverageRuntimeReadback"
)
SCHEMA_VERSION = "a1fs.online.v1_2.u01e.s04.multistandard_coverage_readback.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_2_U01E_S04_MULTISTANDARD_COVERAGE_READBACK"
NEXT_SHORT_STEP = (
    "A1FS-ONLINE-V1.2-U01E-S05_"
    "Unit01V1_2ReleaseMigrationVisualAcceptanceAndRollback"
)
UNIT_ID = s03.s02.s01.m01.UNIT_ID
EXPECTED_EXISTING_COUNT = s02.EXISTING_ACTIVITY_COUNT
EXPECTED_NEW_COUNT = s02.NEW_CANDIDATE_TARGET_COUNT
EXPECTED_TOTAL_COUNT = s02.TARGET_TOTAL_ACTIVITY_COUNT
EXPECTED_ASSESSMENT_PATTERN_COUNT = 8
PASS_OUTCOMES = {"AUTO_PASS", "HUMAN_APPROVE"}
FAIL_OUTCOMES = {"AUTO_FAIL", "HUMAN_REJECT"}
UNRESOLVED_OUTCOMES = {"PENDING_HUMAN_REVIEW", "HUMAN_DEFER", "UNSCORED"}
TARGET_FIELD_BY_DOMAIN = {
    "evp_senses": "target_evp_sense_ids",
    "egp_rows": "target_egp_row_ids",
    "canonical_chunks": "target_chunk_ids",
    "context_phrases": "target_context_phrase_ids",
    "sentences": "target_sentence_ids",
    "patterns": "target_pattern_ids",
    "ket_prerequisites": "target_ket_prerequisite_node_ids",
}
ADDITIVE_TABLES = {
    "u01e_coverage_denominators",
    "u01e_asset_target_bindings",
    "u01e_learner_coverage_snapshots",
}
ADDITIVE_SQL = """
CREATE TABLE IF NOT EXISTS u01e_coverage_denominators(
  coverage_key TEXT PRIMARY KEY,
  denominator_count INTEGER NOT NULL CHECK(denominator_count >= 0),
  denominator_status TEXT NOT NULL,
  source_json TEXT NOT NULL,
  source_digest TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS u01e_asset_target_bindings(
  item_key TEXT PRIMARY KEY,
  unit_id TEXT NOT NULL,
  skill TEXT NOT NULL,
  question_type TEXT NOT NULL,
  runtime_status TEXT NOT NULL,
  target_json TEXT NOT NULL,
  binding_digest TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS u01e_learner_coverage_snapshots(
  snapshot_id TEXT PRIMARY KEY,
  learner_id TEXT NOT NULL,
  source_database_sha256 TEXT NOT NULL,
  snapshot_json TEXT NOT NULL,
  snapshot_digest TEXT NOT NULL UNIQUE
);
"""


class S04CoverageError(ValueError):
    """Fail-closed S04 registry, evidence, coverage, or staging error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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


def table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }


def legacy_schema(connection: sqlite3.Connection) -> list[dict[str, str]]:
    rows = connection.execute(
        "SELECT type,name,tbl_name,COALESCE(sql,'') AS sql "
        "FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
    ).fetchall()
    result = []
    for row in rows:
        name = str(row[1])
        if name in ADDITIVE_TABLES:
            continue
        result.append(
            {
                "type": str(row[0]),
                "name": name,
                "table": str(row[2]),
                "sql": str(row[3]),
            }
        )
    return result


def target_copy(row: Mapping[str, Any]) -> dict[str, list[str]]:
    return {
        field: sorted({str(value) for value in row.get(field, []) if value})
        for field in TARGET_FIELD_BY_DOMAIN.values()
    }


def build_registry(database_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    candidate, safe_pack = s03.build_candidate(database_path)
    approved = s03.admit_candidate(candidate, safe_pack)
    payload = approved.get("payload")
    if not isinstance(payload, Mapping):
        raise S04CoverageError("s03_approved_payload_missing")
    if payload.get("unit_id") != UNIT_ID:
        raise S04CoverageError("s03_unit_identity_invalid")
    if payload.get("new_candidate_item_count") != EXPECTED_NEW_COUNT:
        raise S04CoverageError("s03_new_item_denominator_invalid")

    registry: list[dict[str, Any]] = []
    for source in safe_pack.get("existing_asset_target_index", []):
        if not isinstance(source, Mapping):
            raise S04CoverageError("existing_target_index_row_invalid")
        registry.append(
            {
                "item_key": str(source["asset_key"]),
                "identity_kind": "EXISTING_RUNTIME_ASSET_KEY",
                "runtime_status": "RUNTIME_EXISTING",
                "unit_id": UNIT_ID,
                "lesson_id": str(source["lesson_id"]),
                "skill": str(source["skill"]),
                "question_type": str(source["question_type"]),
                "assessment_pattern_ref": str(source["assessment_pattern_ref"]),
                "context_id": str(source["context_id"]),
                "cambridge_stage": str(source["cambridge_stage"]),
                "learning_role": "EXISTING_APPROVED",
                "support_level": "EXISTING_APPROVED",
                "targets": target_copy(source),
                "semantic_signature": str(source["semantic_signature"]),
                "ket_binding_status": str(source["ket_binding_status"]),
            }
        )
    for source in payload.get("candidate_items", []):
        if not isinstance(source, Mapping):
            raise S04CoverageError("new_target_index_row_invalid")
        registry.append(
            {
                "item_key": str(source["candidate_item_id"]),
                "identity_kind": "APPROVED_CANDIDATE_ITEM_ID",
                "runtime_status": "APPROVED_PENDING_RUNTIME_MATERIALIZATION",
                "unit_id": UNIT_ID,
                "lesson_id": "PENDING_S05_RUNTIME_LESSON_BINDING",
                "skill": str(source["skill"]),
                "question_type": str(source["question_type"]),
                "assessment_pattern_ref": str(source["assessment_pattern_ref"]),
                "context_id": str(source["context_id"]),
                "cambridge_stage": str(source["cambridge_stage"]),
                "learning_role": str(source["learning_role"]),
                "support_level": str(source["support_level"]),
                "targets": target_copy(source),
                "semantic_signature": str(source["semantic_signature"]),
                "ket_binding_status": "UNRESOLVED_NO_EVIDENCE_BACKED_UNIT01_ACTIVITY_BRIDGE",
            }
        )
    registry.sort(key=lambda row: (row["runtime_status"], row["skill"], row["item_key"]))
    if len(registry) != EXPECTED_TOTAL_COUNT:
        raise S04CoverageError(f"registry_total_count_invalid:{len(registry)}")
    if len({row["item_key"] for row in registry}) != len(registry):
        raise S04CoverageError("registry_item_key_duplicate")
    if len({row["semantic_signature"] for row in registry}) != len(registry):
        raise S04CoverageError("registry_semantic_signature_duplicate")
    status_counts = Counter(row["runtime_status"] for row in registry)
    if status_counts != Counter(
        {
            "RUNTIME_EXISTING": EXPECTED_EXISTING_COUNT,
            "APPROVED_PENDING_RUNTIME_MATERIALIZATION": EXPECTED_NEW_COUNT,
        }
    ):
        raise S04CoverageError(f"registry_runtime_status_counts_invalid:{dict(status_counts)}")
    if any(row["targets"]["target_ket_prerequisite_node_ids"] for row in registry):
        raise S04CoverageError("ket_activity_binding_invented")
    return registry, safe_pack, approved


def authority_context() -> tuple[dict[str, Any], dict[str, str]]:
    denominators, scope = s00.authority_denominators()
    labels = {
        str(row["id"]): str(row.get("label") or "")
        for row in scope.get("authorities", {}).get("vocabulary", [])
        if isinstance(row, Mapping) and row.get("id")
    }
    return denominators, labels


def denominator_contract(m1_graph_path: Path, registry: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    authority, _ = authority_context()
    ket, _ = s00.ket_denominators(m1_graph_path)
    cambridge, _ = s00.cambridge_denominators()
    selected = selected_target_sets(registry)
    return {
        "evp_senses": {
            "count": int(authority["evp_a1_sense_count"]),
            "status": "OFFICIAL_A1_AUTHORITY_DENOMINATOR",
        },
        "evp_unique_lemmas": {
            "count": int(authority["evp_a1_unique_lemma_count"]),
            "status": "DERIVED_A1_UNIQUE_LEMMA_DENOMINATOR",
        },
        "egp_rows": {
            "count": int(authority["egp_a1_row_count"]),
            "status": "CANONICAL_A1_EGP_DENOMINATOR",
        },
        "canonical_chunks": {
            "count": int(authority["a1_generator_safe_chunk_count"]),
            "status": "A1_GENERATOR_SAFE_CANONICAL_DENOMINATOR",
        },
        "context_phrases": {
            "count": len(selected["context_phrases"]),
            "status": "UNIT01_SELECTED_NONCANONICAL_PHRASE_DENOMINATOR",
        },
        "sentences": {
            "count": len(selected["sentences"]),
            "status": "UNIT01_SELECTED_SENTENCE_DENOMINATOR",
        },
        "patterns": {
            "count": int(authority["a1_generator_safe_pattern_count"]),
            "status": "A1_GENERATOR_SAFE_PATTERN_DENOMINATOR",
        },
        "ket_prerequisites": {
            "count": int(ket["required_a1_a1plus_mastery_node_count"]),
            "status": "A1_A1PLUS_REQUIRED_MASTERY_NODE_DENOMINATOR",
        },
        "assessment_patterns": {
            "count": int(cambridge["assessment_pattern_count"]),
            "status": "COMMITTED_CAMBRIDGE_COMPATIBLE_TASK_PATTERN_DENOMINATOR",
        },
        "cambridge_capabilities": {
            "count": 0,
            "status": "NOT_AVAILABLE_GRANULAR_CAPABILITY_DENOMINATOR",
        },
        "flyers_a2_handoff": {
            "count": int(cambridge["flyers_handoff_only_unit_alignment_count"]),
            "status": "HANDOFF_ONLY_EXCLUDED_FROM_CURRENT_COMPLETION",
        },
    }


def selected_target_sets(registry: Sequence[Mapping[str, Any]]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {domain: set() for domain in TARGET_FIELD_BY_DOMAIN}
    for row in registry:
        targets = row.get("targets", {})
        for domain, field in TARGET_FIELD_BY_DOMAIN.items():
            result[domain].update(str(value) for value in targets.get(field, []) if value)
    return result


def item_target_sets(rows: Iterable[Mapping[str, Any]]) -> dict[str, set[str]]:
    return selected_target_sets(list(rows))


def parse_exposure_assets(connection: sqlite3.Connection, learner_id: str) -> tuple[set[str], str]:
    if "state_events" not in table_names(connection):
        return set(), "NOT_AVAILABLE_NO_STATE_EVENTS_TABLE"
    rows = connection.execute(
        "SELECT payload_json FROM state_events "
        "WHERE learner_id=? AND event_type='ASSET_EXPOSED' ORDER BY event_seq",
        (learner_id,),
    ).fetchall()
    assets: set[str] = set()
    for row in rows:
        try:
            payload = json.loads(str(row[0]))
        except json.JSONDecodeError as exc:
            raise S04CoverageError("state_event_payload_invalid") from exc
        if isinstance(payload, Mapping) and payload.get("asset_key"):
            assets.add(str(payload["asset_key"]))
    return assets, "AVAILABLE_FROM_M3_STATE_EVENTS"


def learner_evidence(
    database_path: Path,
    learner_id: str,
    registry: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    learner_id = str(learner_id or "").strip()
    if not learner_id:
        raise S04CoverageError("learner_id_required")
    by_key = {str(row["item_key"]): row for row in registry}
    existing_keys = {
        key for key, row in by_key.items() if row["runtime_status"] == "RUNTIME_EXISTING"
    }
    placeholders = ",".join("?" for _ in existing_keys)
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        names = table_names(connection)
        required = {"response_attempts", "scoring_results"}
        missing = required - names
        if missing:
            raise S04CoverageError(f"learner_database_tables_missing:{sorted(missing)[0]}")
        exposed_assets, exposure_status = parse_exposure_assets(connection, learner_id)
        attempts = connection.execute(
            "SELECT a.asset_key,a.submitted_at,s.outcome "
            "FROM response_attempts a "
            "LEFT JOIN scoring_results s ON s.attempt_id=a.attempt_id "
            f"WHERE a.learner_id=? AND a.asset_key IN ({placeholders}) "
            "ORDER BY a.submitted_at,a.attempt_id",
            (learner_id, *sorted(existing_keys)),
        ).fetchall()
    unknown_exposures = sorted(exposed_assets - existing_keys)
    if unknown_exposures:
        exposed_assets &= existing_keys
    attempt_rows: list[dict[str, Any]] = []
    for attempt in attempts:
        key = str(attempt["asset_key"])
        item = by_key.get(key)
        if not isinstance(item, Mapping):
            raise S04CoverageError(f"attempt_item_not_in_registry:{key}")
        attempt_rows.append(
            {
                "item": item,
                "outcome": str(attempt["outcome"] or "UNSCORED"),
                "submitted_at": str(attempt["submitted_at"]),
            }
        )
    exposed_rows = [by_key[key] for key in sorted(exposed_assets) if key in by_key]
    practised_by_key = {str(row["item"]["item_key"]): row["item"] for row in attempt_rows}
    practised_rows = list(practised_by_key.values())
    assessed_rows = [row["item"] for row in attempt_rows if row["outcome"] != "UNSCORED"]
    passed_rows = [row["item"] for row in attempt_rows if row["outcome"] in PASS_OUTCOMES]
    failed_rows = [row["item"] for row in attempt_rows if row["outcome"] in FAIL_OUTCOMES]
    unresolved_rows = [row["item"] for row in attempt_rows if row["outcome"] in UNRESOLVED_OUTCOMES]
    return {
        "attempt_count": len(attempt_rows),
        "distinct_attempted_item_count": len(practised_by_key),
        "outcome_counts": dict(sorted(Counter(row["outcome"] for row in attempt_rows).items())),
        "exposure_status": exposure_status,
        "distinct_exposed_item_count": len(exposed_rows),
        "unknown_exposure_item_count_excluded": len(unknown_exposures),
        "target_sets": {
            "exposed": item_target_sets(exposed_rows),
            "practised": item_target_sets(practised_rows),
            "assessed": item_target_sets(assessed_rows),
            "passed": item_target_sets(passed_rows),
            "weak": item_target_sets(failed_rows),
            "unresolved": item_target_sets(unresolved_rows),
        },
        "assessment_pattern_sets": {
            "exposed": {str(row["assessment_pattern_ref"]) for row in exposed_rows},
            "practised": {str(row["assessment_pattern_ref"]) for row in practised_rows},
            "assessed": {str(row["assessment_pattern_ref"]) for row in assessed_rows},
            "passed": {str(row["assessment_pattern_ref"]) for row in passed_rows},
            "weak": {str(row["assessment_pattern_ref"]) for row in failed_rows},
        },
        "cambridge_stage_sets": {
            "exposed": {str(row["cambridge_stage"]) for row in exposed_rows},
            "practised": {str(row["cambridge_stage"]) for row in practised_rows},
            "assessed": {str(row["cambridge_stage"]) for row in assessed_rows},
        },
    }


def percentage(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(100.0 * numerator / denominator, 4)


def lemma_ids(target_ids: set[str], label_by_id: Mapping[str, str]) -> set[str]:
    return {
        normalized_lemma(label_by_id[target_id])
        for target_id in target_ids
        if target_id in label_by_id and normalized_lemma(label_by_id[target_id])
    }


def coverage_domain_row(
    *,
    selected: set[str],
    evidence: Mapping[str, set[str]],
    denominator: Mapping[str, Any],
) -> dict[str, Any]:
    denominator_count = int(denominator["count"])
    row = {
        "denominator_count": denominator_count,
        "denominator_status": str(denominator["status"]),
        "selected_count": len(selected),
        "exposed_count": len(evidence.get("exposed", set())),
        "practised_count": len(evidence.get("practised", set())),
        "assessed_count": len(evidence.get("assessed", set())),
        "passed_count": len(evidence.get("passed", set())),
        "weak_count": len(evidence.get("weak", set())),
        "unresolved_count": len(evidence.get("unresolved", set())),
        "selected_percentage": percentage(len(selected), denominator_count),
        "exposed_percentage": percentage(len(evidence.get("exposed", set())), denominator_count),
        "practised_percentage": percentage(len(evidence.get("practised", set())), denominator_count),
        "assessed_percentage": percentage(len(evidence.get("assessed", set())), denominator_count),
        "stable_count": None,
        "mastered_count": None,
        "transfer_proven_count": None,
        "stable_status": "NOT_AVAILABLE_FROM_CURRENT_ITEM_LEVEL_EVIDENCE",
        "mastery_status": "NOT_AVAILABLE_FROM_CURRENT_ITEM_LEVEL_EVIDENCE",
        "transfer_status": "NOT_AVAILABLE_FROM_CURRENT_ITEM_LEVEL_EVIDENCE",
    }
    return row


def build_readback(
    *,
    database_path: Path,
    learner_id: str,
    m1_graph_path: Path,
    registry: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    denominators = denominator_contract(m1_graph_path, registry)
    selected = selected_target_sets(registry)
    evidence = learner_evidence(database_path, learner_id, registry)
    target_sets = evidence["target_sets"]
    _, vocabulary_labels = authority_context()
    by_domain: dict[str, Any] = {}
    for domain in TARGET_FIELD_BY_DOMAIN:
        domain_evidence = {
            state: set(values.get(domain, set()))
            for state, values in target_sets.items()
        }
        by_domain[domain] = coverage_domain_row(
            selected=selected[domain],
            evidence=domain_evidence,
            denominator=denominators[domain],
        )
    selected_lemmas = lemma_ids(selected["evp_senses"], vocabulary_labels)
    lemma_evidence = {
        state: lemma_ids(set(values.get("evp_senses", set())), vocabulary_labels)
        for state, values in target_sets.items()
    }
    by_domain["evp_unique_lemmas"] = coverage_domain_row(
        selected=selected_lemmas,
        evidence=lemma_evidence,
        denominator=denominators["evp_unique_lemmas"],
    )
    selected_patterns = {str(row["assessment_pattern_ref"]) for row in registry}
    assessment_evidence = {
        state: set(values)
        for state, values in evidence["assessment_pattern_sets"].items()
    }
    by_domain["assessment_patterns"] = coverage_domain_row(
        selected=selected_patterns,
        evidence=assessment_evidence,
        denominator=denominators["assessment_patterns"],
    )
    by_domain["cambridge_capabilities"] = {
        "denominator_count": 0,
        "denominator_status": denominators["cambridge_capabilities"]["status"],
        "selected_count": None,
        "exposed_count": None,
        "practised_count": None,
        "assessed_count": None,
        "readiness_percentage": None,
        "status": "NOT_AVAILABLE_DO_NOT_DERIVE_CAPABILITY_PERCENTAGE_FROM_UNIT_STAGE_LABELS",
    }
    readback = {
        "unit_id": UNIT_ID,
        "curriculum_item_count": len(registry),
        "existing_runtime_item_count": sum(row["runtime_status"] == "RUNTIME_EXISTING" for row in registry),
        "approved_pending_runtime_item_count": sum(
            row["runtime_status"] == "APPROVED_PENDING_RUNTIME_MATERIALIZATION"
            for row in registry
        ),
        "question_type_count": len(selected_patterns),
        "cambridge_stage": "STARTERS",
        "learner_evidence_summary": {
            key: evidence[key]
            for key in (
                "attempt_count",
                "distinct_attempted_item_count",
                "outcome_counts",
                "exposure_status",
                "distinct_exposed_item_count",
                "unknown_exposure_item_count_excluded",
            )
        },
        "coverage_by_domain": by_domain,
        "ket_prerequisite_readback": {
            **by_domain["ket_prerequisites"],
            "activity_bridge_status": "UNRESOLVED_NO_EVIDENCE_BACKED_UNIT01_ACTIVITY_BRIDGE",
            "coverage_claim_allowed": False,
        },
        "cambridge_readback": {
            "stage": "STARTERS",
            "selected_item_count": len(registry),
            "exposed_item_count": evidence["distinct_exposed_item_count"],
            "practised_item_count": evidence["distinct_attempted_item_count"],
            "granular_capability_status": by_domain["cambridge_capabilities"]["status"],
            "flyers_a2_handoff_excluded": True,
        },
        "assessment_pattern_readback": by_domain["assessment_patterns"],
        "mastery_bridge_status": "NOT_AVAILABLE_NO_ITEM_TARGET_TO_M7_M8_NODE_BRIDGE",
    }
    return readback, denominators


def safe_readback(private_readback: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "unit_id": private_readback["unit_id"],
        "curriculum_item_count": private_readback["curriculum_item_count"],
        "existing_runtime_item_count": private_readback["existing_runtime_item_count"],
        "approved_pending_runtime_item_count": private_readback[
            "approved_pending_runtime_item_count"
        ],
        "question_type_count": private_readback["question_type_count"],
        "cambridge_stage": private_readback["cambridge_stage"],
        "learner_evidence_summary": private_readback["learner_evidence_summary"],
        "coverage_by_domain": private_readback["coverage_by_domain"],
        "ket_prerequisite_readback": private_readback["ket_prerequisite_readback"],
        "cambridge_readback": private_readback["cambridge_readback"],
        "assessment_pattern_readback": private_readback[
            "assessment_pattern_readback"
        ],
        "mastery_bridge_status": private_readback["mastery_bridge_status"],
    }


def source_database_identity(path: Path) -> dict[str, Any]:
    with sqlite3.connect(path) as connection:
        schema = legacy_schema(connection)
    return {
        "sha256": file_digest(path),
        "legacy_schema_sha256": digest(schema),
        "legacy_schema_object_count": len(schema),
    }


def stage_additive_database(
    *,
    source_database_path: Path,
    staged_database_path: Path,
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    source_database_path = Path(source_database_path)
    staged_database_path = Path(staged_database_path)
    before = source_database_identity(source_database_path)
    staged_database_path.parent.mkdir(parents=True, exist_ok=True)
    if staged_database_path.exists():
        staged_database_path.unlink()
    with sqlite3.connect(source_database_path) as source, sqlite3.connect(staged_database_path) as target:
        source.backup(target)
    with sqlite3.connect(staged_database_path) as connection:
        legacy_before = legacy_schema(connection)
        connection.executescript(ADDITIVE_SQL)
        denominators = artifact["denominators"]
        for key, value in sorted(denominators.items()):
            source_json = canonical(value)
            connection.execute(
                "INSERT OR REPLACE INTO u01e_coverage_denominators VALUES(?,?,?,?,?)",
                (key, int(value["count"]), str(value["status"]), source_json, digest(value)),
            )
        for row in artifact["target_registry"]:
            binding = {
                "identity_kind": row["identity_kind"],
                "lesson_id": row["lesson_id"],
                "context_id": row["context_id"],
                "assessment_pattern_ref": row["assessment_pattern_ref"],
                "cambridge_stage": row["cambridge_stage"],
                "learning_role": row["learning_role"],
                "support_level": row["support_level"],
                "targets": row["targets"],
                "semantic_signature": row["semantic_signature"],
                "ket_binding_status": row["ket_binding_status"],
            }
            connection.execute(
                "INSERT OR REPLACE INTO u01e_asset_target_bindings VALUES(?,?,?,?,?,?,?)",
                (
                    row["item_key"],
                    row["unit_id"],
                    row["skill"],
                    row["question_type"],
                    row["runtime_status"],
                    canonical(binding),
                    digest(binding),
                ),
            )
        learner_id = str(artifact["learner_id"])
        snapshot = artifact["coverage_readback"]
        snapshot_digest = digest(snapshot)
        snapshot_id = f"U01E-S04:{digest({'learner_id': learner_id, 'snapshot': snapshot})[:24]}"
        connection.execute(
            "INSERT OR REPLACE INTO u01e_learner_coverage_snapshots VALUES(?,?,?,?,?)",
            (
                snapshot_id,
                learner_id,
                before["sha256"],
                canonical(snapshot),
                snapshot_digest,
            ),
        )
        connection.commit()
        legacy_after = legacy_schema(connection)
        table_counts = {
            name: int(connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0])
            for name in sorted(ADDITIVE_TABLES)
        }
        names = table_names(connection)
    after = source_database_identity(source_database_path)
    if before != after:
        raise S04CoverageError("source_database_mutated")
    if legacy_before != legacy_after:
        raise S04CoverageError("legacy_database_schema_changed")
    if not ADDITIVE_TABLES.issubset(names):
        raise S04CoverageError("additive_tables_missing")
    try:
        os.chmod(staged_database_path, 0o600)
    except OSError:
        pass
    return {
        "source_database_preserved": True,
        "source_database_sha256": before["sha256"],
        "legacy_schema_sha256": before["legacy_schema_sha256"],
        "legacy_schema_unchanged": True,
        "additive_tables": sorted(ADDITIVE_TABLES),
        "additive_table_row_counts": table_counts,
        "snapshot_id": snapshot_id,
        "staged_database_sha256": file_digest(staged_database_path),
        "v1_1_backward_compatible_schema": True,
    }


def build_artifact(
    *,
    database_path: Path,
    learner_id: str,
    m1_graph_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_before = source_database_identity(database_path)
    registry, safe_pack, approved = build_registry(database_path)
    readback, denominators = build_readback(
        database_path=database_path,
        learner_id=learner_id,
        m1_graph_path=m1_graph_path,
        registry=registry,
    )
    source_after = source_database_identity(database_path)
    if source_before != source_after:
        raise S04CoverageError("source_database_changed_during_readback")
    core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "learner_id": str(learner_id),
        "source_identity": {
            "s03_task_id": s03.TASK_ID,
            "s03_approved_sha256": approved["artifact_sha256"],
            "s02_safe_pack_sha256": safe_pack["pack_sha256"],
            "learner_database_sha256": source_before["sha256"],
            "m1_graph_sha256": file_digest(m1_graph_path),
        },
        "denominators": denominators,
        "target_registry": registry,
        "coverage_readback": readback,
        "compatibility_contract": {
            "source_database_read_only": True,
            "legacy_schema_sha256": source_before["legacy_schema_sha256"],
            "legacy_schema_object_count": source_before["legacy_schema_object_count"],
            "allowed_migration_mode": "ADDITIVE_TABLES_ONLY",
            "existing_table_shape_change_allowed": False,
            "existing_response_contract_change_allowed": False,
            "existing_attempt_change_allowed": False,
            "v1_1_rollback_runtime_acceptance_required_in_s05": True,
        },
        "claim_boundaries": {
            "learner_response_included": False,
            "attempt_id_included": False,
            "hidden_answer_included": False,
            "source_database_written": False,
            "runtime_item_bank_installed": False,
            "new_item_attempts_fabricated": False,
            "stable_or_mastery_inferred": False,
            "ket_coverage_claimed": False,
            "cambridge_granular_capability_claimed": False,
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
        "unit_id": UNIT_ID,
        "coverage_readback": safe_readback(readback),
        "compatibility_contract": core["compatibility_contract"],
        "claim_boundaries": core["claim_boundaries"],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    return artifact, safe


def materialize(
    *,
    database_path: Path,
    learner_id: str,
    m1_graph_path: Path,
    staged_database_path: Path,
    artifact_path: Path,
    report_path: Path,
    validation_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    artifact, safe = build_artifact(
        database_path=database_path,
        learner_id=learner_id,
        m1_graph_path=m1_graph_path,
    )
    staging = stage_additive_database(
        source_database_path=database_path,
        staged_database_path=staged_database_path,
        artifact=artifact,
    )
    artifact = {
        **{key: value for key, value in artifact.items() if key != "artifact_sha256"},
        "staging_readback": staging,
    }
    artifact["artifact_sha256"] = digest(
        {key: value for key, value in artifact.items() if key != "artifact_sha256"}
    )
    safe_core = {key: value for key, value in safe.items() if key != "report_sha256"}
    safe_core["staging_readback"] = {
        key: staging[key]
        for key in (
            "source_database_preserved",
            "legacy_schema_unchanged",
            "additive_tables",
            "additive_table_row_counts",
            "v1_1_backward_compatible_schema",
        )
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    from ulga.validators import (
        validate_a1fs_online_v1_2_u01e_s04_multistandard_coverage_readback as validator,
    )

    validation = validator.validate_artifact(artifact, safe)
    if validation["error_count"]:
        raise S04CoverageError("validation_failed:" + "|".join(validation["errors"]))
    write_json(artifact_path, artifact, private=True)
    write_json(report_path, safe)
    write_json(validation_path, validation)
    return artifact, safe, validation


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--learner-id", required=True)
    parser.add_argument("--m1-graph", type=Path, required=True)
    parser.add_argument("--staged-database", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        _, _, validation = materialize(
            database_path=args.database,
            learner_id=args.learner_id,
            m1_graph_path=args.m1_graph,
            staged_database_path=args.staged_database,
            artifact_path=args.artifact,
            report_path=args.report,
            validation_path=args.validation,
        )
        print(json.dumps(validation, ensure_ascii=False, indent=2))
        return 0
    except (
        S04CoverageError,
        s03.S03ItemBankError,
        s02.S02ContextPackError,
        sqlite3.Error,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
