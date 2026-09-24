from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from product.a1fs_v1_2_1 import (
    u04q10r1_unit04_learner_facing_pedagogical_acceptance as u04r1,
)
from product.a1fs_v1_2_1 import (
    u04q10r2_unit04_learner_pdf_materialization_and_visual_acceptance as r2,
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
    ordinal = source_html.stem
    payload = (
        b"%PDF-1.4\n"
        + f"FAKE-U04-{ordinal}\n".encode("ascii")
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
    return 2


def _materialize(tmp_path: Path, source_report=None):
    chromium = tmp_path / "chromium.exe"
    chromium.write_bytes(b"fake-browser")
    return r2.materialize_twenty_form_pdfs(
        output_root=tmp_path / "out",
        chromium_path=chromium,
        browser_runner=_fake_browser_runner,
        pdf_page_counter=_fake_page_counter,
        source_report=source_report,
    )


def test_u04q10r2_materializes_exact_twenty_forms_and_preserves_r1_identity(
    tmp_path: Path,
):
    source = u04r1.build_acceptance_report()
    manifest = _materialize(tmp_path, source)
    out = tmp_path / "out"

    assert manifest["validation_status"] == r2.PASS_STATUS
    assert manifest["source_u04q10r1_task_id"] == u04r1.TASK_ID
    assert manifest["source_u04q10r1_status"] == u04r1.PASS_STATUS
    assert (
        manifest["source_runtime_identity_sha256"]
        == source["source_runtime_identity_sha256"]
    )
    assert (
        manifest["source_item_identity_sha256"]
        == source["source_item_identity_sha256"]
    )
    assert manifest["form_count"] == 20
    assert manifest["materialized_html_count"] == 20
    assert manifest["materialized_pdf_count"] == 20
    assert manifest["materialized_activity_count"] == 800
    assert manifest["machine_preflight_pass_count"] == 20
    assert manifest["learner_facing_machine_acceptance_pass_count"] == 20
    assert manifest["human_visual_review_pending_count"] == 20
    assert manifest["human_pedagogical_review_pending_count"] == 20
    assert manifest["unit04_form01_20_pdf_machine_acceptance"] == (
        "PASS_MACHINE_LEARNER_FACING_ACCEPTANCE"
    )
    assert manifest["unit04_form01_20_human_acceptance"] == (
        "PENDING_HUMAN_VISUAL_PEDAGOGICAL_REVIEW"
    )
    assert manifest["next_short_step"] == r2.NEXT_SHORT_STEP

    source_readback = manifest["source_acceptance_readback"]
    assert source_readback["answer_key_binding_count"] == 800
    assert source_readback["task_family_coverage"] == "10/10"
    assert source_readback["target_relation_coverage"] == "8/8"
    assert source_readback["communicative_function_coverage"] == "6/6"
    assert source_readback["scene_bound_evidence_activity_count"] == 760
    assert source_readback["at_text_bound_activity_count"] == 40
    assert source_readback["fabricated_scene_ref_count"] == 0
    assert source_readback["selected_relation_answer_leak_count"] == 0
    assert source_readback["within_form_exact_duplicate_count"] == 0
    assert source_readback["within_form_normalized_duplicate_count"] == 0

    artifacts = manifest["artifacts"]
    assert len(artifacts) == 20
    assert [row["form_ordinal"] for row in artifacts] == list(range(1, 21))
    assert len({row["html_sha256"] for row in artifacts}) == 20
    assert len({row["pdf_sha256"] for row in artifacts}) == 20
    assert all(row["page_count"] == 2 for row in artifacts)
    assert all(row["learner_visible_activity_count"] == 40 for row in artifacts)
    assert all(row["machine_preflight"] == "PASS" for row in artifacts)
    assert all(row["learner_facing_machine_acceptance"] == "PASS" for row in artifacts)
    assert all(row["human_visual_review"] == "PENDING" for row in artifacts)
    assert all(row["human_pedagogical_review"] == "PENDING" for row in artifacts)

    for ordinal in range(1, 21):
        html_path = out / "html" / f"Form{ordinal:02d}.html"
        pdf_path = out / "pdf" / f"Form{ordinal:02d}.pdf"
        assert html_path.is_file()
        assert pdf_path.is_file()
        html = html_path.read_text(encoding="utf-8")
        assert html.count('<article class="activity">') == 40
        assert html.count(r2.PDF_PRINT_SAFETY_STYLE_ID) == 1
        assert "break-inside: avoid;" in html
        assert "page-break-inside: avoid;" in html
        assert "break-after: avoid;" in html
        assert "page-break-after: avoid;" in html
        raw_r1_html = u04r1.render_form_html(source["learner_forms"][ordinal - 1])
        assert r2.PDF_PRINT_SAFETY_STYLE_ID not in raw_r1_html
        lowered = html.casefold()
        for marker in u04r1.FORBIDDEN_LEARNER_MARKERS:
            assert marker.casefold() not in lowered

    manifest_path = out / r2.MANIFEST_NAME
    assert manifest_path.is_file()
    on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert on_disk == manifest

    assert manifest["source_800_runtime_rows_mutated"] is False
    assert manifest["source_selected_item_identities_mutated"] is False
    assert manifest["source_candidate_identities_mutated"] is False
    assert manifest["questionbank_modified"] is False
    assert manifest["new_question_items_authored"] == 0
    assert manifest["sentence_assets_modified"] is False
    assert manifest["scene_authority_modified"] is False
    assert manifest["q03_redone"] is False
    assert manifest["q07_redone"] is False
    assert manifest["q08_redone"] is False
    assert manifest["q09_redone"] is False
    assert manifest["q10_redone"] is False
    assert manifest["second_questionbank_authority_created"] is False
    assert manifest["second_selector_created"] is False
    assert manifest["second_renderer_created"] is False
    assert manifest["runtime_authority_modified"] is False
    assert manifest["learner_state_modified"] is False
    assert manifest["scoring_authority_modified"] is False
    assert manifest["unit05_to_unit24_modified"] is False
    assert manifest["motion_directional_from_into_to_activated"] is False
    assert manifest["a2_unlocked"] is False


def test_u04q10r2_print_safety_is_pdf_derivative_only_and_fails_closed():
    raw = "<html><head><title>Unit04</title></head><body><article class=\"activity\">Q01</article></body></html>"
    safe = r2._pdf_safe_html(raw)
    assert r2.PDF_PRINT_SAFETY_STYLE_ID not in raw
    assert safe.count(r2.PDF_PRINT_SAFETY_STYLE_ID) == 1
    assert "break-inside: avoid;" in safe
    assert "page-break-inside: avoid;" in safe
    assert safe.endswith("</body></html>")

    with pytest.raises(r2.Unit04PdfMaterializationError, match="LEARNER_HTML_HEAD_MISSING"):
        r2._pdf_safe_html("<html><body>no head close</body></html>")

    with pytest.raises(
        r2.Unit04PdfMaterializationError,
        match="PDF_PRINT_SAFETY_ALREADY_PRESENT",
    ):
        r2._pdf_safe_html(safe)


def test_u04q10r2_fails_closed_on_r1_status_drift(tmp_path: Path):
    source = deepcopy(u04r1.build_acceptance_report())
    source["status"] = "FAIL"
    with pytest.raises(r2.Unit04PdfMaterializationError, match="SOURCE_STATUS_INVALID"):
        _materialize(tmp_path, source)


def test_u04q10r2_fails_closed_on_locked_source_identity_loss(tmp_path: Path):
    source = deepcopy(u04r1.build_acceptance_report())
    source["source_runtime_identity_sha256"] = ""
    with pytest.raises(r2.Unit04PdfMaterializationError, match="SOURCE_IDENTITY_MISSING"):
        _materialize(tmp_path, source)


def test_u04q10r2_fails_closed_on_at_text_bound_contract_drift(tmp_path: Path):
    source = deepcopy(u04r1.build_acceptance_report())
    source["acceptance"]["at_text_bound_activity_count"] = 39
    with pytest.raises(
        r2.Unit04PdfMaterializationError,
        match="SOURCE_ACCEPTANCE_DRIFT:at_text_bound_activity_count",
    ):
        _materialize(tmp_path, source)
