from pathlib import Path

from product.a1fs_v1_2_1 import u04formv3b_existing_renderer_integration_and_visual_review as target


def test_u04_formv3c_a2_reuses_existing_renderer_for_all_diversified_response_modes():
    report = target.build_machine_integration_report()

    assert report["status"] == target.STATUS
    assert report["a3_r1_status"] == target.A3_R1_STATUS
    assert report["form_count"] == 4
    assert report["question_count"] == 160
    assert report["semantic_response_mode_coverage_count"] == 22
    assert set(report["semantic_response_mode_coverage"]) == target.EXPECTED_SEMANTIC_RESPONSE_MODES
    assert set(report["presentation_primitive_counts"]) == {
        "ordered_tokens",
        "practice_only",
        "select_one",
        "short_text",
    }
    assert report["picture_asset_count"] == 8
    assert report["picture_binding_count"] == 8
    assert report["picture_css_form_count"] == 4
    assert report["picture_data_uri_count"] == 8
    assert report["html_activity_count"] == 160
    assert report["context_group_count"] == 40
    assert report["context_group_passage_count"] == 40
    assert report["matching_affordance_count"] == 19
    assert report["order_affordance_count"] == 8
    assert report["field_affordance_count"] == 16
    assert report["worksheet_css_form_count"] == 4
    assert report["pagination_guard_form_count"] == 4
    assert report["renderer_reused"] is True
    assert report["second_renderer_created"] is False

    assert report["python_blueprint_generation_used"] is False
    assert report["python_response_mode_assignment_used"] is False
    assert report["python_task_family_assignment_used"] is False
    assert report["python_learner_content_authoring_used"] is False
    assert report["python_answer_option_authoring_used"] is False
    assert report["python_visual_authoring_used"] is False
    assert report["current360_passage_mutated"] is False
    assert report["listening_modified"] is False
    assert report["a2_a2plus_unlocked"] is False


def test_u04_formv3c_a2_projection_preserves_gpt_prompt_and_current360_passage_authority():
    root = Path(target.__file__).resolve().parents[2]
    projected = target.load_projected_formv3c_forms(root)

    for ordinal, form in enumerate(projected, start=1):
        source = target.formv3c._load_asset(root, ordinal)["form"]
        source_contexts = {row["slot"]: row["passage"] for row in source["contexts"]}
        source_tasks = source["tasks"]

        assert len(form["activities"]) == len(source_tasks) == 40
        assert len(form["semantic_response_mode_counts"]) == 21
        assert len(form["picture_bindings"]) == 2
        assert target._context_group_ranges(form) == [
            (0, 2), (3, 5), (6, 10), (11, 15), (16, 20),
            (21, 25), (26, 29), (30, 33), (34, 36), (37, 39),
        ]

        seen = set()
        for activity, task in zip(form["activities"], source_tasks):
            assert activity["prompt"] == task["prompt"]
            assert activity["context_role"] == task["context_role"]
            assert activity["response_field_count"] == task["response_field_count"]
            assert activity["response_labels"] == [
                str(row.get("label") or "").strip()
                for row in task.get("response_fields") or []
            ]
            key = (task["section"], task["context_role"])
            expected_stimulus = source_contexts[task["context_role"]] if key not in seen else ""
            assert activity["stimulus"] == expected_stimulus
            seen.add(key)

            if activity["response_mode"] == "select_one":
                assert activity["options"] == task["options"]
            if task["response_mode"] == "ORDER_SEQUENCE":
                assert activity["response_mode"] == "ordered_tokens"
                assert len(activity["ordered_tokens"]) == task["response_field_count"]
            if task["response_mode"] in target.MATCHING_MODES:
                assert activity["response_mode"] == "ordered_tokens"
                assert len(activity["ordered_tokens"]) == len(task["left_items"]) + len(task["right_options"])
            if task["response_mode"] in target.FIELD_MODES:
                assert activity["response_mode"] == "ordered_tokens"
                assert len(activity["ordered_tokens"]) == task["response_field_count"]


def test_u04_formv3c_a2_picture_manifest_materializes_exact_eight_gpt_designed_svg_assets():
    root = Path(target.__file__).resolve().parents[2]
    payload = target._load_picture_manifest(root)
    assets = target._picture_assets(root)

    assert len(payload["assets"]) == 8
    assert len(assets) == 8
    assert payload["authoring_provenance"]["visual_asset_design"] == "GPT-5.6_SOL_DIRECT_DESIGN"
    assert payload["authoring_provenance"]["python_visual_authoring_used"] is False

    expected = {
        "U04-FORMV3C-F01-A2-POSITION",
        "U04-FORMV3C-F01-DE2-DIFF",
        "U04-FORMV3C-F02-A2-LABEL",
        "U04-FORMV3C-F02-DE1-DIFF",
        "U04-FORMV3C-F03-A1-POSITION",
        "U04-FORMV3C-F03-DE1-DIFF",
        "U04-FORMV3C-F04-A1-LABEL",
        "U04-FORMV3C-F04-DE1-DIFF",
    }
    assert set(assets) == expected
    for asset in assets.values():
        assert asset["status"] == "MATERIALIZED_STATIC_SVG"
        assert asset["bytes"] > 500
        assert len(asset["sha256"]) == 64
        assert asset["path"].is_file()
        assert asset["path"].read_text(encoding="utf-8").lstrip().startswith("<svg")


def test_u04_formv3c_a3r1_rendered_html_keeps_contexts_together_and_adds_field_affordances():
    forms = target.load_projected_formv3c_forms()

    for form in forms:
        html = target.render_formv3c_with_existing_renderer(form)
        activities = form["activities"]
        assert html.count('<article class="activity">') == 40
        assert html.count('class="u04-context-group"') == 10
        assert html.count('<div class="stimulus">') == 10
        assert html.count('class="matching-answer-grid"') == sum(
            activity["semantic_response_mode"] in target.MATCHING_MODES
            for activity in activities
        )
        assert html.count('class="order-answer-grid"') == sum(
            activity["semantic_response_mode"] == "ORDER_SEQUENCE"
            for activity in activities
        )
        assert html.count('class="field-answer-grid"') == sum(
            activity["semantic_response_mode"] in target.FIELD_MODES
            for activity in activities
        )
        assert target.WORKSHEET_STYLE_ID in html
        assert target.PICTURE_STYLE_ID in html
        assert target.pagination.PDF_PAGINATION_STYLE_ID in html
        assert html.count("data:image/svg+xml;base64,") == 2
        assert ".u04-context-group:nth-of-type(" in html
        assert 'class="choice-mark"' in html
        assert 'class="write-line"' in html
        assert 'class="speaking-box"' in html
        assert "reference_answer" not in html
        assert "correct_option_index" not in html
        assert "question_id" not in html
        assert "episode_id" not in html


def test_u04_formv3c_a3r1_materializer_reuses_chromium_chain_without_real_browser(tmp_path):
    def fake_runner(_chromium, *, source_html, output_path, mode):
        assert mode == "PDF"
        assert Path(source_html).is_file()
        html = Path(source_html).read_text(encoding="utf-8")
        assert target.PICTURE_STYLE_ID in html
        assert html.count("data:image/svg+xml;base64,") == 2
        assert html.count('class="u04-context-group"') == 10
        marker = Path(output_path).name.encode("ascii")
        Path(output_path).write_bytes(b"%PDF-1.4\n" + marker + b"\n" + b"x" * 2048)
        return {"status": "PASS_FAKE_BROWSER_CONTRACT"}

    manifest = target.materialize_form01_04_pdfs(
        output_root=tmp_path,
        chromium_path=Path(__file__),
        browser_runner=fake_runner,
        pdf_page_counter=lambda _path: 8,
    )

    assert manifest["machine_status"] == target.STATUS
    assert manifest["a3_r1_status"] == target.A3_R1_STATUS
    assert manifest["form_count"] == 4
    assert manifest["question_count"] == 160
    assert manifest["semantic_response_mode_coverage_count"] == 22
    assert manifest["materialized_picture_asset_count"] == 8
    assert manifest["materialized_pdf_count"] == 4
    assert manifest["context_group_count"] == 40
    assert manifest["human_visual_review_pending_count"] == 4
    assert manifest["human_pedagogical_review_pending_count"] == 4
    assert manifest["human_acceptance"] == "PENDING_ACTUAL_PDF_REVIEW"
    assert manifest["python_learner_content_authoring_used"] is False
    assert manifest["python_visual_authoring_used"] is False
    assert manifest["next_short_step"] == target.A3_R1_NEXT_SHORT_STEP
    assert (tmp_path / target.MANIFEST_NAME).is_file()
    for ordinal in range(1, 5):
        assert (tmp_path / "html" / f"Form{ordinal:02d}.html").is_file()
        assert (tmp_path / "pdf" / f"Form{ordinal:02d}.pdf").is_file()
