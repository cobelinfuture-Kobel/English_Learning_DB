from __future__ import annotations

import copy
import json
import sqlite3
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2
from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4
from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5
from ulga.builders import build_a1fs_v1_r7_planner_redeploy_reading_stimulus_runtime_projection_fullfix as fullfix
from ulga.validators import validate_a1fs_v1_r7_planner_redeploy_reading_stimulus_runtime_projection_fullfix as validator


def _item(
    item_id: str,
    cell_id: str,
    *,
    skill: str,
    response_mode: str,
    asset_id: str,
    lesson_id: str,
    content_digest: str,
    learner: dict,
) -> dict:
    candidate_sha = fullfix.digest({"candidate": item_id})
    stimulus_fingerprint = fullfix.digest(learner)
    scoring = (
        {
            "scoring_mode": "EXACT_OPTION",
            "response_type": "string",
            "accepted_texts": [learner["options"][0]],
            "case_insensitive": True,
            "punctuation_tolerance": True,
            "human_review_fallback": False,
        }
        if response_mode == "select_one"
        else {
            "scoring_mode": "NORMALIZED_TEXT",
            "response_type": "string",
            "accepted_texts": ["Park Sports Day"],
            "case_insensitive": True,
            "punctuation_tolerance": True,
            "human_review_fallback": False,
        }
    )
    return {
        "item_id": item_id,
        "breadth_cell_id": cell_id,
        "capability_id": f"CAP_{item_id}",
        "life_task_id": f"LIFE_{item_id}",
        "domain": "PERSONAL_PUBLIC_SERVICES",
        "level": "A1",
        "skill": skill,
        "purpose": "REASSESSMENT",
        "task_type": "SHORT_TEXT" if response_mode == "short_text" else "SELECT_ONE",
        "support_level": "S2_FRAME",
        "initiative_level": "GUIDED_INITIATION",
        "interaction_variation": "EXPECTED_SCRIPT",
        "transfer_distance": "NONE",
        "template_family": f"TEMPLATE_{item_id}",
        "stimulus_fingerprint": stimulus_fingerprint,
        "media_payload_state": "NOT_REQUIRED",
        "source_refs": [f"M2_ASSET:{asset_id}", f"M2_LESSON:{lesson_id}"],
        "authority_refs": [f"M2_CONTENT_DIGEST:{content_digest}"],
        "provenance": "EXISTING_AUTHORITY_REVIEWED",
        "learner_contract": learner,
        "private_scoring_contract": scoring,
        "validator_status": "PASS",
        "candidate_sha256": candidate_sha,
        "authority_review": {
            "status": "APPROVED",
            "reviewer_id": "fixture-reviewer",
            "criteria": {},
            "candidate_sha256": candidate_sha,
        },
        "admission": {
            "status": "APPROVED",
            "learner_fingerprint": stimulus_fingerprint,
            "candidate_sha256": candidate_sha,
        },
    }


def _sources() -> tuple[dict, dict, dict]:
    text_payload = {
        "body_title": "Park Sports Day",
        "body_text": "PARK SPORTS DAY\nSaturday at Green Park. Meet at the main gate at ten o'clock.",
        "teacher_delivery": "Ask the learner to identify the main message.",
        "expected_evidence": "The learner states the invitation and arrangements.",
    }
    table_payload = {
        "rows": [
            {"student": "Mia", "available": "2:00"},
            {"student": "Leo", "available": "3:30"},
        ],
        "teacher_delivery": "Ask which student cannot come before three.",
    }
    base_payload = {"prompt": "Choose the correct place."}
    assets = [
        {
            "asset_id": "R-TEXT",
            "asset_key": "READING:R-TEXT",
            "lesson_id": "KETR-RF-00-L01",
            "skill": "READING",
            "level": "A1",
            "role": "EVD",
            "payload": text_payload,
            "content_digest": fullfix.digest(text_payload),
            "release_scope": "PRIVATE_INTERNAL_D0",
        },
        {
            "asset_id": "R-TABLE",
            "asset_key": "READING:R-TABLE",
            "lesson_id": "KETR-RF-00-L02",
            "skill": "READING",
            "level": "A1",
            "role": "EVD",
            "payload": table_payload,
            "content_digest": fullfix.digest(table_payload),
            "release_scope": "PRIVATE_INTERNAL_D0",
        },
        {
            "asset_id": "R-BASE",
            "asset_key": "READING:R-BASE",
            "lesson_id": "KETR-RF-00-L03",
            "skill": "READING",
            "level": "A1",
            "role": "EVD",
            "payload": base_payload,
            "content_digest": fullfix.digest(base_payload),
            "release_scope": "PRIVATE_INTERNAL_D0",
        },
    ]
    consumer = {
        "task_id": m2.TASK_ID,
        "schema_version": m2.SCHEMA_VERSION,
        "validation_status": m2.STATUS,
        "source_graph_sha256": "9" * 64,
        "asset_records": assets,
        "lesson_catalog": [],
        "counts": {"asset_record_count": 3, "lesson_count": 3},
        "claim_boundaries": {"a2_unlocked": False},
    }
    items = [
        _item(
            "ITEM_TEXT",
            "CELL_TEXT",
            skill="READING",
            response_mode="short_text",
            asset_id="R-TEXT",
            lesson_id="KETR-RF-00-L01",
            content_digest=assets[0]["content_digest"],
            learner={
                "prompt": "State the main message and cite the words that decide your answer.",
                "response_mode": "short_text",
                "context": {},
            },
        ),
        _item(
            "ITEM_TABLE",
            "CELL_TABLE",
            skill="READING",
            response_mode="short_text",
            asset_id="R-TABLE",
            lesson_id="KETR-RF-00-L02",
            content_digest=assets[1]["content_digest"],
            learner={
                "prompt": "Which student cannot come before three o'clock?",
                "response_mode": "short_text",
                "context": {},
            },
        ),
        _item(
            "ITEM_BASE",
            "CELL_BASE",
            skill="READING",
            response_mode="select_one",
            asset_id="R-BASE",
            lesson_id="KETR-RF-00-L03",
            content_digest=assets[2]["content_digest"],
            learner={
                "prompt": "Where will the reader meet?",
                "response_mode": "select_one",
                "options": ["At the main gate.", "At the station.", "At school."],
            },
        ),
    ]
    source_bindings = {
        "ontology_sha256": "1" * 64,
        "coverage_sha256": "2" * 64,
        "candidate_registry_sha256": "3" * 64,
        "capacity_policy_registry_sha256": "4" * 64,
    }
    bank_core = {
        "task_id": r4.TASK_ID,
        "schema_version": r4.BANK_SCHEMA_VERSION,
        "validation_status": r4.STATUS,
        "private_local_only": True,
        "source_bindings": source_bindings,
        "selection_contract": {},
        "item_count": len(items),
        "items": items,
    }
    bank = {**bank_core, "bank_sha256": fullfix.digest(bank_core)}
    deployments = [
        {
            "work_item_id": f"WORK_{index}",
            "finding_id": f"FINDING_{index}",
            "breadth_cell_id": item["breadth_cell_id"],
            "selected_item_id": item["item_id"],
            "selected_candidate_sha256": item["candidate_sha256"],
            "selected_stimulus_fingerprint": item["stimulus_fingerprint"],
        }
        for index, item in enumerate(items, 1)
    ]
    deployment_core = {
        "task_id": "A1FS-V1-R7_PlannerRedeployRouteBatchExecutionAndReplayClosure",
        "schema_version": "fixture",
        "source_bindings": {
            "r7_queue_sha256": "5" * 64,
            "r4_bank_sha256": bank["bank_sha256"],
        },
        "counts": {
            "ready_for_real_learner_session_count": 3,
            "blocked_approved_supply_required_count": 0,
        },
        "deployments": deployments,
    }
    deployment = {
        **deployment_core,
        "deployment_queue_sha256": fullfix.digest(deployment_core),
    }
    return bank, deployment, consumer


def _write_sources(tmp_path: Path, bank: dict, deployment: dict, consumer: dict) -> tuple[Path, Path, Path]:
    paths = (
        tmp_path / "bank.json",
        tmp_path / "deployment.json",
        tmp_path / "consumer.json",
    )
    for path, value in zip(paths, (bank, deployment, consumer)):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return paths


def _build(bank: dict, deployment: dict, consumer: dict):
    return fullfix.build_projection(
        bank=bank,
        deployment_queue=deployment,
        consumer=consumer,
        expected_deployment_count=3,
        expected_projected_count=2,
    )


def _write_outputs(root: Path, values) -> None:
    for filename, value in zip(
        (
            fullfix.PROJECTION_FILENAME,
            fullfix.SAFE_FILENAME,
            fullfix.SESSION_FILENAME,
            fullfix.SESSION_SAFE_FILENAME,
        ),
        values,
    ):
        (root / filename).write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def _runtime_database(path: Path, bank: dict, projection_artifact: dict) -> Path:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE r5_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE learner_profiles(
          learner_id TEXT PRIMARY KEY,display_label TEXT,profile_state TEXT NOT NULL
        );
        CREATE TABLE edge_runtime_items(
          item_id TEXT PRIMARY KEY,breadth_cell_id TEXT NOT NULL,capability_id TEXT NOT NULL,
          life_task_id TEXT NOT NULL,domain TEXT NOT NULL,level TEXT NOT NULL,
          skill TEXT NOT NULL,purpose TEXT NOT NULL,stimulus_fingerprint TEXT NOT NULL,
          template_family TEXT NOT NULL,item_json TEXT NOT NULL,item_digest TEXT NOT NULL UNIQUE,
          admission_status TEXT NOT NULL,media_payload_state TEXT NOT NULL
        );
        CREATE TABLE edge_cell_supply(
          breadth_cell_id TEXT PRIMARY KEY,supply_status TEXT NOT NULL,max_recent_reuse INTEGER,
          approved_item_ids_json TEXT NOT NULL,required_skills_json TEXT NOT NULL,
          source_report_digest TEXT NOT NULL
        );
        CREATE TABLE edge_sessions(
          session_id TEXT PRIMARY KEY,learner_id TEXT NOT NULL REFERENCES learner_profiles(learner_id),
          breadth_cell_id TEXT NOT NULL REFERENCES edge_cell_supply(breadth_cell_id),purpose TEXT NOT NULL,
          session_state TEXT NOT NULL,session_version INTEGER NOT NULL,planned_item_count INTEGER NOT NULL,
          access_token_hash TEXT NOT NULL,started_at TEXT NOT NULL,updated_at TEXT NOT NULL,ended_at TEXT
        );
        CREATE TABLE edge_assignments(
          session_id TEXT NOT NULL REFERENCES edge_sessions(session_id),
          item_id TEXT NOT NULL REFERENCES edge_runtime_items(item_id),
          assignment_sequence INTEGER NOT NULL,assignment_state TEXT NOT NULL,
          assigned_at TEXT NOT NULL,submitted_at TEXT,
          PRIMARY KEY(session_id,item_id),UNIQUE(session_id,assignment_sequence)
        );
        CREATE TABLE edge_runtime_events(
          event_seq INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT NOT NULL UNIQUE,
          learner_id TEXT NOT NULL,session_id TEXT,event_type TEXT NOT NULL,event_at TEXT NOT NULL,
          payload_json TEXT NOT NULL,previous_hash TEXT NOT NULL,event_hash TEXT NOT NULL UNIQUE
        );
        """
    )
    connection.execute(
        "INSERT INTO r5_metadata VALUES(?,?)",
        ("source_bank_sha256", bank["bank_sha256"]),
    )
    connection.execute(
        "INSERT INTO learner_profiles VALUES(?,?,?)", ("learner", "Learner", "ACTIVE")
    )
    for item in bank["items"]:
        connection.execute(
            "INSERT INTO edge_runtime_items VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                item["item_id"], item["breadth_cell_id"], item["capability_id"],
                item["life_task_id"], item["domain"], item["level"], item["skill"],
                item["purpose"], item["stimulus_fingerprint"], item["template_family"],
                r5.canonical(item), r5.digest(item), "APPROVED", item["media_payload_state"],
            ),
        )
        connection.execute(
            "INSERT INTO edge_cell_supply VALUES(?,?,?,?,?,?)",
            (
                item["breadth_cell_id"], r5.ASSIGNABLE_CELL_STATUS, 0,
                json.dumps([item["item_id"]]), json.dumps([item["skill"]]), "s" * 64,
            ),
        )
    connection.commit()
    connection.close()
    return path


def test_builds_two_exact_m2_projections_and_one_base_delivery() -> None:
    bank, deployment, consumer = _sources()
    projection_artifact, safe, session, session_safe = _build(bank, deployment, consumer)

    counts = projection_artifact["counts"]
    assert counts["deployment_count"] == 3
    assert counts["source_dependency_projection_count"] == 2
    assert counts["base_contract_delivery_count"] == 1
    assert counts["learner_renderable_count"] == 3
    assert counts["learner_renderability_failure_count"] == 0
    assert counts["unique_m2_reading_asset_count"] == 2
    assert session["session_batch_count"] == 3
    assert session_safe["maximum_items_per_batch"] == 1
    fullfix.safe_scan(safe)
    fullfix.safe_scan(session_safe)


def test_private_projection_contains_exact_source_but_safe_report_does_not() -> None:
    bank, deployment, consumer = _sources()
    projection_artifact, safe, _, _ = _build(bank, deployment, consumer)
    private_text = json.dumps(projection_artifact, ensure_ascii=False)
    safe_text = json.dumps(safe, ensure_ascii=False)
    assert "PARK SPORTS DAY" in private_text
    assert "Mia" in private_text and "Leo" in private_text
    assert "PARK SPORTS DAY" not in safe_text
    assert "Mia" not in safe_text and "Leo" not in safe_text
    text_delivery = next(row for row in projection_artifact["deliveries"] if row["item_id"] == "ITEM_TEXT")
    assert "TEXT" in text_delivery["source_dependency_kinds"]
    table_delivery = next(row for row in projection_artifact["deliveries"] if row["item_id"] == "ITEM_TABLE")
    assert "TABLE" in table_delivery["source_dependency_kinds"]


def test_canonical_r4_item_identity_is_not_modified() -> None:
    bank, deployment, consumer = _sources()
    before = copy.deepcopy(bank)
    projection_artifact, _, _, _ = _build(bank, deployment, consumer)
    assert bank == before
    by_id = {row["item_id"]: row for row in bank["items"]}
    for delivery in projection_artifact["deliveries"]:
        item = by_id[delivery["item_id"]]
        assert delivery["canonical_candidate_sha256"] == item["candidate_sha256"]
        assert delivery["canonical_stimulus_fingerprint"] == item["stimulus_fingerprint"]


def test_m2_content_digest_mismatch_fails_closed() -> None:
    bank, deployment, consumer = _sources()
    bank = copy.deepcopy(bank)
    bank["items"][0]["authority_refs"] = ["M2_CONTENT_DIGEST:" + "f" * 64]
    core = {key: value for key, value in bank.items() if key != "bank_sha256"}
    bank["bank_sha256"] = fullfix.digest(core)
    deployment = copy.deepcopy(deployment)
    deployment["source_bindings"]["r4_bank_sha256"] = bank["bank_sha256"]
    dep_core = {key: value for key, value in deployment.items() if key != "deployment_queue_sha256"}
    deployment["deployment_queue_sha256"] = fullfix.digest(dep_core)
    with pytest.raises(fullfix.RuntimeProjectionError, match="m2_content_digest_mismatch:ITEM_TEXT"):
        _build(bank, deployment, consumer)


def test_teacher_only_m2_payload_is_not_promoted_to_learner_source() -> None:
    bank, deployment, consumer = _sources()
    bank = copy.deepcopy(bank)
    deployment = copy.deepcopy(deployment)
    consumer = copy.deepcopy(consumer)
    payload = {"teacher_delivery": "Tell the learner the answer.", "expected_evidence": "Answer."}
    consumer["asset_records"][0]["payload"] = payload
    consumer["asset_records"][0]["content_digest"] = fullfix.digest(payload)
    bank["items"][0]["authority_refs"] = [
        "M2_CONTENT_DIGEST:" + consumer["asset_records"][0]["content_digest"]
    ]
    bank_core = {key: value for key, value in bank.items() if key != "bank_sha256"}
    bank["bank_sha256"] = fullfix.digest(bank_core)
    deployment["source_bindings"]["r4_bank_sha256"] = bank["bank_sha256"]
    dep_core = {key: value for key, value in deployment.items() if key != "deployment_queue_sha256"}
    deployment["deployment_queue_sha256"] = fullfix.digest(dep_core)
    with pytest.raises(fullfix.RuntimeProjectionError, match="SOURCE_PAYLOAD_NOT_LEARNER_RENDERABLE:ITEM_TEXT"):
        _build(bank, deployment, consumer)


def test_m12f_unseen_text_is_projected_as_learner_visible_text() -> None:
    source = "Park Sports Day\nCome to the city park on Friday."

    kind, path, payload = fullfix.extract_learner_source(
        {"mode": "mastery_evidence", "unseen_text": source},
        item_id="ITEM_TEXT",
    )

    assert kind == "TEXT"
    assert path == ("unseen_text",)
    assert payload == source


def test_m12f_text_ref_resolves_exact_same_lesson_source_asset() -> None:
    source = "Swimming Skills Day\nCome to the swimming pool on Thursday."
    practice_asset = {
        "asset_id": "KETR-RF-05-L01-PRD",
        "lesson_id": "KETR-RF-05-L01",
        "skill": "READING",
        "payload": {"mode": "guided_practice", "text_ref": "TXT", "items": []},
    }
    text_asset = {
        "asset_id": "KETR-RF-05-L01-TXT",
        "lesson_id": "KETR-RF-05-L01",
        "skill": "READING",
        "payload": {"title": "Swimming Skills Day", "text": source},
        "content_digest": fullfix.digest({"title": "Swimming Skills Day", "text": source}),
    }

    kind, path, payload, source_asset = fullfix.resolve_learner_source(
        practice_asset,
        assets=fullfix._asset_index({"asset_records": [practice_asset, text_asset]}),
        lesson_id="KETR-RF-05-L01",
        item_id="ITEM_TEXT_REF",
    )

    assert kind == "TEXT"
    assert path == ("text_ref", "KETR-RF-05-L01-TXT", "text")
    assert payload == source
    assert source_asset == text_asset


def test_a2_item_injection_fails_closed() -> None:
    bank, deployment, consumer = _sources()
    bank = copy.deepcopy(bank)
    bank["items"][0]["level"] = "A2"
    core = {key: value for key, value in bank.items() if key != "bank_sha256"}
    bank["bank_sha256"] = fullfix.digest(core)
    deployment = copy.deepcopy(deployment)
    deployment["source_bindings"]["r4_bank_sha256"] = bank["bank_sha256"]
    dep_core = {key: value for key, value in deployment.items() if key != "deployment_queue_sha256"}
    deployment["deployment_queue_sha256"] = fullfix.digest(dep_core)
    with pytest.raises(fullfix.RuntimeProjectionError, match="r4_a2_item_detected"):
        _build(bank, deployment, consumer)


def test_projection_build_is_idempotent() -> None:
    bank, deployment, consumer = _sources()
    assert _build(bank, deployment, consumer) == _build(bank, deployment, consumer)


def test_apply_runtime_and_start_exact_projected_session(tmp_path: Path) -> None:
    bank, deployment, consumer = _sources()
    projection_artifact, _, _, _ = _build(bank, deployment, consumer)
    database = _runtime_database(tmp_path / "runtime.sqlite3", bank, projection_artifact)
    result = fullfix.apply_projection_to_runtime(
        database_path=database,
        projection=projection_artifact,
    )
    assert result["delivery_count"] == 3
    assert result["source_dependency_projection_count"] == 2
    assert result["learner_evidence_generated"] is False

    started = fullfix.start_exact_projected_session(
        database_path=database,
        projection=projection_artifact,
        learner_id="learner",
        work_item_id="WORK_1",
        session_id="SESSION_PROJECTED",
        started_at="2026-07-21T08:00:00Z",
    )
    assert started["assignments"][0]["item"]["item_id"] == "ITEM_TEXT"
    learner = started["assignments"][0]["item"]["learner_contract"]
    assert learner["context"]["source_text"].startswith("PARK SPORTS DAY")
    assert learner["stimulus_validation"]["answerability_pass"] is True
    assert learner["stimulus_render_manifest"]
    assert started["delivery_fingerprint"] == projection_artifact["deliveries"][0]["delivery_fingerprint"]


def test_independent_validator_rebuilds_projection_and_checks_runtime(tmp_path: Path) -> None:
    bank, deployment, consumer = _sources()
    source_paths = _write_sources(tmp_path, bank, deployment, consumer)
    values = fullfix.build_projection(
        bank=bank,
        deployment_queue=deployment,
        consumer=consumer,
        bank_file_sha256=fullfix.file_digest(source_paths[0]),
        deployment_file_sha256=fullfix.file_digest(source_paths[1]),
        consumer_file_sha256=fullfix.file_digest(source_paths[2]),
        expected_deployment_count=3,
        expected_projected_count=2,
    )
    _write_outputs(tmp_path, values)
    database = _runtime_database(tmp_path / "runtime.sqlite3", bank, values[0])
    fullfix.apply_projection_to_runtime(database_path=database, projection=values[0])
    report = validator.validate(
        bank_path=source_paths[0],
        deployment_queue_path=source_paths[1],
        consumer_path=source_paths[2],
        output_root=tmp_path,
        database_path=database,
        expected_deployment_count=3,
        expected_projected_count=2,
    )
    assert report["error_count"] == 0, report["errors"]
    assert report["source_dependency_projection_count"] == 2
    assert report["learner_renderable_count"] == 3
    assert report["canonical_identity_change_count"] == 0
