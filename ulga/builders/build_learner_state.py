import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.validators.validate_evidence_event_schema import validate_event_collection
from ulga.validators.validate_learner_state_schema import validate_learner_state_collection


DEFAULT_INPUT_PATH = BASE_DIR / "ulga" / "learner_state" / "sample_evidence_events.json"
DEFAULT_OUTPUT_PATH = BASE_DIR / "ulga" / "learner_state" / "learner_state.json"
DEFAULT_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "learner_state_builder_summary.json"
DEFAULT_GUARDRAIL_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "learner_state_guardrail_summary.json"
DEFAULT_DIALOGUE_TIGHTENING_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "dialogue_exception_tightening_summary.json"

EVENT_TYPE_MULTIPLIERS = {
    "worksheet": 0.90,
    "quiz": 1.00,
    "reading": 0.65,
    "dialogue": 1.05,
    "speaking": 1.10,
    "writing": 1.10,
    "listening": 0.70,
    "manual_parent_input": 0.45,
    "manual_teacher_input": 0.95,
}

ROLE_MULTIPLIERS = {
    "primary_target": 1.00,
    "supporting_context": 0.50,
    "prerequisite": 0.40,
    "diagnostic_signal": 0.35,
    "review_signal": 0.30,
    "coverage_signal": 0.20,
}

MASTERY_BANDS = (
    ("unknown", 0.00, 0.10),
    ("seen", 0.10, 0.25),
    ("practicing", 0.25, 0.50),
    ("functional", 0.50, 0.70),
    ("mastered", 0.70, 0.90),
    ("automatic", 0.90, 1.0000001),
)

SUCCESS_THRESHOLD = 0.60
SANITIZE_RE = re.compile(r"[^A-Za-z0-9]+")
ROLE_CEILINGS = {
    "primary_target": 1.00,
    "supporting_context": 0.69,
    "prerequisite": 0.69,
    "coverage_signal": 0.24,
    "diagnostic_signal": 0.49,
    "review_signal": 0.24,
}
NODE_TYPE_CEILINGS = {
    "theme": 0.49,
    "morphology": 0.49,
    "skill": 0.49,
    "assessment": 0.49,
    "dialogue": 0.69,
    "reading": 0.69,
    "exercise_type": 0.24,
    "grammar": 1.00,
    "vocabulary": 1.00,
    "chunk": 1.00,
    "sentence_pattern": 1.00,
}


class BuildError(Exception):
    pass


@dataclass(frozen=True)
class FlattenedEntry:
    event_id: str
    learner_id: str
    node_id: str
    node_type: str
    event_timestamp: str
    event_type: str
    role: str
    effective_strength: float
    weighted_success: float
    effective_normalized_score: float
    event_confidence: float


def get_strongest_entry(entries):
    return max(entries, key=lambda entry: (entry.effective_strength, entry.event_id))


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json_atomic(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8", newline="\n") as tmp_file:
        json.dump(payload, tmp_file, indent=2, ensure_ascii=True, sort_keys=False)
        tmp_file.write("\n")
        temp_path = Path(tmp_file.name)
    last_error = None
    for attempt in range(5):
        try:
            temp_path.replace(path)
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(0.05 * (attempt + 1))
    raise last_error


def parse_timestamp(value):
    if not isinstance(value, str):
        raise BuildError(f"timestamp must be a string, got {type(value).__name__}")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise BuildError(f"malformed timestamp: {value}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_timestamp(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sanitize_key_part(value):
    sanitized = SANITIZE_RE.sub("_", value).strip("_")
    return sanitized or "unknown"


def round4(value):
    return round(float(value), 4)


def detect_duplicates(events):
    event_id_counts = Counter(event["event_id"] for event in events)
    idempotency_counts = Counter(event["processing_idempotency_key"] for event in events)
    duplicate_event_id_count = sum(count - 1 for count in event_id_counts.values() if count > 1)
    duplicate_idem_count = sum(count - 1 for count in idempotency_counts.values() if count > 1)
    return duplicate_event_id_count, duplicate_idem_count


def ensure_no_duplicates(events):
    seen_event_ids = set()
    seen_idempotency_keys = set()
    for event in events:
        event_id = event["event_id"]
        if event_id in seen_event_ids:
            raise BuildError(f"duplicate event_id detected: {event_id}")
        seen_event_ids.add(event_id)

        idem_key = event["processing_idempotency_key"]
        if idem_key in seen_idempotency_keys:
            raise BuildError(f"duplicate processing_idempotency_key detected: {idem_key}")
        seen_idempotency_keys.add(idem_key)


def get_build_timestamp(events, explicit_build_time=None):
    if explicit_build_time:
        return parse_timestamp(explicit_build_time)
    latest = max(parse_timestamp(event["timestamp"]) for event in events)
    return latest


def get_mastery_band(score):
    for band, min_score, max_score in MASTERY_BANDS:
        if min_score <= score < max_score:
            return band
    if score == 1.0:
        return "automatic"
    raise BuildError(f"unable to map mastery band for score: {score}")


def compute_review_due_at(mastery_band, last_seen_at, last_success_at):
    if mastery_band == "unknown":
        return None
    if mastery_band == "seen":
        anchor = last_seen_at
        offset_days = 2
    elif mastery_band == "practicing":
        anchor = last_success_at or last_seen_at
        offset_days = 3
    elif mastery_band == "functional":
        anchor = last_success_at
        offset_days = 7
    elif mastery_band == "mastered":
        anchor = last_success_at
        offset_days = 14
    elif mastery_band == "automatic":
        anchor = last_success_at
        offset_days = 30
    else:
        raise BuildError(f"unsupported mastery band: {mastery_band}")
    if anchor is None:
        return None
    return format_timestamp(anchor + timedelta(days=offset_days))


def flatten_events(events):
    flattened_entries = []
    for event in events:
        event_multiplier = EVENT_TYPE_MULTIPLIERS[event["event_type"]]
        event_confidence = event["confidence"]["value"]
        event_score = event["score"]
        event_timestamp = event["timestamp"]
        normalized_score = event_score * event_multiplier * event_confidence
        for node_ref in event["node_refs"]:
            role_multiplier = ROLE_MULTIPLIERS[node_ref["role"]]
            effective_strength = node_ref["weight"] * role_multiplier * event_multiplier * event_confidence
            flattened_entries.append(
                FlattenedEntry(
                    event_id=event["event_id"],
                    learner_id=event["learner_id"],
                    node_id=node_ref["node_id"],
                    node_type=node_ref["node_type"],
                    event_timestamp=event_timestamp,
                    event_type=event["event_type"],
                    role=node_ref["role"],
                    effective_strength=effective_strength,
                    weighted_success=event_score * effective_strength,
                    effective_normalized_score=normalized_score,
                    event_confidence=event_confidence,
                )
            )
    return flattened_entries


def apply_guardrails(base_mastery_score, node_type, strongest_role, exposure_count, successful_event_count, successful_primary_target_event_count, confidence_value):
    reasons = []
    ceilings = []

    role_ceiling = ROLE_CEILINGS[strongest_role]
    ceilings.append(role_ceiling)
    if base_mastery_score > role_ceiling:
        reasons.append("role_ceiling")

    node_type_ceiling = NODE_TYPE_CEILINGS[node_type]
    if node_type == "sentence_pattern" and strongest_role != "primary_target":
        node_type_ceiling = min(node_type_ceiling, role_ceiling)
    ceilings.append(node_type_ceiling)
    if base_mastery_score > node_type_ceiling:
        reasons.append("node_type_ceiling")

    single_event_ceiling = 1.00
    if exposure_count == 1 and strongest_role != "primary_target":
        if node_type == "reading" and strongest_role == "supporting_context":
            single_event_ceiling = 0.69
        else:
            single_event_ceiling = 0.49
        ceilings.append(single_event_ceiling)
        if base_mastery_score > single_event_ceiling:
            reasons.append("single_event_ceiling")

    mastered_ceiling = 1.00
    if base_mastery_score >= 0.70:
        mastered_allowed = (
            successful_event_count >= 2
            or (
                successful_event_count >= 1
                and strongest_role == "primary_target"
                and confidence_value >= 0.85
            )
        )
        if not mastered_allowed:
            mastered_ceiling = 0.69
            reasons.append("mastered_threshold")
    ceilings.append(mastered_ceiling)

    automatic_ceiling = 1.00
    if base_mastery_score >= 0.90:
        automatic_allowed = (
            successful_event_count >= 3
            and successful_primary_target_event_count >= 1
            and confidence_value >= 0.85
        )
        if not automatic_allowed:
            automatic_ceiling = 0.89
            reasons.append("automatic_threshold")
    ceilings.append(automatic_ceiling)

    guardrail_ceiling = min(ceilings)
    guarded_mastery_score = round4(min(base_mastery_score, guardrail_ceiling))
    return guarded_mastery_score, guardrail_ceiling, reasons


def build_learner_state_payload(events, build_timestamp):
    flattened_entries = flatten_events(events)
    grouped_entries = defaultdict(list)
    event_lookup = {
        event["event_id"]: (parse_timestamp(event["timestamp"]), event["event_id"])
        for event in events
    }

    for entry in flattened_entries:
        grouped_entries[(entry.learner_id, entry.node_id, entry.node_type)].append(entry)

    build_timestamp_text = format_timestamp(build_timestamp)
    build_timestamp_sanitized = build_timestamp_text.replace("-", "").replace(":", "")
    records = []
    guardrail_examples = []
    guardrail_reason_counts = Counter()
    role_ceiling_hits = 0
    node_type_ceiling_hits = 0
    single_event_hits = 0
    mastered_threshold_hits = 0
    automatic_threshold_hits = 0

    for learner_id, node_id, node_type in sorted(grouped_entries, key=lambda key: (key[0], key[2], key[1])):
        entries = grouped_entries[(learner_id, node_id, node_type)]
        weighted_success_sum = sum(entry.weighted_success for entry in entries)
        weighted_exposure_sum = sum(entry.effective_strength for entry in entries)
        base_mastery_score = 0.0 if weighted_exposure_sum == 0 else weighted_success_sum / weighted_exposure_sum
        base_mastery_score = round4(max(0.0, min(1.0, base_mastery_score)))

        unique_event_ids = {
            entry.event_id for entry in entries
        }
        exposure_count = len(unique_event_ids)
        correct_event_ids = {
            entry.event_id for entry in entries if entry.effective_normalized_score >= SUCCESS_THRESHOLD
        }
        incorrect_event_ids = unique_event_ids - correct_event_ids
        correct_count = len(correct_event_ids)
        incorrect_count = len(incorrect_event_ids)

        last_seen_at = max(parse_timestamp(entry.event_timestamp) for entry in entries)
        success_timestamps = [
            parse_timestamp(entry.event_timestamp)
            for entry in entries
            if entry.effective_normalized_score >= SUCCESS_THRESHOLD
        ]
        last_success_at = max(success_timestamps) if success_timestamps else None

        confidence_weight_sum = sum(entry.event_confidence * entry.effective_strength for entry in entries)
        confidence_value = 0.0 if weighted_exposure_sum == 0 else confidence_weight_sum / weighted_exposure_sum
        confidence_value = round4(max(0.0, min(1.0, confidence_value)))
        strongest_entry = get_strongest_entry(entries)
        strongest_role = strongest_entry.role
        successful_primary_target_event_count = len(
            {
                entry.event_id
                for entry in entries
                if entry.effective_normalized_score >= SUCCESS_THRESHOLD and entry.role == "primary_target"
            }
        )
        mastery_score, guardrail_ceiling, guardrail_reasons = apply_guardrails(
            base_mastery_score=base_mastery_score,
            node_type=node_type,
            strongest_role=strongest_role,
            exposure_count=exposure_count,
            successful_event_count=correct_count,
            successful_primary_target_event_count=successful_primary_target_event_count,
            confidence_value=confidence_value,
        )
        mastery_band = get_mastery_band(mastery_score)

        for reason in guardrail_reasons:
            guardrail_reason_counts[reason] += 1
        role_ceiling_hits += int("role_ceiling" in guardrail_reasons)
        node_type_ceiling_hits += int("node_type_ceiling" in guardrail_reasons)
        single_event_hits += int("single_event_ceiling" in guardrail_reasons)
        mastered_threshold_hits += int("mastered_threshold" in guardrail_reasons)
        automatic_threshold_hits += int("automatic_threshold" in guardrail_reasons)

        evidence_refs = [
            event_id
            for _, event_id in sorted(event_lookup[event_id] for event_id in unique_event_ids)
        ]

        record = {
            "learner_id": learner_id,
            "node_id": node_id,
            "node_type": node_type,
            "mastery_score": mastery_score,
            "mastery_band": mastery_band,
            "exposure_count": exposure_count,
            "correct_count": correct_count,
            "incorrect_count": incorrect_count,
            "last_seen_at": format_timestamp(last_seen_at),
            "last_success_at": format_timestamp(last_success_at) if last_success_at else None,
            "evidence_refs": evidence_refs,
            "decay_adjusted_score": mastery_score,
            "review_due_at": compute_review_due_at(mastery_band, last_seen_at, last_success_at),
            "confidence": {
                "value": confidence_value,
                "method": "builder_weighted_average",
                "notes": [
                    "Computed by ULGA-S9E LearnerStateBuilder V1"
                ],
            },
            "source": {
                "authority_name": "LearnerStateAuthority",
                "derivation": "learner_runtime_full_rebuild",
                "aggregation_version": "ULGA-S9E.v1",
            },
            "state_updated_at": build_timestamp_text,
            "processing_idempotency_key": (
                f"learner_state:{sanitize_key_part(learner_id)}:{sanitize_key_part(node_id)}:{build_timestamp_sanitized}"
            ),
        }
        records.append(record)
        if mastery_score != base_mastery_score:
            guardrail_examples.append(
                {
                    "learner_id": learner_id,
                    "node_id": node_id,
                    "node_type": node_type,
                    "strongest_role": strongest_role,
                    "base_mastery_score": base_mastery_score,
                    "guarded_mastery_score": mastery_score,
                    "guardrail_ceiling": guardrail_ceiling,
                    "before_band": get_mastery_band(base_mastery_score),
                    "after_band": mastery_band,
                    "exposure_count": exposure_count,
                    "successful_event_count": correct_count,
                    "confidence": confidence_value,
                    "guardrail_reasons": sorted(set(guardrail_reasons)),
                }
            )

    payload = {
        "contract_version": "ULGA-S9C",
        "learner_state_records": records,
    }
    summary = build_summary(events, flattened_entries, records, build_timestamp_text)
    guardrail_summary = build_guardrail_summary(
        records=records,
        guardrail_examples=guardrail_examples,
        guardrail_reason_counts=guardrail_reason_counts,
        role_ceiling_hits=role_ceiling_hits,
        node_type_ceiling_hits=node_type_ceiling_hits,
        single_event_hits=single_event_hits,
        mastered_threshold_hits=mastered_threshold_hits,
        automatic_threshold_hits=automatic_threshold_hits,
    )
    return payload, summary, guardrail_summary


def build_summary(events, flattened_entries, records, build_timestamp_text):
    learner_ids = {record["learner_id"] for record in records}
    node_type_counts = Counter(record["node_type"] for record in records)
    mastery_band_counts = Counter(record["mastery_band"] for record in records)
    duplicate_event_id_count, duplicate_processing_idempotency_key_count = detect_duplicates(events)
    return {
        "contract_version": "ULGA-S9E",
        "source_event_file": "ulga/learner_state/sample_evidence_events.json",
        "output_file": "ulga/learner_state/learner_state.json",
        "total_events": len(events),
        "total_flattened_entries": len(flattened_entries),
        "total_learner_state_records": len(records),
        "learner_count": len(learner_ids),
        "node_type_counts": dict(sorted(node_type_counts.items())),
        "mastery_band_counts": dict(sorted(mastery_band_counts.items())),
        "duplicate_event_id_count": duplicate_event_id_count,
        "duplicate_processing_idempotency_key_count": duplicate_processing_idempotency_key_count,
        "build_timestamp": build_timestamp_text,
        "status": "PASS",
    }


def build_guardrail_summary(
    records,
    guardrail_examples,
    guardrail_reason_counts,
    role_ceiling_hits,
    node_type_ceiling_hits,
    single_event_hits,
    mastered_threshold_hits,
    automatic_threshold_hits,
):
    return {
        "contract_version": "ULGA-S9H",
        "builder_version": "ULGA-S9H.v1",
        "records_evaluated": len(records),
        "records_modified_by_guardrails": len(guardrail_examples),
        "guardrail_reason_counts": dict(sorted(guardrail_reason_counts.items())),
        "role_ceiling_hits": role_ceiling_hits,
        "node_type_ceiling_hits": node_type_ceiling_hits,
        "single_event_hits": single_event_hits,
        "mastered_threshold_hits": mastered_threshold_hits,
        "automatic_threshold_hits": automatic_threshold_hits,
        "before_after_examples": guardrail_examples,
        "status": "PASS",
    }


def build_dialogue_exception_tightening_summary(records, guardrail_summary):
    dialogue_records = [record for record in records if record["node_type"] == "dialogue"]
    dialogue_examples = [
        example
        for example in guardrail_summary["before_after_examples"]
        if example["node_type"] == "dialogue"
    ]
    return {
        "contract_version": "ULGA-S9K",
        "records_evaluated": len(records),
        "dialogue_records_evaluated": len(dialogue_records),
        "records_modified": len(dialogue_examples),
        "before_after_examples": dialogue_examples,
        "status": "PASS",
    }


def run_build(
    input_path=DEFAULT_INPUT_PATH,
    output_path=DEFAULT_OUTPUT_PATH,
    summary_path=DEFAULT_SUMMARY_PATH,
    guardrail_summary_path=DEFAULT_GUARDRAIL_SUMMARY_PATH,
    dialogue_tightening_summary_path=DEFAULT_DIALOGUE_TIGHTENING_SUMMARY_PATH,
    build_time=None,
):
    payload = load_json(input_path)
    validate_event_collection(payload)
    events = payload["events"]
    ensure_no_duplicates(events)
    events = sorted(events, key=lambda event: (parse_timestamp(event["timestamp"]), event["event_id"]))
    build_timestamp = get_build_timestamp(events, explicit_build_time=build_time)

    learner_state_payload, summary_payload, guardrail_summary_payload = build_learner_state_payload(events, build_timestamp)
    dialogue_tightening_summary_payload = build_dialogue_exception_tightening_summary(
        learner_state_payload["learner_state_records"],
        guardrail_summary_payload,
    )
    validate_learner_state_collection(learner_state_payload)
    write_json_atomic(output_path, learner_state_payload)
    write_json_atomic(summary_path, summary_payload)
    write_json_atomic(guardrail_summary_path, guardrail_summary_payload)
    write_json_atomic(dialogue_tightening_summary_path, dialogue_tightening_summary_payload)

    # Re-read persisted file to ensure the written artifact still validates.
    persisted_payload = load_json(output_path)
    validate_learner_state_collection(persisted_payload)
    return learner_state_payload, summary_payload


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Build ULGA learner state from evidence events.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT_PATH), help="Path to evidence event collection JSON")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Path to learner state JSON")
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY_PATH), help="Path to builder summary JSON")
    parser.add_argument("--guardrail-summary", default=str(DEFAULT_GUARDRAIL_SUMMARY_PATH), help="Path to learner state guardrail summary JSON")
    parser.add_argument("--dialogue-tightening-summary", default=str(DEFAULT_DIALOGUE_TIGHTENING_SUMMARY_PATH), help="Path to dialogue exception tightening summary JSON")
    parser.add_argument("--build-time", default=None, help="Override deterministic build timestamp with ISO-like time")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    input_path = Path(args.input)
    output_path = Path(args.output)
    summary_path = Path(args.summary)
    guardrail_summary_path = Path(args.guardrail_summary)
    dialogue_tightening_summary_path = Path(args.dialogue_tightening_summary)
    try:
        learner_state_payload, summary_payload = run_build(
            input_path=input_path,
            output_path=output_path,
            summary_path=summary_path,
            guardrail_summary_path=guardrail_summary_path,
            dialogue_tightening_summary_path=dialogue_tightening_summary_path,
            build_time=args.build_time,
        )
    except Exception as exc:
        print(f"Learner state build: FAIL - {exc}")
        return 1

    print("Learner state build: PASS")
    print(f"Built {output_path.relative_to(BASE_DIR)}")
    print(f"Built {summary_path.relative_to(BASE_DIR)}")
    print(f"Built {guardrail_summary_path.relative_to(BASE_DIR)}")
    print(f"Built {dialogue_tightening_summary_path.relative_to(BASE_DIR)}")
    print(f"Total learner state records: {len(learner_state_payload['learner_state_records'])}")
    print(f"Build timestamp: {summary_payload['build_timestamp']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
