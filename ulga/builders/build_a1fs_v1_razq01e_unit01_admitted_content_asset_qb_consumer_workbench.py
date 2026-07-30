#!/usr/bin/env python3
"""Bind RAZQ01D-approved Unit01 content assets into the existing QB workbench.

RAZQ01E is a consumer adapter. It does not create another question bank,
planner, renderer, learner database, exposure store, response table, or scoring
engine. U01QB02 still selects the ten tasks and U01QB03 still emits the learner
workbench. This adapter selects one compatible approved content asset per task,
adds that asset as learner-visible study context, and preserves the original
question stimulus and response contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_unit02_handoff
    as content_authority,
)
from ulga.builders import (
    build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02,
)
from ulga.builders import (
    build_a1fs_v1_u01qb03_unit01_approved_variant_learner_renderer_real_attempt
    as renderer,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Consumes the RAZQ01D approved content artifact, U01QB02 session plan, and U01QB03 learner renderer; no new content authority, question bank, planner, renderer, learner database, exposure authority, response capture, scoring authority, audio, A2 content, or Unit02-Unit24 content is produced."
PROGRAM_ID = "A1FS-V1"
TASK_ID = (
    "A1FS-V1-RAZQ01E_"
    "Unit01AdmittedContentAssetExistingQBConsumerAndLearnerWorkbenchIntegration"
)
SCHEMA_VERSION = "a1fs.v1.razq01e.unit01_admitted_content_qb_consumer.v1"
PASS_STATUS = "PASS_A1FS_V1_RAZQ01E_UNIT01_ADMITTED_CONTENT_QB_CONSUMER"
NEXT_SHORT_STEP = (
    "A1FS-V1-RAZQ01F_"
    "Unit01AdmittedContentTenItemCompletionAndEvidenceExportAcceptance"
)
EXPECTED_CONTENT_ASSET_COUNT = 62
SESSION_ASSET_COUNT = qb02.SESSION_SIZE
DEFAULT_APPROVED_CONTENT = Path(
    "ulga/private/a1fs_v1_razq01d_fullfix2_unit01_real44.approved.private.json"
)
PRIVATE_LINEAGE_KEYS = frozenset(
    {
        "candidate_composite_key",
        "original_excerpt_sha256",
        "semantic_identity",
        "source_record_id",
    }
)


class ContentConsumerError(ValueError):
    """Fail-closed RAZQ01E content consumer error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContentConsumerError(f"json_unreadable:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ContentConsumerError(f"json_object_required:{path}")
    return value


def validate_approved_content(
    approved: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from ulga.validators import (
        validate_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_unit02_handoff
        as content_validator,
    )

    policy_artifact.verify_artifact_digest(approved)
    if (
        approved.get("artifact_role") != policy_artifact.APPROVED_ROLE
        or approved.get("producer_id") != content_authority.TASK_ID
        or approved.get("level_scope") != ["A1"]
        or approved.get("learner_facing") is not False
        or (approved.get("admission") or {}).get("status") != "APPROVED"
    ):
        raise ContentConsumerError("approved_content_artifact_invalid")
    payload = approved.get("payload")
    if not isinstance(payload, Mapping):
        raise ContentConsumerError("approved_content_payload_missing")
    summary = content_validator.validate_payload(payload)
    coverage = payload.get("coverage_readback") or {}
    assets = payload.get("content_assets")
    if (
        not isinstance(assets, list)
        or len(assets) != EXPECTED_CONTENT_ASSET_COUNT
        or summary.get("content_asset_count") != EXPECTED_CONTENT_ASSET_COUNT
        or coverage.get("approved_content_asset_count")
        != EXPECTED_CONTENT_ASSET_COUNT
        or coverage.get("human_review_pending_count") != 0
        or coverage.get("real44_acceptance_pass") is not True
        or (coverage.get("unit01_coverage") or {}).get("complete") is not True
    ):
        raise ContentConsumerError("approved_content_real44_contract_invalid")
    return dict(payload), [deepcopy(dict(row)) for row in assets]


def content_text(asset: Mapping[str, Any]) -> str:
    content = asset.get("content") or {}
    sentences = [str(value).strip() for value in content.get("sentences") or []]
    turns = [
        f"{str(row.get('speaker_id') or '').strip()}: "
        f"{str(row.get('utterance') or '').strip()}"
        for row in content.get("dialogue_turns") or []
        if isinstance(row, Mapping)
    ]
    text = " ".join(value for value in (*sentences, *turns) if value).strip()
    if not text:
        raise ContentConsumerError(
            f"approved_content_text_empty:{asset.get('content_asset_id')}"
        )
    return text


def _projection(asset: Mapping[str, Any], skill: str) -> Mapping[str, Any] | None:
    rows = [
        row
        for row in asset.get("skill_projections") or []
        if isinstance(row, Mapping) and row.get("skill") == skill
    ]
    if len(rows) > 1:
        raise ContentConsumerError(
            f"duplicate_skill_projection:{asset.get('content_asset_id')}:{skill}"
        )
    return rows[0] if rows else None


def _private_items(
    database: Path, item_ids: Sequence[str]
) -> dict[str, dict[str, Any]]:
    placeholders = ",".join("?" for _ in item_ids)
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            f"SELECT item_id,private_item_json FROM u01qb02_item_catalog "
            f"WHERE item_id IN ({placeholders})",
            tuple(item_ids),
        ).fetchall()
    values = {str(item_id): json.loads(private_json) for item_id, private_json in rows}
    if set(values) != set(item_ids):
        missing = sorted(set(item_ids) - set(values))
        raise ContentConsumerError("private_qb_item_missing:" + ",".join(missing))
    return values


def compatibility(
    learner_item: Mapping[str, Any],
    private_item: Mapping[str, Any],
    asset: Mapping[str, Any],
) -> dict[str, Any] | None:
    skill = str(learner_item.get("skill") or "")
    projection = _projection(asset, skill)
    if projection is None:
        return None
    family_id = str(learner_item.get("pattern_family_id") or "")
    unit_pattern_id = str(learner_item.get("unit_pattern_id") or "")
    exact_family = family_id in set(projection.get("existing_family_ids") or [])
    alignment = asset.get("target_alignment") or {}
    pattern_match = unit_pattern_id in set(alignment.get("grammar_target_ids") or [])
    if not exact_family and not pattern_match:
        return None

    lexical = private_item.get("lexical_slots") or {}
    noun = str(lexical.get("noun") or "").casefold()
    adjective = str(lexical.get("adjective") or "").casefold()
    asset_nouns = {
        str(value).casefold() for value in alignment.get("active_nouns") or []
    }
    asset_adjectives = {
        str(value).casefold() for value in alignment.get("active_adjectives") or []
    }
    noun_match = not noun or noun in asset_nouns
    adjective_match = not adjective or adjective in asset_adjectives

    score = (100 if exact_family else 70) + (20 if noun_match else 0)
    score += 15 if adjective_match else 0
    if exact_family and noun_match and adjective_match:
        mode = "EXACT_FAMILY_AND_LEXICAL"
    elif exact_family:
        mode = "EXACT_FAMILY"
    elif noun_match and adjective_match:
        mode = "PATTERN_AND_LEXICAL"
    else:
        mode = "PATTERN_FALLBACK"
    return {
        "mode": mode,
        "score": score,
        "exact_family": exact_family,
        "pattern_match": pattern_match,
        "noun_match": noun_match,
        "adjective_match": adjective_match,
        "projection": dict(projection),
    }


def _safe_binding(
    *,
    asset: Mapping[str, Any],
    learner_item: Mapping[str, Any],
    match: Mapping[str, Any],
) -> dict[str, Any]:
    lineage = asset.get("source_lineage") or {}
    return {
        "content_asset_id": str(asset["content_asset_id"]),
        "content_kind": str(asset["content_kind"]),
        "content_sha256": str(asset["content_sha256"]),
        "source_authority": str(lineage.get("source_authority") or ""),
        "compatibility_mode": str(match["mode"]),
        "compatibility_score": int(match["score"]),
        "matched_skill": str(learner_item["skill"]),
        "matched_family_id": str(learner_item["pattern_family_id"]),
        "matched_unit_pattern_id": str(learner_item["unit_pattern_id"]),
        "exact_family_match": bool(match["exact_family"]),
        "pattern_match": bool(match["pattern_match"]),
        "noun_match": bool(match["noun_match"]),
        "adjective_match": bool(match["adjective_match"]),
    }


def bind_bundle(
    *,
    bundle: Mapping[str, Any],
    database: Path,
    approved: Mapping[str, Any],
) -> dict[str, Any]:
    payload, assets = validate_approved_content(approved)
    learner_items = [deepcopy(dict(row)) for row in bundle.get("items") or []]
    if len(learner_items) != SESSION_ASSET_COUNT:
        raise ContentConsumerError(
            f"session_item_count_invalid:{len(learner_items)}"
        )
    private_items = _private_items(
        Path(database), [str(row["item_id"]) for row in learner_items]
    )

    used_assets: set[str] = set()
    bound_items: list[dict[str, Any]] = []
    mode_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    session_id = str(bundle.get("session_id") or "")

    for learner_item in learner_items:
        private_item = private_items[str(learner_item["item_id"])]
        compatible: list[tuple[int, str, str, dict[str, Any], dict[str, Any]]] = []
        for asset in assets:
            match = compatibility(learner_item, private_item, asset)
            if match is None:
                continue
            asset_id = str(asset["content_asset_id"])
            stable = hashlib.sha256(
                f"{session_id}|{learner_item['item_id']}|{asset_id}".encode("utf-8")
            ).hexdigest()
            compatible.append(
                (-int(match["score"]), stable, asset_id, asset, match)
            )
        if not compatible:
            raise ContentConsumerError(
                f"compatible_content_asset_missing:{learner_item['item_id']}"
            )
        compatible.sort(key=lambda row: (row[0], row[1], row[2]))
        chosen = next(
            (row for row in compatible if row[2] not in used_assets), None
        )
        if chosen is None:
            raise ContentConsumerError(
                f"distinct_content_asset_exhausted:{learner_item['item_id']}"
            )
        _negative_score, _stable, asset_id, asset, match = chosen
        used_assets.add(asset_id)

        original_stimulus = str(learner_item.get("stimulus") or "").strip()
        approved_stimulus = content_text(asset)
        combined = f"學習素材：{approved_stimulus}"
        if original_stimulus:
            combined += f"\n題目線索：{original_stimulus}"
        learner_item["question_stimulus"] = original_stimulus
        learner_item["content_asset_stimulus"] = approved_stimulus
        learner_item["stimulus"] = combined
        learner_item["content_binding"] = _safe_binding(
            asset=asset, learner_item=learner_item, match=match
        )
        mode = str(match["mode"])
        source = str((asset.get("source_lineage") or {}).get("source_authority") or "")
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
        source_counts[source] = source_counts.get(source, 0) + 1
        bound_items.append(learner_item)

    value = deepcopy(dict(bundle))
    value.update(
        {
            "task_id": TASK_ID,
            "schema_version": SCHEMA_VERSION,
            "validation_status": PASS_STATUS,
            "content_asset_authority_task_id": content_authority.TASK_ID,
            "content_asset_approved_artifact_sha256": approved["artifact_sha256"],
            "content_asset_available_count": len(assets),
            "content_asset_bound_count": len(bound_items),
            "distinct_bound_content_asset_count": len(used_assets),
            "content_binding_mode_counts": dict(sorted(mode_counts.items())),
            "content_binding_source_counts": dict(sorted(source_counts.items())),
            "items": bound_items,
            "content_consumer_bound": True,
            "next_short_step": NEXT_SHORT_STEP,
        }
    )
    capabilities = deepcopy(dict(value.get("capabilities") or {}))
    capabilities.update(
        {
            "existing_u01qb02_session_selection_reused": True,
            "existing_u01qb03_workbench_reused": True,
            "approved_content_asset_consumer_connected": True,
            "parallel_question_bank_created": False,
            "parallel_renderer_created": False,
            "parallel_scoring_created": False,
            "raw_raz_identity_exposed": False,
        }
    )
    value["capabilities"] = capabilities
    renderer._assert_safe(value)
    if any(key in canonical(value) for key in PRIVATE_LINEAGE_KEYS):
        raise ContentConsumerError("private_raz_lineage_key_exposed")
    if len(used_assets) != SESSION_ASSET_COUNT:
        raise ContentConsumerError("distinct_session_content_asset_count_invalid")
    if payload.get("task_id") != content_authority.TASK_ID:
        raise ContentConsumerError("content_authority_task_drift")
    return value


def build_bundle(
    *,
    database: Path,
    learner_id: str,
    session_id: str,
    approved_content: Mapping[str, Any],
) -> dict[str, Any]:
    base = renderer.build_bundle(
        database=Path(database), learner_id=learner_id, session_id=session_id
    )
    return bind_bundle(
        bundle=base, database=Path(database), approved=approved_content
    )


def build_workbench(
    *,
    database: Path,
    learner_id: str,
    session_id: str,
    approved_content: Mapping[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    output_root = Path(output_root)
    base_manifest = renderer.build_workbench(
        database=Path(database),
        learner_id=learner_id,
        session_id=session_id,
        output_root=output_root,
    )
    bundle = build_bundle(
        database=Path(database),
        learner_id=learner_id,
        session_id=session_id,
        approved_content=approved_content,
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
        "content_asset_approved_artifact_sha256": bundle[
            "content_asset_approved_artifact_sha256"
        ],
        "source_plan_digest": bundle["source_plan_digest"],
        "source_bank_sha256": bundle["source_bank_sha256"],
        "renderer_authority_task_id": renderer.TASK_ID,
        "runtime_authority_task_id": qb02.TASK_ID,
        "base_renderer_manifest_sha256": digest(base_manifest),
        "files": files,
        "private_localhost_only": renderer.PRIVATE_ONLY,
        "existing_u01qb03_workbench_reused": True,
        "parallel_question_bank_created": False,
        "parallel_renderer_created": False,
        "parallel_response_capture_created": False,
        "parallel_scoring_created": False,
        "raw_raz_identity_exposed": False,
        "next_short_step": NEXT_SHORT_STEP,
    }
    renderer.atomic(
        output_root / "manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    )
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--learner-id", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument(
        "--approved-content", type=Path, default=DEFAULT_APPROVED_CONTENT
    )
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    result = build_workbench(
        database=args.database,
        learner_id=args.learner_id,
        session_id=args.session_id,
        approved_content=load_json(args.approved_content),
        output_root=args.output_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
