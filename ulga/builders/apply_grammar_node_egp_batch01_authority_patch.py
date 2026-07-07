import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
GRAMMAR_PATH = BASE_DIR / "ulga" / "grammar" / "grammar_nodes.json"
SOURCE_REF_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_source_ref_resolver_summary.json"
PATCH_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_canonical_authority_patch_report.json"
PATCH_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_canonical_authority_patch_summary.json"
TASK_ID = "R7-M92A_Batch01CanonicalGrammarAuthorityPatchImplementation"

AUTHORITY_TARGETS = {
    "GRAMMAR_ARTICLES_BASIC": "egp_evidence_refs",
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC": "egp_evidence_refs",
}
FORM_ONLY_TARGETS = {
    "GRAMMAR_CAN_STATEMENT": "egp_form_evidence_refs",
}
UNCHANGED_TARGETS = {
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
    "GRAMMAR_BE_VERB_BASIC",
}
ALLOWED_CHANGED_IDS = set(AUTHORITY_TARGETS) | set(FORM_ONLY_TARGETS)
ALL_BATCH01_IDS = ALLOWED_CHANGED_IDS | UNCHANGED_TARGETS


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data, compact=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    else:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolver_map():
    summary = load_json(SOURCE_REF_PATH)
    refs = summary.get("resolved_refs_by_grammar_id", {})
    missing = sorted(ALLOWED_CHANGED_IDS - set(refs))
    if missing:
        raise RuntimeError(f"Missing resolved source refs: {missing}")
    return refs


def append_unique(values, value):
    current = list(values or [])
    if value not in current:
        current.append(value)
    return current


def main():
    nodes = load_json(GRAMMAR_PATH)
    if not isinstance(nodes, list):
        raise RuntimeError("grammar_nodes.json must be a JSON array")
    refs = resolver_map()
    by_id = {node.get("grammar_id"): node for node in nodes}
    missing_batch = sorted(ALL_BATCH01_IDS - set(by_id))
    if missing_batch:
        raise RuntimeError(f"Missing Batch 01 grammar nodes: {missing_batch}")

    before = {grammar_id: json.dumps(by_id[grammar_id], ensure_ascii=False, sort_keys=True) for grammar_id in ALL_BATCH01_IDS}
    changes = []

    for grammar_id, field_name in AUTHORITY_TARGETS.items():
        node = by_id[grammar_id]
        evidence_ref = refs[grammar_id]
        before_values = list(node.get(field_name, []))
        node[field_name] = append_unique(before_values, evidence_ref)
        node.setdefault("traceability", {}).setdefault("notes", [])
        note = "R7-M92A added Batch 01 EGP authority evidence ref."
        if note not in node["traceability"]["notes"]:
            node["traceability"]["notes"].append(note)
        changes.append({
            "grammar_id": grammar_id,
            "field": field_name,
            "added_ref": evidence_ref,
            "before_count": len(before_values),
            "after_count": len(node[field_name]),
        })

    for grammar_id, field_name in FORM_ONLY_TARGETS.items():
        node = by_id[grammar_id]
        evidence_ref = refs[grammar_id]
        before_values = list(node.get(field_name, []))
        node[field_name] = append_unique(before_values, evidence_ref)
        node.setdefault("traceability", {}).setdefault("notes", [])
        note = "R7-M92A added Batch 01 EGP form-only evidence ref; semantic ability usage remains in RAZ usage evidence layer."
        if note not in node["traceability"]["notes"]:
            node["traceability"]["notes"].append(note)
        changes.append({
            "grammar_id": grammar_id,
            "field": field_name,
            "added_ref": evidence_ref,
            "before_count": len(before_values),
            "after_count": len(node[field_name]),
        })

    after = {grammar_id: json.dumps(by_id[grammar_id], ensure_ascii=False, sort_keys=True) for grammar_id in ALL_BATCH01_IDS}
    unexpectedly_changed = sorted(grammar_id for grammar_id in UNCHANGED_TARGETS if before[grammar_id] != after[grammar_id])
    if unexpectedly_changed:
        raise RuntimeError(f"Forbidden Batch 01 nodes changed: {unexpectedly_changed}")

    write_json(GRAMMAR_PATH, nodes, compact=True)
    report = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_batch01_canonical_authority_patch_report",
        "patched_file": "ulga/grammar/grammar_nodes.json",
        "patch_status": "PASS",
        "changed_grammar_ids": sorted(ALLOWED_CHANGED_IDS),
        "unchanged_batch01_grammar_ids": sorted(UNCHANGED_TARGETS),
        "changes": changes,
        "scope_constraints": {
            "only_canonical_grammar_file_modified_by_builder": True,
            "no_practicebank_generation": True,
            "no_learner_state_write": True,
            "no_runtime_change": True,
            "no_coverage_summary_write": True,
        },
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_batch01_canonical_authority_patch_summary",
        "patch_status": "PASS",
        "patched_file": "ulga/grammar/grammar_nodes.json",
        "changed_grammar_id_count": len(ALLOWED_CHANGED_IDS),
        "changed_grammar_ids": sorted(ALLOWED_CHANGED_IDS),
        "unchanged_batch01_grammar_ids": sorted(UNCHANGED_TARGETS),
        "authority_evidence_patch_count": len(AUTHORITY_TARGETS),
        "form_only_evidence_patch_count": len(FORM_ONLY_TARGETS),
        "practicebank_generation": False,
        "learner_state_write": False,
        "runtime_change": False,
        "next_short_step": "R7-M93A_Batch01CanonicalGrammarAuthorityPatchReadback",
        "stop_reason": "NONE",
    }
    write_json(PATCH_REPORT_PATH, report)
    write_json(PATCH_SUMMARY_PATH, summary)
    print("Batch 01 canonical grammar authority patch: PASS")
    print("Changed grammar IDs:", ", ".join(sorted(ALLOWED_CHANGED_IDS)))


if __name__ == "__main__":
    main()
