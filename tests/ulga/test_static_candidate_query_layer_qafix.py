import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
AUDIT_SCRIPT_PATH = BASE_DIR / "ulga" / "audits" / "audit_static_candidate_query_layer_qa.py"
SAFE_TEST_PLAN_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_query_layer_safe_test_plan.json"
QAFIX_DOC_PATH = BASE_DIR / "docs" / "ulga" / "ULGA_S10K1_STATIC_CANDIDATE_QUERY_LAYER_QAFIX.md"

PROTECTED_FILES = [
    "ulga/graph/static_candidate_ranking.json",
    "ulga/graph/static_candidate_ranking_views.json",
    "ulga/reports/static_candidate_ranking_summary.json",
    "ulga/reports/static_candidate_ranking_quality_audit.json",
    "ulga/reports/static_candidate_ranking_views_summary.json",
    "ulga/reports/static_candidate_ranking_views_quality_audit.json",
    "ulga/builders/build_static_candidate_ranking.py",
    "ulga/builders/build_static_candidate_ranking_views.py",
    "ulga/validators/validate_static_candidate_ranking.py",
    "ulga/validators/validate_static_candidate_ranking_views.py",
]


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_safe_test_plan_exists():
    assert SAFE_TEST_PLAN_PATH.exists()


def test_protected_file_list_exists():
    text = AUDIT_SCRIPT_PATH.read_text(encoding="utf-8")
    for rel in PROTECTED_FILES:
        assert rel in text


def test_safe_commands_do_not_include_ranking_view_legacy_tests():
    payload = load_json(SAFE_TEST_PLAN_PATH)
    commands = " ".join(payload["allowed_s10k_safe_commands"])
    assert "test_static_candidate_ranking.py" not in commands
    assert "test_static_candidate_ranking_views.py" not in commands


def test_safe_commands_do_not_include_builders():
    payload = load_json(SAFE_TEST_PLAN_PATH)
    commands = " ".join(payload["allowed_s10k_safe_commands"])
    assert "build_static_candidate_ranking.py" not in commands
    assert "build_static_candidate_ranking_views.py" not in commands


def test_audit_script_does_not_invoke_builder_scripts():
    text = AUDIT_SCRIPT_PATH.read_text(encoding="utf-8")
    assert 'run_command([sys.executable, "ulga/builders/build_static_candidate_ranking.py"' not in text
    assert 'run_command([sys.executable, "ulga/builders/build_static_candidate_ranking_views.py"' not in text


def test_audit_script_does_not_invoke_legacy_ranking_view_tests():
    text = AUDIT_SCRIPT_PATH.read_text(encoding="utf-8")
    assert 'run_command([sys.executable, "-m", "pytest", "tests/ulga/test_static_candidate_ranking.py"' not in text
    assert 'run_command([sys.executable, "-m", "pytest", "tests/ulga/test_static_candidate_ranking_views.py"' not in text


def test_query_layer_targeted_tests_classified_mutation_safe():
    payload = load_json(SAFE_TEST_PLAN_PATH)
    assert "tests/ulga/test_static_candidate_query_layer.py" in payload["mutation_safe_tests"]
    assert "tests/ulga/test_static_candidate_query_layer_qa.py" in payload["mutation_safe_tests"]


def test_ranking_view_legacy_tests_classified_destructive_or_unknown():
    payload = load_json(SAFE_TEST_PLAN_PATH)
    destructive = set(payload["destructive_rebuild_tests"])
    unknown = set(payload["unknown_side_effect_tests"])
    assert "tests/ulga/test_static_candidate_ranking.py" in destructive | unknown
    assert "tests/ulga/test_static_candidate_ranking_views.py" in destructive | unknown


def test_mutation_snapshot_can_be_generated():
    path = BASE_DIR / "ulga" / "reports" / "static_candidate_query_layer_qafix_mutation_snapshot.json"
    assert path.exists()


def test_protected_artifacts_are_unchanged_after_safe_audit():
    payload = load_json(BASE_DIR / "ulga" / "reports" / "static_candidate_query_layer_qafix_mutation_snapshot.json")
    assert payload["mutation_integrity"] == "PASS"
    assert payload["mutated_protected_files"] == []


def test_s10k1_report_exists_and_records_fullfix_status():
    path = BASE_DIR / "ulga" / "reports" / "static_candidate_query_layer_qafix_report.json"
    assert path.exists()
    payload = load_json(path)
    assert payload["fix_completeness"] == "FULLFIX"


def test_s10k1_doc_exists():
    assert QAFIX_DOC_PATH.exists()
