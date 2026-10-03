from __future__ import annotations
from collections import Counter
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u06q10_questionbank_form_materialization as builder

VALIDATOR_ID="validate_a1fs_v1_u06q10_questionbank_form_materialization_v1"

def require(cond: bool, message: str) -> None:
    if not cond:
        raise ValueError(message)

def _validate_counts(payload: Mapping[str, Any], items: list[Mapping[str, Any]]) -> None:
    require(payload.get("status")==builder.PASS_STATUS,"STATUS_INVALID")
    require(len(items)==300,"QUESTIONBANK_ITEM_COUNT_INVALID")
    require(len({str(x["item_id"]) for x in items})==300,"ITEM_ID_COLLISION")
    require(len(payload.get("forms") or [])==10,"FORM_COUNT_INVALID")
    require(payload["materialization_contract"]["capacity_policy"]=="COVERAGE_DRIVEN_NOT_FIXED_BY_LEGACY_20X40","CAPACITY_POLICY_INVALID")
    require(payload["materialization_contract"]["questions_per_form"]==30,"QUESTIONS_PER_FORM_INVALID")
    require(payload["materialization_contract"]["total_items"]==300,"TOTAL_ITEMS_INVALID")

def _validate_forms(payload: Mapping[str, Any], items: list[Mapping[str, Any]]) -> None:
    by_id={str(x["item_id"]):x for x in items}
    expected_sections={"A":6,"B":6,"C":8,"D":4,"E":6}
    progression=Counter()
    seen=[]
    for form in payload["forms"]:
        require(form["question_count"]==30,f"FORM_QUESTION_COUNT_INVALID:{form['form_id']}")
        require(form["section_counts"]==expected_sections,f"FORM_SECTION_COUNTS_INVALID:{form['form_id']}")
        ids=list(form["item_ids"])
        require(len(ids)==30 and len(set(ids))==30,f"FORM_ITEM_ID_INVALID:{form['form_id']}")
        require(all(i in by_id for i in ids),f"FORM_ITEM_NOT_IN_BANK:{form['form_id']}")
        seen.extend(ids)
        progression[str(form["progression_role"])]+=1
    require(len(seen)==300 and len(set(seen))==300,"FORM_ITEM_BANK_ALIGNMENT_INVALID")
    require(progression==Counter({"GUIDED":2,"REDUCED_SUPPORT":2,"INDEPENDENT":2,"TRANSFER":2,"RETENTION":2}),"PROGRESSION_DISTRIBUTION_INVALID")

def _validate_authority_coverage(payload: Mapping[str, Any], items: list[Mapping[str, Any]]) -> None:
    src=builder._sources()
    expected_families={x["task_family_id"] for x in src["q09"]["task_families"]}
    expected_functions={x["function_id"] for x in src["q08"]["communicative_functions"]}
    actual_families={x["task_family_id"] for x in items}
    actual_functions={x["communicative_function_id"] for x in items}
    actual_frames={x["frame_id"] for x in items}
    require(actual_families==expected_families,"TASK_FAMILY_COVERAGE_INVALID")
    require(actual_functions==expected_functions,"FUNCTION_COVERAGE_INVALID")
    require(actual_frames=={"U06-CF-ABILITY-INTRANSITIVE","U06-CF-ABILITY-OBJECT","U06-CF-ABILITY-PREDICATE-TAIL"},"FRAME_COVERAGE_INVALID")
    coverage=payload["coverage"]
    require(coverage["task_family_coverage"]=="10/10","TASK_FAMILY_REPORT_INVALID")
    require(coverage["communicative_function_coverage"]=="6/6","FUNCTION_REPORT_INVALID")
    require(coverage["frame_coverage"]=="3/3","FRAME_REPORT_INVALID")

def _validate_q06_coverage(payload: Mapping[str, Any], items: list[Mapping[str, Any]]) -> None:
    src=builder._sources()
    q06={str(x["sentence_id"]):x for x in builder._q06_rows(src)}
    canonical=[x for x in items if x["source_route"]=="Q06_CANONICAL_SENTENCE"]
    require(len(canonical)==129,"Q06_CANONICAL_ITEM_COUNT_INVALID")
    require({str(x["q06_sentence_id"]) for x in canonical}==set(q06),"Q06_SENTENCE_COVERAGE_INVALID")
    context=[x for x in canonical if x["q06_requires_context_binding"]]
    standalone=[x for x in canonical if not x["q06_requires_context_binding"]]
    require(len(context)==49,"Q06_CONTEXT_COUNT_INVALID")
    require(len(standalone)==80,"Q06_STANDALONE_COUNT_INVALID")
    bindings=builder._binding_map(src)
    scenes=builder._scene_map(src)
    for item in canonical:
        source=q06[str(item["q06_sentence_id"])]
        require(item["frame_id"]==source["frame_id"],f"Q06_FRAME_DRIFT:{item['item_id']}")
        require(item["base_verb"]==source["base_verb"],f"Q06_BASE_VERB_DRIFT:{item['item_id']}")
        if source["requires_context_binding"]:
            require(str(item["q06_sentence_id"]) in bindings,f"Q07_BINDING_MISSING:{item['item_id']}")
            scene_ref=str(bindings[str(item["q06_sentence_id"])]["scene_ref_id"])
            require(item["scene_ref_id"]==scene_ref,f"Q07_SCENE_REF_DRIFT:{item['item_id']}")
            require(scene_ref in scenes,f"Q07_SCENE_NOT_FOUND:{item['item_id']}")
        else:
            require(item["scene_ref_id"] is None,f"STANDALONE_FORCED_SCENE:{item['item_id']}")
    require(payload["coverage"]["q06_sentence_materialized_coverage"]=="129/129","Q06_COVERAGE_REPORT_INVALID")
    require(payload["coverage"]["q06_context_required_sentence_materialized_coverage"]=="49/49","Q06_CONTEXT_REPORT_INVALID")
    require(payload["coverage"]["q06_standalone_sentence_materialized_coverage"]=="80/80","Q06_STANDALONE_REPORT_INVALID")
    require(payload["coverage"]["q07_scene_materialized_coverage"]=="17/17","Q07_SCENE_REPORT_INVALID")

def _validate_chunk_coverage(payload: Mapping[str, Any], items: list[Mapping[str, Any]]) -> None:
    src=builder._sources()
    inv=builder._chunk_inventory(src)
    expected={x["normalized_surface"] for x in inv}
    bound={str(x["functional_chunk_binding"]) for x in items if x.get("functional_chunk_binding")}
    require(bound==expected,"Q07R1_CHUNK_BINDING_COVERAGE_INVALID")
    new_verbs={x["base_verb"] for x in inv if x["q07r1_source_verb_member"]}
    bound_new_verbs={
        str(x["base_verb"])
        for x in items
        if x["source_route"]=="Q07R1_CHUNK_CONTROLLED_REALIZATION" and x.get("q07r1_source_verb_member")
    }
    require(bound_new_verbs==new_verbs and len(bound_new_verbs)==62,"Q07R1_SOURCE_VERB_COVERAGE_INVALID")
    chunk_items=[x for x in items if x["source_route"]=="Q07R1_CHUNK_CONTROLLED_REALIZATION"]
    require(len(chunk_items)==171,"Q07R1_CHUNK_ROUTE_COUNT_INVALID")
    for item in chunk_items:
        require(item["frame_id"]=="U06-CF-ABILITY-PREDICATE-TAIL",f"CHUNK_ROUTE_FRAME_INVALID:{item['item_id']}")
        require(item["item_local_sentence_promoted_to_canonical_asset"] is False,f"ITEM_LOCAL_SENTENCE_PROMOTED:{item['item_id']}")
        if item["functional_chunk_binding"] in builder.RESTRICTED_CHUNK_SENTENCE_SURFACES:
            require(item["task_family_id"] in {"U06-TF03_ABILITY_MEANING_DISCRIMINATION","U06-TF04_FUNCTIONAL_CHUNK_TO_ACTION_OR_SCENE"},f"RESTRICTED_CHUNK_UNSAFE_FAMILY:{item['item_id']}")
            require(item["item_local_sentence_realization"] is False,f"RESTRICTED_CHUNK_SENTENCE_REALIZATION:{item['item_id']}")
        if item["functional_chunk_semantic_admission_class"]=="SCENE_GROUNDED_APPROVE":
            require(item["functional_chunk_scene_grounding"],f"SCENE_GROUNDED_METADATA_MISSING:{item['item_id']}")
    require(payload["coverage"]["q07r1_functional_chunk_binding_coverage"]=="182/182","Q07R1_CHUNK_REPORT_INVALID")
    require(payload["coverage"]["q07r1_source_verb_binding_coverage"]=="62/62","Q07R1_VERB_REPORT_INVALID")
    require(payload["coverage"]["restricted_deferred_chunk_sentence_realization_count"]==0,"RESTRICTED_CHUNK_SENTENCE_REALIZATION_NONZERO")
    require(payload["coverage"]["item_local_sentence_promoted_to_canonical_asset_count"]==0,"ITEM_LOCAL_PROMOTION_NONZERO")

def _validate_answerability(items: list[Mapping[str, Any]]) -> None:
    for item in items:
        options=list(item.get("options") or [])
        response=dict(item.get("response_contract") or {})
        if options:
            require(len(options)==len(set(options)),f"OPTION_DUPLICATION:{item['item_id']}")
            require(item.get("correct_answer") in options,f"CORRECT_NOT_IN_OPTIONS:{item['item_id']}")
            require(response.get("single_answer_required") is True,f"SELECTED_RESPONSE_NOT_SINGLE:{item['item_id']}")
        if item["task_family_id"] in {
            "U06-TF05_CHUNK_TO_COMPLETE_SENTENCE",
            "U06-TF08_U01_U05_CUMULATIVE_INTEGRATION",
            "U06-TF09_PRODUCTIVE_ABILITY_RESPONSE",
            "U06-TF10_TRANSFER",
        }:
            require(response.get("scoring_mode")=="HUMAN_REVIEW",f"OPEN_RESPONSE_NOT_HUMAN_REVIEW:{item['item_id']}")
        require(item["can_interrogative_mastery_activated"] is False,f"CAN_QUESTION_UNLOCK:{item['item_id']}")
        require(item["can_negative_mastery_activated"] is False,f"CAN_NEGATIVE_UNLOCK:{item['item_id']}")
        require(item["non_ability_can_meaning_activated"] is False,f"NON_ABILITY_CAN_UNLOCK:{item['item_id']}")

def _validate_boundaries(payload: Mapping[str, Any]) -> None:
    b=payload["boundaries"]
    require(all(v is False for v in b.values()),"BOUNDARY_FALSE_CONTRACT_DRIFT")
    require(payload["acceptance"]["questionbank_items"]=="300/300","ACCEPTANCE_ITEM_COUNT_INVALID")
    require(payload["acceptance"]["forms"]=="10/10","ACCEPTANCE_FORM_COUNT_INVALID")
    require(payload["acceptance"]["q06_sentence_materialized_coverage"]=="129/129","ACCEPTANCE_Q06_INVALID")
    require(payload["acceptance"]["q07r1_functional_chunk_binding_coverage"]=="182/182","ACCEPTANCE_CHUNK_INVALID")
    require(payload["acceptance"]["q07r1_source_verb_binding_coverage"]=="62/62","ACCEPTANCE_VERB_INVALID")
    require(payload["acceptance"]["q07_scene_materialized_coverage"]=="17/17","ACCEPTANCE_SCENE_INVALID")
    require(payload["acceptance"]["status"]==builder.PASS_STATUS,"ACCEPTANCE_STATUS_INVALID")
    require(payload["next_short_step"]==builder.NEXT_SHORT_STEP,"NEXT_SHORT_STEP_DRIFT")

def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    items=list(payload.get("questionbank_items") or [])
    _validate_counts(payload,items)
    _validate_forms(payload,items)
    _validate_authority_coverage(payload,items)
    _validate_q06_coverage(payload,items)
    _validate_chunk_coverage(payload,items)
    _validate_answerability(items)
    _validate_boundaries(payload)
    return {
        "validator_id":VALIDATOR_ID,
        "status":"PASS",
        "error_count":0,
        "questionbank_items":300,
        "forms":10,
        "task_families":"10/10",
        "communicative_functions":"6/6",
        "frames":"3/3",
        "q06_sentences":"129/129",
        "q07_scenes":"17/17",
        "q07r1_chunks":"182/182",
        "q07r1_source_verbs":"62/62",
    }

def validation_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    report=validate_payload(payload)
    core={
        "validator_id":VALIDATOR_ID,
        "status":report["status"],
        "questionbank_digest":payload["integrity"]["questionbank_digest"],
        "forms_digest":payload["integrity"]["forms_digest"],
        "coverage_digest":payload["integrity"]["coverage_digest"],
    }
    return {"validator_id":VALIDATOR_ID,"status":"PASS","receipt_sha256":builder._digest(core)}

def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    policy_artifact.verify_artifact_digest(candidate)
    require(candidate.get("artifact_role")==policy_artifact.CANDIDATE_ROLE,"CANDIDATE_ROLE_INVALID")
    require(candidate.get("producer_id")==builder.TASK_ID,"PRODUCER_ID_INVALID")
    require(candidate.get("level_scope")==["A1"],"LEVEL_SCOPE_INVALID")
    payload=candidate.get("payload")
    require(isinstance(payload,Mapping),"CANDIDATE_PAYLOAD_INVALID")
    return validation_receipt(payload)

def validate_approved(candidate: Mapping[str, Any], approved: Mapping[str, Any]) -> dict[str, Any]:
    policy_artifact.verify_artifact_digest(candidate)
    policy_artifact.verify_artifact_digest(approved)
    errors=[]
    if approved.get("artifact_role")!=policy_artifact.APPROVED_ROLE: errors.append("APPROVED_ROLE_INVALID")
    if approved.get("producer_id")!=builder.TASK_ID: errors.append("APPROVED_PRODUCER_ID_INVALID")
    if approved.get("admission",{}).get("decision_ref")!=builder.DECISION_REF: errors.append("DECISION_REF_INVALID")
    if approved.get("payload")!=candidate.get("payload"): errors.append("APPROVED_PAYLOAD_DRIFT")
    try: validate_payload(approved.get("payload",{}))
    except Exception as exc: errors.append(str(exc))
    return {"validator_id":VALIDATOR_ID,"status":"PASS" if not errors else "FAIL","error_count":len(errors),"errors":errors}

def main() -> int:
    report=validate_payload(builder.build_export_payload())
    print(report)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
