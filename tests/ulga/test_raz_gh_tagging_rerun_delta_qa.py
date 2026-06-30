from tools import raz_gh_tagging_rerun_delta_qa as qa


def test_pattern_bucket_classification():
    assert qa.pattern_bucket("I am Riya [REE-yaw], and I am nine.") == "pronunciation_annotation"
    assert qa.pattern_bucket("They danced by the light of the moon, the moon, the moon.") == "poetic_or_repetitive_line"
    assert qa.pattern_bucket("And there in the wood a piggy-wig stood.") == "narrative_or_clause_inversion"
    assert qa.pattern_bucket("The cat sat on the mat.") == "normal_declarative_sentence"


def test_family_classification():
    assert qa.classify_family(family="unknown_theme", baseline=10, current=9) == "EXPECTED_IMPROVEMENT"
    assert qa.classify_family(family="unknown_pattern", baseline=10, current=10) == "FAIL_REGRESSION"
    assert qa.classify_family(family="unknown_grammar", baseline=10, current=10) == "STABLE_ACCEPTABLE"
    assert qa.classify_family(family="section_heading_detected", baseline=10, current=11) == "REVIEW_REQUIRED"
    assert qa.classify_family(family="dialogue_or_quotation_warning", baseline=0, current=0) == "STABLE_ACCEPTABLE"


def test_theme_audit_group_uses_proxy_note():
    records = [
        {
            "record_id": "1",
            "record_type": "sentence",
            "title": "Rapunzel",
            "book_id": "1",
            "page_unit_id": "P1",
            "text": "Rapunzel lived in a tower.",
            "mapped_theme": "StoryFable",
            "pattern_tags": ["simple_declarative_svo"],
            "warnings": [],
        }
    ]
    result = qa.build_theme_audit_group(
        records,
        titles={"Rapunzel"},
        allowed_themes={"StoryFable"},
        label="folktale/storyfable",
    )
    assert result["fail_count"] == 0
    assert "pre-patch" in result["inference_note"]
