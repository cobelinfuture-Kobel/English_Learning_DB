from __future__ import annotations

from pathlib import Path

from product.a1fs_v1_2_1 import (
    u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization as u01_pdf,
)
from product.a1fs_v1_2_1 import (
    u02form02_unit02_form01_16_chromium_pdf_materialization_and_learner_facing_acceptance
    as r2,
)
from ulga.builders import (
    build_a1fs_v1_u02form01_unit02_existing_learner_renderer_reuse_and_16x40_deterministic_form_materialization
    as u02form01,
)


def test_u02form02_consumes_exact_merged_u02form01_source_contract():
    source = u02form01.build_materialization()
    forms = r2._validate_source(source)
    assert source["status"] == u02form01.PASS_STATUS
    assert len(forms) == 16
    assert sum(form["learner_visible_activity_count"] for form in forms) == 640
    assert all(form["scene_count"] == 4 for form in forms)
    assert all(form["skill_counts"] == {"READING": 16, "WRITING": 24} for form in forms)
    assert source["form_contract"]["q10_selection_recomputed"] is False
    assert source["form_contract"]["q10_selected_item_identity_mutated"] is False
    assert source["runtime_proof"]["q6_binding_text_exported_to_learner"] is False


def test_u02form02_reuses_unit01_headerless_chromium_and_page_counter():
    assert r2.UNIT01_HEADERLESS_BROWSER_RUNNER is u01_pdf._run_pdf_browser_headerless
    assert r2.UNIT01_PDF_PAGE_COUNTER is r2.chromium_acceptance._pdf_page_count


def test_u02form02_materializes_sixteen_distinct_pdfs_and_machine_acceptance(tmp_path: Path):
    fake_chromium = tmp_path / "chrome"
    fake_chromium.write_bytes(b"fake")
    output_root = tmp_path / "unit02"

    def fake_browser(_chromium, *, source_html: Path, output_path: Path, mode: str):
        assert mode == "PDF"
        html = source_html.read_text(encoding="utf-8")
        assert html.count('class="activity"') == 40
        lowered = html.casefold()
        for marker in u02form01.FORBIDDEN_HTML_MARKERS:
            assert marker not in lowered
        payload = (
            b"%PDF-1.4\n"
            + source_html.stem.encode("ascii")
            + b"\n"
            + (b"x" * 1500)
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(payload)
        return {
            "mode": "PDF",
            "source_name": source_html.name,
            "output_name": output_path.name,
            "bytes": len(payload),
            "pdf_header_footer_suppression": "MODERN_AND_LEGACY_FLAGS",
        }

    manifest = r2.materialize_sixteen_form_pdfs(
        output_root=output_root,
        chromium_path=fake_chromium,
        browser_runner=fake_browser,
        pdf_page_counter=lambda _path: 5,
    )

    assert manifest["validation_status"] == r2.PASS_STATUS
    assert manifest["form_count"] == 16
    assert manifest["materialized_html_count"] == 16
    assert manifest["materialized_pdf_count"] == 16
    assert manifest["materialized_activity_count"] == 640
    assert manifest["machine_preflight_pass_count"] == 16
    assert manifest["learner_facing_machine_acceptance_pass_count"] == 16
    assert manifest["human_visual_review_pending_count"] == 16
    assert manifest["human_pedagogical_review_pending_count"] == 16
    assert manifest["unit02_form01_16_pdf_machine_acceptance"] == (
        "PASS_MACHINE_LEARNER_FACING_ACCEPTANCE"
    )
    assert manifest["unit02_form01_16_human_acceptance"] == (
        "PENDING_HUMAN_VISUAL_PEDAGOGICAL_REVIEW"
    )
    assert len(manifest["artifacts"]) == 16
    assert len({row["pdf_sha256"] for row in manifest["artifacts"]}) == 16
    assert all(row["page_count"] == 5 for row in manifest["artifacts"])
    assert all(row["machine_preflight"] == "PASS" for row in manifest["artifacts"])
    assert all(
        row["learner_facing_machine_acceptance"] == "PASS"
        for row in manifest["artifacts"]
    )
    assert all(row["human_visual_review"] == "PENDING" for row in manifest["artifacts"])
    assert all(
        row["human_pedagogical_review"] == "PENDING"
        for row in manifest["artifacts"]
    )

    htmls = sorted((output_root / "html").glob("Form*.html"))
    pdfs = sorted((output_root / "pdf").glob("Form*.pdf"))
    assert [path.name for path in htmls] == [f"Form{i:02d}.html" for i in range(1, 17)]
    assert [path.name for path in pdfs] == [f"Form{i:02d}.pdf" for i in range(1, 17)]
    assert (output_root / r2.MANIFEST_NAME).is_file()


def test_u02form02_preserves_authority_boundaries(tmp_path: Path):
    fake_chromium = tmp_path / "chrome"
    fake_chromium.write_bytes(b"fake")

    def fake_browser(_chromium, *, source_html: Path, output_path: Path, mode: str):
        payload = b"%PDF-1.4\n" + source_html.stem.encode("ascii") + b"\n" + (b"z" * 1600)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(payload)
        return {"mode": mode, "source_name": source_html.name, "output_name": output_path.name}

    manifest = r2.materialize_sixteen_form_pdfs(
        output_root=tmp_path / "out",
        chromium_path=fake_chromium,
        browser_runner=fake_browser,
        pdf_page_counter=lambda _path: 1,
    )
    assert manifest["questionbank_modified"] is False
    assert manifest["new_question_items_authored"] == 0
    assert manifest["sentence_assets_modified"] is False
    assert manifest["canonical_scene_authority_modified"] is False
    assert manifest["selector_modified"] is False
    assert manifest["runtime_authority_modified"] is False
    assert manifest["learner_state_modified"] is False
    assert manifest["scoring_authority_modified"] is False
    assert manifest["unit03_to_unit24_modified"] is False
    assert manifest["a2_unlocked"] is False
    assert manifest["next_short_step"] == r2.NEXT_SHORT_STEP
