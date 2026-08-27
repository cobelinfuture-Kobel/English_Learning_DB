from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from product.a1fs_v1_2_1 import (
    u03scfv2r1_unit03_twenty_form_learner_facing_acceptance as u03r1,
)
from product.a1fs_v1_2_1 import (
    u03scfv2r2_unit03_form01_20_learner_pdf_materialization_and_visual_acceptance
    as r2,
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
        + f"FAKE-{ordinal}\n".encode("ascii")
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


def test_u03scfv2r2_materializes_exact_twenty_forms_and_preserves_source_identity(
    tmp_path: Path,
):
    source = u03r1.build_acceptance_report()
    manifest = _materialize(tmp_path, source)
    out = tmp_path / "out"

    assert manifest["validation_status"] == r2.PASS_STATUS
    assert manifest["source_u03scfv2r1_task_id"] == u03r1.TASK_ID
    assert manifest["source_u03scfv2r1_status"] == u03r1.PASS_STATUS
    assert manifest["source_package_sha256"] == source["source_package_sha256"]
    assert (
        manifest["source_runtime_identity_sha256"]
        == source["source_runtime_identity_sha256"]
    )
    assert manifest["form_count"] == 20
    assert manifest["materialized_html_count"] == 20
    assert manifest["materialized_pdf_count"] == 20
    assert manifest["materialized_activity_count"] == 800
    assert manifest["machine_preflight_pass_count"] == 20
    assert manifest["learner_facing_machine_acceptance_pass_count"] == 20
    assert manifest["human_visual_review_pending_count"] == 20
    assert manifest["human_pedagogical_review_pending_count"] == 20
    assert manifest["presentation_fixes"] == {
        "reference_chain_answer_leak_fixes": 80,
        "referent_semantic_duplicate_fixes": 35,
    }
    assert manifest["unit03_form01_20_pdf_machine_acceptance"] == (
        "PASS_MACHINE_LEARNER_FACING_ACCEPTANCE"
    )
    assert manifest["unit03_form01_20_human_acceptance"] == (
        "PENDING_HUMAN_VISUAL_PEDAGOGICAL_REVIEW"
    )
    assert manifest["next_short_step"] == r2.NEXT_SHORT_STEP

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
        assert f"Unit 03 Form {ordinal:02d}" in html
        assert html.count('<article class="activity">') == 40

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
    assert manifest["q6_redone"] is False
    assert manifest["q9_redone"] is False
    assert manifest["q10_redone"] is False
    assert manifest["second_questionbank_authority_created"] is False
    assert manifest["second_selector_created"] is False
    assert manifest["second_renderer_created"] is False
    assert manifest["parallel_sentence_asset_schema_created"] is False
    assert manifest["runtime_authority_modified"] is False
    assert manifest["learner_state_modified"] is False
    assert manifest["scoring_authority_modified"] is False
    assert manifest["unit04_to_unit24_modified"] is False
    assert manifest["a2_unlocked"] is False


def test_u03scfv2r2_fails_closed_on_r1_status_drift(tmp_path: Path):
    source = deepcopy(u03r1.build_acceptance_report())
    source["validation_status"] = "FAIL"
    with pytest.raises(r2.Unit03PdfMaterializationError, match="SOURCE_STATUS_INVALID"):
        _materialize(tmp_path, source)


def test_u03scfv2r2_fails_closed_on_locked_runtime_identity_loss(tmp_path: Path):
    source = deepcopy(u03r1.build_acceptance_report())
    source["source_runtime_identity_sha256"] = ""
    with pytest.raises(r2.Unit03PdfMaterializationError, match="SOURCE_IDENTITY_MISSING"):
        _materialize(tmp_path, source)
