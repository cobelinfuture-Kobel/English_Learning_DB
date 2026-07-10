import json
from pathlib import Path

from ulga.builders.build_a1_canonical_rule_validator_index import (
    CANONICAL_OVERLAY_PATH,
    QUERY_INDEX_PATH,
    build_index_and_contract,
    canonical_rule_sources,
    load_json,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def read(relative_path):
    return json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))


def build_from_sources():
    return build_index_and_contract(
        load_json(CANONICAL_OVERLAY_PATH),
        load_json(QUERY_INDEX_PATH),
        canonical_rule_sources(),
    )


def test_checked_in_artifacts_are_deterministic():
    index, contract, report = build_from_sources()
    assert index == read("ulga/graph/a1_canonical_rule_validator_index.json")
    assert contract == read("ulga/contracts/a1_canonical_rule_validator_contract.json")
    assert report == read("ulga/reports/a1_canonical_rule_validator_validation.json")


def test_all_canonical_units_have_primitive_and_schema_coverage():
    index, _, _ = build_from_sources()
    summary = index["coverage_summary"]
    assert summary["canonical_mapping_unit_count"] == 24
    assert summary["canonical_mapping_unique_egp_rows"] == 109
    assert summary["rule_primitive_unit_count"] == 24
    assert summary["schema_validated_unit_count"] == 24
    assert summary["rule_primitive_unit_coverage_percent"] == 100.0
    assert summary["schema_validated_unit_coverage_percent"] == 100.0

    for node in index["by_grammar_id"].values():
        assert node["rule_primitive_count"] > 0
        assert node["schema_validation_status"] == "PASS"
        assert node["canonical_mapping_status"] == "VERIFIED_CANONICAL_MAPPING"


def test_mapping_coverage_is_not_misreported_as_runtime_coverage():
    index, contract, report = build_from_sources()
    summary = index["coverage_summary"]
    assert summary["canonical_mapping_coverage_percent"] == 100.0
    assert summary["executable_sentence_validator_unit_count"] == 24
    assert summary["executable_sentence_validator_unit_coverage_percent"] == 100.0
    assert summary["runtime_validator_unit_count"] == 0
    assert summary["runtime_validator_unit_coverage_percent"] == 0.0
    assert summary["dispatcher_registered_unit_count"] == 24
    assert summary["dispatcher_registered_unit_coverage_percent"] == 100.0

    executable = [
        grammar_id
        for grammar_id, node in index["by_grammar_id"].items()
        if node["executable_sentence_validator"]
    ]
    assert set(executable) == set(index["by_grammar_id"])
    assert index["claim_boundaries"]["executable_sentence_validation_complete"] is True
    assert index["claim_boundaries"]["production_runtime_validation_complete"] is False
    assert index["claim_boundaries"]["offline_dispatcher_complete"] is True
    assert contract["capabilities"]["distinguish_mapping_from_runtime_coverage"] is True
    assert report["validation_status"] == "PASS"


def test_rule_authority_remains_candidate_and_read_only():
    index, contract, _ = build_from_sources()
    assert index["claim_boundaries"]["no_learner_state_write"] is True
    assert index["claim_boundaries"]["no_practicebank_generation"] is True
    assert index["claim_boundaries"]["no_external_nlp_dependency"] is True
    assert contract["capabilities"]["no_learner_state_write"] is True
    assert all(
        node["rule_primitive_authority_status"] == "CANDIDATE_NOT_PROMOTED"
        for node in index["by_grammar_id"].values()
    )
