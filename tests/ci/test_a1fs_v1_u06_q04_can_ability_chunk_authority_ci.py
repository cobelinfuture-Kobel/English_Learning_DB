from __future__ import annotations

import json
from pathlib import Path

from ulga.builders import build_a1fs_v1_u02ch02_unit01_unit02_cumulative_chunk_coverage_recheck as u02ch02


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "ulga" / "contracts" / "a1fs_v1_u06_q04_can_ability_chunk_authority.json"
Q00 = ROOT / "ulga" / "contracts" / "a1fs_v1_u06_q00_unit05_successor_baseline.json"
Q01 = ROOT / "ulga" / "contracts" / "a1fs_v1_u06_q01_canonical_target_gap_projection.json"
Q02 = ROOT / "ulga" / "contracts" / "a1fs_v1_u06_q02_vocabulary_carrier_authority.json"
Q03 = ROOT / "ulga" / "contracts" / "a1fs_v1_u06_q03_can_form_meaning_boundary_authority.json"
U04 = ROOT / "ulga" / "contracts" / "a1fs_v1_u04_q04_place_chunk_authority.json"
U05 = ROOT / "ulga" / "contracts" / "a1fs_v1_u05_q04_be_chunk_authority.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _norm(value: str) -> str:
    return " ".join(value.casefold().split())


def _u01_u02_surfaces() -> set[str]:
    u01 = {_norm(row["surface"]) for row in u02ch02.unit01_rows()}
    u02 = {_norm(row["surface"]) for row in u02ch02.unit02_rows()}
    assert len(u01) == 24
    assert len(u02) == 26
    assert not (u01 & u02)
    return u01 | u02


def _u04_new_surfaces(u04: dict) -> set[str]:
    target = {
        _norm(surface)
        for group in u04["target_relation_chunk_groups"]
        for surface in group["new_surfaces"]
    }
    support = {
        _norm(surface)
        for group in u04["yle_safe_support_chunk_groups"]
        for surface in group["new_surfaces"]
    }
    assert len(target) == 32
    assert len(support) == 8
    assert not (target & support)
    return target | support


def _u05_new_surfaces(u05: dict) -> set[str]:
    rows = [
        _norm(surface)
        for group in u05["chunk_groups"]
        for surface in group["surfaces"]
    ]
    assert len(rows) == 66
    assert len(set(rows)) == 66
    return set(rows)


def test_u06_q04_can_ability_chunk_authority_and_cumulative_dedup() -> None:
    data = _load(ARTIFACT)
    q00 = _load(Q00)
    q01 = _load(Q01)
    q02 = _load(Q02)
    q03 = _load(Q03)
    u04 = _load(U04)
    u05 = _load(U05)

    assert data["status"] == "PASS_A1FS_V1_U06Q04_CAN_ABILITY_CHUNK_AUTHORITY_AND_CUMULATIVE_DEDUP"
    assert data["unit_number"] == 6
    assert data["unit_id"] == "GRAMMAR_CAN_STATEMENT"
    assert data["source_main_sha"] == "d0944beb8e9ec7a1f02478a9c3dc2561f257c92b"

    assert q00["status"] == "PASS_A1FS_V1_U06Q00_UNIT05_SUCCESSOR_BASELINE"
    assert q01["status"] == "PASS_A1FS_V1_U06Q01_UNIT06_CANONICAL_TARGET_AND_GAP_PROJECTION"
    assert q02["status"] == "PASS_A1FS_V1_U06Q02_VOCABULARY_AUTHORITY_AND_REUSABLE_CARRIER_ADMISSION"
    assert q03["status"] == "PASS_A1FS_V1_U06Q03_CAN_FORM_MEANING_BOUNDARY_AUTHORITY"

    prior_50 = _u01_u02_surfaces()
    prior_90 = prior_50 | _u04_new_surfaces(u04)
    prior_156 = prior_90 | _u05_new_surfaces(u05)
    assert len(prior_50) == 50
    assert len(prior_90) == 90
    assert len(prior_156) == 156

    groups = {row["group_id"]: row for row in data["chunk_groups"]}
    assert set(groups) == {
        "U06-CH-G01-SUBJECT-CAN",
        "U06-CH-G02-CAN-BASE-VERB",
        "U06-CH-G03-CAN-EXTENDED-PREDICATE",
    }
    assert groups["U06-CH-G01-SUBJECT-CAN"]["surfaces"] == [
        "I can", "you can", "he can", "she can", "it can", "we can", "they can"
    ]

    q02_actions = {
        row["surface"]
        for row in q02["matrix"]
        if row["carrier_class"] == "ACTION_VERB"
    }
    assert q02_actions == {
        "drink", "eat", "go", "make", "play", "read", "ride",
        "run", "sit", "study", "swim", "walk", "work", "write",
    }
    assert set(groups["U06-CH-G02-CAN-BASE-VERB"]["surfaces"]) == {
        f"can {verb}" for verb in q02_actions
    }

    q02_surfaces = {row["surface"].casefold() for row in q02["matrix"]}
    for row in data["extended_predicate_carrier_bindings"]:
        assert row["surface"] in groups["U06-CH-G03-CAN-EXTENDED-PREDICATE"]["surfaces"]
        for carrier in row["required_q02_surfaces"]:
            assert carrier.casefold() in q02_surfaces

    all_new = [
        surface
        for group in data["chunk_groups"]
        for surface in group["surfaces"]
    ]
    normalized_new = {_norm(surface) for surface in all_new}
    assert len(all_new) == 34
    assert len(normalized_new) == 34
    assert prior_156.isdisjoint(normalized_new)

    coverage = data["coverage"]
    assert coverage == {
        "subject_can_chunks": 7,
        "can_base_verb_chunks": 14,
        "can_extended_predicate_chunks": 13,
        "total_new_surface_count": 34,
    }

    meaning = data["meaning_and_form_gates"]
    assert meaning["required_modal_surface"] == "can"
    assert meaning["required_lexical_verb_form"] == "BASE_FORM"
    assert meaning["chunk_membership_alone_proves_ability_meaning"] is False
    assert meaning["q05_q06_context_disambiguation_required"] is True
    assert set(meaning["blocked_target_readings"]) == {
        "PERMISSION", "OFFER", "REQUEST", "POSSIBILITY"
    }
    assert set(meaning["blocked_target_forms"]) == {
        "CAN_QUESTION", "CAN_NEGATIVE", "CAN_AS_NOUN"
    }

    activity = data["q02_activity_complement_resolution"]
    assert activity["q02_activity_complement_identity_count"] == 0
    assert activity["realized_extended_predicate_count"] == 13
    assert activity["ride_extended_predicate"]["bare_form_carrier_retained"] == "can ride"
    assert {
        row["surface"] for row in activity["deferred_q03_example_surfaces"]
    } == {"can play football", "can make sandwiches"}

    reassess = data["inherited_u05_66_reassessment"]
    assert reassess["total_surfaces_reassessed"] == 66
    assert reassess["exact_chunk_surfaces_consumed_as_unit06_target"] == 0
    assert reassess["not_eligible_as_exact_unit06_target_chunk_count"] == 66
    assert sum(row["surface_count"] for row in reassess["disposition_rows"]) == 66
    assert {row["disposition"] for row in reassess["disposition_rows"]} == {"NOT_ELIGIBLE"}
    assert reassess["origin_identity_preserved"] is True
    assert reassess["no_relabel_as_unit06_native"] is True

    scene = data["scene_functional_extraction"]
    assert q00["unit05_functional_chunk_carry_forward"]["unit06_q04_requirement"].startswith(
        "REASSESS_U05_66_FOR_UNIT06_APPLICABILITY"
    )
    assert q01["real_gap_projection"]["scene_gap"]["next_authority_slot"] == "Q07"
    assert scene["q01_scene_authority_slot"] == "Q07"
    assert scene["current_status"] == "DEFERRED_UNTIL_Q07_SCENE_AUTHORITY"
    assert scene["predecessor_u05_reader360_may_be_relabelled_as_unit06_native"] is False
    assert scene["post_q07_backfill_required"] is True
    assert scene["new_scene_created_by_q04"] is False

    dedup = data["dedup_result"]
    assert dedup == {
        "prior_distinct_surfaces": 156,
        "unit06_new_surfaces": 34,
        "within_unit06_duplicate_count": 0,
        "prior_vs_unit06_overlap_count": 0,
        "cumulative_distinct_surfaces": 190,
        "new_global_canonical_chunk_identities": 0,
    }

    boundaries = data["q04_boundaries"]
    assert boundaries["sentence_frames_materialized"] is False
    assert boundaries["sentence_assets_materialized"] is False
    assert boundaries["scenes_materialized"] is False
    assert boundaries["unit06_native_scene_functional_candidates_materialized"] is False
    assert boundaries["can_questions_activated"] is False
    assert boundaries["can_negatives_activated"] is False
    assert boundaries["non_ability_can_meanings_activated"] is False
    assert boundaries["canonical_graph_mutated"] is False
    assert boundaries["a2_unlocked"] is False

    acceptance = data["acceptance"]
    assert acceptance["predecessor_distinct_surface_reconstruction"] == "156/156"
    assert acceptance["inherited_u05_surfaces_reassessed"] == "66/66"
    assert acceptance["new_unit06_chunk_surfaces_total"] == 34
    assert acceptance["cumulative_distinct_chunk_surfaces"] == 190
    assert acceptance["q02_content_word_carrier_gate"] == "PASS_13_OF_13_EXTENDED_PREDICATES"
    assert acceptance["native_scene_extraction_status"] == "DEFERRED_UNTIL_Q07_SCENE_AUTHORITY"
    assert acceptance["post_q07_backfill_required"] is True
    assert acceptance["learner_facing_sentence_assets_generated"] == 0
    assert acceptance["a2_a2plus_unlocked"] is False

    assert data["next_short_step"] == "A1FS-V1-U06Q05_Unit06CoreSentenceFrameAuthority"
