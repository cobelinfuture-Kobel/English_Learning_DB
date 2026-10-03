from collections import Counter

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u06q10_questionbank_form_materialization as builder
from ulga.validators import validate_a1fs_v1_u06q10_questionbank_form_materialization as validator

def payload():
    return builder.build_export_payload()

def test_u06_q10_materializes_coverage_driven_300_item_10_form_questionbank():
    p=payload()
    r=validator.validate_payload(p)
    assert r["status"]=="PASS"
    assert len(p["questionbank_items"])==300
    assert len(p["forms"])==10
    assert p["materialization_contract"]["capacity_policy"]=="COVERAGE_DRIVEN_NOT_FIXED_BY_LEGACY_20X40"
    assert p["materialization_contract"]["questions_per_form"]==30
    assert p["materialization_contract"]["section_counts_per_form"]=={"A":6,"B":6,"C":8,"D":4,"E":6}
    for form in p["forms"]:
        assert form["question_count"]==30
        assert form["section_counts"]=={"A":6,"B":6,"C":8,"D":4,"E":6}

def test_u06_q10_uses_all_129_q06_sentences_and_all_17_q07_scenes():
    p=payload(); items=p["questionbank_items"]; src=builder._sources()
    q06_ids={x["sentence_id"] for x in builder._q06_rows(src)}
    canonical=[x for x in items if x["source_route"]=="Q06_CANONICAL_SENTENCE"]
    assert len(canonical)==129
    assert {x["q06_sentence_id"] for x in canonical}==q06_ids
    assert p["coverage"]["q06_sentence_materialized_coverage"]=="129/129"
    assert p["coverage"]["q06_context_required_sentence_materialized_coverage"]=="49/49"
    assert p["coverage"]["q06_standalone_sentence_materialized_coverage"]=="80/80"
    assert p["coverage"]["q07_scene_materialized_coverage"]=="17/17"

def test_u06_q10_covers_all_182_chunks_and_all_62_q07r1_source_verbs():
    p=payload(); items=p["questionbank_items"]; src=builder._sources()
    expected={x["normalized_surface"] for x in builder._chunk_inventory(src)}
    bound={x["functional_chunk_binding"] for x in items if x["functional_chunk_binding"]}
    assert bound==expected
    assert p["coverage"]["q07r1_functional_chunk_binding_coverage"]=="182/182"
    assert p["coverage"]["q07r1_source_verb_binding_coverage"]=="62/62"
    assert len([x for x in items if x["source_route"]=="Q07R1_CHUNK_CONTROLLED_REALIZATION"])==171
    assert p["coverage"]["source_route_counts"]=={"Q06_CANONICAL_SENTENCE":129,"Q07R1_CHUNK_CONTROLLED_REALIZATION":171}

def test_u06_q10_never_realizes_deferred_go_study_chunks_as_item_local_sentences():
    p=payload()
    restricted=[
        x for x in p["questionbank_items"]
        if x["functional_chunk_binding"] in {"can go to school","can study at school"}
    ]
    assert restricted
    assert all(x["task_family_id"] in {"U06-TF03_ABILITY_MEANING_DISCRIMINATION","U06-TF04_FUNCTIONAL_CHUNK_TO_ACTION_OR_SCENE"} for x in restricted)
    assert all(x["item_local_sentence_realization"] is False for x in restricted)
    assert p["coverage"]["restricted_deferred_chunk_sentence_realization_count"]==0

def test_u06_q10_task_family_function_frame_and_progression_coverage():
    p=payload(); items=p["questionbank_items"]
    assert len({x["task_family_id"] for x in items})==10
    assert len({x["communicative_function_id"] for x in items})==6
    assert {x["frame_id"] for x in items}=={"U06-CF-ABILITY-INTRANSITIVE","U06-CF-ABILITY-OBJECT","U06-CF-ABILITY-PREDICATE-TAIL"}
    assert p["coverage"]["task_family_coverage"]=="10/10"
    assert p["coverage"]["communicative_function_coverage"]=="6/6"
    assert p["coverage"]["frame_coverage"]=="3/3"
    assert Counter(x["progression_role"] for x in p["forms"])==Counter({"GUIDED":2,"REDUCED_SUPPORT":2,"INDEPENDENT":2,"TRANSFER":2,"RETENTION":2})

def test_u06_q10_item_local_sentences_are_not_promoted_to_sentence_authority():
    p=payload(); rows=[x for x in p["questionbank_items"] if x["item_local_sentence_realization"]]
    assert rows
    assert all(x["item_local_sentence_promoted_to_canonical_asset"] is False for x in rows)
    assert p["coverage"]["item_local_sentence_promoted_to_canonical_asset_count"]==0
    assert p["coverage"]["new_global_sentence_identity_count"]==0
    assert p["materialization_contract"]["item_local_sentence_realization_promoted_to_sentence_authority"] is False

def test_u06_q10_selected_response_items_have_one_exact_scored_answer():
    p=payload()
    for item in p["questionbank_items"]:
        if not item["options"]:
            continue
        assert len(item["options"])==len(set(item["options"]))
        assert item["correct_answer"] in item["options"]
        assert item["response_contract"]["single_answer_required"] is True

def test_u06_q10_policy_bound_admission_and_scope_boundaries():
    p=payload()
    candidate=builder.build_candidate()
    assert candidate["artifact_role"]==policy_artifact.CANDIDATE_ROLE
    receipt=validator.validate_candidate(candidate)
    assert receipt["status"]=="PASS"
    approved=builder.admit_candidate(candidate)
    assert approved["artifact_role"]==policy_artifact.APPROVED_ROLE
    assert approved["admission"]["status"]=="APPROVED"
    assert all(v is False for v in p["boundaries"].values())
    assert p["next_short_step"]==builder.NEXT_SHORT_STEP
