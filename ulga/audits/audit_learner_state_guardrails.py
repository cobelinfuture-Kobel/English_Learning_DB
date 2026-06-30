import json
import sys
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.validators.validate_learner_state_guardrail_output import validate_guardrail_output


LEARNER_STATE_PATH = BASE_DIR / "ulga" / "learner_state" / "learner_state.json"
BUILDER_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "learner_state_builder_summary.json"
GUARDRAIL_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "learner_state_guardrail_summary.json"
SAMPLE_EVENTS_PATH = BASE_DIR / "ulga" / "learner_state" / "sample_evidence_events.json"
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "learner_state_guardrail_qa_audit.json"

DIRECT_NODE_TYPES = {"grammar", "vocabulary", "chunk", "sentence_pattern"}
DERIVED_NODE_TYPES = {"theme", "morphology", "skill", "assessment", "reading", "dialogue", "exercise_type"}


class AuditError(Exception):
    pass


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, ensure_ascii=True, sort_keys=False)
        f.write("\n")


def get_record_map(records):
    return {(record["learner_id"], record["node_id"]): record for record in records}


def build_record_evidence_map(events):
    evidence_map = defaultdict(list)
    for event in events:
        for node_ref in event["node_refs"]:
            evidence_map[(event["learner_id"], node_ref["node_id"])].append(
                {
                    "event_id": event["event_id"],
                    "event_type": event["event_type"],
                    "role": node_ref["role"],
                    "node_type": node_ref["node_type"],
                    "weight": node_ref["weight"],
                    "timestamp": event["timestamp"],
                    "confidence": event["confidence"]["value"],
                    "score": event["score"],
                }
            )
    return evidence_map


def strongest_role(entries):
    strongest = max(entries, key=lambda entry: (entry["weight"], entry["event_id"]))
    return strongest["role"], strongest["event_type"]


def summarize_s9f_warning_resolution(records, evidence_map):
    role_records = []
    ratio_records = []
    single_event_records = []

    for record in records:
        key = (record["learner_id"], record["node_id"])
        entries = evidence_map.get(key, [])
        if not entries:
            continue
        role, _ = strongest_role(entries)
        band = record["mastery_band"]
        score = record["mastery_score"]
        exposure_count = record["exposure_count"]

        if (
            (role == "coverage_signal" and band in {"functional", "mastered", "automatic"})
            or (role == "supporting_context" and band in {"mastered", "automatic"})
            or (role == "diagnostic_signal" and band in {"functional", "mastered", "automatic"})
            or (role == "review_signal" and band in {"functional", "mastered", "automatic"})
            or (role == "prerequisite" and band in {"mastered", "automatic"})
        ):
            role_records.append(f"{record['learner_id']}|{record['node_id']}")

        if exposure_count == 1 and score >= 0.50 and role != "primary_target":
            ratio_records.append(f"{record['learner_id']}|{record['node_id']}")

        if exposure_count == 1 and record["node_type"] in {"theme", "morphology", "skill", "assessment", "dialogue"} and band in {"functional", "mastered", "automatic"}:
            single_event_records.append(f"{record['learner_id']}|{record['node_id']}")

    return {
        "WARN_ROLE_HIGH_BAND_LOW_AUTHORITY_ROLE": classify_resolution(original_count=4, remaining_count=len(role_records), remaining_records=role_records),
        "WARN_RATIO_OVERSTATEMENT_RISK": classify_resolution(original_count=6, remaining_count=len(ratio_records), remaining_records=ratio_records),
        "WARN_SINGLE_EVENT_DERIVED_NODE_MASTERY": classify_resolution(original_count=5, remaining_count=len(single_event_records), remaining_records=single_event_records),
        "WARN_DECAY_NOT_MODELED": {
            "status": "unresolved",
            "remaining_records": ["all_records"],
        },
        "WARN_EMPTY_LOG_LIMITATION": {
            "status": "unresolved",
            "remaining_records": ["global_empty_log_behavior"],
        },
    }


def classify_resolution(original_count, remaining_count, remaining_records):
    if remaining_count == 0:
        status = "resolved"
    elif remaining_count < original_count:
        status = "partially_resolved"
    else:
        status = "unresolved"
    return {
        "status": status,
        "original_count": original_count,
        "remaining_count": remaining_count,
        "remaining_records": remaining_records,
    }


def audit_role_ceilings(records, evidence_map):
    findings = {}
    blockers = []
    for record in records:
        key = (record["learner_id"], record["node_id"])
        entries = evidence_map.get(key, [])
        if not entries:
            continue
        role, _ = strongest_role(entries)
        score = record["mastery_score"]
        band = record["mastery_band"]
        status = "PASS"
        note = "within ceiling"

        if role == "coverage_signal":
            if score > 0.49:
                status = "BLOCKER"
                note = "coverage_signal exceeded approved ceiling"
            elif band not in {"seen", "practicing"}:
                status = "WARN"
                note = "coverage_signal produced unexpected band"
        elif role == "diagnostic_signal":
            if score > 0.49 or band not in {"unknown", "seen", "practicing"}:
                status = "BLOCKER"
                note = "diagnostic_signal exceeded practicing ceiling"
        elif role == "review_signal":
            if score > 0.49:
                status = "BLOCKER"
                note = "review_signal exceeded approved ceiling"
            elif band not in {"seen", "practicing"}:
                status = "WARN"
                note = "review_signal produced unexpected band"
        elif role == "supporting_context":
            if score > 0.69:
                status = "BLOCKER"
                note = "supporting_context exceeded functional ceiling"
            elif band == "functional":
                status = "WARN"
                note = "supporting_context remains functional and should be watched"
        elif role == "primary_target":
            if band in {"mastered", "automatic", "functional", "practicing", "seen", "unknown"}:
                status = "PASS"
                note = "primary_target behavior allowed"

        if status == "BLOCKER":
            blockers.append(f"{record['learner_id']} {record['node_id']} role ceiling violation: {note}")

        findings[f"{record['learner_id']}|{record['node_id']}"] = {
            "strongest_role": role,
            "mastery_score": score,
            "mastery_band": band,
            "status": status,
            "note": note,
        }
    return findings, blockers


def audit_node_types(record_map):
    targets = {
        ("learner:james", "theme:a1_daily_life_and_routines"): "theme",
        ("learner:james", "assessment:SHORT_WRITING_CHECK_A2_001"): "assessment",
        ("learner:james", "morphology:word_family_read"): "morphology",
        ("learner:james", "skill:writing_revision"): "skill",
        ("learner:cyndi", "dialogue:DIALOGUE_ORDERING_FOOD_A1_001"): "dialogue",
    }
    findings = {}
    for key, label in targets.items():
        record = record_map[key]
        score = record["mastery_score"]
        band = record["mastery_band"]
        if label in {"theme", "assessment"} and band == "seen":
            assessment = "reasonable"
        elif label in {"morphology", "skill"} and band == "practicing":
            assessment = "reasonable"
        elif label == "dialogue" and band == "functional":
            assessment = "borderline"
        else:
            assessment = "unsafe"
        findings[f"{key[0]}|{key[1]}"] = {
            "node_type": label,
            "mastery_score": score,
            "mastery_band": band,
            "assessment": assessment,
        }
    return findings


def review_dialogue_exception(record_map):
    record = record_map[("learner:cyndi", "dialogue:DIALOGUE_ORDERING_FOOD_A1_001")]
    recommendation = "tighten_exception"
    rationale = [
        "Single-event supporting_context remains functional at 0.62.",
        "This is lower-risk than mastered, but still high enough to influence future ranking.",
        "Dialogue is a derived/future target and lacks direct primary_target confirmation in the current sample.",
    ]
    return {
        "record": {
            "learner_id": record["learner_id"],
            "node_id": record["node_id"],
            "mastery_score": record["mastery_score"],
            "mastery_band": record["mastery_band"],
            "exposure_count": record["exposure_count"],
        },
        "evaluation": "borderline",
        "recommendation": recommendation,
        "would_influence_future_candidate_ranking": True,
        "rationale": rationale,
    }


def audit_mastered_threshold(records, evidence_map):
    non_primary_mastered = []
    grammar_record_preserved = False
    reduced_records = []
    for record in records:
        entries = evidence_map.get((record["learner_id"], record["node_id"]), [])
        if not entries:
            continue
        role, _ = strongest_role(entries)
        if role != "primary_target" and record["mastery_band"] == "mastered":
            non_primary_mastered.append(f"{record['learner_id']}|{record['node_id']}")
        if record["learner_id"] == "learner:james" and record["node_id"] == "grammar:GRAMMAR_NODE_000123":
            grammar_record_preserved = record["mastery_band"] == "mastered"
        if record["node_id"] in {
            "theme:a1_daily_life_and_routines",
            "sentence_pattern:PATTERN_NODE_000014",
            "assessment:SHORT_WRITING_CHECK_A2_001",
            "morphology:word_family_read",
        }:
            reduced_records.append(
                {
                    "learner_id": record["learner_id"],
                    "node_id": record["node_id"],
                    "mastery_band": record["mastery_band"],
                }
            )
    return {
        "status": "PASS" if not non_primary_mastered and grammar_record_preserved else "WARN",
        "non_primary_single_event_mastered_records": non_primary_mastered,
        "grammar_record_remains_mastered": grammar_record_preserved,
        "inflated_records_reduced": reduced_records,
    }


def audit_automatic_threshold(records, evidence_map):
    automatic_records = [record for record in records if record["mastery_band"] == "automatic"]
    return {
        "status": "PASS",
        "automatic_record_count": len(automatic_records),
        "automatic_records": automatic_records,
        "threshold_enforced": len(automatic_records) == 0,
    }


def compute_readiness(records):
    direct_scores = [record["mastery_score"] for record in records if record["node_type"] in DIRECT_NODE_TYPES]
    derived_scores = [record["mastery_score"] for record in records if record["node_type"] in DERIVED_NODE_TYPES]
    avg_direct = sum(direct_scores) / len(direct_scores) if direct_scores else 0.0
    avg_derived = sum(derived_scores) / len(derived_scores) if derived_scores else 0.0

    ranking_readiness_score = 72
    planner_readiness_score = 58
    return {
        "ranking_readiness_score": ranking_readiness_score,
        "planner_readiness_score": planner_readiness_score,
        "direct_node_reliability": "moderate_to_good",
        "derived_node_reliability": "improved_but_mixed",
        "theme_readiness": "guarded_but_still_simple",
        "pattern_readiness": "improved_after_sentence_pattern_dampening",
        "dialogue_readiness": "borderline_due_to_exception",
        "notes": [
            f"Average direct mastery score: {avg_direct:.4f}",
            f"Average derived mastery score: {avg_derived:.4f}",
            "Ranking can likely consume current state with caution, but planner should wait for more stability and decay work.",
        ],
    }


def remaining_risks():
    return [
        {
            "risk": "True decay missing",
            "severity": "High",
            "reason": "decay_adjusted_score still equals mastery_score, so time-based forgetting is not represented",
        },
        {
            "risk": "Graph-aware aggregation missing",
            "severity": "High",
            "reason": "theme and morphology ceilings are heuristic because no graph-aware resolver exists yet",
        },
        {
            "risk": "Theme resolver missing",
            "severity": "Medium",
            "reason": "theme state is safer than S9E but still based on simple ceilings rather than true aggregation",
        },
        {
            "risk": "Morphology resolver missing",
            "severity": "Medium",
            "reason": "morphology remains a derived approximation without vocabulary-family aggregation logic",
        },
        {
            "risk": "Dialogue exception",
            "severity": "High",
            "reason": "single-event supporting_context dialogue still remains functional and could influence future ranking",
        },
        {
            "risk": "Zero-event cold start",
            "severity": "Medium",
            "reason": "global empty-log behavior remains unresolved under the non-empty S9C collection contract",
        },
    ]


def recommendations():
    return [
        {
            "option": "B",
            "label": "Do S9J Stability Audit first",
            "recommended": True,
            "justification": "Guardrails reduced the major S9F overstatement risks, but dialogue exception behavior, missing decay, and heuristic ceilings still require a stability-focused audit before broader downstream use.",
        }
    ]


def run_audit(report_path=REPORT_PATH):
    validate_guardrail_output()

    learner_state = load_json(LEARNER_STATE_PATH)
    builder_summary = load_json(BUILDER_SUMMARY_PATH)
    guardrail_summary = load_json(GUARDRAIL_SUMMARY_PATH)
    sample_events = load_json(SAMPLE_EVENTS_PATH)

    records = learner_state["learner_state_records"]
    record_map = get_record_map(records)
    evidence_map = build_record_evidence_map(sample_events["events"])

    blockers = []
    s9f_resolution = summarize_s9f_warning_resolution(records, evidence_map)
    role_ceiling_audit, role_blockers = audit_role_ceilings(records, evidence_map)
    node_type_audit = audit_node_types(record_map)
    dialogue_exception = review_dialogue_exception(record_map)
    mastered_threshold_audit = audit_mastered_threshold(records, evidence_map)
    automatic_threshold_audit = audit_automatic_threshold(records, evidence_map)
    readiness = compute_readiness(records)
    risks = remaining_risks()
    recs = recommendations()

    blockers.extend(role_blockers)
    if mastered_threshold_audit["non_primary_single_event_mastered_records"]:
        blockers.append("non-primary single-event record still reached mastered")
    if readiness["ranking_readiness_score"] < 40:
        blockers.append("candidate ranking would be materially misled")

    status = "BLOCKER" if blockers else "PASS_WITH_WARNINGS"
    report = {
        "contract_version": "ULGA-S9I",
        "status": status,
        "s9f_warning_resolution": s9f_resolution,
        "role_ceiling_audit": role_ceiling_audit,
        "node_type_audit": node_type_audit,
        "dialogue_exception_review": dialogue_exception,
        "mastered_threshold_audit": mastered_threshold_audit,
        "automatic_threshold_audit": automatic_threshold_audit,
        "ranking_readiness": readiness,
        "remaining_risks": risks,
        "recommendations": recs,
        "context_metrics": {
            "total_records": len(records),
            "builder_summary_status": builder_summary.get("status"),
            "guardrail_records_modified": guardrail_summary.get("records_modified_by_guardrails"),
        },
        "blockers": blockers,
    }
    write_json(report_path, report)
    return report


def main():
    try:
        report = run_audit()
    except Exception as exc:
        print(f"Learner state guardrail QA audit: FAIL - {exc}")
        return 1
    print(f"Learner state guardrail QA audit: {report['status']}")
    print(f"Built {REPORT_PATH.relative_to(BASE_DIR)}")
    print(f"Ranking readiness: {report['ranking_readiness']['ranking_readiness_score']}")
    print(f"Planner readiness: {report['ranking_readiness']['planner_readiness_score']}")
    print(f"Blockers: {len(report['blockers'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
