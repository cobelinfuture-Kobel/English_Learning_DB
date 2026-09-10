from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from product.a1fs_v1_2_1 import (
    u04fsv2_current360_contextual_form_runtime as fsv2,
)
from product.a1fs_v1_2_1 import (
    u04rswv2_productive_scoring_cambridge_progression_acceptance as rswv2,
)
from product.a1fs_v1_2_1 import (
    u04spv2_current360_speaking_cutover as spv2,
)
from product.a1fs_v1_2_1 import (
    u04vav2_current360_learner_facing_visual_pedagogical_acceptance as vav2,
)


REPORT = vav2.build_unit04_vav2_current360_visual_machine_acceptance()


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
    assert vav2.pagination.PDF_PAGINATION_STYLE_ID in html
    assert html.count('<article class="activity">') == 40
    ordinal = source_html.stem
    payload = (
        b"%PDF-1.4\n"
        + f"FAKE-U04VAV2-{ordinal}\n".encode("ascii")
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


def _materialize(tmp_path: Path, report=REPORT):
    chromium = tmp_path / "chromium.exe"
    chromium.write_bytes(b"fake-browser")
    return vav2.materialize_current360_twenty_form_pdfs(
        output_root=tmp_path / "out",
        chromium_path=chromium,
        browser_runner=_fake_browser_runner,
        pdf_page_counter=_fake_page_counter,
        acceptance_report=report,
    )


def test_u04vav2_accepts_only_active_current360_form_and_speaking_runtimes() -> None:
    assert REPORT["status"] == vav2.STATUS
    authority = REPORT["source_authority"]
    assert authority["active_form_runtime"] == fsv2.TASK_ID
    assert authority["active_speaking_runtime"] == spv2.TASK_ID
    assert (
        authority["productive_scoring_progression_acceptance"]
        == rswv2.TASK_ID
    )
    assert REPORT["safety"]["fsv2_runtime_modified"] is False
    assert REPORT["safety"]["spv2_runtime_modified"] is False
    assert REPORT["safety"]["current360_episode_content_modified"] is False


def test_u04vav2_reuses_existing_learner_renderer_without_activity_mutation() -> None:
    forms = REPORT["learner_forms"]
    assert len(forms) == 20
    assert sum(len(form["activities"]) for form in forms) == 800
    assert [form["form_ordinal"] for form in forms] == list(range(1, 21))
    assert all(form["section_count"] == 5 for form in forms)
    assert all(form["learner_visible_activity_count"] == 40 for form in forms)
    assert all(
        [row["section"] for row in form["sections"]] == ["A", "B", "C", "D", "E"]
        for form in forms
    )
    acceptance = REPORT["machine_acceptance"]["learner_forms"]
    assert acceptance["form_count"] == 20
    assert acceptance["activity_count"] == 800
    assert acceptance["rendered_html_form_count"] == 20
    assert acceptance["pagination_guarded_html_form_count"] == 20
    assert acceptance["stage_form_counts"] == {
        "GUIDED": 4,
        "REDUCED_SUPPORT": 4,
        "INDEPENDENT": 4,
        "TRANSFER": 4,
        "RETENTION": 4,
    }
    assert acceptance["second_renderer_created"] is False


def test_u04vav2_preserves_spv2_240_prompt_surface_and_semantic_scoring() -> None:
    speaking = REPORT["machine_acceptance"]["speaking_surface"]
    assert speaking["bridge_task_count"] == 80
    assert speaking["layer2_task_count"] == 160
    assert speaking["learner_speaking_prompt_count"] == 240
    assert speaking["distinct_speaking_mode_count"] == 11
    assert speaking["stage_task_counts"] == {
        "GUIDED": 48,
        "REDUCED_SUPPORT": 48,
        "INDEPENDENT": 48,
        "TRANSFER": 48,
        "RETENTION": 48,
    }
    assert speaking["all_prompts_nonempty"] is True
    assert speaking["all_current360_passages_nonempty"] is True
    assert speaking["semantic_scoring_preserved"] is True
    assert speaking["acceptable_paraphrase_preserved"] is True
    assert speaking["machine_pronunciation_score_required"] is False
    assert speaking["speaking_pdf_renderer_created"] is False


def test_u04vav2_keeps_requirement_10_human_review_open() -> None:
    progress = REPORT["requirement_10_progress"]
    assert progress["machine_learner_form_presentation"] == "PASS"
    assert progress["machine_pdf_materialization_contract"] == "PASS"
    assert progress["machine_spv2_learner_prompt_surface"] == "PASS"
    assert progress["actual_pdf_human_visual_review"] == "PENDING"
    assert progress["actual_human_pedagogical_review"] == "PENDING"
    assert progress["human_speaking_prompt_review"] == "PENDING"
    assert progress["full_requirement_10_closed"] is False
    assert REPORT["human_review"]["status"] == "PENDING_EXACT_RENDERED_EVIDENCE"
    assert REPORT["next_short_step"] == vav2.NEXT_SHORT_STEP


def test_u04vav2_materializes_20_pdfs_with_existing_runner_and_pagination(
    tmp_path: Path,
) -> None:
    manifest = _materialize(tmp_path)
    out = tmp_path / "out"
    assert manifest["validation_status"] == vav2.STATUS
    assert manifest["form_count"] == 20
    assert manifest["materialized_html_count"] == 20
    assert manifest["materialized_pdf_count"] == 20
    assert manifest["materialized_activity_count"] == 800
    assert manifest["speaking_prompt_machine_acceptance_count"] == 240
    assert manifest["machine_preflight_pass_count"] == 20
    assert manifest["learner_facing_machine_acceptance_pass_count"] == 20
    assert manifest["human_visual_review_pending_count"] == 20
    assert manifest["human_pedagogical_review_pending_count"] == 20
    assert manifest["human_speaking_prompt_review_pending_count"] == 240
    assert manifest["existing_learner_html_renderer_reused"] is True
    assert manifest["existing_chromium_pdf_runner_reused"] is True
    assert manifest["existing_pagination_guard_reused"] is True
    assert manifest["second_renderer_created"] is False
    assert len(manifest["artifacts"]) == 20
    assert len({row["html_sha256"] for row in manifest["artifacts"]}) == 20
    assert len({row["pdf_sha256"] for row in manifest["artifacts"]}) == 20
    assert all(row["page_count"] == 2 for row in manifest["artifacts"])

    for ordinal in range(1, 21):
        html_path = out / "html" / f"Form{ordinal:02d}.html"
        pdf_path = out / "pdf" / f"Form{ordinal:02d}.pdf"
        assert html_path.is_file()
        assert pdf_path.is_file()
        html = html_path.read_text(encoding="utf-8")
        assert html.count('<article class="activity">') == 40
        assert vav2.pagination.PDF_PAGINATION_STYLE_ID in html

    manifest_path = out / vav2.MANIFEST_NAME
    assert manifest_path.is_file()
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == manifest


def test_u04vav2_fails_closed_if_rswv2_visual_gate_is_not_pending() -> None:
    rsw = deepcopy(
        rswv2.build_unit04_rswv2_productive_scoring_cambridge_progression_acceptance()
    )
    rsw["approved_requirements_10_of_10"][
        "10_learner_facing_visual_pedagogical_acceptance"
    ]["status"] = "PASS"
    with pytest.raises(vav2.Unit04VAV2Error, match="RSWV2_VISUAL_GATE_STATE_DRIFT"):
        vav2.build_unit04_vav2_current360_visual_machine_acceptance(
            rsw_report=rsw
        )


def test_u04vav2_fails_closed_if_fsv2_parallel_runtime_is_allowed() -> None:
    forms = deepcopy(fsv2.build_unit04_fsv2_current360_contextual_form_runtime())
    forms["cutover_contract"]["parallel_active_form_runtime_allowed"] = True
    with pytest.raises(vav2.Unit04VAV2Error, match="FSV2_PARALLEL_FORM_RUNTIME_ALLOWED"):
        vav2.build_unit04_vav2_current360_visual_machine_acceptance(
            form_report=forms
        )


def test_u04vav2_preserves_a1_support_listening_and_other_unit_boundaries() -> None:
    safety = REPORT["safety"]
    assert safety["q01_q10_authority_modified"] is False
    assert safety["questionbank_modified"] is False
    assert safety["sentence_assets_modified"] is False
    assert safety["scene_authority_modified"] is False
    assert safety["second_form_renderer_created"] is False
    assert safety["second_speaking_renderer_created"] is False
    assert safety["scoring_authority_modified"] is False
    assert safety["listening_modified"] is False
    assert safety["support_relations_promoted_to_assessed_target"] is False
    assert safety["a2_a2plus_unlocked"] is False
    assert safety["other_units_modified"] is False


def test_u04vav2_is_deterministic() -> None:
    replay = vav2.build_unit04_vav2_current360_visual_machine_acceptance()
    assert replay == REPORT
