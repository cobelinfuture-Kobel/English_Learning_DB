from functools import lru_cache

from ulga.builders import (
    build_a1fs_v1_u02sp02_unit01_unit02_exact_sentence_frame_coverage_recheck as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u02sp02_unit01_unit02_exact_sentence_frame_coverage_recheck as validator,
)


@lru_cache(maxsize=1)
def report():
    value = builder.build_report()
    validation = validator.validate_report(value)
    assert validation["error_count"] == 0
    return value


def test_u02sp02_separates_core_pattern_families_from_exact_sentence_frames():
    value = report()
    patterns = value["pattern_family_coverage"]
    frames = value["exact_frame_coverage"]

    assert patterns["unit01_inherited_pedagogical_core_family_count"] == 3
    assert patterns["unit02_new_canonical_core_pattern_count"] == 4
    assert patterns["cumulative_pedagogical_core_pattern_family_count"] == 7
    assert patterns["unit02_main_plural_sentence_generation_family_count"] == 5

    assert frames["unit01_exact_frame_count"] == 11
    assert frames["unit01_core_sentence_frame_count"] == 6
    assert frames["unit01_adjective_sentence_frame_count"] == 3
    assert frames["unit01_scaffold_frame_count"] == 2
    assert frames["unit02_new_canonical_exact_frame_count"] == 4
    assert frames["cross_unit_exact_template_overlap_count"] == 0
    assert frames["cumulative_declared_exact_frame_count"] == 15


def test_u02sp02_binds_the_four_unit02_new_patterns_to_canonical_sp_authority():
    value = report()
    rows = value["pattern_family_coverage"]["unit02_new_canonical_core_patterns"]
    actual = {
        row["source_record_id"]: row["canonical_pattern"]
        for row in rows
    }
    assert actual == {
        "SP_000003": "I have {noun_phrase}.",
        "SP_000004": "I like {noun_phrase/gerund}.",
        "SP_000005": "I don't like {noun_phrase/gerund}.",
        "SP_000013": "Can I have {noun_phrase}?",
    }
    assert all(row["review_status"] == "accepted" for row in rows)

    i_have = value["i_have_lineage_reconciliation"]
    assert i_have["unit01_contract_frame_id"] == "U01-F02"
    assert i_have["unit01_contract_template"] == "I have {ARTICLE} {THING}."
    assert i_have["unit02_canonical_pattern_id"] == "SP_000003"
    assert i_have["exact_template_match"] is False
    assert i_have["unit01_pedagogical_core_inherited"] is False
    assert i_have["unit02_new_core_pattern"] is True


def test_u02sp02_reconciles_the_994_legacy_sp000002_bindings_without_rewriting_questionbank():
    value = report()
    legacy = value["legacy_pattern_reconciliation"]
    assert legacy["canonical_authority"]["canonical_pattern"] == "My name is {name}."
    assert legacy["raw_approved_u02_item_count"] == 994
    assert legacy["raw_pattern_binding_distribution"] == {"SP_000002": 994}
    assert legacy["raw_legacy_invalid_binding_count"] == 994
    assert legacy["reconciled_legacy_invalid_binding_count"] == 0
    assert legacy["reconciled_direct_canonical_sp_binding_count"] == 0
    assert legacy["unit02_new_core_patterns_bound_in_current_questionbank_count"] == 0
    assert legacy["inherited_clause_shell_recombination_item_count"] == 96
    assert legacy["future_runtime_must_consume_reconciled_projection"] is True
    assert legacy["raw_pattern_ids_runtime_authoritative"] is False

    projection = value["reconciled_questionbank_pattern_projection"]
    assert len(projection) == 13
    assert sum(row["item_count"] for row in projection) == 994
    assert all(row["reconciled_direct_pattern_ids"] == [] for row in projection)
    inherited = [
        row for row in projection
        if row["lineage_class"] == "INHERITED_U01_CLAUSE_SHELL_WITH_UNIT02_PLURAL_NP"
    ]
    assert {row["family_id"] for row in inherited} == {"PRODUCTIVE_RESPONSE", "TRANSFER"}
    assert sum(row["item_count"] for row in inherited) == 96
    assert all(row["source_unit01_frame_id"] == "U01-F06" for row in inherited)


def test_u02sp02_is_read_only_and_stops_before_sentence_asset_q6():
    value = report()
    assert value["claim_boundaries"] == {
        "historical_u02qb02_payload_mutated": False,
        "historical_u02qbc02_payload_mutated": False,
        "questionbank_item_identity_mutated": False,
        "answer_or_scoring_contract_mutated": False,
        "global_sentence_pattern_authority_mutated": False,
        "runtime_connected": False,
        "canonical_scene_authority_mutated": False,
        "new_learner_content_created": False,
        "a2_unlocked": False,
    }
    assert value["next_scope"] == {
        "scope_status": "OUTSIDE_APPROVED_Q5_SCOPE",
        "next_short_step": "A1FS-V1-U02SA01_Unit01Unit02CumulativeSentenceAssetCoverageRecheck",
    }
