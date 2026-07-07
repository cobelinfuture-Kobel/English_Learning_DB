import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
PLAN_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_second_refinement_plan.json"
PROFILE_PATH = BASE_DIR / "grammar_profile" / "json" / "grammar_profile.json"
OUT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_second_refinement_candidates.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_second_refinement_candidates_summary.json"
TASK_ID = "R7-M69_Batch01SecondRefinementCandidateAuditBuilderImplementation"
MAX_CANDIDATES = 5
TOKEN_RE = re.compile(r"[A-Za-z0-9']+")
STOP = {"a", "an", "and", "are", "as", "be", "by", "for", "in", "is", "it", "of", "on", "or", "the", "to", "with", "use", "using", "form", "forms"}


def read_json(path, default):
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8").strip()
    return json.loads(text) if text else default


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def norm(value):
    return " " + str(value or "").upper().replace("/", " / ").replace("-", " ").replace("_", " ") + " "


def toks(*values):
    found = set()
    for value in values:
        for token in TOKEN_RE.findall(str(value or "").lower()):
            if len(token) > 1 and token not in STOP:
                found.add(token)
    return found


def row_text(row):
    return norm(" ".join(str(row.get(key, "")) for key in ["super_category", "sub_category", "guideword", "can_do_statement", "example"]))


def phrase_hit(phrase, text):
    phrase_norm = norm(phrase)
    compact_phrase = phrase_norm.replace(" + ", " ")
    return phrase_norm.strip() in text or compact_phrase.strip() in text


def row_matches_target(row, target):
    text = row_text(row)
    super_category = norm(row.get("super_category"))
    sub_category = norm(row.get("sub_category"))
    allowed_super = target.get("allow_super_categories", [])
    allowed_sub = target.get("allow_sub_category_contains", [])
    if allowed_super and not any(norm(value).strip() in super_category for value in allowed_super):
        return False, "super_category_blocked", []
    if allowed_sub and not any(str(value).upper() in sub_category for value in allowed_sub):
        return False, "sub_category_blocked", []
    exclude_hits = [value for value in target.get("guideword_exclude", []) if phrase_hit(value, text)]
    if exclude_hits:
        return False, "negative_filter", exclude_hits
    include_hits = [value for value in target.get("guideword_include", []) if phrase_hit(value, text)]
    if not include_hits:
        return False, "include_filter", []
    return True, "second_pass_gate_pass", include_hits


def score_row(row, target, include_hits):
    row_tokens = toks(row.get("super_category"), row.get("sub_category"), row.get("guideword"), row.get("can_do_statement"), row.get("example"))
    target_tokens = toks(target.get("grammar_id"), target.get("grammar_family"), target.get("target_description"), " ".join(target.get("guideword_include", [])))
    overlap = sorted(row_tokens & target_tokens)
    score = 0.45 + min(len(include_hits), 4) * 0.09 + min(len(overlap), 5) * 0.025
    return round(min(score, 0.99), 6), overlap[:10]


def confidence_band(score):
    if score >= 0.72:
        return "HIGH"
    if score >= 0.55:
        return "MEDIUM"
    return "LOW"


def build_refine_target(target, profile):
    candidates = []
    for row in profile:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        allowed, reason, hits = row_matches_target(row, target)
        if not allowed:
            continue
        score, overlap = score_row(row, target, hits)
        candidates.append({
            "egp_row_id": str(row.get("id", "")),
            "egp_level": str(row.get("level", "")).upper(),
            "super_category": str(row.get("super_category", "")),
            "sub_category": str(row.get("sub_category", "")),
            "guideword": str(row.get("guideword", "")),
            "candidate_score": score,
            "confidence_band": confidence_band(score),
            "candidate_reason": reason,
            "gate_hits": hits[:10],
            "token_overlap": overlap,
            "review_required": True,
        })
    candidates.sort(key=lambda row: (-row["candidate_score"], row["egp_level"], row["egp_row_id"]))
    return candidates[:MAX_CANDIDATES]


def build_audit_target(target, profile):
    candidate_id = str(target.get("candidate_to_audit", ""))
    row = next((item for item in profile if isinstance(item, dict) and str(item.get("id", "")) == candidate_id), None)
    if not row:
        return {
            "candidate_to_audit": candidate_id,
            "audit_status": "MISSING_SOURCE_ROW",
            "audit_findings": [],
            "review_required": True,
        }
    text = row_text(row)
    findings = []
    if phrase_hit("CAN", text):
        findings.append("CAN_TOKEN_PRESENT")
    if phrase_hit("ABILITY", text):
        findings.append("ABILITY_TOKEN_PRESENT")
    if phrase_hit("MODAL", text):
        findings.append("MODAL_TOKEN_PRESENT")
    audit_status = "NEEDS_OPERATOR_REVIEW"
    if "CAN_TOKEN_PRESENT" in findings and "ABILITY_TOKEN_PRESENT" in findings:
        audit_status = "POSSIBLE_CAN_ABILITY_SUPPORT"
    return {
        "candidate_to_audit": candidate_id,
        "audit_status": audit_status,
        "egp_row": {
            "egp_row_id": str(row.get("id", "")),
            "egp_level": str(row.get("level", "")).upper(),
            "super_category": str(row.get("super_category", "")),
            "sub_category": str(row.get("sub_category", "")),
            "guideword": str(row.get("guideword", "")),
            "can_do_statement": str(row.get("can_do_statement", "")),
            "example": str(row.get("example", "")),
        },
        "audit_findings": findings,
        "allowed_audit_outcomes": target.get("allowed_audit_outcomes", []),
        "review_required": True,
    }


def build(plan, profile):
    records = []
    action_counts = {}
    total_candidates = 0
    audit_count = 0
    missing_candidate_targets = 0
    for target in plan.get("targets", []):
        action = target.get("refinement_action")
        action_counts[action] = action_counts.get(action, 0) + 1
        record = {
            "item_id": target.get("item_id"),
            "grammar_id": target.get("grammar_id"),
            "operator_decision": target.get("operator_decision"),
            "refinement_action": action,
            "mapping_mode": target.get("mapping_mode"),
            "grammar_family": target.get("grammar_family"),
            "review_required": True,
            "learner_state_write": False,
            "practicebank_generation": False,
        }
        if action == "SECOND_PASS_REFINE":
            candidates = build_refine_target(target, profile)
            record["second_refinement_candidates"] = candidates
            total_candidates += len(candidates)
            if not candidates:
                missing_candidate_targets += 1
        elif action == "SOURCE_ROW_AUDIT":
            record["source_row_audit"] = build_audit_target(target, profile)
            audit_count += 1
        records.append(record)
    output = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_batch01_second_refinement_candidates",
        "source_paths": [str(PLAN_PATH.relative_to(BASE_DIR)), str(PROFILE_PATH.relative_to(BASE_DIR))],
        "records": records,
        "scope_constraints": {
            "no_runtime_implementation": True,
            "no_practicebank_generation": True,
            "no_learner_state_write": True,
            "no_auto_egp_row_selection": True,
            "no_authority_write": True,
            "no_egp_evidence_refs_write": True,
            "no_coverage_increase": True,
        },
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_batch01_second_refinement_candidates_summary",
        "validation_status": "PASS_WITH_WARNINGS" if missing_candidate_targets else "PASS",
        "record_count": len(records),
        "action_counts": action_counts,
        "total_second_refinement_candidate_count": total_candidates,
        "source_row_audit_count": audit_count,
        "second_refine_targets_without_candidates": missing_candidate_targets,
        "operator_review_required": True,
        "next_short_step": "R7-M70_Batch01SecondRefinementCandidateAuditReadback",
        "stop_reason": "NONE",
    }
    return output, summary


def main():
    plan = read_json(PLAN_PATH, {"targets": []})
    profile = read_json(PROFILE_PATH, [])
    output, summary = build(plan, profile)
    write_json(OUT_PATH, output)
    write_json(SUMMARY_PATH, summary)
    print(f"Batch 01 second refinement candidates build: {summary['validation_status']}")
    print(f"Records: {summary['record_count']}")
    print(f"Second refinement candidates: {summary['total_second_refinement_candidate_count']}")
    print(f"Source row audits: {summary['source_row_audit_count']}")


if __name__ == "__main__":
    main()
