#!/usr/bin/env python3
"""Supersede U01QB10/U01QB12 source selection with context-stratified FullFix.

U01QB15 preserves the historical U01QB10/U01QB12 task identities and reuses their
item constructors and migration machinery, but replaces the source-selection
policy for the active FullFix path. Reading context-family retirement is spread
across all five canonical Unit01 contexts and the same (context,noun) pair may be
retired from at most one of PF04/PF05/PF08. U01QB12 reference-evidence sources are
also selected by explicit context quota. The resulting base remains 288 items;
Real62 remains 186; the runtime remains 474.

The milestone additionally proves the final 288 base bank itself can satisfy the
31-scene U01QB14R1 rotation across all 36 form/skill sessions using the exact
U01QB13 task bindings and distinct-item matching. Real62 is therefore not used to
mask a deficient canonical base bank.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from ulga.builders import build_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission as s01
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u01qb07_unit01_micro_scene_seed_enrichment as u01qb07
from ulga.builders import build_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as u01qb08
from ulga.builders import build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u01qb09
from ulga.builders import build_a1fs_v1_u01qb10_unit01_question_bank_production_angle_coverage_reconciliation as u01qb10
from ulga.builders import build_a1fs_v1_u01qb12_unit01_reference_evidence_and_phrase_construction_partial_coverage_fullfix as u01qb12
from ulga.builders import build_a1fs_v1_u01qb14r1_unit01_cumulative_scene_world_runtime_bindability_gate_fullfix as u01qb14r1
from ulga.builders import build_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as runtime_patch

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
A1FS_CONTENT_POLICY_EXEMPTION = ""
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB15_Unit01ContextStratifiedQuestionBankReplacementAndPerSceneRuntimeCapacityFullFix"
SCHEMA_VERSION = "a1fs.v1.u01qb15.unit01_context_stratified_question_bank_fullfix.v1"
PASS_STATUS = "PASS_A1FS_V1_U01QB15_UNIT01_CONTEXT_STRATIFIED_QUESTION_BANK_REPLACEMENT_AND_PER_SCENE_RUNTIME_CAPACITY_FULLFIX"
DECISION_REF = "OPERATOR_APPROVAL:2026-08-04:U01QB15"
UNIT_ID = u01qb10.UNIT_ID
BANK_ID = u01qb10.BANK_ID
BANK_VERSION = u01qb10.BANK_VERSION
CANONICAL_REVISION = "U01QB15-R1"
EXPECTED_BASE_COUNT = 288
EXPECTED_EXTENSION_COUNT = 186
EXPECTED_RUNTIME_COUNT = 474
EXPECTED_FORM_COUNT = 12
EXPECTED_SCENE_WORLD_COUNT = 32
EXPECTED_BINDABLE_SCENE_COUNT = 31
EXPECTED_DEFERRED_SCENES = ("U01-MA-FOOD-04",)
EXPECTED_SKILL_SESSION_COUNT = 36
EXPECTED_ACTIVITY_COUNT = 240
READING_REPLACEMENT_FAMILIES = (
    "U01-PF04-FIRST-MENTION-CONTEXT",
    "U01-PF05-KNOWN-REFERENCE-CONTEXT",
    "U01-PF08-TRANSFER-FIRST-MENTION",
)
WRITING_CONTEXT_REPLACEMENT_FAMILY = "U01-PF09-TRANSFER-KNOWN-REFERENCE"
CONTEXT_REPLACEMENT_COUNT = 12
REFERENCE_REPLACEMENT_COUNT = 24
DEFAULT_CANDIDATE = Path("ulga/private/a1fs_v1_u01qb15_context_stratified_qb.candidate.private.json")
DEFAULT_APPROVED = Path("ulga/private/a1fs_v1_u01qb15_context_stratified_qb.approved.private.json")
DEFAULT_REPORT = Path("ulga/reports/a1fs_v1_u01qb15_context_stratified_qb_readback.json")
NEXT_SHORT_STEP = "A1FS-V1-U01QB15_ActualReal62Fresh474MigrationAndU01QB14R1Replay"

CANONICAL_FAMILY = {
    "U01-C1-CLASSROOM-BAG": "SCHOOL",
    "U01-C2-HOME-TOY-BOX": "HOME",
    "U01-C3-PICNIC-FOOD": "FOOD_SOCIAL",
    "U01-C4-TOY-SHOP": "SHOPPING",
    "U01-C5-PARK-BIRTHDAY": "OUTDOORS_SOCIAL",
}


class ContextStratifiedFullFixError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _context_quota(total: int) -> dict[str, int]:
    contexts = list(u01qb10.seed.CONTEXT_IDS)
    base, remainder = divmod(total, len(contexts))
    return {
        context_id: base + int(index < remainder)
        for index, context_id in enumerate(contexts)
    }


U01QB10_CONTEXT_QUOTA = _context_quota(CONTEXT_REPLACEMENT_COUNT)
U01QB12_REFERENCE_CONTEXT_QUOTA = _context_quota(REFERENCE_REPLACEMENT_COUNT)


def _pair_key(row: Mapping[str, Any]) -> tuple[str, str]:
    slots = dict(row.get("lexical_slots") or {})
    return (
        str(row.get("context_id") or slots.get("context_id") or ""),
        str(slots.get("noun") or "").casefold(),
    )


def _group_context_rows(
    items: Sequence[Mapping[str, Any]],
    family_id: str,
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in items:
        if row.get("pattern_family_id") != family_id:
            continue
        context_id, noun = _pair_key(row)
        if context_id not in u01qb10.seed.CONTEXT_IDS or not noun:
            raise ContextStratifiedFullFixError(
                f"CONTEXT_SOURCE_IDENTITY_INVALID:{family_id}:{row.get('item_id')}"
            )
        grouped[context_id].append(deepcopy(dict(row)))
    for context_id in grouped:
        grouped[context_id].sort(key=lambda row: str(row["item_id"]))
    return grouped


def context_stratified_u01qb10_replacement_sources(
    items: Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Select 48 U01QB10 sources without concentrating Reading loss in C1."""
    result: dict[str, list[dict[str, Any]]] = {}
    reserved_reading_pairs: set[tuple[str, str]] = set()

    for family_id in READING_REPLACEMENT_FAMILIES:
        grouped = _group_context_rows(items, family_id)
        selected: list[dict[str, Any]] = []
        for context_id in u01qb10.seed.CONTEXT_IDS:
            need = U01QB10_CONTEXT_QUOTA[context_id]
            candidates = [
                row
                for row in grouped.get(context_id, [])
                if _pair_key(row) not in reserved_reading_pairs
            ]
            if len(candidates) < need:
                raise ContextStratifiedFullFixError(
                    f"READING_CONTEXT_STRATIFICATION_CAPACITY_INVALID:"
                    f"{family_id}:{context_id}:need={need}:available={len(candidates)}"
                )
            chosen = candidates[:need]
            selected.extend(chosen)
            reserved_reading_pairs.update(_pair_key(row) for row in chosen)
        if len(selected) != CONTEXT_REPLACEMENT_COUNT:
            raise ContextStratifiedFullFixError(
                f"READING_REPLACEMENT_COUNT_INVALID:{family_id}:{len(selected)}"
            )
        result[family_id] = selected

    grouped = _group_context_rows(items, WRITING_CONTEXT_REPLACEMENT_FAMILY)
    writing_selected: list[dict[str, Any]] = []
    for context_id in u01qb10.seed.CONTEXT_IDS:
        need = U01QB10_CONTEXT_QUOTA[context_id]
        candidates = grouped.get(context_id, [])
        if len(candidates) < need:
            raise ContextStratifiedFullFixError(
                f"WRITING_CONTEXT_STRATIFICATION_CAPACITY_INVALID:"
                f"{context_id}:need={need}:available={len(candidates)}"
            )
        writing_selected.extend(candidates[:need])
    if len(writing_selected) != CONTEXT_REPLACEMENT_COUNT:
        raise ContextStratifiedFullFixError("WRITING_REPLACEMENT_COUNT_INVALID")
    result[WRITING_CONTEXT_REPLACEMENT_FAMILY] = writing_selected

    if set(result) != set(u01qb10.REPLACEMENT_PLAN):
        raise ContextStratifiedFullFixError("U01QB10_REPLACEMENT_FAMILY_SET_INVALID")
    return result


def context_stratified_u01qb12_reference_sources(
    items: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped = _group_context_rows(items, u01qb12.SOURCE_REFERENCE_FAMILY)
    selected: list[dict[str, Any]] = []
    for context_id in u01qb10.seed.CONTEXT_IDS:
        need = U01QB12_REFERENCE_CONTEXT_QUOTA[context_id]
        rows = grouped.get(context_id, [])
        if len(rows) < need:
            raise ContextStratifiedFullFixError(
                f"REFERENCE_CONTEXT_QUOTA_CAPACITY_INVALID:"
                f"{context_id}:need={need}:available={len(rows)}"
            )
        selected.extend(rows[:need])
    if len(selected) != REFERENCE_REPLACEMENT_COUNT:
        raise ContextStratifiedFullFixError(
            f"REFERENCE_REPLACEMENT_COUNT_INVALID:{len(selected)}"
        )
    return selected


@contextmanager
def context_stratified_policy() -> Iterator[None]:
    """Temporarily supersede historical U01QB10/U01QB12 source selection."""
    old_u10 = u01qb10._replacement_sources
    old_u12 = u01qb12._reference_sources
    u01qb10._replacement_sources = context_stratified_u01qb10_replacement_sources
    u01qb12._reference_sources = context_stratified_u01qb12_reference_sources
    try:
        yield
    finally:
        u01qb10._replacement_sources = old_u10
        u01qb12._reference_sources = old_u12


def _final_u01qb12_authority() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with context_stratified_policy():
        approved, rows = u01qb12.approved_bank()
    return approved, rows


def _legacy_rotation_from_authorities() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for context in s01.CONTEXTS:
        ref = str(context["context_id"])
        rows.append(
            {
                "scene_ref_id": ref,
                "semantic_scene_signature_v2": u01qb08.scene_policy.digest({"scene_ref_id": ref}),
                "situation_family": CANONICAL_FAMILY[ref],
                "setting": str(context["setting"]),
                "micro_scene_event_id": str(context["title"]),
                "scene_origin": "CANONICAL_UNIT01_CONTEXT",
            }
        )
    supplement = json.loads(u01qb07.DEFAULT_SPEC.read_text(encoding="utf-8"))
    for candidate in u01qb07.candidates(supplement):
        ref = str(candidate["candidate_id"])
        rows.append(
            {
                "scene_ref_id": ref,
                "semantic_scene_signature_v2": u01qb08.scene_policy.digest({"scene_ref_id": ref}),
                "situation_family": str(candidate["large_situation_family"]),
                "setting": str(candidate["medium_setting"]),
                "micro_scene_event_id": str(candidate["small_micro_scene_event"]),
                "scene_origin": "MODEL_AUTHORED_SCENE_ENRICHMENT",
            }
        )
    if len(rows) != EXPECTED_SCENE_WORLD_COUNT:
        raise ContextStratifiedFullFixError(f"SCENE_WORLD_COUNT_INVALID:{len(rows)}")
    fake_approved = {
        "artifact_sha256": "u01qb15-static-scene-authority",
        "artifact_role": "APPROVED_CANONICAL_JSON",
        "payload": {"task_id": u01qb07.TASK_ID},
    }
    original = u01qb08.approved_scene_rows
    try:
        u01qb08.approved_scene_rows = lambda _approved: deepcopy(rows)
        return u01qb08.build_rotation(fake_approved)
    finally:
        u01qb08.approved_scene_rows = original


def _base_catalog(items: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_skill: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_skill[str(item["skill"])].append(
            {
                "item_id": str(item["item_id"]),
                "skill": str(item["skill"]),
                "pattern_family_id": str(item["pattern_family_id"]),
                "private_item_json": canonical(item),
            }
        )
    return dict(by_skill)


def base_only_scene_runtime_capacity_proof(
    items: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Run the U01QB14R1 solver against only the final 288 canonical base items."""
    if len(items) != EXPECTED_BASE_COUNT:
        raise ContextStratifiedFullFixError(f"BASE_ITEM_COUNT_INVALID:{len(items)}")
    rotation = u01qb14r1.rematerialize_rotation(_legacy_rotation_from_authorities())
    semantics = u01qb14r1.tolerant_scene_semantic_index()
    catalog = _base_catalog(items)
    prior_angles: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    session_count = 0
    activity_count = 0
    support_counts: Counter[str] = Counter()

    for form in rotation["forms"]:
        support = u01qb09.support_for_form(int(form["form_ordinal"]))
        support_counts[support] += 1
        scene_infos: list[dict[str, Any]] = []
        for slot in form["scene_slots"]:
            ref = str(slot["scene_ref_id"])
            semantic = semantics.get(ref)
            anchors = {
                str(value).casefold()
                for value in (semantic or {}).get("anchors") or []
            }
            if not anchors:
                raise ContextStratifiedFullFixError(f"CAPACITY_SCENE_ANCHORS_MISSING:{ref}")
            scene_infos.append(
                {
                    "scene_ref_id": ref,
                    "anchors": anchors,
                    "situation_family": str(slot["situation_family"]),
                }
            )

        for skill in ("READING", "WRITING", "SPEAKING"):
            chosen = runtime_patch._solve_form_skill(
                support=support,
                skill=skill,
                scene_infos=scene_infos,
                prior_angles=prior_angles,
                catalog=catalog,
            )
            expected_per_scene = 1 if skill == "SPEAKING" else 2
            for scene in scene_infos:
                ref = str(scene["scene_ref_id"])
                angles = tuple(chosen[ref])
                if len(angles) != expected_per_scene:
                    raise ContextStratifiedFullFixError(
                        f"CAPACITY_ANGLE_COUNT_INVALID:{form['form_id']}:{ref}:{skill}"
                    )
                prior_angles[ref][skill].update(angles)
                activity_count += len(angles)
            session_count += 1

    projection = rotation["runtime_bindability_projection"]
    if (
        projection["cumulative_scene_world_count"] != EXPECTED_SCENE_WORLD_COUNT
        or projection["unit_runtime_bindable_scene_count"] != EXPECTED_BINDABLE_SCENE_COUNT
        or tuple(projection["deferred_scene_refs"]) != EXPECTED_DEFERRED_SCENES
    ):
        raise ContextStratifiedFullFixError("SCENE_PROJECTION_DENOMINATOR_INVALID")
    if session_count != EXPECTED_SKILL_SESSION_COUNT or activity_count != EXPECTED_ACTIVITY_COUNT:
        raise ContextStratifiedFullFixError(
            f"BASE_CAPACITY_DENOMINATOR_INVALID:{session_count}:{activity_count}"
        )
    return {
        "proof_mode": "FINAL_288_BASE_ONLY_NO_REAL62_ASSISTANCE",
        "base_item_count": len(items),
        "cumulative_scene_world_count": EXPECTED_SCENE_WORLD_COUNT,
        "runtime_bindable_scene_count": EXPECTED_BINDABLE_SCENE_COUNT,
        "deferred_scene_refs": list(EXPECTED_DEFERRED_SCENES),
        "form_count": EXPECTED_FORM_COUNT,
        "skill_session_count": session_count,
        "verified_activity_count": activity_count,
        "all_36_skill_sessions_distinct_item_capacity_proven": True,
        "real62_used_for_capacity_proof": False,
        "support_form_counts": dict(sorted(support_counts.items())),
    }


def _context_family_counts(items: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    families = {
        *READING_REPLACEMENT_FAMILIES,
        u01qb12.PF16,
        WRITING_CONTEXT_REPLACEMENT_FAMILY,
        u01qb10.PF13,
        u01qb10.PF14,
        u01qb10.PF15,
    }
    result: dict[str, Counter[str]] = defaultdict(Counter)
    for item in items:
        family = str(item["pattern_family_id"])
        if family not in families:
            continue
        context_id, _noun = _pair_key(item)
        if context_id:
            result[family][context_id] += 1
    return {
        family: dict(sorted(counts.items()))
        for family, counts in sorted(result.items())
    }


def build_payload() -> dict[str, Any]:
    with context_stratified_policy():
        u10_approved, u10_items = u01qb10.seed_bank()[0], u01qb10.seed_bank()[1]
        replacements = u01qb10._replacement_sources(u10_items)
        u12_approved, final_items = u01qb12.approved_bank()

    retired_pairs_by_family = {
        family: [_pair_key(row) for row in rows]
        for family, rows in replacements.items()
    }
    reading_retired_pairs = [
        pair
        for family in READING_REPLACEMENT_FAMILIES
        for pair in retired_pairs_by_family[family]
    ]
    if len(reading_retired_pairs) != len(set(reading_retired_pairs)):
        raise ContextStratifiedFullFixError("READING_CONTEXT_NOUN_RETIREMENT_OVERLAP")

    capacity = base_only_scene_runtime_capacity_proof(final_items)
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "bank_identity": {
            "bank_id": BANK_ID,
            "bank_version": BANK_VERSION,
            "canonical_revision": CANONICAL_REVISION,
            "supersedes_selection_policy": [u01qb10.CANONICAL_REVISION, u01qb12.CANONICAL_REVISION],
            "historical_task_identity_rewritten": False,
            "second_question_bank_created": False,
        },
        "source_identity": {
            "u01qb10_task_id": u01qb10.TASK_ID,
            "u01qb12_task_id": u01qb12.TASK_ID,
            "u01qb12_context_stratified_artifact_sha256": str(u12_approved["artifact_sha256"]),
        },
        "count_preservation": {
            "base_item_count": len(final_items),
            "unchanged_real62_extension_count": EXPECTED_EXTENSION_COUNT,
            "projected_runtime_total_count": EXPECTED_RUNTIME_COUNT,
        },
        "u01qb10_context_stratified_replacement": {
            "replacement_count_per_family": CONTEXT_REPLACEMENT_COUNT,
            "context_quota": deepcopy(U01QB10_CONTEXT_QUOTA),
            "reading_family_ids": list(READING_REPLACEMENT_FAMILIES),
            "reading_retired_context_noun_pairs_unique": True,
            "reading_retired_pair_count": len(reading_retired_pairs),
            "replacement_source_ids_by_family": {
                family: [str(row["item_id"]) for row in rows]
                for family, rows in replacements.items()
            },
        },
        "u01qb12_context_stratified_reference_replacement": {
            "replacement_count": REFERENCE_REPLACEMENT_COUNT,
            "context_quota": deepcopy(U01QB12_REFERENCE_CONTEXT_QUOTA),
            "replacement_family_id": u01qb12.PF16,
        },
        "context_family_distribution": _context_family_counts(final_items),
        "per_scene_runtime_capacity": capacity,
        "reconciled_items": [deepcopy(dict(row)) for row in final_items],
        "boundaries": {
            "question_bank_total_expanded": False,
            "real62_extension_modified": False,
            "new_scene_authored": False,
            "second_planner_created": False,
            "second_runtime_created": False,
            "parallel_database_created": False,
            "parallel_scoring_created": False,
            "speaking_capture_enabled": False,
            "speaking_scoring_enabled": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    payload["reconciliation_sha256"] = policy_artifact.digest(payload)
    return payload


def build_candidate() -> dict[str, Any]:
    payload = build_payload()
    return policy_artifact.build_candidate(
        payload=payload,
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings={
            "u01qb10_task_id": u01qb10.TASK_ID,
            "u01qb12_task_id": u01qb12.TASK_ID,
            "canonical_revision": CANONICAL_REVISION,
            "count_preserving": True,
            "operator_decision_ref": DECISION_REF,
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import validate_a1fs_v1_u01qb15_unit01_context_stratified_question_bank_replacement_and_per_scene_runtime_capacity_fullfix as validator

    receipt = validator.validate_candidate(candidate)
    return policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[receipt],
        decision_ref=DECISION_REF,
        producer_id=TASK_ID,
    )


def migrate_fresh_legacy_runtime(database: Path) -> dict[str, Any]:
    """Run U01QB11→U01QB12 under the U01QB15 superseding selection policy."""
    database = Path(database)
    with context_stratified_policy():
        result = u01qb12.migrate_runtime(database)
        replay = u01qb12.replay_474(database)
        _approved, desired_items = u01qb12.approved_bank()

    desired_by_id = {str(row["item_id"]): row for row in desired_items}
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT item_id,item_digest FROM u01qb02_item_catalog ORDER BY item_id"
        ).fetchall()
        extension_ids = {
            str(row[0])
            for row in connection.execute("SELECT item_id FROM razq01e_extension_items")
        }
        active_base_ids = {str(row["item_id"]) for row in rows} - extension_ids
        if active_base_ids != set(desired_by_id):
            raise ContextStratifiedFullFixError("POST_MIGRATION_BASE_IDENTITY_SET_INVALID")
        if len(rows) != EXPECTED_RUNTIME_COUNT or len(extension_ids) != EXPECTED_EXTENSION_COUNT:
            raise ContextStratifiedFullFixError("POST_MIGRATION_RUNTIME_DENOMINATOR_INVALID")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS u01qb15_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)"
        )
        connection.executemany(
            "INSERT OR REPLACE INTO u01qb15_metadata(key,value) VALUES(?,?)",
            {
                "task_id": TASK_ID,
                "schema_version": SCHEMA_VERSION,
                "validation_status": PASS_STATUS,
                "canonical_revision": CANONICAL_REVISION,
                "base_item_count": str(EXPECTED_BASE_COUNT),
                "extension_item_count": str(EXPECTED_EXTENSION_COUNT),
                "runtime_item_count": str(EXPECTED_RUNTIME_COUNT),
                "next_short_step": NEXT_SHORT_STEP,
            }.items(),
        )
    capacity = base_only_scene_runtime_capacity_proof(desired_items)
    return {
        "validation_status": PASS_STATUS,
        "database": str(database),
        "u01qb12_migration": result,
        "u01qb12_replay": replay,
        "base_item_count": EXPECTED_BASE_COUNT,
        "extension_item_count": EXPECTED_EXTENSION_COUNT,
        "runtime_item_count": EXPECTED_RUNTIME_COUNT,
        "per_scene_runtime_capacity": capacity,
        "real62_extension_modified": False,
        "next_short_step": NEXT_SHORT_STEP,
    }


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    if private:
        try:
            path.chmod(0o600)
        except OSError:
            pass


def materialize(
    *,
    candidate_path: Path,
    approved_path: Path,
    report_path: Path,
    database: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidate = build_candidate()
    approved = admit_candidate(candidate)
    from ulga.validators import validate_a1fs_v1_u01qb15_unit01_context_stratified_question_bank_replacement_and_per_scene_runtime_capacity_fullfix as validator

    approval = validator.validate_approved(candidate, approved)
    if approval["error_count"]:
        raise ContextStratifiedFullFixError(
            "U01QB15_APPROVED_INVALID:" + "|".join(approval["errors"])
        )
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "approved_artifact_sha256": str(approved["artifact_sha256"]),
        "approval_validation": approval,
        "runtime_migration_executed": database is not None,
        "runtime_migration": migrate_fresh_legacy_runtime(database) if database is not None else None,
        "next_short_step": NEXT_SHORT_STEP,
    }
    write_json(candidate_path, candidate, private=True)
    write_json(approved_path, approved, private=True)
    write_json(report_path, report)
    return candidate, approved, report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--approved", type=Path, default=DEFAULT_APPROVED)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--database", type=Path)
    args = parser.parse_args(argv)
    try:
        _candidate, approved, report = materialize(
            candidate_path=args.candidate.resolve(),
            approved_path=args.approved.resolve(),
            report_path=args.report.resolve(),
            database=args.database.resolve(strict=True) if args.database else None,
        )
    except Exception as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB15_CONTEXT_STRATIFIED_QUESTION_BANK_FULLFIX")
        print(f"ERROR={exc}")
        return 1
    payload = approved["payload"]
    capacity = payload["per_scene_runtime_capacity"]
    print(f"STATUS={PASS_STATUS}")
    print(f"BASE_ITEMS={payload['count_preservation']['base_item_count']}")
    print(f"PROJECTED_RUNTIME_TOTAL={payload['count_preservation']['projected_runtime_total_count']}")
    print("U01QB10_CONTEXT_QUOTA=" + canonical(payload["u01qb10_context_stratified_replacement"]["context_quota"]))
    print("U01QB12_REFERENCE_CONTEXT_QUOTA=" + canonical(payload["u01qb12_context_stratified_reference_replacement"]["context_quota"]))
    print(f"BASE_ONLY_SKILL_SESSIONS_PROVEN={capacity['skill_session_count']}")
    print(f"BASE_ONLY_ACTIVITIES_PROVEN={capacity['verified_activity_count']}")
    print(f"RUNTIME_MIGRATION_EXECUTED={report['runtime_migration_executed']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
