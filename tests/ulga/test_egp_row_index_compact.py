import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
BUILDER = BASE_DIR / "ulga" / "builders" / "build_egp_row_index_compact.py"
VALIDATOR = BASE_DIR / "ulga" / "validators" / "validate_egp_row_index_compact.py"
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "egp_row_index_compact.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "egp_row_index_compact_summary.json"


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_egp_compact_row_index_builder_can_run_without_source():
    result = run_command([sys.executable, str(BUILDER)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert REPORT_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_egp_compact_row_index_builder_require_source_fails_when_missing():
    result = run_command([sys.executable, str(BUILDER), "--source", "definitely_missing_egp.xlsx", "--require-source"])
    assert result.returncode == 2


def test_egp_compact_row_index_validator_can_pass():
    run_command([sys.executable, str(BUILDER)])
    result = run_command([sys.executable, str(VALIDATOR)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_egp_compact_row_index_contract():
    run_command([sys.executable, str(BUILDER)])
    report = load_json(REPORT_PATH)
    summary = load_json(SUMMARY_PATH)
    assert report["task_id"] == "R7-M97B_EGPCompactRowIndexBuilder"
    assert summary["task_id"] == "R7-M97B_EGPCompactRowIndexBuilder"
    assert report["source_workbook_status"] in {"READY", "MISSING"}
    assert summary["source_workbook_status"] == report["source_workbook_status"]
    for value in report["scope_constraints"].values():
        assert value is False
    assert summary["canonical_grammar_write_allowed"] is False
