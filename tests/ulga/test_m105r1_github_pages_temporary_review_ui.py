import json
from pathlib import Path

from ulga.builders.build_a1_private_pilot_next_unit_pages_payload import build_payload

REPO_ROOT = Path(__file__).resolve().parents[2]
PAGE_ROOT = REPO_ROOT / "pages/private-pilot-review"
TARGET = "GRAMMAR_SUBJECT_PRONOUNS__TFX_P03"


def test_payload_contains_only_canonical_p03_attempt2():
    payload = build_payload()
    assert payload["schema_version"] == "a1_private_pilot_pages_payload.v1"
    assert payload["grammar_unit_id"] == "GRAMMAR_SUBJECT_PRONOUNS"
    assert payload["item_count"] == 1
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["item_id"] == TARGET
    assert item["attempt_sequence"] == 2
    assert item["options"] == ["They play football.", "Her book is red.", "This is my book."]


def test_payload_is_learner_safe_and_contains_no_answer_targets():
    payload = build_payload()
    text = json.dumps(payload, ensure_ascii=False).casefold()
    assert '"answer_key"' not in text
    assert "canonical_target" not in text
    assert "model_target" not in text
    assert payload["privacy"] == {
        "answer_key_included": False,
        "network_submission": False,
        "browser_local_only": True,
    }


def test_page_normalizes_numeric_option_to_text_and_exports_import_contract():
    html = (PAGE_ROOT / "index.html").read_text(encoding="utf-8")
    script = (PAGE_ROOT / "app.js").read_text(encoding="utf-8")
    assert 'id="items"' in html
    assert 'fetch("./next-unit.json"' in script
    assert "a1_grammar_text_mode_private_pilot_response_import.v1" in script
    assert "normalizedResponse(item)" in script
    assert "options[selected - 1]" in script
    assert "attempt_sequence:Number(item.dataset.attemptSequence)" in script
    assert "localStorage.setItem" in script
    assert "URL.createObjectURL" in script
    assert "github.com/api" not in script.casefold()
    assert "XMLHttpRequest" not in script
