import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
QUEUE_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_mapping_review_queue.json"
PROFILE_PATH = BASE_DIR / "grammar_profile" / "json" / "grammar_profile.json"
OUT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_family_gated_candidate_suggestions.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_family_gated_candidate_suggestions_summary.json"
MAX_OPTIONS = 5
TOKEN_RE = re.compile(r"[A-Za-z0-9']+")
STAGE_LEVELS = {"A1": {"A1"}, "A1+": {"A1", "A2"}, "A2": {"A2"}, "A2+": {"A2", "B1"}, "B1": {"B1"}, "B1+": {"B1", "B2"}, "B2": {"B2"}}
STOP = {"a", "an", "and", "are", "as", "be", "by", "for", "in", "is", "it", "of", "on", "or", "the", "to", "with", "use", "using", "form", "forms"}

GATES = {
    "GRAMMAR_ARTICLES_BASIC": {
        "mapping_mode": "collocation_sensitive",
        "grammar_family": "determiner_articles",
        "allow_super": ["DETERMINERS"],
        "allow_sub_contains": ["article"],
        "include": ["ARTICLE", "'A'", " A ", " AN ", " THE ", "DEFINITE", "INDEFINITE"],
        "exclude": ["NO ARTICLE", "PREPOSITION + NO ARTICLE"],
    },
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE": {
        "mapping_mode": "lexico_grammar",
        "grammar_family": "prepositions_place",
        "allow_super": ["PREPOSITIONS"],
        "allow_sub_contains": ["preposition"],
        "include": ["PLACE", "POSITION", "LOCATION", "LOCATIVE", " IN ", " ON ", " AT ", "UNDER", "NEXT TO"],
        "exclude": ["NO ARTICLE", "ARTICLE", "ADJECTIVE + NOUN"],
    },
    "GRAMMAR_BE_VERB_BASIC": {
        "mapping_mode": "grammar",
        "grammar_family": "be_verb_core",
        "allow_super": ["VERBS", "CLAUSES", "QUESTIONS"],
        "allow_sub_contains": ["be", "declarative", "negative", "yes/no"],
        "include": [" BE ", " AM ", " IS ", " ARE ", "BE VERB"],
        "exclude": ["MODAL", "LIKE", "INFINITIVE", "NOUN PHRASE"],
    },
    "GRAMMAR_CAN_STATEMENT": {
        "mapping_mode": "grammar",
        "grammar_family": "modal_can_statement",
        "allow_super": ["VERBS", "CLAUSES"],
        "allow_sub_contains": ["modal", "declarative"],
        "include": [" CAN ", "MODAL", "ABILITY", "AFFIRMATIVE DECLARATIVE"],
        "exclude": ["QUESTION", "YES/NO", "NOUN PHRASE"],
    },
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC": {
        "mapping_mode": "grammar",
        "grammar_family": "possessive_determiners",
        "allow_super": ["DETERMINERS"],
        "allow_sub_contains": ["possessive"],
        "include": ["POSSESSIVE", " MY ", " YOUR ", " HIS ", " HER ", " ITS ", " OUR ", " THEIR "],
        "exclude": ["ARTICLE", "ADJECTIVE + PLURAL NOUN", "LIKE"],
    },
}


def read_json(path, default):
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8").strip()
    return json.loads(text) if text else default


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def norm(value):
    return " " + str(value or "").upper().replace("/", " / ").replace("-", " ") + " "


def tokens(*values):
    found = set()
    for value in values:
        for token in TOKEN_RE.findall(str(value or "").lower()):
            if len(token) > 1 and token not in STOP:
                found.add(token)
    return found


def row_text(row):
    return norm(" ".join(str(row.get(k, "")) for k in ["super_category", "sub_category", "guideword", "can_do_statement", "example"]))


def gate_allows(gate, row):
    text = row_text(row)
    super_category = norm(row.get("super_category"))
    sub_category = norm(row.get("sub_category"))
    if gate.get("allow_super") and not any(norm(value).strip() in super_category for value in gate["allow_super"]):
        return False, "super_category_blocked"
    if gate.get("allow_sub_contains") and not any(value.upper() in sub_category for value in gate["allow_sub_contains"]):
        return False, "sub_category_blocked"
    if gate.get("exclude") and any(value.upper() in text for value in gate["exclude"]):
        return False, "negative_filter"
    if gate.get("include") and not any(value.upper() in text for value in gate["include"]):
        return False, "include_filter"
    return True, "family_gate_pass"


def generic_score(item, row):
    item_tokens = tokens(item.get("grammar_id"), item.get("label"), item.get("category"), item.get("review_reason"))
    candidate_tokens = tokens(row.get("super_category"), row.get("sub_category"), row.get("guideword"), row.get("can_do_statement"), row.get("example"))
    if not item_tokens or not candidate_tokens:
        return 0.0, []
    overlap = item_tokens & candidate_tokens
    union = item_tokens | candidate_tokens
    return len(overlap) / len(union), sorted(overlap)


def gated_score(item, row, gate):
    level = str(row.get("level", "")).upper()
    stage = str(item.get("system_stage", ""))
    if level not in STAGE_LEVELS.get(stage, {"A1", "A2", "B1", "B2"}):
        return None
    allowed, reason = gate_allows(gate, row)
    if not allowed:
        return None
    value, overlap = generic_score(item, row)
    text = row_text(row)
    include_hits = [hit for hit in gate.get("include", []) if hit.upper() in text]
    score = 0.45 + min(len(include_hits), 4) * 0.08 + min(len(overlap), 4) * 0.03 + value * 0.2
    return round(min(score, 0.99), 6), reason, overlap[:8], include_hits[:8]


def band(score):
    if score >= 0.7:
        return "HIGH"
    if score >= 0.5:
        return "MEDIUM"
    return "LOW"


def build(queue, profile):
    records = []
    gate_counts = {"gate_configured": 0, "no_gate": 0}
    for item in queue.get("records", []):
        grammar_id = item.get("grammar_id")
        gate = GATES.get(grammar_id)
        if gate:
            gate_counts["gate_configured"] += 1
        else:
            gate_counts["no_gate"] += 1
        options = []
        if gate:
            for row in profile:
                if not isinstance(row, dict) or not row.get("id"):
                    continue
                scored = gated_score(item, row, gate)
                if not scored:
                    continue
                score, gate_reason, overlap, include_hits = scored
                options.append({
                    "egp_row_id": str(row.get("id", "")),
                    "egp_level": str(row.get("level", "")).upper(),
                    "super_category": str(row.get("super_category", "")),
                    "sub_category": str(row.get("sub_category", "")),
                    "guideword": str(row.get("guideword", "")),
                    "candidate_score": score,
                    "candidate_reason": gate_reason,
                    "grammar_family": gate["grammar_family"],
                    "mapping_mode": gate["mapping_mode"],
                    "gate_hits": include_hits,
                    "token_overlap": overlap,
                    "confidence_band": band(score),
                    "review_required": True,
                })
        options.sort(key=lambda row: (-row["candidate_score"], row["egp_level"], row["egp_row_id"]))
        records.append({
            "grammar_id": grammar_id,
            "review_priority": item.get("review_priority"),
            "system_stage": item.get("system_stage"),
            "node_status": item.get("node_status"),
            "gate_configured": bool(gate),
            "grammar_family": gate.get("grammar_family") if gate else None,
            "mapping_mode": gate.get("mapping_mode") if gate else None,
            "family_gated_candidate_suggestions": options[:MAX_OPTIONS],
            "review_required": True,
            "learner_state_write": False,
            "practicebank_generation": False,
        })
    total = sum(len(row["family_gated_candidate_suggestions"]) for row in records)
    no_safe = sum(1 for row in records if row["gate_configured"] and not row["family_gated_candidate_suggestions"])
    output = {
        "task_id": "R7-M62_GrammarNodeEGPFamilyGatedCandidateBuilderImplementation",
        "artifact_id": "grammar_node_egp_family_gated_candidate_suggestions",
        "source_paths": ["ulga/reports/grammar_node_egp_mapping_review_queue.json", "grammar_profile/json/grammar_profile.json"],
        "max_candidates_per_node": MAX_OPTIONS,
        "gate_policy_task": "R7-M61_GrammarNodeEGPRefinementGateByGrammarFamily",
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
        "task_id": "R7-M62_GrammarNodeEGPFamilyGatedCandidateBuilderImplementation",
        "artifact_id": "grammar_node_egp_family_gated_candidate_suggestions_summary",
        "validation_status": "PASS_WITH_WARNINGS" if no_safe else "PASS",
        "source_record_count": len(queue.get("records", [])),
        "gated_record_count": len(records),
        "gate_counts": gate_counts,
        "total_family_gated_candidate_count": total,
        "configured_gate_records_without_candidates": no_safe,
        "max_candidates_per_node": MAX_OPTIONS,
        "operator_review_required": True,
        "next_short_step": "R7-M63_GrammarNodeEGPFamilyGatedCandidateReadback",
        "stop_reason": "NONE",
    }
    return output, summary


def main():
    queue = read_json(QUEUE_PATH, {"records": []})
    profile = read_json(PROFILE_PATH, [])
    output, summary = build(queue, profile)
    write_json(OUT_PATH, output)
    write_json(SUMMARY_PATH, summary)
    print(f"Grammar node EGP family-gated candidates build: {summary['validation_status']}")
    print(f"Gated records: {summary['gated_record_count']}")
    print(f"Total family-gated candidates: {summary['total_family_gated_candidate_count']}")


if __name__ == "__main__":
    main()
