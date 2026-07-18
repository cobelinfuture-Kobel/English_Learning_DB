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
from tests.ulga.test_e4s_a1v1_m12g_dedicated_writing_reassessment_authority_review import (
    shape_real_writing_shortage,
)
from tests.ulga.test_e4s_a1v1_m12g_remediation_reassessment_execution import (
    expand_source_bank,
)
from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as m08
from ulga.builders import build_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge as bridge
from ulga.builders import build_e4s_a1v1_m12g_dual_writing_reassessment_review_completion as dual
from ulga.builders import build_e4s_a1v1_m12g_writing_reassessment_review_runtime as review
from ulga.builders import build_e4s_a1v1_m12g_remediation_reassessment_execution as m12g


def shape_second_real_shortage(data: dict, expanded: dict) -> tuple[str, str]:
    bank = json.loads(data["source_bank_path"].read_text(encoding="utf-8"))
    consumer = json.loads(data["consumer_path"].read_text(encoding="utf-8"))
    registry_path = data["resolved_root"] / "cumulative_attempt_registry.private.json"
    ledger_path = data["resolved_root"] / "cumulative_progress_ledger.private.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

    by_id = {row["item_id"]: row for row in bank["items"]}
    feature_failed_id = next(
        item_id
        for item_id in expanded["failed_ids"]
        if by_id[item_id]["private_scoring_contract"]["scoring_mode"]
        == "FEATURE_RUBRIC"
    )
    feature_source = by_id[feature_failed_id]
    adjective_grammar_unit = feature_source["grammar_unit_id"]
    cohort = [
        row
        for row in bank["items"]
        if row["grammar_unit_id"] == adjective_grammar_unit
        and row["skill"] == feature_source["skill"]
        and (
            row["item_id"] == feature_failed_id
            or row["item_id"].startswith(feature_failed_id + "_ALT_")
        )
    ]
    cohort.sort(key=lambda row: row["item_id"])
    assert len(cohort) == 4

    rubric = copy.deepcopy(feature_source["private_scoring_contract"])
    rubric["model_texts"] = ["The learner is very happy."]

    first_contract = {
        "prompt": "Write one A1 sentence using an adjective phrase.",
        "response_mode": "short_text",
        "context": {
            "situation": "A learner gets a birthday card and smiles.",
            "required_target": "Use very plus an adjective.",
        },
    }
    second_contract = {
        "prompt": "Write one A1 sentence using an adjective phrase.",
        "response_mode": "short_text",
        "context": {
            "situation": "A learner finishes a long walk and sits down.",
            "required_target": "Use very plus an adjective.",
        },
    }

    cohort[0]["task_type"] = "guided_contextual_writing"
    cohort[0]["learner_contract"] = copy.deepcopy(first_contract)
    cohort[0]["private_scoring_contract"] = copy.deepcopy(rubric)

    cohort[1]["task_type"] = "structured_gap_fill"
    cohort[1]["learner_contract"] = {
        "prompt": "Complete the adjective phrase.",
        "response_mode": "short_text",
        "gap_display_tokens": ["The", "learner", "is", "___", "."],
    }
    cohort[1]["private_scoring_contract"] = {
        "scoring_mode": "NORMALIZED_TEXT",
        "response_type": "string",
        "accepted_texts": ["happy", "tired"],
        "case_insensitive": True,
        "punctuation_tolerance": True,
        "human_review_fallback": False,
    }

    cohort[2]["task_type"] = "guided_contextual_writing"
    cohort[2]["learner_contract"] = copy.deepcopy(second_contract)
    cohort[2]["private_scoring_contract"] = copy.deepcopy(rubric)

    cohort[3]["task_type"] = "text_mode_writing_checkpoint"
    cohort[3]["learner_contract"] = copy.deepcopy(first_contract)
    cohort[3]["private_scoring_contract"] = copy.deepcopy(rubric)

    bank["item_count"] = len(bank["items"])
    bank["items_sha256"] = m08.sha256_value(bank["items"])
    bank_hash = m08.sha256_value(bank)
    for asset in consumer["asset_records"]:
        payload = asset["payload"]
        payload["m12_session_bank_sha256"] = bank_hash
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
    return cohort[1]["item_id"], adjective_grammar_unit


@pytest.fixture()
def fixture() -> dict:
    root = bridge.REPO_ROOT / ".local" / (
        f"m12g-dual-writing-review-test-{uuid.uuid4().hex}"
    )
    data = build_fixture(root / "m12f")
    expanded = expand_source_bank(data)
    shaped = shape_real_writing_shortage(data, expanded)
    adjective_target_id, adjective_grammar_unit = shape_second_real_shortage(
        data, expanded
    )
    bank = json.loads(data["source_bank_path"].read_text(encoding="utf-8"))
    by_id = {row["item_id"]: row for row in bank["items"]}
    adverb_grammar_unit = by_id[shaped["target_id"]]["grammar_unit_id"]

    original_adverb_unit = dual.ADVERB_GRAMMAR_UNIT
    original_adjective_unit = dual.ADJECTIVE_GRAMMAR_UNIT
    dual.ADVERB_GRAMMAR_UNIT = adverb_grammar_unit
    dual.ADJECTIVE_GRAMMAR_UNIT = adjective_grammar_unit

    nested_resolved = data["m12e1_root"] / "resolved_representative"
    shutil.copytree(data["resolved_root"], nested_resolved)
    data["resolved_root"] = nested_resolved
    learner_id = "m12g-dual-writing-review-fixture"
    bridge.import_resolved(
        **common(data),
        database_path=data["database_path"],
        learner_id=learner_id,
        display_label="M12G Dual Writing Review Fixture",
    )
    result = {
        **data,
        **expanded,
        **shaped,
        "root": root,
        "learner_id": learner_id,
        "adverb_target_id": shaped["target_id"],
        "adjective_target_id": adjective_target_id,
        "adverb_grammar_unit": adverb_grammar_unit,
        "adjective_grammar_unit": adjective_grammar_unit,
    }
    try:
        yield result
    finally:
        dual.ADVERB_GRAMMAR_UNIT = original_adverb_unit
        dual.ADJECTIVE_GRAMMAR_UNIT = original_adjective_unit
        shutil.rmtree(root, ignore_errors=True)


def approved_registry(queue: dict, *, reject_second: bool = False) -> dict:
    now = datetime(2026, 7, 18, 15, 0, tzinfo=timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
    rows = []
    for index, entry in enumerate(queue["candidates"]):
        approved = not (reject_second and index == 1)
        rows.append(
            {
                "review_entry_id": entry["review_entry_id"],
                "candidate_item_id": entry["candidate"]["item_id"],
                "candidate_sha256": entry["candidate_sha256"],
                "decision": "APPROVE_AS_IS" if approved else "REJECT",
                "reviewer_id": "fixture-developer",
                "reviewed_at": now,
                "criteria": {
                    key: approved for key in dual.REVIEW_CRITERIA
                },
                "notes": None,
            }
        )
    return {
        "task_id": dual.TASK_ID,
        "schema_version": dual.DECISION_SCHEMA,
        "private_local_only": True,
        "review_queue_sha256": queue["review_queue_sha256"],
        "decision_count": 2,
        "decisions": rows,
    }


def prepare_both(fixture: dict) -> tuple[dict, dict, object, object]:
    adverb = review.prepare_review(
        source_bank_path=fixture["source_bank_path"],
        target_item_id=fixture["adverb_target_id"],
        target_root=fixture["root"] / "adverb-review",
    )
    adjective = dual.prepare_adjective_review(
        source_bank_path=fixture["source_bank_path"],
        target_item_id=fixture["adjective_target_id"],
        target_root=fixture["root"] / "adjective-review",
    )
    adverb_queue = json.loads(adverb["queue_path"].read_text(encoding="utf-8"))
    adjective_queue = json.loads(
        adjective["queue_path"].read_text(encoding="utf-8")
    )
    return adverb_queue, adjective_queue, adverb, adjective


def test_prepare_adjective_review_materializes_two_pending_candidates(
    fixture: dict,
) -> None:
    _, adjective_queue, _, adjective = prepare_both(fixture)
    report = adjective["report"]
    assert report["validation_status"] == dual.STATUS_PENDING
    assert report["grammar_unit_id"] == fixture["adjective_grammar_unit"]
    assert report["source_valid_unique_count"] == 2
    assert report["candidate_count"] == 2
    assert len(adjective_queue["candidates"]) == 2
    assert all(
        row["candidate"]["session_status"]
        == "PENDING_PRIVATE_AUTHORITY_REVIEW"
        for row in adjective_queue["candidates"]
    )
    html = adjective["html_path"].read_text(encoding="utf-8")
    assert f"{fixture['adjective_grammar_unit']}__M12G_WRA01" in html
    assert f"{fixture['adjective_grammar_unit']}__M12G_WRA02" in html
    assert r"model_texts.join('\n')" in html


def test_two_approved_reviews_create_valid_eight_task_package(
    fixture: dict,
) -> None:
    adverb_queue, adjective_queue, adverb, adjective = prepare_both(fixture)
    adverb_decisions = write(
        fixture["root"] / "adverb-review" / "approved.private.json",
        approved_registry(adverb_queue),
    )
    adjective_decisions = write(
        fixture["root"] / "adjective-review" / "approved.private.json",
        approved_registry(adjective_queue),
    )
    database_before = fixture["database_path"].read_bytes()
    result = dual.apply_dual_reviews_and_prepare(
        source_bank_path=fixture["source_bank_path"],
        base_consumer_path=fixture["consumer_path"],
        base_graph_path=fixture["graph_path"],
        source_database_path=fixture["database_path"],
        resolved_root=fixture["resolved_root"],
        m12e1_root=fixture["m12e1_root"],
        adverb_review_queue_path=adverb["queue_path"],
        adverb_decision_registry_path=adverb_decisions,
        adjective_review_queue_path=adjective["queue_path"],
        adjective_decision_registry_path=adjective_decisions,
        learner_id=fixture["learner_id"],
        display_label="M12G Dual Writing Review Fixture",
        target_root=fixture["root"] / "approved",
    )
    report = result["report"]
    assert report["validation_status"] == dual.STATUS_READY
    assert report["approved_candidate_count"] == 4
    assert report["pending_node_count"] == 2
    assert report["required_attempt_count"] == 8
    assert report["learner_contract_valid_count"] == 8
    assert report["a2_lock_state"] == "LOCKED_BY_DESIGN"
    assert report["private_database_overlay_rebound"] is True
    assert report["source_database_original_modified"] is False
    assert fixture["database_path"].read_bytes() == database_before
    package = json.loads(result["package_path"].read_text(encoding="utf-8"))
    selected = {row["source_item_id"] for row in package["tasks"]}
    assert set(report["approved_candidate_ids"]).issubset(selected)
    assert len(package["tasks"]) == 8
    assert "accepted_texts" not in json.dumps(package)
    assert "model_texts" not in json.dumps(package)


def test_unapproved_adjective_candidate_blocks_dual_apply(fixture: dict) -> None:
    adverb_queue, adjective_queue, adverb, adjective = prepare_both(fixture)
    adverb_decisions = write(
        fixture["root"] / "adverb-review" / "approved.private.json",
        approved_registry(adverb_queue),
    )
    adjective_decisions = write(
        fixture["root"] / "adjective-review" / "rejected.private.json",
        approved_registry(adjective_queue, reject_second=True),
    )
    with pytest.raises(dual.core.WritingReviewError, match="candidate_not_approved"):
        dual.apply_dual_reviews_and_prepare(
            source_bank_path=fixture["source_bank_path"],
            base_consumer_path=fixture["consumer_path"],
            base_graph_path=fixture["graph_path"],
            source_database_path=fixture["database_path"],
            resolved_root=fixture["resolved_root"],
            m12e1_root=fixture["m12e1_root"],
            adverb_review_queue_path=adverb["queue_path"],
            adverb_decision_registry_path=adverb_decisions,
            adjective_review_queue_path=adjective["queue_path"],
            adjective_decision_registry_path=adjective_decisions,
            learner_id=fixture["learner_id"],
            display_label="M12G Dual Writing Review Fixture",
            target_root=fixture["root"] / "blocked",
        )
