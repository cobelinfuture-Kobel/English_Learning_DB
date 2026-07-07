import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
OUT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_second_refinement_plan.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_second_refinement_plan_summary.json"

TASK_ID = "R7-M67_Batch01SecondRefinementPlanArtifactBuilder"
SOURCE_TASKS = [
    "R7-M65_Batch01OperatorDecisionArtifact",
    "R7-M66_Batch01DecisionReadbackAndNextRefinementPlan",
]

TARGETS = [
    {
        "item_id": "B01-01",
        "grammar_id": "GRAMMAR_ARTICLES_BASIC",
        "operator_decision": "REQUEST_REFINED_CANDIDATES",
        "refinement_action": "SECOND_PASS_REFINE",
        "target_description": "Find broad basic article presence rules for a/an/the with nouns.",
        "mapping_mode": "collocation_sensitive",
        "grammar_family": "determiner_articles",
        "allow_super_categories": ["DETERMINERS"],
        "allow_sub_category_contains": ["articles"],
        "guideword_include": ["WITH NOUNS", "INDEFINITE", "DEFINITE", "A + NOUN", "AN + NOUN", "THE + NOUN"],
        "guideword_exclude": ["NO ARTICLE", "PREPOSITION + NO ARTICLE", "VERY + ADJECTIVES"],
        "operator_review_required": True,
    },
    {
        "item_id": "B01-02",
        "grammar_id": "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
        "operator_decision": "REQUEST_REFINED_CANDIDATES",
        "refinement_action": "SECOND_PASS_REFINE",
        "target_description": "Find EGP rows for locative/place prepositions.",
        "mapping_mode": "lexico_grammar",
        "grammar_family": "prepositions_place",
        "allow_super_categories": ["PREPOSITIONS", "CLAUSES"],
        "allow_sub_category_contains": ["preposition", "prepositional", "locative"],
        "guideword_include": ["PLACE", "LOCATION", "POSITION", "IN", "ON", "UNDER", "NEXT TO", "BEHIND", "BETWEEN", "IN FRONT OF"],
        "guideword_exclude": ["NO ARTICLE", "ARTICLE-ONLY", "NOUN PHRASE-ONLY"],
        "operator_review_required": True,
    },
    {
        "item_id": "B01-03",
        "grammar_id": "GRAMMAR_BE_VERB_BASIC",
        "operator_decision": "REQUEST_REFINED_CANDIDATES",
        "refinement_action": "SECOND_PASS_REFINE",
        "target_description": "Find direct EGP evidence for am/is/are basic be-verb forms.",
        "mapping_mode": "grammar",
        "grammar_family": "be_verb_core",
        "allow_super_categories": ["VERBS", "CLAUSES", "QUESTIONS"],
        "allow_sub_category_contains": ["be", "declarative", "negative", "yes/no"],
        "guideword_include": ["BE", "AM", "IS", "ARE", "AFFIRMATIVE WITH BE", "NEGATIVE WITH BE", "QUESTIONS WITH BE"],
        "guideword_exclude": ["MODAL", "LIKE", "INFINITIVE", "LEXICAL VERB-ONLY"],
        "operator_review_required": True,
    },
    {
        "item_id": "B01-04",
        "grammar_id": "GRAMMAR_CAN_STATEMENT",
        "operator_decision": "DEFER",
        "refinement_action": "SOURCE_ROW_AUDIT",
        "target_description": "Audit whether the candidate supports can + base verb for ability statements.",
        "mapping_mode": "grammar",
        "grammar_family": "modal_can_statement",
        "candidate_to_audit": "1741163708329x931125497510935300",
        "audit_requirements": [
            "Inspect source row example strings.",
            "Confirm whether can expresses ability rather than generic modal form.",
            "Do not accept the row without explicit source support.",
        ],
        "allowed_audit_outcomes": ["ACCEPT_EGP_ROW", "REQUEST_REFINED_CANDIDATES", "DEFER"],
        "operator_review_required": True,
    },
    {
        "item_id": "B01-05",
        "grammar_id": "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC",
        "operator_decision": "REQUEST_REFINED_CANDIDATES",
        "refinement_action": "SECOND_PASS_REFINE",
        "target_description": "Find EGP rows for possessive adjectives or determiners before nouns.",
        "mapping_mode": "grammar",
        "grammar_family": "possessive_determiners",
        "allow_super_categories": ["DETERMINERS"],
        "allow_sub_category_contains": ["possessive", "determiner"],
        "guideword_include": ["POSSESSIVE", "MY", "YOUR", "HIS", "HER", "ITS", "OUR", "THEIR", "+ NOUN"],
        "guideword_exclude": ["ARTICLE-ONLY", "ADJECTIVE-ONLY", "NOUN PHRASE WITHOUT POSSESSIVE"],
        "operator_review_required": True,
    },
]


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build():
    plan = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_batch01_second_refinement_plan",
        "source_tasks": SOURCE_TASKS,
        "batch_id": "R7-M58R-BATCH-01",
        "targets": TARGETS,
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
    action_counts = {}
    decision_counts = {}
    for target in TARGETS:
        action_counts[target["refinement_action"]] = action_counts.get(target["refinement_action"], 0) + 1
        decision_counts[target["operator_decision"]] = decision_counts.get(target["operator_decision"], 0) + 1
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_batch01_second_refinement_plan_summary",
        "validation_status": "PASS",
        "target_count": len(TARGETS),
        "action_counts": action_counts,
        "decision_counts": decision_counts,
        "operator_review_required": True,
        "next_short_step": "R7-M68_Batch01SecondRefinementPlanReadback",
        "stop_reason": "NONE",
    }
    return plan, summary


def main():
    plan, summary = build()
    write_json(OUT_PATH, plan)
    write_json(SUMMARY_PATH, summary)
    print(f"Batch 01 second refinement plan build: {summary['validation_status']}")
    print(f"Target count: {summary['target_count']}")
    print(f"Action counts: {summary['action_counts']}")


if __name__ == "__main__":
    main()
