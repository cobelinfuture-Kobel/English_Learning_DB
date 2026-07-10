import json
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

ALIGNMENT_TABLE_PATH = BASE_DIR / "ulga" / "graph" / "cefr_egp_alignment_table.json"
COVERAGE_MATRIX_PATH = BASE_DIR / "ulga" / "graph" / "grammar_coverage_matrix.json"
CROSS_SKILL_MATRIX_PATH = BASE_DIR / "ulga" / "graph" / "cross_skill_grammar_gate_matrix.json"
UNCOVERED_RULES_PATH = BASE_DIR / "ulga" / "reports" / "grammar_uncovered_egp_rules.json"
CANONICAL_A1_OVERLAY_PATH = BASE_DIR / "ulga" / "graph" / "a1_egp_canonical_mappings.json"
QUERY_INDEX_PATH = BASE_DIR / "ulga" / "graph" / "grammar_query_index.json"
LOOKUP_CONTRACT_PATH = BASE_DIR / "ulga" / "contracts" / "grammar_lookup_contract.json"
VALIDATION_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_lookup_contract_validation_report.json"

LEVEL_STAGES = ["A1", "A1+", "A2", "A2+", "B1", "B1+", "B2"]
SKILLS = ["reading", "listening", "speaking", "writing"]
OFFICIAL_EGP_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
ALLOWED_STAGE_ROLES = {"focus", "recycle", "preview", "maintenance"}
BLOCKED_STAGE_ROLES = {"blocked", "not_applicable"}
TASK_ID = "R7-M104E20B_A1CanonicalMappingConsumerIntegration"
NEXT_SHORT_STEP = "R7-M104E21A_A1CanonicalRuleValidatorIntegration"


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


def sorted_unique(values):
    return sorted({value for value in values if value})


def build_stage_indexes(coverage_records):
    allowed = {stage: [] for stage in LEVEL_STAGES}
    blocked = {stage: [] for stage in LEVEL_STAGES}
    role_by_stage = {stage: defaultdict(list) for stage in LEVEL_STAGES}

    for record in coverage_records:
        grammar_id = record.get("grammar_id")
        if not grammar_id:
            continue
        stage_roles = record.get("stage_roles", {})
        for stage in LEVEL_STAGES:
            role = stage_roles.get(stage, "not_applicable")
            role_by_stage[stage][role].append(grammar_id)
            if role in ALLOWED_STAGE_ROLES:
                allowed[stage].append(grammar_id)
            elif role in BLOCKED_STAGE_ROLES:
                blocked[stage].append(grammar_id)

    return {
        "allowed_by_level_stage": {stage: sorted_unique(ids) for stage, ids in allowed.items()},
        "blocked_by_level_stage": {stage: sorted_unique(ids) for stage, ids in blocked.items()},
        "role_by_level_stage": {
            stage: {role: sorted_unique(ids) for role, ids in sorted(role_map.items())}
            for stage, role_map in role_by_stage.items()
        },
    }


def build_skill_indexes(cross_skill_records):
    allowed = {stage: {skill: [] for skill in SKILLS} for stage in LEVEL_STAGES}
    blocked = {stage: {skill: [] for skill in SKILLS} for stage in LEVEL_STAGES}
    roles = {stage: {skill: defaultdict(list) for skill in SKILLS} for stage in LEVEL_STAGES}

    for record in cross_skill_records:
        grammar_id = record.get("grammar_id")
        stage = record.get("stage")
        if not grammar_id or stage not in LEVEL_STAGES:
            continue
        for skill, scope in record.get("skill_scope", {}).items():
            if skill not in SKILLS:
                continue
            role = scope.get("role", "blocked")
            roles[stage][skill][role].append(grammar_id)
            if role == "blocked":
                blocked[stage][skill].append(grammar_id)
            else:
                allowed[stage][skill].append(grammar_id)

    return {
        "allowed_by_level_stage_skill": {
            stage: {skill: sorted_unique(ids) for skill, ids in skill_map.items()}
            for stage, skill_map in allowed.items()
        },
        "blocked_by_level_stage_skill": {
            stage: {skill: sorted_unique(ids) for skill, ids in skill_map.items()}
            for stage, skill_map in blocked.items()
        },
        "role_by_level_stage_skill": {
            stage: {
                skill: {role: sorted_unique(ids) for role, ids in sorted(role_map.items())}
                for skill, role_map in skill_maps.items()
            }
            for stage, skill_maps in roles.items()
        },
    }


def import_unit_row_ids(unit):
    """Return the row-id field used by any approved A1 import batch."""
    return unit.get("egp_row_ids", unit.get("new_unique_egp_row_ids", []))


def build_canonical_a1_indexes(canonical_overlay, canonical_batches):
    if canonical_overlay.get("canonical_status") != "ACTIVE":
        raise ValueError("A1 canonical overlay must be ACTIVE before consumer integration")
    if canonical_overlay.get("official_level") != "A1":
        raise ValueError("A1 canonical overlay official_level must be A1")

    declared_units = canonical_overlay.get("canonical_mapping_units", [])
    if len(declared_units) != len(set(declared_units)):
        raise ValueError("A1 canonical overlay contains duplicate canonical mapping units")

    units = {
        grammar_id: {
            "grammar_id": grammar_id,
            "canonical_status": "ACTIVE",
            "official_egp_level": "A1",
            "internal_stages": canonical_overlay.get("internal_stages", []),
            "egp_row_ids": [],
            "source_batches": [],
            "mapping_reference_status": "CANONICAL_UNIT_NO_COVERAGE_INCREMENT",
        }
        for grammar_id in declared_units
    }
    by_egp_row_id = defaultdict(list)

    for source, batch in canonical_batches:
        for unit in batch.get("mapping_import_units", []):
            grammar_id = unit.get("grammar_id")
            if grammar_id not in units:
                raise ValueError(f"Import batch contains undeclared canonical A1 unit: {grammar_id}")
            if unit.get("mapping_status") != "IMPORT_READY":
                raise ValueError(f"Canonical A1 import unit is not IMPORT_READY: {grammar_id}")
            row_ids = import_unit_row_ids(unit)
            units[grammar_id]["egp_row_ids"].extend(row_ids)
            units[grammar_id]["source_batches"].append(source)
            for row_id in row_ids:
                by_egp_row_id[row_id].append(grammar_id)

    for unit in units.values():
        unit["egp_row_ids"] = sorted_unique(unit["egp_row_ids"])
        unit["source_batches"] = sorted_unique(unit["source_batches"])
        if unit["egp_row_ids"]:
            unit["mapping_reference_status"] = "VERIFIED_CANONICAL_MAPPING"

    unique_row_ids = sorted(by_egp_row_id)
    accounting = canonical_overlay.get("canonical_row_accounting", {})
    expected_rows = accounting.get("cumulative_unique_rows")
    if expected_rows != len(unique_row_ids):
        raise ValueError(
            f"Canonical A1 unique-row mismatch: overlay={expected_rows}, batches={len(unique_row_ids)}"
        )
    if accounting.get("remaining_unmapped_unique_rows") != 0:
        raise ValueError("Canonical A1 overlay still reports unmapped rows")

    return {
        "canonical_status": canonical_overlay["canonical_status"],
        "official_level": "A1",
        "internal_stages": canonical_overlay.get("internal_stages", []),
        "coverage_status": canonical_overlay.get("coverage_claim", {}).get("status"),
        "coverage_percent": accounting.get("coverage_percent"),
        "canonical_mapping_unit_count": len(units),
        "canonical_units_with_row_mappings": sum(bool(unit["egp_row_ids"]) for unit in units.values()),
        "canonical_unique_egp_row_count": len(unique_row_ids),
        "canonical_egp_row_ids": unique_row_ids,
        "by_grammar_id": dict(sorted(units.items())),
        "by_egp_row_id": {
            row_id: sorted_unique(grammar_ids)
            for row_id, grammar_ids in sorted(by_egp_row_id.items())
        },
    }


def build_grammar_and_egp_indexes(
    alignment_records,
    coverage_records,
    cross_skill_records,
    canonical_a1,
):
    coverage_by_grammar = {record.get("grammar_id"): record for record in coverage_records if record.get("grammar_id")}
    cross_skill_by_grammar = {record.get("grammar_id"): record for record in cross_skill_records if record.get("grammar_id")}
    by_grammar_id = {}
    by_egp_row_id = defaultdict(list)

    for record in alignment_records:
        grammar_id = record.get("grammar_id")
        if not grammar_id:
            continue
        egp_refs = record.get("egp_refs", [])
        by_grammar_id[grammar_id] = {
            "grammar_id": grammar_id,
            "label": record.get("label", ""),
            "system_stage": record.get("system_stage", ""),
            "node_status": record.get("node_status", ""),
            "alignment_status": record.get("alignment_status", ""),
            "egp_refs": egp_refs,
            "missing_egp_refs": record.get("missing_egp_refs", []),
            "coverage": coverage_by_grammar.get(grammar_id, {}),
            "cross_skill": cross_skill_by_grammar.get(grammar_id, {}),
        }
        for ref in egp_refs:
            egp_row_id = ref.get("egp_row_id")
            if egp_row_id:
                by_egp_row_id[egp_row_id].append(grammar_id)

    for grammar_id, canonical_mapping in canonical_a1["by_grammar_id"].items():
        entry = by_grammar_id.setdefault(
            grammar_id,
            {
                "grammar_id": grammar_id,
                "label": "",
                "system_stage": "",
                "node_status": "CANONICAL_OVERLAY_ONLY",
                "alignment_status": "NOT_PRESENT_IN_BASE_ALIGNMENT_TABLE",
                "egp_refs": [],
                "missing_egp_refs": [],
                "coverage": coverage_by_grammar.get(grammar_id, {}),
                "cross_skill": cross_skill_by_grammar.get(grammar_id, {}),
            },
        )
        entry["canonical_a1_mapping"] = canonical_mapping
        entry["effective_a1_mapping_status"] = "VERIFIED_CANONICAL_MAPPING"

    for egp_row_id, grammar_ids in canonical_a1["by_egp_row_id"].items():
        by_egp_row_id[egp_row_id].extend(grammar_ids)

    return {
        "by_grammar_id": dict(sorted(by_grammar_id.items())),
        "by_egp_row_id": {egp_row_id: sorted_unique(ids) for egp_row_id, ids in sorted(by_egp_row_id.items())},
    }


def build_uncovered_index(uncovered_rules, canonical_a1_row_ids):
    rows_by_level = uncovered_rules.get("rows_by_level", {})
    canonical_a1_row_ids = set(canonical_a1_row_ids)
    uncovered = {}
    for level in OFFICIAL_EGP_LEVELS:
        row_ids = [row.get("egp_row_id") for row in rows_by_level.get(level, []) if row.get("egp_row_id")]
        if level == "A1":
            row_ids = [row_id for row_id in row_ids if row_id not in canonical_a1_row_ids]
        uncovered[level] = row_ids
    return uncovered


def build_query_index_and_contract(
    alignment_table,
    coverage_matrix,
    cross_skill_matrix,
    uncovered_rules,
    canonical_overlay,
    canonical_batches,
):
    alignment_records = alignment_table.get("records", [])
    coverage_records = coverage_matrix.get("records", [])
    cross_skill_records = cross_skill_matrix.get("records", [])

    canonical_a1 = build_canonical_a1_indexes(canonical_overlay, canonical_batches)
    stage_indexes = build_stage_indexes(coverage_records)
    skill_indexes = build_skill_indexes(cross_skill_records)
    grammar_indexes = build_grammar_and_egp_indexes(
        alignment_records,
        coverage_records,
        cross_skill_records,
        canonical_a1,
    )
    uncovered_by_egp_level = build_uncovered_index(
        uncovered_rules,
        canonical_a1["canonical_egp_row_ids"],
    )

    query_index = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_query_index",
        "source_paths": {
            "alignment_table": "ulga/graph/cefr_egp_alignment_table.json",
            "coverage_matrix": "ulga/graph/grammar_coverage_matrix.json",
            "cross_skill_matrix": "ulga/graph/cross_skill_grammar_gate_matrix.json",
            "uncovered_rules": "ulga/reports/grammar_uncovered_egp_rules.json",
            "canonical_a1_overlay": "ulga/graph/a1_egp_canonical_mappings.json",
            "canonical_a1_import_batches": [source for source, _ in canonical_batches],
        },
        "level_stages": LEVEL_STAGES,
        "skills": SKILLS,
        **stage_indexes,
        **skill_indexes,
        **grammar_indexes,
        "canonical_a1": canonical_a1,
        "uncovered_by_egp_level": uncovered_by_egp_level,
        "scope_constraints": {
            "no_runtime_implementation": True,
            "no_practicebank_generation": True,
            "no_learner_state_write": True,
            "read_only_contract_for_downstream_systems": True,
        },
    }

    contract = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_lookup_contract",
        "contract_version": "1.1.0",
        "query_index_path": "ulga/graph/grammar_query_index.json",
        "capabilities": {
            "lookup_by_level": True,
            "lookup_by_skill": True,
            "lookup_by_grammar_id": True,
            "lookup_by_egp_row_id": True,
            "lookup_uncovered_egp_rules": True,
            "lookup_blocked_grammar_by_stage_skill": True,
            "lookup_cross_skill_roles": True,
            "lookup_receptive_preview_vs_productive_mastery": True,
            "lookup_canonical_a1_mappings": True,
            "no_learner_state_write": True,
        },
        "required_inputs": [
            "level_stage",
            "skill",
            "grammar_id",
            "egp_row_id",
            "question_type",
            "activity_type",
        ],
        "required_outputs": [
            "allowed_grammar_ids",
            "blocked_grammar_ids",
            "uncovered_egp_rules",
            "covered_egp_rules",
            "grammar_alignment_status",
            "grammar_prerequisites",
            "cross_skill_roles",
            "validator_requirements",
            "canonical_a1_mapping_status",
            "canonical_a1_coverage",
        ],
        "scope_constraints": query_index["scope_constraints"],
    }

    validation_report = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_lookup_contract_validation_report",
        "validation_status": "PASS_WITH_WARNINGS" if not grammar_indexes["by_grammar_id"] else "PASS",
        "query_index_path": "ulga/graph/grammar_query_index.json",
        "lookup_contract_path": "ulga/contracts/grammar_lookup_contract.json",
        "grammar_id_count": len(grammar_indexes["by_grammar_id"]),
        "egp_row_index_count": len(grammar_indexes["by_egp_row_id"]),
        "uncovered_egp_row_count": sum(len(rows) for rows in uncovered_by_egp_level.values()),
        "canonical_a1_mapping_unit_count": canonical_a1["canonical_mapping_unit_count"],
        "canonical_a1_units_with_row_mappings": canonical_a1["canonical_units_with_row_mappings"],
        "canonical_a1_unique_egp_row_count": canonical_a1["canonical_unique_egp_row_count"],
        "canonical_a1_uncovered_egp_row_count": len(uncovered_by_egp_level["A1"]),
        "canonical_a1_coverage_percent": canonical_a1["coverage_percent"],
        "capabilities": contract["capabilities"],
        "notes": [
            "A1 canonical mappings are consumed as a non-destructive overlay; base alignment, coverage, and cross-skill artifacts are not rewritten.",
            "A1 canonical mapping completeness does not claim runtime parser accuracy or authorize learner-state writes.",
        ],
        "next_short_step": NEXT_SHORT_STEP,
        "stop_reason": "NONE",
    }
    return query_index, contract, validation_report


def main():
    alignment_table = read_json(ALIGNMENT_TABLE_PATH, default={"records": []})
    coverage_matrix = read_json(COVERAGE_MATRIX_PATH, default={"records": []})
    cross_skill_matrix = read_json(CROSS_SKILL_MATRIX_PATH, default={"records": []})
    uncovered_rules = read_json(UNCOVERED_RULES_PATH, default={"rows_by_level": {}})
    canonical_overlay = read_json(CANONICAL_A1_OVERLAY_PATH, default={})
    canonical_batches = [
        (source["path"], read_json(BASE_DIR / source["path"], default={}))
        for source in canonical_overlay.get("source_import_batches", [])
    ]
    query_index, contract, validation_report = build_query_index_and_contract(
        alignment_table,
        coverage_matrix,
        cross_skill_matrix,
        uncovered_rules,
        canonical_overlay,
        canonical_batches,
    )
    write_json(QUERY_INDEX_PATH, query_index)
    write_json(LOOKUP_CONTRACT_PATH, contract)
    write_json(VALIDATION_REPORT_PATH, validation_report)
    print(f"Grammar query index build: {validation_report['validation_status']}")
    print(f"Grammar IDs indexed: {validation_report['grammar_id_count']}")
    print(f"Uncovered EGP rows: {validation_report['uncovered_egp_row_count']}")
    print(f"Canonical A1 rows indexed: {validation_report['canonical_a1_unique_egp_row_count']}")


if __name__ == "__main__":
    main()
