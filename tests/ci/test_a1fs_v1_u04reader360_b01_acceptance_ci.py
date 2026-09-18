from product.a1fs_v1_2_1 import u04r360_b01_reader_acceptance as reader


def test_u04_reader360_b01_e004_e030_acceptance() -> None:
    report = reader.build_acceptance_report()
    assert report["status"] == reader.STATUS
    assert report["source_current360_episode_count"] == 360
    assert report["batch_episode_count"] == 27
    assert report["spoken_entry_count"] == 27
    assert report["pattern_entry_count"] == 27
    assert report["pattern_families_per_entry"] == 7
    assert report["source_lineage_alignment_count"] == 27
    assert report["cross_reader_episode_alignment_count"] == 27
    assert report["current360_passage_alignment_count"] == 54
    assert report["spoken_relation_alignment_count"] == 27
    assert report["pattern_family_semantic_count"] == 189
    assert report["approved_e001_e003_rewritten"] is False
    assert report["a1_boundary_blocked_surface_count"] == 0
    assert report["scope_safety"] == {
        "pdf_materialized": False,
        "unit04_baseline_integrated": False,
        "current360_mutated": False,
        "unit05_plus_opened": False,
        "a2_a2plus_unlocked": False,
    }
