import json
import sys
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.validators.validate_static_candidate_ranking import validate

RANKING_PATH = BASE_DIR / "ulga" / "graph" / "static_candidate_ranking.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_ranking_summary.json"


def read_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=False)
        handle.write("\n")


def status_for(validator_passed, candidate_count, adaptive_leakage_detected, warnings, critical_findings):
    if not validator_passed or candidate_count == 0 or adaptive_leakage_detected or critical_findings:
        return "FAIL"
    if warnings:
        return "PASS_WITH_WARNINGS"
    return "PASS"


def run_audit():
    validator_passed = validate()
    if not RANKING_PATH.exists():
        summary = {
            "status": "FAIL",
            "candidate_count": 0,
            "active_candidate_count": 0,
            "blocked_candidate_count": 0,
            "candidate_type_distribution": {},
            "level_distribution": {},
            "top_20_distribution": {},
            "adaptive_leakage_detected": False,
            "missing_optional_inputs": [],
            "warnings": ["ranking_output_missing"],
            "critical_findings": ["static_candidate_ranking.json not found"],
        }
        write_json(SUMMARY_PATH, summary)
        return summary

    payload = read_json(RANKING_PATH)
    candidates = payload.get("candidates", []) if isinstance(payload, dict) else []
    blocked_candidates = payload.get("blocked_candidates", []) if isinstance(payload, dict) else []
    warnings = list(payload.get("warnings", [])) if isinstance(payload, dict) else []
    missing_optional_inputs = list(payload.get("missing_optional_inputs", [])) if isinstance(payload, dict) else []
    critical_findings = []

    candidate_count = len(candidates) + len(blocked_candidates)
    if not candidates:
        critical_findings.append("active_candidate_count_zero")

    if missing_optional_inputs:
        warnings.append("missing_optional_inputs_present")
    if any("inferred" in explanation for candidate in candidates for explanation in candidate.get("explain", [])):
        warnings.append("inferred_scores_present")

    adaptive_leakage_detected = False
    candidate_type_distribution = Counter(candidate["candidate_type"] for candidate in candidates)
    level_distribution = Counter(candidate["level"] for candidate in candidates)
    top_20_distribution = Counter(candidate["candidate_type"] for candidate in candidates[:20])
    top_10_candidates = [
        {
            "rank": candidate["rank"],
            "candidate_id": candidate["candidate_id"],
            "candidate_type": candidate["candidate_type"],
            "label": candidate["label"],
            "level": candidate["level"],
            "static_score": candidate["static_score"],
        }
        for candidate in candidates[:10]
    ]

    status = status_for(
        validator_passed=validator_passed,
        candidate_count=candidate_count,
        adaptive_leakage_detected=adaptive_leakage_detected,
        warnings=warnings,
        critical_findings=critical_findings,
    )
    summary = {
        "status": status,
        "candidate_count": candidate_count,
        "active_candidate_count": len(candidates),
        "blocked_candidate_count": len(blocked_candidates),
        "candidate_type_distribution": dict(sorted(candidate_type_distribution.items())),
        "level_distribution": dict(sorted(level_distribution.items())),
        "top_20_distribution": dict(sorted(top_20_distribution.items())),
        "top_10_candidates": top_10_candidates,
        "adaptive_leakage_detected": adaptive_leakage_detected,
        "missing_optional_inputs": missing_optional_inputs,
        "warnings": warnings,
        "critical_findings": critical_findings,
    }
    write_json(SUMMARY_PATH, summary)
    return summary


def main():
    try:
        summary = run_audit()
    except Exception as exc:
        print(f"Static Candidate Ranking audit: FAIL - {exc}")
        return 1
    print(f"Static Candidate Ranking audit: {summary['status']}")
    print(f"Candidate count: {summary['candidate_count']}")
    print(f"Active candidates: {summary['active_candidate_count']}")
    print(f"Blocked candidates: {summary['blocked_candidate_count']}")
    print(f"Warnings: {len(summary['warnings'])}")
    return 0 if summary["status"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
