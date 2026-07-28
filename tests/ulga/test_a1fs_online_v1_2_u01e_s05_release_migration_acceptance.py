from __future__ import annotations

import json
import os
import sqlite3
from copy import deepcopy
from pathlib import Path

from tests.ulga._a1fs_online_v1_2_u01e_s05_release_migration_acceptance_core import *  # noqa: F401,F403
from ulga.builders import build_a1fs_online_v1_s05_private_learner_identity_progress_persistence as v1_s05
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import (
    build_a1fs_online_v1_2_u01e_local_production_install_operator_acceptance as operator,
)


_FIXTURE_SOURCE_V111_ROOT = source_v111_root


def canonical_source_v111_root(tmp_path: Path) -> Path:
    root = _FIXTURE_SOURCE_V111_ROOT(tmp_path)
    version, manifest, bundles, sequence = r01._load_product(root)
    canonical_ids = [
        grammar_id
        for grammar_id, _ in sorted(
            builder.s17.s16.s15.s14.UNIT_LABELS.items(),
            key=lambda row: row[1]["sequence_index"],
        )
    ]
    old_ids = [
        grammar_id
        for grammar_id, _ in sorted(sequence.items(), key=lambda row: row[1])
    ]
    mapping = dict(zip(old_ids, canonical_ids, strict=True))
    canonical_bundles: dict[str, dict] = {}
    lesson_mapping: dict[str, str] = {}
    for old_lesson_id, source_bundle in bundles.items():
        parts = old_lesson_id.split(":")
        old_grammar_id = parts[-2]
        skill = parts[-1]
        new_grammar_id = mapping[old_grammar_id]
        new_lesson_id = f"A1FS_ONLINE_V1:{new_grammar_id}:{skill}"
        bundle = deepcopy(source_bundle)
        bundle["lesson"]["lesson_id"] = new_lesson_id
        canonical_bundles[new_lesson_id] = bundle
        lesson_mapping[old_lesson_id] = new_lesson_id
    canonical_sequence = {
        grammar_id: index
        for index, grammar_id in enumerate(canonical_ids, start=1)
    }
    bundle_path = r01._resolve(root, str(manifest["bundle_registry_path"]))
    sequence_path = r01._resolve(root, str(manifest["sequence_path"]))
    bundle_path.write_text(
        json.dumps(canonical_bundles, ensure_ascii=False), encoding="utf-8"
    )
    sequence_path.write_text(
        json.dumps(canonical_sequence, ensure_ascii=False), encoding="utf-8"
    )
    database = root / "shared/database/learner_runtime.sqlite3"
    with sqlite3.connect(database) as connection:
        for old_lesson_id, new_lesson_id in lesson_mapping.items():
            if old_lesson_id == new_lesson_id:
                continue
            connection.execute(
                "UPDATE lesson_catalog SET lesson_id=?,lesson_node_id=? WHERE lesson_id=?",
                (new_lesson_id, f"LESSON:{new_lesson_id}", old_lesson_id),
            )
            connection.execute(
                "UPDATE lesson_assets SET lesson_id=? WHERE lesson_id=?",
                (new_lesson_id, old_lesson_id),
            )
        connection.commit()
    release = root / f"releases/{version}"
    r01._write_checksums(release)
    r01.validate_release(release)
    return root


def test_real_runtime_login_scored_journeys_coverage_and_rollback(tmp_path: Path) -> None:
    root = canonical_source_v111_root(tmp_path)
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


def test_local_operator_acceptance_is_read_only_and_scripts_use_candidate_app(
    tmp_path: Path, monkeypatch,
) -> None:
    root = tmp_path / "A1FS_V1"
    (root / "releases/1.2.0").mkdir(parents=True)
    (root / "shared/database").mkdir(parents=True)
    (root / "shared/state").mkdir(parents=True)
    (root / "shared").mkdir(exist_ok=True)
    (root / "current_version.txt").write_text("1.2.0\n", encoding="ascii")
    (root / "shared/auth.json").write_text("{}\n", encoding="utf-8")
    (root / "shared/graph.json").write_text("{}\n", encoding="utf-8")
    static = root / "releases/1.2.0/static"
    static.mkdir(parents=True)
    (static / "index.html").write_text("<html></html>", encoding="utf-8")
    (static / "app.js").write_text("console.log('v1.2');", encoding="utf-8")

    sequence = {f"GRAMMAR_{index:02d}": index for index in range(1, 25)}
    bundles: dict[str, dict] = {}
    for skill, lesson_id in operator.s05.m01.LESSON_IDS.items():
        bundles[lesson_id] = {"assets": []}
        for index in range(operator.EXPECTED_UNIT01_COUNTS[skill]):
            bundles[lesson_id]["assets"].append(
                {"asset_key": f"UNIT01:{skill}:{index:02d}"}
            )
    for index in range(69):
        bundles[f"A1FS_ONLINE_V1:OTHER_{index:02d}:READING"] = {"assets": []}
    remaining = operator.EXPECTED_ASSET_COUNT - operator.EXPECTED_UNIT01_ACTIVITY_COUNT
    other_lesson = next(
        lesson_id for lesson_id in bundles if lesson_id not in operator.s05.m01.LESSON_IDS.values()
    )
    bundles[other_lesson]["assets"] = [
        {"asset_key": f"OTHER:{index:03d}"} for index in range(remaining)
    ]
    assert len(bundles) == operator.EXPECTED_LESSON_COUNT

    database = root / "shared/database/learner_runtime.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE u01e_coverage_denominators(
              coverage_key TEXT PRIMARY KEY,
              denominator_count INTEGER NOT NULL,
              denominator_status TEXT NOT NULL,
              source_json TEXT NOT NULL,
              source_digest TEXT NOT NULL
            );
            CREATE TABLE u01e_asset_target_bindings(
              item_key TEXT PRIMARY KEY,
              unit_id TEXT NOT NULL,
              skill TEXT NOT NULL,
              question_type TEXT NOT NULL,
              runtime_status TEXT NOT NULL,
              target_json TEXT NOT NULL,
              binding_digest TEXT NOT NULL
            );
            CREATE TABLE u01e_learner_coverage_snapshots(
              snapshot_id TEXT PRIMARY KEY,
              learner_id TEXT NOT NULL,
              source_database_sha256 TEXT NOT NULL,
              snapshot_json TEXT NOT NULL,
              snapshot_digest TEXT NOT NULL
            );
            CREATE TABLE response_contracts(
              asset_key TEXT PRIMARY KEY,
              lesson_id TEXT NOT NULL
            );
            CREATE TABLE response_attempts(
              attempt_id TEXT PRIMARY KEY
            );
            """
        )
        connection.execute(
            "INSERT INTO u01e_coverage_denominators VALUES(?,?,?,?,?)",
            ("EVP", 625, "AVAILABLE", "{}", "denominator-digest"),
        )
        for index in range(operator.EXPECTED_UNIT01_ACTIVITY_COUNT):
            key = (
                f"U01E-S03-{index:02d}"
                if index < operator.EXPECTED_NEW_ACTIVITY_COUNT
                else f"EXISTING-{index:02d}"
            )
            if index < 10:
                lesson_id = operator.s05.m01.LESSON_IDS["READING"]
                skill = "READING"
            elif index < 18:
                lesson_id = operator.s05.m01.LESSON_IDS["WRITING"]
                skill = "WRITING"
            else:
                lesson_id = operator.s05.m01.LESSON_IDS["SPEAKING"]
                skill = "SPEAKING"
            connection.execute(
                "INSERT INTO u01e_asset_target_bindings VALUES(?,?,?,?,?,?,?)",
                (key, operator.s05.m01.UNIT_ID, skill, "FIXED", "RUNTIME_ACTIVE", "{}", f"binding-{index}"),
            )
            connection.execute(
                "INSERT INTO response_contracts VALUES(?,?)",
                (key, lesson_id),
            )
        connection.commit()

    pid_path = root / "shared/a1fs_v1.pid"
    pid_path.write_text(str(os.getpid()) + "\n", encoding="ascii")
    manifest = {
        "asset_count": operator.EXPECTED_ASSET_COUNT,
        "release_id": operator.s05.RELEASE_ID,
    }
    registry = [{"item_key": f"ITEM-{index:02d}"} for index in range(24)]
    monkeypatch.setattr(
        operator.s05,
        "_load_v12",
        lambda product_root: (
            root,
            manifest,
            bundles,
            sequence,
            database,
            root / "shared/auth.json",
            root / "shared/state",
            root / "shared/graph.json",
            static,
            registry,
        ),
    )
    monkeypatch.setattr(operator.s05.r01, "validate_release", lambda release: None)
    monkeypatch.setattr(operator.s05, "_health", lambda port: True)
    monkeypatch.setattr(operator.s05.r01, "_pid_alive", lambda pid: pid == os.getpid())

    readback = operator.operator_acceptance(
        product_root=root,
        port=8765,
        require_running=True,
    )
    assert readback["validation_status"] == operator.PASS_STATUS
    assert readback["release_summary"] == {
        "unit_count": 24,
        "lesson_count": 72,
        "asset_count": 277,
        "unit01_activity_count": 24,
        "unit01_counts": {"READING": 10, "WRITING": 8, "SPEAKING": 6},
        "context_count": 5,
        "question_type_count": 8,
    }
    assert readback["database_readback"]["read_only_probe"] is True
    assert readback["database_readback"]["asset_target_binding_count"] == 24
    assert readback["database_readback"]["new_response_contract_count"] == 13
    assert readback["operator_boundaries"]["learner_state_written"] is False

    package = tmp_path / "package"
    candidate = package / "candidate_release"
    (candidate / "app").mkdir(parents=True)
    scripts = operator.write_operator_scripts(
        package_root=package,
        candidate=candidate,
        default_port=8765,
    )
    install_text = Path(scripts["install_script"]).read_text(encoding="ascii")
    combined_text = Path(scripts["install_start_accept_script"]).read_text(encoding="ascii")
    assert "$CandidateApp" in install_text
    assert f"python -m {operator.MODULE} install" in install_text
    assert f"python -m {operator.MODULE} operator-accept" in combined_text
    assert "A1FS_V1_SESSION_SECRET=" not in combined_text
    assert "Start-Process \"http://127.0.0.1:$Port\"" in combined_text

    output = tmp_path / "operator-readback.json"
    assert operator.main(
        [
            "operator-accept",
            "--product-root",
            str(root),
            "--port",
            "8765",
            "--require-running",
            "--output",
            str(output),
        ]
    ) == 0
    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert persisted["readback_sha256"] == readback["readback_sha256"]
