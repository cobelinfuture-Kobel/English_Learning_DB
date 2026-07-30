#!/usr/bin/env python3
"""Independently validate the RAZQ01E existing-QB content consumer workbench."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_unit02_handoff
    as content_authority,
)
from ulga.builders import (
    build_a1fs_v1_razq01e_unit01_admitted_content_asset_qb_consumer_workbench
    as builder,
)
from ulga.builders import (
    build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02,
)
from ulga.builders import (
    build_a1fs_v1_u01qb03_unit01_approved_variant_learner_renderer_real_attempt
    as renderer,
)
from ulga.validators import (
    validate_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_unit02_handoff
    as content_validator,
)

VALIDATOR_ID = "A1FS-V1-RAZQ01E-INDEPENDENT-VALIDATOR"
FAIL_STATUS = "FAIL_A1FS_V1_RAZQ01E_UNIT01_ADMITTED_CONTENT_QB_CONSUMER"


class ContentConsumerValidationError(ValueError):
    """Raised for deterministic RAZQ01E validation failures."""


def fail(code: str) -> None:
    raise ContentConsumerValidationError(code)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"json_unreadable:{path}:{exc}")
    if not isinstance(value, dict):
        fail(f"json_object_required:{path}")
    return value


def _assert_no_private_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in builder.PRIVATE_LINEAGE_KEYS:
                fail(f"private_raz_lineage_key_exposed:{key}")
            if str(key) in renderer.BLOCKED_LEARNER_KEYS:
                fail(f"private_answer_key_exposed:{key}")
            _assert_no_private_keys(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_private_keys(child)


def _file_contract(output_root: Path, manifest: Mapping[str, Any]) -> None:
    expected_static = {
        "index.html": renderer.HTML,
        "styles.css": renderer.CSS,
        "app.js": renderer.JS,
    }
    files = manifest.get("files") or {}
    if set(files) != {
        "session.private.json",
        "index.html",
        "styles.css",
        "app.js",
    }:
        fail("manifest_file_set_invalid")
    for name, metadata in files.items():
        path = output_root / name
        if not path.is_file():
            fail(f"output_file_missing:{name}")
        raw = path.read_bytes()
        if (
            metadata.get("sha256") != hashlib.sha256(raw).hexdigest()
            or metadata.get("bytes") != len(raw)
        ):
            fail(f"output_file_hash_invalid:{name}")
    for name, expected in expected_static.items():
        if (output_root / name).read_text(encoding="utf-8") != expected:
            fail(f"existing_u01qb03_workbench_drift:{name}")


def _private_items(database: Path, item_ids: Sequence[str]) -> dict[str, dict[str, Any]]:
    placeholders = ",".join("?" for _ in item_ids)
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            f"SELECT item_id,private_item_json FROM u01qb02_item_catalog "
            f"WHERE item_id IN ({placeholders})",
            tuple(item_ids),
        ).fetchall()
    values = {str(item_id): json.loads(private_json) for item_id, private_json in rows}
    if set(values) != set(item_ids):
        fail("private_qb_item_binding_incomplete")
    return values


def _validate_approved(approved: Mapping[str, Any]) -> list[dict[str, Any]]:
    policy_artifact.verify_artifact_digest(approved)
    if (
        approved.get("artifact_role") != policy_artifact.APPROVED_ROLE
        or approved.get("producer_id") != content_authority.TASK_ID
        or approved.get("level_scope") != ["A1"]
        or (approved.get("admission") or {}).get("status") != "APPROVED"
    ):
        fail("approved_content_artifact_invalid")
    payload = approved.get("payload") or {}
    summary = content_validator.validate_payload(payload)
    coverage = payload.get("coverage_readback") or {}
    assets = payload.get("content_assets") or []
    if (
        summary.get("content_asset_count") != builder.EXPECTED_CONTENT_ASSET_COUNT
        or len(assets) != builder.EXPECTED_CONTENT_ASSET_COUNT
        or coverage.get("approved_content_asset_count")
        != builder.EXPECTED_CONTENT_ASSET_COUNT
        or coverage.get("human_review_pending_count") != 0
        or coverage.get("real44_acceptance_pass") is not True
    ):
        fail("approved_content_real44_contract_invalid")
    return [dict(row) for row in assets]


def _validate_item(
    *,
    item: Mapping[str, Any],
    private_item: Mapping[str, Any],
    asset: Mapping[str, Any],
) -> str:
    binding = item.get("content_binding") or {}
    if (
        binding.get("content_asset_id") != asset.get("content_asset_id")
        or binding.get("content_kind") != asset.get("content_kind")
        or binding.get("content_sha256") != asset.get("content_sha256")
        or binding.get("source_authority")
        != (asset.get("source_lineage") or {}).get("source_authority")
        or binding.get("matched_skill") != item.get("skill")
        or binding.get("matched_family_id") != item.get("pattern_family_id")
        or binding.get("matched_unit_pattern_id") != item.get("unit_pattern_id")
    ):
        fail(f"content_binding_identity_invalid:{item.get('item_id')}")

    expected = builder.compatibility(item, private_item, asset)
    if expected is None:
        fail(f"content_binding_incompatible:{item.get('item_id')}")
    if (
        binding.get("compatibility_mode") != expected.get("mode")
        or binding.get("compatibility_score") != expected.get("score")
        or binding.get("exact_family_match") != expected.get("exact_family")
        or binding.get("pattern_match") != expected.get("pattern_match")
        or binding.get("noun_match") != expected.get("noun_match")
        or binding.get("adjective_match") != expected.get("adjective_match")
    ):
        fail(f"content_binding_compatibility_drift:{item.get('item_id')}")

    approved_stimulus = builder.content_text(asset)
    original_stimulus = str(private_item.get("stimulus") or "").strip()
    if (
        item.get("content_asset_stimulus") != approved_stimulus
        or item.get("question_stimulus") != original_stimulus
        or approved_stimulus not in str(item.get("stimulus") or "")
        or (
            original_stimulus
            and original_stimulus not in str(item.get("stimulus") or "")
        )
    ):
        fail(f"learner_stimulus_binding_invalid:{item.get('item_id')}")
    return str(asset["content_asset_id"])


def validate(
    *,
    database: Path,
    approved_content: Mapping[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    details: dict[str, Any] = {}
    try:
        output_root = Path(output_root)
        manifest = load(output_root / "manifest.json")
        bundle = load(output_root / "session.private.json")
        assets = _validate_approved(approved_content)
        assets_by_id = {str(row["content_asset_id"]): row for row in assets}

        if (
            manifest.get("task_id") != builder.TASK_ID
            or manifest.get("schema_version") != builder.SCHEMA_VERSION
            or manifest.get("validation_status") != builder.PASS_STATUS
            or manifest.get("item_count") != qb02.SESSION_SIZE
            or manifest.get("content_asset_available_count")
            != builder.EXPECTED_CONTENT_ASSET_COUNT
            or manifest.get("content_asset_bound_count") != qb02.SESSION_SIZE
            or manifest.get("distinct_bound_content_asset_count")
            != qb02.SESSION_SIZE
            or manifest.get("renderer_authority_task_id") != renderer.TASK_ID
            or manifest.get("runtime_authority_task_id") != qb02.TASK_ID
            or manifest.get("existing_u01qb03_workbench_reused") is not True
            or manifest.get("parallel_question_bank_created") is not False
            or manifest.get("parallel_renderer_created") is not False
            or manifest.get("parallel_scoring_created") is not False
            or manifest.get("raw_raz_identity_exposed") is not False
        ):
            fail("manifest_contract_invalid")
        _file_contract(output_root, manifest)

        items = bundle.get("items") or []
        if (
            bundle.get("task_id") != builder.TASK_ID
            or bundle.get("schema_version") != builder.SCHEMA_VERSION
            or bundle.get("validation_status") != builder.PASS_STATUS
            or bundle.get("content_asset_authority_task_id")
            != content_authority.TASK_ID
            or bundle.get("content_asset_approved_artifact_sha256")
            != approved_content.get("artifact_sha256")
            or bundle.get("content_asset_available_count")
            != builder.EXPECTED_CONTENT_ASSET_COUNT
            or bundle.get("content_asset_bound_count") != qb02.SESSION_SIZE
            or bundle.get("distinct_bound_content_asset_count")
            != qb02.SESSION_SIZE
            or bundle.get("content_consumer_bound") is not True
            or len(items) != qb02.SESSION_SIZE
        ):
            fail("bundle_contract_invalid")
        _assert_no_private_keys(bundle)

        item_ids = [str(row["item_id"]) for row in items]
        if len(item_ids) != len(set(item_ids)):
            fail("session_item_identity_duplicate")
        private_items = _private_items(Path(database), item_ids)
        bound_ids: list[str] = []
        for item in items:
            binding = item.get("content_binding") or {}
            asset_id = str(binding.get("content_asset_id") or "")
            asset = assets_by_id.get(asset_id)
            if asset is None:
                fail(f"bound_content_asset_missing:{asset_id}")
            bound_ids.append(
                _validate_item(
                    item=item,
                    private_item=private_items[str(item["item_id"])],
                    asset=asset,
                )
            )
        if len(bound_ids) != len(set(bound_ids)):
            fail("bound_content_asset_not_distinct")

        with sqlite3.connect(database) as connection:
            metadata = dict(
                connection.execute("SELECT key,value FROM u01qb02_metadata")
            )
            plan_count = connection.execute(
                "SELECT COUNT(*) FROM u01qb02_session_plans WHERE session_id=?",
                (bundle["session_id"],),
            ).fetchone()[0]
            foreign_tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'razq01e%'"
            ).fetchall()
        if metadata.get("validation_status") != qb02.PASS_STATUS:
            fail("u01qb02_runtime_not_validated")
        if plan_count != 1:
            fail("u01qb02_session_plan_not_reused")
        if foreign_tables:
            fail("parallel_razq01e_runtime_table_created")

        details = {
            "session_item_count": len(items),
            "available_content_asset_count": len(assets),
            "bound_content_asset_count": len(bound_ids),
            "distinct_bound_content_asset_count": len(set(bound_ids)),
            "u01qb02_session_plan_count": plan_count,
            "existing_u01qb03_workbench_reused": True,
            "raw_raz_identity_exposed": False,
        }
    except Exception as exc:  # deterministic fail-closed report
        errors.append(str(exc))

    return {
        "validator_id": VALIDATOR_ID,
        "status": builder.PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        **details,
        "next_short_step": builder.NEXT_SHORT_STEP,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument(
        "--approved-content", type=Path, default=builder.DEFAULT_APPROVED_CONTENT
    )
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    report = validate(
        database=args.database,
        approved_content=builder.load_json(args.approved_content),
        output_root=args.output_root,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
