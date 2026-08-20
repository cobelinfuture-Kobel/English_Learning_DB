#!/usr/bin/env python3
"""Blueprint-authoritative Unit01 sentence-pool production reconciliation.

The historical U01QB10 inventory contains 48 generic PF13/PF14/PF15 Writing
items.  That inventory size is NOT the learner-product denominator.  R2R2 reads
the installed U01QB13 240-row blueprint and derives the exact current scored
Writing production requirements from it.  Let N be that blueprint-derived
count (43 in the first real private replay that exposed this contract drift).
R2R2 then retires exactly N legacy generic production rows, family-for-family,
and materializes exactly N sentence-backed exact-scene replacements.  Any
surplus legacy production inventory is retained only as inventory; the R2R2
acceptance guard prevents it from competing with exact-slot items.

The source SQLite database is never mutated.  A disposable backup is reconciled.
The 288 base + 186 Real62 = 474 denominator therefore remains unchanged.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ulga.builders import _u01qb18h_r2r2_fixed48_legacy as legacy

# Public contract / compatibility exports.  The fixed-48 values below describe
# historical inventory capacity, not the current blueprint requirement count.
A1FS_CONTENT_POLICY_MODE = legacy.A1FS_CONTENT_POLICY_MODE
PROGRAM_ID = legacy.PROGRAM_ID
TASK_ID = legacy.TASK_ID
SCHEMA_VERSION = legacy.SCHEMA_VERSION
PASS_STATUS = legacy.PASS_STATUS
DECISION_REF = legacy.DECISION_REF
NEXT_SHORT_STEP = legacy.NEXT_SHORT_STEP
SOURCE_TASK_ID = legacy.SOURCE_TASK_ID
SOURCE_STATUS = legacy.SOURCE_STATUS
EXPECTED_SENTENCE_POOL_TOTAL = legacy.EXPECTED_SENTENCE_POOL_TOTAL
EXPECTED_BLUEPRINT_ACTIVITY_COUNT = legacy.EXPECTED_BLUEPRINT_ACTIVITY_COUNT
EXPECTED_PRODUCTION_REQUIREMENT_COUNT = legacy.EXPECTED_PRODUCTION_REQUIREMENT_COUNT
EXPECTED_BASE_COUNT = legacy.EXPECTED_BASE_COUNT
EXPECTED_EXTENSION_COUNT = legacy.EXPECTED_EXTENSION_COUNT
EXPECTED_RUNTIME_COUNT = legacy.EXPECTED_RUNTIME_COUNT
PRODUCTION_ANGLE_TO_FAMILY = legacy.PRODUCTION_ANGLE_TO_FAMILY
EXPECTED_PRODUCTION_FAMILY_COUNTS = legacy.EXPECTED_PRODUCTION_FAMILY_COUNTS
HISTORICAL_PRODUCTION_INVENTORY_COUNT = EXPECTED_PRODUCTION_REQUIREMENT_COUNT
HISTORICAL_PRODUCTION_FAMILY_COUNTS = dict(EXPECTED_PRODUCTION_FAMILY_COUNTS)
METADATA_TABLE = legacy.METADATA_TABLE

u11 = legacy.u11
scene_authority = legacy.scene_authority
s01 = legacy.s01
policy_artifact = legacy.policy_artifact
qb02 = legacy.qb02
u10 = legacy.u10
u13 = legacy.u13
SentencePoolCapacityError = legacy.SentencePoolCapacityError

# Reuse the already-CI-proven sentence capability / item-authoring helpers.
canonical = legacy.canonical
digest = legacy.digest
file_digest = legacy.file_digest
write_json = legacy.write_json
read_json = legacy.read_json
load_sentence_pool = legacy.load_sentence_pool
_require_table = legacy._require_table
blueprint_rows = legacy.blueprint_rows
_unit01_vocabulary_authority = legacy._unit01_vocabulary_authority
_slot_surface = legacy._slot_surface
_slot_target = legacy._slot_target
_slot_role_eligible = legacy._slot_role_eligible
_usable_np_slots = legacy._usable_np_slots
_source_rank = legacy._source_rank
_profiles_by_scene = legacy._profiles_by_scene
_options = legacy._options
_first_mention_options = legacy._first_mention_options
_known_reference_options = legacy._known_reference_options
_choose_first = legacy._choose_first
_choose_pair = legacy._choose_pair
_internal_unit_pattern = legacy._internal_unit_pattern
_target_egp_rows = legacy._target_egp_rows
_scene_pattern_refs = legacy._scene_pattern_refs
_common_item = legacy._common_item
_response_contract = legacy._response_contract
_finalize = legacy._finalize
_np_surface = legacy._np_surface
_production_item = legacy._production_item
_backup_sqlite = legacy._backup_sqlite
_table_exists = legacy._table_exists


def _normalized_family_counts(values: Mapping[str, int] | Counter[str]) -> dict[str, int]:
    return {
        family: int(values.get(family, 0))
        for family in HISTORICAL_PRODUCTION_FAMILY_COUNTS
    }


def _validate_requirement_capacity(counts: Mapping[str, int]) -> None:
    for family, historical_capacity in HISTORICAL_PRODUCTION_FAMILY_COUNTS.items():
        requested = int(counts.get(family, 0))
        if requested < 0 or requested > int(historical_capacity):
            raise SentencePoolCapacityError(
                f"BLUEPRINT_PRODUCTION_FAMILY_CAPACITY_EXCEEDED:"
                f"{family}:{requested}:{historical_capacity}"
            )


def count_preservation(requirement_count: int) -> dict[str, Any]:
    requirement_count = int(requirement_count)
    if requirement_count <= 0 or requirement_count > HISTORICAL_PRODUCTION_INVENTORY_COUNT:
        raise SentencePoolCapacityError(
            f"BLUEPRINT_PRODUCTION_REQUIREMENT_COUNT_OUT_OF_RANGE:"
            f"{requirement_count}:{HISTORICAL_PRODUCTION_INVENTORY_COUNT}"
        )
    return {
        "base_count_before": EXPECTED_BASE_COUNT,
        "retired_production_item_count": requirement_count,
        "materialized_production_item_count": requirement_count,
        "base_count_after": EXPECTED_BASE_COUNT,
        "real62_extension_count": EXPECTED_EXTENSION_COUNT,
        "runtime_count_after": EXPECTED_RUNTIME_COUNT,
        "question_bank_total_expanded": False,
    }


def production_requirements(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Derive the current production denominator from the canonical blueprint.

    U01QB10's 48 is historical inventory capacity.  The installed U01QB13
    blueprint is the authority for how many scored Writing PF13/PF14/PF15 slots
    the current 12-form learner product actually requires.
    """
    result: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("skill") or "") != "WRITING":
            continue
        angle = str(row.get("task_angle") or "")
        family = PRODUCTION_ANGLE_TO_FAMILY.get(angle)
        if family is None:
            continue
        allowed = {
            str(value)
            for value in json.loads(str(row.get("pattern_family_ids_json") or "[]"))
            if str(value)
        }
        if family not in allowed:
            raise SentencePoolCapacityError(
                f"BLUEPRINT_PRODUCTION_FAMILY_NOT_ALLOWED:"
                f"{row.get('activity_id')}:{angle}:{family}:{sorted(allowed)}"
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
                "task_angle": angle,
                "pattern_family_id": family,
            }
        )
    counts = _normalized_family_counts(Counter(row["pattern_family_id"] for row in result))
    _validate_requirement_capacity(counts)
    count_preservation(len(result))
    return result


def build_reconciliation_payload(
    *,
    blueprint: Sequence[Mapping[str, Any]],
    sentence_pool: Mapping[str, Any],
    sentence_pool_sha256: str,
    scene_resolver: Callable[[str], Mapping[str, Any]] = scene_authority.canonical_scene_package,
) -> dict[str, Any]:
    requirements = production_requirements(blueprint)
    requirement_count = len(requirements)
    requirement_family_counts = _normalized_family_counts(
        Counter(row["pattern_family_id"] for row in requirements)
    )
    by_scene = _profiles_by_scene(sentence_pool)
    vocabulary = _unit01_vocabulary_authority()
    usage: Counter[str] = Counter()
    items: list[dict[str, Any]] = []
    assignments: list[dict[str, Any]] = []

    for requirement in requirements:
        scene_ref = str(requirement["scene_ref_id"])
        profiles = by_scene.get(scene_ref, [])
        if not profiles:
            raise SentencePoolCapacityError(
                f"SCENE_SENTENCE_SUPPLY_GAP:{requirement['activity_id']}:{scene_ref}"
            )
        first_options = _first_mention_options(profiles, vocabulary)
        family = str(requirement["pattern_family_id"])
        known_profile = None
        if family == u10.PF15:
            first_profile, first_slot, known_profile, _known_slot = _choose_pair(
                first_options,
                _known_reference_options(profiles, vocabulary),
                usage,
                scene_ref_id=scene_ref,
                activity_id=str(requirement["activity_id"]),
            )
        else:
            first_profile, first_slot = _choose_first(
                first_options,
                usage,
                scene_ref_id=scene_ref,
                activity_id=str(requirement["activity_id"]),
            )
        item = _production_item(
            requirement,
            first_profile,
            first_slot,
            known_profile,
            source_pool_sha256=sentence_pool_sha256,
            scene_pattern_refs=_scene_pattern_refs(scene_ref, scene_resolver),
        )
        items.append(item)
        assignments.append(
            {
                **deepcopy(dict(requirement)),
                "item_id": item["item_id"],
                "source_sentence_ids": list(item["source_sentence_ids"]),
                "target_pattern_ids": list(item["target_pattern_ids"]),
            }
        )

    item_family_counts = _normalized_family_counts(
        Counter(str(item["pattern_family_id"]) for item in items)
    )
    if item_family_counts != requirement_family_counts:
        raise SentencePoolCapacityError(
            f"MATERIALIZED_FAMILY_DISTRIBUTION_DRIFT:"
            f"{item_family_counts}:{requirement_family_counts}"
        )
    if len(items) != requirement_count:
        raise SentencePoolCapacityError(
            f"MATERIALIZED_REQUIREMENT_COUNT_DRIFT:{len(items)}:{requirement_count}"
        )
    if len({str(item["item_id"]) for item in items}) != requirement_count:
        raise SentencePoolCapacityError("MATERIALIZED_ITEM_ID_DUPLICATE")
    if len({str(item["semantic_signature"]) for item in items}) != requirement_count:
        raise SentencePoolCapacityError("MATERIALIZED_SEMANTIC_SIGNATURE_DUPLICATE")

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": u10.UNIT_ID,
        "source_identity": {
            "sentence_pool_task_id": SOURCE_TASK_ID,
            "sentence_pool_capability_index_sha256": sentence_pool_sha256,
            "sentence_pool_total": EXPECTED_SENTENCE_POOL_TOTAL,
            "blueprint_task_id": u13.TASK_ID,
            "blueprint_activity_count": len(blueprint),
            "vocabulary_authority_task_id": s01.TASK_ID,
            "historical_production_inventory_count": HISTORICAL_PRODUCTION_INVENTORY_COUNT,
        },
        "production_requirements": {
            "requirement_count": requirement_count,
            "family_counts": requirement_family_counts,
            "all_requirements_exact_scene_bound": True,
            "denominator_authority": "U01QB13_BLUEPRINT_ACTIVITIES",
        },
        "assignments": assignments,
        "materialized_items": items,
        "sentence_usage": {
            "distinct_sentence_count": len(usage),
            "sentence_reference_count": sum(usage.values()),
            "max_reuse_count": max(usage.values(), default=0),
        },
        "count_preservation": count_preservation(requirement_count),
        "boundaries": {
            "source_sentence_text_mutated": False,
            "human_sentence_review_decision_mutated": False,
            "scoring_architecture_changed": False,
            "second_question_bank_created": False,
            "second_runtime_created": False,
            "source_database_mutated": False,
            "real62_extension_modified": False,
            "m3_learner_state_rewritten": False,
            "m6_attempts_or_scoring_deleted": False,
            "speaking_scoring_enabled": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    payload["reconciliation_sha256"] = policy_artifact.digest(payload)
    return payload


def build_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    return policy_artifact.build_candidate(
        payload=dict(payload),
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings={
            "sentence_pool_task_id": SOURCE_TASK_ID,
            "sentence_pool_capability_index_sha256": (
                payload.get("source_identity") or {}
            ).get("sentence_pool_capability_index_sha256"),
            "blueprint_task_id": u13.TASK_ID,
            "vocabulary_authority_task_id": s01.TASK_ID,
            "count_preserving": True,
            "operator_decision_ref": DECISION_REF,
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import (
        validate_a1fs_v1_u01qb18h_r2r2_unit01_sentence_pool_driven_production_capacity_reconciliation
        as validator,
    )

    return policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[validator.validate_candidate(candidate)],
        decision_ref=DECISION_REF,
        producer_id=TASK_ID,
    )


def _select_retired_legacy_ids(
    catalog_rows: Sequence[Mapping[str, Any] | sqlite3.Row],
    extension_ids: set[str],
    desired_family_counts: Mapping[str, int],
) -> set[str]:
    by_family: dict[str, list[str]] = defaultdict(list)
    for row in catalog_rows:
        item_id = str(row["item_id"])
        family = str(row["pattern_family_id"])
        if item_id in extension_ids or family not in HISTORICAL_PRODUCTION_FAMILY_COUNTS:
            continue
        by_family[family].append(item_id)
    retired: set[str] = set()
    for family, historical_capacity in HISTORICAL_PRODUCTION_FAMILY_COUNTS.items():
        available = sorted(by_family.get(family, []))
        if len(available) != int(historical_capacity):
            raise SentencePoolCapacityError(
                f"HISTORICAL_PRODUCTION_INVENTORY_DRIFT:"
                f"{family}:{len(available)}:{historical_capacity}"
            )
        requested = int(desired_family_counts.get(family, 0))
        if requested > len(available):
            raise SentencePoolCapacityError(
                f"PRODUCTION_RETIREMENT_CAPACITY_INVALID:"
                f"{family}:{requested}:{len(available)}"
            )
        retired.update(available[:requested])
    return retired


def reconcile_disposable_runtime(
    *,
    source_database: Path,
    disposable_database: Path,
    approved: Mapping[str, Any],
) -> dict[str, Any]:
    payload = approved.get("payload")
    if not isinstance(payload, Mapping) or payload.get("task_id") != TASK_ID:
        raise SentencePoolCapacityError("APPROVED_R2R2_PAYLOAD_INVALID")
    from ulga.validators import validate_a1fs_v1_policy_bound_content_artifact as policy_validator

    policy_validator.validate_artifact(
        approved, expected_role=policy_artifact.APPROVED_ROLE
    )
    _backup_sqlite(Path(source_database), Path(disposable_database))

    desired_items = [
        deepcopy(dict(row)) for row in payload.get("materialized_items") or []
    ]
    desired = {str(row["item_id"]): row for row in desired_items}
    requirement_count = int(
        (payload.get("production_requirements") or {}).get("requirement_count") or 0
    )
    desired_family_counts = _normalized_family_counts(
        Counter(str(row["pattern_family_id"]) for row in desired_items)
    )
    _validate_requirement_capacity(desired_family_counts)
    if len(desired) != requirement_count:
        raise SentencePoolCapacityError(
            f"APPROVED_MATERIALIZED_ITEMS_INVALID:{len(desired)}:{requirement_count}"
        )

    runtime = qb02.Unit01ApprovedVariantSessionRuntime(Path(disposable_database))
    with runtime.write() as connection:
        connection.row_factory = sqlite3.Row
        for table in (
            "metadata",
            "lesson_assets",
            "response_contracts",
            "response_attempts",
            "scoring_results",
            "u01qb02_metadata",
            "u01qb02_item_catalog",
            "u01qb02_session_plans",
            "u01qb02_session_items",
            "u01qb02_item_exposures",
            "razq01e_metadata",
            "razq01e_extension_items",
            "u01qb12_metadata",
            "u01qb13_blueprint_activities",
        ):
            _require_table(connection, table)
        connection.executescript(u11.ARCHIVE_SQL)
        connection.execute(
            f"CREATE TABLE IF NOT EXISTS {METADATA_TABLE}("
            "key TEXT PRIMARY KEY,value TEXT NOT NULL)"
        )
        extension_before = u11._extension_snapshot(connection)
        extension_ids = set(extension_before["item_ids"])
        catalog_rows = connection.execute(
            "SELECT item_id,pattern_family_id FROM u01qb02_item_catalog"
        ).fetchall()
        current_ids = {str(row["item_id"]) for row in catalog_rows}
        if len(current_ids) != EXPECTED_RUNTIME_COUNT:
            raise SentencePoolCapacityError(
                f"PRE_RECONCILIATION_RUNTIME_COUNT_INVALID:{len(current_ids)}"
            )
        if len(current_ids - extension_ids) != EXPECTED_BASE_COUNT:
            raise SentencePoolCapacityError("PRE_RECONCILIATION_BASE_COUNT_INVALID")
        if current_ids & set(desired):
            raise SentencePoolCapacityError("R2R2_ITEM_ID_COLLISION")

        retired = _select_retired_legacy_ids(
            catalog_rows, extension_ids, desired_family_counts
        )
        if len(retired) != requirement_count:
            raise SentencePoolCapacityError(
                f"RETIRED_PRODUCTION_COUNT_INVALID:{len(retired)}:{requirement_count}"
            )
        retired_counts = _normalized_family_counts(
            Counter(
                str(row["pattern_family_id"])
                for row in catalog_rows
                if str(row["item_id"]) in retired
            )
        )
        if retired_counts != desired_family_counts:
            raise SentencePoolCapacityError(
                f"RETIRED_PRODUCTION_DISTRIBUTION_INVALID:"
                f"{retired_counts}:{desired_family_counts}"
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
        if sessions and _table_exists(connection, "u01qb13_session_bindings"):
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
            raise SentencePoolCapacityError("REAL62_EXTENSION_IDENTITY_CHANGED")
        total = int(
            connection.execute("SELECT COUNT(*) FROM u01qb02_item_catalog").fetchone()[0]
        )
        extension_count = int(
            connection.execute("SELECT COUNT(*) FROM razq01e_extension_items").fetchone()[0]
        )
        base_count = total - extension_count
        if (base_count, extension_count, total) != (
            EXPECTED_BASE_COUNT,
            EXPECTED_EXTENSION_COUNT,
            EXPECTED_RUNTIME_COUNT,
        ):
            raise SentencePoolCapacityError(
                f"POST_RECONCILIATION_DENOMINATOR_INVALID:"
                f"{base_count}:{extension_count}:{total}"
            )
        post_production_counts = _normalized_family_counts(
            Counter(
                str(row[0])
                for row in connection.execute(
                    "SELECT pattern_family_id FROM u01qb02_item_catalog "
                    "WHERE item_id NOT IN (SELECT item_id FROM razq01e_extension_items)"
                )
                if str(row[0]) in HISTORICAL_PRODUCTION_FAMILY_COUNTS
            )
        )
        if post_production_counts != HISTORICAL_PRODUCTION_FAMILY_COUNTS:
            raise SentencePoolCapacityError(
                f"POST_PRODUCTION_INVENTORY_DRIFT:"
                f"{post_production_counts}:{HISTORICAL_PRODUCTION_FAMILY_COUNTS}"
            )

        combined_sha = digest(
            {
                "r2r2_approved_artifact_sha256": approved["artifact_sha256"],
                "content_extension_artifact_sha256": extension_after["artifact_sha256"],
            }
        )
        connection.executemany(
            "INSERT OR REPLACE INTO u01qb02_metadata(key,value) VALUES(?,?)",
            {
                "base_source_bank_artifact_sha256": str(approved["artifact_sha256"]),
                "source_bank_artifact_sha256": combined_sha,
                "approved_item_count": str(EXPECTED_BASE_COUNT),
                "razq01e_extension_artifact_sha256": str(extension_after["artifact_sha256"]),
                "razq01e_extension_item_count": str(EXPECTED_EXTENSION_COUNT),
                "razq01e_combined_runtime_item_count": str(EXPECTED_RUNTIME_COUNT),
                "u01qb18h_r2r2_task_id": TASK_ID,
                "u01qb18h_r2r2_schema_version": SCHEMA_VERSION,
                "u01qb18h_r2r2_validation_status": PASS_STATUS,
                "u01qb18h_r2r2_next_short_step": NEXT_SHORT_STEP,
            }.items(),
        )
        connection.executemany(
            f"INSERT OR REPLACE INTO {METADATA_TABLE}(key,value) VALUES(?,?)",
            {
                "task_id": TASK_ID,
                "schema_version": SCHEMA_VERSION,
                "validation_status": PASS_STATUS,
                "approved_artifact_sha256": str(approved["artifact_sha256"]),
                "source_database": str(Path(source_database).resolve()),
                "source_database_mutated": "false",
                "base_item_count": str(base_count),
                "extension_item_count": str(extension_count),
                "runtime_item_count": str(total),
                "retired_production_item_count": str(requirement_count),
                "materialized_production_item_count": str(requirement_count),
                "retained_legacy_production_item_count": str(
                    HISTORICAL_PRODUCTION_INVENTORY_COUNT - requirement_count
                ),
                "next_short_step": NEXT_SHORT_STEP,
            }.items(),
        )

    return {
        "validation_status": PASS_STATUS,
        "source_database": str(Path(source_database).resolve()),
        "disposable_database": str(Path(disposable_database).resolve()),
        "source_database_mutated": False,
        "retired_production_item_count": requirement_count,
        "materialized_production_item_count": requirement_count,
        "retained_legacy_production_item_count": (
            HISTORICAL_PRODUCTION_INVENTORY_COUNT - requirement_count
        ),
        "production_family_replacement_counts": desired_family_counts,
        "affected_session_count": affected_sessions,
        "archived_runtime_history_record_count": archived_records,
        "base_item_count": EXPECTED_BASE_COUNT,
        "extension_item_count": EXPECTED_EXTENSION_COUNT,
        "runtime_item_count": EXPECTED_RUNTIME_COUNT,
        "real62_extension_identity_sha256": extension_after["identity_sha256"],
        "approved_artifact_sha256": str(approved["artifact_sha256"]),
        "combined_source_bank_sha256": combined_sha,
    }


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
    requirement_count = int(payload["production_requirements"]["requirement_count"])
    report = {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "candidate_artifact_sha256": candidate["artifact_sha256"],
        "approved_artifact_sha256": approved["artifact_sha256"],
        "sentence_pool_capability_index_sha256": pool_sha,
        "production_requirement_count": requirement_count,
        "production_family_counts": payload["production_requirements"]["family_counts"],
        "materialized_item_count": len(payload["materialized_items"]),
        "distinct_source_sentence_count": payload["sentence_usage"]["distinct_sentence_count"],
        "source_sentence_reference_count": payload["sentence_usage"]["sentence_reference_count"],
        "max_source_sentence_reuse_count": payload["sentence_usage"]["max_reuse_count"],
        "runtime_migration": migration,
        "validation_receipt": validation,
        "boundaries": deepcopy(payload["boundaries"]),
        "next_short_step": NEXT_SHORT_STEP,
    }
    write_json(report_path, report, private=True)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-database", type=Path, required=True)
    parser.add_argument("--disposable-database", type=Path, required=True)
    parser.add_argument("--sentence-pool-capability-index", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--approved", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        value = materialize(
            source_database=args.source_database,
            disposable_database=args.disposable_database,
            sentence_pool_capability_index=args.sentence_pool_capability_index,
            candidate_path=args.candidate,
            approved_path=args.approved,
            report_path=args.report,
        )
    except Exception as exc:
        print(f"STATUS=FAIL_{TASK_ID}")
        print(f"ERROR={exc}")
        return 1
    migration = value["runtime_migration"]
    print(f"STATUS={PASS_STATUS}")
    print(f"PRODUCTION_REQUIREMENTS={value['production_requirement_count']}")
    print(f"MATERIALIZED_ITEMS={value['materialized_item_count']}")
    print(f"PRODUCTION_FAMILY_COUNTS={value['production_family_counts']}")
    print(f"BASE_ITEMS={migration['base_item_count']}")
    print(f"REAL62_EXTENSION_ITEMS={migration['extension_item_count']}")
    print(f"RUNTIME_ITEMS={migration['runtime_item_count']}")
    print(
        "RETAINED_LEGACY_PRODUCTION_ITEMS="
        f"{migration['retained_legacy_production_item_count']}"
    )
    print(f"SOURCE_DATABASE_MUTATED={migration['source_database_mutated']}")
    print(f"DISPOSABLE_DATABASE={migration['disposable_database']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
