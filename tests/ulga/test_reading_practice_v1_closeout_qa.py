import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.audits import audit_reading_practice_v1_closeout as closeout

AUDIT_PATH = BASE_DIR / "ulga" / "audits" / "audit_reading_practice_v1_closeout.py"


def test_closeout_required_artifact_lists_are_non_empty():
    assert closeout.REQUIRED_STAGE_ARTIFACTS
    assert closeout.REQUIRED_CODE_ARTIFACTS
    assert closeout.REQUIRED_TEST_ARTIFACTS
    assert closeout.GENERATED_ARTIFACTS_NOT_REQUIRED_IN_REPO


def test_closeout_audit_passes_without_blocking_errors():
    result = closeout.run_audit()
    assert result["status"] in {"PASS", "PASS_WITH_WARNINGS"}
    assert result["errors"] == []
    assert result["closeout_decision"] == "READING_SYSTEM_V1_CLOSED_AS_CANDIDATE_PIPELINE"


def test_closeout_audit_confirms_no_v2_v5_spillover():
    result = closeout.run_audit()
    assert "V2/V3/V4/V5" in result["next_allowed_task"]
    assert result["required_stage_artifacts"] == 10
    assert result["required_code_artifacts"] == 6
    assert result["required_test_artifacts"] == 6


def test_closeout_audit_direct_cli_smoke():
    result = subprocess.run(
        [sys.executable, str(AUDIT_PATH)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Reading System V1 closeout QA:" in result.stdout
    assert "READING_SYSTEM_V1_CLOSED_AS_CANDIDATE_PIPELINE" in result.stdout
