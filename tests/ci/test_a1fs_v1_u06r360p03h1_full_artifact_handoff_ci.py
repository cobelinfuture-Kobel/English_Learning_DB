from __future__ import annotations

from product.a1fs_v1_2_1 import u06r360p03h1_full_artifact_handoff as h1


def report():
    return h1.build_report()


def test_u06_full_handoff_has_both_complete_json_artifacts():
    r = report()
    assert r["status"] == h1.STATUS
    assert r["source_join_exact"] is True
    assert r["current360"]["episode_count"] == 360
    assert r["spoken360"]["entry_count"] == 360


def test_u06_full_handoff_has_actual_current_and_spoken_pdfs():
    r = report()
    assert r["current360"]["pdf_page_count"] == 45
    assert r["current360"]["cards_per_page"] == 8
    assert r["current360"]["pdf_bytes"] > 0
    assert r["spoken360"]["pdf_page_count"] == 60
    assert r["spoken360"]["cards_per_page"] == 6
    assert r["spoken360"]["pdf_bytes"] > 0


def test_u06_full_handoff_keeps_scope_locked():
    r = report()
    safety = r["scope_safety"]
    assert safety["current360_rewritten"] is False
    assert safety["spoken360_rewritten_by_python"] is False
    assert safety["pattern360_materialized"] is False
    assert safety["a2_a2plus_unlocked"] is False
    assert r["next_short_step"] == h1.NEXT_SHORT_STEP
