import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_alignment.py"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_alignment.py"
GRAMMAR_PROFILE_PATH = BASE_DIR / "grammar_profile" / "json" / "grammar_profile.json"
GRAMMAR_NODES_PATH = BASE_DIR / "ulga" / "grammar" / "grammar_nodes.json"
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


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def level_counts_from_source():
    rows = load_json(GRAMMAR_PROFILE_PATH)
    counts = Counter(str(row.get("level", "UNKNOWN")).strip().upper() or "UNKNOWN" for row in rows)
    return rows, counts


def source_node_count():
    return len(load_json(GRAMMAR_NODES_PATH))


def source_evidence_ref_count():
    nodes = load_json(GRAMMAR_NODES_PATH)
    return sum(1 for node in nodes if node.get("egp_evidence_refs") or node.get("egp_refs"))


def test_builder_can_run():
    result = run_command([sys.executable, str(BUILDER_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert ALIGNMENT_TABLE_PATH.exists()
    assert UNCOVERED_RULES_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_alignment_outputs_parse():
    alignment = load_json(ALIGNMENT_TABLE_PATH)
    uncovered = load_json(UNCOVERED_RULES_PATH)
    summary = load_json(SUMMARY_PATH)
    assert isinstance(alignment, dict)
    assert isinstance(uncovered, dict)
    assert isinstance(summary, dict)


def test_canonical_static_grammar_nodes_are_alignment_source():
    alignment = load_json(ALIGNMENT_TABLE_PATH)
    summary = load_json(SUMMARY_PATH)
    assert alignment["source_paths"]["grammar_nodes"] == "ulga/grammar/grammar_nodes.json"
    assert summary["grammar_nodes_source_path"] == "ulga/grammar/grammar_nodes.json"
    assert summary["grammar_node_count"] == source_node_count()


def test_existing_egp_evidence_refs_are_normalized_without_new_evidence_selection():
    alignment = load_json(ALIGNMENT_TABLE_PATH)
    summary = load_json(SUMMARY_PATH)
    assert source_evidence_ref_count() > 0
    assert summary["node_status_counts"].get("EGP_MAPPED", 0) > 0
    mapped_records = [record for record in alignment["records"] if record["node_status"] == "EGP_MAPPED"]
    assert mapped_records
    for record in mapped_records:
        assert record["egp_refs"]
        assert set(record["source_ref_fields"]).issubset({"egp_refs", "egp_evidence_refs"})


def test_allowed_alignment_status_contract():
    alignment = load_json(ALIGNMENT_TABLE_PATH)
    assert set(alignment["allowed_alignment_status"]) == ALLOWED_ALIGNMENT_STATUS


def test_source_counts_match_alignment_summary():
    rows, counts = level_counts_from_source()
    alignment = load_json(ALIGNMENT_TABLE_PATH)
    uncovered = load_json(UNCOVERED_RULES_PATH)
    summary = load_json(SUMMARY_PATH)

    expected_counts = {level: counts.get(level, 0) for level in OFFICIAL_EGP_LEVELS}
    assert summary["egp_counts_by_level"] == expected_counts
    assert summary["egp_row_count"] == sum(expected_counts.values())
    assert alignment["summary"]["egp_row_count"] == sum(expected_counts.values())
    assert alignment["summary"]["egp_counts_by_level"] == expected_counts

    for level in OFFICIAL_EGP_LEVELS:
        mapped = summary["mapped_counts_by_level"][level]
        uncovered_count = summary["uncovered_counts_by_level"][level]
        assert mapped + uncovered_count == expected_counts[level]
        assert alignment["summary"]["mapped_counts_by_level"][level] == mapped
        assert alignment["summary"]["uncovered_counts_by_level"][level] == uncovered_count
        assert uncovered["counts_by_level"][level] == uncovered_count
        assert len(uncovered["rows_by_level"][level]) == uncovered_count

    expected_target_total = sum(expected_counts[level] for level in TARGET_LEVELS)
    expected_target_mapped = sum(summary["mapped_counts_by_level"][level] for level in TARGET_LEVELS)
    assert summary["target_a1_b2_total"] == expected_target_total
    assert summary["target_a1_b2_mapped"] == expected_target_mapped


def test_scope_constraints_prevent_runtime_or_ai_promotion():
    alignment = load_json(ALIGNMENT_TABLE_PATH)
    scope = alignment["scope_constraints"]
    assert scope["no_runtime_implementation"] is True
    assert scope["no_practicebank_generation"] is True
    assert scope["no_learner_state_write"] is True
    assert scope["no_ai_mapping_promotion"] is True
    assert scope["no_new_evidence_selection"] is True


def test_next_short_step_points_to_r7_m45():
    summary = load_json(SUMMARY_PATH)
    assert summary["next_short_step"] == "R7-M45_GeneratedGrammarPipelineArtifactsRefresh"
    assert summary["stop_reason"] == "NONE"
