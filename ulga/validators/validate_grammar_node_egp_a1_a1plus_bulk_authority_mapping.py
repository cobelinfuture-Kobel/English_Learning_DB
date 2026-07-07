import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_bulk_authority_mapping.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_bulk_authority_mapping_summary.json"
EXPECTED_TASK = "R7-M95A_A1A1PLUSGrammarEGPAuthorityMappingBulkBuilder"
EXPECTED_LEVEL_BAND = ["A1", "A1_PLUS"]
VALID_CLASSES = {"ALREADY_PATCHED", "NEEDS_REFINED_CANDIDATE"}
MIN_TARGET_COUNT = 10


def fail(message):
    print("FAIL: " + message)
    return False


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL: {path}: {exc}")
        return None


def validate():
    print("Validating A1/A1_PLUS bulk authority mapping...")
    report = load(REPORT_PATH)
    summary = load(SUMMARY_PATH)
    if not isinstance(report, dict) or not isinstance(summary, dict):
        return fail("required report structures missing")
    if report.get("task_id") != EXPECTED_TASK or summary.get("task_id") != EXPECTED_TASK:
        return fail("task_id mismatch")
    if report.get("level_band") != EXPECTED_LEVEL_BAND or summary.get("level_band") != EXPECTED_LEVEL_BAND:
        return fail("level_band mismatch")
    if report.get("mapping_scope") != "REPORT_ONLY_NO_CANONICAL_WRITE":
        return fail("mapping_scope mismatch")
    constraints = report.get("scope_constraints", {})
    for key in [
        "canonical_grammar_write_allowed",
        "egp_evidence_refs_write_allowed",
        "egp_form_evidence_refs_write_allowed",
        "coverage_increase_allowed",
        "practicebank_generation_allowed",
        "learner_state_write_allowed",
        "runtime_change_allowed",
    ]:
        if constraints.get(key) is not False:
            return fail(f"constraint must be false: {key}")
    records = report.get("records", [])
    if len(records) < MIN_TARGET_COUNT:
        return fail("target inventory too small for A1/A1_PLUS bulk mode")
    classes = {}
    ids = set()
    for record in records:
        grammar_id = record.get("grammar_id")
        if not grammar_id or grammar_id in ids:
            return fail("missing or duplicate grammar_id")
        ids.add(grammar_id)
        classification = record.get("classification")
        if classification not in VALID_CLASSES:
            return fail("unexpected classification")
        if record.get("canonical_write_allowed") is not False:
            return fail("record canonical_write_allowed must be false")
        classes[classification] = classes.get(classification, 0) + 1
    if summary.get("target_count") != len(records):
        return fail("summary target_count mismatch")
    if summary.get("classification_counts") != dict(sorted(classes.items())):
        return fail("classification_counts mismatch")
    if summary.get("already_patched_count") != classes.get("ALREADY_PATCHED", 0):
        return fail("already_patched_count mismatch")
    if summary.get("needs_refined_candidate_count") != classes.get("NEEDS_REFINED_CANDIDATE", 0):
        return fail("needs_refined_candidate_count mismatch")
    if summary.get("canonical_grammar_write_allowed") is not False:
        return fail("canonical write must be false")
    if summary.get("coverage_increase_allowed") is not False:
        return fail("coverage increase must be false")
    if summary.get("next_short_step") != "R7-M96A_A1A1PLUSBulkRefinedEGPCandidateSearch":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason must be NONE")
    print("A1/A1_PLUS bulk authority mapping validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
