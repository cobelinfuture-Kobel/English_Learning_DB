import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_raz_usage_evidence_operator_decisions.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_raz_usage_evidence_operator_decisions_summary.json"
EXPECTED_TASK = "R7-M80A_Batch01RAZUsageEvidenceSelectionOperatorDecisionArtifact"
EXPECTED_IDS = {
    "GRAMMAR_ARTICLES_BASIC": 5,
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE": 5,
    "GRAMMAR_BE_VERB_BASIC": 6,
    "GRAMMAR_CAN_STATEMENT": 7,
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC": 6,
}


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL: {path}: {exc}")
        return None


def fail(message):
    print("FAIL: " + message)
    return False


def validate():
    print("Validating Batch 01 RAZ usage evidence operator decisions...")
    if not DATA_PATH.exists() or not SUMMARY_PATH.exists():
        return fail("required output missing")
    data = load(DATA_PATH)
    summary = load(SUMMARY_PATH)
    if not isinstance(data, dict) or not isinstance(summary, dict):
        return fail("top-level outputs must be objects")
    if data.get("task_id") != EXPECTED_TASK or summary.get("task_id") != EXPECTED_TASK:
        return fail("task_id mismatch")
    if data.get("operator_decision_status") != "APPROVED_R7_M79A_PROPOSED_SELECTIONS":
        return fail("operator_decision_status mismatch")
    if data.get("decision_scope") != "RAZ_USAGE_EVIDENCE_SELECTION_ONLY":
        return fail("decision_scope mismatch")
    for key in [
        "authority_write_allowed",
        "egp_evidence_refs_write_allowed",
        "coverage_increase_allowed",
        "practicebank_generation_allowed",
        "learner_state_write_allowed",
        "runtime_change_allowed",
    ]:
        if data.get(key) is not False or summary.get(key) is not False:
            return fail(f"safety flag must be false: {key}")
    records = data.get("records", [])
    if {record.get("grammar_id") for record in records} != set(EXPECTED_IDS):
        return fail("unexpected grammar ids")
    total = 0
    seen = set()
    for record in records:
        grammar_id = record.get("grammar_id")
        expected_count = EXPECTED_IDS[grammar_id]
        examples = record.get("approved_examples", [])
        if len(examples) != expected_count:
            return fail(f"approved example count mismatch for {grammar_id}")
        if record.get("decision") not in {
            "APPROVE_RAZ_USAGE_EVIDENCE_SELECTIONS",
            "APPROVE_RAZ_SEMANTIC_USAGE_EVIDENCE_SELECTIONS",
        }:
            return fail("unexpected decision")
        for example in examples:
            key = (grammar_id, example.get("sentence_text"))
            if key in seen:
                return fail("duplicate approved example")
            seen.add(key)
            if example.get("source_type") != "RAZ":
                return fail("source_type must be RAZ")
            if not example.get("sentence_text") or not example.get("source_path"):
                return fail("example missing required source fields")
            total += 1
    if summary.get("target_count") != len(EXPECTED_IDS):
        return fail("target_count mismatch")
    if summary.get("approved_example_count") != total:
        return fail("approved_example_count mismatch")
    if summary.get("approved_example_count_by_grammar_id") != EXPECTED_IDS:
        return fail("approved_example_count_by_grammar_id mismatch")
    if summary.get("next_short_step") != "R7-M80A_LocalValidationAndOperatorDecisionArtifactCIReadback":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason must be NONE")
    print("Batch 01 RAZ usage evidence operator decision validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
