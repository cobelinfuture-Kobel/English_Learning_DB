from pathlib import Path

from product.a1fs_v1_2_1 import u04formv3b_existing_renderer_integration_and_visual_review as target


def test_u04_formv3b_reuses_existing_renderer_and_restores_response_affordances():
    report = target.build_machine_integration_report()

    assert report["status"] == target.STATUS
    assert report["form_count"] == 4
    assert report["question_count"] == 160
    assert report["html_activity_count"] == 160
    assert report["worksheet_css_form_count"] == 4
    assert report["pagination_guard_form_count"] == 4
    assert report["renderer_reused"] is True
    assert report["second_renderer_created"] is False
    assert report["python_learner_content_authoring_used"] is False
    assert report["current360_passage_mutated"] is False
    assert report["listening_modified"] is False
    assert report["a2_a2plus_unlocked"] is False
    assert all(count >= 3 for count in report["speaking_response_form_counts"])

    forms = target.load_projected_formv3a_forms()
    assert [form["form_ordinal"] for form in forms] == [1, 2, 3, 4]
    for form in forms:
        assert len(form["activities"]) == 40
        html = target.render_formv3a_with_existing_renderer(form)
        assert html.count('<article class="activity">') == 40
        assert target.WORKSHEET_STYLE_ID in html
        assert target.pagination.PDF_PAGINATION_STYLE_ID in html
        assert 'class="choice-mark"' in html
        assert 'class="write-line"' in html
        assert 'class="speaking-box"' in html
        assert "reference_answer" not in html
        assert "correct_option_index" not in html
        assert "question_id" not in html
        assert "episode_id" not in html


def test_u04_formv3b_projection_does_not_reauthor_static_learner_text():
    root = Path(target.__file__).resolve().parents[2]
    projected = target.load_projected_formv3a_forms(root)

    for ordinal, form in enumerate(projected, start=1):
        source = target.formv3a._load_asset(root, ordinal)["form"]
        source_contexts = {row["slot"]: row["passage"] for row in source["contexts"]}
        source_questions = source["questions"]
        assert [a["prompt"] for a in form["activities"]] == [q["prompt"] for q in source_questions]
        for activity, question in zip(form["activities"], source_questions):
            if activity["response_mode"] == "select_one":
                assert activity["options"] == question["options"]
            if activity["stimulus"]:
                assert activity["stimulus"] == source_contexts[question["context_slot"]]


def test_u04_formv3b_materializer_reuses_chromium_chain_without_real_browser(tmp_path):
    def fake_runner(_chromium, *, source_html, output_path, mode):
        assert mode == "PDF"
        assert Path(source_html).is_file()
        marker = Path(output_path).name.encode("ascii")
        Path(output_path).write_bytes(b"%PDF-1.4\n" + marker + b"\n" + b"x" * 2048)
        return {"status": "PASS_FAKE_BROWSER_CONTRACT"}

    manifest = target.materialize_form01_04_pdfs(
        output_root=tmp_path,
        chromium_path=Path(__file__),
        browser_runner=fake_runner,
        pdf_page_counter=lambda _path: 1,
    )

    assert manifest["machine_status"] == target.STATUS
    assert manifest["form_count"] == 4
    assert manifest["question_count"] == 160
    assert manifest["materialized_pdf_count"] == 4
    assert manifest["human_visual_review_pending_count"] == 4
    assert manifest["human_pedagogical_review_pending_count"] == 4
    assert manifest["human_acceptance"] == "PENDING_ACTUAL_PDF_REVIEW"
    assert manifest["python_learner_content_authoring_used"] is False
    assert (tmp_path / target.MANIFEST_NAME).is_file()
    for ordinal in range(1, 5):
        assert (tmp_path / "html" / f"Form{ordinal:02d}.html").is_file()
        assert (tmp_path / "pdf" / f"Form{ordinal:02d}.pdf").is_file()
