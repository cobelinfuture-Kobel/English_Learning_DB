from __future__ import annotations

from pathlib import Path

import pytest

from product.a1fs_v1_2_1 import (
    u05q10r1_unit05_learner_facing_pedagogical_acceptance as u05r1,
)
from product.a1fs_v1_2_1 import (
    u05q10r2_unit05_learner_pdf_materialization_and_visual_acceptance as pdfmat,
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
    assert html.count(pdfmat.PDF_PAGINATION_STYLE_ID) == 1
    assert ".unit05-section > h2 { break-after: avoid; page-break-after: avoid; }" in html
    assert "article.activity { break-inside: avoid; page-break-inside: avoid; }" in html
    assert html.count('<article class="activity">') == 40
    ordinal = source_html.stem
    payload = (
        b"%PDF-1.4\n"
        + f"FAKE-U05-{ordinal}\n".encode("ascii")
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


def test_u05q10r2_print_css_preserves_exact_q10r1_learner_html_except_style():
    source = u05r1.build_acceptance_report()
    form = source["learner_forms"][0]
    original = u05r1.render_form_html(form)
    guarded = pdfmat.render_form_html_for_pdf(form)

    assert pdfmat.PDF_PAGINATION_STYLE_ID not in original
    assert guarded.count(pdfmat.PDF_PAGINATION_STYLE_ID) == 1
    assert guarded.replace(pdfmat.PDF_PAGINATION_STYLE, "", 1) == original
    assert guarded.count('<article class="activity">') == 40
    assert "break-inside: avoid" in guarded
    assert "page-break-inside: avoid" in guarded
    assert "break-after: avoid" in guarded
    assert "page-break-after: avoid" in guarded


def test_u05q10r2_rejects_duplicate_pagination_style_injection():
    with pytest.raises(
        pdfmat.Unit05PdfMaterializationError,
        match="PAGINATION_STYLE_ALREADY_PRESENT",
    ):
        pdfmat.inject_pdf_pagination_guards(
            f"<html><head>{pdfmat.PDF_PAGINATION_STYLE}</head><body></body></html>"
        )


def test_u05q10r2_validates_q10r1_as_sole_direct_content_source():
    report = u05r1.build_acceptance_report()
    forms = pdfmat._validate_source(report)
    assert len(forms) == 20
    assert report["alignment_reference"]["unit04_content_authority_consumed"] is False
    assert report["alignment_reference"]["unit05_q10_is_sole_direct_content_source"] is True
    assert report["acceptance"]["unit04_content_authority_consumed_count"] == 0


def test_u05q10r2_materializes_twenty_pdfs_with_machine_visual_preflight(tmp_path: Path):
    source = u05r1.build_acceptance_report()
    chromium = tmp_path / "chromium.exe"
    chromium.write_bytes(b"fake-browser")

    manifest = pdfmat.materialize_twenty_form_pdfs(
        output_root=tmp_path / "out",
        chromium_path=chromium,
        browser_runner=_fake_browser_runner,
        pdf_page_counter=_fake_page_counter,
        source_report=source,
    )

    assert manifest["validation_status"] == pdfmat.PASS_STATUS
    assert manifest["form_count"] == 20
    assert manifest["materialized_html_count"] == 20
    assert manifest["materialized_pdf_count"] == 20
    assert manifest["materialized_activity_count"] == 800
    assert manifest["pdf_pagination_guard_form_count"] == 20
    assert manifest["pdf_pagination_guard_activity_count"] == 800
    assert manifest["machine_preflight_pass_count"] == 20
    assert manifest["learner_facing_machine_acceptance_pass_count"] == 20
    assert manifest["human_visual_review_pending_count"] == 20
    assert manifest["human_pedagogical_review_pending_count"] == 20
    assert manifest["unit05_form01_20_pdf_machine_acceptance"] == (
        "PASS_MACHINE_LEARNER_FACING_ACCEPTANCE"
    )
    assert manifest["unit05_form01_20_human_acceptance"] == (
        "PENDING_HUMAN_VISUAL_PEDAGOGICAL_REVIEW"
    )
    assert len(manifest["artifacts"]) == 20
    assert len({row["pdf_sha256"] for row in manifest["artifacts"]}) == 20
    assert all(row["page_count"] == 5 for row in manifest["artifacts"])
    assert all(row["pagination_guard"] == "PASS" for row in manifest["artifacts"])

    for ordinal in range(1, 21):
        html_path = tmp_path / "out" / "html" / f"Form{ordinal:02d}.html"
        pdf_path = tmp_path / "out" / "pdf" / f"Form{ordinal:02d}.pdf"
        assert html_path.is_file()
        assert pdf_path.is_file()
        html = html_path.read_text(encoding="utf-8")
        assert html.count(pdfmat.PDF_PAGINATION_STYLE_ID) == 1
        assert html.count('<article class="activity">') == 40


def test_u05q10r2_preserves_source_runtime_and_item_identity(tmp_path: Path):
    source = u05r1.build_acceptance_report()
    chromium = tmp_path / "chromium.exe"
    chromium.write_bytes(b"fake-browser")

    manifest = pdfmat.materialize_twenty_form_pdfs(
        output_root=tmp_path / "out",
        chromium_path=chromium,
        browser_runner=_fake_browser_runner,
        pdf_page_counter=_fake_page_counter,
        source_report=source,
    )

    assert manifest["source_runtime_identity_sha256"] == source[
        "source_runtime_identity_sha256"
    ]
    assert manifest["source_item_identity_sha256"] == source[
        "source_item_identity_sha256"
    ]
    assert manifest["source_800_runtime_rows_mutated"] is False
    assert manifest["source_selected_item_identities_mutated"] is False
    assert manifest["source_candidate_identities_mutated"] is False
    assert manifest["questionbank_modified"] is False
    assert manifest["sentence_assets_modified"] is False
    assert manifest["scene_authority_modified"] is False
    assert manifest["communicative_function_authority_modified"] is False
    assert manifest["task_pedagogical_contract_modified"] is False
    assert manifest["q10_redone"] is False


def test_u05q10r2_keeps_unit04_as_alignment_only_and_all_future_scope_locked(tmp_path: Path):
    source = u05r1.build_acceptance_report()
    chromium = tmp_path / "chromium.exe"
    chromium.write_bytes(b"fake-browser")

    manifest = pdfmat.materialize_twenty_form_pdfs(
        output_root=tmp_path / "out",
        chromium_path=chromium,
        browser_runner=_fake_browser_runner,
        pdf_page_counter=_fake_page_counter,
        source_report=source,
    )

    alignment = manifest["alignment_reference"]
    assert alignment["unit04_role"] == "COMPARISON_AND_ACCEPTANCE_PATTERN_ALIGNMENT_ONLY"
    assert alignment["unit04_content_authority_consumed"] is False
    assert alignment["unit05_q10r1_is_sole_direct_content_source"] is True
    assert alignment["print_pagination_guard_alignment_only"] is True
    assert manifest["unit04_used_as_unit05_content_authority"] is False

    for key in (
        "unit05_current360_materialized",
        "unit05_spoken360_materialized",
        "unit05_pattern360_materialized",
        "be_interrogative_mastery_activated",
        "past_be_activated",
        "existential_there_be_activated",
        "present_continuous_mastery_activated",
        "a2_a2plus_unlocked",
    ):
        assert manifest[key] is False
    assert manifest["next_short_step"] == pdfmat.NEXT_SHORT_STEP


def test_u05q10r2_source_readback_matches_q10r1_acceptance(tmp_path: Path):
    source = u05r1.build_acceptance_report()
    chromium = tmp_path / "chromium.exe"
    chromium.write_bytes(b"fake-browser")

    manifest = pdfmat.materialize_twenty_form_pdfs(
        output_root=tmp_path / "out",
        chromium_path=chromium,
        browser_runner=_fake_browser_runner,
        pdf_page_counter=_fake_page_counter,
        source_report=source,
    )
    rb = manifest["source_acceptance_readback"]
    assert rb == {
        "answer_key_binding_count": 800,
        "task_family_coverage": "10/10",
        "communicative_function_coverage": "7/7",
        "frame_coverage": "6/6",
        "subject_class_coverage": "9/9",
        "context_bound_activity_count": 578,
        "standalone_activity_count": 222,
        "within_form_exact_duplicate_count": 0,
        "within_form_normalized_duplicate_count": 0,
        "engineering_marker_visible_count": 0,
        "unit04_content_authority_consumed_count": 0,
    }
