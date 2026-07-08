import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a2_a2plus_bulk_inventory.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a2_a2plus_bulk_inventory_summary.json"
EXPECTED_TASK = "R7-M102_A2A2PLUSBulkInventoryBuilder"
VALID_CLASSES = {"ALREADY_PATCHED", "NEEDS_EGP_CANDIDATE_RESOLUTION"}


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
    print("Validating A2/A2_PLUS bulk inventory...")
    report = load(REPORT_PATH)
    summary = load(SUMMARY_PATH)
    if not isinstance(report, dict) or not isinstance(summary, dict):
        return fail("required inventory reports missing")
    if report.get("task_id") != EXPECTED_TASK or summary.get("task_id") != EXPECTED_TASK:
        return fail("task_id mismatch")
    if report.get("level_band") != ["A2", "A2_PLUS"] or summary.get("level_band") != ["A2", "A2_PLUS"]:
        return fail("level band mismatch")
    records = report.get("records", [])
    counts = {}
    ids = set()
    for record in records:
        grammar_id = record.get("grammar_id")
        if not grammar_id or grammar_id in ids:
            return fail("missing or duplicate grammar_id")
        ids.add(grammar_id)
        if record.get("introduced_stage") not in {"A2", "A2_PLUS"}:
            return fail("record outside level band")
        item_class = record.get("classification")
        if item_class not in VALID_CLASSES:
            return fail("unexpected classification")
        counts[item_class] = counts.get(item_class, 0) + 1
        if record.get("canonical_write_allowed") is not False:
            return fail("canonical write must be false")
    if summary.get("target_count") != len(records):
        return fail("target count mismatch")
    if summary.get("classification_counts") != dict(sorted(counts.items())):
        return fail("classification counts mismatch")
    if summary.get("canonical_grammar_write_allowed") is not False:
        return fail("summary canonical write must be false")
    if summary.get("next_short_step") != "R7-M103_A2A2PLUSBulkEGPCandidateResolver":
        return fail("next short step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop reason must be NONE")
    print("A2/A2_PLUS bulk inventory validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
