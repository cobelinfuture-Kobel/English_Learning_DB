import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

QUERY_INDEX_PATH = BASE_DIR / "ulga" / "graph" / "grammar_query_index.json"
LOOKUP_CONTRACT_PATH = BASE_DIR / "ulga" / "contracts" / "grammar_lookup_contract.json"
VALIDATION_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_lookup_contract_validation_report.json"

LEVEL_STAGES = ["A1", "A1+", "A2", "A2+", "B1", "B1+", "B2"]
SKILLS = ["reading", "listening", "speaking", "writing"]
REQUIRED_CAPABILITIES = {
    "lookup_by_level",
    "lookup_by_skill",
    "lookup_by_grammar_id",
    "lookup_by_egp_row_id",
    "lookup_uncovered_egp_rules",
    "lookup_blocked_grammar_by_stage_skill",
    "lookup_cross_skill_roles",
    "lookup_receptive_preview_vs_productive_mastery",
    "no_learner_state_write",
}
REQUIRED_QUERY_INDEX_FIELDS = {
    "task_id",
    "artifact_id",
    "source_paths",
    "level_stages",
    "skills",
    "allowed_by_level_stage",
    "blocked_by_level_stage",
    "role_by_level_stage",
    "allowed_by_level_stage_skill",
    "blocked_by_level_stage_skill",
    "role_by_level_stage_skill",
    "by_grammar_id",
    "by_egp_row_id",
    "uncovered_by_egp_level",
    "scope_constraints",
}
REQUIRED_CONTRACT_FIELDS = {
    "task_id",
    "artifact_id",
    "contract_version",
    "query_index_path",
    "capabilities",
    "required_inputs",
    "required_outputs",
    "scope_constraints",
}
REQUIRED_REPORT_FIELDS = {
    "task_id",
    "artifact_id",
    "validation_status",
    "query_index_path",
    "lookup_contract_path",
    "grammar_id_count",
    "egp_row_index_count",
    "uncovered_egp_row_count",
    "capabilities",
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


def validate_shapes(query_index, contract, report):
    for name, payload, required in [
        ("query index", query_index, REQUIRED_QUERY_INDEX_FIELDS),
        ("lookup contract", contract, REQUIRED_CONTRACT_FIELDS),
        ("validation report", report, REQUIRED_REPORT_FIELDS),
    ]:
        if not isinstance(payload, dict):
            return fail(f"{name} must be an object")
        missing = required - set(payload)
        if missing:
            return fail(f"{name} missing fields: {sorted(missing)}")
    expected_task = "R7-M39_GrammarQueryIndexAndLookupContractImplementation"
    if query_index["task_id"] != expected_task:
        return fail("query index task_id mismatch")
    if contract["task_id"] != expected_task:
        return fail("contract task_id mismatch")
    if report["task_id"] != expected_task:
        return fail("report task_id mismatch")
    return True


def validate_capabilities(contract, report):
    capabilities = contract["capabilities"]
    if set(capabilities) != REQUIRED_CAPABILITIES:
        return fail("contract capabilities mismatch")
    for capability in REQUIRED_CAPABILITIES:
        if capabilities.get(capability) is not True:
            return fail(f"capability must be true: {capability}")
    if report["capabilities"] != capabilities:
        return fail("report capabilities do not match contract")
    return True


def validate_scope(query_index, contract):
    for payload_name, payload in [("query_index", query_index), ("contract", contract)]:
        scope = payload["scope_constraints"]
        for key in [
            "no_runtime_implementation",
            "no_practicebank_generation",
            "no_learner_state_write",
            "read_only_contract_for_downstream_systems",
        ]:
            if scope.get(key) is not True:
                return fail(f"{payload_name} scope constraint must be true: {key}")
    return True


def validate_level_and_skill_indexes(query_index):
    if query_index["level_stages"] != LEVEL_STAGES:
        return fail("level_stages mismatch")
    if query_index["skills"] != SKILLS:
        return fail("skills mismatch")
    for key in ["allowed_by_level_stage", "blocked_by_level_stage", "role_by_level_stage"]:
        if set(query_index[key]) != set(LEVEL_STAGES):
            return fail(f"{key} must contain all level stages")
    for key in ["allowed_by_level_stage_skill", "blocked_by_level_stage_skill", "role_by_level_stage_skill"]:
        if set(query_index[key]) != set(LEVEL_STAGES):
            return fail(f"{key} must contain all level stages")
        for stage in LEVEL_STAGES:
            if set(query_index[key][stage]) != set(SKILLS):
                return fail(f"{key}[{stage}] must contain all skills")
    return True


def validate_counts(query_index, report):
    if report["grammar_id_count"] != len(query_index["by_grammar_id"]):
        return fail("grammar_id_count mismatch")
    if report["egp_row_index_count"] != len(query_index["by_egp_row_id"]):
        return fail("egp_row_index_count mismatch")
    uncovered_count = sum(len(rows) for rows in query_index["uncovered_by_egp_level"].values())
    if report["uncovered_egp_row_count"] != uncovered_count:
        return fail("uncovered_egp_row_count mismatch")
    return True


def validate_next_step(report):
    if report["next_short_step"] != "R7-M40_GrammarEGPCoverageValidatorImplementation":
        return fail("next_short_step mismatch")
    if report["stop_reason"] != "NONE":
        return fail("stop_reason must be NONE")
    if report["validation_status"] not in {"PASS", "PASS_WITH_WARNINGS"}:
        return fail("validation_status must be PASS or PASS_WITH_WARNINGS")
    return True


def validate():
    print("Validating Grammar Lookup Contract...")
    for path in [QUERY_INDEX_PATH, LOOKUP_CONTRACT_PATH, VALIDATION_REPORT_PATH]:
        if not path.exists():
            return fail(f"required file does not exist: {path}")
    query_index = read_json(QUERY_INDEX_PATH)
    contract = read_json(LOOKUP_CONTRACT_PATH)
    report = read_json(VALIDATION_REPORT_PATH)
    if query_index is None or contract is None or report is None:
        return False
    if not validate_shapes(query_index, contract, report):
        return False
    if not validate_capabilities(contract, report):
        return False
    if not validate_scope(query_index, contract):
        return False
    if not validate_level_and_skill_indexes(query_index):
        return False
    if not validate_counts(query_index, report):
        return False
    if not validate_next_step(report):
        return False
    print("Grammar Lookup Contract validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
