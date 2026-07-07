import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
APPLIER = BASE_DIR / "ulga" / "builders" / "apply_grammar_node_egp_batch01_authority_patch.py"
VALIDATOR = BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_batch01_canonical_authority_patch.py"
GRAMMAR_PATH = BASE_DIR / "ulga" / "grammar" / "grammar_nodes.json"
PATCH_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_canonical_authority_patch_summary.json"
EXPECTED_REFS = {
    "GRAMMAR_ARTICLES_BASIC": ("egp_evidence_refs", "EGP_SOURCE_XLSX::Data!A311:H311::id=1741163708789x105964971324936210"),
    "GRAMMAR_CAN_STATEMENT": ("egp_form_evidence_refs", "EGP_SOURCE_XLSX::Data!A183:H183::id=1741163708329x931125497510935300"),
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC": ("egp_evidence_refs", "EGP_SOURCE_XLSX::Data!A346:H346::id=1741163709005x427091401714639400"),
}
UNCHANGED_IDS = {"GRAMMAR_BASIC_PREPOSITIONS_PLACE", "GRAMMAR_BE_VERB_BASIC"}


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_patch_applier_can_run_idempotently():
    first = run_command([sys.executable, str(APPLIER)])
    assert first.returncode == 0, first.stdout + first.stderr
    second = run_command([sys.executable, str(APPLIER)])
    assert second.returncode == 0, second.stdout + second.stderr


def test_patch_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_expected_evidence_refs_are_present():
    nodes = load_json(GRAMMAR_PATH)
    by_id = {node["grammar_id"]: node for node in nodes}
    for grammar_id, (field_name, expected_ref) in EXPECTED_REFS.items():
        assert expected_ref in by_id[grammar_id].get(field_name, [])


def test_unresolved_batch01_nodes_remain_unpatched():
    nodes = load_json(GRAMMAR_PATH)
    by_id = {node["grammar_id"]: node for node in nodes}
    for grammar_id in UNCHANGED_IDS:
        assert "egp_evidence_refs" not in by_id[grammar_id]
        assert "egp_form_evidence_refs" not in by_id[grammar_id]


def test_patch_summary_contract():
    summary = load_json(PATCH_SUMMARY_PATH)
    assert summary["task_id"] == "R7-M92A_Batch01CanonicalGrammarAuthorityPatchImplementation"
    assert summary["patch_status"] == "PASS"
    assert summary["changed_grammar_ids"] == sorted(EXPECTED_REFS)
    assert summary["unchanged_batch01_grammar_ids"] == sorted(UNCHANGED_IDS)
    assert summary["practicebank_generation"] is False
    assert summary["learner_state_write"] is False
    assert summary["runtime_change"] is False
