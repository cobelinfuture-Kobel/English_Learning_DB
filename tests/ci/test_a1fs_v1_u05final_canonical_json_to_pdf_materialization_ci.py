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

def _fake_browser(chromium: Path, *, source_html: Path, output_path: Path, mode: str):
    assert chromium.is_file()
    assert source_html.is_file()
    assert mode == "PDF"
    html = source_html.read_text(encoding="utf-8")
    assert "<!doctype html>" in html.lower()
    payload = b"%PDF-1.4\n" + source_html.stem.encode("ascii") + b"\n" + b"X" * 2048 + b"\n%%EOF\n"
    output_path.write_bytes(payload)
    return {"returncode":0,"mode":mode,"source_path":str(source_html),"output_path":str(output_path)}

def test_u05final_v2_preserves_exact_executable_and_deferred_denominators():
    items, counts = pdfmat._items()
    assert len(items) == 816
    assert counts == {"core":480,"ket_text":336,"ket_media_pending":336,"dictation_pending":480}

def test_u05final_v2_core480_html_blocks_known_semantic_regressions():
    items, _ = pdfmat._items()
    core = items[:480]
    assert len({row["learner_facing_content"]["learner_target_sentence"] for row in core}) == 480
    assert len({
        (
            row["learner_facing_content"]["prompt"],
            repr(row["response_contract"].get("options")),
            repr((row["learner_facing_content"].get("stimulus") or {}).get("text")),
            repr(row["learner_facing_content"].get("model_sentence")),
        )
        for row in core
    }) == 480
    assert all(
        row["learner_facing_content"]["subject_cue"] in row["learner_facing_content"]["prompt"]
        for row in core
        if row["target_archetype"] in {"BE_FORM_SELECTION","ONE_WORD_BE_COMPLETION","SUBJECT_BE_AGREEMENT"}
    )
    rendered = pdfmat.render_practice_html(items)
    assert "The students ___ students." not in rendered
    assert "The students ___ not students." not in rendered
    assert "<b>Example</b>" not in rendered[: rendered.find("Q481") if "Q481" in rendered else len(rendered)]
    assert "<b>Context</b>" in rendered

def test_u05final_v2_practice_html_is_learner_friendly_and_hides_engineering_ids():
    items, _ = pdfmat._items()
    rendered = pdfmat.render_practice_html(items)
    assert "Choose the correct be form" in rendered
    assert "Read a short message" in rendered
    assert "Write a short message" in rendered
    assert "Speak: personal answer" in rendered
    assert "Q001" in rendered and "Q816" in rendered
    for marker in ("BE_FORM_SELECTION","U05-FAR2-SET-","U05-FAR7-"):
        assert marker not in rendered
    for marker in pdfmat.MEDIA_PENDING_FAMILIES:
        assert marker not in rendered

def test_u05final_v2_multisentence_writing_renders_sentence_plan_and_final_version():
    items, _ = pdfmat._items()
    email_items=[row for row in items if row.get("task_family")=="SHORT_COMMUNICATIVE_EMAIL"]
    assert len(email_items)==48
    assert all(row["response_contract"].get("final_integration_required") is True for row in email_items)
    rendered=pdfmat.render_practice_html(items)
    assert rendered.count("<b>Final version</b>")==48
    assert rendered.count("<b>Sentence 1</b>")>=48
    assert rendered.count("<b>Sentence 2</b>")>=48

def test_u05final_v2_answer_html_uses_compact_teacher_layout():
    items, _ = pdfmat._items()
    rendered = pdfmat.render_answer_html(items)
    assert 'class="answer-grid"' in rendered
    assert "Q001" in rendered and "Q816" in rendered
    assert "Answer Key 816" in rendered
    assert "Choose the correct be form" in rendered

def test_u05final_v2_materializer_emits_two_pdf_deliverables(tmp_path: Path):
    chromium = tmp_path / "chromium"
    chromium.write_bytes(b"fake-browser")
    report = pdfmat.materialize(tmp_path / "out", chromium_path=chromium, browser_runner=_fake_browser)
    assert report["status"] == pdfmat.PASS_STATUS
    assert report["executable_count"] == 816
    assert report["asset_pending_count"] == 816
    assert report["audio_generated"] is False
    assert report["visual_generated"] is False
    assert report["engineering_family_labels_visible"] is False
    assert report["unit05_closeout_ready"] is True
    for key in ("practice_pdf","answer_pdf"):
        raw=Path(report[key]).read_bytes()
        assert raw.startswith(b"%PDF-1.4") and raw.rstrip().endswith(b"%%EOF")

def test_u05final_v2_committed_pdfs_are_readable_and_redesigned():
    practice = COMMITTED / pdfmat.PRACTICE_PDF_NAME
    answers = COMMITTED / pdfmat.ANSWER_PDF_NAME
    for path in (practice, answers):
        assert path.is_file()
        raw=path.read_bytes()
        assert raw.startswith(b"%PDF-1.4") and raw.rstrip().endswith(b"%%EOF")
        assert len(raw)>100_000
    assert _page_count(practice.read_bytes()) >= 300
    assert _page_count(answers.read_bytes()) >= 40
