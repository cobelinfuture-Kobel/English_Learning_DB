from __future__ import annotations
from copy import deepcopy
import pytest
from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as contract_builder
from ulga.builders import build_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_unit02_handoff as b
from ulga.validators import validate_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_unit02_handoff as v

def candidate(source,semantic,kind,text,nouns,adjs=()):
    return {"source_record_id":source,"semantic_identity":semantic,"source_level":"B","source_type":"page_unit","text_excerpt":text,"selection_class":kind,"selection_reasons":["FIXTURE"],"structural_flags":[],"matched_sentence_frame_ids":[],"direct_task_candidate_roles":["READING_TASK_CANDIDATE","WRITING_TASK_CANDIDATE","SPEAKING_TASK_CANDIDATE"],"active_noun_hits":list(nouns),"active_adjective_hits":list(adjs),"direct_noun_phrases":[f"a {nouns[0]}"],"adjective_noun_phrases":[f"a {adjs[0]} {nouns[0]}"] if adjs else [],"very_adjective_noun_phrases":[],"source_skill_eligibility":[],"canonical_admission":False,"human_review_required":True}

def report():
    return {"schema_version":b.upstream.SCHEMA_VERSION,"task_id":b.upstream.TASK_ID,"status":b.upstream.PASS_STATUS,"scope":{"allowed_units":[b.UNIT_ID],"canonical_promotion":False,"a2_status":"LOCKED"},"selected_candidates":[candidate("SRC-MS","SEM-MS","CONTEXT_SOURCE","The cat sits by a box.",["cat","box"],["small"]),candidate("SRC-SP","SEM-SP","CONTROLLED_PRACTICE_SOURCE","A book is on a desk.",["book","desk"],["red"]),candidate("SRC-DLG","SEM-DLG","DIRECT_MODEL","This is a bag.",["bag"],["blue"]),candidate("SRC-X","SEM-X","REJECT",'"Do not eat the tree!',["tree"])]}

def checks(): return {k:"PASS" for k in b.REVIEW_DIMENSIONS}
def scene(setting,participants,objects,actions,info,functions): return {"setting":setting,"participants":participants,"objects":objects,"actions":actions,"information_structure":info,"communicative_function_ids":functions}
def decisions():
    common={"review_status":"APPROVED","decision_ref":b.DECISION_REF,"adaptation_mode":"PROJECT_AUTHORED_REWRITE","adaptation_reason_codes":["RAZ_GROUNDED_A1_REWRITE"],"review_dimensions":checks(),"template_only":False,"rejection_reason_codes":[]}
    return {"decisions":[
        {**common,"source_record_id":"SRC-MS","semantic_identity":"SEM-MS","content_kind":"MICRO_SCENE","title":"A cat in a pet shop","adapted_sentences":["A girl is in a pet shop.","She sees a small cat.","The cat is in a box."],"dialogue_turns":[],"scene_profile":scene("PET_SHOP",["GIRL"],["CAT","BOX"],["SEE","LOCATE"],["FIRST_MENTION","KNOWN_REFERENCE"],["IDENTIFY","LOCATE"]),"adjacency_pair_types":[],"theme_id":"ANIMALS","situation_family_id":"SHOPPING","micro_situation_id":"PET_SHOP_CAT"},
        {**common,"source_record_id":"SRC-SP","semantic_identity":"SEM-SP","content_kind":"SHORT_PASSAGE","title":"A red book","adapted_sentences":["Mia has a red book.","The book is on a desk.","She puts the book in a bag."],"dialogue_turns":[],"scene_profile":scene("CLASSROOM",["MIA"],["BOOK","DESK","BAG"],["HAVE","PUT"],["FIRST_MENTION","KNOWN_REFERENCE"],["DESCRIBE","LOCATE"]),"adjacency_pair_types":[],"theme_id":"SCHOOL","situation_family_id":"CLASSROOM","micro_situation_id":"BOOK_ON_DESK"},
        {**common,"source_record_id":"SRC-DLG","semantic_identity":"SEM-DLG","content_kind":"SHORT_DIALOGUE","title":"A bag in the classroom","adapted_sentences":[],"dialogue_turns":[{"speaker_id":"TEACHER","utterance":"What is in the classroom?"},{"speaker_id":"CHILD","utterance":"I can see a blue bag."},{"speaker_id":"TEACHER","utterance":"Where is the bag?"},{"speaker_id":"CHILD","utterance":"The bag is near the door."}],"scene_profile":scene("CLASSROOM",["TEACHER","CHILD"],["BAG","DOOR"],["SEE","LOCATE"],["QUESTION_ANSWER","KNOWN_REFERENCE"],["ASK","ANSWER","LOCATE"]),"adjacency_pair_types":["QUESTION_ANSWER"],"theme_id":"SCHOOL","situation_family_id":"CLASSROOM_DIALOGUE","micro_situation_id":"FIND_THE_BAG"},
    ]}

def build(): return b.build_admission(report(),decisions(),contract_builder.build_contract())

def test_builds_shared_three_skill_content_and_unit02_handoff():
    private,safe=build(); c=private["coverage_readback"]
    assert c["approved_content_asset_count"]==3 and c["three_skill_shared_content_count"]==3
    assert c["distinct_micro_scene_count"]==c["distinct_short_passage_count"]==c["distinct_dialogue_count"]==1
    assert all({p["skill"] for p in a["skill_projections"]}==set(b.SKILLS) for a in private["content_assets"])
    assert all("content" not in a for a in safe["content_assets"])
    assert all(a["unit02_reusable_handoff"]["binding_status"]=="AVAILABLE_NOT_BOUND" and a["later_unit_reuse"]["copy_on_reuse"] is False for a in private["content_assets"])

def test_records_all_handshake_findings():
    private,_=build()
    assert {x["finding_code"] for x in private["inspection_record"]["findings"]}=={code for code,_ in b.FINDINGS}

def test_dialogue_and_raw_copy_fail_closed():
    d=decisions(); d["decisions"][2]["dialogue_turns"]=[{"speaker_id":"CHILD","utterance":"I see a bag."},{"speaker_id":"CHILD","utterance":"The bag is blue."}]
    with pytest.raises(b.AdmissionBuildError,match="SHORT_DIALOGUE_STRUCTURE_INVALID"): b.build_admission(report(),d,contract_builder.build_contract())
    d=decisions(); d["decisions"][0]["adapted_sentences"]=["The cat sits by a box."]
    with pytest.raises(b.AdmissionBuildError,match="RAW_RAZ_TEXT_COPY"): b.build_admission(report(),d,contract_builder.build_contract())

def test_incomplete_decisions_and_parallel_bank_drift_fail_closed():
    d=decisions(); d["decisions"].pop()
    with pytest.raises(b.AdmissionBuildError,match="COMPLETE_REVIEWABLE"): b.build_admission(report(),d,contract_builder.build_contract())
    private,safe=build(); result=v.validate_package(private,safe)
    assert result["validation_status"]==v.PASS_STATUS and result["content_kind_counts"]=={"MICRO_SCENE":1,"SHORT_PASSAGE":1,"SHORT_DIALOGUE":1}
    drift=deepcopy(private); drift["boundaries"]["parallel_question_bank_created"]=True; drift["package_sha256"]=b.digest({k:x for k,x in drift.items() if k!="package_sha256"})
    with pytest.raises(v.AdmissionValidationError,match="authority_boundary_invalid"): v.validate_package(drift,safe)
