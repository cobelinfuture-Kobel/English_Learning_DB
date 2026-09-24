import pytest

from ulga.validators import validate_a1fs_v1_u03fullfix_d0_final_acceptance_checkpoint as v


def _manifest():
    return {
        "status": v.EXPECTED_D0_STATUS,
        "final_acceptance": "PASS",
        "q1_q10_scope": "FINAL_ACCEPTED",
        "d3_data_content_acceptance": {
            "status": "PASS", "items": 800, "forms": 20,
            "section_acceptance": {key: "PASS" for key in "ABCDE"},
            "content_exact_repeat_rate": 0.0112,
            "content_exact_repeat_threshold": 0.03,
            "scene_family_count": 17,
            "micro_scene_duplicate_context_count": 0,
        },
        "d2_semantic_acceptance": {
            "status": "PASS", "reviewed_items": 800, "passed_items": 800, "failed_items": 0,
            "section_acceptance": {key: "PASS" for key in "ABCDE"},
            "stories_reviewed": 20, "stories_passed": 20, "stories_failed": 0,
        },
        "d1_pdf_acceptance": {
            "status": v.EXPECTED_D1_STATUS,
            "questionbook_pages": 80, "answerkey_pages": 20,
            "prompt_alignment": 800, "answer_alignment": 800,
            "blank_pages": 0, "clipped_or_edge_violations": 0,
            "answer_label_leakage": 0, "full_page_visual_review": "PASS",
        },
        "source_identity": dict(v.ACCEPTED_SOURCE_IDENTITY),
        "claim_boundaries": {
            "q6_regenerated": False, "q11_created": False, "unit04_started": False,
            "generic_contract_started": False, "pdf_renderer_modified_source_content": False,
        },
    }


def test_d0_checkpoint_accepts_exact_sha_bound_manifest():
    checkpoint = v.build_checkpoint(_manifest())
    assert checkpoint["status"] == v.PASS_STATUS
    assert checkpoint["unit03_final_acceptance"] == "PASS"


def test_d0_checkpoint_fails_on_identity_drift():
    manifest = _manifest()
    manifest["source_identity"]["inventory_sha256"] = "0" * 64
    with pytest.raises(v.U03FullFixD0AcceptanceError, match="D0_SOURCE_IDENTITY_DRIFT"):
        v.validate_d0_manifest(manifest)


def test_stale_second_location_frame_is_rejected():
    rows = [{
        "item_id": "U03-F01-D08", "section": "D", "micro_scene_setting": "in the classroom",
        "micro_scene_context": "In a new situation in the classroom, Jack is the only named person.",
        "stimulus": "Jack arrives in the classroom. ___ has old pens at the train station.",
    }]
    failures = v.semantic_regression_failures(rows)
    assert [row["code"] for row in failures] == ["STALE_LOCATION_FRAME"]


def test_temporal_prefix_must_preserve_proper_name_capitalization():
    rows = [{
        "item_id": "U03-F01-D01", "section": "D", "micro_scene_setting": "in the classroom",
        "micro_scene_context": "During morning practice, sofia, the only person in focus, is in the classroom.",
        "stimulus": "___ can see two bags in the classroom.",
    }]
    failures = v.semantic_regression_failures(rows)
    assert any(row["code"] == "LOWERCASE_PROPER_NAME" and row["detail"] == ["Sofia"] for row in failures)


def test_target_setting_subphrase_is_not_a_false_positive():
    rows = [{
        "item_id": "U03-F05-A06", "section": "A", "micro_scene_setting": "at home with family",
        "micro_scene_context": "Emma is at home with family with Jack.",
        "stimulus": "___ have red photos at home with family.",
    }]
    assert v.semantic_regression_failures(rows) == []
