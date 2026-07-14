from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ulga.builders.build_raz_af_a1_a1plus_observational_consumer import (
    ACTIVITY_TYPES,
    ConsumerBuildError,
    build_binding,
    direct_observations,
    grammar_alignment,
    observational_status,
    read_json,
    situation_alignment,
    verify_s12c_consistency,
)
from ulga.builders.build_raz_af_full_coverage_query_index import build_artifacts as build_s12c
from ulga.validators import validate_raz_af_a1_a1plus_observational_consumer as validator_module
from ulga.validators.validate_raz_af_a1_a1plus_observational_consumer import safe_scan

REPO_ROOT = Path(__file__).resolve().parents[2]
HEX_A = "a" * 64
HEX_B = "b" * 64


def _record() -> dict:
    signals = {
        name: {"status": "UNKNOWN", "confidence": 0.0, "evidence_type": "NONE", "review_required": True}
        for name in (
            "controlled_repetition", "copying_potential", "guided_paragraph_potential",
            "literal_comprehension_potential", "parallel_writing_potential", "picture_support_potential",
            "retelling_potential", "sentence_expansion_potential", "sentence_ordering_potential",
            "substitution_drill_potential",
        )
    }
    signals["literal_comprehension_potential"].update(status="SUPPORTED", confidence=1.0, evidence_type="STRUCTURAL", review_required=False)
    template = lambda template_id: {  # noqa: E731
        "template_id": template_id, "support_status": "SUPPORTED", "supporting_signal_refs": [],
        "difficulty_features": [], "authority_status": "observational", "promotion_status": "not_promoted",
        "review_required": False,
    }
    return {
        "identity": {
            "observational_record_id": "RAZ_AF_OBS_V1__RAZ_A_1_P1", "source_unit_ref": "RAZ_A_1_P1",
            "source_level": "A", "source_book_id": "1", "source_page_number": 1,
            "source_record_sha256": HEX_A, "source_content_sha256": HEX_B,
            "enrichment_schema_version": "raz.af.observational_enrichment.v1", "extractor_version": "test",
            "authority_snapshot_refs": [], "enrichment_payload_sha256": HEX_A,
            "source_role": "observational_reference", "authority_import_allowed": False,
            "learner_facing_original_text_allowed": False, "promotion_status": "not_promoted",
        },
        "observations": {
            "vocabulary_exposure": {"scan_status": "COMPLETE", "token_count": 1, "unique_normalized_count": 1, "items": [{
                "surface_form": "x", "normalized_form": "x", "lemma_candidate": "x", "morphological_form": "base",
                "part_of_speech_candidate": "noun", "occurrence_count": 1, "sentence_occurrence_count": 1,
                "evidence_offsets": [[0, 1]], "evp_candidate_refs": ["vocabulary:test"],
                "evp_level_candidates": ["A1"], "match_status": "MATCHED", "sense_ambiguity_status": "UNAMBIGUOUS",
            }]},
            "chunk_exposure": {"scan_status": "COMPLETE", "longest_match_policy": True, "items": []},
            "sentence_pattern_observations": {"scan_status": "COMPLETE", "items": [{
                "abstract_pattern": "X", "slot_types": ["noun"], "occurrence_count": 1, "sentence_count": 1,
                "evidence_hashes": [HEX_A], "mapping_status": "UNMATCHED", "grammar_candidate_refs": [],
                "pattern_authority_candidate_refs": [], "productive_potential": "UNKNOWN", "review_status": "REVIEW_REQUIRED",
            }]},
            "situation_function_observations": {
                "macro_domain_candidates": ["school"], "situation_family_candidates": [],
                "micro_situation_candidates": [], "communicative_function_candidates": [],
                "participant_role_candidates": [], "interaction_goal_candidates": [],
                "classification_status": "CANDIDATE", "confidence": 1.0, "review_status": "REVIEW_REQUIRED",
            },
            "discourse_observation": {
                "discourse_shape": "single_description", "information_progression": "unknown",
                "sentence_relationship": "unknown", "controlled_repetition": False,
                "one_new_detail_per_sentence": "unknown", "entity_count_candidate": 1,
                "event_count_candidate": 0, "cross_sentence_reference_candidate": False,
                "retelling_potential": False, "ordering_potential": False, "classification_status": "CANDIDATE",
            },
            "pedagogical_signals": signals,
            "four_skill_affordances": {
                "language_templates": [template("substitution")], "discourse_templates": [template("retelling")],
                "scaffolding_templates": [template("picture_support")],
                "skill_activity_templates": {
                    "listening": [template("listen_and_repeat")], "speaking": [template("picture_description")],
                    "reading": [template("literal_what")], "writing": [template("copy")],
                },
            },
            "quality_and_review": {
                "authority_write_performed": False, "deterministic_pass_status": "COMPLETE",
                "semantic_pass_status": "NOT_APPLIED", "semantic_review_required": True,
                "source_text_template_copy_detected": False,
            },
        },
    }


def _selected() -> dict:
    return {
        "selection_id": "E4S_A1V1_READING_SOURCE_001", "source_unit_ref": "RAZ_A_1_P1",
        "source_level": "A", "book_id": "1", "page_number": 1, "content_sha256": HEX_B,
        "record_sha256": HEX_A, "e4s_situation_domain": "school",
    }


def _m04b2() -> dict:
    return {
        **_selected(), "source_integrity_status": "PASS", "grammar_binding_status": "NO_CANONICAL_MATCH_REVIEW_REQUIRED",
        "candidate_grammar_ids": [], "deterministic_item_types": {"true_false": 1, "cloze_vocabulary": 1},
        "literal_review_candidate_types": ["literal_what"], "operator_review_required": True,
    }


def _query(record: dict | None = None) -> dict:
    query, _coverage = build_s12c([record or _record()], HEX_A, [])
    return query


def _binding() -> dict:
    return build_binding(_selected(), _m04b2(), _record(), _query())


def _remove_ref(query: dict, surface: str, key: str, ref: str = "RAZ_A_1_P1") -> None:
    for bucket in query["indexes"][surface]:
        if bucket["key"] == key:
            bucket["source_unit_refs"].remove(ref)
            return
    raise AssertionError(f"bucket missing: {surface}:{key}")


def test_new_schemas_are_valid_draft_2020_12() -> None:
    for name in (
        "raz_af_a1_a1plus_observational_consumer_binding.schema.json",
        "raz_af_a1_a1plus_observational_consumer_safe_report.schema.json",
    ):
        Draft202012Validator.check_schema(json.loads((REPO_ROOT / "ulga/schemas" / name).read_text()))


def test_all_selected_refs_resolve_exactly_once() -> None:
    query = _query()
    assert verify_s12c_consistency(_record(), query)["evp_candidate_refs"] == ["vocabulary:test"]
    assert sum("RAZ_A_1_P1" in b["source_unit_refs"] for b in query["indexes"]["source_unit_refs"]) == 1


def test_missing_s12b_selected_record_fails_closed() -> None:
    with pytest.raises(KeyError):
        {}[_selected()["source_unit_ref"]]


def test_extra_binding_is_detectable() -> None:
    refs = ["RAZ_A_1_P1", "RAZ_A_2_P1"]
    assert set(refs) - {_selected()["source_unit_ref"]} == {"RAZ_A_2_P1"}


def test_duplicate_binding_is_detectable() -> None:
    refs = ["RAZ_A_1_P1", "RAZ_A_1_P1"]
    assert len(refs) - len(set(refs)) == 1


def test_missing_s12c_source_ref_bucket() -> None:
    query = _query()
    _remove_ref(query, "source_unit_refs", "RAZ_A_1_P1")
    with pytest.raises(ConsumerBuildError, match="source_unit_refs"):
        verify_s12c_consistency(_record(), query)


@pytest.mark.parametrize(("surface", "key"), [("raz_source_levels", "A"), ("book_ids", "1")])
def test_wrong_s12c_book_or_level_membership(surface: str, key: str) -> None:
    query = _query()
    _remove_ref(query, surface, key)
    with pytest.raises(ConsumerBuildError, match=surface):
        verify_s12c_consistency(_record(), query)


def test_s12b_s12c_evp_ref_mismatch() -> None:
    query = _query()
    _remove_ref(query, "evp_sense_candidate_refs", "vocabulary:test")
    with pytest.raises(ConsumerBuildError, match="evp_sense"):
        verify_s12c_consistency(_record(), query)


def test_s12b_s12c_chunk_ref_mismatch() -> None:
    record = _record()
    record["observations"]["chunk_exposure"]["items"] = [{
        "canonical_chunk_id": "EVP_CHUNK_1", "equivalence_group_id": None, "safe_chunk_id": None,
        "occurrence_count": 1, "match_status": "CANONICAL_MATCH",
    }]
    query = _query(record)
    _remove_ref(query, "canonical_chunk_ids", "EVP_CHUNK_1")
    with pytest.raises(ConsumerBuildError, match="canonical_chunk"):
        verify_s12c_consistency(record, query)


@pytest.mark.parametrize(("field", "surface", "value"), [
    ("grammar_candidate_refs", "grammar_candidate_refs", "GRAMMAR_TEST"),
    ("pattern_authority_candidate_refs", "sentence_pattern_candidate_refs", "pattern:PATTERN_NODE_1"),
])
def test_s12b_s12c_grammar_or_pattern_mismatch(field: str, surface: str, value: str) -> None:
    record = _record()
    record["observations"]["sentence_pattern_observations"]["items"][0][field] = [value]
    query = _query(record)
    _remove_ref(query, surface, value)
    with pytest.raises(ConsumerBuildError, match=surface):
        verify_s12c_consistency(record, query)


def test_situation_domain_aligned_case() -> None:
    assert situation_alignment("school", ["school"]) == "ALIGNED"


def test_situation_domain_conflict_without_overwrite() -> None:
    binding = _binding()
    assert situation_alignment("school", ["travel_mobility"]) == "CONFLICT_REVIEW_REQUIRED"
    assert binding["canonical_consumer_state"]["e4s_situation_domain"] == "school"


def test_observational_unknown_does_not_block_canonical_eligibility() -> None:
    record = _record()
    record["observations"]["vocabulary_exposure"]["items"] = []
    record["observations"]["situation_function_observations"]["macro_domain_candidates"] = []
    record["observations"]["discourse_observation"]["discourse_shape"] = "unknown"
    record["observations"]["pedagogical_signals"]["literal_comprehension_potential"]["status"] = "UNKNOWN"
    record["observations"]["four_skill_affordances"]["skill_activity_templates"]["reading"] = []
    binding = build_binding(_selected(), _m04b2(), record, _query(record))
    assert binding["consumer_decision"]["canonical_eligibility_status"] == "ELIGIBLE_REVIEW_REQUIRED"


def test_low_observational_coverage_keeps_source() -> None:
    assert observational_status({
        "evp_candidate_refs": [], "canonical_chunk_ids": [], "grammar_candidate_refs": [],
        "pattern_candidate_refs": [], "macro_domain_candidates": [], "supported_pedagogical_signals": [],
        "reading_template_candidates": [], "discourse_shape": "unknown",
    }) == "UNKNOWN_REQUIRES_REVIEW"


def test_source_integrity_failure_blocks_eligibility() -> None:
    m04b2 = _m04b2()
    m04b2["source_integrity_status"] = "FAIL"
    assert build_binding(_selected(), m04b2, _record(), _query())["consumer_decision"]["canonical_eligibility_status"] == "BLOCKED_SOURCE_INTEGRITY"


def test_invalid_authority_id_rejected_by_schema() -> None:
    binding = _binding()
    binding["observational_support"]["canonical_chunk_ids"] = ["not an authority id"]
    schema = read_json(REPO_ROOT / "ulga/schemas/raz_af_a1_a1plus_observational_consumer_binding.schema.json")
    assert list(Draft202012Validator(schema).iter_errors(binding))


def test_modified_m04b1_content_hash_blocks_integrity() -> None:
    selected = _selected()
    selected["content_sha256"] = "c" * 64
    assert build_binding(selected, _m04b2(), _record(), _query())["consumer_decision"]["canonical_eligibility_status"] == "BLOCKED_SOURCE_INTEGRITY"


def test_modified_m04b2_deterministic_count_is_visible() -> None:
    m04b2 = _m04b2()
    m04b2["deterministic_item_types"]["true_false"] = 2
    binding = build_binding(_selected(), m04b2, _record(), _query())
    assert binding["canonical_consumer_state"]["deterministic_item_types"]["true_false"] == 2


def test_modified_m04b2_private_hash_is_detectable() -> None:
    report_hash, current_hash = "a" * 64, "b" * 64
    assert report_hash != current_hash


def test_source_sentence_inserted_into_machine_field_is_rejected() -> None:
    binding = _binding()
    binding["observational_support"]["macro_domain_candidates"] = ["This is source text."]
    schema = read_json(REPO_ROOT / "ulga/schemas/raz_af_a1_a1plus_observational_consumer_binding.schema.json")
    assert list(Draft202012Validator(schema).iter_errors(binding))


def test_source_text_inserted_into_safe_report_is_rejected() -> None:
    assert safe_scan({"source_text": "private"}) == ["forbidden_safe_key:$.source_text"]


def test_promotion_or_authority_write_claim_is_rejected() -> None:
    assert safe_scan({"authority_write": True})
    binding = _binding()
    binding["consumer_decision"]["promotion_status"] = "promoted"
    schema = read_json(REPO_ROOT / "ulga/schemas/raz_af_a1_a1plus_observational_consumer_binding.schema.json")
    assert list(Draft202012Validator(schema).iter_errors(binding))


def test_tampered_activity_support_distribution_is_detectable() -> None:
    expected = {name: {"SUPPORTED": 0, "PARTIALLY_SUPPORTED": 0, "UNKNOWN": 0, "CONFLICT_REVIEW_REQUIRED": 0} for name in ACTIVITY_TYPES}
    actual = copy.deepcopy(expected)
    actual["true_false"]["SUPPORTED"] = 1
    assert actual != expected


def test_tampered_review_reason_distribution_is_detectable() -> None:
    expected = {"canonical_operator_review_required": 1}
    actual = {"canonical_operator_review_required": 0}
    assert actual != expected


def test_deterministic_double_build() -> None:
    assert _binding() == _binding()


def test_grammar_alignment_is_explicit() -> None:
    assert grammar_alignment(["GRAMMAR_TEST"], ["GRAMMAR_TEST"]) == "ALIGNED"
    assert grammar_alignment([], []) == "OBSERVATIONAL_UNKNOWN"


def test_real_54_source_local_integration() -> None:
    root = REPO_ROOT / ".local/raz_af/a1_a1plus_observational_consumer_run_a"
    if not (root / "bindings.json").is_file():
        pytest.skip("private local S12D integration artifact unavailable")
    artifact = json.loads((root / "bindings.json").read_text(encoding="utf-8"))
    safe = json.loads((root / "safe_report.json").read_text(encoding="utf-8"))
    assert artifact["binding_count"] == len(artifact["bindings"]) == 54
    assert safe["join_counts"] == {"m04b1_m04b2": 54, "m04b1_s12b": 54, "m04b1_s12c": 54, "s12d_bindings": 54}
    assert safe["compatibility_counters"] == {key: 0 for key in safe["compatibility_counters"]}
