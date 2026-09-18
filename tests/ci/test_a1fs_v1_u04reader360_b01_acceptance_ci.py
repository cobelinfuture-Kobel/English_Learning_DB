from product.a1fs_v1_2_1 import u04r360_b01_reader_acceptance as reader
def test_u04_reader360_b10_e271_e300_cumulative_acceptance() -> None:
    report=reader.build_acceptance_report()
    assert report["status"]==reader.STATUS
    assert report["materialized_start"]=="U04-NEB-E004"
    assert report["materialized_end"]=="U04-NEB-E300"
    assert report["materialized_episode_count"]==297
    assert report["latest_batch_start"]=="U04-NEB-E271"
    assert report["latest_batch_end"]=="U04-NEB-E300"
    assert report["latest_batch_episode_count"]==30
    assert report["spoken_entry_count"]==297
    assert report["pattern_entry_count"]==297
    assert report["current360_passage_alignment_count"]==594
    assert report["current360_metadata_alignment_count"]==594
    assert report["spoken_relation_alignment_count"]==297
    assert report["pattern_family_semantic_count"]==2079
    assert report["spoken_dialogue_duplicate_count"]==0
    assert report["pattern_bundle_duplicate_count"]==0
    assert report["approved_e001_e003_rewritten"] is False
    assert report["scope_safety"]=={"pdf_materialized":False,"unit04_baseline_integrated":False,"current360_mutated":False,"unit05_plus_opened":False,"a2_a2plus_unlocked":False}
