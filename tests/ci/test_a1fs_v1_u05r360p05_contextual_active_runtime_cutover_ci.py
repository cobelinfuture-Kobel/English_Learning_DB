from __future__ import annotations

from collections import Counter

from product.a1fs_v1_2_1 import u05r360p05_contextual_active_runtime_cutover as p05


REPORT = p05.build_unit05_r360_p05_contextual_active_runtime_cutover()


def test_u05_r360_p05_materializes_one_active_20x40_runtime():
    assert REPORT["status"] == p05.STATUS
    assert REPORT["revision"] == p05.REVISION
    contract = REPORT["materialization_contract"]
    assert contract["form_count"] == 20
    assert contract["activities_per_form"] == 40
    assert contract["activity_count"] == 800
    assert contract["section_counts_per_form"] == {"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}
    assert len(REPORT["forms"]) == 20
    assert len(REPORT["active_items"]) == 800
    assert len(REPORT["runtime_bindings"]) == 800
    assert len({row["active_item_id"] for row in REPORT["active_items"]}) == 800


def test_u05_r360_p05_cutover_supersedes_old_active_runtime_without_deleting_lineage():
    c = REPORT["cutover_contract"]
    assert c["active_contextual_runtime_authority"] == p05.TASK_ID
    assert c["parallel_active_contextual_runtime_allowed"] is False
    assert c["q10_role"] == "ITEM_CANDIDATE_AND_SLOT_LINEAGE_ONLY"
    assert c["legacy_q10r1_role"] == "SUPERSEDED_AS_ACTIVE_CONTEXTUAL_RUNTIME_LEARNER_SHELL_REUSED"
    assert c["reader360_role"] == "ACTIVE_CONTEXTUAL_CONTENT_AUTHORITY"
    assert REPORT["safety"]["q10_source_modified"] is False
    assert REPORT["safety"]["q10r1_source_modified"] is False
    assert all(row["source_q10_lineage"]["selected_item_id"] for row in REPORT["runtime_bindings"])
    assert all(len(row["source_q10_lineage"]["candidate_ids"]) == 3 for row in REPORT["runtime_bindings"])


def test_u05_r360_p05_binds_aligned_current_spoken_pattern_triad_to_every_slot():
    for row in REPORT["runtime_bindings"]:
        triad = row["reader_triad"]
        episode_id = triad["source_episode_id"]
        suffix = episode_id.rsplit("E", 1)[1]
        assert triad["current360_ref"] == episode_id
        assert triad["spoken360_ref"] == f"U05-SPOKEN360-E{suffix}"
        assert triad["pattern360_ref"] == f"U05-PATTERN360-E{suffix}"
        assert row["available_reader_modes"] == ["CURRENT360", "SPOKEN360", "PATTERN360"]


def test_u05_r360_p05_routes_primary_mode_by_section_and_keeps_all_three_modes_reachable():
    expected = {
        "CURRENT360": 360,
        "PATTERN360": 320,
        "SPOKEN360": 120,
    }
    assert REPORT["coverage"]["primary_mode_counts"] == expected
    for row in REPORT["runtime_bindings"]:
        assert row["primary_reader_mode"] == p05.PRIMARY_MODE_BY_SECTION[row["section"]]
    assert REPORT["coverage"]["current360_runtime_reachable_episode_count"] == 360
    assert REPORT["coverage"]["spoken360_runtime_reachable_episode_count"] == 360
    assert REPORT["coverage"]["pattern360_runtime_reachable_episode_count"] == 360


def test_u05_r360_p05_preserves_seen_unseen_progression_with_no_episode_overlap():
    assert REPORT["materialization_contract"]["seen_episode_count"] == 216
    assert REPORT["materialization_contract"]["unseen_episode_count"] == 144
    assert REPORT["coverage"]["seen_unseen_overlap_count"] == 0
    seen = {
        row["reader_triad"]["source_episode_id"]
        for row in REPORT["runtime_bindings"]
        if int(row["form_number"]) <= 12
    }
    unseen = {
        row["reader_triad"]["source_episode_id"]
        for row in REPORT["runtime_bindings"]
        if int(row["form_number"]) >= 13
    }
    assert seen == {f"U05-NEB-E{i:03d}" for i in range(1, 217)}
    assert unseen == {f"U05-NEB-E{i:03d}" for i in range(217, 361)}


def test_u05_r360_p05_keeps_exact_form_section_architecture():
    for form in REPORT["forms"]:
        assert form["activity_count"] == 40
        assert form["section_counts"] == {"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}
        rows = [r for r in REPORT["active_items"] if r["form_number"] == form["form_number"]]
        assert Counter(r["section"] for r in rows) == Counter({"A": 6, "B": 10, "C": 10, "D": 8, "E": 6})


def test_u05_r360_p05_reader_authorities_are_exact_full360_corpora():
    auth = REPORT["reader_authorities"]
    assert len(auth["current360"]) == 360
    assert len(auth["spoken360"]) == 360
    assert len(auth["pattern360"]) == 360
    assert auth["current360"][0]["episode_id"] == "U05-NEB-E001"
    assert auth["current360"][-1]["episode_id"] == "U05-NEB-E360"
    assert auth["spoken360"][0]["reader_entry_id"] == "U05-SPOKEN360-E001"
    assert auth["spoken360"][-1]["reader_entry_id"] == "U05-SPOKEN360-E360"
    assert auth["pattern360"][0]["reader_entry_id"] == "U05-PATTERN360-E001"
    assert auth["pattern360"][-1]["reader_entry_id"] == "U05-PATTERN360-E360"


def test_u05_r360_p05_does_not_rewrite_reader_language_or_unlock_future_scope():
    s = REPORT["safety"]
    assert s["current360_modified"] is False
    assert s["spoken360_modified"] is False
    assert s["pattern360_modified"] is False
    assert s["python_generated_or_rewrote_reader_english"] is False
    assert s["parallel_runtime_created"] is False
    assert s["pdf_materialized"] is False
    assert s["be_interrogative_mastery_unlocked"] is False
    assert s["past_be_unlocked"] is False
    assert s["present_continuous_unlocked"] is False
    assert s["existential_there_be_unlocked"] is False
    assert s["a2_a2plus_unlocked"] is False
    assert s["other_units_modified"] is False
    assert REPORT["next_short_step"] == p05.NEXT_SHORT_STEP


def test_u05_r360_p05_is_deterministic():
    replay = p05.build_unit05_r360_p05_contextual_active_runtime_cutover()
    assert replay == REPORT
