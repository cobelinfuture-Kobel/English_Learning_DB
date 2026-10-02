from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "ulga" / "contracts" / "a1fs_v1_u06_q01_canonical_target_gap_projection.json"
SEQUENCE = ROOT / "product" / "a1fs_v1_2_1" / "runtime" / "sequence.json"
QUERY_INDEX = ROOT / "ulga" / "graph" / "grammar_query_index.json"
MAPPING_BATCH = ROOT / "ulga" / "mappings" / "a1_verified_mapping_import_batch_01.json"
GRAMMAR_PROFILE = ROOT / "grammar_profile" / "json" / "grammar_profile.json"
LEARNING_AUTHORITY = ROOT / "ulga" / "contracts" / "a1_grammar_learning_content_authority.json"
CAN_RULES = ROOT / "ulga" / "rules" / "a1_can_statement_rule_primitives.json"
CAN_VALIDATION = ROOT / "ulga" / "reports" / "a1_can_statement_rule_primitive_validation.json"
BUNDLES = ROOT / "product" / "a1fs_v1_2_1" / "runtime" / "bundles.json"
Q00 = ROOT / "ulga" / "contracts" / "a1fs_v1_u06_q00_unit05_successor_baseline.json"


DIRECT_ROWS = {
    "1741163710388x206193011712334940",
    "1741163710388x882361395502946800",
}
DEFERRED_CAN_ROWS = {
    "1741163710388x273734335473510240",
    "1741163710388x482560605581935800",
    "1741163710388x540901022788007400",
    "1741163710391x459074403345042000",
    "1741163710391x534949859885590850",
}
QUARANTINED_ROWS = {
    "1741163711296x326455472693880200",
    "1741163711296x692481066424056800",
    "1741163711300x363892315600628400",
    "1741163711300x444537304178034940",
    "1741163711300x569087712695511000",
}
EXPECTED_ROWS = DIRECT_ROWS | DEFERRED_CAN_ROWS | QUARANTINED_ROWS


def _collect_egp_rows(node):
    rows = {}
    if isinstance(node, dict):
        if node.get("id") in EXPECTED_ROWS:
            rows[node["id"]] = node
        for value in node.values():
            rows.update(_collect_egp_rows(value))
    elif isinstance(node, list):
        for value in node:
            rows.update(_collect_egp_rows(value))
    return rows


def test_u06_q01_canonical_target_and_gap_projection() -> None:
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    sequence = json.loads(SEQUENCE.read_text(encoding="utf-8"))
    query = json.loads(QUERY_INDEX.read_text(encoding="utf-8"))
    mapping = json.loads(MAPPING_BATCH.read_text(encoding="utf-8"))
    grammar_profile = json.loads(GRAMMAR_PROFILE.read_text(encoding="utf-8"))
    learning_authority = json.loads(LEARNING_AUTHORITY.read_text(encoding="utf-8"))
    can_rules = json.loads(CAN_RULES.read_text(encoding="utf-8"))
    can_validation = json.loads(CAN_VALIDATION.read_text(encoding="utf-8"))
    bundles = json.loads(BUNDLES.read_text(encoding="utf-8"))
    q00 = json.loads(Q00.read_text(encoding="utf-8"))

    assert data["status"] == "PASS_A1FS_V1_U06Q01_UNIT06_CANONICAL_TARGET_AND_GAP_PROJECTION"
    assert data["unit_number"] == 6
    assert data["unit_id"] == "GRAMMAR_CAN_STATEMENT"

    assert sequence["GRAMMAR_BE_VERB_BASIC"] == 5
    assert sequence["GRAMMAR_CAN_STATEMENT"] == 6
    assert sequence["GRAMMAR_DEMONSTRATIVES_CONTRAST"] == 7
    assert sequence["GRAMMAR_CAN_NEGATIVE_A1"] == 14
    assert sequence["GRAMMAR_WILL_FUTURE_A1"] == 21

    canonical = query["by_grammar_id"]["GRAMMAR_CAN_STATEMENT"]["canonical_a1_mapping"]
    assert canonical["mapping_reference_status"] == "VERIFIED_CANONICAL_MAPPING"
    assert set(canonical["egp_row_ids"]) == EXPECTED_ROWS

    can_unit = next(
        unit for unit in mapping["mapping_import_units"]
        if unit["grammar_id"] == "GRAMMAR_CAN_STATEMENT"
    )
    assert can_unit["mapping_status"] == "IMPORT_READY"
    assert set(can_unit["egp_row_ids"]) == EXPECTED_ROWS

    trace = data["canonical_traceability"]
    assert trace["canonical_traceability_row_count"] == 12
    assert set(trace["canonical_egp_row_ids"]) == EXPECTED_ROWS

    rows = _collect_egp_rows(grammar_profile)
    assert set(rows) == EXPECTED_ROWS
    assert rows["1741163710388x206193011712334940"]["sub_category"] == "can"
    assert rows["1741163710388x206193011712334940"]["guideword"] == "FORM: AFFIRMATIVE"
    assert rows["1741163710388x882361395502946800"]["sub_category"] == "can"
    assert rows["1741163710388x882361395502946800"]["guideword"] == "USE: ABILITY"

    for row_id in DEFERRED_CAN_ROWS:
        assert rows[row_id]["sub_category"] == "can"
    assert rows["1741163710388x273734335473510240"]["guideword"] == "FORM: QUESTION"
    assert rows["1741163710388x482560605581935800"]["guideword"] == "FORM: NEGATIVE"

    for row_id in QUARANTINED_ROWS:
        assert rows[row_id]["sub_category"] in {"will", "would"}

    activation = data["teaching_activation"]
    assert activation["target_label"] == "can ability affirmative statements"
    assert activation["direct_teaching_target_row_count"] == 2
    assert {row["egp_row_id"] for row in activation["direct_teaching_target_rows"]} == DIRECT_ROWS
    assert activation["deferred_can_domain_boundary_row_count"] == 5
    assert {row["egp_row_id"] for row in activation["deferred_can_domain_boundary_rows"]} == DEFERRED_CAN_ROWS
    assert activation["quarantined_non_can_modal_row_count"] == 5
    assert {row["egp_row_id"] for row in activation["quarantined_non_can_modal_rows"]} == QUARANTINED_ROWS

    assert learning_authority["content_lifecycle"]["mapping_coverage_does_not_imply_teaching_readiness"] is True
    assert learning_authority["content_lifecycle"]["offline_validator_pass_does_not_imply_pedagogical_accuracy"] is True

    assert len(can_rules["rule_primitives"]) == 3
    assert can_rules["node"]["en_label"] == "can ability affirmative statements"
    assert can_rules["node"]["candidate_only"] is True
    assert can_validation["validation_summary"] == {
        "total_cases": 12,
        "pass_count": 12,
        "fail_count": 0,
        "status": "PASS",
    }

    bundle_keys = [key for key in bundles if "GRAMMAR_CAN_STATEMENT" in key]
    assert sorted(bundle_keys) == sorted([
        "A1FS_ONLINE_V1:GRAMMAR_CAN_STATEMENT:READING",
        "A1FS_ONLINE_V1:GRAMMAR_CAN_STATEMENT:WRITING",
        "A1FS_ONLINE_V1:GRAMMAR_CAN_STATEMENT:SPEAKING",
    ])
    assert len(bundles["A1FS_ONLINE_V1:GRAMMAR_CAN_STATEMENT:READING"]["assets"]) == 4
    assert len(bundles["A1FS_ONLINE_V1:GRAMMAR_CAN_STATEMENT:WRITING"]["assets"]) == 4
    assert len(bundles["A1FS_ONLINE_V1:GRAMMAR_CAN_STATEMENT:SPEAKING"]["assets"]) == 3

    runtime = data["current_runtime_skeleton"]
    assert runtime["total_asset_count"] == 11
    assert runtime["semantic_target"] == "express ability or capability in an affirmative statement"

    assert q00["status"] == "PASS_A1FS_V1_U06Q00_UNIT05_SUCCESSOR_BASELINE"
    assert q00["exact_predecessor_denominator"]["sentence_assets"]["unit01_to_unit05_cumulative_unique"] == 27371
    assert q00["exact_predecessor_denominator"]["chunks"]["unit01_to_unit05_cumulative_chunk_surfaces"] == 156
    assert q00["unit05_functional_chunk_carry_forward"]["source_q04_new_chunk_surface_count"] == 66
    assert q00["unit05_functional_chunk_carry_forward"]["q06_functional_candidate_usage_ledger_entry_count"] == 0

    gap = data["real_gap_projection"]
    assert gap["canonical_traceability_rows_total"] == 12
    assert gap["direct_teaching_target_rows_total"] == 2
    assert gap["deferred_can_domain_boundary_rows_total"] == 5
    assert gap["quarantined_non_can_modal_rows_total"] == 5
    assert gap["sentence_asset_gap"]["predecessor_pool_for_reuse_and_dedup"] == 27371
    assert gap["chunk_gap"]["predecessor_cumulative_chunk_surfaces"] == 156
    assert gap["chunk_gap"]["inherited_u05_native_functional_chunk_surfaces"] == 66
    assert gap["chunk_gap"]["unit06_native_chunk_extraction_required"] is True
    assert gap["frame_gap"]["rule_primitive_seed_family_count"] == 3
    assert gap["reader360_gap"]["final_reader_set_count"] == 3
    assert gap["reader360_gap"]["fourth_parallel_reader_allowed"] is False
    assert gap["far_gap"]["unit05_full1632_reused_as_fixed_denominator"] is False

    scope = data["scope"]
    assert scope["canonical_graph_mutated"] is False
    assert scope["learner_content_materialized"] is False
    assert scope["vocabulary_authority_materialized"] is False
    assert scope["form_authority_materialized"] is False
    assert scope["chunk_authority_materialized"] is False
    assert scope["frame_authority_materialized"] is False
    assert scope["sentence_assets_materialized"] is False
    assert scope["a2_a2plus_unlocked"] is False

    boundaries = data["claim_boundaries"]
    assert boundaries["canonical_12_row_traceability_is_preserved"] is True
    assert boundaries["canonical_12_row_traceability_does_not_equal_12_row_unit06_teaching_activation"] is True
    assert boundaries["unit06_direct_teaching_activation_is_2_rows"] is True
    assert boundaries["deferred_or_quarantined_rows_must_not_enter_q02_to_q06_generation"] is True
    assert boundaries["q01_does_not_mutate_canonical_mapping"] is True

    routing = data["routing_amendment"]
    assert routing["amendment_status"] == "PASS_A1FS_V1_U06Q01R1_FUTURE_TEACHING_OWNER_ROUTING"
    assert routing["outstanding_teaching_obligation_count"] == 10
    assert routing["canonical_graph_mutated"] is False
    assert routing["learner_content_materialized"] is False
    assert routing["current_learning_state"] == {
        "taught_by_unit06_row_count": 2,
        "known_not_yet_taught_routed_row_count": 10,
        "unassigned_row_count": 0,
        "rule": "ROUTED_DOES_NOT_EQUAL_TAUGHT_OR_COVERED",
    }

    owners = {owner["unit_number"]: owner for owner in routing["routed_owner_units"]}
    assert set(owners) == {14, 20, 21}
    assert owners[14]["grammar_id"] == "GRAMMAR_CAN_NEGATIVE_A1"
    assert owners[14]["routed_row_count"] == 5
    assert {row["egp_row_id"] for row in owners[14]["rows"]} == DEFERRED_CAN_ROWS
    assert owners[20]["grammar_id"] == "GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1"
    assert owners[20]["routed_row_count"] == 3
    assert {row["egp_row_id"] for row in owners[20]["rows"]} == {
        "1741163711300x363892315600628400",
        "1741163711300x444537304178034940",
        "1741163711300x569087712695511000",
    }
    assert owners[21]["grammar_id"] == "GRAMMAR_WILL_FUTURE_A1"
    assert owners[21]["routed_row_count"] == 2
    assert {row["egp_row_id"] for row in owners[21]["rows"]} == {
        "1741163711296x326455472693880200",
        "1741163711296x692481066424056800",
    }

    for row in activation["deferred_can_domain_boundary_rows"]:
        assert row["future_teaching_owner_unit"] == 14
        assert row["learning_status"] == "KNOWN_NOT_YET_TAUGHT"
        assert row["coverage_status"] == "DEFERRED_TO_LATER_UNIT"

    for row in activation["quarantined_non_can_modal_rows"]:
        assert row["future_teaching_owner_unit"] in {20, 21}
        assert row["learning_status"] == "KNOWN_NOT_YET_TAUGHT"
        assert row["coverage_status"] == "DEFERRED_TO_LATER_UNIT"
        assert row["unit06_mapping_status"] == "QUARANTINED_FROM_UNIT06_TEACHING"

    assert boundaries["routed_future_owner_does_not_equal_taught_or_covered"] is True
    assert boundaries["all_ten_non_unit06_rows_have_future_teaching_owner"] is True
    assert data["acceptance"]["future_owner_routing"] == "10/10"
    assert data["acceptance"]["future_owner_distribution"] == {"U14": 5, "U20": 3, "U21": 2}
    assert data["acceptance"]["unassigned_outstanding_teaching_rows"] == 0

    assert data["next_short_step"] == "A1FS-V1-U06Q02_Unit06VocabularyAuthorityAndReusableCarrierAdmission"
