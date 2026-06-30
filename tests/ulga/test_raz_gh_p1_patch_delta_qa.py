from tools import raz_gh_p1_patch_delta_qa as qa


def test_looks_like_heading_line():
    assert qa.looks_like_heading_line("Look Out for the Spout")
    assert qa.looks_like_heading_line("Listen for the Song")
    assert not qa.looks_like_heading_line("Look around.")
    assert not qa.looks_like_heading_line("Do not become distracted when a goal is within reach.")


def test_classify_family_for_s6t():
    assert qa.classify_family("unknown_theme", baseline=10, current=9) == "EXPECTED_IMPROVEMENT"
    assert qa.classify_family("unknown_pattern", baseline=10, current=10) == "EXPECTED_STABILITY"
    assert qa.classify_family("unknown_pattern", baseline=10, current=9) == "FAIL_REGRESSION"
    assert qa.classify_family("unknown_grammar", baseline=10, current=10) == "EXPECTED_STABILITY"
    assert qa.classify_family("unknown_grammar", baseline=10, current=11) == "FAIL_REGRESSION"


def test_theme_audit_group_uses_current_state_proxy_note():
    records = [
        {
            "record_id": "1",
            "record_type": "sentence",
            "title": "Billy Gets Lost",
            "book_id": "1",
            "page_unit_id": "P1",
            "text": "Billy is a puppy.",
            "mapped_theme": "Feelings",
            "theme_source": "title_override_map_v2",
            "grammar_tags": [],
            "pattern_tags": [],
            "warnings": [],
        }
    ]
    result = qa.build_theme_audit_group(
        records,
        titles={"Billy Gets Lost"},
        allowed_themes={"Feelings"},
        label="social/emotional/moral-choice",
    )
    assert result["fail_count"] == 0
    assert "Current-state proxy audit" in result["inference_note"]
