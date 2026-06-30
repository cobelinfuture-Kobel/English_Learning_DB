import json
import sys
from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.builders.build_learner_state import EVENT_TYPE_MULTIPLIERS, ROLE_MULTIPLIERS, format_timestamp, parse_timestamp
from ulga.validators.validate_evidence_event_schema import validate_event_collection
from ulga.validators.validate_learner_state_builder_output import validate_builder_output
from ulga.validators.validate_learner_state_schema import validate_learner_state_collection


SAMPLE_EVENTS_PATH = BASE_DIR / "ulga" / "learner_state" / "sample_evidence_events.json"
LEARNER_STATE_PATH = BASE_DIR / "ulga" / "learner_state" / "learner_state.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "learner_state_builder_summary.json"
GUARDRAIL_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "learner_state_guardrail_summary.json"
BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_learner_state.py"
S9E_DOC_PATH = BASE_DIR / "docs" / "ulga" / "ULGA_S9E_LEARNER_STATE_BUILDER_IMPLEMENTATION.md"
AUDIT_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "learner_state_builder_qa_audit.json"

FORBIDDEN_FIELDS = {
    "candidate_score",
    "recommendation",
    "planner_decision",
    "next_best_node",
    "lesson_plan",
    "scheduler_action",
}

DERIVED_NODE_TYPES = {"theme", "morphology", "skill", "assessment", "dialogue"}


class AuditError(Exception):
    pass


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, ensure_ascii=True, sort_keys=False)
        f.write("\n")


def require(condition, message):
    if not condition:
        raise AuditError(message)


def get_required_files():
    return [
        SAMPLE_EVENTS_PATH,
        LEARNER_STATE_PATH,
        SUMMARY_PATH,
        BUILDER_PATH,
        S9E_DOC_PATH,
    ]


def build_event_maps(events):
    event_map = {}
    per_record_entries = defaultdict(list)
    for event in events:
        event_map[event["event_id"]] = event
        event_multiplier = EVENT_TYPE_MULTIPLIERS[event["event_type"]]
        normalized_score = event["score"] * event_multiplier * event["confidence"]["value"]
        for node_ref in event["node_refs"]:
            role_multiplier = ROLE_MULTIPLIERS[node_ref["role"]]
            effective_strength = node_ref["weight"] * role_multiplier * event_multiplier * event["confidence"]["value"]
            per_record_entries[(event["learner_id"], node_ref["node_id"])].append(
                {
                    "event_id": event["event_id"],
                    "event_type": event["event_type"],
                    "node_type": node_ref["node_type"],
                    "role": node_ref["role"],
                    "node_ref_weight": node_ref["weight"],
                    "effective_strength": effective_strength,
                    "effective_normalized_score": normalized_score,
                    "timestamp": event["timestamp"],
                }
            )
    return event_map, per_record_entries


def strongest_entry(entries):
    return max(entries, key=lambda entry: (entry["effective_strength"], entry["event_id"]))


def expected_review_due_at(record):
    mastery_band = record["mastery_band"]
    last_seen_at = parse_timestamp(record["last_seen_at"]) if record["last_seen_at"] else None
    last_success_at = parse_timestamp(record["last_success_at"]) if record["last_success_at"] else None
    if mastery_band == "unknown":
        return None
    if mastery_band == "seen":
        anchor = last_seen_at
        days = 2
    elif mastery_band == "practicing":
        anchor = last_success_at or last_seen_at
        days = 3
    elif mastery_band == "functional":
        anchor = last_success_at
        days = 7
    elif mastery_band == "mastered":
        anchor = last_success_at
        days = 14
    elif mastery_band == "automatic":
        anchor = last_success_at
        days = 30
    else:
        raise AuditError(f"unsupported mastery band during review_due audit: {mastery_band}")
    if anchor is None:
        return None
    return format_timestamp(anchor + timedelta(days=days))


def has_valid_review_anchor(record):
    mastery_band = record.get("mastery_band")
    last_success_at = record.get("last_success_at")
    last_seen_at = record.get("last_seen_at")

    if mastery_band == "seen":
        return bool(last_seen_at or last_success_at)
    if mastery_band == "practicing":
        return bool(last_success_at or last_seen_at)
    if mastery_band in {"functional", "mastered", "automatic"}:
        return bool(last_success_at)
    if mastery_band == "unknown":
        return False
    return bool(last_success_at or last_seen_at)


def audit_role_risks(records, per_record_entries):
    warnings = []
    role_risk_records = []
    for record in records:
        key = (record["learner_id"], record["node_id"])
        entries = per_record_entries.get(key, [])
        if not entries:
            continue
        strongest = strongest_entry(entries)
        role = strongest["role"]
        band = record["mastery_band"]
        should_warn = (
            (role == "coverage_signal" and band in {"functional", "mastered", "automatic"})
            or (role == "supporting_context" and band in {"mastered", "automatic"})
            or (role == "diagnostic_signal" and band in {"functional", "mastered", "automatic"})
            or (role == "review_signal" and band in {"functional", "mastered", "automatic"})
            or (role == "prerequisite" and band in {"mastered", "automatic"})
        )
        if should_warn:
            finding = {
                "learner_id": record["learner_id"],
                "node_id": record["node_id"],
                "node_type": record["node_type"],
                "mastery_band": band,
                "strongest_role": role,
                "event_id": strongest["event_id"],
                "warning_code": "WARN_ROLE_HIGH_BAND_LOW_AUTHORITY_ROLE",
            }
            role_risk_records.append(finding)
            warnings.append(
                f"{finding['warning_code']}: {record['learner_id']} {record['node_id']} strongest role {role} with mastery_band {band}"
            )
    return warnings, role_risk_records


def audit_pre_guardrail_role_risks(guardrail_summary):
    warnings = []
    role_risk_records = []
    for example in guardrail_summary.get("before_after_examples", []):
        role = example.get("strongest_role")
        band = example.get("before_band")
        should_warn = (
            (role == "coverage_signal" and band in {"functional", "mastered", "automatic"})
            or (role == "supporting_context" and band in {"mastered", "automatic"})
            or (role == "diagnostic_signal" and band in {"functional", "mastered", "automatic"})
            or (role == "review_signal" and band in {"functional", "mastered", "automatic"})
            or (role == "prerequisite" and band in {"mastered", "automatic"})
        )
        if not should_warn:
            continue
        finding = {
            "learner_id": example["learner_id"],
            "node_id": example["node_id"],
            "node_type": example["node_type"],
            "mastery_band": band,
            "strongest_role": role,
            "warning_code": "WARN_ROLE_HIGH_BAND_LOW_AUTHORITY_ROLE",
            "audit_scope": "pre_guardrail",
            "guarded_mastery_band": example.get("after_band"),
        }
        role_risk_records.append(finding)
        warnings.append(
            f"{finding['warning_code']}: pre-guardrail {example['learner_id']} {example['node_id']} strongest role {role} with mastery_band {band}"
        )
    return warnings, role_risk_records


def audit_event_type_risks(records, per_record_entries):
    warnings = []
    for record in records:
        key = (record["learner_id"], record["node_id"])
        entries = per_record_entries.get(key, [])
        if not entries:
            continue
        strongest = strongest_entry(entries)
        event_type = strongest["event_type"]
        role = strongest["role"]
        band = record["mastery_band"]
        if event_type == "manual_parent_input" and band in {"mastered", "automatic"}:
            warnings.append(
                f"WARN_EVENT_TYPE_PARENT_HIGH_BAND: {record['learner_id']} {record['node_id']} reached {band} from manual_parent_input"
            )
        if event_type == "reading" and role != "primary_target" and band in {"mastered", "automatic"}:
            warnings.append(
                f"WARN_EVENT_TYPE_READING_INDIRECT_HIGH_BAND: {record['learner_id']} {record['node_id']} reached {band} from indirect reading evidence"
            )
        if event_type == "listening" and role != "primary_target" and band in {"mastered", "automatic"}:
            warnings.append(
                f"WARN_EVENT_TYPE_LISTENING_INDIRECT_HIGH_BAND: {record['learner_id']} {record['node_id']} reached {band} from indirect listening evidence"
            )
        if event_type == "manual_teacher_input" and role in {"diagnostic_signal", "review_signal"} and band in {"mastered", "automatic"}:
            warnings.append(
                f"WARN_EVENT_TYPE_TEACHER_DIAGNOSTIC_HIGH_BAND: {record['learner_id']} {record['node_id']} reached {band} from manual_teacher_input {role}"
            )
    return warnings


def audit_ratio_risks(records, per_record_entries):
    warnings = []
    ratio_risk_records = []
    for record in records:
        key = (record["learner_id"], record["node_id"])
        entries = per_record_entries.get(key, [])
        if not entries:
            continue
        strongest = strongest_entry(entries)
        if (
            record["exposure_count"] == 1
            and record["mastery_score"] >= 0.50
            and strongest["role"] != "primary_target"
        ):
            finding = {
                "learner_id": record["learner_id"],
                "node_id": record["node_id"],
                "node_type": record["node_type"],
                "mastery_score": record["mastery_score"],
                "mastery_band": record["mastery_band"],
                "strongest_role": strongest["role"],
                "event_type": strongest["event_type"],
                "warning_code": "WARN_RATIO_OVERSTATEMENT_RISK",
            }
            ratio_risk_records.append(finding)
            warnings.append(
                f"{finding['warning_code']}: {record['learner_id']} {record['node_id']} exposure_count=1 mastery_score={record['mastery_score']} strongest_role={strongest['role']}"
            )
        if (
            record["exposure_count"] == 1
            and record["node_type"] in DERIVED_NODE_TYPES
            and record["mastery_band"] in {"functional", "mastered", "automatic"}
        ):
            finding = {
                "learner_id": record["learner_id"],
                "node_id": record["node_id"],
                "node_type": record["node_type"],
                "mastery_band": record["mastery_band"],
                "warning_code": "WARN_SINGLE_EVENT_DERIVED_NODE_MASTERY",
            }
            ratio_risk_records.append(finding)
            warnings.append(
                f"{finding['warning_code']}: {record['learner_id']} {record['node_id']} node_type={record['node_type']} mastery_band={record['mastery_band']}"
            )
    return warnings, ratio_risk_records


def audit_pre_guardrail_ratio_risks(guardrail_summary):
    warnings = []
    ratio_risk_records = []
    for example in guardrail_summary.get("before_after_examples", []):
        if (
            example.get("exposure_count") == 1
            and example.get("base_mastery_score", 0) >= 0.50
            and example.get("strongest_role") != "primary_target"
        ):
            finding = {
                "learner_id": example["learner_id"],
                "node_id": example["node_id"],
                "node_type": example["node_type"],
                "mastery_score": example["base_mastery_score"],
                "mastery_band": example["before_band"],
                "strongest_role": example["strongest_role"],
                "warning_code": "WARN_RATIO_OVERSTATEMENT_RISK",
                "audit_scope": "pre_guardrail",
                "guarded_mastery_score": example.get("guarded_mastery_score"),
                "guarded_mastery_band": example.get("after_band"),
            }
            ratio_risk_records.append(finding)
            warnings.append(
                f"{finding['warning_code']}: pre-guardrail {example['learner_id']} {example['node_id']} exposure_count=1 mastery_score={example['base_mastery_score']} strongest_role={example['strongest_role']}"
            )
        if (
            example.get("exposure_count") == 1
            and example.get("node_type") in DERIVED_NODE_TYPES
            and example.get("before_band") in {"functional", "mastered", "automatic"}
        ):
            finding = {
                "learner_id": example["learner_id"],
                "node_id": example["node_id"],
                "node_type": example["node_type"],
                "mastery_band": example["before_band"],
                "warning_code": "WARN_SINGLE_EVENT_DERIVED_NODE_MASTERY",
                "audit_scope": "pre_guardrail",
                "guarded_mastery_band": example.get("after_band"),
            }
            ratio_risk_records.append(finding)
            warnings.append(
                f"{finding['warning_code']}: pre-guardrail {example['learner_id']} {example['node_id']} node_type={example['node_type']} mastery_band={example['before_band']}"
            )
    return warnings, ratio_risk_records


def audit_review_due(records):
    findings = []
    blockers = []
    warnings = []
    for record in records:
        expected = expected_review_due_at(record)
        actual = record["review_due_at"]
        findings.append(
            {
                "learner_id": record["learner_id"],
                "node_id": record["node_id"],
                "mastery_band": record["mastery_band"],
                "expected_review_due_at": expected,
                "actual_review_due_at": actual,
                "status": "PASS" if expected == actual else "BLOCKER",
            }
        )
        if expected != actual:
            blockers.append(
                f"review_due_at mismatch for {record['learner_id']} {record['node_id']}: expected {expected}, actual {actual}"
            )
        if record["mastery_band"] == "unknown" and actual is not None:
            blockers.append(f"unknown record emitted non-null review_due_at: {record['learner_id']} {record['node_id']}")
        if actual is not None and not has_valid_review_anchor(record):
            blockers.append(
                f"record without last_success_at emitted review_due_at outside allowed policy: {record['learner_id']} {record['node_id']}"
            )
    warnings.append("WARN_DECAY_NOT_MODELED: decay_adjusted_score equals mastery_score for all S9E V1 records; true retention decay is not modeled yet")
    return warnings, blockers, findings


def audit_boundary(records):
    blockers = []
    findings = []
    for record in records:
        present = sorted(FORBIDDEN_FIELDS.intersection(record.keys()))
        status = "PASS" if not present else "BLOCKER"
        findings.append(
            {
                "learner_id": record["learner_id"],
                "node_id": record["node_id"],
                "status": status,
                "forbidden_fields_present": present,
            }
        )
        if present:
            blockers.append(
                f"forbidden planner/ranking fields present for {record['learner_id']} {record['node_id']}: {present}"
            )
    return blockers, findings


def run_audit(report_path=AUDIT_REPORT_PATH):
    files_checked = [str(path.relative_to(BASE_DIR)).replace("\\", "/") for path in get_required_files()]
    blockers = []
    warnings = []

    for required_path in get_required_files():
        if not required_path.exists():
            blockers.append(f"missing required file: {required_path.relative_to(BASE_DIR)}")

    if blockers:
        raise AuditError(blockers[0])

    sample_payload = load_json(SAMPLE_EVENTS_PATH)
    learner_state_payload = load_json(LEARNER_STATE_PATH)
    summary_payload = load_json(SUMMARY_PATH)
    guardrail_summary_payload = load_json(GUARDRAIL_SUMMARY_PATH) if GUARDRAIL_SUMMARY_PATH.exists() else {}

    validate_event_collection(sample_payload)
    validate_learner_state_collection(learner_state_payload)
    validate_builder_output(learner_state_path=LEARNER_STATE_PATH, summary_path=SUMMARY_PATH)

    events = sample_payload["events"]
    records = learner_state_payload["learner_state_records"]
    event_map, per_record_entries = build_event_maps(events)

    total_flattened_entries = sum(len(event["node_refs"]) for event in events)
    learner_ids = {record["learner_id"] for record in records}
    node_type_counts = dict(sorted(Counter(record["node_type"] for record in records).items()))
    mastery_band_counts = dict(sorted(Counter(record["mastery_band"] for record in records).items()))

    seen_pairs = set()
    seen_idempotency_keys = set()
    duplicate_pair_count = 0
    duplicate_output_idempotency_key_count = 0
    for record in records:
        pair = (record["learner_id"], record["node_id"])
        if pair in seen_pairs:
            duplicate_pair_count += 1
        seen_pairs.add(pair)

        idem_key = record["processing_idempotency_key"]
        if idem_key in seen_idempotency_keys:
            duplicate_output_idempotency_key_count += 1
        seen_idempotency_keys.add(idem_key)

    if summary_payload.get("total_events") != len(events):
        blockers.append("summary total_events mismatch")
    if summary_payload.get("total_flattened_entries") != total_flattened_entries:
        blockers.append("summary total_flattened_entries mismatch")
    if summary_payload.get("total_learner_state_records") != len(records):
        blockers.append("summary total_learner_state_records mismatch")
    if summary_payload.get("learner_count") != len(learner_ids):
        blockers.append("summary learner_count mismatch")
    if summary_payload.get("node_type_counts") != node_type_counts:
        blockers.append("summary node_type_counts mismatch")
    if summary_payload.get("mastery_band_counts") != mastery_band_counts:
        blockers.append("summary mastery_band_counts mismatch")
    if duplicate_pair_count != 0:
        blockers.append("duplicate learner_id + node_id pairs detected")
    if duplicate_output_idempotency_key_count != 0:
        blockers.append("duplicate output processing_idempotency_key values detected")

    james_nodes = {record["node_id"] for record in records if record["learner_id"] == "learner:james"}
    cyndi_nodes = {record["node_id"] for record in records if record["learner_id"] == "learner:cyndi"}
    require(james_nodes and cyndi_nodes, "expected learner:james and learner:cyndi records to exist")

    role_warnings, role_risk_records = audit_role_risks(records, per_record_entries)
    event_type_warnings = audit_event_type_risks(records, per_record_entries)
    ratio_warnings, ratio_risk_records = audit_ratio_risks(records, per_record_entries)
    pre_guardrail_role_warnings, pre_guardrail_role_risk_records = audit_pre_guardrail_role_risks(guardrail_summary_payload)
    pre_guardrail_ratio_warnings, pre_guardrail_ratio_risk_records = audit_pre_guardrail_ratio_risks(guardrail_summary_payload)
    review_warnings, review_blockers, review_due_findings = audit_review_due(records)
    boundary_blockers, boundary_findings = audit_boundary(records)

    warnings.extend(role_warnings)
    warnings.extend(event_type_warnings)
    warnings.extend(ratio_warnings)
    warnings.extend(pre_guardrail_role_warnings)
    warnings.extend(pre_guardrail_ratio_warnings)
    warnings.extend(review_warnings)
    warnings.append("WARN_EMPTY_LOG_LIMITATION: S9C collection is non-empty, so zero-event global cold start is not naturally supported")
    role_risk_records.extend(pre_guardrail_role_risk_records)
    ratio_risk_records.extend(pre_guardrail_ratio_risk_records)

    blockers.extend(review_blockers)
    blockers.extend(boundary_blockers)

    strongest_role_by_record = {}
    for record in records:
        entries = per_record_entries.get((record["learner_id"], record["node_id"]), [])
        strongest_role_by_record[f"{record['learner_id']}|{record['node_id']}"] = strongest_entry(entries)["role"] if entries else None

    metrics = {
        "total_events": len(events),
        "total_flattened_entries": total_flattened_entries,
        "total_learner_state_records": len(records),
        "learner_count": len(learner_ids),
        "node_type_counts": node_type_counts,
        "mastery_band_counts": mastery_band_counts,
        "duplicate_learner_node_pair_count": duplicate_pair_count,
        "duplicate_output_processing_idempotency_key_count": duplicate_output_idempotency_key_count,
        "learner_isolation": {
            "learner_james_record_count": sum(1 for record in records if record["learner_id"] == "learner:james"),
            "learner_cyndi_record_count": sum(1 for record in records if record["learner_id"] == "learner:cyndi"),
            "shared_node_ids_between_james_and_cyndi": sorted(james_nodes.intersection(cyndi_nodes)),
        },
        "strongest_role_by_record": strongest_role_by_record,
    }

    recommendations = [
        "Introduce role-based caps or dampening for coverage_signal, supporting_context, diagnostic_signal, review_signal, and prerequisite-derived mastery in S9G/S9H.",
        "Consider requiring multiple events before derived node types such as theme, morphology, skill, assessment, and dialogue can reach stable functional-or-higher mastery bands.",
        "Design true retention decay in a future task instead of keeping decay_adjusted_score equal to mastery_score.",
        "Define a zero-event cold-start strategy or revise the non-empty S9C collection constraint for future global empty-log handling.",
    ]

    status = "BLOCKER" if blockers else ("PASS_WITH_WARNINGS" if warnings else "PASS")
    report = {
        "contract_version": "ULGA-S9F",
        "status": status,
        "files_checked": files_checked,
        "metrics": metrics,
        "warnings": warnings,
        "blockers": blockers,
        "role_risk_records": role_risk_records,
        "ratio_risk_records": ratio_risk_records,
        "review_due_findings": review_due_findings,
        "boundary_findings": boundary_findings,
        "recommendations": recommendations,
    }
    write_json(report_path, report)
    return report


def main():
    try:
        report = run_audit()
    except Exception as exc:
        print(f"Learner state builder QA audit: FAIL - {exc}")
        return 1
    print(f"Learner state builder QA audit: {report['status']}")
    print(f"Built {AUDIT_REPORT_PATH.relative_to(BASE_DIR)}")
    print(f"Warnings: {len(report['warnings'])}")
    print(f"Blockers: {len(report['blockers'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
