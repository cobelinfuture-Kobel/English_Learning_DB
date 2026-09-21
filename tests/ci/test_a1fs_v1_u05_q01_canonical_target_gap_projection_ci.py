from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "ulga" / "contracts" / "a1fs_v1_u05_q01_canonical_target_gap_projection.json"
SEQUENCE = ROOT / "product" / "a1fs_v1_2_1" / "runtime" / "sequence.json"
QUERY_INDEX = ROOT / "ulga" / "graph" / "grammar_query_index.json"
MAPPING_BATCH = ROOT / "ulga" / "mappings" / "a1_verified_mapping_import_batch_02.json"
BUNDLES = ROOT / "product" / "a1fs_v1_2_1" / "runtime" / "bundles.json"
Q00 = ROOT / "ulga" / "contracts" / "a1fs_v1_u05_q00_unit04_successor_baseline.json"


EXPECTED_ROWS = {
    "1741163706530x753542801715210100",
    "1741163716067x824562184770361200",
    "1741163712047x409239658002596100",
    "1741163715288x262148040901666750",
    "1741163715288x539616242661052000",
    "1741163715608x123988758899529200",
}


def test_u05_q01_canonical_target_and_gap_projection() -> None:
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    sequence = json.loads(SEQUENCE.read_text(encoding="utf-8"))
    query = json.loads(QUERY_INDEX.read_text(encoding="utf-8"))
    mapping = json.loads(MAPPING_BATCH.read_text(encoding="utf-8"))
    bundles = json.loads(BUNDLES.read_text(encoding="utf-8"))
    q00 = json.loads(Q00.read_text(encoding="utf-8"))

    assert data["status"] == "PASS_A1FS_V1_U05Q01_UNIT05_CANONICAL_TARGET_AND_GAP_PROJECTION"
    assert data["unit_number"] == 5
    assert data["unit_id"] == "GRAMMAR_BE_VERB_BASIC"

    assert sequence["GRAMMAR_BASIC_PREPOSITIONS_PLACE"] == 4
    assert sequence["GRAMMAR_BE_VERB_BASIC"] == 5
    assert sequence["GRAMMAR_CAN_STATEMENT"] == 6

    canonical = query["by_grammar_id"]["GRAMMAR_BE_VERB_BASIC"]["canonical_a1_mapping"]
    assert canonical["mapping_reference_status"] == "VERIFIED_CANONICAL_MAPPING"
    assert set(canonical["egp_row_ids"]) == EXPECTED_ROWS

    be_unit = next(
        unit for unit in mapping["mapping_import_units"]
        if unit["grammar_id"] == "GRAMMAR_BE_VERB_BASIC"
    )
    assert be_unit["split_bucket_id"] == "GRAMMAR_BE_COPULA_BASIC_STATEMENTS"
    assert set(be_unit["new_unique_egp_row_ids"]) == EXPECTED_ROWS

    target_rows = data["canonical_target"]["egp_rows"]
    assert len(target_rows) == 6
    assert {row["egp_row_id"] for row in target_rows} == EXPECTED_ROWS

    gap = data["real_gap_projection"]
    assert gap["canonical_egp_rows_total"] == 6
    assert gap["rows_with_reusable_direct_or_skeleton_carrier"] == 4
    assert gap["rows_with_direct_target_gap"] == 2
    assert set(gap["direct_target_gap_row_ids"]) == {
        "1741163716067x824562184770361200",
        "1741163715288x262148040901666750",
    }

    assert gap["sentence_asset_gap"]["current_unit_canonical_q06_sentence_asset_count"] == 0
    assert gap["sentence_asset_gap"]["predecessor_pool_for_reuse_and_dedup"] == 26610
    assert gap["sentence_asset_gap"]["exact_new_sentence_count"] is None

    assert gap["scene_gap"]["new_global_scene_family_required"] == 0
    assert gap["scene_gap"]["existing_governed_scene_family_count"] == 17
    assert gap["scene_gap"]["current360_micro_scene_count"] == 36

    assert gap["reader_gap"] == {
        "new_reader_required": 0,
        "current360_reusable": True,
        "spoken360_reusable": True,
        "pattern360_reusable": True,
        "rule": "Reuse or derive Unit05 overlays from the three existing Reader360 banks; do not create a fourth Reader.",
    }

    unit05_bundle_keys = [
        key for key in bundles
        if "GRAMMAR_BE_VERB_BASIC" in key
    ]
    assert sorted(unit05_bundle_keys) == sorted([
        "A1FS_ONLINE_V1:GRAMMAR_BE_VERB_BASIC:READING",
        "A1FS_ONLINE_V1:GRAMMAR_BE_VERB_BASIC:WRITING",
        "A1FS_ONLINE_V1:GRAMMAR_BE_VERB_BASIC:SPEAKING",
    ])
    assert len(bundles["A1FS_ONLINE_V1:GRAMMAR_BE_VERB_BASIC:READING"]["assets"]) == 4
    assert len(bundles["A1FS_ONLINE_V1:GRAMMAR_BE_VERB_BASIC:WRITING"]["assets"]) == 4
    assert len(bundles["A1FS_ONLINE_V1:GRAMMAR_BE_VERB_BASIC:SPEAKING"]["assets"]) == 3

    assert q00["status"] == "PASS_A1FS_V1_U05Q00_UNIT04_COMPLETE_PACKAGE_SUCCESSOR_BASELINE"
    assert q00["archive_audit"]["content_files_readable"] == 69
    assert q00["exact_predecessor_denominator"]["cumulative_sentence_assets"] == 26610
    assert q00["exact_predecessor_denominator"]["governed_scene_family_count"] == 17

    scope = data["scope"]
    assert scope["learner_content_materialized"] is False
    assert scope["vocabulary_authority_materialized"] is False
    assert scope["form_authority_materialized"] is False
    assert scope["chunk_authority_materialized"] is False
    assert scope["frame_authority_materialized"] is False
    assert scope["sentence_assets_materialized"] is False
    assert scope["questionbank_materialized"] is False
    assert scope["forms_materialized"] is False
    assert scope["a2_a2plus_unlocked"] is False

    boundaries = data["claim_boundaries"]
    assert boundaries["incidental_reader_usage_does_not_equal_current_unit_authority"] is True
    assert boundaries["runtime_skeleton_does_not_equal_q01_q10_canonical_authority"] is True
    assert boundaries["auxiliary_be_row_is_not_silently_dropped"] is True
    assert boundaries["progressive_auxiliary_usage_requires_explicit_q03_boundary"] is True

    assert data["next_short_step"] == "A1FS-V1-U05Q02_Unit05VocabularyAuthorityAndReusableCarrierAdmission"
