import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_raz_usage_evidence_candidates.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_raz_usage_evidence_candidates_summary.json"
EXPECTED_TASK = "R7-M72A_Batch01RAZUsageEvidenceCandidateBuilderImplementation"
EXPECTED_IDS = {
    "GRAMMAR_ARTICLES_BASIC",
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
    "GRAMMAR_BE_VERB_BASIC",
    "GRAMMAR_CAN_STATEMENT",
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC",
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
    print("Validating Batch 01 RAZ usage evidence candidates...")
    if not DATA_PATH.exists() or not SUMMARY_PATH.exists():
        return fail("required output missing")
    data = load(DATA_PATH)
    summary = load(SUMMARY_PATH)
    if not isinstance(data, dict) or not isinstance(summary, dict):
        return fail("top-level outputs must be objects")
    if data.get("task_id") != EXPECTED_TASK or summary.get("task_id") != EXPECTED_TASK:
        return fail("task_id mismatch")
    scope = data.get("scope_constraints", {})
    for key in ["no_runtime_implementation", "no_practicebank_generation", "no_learner_state_write", "no_auto_egp_row_selection", "no_authority_write", "no_egp_evidence_refs_write", "no_coverage_increase"]:
        if scope.get(key) is not True:
            return fail(f"scope flag not true: {key}")
    records = data.get("records", [])
    if {record.get("grammar_id") for record in records} != EXPECTED_IDS:
        return fail("unexpected target grammar ids")
    total = 0
    missing = 0
    for record in records:
        candidates = record.get("candidates", [])
        if not candidates:
            missing += 1
        for candidate in candidates:
            if candidate.get("source_type") != "RAZ":
                return fail("candidate source_type must be RAZ")
            if candidate.get("operator_review_required") is not True:
                return fail("candidate operator review flag missing")
            if not candidate.get("sentence_text"):
                return fail("candidate sentence_text missing")
            if candidate.get("evidence_role") not in {"RAZ_USAGE_EVIDENCE", "RAZ_SEMANTIC_USAGE_EVIDENCE", "RAZ_PASSAGE_CONTEXT"}:
                return fail("invalid evidence_role")
            total += 1
    if summary.get("target_count") != len(records):
        return fail("target_count mismatch")
    if summary.get("total_raz_usage_candidate_count") != total:
        return fail("candidate total mismatch")
    if summary.get("targets_without_candidates") != missing:
        return fail("missing target count mismatch")
    if summary.get("operator_review_required") is not True:
        return fail("operator_review_required must be true")
    if summary.get("next_short_step") != "R7-M73A_Batch01RAZUsageEvidenceCandidateReadback":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason must be NONE")
    print("Batch 01 RAZ usage evidence candidate validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
