from tools import raz_gh_p1_targeted_patch_plan as plan


def test_theme_category_prefers_poetry_bucket_before_fantasy():
    record = {
        "title": "The Owl and the Pussycat",
        "record_type": "sentence",
    }
    assert plan.theme_category_for_record(record) == "poetry_literary_misc_deferred"


def test_pattern_category_detects_direct_speech_before_question():
    record = {
        "text": '"Do you know the way to my house?" Billy asks.',
        "is_direct_speech": True,
        "is_question": True,
        "is_imperative": False,
        "title": "Billy Gets Lost",
    }
    assert plan.pattern_category_for_record(record) == "quoted_expressive_sentence"


def test_grammar_category_keeps_headings_out_of_imperative_bucket():
    heading_record = {
        "text": "Look Out for the Spout",
        "is_heading": True,
        "record_type": "section_heading",
        "is_imperative": True,
    }
    assert plan.grammar_category_for_record(heading_record) == "section_heading_driven_artifact"
