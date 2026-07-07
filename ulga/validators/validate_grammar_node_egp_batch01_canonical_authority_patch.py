import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
GRAMMAR_PATH = BASE_DIR / "ulga" / "grammar" / "grammar_nodes.json"
PATCH_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_canonical_authority_patch_summary.json"
EXPECTED_REFS = {
    "GRAMMAR_ARTICLES_BASIC": ("egp_evidence_refs", "EGP_SOURCE_XLSX::Data!A311:H311::id=1741163708789x105964971324936210"),
    "GRAMMAR_CAN_STATEMENT": ("egp_form_evidence_refs", "EGP_SOURCE_XLSX::Data!A183:H183::id=1741163708329x931125497510935300"),
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC": ("egp_evidence_refs", "EGP_SOURCE_XLSX::Data!A346:H346::id=1741163709005x427091401714639400"),
}
UNCHANGED_IDS = {"GRAMMAR_BASIC_PREPOSITIONS_PLACE", "GRAMMAR_BE_VERB_BASIC"}
EXPECTED_TASK = "R7-M92A_Batch01CanonicalGrammarAuthorityPatchImplementation"


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
    print("Validating Batch 01 canonical grammar authority patch...")
    nodes = load(GRAMMAR_PATH)
    summary = load(PATCH_SUMMARY_PATH)
    if not isinstance(nodes, list) or not isinstance(summary, dict):
        return fail("required JSON structures missing")
    by_id = {node.get("grammar_id"): node for node in nodes}
    missing = sorted((set(EXPECTED_REFS) | UNCHANGED_IDS) - set(by_id))
    if missing:
        return fail(f"missing grammar IDs: {missing}")
    for grammar_id, (field_name, expected_ref) in EXPECTED_REFS.items():
        values = by_id[grammar_id].get(field_name, [])
        if expected_ref not in values:
            return fail(f"expected ref missing for {grammar_id}.{field_name}")
        if len(values) != len(set(values)):
            return fail(f"duplicate refs found for {grammar_id}.{field_name}")
    for grammar_id in UNCHANGED_IDS:
        node = by_id[grammar_id]
        if "egp_evidence_refs" in node or "egp_form_evidence_refs" in node:
            return fail(f"unresolved node should not have evidence refs: {grammar_id}")
    if summary.get("task_id") != EXPECTED_TASK:
        return fail("summary task_id mismatch")
    if summary.get("patch_status") != "PASS":
        return fail("summary patch_status mismatch")
    if summary.get("changed_grammar_ids") != sorted(EXPECTED_REFS):
        return fail("summary changed_grammar_ids mismatch")
    if summary.get("unchanged_batch01_grammar_ids") != sorted(UNCHANGED_IDS):
        return fail("summary unchanged ids mismatch")
    if summary.get("practicebank_generation") is not False:
        return fail("practicebank_generation must be false")
    if summary.get("learner_state_write") is not False:
        return fail("learner_state_write must be false")
    if summary.get("runtime_change") is not False:
        return fail("runtime_change must be false")
    print("Batch 01 canonical grammar authority patch validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
