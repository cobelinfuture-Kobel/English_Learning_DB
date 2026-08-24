from __future__ import annotations
from typing import Any, Mapping
from ulga.builders.a1fs_v1_u02sa01r1.constants import *
from ulga.builders.a1fs_v1_u02sa01r1.engine import normalize_surface
from .privacy import private_fields

def validate_payload(value: Mapping[str, Any]) -> list[str]:
    e=[]; c=value.get("pipeline_counts",{}); patterns=value.get("pattern_counts",{}); q2=value.get("q2_vocabulary_morphology_list",[]); assets=value.get("sentence_asset_delta",{}).get("assets",[]); receipt=value.get("private_cumulative_dedup_receipt",{}); safety=value.get("sentence_binding_safety_exception",{})
    def req(cond,msg):
        if not cond:e.append(msg)
    req(value.get("schema_version")==SCHEMA_VERSION,"SCHEMA_VERSION_INVALID"); req(value.get("task_id")==TASK_ID,"TASK_ID_INVALID"); req(value.get("status")==PASS_STATUS,"STATUS_INVALID")
    req(c.get("unit01_base_sentence_assets")==EXPECTED_UNIT01_SENTENCE_ASSETS,"U01_BASE_INVALID"); req(c.get("unit01_exact_text_identities")==EXPECTED_UNIT01_EXACT_TEXT_IDENTITIES,"U01_EXACT_INVALID"); req(c.get("unit01_normalized_text_identities")==EXPECTED_UNIT01_NORMALIZED_TEXT_IDENTITIES,"U01_NORMALIZED_INVALID")
    req(c.get("unit02_morphology_target_nouns")==EXPECTED_U02_PLAIN_S_TARGETS,"Q2_TARGET_COUNT_INVALID"); req(len(q2)==EXPECTED_U02_PLAIN_S_TARGETS,"Q2_LIST_COUNT_INVALID"); req(len({normalize_surface(x.get("singular","")) for x in q2})==EXPECTED_U02_PLAIN_S_TARGETS,"Q2_LIST_IDENTITY_INVALID")
    req(c.get("yle_mapping_relationships",0)>0,"YLE_MAPPING_EMPTY"); req(c.get("yle_a1_plain_s_lexical_expansion_nouns",0)>0,"YLE_A1_EXPANSION_EMPTY"); req(c.get("yle_a2_locked_mapped_vocab_ids",-1)>=0,"YLE_A2_LOCK_INVALID")
    generated=c.get("unit02_generated_sentence_candidates",-1); approved=c.get("unit02_semantic_approved",-1); rejected=c.get("unit02_semantic_rejected",-1); deferred=c.get("unit02_semantic_deferred",-1)
    req(generated>EXPECTED_U02_PLAIN_S_TARGETS*2,"LARGE_PRODUCTION_NOT_MATERIALIZED"); req(generated==approved+rejected+deferred,"SEMANTIC_FUNNEL_MISMATCH"); req(c.get("unit02_cumulative_exact_or_normalized_reuse")==0,"CUMULATIVE_REUSE_EXPECTED_ZERO_BY_STRUCTURAL_PROOF"); req(c.get("unit02_new_admitted")==approved==len(assets),"NEW_ADMITTED_MISMATCH"); req(approved>EXPECTED_U02_PLAIN_S_TARGETS,"ADMITTED_POOL_NOT_LARGE_ENOUGH_FOR_CUMULATIVE_PRODUCTION"); req(c.get("cumulative_distinct_sentence_assets")==EXPECTED_UNIT01_SENTENCE_ASSETS+approved,"CUMULATIVE_FORMULA_INVALID")
    req(set(patterns)==set(PATTERN_TEMPLATES),"PATTERN_SET_INVALID"); req(all(row.get("generated",0)>0 and row.get("admitted",0)>0 for row in patterns.values()),"PATTERN_ADMISSION_COVERAGE_INCOMPLETE")
    req(len({x.get("sentence_id") for x in assets})==len(assets),"SENTENCE_ID_DUPLICATE"); req(len({x.get("normalized_text") for x in assets})==len(assets),"SENTENCE_TEXT_DUPLICATE"); req(all(x.get("canonical_admission_status")=="ADMITTED" and x.get("semantic_pedagogical_decision")=="APPROVE" for x in assets),"NON_APPROVED_SENTENCE_ASSET")
    req(all(set(x.get("canonical_levels",[])) <= {"A1"} for x in assets),"A2_CANONICAL_CONTENT_LEAK")
    req(receipt.get("full_private_replay_performed") is True,"PRIVATE_REPLAY_MISSING"); req(receipt.get("exact_overlap_count")==0 and receipt.get("normalized_overlap_count")==0,"PRIVATE_DEDUP_OVERLAP_NONZERO"); req(receipt.get("private_sentence_bodies_committed") is False and receipt.get("private_sentence_fingerprints_committed") is False,"PRIVATE_EVIDENCE_LEAK")
    req(safety.get("morphology_target_denominator")==162,"SAFETY_DENOMINATOR_INVALID"); req(safety.get("sentence_bindable_target_count")==161,"SAFETY_BINDABLE_COUNT_INVALID"); req(safety.get("restricted_target_surfaces")==["beer"],"SAFETY_RESTRICTED_TARGET_INVALID")
    req(value.get("legacy_unit02_reconciliation",{}).get("legacy_asset_delete_count")==0,"LEGACY_DELETE_DETECTED"); req(value.get("legacy_unit02_reconciliation",{}).get("second_unit02_authority_created") is False,"PARALLEL_UNIT02_AUTHORITY_DETECTED")
    req(value.get("next_short_step")==NEXT_SHORT_STEP,"NEXT_SHORT_STEP_INVALID"); req(not private_fields(value),"PRIVATE_FIELDS_PRESENT")
    return e
