import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_raz_usage_evidence_selection_plan.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_raz_usage_evidence_selection_plan_summary.json"
EXPECTED_TASK = "R7-M78A_Batch01RAZUsageEvidenceSelectionPlanArtifactBuilder"
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
    print("Validating Batch 01 RAZ usage evidence selection plan...")
    if not DATA_PATH.exists() or not SUMMARY_PATH.exists():
        return fail("required output missing")
    data = load(DATA_PATH)
    summary = load(SUMMARY_PATH)
    if not isinstance(data, dict) or not isinstance(summary, dict):
        return fail("top-level outputs must be objects")
    if data.get("task_id") != EXPECTED_TASK or summary.get("task_id") != EXPECTED_TASK:
        return fail("task_id mismatch")
    scope = data.get("scope_constraints", {})
    for key in [
        "no_runtime_implementation",
        "no_practicebank_generation",
        "no_learner_state_write",
        "no_auto_egp_row_selection",
        "no_authority_write",
        "no_egp_evidence_refs_write",
        "no_coverage_increase",
        "no_final_usage_evidence_acceptance",
    ]:
        if scope.get(key) is not True:
            return fail(f"scope flag not true: {key}")
    records = data.get("records", [])
    if {record.get("grammar_id") for record in records} != EXPECTED_IDS:
        return fail("unexpected target grammar ids")
    source_total = 0
    selected_total = 0
    missing = 0
    seen = set()
    for record in records:
        source_count = record.get("source_filtered_candidate_count")
        selected_count = record.get("selected_candidate_count")
        selected = record.get("selected_candidates", [])
        if source_count < selected_count:
            return fail("source count below selected count")
        if selected_count != len(selected):
            return fail("selected count mismatch inside record")
        if record.get("selection_status") != "PROPOSED_SELECTION_REQUIRES_OPERATOR_REVIEW":
            return fail("record selection status mismatch")
        source_total += source_count
        selected_total += selected_count
        if not selected:
            missing += 1
        for candidate in selected:
            key = (record.get("grammar_id"), candidate.get("sentence_text", "").strip().lower())
            if key in seen:
                return fail("duplicate selected sentence for grammar id")
            seen.add(key)
            if candidate.get("source_type") != "RAZ":
                return fail("candidate source_type must be RAZ")
            if candidate.get("quality_filter_status") != "KEPT":
                return fail("selected candidate must come from kept filtered candidates")
            if candidate.get("selection_status") != "PROPOSED_RAZ_USAGE_EVIDENCE":
                return fail("selected candidate selection_status mismatch")
            if candidate.get("operator_review_required") is not True:
                return fail("operator review flag missing")
            if not candidate.get("sentence_text"):
                return fail("candidate sentence_text missing")
    if summary.get("source_filtered_candidate_count") != source_total:
        return fail("source_filtered_candidate_count mismatch")
    if summary.get("selected_candidate_count") != selected_total:
        return fail("selected_candidate_count mismatch")
    if summary.get("unselected_candidate_count") != source_total - selected_total:
        return fail("unselected_candidate_count mismatch")
    if summary.get("targets_without_selected_candidates") != missing:
        return fail("targets_without_selected_candidates mismatch")
    if summary.get("operator_review_required") is not True:
        return fail("operator_review_required must be true")
    if summary.get("authority_write_allowed") is not False:
        return fail("authority_write_allowed must be false")
    if summary.get("evidence_refs_write_allowed") is not False:
        return fail("evidence_refs_write_allowed must be false")
    if summary.get("coverage_increase_allowed") is not False:
        return fail("coverage_increase_allowed must be false")
    if summary.get("final_acceptance_allowed") is not False:
        return fail("final_acceptance_allowed must be false")
    if summary.get("next_short_step") != "R7-M79A_Batch01RAZUsageEvidenceSelectionPlanReadback":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason must be NONE")
    print("Batch 01 RAZ usage evidence selection plan validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
