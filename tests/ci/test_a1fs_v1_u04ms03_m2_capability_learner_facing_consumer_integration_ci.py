from __future__ import annotations

from collections import Counter

from product.a1fs_v1_2_1 import u04ms03_m2_capability_learner_facing_consumer_integration as consumer
from product.a1fs_v1_2_1.u04ms02a_raz_aw_multi_sentence_micro_scene_capability import (
    build_unit04_raz_aw_multi_sentence_micro_scene_capability,
)
from product.a1fs_v1_2_1.u04ms02c_ket_four_skill_task_assessment_projection import (
    build_unit04_ket_four_skill_task_assessment_projection,
)
from product.a1fs_v1_2_1 import u04neb02_natural_episode_bank_360 as neb02


REPORT = consumer.build_unit04_m2_capability_learner_facing_consumer_integration()
M2A = build_unit04_raz_aw_multi_sentence_micro_scene_capability()
M2C = build_unit04_ket_four_skill_task_assessment_projection()
CURRENT360 = neb02.build_unit04_neb02_natural_episode_bank_360()


def test_current360_downstream_cutover_uses_existing_consumer_and_keeps_scope_locked() -> None:
    assert REPORT["task_id"] == consumer.TASK_ID
    assert REPORT["status"] == consumer.STATUS
    assert REPORT["revision"] == consumer.REVISION
    assert REPORT["scope"] == {
        "existing_consumer_path_reused": True,
        "parallel_consumer_created": False,
        "reading_current360_cutover": True,
        "speaking_current360_cutover": True,
        "writing_current360_cutover": True,
        "listening_keep": True,
        "current360_content_modified": False,
        "q07_modified": False,
        "m2a_fact_lineage_modified": False,
        "q10_modified": False,
        "a2_a2plus_unlocked": False,
    }
    assert REPORT["safety"]["current360_episode_content_mutated"] is False
    assert REPORT["safety"]["q07_semantic_authority_mutated"] is False
    assert REPORT["safety"]["m2a_fact_lineage_mutated"] is False
    assert REPORT["safety"]["q10_mutated"] is False
    assert REPORT["safety"]["q07_m2a_and_current360_same_scene_claimed"] is False
    assert REPORT["safety"]["family_equivalence_claimed"] is False
    assert REPORT["safety"]["a2_a2plus_unlocked"] is False


def test_reading_speaking_writing_cut_over_to_current360_with_dual_lineage() -> None:
    rsw = [row for row in REPORT["task_projections"] if row["skill"] in consumer.RSW_SKILLS]
    assert len(rsw) == 108
    assert Counter(row["skill"] for row in rsw) == Counter(
        {"READING": 36, "SPEAKING": 36, "WRITING": 36}
    )
    capability_by_id = {row["capability_id"]: row for row in M2A["capabilities"]}
    episode_by_id = {row["episode_id"]: row for row in CURRENT360["effective_episodes"]}

    for row in rsw:
        assert row["response_authority"] == consumer.CURRENT360_AUTHORITY
        assert row["resource_mode"] == "CURRENT360_PASSAGE_AUTHORITY_WITH_INDEPENDENT_Q07_M2A_FACT_TRACE"
        assert row["upstream_response_authority"] == consumer.UPSTREAM_Q07_M2A_AUTHORITY
        assert row["authority_boundary"]["learner_language_authority"] == consumer.CURRENT360_AUTHORITY
        assert row["authority_boundary"]["current360_episode_lineage_preserved"] is True
        assert row["authority_boundary"]["upstream_q07_m2a_fact_lineage_preserved"] is True
        assert row["authority_boundary"]["q07_m2a_and_current360_same_scene_claimed"] is False
        assert row["authority_boundary"]["family_equivalence_claimed"] is False
        assert row["authority_boundary"]["a2_unlocked"] is False

        episode_lineage = row["current360_episode_lineage"]
        source_episode = episode_by_id[episode_lineage["episode_id"]]
        assert episode_lineage["micro_scene_id"] == source_episode["micro_scene_id"]
        assert episode_lineage["governed_scene_family"] == source_episode["governed_scene_family"]
        assert episode_lineage["source_fact_lineage"] == source_episode["source_fact_lineage"]
        assert episode_lineage["passage"] == source_episode["passage"]
        assert set(episode_lineage["target_relations"]).issubset(
            set(episode_lineage["visible_relation_surfaces"])
        )

        fact_lineage = row["q07_m2a_fact_lineage"]
        capability = capability_by_id[row["unit04_capability_id"]]
        assert fact_lineage["unit04_capability_id"] == capability["capability_id"]
        assert fact_lineage["scene_family"] == capability["scene_family"]
        assert fact_lineage["unit04_scene_ref_ids"] == capability["unit04_scene_ref_ids"]
        assert fact_lineage["unit04_sentence_ids"] == capability["unit04_sentence_ids"]
        assert fact_lineage["unit04_sentence_texts"] == capability["unit04_sentence_texts"]

        alignment = row["lineage_alignment"]
        assert alignment["shared_visible_relation_surfaces"]
        assert set(alignment["shared_visible_relation_surfaces"]).issubset(
            set(episode_lineage["visible_relation_surfaces"])
        )
        assert set(alignment["shared_visible_relation_surfaces"]).issubset(
            set(fact_lineage["relation_surfaces"])
        )
        assert alignment["same_scene_claimed"] is False
        assert alignment["same_source_fact_claimed"] is False
        assert alignment["family_equivalence_claimed"] is False
        if alignment["exact_governed_scene_family_match"]:
            assert alignment["current360_governed_scene_family"] == alignment["q07_m2a_scene_family"]
            assert alignment["basis"] == "EXACT_GOVERNED_FAMILY_AND_VISIBLE_RELATION_SURFACE"
        else:
            assert alignment["basis"] == "VISIBLE_RELATION_SURFACE_FALLBACK_NO_FAMILY_EQUIVALENCE_CLAIM"


def test_missing_exact_family_uses_visible_relation_fallback_not_fake_equivalence() -> None:
    summary = REPORT["consumer_summary"]
    assert summary["family_fallback_task_count"] > 0
    assert "MEDIA_ENTERTAINMENT_TECH" in summary["family_fallback_families"]
    assert summary["rsw_visible_relation_alignment_missing_count"] == 0
    fallback_rows = [
        row
        for row in REPORT["task_projections"]
        if row.get("lineage_alignment", {}).get("exact_governed_scene_family_match") is False
    ]
    assert len(fallback_rows) == summary["family_fallback_task_count"]
    assert all(row["lineage_alignment"]["shared_visible_relation_surfaces"] for row in fallback_rows)
    assert all(row["lineage_alignment"]["family_equivalence_claimed"] is False for row in fallback_rows)


def test_support_relation_capabilities_can_bind_only_when_surface_is_visible_in_passage() -> None:
    support_rows = []
    for row in REPORT["task_projections"]:
        if row.get("skill") not in consumer.RSW_SKILLS:
            continue
        shared = set(row["lineage_alignment"]["shared_visible_relation_surfaces"])
        if shared.intersection(consumer.SUPPORT_RELATIONS):
            support_rows.append(row)
            passage = row["current360_episode_lineage"]["passage"].casefold()
            for surface in shared.intersection(consumer.SUPPORT_RELATIONS):
                assert surface in passage
    assert support_rows


def test_listening_is_exactly_kept_from_upstream_m2c() -> None:
    downstream = [row for row in REPORT["task_projections"] if row["skill"] == "LISTENING"]
    upstream = [row for row in M2C["task_projections"] if row["skill"] == "LISTENING"]
    assert downstream == upstream
    assert len(downstream) == 36
    assert all(
        row["response_authority"] == consumer.UPSTREAM_Q07_M2A_AUTHORITY
        for row in downstream
    )
    assert all("current360_episode_lineage" not in row for row in downstream)


def test_current360_cutover_rechecks_missing_bindings_and_preserves_q10_a2_locks() -> None:
    summary = REPORT["consumer_summary"]
    assert summary["upstream_task_projection_count"] == 144
    assert summary["downstream_task_projection_count"] == 144
    assert summary["skill_distribution"] == {
        "READING": 36,
        "LISTENING": 36,
        "SPEAKING": 36,
        "WRITING": 36,
    }
    assert summary["current360_episode_bank_count"] == 360
    assert summary["current360_rsw_bound_task_count"] == 108
    assert summary["current360_missing_binding_count"] == 0
    assert summary["q07_m2a_fact_lineage_missing_count"] == 0
    assert summary["rsw_visible_relation_alignment_missing_count"] == 0
    assert summary["listening_keep_task_count"] == 36
    assert summary["listening_changed_task_count"] == 0

    gaps = REPORT["post_cutover_gap_recheck"]
    assert gaps["rsw_current360_passage_authority_missing"] == 0
    assert gaps["rsw_current360_episode_lineage_missing"] == 0
    assert gaps["rsw_q07_m2a_fact_lineage_missing"] == 0
    assert gaps["rsw_visible_relation_surface_alignment_missing"] == 0
    assert gaps["family_ontology_exact_match_fallback_task_count"] == summary["family_fallback_task_count"]
    assert gaps["family_ontology_exact_match_fallback_families"] == summary["family_fallback_families"]
    assert gaps["listening_authority_changes"] == 0
    assert gaps["q10_changes"] == 0
    assert gaps["a2_a2plus_unlock_count"] == 0


def test_current360_downstream_cutover_is_deterministic() -> None:
    replay = consumer.build_unit04_m2_capability_learner_facing_consumer_integration()
    assert replay == REPORT
