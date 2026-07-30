#!/usr/bin/env python3
"""Reconcile both RAZQ01E consumers and prove real Unit01 multi-session use.

RAZQ01F does not create content, a question bank, a planner, a renderer, a
learner database, response capture, or scoring. It composes the existing
RAZQ01E extension runtime with the existing RAZQ01E content-binding workbench.
An extension task keeps the exact content asset from which it was materialized;
base U01QB tasks receive a compatible distinct content asset. Three sequential
Reading sessions then exercise M3 exposure, M6 scoring, workbench rendering,
and cross-session content diversity on the same learner database.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import (
    build_a1fs_v1_razq01e_unit01_admitted_content_asset_qb_consumer_workbench
    as binding_consumer,
)
from ulga.builders import (
    build_a1fs_v1_razq01e_unit01_approved_content_existing_qb_learner_stimulus_runtime
    as extension_runtime,
)
from ulga.builders import u01qb03_renderer_runtime_impl as renderer

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Composes the existing RAZQ01E extension runtime, existing RAZQ01E content-binding consumer, U01QB02 session runtime, U01QB03 renderer, M3 exposure authority, and M6 response/scoring authority; no content, bank, planner, renderer, database, runtime table, response capture, scoring authority, audio, A2, or Unit02-Unit24 artifact is produced."
PROGRAM_ID = "A1FS-V1"
TASK_ID = (
    "A1FS-V1-RAZQ01F_"
    "Unit01RealContentMultiSessionDiversityAndLearnerUseAcceptance"
)
SCHEMA_VERSION = "a1fs.v1.razq01f.unit01_multisession_reconciliation.v1"
PASS_STATUS = (
    "PASS_A1FS_V1_RAZQ01F_UNIT01_REAL_CONTENT_MULTI_SESSION_"
    "DIVERSITY_AND_LEARNER_USE"
)
SESSION_COUNT = 3
SESSION_SIZE = extension_runtime.qb02.SESSION_SIZE
MIN_EXTENSION_ITEMS_PER_SESSION = extension_runtime.MIN_CONTENT_ITEMS_PER_SESSION
MIN_DISTINCT_ITEMS_ACROSS_SESSIONS = 20
MIN_DISTINCT_CONTENT_ASSETS_ACROSS_SESSIONS = 20
EXPECTED_EXPOSURE_COUNT = SESSION_COUNT * SESSION_SIZE
EXPECTED_ATTEMPT_COUNT = SESSION_COUNT
NEXT_SHORT_STEP = (
    "A1FS-V1-RAZQ01G_"
    "Unit01RealContentLearnerProductReleaseReadinessAcceptance"
)
DEFAULT_APPROVED_CONTENT = Path(
    "ulga/private/a1fs_v1_razq01d_fullfix2_unit01_real44.approved.private.json"
)
DEFAULT_OUTPUT_ROOT = Path(
    "A1FS_Private_Outputs/RAZQ01F_Unit01MultiSessionAcceptance"
)


class MultiSessionAcceptanceError(ValueError):
    """Fail-closed RAZQ01F composition or acceptance error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MultiSessionAcceptanceError(f"json_unreadable:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise MultiSessionAcceptanceError(f"json_object_required:{path}")
    return value


def timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _extension_asset_map(database: Path, session_id: str) -> dict[str, str]:
    with sqlite3.connect(Path(database)) as connection:
        rows = connection.execute(
            """SELECT s.item_id,e.content_asset_id
            FROM u01qb02_session_items s
            JOIN razq01e_extension_items e USING(item_id)
            WHERE s.session_id=?""",
            (session_id,),
        ).fetchall()
    return {str(item_id): str(content_asset_id) for item_id, content_asset_id in rows}


def _safe_content_binding(
    *,
    asset: Mapping[str, Any],
    learner_item: Mapping[str, Any],
    match: Mapping[str, Any],
    authority: str,
    reused_from_prior_session: bool,
) -> dict[str, Any]:
    value = binding_consumer._safe_binding(
        asset=asset,
        learner_item=learner_item,
        match=match,
    )
    value.update(
        {
            "binding_authority": authority,
            "reused_from_prior_session": reused_from_prior_session,
        }
    )
    return value


def bind_reconciled_bundle(
    *,
    bundle: Mapping[str, Any],
    database: Path,
    approved_content: Mapping[str, Any],
    prior_content_asset_ids: Sequence[str] = (),
) -> dict[str, Any]:
    payload, assets = binding_consumer.validate_approved_content(approved_content)
    assets_by_id = {str(row["content_asset_id"]): row for row in assets}
    learner_items = [deepcopy(dict(row)) for row in bundle.get("items") or []]
    if len(learner_items) != SESSION_SIZE:
        raise MultiSessionAcceptanceError(
            f"session_item_count_invalid:{len(learner_items)}"
        )
    item_ids = [str(row["item_id"]) for row in learner_items]
    private_items = binding_consumer._private_items(Path(database), item_ids)
    session_id = str(bundle.get("session_id") or "")
    extension_assets = _extension_asset_map(Path(database), session_id)
    prior = {str(value) for value in prior_content_asset_ids}
    used: set[str] = set()
    bound_items: list[dict[str, Any]] = []
    authoritative_extension_count = 0
    fresh_count = 0

    for learner_item in learner_items:
        item_id = str(learner_item["item_id"])
        private_item = private_items[item_id]
        authoritative_asset_id = extension_assets.get(item_id)
        authority = "RAZQ01E_COMPATIBILITY_SELECTION"

        if authoritative_asset_id:
            asset = assets_by_id.get(authoritative_asset_id)
            if asset is None:
                raise MultiSessionAcceptanceError(
                    f"extension_authoritative_asset_missing:{item_id}:{authoritative_asset_id}"
                )
            match = binding_consumer.compatibility(learner_item, private_item, asset)
            if match is None:
                raise MultiSessionAcceptanceError(
                    f"extension_authoritative_asset_incompatible:{item_id}:{authoritative_asset_id}"
                )
            asset_id = authoritative_asset_id
            authority = "RAZQ01E_EXTENSION_ITEM_IDENTITY"
            authoritative_extension_count += 1
        else:
            compatible: list[tuple[int, int, str, str, dict[str, Any], dict[str, Any]]] = []
            for asset in assets:
                asset_id = str(asset["content_asset_id"])
                if asset_id in used:
                    continue
                match = binding_consumer.compatibility(learner_item, private_item, asset)
                if match is None:
                    continue
                stable = hashlib.sha256(
                    f"{session_id}|{item_id}|{asset_id}".encode("utf-8")
                ).hexdigest()
                compatible.append(
                    (
                        1 if asset_id in prior else 0,
                        -int(match["score"]),
                        stable,
                        asset_id,
                        asset,
                        match,
                    )
                )
            if not compatible:
                raise MultiSessionAcceptanceError(
                    f"compatible_content_asset_missing:{item_id}"
                )
            compatible.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
            _prior_rank, _score, _stable, asset_id, asset, match = compatible[0]

        if asset_id in used:
            raise MultiSessionAcceptanceError(
                f"duplicate_content_asset_in_session:{session_id}:{asset_id}"
            )
        used.add(asset_id)
        reused = asset_id in prior
        fresh_count += int(not reused)

        original_stimulus = str(learner_item.get("stimulus") or "").strip()
        approved_stimulus = binding_consumer.content_text(asset)
        combined = f"學習素材：{approved_stimulus}"
        if original_stimulus:
            combined += f"\n題目線索：{original_stimulus}"
        learner_item["question_stimulus"] = original_stimulus
        learner_item["content_asset_stimulus"] = approved_stimulus
        learner_item["stimulus"] = combined
        learner_item["content_binding"] = _safe_content_binding(
            asset=asset,
            learner_item=learner_item,
            match=match,
            authority=authority,
            reused_from_prior_session=reused,
        )
        bound_items.append(learner_item)

    if len(used) != SESSION_SIZE:
        raise MultiSessionAcceptanceError(
            f"distinct_session_content_asset_count_invalid:{len(used)}"
        )
    if authoritative_extension_count < MIN_EXTENSION_ITEMS_PER_SESSION:
        raise MultiSessionAcceptanceError(
            "authoritative_extension_content_quota_invalid:"
            f"{authoritative_extension_count}"
        )

    value = deepcopy(dict(bundle))
    value.update(
        {
            "task_id": TASK_ID,
            "schema_version": SCHEMA_VERSION,
            "validation_status": PASS_STATUS,
            "content_runtime_authority_task_id": extension_runtime.TASK_ID,
            "content_binding_consumer_task_id": binding_consumer.TASK_ID,
            "content_asset_authority_task_id": extension_runtime.content_builder.TASK_ID,
            "content_asset_approved_artifact_sha256": approved_content["artifact_sha256"],
            "content_asset_available_count": len(assets),
            "content_asset_bound_count": len(bound_items),
            "distinct_bound_content_asset_count": len(used),
            "authoritative_extension_content_count": authoritative_extension_count,
            "fresh_cross_session_content_count": fresh_count,
            "prior_session_content_overlap_count": len(used & prior),
            "items": bound_items,
            "content_consumer_reconciled": True,
            "next_short_step": NEXT_SHORT_STEP,
        }
    )
    capabilities = deepcopy(dict(value.get("capabilities") or {}))
    capabilities.update(
        {
            "existing_razq01e_extension_runtime_reused": True,
            "existing_razq01e_binding_consumer_reused": True,
            "existing_u01qb02_session_selection_reused": True,
            "existing_u01qb03_workbench_reused": True,
            "existing_m3_exposure_reused": True,
            "existing_m6_response_scoring_reused": True,
            "parallel_question_bank_created": False,
            "parallel_runtime_table_created": False,
            "parallel_renderer_created": False,
            "parallel_scoring_created": False,
            "raw_raz_identity_exposed": False,
        }
    )
    value["capabilities"] = capabilities
    renderer._assert_safe(value)
    if any(key in canonical(value) for key in binding_consumer.PRIVATE_LINEAGE_KEYS):
        raise MultiSessionAcceptanceError("private_raz_lineage_key_exposed")
    if payload.get("task_id") != extension_runtime.content_builder.TASK_ID:
        raise MultiSessionAcceptanceError("approved_content_authority_drift")
    return value


def build_workbench(
    *,
    database: Path,
    learner_id: str,
    session_id: str,
    approved_content: Mapping[str, Any],
    output_root: Path,
    prior_content_asset_ids: Sequence[str] = (),
) -> dict[str, Any]:
    output_root = Path(output_root)
    renderer.build_workbench(
        database=Path(database),
        learner_id=learner_id,
        session_id=session_id,
        output_root=output_root,
    )
    base_bundle = load(output_root / "session.private.json")
    bundle = bind_reconciled_bundle(
        bundle=base_bundle,
        database=Path(database),
        approved_content=approved_content,
        prior_content_asset_ids=prior_content_asset_ids,
    )
    renderer.atomic(
        output_root / "session.private.json",
        json.dumps(bundle, ensure_ascii=False, indent=2) + "\n",
    )
    files: dict[str, dict[str, Any]] = {}
    for name in ("session.private.json", "index.html", "styles.css", "app.js"):
        raw = (output_root / name).read_bytes()
        files[name] = {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        }
    manifest = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "session_id": session_id,
        "lesson_id": bundle["lesson_id"],
        "skill": bundle["skill"],
        "item_count": bundle["item_count"],
        "content_asset_available_count": bundle["content_asset_available_count"],
        "content_asset_bound_count": bundle["content_asset_bound_count"],
        "distinct_bound_content_asset_count": bundle[
            "distinct_bound_content_asset_count"
        ],
        "authoritative_extension_content_count": bundle[
            "authoritative_extension_content_count"
        ],
        "fresh_cross_session_content_count": bundle[
            "fresh_cross_session_content_count"
        ],
        "prior_session_content_overlap_count": bundle[
            "prior_session_content_overlap_count"
        ],
        "content_asset_approved_artifact_sha256": approved_content[
            "artifact_sha256"
        ],
        "renderer_authority_task_id": renderer.TASK_ID,
        "runtime_authority_task_id": extension_runtime.qb02.TASK_ID,
        "extension_runtime_task_id": extension_runtime.TASK_ID,
        "binding_consumer_task_id": binding_consumer.TASK_ID,
        "files": files,
        "private_localhost_only": renderer.PRIVATE_ONLY,
        "parallel_question_bank_created": False,
        "parallel_runtime_table_created": False,
        "parallel_renderer_created": False,
        "parallel_response_capture_created": False,
        "parallel_scoring_created": False,
        "next_short_step": NEXT_SHORT_STEP,
    }
    renderer.atomic(
        output_root / "manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    )
    return manifest


def _session_version(database: Path, session_id: str) -> int:
    return renderer.session_version(Path(database), session_id)


def run_acceptance(
    *,
    database: Path,
    approved_content: Mapping[str, Any],
    learner_id: str,
    output_root: Path,
    session_prefix: str = "razq01f-reading-session",
) -> dict[str, Any]:
    database = Path(database)
    output_root = Path(output_root)
    if not database.is_file():
        raise MultiSessionAcceptanceError("learner_database_missing")

    _candidate, approved_extension, _safe = (
        extension_runtime.build_extension_package(approved_content)
    )
    runtime_readback = extension_runtime.materialize_runtime(
        database, approved_extension
    )
    if runtime_readback.get("combined_runtime_item_count") != 474:
        raise MultiSessionAcceptanceError("combined_runtime_item_count_invalid")

    store = m3.LearnerStateStore(database)
    runtime = extension_runtime.qb02.Unit01ApprovedVariantSessionRuntime(database)
    prior_content_assets: set[str] = set()
    all_item_ids: set[str] = set()
    all_content_asset_ids: set[str] = set()
    session_reports: list[dict[str, Any]] = []
    base_time = datetime(2026, 7, 31, 1, 0, tzinfo=timezone.utc)

    for session_index in range(1, SESSION_COUNT + 1):
        session_id = f"{session_prefix}-{session_index}"
        session_root = output_root / f"session_{session_index:02d}"
        started_at = base_time + timedelta(minutes=(session_index - 1) * 30)
        session = store.start_session(
            learner_id=learner_id,
            lesson_id=extension_runtime.qb02.UNIT01_LESSONS["READING"],
            session_id=session_id,
            at=timestamp(started_at),
        )
        plan = extension_runtime.assemble_session_with_content(
            database,
            learner_id=learner_id,
            session_id=session_id,
        )
        if plan.get("content_extension_item_count", 0) < MIN_EXTENSION_ITEMS_PER_SESSION:
            raise MultiSessionAcceptanceError(
                f"session_extension_quota_invalid:{session_id}"
            )
        manifest = build_workbench(
            database=database,
            learner_id=learner_id,
            session_id=session_id,
            approved_content=approved_content,
            output_root=session_root,
            prior_content_asset_ids=sorted(prior_content_assets),
        )
        bundle = load(session_root / "session.private.json")
        items = [dict(row) for row in bundle["items"]]
        private_items = binding_consumer._private_items(
            database, [str(row["item_id"]) for row in items]
        )
        version = int(session["session_version"])
        attempt_outcome = None
        attempted_item_id = None

        for position, item in enumerate(items, 1):
            item_id = str(item["item_id"])
            exposure_at = started_at + timedelta(minutes=position)
            exposure = runtime.record_item_exposure(
                session_id=session_id,
                item_id=item_id,
                expected_session_version=version,
                exposure_id=f"{session_id}-exposure-{position:02d}",
                at=timestamp(exposure_at),
            )
            version = int(exposure["session_version"])
            if attempted_item_id is None and item.get("capture_enabled") is True:
                private_item = private_items[item_id]
                attempt = runtime.capture_response(
                    learner_id=learner_id,
                    session_id=session_id,
                    item_id=item_id,
                    response=deepcopy(private_item["correct_answer"]),
                    expected_session_version=version,
                    attempt_id=f"{session_id}-attempt-01",
                    submitted_at=timestamp(exposure_at + timedelta(seconds=20)),
                )
                attempt_outcome = str(attempt["outcome"])
                attempted_item_id = item_id
                version = _session_version(database, session_id)

        if attempt_outcome != "AUTO_PASS" or attempted_item_id is None:
            raise MultiSessionAcceptanceError(
                f"session_real_attempt_invalid:{session_id}:{attempt_outcome}"
            )
        store.end_session(
            session_id=session_id,
            outcome="COMPLETED",
            expected_session_version=version,
            at=timestamp(started_at + timedelta(minutes=20)),
        )
        evidence = extension_runtime.qb02.m6.ResponseEvidenceStore(
            database
        ).export_evidence(
            session_id=session_id,
            output_root=session_root / "evidence",
            exported_at=timestamp(started_at + timedelta(minutes=21)),
        )

        item_ids = {str(row["item_id"]) for row in items}
        content_ids = {
            str((row.get("content_binding") or {})["content_asset_id"])
            for row in items
        }
        extension_identity_ids = {
            str((row.get("content_binding") or {})["content_asset_id"])
            for row in items
            if (row.get("content_binding") or {}).get("binding_authority")
            == "RAZQ01E_EXTENSION_ITEM_IDENTITY"
        }
        if len(item_ids) != SESSION_SIZE or len(content_ids) != SESSION_SIZE:
            raise MultiSessionAcceptanceError(
                f"session_distinctness_invalid:{session_id}"
            )
        if len(extension_identity_ids) < MIN_EXTENSION_ITEMS_PER_SESSION:
            raise MultiSessionAcceptanceError(
                f"session_extension_identity_invalid:{session_id}"
            )

        session_reports.append(
            {
                "session_index": session_index,
                "session_id": session_id,
                "skill": "READING",
                "item_count": len(item_ids),
                "distinct_item_count": len(item_ids),
                "distinct_content_asset_count": len(content_ids),
                "authoritative_extension_content_count": len(
                    extension_identity_ids
                ),
                "fresh_cross_session_content_count": len(
                    content_ids - prior_content_assets
                ),
                "prior_session_content_overlap_count": len(
                    content_ids & prior_content_assets
                ),
                "attempted_item_id": attempted_item_id,
                "attempt_outcome": attempt_outcome,
                "workbench_manifest_sha256": digest(manifest),
                "evidence_attempt_count": evidence["attempt_count"],
                "item_ids": sorted(item_ids),
                "content_asset_ids": sorted(content_ids),
                "extension_identity_content_asset_ids": sorted(
                    extension_identity_ids
                ),
            }
        )
        all_item_ids.update(item_ids)
        all_content_asset_ids.update(content_ids)
        prior_content_assets.update(content_ids)

    with sqlite3.connect(database) as connection:
        exposure_count = connection.execute(
            "SELECT COUNT(*) FROM u01qb02_item_exposures WHERE learner_id=? AND session_id LIKE ?",
            (learner_id, f"{session_prefix}-%"),
        ).fetchone()[0]
        attempt_count = connection.execute(
            "SELECT COUNT(*) FROM response_attempts WHERE learner_id=? AND session_id LIKE ?",
            (learner_id, f"{session_prefix}-%"),
        ).fetchone()[0]
        pass_count = connection.execute(
            """SELECT COUNT(*) FROM scoring_results r
            JOIN response_attempts a USING(attempt_id)
            WHERE a.learner_id=? AND a.session_id LIKE ? AND r.outcome='AUTO_PASS'""",
            (learner_id, f"{session_prefix}-%"),
        ).fetchone()[0]
        razq01f_tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'razq01f%'"
        ).fetchall()

    if exposure_count != EXPECTED_EXPOSURE_COUNT:
        raise MultiSessionAcceptanceError(
            f"exposure_count_invalid:{exposure_count}"
        )
    if attempt_count != EXPECTED_ATTEMPT_COUNT or pass_count != EXPECTED_ATTEMPT_COUNT:
        raise MultiSessionAcceptanceError(
            f"attempt_count_invalid:{attempt_count}:{pass_count}"
        )
    if len(all_item_ids) < MIN_DISTINCT_ITEMS_ACROSS_SESSIONS:
        raise MultiSessionAcceptanceError(
            f"cross_session_item_diversity_invalid:{len(all_item_ids)}"
        )
    if len(all_content_asset_ids) < MIN_DISTINCT_CONTENT_ASSETS_ACROSS_SESSIONS:
        raise MultiSessionAcceptanceError(
            "cross_session_content_diversity_invalid:"
            f"{len(all_content_asset_ids)}"
        )
    if razq01f_tables:
        raise MultiSessionAcceptanceError("parallel_razq01f_runtime_table_created")

    core = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "learner_id": learner_id,
        "approved_content_artifact_sha256": approved_content["artifact_sha256"],
        "approved_extension_artifact_sha256": approved_extension[
            "artifact_sha256"
        ],
        "combined_runtime_item_count": runtime_readback[
            "combined_runtime_item_count"
        ],
        "session_count": len(session_reports),
        "session_size": SESSION_SIZE,
        "exposure_count": exposure_count,
        "attempt_count": attempt_count,
        "auto_pass_count": pass_count,
        "distinct_item_count_across_sessions": len(all_item_ids),
        "distinct_content_asset_count_across_sessions": len(
            all_content_asset_ids
        ),
        "minimum_distinct_item_count": MIN_DISTINCT_ITEMS_ACROSS_SESSIONS,
        "minimum_distinct_content_asset_count": (
            MIN_DISTINCT_CONTENT_ASSETS_ACROSS_SESSIONS
        ),
        "sessions": session_reports,
        "boundaries": {
            "unit01_only": True,
            "second_question_bank_created": False,
            "parallel_runtime_table_created": False,
            "parallel_renderer_created": False,
            "parallel_response_capture_created": False,
            "parallel_scoring_created": False,
            "unit02_to_unit24_modified": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
            "mastery_claimed": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    report = {**core, "readback_sha256": digest(core)}
    output_root.mkdir(parents=True, exist_ok=True)
    renderer.atomic(
        output_root / "razq01f_multisession_readback.json",
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument(
        "--approved-content", type=Path, default=DEFAULT_APPROVED_CONTENT
    )
    parser.add_argument("--learner-id", required=True)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--session-prefix", default="razq01f-reading-session")
    args = parser.parse_args(argv)
    result = run_acceptance(
        database=args.database,
        approved_content=load(args.approved_content),
        learner_id=args.learner_id,
        output_root=args.output_root,
        session_prefix=args.session_prefix,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"STATUS={PASS_STATUS}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
