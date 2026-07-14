import json
from pathlib import Path

from ulga.builders.build_a1_private_pilot_next_unit_pages_payload import build_payload

REPO_ROOT = Path(__file__).resolve().parents[2]
PAGE_ROOT = REPO_ROOT / "pages/private-pilot-review"


def test_dynamic_payload_selects_one_canonical_next_unit_with_eight_items():
    payload = build_payload()
    assert payload["schema_version"] == "a1_private_pilot_pages_payload.v1"
    assert payload["grammar_unit_id"] not in {
        "GRAMMAR_ARTICLES_BASIC",
        "GRAMMAR_REGULAR_PLURAL_NOUNS",
    }
    assert payload["item_count"] == 8
    assert len(payload["items"]) == 8
    assert len({item["item_id"] for item in payload["items"]}) == 8
    assert all(item["attempt_sequence"] == 1 for item in payload["items"])


def test_payload_is_learner_safe_and_contains_no_answer_targets():
    text = json.dumps(build_payload(), ensure_ascii=False).casefold()
    assert '"answer_key"' not in text
    assert "canonical_target" not in text
    assert "model_target" not in text
    assert build_payload()["privacy"] == {
        "answer_key_included": False,
        "network_submission": False,
        "browser_local_only": True,
    }


def test_page_loads_local_generated_payload_and_exports_import_contract():
    html = (PAGE_ROOT / "index.html").read_text(encoding="utf-8")
    script = (PAGE_ROOT / "app.js").read_text(encoding="utf-8")
    assert 'id="items"' in html
    assert 'fetch("./next-unit.json"' in script
    assert "a1_grammar_text_mode_private_pilot_response_import.v1" in script
    assert "attempt_sequence:Number(item.dataset.attemptSequence)" in script
    assert "localStorage.setItem" in script
    assert "URL.createObjectURL" in script
    assert "github.com/api" not in script.casefold()
    assert "XMLHttpRequest" not in script
