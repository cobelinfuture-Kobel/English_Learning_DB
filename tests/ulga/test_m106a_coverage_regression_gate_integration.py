from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github/workflows/r7-m106-a1-a1plus-coverage-recheck.yml"


def test_coverage_gate_watches_all_upstream_a1_sources():
    text = WORKFLOW.read_text(encoding="utf-8")
    required_paths = {
        "build_a1_grammar_text_mode_practice_item_fullfix.py",
        "build_a1_grammar_derived_pedagogy_fullfix.py",
        "build_a1_grammar_operator_confirmation_text_mode_pilot.py",
        "build_a1_grammar_text_mode_private_pilot_package.py",
        "a1_grammar_text_mode_private_pilot_package.json",
    }
    for path in required_paths:
        assert path in text


def test_coverage_gate_blocks_all_regression_classes():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "canonical_row_count'] == 109" in text
    assert "covered_row_count'] == 109" in text
    assert "coverage_percent'] == 100.0" in text
    assert "missing_row_count'] == 0" in text
    assert "draft_only_row_count'] == 0" in text
    assert "unexpected_row_count'] == 0" in text
    assert "schedule:" in text
    assert "workflow_dispatch:" in text
