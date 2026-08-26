from ulga.builders import build_a1fs_v1_u03q02q04r1_vocabulary_chunk_provenance_recheck as builder


def _report():
    report = builder.build_report()
    builder.validate(report)
    return report


def test_q2_exact_provenance_partition_and_no_false_new_claim():
    report = _report()
    q2 = report["q2"]
    counts = q2["provenance_class_counts"]

    assert q2["support_pool_count"] == 40
    assert counts == {
        "INHERITED_EXACT_FROM_UNIT02": 16,
        "UNIT01_SURFACE_PROVEN_NO_U02_ACTIVE_TARGET": 3,
        "UNIT01_SURFACE_PROVEN_NON_PLAIN_S_NOT_U02_TARGET": 5,
        "SURFACE_COLLISION_DIFFERENT_POS_NOT_INHERITED_IDENTITY": 1,
        "PREVIOUS_UNIT_PROVENANCE_UNRESOLVED": 15,
    }
    assert sum(counts.values()) == 40
    assert q2["unit03_definitely_new_vocabulary_count"] is None
    assert q2["unit03_definitely_new_vocabulary_claimed"] is False


def test_q2_unit02_exact_ids_and_watch_surface_collision():
    rows = {row["resource_id"]: row for row in _report()["q2"]["rows"]}
    inherited = {
        row["resource_id"]
        for row in rows.values()
        if row["unit03_delta_class"] == "INHERITED_EXACT_FROM_UNIT02"
    }
    assert inherited == {
        "KPOP-VR-004", "KPOP-VR-005", "KPOP-VR-007", "KPOP-VR-009",
        "KPOP-VR-010", "KPOP-VR-011", "KPOP-VR-012", "KPOP-VR-013",
        "KPOP-VR-015", "KPOP-VR-017", "KPOP-VR-018", "KPOP-VR-019",
        "KPOP-VR-051", "KPOP-VR-052", "KPOP-VR-053", "KPOP-VR-055",
    }
    watch = rows["KPOP-VR-058"]
    assert watch["vocabulary_id"] == "v_9960"
    assert watch["part_of_speech"] == "verb"
    assert watch["unit03_delta_class"] == "SURFACE_COLLISION_DIFFERENT_POS_NOT_INHERITED_IDENTITY"


def test_q2_unit01_surface_provenance_is_not_overclaimed_as_exact_identity():
    rows = {row["resource_id"]: row for row in _report()["q2"]["rows"]}
    no_active = {
        rid for rid, row in rows.items()
        if row["unit03_delta_class"] == "UNIT01_SURFACE_PROVEN_NO_U02_ACTIVE_TARGET"
    }
    non_plain = {
        rid for rid, row in rows.items()
        if row["unit03_delta_class"] == "UNIT01_SURFACE_PROVEN_NON_PLAIN_S_NOT_U02_TARGET"
    }
    unresolved = {
        rid for rid, row in rows.items()
        if row["unit03_delta_class"] == "PREVIOUS_UNIT_PROVENANCE_UNRESOLVED"
    }
    assert no_active == {"KPOP-VR-001", "KPOP-VR-006", "KPOP-VR-014"}
    assert non_plain == {"KPOP-VR-002", "KPOP-VR-003", "KPOP-VR-008", "KPOP-VR-016", "KPOP-VR-056"}
    assert unresolved == {
        "KPOP-VR-020", "KPOP-VR-021", "KPOP-VR-022", "KPOP-VR-023",
        "KPOP-VR-024", "KPOP-VR-054", "KPOP-VR-057", "KPOP-VR-059",
        "KPOP-VR-060", "KPOP-VR-061", "KPOP-VR-062", "KPOP-VR-063",
        "KPOP-VR-064", "KPOP-VR-065", "KPOP-VR-066",
    }


def test_q4_exact_inherited_vs_unit03_new_denominators():
    q4 = _report()["q4"]
    assert q4["unit01_inherited_surface_rows"] == 24
    assert q4["unit02_native_inherited_surface_rows"] == 26
    assert q4["unit01_unit02_inherited_cumulative_surface_rows"] == 50
    assert q4["unit03_new_admitted_surface_rows"] == 0
    assert q4["unit03_native_surface_rows"] == 0
    assert q4["cumulative_distinct_surface_rows"] == 50
    assert q4["cumulative_direct_or_instructional_surface_rows"] == 49
    assert q4["cumulative_receptive_only_surface_rows"] == 1


def test_scope_boundaries():
    report = _report()
    assert report["status"] == builder.PASS_STATUS
    assert report["claim_boundaries"] == {
        "q2_support_pool_is_not_unit03_new_count": True,
        "unresolved_q2_rows_are_not_labeled_new": True,
        "unit03_q4_new_chunk_count_is_zero": True,
        "canonical_vocabulary_mutated": False,
        "canonical_chunk_authority_mutated": False,
        "sentence_assets_created": False,
        "questionbank_items_created": False,
        "runtime_mutated": False,
        "a2_unlocked": False,
    }
