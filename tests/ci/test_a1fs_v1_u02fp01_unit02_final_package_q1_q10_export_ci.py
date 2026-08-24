import base64
import hashlib
import json
import os
import zlib
from functools import lru_cache

from ulga.builders import (
    build_a1fs_v1_u02fp01_unit02_final_package_q1_q10_export as builder,
)
from ulga.validators.a1fs_v1_u02sa01r1_validation.privacy import private_fields

EXPORT_BRANCH = "a1fs-v1-u02fp01-final-package-q1-q10-export"


@lru_cache(maxsize=1)
def _payload():
    return builder.build_export_payload()


def test_u02fp01_q1_q4_q5_q7_q8_denominators():
    payload = _payload()
    assert payload["status"] == builder.PASS_STATUS

    q1 = payload["q1_grammar"]
    assert q1["unit_id"] == "GRAMMAR_REGULAR_PLURAL_NOUNS"
    assert q1["morphology_scope"] == "PLAIN_S_ONLY"
    assert len(q1["target_egp_row_ids"]) == 4
    assert q1["plain_s_vocabulary_denominator"] == 162
    assert q1["exact_active_vocabulary_ref_count"] == 171

    q4 = payload["q4_chunks"]
    q4_counts = q4["coverage_denominators"]
    assert len(q4["unit01_rows"]) == 24
    assert len(q4["unit02_rows"]) == 26
    assert q4_counts["cross_unit_exact_surface_overlap_count"] == 0
    assert q4_counts["cumulative_distinct_surface_rows"] == 50
    assert q4_counts["cumulative_direct_or_instructional_surface_rows"] == 49
    assert q4_counts["cumulative_receptive_only_surface_rows"] == 1

    q5 = payload["q5_sentence_patterns"]
    assert q5["pattern_family_coverage"]["cumulative_pedagogical_core_pattern_family_count"] == 7
    assert q5["pattern_family_coverage"]["unit02_main_plural_sentence_generation_family_count"] == 5
    assert q5["exact_frame_coverage"]["unit01_exact_frame_count"] == 11
    assert q5["exact_frame_coverage"]["unit02_new_canonical_exact_frame_count"] == 4
    assert q5["exact_frame_coverage"]["cross_unit_exact_template_overlap_count"] == 0
    assert q5["exact_frame_coverage"]["cumulative_declared_exact_frame_count"] == 15

    q7 = payload["q7_micro_scenes"]
    q7_counts = q7["coverage_denominators"]
    assert q7_counts["unit02_vocabulary_surface_count"] == 162
    assert len(q7["coverage_recheck"]) == 162
    assert q7_counts["direct_eligible_covered_by_existing_scene_count"] == 26
    assert q7_counts["direct_eligible_covered_by_admitted_candidate_count"] == 109
    assert len(q7["materialized_scene_candidates"]) == 109
    assert q7_counts["gated_non_scene_gap_count"] == 27
    assert q7_counts["candidate_adjusted_remaining_direct_scene_gap_count"] == 0
    assert all(row["canonical_scene_identity_assigned"] is False for row in q7["materialized_scene_candidates"])
    assert all(row["runtime_bindable"] is False for row in q7["materialized_scene_candidates"])
    assert all(row["learner_facing"] is False for row in q7["materialized_scene_candidates"])

    q8 = payload["q8_communicative_functions"]
    assert q8["coverage_denominators"]["communicative_function_family_count"] == 3
    assert q8["coverage_denominators"]["covered_function_family_count"] == 3
    assert q8["coverage_denominators"]["missing_function_family_count"] == 0


def test_u02fp01_q9_preserves_baseline_and_closes_supply_runtime():
    q9 = _payload()["q9_task_angle_question_type"]
    baseline = {row["task_family"]: row["coverage_status"] for row in q9["baseline_task_family_denominator"]}
    assert baseline == {
        "RECOGNITION": "FULL",
        "MEANING_DISCRIMINATION": "FULL",
        "FORM_SELECTION": "FULL",
        "MORPHOLOGY_CONSTRUCTION": "FULL",
        "ERROR_DETECTION": "PARTIAL",
        "ERROR_CORRECTION": "GAP",
        "CONTEXT_GAP": "PARTIAL",
        "U01_U02_INTEGRATION": "GAP",
        "PRODUCTIVE_RESPONSE": "FULL",
        "TRANSFER": "PARTIAL",
    }
    assert len(q9["baseline_pedagogical_role_denominator"]) == 5
    current = q9["post_materialization_task_families"]
    assert len(current) == 10
    assert min(row["post_qbc02_pool_depth"] for row in current) >= 48
    assert all(row["post_qbc02_supply_materialized"] is True for row in current)
    assert all(row["qb03_runtime_connected"] is True for row in current)
    assert {row["qb03_runtime_selected_occurrences"] for row in current} == {64}
    assert q9["post_materialization_summary"]["runtime_occurrence_count"] == 640
    assert q9["post_materialization_summary"]["post_qbc02_pedagogical_full_partial_gap_recheck_separately_materialized"] is False


def test_u02fp01_q10_full_questionbank_capacity_and_runtime_exports():
    q10 = _payload()["q10_questionbank_capacity_runtime"]
    items = q10["unit02_approved_items"]
    capacity = q10["capacity_slot_matrix"]
    runtime = q10["runtime_occurrences"]

    assert q10["inventory_summary"]["unit01_reference_only_item_count"] == 474
    assert q10["inventory_summary"]["unit02_approved_item_count"] == 994
    assert q10["inventory_summary"]["cumulative_catalog_item_count"] == 1468
    assert len(items) == 994
    assert len({row["item_id"] for row in items}) == 994

    assert len(capacity) == 640
    assert all(len(row["candidate_ids"]) == 3 for row in capacity)
    assert all(len(set(row["candidate_ids"])) == 3 for row in capacity)
    assert sum(len(row["candidate_ids"]) for row in capacity) == 1920

    assert len(runtime) == 640
    assert len({row["runtime_occurrence_id"] for row in runtime}) == 640
    assert q10["runtime_form_contract"]["form_count"] == 16
    assert q10["runtime_form_contract"]["activities_per_form"] == 40
    assert q10["runtime_form_contract"]["runtime_connected"] is True
    assert q10["runtime_form_contract"]["final_forms_materialized"] is True
    assert q10["runtime_form_contract"]["within_form_same_task_family_selected_item_reuse"] is False
    assert q10["sentence_asset_integration"]["bound_runtime_occurrence_count"] == 128
    assert q10["full_unit02_approved_item_inventory_exported"] is True
    assert q10["full_runtime_occurrence_plan_exported"] is True


def test_u02fp01_q2_q3_q6_refs_and_read_only_boundaries():
    payload = _payload()
    assert payload["q2_q3_existing_export_ref"] == {
        "row_count": 162,
        "sha256": "7cfabb8834b7079cf8531d90b6a91576d6166ec9f92d917665c45884af59094d",
        "not_duplicated_in_this_export": True,
    }
    assert payload["q6_existing_export_ref"]["asset_count"] == 3726
    assert payload["q6_existing_export_ref"]["asset_digest"] == "121ff76cb48e92db7d7f8e1fadada89e0af0d7960a00a1e897d8e849e95364bc"
    assert payload["q6_existing_export_ref"]["export_sha256"] == payload["q6_existing_export_ref"]["asset_digest"]
    assert private_fields(payload) == []
    assert payload["claim_boundaries"] == {
        "readback_only": True,
        "canonical_content_created": False,
        "questionbank_items_created": False,
        "sentence_assets_created": False,
        "runtime_authority_created": False,
        "learner_state_mutated": False,
        "a2_unlocked": False,
    }


def test_u02fp01_export_payload_roundtrip_and_emit_only_on_export_branch(capsys):
    payload = _payload()
    raw = builder.canonical(payload).encode("utf-8")
    raw_sha256 = hashlib.sha256(raw).hexdigest()
    compressed = zlib.compress(raw, 9)
    encoded = base64.b64encode(compressed).decode("ascii")
    restored = json.loads(zlib.decompress(base64.b64decode(encoded)).decode("utf-8"))
    assert restored == payload

    if os.environ.get("GITHUB_HEAD_REF") == EXPORT_BRANCH:
        chunks = [encoded[index:index + 6000] for index in range(0, len(encoded), 6000)]
        with capsys.disabled():
            print("U02FP01_EXPORT_BEGIN")
            print(f"U02FP01_EXPORT_SHA256={raw_sha256}")
            print(f"U02FP01_EXPORT_CHUNK_COUNT={len(chunks)}")
            for ordinal, chunk in enumerate(chunks):
                print(f"U02FP01_EXPORT_CHUNK={ordinal:04d}:{chunk}")
            print("U02FP01_EXPORT_END")
