from __future__ import annotations
from product.a1fs_v1_2_1 import u05far7_dictation480_gpt56_materialization as dct
REPORT=dct.build_report()

def test_u05_far7_dictation480_full_authoring_and_asset_boundary():
    assert REPORT["status"]==dct.STATUS
    assert REPORT["dictation_authored_count"]==480
    assert REPORT["d1_count"]==360
    assert REPORT["d2_count"]==120
    assert REPORT["asset_pending_count"]==480
    assert REPORT["executable_count"]==0

def test_u05_far7_dictation480_exact_source_and_retention_linkage():
    assert REPORT["all_gpt56_reviews_pass"] is True
    assert REPORT["all_transcripts_exact_spoken360"] is True
    assert REPORT["all_d2_reuse_d1_core_target"] is True

def test_u05_far7_dictation480_advances_to_full_authoring_closeout():
    assert REPORT["next_short_step"]==dct.NEXT_SHORT_STEP
