from __future__ import annotations

import importlib.util
import json
import shutil
import uuid
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import build_a1fs_v1_r3r4_authority_reviewed_production_population as production
from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4
from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5
from ulga.builders import build_a1fs_v1_r8_legacy_real_evidence_deterministic_production_reconciliation as reconciliation
from ulga.builders import build_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge as legacy
from ulga.builders import build_e4s_a1v1_m12g_learner_contract_assessment_validity_fullfix as assessment
from ulga.validators import validate_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5_validator
from ulga.validators import validate_a1fs_v1_r8_legacy_real_evidence_deterministic_production_reconciliation as validator

REPO_ROOT = Path(__file__).resolve().parents[2]


def write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def legacy_fixture_builder():
    path = REPO_ROOT / "tests/ulga/test_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge.py"
    spec = importlib.util.spec_from_file_location("m12f_fixture_source", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_fixture


def current_r4_fixture(data: dict) -> tuple[Path, Path]:
    consumer = json.loads(data["consumer_path"].read_text(encoding="utf-8"))
    for asset in consumer["asset_records"]:
        scoring = asset["payload"]["private_scoring_contract"]
        if scoring["scoring_mode"] == "FEATURE_RUBRIC":
            asset["payload"]["context"] = {"source_context": "A visible fixture context."}
    write(data["consumer_path"], consumer)
    source = legacy._load_sources(
        source_bank_path=data["source_bank_path"],
        resolved_root=data["resolved_root"],
        m12e1_root=data["m12e1_root"],
        consumer_path=data["consumer_path"],
        graph_path=data["graph_path"],
    )
    mapping = legacy._mapping(source)
    assert mapping["ready"] is True
    assets = {row["asset_key"]: row for row in consumer["asset_records"]}
    items = []
    cells = []
    for index, mapped in enumerate(mapping["mapped"], start=1):
        assert len(mapped["required_node_ids"]) == 1
        node_id = mapped["required_node_ids"][0]
        asset = assets[mapped["asset_key"]]
        derived = m6.derive_contract(asset)
        learner, scoring, task_type, support, initiative, variation, transfer, _ = production._task_projection(asset, derived)
        learner, scoring = assessment.validate_learner_contract(
            item_id=asset["asset_key"],
            task_type=task_type.casefold(),
            learner=learner,
            scoring=scoring,
        )
        item_id = f"R4_CURRENT_ITEM_{index:02d}"
        cell_id = f"R4_CURRENT_CELL_{index:02d}"
        item = {
            "item_id": item_id,
            "breadth_cell_id": cell_id,
            "capability_id": f"CAP_CURRENT_{index:02d}",
            "life_task_id": f"LIFE_CURRENT_{index:02d}",
            "domain": "PERSONAL_SOCIAL",
            "level": "A1",
            "skill": asset["skill"],
            "purpose": "CORE_PRACTICE",
            "task_type": task_type,
            "support_level": support,
            "initiative_level": initiative,
            "interaction_variation": variation,
            "transfer_distance": transfer,
            "template_family": f"TEMPLATE_{asset['skill']}_{task_type}_FIXTURE",
            "stimulus_fingerprint": assessment._contract_fingerprint(learner),
            "media_payload_state": "NOT_REQUIRED",
            "source_refs": [f"M2_ASSET:{asset['asset_key']}", f"M1_NODE:{node_id}"],
            "authority_refs": ["FIXTURE_AUTHORITY"],
            "provenance": "EXISTING_AUTHORITY_REVIEWED",
            "learner_contract": learner,
            "private_scoring_contract": scoring,
            "validator_status": "PASS",
            "authority_review": {
                "status": "APPROVED",
                "reviewer_id": "fixture",
                "criteria": {
                    "a1_a1plus_level_fit": True,
                    "breadth_cell_fit": True,
                    "learner_stimulus_complete": True,
                    "answer_or_rubric_valid": True,
                    "semantic_unambiguous": True,
                    "source_trace_complete": True,
                },
                "candidate_sha256": "0" * 64,
            },
            "candidate_sha256": "0" * 64,
            "admission": {
                "status": "APPROVED",
                "learner_fingerprint": assessment._contract_fingerprint(learner),
                "candidate_sha256": "0" * 64,
            },
        }
        items.append(item)
        cells.append({
            "breadth_cell_id": cell_id,
            "capability_id": item["capability_id"],
            "life_task_id": item["life_task_id"],
            "domain": item["domain"],
            "supply_status": "READY_FOR_LOCAL_SELECTION",
            "capacity_policy_present": True,
            "approved_item_count": 1,
            "approved_item_ids": [item_id],
            "skill_projection": {"required": [asset["skill"]], "approved": [asset["skill"]], "missing": []},
            "purpose_capacity": {},
            "decision_counts": {"APPROVED": 1},
            "max_recent_reuse": 0,
        })
    bindings = {
        "ontology_sha256": "1" * 64,
        "coverage_sha256": "2" * 64,
        "candidate_registry_sha256": "3" * 64,
        "capacity_policy_registry_sha256": "4" * 64,
    }
    bank_core = {
        "task_id": r4.TASK_ID,
        "schema_version": r4.BANK_SCHEMA_VERSION,
        "validation_status": r4.STATUS,
        "private_local_only": True,
        "source_bindings": bindings,
        "selection_contract": {
            "local_free_generation_enabled": False,
            "gpt_direct_item_admission_enabled": False,
            "qwen_direct_item_admission_enabled": False,
            "formal_item_requires_admission_approved": True,
            "recent_reuse_policy_source": "CELL_CAPACITY_POLICY",
            "authority_review_timestamp_externalized": True,
        },
        "item_count": len(items),
        "items": items,
    }
    bank = {**bank_core, "bank_sha256": r4.digest(bank_core)}
    supply_core = {
        "task_id": r4.TASK_ID,
        "schema_version": r4.SCHEMA_VERSION,
        "validation_status": r4.STATUS,
        "source_bindings": bindings,
        "counts": {
            "candidate_count": len(items),
            "approved_item_count": len(items),
            "rejected_or_pending_count": 0,
            "breadth_cell_count": len(cells),
            "capacity_policy_count": len(cells),
            "supply_status_counts": {"READY_FOR_LOCAL_SELECTION": len(cells)},
            "admission_status_counts": {"APPROVED": len(items)},
        },
        "cell_supply": cells,
        "admission_decisions": [],
        "claim_boundaries": {
            "canonical_authority_modified": False,
            "m1_graph_modified": False,
            "r3_denominator_modified": False,
            "local_free_generation_enabled": False,
            "gpt_direct_admission_enabled": False,
            "qwen_required": False,
            "a2_content_admitted": False,
            "audio_files_required": False,
            "mastery_claimed": False,
        },
        "next_short_step": r4.NEXT_SHORT_STEP,
    }
    supply = {**supply_core, "report_sha256": r4.digest(supply_core)}
    return write(data["root"] / "current_bank.private.json", bank), write(data["root"] / "current_supply.safe.json", supply)


@pytest.fixture()
def fixture(monkeypatch) -> dict:
    root = REPO_ROOT / ".local" / f"r8-reconciliation-test-{uuid.uuid4().hex}"
    data = legacy_fixture_builder()(root / "legacy")
    bank_path, supply_path = current_r4_fixture(data)
    monkeypatch.setattr(reconciliation, "REPO_ROOT", REPO_ROOT)
    yield {**data, "current_bank_path": bank_path, "current_supply_path": supply_path, "reconciliation_root": root / "output"}
    shutil.rmtree(root, ignore_errors=True)


def kwargs(data: dict) -> dict:
    return {
        "source_bank_path": data["source_bank_path"],
        "resolved_root": data["resolved_root"],
        "m12e1_root": data["m12e1_root"],
        "consumer_path": data["consumer_path"],
        "graph_path": data["graph_path"],
        "current_bank_path": data["current_bank_path"],
        "current_supply_path": data["current_supply_path"],
        "output_root": data["reconciliation_root"],
    }


def test_projects_nine_resolved_attempts_to_current_r5_export(fixture: dict) -> None:
    report = reconciliation.reconcile(**kwargs(fixture), mode="project")["report"]
    assert report["validation_status"] == reconciliation.PROJECTED_STATUS
    assert report["counts"] == {
        "legacy_real_attempt_count": 9,
        "exact_mapped_attempt_count": 9,
        "mapped_breadth_cell_count": 9,
        "pass_count": 7,
        "failure_count": 2,
    }
    assert report["stop_reason"] == "REAL_LEARNER_ATTESTATION_REQUIRED"
    export = r5_validator.validate_exports(
        fixture["reconciliation_root"] / reconciliation.PACKAGE_NAME,
        fixture["reconciliation_root"] / reconciliation.SAFE_NAME,
        fixture["reconciliation_root"] / reconciliation.JSONL_NAME,
    )
    assert export["error_count"] == 0, export["errors"]
    checked = validator.validate(**kwargs(fixture), mode="project")
    assert checked["error_count"] == 0, checked["errors"]
    package = json.loads((fixture["reconciliation_root"] / reconciliation.PACKAGE_NAME).read_text(encoding="utf-8"))
    assert package["attempt_count"] == 9
    assert package["resolved_valid_attempt_count"] == 9
    assert all(row["compatibility_projection"]["mapping_basis"] == "EXACT_M2_ASSET_M1_NODE_AND_NORMALIZED_CONTRACT" for row in package["entries"])
    assert all(row["telemetry_status"] == "NOT_CAPTURED_LEGACY_ZERO_FILLED" for row in package["entries"])


def test_contract_drift_fails_closed_without_exports(fixture: dict) -> None:
    bank = json.loads(fixture["current_bank_path"].read_text(encoding="utf-8"))
    bank["items"][0]["learner_contract"]["prompt"] = "Changed prompt"
    core = {key: value for key, value in bank.items() if key != "bank_sha256"}
    bank["bank_sha256"] = r4.digest(core)
    write(fixture["current_bank_path"], bank)
    report = reconciliation.reconcile(**kwargs(fixture), mode="project")["report"]
    assert report["validation_status"] == reconciliation.BLOCKED_STATUS
    assert report["counts"]["exact_mapped_attempt_count"] == 8
    assert report["issues"]["current_contract_drift_ids"]
    assert not (fixture["reconciliation_root"] / reconciliation.PACKAGE_NAME).exists()


def test_projection_is_deterministic(fixture: dict) -> None:
    first = reconciliation.reconcile(**kwargs(fixture), mode="project")["report"]
    first_package = (fixture["reconciliation_root"] / reconciliation.PACKAGE_NAME).read_bytes()
    shutil.rmtree(fixture["reconciliation_root"])
    second = reconciliation.reconcile(**kwargs(fixture), mode="project")["report"]
    assert first == second
    assert first_package == (fixture["reconciliation_root"] / reconciliation.PACKAGE_NAME).read_bytes()
