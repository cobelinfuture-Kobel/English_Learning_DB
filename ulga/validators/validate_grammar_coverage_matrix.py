import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

COVERAGE_MATRIX_PATH = BASE_DIR / "ulga" / "graph" / "grammar_coverage_matrix.json"
COVERAGE_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_cefr_egp_coverage_summary.json"
GAP_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_coverage_gap_report.json"

LEVEL_STAGES = ["A1", "A1+", "A2", "A2+", "B1", "B1+", "B2"]
OFFICIAL_EGP_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
TARGET_LEVELS = ["A1", "A2", "B1", "B2"]
ROLE_VALUES = ["focus", "recycle", "preview", "blocked", "maintenance", "not_applicable"]
ALLOWED_TASK_IDS = {
    "R7-M37_GrammarCoverageMatrixBuilderImplementation",
    "R7-M44A_SourcePathAndEvidenceRefNormalizationPatch",
}
ALLOWED_NEXT_STEPS = {
    "R7-M38_CrossSkillGrammarGateMatrixBuilderImplementation",
    "R7-M45_GeneratedGrammarPipelineArtifactsRefresh",
}
REQUIRED_MATRIX_FIELDS = {
    "task_id",
    "artifact_id",
    "level_stages",
    "official_egp_levels",
    "role_values",
    "bridge_stage_policy",
    "records",
    "scope_constraints",
}
REQUIRED_SUMMARY_FIELDS = {
    "task_id",
    "artifact_id",
    "validation_status",
    "grammar_rule_count",
    "egp_counts_by_level",
    "mapped_counts_by_level",
    "uncovered_counts_by_level",
    "coverage_by_level",
    "risk_by_level",
    "target_a1_b2_total",
    "target_a1_b2_mapped",
    "target_a1_b2_coverage",
    "next_short_step",
    "stop_reason",
}
REQUIRED_GAP_FIELDS = {
    "task_id",
    "artifact_id",
    "gap_status",
    "operator_risk_confirmed",
    "message",
    "risk_by_level",
    "uncovered_counts_by_level",
    "target_a1_b2_uncovered_total",
    "next_short_step",
    "stop_reason",
}


def read_json(path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"FAIL: could not load {path}: {exc}")
        return None


def fail(message):
    print(f"FAIL: {message}")
    return False


def validate_shapes(matrix, summary, gap_report):
    if not isinstance(matrix, dict):
        return fail("coverage matrix must be an object")
    if not isinstance(summary, dict):
        return fail("coverage summary must be an object")
    if not isinstance(gap_report, dict):
        return fail("gap report must be an object")
    missing_matrix = REQUIRED_MATRIX_FIELDS - set(matrix)
    if missing_matrix:
        return fail(f"coverage matrix missing fields: {sorted(missing_matrix)}")
    missing_summary = REQUIRED_SUMMARY_FIELDS - set(summary)
    if missing_summary:
        return fail(f"coverage summary missing fields: {sorted(missing_summary)}")
    missing_gap = REQUIRED_GAP_FIELDS - set(gap_report)
    if missing_gap:
        return fail(f"gap report missing fields: {sorted(missing_gap)}")
    for payload_name, payload in [("coverage matrix", matrix), ("coverage summary", summary), ("gap report", gap_report)]:
        if payload["task_id"] not in ALLOWED_TASK_IDS:
            return fail(f"{payload_name} task_id mismatch: {payload['task_id']}")
    if matrix["level_stages"] != LEVEL_STAGES:
        return fail("level_stages mismatch")
    if matrix["official_egp_levels"] != OFFICIAL_EGP_LEVELS:
        return fail("official_egp_levels mismatch")
    if matrix["role_values"] != ROLE_VALUES:
        return fail("role_values mismatch")
    for bridge_stage in ["A1+", "A2+", "B1+"]:
        if matrix["bridge_stage_policy"].get(bridge_stage) != "internal_bridge_stage_not_official_egp_level":
            return fail(f"bridge stage policy missing or invalid for {bridge_stage}")
    return True


def validate_scope(matrix):
    scope = matrix["scope_constraints"]
    for key in [
        "no_runtime_implementation",
        "no_practicebank_generation",
        "no_learner_state_write",
        "no_coverage_claim",
    ]:
        if scope.get(key) is not True:
            return fail(f"scope constraint must be true: {key}")
    return True


def validate_records(matrix, summary):
    records = matrix["records"]
    if not isinstance(records, list):
        return fail("coverage matrix records must be a list")
    if summary["grammar_rule_count"] != len(records):
        return fail("summary grammar_rule_count does not match matrix records")
    for record in records:
        if not isinstance(record, dict):
            return fail("matrix record must be an object")
        for key in ["grammar_id", "stage_roles", "coverage_status"]:
            if key not in record:
                return fail(f"matrix record missing {key}")
        stage_roles = record["stage_roles"]
        if set(stage_roles) != set(LEVEL_STAGES):
            return fail(f"stage_roles must contain all level stages for {record.get('grammar_id')}")
        for stage, role in stage_roles.items():
            if role not in ROLE_VALUES:
                return fail(f"invalid role {role} for {record.get('grammar_id')} at {stage}")
    return True


def validate_counts(summary, gap_report):
    for level in OFFICIAL_EGP_LEVELS:
        total = summary["egp_counts_by_level"].get(level)
        mapped = summary["mapped_counts_by_level"].get(level)
        uncovered = summary["uncovered_counts_by_level"].get(level)
        coverage = summary["coverage_by_level"].get(level)
        if total is None or mapped is None or uncovered is None or coverage is None:
            return fail(f"missing count or coverage for {level}")
        if mapped + uncovered != total:
            return fail(f"mapped + uncovered does not equal total for {level}")
        expected_coverage = mapped / total if total else 0.0
        if coverage != expected_coverage:
            return fail(f"coverage_by_level mismatch for {level}")
        if gap_report["uncovered_counts_by_level"].get(level) != uncovered:
            return fail(f"gap report uncovered count mismatch for {level}")

    expected_target_total = sum(summary["egp_counts_by_level"][level] for level in TARGET_LEVELS)
    expected_target_mapped = sum(summary["mapped_counts_by_level"][level] for level in TARGET_LEVELS)
    if summary["target_a1_b2_total"] != expected_target_total:
        return fail("target_a1_b2_total mismatch")
    if summary["target_a1_b2_mapped"] != expected_target_mapped:
        return fail("target_a1_b2_mapped mismatch")
    expected_target_coverage = expected_target_mapped / expected_target_total if expected_target_total else 0.0
    if summary["target_a1_b2_coverage"] != expected_target_coverage:
        return fail("target_a1_b2_coverage mismatch")
    if gap_report["target_a1_b2_uncovered_total"] != expected_target_total - expected_target_mapped:
        return fail("gap report target uncovered total mismatch")
    return True


def validate_next_step(summary, gap_report):
    if summary["next_short_step"] not in ALLOWED_NEXT_STEPS:
        return fail("summary next_short_step mismatch")
    if gap_report["next_short_step"] not in ALLOWED_NEXT_STEPS:
        return fail("gap report next_short_step mismatch")
    if summary["stop_reason"] != "NONE" or gap_report["stop_reason"] != "NONE":
        return fail("stop_reason must be NONE")
    return True


def validate():
    print("Validating Grammar Coverage Matrix...")
    for path in [COVERAGE_MATRIX_PATH, COVERAGE_SUMMARY_PATH, GAP_REPORT_PATH]:
        if not path.exists():
            return fail(f"required file does not exist: {path}")
    matrix = read_json(COVERAGE_MATRIX_PATH)
    summary = read_json(COVERAGE_SUMMARY_PATH)
    gap_report = read_json(GAP_REPORT_PATH)
    if matrix is None or summary is None or gap_report is None:
        return False
    if not validate_shapes(matrix, summary, gap_report):
        return False
    if not validate_scope(matrix):
        return False
    if not validate_records(matrix, summary):
        return False
    if not validate_counts(summary, gap_report):
        return False
    if not validate_next_step(summary, gap_report):
        return False
    print("Grammar Coverage Matrix validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
