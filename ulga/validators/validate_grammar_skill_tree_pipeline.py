import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_skill_tree_validator_report.json"
COVERAGE_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_cefr_egp_coverage_summary.json"
LOOKUP_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_lookup_contract_validation_report.json"

VALIDATOR_SPECS = [
    ("grammar_egp_level_inventory", BASE_DIR / "ulga" / "validators" / "validate_grammar_egp_level_inventory.py"),
    ("grammar_node_egp_alignment", BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_alignment.py"),
    ("grammar_coverage_matrix", BASE_DIR / "ulga" / "validators" / "validate_grammar_coverage_matrix.py"),
    ("cross_skill_grammar_gate", BASE_DIR / "ulga" / "validators" / "validate_cross_skill_grammar_gate.py"),
    ("grammar_lookup_contract", BASE_DIR / "ulga" / "validators" / "validate_grammar_lookup_contract.py"),
]


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")


def read_json(path, default=None):
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def run_validator(name, path):
    if not path.exists():
        return {
            "validator": name,
            "path": path.relative_to(BASE_DIR).as_posix(),
            "status": "FAIL",
            "returncode": None,
            "stdout": "",
            "stderr": "validator file missing",
        }
    result = subprocess.run([sys.executable, str(path)], cwd=BASE_DIR, capture_output=True, text=True)
    return {
        "validator": name,
        "path": path.relative_to(BASE_DIR).as_posix(),
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def classify_coverage_warning():
    coverage_summary = read_json(COVERAGE_SUMMARY_PATH, default={})
    lookup_report = read_json(LOOKUP_REPORT_PATH, default={})
    warnings = []
    target_coverage = coverage_summary.get("target_a1_b2_coverage")
    if target_coverage is None:
        warnings.append({"warning": "missing_target_a1_b2_coverage"})
    elif target_coverage < 0.95:
        warnings.append({
            "warning": "egp_mapping_coverage_below_pass_threshold",
            "target_a1_b2_coverage": target_coverage,
            "threshold": 0.95,
        })
    if lookup_report.get("grammar_id_count", 0) == 0:
        warnings.append({"warning": "no_grammar_ids_indexed_yet"})
    if lookup_report.get("uncovered_egp_row_count", 0) > 0:
        warnings.append({
            "warning": "uncovered_egp_rows_present",
            "uncovered_egp_row_count": lookup_report.get("uncovered_egp_row_count"),
        })
    return warnings


def validate_pipeline():
    validator_results = [run_validator(name, path) for name, path in VALIDATOR_SPECS]
    fail_count = sum(1 for result in validator_results if result["status"] != "PASS")
    warnings = classify_coverage_warning()
    if fail_count:
        overall_status = "FAIL"
    elif warnings:
        overall_status = "PASS_WITH_WARNINGS"
    else:
        overall_status = "PASS"

    report = {
        "task_id": "R7-M40_GrammarEGPCoverageValidatorImplementation",
        "artifact_id": "grammar_skill_tree_validator_report",
        "overall_status": overall_status,
        "validator_results": validator_results,
        "warning_count": len(warnings),
        "warnings": warnings,
        "scope_constraints": {
            "no_runtime_implementation": True,
            "no_practicebank_generation": True,
            "no_learner_state_write": True,
            "no_completion_claim": True,
        },
        "next_short_step": "R7-M41_GrammarGraphCoverageCloseoutQA",
        "stop_reason": "NONE" if overall_status != "FAIL" else "VALIDATOR_FAILURE",
    }
    write_json(REPORT_PATH, report)
    return report


def main():
    report = validate_pipeline()
    print(f"Grammar Skill Tree pipeline validation: {report['overall_status']}")
    print(f"Validators: {len(report['validator_results'])}")
    print(f"Warnings: {report['warning_count']}")
    if report["overall_status"] == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()
