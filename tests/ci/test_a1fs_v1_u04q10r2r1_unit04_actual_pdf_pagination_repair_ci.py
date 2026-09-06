from __future__ import annotations

from pathlib import Path

import pytest

from product.a1fs_v1_2_1 import (
    u04q10r1_unit04_learner_facing_pedagogical_acceptance as u04r1,
)
from product.a1fs_v1_2_1 import (
    u04q10r2r1_unit04_actual_pdf_pagination_repair as r1,
)


def _fake_browser_runner(
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
    assert html.count(r1.PDF_PAGINATION_STYLE_ID) == 1
    assert "article.activity { break-inside: avoid; page-break-inside: avoid; }" in html
    assert ".unit04-section > h2 { break-after: avoid; page-break-after: avoid; }" in html
    assert html.count('<article class="activity">') == 40
    ordinal = source_html.stem
    payload = (
        b"%PDF-1.4\n"
        + f"FAKE-U04-R1-{ordinal}\n".encode("ascii")
        + (ordinal.encode("ascii") * 700)
        + b"\n%%EOF\n"
    )
    output_path.write_bytes(payload)
    return {
        "returncode": 0,
        "mode": mode,
        "source_path": str(source_html),
        "output_path": str(output_path),
        "browser": str(chromium),
    }


def _fake_page_counter(path: Path) -> int:
    assert path.is_file()
    return 5


def test_u04q10r2r1_print_css_preserves_exact_learner_html_except_style():
    source = u04r1.build_acceptance_report()
    form = source["learner_forms"][0]
    original = u04r1.render_form_html(form)
    repaired = r1.render_form_html_for_pdf(form)

    assert r1.PDF_PAGINATION_STYLE_ID not in original
    assert repaired.count(r1.PDF_PAGINATION_STYLE_ID) == 1
    assert repaired.replace(r1.PDF_PAGINATION_STYLE, "", 1) == original
    assert repaired.count('<article class="activity">') == 40
    assert "break-inside: avoid" in repaired
    assert "page-break-inside: avoid" in repaired
    assert "break-after: avoid" in repaired
    assert "page-break-after: avoid" in repaired


def test_u04q10r2r1_materializes_twenty_guarded_forms_without_identity_drift(
    tmp_path: Path,
):
    source = u04r1.build_acceptance_report()
    original_renderer = u04r1.render_form_html
    chromium = tmp_path / "chromium.exe"
    chromium.write_bytes(b"fake-browser")

    manifest = r1.materialize_twenty_form_pdfs(
        output_root=tmp_path / "out",
        chromium_path=chromium,
        browser_runner=_fake_browser_runner,
        pdf_page_counter=_fake_page_counter,
        source_report=source,
    )

    assert u04r1.render_form_html is original_renderer
    assert manifest["pagination_repair_task_id"] == r1.TASK_ID
    assert manifest["pagination_repair_status"] == r1.PASS_STATUS
    assert manifest["form_count"] == 20
    assert manifest["materialized_pdf_count"] == 20
    assert manifest["materialized_html_count"] == 20
    assert manifest["materialized_activity_count"] == 800
    assert manifest["pdf_pagination_guard_form_count"] == 20
    assert manifest["pdf_pagination_guard_activity_count"] == 800
    assert manifest["pdf_pagination_policy"] == {
        "activity_break_inside": "avoid",
        "section_heading_break_after": "avoid",
        "print_only": True,
        "learner_text_mutated": False,
        "learner_activity_markup_mutated": False,
    }
    assert (
        manifest["source_runtime_identity_sha256"]
        == source["source_runtime_identity_sha256"]
    )
    assert (
        manifest["source_item_identity_sha256"]
        == source["source_item_identity_sha256"]
    )
    assert manifest["source_800_runtime_rows_mutated"] is False
    assert manifest["source_selected_item_identities_mutated"] is False
    assert manifest["questionbank_modified"] is False
    assert manifest["sentence_assets_modified"] is False
    assert manifest["scene_authority_modified"] is False
    assert manifest["q10_redone"] is False
    assert manifest["next_short_step"] == r1.NEXT_SHORT_STEP
    assert all(row["page_count"] == 5 for row in manifest["artifacts"])

    for ordinal in range(1, 21):
        html = (tmp_path / "out" / "html" / f"Form{ordinal:02d}.html").read_text(
            encoding="utf-8"
        )
        assert html.count(r1.PDF_PAGINATION_STYLE_ID) == 1
        assert html.count('<article class="activity">') == 40


def test_u04q10r2r1_fails_closed_if_pagination_style_is_already_present():
    with pytest.raises(
        r1.Unit04PdfPaginationRepairError,
        match="PAGINATION_STYLE_ALREADY_PRESENT",
    ):
        r1.inject_pdf_pagination_guards(
            f"<html><head>{r1.PDF_PAGINATION_STYLE}</head><body></body></html>"
        )
