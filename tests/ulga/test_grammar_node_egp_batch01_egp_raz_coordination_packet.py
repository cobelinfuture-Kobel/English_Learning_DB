import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_batch01_egp_raz_coordination_packet.py"
VALIDATOR = BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_batch01_egp_raz_coordination_packet.py"
DATA_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_egp_raz_coordination_packet.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_egp_raz_coordination_packet_summary.json"
EXPECTED_IDS = {
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


def test_coordination_builder_can_run():
    result = run_command([sys.executable, str(BUILDER)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert DATA_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_coordination_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_coordination_contract_and_safety_flags():
    data = load_json(DATA_PATH)
    summary = load_json(SUMMARY_PATH)
    assert data["task_id"] == "R7-M83A_Batch01EGPRAZCoordinationPacketBuilder"
    assert summary["task_id"] == "R7-M83A_Batch01EGPRAZCoordinationPacketBuilder"
    scope = data["scope_constraints"]
    assert scope["no_runtime_implementation"] is True
    assert scope["no_practicebank_generation"] is True
    assert scope["no_learner_state_write"] is True
    assert scope["no_authority_write"] is True
    assert scope["no_egp_evidence_refs_write"] is True
    assert scope["no_raz_usage_attachment_write"] is True
    assert scope["no_coverage_increase"] is True
    assert scope["operator_review_required"] is True
    assert summary["authority_write_allowed"] is False
    assert summary["egp_evidence_refs_write_allowed"] is False
    assert summary["raz_usage_attachment_write_allowed"] is False
    assert summary["coverage_increase_allowed"] is False


def test_coordination_records_cover_batch01_targets():
    data = load_json(DATA_PATH)
    records = data["records"]
    assert {record["grammar_id"] for record in records} == EXPECTED_IDS
    for record in records:
        assert record["egp_layer"]["operator_review_required"] is True
        assert record["raz_layer"]["operator_review_required"] is False
        assert record["raz_layer"]["approved_example_count"] > 0
        permissions = record["write_permissions"]
        assert permissions["authority_write_allowed"] is False
        assert permissions["egp_evidence_refs_write_allowed"] is False
        assert permissions["raz_usage_attachment_write_allowed"] is False
        assert permissions["coverage_increase_allowed"] is False


def test_summary_counts_match_records():
    data = load_json(DATA_PATH)
    summary = load_json(SUMMARY_PATH)
    records = data["records"]
    rows_available = sum(1 for record in records if record["egp_layer"]["egp_row_id"])
    raz_examples = sum(record["raz_layer"]["approved_example_count"] for record in records)
    assert summary["target_count"] == len(records)
    assert summary["egp_rows_available_for_review"] == rows_available
    assert summary["egp_rows_unresolved"] == len(records) - rows_available
    assert summary["approved_raz_usage_example_count"] == raz_examples
    assert summary["next_short_step"] == "R7-M84A_Batch01EGPRAZCoordinationPacketReadback"
    assert summary["stop_reason"] == "NONE"


def test_can_statement_is_split_layer():
    data = load_json(DATA_PATH)
    record = next(item for item in data["records"] if item["grammar_id"] == "GRAMMAR_CAN_STATEMENT")
    assert record["egp_layer"]["egp_row_id"] == "1741163708329x931125497510935300"
    assert record["egp_layer"]["evidence_role"] == "EGP_FORM_EVIDENCE"
    assert record["raz_layer"]["evidence_role"] == "RAZ_SEMANTIC_USAGE_EVIDENCE"
    assert record["raz_layer"]["approved_example_count"] == 7
