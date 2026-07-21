from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tests.ulga.test_a1fs_v1_r3r4_authority_reviewed_production_population import _fixture
from ulga.builders import build_a1fs_v1_r3r4_authority_reviewed_production_population as population
from ulga.builders import build_a1fs_v1_r4_authority_reference_lineage_repair_and_readmission as repair
from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4
from ulga.validators import validate_a1fs_v1_r4_authority_reference_lineage_repair_and_readmission as validator


def _write(path: Path, value) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _rebind_registry(registry: dict) -> None:
    registry["candidates_sha256"] = r4.digest(registry["candidates"])
    registry["semantic_sha256"] = r4.candidate_registry_semantic_digest(registry["candidates"])


def _rebind_candidate(candidate: dict) -> None:
    candidate["candidate_sha256"] = r4.candidate_digest(candidate)
    candidate["authority_review"]["candidate_sha256"] = candidate["candidate_sha256"]


def _prepared(tmp_path: Path, monkeypatch) -> dict:
    monkeypatch.setattr(population, "REPO_ROOT", tmp_path)
    ontology, graph, consumer = _fixture(tmp_path)
    source_root = tmp_path / ".local" / "population"
    population.materialize(
        ontology_path=ontology,
        graph_path=graph,
        consumer_path=consumer,
        output_root=source_root,
        reviewed_at="2026-07-21T04:00:00Z",
    )
    candidates_path = source_root / population.CANDIDATE_OUTPUT
    registry = json.loads(candidates_path.read_text(encoding="utf-8"))
    assert len(registry["candidates"]) == 2

    project = registry["candidates"][1]
    project["provenance"] = "PROJECT_AUTHORED_CANDIDATE"
    project["authority_refs"] = [
        (f"{repair.M2_CONTENT_PREFIX}{'f' * 64}" if value.startswith(repair.M2_CONTENT_PREFIX) else value)
        for value in project["authority_refs"]
    ]
    _rebind_candidate(project)
    _rebind_registry(registry)
    _write(candidates_path, registry)

    return {
        "ontology": ontology,
        "graph": graph,
        "consumer": consumer,
        "source_root": source_root,
        "candidates": candidates_path,
        "coverage": source_root / population.COVERAGE_OUTPUT,
        "policies": source_root / population.POLICY_OUTPUT,
        "registry": registry,
    }


def _build(data: dict, tmp_path: Path):
    registry, bank, supply, report = repair.build_repair(
        ontology_path=data["ontology"],
        coverage_path=data["coverage"],
        candidates_path=data["candidates"],
        policies_path=data["policies"],
        graph_path=data["graph"],
        consumer_path=data["consumer"],
        reviewer_id="operator-approved-lineage-repair",
        reviewed_at="2026-07-21T05:00:00Z",
        expected_item_count=2,
        expected_project_resolution_count=1,
    )
    output = tmp_path / ".local" / "repair"
    repair.write_json_atomic(output / repair.CANDIDATE_OUTPUT, registry, private=True)
    repair.write_json_atomic(output / repair.BANK_OUTPUT, bank, private=True)
    repair.write_json_atomic(output / repair.SUPPLY_OUTPUT, supply, private=False)
    repair.write_json_atomic(output / repair.REPORT_OUTPUT, report, private=False)
    return output, registry, bank, supply, report


def test_repairs_physical_graph_consumer_refs_and_readmits_all_candidates(tmp_path: Path, monkeypatch) -> None:
    data = _prepared(tmp_path, monkeypatch)
    before = copy.deepcopy(data["registry"])
    output, registry, bank, supply, report = _build(data, tmp_path)

    graph_sha = repair.file_digest(data["graph"])
    consumer_sha = repair.file_digest(data["consumer"])
    assert bank["item_count"] == 2
    assert supply["counts"]["admission_status_counts"] == {"APPROVED": 2}
    assert report["validation_status"] == repair.PASS_STATUS
    assert report["counts"]["authority_ref_repaired_count"] == 2
    assert report["counts"]["project_authored_source_resolved_count"] == 1

    before_by_id = {row["item_id"]: row for row in before["candidates"]}
    for row in registry["candidates"]:
        original = before_by_id[row["item_id"]]
        assert row["learner_contract"] == original["learner_contract"]
        assert row["private_scoring_contract"] == original["private_scoring_contract"]
        assert row["candidate_sha256"] != original["candidate_sha256"]
        assert f"{repair.M1_PREFIX}{graph_sha}" in row["authority_refs"]
        assert f"{repair.M2_PREFIX}{consumer_sha}" in row["authority_refs"]
        assert row["authority_review"]["candidate_sha256"] == row["candidate_sha256"]
        assert row["authority_review"]["lineage_repair"]["operator_approved"] is True

    project = next(row for row in registry["candidates"] if row["provenance"] == "PROJECT_AUTHORED_CANDIDATE")
    assert any(value.startswith(repair.PROJECT_CONTENT_PREFIX) for value in project["authority_refs"])
    assert any(value.startswith(repair.PROJECT_PREVIOUS_PREFIX) for value in project["authority_refs"])
    assert not any(value.startswith(repair.M2_CONTENT_PREFIX) for value in project["authority_refs"])
    assert any(value.startswith(repair.PROJECT_SOURCE_PREFIX) for value in project["source_refs"])
    assert not any(value.startswith(("M2_ASSET:", "M2_LESSON:")) for value in project["source_refs"])

    result = validator.validate(
        ontology_path=data["ontology"],
        coverage_path=data["coverage"],
        source_candidates_path=data["candidates"],
        policies_path=data["policies"],
        graph_path=data["graph"],
        consumer_path=data["consumer"],
        output_root=output,
        expected_item_count=2,
        expected_project_resolution_count=1,
    )
    assert result["error_count"] == 0, result["errors"]


def test_existing_authority_content_digest_mismatch_fails_closed(tmp_path: Path, monkeypatch) -> None:
    data = _prepared(tmp_path, monkeypatch)
    registry = json.loads(data["candidates"].read_text(encoding="utf-8"))
    existing = next(row for row in registry["candidates"] if row["provenance"] == "EXISTING_AUTHORITY_REVIEWED")
    existing["authority_refs"] = [
        (f"{repair.M2_CONTENT_PREFIX}{'e' * 64}" if value.startswith(repair.M2_CONTENT_PREFIX) else value)
        for value in existing["authority_refs"]
    ]
    _rebind_candidate(existing)
    _rebind_registry(registry)
    _write(data["candidates"], registry)

    with pytest.raises(repair.AuthorityLineageRepairError, match="existing_authority_m2_content_mismatch"):
        _build(data, tmp_path)


def test_unbound_previous_authority_review_fails_closed(tmp_path: Path, monkeypatch) -> None:
    data = _prepared(tmp_path, monkeypatch)
    registry = json.loads(data["candidates"].read_text(encoding="utf-8"))
    registry["candidates"][0]["authority_review"]["candidate_sha256"] = "0" * 64
    _rebind_registry(registry)
    _write(data["candidates"], registry)

    with pytest.raises(repair.AuthorityLineageRepairError, match="previous_authority_review_not_hash_bound"):
        _build(data, tmp_path)


def test_a2_candidate_injection_fails_closed(tmp_path: Path, monkeypatch) -> None:
    data = _prepared(tmp_path, monkeypatch)
    registry = json.loads(data["candidates"].read_text(encoding="utf-8"))
    registry["candidates"][0]["level"] = "A2"
    _rebind_candidate(registry["candidates"][0])
    _rebind_registry(registry)
    _write(data["candidates"], registry)

    with pytest.raises(repair.AuthorityLineageRepairError, match="a2_or_out_of_scope_candidate"):
        _build(data, tmp_path)


def test_repair_is_idempotent_for_canonical_registry_bank_and_supply(tmp_path: Path, monkeypatch) -> None:
    data = _prepared(tmp_path, monkeypatch)
    output, first_registry, first_bank, first_supply, _ = _build(data, tmp_path)
    repaired_path = output / repair.CANDIDATE_OUTPUT

    second_registry, second_bank, second_supply, _ = repair.build_repair(
        ontology_path=data["ontology"],
        coverage_path=data["coverage"],
        candidates_path=repaired_path,
        policies_path=data["policies"],
        graph_path=data["graph"],
        consumer_path=data["consumer"],
        reviewer_id="operator-approved-lineage-repair",
        reviewed_at="2026-07-21T05:00:00Z",
        expected_item_count=2,
        expected_project_resolution_count=1,
    )
    assert second_registry == first_registry
    assert second_bank == first_bank
    assert second_supply == first_supply
