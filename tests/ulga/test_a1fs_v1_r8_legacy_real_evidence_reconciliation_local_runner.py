from __future__ import annotations

import importlib.util
import json
import shutil
import uuid
from copy import deepcopy
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_r3_complete_breadth_denominator_coverage_gap_planner as r3
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


def _attach_current_r3_coverage(data: dict, bank_path: Path, supply_path: Path) -> Path:
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    supply = json.loads(supply_path.read_text(encoding="utf-8"))
    items_by_cell: dict[str, list[dict]] = {}
    for item in bank["items"]:
        items_by_cell.setdefault(str(item["breadth_cell_id"]), []).append(item)

    cells = []
    for row in supply["cell_supply"]:
        cell_id = str(row["breadth_cell_id"])
        items = items_by_cell[cell_id]
        skills = sorted({str(item["skill"]) for item in items})
        empty = {"required": [], "observed": [], "missing": []}
        cells.append({
            "cell_id": cell_id,
            "capability_node_id": f"REF:{row['capability_id']}",
            "capability_id": row["capability_id"],
            "obligation_id": f"OBLIGATION:{cell_id}",
            "life_task_id": row["life_task_id"],
            "domain": row["domain"],
            "status": "DEPLOYED",
            "dimension_coverage": {
                "skills": {"required": skills, "observed": skills, "missing": []},
                "support_levels": deepcopy(empty),
                "initiative_levels": deepcopy(empty),
                "variation_types": deepcopy(empty),
                "transfer_distances": deepcopy(empty),
                "evidence_levels": deepcopy(empty),
                "retention_stages": deepcopy(empty),
            },
            "matching_deployment_ids": [],
            "source_refs": [],
            "next_actions": [],
        })

    status_counts = {name: 0 for name in r3.CELL_STATUSES}
    status_counts["DEPLOYED"] = len(cells)
    core = {
        "task_id": r3.TASK_ID,
        "schema_version": r3.SCHEMA_VERSION,
        "validation_status": r3.STATUS,
        "source_bindings": {
            "ontology_sha256": "1" * 64,
            "graph_sha256": "2" * 64,
            "profiles_sha256": "3" * 64,
            "deployments_sha256": "4" * 64,
            "m10_structural_coverage": None,
        },
        "counts": {
            "required_mastery_node_count": len(cells),
            "required_capability_node_count": len(cells),
            "profile_defined_count": len(cells),
            "profile_missing_count": 0,
            "denominator_cell_count": len(cells),
            "deployment_contract_count": len(cells),
            "gap_count": 0,
            "status_counts": status_counts,
        },
        "coverage_metrics": {
            "structural_ready_count": len(cells),
            "structural_ready_percent": 100.0,
            "retention_complete_count": 0,
            "retention_complete_percent": 0.0,
            "false_100_percent_blocked": True,
            "completion_denominator_source": "FIXTURE_EXPLICIT_CELLS",
        },
        "profile_missing_capability_node_ids": [],
        "cells": cells,
        "ranked_gaps": [],
        "claim_boundaries": {
            "m1_graph_modified": False,
            "m10_structural_coverage_replaced": False,
            "cartesian_product_generated": False,
            "a2_unlocked": False,
            "mastery_claimed": False,
            "retention_claimed_from_structure": False,
            "audio_completion_required": False,
        },
        "next_short_step": r3.NEXT_SHORT_STEP,
    }
    coverage = {**core, "report_sha256": r3.digest(core)}
    coverage_path = data["root"] / "current_coverage.safe.json"
    coverage_path.write_text(
        json.dumps(coverage, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    bindings = dict(supply["source_bindings"])
    bindings["coverage_sha256"] = coverage["report_sha256"]
    bank["source_bindings"] = dict(bindings)
    supply["source_bindings"] = dict(bindings)
    bank_core = {key: value for key, value in bank.items() if key != "bank_sha256"}
    supply_core = {key: value for key, value in supply.items() if key != "report_sha256"}
    bank["bank_sha256"] = r4.digest(bank_core)
    supply["report_sha256"] = r4.digest(supply_core)
    bank_path.write_text(
        json.dumps(bank, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    supply_path.write_text(
        json.dumps(supply, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return coverage_path


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
    coverage_path = _attach_current_r3_coverage(data, bank_path, supply_path)
    data["current_coverage_path"] = coverage_path
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



def _prepare_hash_bound_source_context_case(fixture: dict, *, include_source_context: bool) -> None:
    fixture["current_bank_path"].unlink()
    fixture["current_supply_path"].unlink()

    graph = json.loads(fixture["graph_path"].read_text(encoding="utf-8"))
    graph["a2_lock_contract"]["state"] = "LOCKED_BY_DESIGN"
    fixture["graph_path"].write_text(
        json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    bank = json.loads(fixture["source_bank_path"].read_text(encoding="utf-8"))
    for row in bank["items"]:
        scoring = row.get("private_scoring_contract", {})
        if scoring.get("scoring_mode") == "FEATURE_RUBRIC" and include_source_context:
            row["learner_contract"] = {
                "prompt": "Write for the visible school situation.",
                "response_mode": "short_text",
                "context": {"source_context": f"Visible learner context for {row['item_id']}."},
            }
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
    consumer["source_graph_sha256"] = runner.legacy.file_sha(fixture["graph_path"])
    for asset in consumer["asset_records"]:
        payload = asset["payload"]
        payload["domain_hint"] = "school classroom lesson teacher student"
        for key in ("context", "situation", "scenario", "source_text", "passage", "dialogue"):
            payload.pop(key, None)
        if isinstance(payload.get("m12_item_id"), str):
            payload["m12_session_bank_sha256"] = bank_hash
    fixture["consumer_path"].write_text(
        json.dumps(consumer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _prepare_hash_bound_source_options_case(
    fixture: dict,
    *,
    include_source_options: bool,
) -> int:
    fixture["current_bank_path"].unlink()
    fixture["current_supply_path"].unlink()

    graph = json.loads(fixture["graph_path"].read_text(encoding="utf-8"))
    graph["a2_lock_contract"]["state"] = "LOCKED_BY_DESIGN"
    fixture["graph_path"].write_text(
        json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    bank = json.loads(fixture["source_bank_path"].read_text(encoding="utf-8"))
    for row in bank["items"]:
        scoring = row.get("private_scoring_contract", {})
        if scoring.get("scoring_mode") == "FEATURE_RUBRIC":
            learner = row.setdefault("learner_contract", {})
            learner["prompt"] = "Write for the visible school situation."
            learner["response_mode"] = "short_text"
            learner["context"] = {"source_context": "A visible fixture context."}

    target = bank["items"][0]
    target_item_id = str(target["item_id"])
    previous_scoring = target.get("private_scoring_contract", {})
    accepted = list(previous_scoring.get("accepted_texts", [])) or ["answer 1"]
    exact_contract = {
        "scoring_mode": "EXACT_OPTION",
        "response_type": "string",
        "accepted_texts": accepted,
        "case_insensitive": True,
        "punctuation_tolerance": True,
        "human_review_fallback": False,
    }
    target["private_scoring_contract"] = deepcopy(exact_contract)
    learner = target.setdefault("learner_contract", {})
    learner["prompt"] = "Choose the visible answer."
    learner["response_mode"] = "select_one"
    learner.pop("context", None)
    if include_source_options:
        learner["options"] = accepted + ["Visible distractor 1"]
    else:
        learner.pop("options", None)

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
    for entry in ledger["entries"]:
        if entry.get("item_id") == target_item_id:
            entry["scoring_mode"] = "EXACT_OPTION"
    ledger["entries_sha256"] = m08.sha256_value(ledger["entries"])
    ledger_path.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    consumer = json.loads(fixture["consumer_path"].read_text(encoding="utf-8"))
    consumer["source_graph_sha256"] = runner.legacy.file_sha(fixture["graph_path"])
    for asset in consumer["asset_records"]:
        payload = asset["payload"]
        payload["domain_hint"] = "school classroom lesson teacher student"
        if payload.get("m12_item_id") == target_item_id:
            payload["private_scoring_contract"] = deepcopy(exact_contract)
            for key in ("options", "choices", "answer_options", "answer_choices"):
                payload.pop(key, None)
        if isinstance(payload.get("m12_item_id"), str):
            payload["m12_session_bank_sha256"] = bank_hash
        asset["content_digest"] = runner.population.digest(payload)
    fixture["consumer_path"].write_text(
        json.dumps(consumer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 1


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
    assert report["stop_reason"] == "R6_DIAGNOSTIC_RESPONSE_AND_CONTROLLED_DECISION_REQUIRED"
    assert report["next_short_step"] == runner.NEXT_SHORT_STEP
    assert report["selected_lineage"]["breadth_cell_count"] == 9
    assert report["selected_lineage"]["item_count"] == 9
    assert report["selected_lineage"]["r6_intake_ready"] is True
    assert report["r6_intake"]["representative_evidence_count"] == 9
    assert report["r6_intake"]["model_invoked"] is False

    lineage_root = fixture["output_root"] / "lineage"
    r6_root = fixture["output_root"] / "r6_intake"
    assert (lineage_root / runner.population.COVERAGE_OUTPUT).is_file()
    assert (lineage_root / runner.population.BANK_OUTPUT).is_file()
    assert (lineage_root / runner.population.SUPPLY_OUTPUT).is_file()
    assert (lineage_root / runner.LINEAGE_PRIVATE_NAME).is_file()
    assert (lineage_root / runner.LINEAGE_SAFE_NAME).is_file()
    assert (r6_root / runner.R6_REQUEST_NAME).is_file()
    assert (r6_root / runner.R6_SAFE_NAME).is_file()


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



def test_runner_backfills_hash_bound_m08_context_without_mutating_canonical_m2(fixture: dict) -> None:
    _prepare_hash_bound_source_context_case(fixture, include_source_context=True)
    original_consumer = fixture["consumer_path"].read_bytes()
    report = runner.run(local_root=fixture["local_root"], output_root=fixture["output_root"])
    assert report["validation_status"] == runner.STATUS, report
    counts = report["discovery_counts"]
    assert counts["compatibility_feature_rubric_exact_join_count"] == 2
    assert counts["compatibility_context_backfill_count"] == 2
    assert counts["compatibility_source_context_missing_count"] == 0
    assert counts["compatibility_context_conflict_count"] == 0
    assert report["reconciliation"]["exact_mapped_attempt_count"] == 9
    assert fixture["consumer_path"].read_bytes() == original_consumer
    assert "Visible learner context" not in json.dumps(report, ensure_ascii=False)


def test_runner_does_not_invent_missing_feature_rubric_context(fixture: dict) -> None:
    _prepare_hash_bound_source_context_case(fixture, include_source_context=False)
    original_consumer = fixture["consumer_path"].read_bytes()
    report = runner.run(local_root=fixture["local_root"], output_root=fixture["output_root"])
    assert report["validation_status"] == runner.BLOCKED
    counts = report["discovery_counts"]
    assert counts["compatibility_feature_rubric_exact_join_count"] == 2
    assert counts["compatibility_context_backfill_count"] == 0
    assert counts["compatibility_source_context_missing_count"] == 2
    assert fixture["consumer_path"].read_bytes() == original_consumer
    assert report["claim_boundaries"]["new_context_created"] is False
    assert report["claim_boundaries"]["canonical_m2_modified"] is False


def test_runner_backfills_hash_bound_m08_options_without_mutating_canonical_m2(fixture: dict) -> None:
    exact_count = _prepare_hash_bound_source_options_case(
        fixture,
        include_source_options=True,
    )
    original_consumer = fixture["consumer_path"].read_bytes()
    report = runner.run(local_root=fixture["local_root"], output_root=fixture["output_root"])
    assert report["validation_status"] == runner.STATUS, report
    counts = report["discovery_counts"]
    assert counts["compatibility_exact_option_exact_join_count"] == exact_count
    assert counts["compatibility_option_backfill_count"] == exact_count
    assert counts["compatibility_source_options_missing_count"] == 0
    assert counts["compatibility_options_conflict_count"] == 0
    assert counts["compatibility_option_scoring_mismatch_count"] == 0
    assert report["reconciliation"]["exact_mapped_attempt_count"] == 9
    assert fixture["consumer_path"].read_bytes() == original_consumer
    assert "Visible distractor" not in json.dumps(report, ensure_ascii=False)


def test_runner_does_not_invent_missing_exact_option_choices(fixture: dict) -> None:
    exact_count = _prepare_hash_bound_source_options_case(
        fixture,
        include_source_options=False,
    )
    original_consumer = fixture["consumer_path"].read_bytes()
    report = runner.run(local_root=fixture["local_root"], output_root=fixture["output_root"])
    assert report["validation_status"] == runner.BLOCKED
    counts = report["discovery_counts"]
    assert counts["compatibility_exact_option_exact_join_count"] == exact_count
    assert counts["compatibility_option_backfill_count"] == 0
    assert counts["compatibility_source_options_missing_count"] == exact_count
    assert fixture["consumer_path"].read_bytes() == original_consumer
    assert report["claim_boundaries"]["new_options_created"] is False
    assert report["claim_boundaries"]["canonical_m2_modified"] is False


def _write_second_current_identity(
    fixture: dict,
    *,
    semantic_mapping_change: bool,
) -> None:
    bank = json.loads(fixture["current_bank_path"].read_text(encoding="utf-8"))
    supply = json.loads(fixture["current_supply_path"].read_text(encoding="utf-8"))
    bank["selection_contract"]["fixture_variant"] = "SECOND_ARTIFACT_IDENTITY"
    supply["fixture_variant"] = "SECOND_ARTIFACT_IDENTITY"

    if semantic_mapping_change:
        target = bank["items"][0]
        original_item_id = str(target["item_id"])
        replacement_item_id = original_item_id + ":SEMANTIC_VARIANT"
        target["item_id"] = replacement_item_id
        replaced = 0
        for cell in supply["cell_supply"]:
            approved = cell.get("approved_item_ids", [])
            if original_item_id in approved:
                cell["approved_item_ids"] = [
                    replacement_item_id if item_id == original_item_id else item_id
                    for item_id in approved
                ]
                replaced += 1
        assert replaced == 1

    bank_core = {key: value for key, value in bank.items() if key != "bank_sha256"}
    bank["bank_sha256"] = r4.digest(bank_core)
    supply_core = {key: value for key, value in supply.items() if key != "report_sha256"}
    supply["report_sha256"] = r4.digest(supply_core)
    second = fixture["local_root"] / (
        "second_semantic_identity" if semantic_mapping_change
        else "second_equivalent_artifact_identity"
    )
    second.mkdir(parents=True)
    (second / "a1fs_v1_r4_approved_practice_bank.private.json").write_text(
        json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (second / "a1fs_v1_r4_supply_report.safe.json").write_text(
        json.dumps(supply, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def test_runner_collapses_equivalent_current_artifact_variants(fixture: dict) -> None:
    _write_second_current_identity(fixture, semantic_mapping_change=False)
    report = runner.run(local_root=fixture["local_root"], output_root=fixture["output_root"])
    assert report["validation_status"] == runner.STATUS, report
    diagnostics = report["reconciliation_diagnostics"]
    assert diagnostics["ready_combination_count"] == 4
    assert diagnostics["ready_artifact_identity_count"] == 4
    assert diagnostics["ready_semantic_identity_count"] == 1
    assert diagnostics["ready_equivalent_variant_count"] == 3


def test_runner_collapses_equivalent_registry_ledger_copies(fixture: dict) -> None:
    source_resolved = fixture["resolved_root"]
    registry = json.loads(
        (source_resolved / "cumulative_attempt_registry.private.json").read_text(
            encoding="utf-8"
        )
    )
    ledger = json.loads(
        (source_resolved / "cumulative_progress_ledger.private.json").read_text(
            encoding="utf-8"
        )
    )
    registry["copy_metadata"] = "NON_SEMANTIC_REGISTRY_COPY"
    ledger["attempt_registry_sha256"] = m08.sha256_value(registry)
    ledger["copy_metadata"] = "NON_SEMANTIC_LEDGER_COPY"
    duplicate = fixture["local_root"] / "duplicate_evidence_copy"
    duplicate.mkdir(parents=True)
    (duplicate / "cumulative_attempt_registry.private.json").write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (duplicate / "cumulative_progress_ledger.private.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    report = runner.run(local_root=fixture["local_root"], output_root=fixture["output_root"])
    assert report["validation_status"] == runner.STATUS, report
    assert report["discovery_counts"]["legacy_semantic_chain_count"] == 2
    diagnostics = report["reconciliation_diagnostics"]
    assert diagnostics["ready_artifact_identity_count"] == 2
    assert diagnostics["ready_semantic_identity_count"] == 1


def test_runner_blocks_semantically_distinct_exact_mapping(fixture: dict) -> None:
    _write_second_current_identity(fixture, semantic_mapping_change=True)
    report = runner.run(local_root=fixture["local_root"], output_root=fixture["output_root"])
    assert report["validation_status"] == runner.BLOCKED
    diagnostics = report["reconciliation_diagnostics"]
    assert diagnostics["ready_artifact_identity_count"] == 2
    assert diagnostics["ready_semantic_identity_count"] == 2
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
    assert diagnostics["ready_combination_count"] == 0
    assert diagnostics["ready_artifact_identity_count"] == 0
    assert diagnostics["ready_semantic_identity_count"] == 0
    assert diagnostics["ready_equivalent_variant_count"] == 0
    assert diagnostics["max_pass_count"] == 3
    assert diagnostics["max_failure_count"] == 1
    assert not any(secret in json.dumps(diagnostics) for secret in secret_ids)
