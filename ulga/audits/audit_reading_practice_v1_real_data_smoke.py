import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.builders import build_reading_candidate_items
from ulga.builders import build_reading_practice_package
from ulga.validators import validate_reading_practice_items

SMOKE_TASK = "RAZ-AW-V1_RealDataSmokeValidation"
DEFAULT_INDEX_PATH = BASE_DIR / "ulga" / "graph" / "raz_reading_authority_intake_query_index.json"
DEFAULT_INDEX_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "raz_reading_authority_intake_query_index_summary.json"
DEFAULT_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "reading_practice_v1_real_data_smoke_report.json"


def read_json(path):
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def build_missing_input_result(index_path, index_summary_path):
    missing = []
    if not Path(index_path).exists():
        missing.append(str(index_path))
    if not Path(index_summary_path).exists():
        missing.append(str(index_summary_path))
    return {
        "smoke_task": SMOKE_TASK,
        "status": "BLOCKED_INPUT_ABSENT",
        "decision": "REAL_DATA_SMOKE_NOT_RUN",
        "missing_inputs": missing,
        "generated_items": 0,
        "validated_items": 0,
        "package_items": 0,
        "errors": [],
        "warnings": ["s11_generated_index_required_for_real_data_smoke"],
    }


def run_smoke(index_path=DEFAULT_INDEX_PATH, index_summary_path=DEFAULT_INDEX_SUMMARY_PATH, limit_per_question_type=10):
    index_path = Path(index_path)
    index_summary_path = Path(index_summary_path)
    if not index_path.exists() or not index_summary_path.exists():
        return build_missing_input_result(index_path, index_summary_path)

    index_payload = read_json(index_path)
    index_summary = read_json(index_summary_path)
    errors = []
    warnings = []

    if not isinstance(index_payload, dict):
        return {
            "smoke_task": SMOKE_TASK,
            "status": "FAIL",
            "decision": "REAL_DATA_SMOKE_FAILED",
            "missing_inputs": [],
            "generated_items": 0,
            "validated_items": 0,
            "package_items": 0,
            "errors": ["index_payload_not_object"],
            "warnings": [],
        }

    if index_payload.get("summary") != index_summary:
        warnings.append("index_summary_file_differs_from_embedded_summary")

    candidate_payload = build_reading_candidate_items.build_candidate_items(
        index_payload=index_payload,
        limit_per_question_type=limit_per_question_type,
        write_outputs=False,
    )
    generated_items = len(candidate_payload.get("items", []))
    if generated_items <= 0:
        errors.append("real_data_generated_items_zero")

    validation_result = validate_reading_practice_items.validate_payload(candidate_payload, candidate_payload.get("summary"))
    validated_items = validation_result.get("total_items_checked", 0)
    if validation_result.get("status") == "FAIL":
        errors.append("s18_validation_failed")

    package_payload = build_reading_practice_package.build_package(
        items_payload=candidate_payload,
        items_summary=candidate_payload.get("summary"),
        max_items=limit_per_question_type * 6,
        write_outputs=False,
    )
    package_items = package_payload.get("summary", {}).get("total_package_items", 0)
    if package_payload.get("summary", {}).get("status") == "FAIL":
        errors.append("s19_package_failed")
    if package_items <= 0:
        errors.append("real_data_package_items_zero")

    item_summary = candidate_payload.get("summary", {}) if isinstance(candidate_payload.get("summary"), dict) else {}
    package_summary = package_payload.get("summary", {}) if isinstance(package_payload.get("summary"), dict) else {}

    status = "FAIL" if errors else "PASS_WITH_WARNINGS" if warnings else "PASS"
    return {
        "smoke_task": SMOKE_TASK,
        "status": status,
        "decision": "REAL_DATA_SMOKE_PASS" if not errors else "REAL_DATA_SMOKE_FAILED",
        "input_index": str(index_path),
        "input_index_summary": str(index_summary_path),
        "limit_per_question_type": limit_per_question_type,
        "source_index_total_items": len(index_payload.get("items", [])) if isinstance(index_payload.get("items"), list) else 0,
        "generated_items": generated_items,
        "validated_items": validated_items,
        "package_items": package_items,
        "by_question_type": item_summary.get("by_question_type", {}),
        "package_by_question_type": package_summary.get("by_question_type", {}),
        "candidate_only_count": item_summary.get("candidate_only_count", 0),
        "promoted_count": item_summary.get("promoted_count", 0),
        "learner_facing_count": item_summary.get("learner_facing_count", 0),
        "validation_gate_status": package_summary.get("validation_gate_status"),
        "errors": errors,
        "warnings": warnings,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Run real-data smoke validation for Reading System V1.")
    parser.add_argument("--index", default=str(DEFAULT_INDEX_PATH), help="Path to S11 generated intake query index JSON.")
    parser.add_argument("--index-summary", default=str(DEFAULT_INDEX_SUMMARY_PATH), help="Path to S11 generated intake query index summary JSON.")
    parser.add_argument("--limit-per-question-type", type=int, default=10)
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH), help="Optional smoke report output path.")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    result = run_smoke(
        index_path=args.index,
        index_summary_path=args.index_summary,
        limit_per_question_type=max(0, args.limit_per_question_type),
    )
    if args.write_report:
        write_json(args.report, result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for warning in result.get("warnings", []):
            print(f"WARN: {warning}")
        for error in result.get("errors", []):
            print(f"FAIL: {error}")
        print(f"Reading System V1 real-data smoke: {result['status']}")
        print(f"Decision: {result['decision']}")
        print(f"Generated items: {result['generated_items']}")
        print(f"Package items: {result['package_items']}")
    return 1 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
