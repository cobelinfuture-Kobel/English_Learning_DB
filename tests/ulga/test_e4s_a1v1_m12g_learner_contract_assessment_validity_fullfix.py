from __future__ import annotations

import copy
import json
import shutil
import uuid
from pathlib import Path

import pytest

from tests.ulga.test_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge import (
    build_fixture,
    common,
    write,
)
from tests.ulga.test_e4s_a1v1_m12g_remediation_reassessment_execution import (
    expand_source_bank,
    passing_registry,
)
from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as m08
from ulga.builders import build_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge as bridge
from ulga.builders import build_e4s_a1v1_m12g_learner_contract_assessment_validity_fullfix as fullfix
from ulga.builders import build_e4s_a1v1_m12g_remediation_reassessment_execution as m12g


def make_realistic_contracts(data: dict, expanded: dict) -> dict:
    bank = json.loads(data["source_bank_path"].read_text(encoding="utf-8"))
    consumer = json.loads(data["consumer_path"].read_text(encoding="utf-8"))
    registry_path = data["resolved_root"] / "cumulative_attempt_registry.private.json"
    ledger_path = data["resolved_root"] / "cumulative_progress_ledger.private.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

    relevant = tuple(expanded["failed_ids"])
    for item in bank["items"]:
        item_id = str(item["item_id"])
        if not any(item_id == failed or item_id.startswith(failed + "_ALT_") for failed in relevant):
            continue
        contract = item["private_scoring_contract"]
        feature = contract["scoring_mode"] == "FEATURE_RUBRIC"
        if feature:
            item["task_type"] = "text_mode_writing_checkpoint"
            item["learner_contract"] = {
                "prompt": "Write one complete A1 sentence for the situation using an adjective phrase.",
                "response_mode": "short_text",
                "context": {
                    "situation": f"Describe the friendly learner shown in situation {item_id}.",
                    "required_target": "Use one adjective phrase with a modifier.",
                },
            }
        else:
            accepted = contract["accepted_texts"][0]
            item["task_type"] = "structured_gap_fill"
            item["learner_contract"] = {
                "prompt": "Complete the visible sentence using the word bank.",
                "response_mode": "short_text",
                "context": {
                    "situation": f"School schedule example {item_id}.",
                    "word_bank": [accepted, f"distractor-{item_id}"],
                },
                "gap_display_tokens": ["The", "answer", "is", "___", "."],
                "word_bank": [accepted, f"distractor-{item_id}"],
            }

    bank["item_count"] = len(bank["items"])
    bank["items_sha256"] = m08.sha256_value(bank["items"])
    bank_hash = m08.sha256_value(bank)
    for asset in consumer["asset_records"]:
        asset["payload"]["m12_session_bank_sha256"] = bank_hash
        asset["content_digest"] = m12g.digest(asset["payload"])
    consumer["m12f_dedicated_private_bridge_overlay"]["source_session_bank_sha256"] = bank_hash

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
    root = bridge.REPO_ROOT / ".local" / f"m12g-validity-test-{uuid.uuid4().hex}"
    data = build_fixture(root / "m12f")
    expanded = expand_source_bank(data)
    realistic = make_realistic_contracts(data, expanded)
    learner_id = "m12g-validity-fixture-learner"
    bridge.import_resolved(
        **common(data),
        database_path=data["database_path"],
        learner_id=learner_id,
        display_label="M12G Validity Fixture Learner",
    )
    target_root = root / "m12g"
    prepared = fullfix.prepare(
        source_bank_path=data["source_bank_path"],
        base_consumer_path=data["consumer_path"],
        base_graph_path=data["graph_path"],
        source_database_path=data["database_path"],
        resolved_root=data["resolved_root"],
        m12e1_root=data["m12e1_root"],
        learner_id=learner_id,
        display_label="M12G Validity Fixture Learner",
        target_root=target_root,
    )
    result = {
        **data,
        **expanded,
        **realistic,
        "learner_id": learner_id,
        "target_root": target_root,
        "prepared": prepared,
    }
    yield result
    shutil.rmtree(root, ignore_errors=True)


def test_incomplete_real_shapes_fail_closed() -> None:
    scoring = {
        "scoring_mode": "FEATURE_RUBRIC",
        "response_type": "string",
        "model_texts": ["private model"],
        "rubric": {"grammar_target_match": "required"},
        "human_review_fallback": True,
    }
    with pytest.raises(fullfix.AssessmentValidityError, match="context_stimulus_missing"):
        fullfix.validate_learner_contract(
            item_id="WRITING_NO_CONTEXT",
            task_type="text_mode_writing_checkpoint",
            learner={
                "prompt": "Write one sentence for the situation.",
                "response_mode": "short_text",
            },
            scoring=scoring,
        )

    with pytest.raises(fullfix.AssessmentValidityError, match="ordered_tokens_stimulus_missing"):
        fullfix.validate_learner_contract(
            item_id="ORDER_NO_TOKENS",
            task_type="ordering",
            learner={
                "prompt": "Put the supplied tokens in order.",
                "response_mode": "ordered_tokens",
            },
            scoring={
                "scoring_mode": "EXACT_SEQUENCE",
                "response_type": "string_array",
                "accepted_sequence": ["Tom", "runs"],
            },
        )

    with pytest.raises(fullfix.AssessmentValidityError, match="gap_disambiguating_stimulus_missing"):
        fullfix.validate_learner_contract(
            item_id="AMBIGUOUS_GAP",
            task_type="structured_gap_fill",
            learner={
                "prompt": "Complete: See you ____.",
                "response_mode": "short_text",
                "gap_display_tokens": ["See", "you", "____", "."],
            },
            scoring={
                "scoring_mode": "NORMALIZED_TEXT",
                "response_type": "string",
                "accepted_texts": ["soon"],
            },
        )


def test_select_and_order_contracts_require_exact_visible_stimulus() -> None:
    learner, _ = fullfix.validate_learner_contract(
        item_id="SELECT_VALID",
        task_type="form_choice",
        learner={
            "prompt": "Choose the correct option.",
            "response_mode": "select_one",
            "options": ["at", "in", "on"],
        },
        scoring={
            "scoring_mode": "EXACT_OPTION",
            "response_type": "string",
            "accepted_texts": ["on"],
        },
    )
    assert learner["assessment_validity"]["status"] == "PASS"

    learner, _ = fullfix.validate_learner_contract(
        item_id="ORDER_VALID",
        task_type="ordering",
        learner={
            "prompt": "Put the supplied tokens in order.",
            "response_mode": "ordered_tokens",
            "supplied_tokens": ["runs", "Tom"],
        },
        scoring={
            "scoring_mode": "EXACT_SEQUENCE",
            "response_type": "string_array",
            "accepted_sequence": ["Tom", "runs"],
        },
    )
    assert learner["assessment_validity"]["stimulus_complete"] is True


def test_prepare_produces_eight_valid_rendered_tasks(fixture: dict) -> None:
    report = fixture["prepared"]["report"]
    assert report["validation_status"] == fullfix.STATUS
    assert report["required_attempt_count"] == 8
    assert report["learner_contract_valid_count"] == 8
    assert report["rendered_task_count"] == 8
    assert report["legacy_incomplete_package_reusable"] is False

    package = json.loads(fixture["prepared"]["package_path"].read_text(encoding="utf-8"))
    assert all(
        task["learner_contract"]["assessment_validity"]["status"] == "PASS"
        for task in package["tasks"]
    )
    serialized = json.dumps(package)
    assert "accepted_texts" not in serialized
    assert "accepted_sequence" not in serialized
    assert "model_texts" not in serialized
    assert '"rubric"' not in serialized

    html = fixture["prepared"]["html_path"].read_text(encoding="utf-8")
    for marker in (
        "gap_display_tokens",
        "supplied_tokens",
        "supplied_morphemes",
        "情境／資料",
        "教師審核",
        "data-response",
    ):
        assert marker in html


def test_valid_real_evidence_still_closes_m7_remediation(fixture: dict) -> None:
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


def test_source_selection_rejects_duplicate_visible_stimulus() -> None:
    scoring = {
        "scoring_mode": "NORMALIZED_TEXT",
        "response_type": "string",
        "accepted_texts": ["on"],
    }
    source = {
        "item_id": "ITEM_0",
        "grammar_unit_id": "UNIT",
        "skill": "reading",
        "task_type": "structured_gap_fill",
        "learner_contract": {
            "prompt": "Complete the sentence.",
            "response_mode": "short_text",
            "context": {"word_bank": ["on", "in"]},
            "gap_display_tokens": ["___", "Monday"],
        },
        "private_scoring_contract": scoring,
    }
    bank = {
        f"ITEM_{index}": {
            **copy.deepcopy(source),
            "item_id": f"ITEM_{index}",
        }
        for index in range(4)
    }
    with pytest.raises(fullfix.AssessmentValidityError, match="valid_reassessment_items_insufficient"):
        fullfix.choose_source_items(source, bank, 4)
