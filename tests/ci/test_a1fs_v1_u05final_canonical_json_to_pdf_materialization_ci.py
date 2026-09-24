from __future__ import annotations

import re
from pathlib import Path

from product.a1fs_v1_2_1 import (
    u05final_canonical_json_to_pdf_materialization as pdfmat,
)

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = ROOT / "product/a1fs_v1_2_1/pdf/unit05"

ENGINEERING_LABELS = (
    b"BE_FORM_SELECTION",
    b"ONE_WORD_BE_COMPLETION",
    b"AFFIRMATIVE_NEGATIVE_CONTRAST",
    b"SUBJECT_BE_AGREEMENT",
    b"SENTENCE_CORRECTION",
    b"CONTROLLED_SELF_PRODUCTION",
    b"SHORT_MESSAGE_MEANING",
    b"PERSON_TEXT_DETAIL_MATCHING",
    b"LONG_TEXT_DETAIL_INFERENCE",
    b"LEXICAL_CLOZE",
    b"OPEN_CLOZE",
    b"SHORT_COMMUNICATIVE_EMAIL",
    b"PERSONAL_INTERVIEW",
)

MEDIA_PENDING_LABELS = (
    b"PICTURE_SEQUENCE_STORY",
    b"AUDIO_PICTURE_DETAIL_SELECTION",
    b"AUDIO_NOTE_COMPLETION",
    b"AUDIO_CONVERSATION_DETAIL",
    b"SHORT_AUDIO_GIST_INTENT_DETAIL",
    b"AUDIO_LIST_MATCHING",
    b"COLLABORATIVE_VISUAL_DISCUSSION",
    b"DELAYED_DICTATION",
)


def _page_count(raw: bytes) -> int:
    return len(re.findall(rb"/Type /Page\b", raw))


def _fake_browser(
    chromium: Path,
    *,
    source_html: Path,
    output_path: Path,
    mode: str,
):
    assert chromium.is_file()
    assert source_html.is_file()
    assert mode == "PDF"
    html = source_html.read_text(encoding="utf-8")
    assert "<!doctype html>" in html.lower()
    payload = (
        b"%PDF-1.4\n"
        + source_html.stem.encode("ascii")
        + b"\n"
        + b"X" * 2048
        + b"\n%%EOF\n"
    )
    output_path.write_bytes(payload)
    return {
        "returncode": 0,
        "mode": mode,
        "source_path": str(source_html),
        "output_path": str(output_path),
    }


def test_u05final_v2_preserves_exact_executable_and_deferred_denominators():
    items, counts = pdfmat._items()
    assert len(items) == 816
    assert counts == {
        "core": 480,
        "ket_text": 336,
        "ket_media_pending": 336,
        "dictation_pending": 480,
    }


def test_u05final_v2_practice_html_is_learner_friendly_and_hides_engineering_ids():
    items, _ = pdfmat._items()
    rendered = pdfmat.render_practice_html(items)

    assert "Choose the correct be form" in rendered
    assert "Read a short message" in rendered
    assert "Write a short message" in rendered
    assert "Speak: personal answer" in rendered
    assert "Q001" in rendered
    assert "Q816" in rendered

    for marker in (
        "BE_FORM_SELECTION",
        "U05-FAR2-SET-",
        "U05-FAR7-",
    ):
        assert marker not in rendered

    for marker in pdfmat.MEDIA_PENDING_FAMILIES:
        assert marker not in rendered


def test_u05final_v2_answer_html_uses_compact_teacher_layout():
    items, _ = pdfmat._items()
    rendered = pdfmat.render_answer_html(items)

    assert 'class="answer-grid"' in rendered
    assert "Q001" in rendered
    assert "Q816" in rendered
    assert "Answer Key 816" in rendered
    assert "Choose the correct be form" in rendered


def test_u05final_v2_materializer_emits_two_pdf_deliverables(tmp_path: Path):
    chromium = tmp_path / "chromium"
    chromium.write_bytes(b"fake-browser")

    report = pdfmat.materialize(
        tmp_path / "out",
        chromium_path=chromium,
        browser_runner=_fake_browser,
    )

    assert report["status"] == pdfmat.PASS_STATUS
    assert report["executable_count"] == 816
    assert report["asset_pending_count"] == 816
    assert report["audio_generated"] is False
    assert report["visual_generated"] is False
    assert report["engineering_family_labels_visible"] is False
    assert report["unit05_closeout_ready"] is True

    for key in ("practice_pdf", "answer_pdf"):
        raw = Path(report[key]).read_bytes()
        assert raw.startswith(b"%PDF-1.4")
        assert raw.rstrip().endswith(b"%%EOF")


def test_u05final_v2_committed_pdfs_are_readable_and_redesigned():
    practice = COMMITTED / pdfmat.PRACTICE_PDF_NAME
    answers = COMMITTED / pdfmat.ANSWER_PDF_NAME

    for path in (practice, answers):
        assert path.is_file()
        raw = path.read_bytes()
        assert raw.startswith(b"%PDF-1.4")
        assert raw.rstrip().endswith(b"%%EOF")
        assert len(raw) > 100_000

    practice_raw = practice.read_bytes()
    answer_raw = answers.read_bytes()

    assert _page_count(practice_raw) >= 300
    # The v2 answer key is intentionally compact and two-column. FullFix can
    # shorten answer text without losing any Q001-Q816 coverage, so page count
    # is a layout sanity floor rather than a legacy >=60-page requirement.
    assert _page_count(answer_raw) >= 40

    assert b"Q001" in practice_raw
    assert b"Q816" in practice_raw
    assert b"Q001" in answer_raw
    assert b"Q816" in answer_raw

    assert b"Choose the correct be form" in practice_raw
    assert b"Read a short message" in practice_raw
    assert b"Write a short message" in practice_raw
    assert b"Speak: personal answer" in practice_raw

    for marker in ENGINEERING_LABELS:
        assert marker not in practice_raw
    for marker in MEDIA_PENDING_LABELS:
        assert marker not in practice_raw

    assert b"Answer Key 816" in answer_raw
    assert b"Choose the correct be form" in answer_raw
