from product.a1fs_v1_2_1 import u06r360p03h1_full_artifact_handoff as h1


def report():
    return h1.build_report()


def test_u06_r2_handoff_has_complete_exact_join_jsons():
    r = report()
    assert r["status"] == h1.STATUS
    assert r["source_join_exact"] is True
    assert r["current360"]["episode_count"] == 360
    assert r["current360"]["sentence_range"] == "6_TO_8"
    assert r["spoken360"]["entry_count"] == 360
    assert r["spoken360"]["turn_range"] == "6_TO_8"


def test_u06_r2_handoff_has_two_full_60_page_pdfs():
    r = report()
    assert r["current360"]["pdf_page_count"] == 60
    assert r["current360"]["cards_per_page"] == 6
    assert r["current360"]["pdf_bytes"] > 0
    assert r["spoken360"]["pdf_page_count"] == 60
    assert r["spoken360"]["cards_per_page"] == 6
    assert r["spoken360"]["pdf_bytes"] > 0


def test_u06_r2_handoff_records_gpt_rewrite_and_scope_lock():
    r = report()
    s = r["scope_safety"]
    assert s["current360_rewritten_by_gpt56"] is True
    assert s["spoken360_rewritten_by_gpt56"] is True
    assert s["current360_rewritten_by_python"] is False
    assert s["spoken360_rewritten_by_python"] is False
    assert s["pattern360_materialized"] is False
    assert s["a2_a2plus_unlocked"] is False
    assert r["next_short_step"] == h1.NEXT_SHORT_STEP
