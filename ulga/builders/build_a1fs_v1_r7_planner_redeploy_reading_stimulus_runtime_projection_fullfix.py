#!/usr/bin/env python3
"""Build and apply a runtime-only Reading stimulus projection for R7 Planner redeployments.

The active R4 bank remains canonical and unchanged. This module binds each selected
R7 deployment to its exact admitted R4 item and, when a Reading short-text item has
no learner-visible source, projects the exact M2 asset payload into the learner
contract. The projection is applied to the existing R5 SQLite runtime as a reversible
private delivery overlay; it does not create a second R4 bank or learner evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import sqlite3
import tempfile
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2
from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5
from ulga.builders import build_a1fs_v1_r7_route_batch_execution_and_replay_closure as r7
from ulga.builders import build_a1fs_v1_shared_learner_stimulus_contract_renderer as stimulus

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "RUNTIME_ONLY_DELIVERY_OVERLAY_FROM_EXISTING_APPROVED_R4_AND_EXACT_M2_CONTENT"

TASK_ID = "A1FS-V1-R7_PlannerRedeploy198ReadingStimulusRuntimeProjectionFullFix"
SCHEMA_VERSION = "a1fs.v1.r7.reading_stimulus_runtime_projection.v1"
SAFE_SCHEMA_VERSION = "a1fs.v1.r7.reading_stimulus_runtime_projection_safe.v1"
SESSION_SCHEMA_VERSION = "a1fs.v1.r7.projected_real_learner_session_batch.v1"
SESSION_SAFE_SCHEMA_VERSION = "a1fs.v1.r7.projected_real_learner_session_batch_safe.v1"
STATUS = "PASS_R7_READING_STIMULUS_RUNTIME_PROJECTION_READY"
NEXT_SHORT_STEP = r7.TASK_ID

PROJECTION_FILENAME = "a1fs_v1_r7_reading_stimulus_runtime_projection.private.json"
SAFE_FILENAME = "a1fs_v1_r7_reading_stimulus_runtime_projection.safe.json"
SESSION_FILENAME = "a1fs_v1_r7_projected_real_learner_session_batch.private.json"
SESSION_SAFE_FILENAME = "a1fs_v1_r7_projected_real_learner_session_batch.safe.json"

VISIBLE_SOURCE_KINDS = {"TEXT", "DIALOGUE", "TABLE", "IMAGE"}
FORBIDDEN_SOURCE_PATH_PARTS = {
    "teacher", "answer", "accepted", "rubric", "expected", "acceptance",
    "diagnostic", "scaffold", "failure", "solution", "key", "target_refs",
    "supporting_target_refs", "resource_refs", "candidate_resource_refs",
}
SOURCE_PATH_PRIORITY: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("TEXT", ("source_text",)),
    ("TEXT", ("body_text",)),
    ("TEXT", ("reading_text",)),
    ("TEXT", ("unseen_text",)),
    ("TEXT", ("learner_text",)),
    ("TEXT", ("passage",)),
    ("TEXT", ("notice",)),
    ("TEXT", ("message",)),
    ("TEXT", ("email",)),
    ("TEXT", ("postcard",)),
    ("TEXT", ("announcement",)),
    ("TEXT", ("advertisement",)),
    ("TEXT", ("paragraph",)),
    ("TEXT", ("story",)),
    ("TEXT", ("text",)),
    ("DIALOGUE", ("dialogue",)),
    ("DIALOGUE", ("conversation",)),
    ("DIALOGUE", ("turns",)),
    ("TABLE", ("table",)),
    ("TABLE", ("rows",)),
    ("TABLE", ("schedule",)),
    ("TABLE", ("timetable",)),
    ("TEXT", ("prompt",)),
)
NESTED_SOURCE_ROOTS = ("learner", "student", "stimulus", "content", "source", "body")


class RuntimeProjectionError(ValueError):
    """Fail-closed runtime projection error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeProjectionError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeProjectionError(f"{code}_not_object")
    return value


def atomic_json(path: Path, value: Mapping[str, Any], *, private: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        if private:
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def _owned_digest(value: Mapping[str, Any], field: str) -> str:
    actual = value.get(field)
    if not isinstance(actual, str) or len(actual) != 64:
        raise RuntimeProjectionError(f"owned_digest_missing:{field}")
    expected = digest({key: child for key, child in value.items() if key != field})
    if actual != expected:
        raise RuntimeProjectionError(f"owned_digest_invalid:{field}")
    return actual


def _nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return bool(value) and any(_nonempty(child) for child in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return bool(value) and any(_nonempty(child) for child in value)
    return value is not None


def _get_path(value: Mapping[str, Any], path: Sequence[str]) -> Any:
    current: Any = value
    for part in path:
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _prefixed(values: Any, prefix: str, *, item_id: str, required: bool = True) -> str | None:
    matches = [
        value[len(prefix):]
        for value in values
        if isinstance(value, str) and value.startswith(prefix)
    ] if isinstance(values, list) else []
    if not matches and not required:
        return None
    if len(matches) != 1 or not matches[0]:
        raise RuntimeProjectionError(f"source_ref_invalid:{item_id}:{prefix}")
    return matches[0]


def _asset_index(consumer: Mapping[str, Any]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    result: dict[tuple[str, str], list[dict[str, Any]]] = {}
    rows = consumer.get("asset_records")
    if not isinstance(rows, list):
        raise RuntimeProjectionError("m2_asset_records_missing")
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise RuntimeProjectionError("m2_asset_not_object")
        row = dict(raw)
        lesson_id = str(row.get("lesson_id") or "")
        identities = {str(row.get("asset_id") or ""), str(row.get("asset_key") or "")} - {""}
        for identity in identities:
            result.setdefault((identity, lesson_id), []).append(row)
    return result


def _source_dependencies(learner: Mapping[str, Any]) -> set[str]:
    return {
        str(row.get("kind"))
        for row in stimulus.derive_dependencies(learner)
        if str(row.get("kind")) in VISIBLE_SOURCE_KINDS
    }


def requires_reading_projection(item: Mapping[str, Any]) -> bool:
    learner = item.get("learner_contract")
    return (
        item.get("skill") == "READING"
        and isinstance(learner, Mapping)
        and learner.get("response_mode") == "short_text"
        and not _source_dependencies(learner)
    )


def _candidate_source_paths() -> list[tuple[str, tuple[str, ...]]]:
    rows: list[tuple[str, tuple[str, ...]]] = list(SOURCE_PATH_PRIORITY)
    for root in NESTED_SOURCE_ROOTS:
        rows.extend((kind, (root, *path)) for kind, path in SOURCE_PATH_PRIORITY)
    return rows


def extract_learner_source(payload: Mapping[str, Any], *, item_id: str) -> tuple[str, tuple[str, ...], Any]:
    if not isinstance(payload, Mapping) or not payload:
        raise RuntimeProjectionError(f"source_payload_not_object:{item_id}")
    for kind, path in _candidate_source_paths():
        if any(part.casefold() in FORBIDDEN_SOURCE_PATH_PARTS for part in path):
            continue
        value = _get_path(payload, path)
        if _nonempty(value):
            return kind, path, deepcopy(value)
    available = sorted(str(key) for key, value in payload.items() if _nonempty(value))
    raise RuntimeProjectionError(
        f"SOURCE_PAYLOAD_NOT_LEARNER_RENDERABLE:{item_id}:available={','.join(available)}"
    )


def resolve_learner_source(
    asset: Mapping[str, Any],
    *,
    assets: Mapping[tuple[str, str], list[dict[str, Any]]],
    lesson_id: str,
    item_id: str,
) -> tuple[str, tuple[str, ...], Any, Mapping[str, Any]]:
    payload = asset.get("payload")
    try:
        kind, path, source_payload = extract_learner_source(payload, item_id=item_id)
        return kind, path, source_payload, asset
    except RuntimeProjectionError as exc:
        if not str(exc).startswith("SOURCE_PAYLOAD_NOT_LEARNER_RENDERABLE:"):
            raise
        extraction_error = exc
    text_ref = payload.get("text_ref") if isinstance(payload, Mapping) else None
    if not isinstance(text_ref, str) or not text_ref.strip():
        raise extraction_error
    source_asset_id = f"{lesson_id}-{text_ref.strip()}"
    matches = [
        row for row in assets.get((source_asset_id, lesson_id), [])
        if row.get("skill") == "READING" and row.get("lesson_id") == lesson_id
    ]
    if len(matches) != 1:
        raise RuntimeProjectionError(
            f"m2_text_ref_resolution_failed:{item_id}:{source_asset_id}:{len(matches)}"
        )
    source_asset = matches[0]
    kind, path, source_payload = extract_learner_source(source_asset.get("payload"), item_id=item_id)
    return kind, ("text_ref", source_asset_id, *path), source_payload, source_asset


def _inject_source(learner: Mapping[str, Any], kind: str, payload: Any) -> dict[str, Any]:
    result = deepcopy(dict(learner))
    context = result.get("context")
    if context is None:
        context_value: dict[str, Any] = {}
    elif isinstance(context, Mapping):
        context_value = deepcopy(dict(context))
    else:
        context_value = {"existing_context": deepcopy(context)}
    field = {"TEXT": "source_text", "DIALOGUE": "dialogue", "TABLE": "table"}.get(kind)
    if field is None:
        raise RuntimeProjectionError(f"unsupported_projected_source_kind:{kind}")
    if field in context_value and _nonempty(context_value[field]):
        raise RuntimeProjectionError(f"projected_source_would_overwrite_existing:{field}")
    context_value[field] = deepcopy(payload)
    result["context"] = context_value
    return result


def _validate_sources(
    *, bank: Mapping[str, Any], deployment_queue: Mapping[str, Any], consumer: Mapping[str, Any],
    expected_deployment_count: int | None,
) -> tuple[list[Mapping[str, Any]], dict[str, Mapping[str, Any]], dict[tuple[str, str], list[dict[str, Any]]]]:
    bank_sha = _owned_digest(bank, "bank_sha256")
    deployment_sha = _owned_digest(deployment_queue, "deployment_queue_sha256")
    del deployment_sha
    if bank.get("private_local_only") is not True:
        raise RuntimeProjectionError("r4_bank_not_private")
    items = bank.get("items")
    deployments = deployment_queue.get("deployments")
    if not isinstance(items, list) or not isinstance(deployments, list):
        raise RuntimeProjectionError("bank_or_deployment_rows_missing")
    if expected_deployment_count is not None and len(deployments) != expected_deployment_count:
        raise RuntimeProjectionError(
            f"deployment_count_mismatch:{len(deployments)}:{expected_deployment_count}"
        )
    if deployment_queue.get("source_bindings", {}).get("r4_bank_sha256") != bank_sha:
        raise RuntimeProjectionError("deployment_r4_bank_binding_mismatch")
    if consumer.get("task_id") != m2.TASK_ID or consumer.get("schema_version") != m2.SCHEMA_VERSION:
        raise RuntimeProjectionError("m2_consumer_identity_invalid")
    if consumer.get("validation_status") != m2.STATUS:
        raise RuntimeProjectionError("m2_consumer_status_invalid")
    if consumer.get("claim_boundaries", {}).get("a2_unlocked") is True:
        raise RuntimeProjectionError("m2_a2_unlock_detected")
    if any(item.get("level") == "A2" for item in items if isinstance(item, Mapping)):
        raise RuntimeProjectionError("r4_a2_item_detected")
    bank_by_id = {
        str(item.get("item_id")): item
        for item in items
        if isinstance(item, Mapping) and item.get("item_id")
    }
    if len(bank_by_id) != len(items):
        raise RuntimeProjectionError("r4_item_identity_invalid")
    return deployments, bank_by_id, _asset_index(consumer)


def build_projection(
    *,
    bank: Mapping[str, Any],
    deployment_queue: Mapping[str, Any],
    consumer: Mapping[str, Any],
    bank_file_sha256: str | None = None,
    deployment_file_sha256: str | None = None,
    consumer_file_sha256: str | None = None,
    expected_deployment_count: int | None = 209,
    expected_projected_count: int | None = 198,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    deployments, bank_by_id, assets = _validate_sources(
        bank=bank,
        deployment_queue=deployment_queue,
        consumer=consumer,
        expected_deployment_count=expected_deployment_count,
    )
    rows: list[dict[str, Any]] = []
    work_ids: set[str] = set()
    item_ids: set[str] = set()
    projected_count = 0
    unique_assets: set[tuple[str, str, str]] = set()
    source_kind_counts: dict[str, int] = {}

    for deployment in deployments:
        if not isinstance(deployment, Mapping):
            raise RuntimeProjectionError("deployment_not_object")
        work_item_id = str(deployment.get("work_item_id") or "")
        item_id = str(deployment.get("selected_item_id") or "")
        if not work_item_id or work_item_id in work_ids:
            raise RuntimeProjectionError(f"work_item_identity_invalid:{work_item_id}")
        if not item_id or item_id in item_ids:
            raise RuntimeProjectionError(f"selected_item_identity_invalid:{item_id}")
        work_ids.add(work_item_id)
        item_ids.add(item_id)
        item = bank_by_id.get(item_id)
        if item is None:
            raise RuntimeProjectionError(f"selected_item_missing:{item_id}")
        if item.get("candidate_sha256") != deployment.get("selected_candidate_sha256", item.get("candidate_sha256")):
            raise RuntimeProjectionError(f"candidate_binding_mismatch:{item_id}")
        if item.get("stimulus_fingerprint") != deployment.get("selected_stimulus_fingerprint"):
            raise RuntimeProjectionError(f"stimulus_binding_mismatch:{item_id}")
        learner = item.get("learner_contract")
        scoring = item.get("private_scoring_contract")
        if not isinstance(learner, Mapping) or not isinstance(scoring, Mapping):
            raise RuntimeProjectionError(f"item_contract_missing:{item_id}")

        projection_applied = requires_reading_projection(item)
        m2_asset_id: str | None = None
        m2_lesson_id: str | None = None
        m2_content_digest: str | None = None
        source_m2_asset_id: str | None = None
        source_m2_content_digest: str | None = None
        source_payload_sha256: str | None = None
        source_path: list[str] | None = None
        if projection_applied:
            m2_asset_id = _prefixed(item.get("source_refs"), "M2_ASSET:", item_id=item_id)
            m2_lesson_id = _prefixed(item.get("source_refs"), "M2_LESSON:", item_id=item_id)
            m2_content_digest = _prefixed(item.get("authority_refs"), "M2_CONTENT_DIGEST:", item_id=item_id)
            matches = [
                row for row in assets.get((str(m2_asset_id), str(m2_lesson_id)), [])
                if row.get("skill") == "READING"
            ]
            if len(matches) != 1:
                raise RuntimeProjectionError(f"exact_m2_asset_resolution_failed:{item_id}:{len(matches)}")
            asset = matches[0]
            if asset.get("content_digest") != m2_content_digest:
                raise RuntimeProjectionError(f"m2_content_digest_mismatch:{item_id}")
            kind, path, source_payload, source_asset = resolve_learner_source(
                asset,
                assets=assets,
                lesson_id=str(m2_lesson_id),
                item_id=item_id,
            )
            projected_learner = _inject_source(learner, kind, source_payload)
            source_m2_asset_id = str(source_asset.get("asset_id") or source_asset.get("asset_key") or "")
            source_m2_content_digest = str(source_asset.get("content_digest") or "")
            if not source_m2_asset_id or len(source_m2_content_digest) != 64:
                raise RuntimeProjectionError(f"m2_source_asset_identity_invalid:{item_id}")
            source_payload_sha256 = digest(source_payload)
            source_path = list(path)
            unique_assets.add((str(m2_asset_id), str(m2_lesson_id), str(m2_content_digest)))
            projected_count += 1
        else:
            projected_learner = deepcopy(dict(learner))

        try:
            validated_learner = stimulus.ensure_learner_contract(
                item_id=item_id,
                task_type=str(item.get("task_type") or ""),
                learner=projected_learner,
                scoring=scoring,
                media_payload_state=str(item.get("media_payload_state") or "NOT_REQUIRED"),
            )
        except stimulus.StimulusContractError as exc:
            raise RuntimeProjectionError(f"projected_learner_not_answerable:{item_id}:{exc}") from exc
        kinds = sorted(_source_dependencies(validated_learner))
        if projection_applied and not (set(kinds) & {"TEXT", "DIALOGUE", "TABLE"}):
            raise RuntimeProjectionError(f"projected_source_not_visible:{item_id}")
        for kind in kinds:
            source_kind_counts[kind] = source_kind_counts.get(kind, 0) + 1

        delivery_core = {
            "task_id": TASK_ID,
            "work_item_id": work_item_id,
            "finding_id": deployment.get("finding_id"),
            "breadth_cell_id": deployment.get("breadth_cell_id"),
            "item_id": item_id,
            "canonical_candidate_sha256": item.get("candidate_sha256"),
            "canonical_stimulus_fingerprint": item.get("stimulus_fingerprint"),
            "projection_applied": projection_applied,
            "m2_asset_id": m2_asset_id,
            "m2_lesson_id": m2_lesson_id,
            "m2_content_digest": m2_content_digest,
            "source_m2_asset_id": source_m2_asset_id,
            "source_m2_content_digest": source_m2_content_digest,
            "source_payload_path": source_path,
            "source_payload_sha256": source_payload_sha256,
            "projected_learner_contract_sha256": digest(validated_learner),
            "stimulus_render_manifest_sha256": validated_learner.get("stimulus_render_manifest_sha256"),
            "source_dependency_kinds": kinds,
        }
        delivery_fingerprint = digest(delivery_core)
        runtime_binding = {
            "task_id": TASK_ID,
            "work_item_id": work_item_id,
            "delivery_fingerprint": delivery_fingerprint,
            "canonical_candidate_sha256": item.get("candidate_sha256"),
            "canonical_stimulus_fingerprint": item.get("stimulus_fingerprint"),
            "m2_asset_id": m2_asset_id,
            "m2_lesson_id": m2_lesson_id,
            "m2_content_digest": m2_content_digest,
            "projection_applied": projection_applied,
        }
        runtime_item = deepcopy(dict(item))
        runtime_item["learner_contract"] = validated_learner
        runtime_item["runtime_delivery_binding"] = runtime_binding
        rows.append({
            **delivery_core,
            "delivery_fingerprint": delivery_fingerprint,
            "delivery_contract_sha256": digest({
                "learner_contract": validated_learner,
                "runtime_delivery_binding": runtime_binding,
            }),
            "runtime_item_digest": r5.digest(runtime_item),
            "projected_learner_contract": validated_learner,
            "renderability_status": "LEARNER_RENDERABLE",
        })

    if expected_projected_count is not None and projected_count != expected_projected_count:
        raise RuntimeProjectionError(
            f"projected_count_mismatch:{projected_count}:{expected_projected_count}"
        )
    if len(rows) != len(deployments):
        raise RuntimeProjectionError("delivery_denominator_drift")

    source_bindings = {
        "r4_bank_sha256": bank["bank_sha256"],
        "r4_bank_file_sha256": bank_file_sha256 or digest(bank),
        "deployment_queue_sha256": deployment_queue["deployment_queue_sha256"],
        "deployment_queue_file_sha256": deployment_file_sha256 or digest(deployment_queue),
        "m2_consumer_file_sha256": consumer_file_sha256 or digest(consumer),
        "m2_source_graph_sha256": consumer.get("source_graph_sha256"),
    }
    counts = {
        "deployment_count": len(rows),
        "reading_deployment_count": sum(bank_by_id[row["item_id"]].get("skill") == "READING" for row in rows),
        "writing_deployment_count": sum(bank_by_id[row["item_id"]].get("skill") == "WRITING" for row in rows),
        "source_dependency_projection_count": projected_count,
        "base_contract_delivery_count": len(rows) - projected_count,
        "learner_renderable_count": len(rows),
        "learner_renderability_failure_count": 0,
        "unique_m2_reading_asset_count": len(unique_assets),
        "source_dependency_kind_counts": dict(sorted(source_kind_counts.items())),
        "synthetic_evidence_count": 0,
    }
    projection_core = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": STATUS,
        "private_local_only": True,
        "source_bindings": source_bindings,
        "counts": counts,
        "deliveries": rows,
        "claim_boundaries": {
            "canonical_r4_bank_modified": False,
            "candidate_identity_modified": False,
            "authority_review_modified": False,
            "m2_content_modified": False,
            "learner_evidence_generated": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    projection = {**projection_core, "projection_sha256": digest(projection_core)}
    safe_core = {
        "task_id": TASK_ID,
        "schema_version": SAFE_SCHEMA_VERSION,
        "validation_status": STATUS,
        "source_bindings": source_bindings,
        "counts": counts,
        "claim_boundaries": projection_core["claim_boundaries"],
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}

    session_batches = []
    for index, row in enumerate(rows, 1):
        session_batches.append({
            "batch_id": f"R7_PROJECTED_SESSION_BATCH_{index:03d}",
            "work_item_id": row["work_item_id"],
            "item_id": row["item_id"],
            "breadth_cell_id": row["breadth_cell_id"],
            "canonical_candidate_sha256": row["canonical_candidate_sha256"],
            "canonical_stimulus_fingerprint": row["canonical_stimulus_fingerprint"],
            "delivery_fingerprint": row["delivery_fingerprint"],
            "runtime_item_digest": row["runtime_item_digest"],
            "skill": bank_by_id[row["item_id"]].get("skill"),
            "purpose": bank_by_id[row["item_id"]].get("purpose"),
            "runtime_launch_contract": {
                "builder": "ulga/builders/build_a1fs_v1_r7_planner_redeploy_reading_stimulus_runtime_projection_fullfix.py",
                "command": "start-session",
                "execution_order": "SEQUENTIAL_ONE_ACTIVE_SESSION_PER_LEARNER",
                "planned_item_count": 1,
                "requires_projection_applied": True,
            },
        })
    session_core = {
        "task_id": TASK_ID,
        "schema_version": SESSION_SCHEMA_VERSION,
        "private_local_only": True,
        "source_projection_sha256": projection["projection_sha256"],
        "source_deployment_queue_sha256": deployment_queue["deployment_queue_sha256"],
        "session_batch_count": len(session_batches),
        "session_batches": session_batches,
        "a2_unlocked": False,
    }
    session = {**session_core, "manifest_sha256": digest(session_core)}
    session_safe_core = {
        "task_id": TASK_ID,
        "schema_version": SESSION_SAFE_SCHEMA_VERSION,
        "validation_status": STATUS,
        "source_projection_sha256": projection["projection_sha256"],
        "session_batch_count": len(session_batches),
        "maximum_items_per_batch": 1 if session_batches else 0,
        "a2_unlocked": False,
    }
    session_safe = {**session_safe_core, "report_sha256": digest(session_safe_core)}
    return projection, safe, session, session_safe


def safe_scan(value: Any) -> None:
    forbidden = {
        "projected_learner_contract", "learner_contract", "prompt", "context", "options",
        "accepted_texts", "accepted_sequence", "rubric", "response", "private_scoring_contract",
    }
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in forbidden:
                raise RuntimeProjectionError(f"safe_private_field:{key}")
            safe_scan(child)
    elif isinstance(value, list):
        for child in value:
            safe_scan(child)
    elif isinstance(value, str):
        if Path(value).is_absolute() or (len(value) > 2 and value[1:3] in {":/", ":\\"}):
            raise RuntimeProjectionError("safe_absolute_path")


def validate_projection_artifact(projection: Mapping[str, Any]) -> str:
    if projection.get("task_id") != TASK_ID or projection.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeProjectionError("projection_identity_invalid")
    if projection.get("validation_status") != STATUS or projection.get("private_local_only") is not True:
        raise RuntimeProjectionError("projection_status_or_privacy_invalid")
    actual = projection.get("projection_sha256")
    if actual != digest({key: value for key, value in projection.items() if key != "projection_sha256"}):
        raise RuntimeProjectionError("projection_digest_invalid")
    if projection.get("claim_boundaries", {}).get("a2_unlocked") is not False:
        raise RuntimeProjectionError("projection_a2_lock_invalid")
    deliveries = projection.get("deliveries")
    if not isinstance(deliveries, list) or len(deliveries) != projection.get("counts", {}).get("deployment_count"):
        raise RuntimeProjectionError("projection_delivery_count_invalid")
    return str(actual)


def apply_projection_to_runtime(
    *, database_path: Path, projection: Mapping[str, Any], allow_projection_rebind: bool = False,
) -> dict[str, Any]:
    projection_sha = validate_projection_artifact(projection)
    database_path = Path(database_path)
    if not database_path.is_file():
        raise RuntimeProjectionError("r5_database_missing")
    backup_path = database_path.with_name(
        f"{database_path.name}.before-{projection_sha[:12]}.backup"
    )
    temporary_path = database_path.with_name(f".{database_path.name}.{uuid.uuid4().hex}.tmp")
    shutil.copy2(database_path, temporary_path)
    try:
        connection = sqlite3.connect(temporary_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        try:
            connection.execute("BEGIN IMMEDIATE")
            names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            required = {"r5_metadata", "edge_runtime_items", "edge_sessions"}
            if required - names:
                raise RuntimeProjectionError("r5_runtime_tables_missing")
            metadata = dict(connection.execute("SELECT key,value FROM r5_metadata"))
            expected_bank = projection.get("source_bindings", {}).get("r4_bank_sha256")
            if metadata.get("source_bank_sha256") != expected_bank:
                raise RuntimeProjectionError("r5_runtime_bank_binding_mismatch")
            existing_projection = metadata.get("source_delivery_projection_sha256")
            if existing_projection and existing_projection != projection_sha and not allow_projection_rebind:
                raise RuntimeProjectionError("r5_runtime_projection_rebind_requires_explicit_allow")
            open_sessions = connection.execute(
                "SELECT COUNT(*) FROM edge_sessions WHERE session_state IN('ACTIVE','PAUSED')"
            ).fetchone()[0]
            if open_sessions:
                raise RuntimeProjectionError("r5_runtime_projection_open_session")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS edge_runtime_delivery_projection(
                item_id TEXT PRIMARY KEY REFERENCES edge_runtime_items(item_id),
                work_item_id TEXT NOT NULL UNIQUE,
                canonical_candidate_sha256 TEXT NOT NULL,
                canonical_stimulus_fingerprint TEXT NOT NULL,
                delivery_fingerprint TEXT NOT NULL UNIQUE,
                delivery_contract_sha256 TEXT NOT NULL,
                runtime_item_digest TEXT NOT NULL UNIQUE,
                m2_asset_id TEXT,
                m2_lesson_id TEXT,
                m2_content_digest TEXT,
                projected_learner_contract_sha256 TEXT NOT NULL,
                stimulus_render_manifest_sha256 TEXT NOT NULL,
                projection_sha256 TEXT NOT NULL
                )"""
            )
            if existing_projection and existing_projection != projection_sha:
                connection.execute("DELETE FROM edge_runtime_delivery_projection")
            for delivery in projection["deliveries"]:
                item_id = str(delivery["item_id"])
                row = connection.execute(
                    "SELECT item_json FROM edge_runtime_items WHERE item_id=?", (item_id,)
                ).fetchone()
                if not row:
                    raise RuntimeProjectionError(f"runtime_item_missing:{item_id}")
                item = json.loads(row["item_json"])
                if item.get("candidate_sha256") != delivery.get("canonical_candidate_sha256"):
                    raise RuntimeProjectionError(f"runtime_candidate_binding_mismatch:{item_id}")
                if item.get("stimulus_fingerprint") != delivery.get("canonical_stimulus_fingerprint"):
                    raise RuntimeProjectionError(f"runtime_stimulus_binding_mismatch:{item_id}")
                runtime_binding = {
                    "task_id": TASK_ID,
                    "work_item_id": delivery["work_item_id"],
                    "delivery_fingerprint": delivery["delivery_fingerprint"],
                    "canonical_candidate_sha256": delivery["canonical_candidate_sha256"],
                    "canonical_stimulus_fingerprint": delivery["canonical_stimulus_fingerprint"],
                    "m2_asset_id": delivery.get("m2_asset_id"),
                    "m2_lesson_id": delivery.get("m2_lesson_id"),
                    "m2_content_digest": delivery.get("m2_content_digest"),
                    "projection_applied": delivery["projection_applied"],
                }
                item["learner_contract"] = deepcopy(delivery["projected_learner_contract"])
                item["runtime_delivery_binding"] = runtime_binding
                runtime_item_digest = r5.digest(item)
                if runtime_item_digest != delivery["runtime_item_digest"]:
                    raise RuntimeProjectionError(f"runtime_item_digest_rebuild_mismatch:{item_id}")
                connection.execute(
                    "UPDATE edge_runtime_items SET item_json=?,item_digest=? WHERE item_id=?",
                    (r5.canonical(item), runtime_item_digest, item_id),
                )
                connection.execute(
                    """INSERT OR REPLACE INTO edge_runtime_delivery_projection(
                    item_id,work_item_id,canonical_candidate_sha256,canonical_stimulus_fingerprint,
                    delivery_fingerprint,delivery_contract_sha256,runtime_item_digest,m2_asset_id,
                    m2_lesson_id,m2_content_digest,projected_learner_contract_sha256,
                    stimulus_render_manifest_sha256,projection_sha256)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        item_id, delivery["work_item_id"], delivery["canonical_candidate_sha256"],
                        delivery["canonical_stimulus_fingerprint"], delivery["delivery_fingerprint"],
                        delivery["delivery_contract_sha256"], runtime_item_digest,
                        delivery.get("m2_asset_id"), delivery.get("m2_lesson_id"),
                        delivery.get("m2_content_digest"), delivery["projected_learner_contract_sha256"],
                        delivery["stimulus_render_manifest_sha256"], projection_sha,
                    ),
                )
            connection.execute(
                "INSERT OR REPLACE INTO r5_metadata(key,value) VALUES(?,?)",
                ("source_delivery_projection_sha256", projection_sha),
            )
            connection.execute(
                "INSERT OR REPLACE INTO r5_metadata(key,value) VALUES(?,?)",
                ("learner_renderable_item_count", str(len(projection["deliveries"]))),
            )
            if connection.execute("PRAGMA foreign_key_check").fetchall():
                raise RuntimeProjectionError("runtime_projection_foreign_key_check_failed")
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeProjectionError("runtime_projection_integrity_check_failed")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        if not backup_path.exists():
            shutil.copy2(database_path, backup_path)
        os.replace(temporary_path, database_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return {
        "validation_status": STATUS,
        "projection_sha256": projection_sha,
        "delivery_count": len(projection["deliveries"]),
        "source_dependency_projection_count": projection["counts"]["source_dependency_projection_count"],
        "backup_path": str(backup_path),
        "a2_unlocked": False,
        "learner_evidence_generated": False,
    }


def _utc(value: str | None = None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise RuntimeProjectionError("timestamp_timezone_required")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def start_exact_projected_session(
    *, database_path: Path, projection: Mapping[str, Any], learner_id: str,
    work_item_id: str, session_id: str | None = None, started_at: str | None = None,
) -> dict[str, Any]:
    projection_sha = validate_projection_artifact(projection)
    delivery = next(
        (row for row in projection["deliveries"] if row.get("work_item_id") == work_item_id), None
    )
    if delivery is None:
        raise RuntimeProjectionError(f"projection_work_item_missing:{work_item_id}")
    runtime = r5.LocalEdgeRuntime(Path(database_path))
    at = _utc(started_at)
    session_id = session_id or f"R5_SESSION:{uuid.uuid4()}"
    access_token = secrets.token_urlsafe(32)
    with runtime.write() as connection:
        metadata = dict(connection.execute("SELECT key,value FROM r5_metadata"))
        if metadata.get("source_delivery_projection_sha256") != projection_sha:
            raise RuntimeProjectionError("runtime_projection_not_applied")
        runtime._profile(connection, learner_id)
        if connection.execute(
            "SELECT 1 FROM edge_sessions WHERE learner_id=? AND session_state IN('ACTIVE','PAUSED')",
            (learner_id,),
        ).fetchone():
            raise RuntimeProjectionError("open_edge_session_exists")
        item = connection.execute(
            "SELECT * FROM edge_runtime_items WHERE item_id=?", (delivery["item_id"],)
        ).fetchone()
        if not item:
            raise RuntimeProjectionError("projected_runtime_item_missing")
        cell = connection.execute(
            "SELECT * FROM edge_cell_supply WHERE breadth_cell_id=?", (delivery["breadth_cell_id"],)
        ).fetchone()
        if not cell or cell["supply_status"] != r5.ASSIGNABLE_CELL_STATUS:
            raise RuntimeProjectionError("projected_breadth_cell_not_assignable")
        connection.execute(
            "INSERT INTO edge_sessions VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                session_id, learner_id, delivery["breadth_cell_id"], item["purpose"], "ACTIVE", 1,
                1, r5.digest(access_token), at, at, None,
            ),
        )
        connection.execute(
            "INSERT INTO edge_assignments VALUES(?,?,?,?,?,?)",
            (session_id, delivery["item_id"], 1, "ASSIGNED", at, None),
        )
        runtime._append_event(
            connection,
            learner_id=learner_id,
            session_id=session_id,
            event_type="EDGE_PROJECTED_SESSION_STARTED",
            event_at=at,
            payload={
                "work_item_id": work_item_id,
                "item_id": delivery["item_id"],
                "breadth_cell_id": delivery["breadth_cell_id"],
                "delivery_fingerprint": delivery["delivery_fingerprint"],
                "projection_sha256": projection_sha,
                "planned_item_count": 1,
            },
        )
    result = runtime.session_payload(session_id=session_id, access_token=access_token)
    result["access_token"] = access_token
    result["work_item_id"] = work_item_id
    result["delivery_fingerprint"] = delivery["delivery_fingerprint"]
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    build_parser = sub.add_parser("build")
    build_parser.add_argument("--r4-bank", type=Path, required=True)
    build_parser.add_argument("--deployment-queue", type=Path, required=True)
    build_parser.add_argument("--m2-consumer", type=Path, required=True)
    build_parser.add_argument("--output-root", type=Path, required=True)
    build_parser.add_argument("--expected-deployment-count", type=int, default=209)
    build_parser.add_argument("--expected-projected-count", type=int, default=198)

    apply_parser = sub.add_parser("apply-runtime")
    apply_parser.add_argument("--database", type=Path, required=True)
    apply_parser.add_argument("--projection", type=Path, required=True)
    apply_parser.add_argument("--allow-projection-rebind", action="store_true")

    start_parser = sub.add_parser("start-session")
    start_parser.add_argument("--database", type=Path, required=True)
    start_parser.add_argument("--projection", type=Path, required=True)
    start_parser.add_argument("--learner-id", required=True)
    start_parser.add_argument("--work-item-id", required=True)
    start_parser.add_argument("--session-id")
    start_parser.add_argument("--started-at")

    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            bank = read_json(args.r4_bank, "r4_bank")
            deployment = read_json(args.deployment_queue, "deployment_queue")
            consumer = read_json(args.m2_consumer, "m2_consumer")
            projection, safe, session, session_safe = build_projection(
                bank=bank,
                deployment_queue=deployment,
                consumer=consumer,
                bank_file_sha256=file_digest(args.r4_bank),
                deployment_file_sha256=file_digest(args.deployment_queue),
                consumer_file_sha256=file_digest(args.m2_consumer),
                expected_deployment_count=args.expected_deployment_count,
                expected_projected_count=args.expected_projected_count,
            )
            safe_scan(safe)
            safe_scan(session_safe)
            atomic_json(args.output_root / PROJECTION_FILENAME, projection, private=True)
            atomic_json(args.output_root / SAFE_FILENAME, safe, private=False)
            atomic_json(args.output_root / SESSION_FILENAME, session, private=True)
            atomic_json(args.output_root / SESSION_SAFE_FILENAME, session_safe, private=False)
            result = {
                "validation_status": STATUS,
                "projection_sha256": projection["projection_sha256"],
                "counts": projection["counts"],
                "session_batch_count": session["session_batch_count"],
                "next_short_step": NEXT_SHORT_STEP,
            }
        elif args.command == "apply-runtime":
            result = apply_projection_to_runtime(
                database_path=args.database,
                projection=read_json(args.projection, "projection"),
                allow_projection_rebind=args.allow_projection_rebind,
            )
        else:
            result = start_exact_projected_session(
                database_path=args.database,
                projection=read_json(args.projection, "projection"),
                learner_id=args.learner_id,
                work_item_id=args.work_item_id,
                session_id=args.session_id,
                started_at=args.started_at,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (RuntimeProjectionError, r5.LocalEdgeRuntimeError, stimulus.StimulusContractError, sqlite3.Error, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
