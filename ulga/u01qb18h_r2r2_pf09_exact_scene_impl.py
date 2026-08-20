#!/usr/bin/env python3
"""Extend R2R2 with blueprint-authoritative exact-scene PF09 materialization.

The existing R2R2 implementation reconciles scored Writing production families
PF13/PF14/PF15 from the admitted 3805-sentence capability pool.  Fresh private
R4 evidence at exact head 8aab8f62 showed a separate residual: legacy PF09
CONTEXTUAL_REFERENCE_GAP items can retain their old canonical-context wording
while being selected for a different canonical micro-scene.  This module keeps
one R2R2 authority and adds only that missing demand class.

PF09 demand is derived from the installed U01QB13 240-row blueprint.  Each
required slot receives an exact-scene item whose antecedent is an admitted
first-mention sentence from that scene.  The assessment wrapper asks for the
second mention of the same sentence-pool entity without synthesizing a new
location/event sentence.  The disposable runtime retires the same number of
legacy base PF09 rows and registers the exact-scene replacements, preserving
PF09 inventory, 288 base + 186 Real62 = 474, and the frozen source database.
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ulga import u01qb18h_r2r2_blueprint_dynamic_impl as base

PF09_FAMILY = "U01-PF09-TRANSFER-KNOWN-REFERENCE"
PF09_TASK_ANGLE = "CONTEXTUAL_REFERENCE_GAP"
HISTORICAL_CONTEXTUAL_REFERENCE_BASE_CAPACITY = 35

# Re-export canonical identity/constants through this single implementation.
A1FS_CONTENT_POLICY_MODE = base.A1FS_CONTENT_POLICY_MODE
PROGRAM_ID = base.PROGRAM_ID
TASK_ID = base.TASK_ID
SCHEMA_VERSION = base.SCHEMA_VERSION
PASS_STATUS = base.PASS_STATUS
DECISION_REF = base.DECISION_REF
NEXT_SHORT_STEP = base.NEXT_SHORT_STEP
SOURCE_TASK_ID = base.SOURCE_TASK_ID
SOURCE_STATUS = base.SOURCE_STATUS
EXPECTED_SENTENCE_POOL_TOTAL = base.EXPECTED_SENTENCE_POOL_TOTAL
EXPECTED_BLUEPRINT_ACTIVITY_COUNT = base.EXPECTED_BLUEPRINT_ACTIVITY_COUNT
EXPECTED_PRODUCTION_REQUIREMENT_COUNT = base.EXPECTED_PRODUCTION_REQUIREMENT_COUNT
EXPECTED_BASE_COUNT = base.EXPECTED_BASE_COUNT
EXPECTED_EXTENSION_COUNT = base.EXPECTED_EXTENSION_COUNT
EXPECTED_RUNTIME_COUNT = base.EXPECTED_RUNTIME_COUNT
PRODUCTION_ANGLE_TO_FAMILY = base.PRODUCTION_ANGLE_TO_FAMILY
EXPECTED_PRODUCTION_FAMILY_COUNTS = base.EXPECTED_PRODUCTION_FAMILY_COUNTS
HISTORICAL_PRODUCTION_INVENTORY_COUNT = base.HISTORICAL_PRODUCTION_INVENTORY_COUNT
HISTORICAL_PRODUCTION_FAMILY_COUNTS = base.HISTORICAL_PRODUCTION_FAMILY_COUNTS
METADATA_TABLE = base.METADATA_TABLE

u11 = base.u11
scene_authority = base.scene_authority
s01 = base.s01
policy_artifact = base.policy_artifact
qb02 = base.qb02
u10 = base.u10
u13 = base.u13
SentencePoolCapacityError = base.SentencePoolCapacityError

# Compatibility exports used by the canonical validator/tests.
_normalized_family_counts = base._normalized_family_counts
_validate_requirement_capacity = base._validate_requirement_capacity
count_preservation = base.count_preservation
production_requirements = base.production_requirements
canonical = base.canonical
digest = base.digest
file_digest = base.file_digest
write_json = base.write_json
read_json = base.read_json
load_sentence_pool = base.load_sentence_pool
blueprint_rows = base.blueprint_rows


def contextual_reference_requirements(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Derive exact current PF09 demand from the persisted 240-row blueprint."""
    result: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("skill") or "") != "WRITING":
            continue
        if str(row.get("task_angle") or "") != PF09_TASK_ANGLE:
            continue
        allowed = {
            str(value)
            for value in json.loads(str(row.get("pattern_family_ids_json") or "[]"))
            if str(value)
        }
        if PF09_FAMILY not in allowed:
            raise SentencePoolCapacityError(
                "BLUEPRINT_CONTEXTUAL_REFERENCE_FAMILY_NOT_ALLOWED:"
                f"{row.get('activity_id')}:{sorted(allowed)}"
            )
        result.append(
            {
                "activity_id": str(row["activity_id"]),
                "form_id": str(row["form_id"]),
                "form_ordinal": int(row["form_ordinal"]),
                "scene_ref_id": str(row["scene_ref_id"]),
                "situation_family": str(row["situation_family"]),
                "setting": str(row["setting"]),
                "support_level": str(row["support_level"]),
                "assessment_candidate": bool(row["assessment_candidate"]),
                "task_angle": PF09_TASK_ANGLE,
                "pattern_family_id": PF09_FAMILY,
            }
        )
    if not result:
        raise SentencePoolCapacityError("BLUEPRINT_CONTEXTUAL_REFERENCE_REQUIREMENTS_EMPTY")
    if len(result) > HISTORICAL_CONTEXTUAL_REFERENCE_BASE_CAPACITY:
        raise SentencePoolCapacityError(
            "BLUEPRINT_CONTEXTUAL_REFERENCE_CAPACITY_EXCEEDED:"
            f"{len(result)}:{HISTORICAL_CONTEXTUAL_REFERENCE_BASE_CAPACITY}"
        )
    return result


def _contextual_reference_item(
    requirement: Mapping[str, Any],
    first_profile: Mapping[str, Any],
    first_slot: Mapping[str, Any],
    *,
    source_pool_sha256: str,
    scene_pattern_refs: Sequence[str],
) -> dict[str, Any]:
    """Create one PF09 item without importing wording from another scene.

    The admitted first-mention sentence is the antecedent evidence.  The second
    mention is represented as a noun-phrase assessment wrapper, not as a newly
    authored location/event sentence.  This keeps the task self-contained while
    avoiding the legacy `classroom/park` context leakage exposed by R4.
    """
    source_sentence_id = str(first_profile.get("sentence_id") or "")
    first_text = str(first_profile.get("text") or "").strip()
    noun = str(first_slot.get("_noun") or "").strip().casefold()
    entity_id = str(first_slot.get("_entity_id") or "").strip()
    if not source_sentence_id or not first_text or not noun or not entity_id:
        raise SentencePoolCapacityError(
            f"PF09_SENTENCE_ENTITY_EVIDENCE_MISSING:{requirement.get('activity_id')}"
        )

    common = base._common_item(
        requirement,
        first_slot,
        [source_sentence_id],
        source_pool_sha256,
        scene_pattern_refs,
    )
    common.update(
        {
            "item_id": (
                "U01QB18H-R2R2-PF09-"
                + u10.seed.slug(str(requirement["activity_id"]))
            ),
            "pattern_family_id": PF09_FAMILY,
            "question_type": "contextual_gap",
            "task_angle": PF09_TASK_ANGLE,
            "prompt": "Complete the second mention of the same item.",
            "stimulus": (
                f"First mention: {first_text} | "
                f"Second mention: ___ {noun}"
            ),
            "options": [],
            "correct_answer": "the",
            "accepted_answers": ["the"],
            "scoring_mode": "NORMALIZED_TEXT",
            "support_level": str(requirement["support_level"]),
            "human_review_required": False,
            "transfer_eligible": str(requirement["support_level"]) == "TRANSFER",
            "response_contract": base._response_contract(
                mode="NORMALIZED_TEXT", model_answer="the"
            ),
            "contextual_reference_scene_ref_id": str(requirement["scene_ref_id"]),
            "contextual_reference_activity_id": str(requirement["activity_id"]),
            "contextual_reference_entity_id": entity_id,
            "contextual_reference_source_sentence_id": source_sentence_id,
        }
    )
    proposal = dict(common.get("admission_proposal") or {})
    proposal["reason_codes"] = list(
        dict.fromkeys(
            [
                *(proposal.get("reason_codes") or []),
                "U01QB13_EXACT_BLUEPRINT_CONTEXTUAL_REFERENCE_REQUIREMENT",
                "U01SA05R2_EXACT_SCENE_ANTECEDENT_SENTENCE_BOUND",
            ]
        )
    )
    common["admission_proposal"] = proposal
    return base._finalize(common)


def _contextual_reference_payload(
    *,
    blueprint: Sequence[Mapping[str, Any]],
    sentence_pool: Mapping[str, Any],
    sentence_pool_sha256: str,
    scene_resolver: Callable[[str], Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    requirements = contextual_reference_requirements(blueprint)
    by_scene = base._profiles_by_scene(sentence_pool)
    vocabulary = base._unit01_vocabulary_authority()
    usage: Counter[str] = Counter()
    items: list[dict[str, Any]] = []
    assignments: list[dict[str, Any]] = []

    for requirement in requirements:
        ref = str(requirement["scene_ref_id"])
        profiles = by_scene.get(ref, [])
        if not profiles:
            raise SentencePoolCapacityError(
                f"PF09_SCENE_SENTENCE_SUPPLY_GAP:{requirement['activity_id']}:{ref}"
            )
        first_profile, first_slot = base._choose_first(
            base._first_mention_options(profiles, vocabulary),
            usage,
            scene_ref_id=ref,
            activity_id=str(requirement["activity_id"]),
        )
        item = _contextual_reference_item(
            requirement,
            first_profile,
            first_slot,
            source_pool_sha256=sentence_pool_sha256,
            scene_pattern_refs=base._scene_pattern_refs(ref, scene_resolver),
        )
        items.append(item)
        assignments.append(
            {
                **deepcopy(dict(requirement)),
                "item_id": item["item_id"],
                "source_sentence_ids": list(item["source_sentence_ids"]),
                "target_pattern_ids": list(item["target_pattern_ids"]),
                "contextual_reference_entity_id": item[
                    "contextual_reference_entity_id"
                ],
            }
        )

    count = len(requirements)
    if len(items) != count or len(assignments) != count:
        raise SentencePoolCapacityError(
            f"PF09_MATERIALIZED_COUNT_DRIFT:{len(items)}:{len(assignments)}:{count}"
        )
    if len({str(row["item_id"]) for row in items}) != count:
        raise SentencePoolCapacityError("PF09_MATERIALIZED_ITEM_ID_DUPLICATE")
    if len({str(row["semantic_signature"]) for row in items}) != count:
        raise SentencePoolCapacityError("PF09_MATERIALIZED_SEMANTIC_SIGNATURE_DUPLICATE")
    return items, assignments, {
        "distinct_sentence_count": len(usage),
        "sentence_reference_count": sum(usage.values()),
        "max_reuse_count": max(usage.values(), default=0),
    }


def build_reconciliation_payload(
    *,
    blueprint: Sequence[Mapping[str, Any]],
    sentence_pool: Mapping[str, Any],
    sentence_pool_sha256: str,
    scene_resolver: Callable[[str], Mapping[str, Any]] = scene_authority.canonical_scene_package,
) -> dict[str, Any]:
    payload = base.build_reconciliation_payload(
        blueprint=blueprint,
        sentence_pool=sentence_pool,
        sentence_pool_sha256=sentence_pool_sha256,
        scene_resolver=scene_resolver,
    )
    items, assignments, usage = _contextual_reference_payload(
        blueprint=blueprint,
        sentence_pool=sentence_pool,
        sentence_pool_sha256=sentence_pool_sha256,
        scene_resolver=scene_resolver,
    )
    count = len(items)
    production_count = int(payload["production_requirements"]["requirement_count"])

    payload["source_identity"][
        "historical_contextual_reference_inventory_count"
    ] = HISTORICAL_CONTEXTUAL_REFERENCE_BASE_CAPACITY
    payload["contextual_reference_requirements"] = {
        "requirement_count": count,
        "family_id": PF09_FAMILY,
        "task_angle": PF09_TASK_ANGLE,
        "all_requirements_exact_scene_bound": True,
        "denominator_authority": "U01QB13_BLUEPRINT_ACTIVITIES",
    }
    payload["contextual_reference_assignments"] = assignments
    payload["contextual_reference_items"] = items
    payload["contextual_reference_sentence_usage"] = usage
    payload["count_preservation"].update(
        {
            "retired_contextual_reference_item_count": count,
            "materialized_contextual_reference_item_count": count,
            "total_retired_item_count": production_count + count,
            "total_materialized_item_count": production_count + count,
            "contextual_reference_family_count_before": (
                HISTORICAL_CONTEXTUAL_REFERENCE_BASE_CAPACITY
            ),
            "contextual_reference_family_count_after": (
                HISTORICAL_CONTEXTUAL_REFERENCE_BASE_CAPACITY
            ),
        }
    )
    unsigned = dict(payload)
    unsigned.pop("reconciliation_sha256", None)
    payload["reconciliation_sha256"] = policy_artifact.digest(unsigned)
    return payload


def build_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    return base.build_candidate(payload)


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return base.admit_candidate(candidate)


def _select_contextual_reference_retired_ids(
    catalog_rows: Sequence[Mapping[str, Any] | sqlite3.Row],
    extension_ids: set[str],
    desired_count: int,
) -> set[str]:
    available = sorted(
        str(row["item_id"])
        for row in catalog_rows
        if str(row["pattern_family_id"]) == PF09_FAMILY
        and str(row["item_id"]) not in extension_ids
    )
    if len(available) != HISTORICAL_CONTEXTUAL_REFERENCE_BASE_CAPACITY:
        raise SentencePoolCapacityError(
            "HISTORICAL_CONTEXTUAL_REFERENCE_INVENTORY_DRIFT:"
            f"{len(available)}:{HISTORICAL_CONTEXTUAL_REFERENCE_BASE_CAPACITY}"
        )
    if desired_count <= 0 or desired_count > len(available):
        raise SentencePoolCapacityError(
            f"CONTEXTUAL_REFERENCE_RETIREMENT_CAPACITY_INVALID:{desired_count}:{len(available)}"
        )
    return set(available[:desired_count])


def _reconcile_contextual_reference_runtime(
    *,
    disposable_database: Path,
    approved: Mapping[str, Any],
) -> dict[str, Any]:
    payload = approved.get("payload") or {}
    desired_items = [
        deepcopy(dict(row)) for row in payload.get("contextual_reference_items") or []
    ]
    desired = {str(row["item_id"]): row for row in desired_items}
    requirement_count = int(
        (payload.get("contextual_reference_requirements") or {}).get(
            "requirement_count"
        )
        or 0
    )
    if len(desired) != requirement_count:
        raise SentencePoolCapacityError(
            f"PF09_APPROVED_MATERIALIZED_ITEMS_INVALID:{len(desired)}:{requirement_count}"
        )

    runtime = qb02.Unit01ApprovedVariantSessionRuntime(Path(disposable_database))
    with runtime.write() as connection:
        connection.row_factory = sqlite3.Row
        extension_before = u11._extension_snapshot(connection)
        extension_ids = set(extension_before["item_ids"])
        catalog_rows = connection.execute(
            "SELECT item_id,pattern_family_id FROM u01qb02_item_catalog"
        ).fetchall()
        current_ids = {str(row["item_id"]) for row in catalog_rows}
        if current_ids & set(desired):
            raise SentencePoolCapacityError("PF09_R2R2_ITEM_ID_COLLISION")

        retired = _select_contextual_reference_retired_ids(
            catalog_rows, extension_ids, requirement_count
        )
        marks = ",".join("?" for _ in retired)
        retired_values = tuple(sorted(retired))
        sessions = sorted(
            {
                str(row[0])
                for row in connection.execute(
                    f"SELECT DISTINCT session_id FROM u01qb02_session_items "
                    f"WHERE item_id IN ({marks})",
                    retired_values,
                )
            }
            | {
                str(row[0])
                for row in connection.execute(
                    f"SELECT DISTINCT session_id FROM u01qb02_item_exposures "
                    f"WHERE item_id IN ({marks})",
                    retired_values,
                )
            }
        )
        if sessions and base._table_exists(connection, "u01qb13_session_bindings"):
            session_marks = ",".join("?" for _ in sessions)
            connection.execute(
                f"DELETE FROM u01qb13_session_bindings "
                f"WHERE session_id IN ({session_marks})",
                tuple(sessions),
            )
        affected_sessions, archived_records = u11._archive_affected_history(
            connection, retired, archived_at=u11.utc_now()
        )
        connection.execute(
            f"DELETE FROM u01qb02_item_catalog WHERE item_id IN ({marks})",
            retired_values,
        )
        for item_id in sorted(desired):
            u11._register_base_item(connection, desired[item_id])

        extension_after = u11._extension_snapshot(connection)
        if extension_after["identity_sha256"] != extension_before["identity_sha256"]:
            raise SentencePoolCapacityError("PF09_REAL62_EXTENSION_IDENTITY_CHANGED")
        total = int(
            connection.execute("SELECT COUNT(*) FROM u01qb02_item_catalog").fetchone()[0]
        )
        extension_count = int(
            connection.execute("SELECT COUNT(*) FROM razq01e_extension_items").fetchone()[0]
        )
        base_count = total - extension_count
        pf09_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM u01qb02_item_catalog "
                "WHERE pattern_family_id=? "
                "AND item_id NOT IN (SELECT item_id FROM razq01e_extension_items)",
                (PF09_FAMILY,),
            ).fetchone()[0]
        )
        if (base_count, extension_count, total) != (
            EXPECTED_BASE_COUNT,
            EXPECTED_EXTENSION_COUNT,
            EXPECTED_RUNTIME_COUNT,
        ):
            raise SentencePoolCapacityError(
                f"PF09_POST_RECONCILIATION_DENOMINATOR_INVALID:"
                f"{base_count}:{extension_count}:{total}"
            )
        if pf09_count != HISTORICAL_CONTEXTUAL_REFERENCE_BASE_CAPACITY:
            raise SentencePoolCapacityError(
                f"PF09_POST_INVENTORY_DRIFT:{pf09_count}:"
                f"{HISTORICAL_CONTEXTUAL_REFERENCE_BASE_CAPACITY}"
            )
        connection.executemany(
            f"INSERT OR REPLACE INTO {METADATA_TABLE}(key,value) VALUES(?,?)",
            {
                "contextual_reference_requirement_count": str(requirement_count),
                "retired_contextual_reference_item_count": str(requirement_count),
                "materialized_contextual_reference_item_count": str(requirement_count),
                "contextual_reference_family_count_after": str(pf09_count),
            }.items(),
        )

    return {
        "validation_status": PASS_STATUS,
        "retired_contextual_reference_item_count": requirement_count,
        "materialized_contextual_reference_item_count": requirement_count,
        "contextual_reference_family_count_after": (
            HISTORICAL_CONTEXTUAL_REFERENCE_BASE_CAPACITY
        ),
        "contextual_reference_affected_session_count": affected_sessions,
        "contextual_reference_archived_runtime_history_record_count": archived_records,
        "base_item_count": EXPECTED_BASE_COUNT,
        "extension_item_count": EXPECTED_EXTENSION_COUNT,
        "runtime_item_count": EXPECTED_RUNTIME_COUNT,
        "real62_extension_identity_sha256": extension_after["identity_sha256"],
    }


def reconcile_disposable_runtime(
    *,
    source_database: Path,
    disposable_database: Path,
    approved: Mapping[str, Any],
) -> dict[str, Any]:
    migration = base.reconcile_disposable_runtime(
        source_database=source_database,
        disposable_database=disposable_database,
        approved=approved,
    )
    contextual = _reconcile_contextual_reference_runtime(
        disposable_database=disposable_database,
        approved=approved,
    )
    migration.update(contextual)
    return migration


def materialize(
    *,
    source_database: Path,
    disposable_database: Path,
    sentence_pool_capability_index: Path,
    candidate_path: Path,
    approved_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    pool = load_sentence_pool(sentence_pool_capability_index)
    pool_sha = file_digest(sentence_pool_capability_index)
    with sqlite3.connect(source_database) as connection:
        connection.row_factory = sqlite3.Row
        blueprint = blueprint_rows(connection)
    payload = build_reconciliation_payload(
        blueprint=blueprint,
        sentence_pool=pool,
        sentence_pool_sha256=pool_sha,
    )
    candidate = build_candidate(payload)
    approved = admit_candidate(candidate)
    from ulga.validators import (
        validate_a1fs_v1_u01qb18h_r2r2_unit01_sentence_pool_driven_production_capacity_reconciliation
        as validator,
    )

    validation = validator.validate_approved(candidate, approved)
    if validation.get("error_count"):
        raise SentencePoolCapacityError(
            "R2R2_APPROVED_VALIDATION_FAILED:"
            + "|".join(validation.get("errors") or [])
        )
    write_json(candidate_path, candidate, private=True)
    write_json(approved_path, approved, private=True)
    migration = reconcile_disposable_runtime(
        source_database=source_database,
        disposable_database=disposable_database,
        approved=approved,
    )
    production_count = int(payload["production_requirements"]["requirement_count"])
    contextual_count = int(
        payload["contextual_reference_requirements"]["requirement_count"]
    )
    report = {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "candidate_artifact_sha256": candidate["artifact_sha256"],
        "approved_artifact_sha256": approved["artifact_sha256"],
        "sentence_pool_capability_index_sha256": pool_sha,
        "production_requirement_count": production_count,
        "production_family_counts": payload["production_requirements"]["family_counts"],
        "materialized_item_count": len(payload["materialized_items"]),
        "contextual_reference_requirement_count": contextual_count,
        "contextual_reference_materialized_item_count": len(
            payload["contextual_reference_items"]
        ),
        "distinct_source_sentence_count": payload["sentence_usage"][
            "distinct_sentence_count"
        ],
        "source_sentence_reference_count": payload["sentence_usage"][
            "sentence_reference_count"
        ],
        "max_source_sentence_reuse_count": payload["sentence_usage"][
            "max_reuse_count"
        ],
        "contextual_reference_sentence_usage": deepcopy(
            payload["contextual_reference_sentence_usage"]
        ),
        "runtime_migration": migration,
        "validation_receipt": validation,
        "boundaries": deepcopy(payload["boundaries"]),
        "next_short_step": NEXT_SHORT_STEP,
    }
    write_json(report_path, report, private=True)
    return report


def __getattr__(name: str):
    return getattr(base, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(base)))
