import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
EXPORT_SCRIPT = BASE_DIR / "tools" / "export_raz_aw_v1_status_snapshot_html.py"
HTML_PATH = BASE_DIR / "docs" / "status" / "raz_aw_v1_status_snapshot.html"
MANIFEST_PATH = BASE_DIR / "docs" / "status" / "raz_aw_v1_status_snapshot_manifest.json"

REQUIRED_MANIFEST_KEYS = {
    "project_id",
    "epic_id",
    "subtask_id",
    "generated_at",
    "active_target",
    "deferred_targets",
    "source_records",
    "progress_areas",
    "milestones",
    "gate_metrics",
    "distance_vector",
    "warnings",
}

ALLOWED_PROGRESS_STATUSES = {
    "NOT_STARTED",
    "IN_PROGRESS",
    "PARTIAL",
    "COMPLETE",
    "BLOCKED",
    "UNKNOWN",
}


def run_export():
    return subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )


def load_manifest():
    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_export_script_can_run():
    result = run_export()
    assert result.returncode == 0, result.stdout + result.stderr
    assert HTML_PATH.exists()
    assert MANIFEST_PATH.exists()


def test_manifest_contract():
    run_export()
    manifest = load_manifest()
    assert REQUIRED_MANIFEST_KEYS <= set(manifest)
    assert manifest["project_id"] == "English_Learning_DB"
    assert manifest["epic_id"] == "RAZ-AW-V1_ReadingSystemV1ProgressAndStatusReporting"
    assert manifest["subtask_id"] == "RAZ-AW-V1_StatusSnapshotHTMLExport"
    assert "Reading System V1" in manifest["active_target"]


def test_v2_to_v5_are_deferred_not_active():
    run_export()
    manifest = load_manifest()
    deferred = "\n".join(manifest["deferred_targets"])
    assert "Reading System V2" in deferred
    assert "Reading System V3" in deferred
    assert "Reading System V4" in deferred
    assert "Reading System V5" in deferred
    assert manifest["gate_metrics"]["no_v2_v5_scope_creep"] is True
    assert manifest["gate_metrics"]["adaptive_learning_changed"] is False
    assert manifest["gate_metrics"]["learner_error_tagging_changed"] is False


def test_progress_and_milestone_status_enums_are_valid():
    run_export()
    manifest = load_manifest()
    for area in manifest["progress_areas"]:
        assert area["status"] in ALLOWED_PROGRESS_STATUSES
    for milestone in manifest["milestones"]:
        assert milestone["status"] in ALLOWED_PROGRESS_STATUSES


def test_html_contains_required_sections():
    run_export()
    html = HTML_PATH.read_text(encoding="utf-8")
    for required_text in [
        "RAZ-AW V1 Status Snapshot HTML Export",
        "V1 Boundary",
        "Progress Snapshot",
        "Milestone Status",
        "Source Trace / Evidence Trace",
        "Gate Metrics",
        "Distance Vector",
        "Warnings",
        "Scope Lock",
    ]:
        assert required_text in html


def test_snapshot_does_not_claim_reading_generation_change():
    run_export()
    manifest = load_manifest()
    assert manifest["gate_metrics"]["reading_generation_changed"] is False
    milestones = {item["milestone"]: item for item in manifest["milestones"]}
    assert milestones["Reading question generation"]["status"] == "NOT_STARTED"
