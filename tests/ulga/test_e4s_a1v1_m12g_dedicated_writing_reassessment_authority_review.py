from __future__ import annotations

import copy
import json
import shutil
import uuid
from datetime import datetime, timezone

import pytest

from tests.ulga.test_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge import (
    build_fixture,
    common,
    write,
)
from tests.ulga.test_e4s_a1v1_m12g_remediation_reassessment_execution import (
    expand_source_bank,
)
from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as m08
from ulga.builders import build_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge as bridge
from ulga.builders import build_e4s_a1v1_m12g_writing_reassessment_review_runtime as review
from ulga.builders import build_e4s_a1v1_m12g_remediation_reassessment_execution as m12g


def shape_real_writing_shortage(data: dict, expanded: dict) -> dict:
    bank = json.loads(data["source_bank_path"].read_text(encoding="utf-8"))
    consumer = json.loads(data["consumer_path"].read_text(encoding="utf-8"))
    registry_path = data["resolved_root"] / "cumulative_attempt_registry.private.json"
    ledger_path = data["resolved_root"] / "cumulative_progress_ledger.private.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

    by_id = {row["item_id"]: row for row in bank["items"]}
    target_id = next(
        item_id
        for item_id in expanded["failed_ids"]
        if by_id[item_id]["private_scoring_contract"]["scoring_mode"]
        != "FEATURE_RUBRIC"
    )
    target = by_id[target_id]
    cohort = [
        row
        for row in bank["items"]
        if row["grammar_unit_id"] == target["grammar_unit_id"]
        and row["skill"] == target["skill"]
        and (
            row["item_id"] == target_id
            or row["item_id"].startswith(target_id + "_ALT_")
        )
    ]
    cohort.sort(key=lambda row: row["item_id"])
    assert len(cohort) == 4
    target = next(row for row in cohort if row["item_id"] == target_id)
    alternatives = [row for row in cohort if row["item_id"] != target_id]

    target["task_type"] = "structured_gap_fill"
    target["learner_contract"] = {
        "prompt": "Complete the sentence or phrase with the missing target form.",
        "response_mode": "short_text",
        "gap_display_tokens": ["See", "you", "___", "."],
    }
    target["private_scoring_contract"] = {
        "scoring_mode": "NORMALIZED_TEXT",
        "response_type": "string",
        "accepted_texts": ["soon", "later"],
        "case_insensitive": True,
        "punctuation_tolerance": True,
        "human_review_fallback": False,
    }

    alternatives[0]["task_type"] = "structured_word_order"
    alternatives[0]["learner_contract"] = {
        "prompt": "Put the supplied tokens in the correct order.",
        "response_mode": "ordered_tokens",
        "supplied_tokens": ["quietly", "works", "the", "learner"],
    }
    alternatives[0]["private_scoring_contract"] = {
        "scoring_mode": "EXACT_SEQUENCE",
        "response_type": "string_array",
        "accepted_sequence": ["the", "learner", "works", "quietly"],
        "case_insensitive": True,
        "punctuation_tolerance": True,
        "human_review_fallback": False,
    }

    rubric_template = next(
        copy.deepcopy(row["private_scoring_contract"])
        for row in bank["items"]
        if row["private_scoring_contract"]["scoring_mode"] == "FEATURE_RUBRIC"
    )
    rubric_template["model_texts"] = ["The learner works carefully."]
    shared_learner = {
        "prompt": (
            "Write one complete A1 sentence for the situation using an "
            "adverb or adverb phrase."
        ),
        "response_mode": "short_text",
        "context": {
            "situation": "A learner finishes a school task with care.",
            "required_target": "Use an adverb or adverb phrase.",
        },
    }
    alternatives[1]["task_type"] = "guided_contextual_writing"
    alternatives[1]["learner_contract"] = copy.deepcopy(shared_learner)
    alternatives[1]["private_scoring_contract"] = copy.deepcopy(rubric_template)
    alternatives[2]["task_type"] = "text_mode_writing_checkpoint"
    alternatives[2]["learner_contract"] = copy.deepcopy(shared_learner)
    alternatives[2]["private_scoring_contract"] = copy.deepcopy(rubric_template)

    bank["item_count"] = len(bank["items"])
    bank["items_sha256"] = m08.sha256_value(bank["items"])
    bank_hash = m08.sha256_value(bank)
    for asset in consumer["asset_records"]:
        payload = asset["payload"]
        payload["m12_session_bank_sha256"] = bank_hash
        if payload.get("m12_item_id") == target_id:
            payload["private_scoring_contract"] = copy.deepcopy(
                target["private_scoring_contract"]
            )
        asset["content_digest"] = m12g.digest(payload)
    consumer["m12f_dedicated_private_bridge_overlay"][
        "source_session_bank_sha256"
    ] = bank_hash
    registry["session_bank_sha256"] = bank_hash
    ledger["session_bank_sha256"] = bank_hash
    ledger["attempt_registry_sha256"] = m08.sha256_value(registry)

    write(data["source_bank_path"], bank)
    write(data["consumer_path"], consumer)
    write(registry_path, registry)
    write(ledger_path, ledger)
    return {"target_id": target_id, "bank_hash": bank_hash}


@pytest.fixture()
def fixture() -> dict:
    root = bridge.REPO_ROOT / ".local" / (
        f"m12g-writing-review-test-{uuid.uuid4().hex}"
    )
    data = build_fixture(root / "m12f")
    expanded = expand_source_bank(data)
    shaped = shape_real_writing_shortage(data, expanded)
    nested_resolved = data["m12e1_root"] / "resolved_representative"
    shutil.copytree(data["resolved_root"], nested_resolved)
    data["resolved_root"] = nested_resolved
    learner_id = "m12g-writing-review-fixture"
    bridge.import_resolved(
        **common(data),
        database_path=data["database_path"],
        learner_id=learner_id,
        display_label="M12G Writing Review Fixture",
    )
    result = {
        **data,
        **expanded,
        **shaped,
        "root": root,
        "learner_id": learner_id,
    }
    yield result
    shutil.rmtree(root, ignore_errors=True)


def approved_registry(queue: dict) -> dict:
    now = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
    return {
        "task_id": review.TASK_ID,
        "schema_version": review.DECISION_SCHEMA,
        "private_local_only": True,
        "review_queue_sha256": queue["review_queue_sha256"],
        "decision_count": 2,
        "decisions": [
            {
                "review_entry_id": entry["review_entry_id"],
                "candidate_item_id": entry["candidate"]["item_id"],
                "candidate_sha256": entry["candidate_sha256"],
                "decision": "APPROVE_AS_IS",
                "reviewer_id": "fixture-authority-reviewer",
                "reviewed_at": now,
                "criteria": {key: True for key in review.REVIEW_CRITERIA},
                "notes": None,
            }
            for entry in queue["candidates"]
        ],
    }


def test_prepare_review_materializes_two_distinct_pending_candidates(
    fixture: dict,
) -> None:
    prepared = review.prepare_review(
        source_bank_path=fixture["source_bank_path"],
        target_item_id=fixture["target_id"],
        target_root=fixture["root"] / "review",
    )
    report = prepared["report"]
    assert report["validation_status"] == review.STATUS_PENDING
    assert report["source_valid_unique_count"] == 2
    assert report["candidate_count"] == 2
    assert report["approved_candidate_count"] == 0
    queue = json.loads(prepared["queue_path"].read_text(encoding="utf-8"))
    assert len(queue["candidates"]) == 2
    fingerprints = {
        review.fullfix._contract_fingerprint(
            row["candidate"]["learner_contract"]
        )
        for row in queue["candidates"]
    }
    assert len(fingerprints) == 2
    assert all(
        row["candidate"]["session_status"]
        == "PENDING_PRIVATE_AUTHORITY_REVIEW"
        for row in queue["candidates"]
    )
    html = prepared["html_path"].read_text(encoding="utf-8")
    assert "Model response" in html
    assert "APPROVE_AS_IS" in html


def test_approved_candidates_create_valid_eight_task_m12g_package(
    fixture: dict,
) -> None:
    review_root = fixture["root"] / "review"
    prepared = review.prepare_review(
        source_bank_path=fixture["source_bank_path"],
        target_item_id=fixture["target_id"],
        target_root=review_root,
    )
    queue = json.loads(prepared["queue_path"].read_text(encoding="utf-8"))
    decisions_path = write(
        review_root / "approved.private.json",
        approved_registry(queue),
    )
    source_database_before = fixture["database_path"].read_bytes()
    result = review.apply_review_and_prepare(
        source_bank_path=fixture["source_bank_path"],
        base_consumer_path=fixture["consumer_path"],
        base_graph_path=fixture["graph_path"],
        source_database_path=fixture["database_path"],
        resolved_root=fixture["resolved_root"],
        m12e1_root=fixture["m12e1_root"],
        review_queue_path=prepared["queue_path"],
        decision_registry_path=decisions_path,
        learner_id=fixture["learner_id"],
        display_label="M12G Writing Review Fixture",
        target_root=fixture["root"] / "approved",
    )
    report = result["report"]
    assert report["validation_status"] == review.STATUS_READY
    assert report["approved_candidate_count"] == 2
    assert report["pending_node_count"] == 2
    assert report["required_attempt_count"] == 8
    assert report["learner_contract_valid_count"] == 8
    assert report["a2_lock_state"] == "LOCKED_BY_DESIGN"
    assert report["private_database_overlay_rebound"] is True
    assert report["source_database_original_modified"] is False
    assert fixture["database_path"].read_bytes() == source_database_before
    assert result["source_database_overlay_path"].is_file()
    package = json.loads(result["package_path"].read_text(encoding="utf-8"))
    selected = {row["source_item_id"] for row in package["tasks"]}
    assert set(report["approved_candidate_ids"]).issubset(selected)
    assert "accepted_texts" not in json.dumps(package)
    assert "model_texts" not in json.dumps(package)


def test_nonapproved_candidate_cannot_enter_m12g(fixture: dict) -> None:
    prepared = review.prepare_review(
        source_bank_path=fixture["source_bank_path"],
        target_item_id=fixture["target_id"],
        target_root=fixture["root"] / "review-reject",
    )
    queue = json.loads(prepared["queue_path"].read_text(encoding="utf-8"))
    registry = approved_registry(queue)
    registry["decisions"][1]["decision"] = "REJECT"
    registry["decisions"][1]["criteria"] = {
        key: False for key in review.REVIEW_CRITERIA
    }
    decisions_path = write(
        fixture["root"] / "review-reject" / "rejected.private.json",
        registry,
    )
    with pytest.raises(review.WritingReviewError, match="candidate_not_approved"):
        review.apply_review_and_prepare(
            source_bank_path=fixture["source_bank_path"],
            base_consumer_path=fixture["consumer_path"],
            base_graph_path=fixture["graph_path"],
            source_database_path=fixture["database_path"],
            resolved_root=fixture["resolved_root"],
            m12e1_root=fixture["m12e1_root"],
            review_queue_path=prepared["queue_path"],
            decision_registry_path=decisions_path,
            learner_id=fixture["learner_id"],
            display_label="M12G Writing Review Fixture",
            target_root=fixture["root"] / "blocked",
        )
