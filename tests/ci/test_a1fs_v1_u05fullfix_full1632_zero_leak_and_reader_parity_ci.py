from __future__ import annotations

from product.a1fs_v1_2_1 import (
    u05fullfix_full1632_zero_leak_and_reader_parity as closeout,
)

REPORT = closeout.build_report()


def test_u05fullfix_reader_consolidated_shard_parity():
    assert REPORT["status"] == closeout.STATUS
    assert REPORT["reader_counts"] == {
        "current360": 360,
        "spoken360": 360,
        "pattern360": 360,
    }
    assert REPORT["current_exact_shard_equality"] is True
    assert REPORT["spoken_exact_shard_equality"] is True
    assert REPORT["pattern_exact_shard_equality"] is True


def test_u05fullfix_full1632_identity_and_balances():
    assert REPORT["full1632_count"] == 1632
    assert REPORT["unique_practice_id_count"] == 1632
    assert REPORT["unique_source_slot_id_count"] == 1632
    assert len(REPORT["core_archetype_counts"]) == 6
    assert set(REPORT["core_archetype_counts"].values()) == {80}
    assert len(REPORT["ket_family_counts"]) == 14
    assert set(REPORT["ket_family_counts"].values()) == {48}


def test_u05fullfix_zero_irregular_plural_leak_across_readers_shards_and_practice():
    assert REPORT["banned_irregular_plural_tokens"] == [
        "children",
        "people",
        "feet",
        "men",
        "women",
    ]
    assert REPORT["zero_leak_artifact_count"] == 30
    assert REPORT["zero_leak_violation_count"] == 0


def test_u05fullfix_dictation_exact_spoken_and_retention_lineage():
    assert REPORT["dictation_spoken360_mismatch_count"] == 0
    assert REPORT["dictation_d2_lineage_mismatch_count"] == 0


def test_u05fullfix_advances_to_compact_pdf_regeneration():
    assert REPORT["next_short_step"] == closeout.NEXT_SHORT_STEP
