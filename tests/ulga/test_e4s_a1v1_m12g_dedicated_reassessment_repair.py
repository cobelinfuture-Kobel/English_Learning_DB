from __future__ import annotations

import copy
import json
import shutil
import uuid
from datetime import datetime, timedelta, timezone

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
from ulga.builders import build_e4s_a1v1_m12g_dedicated_reassessment_repair as repair
from ulga.builders import build_e4s_a1v1_m12g_remediation_reassessment_execution as m12g


def make_shortage_contracts(data: dict, expanded: dict) -> dict:
    bank = json.loads(data["source_bank_path"].read_text(encoding="utf-8"))
    consumer = json.loads(data["consumer_path"].read_text(encoding="utf-8"))
    registry_path = data["resolved_root"] / "cumulative_attempt_registry.private.json"
    ledger_path = data["resolved_root"] / "cumulative_progress_ledger.private.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

    relevant = set(expanded["failed_ids"])
    grouped: dict[str, list[dict]] = {}
    for failed_id in relevant:
        grouped[failed_id] = [
            item
            for item in bank["items"]
            if item["item_id"] == failed_id
            or item["item_id"].startswith(failed_id + "_ALT_")
        ]
        grouped[failed_id].sort(key=lambda item: item["item_id"])

    for failed_id, rows in grouped.items():
        feature = (
            rows[0]["private_scoring_contract"]["scoring_mode"]
            == "FEATURE_RUBRIC"
        )
        if feature:
            for index, item in enumerate(rows, 1):
                item["task_type"] = "text_mode_writing_checkpoint"
                item["learner_contract"] = {
                    "prompt": (
                        "Write one complete A1 sentence for the situation "
                        "using an adjective phrase."
                    ),
                    "response_mode": "short_text",
                    "context": {
                        "situation": f"Describe learner situation {index}.",
                        "required_target": (
                            "Use one adjective phrase with a modifier."
                        ),
                    },
                }
            continue

        assert len(rows) == 4
        targets = ["quickly", "carefully", "soon", "later"]
        for index, (item, target) in enumerate(zip(rows, targets), 1):
            item["task_type"] = "structured_gap_fill"
            item["private_scoring_contract"] = {
                "scoring_mode": "NORMALIZED_TEXT",
                "response_type": "string",
                "accepted_texts": [target],
                "case_insensitive": True,
                "punctuation_tolerance": True,
                "human_review_fallback": False,
            }
            if index <= 2:
                item["learner_contract"] = {
                    "prompt": "Complete the visible sentence using the word bank.",
                    "response_mode": "short_text",
                    "context": {
                        "situation": f"Distinct adverb situation {index}.",
                    },
                    "gap_display_tokens": [
                        "The",
                        "learner",
                        "works",
                        "___",
                        ".",
                    ],
                    "word_bank": [target, f"not-{target}"],
                }
            else:
                item["learner_contract"] = {
                    "prompt": (
                        "Complete the sentence or phrase with the missing "
                        "target form."
                    ),
                    "response_mode": "short_text",
                    "gap_display_tokens": ["See", "you", "___", "."],
                }

    bank["item_count"] = len(bank["items"])
    bank["items_sha256"] = m08.sha256_value(bank["items"])
    bank_hash = m08.sha256_value(bank)

    for asset in consumer["asset_records"]:
        asset["payload"]["m12_session_bank_sha256"] = bank_hash
        asset["content_digest"] = m12g.digest(asset["payload"])
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
    return {"bank": bank, "bank_hash": bank_hash}


@pytest.fixture()
def fixture() -> dict:
    root = bridge.REPO_ROOT / ".local" / (
        f"m12g-dedicated-repair-test-{uuid.uuid4().hex}"
    )
    data = build_fixture(root / "m12f")
    expanded = expand_source_bank(data)
    shortage = make_shortage_contracts(data, expanded)
    learner_id = "m12g-dedicated-repair-fixture-learner"

    bridge.import_resolved(
        **common(data),
        database_path=data["database_path"],
        learner_id=learner_id,
        display_label="M12G Dedicated Repair Fixture Learner",
    )

    target_root = root / "m12g"
    prepared = repair.prepare(
        source_bank_path=data["source_bank_path"],
        base_consumer_path=data["consumer_path"],
        base_graph_path=data["graph_path"],
        source_database_path=data["database_path"],
        resolved_root=data["resolved_root"],
        m12e1_root=data["m12e1_root"],
        learner_id=learner_id,
        display_label="M12G Dedicated Repair Fixture Learner",
        target_root=target_root,
    )
    result = {
        **data,
        **expanded,
        **shortage,
        "learner_id": learner_id,
        "target_root": target_root,
        "prepared": prepared,
    }
    yield result
    shutil.rmtree(root, ignore_errors=True)


def passing_registry(fixture: dict) -> dict:
    package = json.loads(
        fixture["prepared"]["package_path"].read_text(encoding="utf-8")
    )
    consumer = json.loads(
        fixture["prepared"]["consumer_path"].read_text(encoding="utf-8")
    )
    asset_by_key = {
        asset["asset_key"]: asset for asset in consumer["asset_records"]
    }
    start = datetime(2026, 7, 18, 9, 0, tzinfo=timezone.utc)
    attempts = []

    for index, task in enumerate(package["tasks"]):
        submitted = start + timedelta(minutes=index * 2)
        contract = asset_by_key[task["asset_key"]]["payload"][
            "private_scoring_contract"
        ]
        if contract["scoring_mode"] in {"NORMALIZED_TEXT", "EXACT_OPTION"}:
            response = contract["accepted_texts"][0]
        elif contract["scoring_mode"] == "EXACT_SEQUENCE":
            response = list(contract["accepted_sequence"])
        else:
            response = "Complete context-appropriate A1 response."

        review = None
        if task["human_review_required"]:
            review = {
                "decision": "APPROVE",
                "reviewer_id": "fixture-reviewer",
                "reviewed_at": (
                    submitted + timedelta(minutes=1)
                ).isoformat().replace("+00:00", "Z"),
                "criteria": {
                    "grammar_target_match": True,
                    "meaning_matches_context": True,
                    "complete_response": True,
                },
                "notes": "Fixture approval.",
            }
        attempts.append({
            "task_instance_id": task["task_instance_id"],
            "response": response,
            "submitted_at": submitted.isoformat().replace("+00:00", "Z"),
            "operator_review": review,
        })

    return {
        "task_id": package["task_id"],
        "schema_version": m12g.REGISTRY_SCHEMA_VERSION,
        "private_local_only": True,
        "package_sha256": package["package_sha256"],
        "learner_id": fixture["learner_id"],
        "attempts": attempts,
    }


def test_prepare_repairs_exactly_two_ambiguous_gap_items(
    fixture: dict,
) -> None:
    report = fixture["prepared"]["report"]
    assert report["validation_status"] == repair.STATUS
    assert report["required_attempt_count"] == 8
    assert report["learner_contract_valid_count"] == 8
    assert report["dedicated_repair_count"] == 2
    assert report["duplicate_target_sequences_allowed"] is False
    assert report["canonical_authority_modified"] is False
    assert report["generated_learner_answers"] is False

    package = json.loads(
        fixture["prepared"]["package_path"].read_text(encoding="utf-8")
    )
    repaired = [
        task
        for task in package["tasks"]
        if task["source_item_id"].endswith(repair.DERIVED_SUFFIX)
    ]
    assert len(repaired) == 2
    assert all(
        task["learner_contract"]["response_mode"] == "ordered_tokens"
        for task in repaired
    )
    assert all(
        len(task["learner_contract"]["supplied_tokens"]) >= 2
        for task in repaired
    )

    serialized = json.dumps(package)
    assert "accepted_sequence" not in serialized
    assert "accepted_texts" not in serialized

    html = fixture["prepared"]["html_path"].read_text(encoding="utf-8")
    assert "提供的單字" in html
    assert "data-response" in html


def test_repaired_real_evidence_closes_m7(fixture: dict) -> None:
    registry_path = write(
        fixture["target_root"] / "responses.private.json",
        passing_registry(fixture),
    )
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


def test_duplicate_reconstructed_targets_remain_blocked() -> None:
    source = {
        "item_id": "ITEM_ORIGINAL",
        "grammar_unit_id": "GRAMMAR_ADVERB_PHRASES_A1",
        "skill": "reading",
        "task_type": "structured_gap_fill",
        "learner_contract": {
            "prompt": "Complete the sentence.",
            "response_mode": "short_text",
            "gap_display_tokens": ["See", "you", "___", "."],
        },
        "private_scoring_contract": {
            "scoring_mode": "NORMALIZED_TEXT",
            "response_type": "string",
            "accepted_texts": ["soon"],
        },
    }
    bank = {
        f"ITEM_{index}": {
            **copy.deepcopy(source),
            "item_id": f"ITEM_{index}",
        }
        for index in range(4)
    }

    with pytest.raises(
        repair.DedicatedRepairError,
        match="dedicated_reassessment_repair_insufficient",
    ):
        repair.choose_source_items(bank["ITEM_0"], bank, 4)
