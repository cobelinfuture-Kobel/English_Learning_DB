import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
QUEUE_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_mapping_review_queue.json"
PROFILE_PATH = BASE_DIR / "grammar_profile" / "json" / "grammar_profile.json"
OUT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_candidate_suggestions.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_candidate_suggestions_summary.json"
MAX_OPTIONS = 5
TOKEN_RE = re.compile(r"[A-Za-z0-9']+")
STOP = {"a", "an", "and", "are", "as", "be", "by", "for", "in", "is", "it", "of", "on", "or", "the", "to", "with", "use", "using", "form", "forms"}
STAGE_LEVELS = {"A1": ["A1"], "A1+": ["A1", "A2"], "A2": ["A2"], "A2+": ["A2", "B1"], "B1": ["B1"], "B1+": ["B1", "B2"], "B2": ["B2"]}


def read_json(path, default):
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8").strip()
    return json.loads(text) if text else default


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def toks(*values):
    found = set()
    for value in values:
        for token in TOKEN_RE.findall(str(value or "").lower()):
            if len(token) > 1 and token not in STOP:
                found.add(token)
    return found


def score(item, row):
    item_tokens = toks(item.get("grammar_id"), item.get("label"), item.get("category"), item.get("review_reason"))
    row_tokens = toks(row.get("super_category"), row.get("sub_category"), row.get("guideword"), row.get("can_do_statement"), row.get("example"))
    overlap = item_tokens & row_tokens
    union = item_tokens | row_tokens
    value = (len(overlap) / len(union) * 0.7) if union else 0.0
    if str(row.get("level", "")).upper() in STAGE_LEVELS.get(str(item.get("system_stage", "")), ["A1", "A2", "B1", "B2", "C1", "C2"]):
        value += 0.2
    else:
        value -= 0.25
    if toks(item.get("category")) & toks(row.get("super_category"), row.get("sub_category")):
        value += 0.1
    return max(value, 0.0), sorted(overlap)[:8]


def build(queue, profile):
    output = []
    for item in queue.get("records", []):
        options = []
        for row in profile:
            if not isinstance(row, dict) or not row.get("id"):
                continue
            value, overlap = score(item, row)
            if value <= 0:
                continue
            options.append({
                "egp_row_id": str(row.get("id", "")),
                "egp_level": str(row.get("level", "")).upper(),
                "super_category": str(row.get("super_category", "")),
                "sub_category": str(row.get("sub_category", "")),
                "guideword": str(row.get("guideword", "")),
                "candidate_score": round(value, 6),
                "candidate_reason": "deterministic token and level similarity" + (": " + ", ".join(overlap) if overlap else ""),
                "review_required": True,
            })
        options.sort(key=lambda row: (-row["candidate_score"], row["egp_level"], row["egp_row_id"]))
        output.append({
            "grammar_id": item.get("grammar_id"),
            "review_priority": item.get("review_priority"),
            "system_stage": item.get("system_stage"),
            "node_status": item.get("node_status"),
            "candidate_suggestions": options[:MAX_OPTIONS],
            "review_required": True,
            "learner_state_write": False,
            "practicebank_generation": False,
        })
    total = sum(len(row["candidate_suggestions"]) for row in output)
    suggestions = {
        "task_id": "R7-M50_GrammarNodeEGPCandidateSuggestionBuilderImplementation",
        "artifact_id": "grammar_node_egp_candidate_suggestions",
        "records": output,
        "scope_constraints": {
            "no_runtime_implementation": True,
            "no_practicebank_generation": True,
            "no_learner_state_write": True,
        },
    }
    summary = {
        "task_id": "R7-M50_GrammarNodeEGPCandidateSuggestionBuilderImplementation",
        "artifact_id": "grammar_node_egp_candidate_suggestions_summary",
        "validation_status": "PASS_WITH_WARNINGS" if any(not row["candidate_suggestions"] for row in output) else "PASS",
        "review_queue_count": len(queue.get("records", [])),
        "suggestion_record_count": len(output),
        "total_candidate_count": total,
        "max_candidates_per_node": MAX_OPTIONS,
        "review_required": True,
        "next_short_step": "R7-M51_GrammarNodeEGPCandidateSuggestionReviewReadback",
        "stop_reason": "NONE",
    }
    return suggestions, summary


def main():
    queue = read_json(QUEUE_PATH, {"records": []})
    profile = read_json(PROFILE_PATH, [])
    suggestions, summary = build(queue, profile)
    write_json(OUT_PATH, suggestions)
    write_json(SUMMARY_PATH, summary)
    print(f"Grammar node EGP candidate suggestions build: {summary['validation_status']}")
    print(f"Suggestion records: {summary['suggestion_record_count']}")
    print(f"Total candidates: {summary['total_candidate_count']}")


if __name__ == "__main__":
    main()
