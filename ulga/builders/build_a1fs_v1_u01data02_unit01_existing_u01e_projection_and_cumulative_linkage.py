#!/usr/bin/env python3
"""Link the cumulative Unit01 registry to existing U01E contexts, sentences, and activities."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as contract_builder
from ulga.builders import build_a1fs_v1_u01data01_unit01_cumulative_reusable_language_asset_registry as u01data01
from ulga.builders import build_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission as s01
from ulga.builders import build_a1fs_online_v1_2_u01e_s02_question_generation_context_pack as s02
from ulga.builders import build_a1fs_online_v1_2_u01e_s03_fixed_multitype_item_bank as s03

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Creates reference-only linkage and exact canonical chunk alias reconciliation across the approved Unit01 registry and existing admitted U01E identities; it copies no learner-facing question text or answers and creates no new content, scoring, state, audio, A2 target, or parallel bank."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01DATA02_Unit01ExistingU01ELanguageSentenceQuestionProjectionAndCumulativeLinkage"
SCHEMA_VERSION = "a1fs.v1.u01data02.unit01_existing_u01e_projection_cumulative_linkage.v2"
PASS_STATUS = "PASS_A1FS_V1_U01DATA02_UNIT01_EXISTING_U01E_PROJECTION_AND_CUMULATIVE_LINKAGE"
UNIT_ID = u01data01.UNIT_ID
DEFAULT_CONTRACT = u01data01.DEFAULT_CONTRACT
DEFAULT_APPROVAL = u01data01.DEFAULT_APPROVAL
DEFAULT_OUTPUT = Path("ulga/graph/a1fs_v1_u01data02_unit01_existing_u01e_projection_and_cumulative_linkage.json")
NEXT_SHORT_STEP = "A1FS-V1-U01DATA03_Unit01CumulativeDataWorkbookAndJsonExport"
FUTURE_ROLES = u01data01.FUTURE_ROLES
EXPECTED_CANONICAL_CHUNK_ALIAS_IDS = (
    "chunk:cd_player",
    "chunk:ice_cream",
    "chunk:living_room",
)
WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?")


class ProjectionBuildError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def normalized(value: Any) -> str:
    return " ".join(WORD_RE.findall(str(value).casefold().replace("’", "'")))


def contains_phrase(text: str, phrase: str) -> bool:
    return f" {normalized(phrase)} " in f" {normalized(text)} "


def flatten_registry(registry: Mapping[str, Any]) -> list[dict[str, Any]]:
    groups = registry.get("asset_bindings") or {}
    result: list[dict[str, Any]] = []
    for group_name in ("vocabulary", "canonical_chunks", "instructional_phrases", "sentence_frames"):
        rows = groups.get(group_name) or []
        if not isinstance(rows, list):
            raise ProjectionBuildError(f"REGISTRY_GROUP_INVALID:{group_name}")
        result.extend(deepcopy(rows))
    return result


def registry_indexes(registry: Mapping[str, Any]) -> dict[str, Any]:
    rows = flatten_registry(registry)
    by_asset = {str(row["asset_id"]): row for row in rows}
    by_surface: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        surface = row.get("normalized_surface") or row.get("surface_form")
        if surface:
            by_surface.setdefault(normalized(surface), []).append(row)
    return {"rows": rows, "by_asset": by_asset, "by_surface": by_surface}


def binding_ids_for_text(text: str, indexes: Mapping[str, Any]) -> list[str]:
    matches: set[str] = set()
    for surface, rows in indexes["by_surface"].items():
        if surface and contains_phrase(text, surface):
            matches.update(str(row["binding_id"]) for row in rows)
    return sorted(matches)


def context_phrase_lookup(payload: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(row["phrase_id"]): str(row["label"])
        for row in payload.get("language_targets", {}).get("context_phrases", [])
        if isinstance(row, Mapping) and row.get("phrase_id") and row.get("label")
    }


def canonical_chunk_alias_lookup(payload: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in payload.get("language_targets", {}).get("canonical_chunks", []) or []:
        if not isinstance(row, Mapping) or not row.get("authority_id") or not row.get("label"):
            continue
        alias_id = str(row["authority_id"])
        label = str(row["label"])
        previous = result.get(alias_id)
        if previous is not None and normalized(previous) != normalized(label):
            raise ProjectionBuildError(f"CANONICAL_CHUNK_ALIAS_LABEL_CONFLICT:{alias_id}")
        result[alias_id] = label
    return result


def unique_canonical_chunk_candidate(label: str, indexes: Mapping[str, Any]) -> dict[str, Any] | None:
    candidates = [
        row
        for row in indexes["by_surface"].get(normalized(label), [])
        if row.get("asset_kind") == "CANONICAL_CHUNK"
    ]
    if len(candidates) > 1:
        raise ProjectionBuildError(f"CANONICAL_CHUNK_ALIAS_AMBIGUOUS:{normalized(label)}")
    return candidates[0] if candidates else None


def target_linkage(
    row: Mapping[str, Any],
    *,
    indexes: Mapping[str, Any],
    phrase_labels: Mapping[str, str],
    chunk_alias_labels: Mapping[str, str],
) -> dict[str, Any]:
    linked: set[str] = set()
    unlinked: set[str] = set()
    reconciliations: list[dict[str, str]] = []

    for target in row.get("target_evp_sense_ids", []) or []:
        target_id = str(target)
        registry_row = indexes["by_asset"].get(target_id)
        if registry_row:
            linked.add(str(registry_row["binding_id"]))
        else:
            unlinked.add(target_id)

    for target in row.get("target_chunk_ids", []) or []:
        target_id = str(target)
        registry_row = indexes["by_asset"].get(target_id)
        if registry_row:
            linked.add(str(registry_row["binding_id"]))
            continue
        alias_label = chunk_alias_labels.get(target_id)
        candidate = unique_canonical_chunk_candidate(alias_label, indexes) if alias_label else None
        if candidate:
            binding_id = str(candidate["binding_id"])
            linked.add(binding_id)
            reconciliations.append(
                {
                    "source_alias_id": target_id,
                    "source_label": alias_label,
                    "registry_asset_id": str(candidate["asset_id"]),
                    "registry_binding_id": binding_id,
                    "reconciliation_method": "EXACT_NORMALIZED_LABEL_UNIQUE_CANONICAL_CHUNK",
                }
            )
        else:
            unlinked.add(target_id)

    for phrase_id in row.get("target_context_phrase_ids", []) or []:
        label = phrase_labels.get(str(phrase_id))
        candidates = indexes["by_surface"].get(normalized(label), []) if label else []
        if candidates:
            linked.update(str(candidate["binding_id"]) for candidate in candidates)
        else:
            unlinked.add(str(phrase_id))

    return {
        "linked_registry_binding_ids": sorted(linked),
        "unlinked_external_support_target_ids": sorted(unlinked),
        "canonical_chunk_alias_reconciliations": sorted(
            reconciliations, key=lambda item: item["source_alias_id"]
        ),
        "linkage_status": (
            "LINKED_WITH_EXTERNAL_SUPPORT" if linked and unlinked
            else "LINKED_TO_CUMULATIVE_REGISTRY" if linked
            else "UNLINKED_EXTERNAL_SUPPORT_ONLY"
        ),
    }


def build_context_and_sentence_projections(
    payload: Mapping[str, Any], indexes: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sentence_rows = payload.get("language_targets", {}).get("sentences", [])
    by_context: dict[str, list[dict[str, Any]]] = {}
    sentence_projections: list[dict[str, Any]] = []
    for row in sentence_rows:
        text = str(row["text"])
        projection = {
            "sentence_id": str(row["sentence_id"]),
            "context_id": str(row["context_id"]),
            "introduced_unit_id": UNIT_ID,
            "introduced_unit_sequence": 1,
            "available_from_unit_sequence": 1,
            "source_task_id": s01.TASK_ID,
            "source_role": str(row["source_role"]),
            "learning_role": str(row["learning_role"]),
            "linked_registry_binding_ids": binding_ids_for_text(text, indexes),
            "future_unit_reference_allowed": True,
            "copy_on_reuse": False,
            "eligible_future_unit_roles": list(FUTURE_ROLES),
            "text_ownership": "S01_APPROVED_LANGUAGE_TARGET",
        }
        sentence_projections.append(projection)
        by_context.setdefault(projection["context_id"], []).append(projection)
    contexts: list[dict[str, Any]] = []
    for row in payload.get("contexts", []):
        context_id = str(row["context_id"])
        sentences = by_context.get(context_id, [])
        contexts.append(
            {
                "context_id": context_id,
                "introduced_unit_id": UNIT_ID,
                "introduced_unit_sequence": 1,
                "available_from_unit_sequence": 1,
                "context_role": str(row["role"]),
                "setting": str(row["setting"]),
                "source_role": str(row["source_role"]),
                "sentence_ids": [sentence["sentence_id"] for sentence in sentences],
                "linked_registry_binding_ids": sorted(
                    {binding for sentence in sentences for binding in sentence["linked_registry_binding_ids"]}
                ),
                "future_unit_reference_allowed": True,
                "copy_on_reuse": False,
                "eligible_future_unit_roles": list(FUTURE_ROLES),
                "content_ownership": "S01_APPROVED_CONTEXT",
            }
        )
    return sorted(contexts, key=lambda row: row["context_id"]), sorted(
        sentence_projections, key=lambda row: row["sentence_id"]
    )


def existing_activity_projections(
    safe_pack: Mapping[str, Any],
    indexes: Mapping[str, Any],
    phrase_labels: Mapping[str, str],
    chunk_alias_labels: Mapping[str, str],
) -> list[dict[str, Any]]:
    result = []
    for row in safe_pack.get("existing_asset_target_index", []):
        linkage = target_linkage(
            row,
            indexes=indexes,
            phrase_labels=phrase_labels,
            chunk_alias_labels=chunk_alias_labels,
        )
        result.append(
            {
                "activity_id": str(row["asset_key"]),
                "activity_source": "EXISTING_RESPONSE_CONTRACT",
                "activity_owner_task_id": s01.m01.TASK_ID,
                "lesson_id": str(row["lesson_id"]),
                "skill": str(row["skill"]),
                "question_type": str(row["question_type"]),
                "context_id": str(row["context_id"]),
                "target_sentence_ids": sorted(str(value) for value in row.get("target_sentence_ids", [])),
                "target_pattern_ids": sorted(str(value) for value in row.get("target_pattern_ids", [])),
                "target_egp_row_ids": sorted(str(value) for value in row.get("target_egp_row_ids", [])),
                "introduced_unit_id": UNIT_ID,
                "introduced_unit_sequence": 1,
                "future_unit_reference_allowed": True,
                "copy_on_reuse": False,
                "eligible_future_unit_roles": list(FUTURE_ROLES),
                "content_copied_into_projection": False,
                "answer_contract_copied_into_projection": False,
                "canonical_activity_identity_preserved": True,
                **linkage,
            }
        )
    return sorted(result, key=lambda row: row["activity_id"])


def fixed_item_projections(
    approved_bank: Mapping[str, Any],
    indexes: Mapping[str, Any],
    phrase_labels: Mapping[str, str],
    chunk_alias_labels: Mapping[str, str],
) -> list[dict[str, Any]]:
    payload = approved_bank.get("payload") or {}
    result = []
    for row in payload.get("candidate_items", []):
        linkage = target_linkage(
            row,
            indexes=indexes,
            phrase_labels=phrase_labels,
            chunk_alias_labels=chunk_alias_labels,
        )
        result.append(
            {
                "activity_id": str(row["candidate_item_id"]),
                "activity_source": "U01E_S03_FIXED_ADMITTED_ITEM_BANK",
                "activity_owner_task_id": s03.TASK_ID,
                "item_bank_id": str(payload["item_bank_id"]),
                "item_bank_version": str(payload["item_bank_version"]),
                "skill": str(row["skill"]),
                "question_type": str(row["question_type"]),
                "learning_role": str(row["learning_role"]),
                "support_level": str(row["support_level"]),
                "context_id": str(row["context_id"]),
                "target_sentence_ids": sorted(str(value) for value in row.get("target_sentence_ids", [])),
                "target_pattern_ids": sorted(str(value) for value in row.get("target_pattern_ids", [])),
                "target_egp_row_ids": sorted(str(value) for value in row.get("target_egp_row_ids", [])),
                "semantic_signature": str(row["semantic_signature"]),
                "introduced_unit_id": UNIT_ID,
                "introduced_unit_sequence": 1,
                "future_unit_reference_allowed": True,
                "copy_on_reuse": False,
                "eligible_future_unit_roles": list(FUTURE_ROLES),
                "content_copied_into_projection": False,
                "answer_contract_copied_into_projection": False,
                "canonical_activity_identity_preserved": True,
                **linkage,
            }
        )
    return sorted(result, key=lambda row: row["activity_id"])


def build_projection(
    *, database_path: Path, contract: Mapping[str, Any], approval: Mapping[str, Any]
) -> dict[str, Any]:
    registry = u01data01.build_registry(contract, approval)
    indexes = registry_indexes(registry)
    s01_candidate = s01.build_candidate(database_path)
    s01_approved = s01.admit_candidate(s01_candidate)
    safe_pack = s02.build_safe_pack(s01_approved)
    s03_candidate, s03_safe_pack = s03.build_candidate(database_path)
    if s03_safe_pack.get("pack_sha256") != safe_pack.get("pack_sha256"):
        raise ProjectionBuildError("S02_SAFE_PACK_NONDETERMINISTIC")
    s03_approved = s03.admit_candidate(s03_candidate, s03_safe_pack)
    payload = s01_approved["payload"]
    phrase_labels = context_phrase_lookup(payload)
    chunk_alias_labels = canonical_chunk_alias_lookup(payload)
    contexts, sentences = build_context_and_sentence_projections(payload, indexes)
    existing = existing_activity_projections(safe_pack, indexes, phrase_labels, chunk_alias_labels)
    fixed = fixed_item_projections(s03_approved, indexes, phrase_labels, chunk_alias_labels)
    activities = existing + fixed
    skill_counts = dict(sorted(Counter(row["skill"] for row in activities).items()))
    status_counts = dict(sorted(Counter(row["linkage_status"] for row in activities).items()))
    unlinked_support = sorted(
        {target for row in activities for target in row["unlinked_external_support_target_ids"]}
    )
    alias_by_id: dict[str, dict[str, str]] = {}
    for row in activities:
        for reconciliation in row["canonical_chunk_alias_reconciliations"]:
            alias_id = reconciliation["source_alias_id"]
            previous = alias_by_id.get(alias_id)
            if previous is not None and previous != reconciliation:
                raise ProjectionBuildError(f"CANONICAL_CHUNK_ALIAS_RECONCILIATION_CONFLICT:{alias_id}")
            alias_by_id[alias_id] = reconciliation
    expected_aliases = set(EXPECTED_CANONICAL_CHUNK_ALIAS_IDS)
    if set(alias_by_id) != expected_aliases:
        raise ProjectionBuildError(
            "CANONICAL_CHUNK_ALIAS_RECONCILIATION_INCOMPLETE:"
            f"expected={sorted(expected_aliases)}:actual={sorted(alias_by_id)}"
        )
    if expected_aliases & set(unlinked_support):
        raise ProjectionBuildError("RECONCILED_CANONICAL_CHUNK_ALIAS_REMAINS_EXTERNAL_SUPPORT")
    if any(not row["linked_registry_binding_ids"] for row in activities):
        missing = next(row["activity_id"] for row in activities if not row["linked_registry_binding_ids"])
        raise ProjectionBuildError(f"ACTIVITY_WITHOUT_CUMULATIVE_REGISTRY_LINK:{missing}")
    core = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit": {"unit_id": UNIT_ID, "unit_sequence": 1, "level_scope": ["A1"]},
        "source_identity": {
            "u01data01_task_id": u01data01.TASK_ID,
            "u01data01_registry_sha256": registry["registry_sha256"],
            "s01_task_id": s01.TASK_ID,
            "s01_approved_sha256": s01_approved["artifact_sha256"],
            "s02_task_id": s02.TASK_ID,
            "s02_safe_pack_sha256": safe_pack["pack_sha256"],
            "s03_task_id": s03.TASK_ID,
            "s03_approved_sha256": s03_approved["artifact_sha256"],
            "s03_item_bank_id": s03_approved["payload"]["item_bank_id"],
            "s03_item_bank_version": s03_approved["payload"]["item_bank_version"],
        },
        "ownership_contract": {
            "language_asset_authority": "U01DATA01_REGISTRY_PLUS_EXISTING_CANONICAL_AUTHORITIES",
            "context_and_sentence_owner": s01.TASK_ID,
            "existing_activity_owner": s01.m01.TASK_ID,
            "fixed_item_bank_owner": s03.TASK_ID,
            "projection_creates_parallel_content": False,
            "projection_copies_question_or_answer_content": False,
            "later_units_reference_existing_ids": True,
            "later_units_copy_records": False,
        },
        "registry_summary": deepcopy(registry["denominators"]),
        "context_projections": contexts,
        "sentence_asset_projections": sentences,
        "activity_projections": {
            "existing_response_contract_activities": existing,
            "fixed_admitted_items": fixed,
        },
        "linkage_summary": {
            "context_count": len(contexts),
            "sentence_asset_count": len(sentences),
            "existing_activity_count": len(existing),
            "fixed_admitted_item_count": len(fixed),
            "total_activity_count": len(activities),
            "activity_count_by_skill": skill_counts,
            "activity_linkage_status_counts": status_counts,
            "activity_asset_link_count": sum(len(row["linked_registry_binding_ids"]) for row in activities),
            "unique_activity_linked_registry_binding_count": len(
                {binding for row in activities for binding in row["linked_registry_binding_ids"]}
            ),
            "canonical_chunk_alias_reconciliation_status": "PASS_EXACT_NORMALIZED_LABEL_TO_SINGLE_CANONICAL_CHUNK_BINDING",
            "canonical_chunk_alias_reconciled_target_count": len(alias_by_id),
            "canonical_chunk_alias_reconciliations": [alias_by_id[key] for key in sorted(alias_by_id)],
            "unlinked_external_support_target_ids": unlinked_support,
            "unlinked_external_support_is_promoted_to_registry": False,
            "canonical_pattern_to_unit_frame_bridge_status": "UNRESOLVED_RECORDED_NOT_INFERRED",
        },
        "cumulative_reuse_contract": {
            "sentence_assets_reusable_from_unit_sequence": 1,
            "activity_identities_reusable_from_unit_sequence": 1,
            "future_unit_roles": list(FUTURE_ROLES),
            "selection_requires_new_unit_compatibility_gate": True,
            "selection_requires_learner_state_or_scheduled_review_reason": True,
            "full_cumulative_pool_may_not_be_assigned_as_one_lesson": True,
        },
        "boundaries": {
            "unit02_to_unit24_modified": False,
            "new_question_bank_created": False,
            "new_sentence_text_created": False,
            "question_content_copied": False,
            "answer_content_copied": False,
            "learner_database_written": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
            "parallel_curriculum_created": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    core["projection_sha256"] = digest(core)
    return core


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProjectionBuildError(f"UNREADABLE_JSON:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ProjectionBuildError(f"OBJECT_REQUIRED:{path}")
    return value


def run(*, database_path: Path, contract_path: Path, approval_path: Path, output_path: Path) -> dict[str, Any]:
    report = build_projection(
        database_path=database_path,
        contract=_load(contract_path),
        approval=_load(approval_path),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--approval", type=Path, default=DEFAULT_APPROVAL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        report = run(
            database_path=args.database.resolve(),
            contract_path=args.contract.resolve(),
            approval_path=args.approval.resolve(),
            output_path=args.output.resolve(),
        )
    except (ProjectionBuildError, ValueError, KeyError, TypeError, OSError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01DATA02_UNIT01_EXISTING_U01E_PROJECTION_AND_CUMULATIVE_LINKAGE")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={report['status']}")
    for key, value in report["linkage_summary"].items():
        if isinstance(value, (str, int, bool)):
            print(f"{key.upper()}={value}")
    print(f"PROJECTION_SHA256={report['projection_sha256']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
