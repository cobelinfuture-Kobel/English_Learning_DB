import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

SENTENCE_PATTERNS_PATH = BASE_DIR / "ulga" / "graph" / "sentence_patterns.json"
CONSTRAINTS_PATH = BASE_DIR / "ulga" / "graph" / "pattern_vocabulary_constraints.json"
QUERY_CONTRACT_PATH = BASE_DIR / "ulga" / "graph" / "pattern_vocabulary_candidate_query_contract.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "pattern_vocabulary_constraint_summary.json"

ALLOWED_CEFR = {"A1", "A2", "B1", "B2", "C1", "C2", None}
ALLOWED_THEME_MODES = {"hard_filter", "soft_filter", "none"}
ALLOWED_FREQUENCY_MODES = {"ranking_signal"}
ALLOWED_CEFR_GATE_MODES = {"max_cefr"}
ALLOWED_POS = {
    "noun",
    "phrase",
    "pronoun",
    "verb",
    "phrasal verb",
    "adjective",
    "adverb",
}
ALLOWED_COMPATIBILITY_CLASSES = {
    "common_noun_phrase",
    "singular_entity",
    "plural_entity",
    "countable_object",
    "mass_object",
    "descriptive_adjective",
    "action_verb",
    "activity_gerund",
    "location_entity",
    "person_entity",
    "time_expression",
    "generic_object",
    "generic_person",
}


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"FAIL: Could not load {path}: {exc}")
        return None


def fail(message):
    print(f"FAIL: {message}")
    return False


def validate_query_contract(contract):
    if not isinstance(contract, dict):
        return fail("candidate query contract must be an object.")
    if contract.get("contract_version") != "S7D_v1":
        return fail("candidate query contract_version must be S7D_v1.")
    limit_default = contract.get("limit_default")
    limit_max = contract.get("limit_max")
    if "limit_default" not in contract:
        return fail("candidate query contract missing limit_default.")
    if "limit_max" not in contract:
        return fail("candidate query contract missing limit_max.")
    if not isinstance(limit_default, int) or limit_default <= 0:
        return fail("candidate query contract limit_default must be a positive integer.")
    if not isinstance(limit_max, int) or limit_max <= 0:
        return fail("candidate query contract limit_max must be a positive integer.")
    if limit_default > limit_max:
        return fail("candidate query contract limit_default must be <= limit_max.")
    if limit_max > 200:
        return fail("candidate query contract limit_max must be <= 200.")
    for key in ["query_inputs", "gate_order", "ranking_signals", "output_shape", "materialization_policy"]:
        if key not in contract:
            return fail(f"candidate query contract missing {key}.")
    if contract["query_inputs"].get("pattern_id") != "required":
        return fail("candidate query contract must require pattern_id.")
    if contract["query_inputs"].get("slot_id") != "required":
        return fail("candidate query contract must require slot_id.")
    if "slot_constraint" not in contract["gate_order"]:
        return fail("candidate query contract gate_order must include slot_constraint.")
    if "frequency_band" not in contract["ranking_signals"]:
        return fail("candidate query contract ranking_signals must include frequency_band.")
    if contract["materialization_policy"].get("full_pattern_vocabulary_edges") is not False:
        return fail("candidate query contract must forbid full pattern-vocabulary edge materialization.")
    return True


def validate_slot_constraint(record, slot_constraint, top_level_limit_max):
    required = {
        "slot_id",
        "slot_label",
        "slot_type",
        "allowed_slot_types",
        "compatibility_classes",
        "allowed_pos",
        "cefr_gate",
        "theme_gate",
        "frequency_hint",
        "morphology_requirements",
        "candidate_query",
    }
    missing = required - set(slot_constraint)
    if missing:
        return fail(f"{record['pattern_node_id']} slot constraint missing fields: {sorted(missing)}")

    if not slot_constraint["slot_id"] or not slot_constraint["slot_type"]:
        return fail(f"{record['pattern_node_id']} slot constraint has empty slot_id or slot_type.")

    if slot_constraint["slot_type"] == "multi_type":
        allowed_slot_types = slot_constraint.get("allowed_slot_types")
        if not isinstance(allowed_slot_types, list) or len(allowed_slot_types) < 2:
            return fail(f"{record['pattern_node_id']} multi_type slot must have >=2 allowed_slot_types.")

    compatibility_classes = slot_constraint.get("compatibility_classes")
    if not isinstance(compatibility_classes, list) or not compatibility_classes:
        return fail(f"{record['pattern_node_id']} slot has empty compatibility_classes.")
    unknown_classes = set(compatibility_classes) - ALLOWED_COMPATIBILITY_CLASSES
    if unknown_classes:
        return fail(f"{record['pattern_node_id']} slot has unknown compatibility classes: {sorted(unknown_classes)}")

    allowed_pos = slot_constraint.get("allowed_pos")
    if not isinstance(allowed_pos, list) or not allowed_pos:
        return fail(f"{record['pattern_node_id']} slot has empty allowed_pos.")
    unknown_pos = set(allowed_pos) - ALLOWED_POS
    if unknown_pos:
        return fail(f"{record['pattern_node_id']} slot has unknown allowed_pos: {sorted(unknown_pos)}")

    cefr_gate = slot_constraint["cefr_gate"]
    if cefr_gate.get("mode") not in ALLOWED_CEFR_GATE_MODES:
        return fail(f"{record['pattern_node_id']} has invalid cefr_gate mode.")
    if cefr_gate.get("max_level") not in ALLOWED_CEFR:
        return fail(f"{record['pattern_node_id']} has invalid cefr max_level.")
    if cefr_gate.get("allow_plus_one_for_review") is not False:
        return fail(f"{record['pattern_node_id']} cefr gate must not allow plus-one review by default.")

    theme_gate = slot_constraint["theme_gate"]
    if theme_gate.get("mode") not in ALLOWED_THEME_MODES:
        return fail(f"{record['pattern_node_id']} has invalid theme_gate mode.")
    if not isinstance(theme_gate.get("allowed_theme_ids"), list):
        return fail(f"{record['pattern_node_id']} theme_gate allowed_theme_ids must be a list.")

    frequency_hint = slot_constraint["frequency_hint"]
    if frequency_hint.get("mode") not in ALLOWED_FREQUENCY_MODES:
        return fail(f"{record['pattern_node_id']} frequency_hint mode must be ranking_signal.")
    if frequency_hint.get("low_frequency_allowed") is not True:
        return fail(f"{record['pattern_node_id']} frequency_hint must allow low frequency items.")

    morphology = slot_constraint["morphology_requirements"]
    for key in ["requires_gerund_capable", "requires_plural_capable", "requires_countability"]:
        if not isinstance(morphology.get(key), bool):
            return fail(f"{record['pattern_node_id']} morphology flag {key} must be boolean.")

    candidate_query = slot_constraint["candidate_query"]
    slot_limit_default = candidate_query.get("limit_default")
    if not isinstance(slot_limit_default, int) or slot_limit_default <= 0:
        return fail(f"{record['pattern_node_id']} candidate_query limit_default must be a positive integer.")
    if slot_limit_default > top_level_limit_max:
        return fail(
            f"{record['pattern_node_id']} candidate_query limit_default exceeds top-level limit_max."
        )
    if candidate_query.get("frequency_mode") != "ranking_signal":
        return fail(f"{record['pattern_node_id']} candidate_query frequency_mode must be ranking_signal.")

    return True


def validate():
    print("Validating Pattern Vocabulary Constraint layer...")
    for path in [SENTENCE_PATTERNS_PATH, CONSTRAINTS_PATH, QUERY_CONTRACT_PATH, SUMMARY_PATH]:
        if not path.exists():
            return fail(f"required file does not exist: {path}")

    patterns = load_json(SENTENCE_PATTERNS_PATH)
    constraints = load_json(CONSTRAINTS_PATH)
    query_contract = load_json(QUERY_CONTRACT_PATH)
    summary = load_json(SUMMARY_PATH)

    if patterns is None or constraints is None or query_contract is None or summary is None:
        return False
    if not isinstance(constraints, list):
        return fail("pattern_vocabulary_constraints.json must contain a list.")
    if not validate_query_contract(query_contract):
        return False
    top_level_limit_max = query_contract["limit_max"]

    patterns_by_node_id = {node["id"]: node for node in patterns}
    active_pattern_ids = {
        node["id"]
        for node in patterns
        if node.get("metadata", {}).get("review_status") == "accepted"
        and node.get("metadata", {}).get("generator_allowed") is True
    }

    seen_pattern_node_ids = set()
    total_slot_constraints = 0
    for record in constraints:
        if not isinstance(record, dict):
            return fail("constraint record must be an object.")
        forbidden_edge_fields = {"source_node_id", "target_node_id", "edge_type"}
        if forbidden_edge_fields & set(record):
            return fail("constraint records must not be materialized graph edges.")
        if record.get("active") is not True:
            return fail("all emitted constraint records must be active.")

        pattern_node_id = record.get("pattern_node_id")
        if pattern_node_id not in patterns_by_node_id:
            return fail(f"unknown pattern_node_id in constraints: {pattern_node_id}")
        if pattern_node_id in seen_pattern_node_ids:
            return fail(f"duplicate constraint record for {pattern_node_id}")
        seen_pattern_node_ids.add(pattern_node_id)

        pattern = patterns_by_node_id[pattern_node_id]
        meta = pattern.get("metadata", {})
        if pattern_node_id not in active_pattern_ids:
            return fail(f"inactive pattern emitted as active constraint: {pattern_node_id}")
        if record.get("review_status") != "accepted" or record.get("generator_allowed") is not True:
            return fail(f"{pattern_node_id} must be accepted and generator_allowed.")
        if record.get("pattern_id") != pattern.get("authority_source", {}).get("source_record_id"):
            return fail(f"{pattern_node_id} pattern_id does not match source_record_id.")
        if record.get("canonical_pattern") != meta.get("canonical_pattern"):
            return fail(f"{pattern_node_id} canonical_pattern mismatch.")

        slot_constraints = record.get("slot_constraints")
        if not isinstance(slot_constraints, list) or not slot_constraints:
            return fail(f"{pattern_node_id} has no slot_constraints.")
        if len(slot_constraints) != len(meta.get("slots", [])):
            return fail(f"{pattern_node_id} slot_constraints count does not match pattern slots.")

        if meta.get("source") == "MANUAL_A1_CORE_PATTERN":
            for slot_constraint in slot_constraints:
                if slot_constraint["cefr_gate"].get("max_level") != "A1":
                    return fail(f"{pattern_node_id} manual A1 constraint max_cefr must be A1.")

        for slot_constraint in slot_constraints:
            if not validate_slot_constraint(record, slot_constraint, top_level_limit_max):
                return False
            total_slot_constraints += 1

    if seen_pattern_node_ids != active_pattern_ids:
        missing = sorted(active_pattern_ids - seen_pattern_node_ids)[:10]
        return fail(f"missing active constraints for accepted generator_allowed patterns: {missing}")

    if summary.get("active_constraint_count") != len(constraints):
        return fail("summary active_constraint_count does not match constraints length.")
    if summary.get("inactive_skipped_pattern_count") != len(patterns) - len(active_pattern_ids):
        return fail("summary inactive_skipped_pattern_count is incorrect.")
    if summary.get("slot_constraint_count") != total_slot_constraints:
        return fail("summary slot_constraint_count is incorrect.")
    if summary.get("full_pattern_vocabulary_edges_generated") is not False:
        return fail("summary must declare no full pattern-vocabulary edges generated.")

    print("Pattern Vocabulary Constraint validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
