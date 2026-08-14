from __future__ import annotations

import json
from pathlib import Path

import pytest

from product.a1fs_v1_2_1 import (
    u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization as r1,
)


def _student_form(ordinal: int) -> dict:
    scenes = []
    activities = []
    q = 0
    for scene_number in range(1, 5):
        ref = f"TEST-SCENE-{ordinal:02d}-{scene_number:02d}"
        scenes.append(
            {
                "scene_number": scene_number,
                "scene_ref_id": ref,
                "situation_family": "TEST_FAMILY",
                "setting": f"SCHOOL_LIBRARY_{scene_number}",
            }
        )
        rows = (
            (
                "READING",
                "select_one",
                ["a", "an", "the"],
                (
                    "Scene: School Library | Scene words: book, apple | "
                    "Relationship: in | I can see a book. Target phrase: ___ book."
                ),
                "Choose the correct article for the target phrase.",
            ),
            (
                "READING",
                "select_one",
                ["a small bag", "an small bag"],
                "Scene: School Library | Target phrase: ___ small bag.",
                "Choose the correct noun phrase.",
            ),
            (
                "WRITING",
                "ordered_tokens",
                [],
                (
                    "Scene: School Library | Example: a small book | "
                    "Words: bag | blue | a | Task focus: word order"
                ),
                "Put the target phrase in the correct order.",
            ),
            (
                "WRITING",
                "short_text",
                [],
                (
                    "Scene: School Library | use: a/an | noun: apple | "
                    "Task focus: phrase construction"
                ),
                "Write the complete noun phrase from the cues.",
            ),
            (
                "SPEAKING",
                "practice_only",
                [],
                (
                    "Scene: School Library | Scene words: apple, bag | "
                    "Relationship: near | Example: This is a bag. | "
                    "Your turn: This is ___ ______. | Word: apple | "
                    "Task focus: scene description"
                ),
                "Complete the sentence frame, then say it aloud.",
            ),
        )
        for skill, mode, options, stimulus, prompt in rows:
            q += 1
            activities.append(
                {
                    "question_number": f"Q{q:02d}",
                    "skill": skill,
                    "scene_ref_id": ref,
                    "setting": f"SCHOOL_LIBRARY_{scene_number}",
                    "stimulus": stimulus,
                    "prompt": prompt,
                    "options": options,
                    "response_mode": mode,
                    "capture_enabled": skill != "SPEAKING",
                    "practice_only": skill == "SPEAKING",
                }
            )
    return {
        "unit_id": "UNIT01",
        "form_id": f"U01-FORM-{ordinal:02d}",
        "form_ordinal": ordinal,
        "learner_mode": "FRESH_SEQUENTIAL_REPLAY",
        "learner_id": "PRIVATE_TEST_LEARNER_SHOULD_NEVER_RENDER",
        "scene_count": 4,
        "learner_visible_activity_count": 20,
        "skill_counts": {"READING": 8, "WRITING": 8, "SPEAKING": 4},
        "scenes": scenes,
        "activities": activities,
    }


def _forms() -> list[dict]:
    return [
        {
            "form_ordinal": ordinal,
            "form_id": f"U01-FORM-{ordinal:02d}",
            "student_form": _student_form(ordinal),
        }
        for ordinal in range(1, 13)
    ]


def test_renderer_projects_learner_text_without_engineering_scene_metadata():
    rendered = r1.render_form_html(_student_form(1))
    assert "Unit 01" in rendered
    assert "Form 01" in rendered
    assert "School Library 1" in rendered
    assert "PRIVATE_TEST_LEARNER_SHOULD_NEVER_RENDER" not in rendered
    assert "TEST-SCENE-01-01" not in rendered
    assert "scene_ref_id" not in rendered
    assert "learner_id" not in rendered
    assert "Scene words:" not in rendered
    assert "Relationship:" not in rendered
    assert "Task focus:" not in rendered
    assert "noun:" not in rendered
    assert "SCHOOL_LIBRARY" not in rendered
    assert "School Library" in rendered


def test_renderer_suppresses_obvious_target_phrase_answer_demonstration():
    student = _student_form(1)
    rendered = r1.render_form_html(student)
    assert "I can see a book." not in rendered
    assert "Target phrase: ___ book." in rendered


def test_renderer_humanizes_phrase_construction_cues():
    rendered = r1.render_form_html(_student_form(1))
    assert "Use a or an." in rendered
    assert "Word: apple" in rendered
    assert "use: a/an" not in rendered


def test_word_order_tokens_survive_when_r4_options_are_empty():
    student = _student_form(1)
    ordered = student["activities"][2]
    assert ordered["response_mode"] == "ordered_tokens"
    assert ordered["options"] == []
    rendered = r1.render_form_html(student)
    assert '<span class="token">bag</span>' in rendered
    assert '<span class="token">blue</span>' in rendered
    assert '<span class="token">a</span>' in rendered
    assert "Words: bag" not in rendered
    assert "Example: a small book" in rendered


def test_renderer_no_longer_forces_one_page_per_scene():
    rendered = r1.render_form_html(_student_form(1))
    compact = rendered.replace(" ", "")
    assert ".scene-section{margin:0010px;break-before:auto;break-inside:auto}" in compact
    assert "break-before:page" not in compact
    assert "min-height:33mm" not in compact


def test_renderer_escapes_learner_visible_text():
    student = _student_form(1)
    student["activities"][0]["prompt"] = '<script>alert("x")</script>'
    rendered = r1.render_form_html(student)
    assert "<script>alert" not in rendered
    assert "&lt;script&gt;alert" in rendered


def test_renderer_fails_closed_on_private_answer_key():
    student = _student_form(1)
    student["activities"][0]["correct_answer"] = "a"
    with pytest.raises(Exception, match="ANSWER_OR_PRIVATE_KEY_EXPORTED"):
        r1.render_form_html(student)


def test_renderer_fails_closed_on_unknown_response_mode():
    student = _student_form(1)
    student["activities"][0]["response_mode"] = "mystery_mode"
    with pytest.raises(r1.TwelveFormPdfMaterializationError, match="RESPONSE_MODE_INVALID"):
        r1.render_form_html(student)


def test_headerless_browser_uses_modern_and_legacy_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    chromium = tmp_path / "chrome.exe"
    chromium.write_bytes(b"fake")
    source = tmp_path / "Form01.html"
    source.write_text("<html></html>", encoding="utf-8")
    output = tmp_path / "Form01.pdf"
    seen = {}

    class Result:
        returncode = 0
        stderr = ""

    def fake_run(command, **kwargs):
        seen["command"] = list(command)
        target = next(
            value.split("=", 1)[1]
            for value in command
            if str(value).startswith("--print-to-pdf=")
        )
        Path(target).write_bytes(b"%PDF-1.4\n" + b"x" * 1500)
        return Result()

    monkeypatch.setattr(r1.subprocess, "run", fake_run)
    result = r1._run_pdf_browser_headerless(
        chromium,
        source_html=source,
        output_path=output,
        mode="PDF",
    )
    assert "--no-pdf-header-footer" in seen["command"]
    assert "--print-to-pdf-no-header" in seen["command"]
    assert result["pdf_header_footer_suppression"] == "MODERN_AND_LEGACY_FLAGS"


def _materialize_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    report_path = tmp_path / "r4.json"
    report_path.write_text(
        json.dumps(
            {
                "task_id": "TEST_R4",
                "validation_status": "TEST_PASS",
                "forms": _forms(),
            }
        ),
        encoding="utf-8",
    )
    output_root = tmp_path / "output"
    fake_chromium = tmp_path / "chrome.exe"
    fake_chromium.write_bytes(b"fake")

    monkeypatch.setattr(r1, "_validate_r4_report", lambda report: report["forms"])

    def fake_browser(_chromium, *, source_html: Path, output_path: Path, mode: str):
        assert mode == "PDF"
        ordinal = source_html.stem
        payload = b"%PDF-1.4\n" + ordinal.encode("ascii") + b"\n" + (b"x" * 1400)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(payload)
        return {
            "mode": "PDF",
            "source_name": source_html.name,
            "output_name": output_path.name,
            "bytes": len(payload),
            "pdf_header_footer_suppression": "TEST",
        }

    result = r1.materialize_twelve_form_pdfs(
        r4_report_path=report_path,
        output_root=output_root,
        chromium_path=fake_chromium,
        browser_runner=fake_browser,
        pdf_page_counter=lambda _path: 4,
    )
    return output_root, result


def test_fullfix_materializes_twelve_pdfs_with_reviewable_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    output_root, result = _materialize_fixture(tmp_path, monkeypatch)

    assert result["validation_status"] == r1.PASS_STATUS
    assert result["schema_version"] == r1.MANIFEST_SCHEMA_VERSION
    assert result["form_count"] == 12
    assert result["materialized_html_count"] == 12
    assert result["materialized_pdf_count"] == 12
    assert result["machine_preflight_pass_count"] == 12
    assert result["human_visual_review_pass_count"] == 0
    assert result["human_visual_review_fail_count"] == 0
    assert result["human_visual_review_pending_count"] == 12
    assert result["human_pedagogical_review_pass_count"] == 0
    assert result["human_pedagogical_review_fail_count"] == 0
    assert result["human_pedagogical_review_pending_count"] == 12
    assert result["unit01_form01_12_pdf_acceptance"] == (
        "PENDING_HUMAN_VISUAL_PEDAGOGICAL_REVIEW"
    )
    assert result["unit01_product_d0_closeout"] is False
    assert result["questionbank_modified"] is False
    assert result["new_question_items_authored"] == 0
    assert result["scene_authority_modified"] is False
    assert result["production_database_modified"] is False
    assert result["unit02_to_unit24_modified"] is False
    assert result["a2_unlocked"] is False

    pdfs = sorted((output_root / "pdf").glob("Form*.pdf"))
    htmls = sorted((output_root / "html").glob("Form*.html"))
    assert [path.name for path in pdfs] == [f"Form{i:02d}.pdf" for i in range(1, 13)]
    assert [path.name for path in htmls] == [f"Form{i:02d}.html" for i in range(1, 13)]
    assert len({row["pdf_sha256"] for row in result["artifacts"]}) == 12
    assert all(row["human_visual_review"] == "PENDING" for row in result["artifacts"])
    assert all(row["human_pedagogical_review"] == "PENDING" for row in result["artifacts"])
    assert all(row["human_review_defect_codes"] == [] for row in result["artifacts"])
    assert all(row["human_review_evidence_pdf_sha256"] is None for row in result["artifacts"])

    manifest = json.loads((output_root / r1.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["materialized_pdf_count"] == 12
    assert manifest["unit01_final_pdf_acceptance"] == (
        "PENDING_HUMAN_VISUAL_PEDAGOGICAL_REVIEW"
    )


def test_manifest_records_sha_bound_form01_human_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    output_root, result = _materialize_fixture(tmp_path, monkeypatch)
    form01_sha = result["artifacts"][0]["pdf_sha256"]
    manifest_path = output_root / r1.MANIFEST_NAME

    reviewed = r1.record_human_review(
        manifest_path=manifest_path,
        form_ordinal=1,
        expected_pdf_sha256=form01_sha,
        visual_review="FAIL",
        pedagogical_review="FAIL",
        defect_codes=[
            "LOCAL_FILE_URI_EXPOSED",
            "LEARNER_ENGINEERING_METADATA_EXPOSED",
        ],
        reviewed_at="2026-08-14T15:30:00Z",
    )

    form01 = reviewed["artifacts"][0]
    assert form01["human_visual_review"] == "FAIL"
    assert form01["human_pedagogical_review"] == "FAIL"
    assert form01["human_review_evidence_pdf_sha256"] == form01_sha
    assert form01["human_review_defect_codes"] == [
        "LEARNER_ENGINEERING_METADATA_EXPOSED",
        "LOCAL_FILE_URI_EXPOSED",
    ]
    assert reviewed["human_visual_review_fail_count"] == 1
    assert reviewed["human_visual_review_pending_count"] == 11
    assert reviewed["human_pedagogical_review_fail_count"] == 1
    assert reviewed["unit01_form01_12_pdf_acceptance"] == "FAIL_HUMAN_REVIEW"
    assert reviewed["unit01_final_pdf_acceptance"] == (
        "BLOCKED_FORM_PDF_HUMAN_REVIEW_FAILURE"
    )
    assert reviewed["unit01_product_d0_closeout"] is False


def test_manifest_rejects_stale_pdf_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    output_root, _result = _materialize_fixture(tmp_path, monkeypatch)
    with pytest.raises(r1.TwelveFormPdfMaterializationError, match="STALE_HUMAN_REVIEW_PDF_SHA256"):
        r1.record_human_review(
            manifest_path=output_root / r1.MANIFEST_NAME,
            form_ordinal=1,
            expected_pdf_sha256="0" * 64,
            visual_review="PASS",
            pedagogical_review="PASS",
            reviewed_at="2026-08-14T15:30:00Z",
        )


def test_new_materialization_resets_human_review_to_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    output_root, first = _materialize_fixture(tmp_path, monkeypatch)
    form01_sha = first["artifacts"][0]["pdf_sha256"]
    r1.record_human_review(
        manifest_path=output_root / r1.MANIFEST_NAME,
        form_ordinal=1,
        expected_pdf_sha256=form01_sha,
        visual_review="FAIL",
        pedagogical_review="FAIL",
        defect_codes=["OLD_PDF_DEFECT"],
        reviewed_at="2026-08-14T15:30:00Z",
    )

    _, second = _materialize_fixture(tmp_path, monkeypatch)
    form01 = second["artifacts"][0]
    assert form01["human_visual_review"] == "PENDING"
    assert form01["human_pedagogical_review"] == "PENDING"
    assert form01["human_review_defect_codes"] == []
    assert form01["human_review_evidence_pdf_sha256"] is None


def test_fullfix_rejects_duplicate_pdf_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    report_path = tmp_path / "r4.json"
    report_path.write_text(json.dumps({"forms": _forms()}), encoding="utf-8")
    fake_chromium = tmp_path / "chrome.exe"
    fake_chromium.write_bytes(b"fake")
    monkeypatch.setattr(r1, "_validate_r4_report", lambda report: report["forms"])

    def identical_pdf(_chromium, *, source_html: Path, output_path: Path, mode: str):
        payload = b"%PDF-1.4\n" + (b"same" * 400)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(payload)
        return {
            "mode": mode,
            "source_name": source_html.name,
            "output_name": output_path.name,
        }

    with pytest.raises(r1.TwelveFormPdfMaterializationError, match="PDF_SHA256_NOT_DISTINCT"):
        r1.materialize_twelve_form_pdfs(
            r4_report_path=report_path,
            output_root=tmp_path / "output",
            chromium_path=fake_chromium,
            browser_runner=identical_pdf,
            pdf_page_counter=lambda _path: 1,
        )
