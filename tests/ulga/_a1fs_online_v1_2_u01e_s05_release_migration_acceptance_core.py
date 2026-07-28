from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from tests.ulga import test_a1fs_v1_1_m02_unit01_local_product_acceptance_release as v11
from ulga.builders import build_a1fs_v1_1_m02f_exact_sequence_learner_submission_fullfix as fullfix
from ulga.builders import build_a1fs_online_v1_r01_self_contained_product_root_update_channel as r01
from ulga.builders import build_a1fs_online_v1_2_u01e_s05_release_migration_acceptance as builder
from ulga.builders import _a1fs_online_v1_2_u01e_s05_static as static_adapter
from ulga.validators import validate_a1fs_online_v1_2_u01e_s05_release_migration_acceptance as validator


def m1_graph() -> dict:
    required = [f"REQ:{index:03d}" for index in range(553)]
    skills = ("LISTENING", "SPEAKING", "READING", "WRITING")
    return {
        "task_id": "A1FS-V1-M1_A1A1PlusPrerequisiteGraphAndCoverage",
        "validation_status": "PASS_A1FS_V1_M1_PREREQUISITE_GRAPH_AND_COVERAGE",
        "counts": {
            "required_mastery_node_count": 553,
            "a2_handoff_lesson_count": 165,
            "uncovered_required_node_count": 0,
        },
        "a2_lock_contract": {
            "required_mastery_node_ids": required,
            "state": "LOCKED_BY_DESIGN",
            "runtime_unlock_implemented": False,
        },
        "nodes": [
            {
                "node_id": node_id,
                "skill": skills[index % 4],
                "node_type": "CAPABILITY",
                "level": "A1" if index % 2 == 0 else "A1+",
            }
            for index, node_id in enumerate(required)
        ],
    }


def augment_database(root: Path, bundles: dict) -> None:
    database = root / "shared/database/learner_runtime.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS lesson_catalog(
              lesson_id TEXT PRIMARY KEY,lesson_node_id TEXT NOT NULL UNIQUE,
              skill TEXT NOT NULL,level TEXT NOT NULL,roles_json TEXT NOT NULL,
              requirement_node_ids_json TEXT NOT NULL,payload_access_allowed INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS lesson_assets(
              asset_key TEXT PRIMARY KEY,asset_id TEXT NOT NULL,lesson_id TEXT NOT NULL,
              role TEXT NOT NULL,content_digest TEXT NOT NULL,UNIQUE(lesson_id,asset_key)
            );
            CREATE TABLE IF NOT EXISTS learner_profiles(
              learner_id TEXT PRIMARY KEY,display_label TEXT NOT NULL,locale TEXT NOT NULL,
              timezone_name TEXT NOT NULL,profile_state TEXT NOT NULL,profile_version INTEGER NOT NULL,
              created_at TEXT NOT NULL,updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS learning_sessions(
              session_id TEXT PRIMARY KEY,learner_id TEXT NOT NULL,lesson_id TEXT NOT NULL,
              skill TEXT NOT NULL,level TEXT NOT NULL,session_state TEXT NOT NULL,
              session_version INTEGER NOT NULL,started_at TEXT NOT NULL,ended_at TEXT
            );
            CREATE TABLE IF NOT EXISTS lesson_progress(
              learner_id TEXT NOT NULL,lesson_id TEXT NOT NULL,skill TEXT NOT NULL,level TEXT NOT NULL,
              progress_state TEXT NOT NULL,exposure_count INTEGER NOT NULL,progress_version INTEGER NOT NULL,
              first_seen_at TEXT,last_seen_at TEXT,PRIMARY KEY(learner_id,lesson_id)
            );
            CREATE TABLE IF NOT EXISTS state_events(
              event_seq INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT NOT NULL UNIQUE,
              learner_id TEXT NOT NULL,session_id TEXT,event_type TEXT NOT NULL,event_at TEXT NOT NULL,
              payload_json TEXT NOT NULL,previous_hash TEXT NOT NULL,event_hash TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS response_attempts(
              attempt_id TEXT PRIMARY KEY,learner_id TEXT NOT NULL,session_id TEXT NOT NULL,
              lesson_id TEXT NOT NULL,asset_key TEXT NOT NULL,attempt_sequence INTEGER NOT NULL,
              response_json TEXT NOT NULL,submitted_at TEXT NOT NULL,previous_hash TEXT NOT NULL,
              attempt_hash TEXT NOT NULL UNIQUE,UNIQUE(session_id,asset_key,attempt_sequence)
            );
            CREATE TABLE IF NOT EXISTS scoring_results(
              attempt_id TEXT PRIMARY KEY,scoring_mode TEXT NOT NULL,outcome TEXT NOT NULL,
              score REAL,human_review_required INTEGER NOT NULL,scored_at TEXT NOT NULL,
              contract_digest TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS human_review_queue(
              attempt_id TEXT PRIMARY KEY,decision TEXT NOT NULL,reviewer_id TEXT,reviewed_at TEXT,
              criteria_json TEXT NOT NULL,notes TEXT
            );
            """
        )
        for lesson_id, bundle in bundles.items():
            lesson = bundle["lesson"]
            connection.execute(
                "INSERT OR IGNORE INTO lesson_catalog VALUES(?,?,?,?,?,?,?)",
                (
                    lesson_id,
                    f"LESSON:{lesson_id}",
                    lesson["skill"],
                    lesson.get("level", "A1"),
                    json.dumps(sorted({row["role"] for row in bundle["assets"]})),
                    "[]",
                    1,
                ),
            )
            for asset in bundle["assets"]:
                connection.execute(
                    "INSERT OR IGNORE INTO lesson_assets VALUES(?,?,?,?,?)",
                    (
                        asset["asset_key"],
                        asset.get("asset_id", asset["asset_key"]),
                        lesson_id,
                        asset["role"],
                        r01.digest(asset),
                    ),
                )
        connection.commit()


def source_v111_root(tmp_path: Path) -> Path:
    root = v11.installed_v110_root(tmp_path)
    output = tmp_path / "v111/m02f.private.json"
    report = tmp_path / "v111/m02f.safe.json"
    receipt, _ = fullfix.materialize(product_root=root, output_path=output, report_path=report)
    r01.install_candidate(
        product_root=root,
        candidate=Path(receipt["runtime_outputs"]["candidate_root"]),
        version=builder.SOURCE_VERSION,
    )
    assert r01._current_version(root) == builder.SOURCE_VERSION
    _, manifest, bundles, _ = r01._load_product(root)
    augment_database(root, bundles)
    release = root / f"releases/{builder.SOURCE_VERSION}"
    static = r01._resolve(root, str(manifest["secure_static_root"]))
    (static / "index.html").write_text(
        "<html><body><main><section id='app'></section></main></body></html>\n",
        encoding="utf-8",
    )
    graph = r01._resolve(root, str(manifest["graph_path"]))
    graph.write_text(json.dumps(m1_graph()), encoding="utf-8")
    r01._write_checksums(release)
    r01.validate_release(release)
    return root


def fake_acceptance(*, product_root: Path, source, overlay, static_result, screenshot_path: Path):
    version, manifest, bundles, _ = r01._load_product(product_root)
    assert version == builder.TARGET_VERSION
    assert manifest["asset_count"] == 277
    counts = {
        skill: len(bundles[builder.m01.LESSON_IDS[skill]]["assets"])
        for skill in builder.EXPECTED_UNIT01_COUNTS
    }
    assert counts == builder.EXPECTED_UNIT01_COUNTS
    database = product_root / "shared/database/learner_runtime.sqlite3"
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM lesson_assets WHERE asset_key LIKE 'U01E-S03-%'"
        ).fetchone()[0] == 13
        assert connection.execute(
            "SELECT COUNT(*) FROM response_contracts WHERE asset_key LIKE 'U01E-S03-%'"
        ).fetchone()[0] == 13
        assert connection.execute(
            "SELECT COUNT(*) FROM u01e_asset_target_bindings"
        ).fetchone()[0] == 24
    rollback = builder.v1_1_rollback_acceptance(
        product_root=product_root,
        migrated_database=database,
    )
    return {
        "installed_version": "1.2.0",
        "unit_count": 24,
        "lesson_count": 72,
        "asset_count": 277,
        "unit01_activity_count": 24,
        "unit01_counts": builder.EXPECTED_UNIT01_COUNTS,
        "context_count": 5,
        "question_type_count": 8,
        "reading": {
            "lesson_id": builder.m01.LESSON_IDS["READING"],
            "contract_count": 10,
            "pending_human_review_count": 0,
            "completion_allowed": True,
            "session_completed": True,
        },
        "writing": {
            "lesson_id": builder.m01.LESSON_IDS["WRITING"],
            "contract_count": 8,
            "pending_human_review_count": 2,
            "completion_allowed": True,
            "session_completed": True,
        },
        "speaking_practice_card_count": 6,
        "coverage_before_practised_item_count": 0,
        "coverage_after_practised_item_count": 18,
        "coverage_distinct_attempt_semantics_pass": True,
        "http": {
            "authenticated_login_pass": True,
            "bootstrap_pass": True,
            "progress_pass": True,
            "coverage_endpoint_pass": True,
            "unit_count": 24,
            "unit01_activity_count": 24,
            "practised_item_count": 18,
        },
        "static_surface": dict(static_result),
        "visual": {
            "status": "NOT_AVAILABLE_IN_EXECUTION_ENVIRONMENT",
            "browser": None,
            "screenshot_created": False,
            "dom_contract_pass": True,
        },
        "rollback": rollback,
        "speaking_capture_enabled": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "a2_unlocked": False,
    }


def test_runtime_overlay_is_fixed_24_item_bank_and_exposes_no_answers(tmp_path: Path) -> None:
    root = source_v111_root(tmp_path)
    source = builder.source_product(root)
    overlay = builder.build_runtime_overlay(source)
    assert overlay["unit01_counts"] == {"READING": 10, "WRITING": 8, "SPEAKING": 6}
    assert overlay["asset_count"] == 277
    assert len(overlay["assets"]) == 13
    assert len(overlay["contracts"]) == 13
    assert len(overlay["target_registry"]) == 24
    assert all(row["runtime_status"] == "RUNTIME_ACTIVE" for row in overlay["target_registry"])
    learner_encoded = json.dumps(overlay["assets"], ensure_ascii=False, sort_keys=True)
    for forbidden in ("accepted_texts", "accepted_sequence", "correct_answer", "answerability_evidence"):
        assert forbidden not in learner_encoded
    contracts_encoded = json.dumps(overlay["contracts"], ensure_ascii=False, sort_keys=True)
    assert "accepted_texts" in contracts_encoded
    assert all(asset["learner_payload"]["runtime_generation_used"] is False for asset in overlay["assets"])


def test_static_surface_supports_sequence_by_response_type_and_coverage_panel(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "index.html").write_text("<html><body><main></main></body></html>", encoding="utf-8")
    (source / "app.js").write_text(
        "const serializeTextResponse=(asset,value)=>{const trimmed=value.trim();"
        "if(asset.learner_payload.writing_stage==='CONTROLLED_SEQUENCE')"
        "return trimmed.split(/\\s+/);return value};"
        "const options=asset.learner_payload.options||[];",
        encoding="utf-8",
    )
    (source / "styles.css").write_text("body{}", encoding="utf-8")
    result = static_adapter.patch_static(source, tmp_path / "target")
    assert result["coverage_panel_visible_contract"] is True
    assert result["sequence_response_type_supported"] is True
    assert result["token_bank_renderer_present"] is True
    assert result["hidden_answers_absent"] is True


def test_dynamic_completion_gate_accepts_10_and_8_contract_bundles(tmp_path: Path) -> None:
    database = tmp_path / "dynamic.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE learning_sessions(
              session_id TEXT PRIMARY KEY,lesson_id TEXT NOT NULL,skill TEXT NOT NULL,
              session_state TEXT NOT NULL,session_version INTEGER NOT NULL
            );
            CREATE TABLE response_contracts(
              asset_key TEXT PRIMARY KEY,contract_json TEXT NOT NULL,capture_enabled INTEGER NOT NULL
            );
            CREATE TABLE response_attempts(
              attempt_id TEXT PRIMARY KEY,session_id TEXT NOT NULL,asset_key TEXT NOT NULL,
              attempt_sequence INTEGER NOT NULL
            );
            CREATE TABLE scoring_results(attempt_id TEXT PRIMARY KEY,outcome TEXT NOT NULL);
            """
        )
        bundles = {}
        for skill, count in (("READING", 10), ("WRITING", 8)):
            lesson_id = builder.m01.LESSON_IDS[skill]
            session_id = f"SESSION:{skill}"
            connection.execute(
                "INSERT INTO learning_sessions VALUES(?,?,?,?,?)",
                (session_id, lesson_id, skill, "ACTIVE", 1),
            )
            assets = []
            for index in range(1, count + 1):
                key = f"{skill}:{index}"
                assets.append({"asset_key": key})
                connection.execute(
                    "INSERT INTO response_contracts VALUES(?,?,1)",
                    (key, json.dumps({"scoring_mode": "EXACT_OPTION", "human_review_fallback": False})),
                )
                attempt = f"ATTEMPT:{skill}:{index}"
                connection.execute(
                    "INSERT INTO response_attempts VALUES(?,?,?,1)",
                    (attempt, session_id, key),
                )
                connection.execute(
                    "INSERT INTO scoring_results VALUES(?,?)",
                    (attempt, "AUTO_PASS"),
                )
            bundles[lesson_id] = {"assets": assets}
        connection.commit()
    app = object.__new__(builder.V12Application)
    app.database_path = database
    app.lesson_bundles = bundles
    reading = app.completion_readiness("SESSION:READING")
    writing = app.completion_readiness("SESSION:WRITING")
    assert reading["required_response_count"] == 10
    assert writing["required_response_count"] == 8
    assert reading["completion_allowed"] is True
    assert writing["completion_allowed"] is True


def test_materialize_preserves_production_and_proves_update_and_rollback(tmp_path: Path) -> None:
    root = source_v111_root(tmp_path)
    before = builder.m02_core.shared_identity(root)
    receipt, safe = builder.materialize(
        product_root=root,
        code_root=Path(__file__).resolve().parents[2],
        output_path=tmp_path / "out/s05.private.json",
        report_path=tmp_path / "out/s05.safe.json",
        acceptance_runner=fake_acceptance,
    )
    report = validator.validate_outputs(receipt, safe)
    assert report["error_count"] == 0, report
    assert r01._current_version(root) == "1.1.1"
    assert builder.m02_core.shared_identity(root) == before
    assert receipt["release_summary"]["target_asset_count"] == 277
    assert receipt["migration_summary"]["legacy_schema_unchanged"] is True
    assert receipt["recovery_summary"]["failed_update_automatic_rollback_pass"] is True
    assert receipt["recovery_summary"]["explicit_v1_1_rollback_pass"] is True
    candidate = Path(receipt["runtime_outputs"]["candidate_root"])
    manifest = r01.validate_release(candidate)
    assert manifest["product_version"] == "1.2.0"
    assert manifest["asset_count"] == 277
    assert manifest["runtime_free_generation_allowed"] is False
    assert manifest["serve_module"] == builder.MODULE


def test_migration_failure_restores_exact_v111_shared_state(tmp_path: Path) -> None:
    root = source_v111_root(tmp_path)
    source = builder.source_product(root)
    overlay = builder.build_runtime_overlay(source)
    candidate, _ = builder.build_candidate_release(
        source=source,
        overlay=overlay,
        package_root=tmp_path / "pkg",
        code_root=Path(__file__).resolve().parents[2],
    )
    acceptance = builder.m02_core.build_acceptance_root(
        product_root=root,
        target_root=tmp_path / "failed",
    )
    before = builder.m02_core.shared_identity(acceptance)
    with pytest.raises(builder.S05ReleaseError, match="injected_migration_failure"):
        builder.install_with_migration(
            product_root=acceptance,
            candidate=candidate,
            overlay=overlay,
            inject_failure=True,
        )
    assert r01._current_version(acceptance) == "1.1.1"
    assert builder.m02_core.shared_identity(acceptance) == before
    assert not (acceptance / "releases/1.2.0").exists()
