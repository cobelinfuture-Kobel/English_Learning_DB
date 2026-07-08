import json
import sys
from pathlib import Path
from urllib.parse import urlparse

BASE = Path(__file__).resolve().parents[2]
REPORT = BASE / "ulga" / "reports" / "a1_egp_alignment_cambridge_official_exam_source_manifest.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_egp_alignment_cambridge_official_exam_source_manifest_summary.json"
TASK_ID = "R7-M104E1_CambridgeOfficialExamEvidenceIntake"
REQUIRED_EXAMS = {"Pre A1 Starters", "A1 Movers", "A2 Flyers", "A2 Key for Schools and A2 Key"}
REQUIRED_LEVELS = {"Pre A1", "A1", "A2"}


def fail(message):
    print("FAIL: " + message)
    return False


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL: {path}: {exc}")
        return None


def validate():
    print("Validating A1 EGP alignment Cambridge official exam source manifest...")
    report = load(REPORT)
    summary = load(SUMMARY)
    if not isinstance(report, dict) or not isinstance(summary, dict):
        return fail("required manifest files missing")
    if report.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    sources = report.get("official_sources", [])
    if report.get("official_source_count") != len(sources) or summary.get("official_source_count") != len(sources):
        return fail("official_source_count mismatch")
    exams = {source.get("exam") for source in sources}
    if not REQUIRED_EXAMS.issubset(exams):
        return fail("required Cambridge exams missing")
    levels = {source.get("cefr_level") for source in sources}
    if not REQUIRED_LEVELS.issubset(levels):
        return fail("required CEFR levels missing")
    for source in sources:
        url = source.get("url", "")
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != "www.cambridgeenglish.org":
            return fail("source URL must be official Cambridge English HTTPS URL")
        if source.get("source_type") != "official_cambridge_exam_page":
            return fail("invalid source_type")
        if source.get("evidence_scope") != "exam_level_and_learner_outcome_only":
            return fail("invalid evidence_scope")
        if not source.get("verified_claims"):
            return fail("verified_claims missing")
    if report.get("official_cambridge_source_verified") is not True or summary.get("official_cambridge_source_verified") is not True:
        return fail("official source must be verified")
    if report.get("per_cluster_official_cambridge_bridge_ready") is not False or summary.get("per_cluster_official_cambridge_bridge_ready") is not False:
        return fail("per-cluster bridge must not be ready yet")
    if summary.get("operator_patch_decision_allowed") is not False:
        return fail("operator patch decision must not be allowed yet")
    for key in ["final_closeout_allowed", "a2_a2plus_progression_allowed", "canonical_grammar_write_allowed"]:
        if report.get(key) is not False or summary.get(key) is not False:
            return fail(f"{key} must be false")
    if report.get("local_validation_required") is not True:
        return fail("local_validation_required must be true")
    if report.get("ci_gate_required") is not False:
        return fail("ci_gate_required must be false")
    if summary.get("next_short_step") != "R7-M104E2_CambridgeOfficialClusterBridgePlan":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason mismatch")
    print("A1 EGP alignment Cambridge official exam source manifest validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
