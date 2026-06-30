import pytest
from tools.raz.build_raz_a_reference_sentences import (
    check_reversed_word_anomaly,
    classify_sentence_role,
    apply_sentence_filters,
    apply_reference_duplicate_policy,
    build_qc_rows,
)

def test_check_reversed_word_anomaly():
    valid_words = {"turtles", "worms", "see", "five", "four", "fish"}
    
    # Clean forward sentence
    assert check_reversed_word_anomaly("I see four fish.", valid_words) is False
    
    # Anomalous sentence containing reversed words
    # "seltrut" reversed is "turtles", which is in valid_words
    # "evif" reversed is "five", which is in valid_words
    # "ees" reversed is "see", which is in valid_words
    assert check_reversed_word_anomaly("seltrut evif ees I I see four fish.", valid_words) is True
    assert check_reversed_word_anomaly("smrow I see.", valid_words) is True
    
    # Completely unknown words that don't reverse to valid words
    assert check_reversed_word_anomaly("xyz abc.", valid_words) is False

def test_anomaly_role_classification():
    valid_words = {"turtles", "worms", "see", "five", "four", "fish"}
    
    # Mixed direction anomaly sentence
    role, include, reason, direction, confidence, dir_reason = classify_sentence_role(
        clean_text="seltrut evif ees I I see four fish.",
        normalized_text="seltrut evif ees i i see four fish.",
        book_title="Test Book",
        page_no=3,
        page_count=10,
        sentence_boundary_status="clean",
        word_count=8,
        tokens=["seltrut", "evif", "ees", "i", "i", "see", "four", "fish"],
        duplicate_count=1,
        page_context="seltrut evif ees I I see four fish.",
        page_direction_context={},
        valid_words=valid_words,
    )
    
    assert role == "mixed_direction_text_artifact"
    assert include is False
    assert reason == "reversed_word_token_anomaly"
    assert direction == "mixed_direction_text_artifact"
    assert confidence == 0.0
    assert dir_reason == "reversed_word_token_anomaly"

def test_anomaly_pipeline_filtering_and_qc():
    valid_words = {"turtles", "worms", "see", "five", "four", "fish"}
    
    sentences = [
        {
            "sentence_id": "TEST_P003_S001",
            "book_id": "TEST_B001",
            "raz_level": "A",
            "book_title": "Test Book",
            "pdf_file": "test.pdf",
            "page_no": 3,
            "sentence_order_in_book": 1,
            "sentence_order_on_page": 1,
            "raw_text": "seltrut evif ees I I see four fish.",
            "clean_text": "seltrut evif ees I I see four fish.",
            "normalized_text": "seltrut evif ees i i see four fish.",
            "word_count": 8,
            "unique_word_count": 6,
            "char_count": 35,
            "sentence_boundary_status": "clean",
            "sentence_role": "unknown",
            "text_direction_status": "not_applicable",
            "directionality_confidence": 0.0,
            "directionality_reason": "not_applicable_non_reference",
            "include_in_reference": False,
            "include_in_unique_reference": False,
            "review_status": "not_required",
            "exclude_reason": "unknown_noise",
            "notes": "",
        }
    ]
    
    # 1. Apply filters
    apply_sentence_filters(
        sentences_v01=sentences,
        book_title="Test Book",
        page_count=10,
        page_context_by_page_no={3: "seltrut evif ees I I see four fish."},
        page_direction_context_by_page_no={3: {}},
        valid_words=valid_words,
    )
    
    s = sentences[0]
    assert s["sentence_role"] == "mixed_direction_text_artifact"
    assert s["text_direction_status"] == "mixed_direction_text_artifact"
    assert s["directionality_confidence"] == 0.0
    assert s["directionality_reason"] == "reversed_word_token_anomaly"
    assert s["include_in_reference"] is False
    assert s["include_in_unique_reference"] is False
    assert s["review_status"] == "pending_review"
    assert s["exclude_reason"] == "reversed_word_token_anomaly"
    
    # 2. Run duplicate policy
    apply_reference_duplicate_policy(sentences)
    assert s["include_in_reference"] is False
    assert s["include_in_unique_reference"] is False
    assert s["duplicate_reference_status"] == "non_reference"
    
    # 3. Build QC rows
    qc_rows = build_qc_rows(sentences)
    assert len(qc_rows) == 1
    qc = qc_rows[0]
    assert qc["issue_type"] == "reversed_word_token_anomaly"
    assert qc["review_status"] == "pending_review"
    assert qc["include_in_reference"] is False
