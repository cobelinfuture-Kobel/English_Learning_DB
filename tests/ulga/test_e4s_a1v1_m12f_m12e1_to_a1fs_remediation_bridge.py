from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as m08
from ulga.builders import build_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge as bridge
from ulga.validators import validate_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge as validator


def write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def pending_review() -> dict:
    return {
        "decision": "PENDING", "reviewer_id": None, "reviewed_at": None,
        "criteria": {"grammar_target_match": None, "meaning_matches_context": None, "complete_response": None},
        "notes": None,
    }


def resolved_review(decision: str) -> dict:
    return {
        "decision": decision, "reviewer_id": "fixture-reviewer",
        "reviewed_at": "2026-07-17T12:57:35.650Z",
        "criteria": {
            "grammar_target_match": True,
            "meaning_matches_context": True,
            "complete_response": decision == "APPROVE",
        },
        "notes": "Fixture review evidence.",
    }


def build_fixture(root: Path) -> dict:
    outcomes = ["AUTO_PASS"] * 6 + ["AUTO_FAIL", "HUMAN_APPROVE", "HUMAN_REJECT"]
    bank_items: list[dict] = []
    attempts: list[dict] = []
    entries: list[dict] = []
    assets: list[dict] = []
    nodes: list[dict] = []
    coverage: list[dict] = []
    lessons = {
        "LESSON_READING": {"skill": "READING", "asset_keys": [], "roles": set(), "requirements": []},
        "LESSON_WRITING": {"skill": "WRITING", "asset_keys": [], "roles": set(), "requirements": []},
    }
    for index, outcome in enumerate(outcomes, 1):
        item_id = f"M12_ITEM_{index:02d}"
        lesson_id = "LESSON_READING" if index <= 5 else "LESSON_WRITING"
        skill = lessons[lesson_id]["skill"]
        asset_id = f"ASSET_{index:02d}"
        asset_key = f"{skill}:{asset_id}"
        node_id = f"CAP:{skill}:{index:02d}"
        feature = outcome.startswith("HUMAN_")
        if feature:
            contract = {
                "scoring_mode": "FEATURE_RUBRIC", "response_type": "string",
                "model_texts": ["a complete model response"],
                "rubric": {
                    "grammar_target_match": "Target grammar is present.",
                    "meaning_matches_context": "Meaning fits the context.",
                    "complete_response": "Response is structurally complete.",
                },
                "human_review_fallback": True,
            }
            response = "a complete model response" if outcome == "HUMAN_APPROVE" else "incomplete response"
            review = resolved_review("APPROVE" if outcome == "HUMAN_APPROVE" else "REJECT")
            role = "EVD"
        else:
            contract = {
                "scoring_mode": "NORMALIZED_TEXT", "response_type": "string",
                "accepted_texts": [f"answer {index}"], "case_insensitive": True,
                "punctuation_tolerance": True, "human_review_fallback": False,
            }
            response = f"answer {index}" if outcome == "AUTO_PASS" else "wrong answer"
            review = pending_review()
            role = "CHK"
        submitted_at = f"2026-07-17T12:{index:02d}:00.000Z"
        bank_items.append({
            "item_id": item_id, "private_scoring_contract": contract,
            "shared_item_id": f"SHARED_{index:02d}", "grammar_unit_id": f"GRAMMAR_{index:02d}",
            "canonical_egp_row_ids": [f"EGP_{index:02d}"], "skill": skill.casefold(),
            "item_role": "assessment" if feature else "practice",
        })
        attempt = {
            "item_id": item_id, "attempt_sequence": index, "response": response,
            "submitted_at": submitted_at, "operator_review": review,
        }
        attempts.append(attempt)
        entries.append({
            "evidence_id": f"M08_EVIDENCE:{item_id}:{index}", "item_id": item_id,
            "shared_item_id": f"SHARED_{index:02d}", "grammar_unit_id": f"GRAMMAR_{index:02d}",
            "canonical_egp_row_ids": [f"EGP_{index:02d}"], "skill": skill.casefold(),
            "item_role": "assessment" if feature else "practice", "attempt_sequence": index,
            "response": response, "submitted_at": submitted_at, "scoring_mode": contract["scoring_mode"],
            "outcome": outcome, "score": 1.0 if outcome in {"AUTO_PASS", "HUMAN_APPROVE"} else 0.0,
            "operator_review": review, "mastery_claimed": False,
        })
        assets.append({
            "asset_id": asset_id, "asset_key": asset_key, "lesson_id": lesson_id,
            "skill": skill, "level": "A1", "role": role,
            "payload": {
                "prompt": f"Fixture prompt {index}", "response_capture_enabled": True,
                "m12_item_id": item_id, "private_scoring_contract": copy.deepcopy(contract),
            },
            "content_digest": hashlib.sha256(item_id.encode()).hexdigest(),
            "release_scope": "PRIVATE_INTERNAL_D0",
        })
        lessons[lesson_id]["asset_keys"].append(asset_key)
        lessons[lesson_id]["roles"].add(role)
        lessons[lesson_id]["requirements"].append(node_id)
        nodes.append({"node_id": node_id, "node_type": "CAPABILITY", "source_ref": f"EGP_{index:02d}", "skill": skill, "level": "A1"})
        coverage.append({"node_id": node_id, "source_ref": f"EGP_{index:02d}", "asset_body_ids": [asset_id], "lesson_ids": [lesson_id]})

    bank = {
        "task_id": m08.TASK_ID, "schema_version": m08.SESSION_SCHEMA_VERSION,
        "private_local_only": True, "source_hashes": {"fixture": "0" * 64},
        "item_count": 9, "unit_count": 9, "canonical_egp_row_count": 9,
        "items": bank_items, "items_sha256": m08.sha256_value(bank_items),
        "claim_boundaries": {"private_local_only": True},
    }
    bank_hash = m08.sha256_value(bank)
    for asset in assets:
        asset["payload"]["m12_session_bank_sha256"] = bank_hash
    registry = {
        "task_id": m08.TASK_ID, "schema_version": m08.ATTEMPT_SCHEMA_VERSION,
        "private_local_only": True, "session_bank_sha256": bank_hash,
        "session_id": "m12f-fixture-session", "learner_ref": "fixture-private-learner",
        "attempts": attempts,
    }
    outcome_counts = {name: sum(row["outcome"] == name for row in entries) for name in m08.OUTCOMES}
    ledger = {
        "task_id": m08.TASK_ID, "schema_version": m08.LEDGER_SCHEMA_VERSION,
        "private_local_only": True, "session_bank_sha256": bank_hash,
        "attempt_registry_sha256": m08.sha256_value(registry), "session_id": registry["session_id"],
        "learner_ref": registry["learner_ref"], "attempt_count": 9,
        "outcome_counts": outcome_counts, "attempted_unit_count": 9, "attempted_row_count": 9,
        "entries": entries, "entries_sha256": m08.sha256_value(entries),
        "claim_boundaries": {"private_local_only": True, "learner_mastery_claimed": False},
    }
    graph = {
        "task_id": "A1FS-V1-M1_PrerequisiteGraphAndCoverage",
        "validation_status": bridge.GRAPH_STATUS, "nodes": nodes, "coverage": coverage,
        "a2_lock_contract": {"required_mastery_node_ids": [row["node_id"] for row in nodes]},
        "counts": {"required_mastery_node_count": 9},
    }
    graph_path = write(root / "graph.json", graph)
    catalog = [{
        "lesson_id": lesson_id, "lesson_node_id": f"LESSON:{row['skill']}:{lesson_id}",
        "skill": row["skill"], "level": "A1", "asset_keys": sorted(row["asset_keys"]),
        "roles": sorted(row["roles"]), "requirement_node_ids": sorted(row["requirements"]),
        "release_scope": "PRIVATE_INTERNAL_D0",
    } for lesson_id, row in lessons.items()]
    consumer = {
        "task_id": "A1FS-V1-M2_FourSkillAssetBodyConsumerAndQuery",
        "schema_version": "a1fs.v1.m2.four_skill_asset_body_consumer.v1",
        "validation_status": bridge.CONSUMER_STATUS,
        "source_graph_sha256": hashlib.sha256(graph_path.read_bytes()).hexdigest(),
        "asset_records": assets, "lesson_catalog": catalog,
        "counts": {"asset_record_count": 9, "lesson_count": 2, "learning_lesson_count": 2, "a2_handoff_lesson_count": 0},
        "access_contract": {"visibility": "PRIVATE_INTERNAL"},
        "claim_boundaries": {"a2_unlocked": False}, "errors": [], "next_short_step": bridge.m3.TASK_ID,
    }
    source_bank_path = write(root / "source_bank.private.json", bank)
    consumer_path = write(root / "consumer.private.json", consumer)
    resolved_root = root / "resolved"
    write(resolved_root / "cumulative_attempt_registry.private.json", registry)
    write(resolved_root / "cumulative_progress_ledger.private.json", ledger)
    write(resolved_root / "cumulative_progress_query_index.json", {"task_id": m08.TASK_ID, "attempt_count": 9, "items": []})
    m12e1_root = root / "m12e1"
    write(m12e1_root / "human_review_materialization_safe_report.json", {
        "task_id": bridge.M12E1_TASK_ID, "validation_status": bridge.M12E1_STATUS,
        "remaining_pending_count": 0, "stop_reason": "NONE", "outcome_counts": outcome_counts,
    })
    return {
        "root": root, "source_bank_path": source_bank_path, "resolved_root": resolved_root,
        "m12e1_root": m12e1_root, "consumer_path": consumer_path, "graph_path": graph_path,
        "database_path": root / "a1fs.private.sqlite3", "output_root": root / "output",
        "consumer": consumer, "graph": graph, "ledger": ledger,
    }


@pytest.fixture()
def fixture() -> dict:
    root = bridge.REPO_ROOT / ".local" / f"m12f-bridge-test-{uuid.uuid4().hex}"
    data = build_fixture(root)
    yield data
    shutil.rmtree(root, ignore_errors=True)


def common(data: dict) -> dict:
    return {
        "source_bank_path": data["source_bank_path"], "resolved_root": data["resolved_root"],
        "m12e1_root": data["m12e1_root"], "consumer_path": data["consumer_path"],
        "graph_path": data["graph_path"], "output_root": data["output_root"],
    }


def test_inspect_and_independent_validation(fixture: dict) -> None:
    report = bridge.inspect_bridge(**common(fixture))["safe_report"]
    assert report["validation_status"] == bridge.INSPECT_READY
    assert report["mapping"]["mapped_count"] == 9
    assert all(not report["mapping"][key] for key in (
        "unmapped_item_ids", "duplicate_item_ids", "wrong_bank_hash_item_ids",
        "contract_drift_items", "coverage_missing_item_ids", "a2_item_ids",
    ))
    validated = validator.validate(mode="inspect", **common(fixture))
    assert validated["error_count"] == 0, validated["errors"]


def test_import_builds_canonical_m3_m6_m7_chain(fixture: dict) -> None:
    result = bridge.import_resolved(
        **common(fixture), database_path=fixture["database_path"],
        learner_id="m12f-fixture-learner", display_label="Fixture Learner",
    )
    report = result["safe_report"]
    assert report["validation_status"] == bridge.IMPORT_STATUS
    assert report["import_result"]["imported_outcome_counts"] == {
        "AUTO_PASS": 6, "AUTO_FAIL": 1, "PENDING_HUMAN_REVIEW": 0,
        "HUMAN_APPROVE": 1, "HUMAN_REJECT": 1, "HUMAN_DEFER": 0,
    }
    assert report["import_result"]["m7_error_diagnosis_count"] == 2
    assert report["import_result"]["open_remediation_count"] == 2
    assert report["import_result"]["pending_reassessment_count"] == 2
    assert report["import_result"]["a2_lock_state"] == "LOCKED"
    with sqlite3.connect(fixture["database_path"]) as connection:
        assert connection.execute("SELECT COUNT(*) FROM state_events").fetchone()[0] == 14
        assert connection.execute("SELECT COUNT(*) FROM learning_sessions WHERE session_state='COMPLETED'").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM response_attempts").fetchone()[0] == 9
        assert connection.execute("SELECT COUNT(*) FROM remediation_assignments WHERE assignment_state='OPEN'").fetchone()[0] == 2
    validated = validator.validate(mode="import-resolved", **common(fixture), database_path=fixture["database_path"])
    assert validated["error_count"] == 0, validated["errors"]


def test_replay_is_idempotent(fixture: dict) -> None:
    kwargs = dict(**common(fixture), database_path=fixture["database_path"], learner_id="replay-learner", display_label="Replay Learner")
    first = bridge.import_resolved(**kwargs)
    before = fixture["database_path"].read_bytes()
    second = bridge.import_resolved(**kwargs)
    assert first["safe_report"]["validation_status"] == bridge.IMPORT_STATUS
    assert second["safe_report"]["validation_status"] == bridge.REPLAY_STATUS
    assert fixture["database_path"].read_bytes() == before


def test_missing_mapping_blocks_without_guessing(fixture: dict) -> None:
    consumer = copy.deepcopy(fixture["consumer"])
    consumer["asset_records"][0]["payload"].pop("m12_item_id")
    write(fixture["consumer_path"], consumer)
    report = bridge.inspect_bridge(**common(fixture))["safe_report"]
    assert report["validation_status"] == bridge.INSPECT_BLOCKED
    assert report["mapping"]["unmapped_item_ids"] == ["M12_ITEM_01"]
    with pytest.raises(bridge.BridgeError, match="MAPPING_AUTHORITY_REQUIRED"):
        bridge.import_resolved(**common(fixture), database_path=fixture["database_path"], learner_id="blocked", display_label="Blocked")
    assert not fixture["database_path"].exists()


@pytest.mark.parametrize("mutation,issue_key", [
    ("wrong_hash", "wrong_bank_hash_item_ids"),
    ("contract", "contract_drift_items"),
    ("a2", "a2_item_ids"),
    ("coverage", "coverage_missing_item_ids"),
])
def test_mapping_drift_is_fail_closed(fixture: dict, mutation: str, issue_key: str) -> None:
    consumer = copy.deepcopy(fixture["consumer"])
    graph = copy.deepcopy(fixture["graph"])
    if mutation == "wrong_hash":
        consumer["asset_records"][0]["payload"]["m12_session_bank_sha256"] = "f" * 64
    elif mutation == "contract":
        consumer["asset_records"][0]["payload"]["private_scoring_contract"]["accepted_texts"] = ["different"]
    elif mutation == "a2":
        consumer["asset_records"][0]["level"] = "A2"
    else:
        graph["coverage"][0]["asset_body_ids"] = []
        write(fixture["graph_path"], graph)
        consumer["source_graph_sha256"] = hashlib.sha256(fixture["graph_path"].read_bytes()).hexdigest()
    write(fixture["consumer_path"], consumer)
    report = bridge.inspect_bridge(**common(fixture))["safe_report"]
    assert report["validation_status"] == bridge.INSPECT_BLOCKED
    assert report["mapping"][issue_key]


def test_duplicate_mapping_is_rejected(fixture: dict) -> None:
    consumer = copy.deepcopy(fixture["consumer"])
    duplicate = copy.deepcopy(consumer["asset_records"][0])
    duplicate.update({"asset_id": "ASSET_DUP", "asset_key": "READING:ASSET_DUP", "content_digest": "d" * 64})
    consumer["asset_records"].append(duplicate)
    consumer["lesson_catalog"][0]["asset_keys"].append(duplicate["asset_key"])
    consumer["counts"]["asset_record_count"] = 10
    graph = copy.deepcopy(fixture["graph"])
    graph["coverage"][0]["asset_body_ids"].append("ASSET_DUP")
    write(fixture["graph_path"], graph)
    consumer["source_graph_sha256"] = hashlib.sha256(fixture["graph_path"].read_bytes()).hexdigest()
    write(fixture["consumer_path"], consumer)
    report = bridge.inspect_bridge(**common(fixture))["safe_report"]
    assert report["mapping"]["duplicate_item_ids"] == ["M12_ITEM_01"]


def test_outcome_drift_rolls_back_database(fixture: dict) -> None:
    ledger_path = fixture["resolved_root"] / "cumulative_progress_ledger.private.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["entries"][0]["outcome"] = "AUTO_FAIL"
    write(ledger_path, ledger)
    with pytest.raises(bridge.BridgeError, match="outcome_rebuild_drift"):
        bridge.import_resolved(**common(fixture), database_path=fixture["database_path"], learner_id="rollback", display_label="Rollback")
    assert not fixture["database_path"].exists()


def test_safe_report_has_no_private_payload(fixture: dict) -> None:
    encoded = json.dumps(bridge.inspect_bridge(**common(fixture))["safe_report"], ensure_ascii=False).casefold()
    for forbidden in ("fixture-private-learner", "wrong answer", "incomplete response", "fixture-reviewer", "fixture prompt"):
        assert forbidden not in encoded


def test_direct_cli_inspect(fixture: dict) -> None:
    process = subprocess.run([
        sys.executable, str(Path(bridge.__file__).resolve()), "inspect",
        "--source-bank", str(fixture["source_bank_path"]), "--resolved-root", str(fixture["resolved_root"]),
        "--m12e1-root", str(fixture["m12e1_root"]), "--consumer", str(fixture["consumer_path"]),
        "--graph", str(fixture["graph_path"]), "--output-root", str(fixture["output_root"]),
    ], cwd=bridge.REPO_ROOT, capture_output=True, text=True, check=False)
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout)["mapped_count"] == 9
