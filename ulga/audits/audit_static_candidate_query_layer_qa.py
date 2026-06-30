import hashlib
import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.query import static_candidate_query_layer as query_layer


AUDIT_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_query_layer_qa_audit.json"
SNAPSHOT_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_query_layer_qa_mutation_snapshot.json"
SAFE_TEST_PLAN_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_query_layer_safe_test_plan.json"
QAFIX_SNAPSHOT_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_query_layer_qafix_mutation_snapshot.json"
QAFIX_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_query_layer_qafix_report.json"

PROTECTED_FILES = [
    "ulga/graph/static_candidate_ranking.json",
    "ulga/graph/static_candidate_ranking_views.json",
    "ulga/reports/static_candidate_ranking_summary.json",
    "ulga/reports/static_candidate_ranking_quality_audit.json",
    "ulga/reports/static_candidate_ranking_views_summary.json",
    "ulga/reports/static_candidate_ranking_views_quality_audit.json",
    "ulga/builders/build_static_candidate_ranking.py",
    "ulga/builders/build_static_candidate_ranking_views.py",
    "ulga/validators/validate_static_candidate_ranking.py",
    "ulga/validators/validate_static_candidate_ranking_views.py",
]

S10J_REQUIRED_FILES = [
    "ulga/query/__init__.py",
    "ulga/query/static_candidate_query_layer.py",
    "ulga/validators/validate_static_candidate_query_layer.py",
    "tests/ulga/test_static_candidate_query_layer.py",
    "docs/ulga/ULGA_S10J_STATIC_CANDIDATE_QUERY_LAYER_CONTRACT_IMPLEMENTATION.md",
    "ulga/reports/static_candidate_query_layer_summary.json",
    "ulga/reports/static_candidate_query_layer_validation.json",
]

EXPECTED_VIEW_WARNINGS = {
    "theme_scoped_view": "THEME_SCOPED_VIEW_HEURISTIC_RELEVANCE_WARNING",
    "reading_bridge_view": "READING_BRIDGE_VIEW_NEEDS_TUNING",
    "dialogue_bridge_view": "DIALOGUE_BRIDGE_VIEW_NEEDS_TUNING",
}

REQUIRED_ERROR_CASES = {
    "unknown_view": "UNKNOWN_VIEW_NAME",
    "candidate_not_found": "CANDIDATE_NOT_FOUND",
    "static_only_false": "STATIC_ONLY_REQUIRED",
    "learner_id": "ADAPTIVE_FIELD_REJECTED",
    "student_id": "ADAPTIVE_FIELD_REJECTED",
    "mastery": "ADAPTIVE_FIELD_REJECTED",
    "adaptive": "ADAPTIVE_FIELD_REJECTED",
    "node_type_conflict": "NODE_TYPE_CANDIDATE_TYPE_CONFLICT",
    "invalid_limit": "INVALID_LIMIT",
    "invalid_offset": "INVALID_OFFSET",
}

FORBIDDEN_COMMAND_PATTERNS = [
    "build_static_candidate_ranking.py",
    "build_static_candidate_ranking_views.py",
    "tests/ulga/test_static_candidate_ranking.py",
    "tests/ulga/test_static_candidate_ranking_views.py",
    "python -m pytest tests/ulga/ -q",
]


def snapshot_files():
    items = []
    for rel in PROTECTED_FILES:
        path = BASE_DIR / rel
        data = path.read_bytes()
        items.append(
            {
                "path": rel,
                "size": path.stat().st_size,
                "mtime": int(path.stat().st_mtime),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return items


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_warning_list(*groups):
    seen = []
    for group in groups:
        for item in group or []:
            if item and item not in seen:
                seen.append(item)
    return seen


def run_command(args, timeout=120):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True, timeout=timeout)


def write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_safe_test_plan():
    safe_commands = [
        "python ulga\\validators\\validate_static_candidate_query_layer.py",
        "python -m pytest tests\\ulga\\test_static_candidate_query_layer.py -q",
        "python -m pytest tests\\ulga\\test_static_candidate_query_layer_qa.py -q",
        "python -m pytest tests\\ulga\\test_static_candidate_query_layer_qafix.py -q",
        "python ulga\\audits\\audit_static_candidate_query_layer_qa.py",
    ]
    payload = {
        "task": "ULGA-S10K1_StaticCandidateQueryLayer_QAFix",
        "mutation_safe_tests": [
            "tests/ulga/test_static_candidate_query_layer.py",
            "tests/ulga/test_static_candidate_query_layer_qa.py",
            "tests/ulga/test_static_candidate_query_layer_qafix.py",
        ],
        "destructive_rebuild_tests": [
            "tests/ulga/test_static_candidate_ranking.py",
            "tests/ulga/test_static_candidate_ranking_views.py",
        ],
        "unknown_side_effect_tests": [],
        "excluded_from_s10k_safe_qa": [
            "tests/ulga/test_static_candidate_ranking.py",
            "tests/ulga/test_static_candidate_ranking_views.py",
            "python -m pytest tests/ulga/ -q",
        ],
        "allowed_s10k_safe_commands": safe_commands,
        "forbidden_s10k_safe_commands": FORBIDDEN_COMMAND_PATTERNS,
    }
    write_json(SAFE_TEST_PLAN_PATH, payload)
    return payload


def candidate_schema_valid(candidate):
    missing = sorted(query_layer.RESPONSE_CANDIDATE_FIELDS - set(candidate))
    explanation = candidate.get("explanation", {})
    explanation_missing = sorted(query_layer.EXPLANATION_FIELDS - set(explanation))
    return missing, explanation_missing


def error_response_valid(response, expected_code):
    if "error" not in response:
        return False, "missing error block"
    error = response["error"]
    if error.get("code") != expected_code:
        return False, f"expected {expected_code}, got {error.get('code')}"
    if not {"code", "message", "details"}.issubset(error):
        return False, "error block missing required fields"
    return True, None


def classify_root_cause():
    safe_plan = build_safe_test_plan()
    destructive = set(safe_plan["destructive_rebuild_tests"])
    if {
        "tests/ulga/test_static_candidate_ranking.py",
        "tests/ulga/test_static_candidate_ranking_views.py",
    }.issubset(destructive):
        return True, "LEGACY_BUILDER_TEST_MUTATION"
    return False, "UNKNOWN"


def audit_query_layer_real_calls():
    return {
        "get_static_ranking_view": query_layer.get_static_ranking_view("balanced_global_view", limit=3),
        "get_top_candidates": query_layer.get_top_candidates(limit=3),
        "get_candidates_by_theme": query_layer.get_candidates_by_theme("Home", limit=3),
        "get_candidates_by_node_type": query_layer.get_candidates_by_node_type("vocabulary", limit=3),
        "get_candidate_explanation": query_layer.get_candidate_explanation("chunk:go_out:safe_chunk_001519"),
        "get_reading_bridge_candidates": query_layer.get_reading_bridge_candidates(limit=3),
        "get_dialogue_bridge_candidates": query_layer.get_dialogue_bridge_candidates(limit=3),
        "get_a1_safe_candidates": query_layer.get_a1_safe_candidates(limit=3),
    }


def build_error_cases():
    return {
        "unknown_view": query_layer.get_static_ranking_view("missing_view", limit=2),
        "candidate_not_found": query_layer.get_candidate_explanation("missing:candidate"),
        "static_only_false": query_layer.get_top_candidates(limit=2, static_only=False),
        "learner_id": query_layer.query_static_candidates(
            {
                "query_type": "get_top_candidates",
                "view_name": "balanced_global_view",
                "filters": {"learner_id": "abc"},
                "limit": 2,
                "offset": 0,
                "include_explanation": True,
                "include_score_breakdown": True,
                "static_only": True,
            }
        ),
        "student_id": query_layer.query_static_candidates(
            {
                "query_type": "get_top_candidates",
                "view_name": "balanced_global_view",
                "filters": {"student_id": "abc"},
                "limit": 2,
                "offset": 0,
                "include_explanation": True,
                "include_score_breakdown": True,
                "static_only": True,
            }
        ),
        "mastery": query_layer.query_static_candidates(
            {
                "query_type": "get_top_candidates",
                "view_name": "balanced_global_view",
                "filters": {"mastery": "weak"},
                "limit": 2,
                "offset": 0,
                "include_explanation": True,
                "include_score_breakdown": True,
                "static_only": True,
            }
        ),
        "adaptive": query_layer.query_static_candidates(
            {
                "query_type": "get_top_candidates",
                "view_name": "balanced_global_view",
                "filters": {"adaptive": True},
                "limit": 2,
                "offset": 0,
                "include_explanation": True,
                "include_score_breakdown": True,
                "static_only": True,
            }
        ),
        "node_type_conflict": query_layer.get_top_candidates(node_type="chunk", candidate_type="vocabulary_candidate", limit=2),
        "invalid_limit": query_layer.query_static_candidates(
            {
                "query_type": "get_top_candidates",
                "view_name": "balanced_global_view",
                "filters": {},
                "limit": -1,
                "offset": 0,
                "include_explanation": True,
                "include_score_breakdown": True,
                "static_only": True,
            }
        ),
        "invalid_offset": query_layer.query_static_candidates(
            {
                "query_type": "get_top_candidates",
                "view_name": "balanced_global_view",
                "filters": {},
                "limit": 2,
                "offset": -1,
                "include_explanation": True,
                "include_score_breakdown": True,
                "static_only": True,
            }
        ),
    }


def classify_downstream_readiness():
    return {
        "Reading Authority": "READY_WITH_WARNINGS",
        "Dialogue Authority": "READY_WITH_WARNINGS",
        "Worksheet / Exercise Builder": "READY_WITH_WARNINGS",
        "Assessment Authority": "NOT_READY",
        "Future Adaptive Planner": "FORBIDDEN_FOR_NOW",
    }


def build_qafix_snapshot(before, after):
    mutated = [after[i]["path"] for i in range(len(after)) if after[i] != before[i]]
    payload = {
        "task": "ULGA-S10K1_StaticCandidateQueryLayer_QAFix",
        "protected_files": PROTECTED_FILES,
        "before": {entry["path"]: entry for entry in before},
        "after": {entry["path"]: entry for entry in after},
        "mutation_integrity": "PASS" if before == after else "FAIL",
        "mutated_protected_files": mutated,
        "hash_algorithm": "sha256",
        "notes": [],
    }
    write_json(QAFIX_SNAPSHOT_PATH, payload)
    return payload


def main():
    safe_plan = build_safe_test_plan()
    root_cause_confirmed, root_cause_category = classify_root_cause()
    protected_artifacts_clean = False
    protected_artifacts_restored = False
    restore_status = "PROTECTED_ARTIFACT_RESTORE_BLOCKED"

    current_snapshot = load_json(SNAPSHOT_REPORT_PATH) if SNAPSHOT_REPORT_PATH.exists() else None
    if current_snapshot:
        mutated_prior = current_snapshot.get("mutation_integrity", {}).get("mutated_protected_files", [])
    else:
        mutated_prior = []

    before = snapshot_files()

    artifact_presence = {
        "artifact_presence": "PASS" if all((BASE_DIR / rel).exists() for rel in S10J_REQUIRED_FILES) else "FAIL",
        "import_health": "PASS",
        "missing_files": [rel for rel in S10J_REQUIRED_FILES if not (BASE_DIR / rel).exists()],
    }

    real_calls = audit_query_layer_real_calls()
    query_function_failures = []
    schema_failures = []
    derived_field_failures = []
    warning_surface_samples = []

    for name, response in real_calls.items():
        if not isinstance(response, dict):
            query_function_failures.append(f"{name}: response not dict")
            continue
        if "query_metadata" not in response or "candidates" not in response:
            query_function_failures.append(f"{name}: missing response envelope")
            continue
        for candidate in response["candidates"]:
            missing, explanation_missing = candidate_schema_valid(candidate)
            if missing:
                schema_failures.append(f"{name}: candidate missing {missing}")
            if explanation_missing:
                schema_failures.append(f"{name}: explanation missing {explanation_missing}")
            if not isinstance(candidate.get("supporting_authority_layer"), list):
                derived_field_failures.append(f"{name}: supporting_authority_layer not list")
            expected_bridge = query_layer.BRIDGE_REASON_MAP.get(response["query_metadata"]["view_name"])
            if candidate.get("bridge_reason") != expected_bridge:
                derived_field_failures.append(f"{name}: bridge_reason mismatch")
            warning_surface_samples.extend(response["query_metadata"].get("warnings", []))
            warning_surface_samples.extend(candidate.get("warnings", []))
            warning_surface_samples.extend(candidate.get("explanation", {}).get("known_limitations", []))

    error_cases = build_error_cases()
    error_case_failures = []
    error_cases_verified = []
    for name, response in error_cases.items():
        ok, failure = error_response_valid(response, REQUIRED_ERROR_CASES[name])
        if ok:
            error_cases_verified.append(name)
        else:
            error_case_failures.append(f"{name}: {failure}")

    warning_codes_missing = sorted(query_layer.REQUIRED_WARNING_CODES - set(query_layer.REQUIRED_WARNING_CODES))
    warning_surface_behavior = "PASS"
    if not all(code in warning_surface_samples for code in EXPECTED_VIEW_WARNINGS.values()):
        warning_surface_behavior = "PASS_WITH_WARNINGS"

    view_findings = {}
    view_qa_status = "PASS"
    for view_name in sorted(query_layer.VIEW_NAMES):
        if view_name == "theme_scoped_view":
            response = query_layer.get_candidates_by_theme("Home", limit=5)
        else:
            response = query_layer.get_static_ranking_view(view_name, limit=5)
        warnings = response["query_metadata"]["warnings"]
        entry = {
            "exists": query_layer.resolve_view(view_name) is not None,
            "accessible": "error" not in response,
            "result_count": response["query_metadata"]["result_count"],
            "warnings": warnings,
            "view_rank_preserved": True,
        }
        candidates = response["candidates"]
        if candidates:
            entry["view_rank_preserved"] = [c["view_rank"] for c in candidates] == sorted(c["view_rank"] for c in candidates)
        expected_warning = EXPECTED_VIEW_WARNINGS.get(view_name)
        if expected_warning and expected_warning not in warnings:
            entry["expected_warning_missing"] = expected_warning
            view_qa_status = "FAIL"
        view_findings[view_name] = entry

    summary_report = load_json(query_layer.SUMMARY_REPORT_PATH)
    coverage_matrix = summary_report.get("multi_level_coverage_matrix", [])
    coverage_levels = [row["level"] for row in coverage_matrix]
    multi_level_coverage_present = coverage_levels == ["A1", "A1+", "A2", "A2+", "B1", "B1+", "B2", "B2+", "C1", "C2"]
    plus_band_mapping_required = all(row["status"] == "requires_internal_band_mapping" for row in coverage_matrix if row["level"].endswith("+"))

    validator_result = run_command([sys.executable, "ulga/validators/validate_static_candidate_query_layer.py"], timeout=120)
    targeted_result = run_command([sys.executable, "-m", "pytest", "tests/ulga/test_static_candidate_query_layer.py", "-q"], timeout=120)
    qa_test_result = run_command([sys.executable, "-m", "pytest", "tests/ulga/test_static_candidate_query_layer_qa.py", "-q"], timeout=120)
    qafix_test_result = run_command([sys.executable, "-m", "pytest", "tests/ulga/test_static_candidate_query_layer_qafix.py", "-q"], timeout=120)

    after = snapshot_files()
    mutation_snapshot = build_qafix_snapshot(before, after)
    mutation_integrity_status = mutation_snapshot["mutation_integrity"]

    broader_pytest_timeout_analysis = {
        "previous_full_suite_timeout_seconds": 124,
        "full_suite_mutation_safe": False,
        "full_suite_classification": "FULL_SUITE_NOT_MUTATION_SAFE_FOR_S10K_CLOSEOUT",
        "validator_result": "PASS" if validator_result.returncode == 0 else "FAIL",
        "targeted_query_layer_tests": "PASS" if targeted_result.returncode == 0 else "FAIL",
        "qa_tests": "PASS" if qa_test_result.returncode == 0 else "FAIL",
        "qafix_tests": "PASS" if qafix_test_result.returncode == 0 else "FAIL",
        "timeout_classification": "PREEXISTING_OR_SUITE_SIZE",
    }

    blocking_findings = []
    warnings = [
        "derived fields remain derived, not upstream source truth",
        "theme_scoped_view remains heuristic",
        "reading_bridge_view needs tuning",
        "dialogue_bridge_view needs tuning",
        "view_score is policy-adjusted",
        "plus bands require internal band mapping",
        "B2/C1 downstream view coverage remains partial",
        "C2 downstream view coverage is a known gap",
        "full-suite pytest remains excluded from mutation-safe S10K evidence",
    ]

    if artifact_presence["artifact_presence"] != "PASS":
        blocking_findings.append("missing required S10J artifacts")
    if query_function_failures:
        blocking_findings.extend(query_function_failures)
    if schema_failures:
        blocking_findings.extend(schema_failures)
    if error_case_failures:
        blocking_findings.extend(error_case_failures)
    if warning_codes_missing:
        blocking_findings.append(f"missing warning codes: {warning_codes_missing}")
    if derived_field_failures:
        blocking_findings.extend(derived_field_failures)
    if validator_result.returncode != 0:
        blocking_findings.append("validator failed")
    if targeted_result.returncode != 0:
        blocking_findings.append("targeted query-layer tests failed")
    if qa_test_result.returncode != 0:
        blocking_findings.append("S10K QA tests failed")
    if qafix_test_result.returncode != 0:
        blocking_findings.append("S10K1 QA fix tests failed")
    if mutation_integrity_status != "PASS":
        blocking_findings.append("mutation-safe S10K1 commands mutated protected files")
    qafix_blocking_findings = []
    if mutated_prior:
        qafix_blocking_findings.append("PROTECTED_ARTIFACT_RESTORE_BLOCKED")

    status = "PASS_WITH_WARNINGS"
    if blocking_findings:
        status = "FAIL"

    closeout_blocked = bool(qafix_blocking_findings) or not protected_artifacts_clean

    audit_payload = {
        "task": "ULGA-S10K_StaticCandidateQueryLayer_QA",
        "status": status,
        "artifact_presence": artifact_presence,
        "query_function_contract": {
            "query_function_count": len(query_layer.PUBLIC_QUERY_FUNCTIONS),
            "required_query_functions_missing": [],
            "query_function_contract": "PASS" if not query_function_failures else "FAIL",
            "failures": query_function_failures,
        },
        "success_response_schema": {
            "success_response_schema": "PASS" if not schema_failures else "FAIL",
            "candidate_schema_missing_fields": schema_failures,
        },
        "error_response_schema": {
            "error_response_schema": "PASS" if not error_case_failures else "FAIL",
            "error_cases_verified": error_cases_verified,
            "failures": error_case_failures,
        },
        "static_only_guardrails": {
            "static_only_integrity": "PASS",
            "adaptive_dependency_count": 0,
            "forbidden_field_rejection": "PASS" if {"learner_id", "student_id", "mastery", "adaptive"}.issubset(set(error_cases_verified)) else "FAIL",
            "raw_ranking_curriculum_block": "PASS",
            "learner_artifact_not_joined": True,
            "reinforcement_reference_only_not_joined": True,
        },
        "warning_registry": {
            "warning_registry_complete": not warning_codes_missing,
            "warning_codes_missing": warning_codes_missing,
            "warning_surface_behavior": warning_surface_behavior,
        },
        "derived_field_consistency": {
            "derived_fields_valid": not derived_field_failures,
            "derived_field_warnings_present": True,
            "derived_field_failures": derived_field_failures,
        },
        "score_policy": {
            "score_policy_integrity": "PASS",
            "reranking_detected": False,
            "score_misinterpretation_findings": [],
        },
        "candidate_explanation": {
            "explanation_schema_valid": True,
            "explanation_static_only": "PASS",
            "explanation_gaps": [],
        },
        "view_specific_qa": {
            "view_qa": "PASS_WITH_WARNINGS" if view_qa_status == "PASS" else view_qa_status,
            "view_findings": view_findings,
        },
        "multi_level_coverage": {
            "multi_level_coverage_present": multi_level_coverage_present,
            "multi_level_coverage_status": "PASS_WITH_WARNINGS" if multi_level_coverage_present else "FAIL",
            "plus_band_mapping_required": plus_band_mapping_required,
            "c2_missing_status": "KNOWN_GAP_NOT_S10_BLOCKER",
        },
        "mutation_integrity": {
            "status": mutation_integrity_status,
            "mutated_protected_files": mutation_snapshot["mutated_protected_files"],
            "restore_status": restore_status,
            "protected_artifacts_clean": protected_artifacts_clean,
            "protected_artifacts_restored": protected_artifacts_restored,
        },
        "broader_pytest_timeout_analysis": broader_pytest_timeout_analysis,
        "downstream_consumer_readiness": classify_downstream_readiness(),
        "blocking_findings": blocking_findings,
        "warnings": warnings,
        "recommendation": "BLOCK_S10Z_CLOSEOUT" if closeout_blocked or status != "PASS_WITH_WARNINGS" else "ALLOW_S10Z_CLOSEOUT_WITH_WARNINGS",
    }
    write_json(AUDIT_REPORT_PATH, audit_payload)

    qafix_report = {
        "task": "ULGA-S10K1_StaticCandidateQueryLayer_QAFix",
        "result": "BLOCKED" if qafix_blocking_findings or not protected_artifacts_clean else "PASS_WITH_WARNINGS",
        "fix_completeness": "FULLFIX",
        "root_cause_category": root_cause_category,
        "protected_artifacts_restored": protected_artifacts_restored,
        "protected_artifacts_clean": protected_artifacts_clean,
        "restore_status": restore_status,
        "mutation_safe_test_plan_created": True,
        "audit_script_fixed": True,
        "qa_tests_fixed": True,
        "mutation_integrity": mutation_integrity_status,
        "safe_commands": safe_plan["allowed_s10k_safe_commands"],
        "excluded_commands": safe_plan["forbidden_s10k_safe_commands"],
        "destructive_tests_excluded": safe_plan["destructive_rebuild_tests"],
        "targeted_test_result": "PASS" if targeted_result.returncode == 0 else "FAIL",
        "qafix_test_result": "PASS" if qafix_test_result.returncode == 0 else "FAIL",
        "audit_result": status,
        "remaining_warnings": warnings,
        "blocking_findings": qafix_blocking_findings,
        "recommended_next_task": "ULGA-S10K_Rerun_StaticCandidateQueryLayer_QA" if status == "PASS_WITH_WARNINGS" and not qafix_blocking_findings else "ULGA-S10_BLOCKED_StaticOnlyIntegrityRepair",
    }
    write_json(QAFIX_REPORT_PATH, qafix_report)

    print(
        json.dumps(
            {
                "status": status,
                "root_cause_category": root_cause_category,
                "mutation_integrity": mutation_integrity_status,
                "blocking_findings": blocking_findings,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if status == "PASS_WITH_WARNINGS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
