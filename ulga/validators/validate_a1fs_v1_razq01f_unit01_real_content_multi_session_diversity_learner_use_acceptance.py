#!/usr/bin/env python3
"""Independently validate RAZQ01F multi-session reconciliation and use."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_v1_razq01e_unit01_admitted_content_asset_qb_consumer_workbench
    as binding_consumer,
)
from ulga.builders import (
    build_a1fs_v1_razq01e_unit01_approved_content_existing_qb_learner_stimulus_runtime
    as extension_runtime,
)
from ulga.builders import (
    build_a1fs_v1_razq01f_unit01_real_content_multi_session_diversity_learner_use_acceptance
    as builder,
)
from ulga.builders import u01qb03_renderer_runtime_impl as renderer

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_RAZQ01F_UNIT01_MULTI_SESSION_RECONCILIATION_VALIDATOR"
PASS_STATUS = "PASS_A1FS_V1_RAZQ01F_MULTI_SESSION_VALIDATION"
FAIL_STATUS = "FAIL_A1FS_V1_RAZQ01F_MULTI_SESSION_VALIDATION"
EXPECTED_RAZQ01E_TABLES = {"razq01e_metadata", "razq01e_extension_items"}


class MultiSessionValidationError(ValueError):
    """Raised for deterministic RAZQ01F validation failures."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise MultiSessionValidationError(code)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MultiSessionValidationError(f"json_unreadable:{path}:{exc}") from exc
    require(isinstance(value, dict), f"json_object_required:{path}")
    return value


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _file_hashes(output_root: Path, manifest: Mapping[str, Any]) -> None:
    files = manifest.get("files") or {}
    require(
        set(files) == {"session.private.json", "index.html", "styles.css", "app.js"},
        "manifest_file_set_invalid",
    )
    for name, metadata in files.items():
        path = output_root / name
        require(path.is_file(), f"workbench_file_missing:{name}")
        raw = path.read_bytes()
        require(
            metadata.get("sha256") == hashlib.sha256(raw).hexdigest(),
            f"workbench_file_hash_invalid:{name}",
        )
        require(metadata.get("bytes") == len(raw), f"workbench_file_size_invalid:{name}")
    require(
        (output_root / "index.html").read_text(encoding="utf-8") == renderer.HTML,
        "existing_renderer_html_drift",
    )
    require(
        (output_root / "styles.css").read_text(encoding="utf-8") == renderer.CSS,
        "existing_renderer_css_drift",
    )
    require(
        (output_root / "app.js").read_text(encoding="utf-8") == renderer.JS,
        "existing_renderer_js_drift",
    )


def _extension_map(connection: sqlite3.Connection, session_id: str) -> dict[str, str]:
    return {
        str(item_id): str(content_asset_id)
        for item_id, content_asset_id in connection.execute(
            """SELECT s.item_id,e.content_asset_id
            FROM u01qb02_session_items s
            JOIN razq01e_extension_items e USING(item_id)
            WHERE s.session_id=?""",
            (session_id,),
        )
    }


def _private_items(
    connection: sqlite3.Connection, item_ids: Sequence[str]
) -> dict[str, dict[str, Any]]:
    placeholders = ",".join("?" for _ in item_ids)
    rows = connection.execute(
        f"SELECT item_id,private_item_json FROM u01qb02_item_catalog "
        f"WHERE item_id IN ({placeholders})",
        tuple(item_ids),
    ).fetchall()
    values = {
        str(item_id): json.loads(private_item_json)
        for item_id, private_item_json in rows
    }
    require(set(values) == set(item_ids), "private_item_binding_incomplete")
    return values


def _validate_item(
    *,
    item: Mapping[str, Any],
    private_item: Mapping[str, Any],
    asset: Mapping[str, Any],
    authoritative_extension_asset_id: str | None,
) -> str:
    binding = item.get("content_binding") or {}
    item_id = str(item.get("item_id") or "")
    asset_id = str(binding.get("content_asset_id") or "")
    require(asset_id == asset.get("content_asset_id"), f"binding_asset_invalid:{item_id}")
    require(
        binding.get("content_sha256") == asset.get("content_sha256"),
        f"binding_content_digest_invalid:{item_id}",
    )
    require(
        binding.get("matched_skill") == item.get("skill"),
        f"binding_skill_invalid:{item_id}",
    )
    require(
        binding.get("matched_family_id") == item.get("pattern_family_id"),
        f"binding_family_invalid:{item_id}",
    )
    expected = binding_consumer.compatibility(item, private_item, asset)
    require(expected is not None, f"binding_incompatible:{item_id}")
    require(
        binding.get("compatibility_mode") == expected.get("mode")
        and binding.get("compatibility_score") == expected.get("score")
        and binding.get("exact_family_match") == expected.get("exact_family")
        and binding.get("pattern_match") == expected.get("pattern_match")
        and binding.get("noun_match") == expected.get("noun_match")
        and binding.get("adjective_match") == expected.get("adjective_match"),
        f"binding_compatibility_drift:{item_id}",
    )

    if authoritative_extension_asset_id is not None:
        require(
            asset_id == authoritative_extension_asset_id,
            f"extension_identity_asset_drift:{item_id}",
        )
        require(
            binding.get("binding_authority") == "RAZQ01E_EXTENSION_ITEM_IDENTITY",
            f"extension_identity_authority_invalid:{item_id}",
        )
    else:
        require(
            binding.get("binding_authority") == "RAZQ01E_COMPATIBILITY_SELECTION",
            f"base_item_binding_authority_invalid:{item_id}",
        )

    approved_stimulus = binding_consumer.content_text(asset)
    original_stimulus = str(private_item.get("stimulus") or "").strip()
    require(
        item.get("content_asset_stimulus") == approved_stimulus,
        f"approved_stimulus_invalid:{item_id}",
    )
    require(
        item.get("question_stimulus") == original_stimulus,
        f"question_stimulus_invalid:{item_id}",
    )
    visible = str(item.get("stimulus") or "")
    require(approved_stimulus in visible, f"approved_stimulus_not_visible:{item_id}")
    if original_stimulus:
        require(original_stimulus in visible, f"question_stimulus_not_visible:{item_id}")
    return asset_id


def validate(
    *,
    database: Path,
    approved_content: Mapping[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    details: dict[str, Any] = {}
    try:
        database = Path(database)
        output_root = Path(output_root)
        require(database.is_file(), "learner_database_missing")
        report = load(output_root / "razq01f_multisession_readback.json")
        core = {key: value for key, value in report.items() if key != "readback_sha256"}
        require(report.get("readback_sha256") == digest(core), "readback_digest_invalid")
        require(report.get("task_id") == builder.TASK_ID, "report_task_invalid")
        require(report.get("schema_version") == builder.SCHEMA_VERSION, "report_schema_invalid")
        require(report.get("status") == builder.PASS_STATUS, "report_status_invalid")
        require(report.get("session_count") == builder.SESSION_COUNT, "session_count_invalid")
        require(report.get("session_size") == builder.SESSION_SIZE, "session_size_invalid")
        require(
            report.get("approved_content_artifact_sha256")
            == approved_content.get("artifact_sha256"),
            "approved_content_binding_invalid",
        )
        _payload, assets = binding_consumer.validate_approved_content(approved_content)
        assets_by_id = {str(row["content_asset_id"]): row for row in assets}

        sessions = report.get("sessions") or []
        require(len(sessions) == builder.SESSION_COUNT, "session_report_count_invalid")
        all_items: set[str] = set()
        all_assets: set[str] = set()
        expected_exposures = 0
        expected_attempts = 0

        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        try:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            require(EXPECTED_RAZQ01E_TABLES.issubset(tables), "razq01e_authority_tables_missing")
            require(
                not {name for name in tables if name.startswith("razq01f")},
                "parallel_razq01f_runtime_table_created",
            )
            runtime_metadata = dict(
                connection.execute("SELECT key,value FROM razq01e_metadata")
            )
            require(
                runtime_metadata.get("validation_status") == extension_runtime.PASS_STATUS,
                "extension_runtime_status_invalid",
            )
            require(
                runtime_metadata.get("combined_runtime_item_count") == "474",
                "combined_runtime_count_invalid",
            )

            for expected_index, session_report in enumerate(sessions, 1):
                require(
                    session_report.get("session_index") == expected_index,
                    f"session_index_invalid:{expected_index}",
                )
                session_id = str(session_report.get("session_id") or "")
                session_root = output_root / f"session_{expected_index:02d}"
                manifest = load(session_root / "manifest.json")
                bundle = load(session_root / "session.private.json")
                require(manifest.get("task_id") == builder.TASK_ID, f"manifest_task_invalid:{session_id}")
                require(manifest.get("validation_status") == builder.PASS_STATUS, f"manifest_status_invalid:{session_id}")
                require(bundle.get("task_id") == builder.TASK_ID, f"bundle_task_invalid:{session_id}")
                require(bundle.get("validation_status") == builder.PASS_STATUS, f"bundle_status_invalid:{session_id}")
                require(bundle.get("session_id") == session_id, f"bundle_session_invalid:{session_id}")
                require(bundle.get("item_count") == builder.SESSION_SIZE, f"bundle_item_count_invalid:{session_id}")
                require(bundle.get("content_consumer_reconciled") is True, f"bundle_not_reconciled:{session_id}")
                require(
                    bundle.get("content_runtime_authority_task_id")
                    == extension_runtime.TASK_ID,
                    f"extension_runtime_binding_invalid:{session_id}",
                )
                require(
                    bundle.get("content_binding_consumer_task_id")
                    == binding_consumer.TASK_ID,
                    f"binding_consumer_binding_invalid:{session_id}",
                )
                renderer._assert_safe(bundle)
                require(
                    not any(
                        key in canonical(bundle)
                        for key in binding_consumer.PRIVATE_LINEAGE_KEYS
                    ),
                    f"private_raz_lineage_exposed:{session_id}",
                )
                _file_hashes(session_root, manifest)

                items = [dict(row) for row in bundle.get("items") or []]
                item_ids = [str(row["item_id"]) for row in items]
                require(
                    len(item_ids) == builder.SESSION_SIZE
                    and len(set(item_ids)) == builder.SESSION_SIZE,
                    f"session_item_distinctness_invalid:{session_id}",
                )
                private_items = _private_items(connection, item_ids)
                extension_map = _extension_map(connection, session_id)
                bound_asset_ids: list[str] = []
                extension_identity_count = 0
                for item in items:
                    binding = item.get("content_binding") or {}
                    asset_id = str(binding.get("content_asset_id") or "")
                    asset = assets_by_id.get(asset_id)
                    require(asset is not None, f"bound_asset_missing:{session_id}:{asset_id}")
                    authoritative_id = extension_map.get(str(item["item_id"]))
                    if authoritative_id is not None:
                        extension_identity_count += 1
                    bound_asset_ids.append(
                        _validate_item(
                            item=item,
                            private_item=private_items[str(item["item_id"])],
                            asset=asset,
                            authoritative_extension_asset_id=authoritative_id,
                        )
                    )
                require(
                    len(set(bound_asset_ids)) == builder.SESSION_SIZE,
                    f"session_content_distinctness_invalid:{session_id}",
                )
                require(
                    extension_identity_count >= builder.MIN_EXTENSION_ITEMS_PER_SESSION,
                    f"session_extension_identity_quota_invalid:{session_id}",
                )
                require(
                    session_report.get("authoritative_extension_content_count")
                    == extension_identity_count,
                    f"session_extension_report_drift:{session_id}",
                )
                require(
                    set(session_report.get("item_ids") or []) == set(item_ids),
                    f"session_item_report_drift:{session_id}",
                )
                require(
                    set(session_report.get("content_asset_ids") or [])
                    == set(bound_asset_ids),
                    f"session_content_report_drift:{session_id}",
                )

                plan_count = connection.execute(
                    "SELECT COUNT(*) FROM u01qb02_session_plans WHERE session_id=?",
                    (session_id,),
                ).fetchone()[0]
                exposure_count = connection.execute(
                    "SELECT COUNT(*) FROM u01qb02_item_exposures WHERE session_id=?",
                    (session_id,),
                ).fetchone()[0]
                attempt_count = connection.execute(
                    "SELECT COUNT(*) FROM response_attempts WHERE session_id=?",
                    (session_id,),
                ).fetchone()[0]
                pass_count = connection.execute(
                    """SELECT COUNT(*) FROM scoring_results r
                    JOIN response_attempts a USING(attempt_id)
                    WHERE a.session_id=? AND r.outcome='AUTO_PASS'""",
                    (session_id,),
                ).fetchone()[0]
                require(plan_count == 1, f"session_plan_count_invalid:{session_id}")
                require(exposure_count == builder.SESSION_SIZE, f"session_exposure_count_invalid:{session_id}")
                require(attempt_count == 1 and pass_count == 1, f"session_attempt_invalid:{session_id}")
                require(
                    session_report.get("attempt_outcome") == "AUTO_PASS",
                    f"session_attempt_report_invalid:{session_id}",
                )
                require(
                    session_report.get("evidence_attempt_count") == 1,
                    f"session_evidence_count_invalid:{session_id}",
                )
                all_items.update(item_ids)
                all_assets.update(bound_asset_ids)
                expected_exposures += exposure_count
                expected_attempts += attempt_count
        finally:
            connection.close()

        require(
            expected_exposures == builder.EXPECTED_EXPOSURE_COUNT,
            "aggregate_exposure_count_invalid",
        )
        require(
            expected_attempts == builder.EXPECTED_ATTEMPT_COUNT,
            "aggregate_attempt_count_invalid",
        )
        require(
            len(all_items) >= builder.MIN_DISTINCT_ITEMS_ACROSS_SESSIONS,
            f"aggregate_item_diversity_invalid:{len(all_items)}",
        )
        require(
            len(all_assets)
            >= builder.MIN_DISTINCT_CONTENT_ASSETS_ACROSS_SESSIONS,
            f"aggregate_content_diversity_invalid:{len(all_assets)}",
        )
        require(
            report.get("exposure_count") == expected_exposures,
            "report_exposure_count_invalid",
        )
        require(
            report.get("attempt_count") == expected_attempts
            and report.get("auto_pass_count") == expected_attempts,
            "report_attempt_count_invalid",
        )
        require(
            report.get("distinct_item_count_across_sessions") == len(all_items),
            "report_item_diversity_invalid",
        )
        require(
            report.get("distinct_content_asset_count_across_sessions")
            == len(all_assets),
            "report_content_diversity_invalid",
        )
        boundaries = report.get("boundaries") or {}
        require(boundaries.get("unit01_only") is True, "unit01_boundary_invalid")
        for key in (
            "second_question_bank_created",
            "parallel_runtime_table_created",
            "parallel_renderer_created",
            "parallel_response_capture_created",
            "parallel_scoring_created",
            "unit02_to_unit24_modified",
            "audio_enabled",
            "speaking_capture_enabled",
            "a2_unlocked",
            "mastery_claimed",
        ):
            require(boundaries.get(key) is False, f"boundary_invalid:{key}")

        details = {
            "session_count": len(sessions),
            "exposure_count": expected_exposures,
            "attempt_count": expected_attempts,
            "auto_pass_count": expected_attempts,
            "distinct_item_count_across_sessions": len(all_items),
            "distinct_content_asset_count_across_sessions": len(all_assets),
            "combined_runtime_item_count": report["combined_runtime_item_count"],
            "readback_sha256": report["readback_sha256"],
        }
    except Exception as exc:
        errors.append(str(exc))

    return {
        "validator_id": VALIDATOR_ID,
        "validation_status": PASS_STATUS if not errors else FAIL_STATUS,
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
    parser.add_argument("--output-root", type=Path, default=builder.DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    report = validate(
        database=args.database,
        approved_content=builder.load(args.approved_content),
        output_root=args.output_root,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
