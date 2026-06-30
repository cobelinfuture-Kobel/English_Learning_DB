from tools import raz_h_warning_cluster_and_report_coverage_qa as qa


def test_coverage_status_matrix():
    assert qa.coverage_status(3, 3) == "PASS"
    assert qa.coverage_status(5, 0) == "MISSING_FROM_FLAT_REPORT"
    assert qa.coverage_status(5, 2) == "UNDERREPORTED"
    assert qa.coverage_status(2, 5) == "OVERREPORTED"


def test_classify_unknown_pattern_bucket():
    assert qa.classify_unknown_pattern_bucket("I am Riya [REE-yaw], and I am nine.") == "pronunciation_annotation"
    assert qa.classify_unknown_pattern_bucket("They danced by the light of the moon, the moon, the moon.") == "poetic_or_repetitive_line"
    assert qa.classify_unknown_pattern_bucket("Then hand in hand they danced in the sand.") == "narrative_or_clause_inversion"
    assert qa.classify_unknown_pattern_bucket("The cat sat on the mat.") == "normal_declarative_sentence"


def test_classify_section_heading():
    assert qa.classify_section_heading("Around the World") == "true_heading"
    assert qa.classify_section_heading("Birds in winter") == "ambiguous"
    assert qa.classify_section_heading("This is a full sentence.") == "likely_false_positive"
