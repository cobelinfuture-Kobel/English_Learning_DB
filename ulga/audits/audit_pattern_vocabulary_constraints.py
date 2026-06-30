import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

GRAPH_DIR = BASE_DIR / "ulga" / "graph"
REPORTS_DIR = BASE_DIR / "ulga" / "reports"
DOCS_DIR = BASE_DIR / "docs" / "ulga"
VOCAB_DIR = BASE_DIR / "vocabulary" / "json"
THEME_DIR = BASE_DIR / "themes"

CONSTRAINTS_PATH = GRAPH_DIR / "pattern_vocabulary_constraints.json"
CONTRACT_PATH = GRAPH_DIR / "pattern_vocabulary_candidate_query_contract.json"
PATTERNS_PATH = GRAPH_DIR / "sentence_patterns.json"
ULGA_PATTERN_NODES_PATH = GRAPH_DIR / "ulga_sentence_pattern_nodes.json"
VOCABULARY_PATH = VOCAB_DIR / "vocabulary.json"
FREQUENCY_MAPPING_PATH = BASE_DIR / "vocabulary" / "mapping" / "frequency_mapping.json"
THEME_VOCAB_MAPPING_PATH = THEME_DIR / "theme_vocab_mapping.json"
THEME_CATALOG_PATH = THEME_DIR / "theme_catalog.json"
SUMMARY_PATH = REPORTS_DIR / "pattern_vocabulary_constraint_summary.json"
IMPLEMENTATION_CLOSEOUT_PATH = DOCS_DIR / "ULGA_S7D_PATTERN_VOCABULARY_CONSTRAINT_IMPLEMENTATION_CLOSEOUT.md"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_pattern_vocabulary_constraints.py"

AUDIT_JSON_PATH = REPORTS_DIR / "pattern_vocabulary_constraint_qa_audit.json"
AUDIT_DOC_PATH = DOCS_DIR / "ULGA_S7DI_PATTERN_VOCABULARY_CONSTRAINT_QA_AUDIT.md"

ALLOWED_SLOT_TYPES = {
    "noun_phrase",
    "noun",
    "plural_noun",
    "singular_noun",
    "adjective",
    "gerund",
    "verb",
    "base_verb",
    "verb_phrase",
    "location",
    "person",
    "activity",
    "object",
    "place",
    "time_phrase",
    "sth",
    "sb",
    "multi_type",
    "proper_noun",
    "name",
    "verb_stem",
    "verb_gerund",
    "verb_infinitive",
    "infinitive",
    "time",
    "noun_phrase_1",
    "noun_phrase_2",
}
ALLOWED_COMPATIBILITY_CLASSES = {
    "common_noun_phrase",
    "activity_gerund",
    "action_verb",
    "descriptive_adjective",
    "singular_entity",
    "plural_entity",
    "person_entity",
    "location_entity",
    "generic_object",
    "generic_person",
    "time_expression",
}
ALLOWED_POS = {"noun", "verb", "adjective", "adverb", "phrase", "pronoun", "phrasal verb"}
CEFR_ORDER = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
EXPECTED_GATE_ORDER = [
    "review_status",
    "generator_allowed",
    "slot_constraint",
    "cefr_gate",
    "pos_gate",
    "morphology_gate",
]


def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def run_command(command):
    try:
        result = subprocess.run(
            command,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=180,
        )
        output = (result.stdout + result.stderr).strip()
        return {
            "command": " ".join(command),
            "returncode": result.returncode,
            "status": "PASS" if result.returncode == 0 else "FAIL",
            "output": output,
        }
    except subprocess.TimeoutExpired as exc:
        output = ((exc.stdout or "") + (exc.stderr or "")).strip()
        return {
            "command": " ".join(command),
            "returncode": None,
            "status": "TIMEOUT",
            "output": output or "Command timed out after 180 seconds.",
        }


def safe_ratio(part, whole):
    return (part / whole) if whole else 0.0


def pct(part, whole):
    return safe_ratio(part, whole) * 100


def short_counter(counter_obj, limit=20):
    return [
        {"value": key, "count": value}
        for key, value in counter_obj.most_common(limit)
    ]


def build_markdown(report):
    basic = report["basic_integrity"]
    slot = report["slot_coverage_analysis"]
    compat = report["compatibility_class_analysis"]
    pos = report["allowed_pos_analysis"]
    cefr = report["cefr_gate_audit"]
    theme = report["theme_gate_audit"]
    freq = report["frequency_hint_audit"]
    contract = report["candidate_query_contract_audit"]
    risk = report["risk_findings"]
    readiness = report["s7e_readiness_assessment"]
    validator = report["validator_result"]
    pytest_result = report["pytest_result"]

    lines = [
        "# ULGA-S7DI Pattern Vocabulary Constraint QA Audit",
        "",
        "## 1. Executive Summary",
        "",
        (
            f"The S7D Pattern Vocabulary Constraint layer contains "
            f"**{basic['active_constraints']}** active constraints over "
            f"**{basic['total_slot_constraints']}** slot constraints from "
            f"**{basic['total_patterns']}** sentence patterns. "
            f"Validator status is **{validator['status']}** and pytest status is "
            f"**{pytest_result['status']}**."
        ),
        "",
        f"**Final Verdict**: **{report['final_verdict']}**",
        "",
        "## 2. Files Created",
        "",
        "- `ulga/audits/audit_pattern_vocabulary_constraints.py`",
        "- `ulga/reports/pattern_vocabulary_constraint_qa_audit.json`",
        "- `docs/ulga/ULGA_S7DI_PATTERN_VOCABULARY_CONSTRAINT_QA_AUDIT.md`",
        "",
        "## 3. Files Modified",
        "",
    ]
    for item in report["files_modified"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
        "",
        "## 4. Files Inspected",
        "",
        ]
    )
    for item in report["files_inspected"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "## 5. Basic Integrity Metrics",
            "",
            f"- Total patterns: `{basic['total_patterns']}`",
            f"- Active constraints: `{basic['active_constraints']}`",
            f"- Inactive / skipped patterns: `{basic['inactive_constraints']}`",
            f"- Total slot constraints: `{basic['total_slot_constraints']}`",
            f"- Accepted patterns: `{basic['accepted_patterns']}`",
            f"- Needs review / inactive patterns: `{basic['needs_review_patterns']}`",
            f"- Active constraint ratio: `{basic['active_constraint_ratio']:.2f}%`",
            f"- Inactive constraint ratio: `{basic['inactive_constraint_ratio']:.2f}%`",
            "",
            "## 6. Slot Coverage Analysis",
            "",
            f"- Unique slot types in active constraints: `{slot['unique_slot_type_count']}`",
            f"- Empty slot count: `{slot['empty_slot_count']}`",
            f"- Unknown slot count: `{slot['unknown_slot_count']}`",
            f"- Multi-type coverage count: `{slot['multi_type_coverage_count']}`",
            f"- Multi-type coverage ratio: `{slot['multi_type_coverage_ratio']:.2f}%`",
            "",
            "### Top 20 Slot Labels",
            "",
            "```json",
            json.dumps(slot["top_20_slot_labels"], indent=2, ensure_ascii=False),
            "```",
            "",
            "### Slot Type Distribution",
            "",
            "```json",
            json.dumps(slot["slot_type_distribution"], indent=2, ensure_ascii=False),
            "```",
            "",
            "## 7. Compatibility Class Analysis",
            "",
            f"- Empty compatibility_classes count: `{compat['empty_compatibility_classes_count']}`",
            f"- Unknown compatibility_classes count: `{compat['unknown_compatibility_classes_count']}`",
            f"- Unique compatibility classes used: `{compat['unique_compatibility_class_count']}`",
            "",
            "```json",
            json.dumps(compat["compatibility_class_distribution"], indent=2, ensure_ascii=False),
            "```",
            "",
            "## 8. Allowed POS Analysis",
            "",
            f"- Empty allowed_pos count: `{pos['empty_allowed_pos_count']}`",
            f"- Suspicious combinations count: `{pos['suspicious_combination_count']}`",
            "",
            "```json",
            json.dumps(pos["allowed_pos_distribution"], indent=2, ensure_ascii=False),
            "```",
            "",
            "## 9. CEFR Gate Audit",
            "",
            f"- Null CEFR gate count: `{cefr['null_cefr_gate_count']}`",
            f"- Invalid CEFR gate count: `{cefr['invalid_cefr_gate_count']}`",
            f"- Manual A1 patterns with non-A1 gate: `{cefr['manual_a1_non_a1_gate_count']}`",
            f"- Plus-one allowance enabled count: `{cefr['plus_one_allowance_true_count']}`",
            "",
            "```json",
            json.dumps(cefr["cefr_gate_distribution"], indent=2, ensure_ascii=False),
            "```",
            "",
            "## 10. Theme Gate Audit",
            "",
            f"- Invalid theme mode count: `{theme['invalid_theme_mode_count']}`",
            f"- Manual A1 hard_filter compliance: `{theme['manual_a1_hard_filter_compliance']}`",
            f"- Chunk-derived soft_filter compliance: `{theme['chunk_derived_soft_filter_compliance']}`",
            "",
            "```json",
            json.dumps(theme["theme_mode_distribution"], indent=2, ensure_ascii=False),
            "```",
            "",
            "## 11. Frequency Hint Audit",
            "",
            f"- Invalid frequency mode count: `{freq['invalid_frequency_mode_count']}`",
            f"- Hard block count: `{freq['hard_block_count']}`",
            f"- Low frequency allowed false count: `{freq['low_frequency_allowed_false_count']}`",
            "",
            "```json",
            json.dumps(freq["frequency_mode_distribution"], indent=2, ensure_ascii=False),
            "```",
            "",
            "## 12. Candidate Query Contract Audit",
            "",
            f"- Contract version: `{contract['contract_version']}`",
            f"- Gate order matches design: `{contract['gate_order_matches_expected']}`",
            f"- Ranking signals count: `{contract['ranking_signal_count']}`",
            f"- Output shape key count: `{contract['output_shape_key_count']}`",
            f"- Contract-level limit_default present: `{contract['limit_default_present']}`",
            f"- Contract-level limit_max present: `{contract['limit_max_present']}`",
            f"- Contract-level limit_default valid: `{contract['limit_default_valid']}`",
            f"- Contract-level limit_max valid: `{contract['limit_max_valid']}`",
            f"- Contract-level limit_default <= limit_max: `{contract['limit_default_le_limit_max']}`",
            f"- Candidate limit > 200 count: `{contract['candidate_limit_gt_200_count']}`",
            f"- Slot limit > top-level limit_max count: `{contract['slot_limit_gt_top_level_limit_max_count']}`",
            "",
            "```json",
            json.dumps(contract, indent=2, ensure_ascii=False),
            "```",
            "",
            "## 13. Risk Findings",
            "",
        ]
    )
    for item in risk["findings"]:
        lines.append(f"- [{item['severity']}] {item['code']}: {item['message']}")
    lines.extend(
        [
            "",
            "## 14. S7E Readiness Assessment",
            "",
            "```json",
            json.dumps(readiness, indent=2, ensure_ascii=False),
            "```",
            "",
            "## 15. Validator Result",
            "",
            "```text",
            validator["output"] or "(no output)",
            "```",
            "",
            "## 16. Pytest Result",
            "",
            "```text",
            pytest_result["output"] or "(no output)",
            "```",
            "",
            "## 17. Known Warnings",
            "",
        ]
    )
    for warning in report["known_warnings"]:
        lines.append(f"- {warning}")
    lines.extend(
        [
            "",
            "## 18. Recommended Next Task",
            "",
            report["recommended_next_task"],
            "",
            "## 19. Final Verdict",
            "",
            report["final_verdict"],
            "",
        ]
    )
    return "\n".join(lines)


def main():
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    constraints = read_json(CONSTRAINTS_PATH)
    contract = read_json(CONTRACT_PATH)
    patterns = read_json(PATTERNS_PATH)
    summary = read_json(SUMMARY_PATH)
    vocabulary = read_json(VOCABULARY_PATH)
    frequency_mapping = read_json(FREQUENCY_MAPPING_PATH)
    theme_vocab_mapping = read_json(THEME_VOCAB_MAPPING_PATH)
    theme_catalog = read_json(THEME_CATALOG_PATH)
    ulga_pattern_nodes = read_json(ULGA_PATTERN_NODES_PATH)

    validator_result = run_command([sys.executable, str(VALIDATOR_PATH)])
    pytest_result = run_command([sys.executable, "-m", "pytest", "tests/ulga/", "-q"])

    patterns_by_id = {pattern["id"]: pattern for pattern in patterns}
    active_pattern_ids = {
        pattern["id"]
        for pattern in patterns
        if pattern.get("metadata", {}).get("review_status") == "accepted"
        and pattern.get("metadata", {}).get("generator_allowed") is True
    }
    constraint_pattern_ids = {record["pattern_node_id"] for record in constraints}

    slot_type_counter = Counter()
    slot_label_counter = Counter()
    compatibility_counter = Counter()
    allowed_pos_counter = Counter()
    cefr_gate_counter = Counter()
    theme_mode_counter = Counter()
    frequency_mode_counter = Counter()
    theme_ref_count_counter = Counter()

    empty_slot_count = 0
    unknown_slot_count = 0
    empty_compatibility_count = 0
    unknown_compatibility_count = 0
    empty_allowed_pos_count = 0
    suspicious_combinations = []
    null_cefr_gate_count = 0
    invalid_cefr_gate_count = 0
    plus_one_allowance_true_count = 0
    invalid_theme_mode_count = 0
    invalid_frequency_mode_count = 0
    low_frequency_allowed_false_count = 0
    hard_block_count = 0
    active_constraint_not_accepted = []
    active_constraint_generator_blocked = []
    duplicate_slot_constraint_ids = []
    malformed_candidate_query_records = []
    slot_limit_gt_top_level_limit_max_records = []

    manual_a1_total = 0
    manual_a1_slot_expected = 0
    manual_a1_hard_filter_ok = 0
    manual_a1_non_a1_gate_count = 0
    chunk_derived_total = 0
    chunk_derived_slot_expected = 0
    chunk_derived_soft_filter_ok = 0

    seen_slot_constraint_ids = set()
    multi_type_examples = []
    contract_limit_default_present = "limit_default" in contract
    contract_limit_max_present = "limit_max" in contract
    contract_limit_default_value = contract.get("limit_default")
    contract_limit_max_value = contract.get("limit_max")
    contract_limit_default_valid = isinstance(contract_limit_default_value, int) and contract_limit_default_value > 0
    contract_limit_max_valid = (
        isinstance(contract_limit_max_value, int)
        and contract_limit_max_value > 0
        and contract_limit_max_value <= 200
    )
    contract_limit_default_le_limit_max = (
        contract_limit_default_valid
        and contract_limit_max_valid
        and contract_limit_default_value <= contract_limit_max_value
    )

    for record in constraints:
        pattern = patterns_by_id.get(record["pattern_node_id"], {})
        meta = pattern.get("metadata", {})
        slots = record.get("slot_constraints", [])
        if record.get("review_status") != "accepted":
            active_constraint_not_accepted.append(record["pattern_node_id"])
        if record.get("generator_allowed") is not True:
            active_constraint_generator_blocked.append(record["pattern_node_id"])

        if record.get("source") == "MANUAL_A1_CORE_PATTERN":
            manual_a1_total += 1
            manual_a1_slot_expected += len(slots)
        if record.get("source") == "CHUNK_GRAMMAR_METADATA_DERIVED":
            chunk_derived_total += 1
            chunk_derived_slot_expected += len(slots)

        for slot in slots:
            composite_slot_id = f"{record['pattern_node_id']}::{slot.get('slot_id')}"
            if composite_slot_id in seen_slot_constraint_ids:
                duplicate_slot_constraint_ids.append(composite_slot_id)
            seen_slot_constraint_ids.add(composite_slot_id)

            slot_type = slot.get("slot_type")
            slot_label = slot.get("slot_label")
            compatibility_classes = slot.get("compatibility_classes") or []
            allowed_pos = slot.get("allowed_pos") or []
            cefr_gate = slot.get("cefr_gate", {})
            theme_gate = slot.get("theme_gate", {})
            frequency_hint = slot.get("frequency_hint", {})
            candidate_query = slot.get("candidate_query", {})

            if not slot.get("slot_id") or not slot_type:
                empty_slot_count += 1

            slot_type_counter[slot_type] += 1
            slot_label_counter[slot_label] += 1
            cefr_gate_counter[cefr_gate.get("max_level")] += 1
            theme_mode_counter[theme_gate.get("mode")] += 1
            frequency_mode_counter[frequency_hint.get("mode")] += 1
            theme_ref_count_counter[len(theme_gate.get("allowed_theme_ids", []))] += 1

            if slot_type not in ALLOWED_SLOT_TYPES:
                unknown_slot_count += 1

            if slot_type == "multi_type":
                multi_type_examples.append(
                    {
                        "pattern_node_id": record["pattern_node_id"],
                        "canonical_pattern": record.get("canonical_pattern"),
                        "allowed_slot_types": slot.get("allowed_slot_types", []),
                    }
                )

            if not compatibility_classes:
                empty_compatibility_count += 1
            for value in compatibility_classes:
                compatibility_counter[value] += 1
                if value not in ALLOWED_COMPATIBILITY_CLASSES:
                    unknown_compatibility_count += 1

            if not allowed_pos:
                empty_allowed_pos_count += 1
            for value in allowed_pos:
                allowed_pos_counter[value] += 1

            if slot_type == "location" and "verb" in allowed_pos:
                suspicious_combinations.append(
                    {
                        "pattern_node_id": record["pattern_node_id"],
                        "canonical_pattern": record.get("canonical_pattern"),
                        "slot_id": slot.get("slot_id"),
                        "combination": "location+verb",
                    }
                )
            if slot_type == "person" and "adjective" in allowed_pos:
                suspicious_combinations.append(
                    {
                        "pattern_node_id": record["pattern_node_id"],
                        "canonical_pattern": record.get("canonical_pattern"),
                        "slot_id": slot.get("slot_id"),
                        "combination": "person+adjective",
                    }
                )

            max_level = cefr_gate.get("max_level")
            if max_level is None:
                null_cefr_gate_count += 1
            elif max_level not in CEFR_ORDER:
                invalid_cefr_gate_count += 1
            if cefr_gate.get("allow_plus_one_for_review") is True:
                plus_one_allowance_true_count += 1
            if record.get("source") == "MANUAL_A1_CORE_PATTERN" and max_level != "A1":
                manual_a1_non_a1_gate_count += 1

            if theme_gate.get("mode") not in {"hard_filter", "soft_filter", "none"}:
                invalid_theme_mode_count += 1
            if frequency_hint.get("mode") != "ranking_signal":
                invalid_frequency_mode_count += 1
            if frequency_hint.get("low_frequency_allowed") is False:
                low_frequency_allowed_false_count += 1
            if candidate_query.get("frequency_mode") == "hard_block":
                hard_block_count += 1

            if record.get("source") == "MANUAL_A1_CORE_PATTERN":
                if theme_gate.get("mode") == "hard_filter" and theme_gate.get("allowed_theme_ids"):
                    manual_a1_hard_filter_ok += 1
            if record.get("source") == "CHUNK_GRAMMAR_METADATA_DERIVED":
                if theme_gate.get("mode") == "soft_filter":
                    chunk_derived_soft_filter_ok += 1

            limit_default = candidate_query.get("limit_default")
            if not isinstance(limit_default, int) or limit_default <= 0:
                malformed_candidate_query_records.append(
                    {
                        "pattern_node_id": record["pattern_node_id"],
                        "slot_id": slot.get("slot_id"),
                        "issue": "missing_or_invalid_limit_default",
                    }
                )
            elif limit_default > 200:
                malformed_candidate_query_records.append(
                    {
                        "pattern_node_id": record["pattern_node_id"],
                        "slot_id": slot.get("slot_id"),
                        "issue": "limit_default_gt_200",
                        "value": limit_default,
                    }
                )
            if contract_limit_max_present and isinstance(contract_limit_max_value, int) and limit_default > contract_limit_max_value:
                slot_limit_gt_top_level_limit_max_records.append(
                    {
                        "pattern_node_id": record["pattern_node_id"],
                        "slot_id": slot.get("slot_id"),
                        "limit_default": limit_default,
                        "top_level_limit_max": contract_limit_max_value,
                    }
                )

    missing_active_constraints = sorted(active_pattern_ids - constraint_pattern_ids)
    unexpected_active_constraints = sorted(constraint_pattern_ids - active_pattern_ids)
    accepted_patterns = len(active_pattern_ids)
    total_patterns = len(patterns)
    inactive_patterns = total_patterns - accepted_patterns
    total_slot_constraints = sum(len(record.get("slot_constraints", [])) for record in constraints)

    candidate_limit_gt_200_count = sum(
        1 for row in malformed_candidate_query_records if row["issue"] == "limit_default_gt_200"
    )
    malformed_candidate_query_count = len(malformed_candidate_query_records)

    risk_findings = []

    def add_finding(severity, code, message):
        risk_findings.append({"severity": severity, "code": code, "message": message})

    if missing_active_constraints:
        add_finding(
            "BLOCKED",
            "active_constraint_missing_for_accepted_pattern",
            f"{len(missing_active_constraints)} accepted generator-allowed patterns are missing active constraints.",
        )
    if unexpected_active_constraints:
        add_finding(
            "BLOCKED",
            "unexpected_active_constraint",
            f"{len(unexpected_active_constraints)} active constraints do not map back to accepted generator-allowed patterns.",
        )
    if active_constraint_not_accepted:
        add_finding(
            "BLOCKED",
            "active_constraint_not_accepted",
            f"{len(active_constraint_not_accepted)} active constraints are not marked accepted.",
        )
    if active_constraint_generator_blocked:
        add_finding(
            "BLOCKED",
            "active_constraint_generator_blocked",
            f"{len(active_constraint_generator_blocked)} active constraints are marked generator_allowed=false.",
        )
    if unknown_slot_count:
        add_finding(
            "BLOCKED",
            "unknown_slot_type",
            f"{unknown_slot_count} slot constraints use unknown slot types.",
        )
    if empty_compatibility_count:
        add_finding(
            "BLOCKED",
            "empty_compatibility_classes",
            f"{empty_compatibility_count} slot constraints have empty compatibility_classes.",
        )
    if empty_allowed_pos_count:
        add_finding(
            "BLOCKED",
            "empty_allowed_pos",
            f"{empty_allowed_pos_count} slot constraints have empty allowed_pos.",
        )
    if invalid_cefr_gate_count or null_cefr_gate_count:
        add_finding(
            "BLOCKED",
            "invalid_cefr_gate",
            f"{invalid_cefr_gate_count + null_cefr_gate_count} slot constraints have invalid or null CEFR gates.",
        )
    if invalid_theme_mode_count:
        add_finding(
            "BLOCKED",
            "invalid_theme_mode",
            f"{invalid_theme_mode_count} slot constraints have invalid theme modes.",
        )
    if invalid_frequency_mode_count:
        add_finding(
            "BLOCKED",
            "invalid_frequency_mode",
            f"{invalid_frequency_mode_count} slot constraints have invalid frequency modes.",
        )
    if duplicate_slot_constraint_ids:
        add_finding(
            "BLOCKED",
            "duplicate_slot_constraint_id",
            f"{len(duplicate_slot_constraint_ids)} duplicate composite slot constraint ids were detected.",
        )
    if malformed_candidate_query_count:
        add_finding(
            "BLOCKED",
            "candidate_query_malformed",
            f"{malformed_candidate_query_count} slot constraints have malformed candidate_query payloads.",
        )
    if not contract_limit_default_present or not contract_limit_default_valid:
        add_finding(
            "BLOCKED",
            "contract_limit_default_invalid",
            "The top-level candidate query contract must publish a positive integer limit_default.",
        )
    if not contract_limit_max_present or not contract_limit_max_valid:
        add_finding(
            "BLOCKED",
            "contract_limit_max_invalid",
            "The top-level candidate query contract must publish a positive integer limit_max <= 200.",
        )
    if contract_limit_default_present and contract_limit_max_present and not contract_limit_default_le_limit_max:
        add_finding(
            "BLOCKED",
            "contract_limit_order_invalid",
            "The top-level candidate query contract must satisfy limit_default <= limit_max.",
        )
    if slot_limit_gt_top_level_limit_max_records:
        add_finding(
            "BLOCKED",
            "slot_limit_exceeds_top_level_limit_max",
            (
                f"{len(slot_limit_gt_top_level_limit_max_records)} slot constraints declare limit_default "
                "greater than the top-level limit_max."
            ),
        )
    if validator_result["status"] != "PASS":
        add_finding("BLOCKED", "validator_failed", "Pattern vocabulary constraint validator did not pass.")
    if pytest_result["status"] != "PASS":
        add_finding("BLOCKED", "pytest_failed", "ULGA pytest suite did not pass.")

    used_expected_slot_types = {
        "noun_phrase",
        "noun",
        "plural_noun",
        "singular_noun",
        "adjective",
        "gerund",
        "verb",
        "base_verb",
        "verb_phrase",
        "location",
        "person",
        "activity",
        "object",
        "place",
        "time_phrase",
        "sth",
        "sb",
        "multi_type",
    }
    missing_slot_coverage = sorted(used_expected_slot_types - set(slot_type_counter))
    if missing_slot_coverage:
        add_finding(
            "WARNING",
            "slot_type_coverage_gap",
            (
                f"Active constraints do not yet exercise {len(missing_slot_coverage)} design-scan slot types: "
                f"{', '.join(missing_slot_coverage[:10])}"
            ),
        )
    if suspicious_combinations:
        add_finding(
            "WARNING",
            "suspicious_allowed_pos_combinations",
            f"{len(suspicious_combinations)} suspicious slot_type/allowed_pos combinations were detected.",
        )

    known_warnings = [
        (
            "Coverage remains narrow for several design-scan slot types and compatibility classes; "
            "this is a corpus coverage issue, not a structural S7D break."
        ),
        (
            "Theme hard_filter coverage is limited to manual A1 patterns; chunk-derived patterns remain "
            "soft-filter only and depend on downstream theme linkage quality."
        ),
    ]

    blocked_count = sum(1 for item in risk_findings if item["severity"] == "BLOCKED")
    warning_count = sum(1 for item in risk_findings if item["severity"] == "WARNING")

    if blocked_count:
        final_verdict = "BLOCKED"
    elif warning_count:
        final_verdict = "WARNING_ACCEPTED"
    else:
        final_verdict = "PASS"

    readiness = {
        "status": final_verdict,
        "criteria": {
            "active_constraints_present": not missing_active_constraints and not unexpected_active_constraints,
            "slot_coverage_valid": unknown_slot_count == 0 and empty_slot_count == 0,
            "cefr_gate_valid": invalid_cefr_gate_count == 0 and null_cefr_gate_count == 0 and plus_one_allowance_true_count == 0,
            "theme_mode_valid": invalid_theme_mode_count == 0,
            "frequency_ranking_valid": invalid_frequency_mode_count == 0 and hard_block_count == 0,
            "candidate_query_contract_valid": (
                malformed_candidate_query_count == 0
                and contract_limit_default_valid
                and contract_limit_max_valid
                and contract_limit_default_le_limit_max
                and len(slot_limit_gt_top_level_limit_max_records) == 0
            ),
            "validator_pass": validator_result["status"] == "PASS",
            "pytest_pass": pytest_result["status"] == "PASS",
        },
        "warnings": [item["message"] for item in risk_findings if item["severity"] == "WARNING"],
        "blocked_reasons": [item["message"] for item in risk_findings if item["severity"] == "BLOCKED"],
    }

    report = {
        "audit_stage": "ULGA-S7DI",
        "audit_timestamp": timestamp,
        "files_created": [
            "ulga/audits/audit_pattern_vocabulary_constraints.py",
            "ulga/reports/pattern_vocabulary_constraint_qa_audit.json",
            "docs/ulga/ULGA_S7DI_PATTERN_VOCABULARY_CONSTRAINT_QA_AUDIT.md",
        ],
        "files_modified": [
            "ulga/builders/build_pattern_vocabulary_constraints.py",
            "ulga/validators/validate_pattern_vocabulary_constraints.py",
            "tests/ulga/test_pattern_vocabulary_constraints.py",
            "ulga/audits/audit_pattern_vocabulary_constraints.py",
            "ulga/graph/pattern_vocabulary_candidate_query_contract.json",
            "ulga/reports/pattern_vocabulary_constraint_summary.json",
            "ulga/reports/pattern_vocabulary_constraint_qa_audit.json",
            "docs/ulga/ULGA_S7DI_PATTERN_VOCABULARY_CONSTRAINT_QA_AUDIT.md",
        ],
        "files_inspected": [
            str(CONSTRAINTS_PATH.relative_to(BASE_DIR)).replace("\\", "/"),
            str(CONTRACT_PATH.relative_to(BASE_DIR)).replace("\\", "/"),
            str(SUMMARY_PATH.relative_to(BASE_DIR)).replace("\\", "/"),
            str(PATTERNS_PATH.relative_to(BASE_DIR)).replace("\\", "/"),
            str(ULGA_PATTERN_NODES_PATH.relative_to(BASE_DIR)).replace("\\", "/"),
            str(VOCABULARY_PATH.relative_to(BASE_DIR)).replace("\\", "/"),
            str(FREQUENCY_MAPPING_PATH.relative_to(BASE_DIR)).replace("\\", "/"),
            str(THEME_VOCAB_MAPPING_PATH.relative_to(BASE_DIR)).replace("\\", "/"),
            str(THEME_CATALOG_PATH.relative_to(BASE_DIR)).replace("\\", "/"),
            str(VALIDATOR_PATH.relative_to(BASE_DIR)).replace("\\", "/"),
            "tests/ulga/test_pattern_vocabulary_constraints.py",
            str(IMPLEMENTATION_CLOSEOUT_PATH.relative_to(BASE_DIR)).replace("\\", "/"),
        ],
        "supporting_dataset_counts": {
            "vocabulary_count": len(vocabulary),
            "frequency_mapping_count": len(frequency_mapping),
            "theme_vocab_mapping_count": len(theme_vocab_mapping),
            "theme_catalog_count": len(theme_catalog),
            "ulga_sentence_pattern_node_wrapper_count": ulga_pattern_nodes.get("node_count"),
        },
        "basic_integrity": {
            "total_patterns": total_patterns,
            "active_constraints": len(constraints),
            "inactive_constraints": inactive_patterns,
            "total_slot_constraints": total_slot_constraints,
            "accepted_patterns": accepted_patterns,
            "needs_review_patterns": inactive_patterns,
            "active_constraint_ratio": pct(len(constraints), total_patterns),
            "inactive_constraint_ratio": pct(inactive_patterns, total_patterns),
            "missing_active_constraint_count": len(missing_active_constraints),
            "unexpected_active_constraint_count": len(unexpected_active_constraints),
            "summary_matches_constraints_length": summary.get("active_constraint_count") == len(constraints),
            "summary_matches_slot_constraint_count": summary.get("slot_constraint_count") == total_slot_constraints,
        },
        "slot_coverage_analysis": {
            "slot_type_distribution": dict(slot_type_counter),
            "top_20_slot_labels": short_counter(slot_label_counter, limit=20),
            "multi_type_coverage_count": slot_type_counter.get("multi_type", 0),
            "multi_type_coverage_ratio": pct(slot_type_counter.get("multi_type", 0), total_slot_constraints),
            "multi_type_examples": multi_type_examples,
            "empty_slot_count": empty_slot_count,
            "unknown_slot_count": unknown_slot_count,
            "missing_design_slot_coverage": missing_slot_coverage,
            "unique_slot_type_count": len(slot_type_counter),
        },
        "compatibility_class_analysis": {
            "compatibility_class_distribution": dict(compatibility_counter),
            "empty_compatibility_classes_count": empty_compatibility_count,
            "unknown_compatibility_classes_count": unknown_compatibility_count,
            "unique_compatibility_class_count": len(compatibility_counter),
            "missing_design_compatibility_classes": sorted(ALLOWED_COMPATIBILITY_CLASSES - set(compatibility_counter)),
        },
        "allowed_pos_analysis": {
            "allowed_pos_distribution": dict(allowed_pos_counter),
            "empty_allowed_pos_count": empty_allowed_pos_count,
            "unknown_allowed_pos_count": sum(1 for key in allowed_pos_counter if key not in ALLOWED_POS),
            "suspicious_combination_count": len(suspicious_combinations),
            "suspicious_combinations": suspicious_combinations[:20],
        },
        "cefr_gate_audit": {
            "cefr_gate_distribution": dict(cefr_gate_counter),
            "null_cefr_gate_count": null_cefr_gate_count,
            "invalid_cefr_gate_count": invalid_cefr_gate_count,
            "manual_a1_pattern_count": manual_a1_total,
            "manual_a1_non_a1_gate_count": manual_a1_non_a1_gate_count,
            "plus_one_allowance_true_count": plus_one_allowance_true_count,
        },
        "theme_gate_audit": {
            "theme_mode_distribution": dict(theme_mode_counter),
            "invalid_theme_mode_count": invalid_theme_mode_count,
            "manual_a1_hard_filter_ok_count": manual_a1_hard_filter_ok,
            "manual_a1_hard_filter_expected_slot_count": manual_a1_slot_expected,
            "manual_a1_hard_filter_compliance": (
                manual_a1_non_a1_gate_count == 0 and manual_a1_hard_filter_ok == manual_a1_slot_expected
            ),
            "chunk_derived_pattern_count": chunk_derived_total,
            "chunk_derived_soft_filter_ok_count": chunk_derived_soft_filter_ok,
            "chunk_derived_soft_filter_compliance": chunk_derived_soft_filter_ok == chunk_derived_slot_expected,
            "theme_ref_count_distribution": dict(theme_ref_count_counter),
        },
        "frequency_hint_audit": {
            "frequency_mode_distribution": dict(frequency_mode_counter),
            "invalid_frequency_mode_count": invalid_frequency_mode_count,
            "hard_block_count": hard_block_count,
            "low_frequency_allowed_false_count": low_frequency_allowed_false_count,
        },
        "candidate_query_contract_audit": {
            "contract_version": contract.get("contract_version"),
            "gate_order": contract.get("gate_order", []),
            "gate_order_matches_expected": contract.get("gate_order") == EXPECTED_GATE_ORDER,
            "ranking_signals": contract.get("ranking_signals", []),
            "ranking_signal_count": len(contract.get("ranking_signals", [])),
            "output_shape_keys": sorted((contract.get("output_shape") or {}).keys()),
            "output_shape_key_count": len((contract.get("output_shape") or {}).keys()),
            "materialization_policy": contract.get("materialization_policy", {}),
            "limit_default_present": contract_limit_default_present,
            "limit_default_value": contract_limit_default_value,
            "limit_default_valid": contract_limit_default_valid,
            "limit_max_present": contract_limit_max_present,
            "limit_max_value": contract_limit_max_value,
            "limit_max_valid": contract_limit_max_valid,
            "limit_default_le_limit_max": contract_limit_default_le_limit_max,
            "candidate_limit_gt_200_count": candidate_limit_gt_200_count,
            "slot_limit_gt_top_level_limit_max_count": len(slot_limit_gt_top_level_limit_max_records),
            "slot_limit_gt_top_level_limit_max_examples": slot_limit_gt_top_level_limit_max_records[:20],
            "malformed_candidate_query_count": malformed_candidate_query_count,
            "malformed_candidate_query_examples": malformed_candidate_query_records[:20],
        },
        "risk_findings": {
            "finding_count": len(risk_findings),
            "blocked_count": blocked_count,
            "warning_count": warning_count,
            "findings": risk_findings,
        },
        "validator_result": validator_result,
        "pytest_result": pytest_result,
        "s7e_readiness_assessment": readiness,
        "known_warnings": known_warnings,
        "recommended_next_task": "ULGA-S7E_PatternThemeLinkage_DesignScan",
        "final_verdict": final_verdict,
    }

    write_json(AUDIT_JSON_PATH, report)
    AUDIT_DOC_PATH.write_text(build_markdown(report), encoding="utf-8")

    print(f"ULGA S7DI pattern vocabulary constraint QA audit: {final_verdict}")
    print(f"Active constraints: {len(constraints)}")
    print(f"Total slot constraints: {total_slot_constraints}")
    print(f"Validator: {validator_result['status']}")
    print(f"Pytest: {pytest_result['status']}")
    return 0 if final_verdict != "BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
