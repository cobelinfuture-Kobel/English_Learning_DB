from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "ulga" / "contracts" / "a1fs_v1_u05_q03_be_form_meaning_auxiliary_boundary_authority.json"
Q01 = ROOT / "ulga" / "contracts" / "a1fs_v1_u05_q01_canonical_target_gap_projection.json"
Q02 = ROOT / "ulga" / "contracts" / "a1fs_v1_u05_q02_vocabulary_carrier_authority.json"
MAPPING = ROOT / "ulga" / "mappings" / "a1_verified_mapping_import_batch_02.json"
GRAMMAR_PROFILE = ROOT / "grammar_profile" / "json" / "grammar_profile.json"
SEQUENCE = ROOT / "product" / "a1fs_v1_2_1" / "runtime" / "sequence.json"
U04_Q03 = ROOT / "ulga" / "contracts" / "a1fs_v1_u04_q03_place_relation_form_meaning_authority.json"


EXPECTED_EGP_ROWS = {
    "1741163706530x753542801715210100",
    "1741163716067x824562184770361200",
    "1741163712047x409239658002596100",
    "1741163715288x262148040901666750",
    "1741163715288x539616242661052000",
    "1741163715608x123988758899529200",
}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_u05_q03_be_form_meaning_and_auxiliary_boundary() -> None:
    data = _load(ARTIFACT)
    q01 = _load(Q01)
    q02 = _load(Q02)
    mapping = _load(MAPPING)
    grammar_rows = _load(GRAMMAR_PROFILE)
    sequence = _load(SEQUENCE)
    u04_q03 = _load(U04_Q03)

    assert data["status"] == "PASS_A1FS_V1_U05Q03_BE_FORM_MEANING_AND_AUXILIARY_BOUNDARY_AUTHORITY"
    assert data["unit_number"] == 5
    assert data["unit_id"] == "GRAMMAR_BE_VERB_BASIC"

    assert q01["status"] == "PASS_A1FS_V1_U05Q01_UNIT05_CANONICAL_TARGET_AND_GAP_PROJECTION"
    assert q02["status"] == "PASS_A1FS_V1_U05Q02_VOCABULARY_AUTHORITY_AND_REUSABLE_CARRIER_ADMISSION"
    assert q02["summary"]["overall"]["admitted_identity_count"] == 106
    assert q02["summary"]["overall"]["new_global_vocabulary_identity_count"] == 0

    be_mapping = next(
        row for row in mapping["mapping_import_units"]
        if row["grammar_id"] == "GRAMMAR_BE_VERB_BASIC"
    )
    assert be_mapping["split_bucket_id"] == "GRAMMAR_BE_COPULA_BASIC_STATEMENTS"
    assert set(be_mapping["new_unique_egp_row_ids"]) == EXPECTED_EGP_ROWS
    assert "progressive auxiliary" in be_mapping["import_reason"]
    assert "past-be" in be_mapping["import_reason"]

    by_id = {row["id"]: row for row in grammar_rows}
    assert EXPECTED_EGP_ROWS <= set(by_id)
    q03_rows = data["canonical_mapping"]["egp_rows"]
    assert {row["egp_row_id"] for row in q03_rows} == EXPECTED_EGP_ROWS
    assert data["canonical_mapping"]["direct_target_row_count"] == 5
    assert data["canonical_mapping"]["boundary_only_row_count"] == 1

    for row in q03_rows:
        source = by_id[row["egp_row_id"]]
        assert source["level"] == "A1"
        assert row["guideword"] == source["guideword"]
        assert row["can_do_statement"] == source["can_do_statement"]
        assert row["source_row"] == source["source_row"]

    aux_id = "1741163715288x262148040901666750"
    aux = next(row for row in q03_rows if row["egp_row_id"] == aux_id)
    assert aux["q03_role"] == "BOUNDARY_ONLY_NOT_DIRECT_UNIT05_MASTERY"
    assert "present continuous" in by_id[aux_id]["can_do_statement"]

    contract = data["form_contract"]
    assert contract["clause_type"] == "DECLARATIVE_STATEMENT_ONLY"
    assert contract["time_reference"] == "PRESENT_ONLY_FOR_UNIT05_DIRECT_TARGET"
    assert contract["core_full_forms"] == ["am", "is", "are"]
    assert contract["direct_target_polarities"] == ["AFFIRMATIVE", "NEGATIVE"]
    assert contract["interrogatives_materialized"] is False
    assert contract["past_be_materialized"] is False
    assert contract["existential_there_be_materialized"] is False
    assert contract["present_continuous_mastery_materialized"] is False
    assert contract["a2_unlocked"] is False

    agreement = {row["subject_class"]: row["be_form"] for row in data["subject_be_agreement"]}
    assert agreement == {
        "I": "am",
        "you": "are",
        "he": "is",
        "she": "is",
        "it": "is",
        "we": "are",
        "they": "are",
        "ADMITTED_SINGULAR_NOUN_PHRASE": "is",
        "ADMITTED_PLURAL_NOUN_PHRASE": "are",
    }

    affirmative = data["affirmative_contraction_policy"]
    assert affirmative["direct_core_mastery_required"] is False
    assert affirmative["natural_variant_allowed"] is True
    assert affirmative["noun_subject_contraction_target_allowed"] is False
    assert {row["contracted"] for row in affirmative["pronoun_variants"]} == {
        "I'm", "you're", "he's", "she's", "it's", "we're", "they're"
    }

    negative = data["negative_be_contract"]
    assert negative["direct_target"] is True
    assert negative["source_egp_row_id"] == "1741163716067x824562184770361200"
    assert negative["contracted_and_uncontracted_required"] is True
    negative_by_subject = {row["subject_class"]: row for row in negative["paradigms"]}
    assert negative_by_subject["I"]["allowed_contractions"] == ["I'm not"]
    assert negative_by_subject["I"]["blocked_forms"] == ["I amn't"]
    assert set(negative_by_subject["you"]["allowed_contractions"]) == {"you're not", "you aren't"}
    assert set(negative_by_subject["he"]["allowed_contractions"]) == {"he's not", "he isn't"}
    assert set(negative_by_subject["we"]["allowed_contractions"]) == {"we're not", "we aren't"}

    bindings = {row["binding_id"]: row for row in data["form_meaning_bindings"]}
    assert set(bindings) == {
        "U05-BE-NP-IDENTITY-CLASSIFICATION",
        "U05-BE-ADJ-DESCRIPTION-STATE",
        "U05-BE-PLACE-LOCATION",
        "U05-BE-AGE-STATE",
        "U05-AUX-BE-ACTION-BOUNDARY",
    }
    assert bindings["U05-BE-NP-IDENTITY-CLASSIFICATION"]["direct_target"] is True
    assert bindings["U05-BE-ADJ-DESCRIPTION-STATE"]["direct_target"] is True
    assert bindings["U05-BE-PLACE-LOCATION"]["direct_target"] is True
    assert bindings["U05-BE-AGE-STATE"]["direct_target"] is True
    assert bindings["U05-AUX-BE-ACTION-BOUNDARY"]["direct_target"] is False
    assert bindings["U05-AUX-BE-ACTION-BOUNDARY"]["mastery_credit"] is False

    assert bindings["U05-BE-PLACE-LOCATION"]["admitted_place_relations"] == [
        "in", "inside", "on", "near", "at", "under", "behind", "between"
    ]
    assert [row["surface"] for row in u04_q03["relations"]] == [
        "in", "inside", "on", "near", "at", "under", "behind", "between"
    ]

    aux_boundary = data["auxiliary_be_boundary"]
    assert aux_boundary["retained_in_canonical_mapping"] is True
    assert aux_boundary["direct_unit05_target"] is False
    assert aux_boundary["unit05_mastery_credit"] is False
    assert aux_boundary["new_q04_target_chunks_from_auxiliary_be"] is False
    assert aux_boundary["new_q05_target_frames_from_auxiliary_be"] is False
    assert aux_boundary["new_q06_target_sentence_assets_from_auxiliary_be"] is False
    assert aux_boundary["q02_action_support_identity_count"] == 12

    gates = {row["form_or_domain"]: row for row in data["false_positive_and_future_unit_gates"]}
    assert gates["BE_INTERROGATIVES"]["future_sequence_unit"] == 13
    assert gates["PAST_BE"]["future_sequence_unit"] == 17
    assert gates["EXISTENTIAL_THERE_BE"]["future_sequence_unit"] == 19
    assert gates["POSSESSIVE_ADJECTIVE_AS_NEW_SIGNAL"]["future_sequence_unit"] == 9
    assert gates["DEMONSTRATIVE_CONTRAST_AS_NEW_SIGNAL"]["future_sequence_unit"] == 7
    assert gates["OBJECT_PRONOUN_AS_NEW_SIGNAL"]["future_sequence_unit"] == 8
    assert gates["PRESENT_CONTINUOUS_PRODUCTION"]["status"] == "BOUNDARY_SUPPORT_ONLY_NOT_UNIT05_MASTERY"
    assert gates["ORIGIN_BE_FROM"]["status"] == "BLOCKED_FROM_UNIT05_TARGET_GENERATION"

    assert sequence["GRAMMAR_BE_VERB_BASIC"] == 5
    assert sequence["GRAMMAR_DEMONSTRATIVES_CONTRAST"] == 7
    assert sequence["GRAMMAR_OBJECT_PRONOUNS_BASIC"] == 8
    assert sequence["GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC"] == 9
    assert sequence["GRAMMAR_BE_INTERROGATIVES_A1"] == 13
    assert sequence["GRAMMAR_PAST_SIMPLE_A1"] == 17
    assert sequence["GRAMMAR_THERE_IS"] == 19
    assert "GRAMMAR_PRESENT_CONTINUOUS_BASIC" not in sequence

    downstream = data["downstream_constraints"]
    assert downstream["q05"]["auxiliary_be_target_frame_allowed"] is False
    assert downstream["q06"]["predecessor_sentence_pool_for_dedup"] == 26610
    assert downstream["q06"]["auxiliary_be_target_sentence_asset_allowed"] is False

    acceptance = data["acceptance"]
    assert acceptance["canonical_egp_row_count"] == 6
    assert acceptance["active_direct_target_row_count"] == 5
    assert acceptance["boundary_only_row_count"] == 1
    assert acceptance["subject_agreement_rows"] == 9
    assert acceptance["direct_complement_binding_count"] == 4
    assert acceptance["auxiliary_boundary_binding_count"] == 1
    assert acceptance["negative_contracted_and_uncontracted_required"] is True
    assert acceptance["new_global_vocabulary_identity_count"] == 0
    assert acceptance["a2_a2plus_unlocked"] is False

    boundaries = data["q03_boundaries"]
    assert boundaries == {
        "chunk_inventory_materialized": False,
        "sentence_frames_materialized": False,
        "sentence_assets_materialized": False,
        "scenes_materialized": False,
        "communicative_functions_materialized": False,
        "questionbank_materialized": False,
        "forms_materialized": False,
        "a2_unlocked": False,
    }

    assert data["next_short_step"] == "A1FS-V1-U05Q04_Unit05BeChunkAuthorityAndCumulativeDedup"
