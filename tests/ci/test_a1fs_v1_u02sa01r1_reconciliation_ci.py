from tests.ci.a1fs_v1_u02sa01r1_test_support import validator, report

def test_private_dedup_without_public_fingerprints():
    receipt=report()["private_cumulative_dedup_receipt"]; assert receipt["unit01_sentence_pool_count"]==3805; assert receipt["unit01_exact_identity_count"]==3529; assert receipt["unit01_normalized_identity_count"]==3529; assert receipt["exact_overlap_count"]==0; assert receipt["normalized_overlap_count"]==0; assert receipt["private_sentence_bodies_committed"] is False; assert receipt["private_sentence_fingerprints_committed"] is False; assert validator._private_fields(report())==[]

def test_semantic_funnel_and_patterns():
    value=report(); c=value["pipeline_counts"]; assert c["unit02_semantic_review_eligible"]==c["unit02_semantic_approved"]+c["unit02_semantic_rejected"]+c["unit02_semantic_deferred"]; assert set(value["pattern_counts"])=={"SP_000002","SP_000003","SP_000004","SP_000005","SP_000013"}; assert all(x["admitted"]>0 for x in value["pattern_counts"].values())

def test_morphology_denominator_child_safe_exception():
    value=report(); c=value["pipeline_counts"]; safety=value["sentence_binding_safety_exception"]; assert c["unit02_morphology_target_nouns"]==162; assert c["unit02_sentence_bindable_morphology_target_nouns"]==161; assert safety["restricted_target_surfaces"]==["beer"]; assert safety["q2_authority_mutated"] is False; assert safety["qbc02_mutated"] is False

def test_legacy_reconciliation_and_qb03_return():
    value=report(); legacy=value["legacy_unit02_reconciliation"]; assert legacy["legacy_asset_delete_count"]==0; assert legacy["second_unit02_authority_created"] is False; assert legacy["old_u02sa01_read_only_3805_984_4_model"]=="SUPERSEDED_BY_R1_DYNAMIC_PRODUCTION_PIPELINE"; assert value["next_short_step"]=="A1FS-V1-U02QB03_Unit02CumulativeQuestionBankRuntimeIntegration"
