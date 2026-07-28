from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from tests.ulga._a1fs_online_v1_2_u01e_s05_release_migration_acceptance_core import *  # noqa: F401,F403
from ulga.builders import build_a1fs_online_v1_s05_private_learner_identity_progress_persistence as v1_s05
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6


def test_real_runtime_login_scored_journeys_coverage_and_rollback(tmp_path: Path) -> None:
    root = source_v111_root(tmp_path)
    version, manifest, _, _ = r01._load_product(root)
    release = root / f"releases/{version}"
    graph_path = r01._resolve(root, str(manifest["graph_path"]))
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    required = list(graph["a2_lock_contract"]["required_mastery_node_ids"])
    graph["coverage"] = [
        {"node_id": node_id, "asset_body_ids": [], "lesson_ids": []}
        for node_id in required
    ]
    graph_path.write_text(json.dumps(graph, ensure_ascii=False), encoding="utf-8")
    r01._write_checksums(release)
    r01.validate_release(release)

    with sqlite3.connect(root / "shared/database/learner_runtime.sqlite3") as connection:
        connection.row_factory = sqlite3.Row
        connection.executescript(
            v1_s05.PERSISTENCE_SQL
            + """
            CREATE TABLE IF NOT EXISTS metadata(
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            """
        )
        connection.executemany(
            "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
            {
                "task_id": m3.TASK_ID,
                "schema_version": m3.SCHEMA_VERSION,
                "validation_status": m3.STATUS,
                "m6_task_id": m6.TASK_ID,
                "m6_schema_version": m6.SCHEMA_VERSION,
                "m6_validation_status": m6.STATUS,
                "response_capture_enabled": "true",
                "scoring_write_enabled": "true",
                "mastery_write_enabled": "false",
                "a2_session_enabled": "false",
            }.items(),
        )
        rows = connection.execute(
            "SELECT asset_key,lesson_id,skill,role,capture_enabled,contract_json FROM response_contracts"
        ).fetchall()
        for row in rows:
            contract = json.loads(str(row["contract_json"]))
            mode = str(contract.get("scoring_mode") or "NONE")
            contract.update(
                {
                    "asset_key": str(row["asset_key"]),
                    "lesson_id": str(row["lesson_id"]),
                    "skill": str(row["skill"]),
                    "role": str(row["role"]),
                    "capture_enabled": bool(row["capture_enabled"]),
                    "response_type": str(contract.get("response_type") or "string"),
                    "accepted_texts": list(contract.get("accepted_texts") or []),
                    "accepted_sequence": list(contract.get("accepted_sequence") or []),
                    "case_insensitive": bool(contract.get("case_insensitive", True)),
                    "punctuation_tolerance": bool(
                        contract.get("punctuation_tolerance", True)
                    ),
                    "human_review_fallback": bool(
                        contract.get("human_review_fallback", mode == "FEATURE_RUBRIC")
                    ),
                    "rubric": dict(contract.get("rubric") or {}),
                    "m12_item_id": str(
                        contract.get("m12_item_id")
                        or f"A1FS_ASSET:{row['asset_key']}"
                    ),
                    "m12_session_bank_sha256": contract.get(
                        "m12_session_bank_sha256"
                    ),
                }
            )
            connection.execute(
                "UPDATE response_contracts SET contract_json=?,contract_digest=? WHERE asset_key=?",
                (
                    json.dumps(contract, ensure_ascii=False),
                    r01.digest(contract),
                    row["asset_key"],
                ),
            )
        connection.commit()
    receipt, safe = builder.materialize(
        product_root=root,
        code_root=Path(__file__).resolve().parents[2],
        output_path=tmp_path / "real/out/s05.private.json",
        report_path=tmp_path / "real/out/s05.safe.json",
    )
    report = validator.validate_outputs(receipt, safe)
    assert report["error_count"] == 0, report
    acceptance = receipt["acceptance_summary"]
    assert acceptance["reading"]["contract_count"] == 10
    assert acceptance["reading"]["session_completed"] is True
    assert acceptance["writing"]["contract_count"] == 8
    assert acceptance["writing"]["session_completed"] is True
    assert acceptance["speaking_practice_card_count"] == 6
    assert acceptance["coverage_before_practised_item_count"] == 0
    assert acceptance["coverage_after_practised_item_count"] == 18
    assert acceptance["http"] == {
        "authenticated_login_pass": True,
        "bootstrap_pass": True,
        "progress_pass": True,
        "coverage_endpoint_pass": True,
        "unit_count": 24,
        "unit01_activity_count": 24,
        "practised_item_count": 18,
    }
    assert acceptance["visual"]["dom_contract_pass"] is True
    assert acceptance["visual"]["status"] in {
        "PASS_HEADLESS_CHROMIUM_SCREENSHOT",
        "NOT_AVAILABLE_IN_EXECUTION_ENVIRONMENT",
    }
    assert acceptance["rollback"]["v1_1_version_loaded"] is True
    assert acceptance["rollback"]["post_migration_database_readable"] is True
    assert acceptance["rollback"]["forward_switch_back_to_v1_2_pass"] is True
    assert receipt["recovery_summary"]["failed_update_automatic_rollback_pass"] is True
    assert receipt["production_safety"] == {
        "production_current_version_unchanged": True,
        "production_shared_state_unchanged": True,
        "production_legacy_rows_unchanged": True,
        "source_database_mutated": False,
        "existing_11_asset_identities_changed": False,
        "other_69_lessons_changed": False,
    }
