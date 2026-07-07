import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
IN_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_candidate_suggestions.json"
OUT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_refined_candidate_suggestions.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_refined_candidate_suggestions_summary.json"
MAX_REFINED = 3
MIN_SCORE = 0.22
STAGE_LEVELS = {
    "A1": {"A1"},
    "A1+": {"A1", "A2"},
    "A2": {"A2"},
    "A2+": {"A2", "B1"},
    "B1": {"B1"},
    "B1+": {"B1", "B2"},
    "B2": {"B2"},
}


def read_json(path, default):
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8").strip()
    return json.loads(text) if text else default


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def level_ok(stage, level):
    allowed = STAGE_LEVELS.get(str(stage or ""))
    return str(level or "").upper() in allowed if allowed else True


def band(score):
    if score >= 0.40:
        return "HIGH"
    if score >= 0.30:
        return "MEDIUM"
    return "LOW"


def has_specific_reason(option):
    reason = str(option.get("candidate_reason", ""))
    return ":" in reason


def keep_option(stage, option):
    score = float(option.get("candidate_score", 0.0))
    if score < MIN_SCORE:
        return False
    if not level_ok(stage, option.get("egp_level")):
        return False
    if score < 0.30 and not has_specific_reason(option):
        return False
    return True


def refine(records):
    out = []
    removed = 0
    for record in records:
        stage = record.get("system_stage")
        kept = []
        for option in record.get("candidate_suggestions", []):
            if keep_option(stage, option):
                item = dict(option)
                item["confidence_band"] = band(float(item.get("candidate_score", 0.0)))
                item["review_required"] = True
                kept.append(item)
            else:
                removed += 1
        kept.sort(key=lambda row: (-float(row.get("candidate_score", 0.0)), row.get("egp_level", ""), row.get("egp_row_id", "")))
        out.append({
            "grammar_id": record.get("grammar_id"),
            "review_priority": record.get("review_priority"),
            "system_stage": stage,
            "node_status": record.get("node_status"),
            "refined_candidate_suggestions": kept[:MAX_REFINED],
            "review_required": True,
            "learner_state_write": False,
            "practicebank_generation": False,
        })
    return out, removed


def build(source):
    records, removed = refine(source.get("records", []))
    total = sum(len(row["refined_candidate_suggestions"]) for row in records)
    no_safe = sum(1 for row in records if not row["refined_candidate_suggestions"])
    bands = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for row in records:
        for option in row["refined_candidate_suggestions"]:
            bands[option["confidence_band"]] += 1
    refined = {
        "task_id": "R7-M56R_GrammarNodeEGPRefinedCandidateBuilderImplementation",
        "artifact_id": "grammar_node_egp_refined_candidate_suggestions",
        "source_path": "ulga/reports/grammar_node_egp_candidate_suggestions.json",
        "max_refined_candidates_per_node": MAX_REFINED,
        "minimum_candidate_score": MIN_SCORE,
        "records": records,
        "scope_constraints": {
            "no_runtime_implementation": True,
            "no_practicebank_generation": True,
            "no_learner_state_write": True,
            "no_auto_egp_row_selection": True,
            "no_authority_write": True,
        },
    }
    summary = {
        "task_id": "R7-M56R_GrammarNodeEGPRefinedCandidateBuilderImplementation",
        "artifact_id": "grammar_node_egp_refined_candidate_suggestions_summary",
        "validation_status": "PASS_WITH_WARNINGS" if no_safe else "PASS",
        "source_record_count": len(source.get("records", [])),
        "refined_record_count": len(records),
        "total_refined_candidate_count": total,
        "records_without_refined_candidates": no_safe,
        "removed_candidate_count": removed,
        "confidence_band_counts": bands,
        "max_refined_candidates_per_node": MAX_REFINED,
        "operator_review_required": True,
        "next_short_step": "R7-M57R_GrammarNodeEGPRefinedCandidateReadback",
        "stop_reason": "NONE",
    }
    return refined, summary


def main():
    source = read_json(IN_PATH, {"records": []})
    refined, summary = build(source)
    write_json(OUT_PATH, refined)
    write_json(SUMMARY_PATH, summary)
    print(f"Refined grammar node EGP candidates build: {summary['validation_status']}")
    print(f"Refined records: {summary['refined_record_count']}")
    print(f"Total refined candidates: {summary['total_refined_candidate_count']}")


if __name__ == "__main__":
    main()
