from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PAGE_ROOT = REPO_ROOT / "pages/private-pilot-review"


def test_temporary_review_page_contains_exact_targeted_items():
    html = (PAGE_ROOT / "index.html").read_text(encoding="utf-8")
    expected = {
        "GRAMMAR_REGULAR_PLURAL_NOUNS__TFX_P04",
        "GRAMMAR_REGULAR_PLURAL_NOUNS__TFX_P05",
        "GRAMMAR_REGULAR_PLURAL_NOUNS__TFX_P06",
        "GRAMMAR_REGULAR_PLURAL_NOUNS__TFX_A02",
    }
    assert html.count('class="panel item"') == 4
    for item_id in expected:
        assert html.count(item_id) == 1
    assert "Source form:</strong> cat" in html
    assert "Supplied parts:</strong> es | box" in html


def test_public_page_contains_no_answer_key_or_productive_model_targets():
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (PAGE_ROOT / "index.html", PAGE_ROOT / "app.js")
    ).casefold()
    assert "answer_key" not in combined
    assert "canonical_target" not in combined
    assert "model_target" not in combined
    for forbidden in ('"cats"', '"boxes"', '"buses"'):
        assert forbidden not in combined


def test_export_contract_matches_existing_importer_boundary():
    script = (PAGE_ROOT / "app.js").read_text(encoding="utf-8")
    required = {
        'import_schema_version: "a1_grammar_text_mode_private_pilot_response_import.v1"',
        "session_id:",
        "learner_ref:",
        "operator_ref:",
        "started_at:",
        "completed_at:",
        "evidence_source_ref:",
        "item_id:",
        "response_text:",
        "attempt_sequence: 2",
        "submitted_at:",
        'evaluator_type = "MANUAL"',
        "evaluator_ref",
    }
    for marker in required:
        assert marker in script
    assert "fetch(" not in script
    assert "XMLHttpRequest" not in script
    assert "github.com/api" not in script.casefold()


def test_answers_are_browser_local_and_download_only():
    script = (PAGE_ROOT / "app.js").read_text(encoding="utf-8")
    assert "localStorage.setItem" in script
    assert "localStorage.removeItem" in script
    assert "URL.createObjectURL" in script
    assert 'link.download = `${payload.session.session_id}.json`' in script
