from __future__ import annotations

import re
from pathlib import Path

from product.a1fs_v1_2_1 import (
    u05final_canonical_json_to_pdf_materialization as pdfmat,
)

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = ROOT / "product/a1fs_v1_2_1/pdf/unit05"


def _page_count(raw: bytes) -> int:
    return len(re.findall(rb"/Type /Page\b", raw))


def test_u05final_materializes_exact_executable_and_deferred_denominators(
    tmp_path: Path,
):
    report = pdfmat.materialize(tmp_path / "pdf")
    assert report["status"] == pdfmat.PASS_STATUS
    assert report["executable_count"] == 816
    assert report["asset_pending_count"] == 816
    assert report["core"] == 480
    assert report["ket_text"] == 336
    assert report["ket_media_pending"] == 336
    assert report["dictation_pending"] == 480
    assert report["audio_generated"] is False
    assert report["visual_generated"] is False
    assert report["unit05_closeout_ready"] is True


def test_u05final_materialized_pdfs_are_nontrivial_and_machine_readable(
    tmp_path: Path,
):
    report = pdfmat.materialize(tmp_path / "pdf")
    for key in ("practice_pdf", "answer_pdf"):
        raw = Path(report[key]).read_bytes()
        assert raw.startswith(b"%PDF-1.4")
        assert raw.rstrip().endswith(b"%%EOF")
        assert len(raw) > 100_000
        assert _page_count(raw) > 20


def test_u05final_practice_excludes_deferred_media_families(
    tmp_path: Path,
):
    report = pdfmat.materialize(tmp_path / "pdf")
    raw = Path(report["practice_pdf"]).read_bytes()

    for marker in (
        b"AUDIO_PICTURE_DETAIL_SELECTION",
        b"AUDIO_NOTE_COMPLETION",
        b"AUDIO_CONVERSATION_DETAIL",
        b"SHORT_AUDIO_GIST_INTENT_DETAIL",
        b"AUDIO_LIST_MATCHING",
        b"COLLABORATIVE_VISUAL_DISCUSSION",
        b"PICTURE_SEQUENCE_STORY",
        b"DELAYED_DICTATION",
    ):
        assert marker not in raw

    for marker in (
        b"BE_FORM_SELECTION",
        b"SHORT_MESSAGE_MEANING",
        b"PERSONAL_INTERVIEW",
    ):
        assert marker in raw


def test_u05final_committed_pdf_delivery_matches_closeout_contract():
    practice = COMMITTED / "unit05_executable_practice_816.pdf"
    answers = COMMITTED / "unit05_answer_key_816.pdf"

    for path in (practice, answers):
        assert path.is_file()
        raw = path.read_bytes()
        assert raw.startswith(b"%PDF-1.4")
        assert raw.rstrip().endswith(b"%%EOF")
        assert len(raw) > 100_000
        assert _page_count(raw) > 20

    practice_raw = practice.read_bytes()
    answer_raw = answers.read_bytes()

    assert b"Q1." in practice_raw
    assert b"Q816." in practice_raw
    assert b"Q1." in answer_raw
    assert b"Q816." in answer_raw
    assert b"U05-FAR7-CORE-0001" in answer_raw
    assert b"Audio and visual assets are not fabricated" in practice_raw
