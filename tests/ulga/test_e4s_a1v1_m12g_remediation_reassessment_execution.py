from __future__ import annotations

import copy
import json
import shutil
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tests.ulga.test_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge import (
    build_fixture,
    common,
    write,
)
from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as m08
from ulga.builders import build_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge as bridge
from ulga.builders import build_e4s_a1v1_m12g_remediation_reassessment_execution as m12g


def expand_source_bank(data: dict) -> dict:
    bank = json.loads(data["source_bank_path"].read_text(encoding="utf-8"))
    consumer = json.loads(data["consumer_path"].read_text(encoding="utf-8"))
    graph = json.loads(data["graph_path"].read_text(encoding="utf-8"))
    registry_path = data["resolved_root"] / "cumulative_attempt_registry.private.json"
    ledger_path = data["resolved_root"] / "cumulative_progress_ledger.private.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

    by_id = {row["item_id"]: row for row in bank["items"]}
    failed_ids = [row["item_id"] for row in ledger["entries"] if row["outcome"] in {"AUTO_FAIL", "HUMAN_REJECT"}]
    assert failed_ids == ["M12_ITEM_07", "M12_ITEM_09"]

    for item in bank["items"]:
        feature = item["private_scoring_contract"]["scoring_mode"] == "FEATURE_RUBRIC"
        item["task_type"] = "text_mode_writing_checkpoint" if feature else "structured_gap_fill"
        item["learner_contract"] = {
            "prompt": f"Reassessment prompt for {item['item_id']}",
            "response_mode": "short_text",
        }

    for failed_id in failed_ids:
        original = by_id[failed_id]
        feature = original["private_scoring_contract"]["scoring_mode"] == "FEATURE_RUBRIC"
        for number in range(1, 4):
            item_id = f"{failed_id}_ALT_{number}"
            if feature:
                contract = {
                    "scoring_mode": "FEATURE_RUBRIC",
                    "response_type": "string",
                    "model_texts": [f"complete reassessment {failed_id} {number}"],
                    "rubric": copy.deepcopy(original["private_scoring_contract"]["rubric"]),
                    "human_review_fallback": True,
                }
            else:
                contract = {
                    "scoring_mode": "NORMALIZED_TEXT",
                    "response_type": "string",
                    "accepted_texts": [f"reassessment answer {failed_id} {number}"],
                    "case_insensitive": True,
                    "punctuation_tolerance": True,
                    "human_review_fallback": False,
                }
            bank["items"].append({
                "item_id": item_id,
                "shared_item_id": f"SHARED_{item_id}",
                "learning_unit_id": f"UNIT_{original['grammar_unit_id']}",
                "grammar_unit_id": original["grammar_unit_id"],
                "canonical_egp_row_ids": list(original["canonical_egp_row_ids"]),
                "internal_stage": "A1",
                "skill": original["skill"],
                "item_role": "assessment" if feature else "practice",
                "evidence_dimension": "reassessment",
                "task_type": "text_mode_writing_checkpoint" if feature else "structured_gap_fill",
                "learner_contract": {
                    "prompt": f"Distinct reassessment prompt {failed_id} {number}",
                    "response_mode": "short_text",
                },
                "private_scoring_contract": contract,
                "session_status": "READY_FOR_LOCAL_TEXT_SESSION",
            })

    bank["item_count"] = len(bank["items"])
    bank["items_sha256"] = m08.sha256_value(bank["items"])
    bank_hash = m08.sha256_value(bank)
    for asset in consumer["asset_records"]:
        asset["payload"]["m12_session_bank_sha256"] = bank_hash
        asset["content_digest"] = m12g.digest(asset["payload"])
    consumer["m12f_dedicated_private_bridge_overlay"] = {
        "task_id": "fixture",
        "source_session_bank_sha256": bank_hash,
        "private_local_only": True,
    }

    graph["edges"] = graph.get("edges", [])
    graph["a2_lock_contract"]["state"] = "LOCKED_BY_DESIGN"
    graph["counts"] = {
        "node_count": len(graph["nodes"]),
        "edge_count": len(graph["edges"]),
        "coverage_record_count": len(graph["coverage"]),
        "lesson_count": len(consumer["lesson_catalog"]),
        "lesson_count_by_level": {"A1": len(consumer["lesson_catalog"]), "A1+": 0, "A2": 0},
        "required_mastery_node_count": len(graph["a2_lock_contract"]["required_mastery_node_ids"]),
        "a2_handoff_lesson_count": 0,
        "uncovered_required_node_count": 0,
    }
    write(data["graph_path"], graph)
    consumer["source_graph_sha256"] = m12g.file_sha(data["graph_path"])
    write(data["consumer_path"], consumer)

    registry["session_bank_sha256"] = bank_hash
    write(registry_path, registry)
    ledger["session_bank_sha256"] = bank_hash
    ledger["attempt_registry_sha256"] = m08.sha256_value(registry)
    write(ledger_path, ledger)
    write(data["source_bank_path"], bank)
    return {"bank": bank, "bank_hash": bank_hash, "failed_ids": failed_ids}


@pytest.fixture()
def fixture() -> dict:
    root = bridge.REPO_ROOT / ".local" / f"m12g-test-{uuid.uuid4().hex}"
    data = build_fixture(root / "m12f")
    expanded = expand_source_bank(data)
    learner_id = "m12g-fixture-learner"
    bridge.import_resolved(
        **common(data), database_path=data["database_path"],
        learner_id=learner_id, display_label="M12G Fixture Learner",
    )
    target_root = root / "m12g"
    prepared = m12g.prepare(
        source_bank_path=data["source_bank_path"],
        base_consumer_path=data["consumer_path"],
        base_graph_path=data["graph_path"],
        source_database_path=data["database_path"],
        resolved_root=data["resolved_root"],
        m12e1_root=data["m12e1_root"],
        learner_id=learner_id,
        display_label="M12G Fixture Learner",
        target_root=target_root,
    )
    result = {**data, **expanded, "learner_id": learner_id, "target_root": target_root, "prepared": prepared}
    yield result
    shutil.rmtree(root, ignore_errors=True)


def accepted_response(item: dict) -> object:
    contract = item["private_scoring_contract"]
    if contract["scoring_mode"] in {"NORMALIZED_TEXT", "EXACT_OPTION"}:
        return contract["accepted_texts"][0]
    if contract["scoring_mode"] == "EXACT_SEQUENCE":
        return list(contract["accepted_sequence"])
    return "Complete, context-appropriate reassessment response."


def passing_registry(fixture: dict) -> dict:
    package = json.loads(fixture["prepared"]["package_path"].read_text(encoding="utf-8"))
    bank_by_id = {row["item_id"]: row for row in fixture["bank"]["items"]}
    start = datetime(2026, 7, 18, 7, 0, tzinfo=timezone.utc)
    attempts = []
    for index, task in enumerate(package["tasks"]):
        submitted = start + timedelta(minutes=index * 2)
        item = bank_by_id[task["source_item_id"]]
        review = None
        if task["human_review_required"]:
            review = {
                "decision": "APPROVE",
                "reviewer_id": "fixture-reviewer",
                "reviewed_at": (submitted + timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
                "criteria": {
                    "grammar_target_match": True,
                    "meaning_matches_context": True,
                    "complete_response": True,
                },
                "notes": "Fixture approval.",
            }
        attempts.append({
            "task_instance_id": task["task_instance_id"],
            "response": accepted_response(item),
            "submitted_at": submitted.isoformat().replace("+00:00", "Z"),
            "operator_review": review,
        })
    return {
        "task_id": m12g.TASK_ID,
        "schema_version": m12g.REGISTRY_SCHEMA_VERSION,
        "private_local_only": True,
        "package_sha256": package["package_sha256"],
        "learner_id": fixture["learner_id"],
        "attempts": attempts,
    }


def test_prepare_builds_eight_distinct_authority_reviewed_tasks(fixture: dict) -> None:
    report = fixture["prepared"]["report"]
    assert report["validation_status"] == m12g.PREPARE_STATUS
    assert report["pending_node_count"] == 2
    assert report["required_attempt_count"] == 8
    assert all(row["required_successful_attempt_count"] == 4 for row in report["node_plan"])
    package = json.loads(fixture["prepared"]["package_path"].read_text(encoding="utf-8"))
    by_node = {}
    for task in package["tasks"]:
        by_node.setdefault(task["node_id"], []).append(task)
    assert len(by_node) == 2
    assert all(len(rows) == 4 for rows in by_node.values())
    assert all(len({row["source_item_id"] for row in rows}) == 4 for rows in by_node.values())
    serialized = json.dumps(package)
    assert "accepted_texts" not in serialized
    assert "accepted_sequence" not in serialized
    assert "model_texts" not in serialized
    assert '"rubric"' not in serialized
    with sqlite3.connect(fixture["prepared"]["database_path"]) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert len(connection.execute("PRAGMA foreign_key_check").fetchall()) == 0
        assert connection.execute("SELECT COUNT(*) FROM reassessment_queue WHERE queue_state='PENDING'").fetchone()[0] == 2


def test_import_eight_passes_closes_two_remediation_nodes(fixture: dict) -> None:
    registry = passing_registry(fixture)
    registry_path = write(fixture["target_root"] / "responses.private.json", registry)
    result = m12g.import_evidence(
        package_path=fixture["prepared"]["package_path"],
        registry_path=registry_path,
        consumer_path=fixture["prepared"]["consumer_path"],
        graph_path=fixture["prepared"]["graph_path"],
        database_path=fixture["prepared"]["database_path"],
        learner_id=fixture["learner_id"],
        target_root=fixture["target_root"] / "import",
    )
    report = result["report"]
    assert report["validation_status"] == m12g.IMPORT_STATUS
    assert report["imported_attempt_count"] == 8
    assert report["closed_remediation_node_count"] == 2
    assert report["pending_node_ids"] == []
    assert report["m7_validation_error_count"] == 0
    assert report["a2_lock_state"] == "LOCKED"
    assert report["stop_reason"] == "NONE"
    with sqlite3.connect(fixture["prepared"]["database_path"]) as connection:
        assert connection.execute("SELECT COUNT(*) FROM response_attempts").fetchone()[0] == 17
        assert connection.execute("SELECT COUNT(*) FROM remediation_assignments WHERE assignment_state='OPEN'").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM reassessment_queue WHERE queue_state='PENDING'").fetchone()[0] == 0


def test_registry_must_cover_exact_package_partition(fixture: dict) -> None:
    registry = passing_registry(fixture)
    registry["attempts"].pop()
    registry_path = write(fixture["target_root"] / "partial.private.json", registry)
    with pytest.raises(m12g.ReassessmentError, match="registry_attempt_partition"):
        m12g.import_evidence(
            package_path=fixture["prepared"]["package_path"],
            registry_path=registry_path,
            consumer_path=fixture["prepared"]["consumer_path"],
            graph_path=fixture["prepared"]["graph_path"],
            database_path=fixture["prepared"]["database_path"],
            learner_id=fixture["learner_id"],
            target_root=fixture["target_root"] / "partial-import",
        )


def test_prepare_fails_without_four_distinct_same_skill_items() -> None:
    root = bridge.REPO_ROOT / ".local" / f"m12g-insufficient-{uuid.uuid4().hex}"
    data = build_fixture(root / "m12f")
    expanded = expand_source_bank(data)
    bank = json.loads(data["source_bank_path"].read_text(encoding="utf-8"))
    bank["items"] = [row for row in bank["items"] if not row["item_id"].endswith("_ALT_3")]
    bank["item_count"] = len(bank["items"])
    bank["items_sha256"] = m08.sha256_value(bank["items"])
    new_hash = m08.sha256_value(bank)
    consumer = json.loads(data["consumer_path"].read_text(encoding="utf-8"))
    for asset in consumer["asset_records"]:
        asset["payload"]["m12_session_bank_sha256"] = new_hash
    consumer["m12f_dedicated_private_bridge_overlay"]["source_session_bank_sha256"] = new_hash
    write(data["consumer_path"], consumer)
    registry_path = data["resolved_root"] / "cumulative_attempt_registry.private.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8")); registry["session_bank_sha256"] = new_hash; write(registry_path, registry)
    ledger_path = data["resolved_root"] / "cumulative_progress_ledger.private.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8")); ledger["session_bank_sha256"] = new_hash; ledger["attempt_registry_sha256"] = m08.sha256_value(registry); write(ledger_path, ledger)
    write(data["source_bank_path"], bank)
    learner_id = "insufficient-learner"
    bridge.import_resolved(**common(data), database_path=data["database_path"], learner_id=learner_id, display_label="Insufficient")
    with pytest.raises(m12g.ReassessmentError, match="distinct_reassessment_items_insufficient"):
        m12g.prepare(
            source_bank_path=data["source_bank_path"], base_consumer_path=data["consumer_path"],
            base_graph_path=data["graph_path"], source_database_path=data["database_path"],
            resolved_root=data["resolved_root"], m12e1_root=data["m12e1_root"],
            learner_id=learner_id, display_label="Insufficient", target_root=root / "m12g",
        )
    shutil.rmtree(root, ignore_errors=True)
