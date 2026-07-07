import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_family_gated_candidate_suggestions.py"
VALIDATOR = BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_family_gated_candidate_suggestions.py"
DATA_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_family_gated_candidate_suggestions.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_family_gated_candidate_suggestions_summary.json"
BATCH01_IDS = {
    "GRAMMAR_ARTICLES_BASIC",
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
    "GRAMMAR_BE_VERB_BASIC",
    "GRAMMAR_CAN_STATEMENT",
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC",
}


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_builder_can_run():
    result = run_command([sys.executable, str(BUILDER)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert DATA_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_contract_and_safety_flags():
    data = load_json(DATA_PATH)
    summary = load_json(SUMMARY_PATH)
    assert data["task_id"] == "R7-M62_GrammarNodeEGPFamilyGatedCandidateBuilderImplementation"
    assert summary["task_id"] == "R7-M62_GrammarNodeEGPFamilyGatedCandidateBuilderImplementation"
    scope = data["scope_constraints"]
    assert scope["no_runtime_implementation"] is True
    assert scope["no_practicebank_generation"] is True
    assert scope["no_learner_state_write"] is True
    assert scope["no_auto_egp_row_selection"] is True
    assert scope["no_authority_write"] is True


def test_batch01_records_have_gate_metadata():
    data = load_json(DATA_PATH)
    records = {row["grammar_id"]: row for row in data["records"]}
    assert BATCH01_IDS <= set(records)
    for grammar_id in BATCH01_IDS:
        row = records[grammar_id]
        assert row["gate_configured"] is True
        assert row["grammar_family"]
        assert row["mapping_mode"] in {"grammar", "lexico_grammar", "collocation_sensitive"}
        assert row["review_required"] is True
        assert row["learner_state_write"] is False
        assert row["practicebank_generation"] is False


def test_summary_counts_match_records():
    data = load_json(DATA_PATH)
    summary = load_json(SUMMARY_PATH)
    records = data["records"]
    total = sum(len(row["family_gated_candidate_suggestions"]) for row in records)
    missing = sum(1 for row in records if row["gate_configured"] and not row["family_gated_candidate_suggestions"])
    assert summary["gated_record_count"] == len(records)
    assert summary["total_family_gated_candidate_count"] == total
    assert summary["configured_gate_records_without_candidates"] == missing
    assert summary["operator_review_required"] is True
    assert summary["next_short_step"] == "R7-M63_GrammarNodeEGPFamilyGatedCandidateReadback"
    assert summary["stop_reason"] == "NONE"
