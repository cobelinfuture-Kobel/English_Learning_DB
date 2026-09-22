from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "FAR3 validates the production contract for future GPT-5.6-authored learner-facing "
    "practice. It does not author learner-facing text. Python may validate contract "
    "structure, FAR2 slot denominators, lineage requirements, review gates, and "
    "artifact-proliferation guards only."
)

TASK_ID = "A1FS-V1-U05FAR3_LearnerFacingPracticeMaterializationContract"
STATUS = "PASS_A1FS_V1_U05FAR3_LEARNER_FACING_PRACTICE_MATERIALIZATION_CONTRACT"
NEXT_SHORT_STEP = "A1FS-V1-U05FAR4_GPT56LearnerFacingPracticeMaterializationPreflight"

REPO_ROOT = Path(__file__).resolve().parents[2]
FAR3_PATH = REPO_ROOT / "product/a1fs_v1_2_1/data/unit05_learner_facing_practice_materialization_contract.json"
FAR2_PATH = REPO_ROOT / "product/a1fs_v1_2_1/data/unit05_coverage_driven_practice_slots.json"
S2_PATH = REPO_ROOT / "data/ket/ket_s2_semantic_task_profiles.json"
S9_PATH = REPO_ROOT / "data/ket/ket_s9_level_adaptation_contract.json"

EXPECTED_AUDIO_FAMILIES = {
    "AUDIO_PICTURE_DETAIL_SELECTION",
    "AUDIO_NOTE_COMPLETION",
    "AUDIO_CONVERSATION_DETAIL",
    "SHORT_AUDIO_GIST_INTENT_DETAIL",
    "AUDIO_LIST_MATCHING",
}
EXPECTED_VISUAL_FAMILIES = {
    "PICTURE_SEQUENCE_STORY",
    "AUDIO_PICTURE_DETAIL_SELECTION",
    "COLLABORATIVE_VISUAL_DISCUSSION",
}
EXPECTED_REVIEW_FIELDS = {
    "author_model",
    "gpt56_semantic_review",
    "gpt56_pedagogical_review",
    "gpt56_source_grounding_review",
    "gpt56_unit05_scope_review",
    "gpt56_answerability_review",
}
EXPECTED_FINAL_FILES = {
    "unit05_core_practice_480.json",
    "unit05_ket_adapted_practice_672.json",
    "unit05_dictation_practice_480.json",
}


class U05FAR3Error(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise U05FAR3Error(f"MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise U05FAR3Error(f"NOT_OBJECT:{path}")
    return value


def build_report() -> dict[str, Any]:
    far3 = _load(FAR3_PATH)
    far2 = _load(FAR2_PATH)
    s2 = _load(S2_PATH)
    s9 = _load(S9_PATH)

    if far3.get("task_id") != TASK_ID or far3.get("status") != STATUS:
        raise U05FAR3Error("TASK_OR_STATUS_DRIFT")
    if far3.get("next_short_step") != NEXT_SHORT_STEP:
        raise U05FAR3Error("NEXT_SHORT_STEP_DRIFT")

    scope = far3["scope"]
    if (
        scope["practice_slot_denominator"] != 1632
        or scope["core_grammar_slots"] != 480
        or scope["ket_adapted_slots"] != 672
        or scope["delayed_dictation_slots"] != 480
        or scope["reader_study_slots"] != 360
    ):
        raise U05FAR3Error("FAR3_SCOPE_DENOMINATOR_DRIFT")
    for key in (
        "learner_facing_content_materialized_in_far3",
        "audio_materialized_in_far3",
        "visual_assets_materialized_in_far3",
        "pdf_materialized_in_far3",
        "a2_grammar_unlocked",
        "a2_native_task_demand_unlocked",
    ):
        if scope[key] is not False:
            raise U05FAR3Error(f"FAR3_SCOPE_UNLOCKED:{key}")

    far2_contract = far2["materialization_contract"]
    if far2_contract["total_practice_slot_count"] != 1632:
        raise U05FAR3Error("FAR2_TOTAL_SLOT_DRIFT")
    if len(far2["core_grammar_slots"]) != 480:
        raise U05FAR3Error("FAR2_CORE_SLOT_DRIFT")
    if len(far2["ket_adapted_slots"]) != 672:
        raise U05FAR3Error("FAR2_KET_SLOT_DRIFT")
    if len(far2["delayed_dictation_slots"]) != 480:
        raise U05FAR3Error("FAR2_DICTATION_SLOT_DRIFT")
    if len(far2["reader_study_slots"]) != 360:
        raise U05FAR3Error("FAR2_READER_SLOT_DRIFT")

    author = far3["authorship_governance"]
    if author["learner_facing_author_model"] != "GPT-5.6 Sol":
        raise U05FAR3Error("AUTHOR_MODEL_DRIFT")
    if author["learner_facing_semantic_reviewer_model"] != "GPT-5.6 Sol":
        raise U05FAR3Error("REVIEWER_MODEL_DRIFT")
    for key in (
        "python_may_generate_learner_facing_english",
        "python_may_rewrite_paraphrase_or_repair_learner_facing_english",
        "python_may_select_or_invent_distractors",
        "python_may_decide_semantically_correct_answer",
    ):
        if author[key] is not False:
            raise U05FAR3Error(f"PYTHON_CONTENT_AUTHORITY_UNLOCKED:{key}")
    if "ANY_GAP_PARAPHRASE_REORDER_POLARITY_CHANGE_DISTRACTOR_PROMPT_RUBRIC_OR_OPTION_TEXT_IS_NEW_LEARNER_FACING_LANGUAGE_AND_REQUIRES_GPT56_AUTHORSHIP" != author["transformation_rule"]:
        raise U05FAR3Error("TRANSFORMATION_RULE_DRIFT")

    provenance = far3["provenance_modes"]
    expected_modes = {
        "SOURCE_EXACT_REUSE",
        "GPT56_DERIVED_FROM_SOURCE",
        "LEARNER_PERSONAL_RESPONSE",
        "AUDIO_TRANSCRIPT_EXACT",
    }
    if set(provenance) != expected_modes:
        raise U05FAR3Error(f"PROVENANCE_MODE_DRIFT:{sorted(provenance)}")
    if provenance["SOURCE_EXACT_REUSE"]["may_be_mechanically_bound_by_python"] is not True:
        raise U05FAR3Error("SOURCE_EXACT_BINDING_NOT_ALLOWED")
    if provenance["GPT56_DERIVED_FROM_SOURCE"]["may_be_mechanically_bound_by_python"] is not False:
        raise U05FAR3Error("GPT56_DERIVED_TEXT_PYTHON_BINDING_DRIFT")

    item = far3["universal_materialized_item_contract"]
    if not EXPECTED_REVIEW_FIELDS.issubset(set(item["required_review_fields"])):
        raise U05FAR3Error("REQUIRED_REVIEW_FIELDS_INCOMPLETE")
    if item["review_pass_value"] != "PASS":
        raise U05FAR3Error("REVIEW_PASS_VALUE_DRIFT")
    for key in (
        "source_slot_identity_must_be_preserved",
        "stage_must_equal_far2_slot",
        "output_level_must_equal_far2_slot_when_present",
        "practice_set_id_must_equal_far2_slot",
    ):
        if item[key] is not True:
            raise U05FAR3Error(f"FAR2_IDENTITY_BINDING_UNLOCKED:{key}")

    answer = far3["answerability_contract"]
    deterministic = answer["deterministic_response_modes"]
    if deterministic["unique_answer_review_required"] is not True:
        raise U05FAR3Error("UNIQUE_ANSWER_REVIEW_NOT_REQUIRED")
    if deterministic["answer_must_be_resolvable_from_declared_evidence"] is not True:
        raise U05FAR3Error("ANSWER_EVIDENCE_BINDING_NOT_REQUIRED")
    if deterministic["distractor_ambiguity_forbidden"] is not True:
        raise U05FAR3Error("DISTRACTOR_AMBIGUITY_NOT_FORBIDDEN")
    productive = answer["productive_response_modes"]
    if productive["single_exact_answer_forbidden"] is not True:
        raise U05FAR3Error("PRODUCTIVE_SINGLE_EXACT_ANSWER_NOT_FORBIDDEN")
    if productive["rubric_required"] is not True:
        raise U05FAR3Error("PRODUCTIVE_RUBRIC_NOT_REQUIRED")
    if productive["model_response_is_example_not_answer_key"] is not True:
        raise U05FAR3Error("MODEL_RESPONSE_ROLE_DRIFT")

    core = far3["core_grammar_materialization_contract"]
    if core["slot_count"] != 480:
        raise U05FAR3Error("CORE_CONTRACT_SLOT_DRIFT")
    if core["minimum_distinct_archetypes_per_frame"] < 4:
        raise U05FAR3Error("CORE_VARIETY_FLOOR_TOO_LOW")
    if float(core["maximum_single_archetype_share_per_frame"]) > 0.5:
        raise U05FAR3Error("CORE_SINGLE_ARCHETYPE_SHARE_TOO_HIGH")
    if len(core["allowed_practice_archetypes"]) < 6:
        raise U05FAR3Error("CORE_ARCHETYPE_SET_INCOMPLETE")
    if core["derived_gaps_or_changes_require_gpt56"] is not True:
        raise U05FAR3Error("CORE_DERIVATION_GPT56_NOT_REQUIRED")

    ket = far3["ket_adapted_materialization_contract"]
    if ket["family_count"] != 14 or ket["slots_per_family"] != 48 or ket["total_slot_count"] != 672:
        raise U05FAR3Error("KET_CONTRACT_DENOMINATOR_DRIFT")
    if ket["ket_native_item_copying_allowed"] is not False:
        raise U05FAR3Error("KET_NATIVE_ITEM_COPYING_UNLOCKED")
    if ket["native_a2_answer_shape_is_reference_only"] is not True:
        raise U05FAR3Error("A2_NATIVE_SHAPE_PROMOTED")

    profiles = list(s2["task_profiles"])
    family_contracts = list(ket["task_family_contracts"])
    if len(family_contracts) != 14:
        raise U05FAR3Error("KET_FAMILY_CONTRACT_COUNT_DRIFT")
    if [row["ket_profile_id"] for row in family_contracts] != [row["id"] for row in profiles]:
        raise U05FAR3Error("KET_PROFILE_ORDER_DRIFT")
    if [row["task_family"] for row in family_contracts] != [row["task_family"] for row in profiles]:
        raise U05FAR3Error("KET_TASK_FAMILY_ORDER_DRIFT")

    adaptation = s9["level_adaptation_policy"]
    if adaptation["adaptation_rule"] != "PRESERVE_S3_MECHANIC_REDUCE_RESPONSE_DEMAND":
        raise U05FAR3Error("S9_ADAPTATION_RULE_DRIFT")
    if adaptation["adapted_output_origin_must_be_a1fs_derived"] is not True:
        raise U05FAR3Error("S9_A1FS_DERIVED_ORIGIN_DRIFT")
    if adaptation["adapted_output_must_not_be_promoted_to_current_ket_canonical"] is not True:
        raise U05FAR3Error("S9_CANONICAL_PROMOTION_GUARD_DRIFT")

    for source, row in zip(profiles, family_contracts):
        if row["adaptation_level"] != "A1":
            raise U05FAR3Error(f"KET_A1_LEVEL_DRIFT:{row['task_family']}")
        if row["adaptation_rule"] != adaptation["adaptation_rule"]:
            raise U05FAR3Error(f"KET_ADAPTATION_RULE_DRIFT:{row['task_family']}")
        for key in (
            "preserve_response_mode",
            "preserve_task_family",
            "preserve_stimulus_modality",
            "preserve_assessment_capability",
        ):
            if row[key] is not True:
                raise U05FAR3Error(f"KET_MECHANIC_NOT_PRESERVED:{row['task_family']}:{key}")
        if row["source_origin_class"] != "A1FS_DERIVED_FROM_READER360_NOT_CURRENT_KET_CANONICAL":
            raise U05FAR3Error(f"KET_ORIGIN_CLASS_DRIFT:{row['task_family']}")
        if row["response_mode"] != source["response_mode"]:
            raise U05FAR3Error(f"KET_RESPONSE_MODE_DRIFT:{row['task_family']}")
        if row["assessment_capability"] != source["assessment_capability"]:
            raise U05FAR3Error(f"KET_CAPABILITY_DRIFT:{row['task_family']}")
        if not str(row["materialization_mode"]).strip():
            raise U05FAR3Error(f"KET_MATERIALIZATION_MODE_EMPTY:{row['task_family']}")
        if not str(row["answer_mode"]).strip():
            raise U05FAR3Error(f"KET_ANSWER_MODE_EMPTY:{row['task_family']}")
        if not list(row["source_modes"]):
            raise U05FAR3Error(f"KET_SOURCE_MODE_EMPTY:{row['task_family']}")

    far2_family_counts = Counter(row["task_family"] for row in far2["ket_adapted_slots"])
    if set(far2_family_counts.values()) != {48}:
        raise U05FAR3Error(f"FAR2_KET_FAMILY_COUNT_DRIFT:{dict(far2_family_counts)}")
    if set(far2_family_counts) != {row["task_family"] for row in family_contracts}:
        raise U05FAR3Error("FAR2_FAR3_KET_FAMILY_SET_DRIFT")

    audio = far3["asset_precondition_contract"]
    if set(audio["audio_required_families"]) != EXPECTED_AUDIO_FAMILIES:
        raise U05FAR3Error("AUDIO_REQUIRED_FAMILY_SET_DRIFT")
    if set(audio["visual_required_families"]) != EXPECTED_VISUAL_FAMILIES:
        raise U05FAR3Error("VISUAL_REQUIRED_FAMILY_SET_DRIFT")
    if audio["executable_practice_may_not_be_admitted_before_required_asset_binding"] is not True:
        raise U05FAR3Error("ASSET_PRECONDITION_NOT_REQUIRED")
    if audio["no_visual_asset_generation_in_far3"] is not True or audio["no_audio_asset_generation_in_far3"] is not True:
        raise U05FAR3Error("FAR3_ASSET_GENERATION_UNLOCKED")

    dictation = far3["delayed_dictation_materialization_contract"]
    if dictation["slot_count"] != 480 or dictation["d1_slot_count"] != 360 or dictation["d2_slot_count"] != 120:
        raise U05FAR3Error("DICTATION_CONTRACT_DENOMINATOR_DRIFT")
    if dictation["transcript_source_must_be_exact_spoken360_segment"] is not True:
        raise U05FAR3Error("DICTATION_SOURCE_EXACT_NOT_REQUIRED")
    if dictation["transcript_hidden_during_attempt"] is not True:
        raise U05FAR3Error("DICTATION_TRANSCRIPT_NOT_HIDDEN")
    if dictation["segment_selection_requires_gpt56_review"] is not True:
        raise U05FAR3Error("DICTATION_SEGMENT_GPT56_REVIEW_NOT_REQUIRED")
    if dictation["audio_generation_or_recording_is_separate_scope"] is not True:
        raise U05FAR3Error("DICTATION_AUDIO_SCOPE_DRIFT")

    duplicate = far3["duplicate_and_retention_policy"]
    if duplicate["non_retention_exact_visible_item_duplicate_forbidden"] is not True:
        raise U05FAR3Error("NONRETENTION_DUPLICATE_NOT_FORBIDDEN")
    if duplicate["delayed_retention_may_repeat_prior_target"] is not True:
        raise U05FAR3Error("RETENTION_REPEAT_NOT_ALLOWED")
    if duplicate["repeated_event_counts_as_spaced_retrieval_not_new_unique_question"] is not True:
        raise U05FAR3Error("SPACED_RETRIEVAL_ACCOUNTING_DRIFT")

    artifact = far3["production_artifact_policy"]
    if artifact["one_file_per_practice_set_forbidden"] is not True:
        raise U05FAR3Error("ONE_FILE_PER_SET_NOT_FORBIDDEN")
    if artifact["planning_review_sync_preview_docs_forbidden"] is not True:
        raise U05FAR3Error("ARTIFACT_PROLIFERATION_GUARD_DRIFT")
    if set(artifact["preferred_final_authority_files"]) != EXPECTED_FINAL_FILES:
        raise U05FAR3Error("FINAL_AUTHORITY_FILE_SET_DRIFT")
    if artifact["max_final_learner_facing_json_authority_files"] != 3:
        raise U05FAR3Error("FINAL_AUTHORITY_FILE_CAP_DRIFT")
    if artifact["temporary_generation_shards_may_exist_only_on_work_branch_and_must_consolidate_before_closeout"] is not True:
        raise U05FAR3Error("TEMP_SHARD_CLOSEOUT_GUARD_DRIFT")

    gates = far3["admission_gates"]
    for key, value in gates.items():
        if value is not True:
            raise U05FAR3Error(f"ADMISSION_GATE_NOT_LOCKED:{key}")

    safety = far3["scope_safety"]
    for key, value in safety.items():
        if value is not False:
            raise U05FAR3Error(f"SCOPE_SAFETY_DRIFT:{key}")

    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "practice_slot_denominator": 1632,
        "core_grammar_slot_count": 480,
        "ket_family_contract_count": len(family_contracts),
        "ket_adapted_slot_count": 672,
        "dictation_slot_count": 480,
        "reader_study_slot_count": 360,
        "audio_required_family_count": len(EXPECTED_AUDIO_FAMILIES),
        "visual_required_family_count": len(EXPECTED_VISUAL_FAMILIES),
        "required_gpt56_review_field_count": len(EXPECTED_REVIEW_FIELDS),
        "final_learner_facing_authority_file_cap": 3,
        "learner_facing_items_materialized": False,
        "python_learner_facing_authoring_allowed": False,
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    print(json.dumps(build_report(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
