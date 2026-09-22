from __future__ import annotations

from product.a1fs_v1_2_1 import u05r360p04h1_consolidated_json_handoff as handoff


def test_u05_r360_p04h1_consolidated_json_handoff():
    r = handoff.build_report()
    assert r["status"] == handoff.STATUS
    assert r["current360_count"] == 360
    assert r["spoken360_count"] == 360
    assert r["pattern360_count"] == 360
    assert r["pattern360_example_count"] == 4675
    assert r["spoken_exact_shard_equality"] is True
    assert r["pattern_exact_shard_equality"] is True
    assert r["learner_facing_language_rewritten_during_consolidation"] is False
    assert r["next_short_step"] == handoff.NEXT_SHORT_STEP
