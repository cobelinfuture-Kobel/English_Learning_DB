from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from tests.ulga.test_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge import (
    build_fixture,
    common,
    write,
)
from tests.ulga.test_e4s_a1v1_m12g_dedicated_writing_reassessment_authority_review import (
    shape_real_writing_shortage,
)
from tests.ulga.test_e4s_a1v1_m12g_dual_writing_reassessment_review_completion import (
    approved_registry,
    prepare_both,
    shape_second_real_shortage,
)
from tests.ulga.test_e4s_a1v1_m12g_remediation_reassessment_execution import (
    expand_source_bank,
)
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import build_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge as bridge
from ulga.builders import build_e4s_a1v1_m12g_additional_reassessment_continuation as continuation
from ulga.builders import build_e4s_a1v1_m12g_dual_writing_reassessment_review_completion as dual
from ulga.builders import build_e4s_a1v1_m12g_remediation_reassessment_execution as m12g


def _operator_review(submitted: datetime, *, approved: bool) -> dict[str, Any]:
    return {
        "decision": "APPROVE" if approved else "REJECT",
        "reviewer_id": "fixture-developer",
        "reviewed_at": (submitted + timedelta(seconds=1))
        .isoformat()
        .replace("+00:00", "Z"),
        "criteria": {
            "grammar_target_match": approved,
            "meaning_matches_context": approved,
            "complete_response": approved,
        },
        "notes": None,
    }


def _contracts(package: dict, consumer: dict) -> dict[str, dict]:
    assets = {row["asset_key"]: row for row in consumer["asset_records"]}
    return {
        task["task_instance_id"]: m6.derive_contract(assets[task["asset_key"]])
        for task in package["tasks"]
    }


def _failure_partition(package: dict, contracts: dict[str, dict]) -> set[str]:
    grouped: dict[str, list[dict]] = {}
    for task in package["tasks"]:
        grouped.setdefault(task["node_id"], []).append(task)
    failures: set[str] = set()
    for rows in grouped.values():
        rows.sort(key=lambda row: (row["attempt_order"], row["task_instance_id"]))
        ordered = next(
            (
                row
                for row in rows
                if contracts[row["task_instance_id"]]["scoring_mode"]
                == "EXACT_SEQUENCE"
            ),
            None,
        )
        failures.add((ordered or rows[0])["task_instance_id"])
    assert len(failures) == len(grouped) == 2
    return failures


def _passing_response(contract: dict) -> object:
    if contract["scoring_mode"] == "EXACT_SEQUENCE":
        return list(contract["accepted_sequence"])
    if contract["scoring_mode"] in {"NORMALIZED_TEXT", "EXACT_OPTION"}:
        return contract["accepted_texts"][0]
    if contract["scoring_mode"] == "FEATURE_RUBRIC":
        return "A complete A1 response approved by the fixture developer."
    raise AssertionError(contract["scoring_mode"])


def _registry(
    *,
    package: dict,
    consumer: dict,
    learner_id: str,
    induce_one_failure_per_node: bool,
    start: datetime,
) -> dict:
    contracts = _contracts(package, consumer)
    failures = (
        _failure_partition(package, contracts)
        if induce_one_failure_per_node
        else set()
    )
    attempts = []
    actual_failures: set[str] = set()
    for index, task in enumerate(package["tasks"]):
        submitted = start + timedelta(minutes=index * 2)
        task_id = task["task_instance_id"]
        contract = contracts[task_id]
        fail = task_id in failures
        response = _passing_response(contract)
        review = None
        if task["human_review_required"]:
            review = _operator_review(submitted, approved=not fail)
        elif fail:
            if contract["scoring_mode"] == "EXACT_SEQUENCE":
                response = ["incorrect single item"]
            elif contract["scoring_mode"] in {"NORMALIZED_TEXT", "EXACT_OPTION"}:
                response = "incorrect response"
            else:
                raise AssertionError(contract["scoring_mode"])
        if fail:
            actual_failures.add(task["node_id"])
        attempts.append(
            {
                "task_instance_id": task_id,
                "response": response,
                "submitted_at": submitted.isoformat().replace("+00:00", "Z"),
                "operator_review": review,
            }
        )
    if induce_one_failure_per_node:
        assert len(actual_failures) == 2
    return {
        "task_id": m12g.TASK_ID,
        "schema_version": m12g.REGISTRY_SCHEMA_VERSION,
        "private_local_only": True,
        "package_sha256": package["package_sha256"],
        "learner_id": learner_id,
        "attempts": attempts,
    }


@pytest.fixture()
def fixture() -> dict:
    root = bridge.REPO_ROOT / ".local" / (
        f"m12g-continuation-test-{uuid.uuid4().hex}"
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

    original_adverb = dual.ADVERB_GRAMMAR_UNIT
    original_adjective = dual.ADJECTIVE_GRAMMAR_UNIT
    dual.ADVERB_GRAMMAR_UNIT = adverb_grammar_unit
    dual.ADJECTIVE_GRAMMAR_UNIT = adjective_grammar_unit

    nested_resolved = data["m12e1_root"] / "resolved_representative"
    shutil.copytree(data["resolved_root"], nested_resolved)
    data["resolved_root"] = nested_resolved
    learner_id = "m12g-continuation-fixture"
    bridge.import_resolved(
        **common(data),
        database_path=data["database_path"],
        learner_id=learner_id,
        display_label="M12G Continuation Fixture",
    )
    context = {
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
        adverb_queue, adjective_queue, adverb, adjective = prepare_both(context)
        adverb_decisions = write(
            root / "adverb-review" / "approved.private.json",
            approved_registry(adverb_queue),
        )
        adjective_decisions = write(
            root / "adjective-review" / "approved.private.json",
            approved_registry(adjective_queue),
        )
        dual_result = dual.apply_dual_reviews_and_prepare(
            source_bank_path=data["source_bank_path"],
            base_consumer_path=data["consumer_path"],
            base_graph_path=data["graph_path"],
            source_database_path=data["database_path"],
            resolved_root=data["resolved_root"],
            m12e1_root=data["m12e1_root"],
            adverb_review_queue_path=adverb["queue_path"],
            adverb_decision_registry_path=adverb_decisions,
            adjective_review_queue_path=adjective["queue_path"],
            adjective_decision_registry_path=adjective_decisions,
            learner_id=learner_id,
            display_label="M12G Continuation Fixture",
            target_root=root / "dual-approved",
        )
        source_package = json.loads(
            dual_result["package_path"].read_text(encoding="utf-8")
        )
        consumer = json.loads(
            dual_result["consumer_path"].read_text(encoding="utf-8")
        )
        first_registry = _registry(
            package=source_package,
            consumer=consumer,
            learner_id=learner_id,
            induce_one_failure_per_node=True,
            start=datetime(2026, 7, 18, 15, 0, tzinfo=timezone.utc),
        )
        first_registry_path = write(
            root / "first-import" / "responses.private.json", first_registry
        )
        first_import = m12g.import_evidence(
            package_path=dual_result["package_path"],
            registry_path=first_registry_path,
            consumer_path=dual_result["consumer_path"],
            graph_path=dual_result["graph_path"],
            database_path=dual_result["database_path"],
            learner_id=learner_id,
            target_root=root / "first-import",
        )
        assert first_import["report"]["validation_status"] == m12g.PARTIAL_STATUS
        state = m12g.database_state(
            dual_result["database_path"],
            dual_result["consumer_path"],
            dual_result["graph_path"],
            learner_id,
        )
        pending_ids = set(first_import["report"]["pending_node_ids"])
        states = {
            row["node_id"]: row
            for row in state["snapshot"]["node_states"]
            if row["node_id"] in pending_ids
        }
        assert len(states) == 2
        assert all(row["pass_count"] == 3 for row in states.values())
        assert all(row["fail_count"] == 2 for row in states.values())
        assert all(row["resolved_attempt_count"] == 5 for row in states.values())
        assert all(row["pass_rate"] == 0.6 for row in states.values())
        yield {
            **context,
            "dual_result": dual_result,
            "source_package": source_package,
            "consumer": consumer,
        }
    finally:
        dual.ADVERB_GRAMMAR_UNIT = original_adverb
        dual.ADJECTIVE_GRAMMAR_UNIT = original_adjective
        shutil.rmtree(root, ignore_errors=True)


def test_prepare_preserves_history_and_builds_ten_attempts(fixture: dict) -> None:
    dual_result = fixture["dual_result"]
    database_before = dual_result["database_path"].read_bytes()
    prepared = continuation.prepare(
        source_package_path=dual_result["package_path"],
        consumer_path=dual_result["consumer_path"],
        graph_path=dual_result["graph_path"],
        database_path=dual_result["database_path"],
        learner_id=fixture["learner_id"],
        target_root=fixture["root"] / "continuation",
    )
    report = prepared["report"]
    assert report["validation_status"] == continuation.STATUS
    assert report["pending_node_count"] == 2
    assert report["required_attempt_count"] == 10
    assert set(report["required_attempt_count_by_node"].values()) == {5}
    assert report["source_database_original_modified"] is False
    assert dual_result["database_path"].read_bytes() == database_before
    assert report["a2_lock_state"] == "LOCKED_BY_DESIGN"

    package = json.loads(prepared["package_path"].read_text(encoding="utf-8"))
    grouped: dict[str, list[dict]] = {}
    for task in package["tasks"]:
        grouped.setdefault(task["node_id"], []).append(task)
    assert len(grouped) == 2
    assert all(len(rows) == 5 for rows in grouped.values())
    assert len({row["task_instance_id"] for row in package["tasks"]}) == 10
    serialized = json.dumps(package)
    assert "accepted_sequence" not in serialized
    assert "accepted_texts" not in serialized
    assert "model_texts" not in serialized

    html = prepared["html_path"].read_text(encoding="utf-8")
    assert continuation.PROHIBITED_DELIMITER_EXPRESSION not in html
    assert "article._ordered" in html
    assert "dataset.tokenBank" in html
    assert "dataset.tokenAnswer" in html


def test_ten_additional_passes_close_both_nodes(fixture: dict) -> None:
    dual_result = fixture["dual_result"]
    prepared = continuation.prepare(
        source_package_path=dual_result["package_path"],
        consumer_path=dual_result["consumer_path"],
        graph_path=dual_result["graph_path"],
        database_path=dual_result["database_path"],
        learner_id=fixture["learner_id"],
        target_root=fixture["root"] / "continuation-import",
    )
    package = json.loads(prepared["package_path"].read_text(encoding="utf-8"))
    registry = _registry(
        package=package,
        consumer=fixture["consumer"],
        learner_id=fixture["learner_id"],
        induce_one_failure_per_node=False,
        start=datetime(2026, 7, 19, 8, 0, tzinfo=timezone.utc),
    )
    registry_path = write(
        fixture["root"] / "continuation-import" / "responses.private.json",
        registry,
    )
    result = m12g.import_evidence(
        package_path=prepared["package_path"],
        registry_path=registry_path,
        consumer_path=dual_result["consumer_path"],
        graph_path=dual_result["graph_path"],
        database_path=dual_result["database_path"],
        learner_id=fixture["learner_id"],
        target_root=fixture["root"] / "continuation-import" / "import",
    )
    report = result["report"]
    assert report["validation_status"] == m12g.IMPORT_STATUS
    assert report["imported_attempt_count"] == 10
    assert report["closed_remediation_node_count"] == 2
    assert report["pending_node_ids"] == []
    assert report["m7_validation_error_count"] == 0
    assert report["a2_lock_state"] == "LOCKED"
    assert report["stop_reason"] == "NONE"
