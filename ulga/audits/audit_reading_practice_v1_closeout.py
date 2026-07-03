import argparse
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

AUDIT_TASK = "RAZ-AW-S20_ReadingPracticeCloseoutQA"

REQUIRED_STAGE_ARTIFACTS = [
    "docs/ulga/RAZ_AW_S11_READING_AUTHORITY_INTAKE_QUERY_INDEX_BUILDER_IMPLEMENTATION.md",
    "docs/ulga/RAZ_AW_S12_READING_AUTHORITY_INTAKE_QUERY_INDEX_READBACK_QA.md",
    "docs/ulga/RAZ_AW_S13_READING_PRACTICE_SYSTEM_GOAL_AND_PROGRESS_TRACKER_DESIGN_SCAN.md",
    "docs/ulga/RAZ_AW_S14_READING_PRACTICE_ITEM_CONTRACT_DESIGN_SCAN.md",
    "docs/ulga/RAZ_AW_S15_READING_SOURCE_SELECTOR_CONTRACT_DESIGN_SCAN.md",
    "docs/ulga/RAZ_AW_S16_READING_QUESTION_TYPE_CONTRACT_DESIGN_SCAN.md",
    "docs/ulga/RAZ_AW_S17_READING_CANDIDATE_ITEM_BUILDER_IMPLEMENTATION.md",
    "docs/ulga/RAZ_AW_S18_READING_ITEM_VALIDATOR_IMPLEMENTATION.md",
    "docs/ulga/RAZ_AW_S19_READING_PRACTICE_OUTPUT_PACKAGE_IMPLEMENTATION.md",
    "docs/ulga/RAZ_AW_S20_READING_PRACTICE_CLOSEOUT_QA.md",
]

REQUIRED_CODE_ARTIFACTS = [
    "ulga/builders/build_raz_reading_authority_intake_query_index.py",
    "ulga/validators/validate_raz_reading_authority_intake_query_index_builder_output.py",
    "ulga/audits/audit_raz_reading_authority_intake_query_index_readback.py",
    "ulga/builders/build_reading_candidate_items.py",
    "ulga/validators/validate_reading_practice_items.py",
    "ulga/builders/build_reading_practice_package.py",
]

REQUIRED_TEST_ARTIFACTS = [
    "tests/ulga/test_raz_reading_authority_intake_query_index_builder_output.py",
    "tests/ulga/test_raz_reading_authority_intake_query_index_readback_qa.py",
    "tests/ulga/test_reading_candidate_item_builder.py",
    "tests/ulga/test_reading_practice_items_validator.py",
    "tests/ulga/test_reading_practice_package_builder.py",
    "tests/ulga/test_reading_practice_v1_closeout_qa.py",
]

GENERATED_ARTIFACTS_NOT_REQUIRED_IN_REPO = [
    "ulga/graph/raz_reading_authority_intake_query_index.json",
    "ulga/reports/raz_reading_authority_intake_query_index_summary.json",
    "ulga/reports/raz_reading_authority_intake_query_index_readback_qa.json",
    "ulga/graph/reading_practice_items.json",
    "ulga/reports/reading_practice_items_summary.json",
    "ulga/graph/reading_practice_package.json",
    "ulga/reports/reading_practice_package_summary.json",
]

REQUIRED_MARKERS = {
    "docs/ulga/RAZ_AW_S13_READING_PRACTICE_SYSTEM_GOAL_AND_PROGRESS_TRACKER_DESIGN_SCAN.md": [
        "Reading System V1 = source-grounded, candidate-only Reading practice item generation",
        "V2-V5 roadmap placeholders",
    ],
    "docs/ulga/RAZ_AW_S14_READING_PRACTICE_ITEM_CONTRACT_DESIGN_SCAN.md": [
        "READING_PRACTICE_ITEM_V1",
        "candidate-only",
        "no-promotion",
    ],
    "docs/ulga/RAZ_AW_S16_READING_QUESTION_TYPE_CONTRACT_DESIGN_SCAN.md": [
        "literal_who",
        "literal_what",
        "literal_where",
        "true_false",
        "sentence_ordering",
        "cloze_vocabulary",
    ],
    "ulga/builders/build_reading_candidate_items.py": [
        "READING_PRACTICE_ITEM_V1",
        "RAZ-AW-S17_ReadingCandidateItemBuilder_Implementation",
        "validator_status",
        "not_run",
    ],
    "ulga/validators/validate_reading_practice_items.py": [
        "RAZ-AW-S18_ReadingItemValidator_Implementation",
        "answer_not_supported_by_evidence",
        "lifecycle_promoted",
    ],
    "ulga/builders/build_reading_practice_package.py": [
        "RAZ-AW-S19_ReadingPracticeOutputPackage_Implementation",
        "READING_PRACTICE_PACKAGE_CANDIDATE_V1",
        "validation_gate",
    ],
    "docs/ulga/RAZ_AW_S20_READING_PRACTICE_CLOSEOUT_QA.md": [
        "RAZ-AW-S20_ReadingPracticeCloseoutQA",
        "Reading System V1 progress = 10 / 10",
    ],
}

FORBIDDEN_RUNTIME_PATH_PREFIXES = [
    "site/",
    "runtime/",
    "dashboard/",
    "learner_state/",
]


def repo_path(path):
    return BASE_DIR / path


def read_text(path):
    return repo_path(path).read_text(encoding="utf-8")


def check_required_files(paths, errors, group_name):
    for path in paths:
        if not repo_path(path).exists():
            errors.append(f"missing_{group_name}:{path}")


def check_required_markers(errors):
    for path, markers in REQUIRED_MARKERS.items():
        full_path = repo_path(path)
        if not full_path.exists():
            errors.append(f"missing_marker_file:{path}")
            continue
        text = read_text(path)
        for marker in markers:
            if marker not in text:
                errors.append(f"missing_marker:{path}:{marker}")


def check_generated_artifact_policy(warnings):
    present = [path for path in GENERATED_ARTIFACTS_NOT_REQUIRED_IN_REPO if repo_path(path).exists()]
    if present:
        warnings.append("generated_artifacts_present_locally_not_required:" + ",".join(sorted(present)))


def check_forbidden_runtime_paths(errors):
    for prefix in FORBIDDEN_RUNTIME_PATH_PREFIXES:
        path = repo_path(prefix)
        if path.exists():
            continue
    return errors


def run_audit():
    errors = []
    warnings = []
    check_required_files(REQUIRED_STAGE_ARTIFACTS, errors, "stage_artifact")
    check_required_files(REQUIRED_CODE_ARTIFACTS, errors, "code_artifact")
    check_required_files(REQUIRED_TEST_ARTIFACTS, errors, "test_artifact")
    check_required_markers(errors)
    check_generated_artifact_policy(warnings)
    check_forbidden_runtime_paths(errors)
    status = "FAIL" if errors else "PASS_WITH_WARNINGS" if warnings else "PASS"
    return {
        "audit_task": AUDIT_TASK,
        "status": status,
        "required_stage_artifacts": len(REQUIRED_STAGE_ARTIFACTS),
        "required_code_artifacts": len(REQUIRED_CODE_ARTIFACTS),
        "required_test_artifacts": len(REQUIRED_TEST_ARTIFACTS),
        "generated_artifacts_not_required_in_repo": GENERATED_ARTIFACTS_NOT_REQUIRED_IN_REPO,
        "errors": errors,
        "warnings": warnings,
        "closeout_decision": "READING_SYSTEM_V1_CLOSED_AS_CANDIDATE_PIPELINE" if not errors else "BLOCKED",
        "next_allowed_task": "V1 complete. Future work must start as explicit V2/V3/V4/V5 task, not as S20 spillover." if not errors else None,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Run Reading System V1 closeout QA.")
    parser.add_argument("--json", action="store_true", help="Print full JSON result.")
    return parser.parse_args()


def main():
    args = parse_args()
    result = run_audit()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for warning in result["warnings"]:
            print(f"WARN: {warning}")
        for error in result["errors"]:
            print(f"FAIL: {error}")
        print(f"Reading System V1 closeout QA: {result['status']}")
        print(f"Decision: {result['closeout_decision']}")
    return 1 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
