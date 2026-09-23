from __future__ import annotations
from product.a1fs_v1_2_1 import u05far7_full1632_identity_materialization as far7
REPORT=far7.build_report()

def test_u05_far7_identity_denominators():
    assert REPORT["status"]==far7.STATUS
    assert REPORT["core_identity_count"]==480
    assert REPORT["ket_identity_count"]==672
    assert REPORT["dictation_identity_count"]==480
    assert REPORT["total_identity_count"]==1632

def test_u05_far7_identity_tracks_monotonic_authoring_without_changing_identity():
    assert 0 <= REPORT["core_authored_item_count"] <= 480
    assert 0 <= REPORT["ket_authored_item_count"] <= 672
    assert 0 <= REPORT["dictation_authored_item_count"] <= 480
    assert REPORT["authored_item_count"] == (
        REPORT["core_authored_item_count"]
        + REPORT["ket_authored_item_count"]
        + REPORT["dictation_authored_item_count"]
    )
    assert 0 <= REPORT["authored_item_count"] <= 1632
    assert REPORT["multi_source_bundle_review_required_count"]==96

def test_u05_far7_identity_advances_within_far7():
    assert REPORT["next_short_step"]==far7.NEXT_SHORT_STEP
