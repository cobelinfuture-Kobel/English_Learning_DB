import hashlib
import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_learner_exposure_evidence.py"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_learner_exposure_evidence.py"
EVIDENCE_PATH = BASE_DIR / "ulga" / "graph" / "learner_exposure_evidence.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "learner_exposure_evidence_summary.json"
UPSTREAM_PATHS = [
    BASE_DIR / "ulga" / "learner_state" / "learner_state.json",
    BASE_DIR / "ulga" / "graph" / "learning_opportunities.json",
    BASE_DIR / "ulga" / "graph" / "dependency_readiness_resolution.json",
    BASE_DIR / "ulga" / "graph" / "reinforcement_candidate_expansion.json",
    BASE_DIR / "ulga" / "reports" / "reinforcement_candidate_expansion_summary.json",
    BASE_DIR / "ulga" / "graph" / "reinforcement_signal.json",
    BASE_DIR / "ulga" / "graph" / "antigravity_plan.json",
    BASE_DIR / "ulga" / "graph" / "dependency_graph.json",
    BASE_DIR / "ulga" / "graph" / "exposure_mapping_bridge.json",
]


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def test_builder_runs():
    result = run_command([sys.executable, str(BUILDER_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert EVIDENCE_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_passes():
    result = run_command([sys.executable, str(VALIDATOR_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_evidence_exists():
    payload = load_json(EVIDENCE_PATH)
    assert len(payload["evidence"]) > 0


def test_mapping_count_gt_zero():
    summary = load_json(SUMMARY_PATH)
    assert summary["opportunity_mapping_count"] > 0


def test_summary_exists():
    payload = load_json(EVIDENCE_PATH)
    summary = load_json(SUMMARY_PATH)
    mapped_opportunities = {item["target_id"] for item in payload["evidence"]}
    assert summary["status"] in {"PASS", "PASS_WITH_WARNINGS", "BLOCKED"}
    assert summary["evidence_count"] == len(payload["evidence"])
    assert summary["opportunity_mapping_count"] == len(mapped_opportunities)
    assert "coverage_rate" in summary
    assert "evidence_source_distribution" in summary
    assert "bridge_ref_count" in summary
    assert isinstance(summary["warnings"], list)


def test_sources_and_scores_valid():
    payload = load_json(EVIDENCE_PATH)
    for evidence in payload["evidence"]:
        assert evidence["target_type"] == "opportunity"
        assert 0 <= evidence["opportunity_exposure_score"] <= 1
        assert evidence["confidence_band"] in {"weak", "medium", "strong"}
        assert isinstance(evidence["prior_exposure"], bool)
        assert evidence["prior_exposure"] == (evidence["opportunity_exposure_score"] > 0)
        assert evidence["evidence_sources"]
        assert set(evidence["evidence_sources"]).issubset(
            {"vocabulary", "grammar", "theme", "direct_focus_node", "dependency_parent"}
        )
        assert isinstance(evidence["bridge_refs"], list)


def test_bridge_refs_used_when_bridge_layer_exists():
    payload = load_json(EVIDENCE_PATH)
    bridged = [evidence for evidence in payload["evidence"] if evidence["bridge_refs"]]
    assert bridged
    assert any(evidence["mapping_type"] == "direct_focus_node_bridge" for evidence in bridged)


def test_deterministic_output():
    first_result = run_command([sys.executable, str(BUILDER_PATH)])
    assert first_result.returncode == 0, first_result.stdout + first_result.stderr
    first_evidence = EVIDENCE_PATH.read_bytes()
    first_summary = SUMMARY_PATH.read_bytes()

    second_result = run_command([sys.executable, str(BUILDER_PATH)])
    assert second_result.returncode == 0, second_result.stdout + second_result.stderr
    assert EVIDENCE_PATH.read_bytes() == first_evidence
    assert SUMMARY_PATH.read_bytes() == first_summary


def test_no_upstream_files_modified():
    before = {path: file_hash(path) for path in UPSTREAM_PATHS if path.exists()}
    result = run_command([sys.executable, str(BUILDER_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
    after = {path: file_hash(path) for path in UPSTREAM_PATHS if path.exists()}
    assert after == before
