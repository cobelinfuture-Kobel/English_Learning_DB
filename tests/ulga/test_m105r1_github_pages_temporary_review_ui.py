import json
from pathlib import Path

import pytest

from ulga.builders.build_a1_private_pilot_next_unit_pages_payload import (
    build_payload,
    require_unit_coverage,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PAGE_ROOT = REPO_ROOT / "pages/private-pilot-review"
COMPLETED = {
    "GRAMMAR_ARTICLES_BASIC",
    "GRAMMAR_REGULAR_PLURAL_NOUNS",
    "GRAMMAR_SUBJECT_PRONOUNS",
}


def test_payload_selects_next_canonical_unit_with_eight_attempt1_items():
    payload = build_payload()
    assert payload["schema_version"] == "a1_private_pilot_pages_payload.v1"
    assert payload["grammar_unit_id"] not in COMPLETED
    assert payload["item_count"] == 8
    assert len(payload["items"]) == 8
    assert len({item["item_id"] for item in payload["items"]}) == 8
    assert all(item["attempt_sequence"] == 1 for item in payload["items"])
    assert payload["coverage_gate"]["status"] == "PASS_ALL_CANONICAL_ROWS_COVERED"
    assert payload["coverage_gate"]["canonical_egp_row_ids"]


def test_delivery_gate_fails_closed_for_missing_or_uncovered_rows():
    unit = {
        "grammar_unit_id": "UNIT_X",
        "canonical_egp_row_ids": ["ROW_1", "ROW_2"],
    }
    report = {
        "rows": [
            {"egp_row_id": "ROW_1", "status": "COVERED"},
            {"egp_row_id": "ROW_2", "status": "DRAFT_ONLY"},
        ]
    }
    with pytest.raises(RuntimeError, match="next_unit_pages_uncovered_canonical_rows"):
        require_unit_coverage(unit, report)
    with pytest.raises(RuntimeError, match="next_unit_pages_canonical_rows_missing"):
        require_unit_coverage({"grammar_unit_id": "UNIT_EMPTY"}, report)


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
