from __future__ import annotations

from collections import Counter
from typing import Any

from product.a1fs_v1_2_1 import u04neb02_natural_episode_bank_360 as current360
from product.a1fs_v1_2_1 import u04fsv2_current360_contextual_form_runtime as legacy_fsv2

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Executable production contract only. GPT-5.6 directly authors learner-facing FormV3 "
    "assets from immutable Current360 episodes; Python is restricted to mechanical "
    "validation, identity, coverage, rendering, pagination, and packaging."
)
PROGRAM_ID = "A1FS-V1"
UNIT_ID = "GRAMMAR_BASIC_PREPOSITIONS_PLACE"
TASK_ID = "A1FS-V1-U04FORMV3_ProductionContract"
STATUS = "PASS_A1FS_V1_U04FORMV3_DIRECT_AUTHORING_PRODUCTION_CONTRACT"
REVISION = "GPT5_6_DIRECT_AUTHORING_PYTHON_VALIDATION_ONLY_V1"
NEXT_SHORT_STEP = "A1FS-V1-U04FORMV3A_GPT56DirectForm01To04LearnerTaskRematerialization"

FORM_COUNT = 20
QUESTIONS_PER_FORM = 40
SECTION_ORDER = ("A", "B", "C", "D", "E")
SECTION_COUNTS = {"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}
TARGET_RELATIONS = tuple(legacy_fsv2.TARGET_RELATIONS)
SUPPORT_RELATIONS = tuple(legacy_fsv2.SUPPORT_RELATIONS)
STAGE_ORDER = ("GUIDED", "REDUCED_SUPPORT", "INDEPENDENT", "TRANSFER", "RETENTION")
STAGE_FORM_RANGES = {
    "GUIDED": (1, 2, 3, 4),
    "REDUCED_SUPPORT": (5, 6, 7, 8),
    "INDEPENDENT": (9, 10, 11, 12),
    "TRANSFER": (13, 14, 15, 16),
    "RETENTION": (17, 18, 19, 20),
}
SEEN_UNSEEN_BOUNDARY_FORM = 13

# Each Form uses six coherent, immutable Current360 episodes rather than one passage per item.
CONTEXT_SLOT_CONTRACT = {
    "A1": {"sections": ("A",), "question_load": {"A": 3}},
    "A2": {"sections": ("A",), "question_load": {"A": 3}},
    "BC1": {"sections": ("B", "C"), "question_load": {"B": 5, "C": 5}},
    "BC2": {"sections": ("B", "C"), "question_load": {"B": 5, "C": 5}},
    "DE1": {"sections": ("D", "E"), "question_load": {"D": 4, "E": 3}},
    "DE2": {"sections": ("D", "E"), "question_load": {"D": 4, "E": 3}},
}
CONTEXT_SLOTS_PER_FORM = 6
CROSS_FORM_EPISODE_REUSE_ALLOWED = False
PASSAGE_MUTATION_ALLOWED = False
PASSAGE_DISPLAY_POLICY = "DISPLAY_EXACT_CURRENT360_PASSAGE_ONCE_PER_SECTION_CONTEXT"

AUTHORING_CONTRACT = {
    "learner_content_author": "GPT-5.6_SOL_DIRECT_AUTHORING",
    "current360_passage_authority": current360.TASK_ID,
    "current360_passage_text_must_be_exact": True,
    "python_may_author_learner_facing_english": False,
    "python_allowed_roles": (
        "schema_validation", "identity_assignment", "coverage_counting",
        "deduplication_detection", "answer_position_audit",
        "semantic_leakage_detection", "source_lineage_validation",
        "renderer_invocation", "pagination_validation", "packaging",
    ),
    "python_forbidden_roles": (
        "prompt_composition", "stimulus_composition", "distractor_composition",
        "learner_sentence_generation", "passage_paraphrase",
        "preposition_string_replacement", "wrong_sentence_synthesis", "semantic_repair",
    ),
    "legacy_python_task_builder_role": "SUPERSEDED_FOR_FORMV3_LEARNER_AUTHORING_ONLY",
    "legacy_fsv2_active_runtime_cutover": "NOT_CHANGED_UNTIL_FORMV3_FULL_ACCEPTANCE",
}
LEARNER_LANGUAGE_FORBIDDEN_PHRASES = (
    "located thing", "position evidence", "focus sentence", "focus place word",
    "given place word", "target relation", "grammar level", "task family",
    "reference continuity",
)
SEMANTIC_QUALITY_CONTRACT = {
    "masked_duplicate_answer_leakage_allowed": False,
    "reading_detail_answer_recoverable_from_passage_allowed": True,
    "blank_or_reconstruction_answer_may_remain_verbatim_visible_elsewhere": False,
    "error_correction_wrong_sentence_must_be_grammatical": True,
    "error_correction_wrong_sentence_must_be_semantically_plausible": True,
    "error_correction_wrong_sentence_must_conflict_with_passage_fact": True,
    "mechanical_preposition_replacement_allowed": False,
    "all_distractors_must_be_grammatical": True,
    "all_distractors_must_match_semantic_type": True,
    "exactly_one_correct_choice_required": True,
    "learner_internal_engineering_language_allowed": False,
}
ANSWER_DIVERSITY_CONTRACT = {
    "per_form_select_one_position_max_delta": 1,
    "identical_select_answer_sequence_across_forms_allowed": False,
    "same_question_slot_fixed_answer_across_all_four_forms_allowed": False,
    "identical_40_task_family_sequence_across_forms_allowed": False,
    "python_may_shuffle_answers_after_authoring": False,
    "repair_action": "RETURN_ITEM_TO_GPT5_6_FOR_REAUTHORING",
}

STAGE_COGNITIVE_CONTRACT = {
    "GUIDED": {
        "context_exposure": "SEEN_GUIDED", "support_level": "HIGH",
        "source_sentence_count_preference": (2, 3),
        "output": "ONE_SHORT_SENTENCE_OR_SHORT_ORAL_RESPONSE",
        "capabilities": ("literal_location_meaning", "natural_sentence_discrimination",
            "explicit_detail_retrieval", "basic_reference_tracking", "simple_sequence",
            "one_sentence_production"),
    },
    "REDUCED_SUPPORT": {
        "context_exposure": "SEEN_REDUCED_SUPPORT", "support_level": "MEDIUM",
        "source_sentence_count_preference": (3, 4),
        "output": "ONE_TO_TWO_CONNECTED_A1_SENTENCES",
        "capabilities": ("detail_retrieval", "meaning_based_reconstruction",
            "two_sentence_connection", "basic_reference_tracking", "simple_inference",
            "short_productive_response"),
    },
    "INDEPENDENT": {
        "context_exposure": "SEEN_INDEPENDENT", "support_level": "LOW",
        "source_sentence_count_preference": (3, 4, 5),
        "output": "ONE_TO_THREE_A1_SENTENCES",
        "capabilities": ("person_object_location_tracking", "action_sequence",
            "reference_resolution", "detail_and_gist", "simple_inference",
            "independent_short_writing_and_speaking"),
    },
    "TRANSFER": {
        "context_exposure": "UNSEEN_TRANSFER", "support_level": "MINIMAL",
        "source_sentence_count_preference": (3, 4, 5),
        "output": "ONE_TO_THREE_A1_SENTENCES",
        "capabilities": ("unseen_context_comprehension", "relation_transfer_without_new_grammar",
            "reference_resolution", "simple_inference", "meaning_preserving_rewrite",
            "independent_short_productive_transfer"),
    },
    "RETENTION": {
        "context_exposure": "UNSEEN_RETENTION", "support_level": "CUMULATIVE",
        "source_sentence_count_preference": (3, 4, 5),
        "output": "ONE_TO_THREE_A1_SENTENCES",
        "capabilities": ("cumulative_location_comprehension", "reference_and_sequence_retention",
            "evidence_selection", "simple_inference", "short_connected_writing",
            "short_connected_speaking"),
    },
}

# Per-form family quotas. Family order is intentionally not fixed across forms.
STAGE_FAMILY_QUOTAS = {
    "GUIDED": {
        "A": {"RELATION_MEANING_CHOICE": 2, "NATURAL_SENTENCE_CHOICE": 2, "LOCATION_CONTRAST_CHOICE": 2},
        "B": {"DETAIL_QA": 4, "EVIDENCE_CHOICE": 2, "REFERENCE_QA": 2, "FACT_CHECK_NATURAL": 2},
        "C": {"MEANING_BASED_RECONSTRUCTION": 3, "NATURAL_FACT_CORRECTION": 2, "EVIDENCE_TO_SENTENCE": 2, "OPEN_LOCATION_SENTENCE": 2, "TWO_SENTENCE_LINK": 1},
        "D": {"PERSON_OBJECT_TRACKING": 2, "ACTION_SEQUENCE": 2, "REFERENCE_RESOLUTION": 2, "SIMPLE_INFERENCE": 1, "EVIDENCE_JUSTIFICATION": 1},
        "E": {"WRITE_ONE_FACT": 2, "SPEAK_LOCATION_QA": 2, "SPEAK_SHORT_RETELL": 1, "ASK_LOCATION_QUESTION": 1},
    },
    "REDUCED_SUPPORT": {
        "A": {"NATURAL_SENTENCE_CHOICE": 2, "LOCATION_CONTRAST_CHOICE": 2, "GRAMMAR_IN_CONTEXT_SHORT": 2},
        "B": {"DETAIL_QA": 3, "REFERENCE_QA": 2, "ACTION_SEQUENCE": 2, "SIMPLE_INFERENCE": 2, "EVIDENCE_CHOICE": 1},
        "C": {"MEANING_BASED_RECONSTRUCTION": 2, "NATURAL_FACT_CORRECTION": 2, "TWO_SENTENCE_LINK": 2, "EVIDENCE_TO_SENTENCE": 2, "REFERENCE_REWRITE": 2},
        "D": {"PERSON_OBJECT_TRACKING": 1, "ACTION_SEQUENCE": 2, "REFERENCE_RESOLUTION": 2, "SIMPLE_INFERENCE": 2, "EVIDENCE_JUSTIFICATION": 1},
        "E": {"WRITE_ONE_FACT": 1, "WRITE_TWO_CONNECTED_FACTS": 2, "SPEAK_LOCATION_QA": 1, "SPEAK_SHORT_RETELL": 1, "ASK_LOCATION_QUESTION": 1},
    },
    "INDEPENDENT": {
        "A": {"LOCATION_CONTRAST_CHOICE": 2, "GRAMMAR_IN_CONTEXT_SHORT": 2, "NATURAL_CORRECTION_CHOICE": 2},
        "B": {"DETAIL_QA": 2, "REFERENCE_QA": 2, "ACTION_SEQUENCE": 2, "SIMPLE_INFERENCE": 2, "GIST_QA": 1, "EVIDENCE_CHOICE": 1},
        "C": {"MEANING_BASED_RECONSTRUCTION": 1, "NATURAL_FACT_CORRECTION": 2, "TWO_SENTENCE_LINK": 2, "REFERENCE_REWRITE": 2, "OPEN_LOCATION_SENTENCE": 2, "SHORT_RETELL_WRITING": 1},
        "D": {"PERSON_OBJECT_TRACKING": 1, "ACTION_SEQUENCE": 1, "REFERENCE_RESOLUTION": 2, "SIMPLE_INFERENCE": 2, "EVIDENCE_JUSTIFICATION": 2},
        "E": {"WRITE_TWO_CONNECTED_FACTS": 2, "SPEAK_SHORT_RETELL": 1, "ASK_LOCATION_QUESTION": 1, "SPEAK_TRANSFER_RESPONSE": 1, "WRITE_TRANSFER_RESPONSE": 1},
    },
    "TRANSFER": {
        "A": {"LOCATION_CONTRAST_CHOICE": 2, "GRAMMAR_IN_CONTEXT_SHORT": 2, "NATURAL_CORRECTION_CHOICE": 2},
        "B": {"DETAIL_QA": 2, "REFERENCE_QA": 2, "ACTION_SEQUENCE": 1, "SIMPLE_INFERENCE": 2, "GIST_QA": 1, "EVIDENCE_CHOICE": 2},
        "C": {"NATURAL_FACT_CORRECTION": 1, "TWO_SENTENCE_LINK": 2, "REFERENCE_REWRITE": 2, "OPEN_LOCATION_SENTENCE": 2, "TRANSFER_REWRITE": 3},
        "D": {"PERSON_OBJECT_TRACKING": 1, "ACTION_SEQUENCE": 1, "REFERENCE_RESOLUTION": 2, "SIMPLE_INFERENCE": 2, "EVIDENCE_JUSTIFICATION": 2},
        "E": {"WRITE_TWO_CONNECTED_FACTS": 2, "SPEAK_TRANSFER_RESPONSE": 2, "ASK_LOCATION_QUESTION": 1, "SPEAK_SHORT_RETELL": 1},
    },
    "RETENTION": {
        "A": {"RELATION_MEANING_CHOICE": 1, "LOCATION_CONTRAST_CHOICE": 2, "GRAMMAR_IN_CONTEXT_SHORT": 1, "NATURAL_CORRECTION_CHOICE": 2},
        "B": {"DETAIL_QA": 1, "REFERENCE_QA": 2, "ACTION_SEQUENCE": 1, "SIMPLE_INFERENCE": 2, "GIST_QA": 2, "EVIDENCE_CHOICE": 2},
        "C": {"NATURAL_FACT_CORRECTION": 1, "TWO_SENTENCE_LINK": 2, "REFERENCE_REWRITE": 1, "OPEN_LOCATION_SENTENCE": 2, "SHORT_RETELL_WRITING": 2, "TRANSFER_REWRITE": 2},
        "D": {"ACTION_SEQUENCE": 1, "REFERENCE_RESOLUTION": 2, "SIMPLE_INFERENCE": 2, "EVIDENCE_JUSTIFICATION": 2, "SHORT_RETELL_PLANNING": 1},
        "E": {"WRITE_TWO_CONNECTED_FACTS": 1, "WRITE_TRANSFER_RESPONSE": 1, "SPEAK_SHORT_RETELL": 1, "SPEAK_TRANSFER_RESPONSE": 2, "ASK_LOCATION_QUESTION": 1},
    },
}

CAMBRIDGE_BOUNDARY = {
    "grammar_ceiling": "A1",
    "yle_role": "A1_MOVERS_COMPATIBLE_SKILL_PROGRESSION",
    "ket_role": "PREREQUISITE_TASK_MATURITY_ONLY",
    "official_ket_item_claimed": False,
    "a2_a2plus_unlocked": False,
    "listening_modified": False,
    "forbidden_a2_like_outputs": ("25_PLUS_WORD_EMAIL_TASK", "35_PLUS_WORD_PICTURE_STORY_TASK", "EXTENDED_REASONED_DISCUSSION"),
}
ACTIVATION_CONTRACT = {
    "pilot_forms": (1, 2, 3, 4),
    "formv3_pilot_active_runtime": False,
    "full_runtime_cutover_before_human_acceptance_allowed": False,
    "current_fsv2_runtime_remains_active_until_successor_acceptance": True,
    "parallel_form_runtime_allowed": False,
}

class Unit04FormV3ContractError(ValueError):
    pass


def validate_contract() -> dict[str, Any]:
    if sum(SECTION_COUNTS.values()) != QUESTIONS_PER_FORM:
        raise Unit04FormV3ContractError("SECTION_COUNT_SUM_DRIFT")
    forms = [n for stage in STAGE_ORDER for n in STAGE_FORM_RANGES[stage]]
    if forms != list(range(1, FORM_COUNT + 1)):
        raise Unit04FormV3ContractError("STAGE_FORM_COVERAGE_DRIFT")
    load = Counter()
    for slot in CONTEXT_SLOT_CONTRACT.values():
        load.update(slot["question_load"])
    if dict(load) != SECTION_COUNTS:
        raise Unit04FormV3ContractError(f"CONTEXT_QUESTION_LOAD_DRIFT:{dict(load)}")
    for stage in STAGE_ORDER:
        if tuple(STAGE_FAMILY_QUOTAS[stage]) != SECTION_ORDER:
            raise Unit04FormV3ContractError(f"STAGE_SECTION_ORDER_DRIFT:{stage}")
        for section in SECTION_ORDER:
            actual = sum(STAGE_FAMILY_QUOTAS[stage][section].values())
            if actual != SECTION_COUNTS[section]:
                raise Unit04FormV3ContractError(f"FAMILY_QUOTA_DRIFT:{stage}:{section}:{actual}")
    if AUTHORING_CONTRACT["python_may_author_learner_facing_english"] is not False:
        raise Unit04FormV3ContractError("PYTHON_AUTHORING_NOT_FORBIDDEN")
    if PASSAGE_MUTATION_ALLOWED or CROSS_FORM_EPISODE_REUSE_ALLOWED:
        raise Unit04FormV3ContractError("CURRENT360_SOURCE_BOUNDARY_DRIFT")
    if SEMANTIC_QUALITY_CONTRACT["mechanical_preposition_replacement_allowed"]:
        raise Unit04FormV3ContractError("MECHANICAL_PREPOSITION_REPLACEMENT_ALLOWED")
    if ANSWER_DIVERSITY_CONTRACT["python_may_shuffle_answers_after_authoring"]:
        raise Unit04FormV3ContractError("PYTHON_ANSWER_SHUFFLE_ALLOWED")
    if CAMBRIDGE_BOUNDARY["grammar_ceiling"] != "A1" or CAMBRIDGE_BOUNDARY["a2_a2plus_unlocked"]:
        raise Unit04FormV3ContractError("A1_CEILING_DRIFT")
    if CAMBRIDGE_BOUNDARY["listening_modified"]:
        raise Unit04FormV3ContractError("LISTENING_MODIFIED")
    if ACTIVATION_CONTRACT["formv3_pilot_active_runtime"] or ACTIVATION_CONTRACT["parallel_form_runtime_allowed"]:
        raise Unit04FormV3ContractError("PILOT_ACTIVATION_DRIFT")
    return {
        "task_id": TASK_ID, "status": STATUS, "revision": REVISION,
        "form_count": FORM_COUNT, "questions_per_form": QUESTIONS_PER_FORM,
        "section_counts": dict(SECTION_COUNTS), "context_slots_per_form": CONTEXT_SLOTS_PER_FORM,
        "stage_form_ranges": {k: list(v) for k, v in STAGE_FORM_RANGES.items()},
        "current360_passage_authority": current360.TASK_ID,
        "python_may_author_learner_facing_english": False,
        "grammar_ceiling": "A1", "a2_a2plus_unlocked": False, "listening_modified": False,
        "pilot_forms": list(ACTIVATION_CONTRACT["pilot_forms"]),
        "pilot_active_runtime": False, "next_short_step": NEXT_SHORT_STEP,
    }
