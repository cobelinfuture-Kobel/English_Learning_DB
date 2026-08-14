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
            ("READING", "select_one", ["a", "an", "the"]),
            ("READING", "select_one", ["a book", "an book"]),
            ("WRITING", "ordered_tokens", ["This", "is", "a", "book"]),
            ("WRITING", "short_text", []),
            ("SPEAKING", "practice_only", []),
        )
        for skill, mode, options in rows:
            q += 1
            activities.append(
                {
                    "question_number": f"Q{q:02d}",
                    "skill": skill,
                    "scene_ref_id": ref,
                    "setting": f"SCHOOL_LIBRARY_{scene_number}",
                    "stimulus": (
                        f"There is ___ book in scene {scene_number}."
                        if skill == "READING"
                        else ""
                    ),
                    "prompt": (
                        "Choose the best answer."
                        if skill == "READING"
                        else "Write or say the sentence for this scene."
                    ),
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


def test_renderer_projects_only_learner_visible_fields():
    student = _student_form(1)
    rendered = r1.render_form_html(student)
    assert "Unit 01" in rendered
    assert "Form 01" in rendered
    assert "School Library 1" in rendered
    assert "Choose the best answer." in rendered
    assert "Speaking practice" in rendered
    assert "PRIVATE_TEST_LEARNER_SHOULD_NEVER_RENDER" not in rendered
    assert "TEST-SCENE-01-01" not in rendered
    assert "scene_ref_id" not in rendered
    assert "learner_id" not in rendered
    assert "correct_answer" not in rendered
    assert "scoring_contract" not in rendered


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


def test_fullfix_materializes_exactly_twelve_distinct_pdf_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
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

    monkeypatch.setattr(r1, "_validate_r4_report", lambda _report: _report["forms"])

    def fake_browser(_chromium, *, source_html: Path, output_path: Path, mode: str):
        assert mode == "PDF"
        assert source_html.is_file()
        ordinal = source_html.stem
        payload = b"%PDF-1.4\n" + ordinal.encode("ascii") + b"\n" + (b"x" * 1400)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(payload)
        return {
            "mode": "PDF",
            "source_name": source_html.name,
            "output_name": output_path.name,
            "bytes": len(payload),
        }

    result = r1.materialize_twelve_form_pdfs(
        r4_report_path=report_path,
        output_root=output_root,
        chromium_path=fake_chromium,
        browser_runner=fake_browser,
        pdf_page_counter=lambda _path: 4,
    )

    assert result["validation_status"] == r1.PASS_STATUS
    assert result["form_count"] == 12
    assert result["materialized_html_count"] == 12
    assert result["materialized_pdf_count"] == 12
    assert result["machine_preflight_pass_count"] == 12
    assert result["human_visual_review_pass_count"] == 0
    assert result["human_visual_review_pending_count"] == 12
    assert result["unit01_product_d0_closeout"] is False
    assert result["questionbank_modified"] is False
    assert result["new_question_items_authored"] == 0
    assert result["scene_authority_modified"] is False
    assert result["production_database_modified"] is False
    assert result["unit02_to_unit24_modified"] is False
    assert result["a2_unlocked"] is False
    assert result["next_short_step"] == r1.NEXT_SHORT_STEP

    pdfs = sorted((output_root / "pdf").glob("Form*.pdf"))
    htmls = sorted((output_root / "html").glob("Form*.html"))
    assert [path.name for path in pdfs] == [f"Form{i:02d}.pdf" for i in range(1, 13)]
    assert [path.name for path in htmls] == [f"Form{i:02d}.html" for i in range(1, 13)]
    assert len({row["pdf_sha256"] for row in result["artifacts"]}) == 12
    assert all(row["page_count"] == 4 for row in result["artifacts"])
    assert all(row["human_visual_review"] == "PENDING" for row in result["artifacts"])

    manifest = json.loads((output_root / r1.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["materialized_pdf_count"] == 12
    assert manifest["unit01_final_pdf_acceptance"] == "PENDING_HUMAN_VISUAL_REVIEW"


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
        return {"mode": mode, "source_name": source_html.name, "output_name": output_path.name}

    with pytest.raises(r1.TwelveFormPdfMaterializationError, match="PDF_SHA256_NOT_DISTINCT"):
        r1.materialize_twelve_form_pdfs(
            r4_report_path=report_path,
            output_root=tmp_path / "output",
            chromium_path=fake_chromium,
            browser_runner=identical_pdf,
            pdf_page_counter=lambda _path: 1,
        )
