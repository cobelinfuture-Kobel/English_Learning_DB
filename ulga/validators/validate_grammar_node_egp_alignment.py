import json
import sys
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

GRAMMAR_PROFILE_PATH = BASE_DIR / "grammar_profile" / "json" / "grammar_profile.json"
ALIGNMENT_TABLE_PATH = BASE_DIR / "ulga" / "graph" / "cefr_egp_alignment_table.json"
UNCOVERED_RULES_PATH = BASE_DIR / "ulga" / "reports" / "grammar_uncovered_egp_rules.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_alignment_summary.json"

OFFICIAL_EGP_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
TARGET_LEVELS = ["A1", "A2", "B1", "B2"]
ALLOWED_ALIGNMENT_STATUS = {
    "MATCH",
    "EARLY_BY_DESIGN",
    "LATE_BY_DEPENDENCY",
    "PREVIEW_ONLY",
    "CONFLICT_REVIEW_REQUIRED",
    "NOT_IN_AUTHORITY_SOURCE",
    "UNMAPPED",
}
REQUIRED_ALIGNMENT_FIELDS = {
    "task_id",
    "artifact_id",
    "source_paths",
    "allowed_alignment_status",
    "records",
    "summary",
    "scope_constraints",
}
REQUIRED_UNCOVERED_FIELDS = {
    "task_id",
    "artifact_id",
    "definition",
    "counts_by_level",
    "target_a1_b2_uncovered_total",
    "rows_by_level",
}
REQUIRED_SUMMARY_FIELDS = {
    "task_id",
    "artifact_id",
    "validation_status",
    "grammar_node_count",
    "egp_row_count",
    "egp_counts_by_level",
    "mapped_counts_by_level",
    "uncovered_counts_by_level",
    "coverage_by_level",
    "target_a1_b2_total",
    "target_a1_b2_mapped",
    "target_a1_b2_coverage",
    "node_status_counts",
    "unresolved_refs",
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


def normalize_level(value):
    if value is None:
        return "UNKNOWN"
    return str(value).strip().upper() or "UNKNOWN"


def source_level_counts(rows):
    return Counter(normalize_level(row.get("level")) for row in rows if isinstance(row, dict))


def validate_shapes(alignment, uncovered, summary):
    if not isinstance(alignment, dict):
        return fail("alignment table must be an object")
    if not isinstance(uncovered, dict):
        return fail("uncovered rules must be an object")
    if not isinstance(summary, dict):
        return fail("summary must be an object")
    missing_alignment = REQUIRED_ALIGNMENT_FIELDS - set(alignment)
    if missing_alignment:
        return fail(f"alignment missing fields: {sorted(missing_alignment)}")
    missing_uncovered = REQUIRED_UNCOVERED_FIELDS - set(uncovered)
    if missing_uncovered:
        return fail(f"uncovered rules missing fields: {sorted(missing_uncovered)}")
    missing_summary = REQUIRED_SUMMARY_FIELDS - set(summary)
    if missing_summary:
        return fail(f"summary missing fields: {sorted(missing_summary)}")
    if alignment["task_id"] != "R7-M36_GrammarNodeEGPAlignmentPipelineImplementation":
        return fail("alignment task_id mismatch")
    if uncovered["task_id"] != "R7-M36_GrammarNodeEGPAlignmentPipelineImplementation":
        return fail("uncovered rules task_id mismatch")
    if summary["task_id"] != "R7-M36_GrammarNodeEGPAlignmentPipelineImplementation":
        return fail("summary task_id mismatch")
    if set(alignment["allowed_alignment_status"]) != ALLOWED_ALIGNMENT_STATUS:
        return fail("allowed alignment status mismatch")
    if summary["next_short_step"] != "R7-M37_GrammarCoverageMatrixBuilderImplementation":
        return fail("summary next_short_step mismatch")
    if summary["stop_reason"] != "NONE":
        return fail("summary stop_reason must be NONE")
    return True


def validate_scope(alignment):
    scope = alignment["scope_constraints"]
    for key in [
        "no_runtime_implementation",
        "no_practicebank_generation",
        "no_learner_state_write",
        "no_ai_mapping_promotion",
    ]:
        if scope.get(key) is not True:
            return fail(f"scope constraint must be true: {key}")
    return True


def validate_counts(rows, alignment, uncovered, summary):
    counts = source_level_counts(rows)
    egp_counts = {level: counts.get(level, 0) for level in OFFICIAL_EGP_LEVELS}
    if summary["egp_counts_by_level"] != egp_counts:
        return fail("summary egp_counts_by_level do not match source")
    if summary["egp_row_count"] != sum(egp_counts.values()):
        return fail("summary egp_row_count does not match official source counts")
    if alignment["summary"]["egp_row_count"] != sum(egp_counts.values()):
        return fail("alignment egp_row_count does not match official source counts")

    for level in OFFICIAL_EGP_LEVELS:
        mapped = summary["mapped_counts_by_level"].get(level)
        uncovered_count = summary["uncovered_counts_by_level"].get(level)
        if mapped is None or uncovered_count is None:
            return fail(f"missing mapped/uncovered count for {level}")
        if mapped + uncovered_count != egp_counts[level]:
            return fail(f"mapped + uncovered does not match source count for {level}")
        if uncovered["counts_by_level"].get(level) != uncovered_count:
            return fail(f"uncovered report count mismatch for {level}")
        if len(uncovered["rows_by_level"].get(level, [])) != uncovered_count:
            return fail(f"uncovered rows_by_level length mismatch for {level}")

    target_total = sum(egp_counts[level] for level in TARGET_LEVELS)
    target_mapped = sum(summary["mapped_counts_by_level"][level] for level in TARGET_LEVELS)
    if summary["target_a1_b2_total"] != target_total:
        return fail("target_a1_b2_total mismatch")
    if summary["target_a1_b2_mapped"] != target_mapped:
        return fail("target_a1_b2_mapped mismatch")
    expected_coverage = target_mapped / target_total if target_total else 0.0
    if summary["target_a1_b2_coverage"] != expected_coverage:
        return fail("target_a1_b2_coverage mismatch")
    return True


def validate_records(alignment):
    records = alignment["records"]
    if not isinstance(records, list):
        return fail("alignment records must be a list")
    for record in records:
        if not isinstance(record, dict):
            return fail("alignment record must be an object")
        for key in [
            "grammar_id",
            "node_status",
            "egp_refs",
            "missing_egp_refs",
            "alignment_status",
            "alignment_reason",
            "review_status",
        ]:
            if key not in record:
                return fail(f"alignment record missing {key}")
        if record["alignment_status"] not in ALLOWED_ALIGNMENT_STATUS:
            return fail(f"invalid alignment_status: {record['alignment_status']}")
    return True


def validate():
    print("Validating Grammar Node EGP Alignment...")
    for path in [GRAMMAR_PROFILE_PATH, ALIGNMENT_TABLE_PATH, UNCOVERED_RULES_PATH, SUMMARY_PATH]:
        if not path.exists():
            return fail(f"required file does not exist: {path}")

    rows = read_json(GRAMMAR_PROFILE_PATH)
    alignment = read_json(ALIGNMENT_TABLE_PATH)
    uncovered = read_json(UNCOVERED_RULES_PATH)
    summary = read_json(SUMMARY_PATH)
    if rows is None or alignment is None or uncovered is None or summary is None:
        return False
    if not isinstance(rows, list):
        return fail("grammar profile source must be a list")
    if not validate_shapes(alignment, uncovered, summary):
        return False
    if not validate_scope(alignment):
        return False
    if not validate_counts(rows, alignment, uncovered, summary):
        return False
    if not validate_records(alignment):
        return False

    print("Grammar Node EGP Alignment validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
