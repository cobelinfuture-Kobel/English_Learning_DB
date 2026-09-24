from __future__ import annotations
from product.a1fs_v1_2_1 import u05far7_core480_gpt56_materialization as core
REPORT=core.build_report()

def test_u05_far7_core480_reader360_backed_full_materialization():
    assert REPORT["status"]==core.STATUS
    assert REPORT["core_authored_count"]==480
    assert REPORT["deterministic_count"]==400
    assert REPORT["productive_count"]==80
    assert REPORT["sentence_correction_count"]==80
    assert REPORT["unique_target_sentence_count"]==480
    assert REPORT["unique_activity_signature_count"]==480

def test_u05_far7_core480_reader360_source_mix_and_context_progression():
    assert REPORT["pattern360_target_count"]==372
    assert REPORT["controlled_transfer_target_count"]==108
    assert REPORT["visible_context_count"]==240
    assert REPORT["legacy_static_template_bank_retired"] is True

def test_u05_far7_core480_review_and_archetype_balance():
    assert REPORT["all_gpt56_reviews_pass"] is True
    assert REPORT["archetype_count"]==6

def test_u05_far7_core480_advances_to_ket_text_first():
    assert REPORT["next_short_step"]==core.NEXT_SHORT_STEP
