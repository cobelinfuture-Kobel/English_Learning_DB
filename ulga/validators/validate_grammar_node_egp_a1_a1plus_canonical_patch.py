import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
GRAMMAR_PATH = BASE_DIR / "ulga" / "grammar" / "grammar_nodes.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_canonical_patch_summary.json"
EXPECTED_TASK = "R7-M99D_A1A1PLUSCanonicalPatchApplier"
EXPECTED_DEFERRED = {
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
    "GRAMMAR_REGULAR_PLURAL_NOUNS",
    "GRAMMAR_THIS_IS",
}
EXPECTED_CHANGED = {
    "GRAMMAR_BE_VERB_BASIC",
    "GRAMMAR_DEMONSTRATIVES_CONTRAST",
    "GRAMMAR_OBJECT_PRONOUNS_BASIC",
    "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS",
    "GRAMMAR_PRESENT_SIMPLE_NEGATIVES",
    "GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS",
    "GRAMMAR_SUBJECT_PRONOUNS",
    "GRAMMAR_THERE_IS",
    "GRAMMAR_WH_QUESTIONS_BE_DO_BASIC",
}


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
    print("Validating A1/A1_PLUS canonical patch...")
    nodes = load(GRAMMAR_PATH)
    summary = load(SUMMARY_PATH)
    if not isinstance(nodes, list) or not isinstance(summary, dict):
        return fail("required canonical patch files missing")
    if summary.get("task_id") != EXPECTED_TASK:
        return fail("summary task_id mismatch")
    if summary.get("patch_status") != "PASS":
        return fail("patch_status mismatch")
    if set(summary.get("changed_grammar_ids", [])) != EXPECTED_CHANGED:
        return fail("changed grammar IDs mismatch")
    if set(summary.get("deferred_grammar_ids", [])) != EXPECTED_DEFERRED:
        return fail("deferred grammar IDs mismatch")
    by_id = {node.get("grammar_id"): node for node in nodes}
    for grammar_id in EXPECTED_CHANGED:
        node = by_id.get(grammar_id)
        if not node:
            return fail(f"missing changed node: {grammar_id}")
        if grammar_id == "GRAMMAR_BE_VERB_BASIC":
            if not node.get("egp_form_evidence_refs"):
                return fail("BE verb must have form evidence refs")
        elif not node.get("egp_evidence_refs"):
            return fail(f"changed node missing egp_evidence_refs: {grammar_id}")
    for grammar_id in EXPECTED_DEFERRED:
        node = by_id.get(grammar_id)
        if not node:
            return fail(f"missing deferred node: {grammar_id}")
        if grammar_id != "GRAMMAR_BE_VERB_BASIC" and node.get("egp_evidence_refs"):
            return fail(f"deferred node unexpectedly patched: {grammar_id}")
    if summary.get("practicebank_generation") is not False:
        return fail("practicebank_generation must be false")
    if summary.get("learner_state_write") is not False:
        return fail("learner_state_write must be false")
    if summary.get("runtime_change") is not False:
        return fail("runtime_change must be false")
    if summary.get("next_short_step") != "R7-M99E_A1A1PLUSCanonicalPatchReadback":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason must be NONE")
    print("A1/A1_PLUS canonical patch validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
