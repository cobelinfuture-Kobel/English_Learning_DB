from __future__ import annotations

import re
from pathlib import Path

from product.a1fs_v1_2_1 import u06r360p02r1_current360_card_pdf_materialization as m

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / "product/a1fs_v1_2_1/pdf/unit06/unit06_current360_cards_45p.pdf"


def test_u06_current360_card_pdf_layout_and_counts_are_exact() -> None:
    report = m.build_report()
    assert report["status"] == m.STATUS
    assert report["layout"] == "A4_PORTRAIT_2_COLUMNS_X_4_ROWS_8_CARDS_PER_PAGE"
    assert report["source_episode_count"] == 360
    assert report["cards_per_page"] == 8
    assert report["page_count"] == 45
    assert report["first_episode_id"] == "U06-NEB-E001"
    assert report["last_episode_id"] == "U06-NEB-E360"


def test_u06_current360_card_pdf_is_deterministic_projection_of_merged_source() -> None:
    committed = PDF.read_bytes()
    rebuilt = m.build_pdf_bytes()
    assert committed == rebuilt
    assert committed.startswith(b"%PDF-1.4")
    assert committed.rstrip().endswith(b"%%EOF")
    assert len(re.findall(rb"/Type /Page\b", committed)) == 45
    assert committed.count(b"Target: ") == 360
    assert b"U06-NEB-E001 | U06-N360-S001" in committed
    assert b"U06-NEB-E360 | U06-N360-S360" in committed


def test_u06_current360_card_projection_does_not_rewrite_learner_english() -> None:
    episodes = m._load_episodes()
    assert len(episodes) == 360
    for row in episodes:
        paragraph = str(row["paragraph"])
        wrapped = m._wrap(paragraph)
        assert " ".join(wrapped) == paragraph
        stream = m._page_stream([row], 1)
        assert all(m._escape_pdf_text(line) in stream for line in wrapped)
        assert row["gpt56_semantic_review"] == "PASS"
        assert row["natural_style_review"] == "PASS"


def test_u06_current360_card_repair_preserves_scope_boundary() -> None:
    report = m.build_report()
    assert report["learner_facing_source_text_rewritten"] is False
    assert report["spoken360_modified"] is False
    assert report["pattern360_modified"] is False
    assert report["q01_q10_modified"] is False
    assert report["a2_a2plus_unlocked"] is False


def test_u06_current360_card_typography_matches_human_approved_large_font_contract() -> None:
    assert m.ID_SIZE == 9.4
    assert m.TARGET_SIZE == 10.2
    assert m.BODY_SIZE == 13.5
    assert m.BODY_LEADING == 16.0
    assert m.FOOTER_SIZE == 7.5
    episodes = m._load_episodes()
    line_counts = [len(m._wrap(str(row["paragraph"]))) for row in episodes]
    assert max(line_counts) <= 6
    assert len(line_counts) == 360
    assert m.build_report()["page_count"] == 45
