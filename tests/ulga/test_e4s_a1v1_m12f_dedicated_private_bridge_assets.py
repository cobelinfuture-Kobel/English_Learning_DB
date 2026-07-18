from __future__ import annotations

import copy
import json
import shutil
import uuid
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as m08
from ulga.builders import build_e4s_a1v1_m12f_dedicated_private_bridge_assets as dedicated
from ulga.builders import build_e4s_a1v1_m12f_explicit_mapping_overlay as overlay
from ulga.builders import build_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge as bridge


def write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def fixture(root: Path) -> dict:
    items = []
    for index in range(1, 10):
        feature = index >= 8
        skill = "writing" if feature else "reading"
        contract = (
            {
                "scoring_mode": "FEATURE_RUBRIC",
                "response_type": "string",
                "model_texts": [f"private model {index}"],
                "rubric": {
                    "grammar_target_match": "Target grammar is present.",
                    "meaning_matches_context": "Meaning fits the context.",
                    "complete_response": "Response is complete.",
                },
                "human_review_fallback": True,
            }
            if feature
            else {
                "scoring_mode": "NORMALIZED_TEXT",
                "response_type": "string",
                "accepted_texts": [f"private answer {index}"],
                "case_insensitive": True,
                "punctuation_tolerance": True,
                "human_review_fallback": False,
            }
        )
        items.append({
            "item_id": f"GRAMMAR_UNIT_{index:02d}__TFX_{index:02d}",
            "grammar_unit_id": f"GRAMMAR_UNIT_{index:02d}",
            "canonical_egp_row_ids": [f"EGP_{index:02d}"],
            "skill": skill,
            "task_type": "text_mode_writing_checkpoint" if feature else "form_choice",
            "private_scoring_contract": contract,
        })
    bank = {
        "task_id": m08.TASK_ID,
        "schema_version": m08.SESSION_SCHEMA_VERSION,
        "private_local_only": True,
        "source_hashes": {"fixture": "0" * 64},
        "item_count": 9,
        "unit_count": 9,
        "canonical_egp_row_count": 9,
        "items": items,
        "items_sha256": m08.sha256_value(items),
        "claim_boundaries": {"private_local_only": True},
    }
    graph = {
        "task_id": "A1FS-V1-M1_A1A1PlusPrerequisiteGraphAndCoverage",
        "schema_version": "a1fs.v1.m1.prerequisite_graph_and_coverage.v1",
        "validation_status": bridge.GRAPH_STATUS,
        "source_baseline_sha256": "0" * 64,
        "nodes": [
            {
                "node_id": "LESSON:READING:BASE-L01",
                "node_type": "LESSON",
                "skill": "READING",
                "level": "A1",
                "source_ref": "BASE-L01",
                "mastery_required_before_a2": True,
                "asset_body_count": 1,
                "roles": ["CHK"],
            },
            {
                "node_id": "REF:READING:BASE-CAP",
                "node_type": "CAPABILITY",
                "skill": "READING",
                "level": "A1",
                "source_ref": "BASE-CAP",
                "mastery_required_before_a2": True,
            },
            {
                "node_id": "GATE:A1FS:A2_LOCK",
                "node_type": "A2_LOCK",
                "skill": "FOUR_SKILL",
                "level": "A2",
                "source_ref": "A2_ENTRY",
                "mastery_required_before_a2": False,
            },
        ],
        "edges": [
            {
                "from_node_id": "REF:READING:BASE-CAP",
                "to_node_id": "LESSON:READING:BASE-L01",
                "edge_type": "TAUGHT_BY",
            },
            {
                "from_node_id": "REF:READING:BASE-CAP",
                "to_node_id": "GATE:A1FS:A2_LOCK",
                "edge_type": "UNLOCK_REQUIRES",
            },
            {
                "from_node_id": "LESSON:READING:BASE-L01",
                "to_node_id": "GATE:A1FS:A2_LOCK",
                "edge_type": "UNLOCK_REQUIRES",
            },
        ],
        "coverage": [
            {
                "node_id": "REF:READING:BASE-CAP",
                "skill": "READING",
                "source_ref": "BASE-CAP",
                "coverage_class": "MASTERY",
                "levels": ["A1"],
                "lesson_ids": ["BASE-L01"],
                "asset_body_ids": ["BASE-ASSET"],
                "roles": ["CHK"],
                "coverage_status": "COVERED",
            }
        ],
        "counts": {
            "node_count": 3,
            "edge_count": 3,
            "coverage_record_count": 1,
            "lesson_count": 1,
            "lesson_count_by_level": {"A1": 1, "A1+": 0, "A2": 0},
            "required_mastery_node_count": 2,
            "a2_handoff_lesson_count": 0,
            "uncovered_required_node_count": 0,
        },
        "a2_lock_contract": {
            "gate_node_id": "GATE:A1FS:A2_LOCK",
            "state": "LOCKED_BY_DESIGN",
            "required_mastery_node_ids": [
                "LESSON:READING:BASE-L01",
                "REF:READING:BASE-CAP",
            ],
            "a2_handoff_lesson_node_ids": [],
            "unlock_rule": "ALL_REQUIRED_MASTERY_NODES_MUST_BE_MASTERED",
            "runtime_unlock_implemented": False,
        },
        "claim_boundaries": {"a2_unlocked": False},
        "errors": [],
    }
    graph_path = write(root / "graph.private.json", graph)
    base_payload = {
        "instruction": "Read and answer.",
        "private_scoring_contract": {
            "scoring_mode": "NORMALIZED_TEXT",
            "response_type": "string",
            "accepted_texts": ["base"],
        },
        "response_capture_enabled": True,
    }
    consumer = {
        "task_id": "A1FS-V1-M2_FourSkillAssetBodyConsumerAndQuery",
        "schema_version": "a1fs.v1.m2.four_skill_asset_body_consumer.v1",
        "validation_status": bridge.CONSUMER_STATUS,
        "source_graph_sha256": overlay.file_sha(graph_path),
        "asset_records": [
            {
                "asset_id": "BASE-ASSET",
                "asset_key": "READING:BASE-ASSET",
                "lesson_id": "BASE-L01",
                "skill": "READING",
                "level": "A1",
                "role": "CHK",
                "payload": base_payload,
                "content_digest": overlay.canonical_sha(base_payload),
                "release_scope": "PRIVATE_INTERNAL_D0",
            }
        ],
        "lesson_catalog": [
            {
                "lesson_id": "BASE-L01",
                "lesson_node_id": "LESSON:READING:BASE-L01",
                "skill": "READING",
                "level": "A1",
                "asset_keys": ["READING:BASE-ASSET"],
                "roles": ["CHK"],
                "requirement_node_ids": ["REF:READING:BASE-CAP"],
                "release_scope": "PRIVATE_INTERNAL_D0",
            }
        ],
        "counts": {
            "asset_record_count": 1,
            "lesson_count": 1,
            "learning_lesson_count": 1,
            "a2_handoff_lesson_count": 0,
        },
        "access_contract": {"visibility": "PRIVATE_INTERNAL"},
        "claim_boundaries": {"a2_unlocked": False},
        "errors": [],
    }
    bank_path = write(root / "bank.private.json", bank)
    consumer_path = write(root / "consumer.private.json", consumer)
    source = overlay.load_sources(bank_path, consumer_path, graph_path)
    item_ids = [row["item_id"] for row in items]
    candidate = {
        "task_id": overlay.TASK_ID,
        "schema_version": overlay.SCHEMA_VERSION,
        "validation_status": overlay.CANDIDATE_BLOCKED_STATUS,
        "source_session_bank_sha256": source["bank_hash"],
        "source_consumer_sha256": source["consumer_hash"],
        "source_graph_sha256": source["graph_hash"],
        "item_count": 9,
        "blocked_item_ids": item_ids,
        "items": [
            {"item_id": item_id, "candidate_count": 0, "top_candidates": []}
            for item_id in item_ids
        ],
        "stop_reason": overlay.CANDIDATE_EVIDENCE_STOP,
    }
    candidate_path = write(root / "candidate.safe.json", candidate)
    return {
        "bank_path": bank_path,
        "consumer_path": consumer_path,
        "graph_path": graph_path,
        "candidate_path": candidate_path,
        "item_ids": item_ids,
        "consumer": consumer,
        "graph": graph,
        "candidate": candidate,
    }


@pytest.fixture()
def data() -> dict:
    root = dedicated.REPO_ROOT / ".local" / f"m12f-dedicated-test-{uuid.uuid4().hex}"
    result = fixture(root)
    result["root"] = root
    yield result
    shutil.rmtree(root, ignore_errors=True)


def run_materialize(data: dict) -> dict:
    return dedicated.materialize(
        source_bank_path=data["bank_path"],
        consumer_path=data["consumer_path"],
        graph_path=data["graph_path"],
        candidate_report_path=data["candidate_path"],
        item_ids=data["item_ids"],
        output_root=data["root"] / "output",
    )


def test_materializes_identity_preserving_private_overlays(data: dict) -> None:
    original_consumer = copy.deepcopy(data["consumer"])
    original_graph = copy.deepcopy(data["graph"])
    result = run_materialize(data)
    report = result["report"]
    assert report["validation_status"] == dedicated.STATUS
    assert report["dedicated_asset_count"] == 9
    assert report["required_mastery_added_count"] == 9
    assert report["mapped_count"] == 9
    assert report["mapping_ready"] is True
    assert report["a2_lock_state"] == "LOCKED_BY_DESIGN"
    assert result["mapping"]["ready"] is True
    assert data["consumer"] == original_consumer
    assert data["graph"] == original_graph
    assert result["consumer"]["counts"]["asset_record_count"] == 10
    assert result["consumer"]["counts"]["lesson_count"] == 10
    assert result["graph"]["counts"]["required_mastery_node_count"] == 11
    assert result["graph"]["a2_lock_contract"]["runtime_unlock_implemented"] is False


def test_outputs_initialize_m3_and_preserve_m6_contracts(data: dict) -> None:
    result = run_materialize(data)
    database = data["root"] / "a1fs_m12f.private.sqlite3"
    initialized = m3.LearnerStateStore(database).initialize(result["consumer_output"])
    assert initialized["lesson_count"] == 10
    dedicated_assets = [
        row for row in result["consumer"]["asset_records"]
        if row.get("payload", {}).get("bridge_only") is True
    ]
    assert len(dedicated_assets) == 9
    bank = json.loads(data["bank_path"].read_text(encoding="utf-8"))
    by_item = {row["item_id"]: row for row in bank["items"]}
    for asset in dedicated_assets:
        item_id = asset["payload"]["m12_item_id"]
        assert m6.derive_contract(asset)["capture_enabled"] is True
        assert bridge._contract_drift(asset, by_item[item_id]) == []
        assert asset["payload"]["rendering_allowed"] is False


def test_safe_report_does_not_expose_private_answers(data: dict) -> None:
    result = run_materialize(data)
    serialized = json.dumps(result["report"])
    assert "private answer" not in serialized
    assert "private model" not in serialized
    assert result["report"]["claim_boundaries"]["new_curriculum_authored"] is False
    assert result["report"]["claim_boundaries"]["learner_rendering_enabled"] is False


def test_nonzero_candidate_prevents_dedicated_materialization(data: dict) -> None:
    bad = copy.deepcopy(data["candidate"])
    bad["items"][0]["candidate_count"] = 1
    bad["items"][0]["top_candidates"] = [{"asset_key": "READING:BASE-ASSET"}]
    bad_path = write(data["root"] / "candidate-not-exhausted.safe.json", bad)
    with pytest.raises(dedicated.DedicatedBridgeError, match="candidate_not_exhausted"):
        dedicated.materialize(
            source_bank_path=data["bank_path"],
            consumer_path=data["consumer_path"],
            graph_path=data["graph_path"],
            candidate_report_path=bad_path,
            item_ids=data["item_ids"],
            output_root=data["root"] / "bad-output",
        )


def test_materialization_is_deterministic(data: dict) -> None:
    first = run_materialize(data)
    first_graph = first["report"]["output_graph_sha256"]
    first_consumer = first["report"]["output_consumer_sha256"]
    second = run_materialize(data)
    assert second["report"]["output_graph_sha256"] == first_graph
    assert second["report"]["output_consumer_sha256"] == first_consumer
