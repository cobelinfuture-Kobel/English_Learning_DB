import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
RESOLVER_BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_a1_a1plus_candidate_resolver.py"
RESOLVER_REPORT = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_candidate_resolver.json"
EGP_INDEX = BASE_DIR / "ulga" / "reports" / "egp_row_index_compact.json"
OUT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_deterministic_selection.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_deterministic_selection_summary.json"
TASK_ID = "R7-M99B_A1A1PLUSDeterministicEGPSelection"

SELECTIONS = {
    "GRAMMAR_DEMONSTRATIVES_CONTRAST": ("SELECT_AUTHORITY_EVIDENCE", [
        "EGP_SOURCE_XLSX::Data!A327:H327::id=1741163708998x446294161060833700",
        "EGP_SOURCE_XLSX::Data!A329:H329::id=1741163708998x842376822392022500",
        "EGP_SOURCE_XLSX::Data!A330:H330::id=1741163708999x197534813538877700",
        "EGP_SOURCE_XLSX::Data!A335:H335::id=1741163709000x205393325500403900",
        "EGP_SOURCE_XLSX::Data!A344:H344::id=1741163709001x956266227421554000",
    ]),
    "GRAMMAR_OBJECT_PRONOUNS_BASIC": ("SELECT_AUTHORITY_EVIDENCE", [
        "EGP_SOURCE_XLSX::Data!A1024:H1024::id=1741163713867x281198469131771500",
        "EGP_SOURCE_XLSX::Data!A1028:H1028::id=1741163713867x710371035379195900",
    ]),
    "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS": ("SELECT_AUTHORITY_EVIDENCE", [
        "EGP_SOURCE_XLSX::Data!A971:H971::id=1741163713626x486355013779909760",
    ]),
    "GRAMMAR_PRESENT_SIMPLE_NEGATIVES": ("SELECT_AUTHORITY_EVIDENCE", [
        "EGP_SOURCE_XLSX::Data!A969:H969::id=1741163713626x335670389512142900",
        "EGP_SOURCE_XLSX::Data!A718:H718::id=1741163716067x101148462288360720",
    ]),
    "GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS": ("SELECT_AUTHORITY_EVIDENCE", [
        "EGP_SOURCE_XLSX::Data!A976:H976::id=1741163713633x426061404387356740",
        "EGP_SOURCE_XLSX::Data!A1136:H1136::id=1741163715033x199281404596736400",
    ]),
    "GRAMMAR_SUBJECT_PRONOUNS": ("SELECT_AUTHORITY_EVIDENCE", [
        "EGP_SOURCE_XLSX::Data!A1030:H1030::id=1741163713868x463659211645272000",
        "EGP_SOURCE_XLSX::Data!A1023:H1023::id=1741163713867x150062658595893500",
        "EGP_SOURCE_XLSX::Data!A1027:H1027::id=1741163713867x609205291409504700",
    ]),
    "GRAMMAR_THERE_IS": ("SELECT_AUTHORITY_EVIDENCE", [
        "EGP_SOURCE_XLSX::Data!A1212:H1212::id=1741163715607x526138276437947400",
        "EGP_SOURCE_XLSX::Data!A1214:H1214::id=1741163715607x671128268905876200",
    ]),
    "GRAMMAR_WH_QUESTIONS_BE_DO_BASIC": ("SELECT_AUTHORITY_EVIDENCE", [
        "EGP_SOURCE_XLSX::Data!A1126:H1126::id=1741163715031x260861213622010530",
        "EGP_SOURCE_XLSX::Data!A1127:H1127::id=1741163715031x588201738254725100",
        "EGP_SOURCE_XLSX::Data!A1130:H1130::id=1741163715031x898125206259626100",
    ]),
    "GRAMMAR_BE_VERB_BASIC": ("SELECT_FORM_ONLY_EVIDENCE", [
        "EGP_SOURCE_XLSX::Data!A719:H719::id=1741163716067x824562184770361200",
        "EGP_SOURCE_XLSX::Data!A181:H181::id=1741163708329x778951051617750700",
    ]),
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE": ("DEFER_REFINED_SOURCE_REQUIRED", []),
    "GRAMMAR_REGULAR_PLURAL_NOUNS": ("DEFER_REFINED_SOURCE_REQUIRED", []),
    "GRAMMAR_THIS_IS": ("DEFER_COMPOSITIONAL_SOURCE_REQUIRED", []),
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_resolver_report():
    if RESOLVER_REPORT.exists():
        return
    result = subprocess.run([sys.executable, str(RESOLVER_BUILDER)], cwd=BASE_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stdout + result.stderr)


def available_refs():
    index = load_json(EGP_INDEX)
    return {row["source_ref"] for row in index.get("rows", [])}


def main():
    ensure_resolver_report()
    resolver = load_json(RESOLVER_REPORT)
    refs = available_refs()
    records = []
    counts = {}
    for source_record in resolver.get("records", []):
        grammar_id = source_record["grammar_id"]
        decision, selected_refs = SELECTIONS.get(grammar_id, ("DEFER_NO_DETERMINISTIC_SELECTION", []))
        missing = [ref for ref in selected_refs if ref not in refs]
        if missing:
            raise RuntimeError(f"Selected refs not found in EGP compact index for {grammar_id}: {missing}")
        records.append({
            "grammar_id": grammar_id,
            "selection_decision": decision,
            "selected_egp_refs": selected_refs,
            "selected_ref_count": len(selected_refs),
            "source_candidate_count": source_record.get("candidate_count", 0),
            "canonical_write_allowed": False,
            "operator_review_required": decision.startswith("DEFER"),
        })
        counts[decision] = counts.get(decision, 0) + 1
    report = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_a1_a1plus_deterministic_selection",
        "selection_scope": "A1_A1PLUS_DETERMINISTIC_SELECTION_NO_CANONICAL_WRITE",
        "records": sorted(records, key=lambda item: item["grammar_id"]),
        "scope_constraints": {
            "canonical_grammar_write_allowed": False,
            "egp_evidence_refs_write_allowed": False,
            "coverage_increase_allowed": False,
            "practicebank_generation_allowed": False,
            "learner_state_write_allowed": False,
            "runtime_change_allowed": False
        }
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_a1_a1plus_deterministic_selection_summary",
        "validation_status": "PASS",
        "source_target_count": len(resolver.get("records", [])),
        "selected_authority_target_count": counts.get("SELECT_AUTHORITY_EVIDENCE", 0),
        "selected_form_only_target_count": counts.get("SELECT_FORM_ONLY_EVIDENCE", 0),
        "deferred_target_count": sum(v for k, v in counts.items() if k.startswith("DEFER")),
        "selection_counts": dict(sorted(counts.items())),
        "canonical_grammar_write_allowed": False,
        "next_short_step": "R7-M99C_A1A1PLUSSelectionPatchPlanBuilder",
        "stop_reason": "NONE"
    }
    write_json(OUT_PATH, report)
    write_json(SUMMARY_PATH, summary)
    print("A1/A1_PLUS deterministic EGP selection build: PASS")
    print("Selection counts:", summary["selection_counts"])


if __name__ == "__main__":
    main()
