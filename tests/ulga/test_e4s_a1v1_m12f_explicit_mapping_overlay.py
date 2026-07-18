from __future__ import annotations

import copy
import hashlib
import json
import shutil
import uuid
from pathlib import Path

import pytest

from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as m08
from ulga.builders import build_e4s_a1v1_m12f_explicit_mapping_overlay as overlay
from ulga.builders import build_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge as bridge


def write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def fixture_data(root: Path) -> dict:
    items = []
    assets = []
    nodes = []
    coverage = []
    lesson_catalog = []
    for index in range(1, 10):
        feature = index >= 8
        item_id = f"GRAMMAR_ADJECTIVE_PHRASES_A1__TFX_{index:02d}"
        asset_id = f"ASSET_{index:02d}"
        asset_key = f"READING:{asset_id}"
        lesson_id = f"LESSON_{index:02d}"
        node_id = f"REF:READING:CAP_{index:02d}"
        if feature:
            source_contract = {
                "scoring_mode": "FEATURE_RUBRIC",
                "response_type": "string",
                "model_texts": [f"model {index}"],
                "rubric": {
                    "grammar_target_match": "Target grammar is present.",
                    "meaning_matches_context": "Meaning fits the context.",
                    "complete_response": "Response is complete.",
                },
                "human_review_fallback": True,
            }
            existing_contract = {
                "scoring_mode": "FEATURE_RUBRIC",
                "response_type": "string",
                "rubric": {"placeholder": "fixture"},
                "human_review_fallback": True,
            }
            role = "EVD"
        else:
            source_contract = {
                "scoring_mode": "NORMALIZED_TEXT",
                "response_type": "string",
                "accepted_texts": [f"answer {index}"],
                "case_insensitive": True,
                "punctuation_tolerance": True,
                "human_review_fallback": False,
            }
            existing_contract = {
                "scoring_mode": "NORMALIZED_TEXT",
                "response_type": "string",
                "accepted_texts": [f"old answer {index}"],
                "case_insensitive": True,
                "punctuation_tolerance": True,
                "human_review_fallback": False,
            }
            role = "CHK"
        items.append({
            "item_id": item_id,
            "grammar_unit_id": "GRAMMAR_ADJECTIVE_PHRASES_A1",
            "canonical_egp_row_ids": [f"EGP_{index:02d}"],
            "skill": "reading",
            "private_scoring_contract": source_contract,
        })
        payload = {
            "body_text": f"Practice adjective phrases in context number {index}.",
            "private_scoring_contract": existing_contract,
            "response_capture_enabled": True,
        }
        assets.append({
            "asset_id": asset_id,
            "asset_key": asset_key,
            "lesson_id": lesson_id,
            "skill": "READING",
            "level": "A1",
            "role": role,
            "payload": payload,
            "content_digest": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
            "release_scope": "PRIVATE_INTERNAL_D0",
        })
        nodes.append({
            "node_id": node_id,
            "node_type": "CAPABILITY",
            "source_ref": f"CAP_{index:02d}",
            "skill": "READING",
            "level": "A1",
        })
        coverage.append({
            "node_id": node_id,
            "source_ref": f"CAP_{index:02d}",
            "asset_body_ids": [asset_id],
            "lesson_ids": [lesson_id],
        })
        lesson_catalog.append({
            "lesson_id": lesson_id,
            "lesson_node_id": f"LESSON:READING:{lesson_id}",
            "skill": "READING",
            "level": "A1",
            "asset_keys": [asset_key],
            "roles": [role],
            "requirement_node_ids": [node_id],
            "release_scope": "PRIVATE_INTERNAL_D0",
        })
    bank = {
        "task_id": m08.TASK_ID,
        "schema_version": m08.SESSION_SCHEMA_VERSION,
        "private_local_only": True,
        "source_hashes": {"fixture": "0" * 64},
        "item_count": len(items),
        "unit_count": 1,
        "canonical_egp_row_count": 9,
        "items": items,
        "items_sha256": m08.sha256_value(items),
        "claim_boundaries": {"private_local_only": True},
    }
    graph = {
        "task_id": "A1FS-V1-M1_A1A1PlusPrerequisiteGraphAndCoverage",
        "validation_status": bridge.GRAPH_STATUS,
        "nodes": nodes,
        "coverage": coverage,
        "a2_lock_contract": {"required_mastery_node_ids": [row["node_id"] for row in nodes]},
    }
    graph_path = write(root / "graph.private.json", graph)
    consumer = {
        "task_id": "A1FS-V1-M2_FourSkillAssetBodyConsumerAndQuery",
        "schema_version": "a1fs.v1.m2.four_skill_asset_body_consumer.v1",
        "validation_status": bridge.CONSUMER_STATUS,
        "source_graph_sha256": overlay.file_sha(graph_path),
        "asset_records": assets,
        "lesson_catalog": lesson_catalog,
        "counts": {"asset_record_count": 9, "lesson_count": 9, "learning_lesson_count": 9, "a2_handoff_lesson_count": 0},
        "access_contract": {"visibility": "PRIVATE_INTERNAL"},
        "claim_boundaries": {"a2_unlocked": False},
        "errors": [],
    }
    bank_path = write(root / "bank.private.json", bank)
    consumer_path = write(root / "consumer.private.json", consumer)
    source = overlay.load_sources(bank_path, consumer_path, graph_path)
    item_ids = [row["item_id"] for row in items]
    authority = {
        "task_id": overlay.AUTHORITY_TASK_ID,
        "schema_version": overlay.AUTHORITY_SCHEMA_VERSION,
        "approval_state": "OPERATOR_APPROVED",
        "source_session_bank_sha256": source["bank_hash"],
        "source_consumer_sha256": source["consumer_hash"],
        "source_graph_sha256": source["graph_hash"],
        "mappings": [
            {
                "item_id": item_id,
                "asset_key": f"READING:ASSET_{index:02d}",
                "evidence_basis": "OPERATOR_REVIEWED_CONTENT_EQUIVALENCE",
            }
            for index, item_id in enumerate(item_ids, 1)
        ],
    }
    authority_path = write(root / "mapping_authority.private.json", authority)
    return {
        "source": source,
        "item_ids": item_ids,
        "authority": authority,
        "authority_path": authority_path,
        "consumer": consumer,
    }


@pytest.fixture()
def data() -> dict:
    root = overlay.REPO_ROOT / ".local" / f"m12f-overlay-test-{uuid.uuid4().hex}"
    result = fixture_data(root)
    result["root"] = root
    yield result
    shutil.rmtree(root, ignore_errors=True)


def test_candidate_report_is_safe_and_operator_gated(data: dict) -> None:
    report = overlay.build_candidate_report(data["source"], data["item_ids"], limit=3)
    assert report["validation_status"] == overlay.CANDIDATE_STATUS
    assert report["stop_reason"] == "OPERATOR_MAPPING_SELECTION_REQUIRED"
    assert all(row["candidate_count"] >= 1 for row in report["items"])
    serialized = json.dumps(report)
    assert "old answer" not in serialized
    assert "answer 1" not in serialized


def test_operator_authority_builds_bridge_compatible_private_overlay(data: dict) -> None:
    original = copy.deepcopy(data["consumer"])
    consumer_overlay, report = overlay.build_overlay(data["source"], data["item_ids"], data["authority_path"])
    assert report["validation_status"] == overlay.OVERLAY_STATUS
    assert report["mapped_count"] == 9
    assert data["consumer"] == original
    source = {
        "entries_by_id": {item_id: {} for item_id in data["item_ids"]},
        "consumer": consumer_overlay,
        "graph": data["source"]["graph"],
        "bank_hash": data["source"]["bank_hash"],
        "bank_by_id": data["source"]["items_by_id"],
    }
    mapped = bridge._mapping(source)
    assert mapped["ready"] is True
    assert len(mapped["mapped"]) == 9
    assert not any(mapped["issues"].values())


def test_authority_hash_drift_fails_closed(data: dict) -> None:
    bad = copy.deepcopy(data["authority"])
    bad["source_consumer_sha256"] = "0" * 64
    bad_path = write(data["root"] / "bad-authority.private.json", bad)
    with pytest.raises(overlay.OverlayError, match="authority_consumer_hash"):
        overlay.build_overlay(data["source"], data["item_ids"], bad_path)


def test_authority_cannot_reuse_asset(data: dict) -> None:
    bad = copy.deepcopy(data["authority"])
    bad["mappings"][1]["asset_key"] = bad["mappings"][0]["asset_key"]
    bad_path = write(data["root"] / "duplicate-authority.private.json", bad)
    with pytest.raises(overlay.OverlayError, match="authority_asset_reused"):
        overlay.build_overlay(data["source"], data["item_ids"], bad_path)
