import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
Q04 = ROOT / "ulga/contracts/a1fs_v1_u04_q04_place_chunk_authority.json"
Q05 = ROOT / "ulga/contracts/a1fs_v1_u04_q05_core_sentence_frame_authority.json"
Q06 = ROOT / "ulga/contracts/a1fs_v1_u04_q06_sentence_assets.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_u04_q06_materializes_exact_new_delta_and_cumulative_total():
    data = load(Q06)
    assert data["status"] == "PASS_Q06_UNIT04_SENTENCE_ASSET_PRODUCTION_AND_SEMANTIC_ADMISSION"
    assert data["prior_cumulative_baseline"]["cumulative_distinct"] == 26514
    assert len(data["assets"]) == 96
    assert data["coverage"]["target_relation_asset_count"] == 64
    assert data["coverage"]["support_relation_asset_count"] == 32
    assert data["coverage"]["cumulative_sentence_assets_after_q06"] == 26610
    assert data["delta_vs_unit03"]["unit04_new_admitted"] == 96


def test_u04_q06_is_exact_and_normalized_unique_with_deterministic_ids():
    data = load(Q06)
    rows = data["assets"]
    ids = [x["sentence_id"] for x in rows]
    norms = [x["normalized_text"] for x in rows]
    assert len(ids) == len(set(ids)) == 96
    assert len(norms) == len(set(norms)) == 96
    for row in rows:
        expected = "U04-SENT-" + hashlib.sha256(row["normalized_text"].encode("utf-8")).hexdigest()[:20].upper()
        assert row["sentence_id"] == expected


def test_u04_q06_uses_only_q04_new_chunks_and_q05_primary_routes():
    q04 = load(Q04)
    q05 = load(Q05)
    q06 = load(Q06)

    target_chunks = {}
    for group in q04["target_relation_chunk_groups"]:
        if group["relation_surface"] in {"inside", "under", "behind", "between"}:
            target_chunks[group["relation_surface"]] = set(group["new_surfaces"])
    support_chunks = {
        group["support_pattern"]: set(group["new_surfaces"])
        for group in q04["yle_safe_support_chunk_groups"]
    }
    routes = {}
    routes.update(q05["q06_primary_generation_routing"]["target_relations"])
    routes.update(q05["q06_primary_generation_routing"]["support_relations"])

    for row in q06["assets"]:
        relation = row["relation_surface"]
        if row["generation_role"] == "TARGET_RELATION":
            assert relation in target_chunks
            assert row["place_chunk_surface"] in target_chunks[relation]
        else:
            assert relation in support_chunks
            assert row["place_chunk_surface"] in support_chunks[relation]
        assert row["pattern_id"] == routes[relation]


def test_u04_q06_relation_coverage_is_balanced_and_does_not_regenerate_prior_supply():
    data = load(Q06)
    counts = Counter(x["relation_surface"] for x in data["assets"])
    assert counts == {
        "inside": 16,
        "under": 16,
        "behind": 16,
        "between": 16,
        "next to": 16,
        "in front of": 16,
    }
    assert data["reuse_supply"]["unit04_no_new_assets_for_prior_supplied_relations"] == ["in", "near", "on", "at"]
    assert not ({"in", "near", "on", "at"} & set(counts))


def test_u04_q06_all_new_assets_are_context_bound_until_q07_scene_binding():
    data = load(Q06)
    for row in data["assets"]:
        assert row["canonical_admission_status"] == "ADMITTED"
        assert row["semantic_admission_class"] == "CONTEXT_BOUND_APPROVE"
        assert row["requires_scene_binding"] is True
        assert row["scene_binding_required_at_use_time"] is True
        assert row["direct_unit04_assessment_allowed"] is False
        assert row["context_bound_unit04_assessment_allowed"] is True
        assert row["a2_unlocked"] is False


def test_u04_q06_between_requires_two_distinct_landmarks_and_no_directional_leakage():
    data = load(Q06)
    subject_pronouns = re.compile(r"^(?:I|you|he|she|it|we|they)\b", re.I)
    for row in data["assets"]:
        assert row["relation_surface"] not in {"from", "into", "to"}
        assert not subject_pronouns.search(row["text"])
        if row["relation_surface"] == "between":
            m = re.search(r"between the (.+?) and the (.+)$", row["normalized_text"])
            assert m
            assert m.group(1) != m.group(2)


def test_u04_q06_dedup_claim_is_bounded_and_semantic_review_is_explicit():
    data = load(Q06)
    dedup = data["dedup_evidence"]
    assert dedup["raw_exact_normalized_pool_checked"] == 3726 + 18983
    assert dedup["raw_exact_normalized_collision_count"] == 0
    assert dedup["unit01_evidence_mode"] == "INDEXED_FULL3805_RELATION_FAMILY_CHECK"
    assert dedup["unit01_indexed_search_collision_found"] is False
    assert "No claim of raw-byte exhaustive exact comparison against Unit01" in dedup["claim_boundary"]
    sem = data["semantic_admission"]
    assert sem["manual_reviewed"] == sem["manual_approved"] == 96
    assert sem["manual_rejected"] == 0
    assert data["acceptance"]["manual_semantic_review_pass"] == "96/96"


def test_u04_q06_boundaries_and_next_step():
    data = load(Q06)
    assert data["q06_boundaries"] == {
        "scenes_materialized": False,
        "communicative_functions_materialized": False,
        "questionbank_materialized": False,
        "forms_materialized": False,
        "directional_from_into_to_activated": False,
        "a2_unlocked": False,
    }
    assert data["next_short_step"] == "A1FS-V1-U04Q07_Unit04LifeSkillMicroSceneMaterializationAndSentenceBinding"
