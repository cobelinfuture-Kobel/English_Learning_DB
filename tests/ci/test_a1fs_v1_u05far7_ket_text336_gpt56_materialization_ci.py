from __future__ import annotations
from product.a1fs_v1_2_1 import u05far7_ket_text336_gpt56_materialization as ket
REPORT=ket.build_report()

def test_u05_far7_ket_text336_full_denominator():
    assert REPORT["status"]==ket.STATUS
    assert REPORT["ket_text_authored_count"]==336
    assert REPORT["ket_media_pending_count"]==336
    assert set(REPORT["text_family_counts"])==ket.TEXT_FAMILIES
    assert set(REPORT["text_family_counts"].values())=={48}

def test_u05_far7_ket_text336_answer_modes_and_bundle_review():
    assert REPORT["matching_bundle_review_pass_count"]==48
    assert REPORT["deterministic_count"]==240
    assert REPORT["productive_count"]==48
    assert REPORT["oral_count"]==48
    assert REPORT["all_gpt56_reviews_pass"] is True

def test_u05_far7_ket_text336_advances_to_asset_dependent():
    assert REPORT["next_short_step"]==ket.NEXT_SHORT_STEP
