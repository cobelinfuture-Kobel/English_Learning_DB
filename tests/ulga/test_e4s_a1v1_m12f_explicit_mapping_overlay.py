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
        skill = "writing" if feature else "reading"
        asset_key = f"{skill.upper()}:{asset_id}"
        lesson_id = f"LESSON_{index:02d}"
        node_id = f"REF:{skill.upper()}:CAP_{index:02d}"
        if feature:
            source_contract = {
                "scoring_mode": "FEATURE_RUBRIC",
                "response_type": "string",
                "model_texts": [f"very happy {index}"],
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
            task_type = "text_mode_writing_checkpoint"
            body_text = (
                f"Write one sentence with adjective phrases. "
                f"Target example: very happy {index}."
            )
        else:
            source_contract = {
                "scoring_mode": "NORMALIZED_TEXT",
                "response_type": "string",
                "accepted_texts": [f"nice and friendly {index}"],
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
            task_type = "form_choice"
            body_text = (
                f"Choose the option that uses adjective phrases. "
                f"Target example: nice and friendly {index}."
            )
        items.append({
            "item_id": item_id,
            "grammar_unit_id": "GRAMMAR_ADJECTIVE_PHRASES_A1",
            "canonical_egp_row_ids": [f"EGP_{index:02d}"],
            "skill": skill,
            "task_type": task_type,
            "private_scoring_contract": source_contract,
        })
        payload = {
            "body_text": body_text,
            "private_scoring_contract": existing_contract,
            "response_capture_enabled": True,
        }
        assets.append({
            "asset_id": asset_id,
            "asset_key": asset_key,
            "lesson_id": lesson_id,
            "skill": skill.upper(),
            "level": "A1",
            "role": role,
            "payload": payload,
            "content_digest": hashlib.sha256(
                json.dumps(payload, sort_keys=True).encode()
            ).hexdigest(),
            "release_scope": "PRIVATE_INTERNAL_D0",
        })
        nodes.append({
            "node_id": node_id,
            "node_type": "CAPABILITY",
            "source_ref": f"CAP_{index:02d}",
            "skill": skill.upper(),
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
            "lesson_node_id": f"LESSON:{skill.upper()}:{lesson_id}",
            "skill": skill.upper(),
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
        "a2_lock_contract": {
            "required_mastery_node_ids": [row["node_id"] for row in nodes]
        },
    }
    graph_path = write(root / "graph.private.json", graph)
    consumer = {
        "task_id": "A1FS-V1-M2_FourSkillAssetBodyConsumerAndQuery",
        "schema_version": "a1fs.v1.m2.four_skill_asset_body_consumer.v1",
        "validation_status": bridge.CONSUMER_STATUS,
        "source_graph_sha256": overlay.file_sha(graph_path),
        "asset_records": assets,
        "lesson_catalog": lesson_catalog,
        "counts": {
            "asset_record_count": 9,
            "lesson_count": 9,
            "learning_lesson_count": 9,
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
                "asset_key": assets[index - 1]["asset_key"],
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
    assert report["stop_reason"] == overlay.CANDIDATE_REVIEW_STOP
    assert report["blocked_item_ids"] == []
    assert all(row["candidate_count"] >= 1 for row in report["items"])
    assert all(
        row["top_candidates"][0]["content_equivalence_evidence"]["approved"]
        for row in report["items"]
    )
    assert all(
        row["top_candidates"][0]["content_equivalence_evidence"]["evidence_field_scope"]
        == "TASK_ANSWER_ACCEPTANCE_ONLY"
        for row in report["items"]
    )
    serialized = json.dumps(report)
    assert "old answer" not in serialized
    assert "nice and friendly" not in serialized
    assert "very happy" not in serialized


def test_generic_structural_matches_are_blocked_not_ranked(data: dict) -> None:
    source = copy.deepcopy(data["source"])
    for asset in source["assets"]:
        asset["payload"]["body_text"] = (
            "Read the passage. Which place is named in the text? "
            "Record the learner response and route the result."
        )
    report = overlay.build_candidate_report(source, data["item_ids"], limit=3)
    assert report["validation_status"] == overlay.CANDIDATE_BLOCKED_STATUS
    assert report["stop_reason"] == overlay.CANDIDATE_EVIDENCE_STOP
    assert set(report["blocked_item_ids"]) == set(data["item_ids"])
    assert all(row["candidate_count"] == 0 for row in report["items"])
    assert all(row["structurally_compatible_count"] >= 1 for row in report["items"])
    assert all(not row["top_candidates"] for row in report["items"])


def test_passage_anchor_and_incidental_choose_are_not_evidence() -> None:
    source_item = {
        "item_id": "GRAMMAR_ADVERB_PHRASES_A1__TFX_A01",
        "grammar_unit_id": "GRAMMAR_ADVERB_PHRASES_A1",
        "task_type": "context_choice",
        "private_scoring_contract": {
            "scoring_mode": "EXACT_OPTION",
            "response_type": "string",
            "accepted_texts": ["See you soon."],
        },
    }
    asset = {
        "payload": {
            "unseen_text": (
                "We are going to choose a birthday card. See you soon!"
            ),
            "items": [
                {
                    "question": "Which place is named in the text?",
                    "answer": "bookshop",
                }
            ],
        }
    }
    evidence = overlay.content_equivalence_evidence(asset, source_item)
    assert evidence["approved"] is False
    assert evidence["matched_target_anchor_count"] == 0
    assert evidence["matched_task_markers"] == []


def test_negative_route_and_broad_relation_text_are_not_evidence() -> None:
    adjective_item = {
        "item_id": "GRAMMAR_ADJECTIVE_PHRASES_A1__TFX_A02",
        "grammar_unit_id": "GRAMMAR_ADJECTIVE_PHRASES_A1",
        "task_type": "text_mode_writing_checkpoint",
        "private_scoring_contract": {
            "scoring_mode": "FEATURE_RUBRIC",
            "response_type": "string",
            "model_texts": ["very happy"],
        },
    }
    adjective_asset = {
        "payload": {
            "body_text": "Write one truthful playground sentence with a place phrase.",
            "acceptance_rule": "Production makes useful modifier attachment observable.",
            "critical_failure": "Adjective count prohibited.",
            "diagnostic_route": "Adjective phrase attachment.",
        }
    }
    adjective_evidence = overlay.content_equivalence_evidence(
        adjective_asset,
        adjective_item,
    )
    assert adjective_evidence["approved"] is False
    assert adjective_evidence["matched_concept_tokens"] == ["phrases"]

    preposition_item = {
        "item_id": "GRAMMAR_BASIC_PREPOSITIONS_PLACE__TFX_A02",
        "grammar_unit_id": "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
        "task_type": "text_mode_writing_checkpoint",
        "private_scoring_contract": {
            "scoring_mode": "FEATURE_RUBRIC",
            "response_type": "string",
            "model_texts": ["on the table"],
        },
    }
    preposition_asset = {
        "payload": {
            "body_text": "Write one complete picnic event and add one useful detail.",
            "acceptance_rule": "Production makes accurate place/time relation observable.",
            "scaffold_and_fade": "Use a phrase bank.",
        }
    }
    preposition_evidence = overlay.content_equivalence_evidence(
        preposition_asset,
        preposition_item,
    )
    assert preposition_evidence["approved"] is False
    assert preposition_evidence["matched_concept_tokens"] == []


def test_operator_authority_builds_bridge_compatible_private_overlay(data: dict) -> None:
    original = copy.deepcopy(data["consumer"])
    consumer_overlay, report = overlay.build_overlay(
        data["source"], data["item_ids"], data["authority_path"]
    )
    assert report["validation_status"] == overlay.OVERLAY_STATUS
    assert report["mapped_count"] == 9
    assert data["consumer"] == original
    assert all(row["content_equivalence_evidence"]["approved"] for row in report["mapped"])
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


def test_operator_label_cannot_bypass_content_equivalence(data: dict) -> None:
    source = copy.deepcopy(data["source"])
    source["assets"][0]["payload"]["body_text"] = "Record the learner output and route the result."
    with pytest.raises(overlay.OverlayError, match="authority_target_content_equivalence_unproven"):
        overlay.build_overlay(source, data["item_ids"], data["authority_path"])


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
