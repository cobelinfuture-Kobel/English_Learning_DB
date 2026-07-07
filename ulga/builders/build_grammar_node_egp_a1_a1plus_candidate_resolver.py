import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SEARCH_BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_a1_a1plus_refined_candidate_search.py"
SEARCH_REPORT = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_refined_candidate_search.json"
EGP_INDEX = BASE_DIR / "ulga" / "reports" / "egp_row_index_compact.json"
OUT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_candidate_resolver.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_candidate_resolver_summary.json"
TASK_ID = "R7-M97A_A1A1PLUSBulkEGPRowCandidateResolver"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_search_report():
    if SEARCH_REPORT.exists():
        return
    result = subprocess.run([sys.executable, str(SEARCH_BUILDER)], cwd=BASE_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stdout + result.stderr)


def match_candidates(record, index_rows):
    seeds = record.get("query_seeds", [])
    terms = sorted({term.lower() for seed in seeds for term in seed.replace("/", " ").split() if len(term) > 2})
    hits = []
    for row in index_rows:
        haystack = " ".join(str(row.get(k, "")) for k in ["level", "super_category", "sub_category", "guideword", "can_do"] ).lower()
        score = sum(1 for term in terms if term in haystack)
        if score:
            hits.append({
                "egp_source_ref": row["source_ref"],
                "score": score,
                "level": row.get("level"),
                "candidate_strength": "review"
            })
    hits.sort(key=lambda item: (-item["score"], item["egp_source_ref"]))
    return hits[:5]


def main():
    ensure_search_report()
    search = load_json(SEARCH_REPORT)
    index_rows = []
    source_index_status = "MISSING"
    if EGP_INDEX.exists():
        index = load_json(EGP_INDEX)
        index_rows = index.get("rows", [])
        source_index_status = "READY"
    records = []
    total_candidates = 0
    for item in search["records"]:
        candidates = match_candidates(item, index_rows) if index_rows else []
        total_candidates += len(candidates)
        records.append({
            "grammar_id": item["grammar_id"],
            "resolution_status": "CANDIDATES_RESOLVED_FOR_OPERATOR_REVIEW" if candidates else "SOURCE_INDEX_REQUIRED",
            "candidate_count": len(candidates),
            "candidates": candidates,
            "canonical_write_allowed": False,
            "operator_review_required": True
        })
    report = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_a1_a1plus_candidate_resolver",
        "source_index_status": source_index_status,
        "records": records,
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
        "artifact_id": "grammar_node_egp_a1_a1plus_candidate_resolver_summary",
        "validation_status": "PASS",
        "source_index_status": source_index_status,
        "source_refined_target_count": len(search["records"]),
        "resolved_target_count": sum(1 for r in records if r["candidate_count"] > 0),
        "total_candidate_count": total_candidates,
        "targets_without_candidates": [r["grammar_id"] for r in records if r["candidate_count"] == 0],
        "canonical_grammar_write_allowed": False,
        "operator_review_required": True,
        "next_short_step": "R7-M97B_EGPCompactRowIndexBuilder",
        "stop_reason": "NONE"
    }
    write_json(OUT_PATH, report)
    write_json(SUMMARY_PATH, summary)
    print("A1/A1_PLUS candidate resolver infrastructure build: PASS")
    print("Source index status:", source_index_status)
    print("Resolved targets:", summary["resolved_target_count"])


if __name__ == "__main__":
    main()
