import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
VALIDATOR = BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_batch01_raz_usage_evidence_operator_decisions.py"
DATA_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_raz_usage_evidence_operator_decisions.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_raz_usage_evidence_operator_decisions_summary.json"
EXPECTED_IDS = {
    "GRAMMAR_ARTICLES_BASIC": 5,
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE": 5,
    "GRAMMAR_BE_VERB_BASIC": 6,
    "GRAMMAR_CAN_STATEMENT": 7,
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC": 6,
}


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_operator_decision_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_operator_decision_contract_and_safety_flags():
    data = load_json(DATA_PATH)
    summary = load_json(SUMMARY_PATH)
    assert data["task_id"] == "R7-M80A_Batch01RAZUsageEvidenceSelectionOperatorDecisionArtifact"
    assert summary["task_id"] == "R7-M80A_Batch01RAZUsageEvidenceSelectionOperatorDecisionArtifact"
    assert data["operator_decision_status"] == "APPROVED_R7_M79A_PROPOSED_SELECTIONS"
    assert data["decision_scope"] == "RAZ_USAGE_EVIDENCE_SELECTION_ONLY"
    for key in [
        "authority_write_allowed",
        "egp_evidence_refs_write_allowed",
        "coverage_increase_allowed",
        "practicebank_generation_allowed",
        "learner_state_write_allowed",
        "runtime_change_allowed",
    ]:
        assert data[key] is False
        assert summary[key] is False


def test_operator_decision_records_cover_batch01_targets():
    data = load_json(DATA_PATH)
    records = data["records"]
    assert {record["grammar_id"] for record in records} == set(EXPECTED_IDS)
    for record in records:
        grammar_id = record["grammar_id"]
        assert len(record["approved_examples"]) == EXPECTED_IDS[grammar_id]
        for example in record["approved_examples"]:
            assert example["source_type"] == "RAZ"
            assert example["source_path"]
            assert example["sentence_text"]
            assert example["pattern_id"]


def test_summary_counts_match_records():
    data = load_json(DATA_PATH)
    summary = load_json(SUMMARY_PATH)
    records = data["records"]
    total = sum(len(record["approved_examples"]) for record in records)
    by_id = {record["grammar_id"]: len(record["approved_examples"]) for record in records}
    assert summary["target_count"] == len(records)
    assert summary["approved_example_count"] == total
    assert summary["approved_example_count_by_grammar_id"] == by_id
    assert summary["next_short_step"] == "R7-M80A_LocalValidationAndOperatorDecisionArtifactCIReadback"
    assert summary["stop_reason"] == "NONE"


def test_can_statement_semantic_usage_examples_are_approved():
    data = load_json(DATA_PATH)
    can_record = next(record for record in data["records"] if record["grammar_id"] == "GRAMMAR_CAN_STATEMENT")
    sentences = {example["sentence_text"] for example in can_record["approved_examples"]}
    assert "I can run." in sentences
    assert "I can jump." in sentences
    assert "I can hop." in sentences
    assert "I can ride." in sentences
    assert "I can climb." in sentences
    assert "I can play." in sentences
    assert "We can make sounds." in sentences
