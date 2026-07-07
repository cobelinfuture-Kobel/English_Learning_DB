import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

CROSS_SKILL_MATRIX_PATH = BASE_DIR / "ulga" / "graph" / "cross_skill_grammar_gate_matrix.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "cross_skill_grammar_gate_summary.json"

SKILLS = ["reading", "listening", "speaking", "writing"]
LEVEL_STAGES = ["A1", "A1+", "A2", "A2+", "B1", "B1+", "B2"]
GLOBAL_ROLES = ["focus", "recycle", "preview", "blocked", "maintenance", "not_applicable"]
REQUIRED_MATRIX_FIELDS = {
    "task_id",
    "artifact_id",
    "skills",
    "level_stages",
    "global_roles",
    "records",
    "scope_constraints",
}
REQUIRED_SUMMARY_FIELDS = {
    "task_id",
    "artifact_id",
    "validation_status",
    "grammar_rule_count",
    "skill_role_counts",
    "receptive_preview_only_count",
    "productive_blocked_count",
    "cross_skill_gate_ready",
    "notes",
    "next_short_step",
    "stop_reason",
}


def read_json(path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"FAIL: could not load {path}: {exc}")
        return None


def fail(message):
    print(f"FAIL: {message}")
    return False


def validate_shapes(matrix, summary):
    if not isinstance(matrix, dict):
        return fail("cross-skill matrix must be an object")
    if not isinstance(summary, dict):
        return fail("summary must be an object")
    missing_matrix = REQUIRED_MATRIX_FIELDS - set(matrix)
    if missing_matrix:
        return fail(f"cross-skill matrix missing fields: {sorted(missing_matrix)}")
    missing_summary = REQUIRED_SUMMARY_FIELDS - set(summary)
    if missing_summary:
        return fail(f"summary missing fields: {sorted(missing_summary)}")
    if matrix["task_id"] != "R7-M38_CrossSkillGrammarGateMatrixBuilderImplementation":
        return fail("matrix task_id mismatch")
    if summary["task_id"] != "R7-M38_CrossSkillGrammarGateMatrixBuilderImplementation":
        return fail("summary task_id mismatch")
    if matrix["skills"] != SKILLS:
        return fail("skills mismatch")
    if matrix["level_stages"] != LEVEL_STAGES:
        return fail("level_stages mismatch")
    if matrix["global_roles"] != GLOBAL_ROLES:
        return fail("global_roles mismatch")
    if summary["next_short_step"] != "R7-M39_GrammarQueryIndexAndLookupContractImplementation":
        return fail("summary next_short_step mismatch")
    if summary["stop_reason"] != "NONE":
        return fail("summary stop_reason must be NONE")
    return True


def validate_scope(matrix):
    scope = matrix["scope_constraints"]
    for key in [
        "no_runtime_implementation",
        "no_practicebank_generation",
        "no_learner_state_write",
        "no_productive_use_for_receptive_preview",
    ]:
        if scope.get(key) is not True:
            return fail(f"scope constraint must be true: {key}")
    return True


def validate_records(matrix, summary):
    records = matrix["records"]
    if not isinstance(records, list):
        return fail("records must be a list")
    if summary["grammar_rule_count"] != len(records):
        return fail("summary grammar_rule_count mismatch")
    receptive_preview_only_count = 0
    productive_blocked_count = 0
    skill_role_counts = {skill: {} for skill in SKILLS}

    for record in records:
        if not isinstance(record, dict):
            return fail("record must be an object")
        for key in [
            "grammar_id",
            "stage",
            "global_role",
            "skill_scope",
            "blocked_in",
            "receptive_preview_only",
            "productive_allowed",
        ]:
            if key not in record:
                return fail(f"record missing {key}")
        if record["global_role"] not in GLOBAL_ROLES:
            return fail(f"invalid global_role: {record['global_role']}")
        if record["stage"] and record["stage"] not in LEVEL_STAGES:
            return fail(f"invalid stage: {record['stage']}")
        skill_scope = record["skill_scope"]
        if set(skill_scope) != set(SKILLS):
            return fail(f"skill_scope must contain all skills for {record.get('grammar_id')}")
        for skill, scope in skill_scope.items():
            if "role" not in scope:
                return fail(f"skill scope missing role: {skill}")
            role = scope["role"]
            skill_role_counts[skill][role] = skill_role_counts[skill].get(role, 0) + 1
        if record["receptive_preview_only"]:
            receptive_preview_only_count += 1
            if skill_scope["speaking"]["role"] != "blocked" or skill_scope["writing"]["role"] != "blocked":
                return fail("receptive_preview_only grammar must be blocked for speaking and writing")
        if "speaking" in record["blocked_in"] or "writing" in record["blocked_in"]:
            productive_blocked_count += 1

    if summary["receptive_preview_only_count"] != receptive_preview_only_count:
        return fail("receptive_preview_only_count mismatch")
    if summary["productive_blocked_count"] != productive_blocked_count:
        return fail("productive_blocked_count mismatch")
    if summary["skill_role_counts"] != {skill: dict(sorted(counts.items())) for skill, counts in skill_role_counts.items()}:
        return fail("skill_role_counts mismatch")
    if summary["cross_skill_gate_ready"] != bool(records):
        return fail("cross_skill_gate_ready mismatch")
    return True


def validate():
    print("Validating Cross-Skill Grammar Gate Matrix...")
    for path in [CROSS_SKILL_MATRIX_PATH, SUMMARY_PATH]:
        if not path.exists():
            return fail(f"required file does not exist: {path}")
    matrix = read_json(CROSS_SKILL_MATRIX_PATH)
    summary = read_json(SUMMARY_PATH)
    if matrix is None or summary is None:
        return False
    if not validate_shapes(matrix, summary):
        return False
    if not validate_scope(matrix):
        return False
    if not validate_records(matrix, summary):
        return False
    print("Cross-Skill Grammar Gate Matrix validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
