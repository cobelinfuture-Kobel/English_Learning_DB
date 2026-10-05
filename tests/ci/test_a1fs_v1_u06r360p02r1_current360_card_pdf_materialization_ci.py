from __future__ import annotations

import re
from pathlib import Path

from product.a1fs_v1_2_1 import u06r360p02r1_current360_card_pdf_materialization as m

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / "product/a1fs_v1_2_1/pdf/unit06/unit06_current360_cards_60p.pdf"


def test_u06_current360_r2_pdf_layout_counts_and_large_font():
    r = m.build_report()
    assert r["status"] == m.STATUS
    assert r["layout"] == "A4_PORTRAIT_2_COLUMNS_X_3_ROWS_6_CARDS_PER_PAGE"
    assert r["source_episode_count"] == 360
    assert r["cards_per_page"] == 6
    assert r["page_count"] == 60
    assert r["body_pt"] == 13.5
    assert r["max_body_line_count"] <= 8


def test_u06_current360_r2_committed_pdf_has_all_cards_and_range():
    raw = PDF.read_bytes()
    assert raw.startswith(b"%PDF-1.4")
    assert raw.rstrip().endswith(b"%%EOF")
    assert len(re.findall(rb"/Type /Page\\b", raw)) == 60
    assert raw.count(b"Target: ") == 360
    assert b"U06-NEB-E001 | U06-N360-S001" in raw
    assert b"U06-NEB-E360 | U06-N360-S360" in raw


def test_u06_current360_r2_pdf_projection_preserves_scope():
    for row in m._load_episodes():
        assert 6 <= m._sentence_count(row["paragraph"]) <= 8
    r = m.build_report()
    assert r["learner_facing_source_text_rewritten_by_pdf_builder"] is False
    assert r["q01_q10_modified"] is False
    assert r["pattern360_modified"] is False
    assert r["a2_a2plus_unlocked"] is False
