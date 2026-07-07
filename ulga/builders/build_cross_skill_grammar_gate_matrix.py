import json
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

COVERAGE_MATRIX_PATH = BASE_DIR / "ulga" / "graph" / "grammar_coverage_matrix.json"
CROSS_SKILL_MATRIX_PATH = BASE_DIR / "ulga" / "graph" / "cross_skill_grammar_gate_matrix.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "cross_skill_grammar_gate_summary.json"

SKILLS = ["reading", "listening", "speaking", "writing"]
LEVEL_STAGES = ["A1", "A1+", "A2", "A2+", "B1", "B1+", "B2"]
GLOBAL_ROLES = ["focus", "recycle", "preview", "blocked", "maintenance", "not_applicable"]


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


def dominant_stage_and_role(stage_roles):
    for role in ["focus", "recycle", "preview", "maintenance", "blocked"]:
        for stage in LEVEL_STAGES:
            if stage_roles.get(stage) == role:
                return stage, role
    return "", "not_applicable"


def skill_scope_for_role(global_role):
    if global_role in {"focus", "recycle", "maintenance"}:
        return {
            "reading": {
                "role": global_role,
                "allowed_question_types": ["literal_who", "literal_what", "literal_where", "true_false", "sentence_ordering", "cloze_grammar"],
            },
            "listening": {
                "role": "recognition" if global_role == "maintenance" else global_role,
                "allowed_question_types": ["listen_choose_picture", "listen_sentence_order", "listen_true_false"],
            },
            "speaking": {
                "role": "controlled_production",
                "allowed_activity_types": ["oral_substitution", "picture_prompt", "short_answer"],
            },
            "writing": {
                "role": "guided_writing",
                "allowed_activity_types": ["sentence_frame", "fill_and_write", "guided_rewrite"],
            },
        }
    if global_role == "preview":
        return {
            "reading": {
                "role": "preview",
                "allowed_question_types": ["recognition", "literal_comprehension"],
            },
            "listening": {
                "role": "recognition",
                "allowed_question_types": ["listen_recognition"],
            },
            "speaking": {
                "role": "blocked",
                "allowed_activity_types": [],
            },
            "writing": {
                "role": "blocked",
                "allowed_activity_types": [],
            },
        }
    return {
        "reading": {"role": "blocked", "allowed_question_types": []},
        "listening": {"role": "blocked", "allowed_question_types": []},
        "speaking": {"role": "blocked", "allowed_activity_types": []},
        "writing": {"role": "blocked", "allowed_activity_types": []},
    }


def build_cross_skill_matrix(coverage_matrix):
    if not isinstance(coverage_matrix, dict):
        raise TypeError("coverage matrix must be an object")
    source_records = coverage_matrix.get("records", [])
    records = []
    skill_role_counts = {skill: Counter() for skill in SKILLS}
    blocked_productive_count = 0
    receptive_preview_count = 0

    for source in source_records:
        stage, global_role = dominant_stage_and_role(source.get("stage_roles", {}))
        skill_scope = skill_scope_for_role(global_role)
        receptive_preview_only = global_role == "preview"
        productive_allowed = skill_scope["speaking"]["role"] != "blocked" or skill_scope["writing"]["role"] != "blocked"
        blocked_in = [skill for skill, scope in skill_scope.items() if scope["role"] == "blocked"]

        if receptive_preview_only:
            receptive_preview_count += 1
        if "speaking" in blocked_in or "writing" in blocked_in:
            blocked_productive_count += 1
        for skill, scope in skill_scope.items():
            skill_role_counts[skill][scope["role"]] += 1

        records.append({
            "grammar_id": source.get("grammar_id"),
            "stage": stage,
            "global_role": global_role,
            "skill_scope": skill_scope,
            "blocked_in": blocked_in,
            "receptive_preview_only": receptive_preview_only,
            "productive_allowed": productive_allowed,
            "source_alignment_status": source.get("alignment_status"),
            "source_coverage_status": source.get("coverage_status"),
        })

    matrix = {
        "task_id": "R7-M38_CrossSkillGrammarGateMatrixBuilderImplementation",
        "artifact_id": "cross_skill_grammar_gate_matrix",
        "skills": SKILLS,
        "level_stages": LEVEL_STAGES,
        "global_roles": GLOBAL_ROLES,
        "records": sorted(records, key=lambda item: str(item.get("grammar_id"))),
        "scope_constraints": {
            "no_runtime_implementation": True,
            "no_practicebank_generation": True,
            "no_learner_state_write": True,
            "no_productive_use_for_receptive_preview": True,
        },
    }
    summary = {
        "task_id": "R7-M38_CrossSkillGrammarGateMatrixBuilderImplementation",
        "artifact_id": "cross_skill_grammar_gate_summary",
        "validation_status": "PASS_WITH_WARNINGS" if not records else "PASS",
        "grammar_rule_count": len(records),
        "skill_role_counts": {
            skill: dict(sorted(counts.items())) for skill, counts in skill_role_counts.items()
        },
        "receptive_preview_only_count": receptive_preview_count,
        "productive_blocked_count": blocked_productive_count,
        "cross_skill_gate_ready": bool(records),
        "notes": [
            "An empty matrix is valid for pipeline readiness but not sufficient for ReadingV1 grammar readiness.",
            "Preview-only grammar must remain blocked for speaking and writing production.",
        ],
        "next_short_step": "R7-M39_GrammarQueryIndexAndLookupContractImplementation",
        "stop_reason": "NONE",
    }
    return matrix, summary


def main():
    coverage_matrix = read_json(COVERAGE_MATRIX_PATH, default={"records": []})
    matrix, summary = build_cross_skill_matrix(coverage_matrix)
    write_json(CROSS_SKILL_MATRIX_PATH, matrix)
    write_json(SUMMARY_PATH, summary)
    print(f"Cross-skill grammar gate matrix build: {summary['validation_status']}")
    print(f"Grammar rules: {summary['grammar_rule_count']}")
    print(f"Cross-skill gate ready: {summary['cross_skill_gate_ready']}")


if __name__ == "__main__":
    main()
