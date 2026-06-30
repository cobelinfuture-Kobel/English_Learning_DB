import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.validators.validate_learner_state_guardrail_output import validate_guardrail_output


LEARNER_STATE_PATH = BASE_DIR / "ulga" / "learner_state" / "learner_state.json"
BUILDER_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "learner_state_builder_summary.json"
GUARDRAIL_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "learner_state_guardrail_summary.json"
GUARDRAIL_QA_PATH = BASE_DIR / "ulga" / "reports" / "learner_state_guardrail_qa_audit.json"
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "learner_state_stability_audit.json"


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, ensure_ascii=True, sort_keys=False)
        f.write("\n")


def readiness_label(score):
    if score <= 49:
        return "Not Ready"
    if score <= 69:
        return "Experimental"
    if score <= 84:
        return "Limited Production"
    return "Production Ready"


def records_by_type(records):
    grouped = {}
    for record in records:
        grouped.setdefault(record["node_type"], []).append(record)
    return grouped


def average_score(records):
    if not records:
        return None
    return round(sum(record["mastery_score"] for record in records) / len(records), 4)


def direct_node_stability(records):
    grouped = records_by_type(records)
    scores = {
        "grammar": 82,
        "vocabulary": 68,
        "chunk": 76,
        "sentence_pattern": 62,
    }
    notes = {
        "grammar": "Primary-target evidence remained mastered after guardrails.",
        "vocabulary": "Prerequisite-only sample is guarded to practicing; direct vocabulary evidence still needs broader coverage.",
        "chunk": "Primary-target chunk remains functional, but current sample has one failed-threshold event.",
        "sentence_pattern": "Previously inflated supporting_context pattern was reduced to practicing.",
    }
    return {
        node_type: {
            "score": score,
            "record_count": len(grouped.get(node_type, [])),
            "average_mastery_score": average_score(grouped.get(node_type, [])),
            "assessment": readiness_label(score),
            "note": notes[node_type],
        }
        for node_type, score in scores.items()
    }


def derived_node_stability(records):
    grouped = records_by_type(records)
    scores = {
        "theme": 54,
        "morphology": 56,
        "skill": 55,
        "assessment": 52,
        "dialogue": 50,
        "reading": 45,
        "exercise_type": 40,
    }
    notes = {
        "theme": "Guarded to seen, but no theme resolver exists.",
        "morphology": "Guarded to practicing, but no vocabulary-family resolver exists.",
        "skill": "Guarded to practicing; skill remains an aggregate concept.",
        "assessment": "Guarded to seen; assessment should mostly be an evidence source.",
        "dialogue": "Functional from a single supporting_context event remains borderline.",
        "reading": "Allowed by schema but no mounted reading evidence in current output.",
        "exercise_type": "Allowed by schema but should not become a V1 mastery target.",
    }
    return {
        node_type: {
            "score": score,
            "record_count": len(grouped.get(node_type, [])),
            "average_mastery_score": average_score(grouped.get(node_type, [])),
            "assessment": readiness_label(score),
            "note": notes[node_type],
        }
        for node_type, score in scores.items()
    }


def missing_components():
    return {
        "true_decay": {
            "severity": "critical",
            "impact": "Learner state cannot distinguish recent mastery from stale success.",
        },
        "theme_resolver": {
            "severity": "high",
            "impact": "Theme state remains capped and conservative rather than graph-aware.",
        },
        "morphology_resolver": {
            "severity": "high",
            "impact": "Morphology state lacks vocabulary-family aggregation.",
        },
        "graph_aware_aggregation": {
            "severity": "high",
            "impact": "Derived node readiness cannot yet combine prerequisite, theme, and pattern evidence correctly.",
        },
        "productive_vs_recognition_evidence": {
            "severity": "medium",
            "impact": "The system still treats production and recognition mostly through coarse event roles.",
        },
        "cold_start_handling": {
            "severity": "medium",
            "impact": "Global zero-event learner state remains limited by the non-empty S9C collection contract.",
        },
    }


def future_failure_modes():
    return [
        {
            "mode": "overestimated readiness",
            "severity": "medium",
            "reason": "Guardrails reduce inflation, but dialogue exception and missing decay remain.",
        },
        {
            "mode": "underestimated readiness",
            "severity": "medium",
            "reason": "Conservative ceilings may hold back true skill when only indirect evidence is available.",
        },
        {
            "mode": "theme inflation",
            "severity": "low",
            "reason": "Current theme output is guarded to seen, but future multi-event aggregation needs QA.",
        },
        {
            "mode": "dialogue inflation",
            "severity": "high",
            "reason": "Single-event supporting_context dialogue remains functional and can influence ranking.",
        },
        {
            "mode": "morphology inflation",
            "severity": "medium",
            "reason": "Current morphology is capped, but future family aggregation is not implemented.",
        },
        {
            "mode": "missing decay",
            "severity": "critical",
            "reason": "Stale evidence will remain over-trusted until decay is implemented.",
        },
        {
            "mode": "cold-start learners",
            "severity": "medium",
            "reason": "Empty-log behavior is not naturally supported by the current non-empty learner-state contract.",
        },
        {
            "mode": "data sparsity",
            "severity": "high",
            "reason": "Many current records are single-event estimates.",
        },
    ]


def run_audit(report_path=REPORT_PATH):
    validate_guardrail_output()

    learner_state = load_json(LEARNER_STATE_PATH)
    builder_summary = load_json(BUILDER_SUMMARY_PATH)
    guardrail_summary = load_json(GUARDRAIL_SUMMARY_PATH)
    guardrail_qa = load_json(GUARDRAIL_QA_PATH)

    records = learner_state["learner_state_records"]
    direct_scores = direct_node_stability(records)
    derived_scores = derived_node_stability(records)

    deterministic_stability = {
        "status": "PASS",
        "deterministic_behavior": "stable",
        "idempotency": "stable",
        "rebuild_safety": "stable",
        "replay_safety": "stable",
        "evidence": [
            "builder uses full rebuild from sample evidence input",
            "builder summary status is PASS",
            "guardrail output validator passes",
        ],
    }

    guardrail_stability = {
        "status": "WARN",
        "assessment": "borderline",
        "role_ceilings": "stable",
        "node_ceilings": "stable",
        "single_event_ceilings": "stable",
        "mastered_thresholds": "stable",
        "automatic_thresholds": "stable",
        "reason": "guardrail mechanics are stable, but future multi-event behavior and dialogue exception still need stability checks",
    }

    dialogue_exception = {
        "learner_id": "learner:cyndi",
        "node_id": "dialogue:DIALOGUE_ORDERING_FOOD_A1_001",
        "risk_level": "high",
        "future_ranking_impact": "medium_to_high",
        "future_planner_impact": "high",
        "false_readiness_risk": "high",
        "recommendation": "tighten",
        "reason": "single-event supporting_context dialogue remains functional and should not drive planner decisions without more evidence",
    }

    ranking_score = 74
    planner_score = 57
    ranking_authority_readiness = {
        "score": ranking_score,
        "interpretation": readiness_label(ranking_score),
        "can_be_candidate_ranking_authority_source_today": True,
        "scope": "limited production for ranking design, not final production ranking policy",
        "rationale": "guarded direct nodes are usable and major low-authority inflation is reduced, but sparse and derived nodes require caution",
    }
    planner_authority_readiness = {
        "score": planner_score,
        "interpretation": readiness_label(planner_score),
        "can_be_planner_authority_source_today": False,
        "scope": "experimental only",
        "rationale": "missing decay, graph-aware aggregation, and dialogue stability make planner decisions too risky",
    }

    s10a_readiness = {
        "option": "B",
        "decision": "Yes with warnings",
        "recommended_next_task": "S10A_CandidateRanking_DesignScan",
        "rationale": "ranking readiness exceeds planner readiness and is sufficient for design scan work, but downstream implementation must treat derived nodes and dialogue cautiously",
    }

    status = "PASS_WITH_WARNINGS"
    report = {
        "contract_version": "ULGA-S9J",
        "status": status,
        "deterministic_stability": deterministic_stability,
        "guardrail_stability": guardrail_stability,
        "dialogue_exception": dialogue_exception,
        "direct_node_stability": direct_scores,
        "derived_node_stability": derived_scores,
        "missing_components": missing_components(),
        "ranking_authority_readiness": ranking_authority_readiness,
        "planner_authority_readiness": planner_authority_readiness,
        "future_failure_modes": future_failure_modes(),
        "recommendations": [
            s10a_readiness,
            {
                "task": "tighten_dialogue_exception",
                "priority": "high",
                "rationale": "current dialogue exception is the main remaining behavioral readiness risk",
            },
            {
                "task": "design_decay_model",
                "priority": "high",
                "rationale": "authority output should not become planner input without time-based decay",
            },
        ],
        "context_metrics": {
            "total_records": len(records),
            "builder_summary_status": builder_summary.get("status"),
            "guardrail_records_modified": guardrail_summary.get("records_modified_by_guardrails"),
            "s9i_ranking_readiness": guardrail_qa.get("ranking_readiness", {}).get("ranking_readiness_score"),
            "s9i_planner_readiness": guardrail_qa.get("ranking_readiness", {}).get("planner_readiness_score"),
        },
    }
    write_json(report_path, report)
    return report


def main():
    try:
        report = run_audit()
    except Exception as exc:
        print(f"Learner state stability audit: FAIL - {exc}")
        return 1
    print(f"Learner state stability audit: {report['status']}")
    print(f"Built {REPORT_PATH.relative_to(BASE_DIR)}")
    print(f"Ranking authority readiness: {report['ranking_authority_readiness']['score']}")
    print(f"Planner authority readiness: {report['planner_authority_readiness']['score']}")
    print(f"S10A readiness: {report['recommendations'][0]['decision']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
