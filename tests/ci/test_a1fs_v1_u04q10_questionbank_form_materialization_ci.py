from collections import Counter

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u04q10_questionbank_form_materialization as builder
from ulga.validators import validate_a1fs_v1_u04q10_questionbank_form_materialization as validator


def test_u04_q10_materializes_exact_twenty_by_forty_questionbank_and_forms():
    payload = builder.build_export_payload()
    report = validator.validate_payload(payload)
    assert report["status"] == "PASS"
    assert len(payload["questionbank_items"]) == 800
    assert len(payload["forms"]) == 20
    assert len(payload["runtime_bindings"]) == 800
    assert payload["materialization_contract"]["section_counts_per_form"] == {"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}
    for form in payload["forms"]:
        assert form["question_count"] == 40
        assert form["section_counts"] == {"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}


def test_u04_q10_covers_all_task_families_relations_and_communicative_functions():
    payload = builder.build_export_payload()
    items = payload["questionbank_items"]
    assert {row["task_family_id"] for row in items} == set(builder._families())
    assert {row["relation_surface"] for row in items} == set(builder.TARGET_RELATIONS)
    q08_ids = {row["function_id"] for row in builder._sources()["q08"]["communicative_functions"]}
    assert len(q08_ids) == 6
    assert {row["communicative_function_id"] for row in items} == q08_ids
    assert payload["coverage"]["task_family_coverage"] == "10/10"
    assert payload["coverage"]["target_relation_coverage"] == "8/8"
    assert payload["coverage"]["communicative_function_coverage"] == "6/6"
    assert all(payload["coverage"]["target_relation_counts"][relation] > 0 for relation in builder.TARGET_RELATIONS)


def test_u04_q10_at_is_text_bound_only_with_zero_scene_refs_and_zero_fabrication():
    payload = builder.build_export_payload()
    repair = builder._sources()["repair"]
    admitted = {row["sentence_id"] for row in repair["at_text_bound_admitted_sentence_evidence"]}
    at_rows = [row for row in payload["questionbank_items"] if row["relation_surface"] == "at"]
    assert len(at_rows) == 40
    assert {row["task_family_id"] for row in at_rows}.issubset(builder.AT_ALLOWED_FAMILIES)
    assert {row["communicative_function_id"] for row in at_rows} == {builder.AT_CF}
    assert {row["evidence_mode"] for row in at_rows} == {"PRIOR_ADMITTED_TEXT_BOUND_POINT_PLACE_EVIDENCE"}
    assert all(row["scene_ref_id"] is None and row["source_scene_ref"] is None for row in at_rows)
    assert all(row["source_sentence_id"] in admitted for row in at_rows)
    assert all(not row["options"] for row in at_rows)
    assert payload["coverage"]["at_scene_ref_count"] == 0
    assert payload["coverage"]["fabricated_scene_ref_count"] == 0
    assert payload["repair_enforcement"]["fabricated_scene_ref_count"] == 0


def test_u04_q10_reuse_and_q07_scene_evidence_resolve_exact_authority_rows():
    payload = builder.build_export_payload()
    src = builder._sources()
    reuse_pairs = {
        (row["sentence_id"], row["relation_surface"], scene_ref)
        for row in src["repair"]["resolved_existing_sentence_scene_evidence"]
        for scene_ref in row["source_scene_refs"]
    }
    q07_pairs = {
        (row["bound_sentence_id"], row["relation_surface"], row["scene_ref_id"])
        for row in src["q07"]["micro_scenes"]
        if row["relation_surface"] in builder.NEW_RELATIONS
    }
    for row in payload["questionbank_items"]:
        relation = row["relation_surface"]
        if relation in builder.REUSE_RELATIONS:
            assert (row["source_sentence_id"], relation, row["scene_ref_id"]) in reuse_pairs
        elif relation in builder.NEW_RELATIONS:
            assert (row["source_sentence_id"], relation, row["scene_ref_id"]) in q07_pairs
            if relation == "between":
                assert len(row["reference_landmarks"]) == 2
                assert len(set(row["reference_landmarks"])) == 2


def test_u04_q10_proves_distinct_capacity_and_policy_bound_admission():
    payload = builder.build_export_payload()
    assert len({row["item_id"] for row in payload["questionbank_items"]}) == 800
    assert len({row["semantic_signature"] for row in payload["questionbank_items"]}) == 800
    assert payload["coverage"]["exact_semantic_duplicate_count"] == 0
    assert len({row["slot_id"] for row in payload["runtime_bindings"]}) == 800
    assert len({row["selected_item_id"] for row in payload["runtime_bindings"]}) == 800
    assert all(len(row["candidate_ids"]) == 3 and len(set(row["candidate_ids"])) == 3 for row in payload["runtime_bindings"])
    candidate = builder.build_candidate()
    assert candidate["artifact_role"] == policy_artifact.CANDIDATE_ROLE
    receipt = validator.validate_candidate(candidate)
    assert receipt["status"] == "PASS"
    approved = builder.admit_candidate(candidate)
    assert approved["artifact_role"] == policy_artifact.APPROVED_ROLE
    assert approved["admission"]["status"] == "APPROVED"


def test_u04_q10_progression_and_scope_boundaries_remain_locked():
    payload = builder.build_export_payload()
    forms = payload["forms"]
    assert Counter(form["progression_role"] for form in forms) == Counter({
        "GUIDED": 4,
        "REDUCED_SUPPORT": 4,
        "INDEPENDENT": 4,
        "TRANSFER": 4,
        "RETENTION": 4,
    })
    assert all(value is False for value in payload["boundaries"].values())
    assert payload["coverage"]["support_relation_item_count"] == 0
    assert payload["next_short_step"] == builder.NEXT_SHORT_STEP
