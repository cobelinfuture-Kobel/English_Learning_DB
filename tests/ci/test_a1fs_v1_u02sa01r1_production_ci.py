from tests.ci.a1fs_v1_u02sa01r1_test_support import builder, validator, report

def test_policy_bound_transition():
    candidate=builder.build_candidate(); approved=builder.admit_candidate(candidate); assert candidate["artifact_role"]=="CANDIDATE_JSON"; assert approved["artifact_role"]=="APPROVED_CANONICAL_JSON"; assert approved["admission"]["decision_ref"]==builder.DECISION_REF; assert validator.validate_approved(candidate,approved)["error_count"]==0

def test_q2_vocabulary_morphology_master_list():
    value=report(); rows=value["q2_vocabulary_morphology_list"]; assert len(rows)==162; assert len({r["singular"].casefold() for r in rows})==162; beer=[r for r in rows if r["singular"].casefold()=="beer"]; assert len(beer)==1 and beer[0]["sentence_bindable"] is False

def test_dynamic_large_sentence_asset_list():
    value=report(); c=value["pipeline_counts"]; assets=value["sentence_asset_delta"]["assets"]; assert c["unit02_new_admitted"]==len(assets)==c["unit02_semantic_approved"]; assert len(assets)>162; assert c["cumulative_distinct_sentence_assets"]==3805+len(assets); assert len({x["normalized_text"] for x in assets})==len(assets)

def test_yle_evidence_canonical_vocab_and_a2_lock():
    value=report(); c=value["pipeline_counts"]; assert c["yle_mapping_relationships"]>0; assert c["yle_a1_plain_s_lexical_expansion_nouns"]>0; assert c["yle_a2_locked_mapped_vocab_ids"]>=0; assert value["source_authority"]["cambridge_yle_role"]=="LEXICAL_EXPANSION_EVIDENCE_ONLY"; assert value["claim_boundaries"]["cambridge_yle_promoted_to_vocabulary_authority"] is False; assert value["coverage_verdict"]["a2_curriculum_unlocked"] is False
