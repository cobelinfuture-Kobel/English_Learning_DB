import json
from pathlib import Path

from ulga.builders.build_grammar_query_index import (
    build_query_index_and_contract,
    build_skill_indexes,
    build_stage_indexes,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_json(relative_path):
    return json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))


def build_from_sources():
    overlay = load_json("ulga/graph/a1_egp_canonical_mappings.json")
    batches = [
        (source["path"], load_json(source["path"]))
        for source in overlay["source_import_batches"]
    ]
    return build_query_index_and_contract(
        load_json("ulga/graph/cefr_egp_alignment_table.json"),
        load_json("ulga/graph/grammar_coverage_matrix.json"),
        load_json("ulga/graph/cross_skill_grammar_gate_matrix.json"),
        load_json("ulga/reports/grammar_uncovered_egp_rules.json"),
        overlay,
        batches,
    )


def test_checked_in_consumer_artifacts_match_builder_output():
    query_index, contract, report = build_from_sources()
    assert query_index == load_json("ulga/graph/grammar_query_index.json")
    assert contract == load_json("ulga/contracts/grammar_lookup_contract.json")
    assert report == load_json("ulga/reports/grammar_lookup_contract_validation_report.json")


def test_a1_canonical_overlay_is_queryable_without_uncovered_rows():
    query_index, contract, report = build_from_sources()
    canonical = query_index["canonical_a1"]

    assert canonical["canonical_status"] == "ACTIVE"
    assert canonical["canonical_mapping_unit_count"] == 24
    assert canonical["canonical_unique_egp_row_count"] == 109
    assert canonical["coverage_percent"] == 100.0
    assert len(canonical["by_egp_row_id"]) == 109
    assert query_index["uncovered_by_egp_level"]["A1"] == []
    assert report["canonical_a1_uncovered_egp_row_count"] == 0
    assert contract["capabilities"]["lookup_canonical_a1_mappings"] is True

    for grammar_id in canonical["by_grammar_id"]:
        assert grammar_id in query_index["by_grammar_id"]
        assert query_index["by_grammar_id"][grammar_id]["effective_a1_mapping_status"] == (
            "VERIFIED_CANONICAL_MAPPING"
        )
    for row_id, grammar_ids in canonical["by_egp_row_id"].items():
        assert set(grammar_ids).issubset(query_index["by_egp_row_id"][row_id])


def test_non_a1_stage_and_skill_indexes_are_not_reclassified():
    coverage = load_json("ulga/graph/grammar_coverage_matrix.json")
    cross_skill = load_json("ulga/graph/cross_skill_grammar_gate_matrix.json")
    query_index, _, _ = build_from_sources()

    expected_stage = build_stage_indexes(coverage["records"])
    expected_skill = build_skill_indexes(cross_skill["records"])
    for key, expected in {**expected_stage, **expected_skill}.items():
        assert query_index[key] == expected


def test_base_alignment_status_is_preserved_for_existing_nodes():
    alignment = load_json("ulga/graph/cefr_egp_alignment_table.json")
    query_index, _, _ = build_from_sources()

    for record in alignment["records"]:
        grammar_id = record["grammar_id"]
        assert query_index["by_grammar_id"][grammar_id]["alignment_status"] == record["alignment_status"]

