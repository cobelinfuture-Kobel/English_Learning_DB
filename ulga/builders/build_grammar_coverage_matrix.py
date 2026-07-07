import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

ALIGNMENT_TABLE_PATH = BASE_DIR / "ulga" / "graph" / "cefr_egp_alignment_table.json"
UNCOVERED_RULES_PATH = BASE_DIR / "ulga" / "reports" / "grammar_uncovered_egp_rules.json"
COVERAGE_MATRIX_PATH = BASE_DIR / "ulga" / "graph" / "grammar_coverage_matrix.json"
COVERAGE_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_cefr_egp_coverage_summary.json"
GAP_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_coverage_gap_report.json"

LEVEL_STAGES = ["A1", "A1+", "A2", "A2+", "B1", "B1+", "B2"]
OFFICIAL_EGP_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
TARGET_LEVELS = ["A1", "A2", "B1", "B2"]
ROLE_VALUES = ["focus", "recycle", "preview", "blocked", "maintenance", "not_applicable"]


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")


def read_json(path, default=None):
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return default
    return json.loads(text)


def normalize_stage(value):
    if value is None:
        return ""
    return str(value).strip()


def default_stage_roles():
    return {stage: "not_applicable" for stage in LEVEL_STAGES}


def infer_role(record):
    status = record.get("alignment_status")
    node_status = record.get("node_status")
    if status in {"MATCH", "LATE_BY_DEPENDENCY", "EARLY_BY_DESIGN"} and node_status == "EGP_MAPPED":
        return "focus"
    if status == "PREVIEW_ONLY":
        return "preview"
    if status in {"UNMAPPED", "CONFLICT_REVIEW_REQUIRED"}:
        return "blocked"
    return "not_applicable"


def risk_from_coverage(coverage_rate):
    if coverage_rate >= 0.95:
        return "LOW"
    if coverage_rate >= 0.85:
        return "MEDIUM"
    if coverage_rate >= 0.60:
        return "HIGH_GAP_RISK"
    return "CRITICAL_GAP"


def counts_from_alignment_summary(alignment_summary, uncovered_rules):
    if "egp_counts_by_level" in alignment_summary:
        egp_counts = {
            level: alignment_summary.get("egp_counts_by_level", {}).get(level, 0)
            for level in OFFICIAL_EGP_LEVELS
        }
        mapped_counts = {
            level: alignment_summary.get("mapped_counts_by_level", {}).get(level, 0)
            for level in OFFICIAL_EGP_LEVELS
        }
        uncovered_counts = {
            level: alignment_summary.get("uncovered_counts_by_level", {}).get(level, 0)
            for level in OFFICIAL_EGP_LEVELS
        }
        return egp_counts, mapped_counts, uncovered_counts

    uncovered_counts = {
        level: uncovered_rules.get("counts_by_level", {}).get(level, 0)
        for level in OFFICIAL_EGP_LEVELS
    }
    egp_counts = dict(uncovered_counts)
    mapped_counts = {level: 0 for level in OFFICIAL_EGP_LEVELS}
    return egp_counts, mapped_counts, uncovered_counts


def build_coverage_matrix(alignment_table, uncovered_rules):
    if not isinstance(alignment_table, dict):
        raise TypeError("alignment table must be an object")
    if not isinstance(uncovered_rules, dict):
        raise TypeError("uncovered rules report must be an object")

    records = alignment_table.get("records", [])
    matrix_records = []
    for record in records:
        stage_roles = default_stage_roles()
        system_stage = normalize_stage(record.get("system_stage"))
        if system_stage in stage_roles:
            stage_roles[system_stage] = infer_role(record)
        matrix_records.append({
            "grammar_id": record.get("grammar_id"),
            "label": record.get("label", ""),
            "system_stage": system_stage,
            "node_status": record.get("node_status"),
            "alignment_status": record.get("alignment_status"),
            "egp_levels": sorted({ref.get("egp_level") for ref in record.get("egp_refs", []) if ref.get("egp_level")}),
            "stage_roles": stage_roles,
            "coverage_status": "MAPPED" if record.get("egp_refs") else "UNMAPPED",
        })

    alignment_summary = alignment_table.get("summary", {})
    egp_counts, mapped_counts, uncovered_counts = counts_from_alignment_summary(alignment_summary, uncovered_rules)
    coverage_by_level = {}
    risk_by_level = {}
    for level in OFFICIAL_EGP_LEVELS:
        total = egp_counts[level]
        mapped = mapped_counts[level]
        coverage = mapped / total if total else 0.0
        coverage_by_level[level] = coverage
        risk_by_level[level] = risk_from_coverage(coverage)

    matrix = {
        "task_id": "R7-M44A_SourcePathAndEvidenceRefNormalizationPatch",
        "artifact_id": "grammar_coverage_matrix",
        "level_stages": LEVEL_STAGES,
        "official_egp_levels": OFFICIAL_EGP_LEVELS,
        "role_values": ROLE_VALUES,
        "bridge_stage_policy": {
            "A1+": "internal_bridge_stage_not_official_egp_level",
            "A2+": "internal_bridge_stage_not_official_egp_level",
            "B1+": "internal_bridge_stage_not_official_egp_level",
        },
        "records": sorted(matrix_records, key=lambda item: str(item.get("grammar_id"))),
        "scope_constraints": {
            "no_runtime_implementation": True,
            "no_practicebank_generation": True,
            "no_learner_state_write": True,
            "no_coverage_claim": True,
        },
    }

    target_total = sum(egp_counts[level] for level in TARGET_LEVELS)
    target_mapped = sum(mapped_counts[level] for level in TARGET_LEVELS)
    summary = {
        "task_id": "R7-M44A_SourcePathAndEvidenceRefNormalizationPatch",
        "artifact_id": "grammar_cefr_egp_coverage_summary",
        "validation_status": "PASS_WITH_WARNINGS" if target_mapped < target_total else "PASS",
        "grammar_rule_count": len(matrix_records),
        "egp_counts_by_level": {level: egp_counts[level] for level in OFFICIAL_EGP_LEVELS},
        "mapped_counts_by_level": {level: mapped_counts[level] for level in OFFICIAL_EGP_LEVELS},
        "uncovered_counts_by_level": {level: uncovered_counts[level] for level in OFFICIAL_EGP_LEVELS},
        "coverage_by_level": coverage_by_level,
        "risk_by_level": risk_by_level,
        "target_a1_b2_total": target_total,
        "target_a1_b2_mapped": target_mapped,
        "target_a1_b2_coverage": target_mapped / target_total if target_total else 0.0,
        "next_short_step": "R7-M45_GeneratedGrammarPipelineArtifactsRefresh",
        "stop_reason": "NONE",
    }

    gap_report = {
        "task_id": "R7-M44A_SourcePathAndEvidenceRefNormalizationPatch",
        "artifact_id": "grammar_coverage_gap_report",
        "gap_status": "CRITICAL_GAP" if summary["target_a1_b2_coverage"] < 0.60 else "GAP_PRESENT",
        "operator_risk_confirmed": True,
        "message": "Coverage matrix uses alignment summary counts and preserves EGP coverage gap visibility.",
        "risk_by_level": risk_by_level,
        "uncovered_counts_by_level": summary["uncovered_counts_by_level"],
        "target_a1_b2_uncovered_total": target_total - target_mapped,
        "next_short_step": "R7-M45_GeneratedGrammarPipelineArtifactsRefresh",
        "stop_reason": "NONE",
    }
    return matrix, summary, gap_report


def main():
    alignment_table = read_json(ALIGNMENT_TABLE_PATH, default={"records": [], "summary": {}})
    uncovered_rules = read_json(UNCOVERED_RULES_PATH, default={"counts_by_level": {}})
    matrix, summary, gap_report = build_coverage_matrix(alignment_table, uncovered_rules)
    write_json(COVERAGE_MATRIX_PATH, matrix)
    write_json(COVERAGE_SUMMARY_PATH, summary)
    write_json(GAP_REPORT_PATH, gap_report)
    print(f"Grammar coverage matrix build: {summary['validation_status']}")
    print(f"Grammar rules: {summary['grammar_rule_count']}")
    print(f"A1-B2 coverage: {summary['target_a1_b2_coverage']:.4f}")


if __name__ == "__main__":
    main()
