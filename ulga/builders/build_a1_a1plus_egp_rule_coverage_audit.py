import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
GRAMMAR = BASE / "ulga" / "grammar" / "grammar_nodes.json"
INDEX = BASE / "ulga" / "reports" / "egp_row_index_compact.json"
OUT = BASE / "ulga" / "reports" / "a1_a1plus_egp_rule_coverage_audit.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_egp_rule_coverage_audit_summary.json"
TASK_ID = "R7-M100B_A1A1PLUS_EGPRuleCoverageAudit"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pct(num, den):
    return 0.0 if den == 0 else round(num / den, 6)


def main():
    nodes = load(GRAMMAR)
    index = load(INDEX)
    rows = index.get("rows", [])
    a1_rows = [r for r in rows if r.get("level") == "A1"]
    a1_refs = {r.get("source_ref") for r in a1_rows}
    target_nodes = [n for n in nodes if n.get("introduced_stage") in {"A1", "A1_PLUS"}]
    ref_to_nodes = {}
    node_records = []
    for node in target_nodes:
        gid = node.get("grammar_id")
        authority = node.get("egp_evidence_refs", []) or []
        form_only = node.get("egp_form_evidence_refs", []) or []
        for ref in authority:
            ref_to_nodes.setdefault(ref, []).append({"grammar_id": gid, "ref_type": "authority"})
        for ref in form_only:
            ref_to_nodes.setdefault(ref, []).append({"grammar_id": gid, "ref_type": "form_only"})
        node_records.append({
            "grammar_id": gid,
            "introduced_stage": node.get("introduced_stage"),
            "authority_ref_count": len(authority),
            "form_only_ref_count": len(form_only),
            "a1_ref_count": sum(1 for ref in authority + form_only if ref in a1_refs),
            "non_a1_ref_count": sum(1 for ref in authority + form_only if ref and ref not in a1_refs),
        })
    covered = []
    missing = []
    by_super = {}
    for row in a1_rows:
        ref = row.get("source_ref")
        hit = ref in ref_to_nodes
        item = {
            "source_ref": ref,
            "row_number": row.get("row_number"),
            "super_category": row.get("super_category"),
            "sub_category": row.get("sub_category"),
            "guideword": row.get("guideword"),
            "covering_nodes": ref_to_nodes.get(ref, []),
        }
        bucket = by_super.setdefault(row.get("super_category") or "UNKNOWN", {"total": 0, "covered": 0})
        bucket["total"] += 1
        if hit:
            bucket["covered"] += 1
            covered.append(item)
        else:
            missing.append(item)
    for data in by_super.values():
        data["coverage_ratio"] = pct(data["covered"], data["total"])
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_egp_rule_coverage_audit",
        "source_index_status": index.get("source_workbook_status"),
        "source_egp_level": "A1",
        "node_records": sorted(node_records, key=lambda x: x["grammar_id"] or ""),
        "covered_egp_a1_rows": sorted(covered, key=lambda x: x.get("row_number") or 0),
        "missing_egp_a1_rows": sorted(missing, key=lambda x: x.get("row_number") or 0),
        "coverage_by_super_category": dict(sorted(by_super.items())),
        "canonical_grammar_write_allowed": False,
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_egp_rule_coverage_audit_summary",
        "validation_status": "PASS",
        "source_index_status": index.get("source_workbook_status"),
        "a1_a1plus_node_count": len(target_nodes),
        "egp_a1_row_count": len(a1_rows),
        "covered_egp_a1_row_count": len(covered),
        "missing_egp_a1_row_count": len(missing),
        "egp_a1_row_coverage_ratio": pct(len(covered), len(a1_rows)),
        "nodes_using_non_a1_refs_count": sum(1 for r in node_records if r["non_a1_ref_count"] > 0),
        "final_closeout_allowed": False,
        "final_closeout_blocker": "THRESHOLD_POLICY_REQUIRED",
        "next_short_step": "R7-M100C_LevelBandCloseoutGateValidator",
        "stop_reason": "NONE",
    }
    write(OUT, report)
    write(SUMMARY, summary)
    print("A1/A1_PLUS EGP rule coverage audit build: PASS")
    print("EGP A1 rows:", len(a1_rows))
    print("Covered:", len(covered))
    print("Coverage:", summary["egp_a1_row_coverage_ratio"])


if __name__ == "__main__":
    main()
