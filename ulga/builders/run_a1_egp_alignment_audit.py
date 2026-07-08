import json
import re
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
RESET = BASE / "ulga" / "reports" / "a1_a1plus_alignment_reset_status.json"
GRAMMAR = BASE / "ulga" / "grammar" / "grammar_nodes.json"
EGP_V2 = BASE / "ulga" / "reports" / "egp_row_index_compact_v2.json"
OUT = BASE / "ulga" / "reports" / "a1_egp_alignment_matrix.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_egp_alignment_matrix_summary.json"
TASK_ID = "R7-M101_RESET_A1_EGPAlignmentMatrixOneShot"
STOPWORDS = {
    "a", "an", "the", "and", "or", "to", "with", "for", "of", "in", "on", "at", "as",
    "form", "use", "uses", "basic", "simple", "example", "can", "do", "be", "is", "are",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def tokens(text):
    return {t for t in re.findall(r"[a-zA-Z]+", (text or "").lower()) if len(t) > 1 and t not in STOPWORDS}


def node_text(node):
    return " ".join(str(node.get(k, "")) for k in ["grammar_id", "label", "category", "introduced_stage"])


def row_text(row):
    return " ".join(str(row.get(k, "")) for k in ["super_category", "sub_category", "lexical_range", "guideword", "can_do", "example"])


def cluster_key(row):
    guide = row.get("guideword") or "UNKNOWN"
    guide_head = guide.split(":", 1)[0].strip() if ":" in guide else guide.strip()
    return " | ".join([
        row.get("super_category") or "UNKNOWN",
        row.get("sub_category") or "UNKNOWN",
        guide_head or "UNKNOWN",
    ])


def make_cluster_id(key):
    return re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")[:96]


def main():
    reset = load(RESET)
    if reset.get("a2_a2plus_progression_allowed") is not False:
        raise RuntimeError("A2/A2_PLUS progression must remain blocked before A1 alignment matrix")
    nodes = load(GRAMMAR)
    egp = load(EGP_V2)
    if egp.get("source_workbook_status") != "READY":
        raise RuntimeError("EGP v2 index must be READY")
    target_nodes = [n for n in nodes if n.get("introduced_stage") in {"A1", "A1_PLUS"}]
    a1_rows = [r for r in egp.get("rows", []) if r.get("level") == "A1"]
    node_by_ref = defaultdict(list)
    node_tokens = {}
    for node in target_nodes:
        gid = node.get("grammar_id")
        node_tokens[gid] = tokens(node_text(node))
        for ref in node.get("egp_evidence_refs", []) or []:
            node_by_ref[ref].append({"grammar_id": gid, "ref_type": "authority"})
        for ref in node.get("egp_form_evidence_refs", []) or []:
            node_by_ref[ref].append({"grammar_id": gid, "ref_type": "form_only"})
    clusters = {}
    for row in a1_rows:
        key = cluster_key(row)
        cluster = clusters.setdefault(key, {
            "cluster_id": make_cluster_id(key),
            "cluster_key": key,
            "super_category": row.get("super_category"),
            "sub_category": row.get("sub_category"),
            "row_count": 0,
            "covered_row_count": 0,
            "missing_row_count": 0,
            "rows": [],
            "candidate_node_scores": Counter(),
        })
        ref = row.get("source_ref")
        exact = node_by_ref.get(ref, [])
        rtok = tokens(row_text(row))
        candidate_hits = []
        for gid, ntok in node_tokens.items():
            score = len(rtok & ntok)
            if score >= 2:
                cluster["candidate_node_scores"][gid] += score
                candidate_hits.append({"grammar_id": gid, "score": score})
        row_record = {
            "source_ref": ref,
            "row_number": row.get("row_number"),
            "guideword": row.get("guideword"),
            "can_do": row.get("can_do"),
            "example": row.get("example"),
            "exact_covering_nodes": exact,
            "semantic_candidate_nodes": sorted(candidate_hits, key=lambda x: (-x["score"], x["grammar_id"]))[:5],
        }
        cluster["rows"].append(row_record)
        cluster["row_count"] += 1
        if exact:
            cluster["covered_row_count"] += 1
        else:
            cluster["missing_row_count"] += 1
    cluster_records = []
    decision_counts = Counter()
    for cluster in clusters.values():
        top_candidates = [
            {"grammar_id": gid, "score": score}
            for gid, score in cluster.pop("candidate_node_scores").most_common(5)
        ]
        if cluster["missing_row_count"] == 0:
            decision = "COVERED_BY_EXISTING_NODE_REFS"
        elif cluster["covered_row_count"] > 0:
            decision = "REVIEW_EXTEND_EXISTING_NODE_EVIDENCE"
        elif top_candidates:
            decision = "REVIEW_PATCH_EXISTING_NODE_OR_SPLIT_CLUSTER"
        else:
            decision = "REVIEW_CREATE_NODE_OR_MARK_OUT_OF_SCOPE"
        cluster["suggested_existing_nodes"] = top_candidates
        cluster["decision"] = decision
        decision_counts[decision] += 1
        cluster_records.append(cluster)
    a1_ref_set = {r.get("source_ref") for r in a1_rows}
    wrong_level_refs = []
    for node in target_nodes:
        refs = (node.get("egp_evidence_refs", []) or []) + (node.get("egp_form_evidence_refs", []) or [])
        non_a1 = [ref for ref in refs if ref not in a1_ref_set]
        if non_a1:
            wrong_level_refs.append({"grammar_id": node.get("grammar_id"), "non_a1_refs": non_a1})
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_egp_alignment_matrix",
        "input_reset_status": reset.get("prior_closeout_status"),
        "egp_a1_row_count": len(a1_rows),
        "a1_a1plus_node_count": len(target_nodes),
        "clusters": sorted(cluster_records, key=lambda c: (c["super_category"] or "", c["sub_category"] or "", c["cluster_key"])),
        "wrong_level_or_bridge_refs": sorted(wrong_level_refs, key=lambda x: x["grammar_id"]),
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "local_validation_required": True,
        "ci_gate_required": False,
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "a1_egp_alignment_matrix_summary",
        "validation_status": "PASS",
        "egp_a1_row_count": len(a1_rows),
        "a1_a1plus_node_count": len(target_nodes),
        "cluster_count": len(cluster_records),
        "decision_counts": dict(sorted(decision_counts.items())),
        "wrong_level_or_bridge_node_count": len(wrong_level_refs),
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "next_short_step": "R7-M102_A1EGPAlignmentMatrixOperatorReview",
        "stop_reason": "NONE",
    }
    write(OUT, report)
    write(SUMMARY, summary)
    print("A1 EGP alignment matrix one-shot audit build: PASS")
    print("EGP A1 rows:", len(a1_rows))
    print("Clusters:", len(cluster_records))
    print("Decision counts:", summary["decision_counts"])


if __name__ == "__main__":
    main()
