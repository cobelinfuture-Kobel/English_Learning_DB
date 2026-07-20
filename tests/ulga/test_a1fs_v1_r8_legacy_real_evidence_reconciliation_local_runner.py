from __future__ import annotations

import importlib.util
import json
import shutil
import uuid
from copy import deepcopy
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4
from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as m08
from ulga.builders import run_a1fs_v1_r8_legacy_real_evidence_reconciliation_local as runner

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_local_fixture(root: Path) -> dict:
    legacy_test = load_module(
        "m12f_fixture_source_for_runner",
        REPO_ROOT / "tests/ulga/test_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge.py",
    )
    reconciliation_test = load_module(
        "r8_reconciliation_fixture_source",
        REPO_ROOT / "tests/ulga/test_a1fs_v1_r8_legacy_real_evidence_deterministic_production_reconciliation.py",
    )
    source_root = root / "legacy"
    data = legacy_test.build_fixture(source_root)
    resolved_target = data["m12e1_root"] / "resolved_representative"
    shutil.move(str(data["resolved_root"]), resolved_target)
    data["resolved_root"] = resolved_target
    bank_path, supply_path = reconciliation_test.current_r4_fixture(data)
    data["current_bank_path"] = bank_path
    data["current_supply_path"] = supply_path
    return data


@pytest.fixture()
def fixture() -> dict:
    root = REPO_ROOT / ".local" / f"r8-local-runner-test-{uuid.uuid4().hex}"
    data = build_local_fixture(root)
    yield {**data, "local_root": root, "output_root": root / "output"}
    shutil.rmtree(root, ignore_errors=True)


def _move(source: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), target)
    return target


def _upgrade_to_production_contract(graph_path: Path, consumer_path: Path) -> None:
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    graph["a2_lock_contract"]["state"] = "LOCKED_BY_DESIGN"
    graph_path.write_text(
        json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    consumer = json.loads(consumer_path.read_text(encoding="utf-8"))
    consumer["source_graph_sha256"] = runner.legacy.file_sha(graph_path)
    for asset in consumer["asset_records"]:
        asset["payload"]["scenario"] = "A school classroom lesson with a teacher and students."
    consumer_path.write_text(
        json.dumps(consumer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _expand_source_bank_to_formal_m08_size(fixture: dict) -> None:
    bank = json.loads(fixture["source_bank_path"].read_text(encoding="utf-8"))
    seed = deepcopy(bank["items"][0])
    for index in range(len(bank["items"]) + 1, 193):
        filler = deepcopy(seed)
        filler["item_id"] = f"M08_FORMAL_FILLER_{index:03d}"
        if "session_item_id" in filler:
            filler["session_item_id"] = f"M08_SESSION:M08_FORMAL_FILLER_{index:03d}"
        bank["items"].append(filler)
    bank["item_count"] = len(bank["items"])
    bank["items_sha256"] = m08.sha256_value(bank["items"])
    fixture["source_bank_path"].write_text(
        json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    bank_hash = m08.sha256_value(bank)

    registry_path = fixture["resolved_root"] / "cumulative_attempt_registry.private.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["session_bank_sha256"] = bank_hash
    registry_path.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    ledger_path = fixture["resolved_root"] / "cumulative_progress_ledger.private.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["session_bank_sha256"] = bank_hash
    ledger["attempt_registry_sha256"] = m08.sha256_value(registry)
    ledger_path.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    consumer = json.loads(fixture["consumer_path"].read_text(encoding="utf-8"))
    for asset in consumer["asset_records"]:
        payload = asset.get("payload", {})
        if isinstance(payload.get("m12_item_id"), str):
            payload["m12_session_bank_sha256"] = bank_hash
    fixture["consumer_path"].write_text(
        json.dumps(consumer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def test_runner_discovers_unique_chain_and_projects(fixture: dict) -> None:
    report = runner.run(local_root=fixture["local_root"], output_root=fixture["output_root"])
    assert report["validation_status"] == runner.STATUS
    assert report["reconciliation"]["legacy_real_attempt_count"] == 9
    assert report["reconciliation"]["exact_mapped_attempt_count"] == 9
    assert report["reconciliation"]["mapped_breadth_cell_count"] == 9
    assert report["reconciliation"]["pass_count"] == 7
    assert report["reconciliation"]["failure_count"] == 2
    assert report["stop_reason"] == "REAL_LEARNER_ATTESTATION_REQUIRED"
    assert report["next_short_step"] == runner.NEXT_SHORT_STEP


def test_runner_accepts_formal_192_item_m08_bank_with_nine_attempts(fixture: dict) -> None:
    _expand_source_bank_to_formal_m08_size(fixture)
    report = runner.run(local_root=fixture["local_root"], output_root=fixture["output_root"])
    assert report["validation_status"] == runner.STATUS, report
    assert report["discovery_counts"]["legacy_bank_candidate_count"] == 1
    assert report["discovery_counts"]["legacy_semantic_chain_count"] == 1
    assert report["reconciliation"]["legacy_real_attempt_count"] == 9
    assert report["reconciliation"]["exact_mapped_attempt_count"] == 9


def test_runner_uses_content_identity_and_rematerializes_missing_current_pair(fixture: dict) -> None:
    local = fixture["local_root"]
    fixture["current_bank_path"].unlink()
    fixture["current_supply_path"].unlink()
    _upgrade_to_production_contract(fixture["graph_path"], fixture["consumer_path"])

    _move(fixture["source_bank_path"], local / "shuffled/a/source_payload.json")
    _move(
        fixture["resolved_root"] / "cumulative_attempt_registry.private.json",
        local / "shuffled/b/attempts_payload.json",
    )
    _move(
        fixture["resolved_root"] / "cumulative_progress_ledger.private.json",
        local / "shuffled/c/ledger_payload.json",
    )
    (fixture["resolved_root"] / "cumulative_progress_query_index.json").unlink()
    _move(
        fixture["m12e1_root"] / "human_review_materialization_safe_report.json",
        local / "shuffled/d/review_status.json",
    )
    _move(fixture["consumer_path"], local / "shuffled/e/consumer_payload.json")
    _move(fixture["graph_path"], local / "shuffled/f/graph_payload.json")

    report = runner.run(local_root=local, output_root=fixture["output_root"])
    assert report["validation_status"] == runner.STATUS, report
    assert report["reconciliation"]["exact_mapped_attempt_count"] == 9
    counts = report["discovery_counts"]
    assert counts["legacy_semantic_chain_count"] == 1
    assert counts["deterministic_materialization_attempt_count"] >= 1
    assert counts["deterministic_materialization_validated_count"] >= 1
    assert counts["deterministic_materialized_pair_count"] >= 1


def test_runner_blocks_multiple_distinct_exact_production_identities(fixture: dict) -> None:
    bank = json.loads(fixture["current_bank_path"].read_text(encoding="utf-8"))
    supply = json.loads(fixture["current_supply_path"].read_text(encoding="utf-8"))
    bank["selection_contract"]["fixture_variant"] = "SECOND_EXACT_IDENTITY"
    bank_core = {key: value for key, value in bank.items() if key != "bank_sha256"}
    bank["bank_sha256"] = r4.digest(bank_core)
    supply["fixture_variant"] = "SECOND_EXACT_IDENTITY"
    supply_core = {key: value for key, value in supply.items() if key != "report_sha256"}
    supply["report_sha256"] = r4.digest(supply_core)
    second = fixture["local_root"] / "second_current_identity"
    second.mkdir(parents=True)
    (second / "a1fs_v1_r4_approved_practice_bank.private.json").write_text(
        json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (second / "a1fs_v1_r4_supply_report.safe.json").write_text(
        json.dumps(supply, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = runner.run(local_root=fixture["local_root"], output_root=fixture["output_root"])
    assert report["validation_status"] == runner.BLOCKED
    assert report["discovery_counts"]["exact_ready_identity_count"] > 1
    assert report["stop_reason"] == "MULTIPLE_DISTINCT_EXACT_RECONCILIATION_CHAINS"


def test_runner_safe_report_contains_no_absolute_path(fixture: dict) -> None:
    report = runner.run(local_root=fixture["local_root"], output_root=fixture["output_root"])
    serialized = json.dumps(report, ensure_ascii=False)
    assert str(fixture["local_root"]) not in serialized
    assert "a complete model response" not in serialized
    assert "incomplete response" not in serialized


def test_inspect_aggregates_safe_mismatch_diagnostics(tmp_path: Path, monkeypatch) -> None:
    resolved = tmp_path / "resolved"
    resolved.mkdir(parents=True)
    registry_path = resolved / "cumulative_attempt_registry.private.json"
    registry_path.write_text("{}\n", encoding="utf-8")
    bank_path = tmp_path / "bank.json"
    supply_path = tmp_path / "supply.json"
    bank_path.write_text("{}\n", encoding="utf-8")
    supply_path.write_text("{}\n", encoding="utf-8")
    secret_ids = ["private-item-a", "private-item-b"]

    def fake_reconcile(**kwargs):
        return {
            "report": {
                "validation_status": runner.reconciliation.BLOCKED_STATUS,
                "counts": {
                    "legacy_real_attempt_count": 9,
                    "exact_mapped_attempt_count": 4,
                    "mapped_breadth_cell_count": 3,
                    "pass_count": 3,
                    "failure_count": 1,
                },
                "issues": {
                    "current_contract_drift_ids": secret_ids,
                    "current_item_missing_ids": [],
                },
            }
        }

    monkeypatch.setattr(runner.reconciliation, "reconcile", fake_reconcile)
    ready, inspected, diagnostics = runner._inspect(
        [{"resolved_root": resolved}],
        [{
            "current_bank_path": bank_path,
            "current_supply_path": supply_path,
            "current_bank_sha256": "b" * 64,
            "current_supply_sha256": "c" * 64,
        }],
        staging_root=tmp_path / "probes",
    )
    assert ready == {}
    assert inspected == 1
    assert diagnostics["inspect_exception_count"] == 0
    assert diagnostics["issue_combination_counts"] == {
        "current_contract_drift_ids": 1
    }
    assert diagnostics["issue_item_counts"] == {
        "current_contract_drift_ids": 2
    }
    assert diagnostics["max_exact_mapped_attempt_count"] == 4
    assert diagnostics["max_mapped_breadth_cell_count"] == 3
    assert not any(secret in json.dumps(diagnostics) for secret in secret_ids)
