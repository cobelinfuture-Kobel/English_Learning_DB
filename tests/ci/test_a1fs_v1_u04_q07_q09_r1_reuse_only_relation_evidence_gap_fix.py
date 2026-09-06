import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
Q03 = ROOT / "ulga/contracts/a1fs_v1_u04_q03_place_relation_form_meaning_authority.json"
Q06 = ROOT / "ulga/contracts/a1fs_v1_u04_q06_sentence_assets.json"
Q07 = ROOT / "ulga/contracts/a1fs_v1_u04_q07_life_skill_micro_scenes.json"
Q09 = ROOT / "ulga/contracts/a1fs_v1_u04_q09_task_pedagogical_contract.json"
REPAIR = ROOT / "ulga/contracts/a1fs_v1_u04_q07_q09_r1_reuse_only_relation_evidence_gap_fix.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_u04_q07_q09_r1_audits_raw_supply_vs_resolved_scene_pairs():
    q06 = load(Q06)
    q07 = load(Q07)
    repair = load(REPAIR)

    assert repair["status"] == "PASS_Q07_Q09_R1_REUSE_ONLY_AT_RELATION_EVIDENCE_GAP_FULL_FIX"
    assert repair["audit"] == {
        "raw_predicative_reuse_supply_count": 37,
        "raw_predicative_reuse_counts": {"in": 14, "near": 14, "on": 3, "at": 6},
        "existing_sentence_scene_pair_capable_sentence_count": 19,
        "existing_sentence_scene_pair_capable_counts": {"in": 8, "near": 8, "on": 3},
        "raw_without_scene_ref_count": 18,
        "raw_without_scene_ref_counts": {"near": 6, "at": 6, "in": 6},
        "at_existing_sentence_scene_pair_count": 0,
        "at_text_bound_admitted_sentence_count": 6,
        "fabricated_scene_ref_count": 0,
    }

    assert q06["reuse_supply"]["unit03_raw_predicative_place_relation_reuse_counts"] == repair["audit"]["raw_predicative_reuse_counts"]
    assert {
        relation: row["prior_unit03_sentence_supply"]
        for relation, row in q07["prior_relation_scene_reuse"]["relations"].items()
    } == repair["audit"]["raw_predicative_reuse_counts"]
    assert q07["prior_relation_scene_reuse"]["fabricated_prior_scene_ref_count"] == 0


def test_u04_q07_q09_r1_resolves_only_real_scene_bound_in_near_on_evidence():
    repair = load(REPAIR)
    rows = repair["resolved_existing_sentence_scene_evidence"]

    assert len(rows) == 19
    assert len({row["sentence_id"] for row in rows}) == 19
    assert Counter(row["relation_surface"] for row in rows) == {"in": 8, "near": 8, "on": 3}
    assert all(row["source_scene_refs"] for row in rows)
    assert all(row["relation_surface"] != "at" for row in rows)
    assert all(all(ref.startswith("U01-") for ref in row["source_scene_refs"]) for row in rows)


def test_u04_q07_q09_r1_at_uses_six_admitted_text_bound_point_place_sentences():
    q03 = load(Q03)
    repair = load(REPAIR)
    at_relation = next(row for row in q03["relations"] if row["surface"] == "at")
    rows = repair["at_text_bound_admitted_sentence_evidence"]

    assert at_relation["relation_id"] == "U04-REL-AT-POINT-PLACE"
    assert "point or general location" in at_relation["meaning"]
    assert "without asserting exact interior or surface geometry" in at_relation["meaning"]
    assert q03["semantic_overlap_and_answerability_policy"]["at_in_viewpoint_overlap"]["classification"] == "VIEWPOINT_DEPENDENT_OVERLAP"

    assert len(rows) == 6
    assert len({row["sentence_id"] for row in rows}) == 6
    assert {row["subject_pronoun"] for row in rows} == {"i", "you", "he", "she", "we", "they"}
    assert all(row["relation_surface"] == "at" for row in rows)
    assert all(row["normalized_text"].endswith("at the park") for row in rows)


def test_u04_q07_q09_r1_supersedes_only_the_overbroad_at_scene_pair_requirement():
    q09 = load(Q09)
    repair = load(REPAIR)
    contract = repair["repair_contract"]

    assert q09["scope"]["reuse_only_target_relations"] == ["in", "near", "on", "at"]
    assert contract["scene_bound_reuse_relations"] == ["in", "near", "on"]
    assert contract["at_evidence_mode"] == "PRIOR_ADMITTED_TEXT_BOUND_POINT_PLACE_EVIDENCE"
    assert contract["at_scene_bound_item_allowed"] is False
    assert contract["at_picture_relation_selection_allowed"] is False
    assert contract["at_in_forced_single_answer_contrast_allowed"] is False
    assert contract["unresolved_in_near_raw_sentences_fail_closed"] is True
    assert contract["new_global_scene_identity_count"] == 0
    assert contract["new_sentence_identity_count"] == 0
    assert contract["new_relation_identity_count"] == 0
    assert contract["q03_target_relation_count_remains"] == 8
    assert contract["a2_unlocked"] is False


def test_u04_q07_q09_r1_at_routes_only_to_non_scene_non_single_answer_task_families():
    q09 = load(Q09)
    repair = load(REPAIR)
    by_id = {row["task_family_id"]: row for row in q09["task_families"]}
    allowed = repair["repair_contract"]["at_allowed_task_family_ids"]

    assert allowed == ["U04-TF04_PLACE_PHRASE_CONSTRUCTION", "U04-TF09_PRODUCTIVE_RESPONSE"]
    assert all(task_id in by_id for task_id in allowed)
    assert all(by_id[task_id]["single_answer_possible"] is False for task_id in allowed)
    assert q09["answerability_and_distractor_contract"]["at_in_may_not_be_forced_as_mutually_exclusive_when_both_viewpoints_are_natural"] is True


def test_u04_q07_q09_r1_q10_consumer_contract_and_boundaries():
    repair = load(REPAIR)
    q10 = repair["q10_consumer_requirements"]

    assert q10["must_load_this_repair_after_q07_and_q09"] is True
    assert q10["all_eight_q03_target_relations_still_require_nonzero_materialized_coverage"] is True
    assert q10["at_coverage_must_reference_one_of_at_text_bound_admitted_sentence_evidence"] is True
    assert q10["at_coverage_may_not_claim_scene_bound_evidence"] is True
    assert q10["in_near_on_scene_bound_items_must_reference_resolved_existing_sentence_scene_evidence"] is True
    assert q10["inside_under_behind_between_scene_bound_items_continue_to_use_q07_unit04_scene_ids"] is True
    assert q10["support_relations_next_to_in_front_of_remain_non_target_support"] is True

    assert repair["boundaries"] == {
        "q10_questionbank_materialized": False,
        "q10_forms_materialized": False,
        "q07_micro_scene_rows_modified": False,
        "q09_task_family_inventory_modified": False,
        "motion_directional_from_into_to_activated": False,
        "a2_unlocked": False,
    }
    assert repair["next_short_step"] == "A1FS-V1-U04Q10_Unit04QuestionBankAndFormMaterialization"
