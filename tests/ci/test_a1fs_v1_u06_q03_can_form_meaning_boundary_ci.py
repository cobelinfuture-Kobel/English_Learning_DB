from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "ulga" / "contracts" / "a1fs_v1_u06_q03_can_form_meaning_boundary_authority.json"
Q01 = ROOT / "ulga" / "contracts" / "a1fs_v1_u06_q01_canonical_target_gap_projection.json"
Q02 = ROOT / "ulga" / "contracts" / "a1fs_v1_u06_q02_vocabulary_carrier_authority.json"
RULES = ROOT / "ulga" / "rules" / "a1_can_statement_rule_primitives.json"
RULE_VALIDATION = ROOT / "ulga" / "reports" / "a1_can_statement_rule_primitive_validation.json"
SEQUENCE = ROOT / "product" / "a1fs_v1_2_1" / "runtime" / "sequence.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_u06_q03_can_form_meaning_boundary_authority() -> None:
    data = _load(ARTIFACT)
    q01 = _load(Q01)
    q02 = _load(Q02)
    rules = _load(RULES)
    validation = _load(RULE_VALIDATION)
    sequence = _load(SEQUENCE)

    assert data["status"] == "PASS_A1FS_V1_U06Q03_CAN_FORM_MEANING_BOUNDARY_AUTHORITY"
    assert data["unit_number"] == 6
    assert data["unit_id"] == "GRAMMAR_CAN_STATEMENT"
    assert data["source_main_sha"] == "389d9b5f5722627b36e203f748a09661213e423d"

    assert q01["status"] == "PASS_A1FS_V1_U06Q01_UNIT06_CANONICAL_TARGET_AND_GAP_PROJECTION"
    assert q01["teaching_activation"]["direct_teaching_target_row_count"] == 2
    assert q01["acceptance"]["future_owner_routing"] == "10/10"
    assert q02["status"] == "PASS_A1FS_V1_U06Q02_VOCABULARY_AUTHORITY_AND_REUSABLE_CARRIER_ADMISSION"
    assert q02["summary"]["admitted_identity_count"] == 91
    assert q02["summary"]["new_global_vocabulary_identity_count"] == 0

    target = data["canonical_target"]
    assert target["direct_teaching_row_count"] == 2
    assert {row["egp_row_id"] for row in target["direct_teaching_rows"]} == {
        "1741163710388x206193011712334940",
        "1741163710388x882361395502946800",
    }
    assert target["future_owner_row_count"] == 10
    assert target["future_owner_rows_must_remain_inactive"] is True
    assert target["routing_distribution"] == {"U14": 5, "U20": 3, "U21": 2}

    contract = data["form_contract"]
    assert contract["clause_type"] == "DECLARATIVE_STATEMENT_ONLY"
    assert contract["polarity"] == "AFFIRMATIVE_ONLY"
    assert contract["modal_surface"] == "can"
    assert contract["modal_function"] == "MODAL_AUXILIARY"
    assert contract["meaning_domain"] == "ABILITY_OR_CAPABILITY_TO_DO_AN_ACTION"
    assert contract["subject_modal_agreement_rule"] == "CAN_IS_INVARIANT_ACROSS_ALL_SUBJECTS"
    assert contract["lexical_verb_form"] == "BASE_FORM"
    assert contract["do_support_allowed"] is False
    assert contract["infinitive_to_after_can_allowed"] is False
    assert contract["third_person_s_after_can_allowed"] is False
    assert contract["past_form_after_can_allowed"] is False
    assert contract["ing_form_after_can_allowed"] is False
    assert contract["question_inversion_allowed"] is False
    assert contract["negative_can_not_allowed"] is False
    assert contract["a2_unlocked"] is False

    paradigm = data["subject_can_paradigm"]
    assert len(paradigm) == 9
    by_subject = {row["subject_class"]: row["form"] for row in paradigm}
    assert by_subject["I"] == "I can {BASE_VERB}"
    assert by_subject["he"] == "he can {BASE_VERB}"
    assert by_subject["they"] == "they can {BASE_VERB}"
    assert by_subject["ADMITTED_PERSON_OR_ROLE_NOUN_PHRASE"] == "{ADMITTED_PERSON_OR_ROLE_NP} can {BASE_VERB}"

    carriers = data["q02_carrier_binding"]
    assert carriers["admitted_identity_count"] == 91
    assert carriers["by_carrier_class"] == {
        "SUBJECT_OR_PERSON": 21,
        "ACTION_VERB": 15,
        "OBJECT": 25,
        "ACTIVITY_COMPLEMENT": 0,
        "PLACE": 29,
        "MANNER_OR_SUPPORT": 1,
    }
    assert carriers["activity_complement_zero_identity_policy"].startswith("STRUCTURAL_OR_PHRASE_LEVEL_SLOT_ONLY")
    assert carriers["q02_carriers_do_not_prove_actual_q06_sentence_usage"] is True

    bindings = {row["binding_id"]: row for row in data["form_meaning_bindings"]}
    assert set(bindings) == {
        "U06-CAN-INTRANSITIVE-ABILITY",
        "U06-CAN-TRANSITIVE-ABILITY-OBJECT",
        "U06-CAN-ACTIVITY-COMPLEMENT-ABILITY",
    }
    assert all(row["direct_target"] is True for row in bindings.values())
    assert bindings["U06-CAN-INTRANSITIVE-ABILITY"]["form"] == "SUBJECT + can + BASE_VERB"
    assert bindings["U06-CAN-TRANSITIVE-ABILITY-OBJECT"]["form"] == "SUBJECT + can + BASE_VERB + OBJECT"
    assert bindings["U06-CAN-ACTIVITY-COMPLEMENT-ABILITY"]["downstream_required_authorities"] == [
        "Q04_APPROVED_CHUNK_OR_PHRASE",
        "Q05_APPROVED_FRAME",
    ]

    source_primitives = {row["rule_id"] for row in rules["rule_primitives"]}
    assert source_primitives == {
        "CAN_AFFIRMATIVE_INTRANSITIVE_ABILITY_CORE",
        "CAN_AFFIRMATIVE_TRANSITIVE_ABILITY_OBJECT",
        "CAN_AFFIRMATIVE_ACTIVITY_COMPLEMENT",
    }
    promotion = data["rule_primitive_promotion"]
    assert promotion["source_primitive_count"] == 3
    assert promotion["q03_disposition"] == "PROMOTED_AS_FORM_MEANING_FAMILY_SEEDS_ONLY_NOT_EXACT_Q05_FRAMES"
    assert promotion["exact_q05_frame_identity_count"] == 0
    assert promotion["learner_facing_sentence_asset_count"] == 0
    assert validation["validation_summary"] == {
        "total_cases": 12,
        "pass_count": 12,
        "fail_count": 0,
        "status": "PASS",
    }

    meaning = data["meaning_boundary"]
    assert meaning["required_meaning"] == "ABILITY"
    assert set(meaning["blocked_readings"]) == {"PERMISSION", "OFFER", "REQUEST", "POSSIBILITY"}
    assert meaning["ambiguous_without_context_policy"] == "DO_NOT_ADMIT_AS_UNIT06_TARGET_UNTIL_CONTEXT_DISAMBIGUATES_TO_ABILITY"
    assert meaning["can_as_noun_policy"] == "BLOCK"

    morph = data["morphology_and_valency_gates"]
    assert morph["accepted_core_sequence"] == "SUBJECT + can + BASE_VERB"
    blocked = set(morph["blocked_sequences"])
    assert "SUBJECT + can + to + VERB" in blocked
    assert "SUBJECT + can + VERB_S" in blocked
    assert "SUBJECT + can + VERB_ING" in blocked
    assert "SUBJECT + do/does + can + VERB" in blocked
    assert "SUBJECT + cannot/can't + VERB as Unit06 target" in blocked

    gates = {row["form_or_meaning"]: row for row in data["future_owner_and_false_positive_gates"]}
    for key in ["CAN_QUESTION", "CAN_NEGATIVE", "CAN_OFFER", "CAN_REQUEST", "CAN_PERMISSION", "CAN_POSSIBILITY"]:
        assert gates[key]["future_sequence_unit"] == 14
        assert gates[key]["future_unit_id"] == "GRAMMAR_CAN_NEGATIVE_A1"
    assert gates["WILL_AFFIRMATIVE_OR_PLANS"]["future_sequence_unit"] == 21
    assert gates["WOULD_LIKE"]["future_sequence_unit"] == 20

    assert sequence["GRAMMAR_CAN_STATEMENT"] == 6
    assert sequence["GRAMMAR_CAN_NEGATIVE_A1"] == 14
    assert sequence["GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1"] == 20
    assert sequence["GRAMMAR_WILL_FUTURE_A1"] == 21

    predecessor = data["predecessor_integration"]
    assert predecessor["predecessor_sentence_pool_for_future_q06_dedup"] == 27371
    assert predecessor["predecessor_chunk_surfaces_for_future_q04_dedup"] == 156
    assert predecessor["inherited_u05_functional_chunk_surfaces_for_q04_reassessment"] == 66
    assert predecessor["q03_does_not_relabel_predecessor_assets_as_unit06_native"] is True

    downstream = data["downstream_constraints"]
    assert downstream["q04"]["must_reassess_inherited_u05_functional_chunks"] is True
    assert downstream["q05"]["seed_family_ids"] == [
        "CAN_AFFIRMATIVE_INTRANSITIVE_ABILITY_CORE",
        "CAN_AFFIRMATIVE_TRANSITIVE_ABILITY_OBJECT",
        "CAN_AFFIRMATIVE_ACTIVITY_COMPLEMENT",
    ]
    assert downstream["q05"]["exact_frames_materialized_by_q03"] is False
    assert downstream["q06"]["predecessor_sentence_pool_for_dedup"] == 27371
    assert downstream["q06"]["question_or_negative_target_sentence_asset_allowed"] is False
    assert downstream["q06"]["non_ability_can_target_sentence_asset_allowed"] is False

    acceptance = data["acceptance"]
    assert acceptance["q01_direct_teaching_rows"] == "2/2"
    assert acceptance["q01_future_owner_rows_inactive"] == "10/10"
    assert acceptance["q02_admitted_carrier_identities"] == "91/91"
    assert acceptance["form_meaning_binding_count"] == 3
    assert acceptance["invariant_subject_paradigm_rows"] == 9
    assert acceptance["rule_primitive_family_seeds"] == "3/3"
    assert acceptance["prototype_validation"] == "12/12"
    assert acceptance["exact_q05_frames_materialized"] == 0
    assert acceptance["learner_facing_sentences_generated"] == 0
    assert acceptance["canonical_graph_mutations"] == 0
    assert acceptance["a2_a2plus_unlocked"] is False

    assert data["q03_boundaries"] == {
        "chunk_inventory_materialized": False,
        "sentence_frames_materialized": False,
        "sentence_assets_materialized": False,
        "scenes_materialized": False,
        "reader360_materialized": False,
        "practice_materialized": False,
        "a2_unlocked": False,
    }

    assert data["next_short_step"] == "A1FS-V1-U06Q04_Unit06CanAbilityChunkAuthorityAndCumulativeDedup"
