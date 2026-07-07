import json
from collections import Counter, defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

GRAMMAR_PROFILE_PATH = BASE_DIR / "grammar_profile" / "json" / "grammar_profile.json"
GRAMMAR_NODES_PATH = BASE_DIR / "ulga" / "graph" / "grammar_nodes.json"
ALIGNMENT_TABLE_PATH = BASE_DIR / "ulga" / "graph" / "cefr_egp_alignment_table.json"
UNCOVERED_RULES_PATH = BASE_DIR / "ulga" / "reports" / "grammar_uncovered_egp_rules.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_alignment_summary.json"

OFFICIAL_EGP_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
TARGET_LEVELS = ["A1", "A2", "B1", "B2"]
ALLOWED_ALIGNMENT_STATUS = {
    "MATCH",
    "EARLY_BY_DESIGN",
    "LATE_BY_DEPENDENCY",
    "PREVIEW_ONLY",
    "CONFLICT_REVIEW_REQUIRED",
    "NOT_IN_AUTHORITY_SOURCE",
    "UNMAPPED",
}


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


def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_level(value):
    if value is None:
        return "UNKNOWN"
    return str(value).strip().upper() or "UNKNOWN"


def normalize_egp_ref(ref):
    if isinstance(ref, str):
        return ref.strip()
    if isinstance(ref, dict):
        for key in ["egp_row_id", "id", "row_id"]:
            value = normalize_text(ref.get(key))
            if value:
                return value
    return ""


def get_grammar_id(node, index):
    for key in ["grammar_id", "id", "node_id"]:
        value = normalize_text(node.get(key))
        if value:
            return value
    return f"UNIDENTIFIED_GRAMMAR_NODE_{index:06d}"


def make_egp_lookup(rows):
    lookup = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_id = normalize_text(row.get("id"))
        if not row_id:
            continue
        lookup[row_id] = {
            "egp_row_id": row_id,
            "egp_level": normalize_level(row.get("level")),
            "super_category": normalize_text(row.get("super_category")),
            "sub_category": normalize_text(row.get("sub_category")),
            "guideword": normalize_text(row.get("guideword")),
            "source_sheet": normalize_text(row.get("source_sheet")),
            "source_row": row.get("source_row"),
        }
    return lookup


def build_alignment(nodes, egp_rows):
    if not isinstance(nodes, list):
        raise TypeError("grammar_nodes.json must contain a JSON list")
    if not isinstance(egp_rows, list):
        raise TypeError("grammar_profile.json must contain a JSON list")

    egp_lookup = make_egp_lookup(egp_rows)
    all_egp_ids = set(egp_lookup)
    mapped_egp_ids = set()
    alignment_records = []
    node_status_counts = Counter()
    unresolved_refs = []

    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            grammar_id = f"INVALID_GRAMMAR_NODE_{index:06d}"
            alignment_records.append({
                "grammar_id": grammar_id,
                "node_status": "INVALID_NODE_SHAPE",
                "egp_refs": [],
                "alignment_status": "CONFLICT_REVIEW_REQUIRED",
                "alignment_reason": "grammar node is not an object",
                "review_status": "operator_required",
            })
            node_status_counts["INVALID_NODE_SHAPE"] += 1
            continue

        grammar_id = get_grammar_id(node, index)
        raw_refs = node.get("egp_refs", []) or []
        if not isinstance(raw_refs, list):
            raw_refs = [raw_refs]
        ref_ids = [normalize_egp_ref(ref) for ref in raw_refs]
        ref_ids = [ref_id for ref_id in ref_ids if ref_id]
        resolved_refs = []
        missing_refs = []
        for ref_id in ref_ids:
            if ref_id in egp_lookup:
                resolved_refs.append(egp_lookup[ref_id])
                mapped_egp_ids.add(ref_id)
            else:
                missing_refs.append(ref_id)
                unresolved_refs.append({"grammar_id": grammar_id, "egp_row_id": ref_id})

        if resolved_refs and not missing_refs:
            alignment_status = node.get("alignment_status") or "MATCH"
            if alignment_status not in ALLOWED_ALIGNMENT_STATUS:
                alignment_status = "CONFLICT_REVIEW_REQUIRED"
            node_status = "EGP_MAPPED"
            review_status = node.get("review_status") or "approved"
            reason = node.get("alignment_reason") or "all egp_refs resolve to normalized EGP rows"
        elif resolved_refs and missing_refs:
            alignment_status = "CONFLICT_REVIEW_REQUIRED"
            node_status = "EGP_PARTIAL_MATCH"
            review_status = "operator_required"
            reason = "some egp_refs resolve, but at least one referenced EGP row is missing"
        elif ref_ids:
            alignment_status = "CONFLICT_REVIEW_REQUIRED"
            node_status = "UNRESOLVED_EGP_REFS"
            review_status = "operator_required"
            reason = "egp_refs exist but none resolve to normalized EGP rows"
        else:
            alignment_status = node.get("alignment_status") or "UNMAPPED"
            if alignment_status == "NOT_IN_AUTHORITY_SOURCE":
                node_status = "NOT_IN_EGP_BUT_SYSTEM_REQUIRED"
                review_status = node.get("review_status") or "pending"
                reason = node.get("alignment_reason") or "node explicitly marked outside EGP authority"
            else:
                alignment_status = "UNMAPPED"
                node_status = "UNMAPPED"
                review_status = node.get("review_status") or "pending"
                reason = "grammar node has no egp_refs"

        node_status_counts[node_status] += 1
        alignment_records.append({
            "grammar_id": grammar_id,
            "label": normalize_text(node.get("label")),
            "system_stage": normalize_text(node.get("system_stage")),
            "node_status": node_status,
            "egp_refs": resolved_refs,
            "missing_egp_refs": missing_refs,
            "alignment_status": alignment_status,
            "alignment_reason": reason,
            "review_status": review_status,
        })

    uncovered_by_level = defaultdict(list)
    for egp_id in sorted(all_egp_ids - mapped_egp_ids):
        row = egp_lookup[egp_id]
        uncovered_by_level[row["egp_level"]].append(row)

    egp_counts_by_level = Counter(row["egp_level"] for row in egp_lookup.values())
    uncovered_counts_by_level = {
        level: len(uncovered_by_level.get(level, [])) for level in OFFICIAL_EGP_LEVELS
    }
    mapped_counts_by_level = {
        level: egp_counts_by_level.get(level, 0) - uncovered_counts_by_level.get(level, 0)
        for level in OFFICIAL_EGP_LEVELS
    }
    coverage_by_level = {
        level: (
            mapped_counts_by_level[level] / egp_counts_by_level[level]
            if egp_counts_by_level.get(level, 0)
            else 0.0
        )
        for level in OFFICIAL_EGP_LEVELS
    }

    alignment_table = {
        "task_id": "R7-M36_GrammarNodeEGPAlignmentPipelineImplementation",
        "artifact_id": "cefr_egp_alignment_table",
        "source_paths": {
            "grammar_nodes": "ulga/graph/grammar_nodes.json",
            "grammar_profile": "grammar_profile/json/grammar_profile.json",
        },
        "allowed_alignment_status": sorted(ALLOWED_ALIGNMENT_STATUS),
        "records": sorted(alignment_records, key=lambda item: item["grammar_id"]),
        "summary": {
            "grammar_node_count": len(nodes),
            "egp_row_count": len(egp_lookup),
            "mapped_egp_row_count": len(mapped_egp_ids),
            "uncovered_egp_row_count": len(all_egp_ids - mapped_egp_ids),
            "node_status_counts": dict(sorted(node_status_counts.items())),
            "unresolved_ref_count": len(unresolved_refs),
        },
        "scope_constraints": {
            "no_runtime_implementation": True,
            "no_practicebank_generation": True,
            "no_learner_state_write": True,
            "no_ai_mapping_promotion": True,
        },
    }

    uncovered_rules = {
        "task_id": "R7-M36_GrammarNodeEGPAlignmentPipelineImplementation",
        "artifact_id": "grammar_uncovered_egp_rules",
        "definition": "EGP rows with no resolving grammar_node egp_ref in the current alignment table.",
        "counts_by_level": uncovered_counts_by_level,
        "target_a1_b2_uncovered_total": sum(uncovered_counts_by_level[level] for level in TARGET_LEVELS),
        "rows_by_level": {
            level: uncovered_by_level.get(level, []) for level in OFFICIAL_EGP_LEVELS
        },
    }

    target_total = sum(egp_counts_by_level.get(level, 0) for level in TARGET_LEVELS)
    target_mapped = sum(mapped_counts_by_level.get(level, 0) for level in TARGET_LEVELS)
    summary = {
        "task_id": "R7-M36_GrammarNodeEGPAlignmentPipelineImplementation",
        "artifact_id": "grammar_node_egp_alignment_summary",
        "validation_status": "PASS_WITH_WARNINGS" if len(mapped_egp_ids) < len(all_egp_ids) else "PASS",
        "grammar_node_count": len(nodes),
        "egp_row_count": len(egp_lookup),
        "egp_counts_by_level": {level: egp_counts_by_level.get(level, 0) for level in OFFICIAL_EGP_LEVELS},
        "mapped_counts_by_level": mapped_counts_by_level,
        "uncovered_counts_by_level": uncovered_counts_by_level,
        "coverage_by_level": coverage_by_level,
        "target_a1_b2_total": target_total,
        "target_a1_b2_mapped": target_mapped,
        "target_a1_b2_coverage": target_mapped / target_total if target_total else 0.0,
        "node_status_counts": dict(sorted(node_status_counts.items())),
        "unresolved_refs": unresolved_refs,
        "next_short_step": "R7-M37_GrammarCoverageMatrixBuilderImplementation",
        "stop_reason": "NONE",
    }

    return alignment_table, uncovered_rules, summary


def main():
    nodes = read_json(GRAMMAR_NODES_PATH, default=[])
    egp_rows = read_json(GRAMMAR_PROFILE_PATH, default=[])
    alignment_table, uncovered_rules, summary = build_alignment(nodes, egp_rows)
    write_json(ALIGNMENT_TABLE_PATH, alignment_table)
    write_json(UNCOVERED_RULES_PATH, uncovered_rules)
    write_json(SUMMARY_PATH, summary)
    print(f"Grammar node EGP alignment build: {summary['validation_status']}")
    print(f"Grammar nodes: {summary['grammar_node_count']}")
    print(f"A1-B2 coverage: {summary['target_a1_b2_coverage']:.4f}")


if __name__ == "__main__":
    main()
