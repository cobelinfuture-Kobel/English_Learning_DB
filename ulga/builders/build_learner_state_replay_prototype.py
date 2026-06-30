import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = BASE_DIR / "ulga" / "learner_state" / "prototype"
DEFAULT_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "learner_state_replay_prototype_summary.json"
DEFAULT_REDUCER_VERSION = "ULGA-S9Z6-prototype"
SUPPORTED_NODE_GROUPS = ("vocabulary", "grammar", "pattern", "chunk", "theme")


class ReplayBuildError(Exception):
    pass


def load_events(input_path: Path) -> list[dict]:
    with input_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("events"), list):
        return payload["events"]
    raise ReplayBuildError("Input JSON must be a list of events or an object containing an 'events' list.")


def parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise ReplayBuildError("Timestamp value must be a string.")

    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ReplayBuildError(f"Invalid timestamp: {value}") from exc

    if dt.tzinfo is None:
        raise ReplayBuildError(f"Timestamp must include timezone information: {value}")
    return dt.astimezone(timezone.utc)


def format_timestamp(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_event_timestamp(event: dict) -> str:
    occurred_at_utc = event.get("occurred_at_utc")
    if isinstance(occurred_at_utc, str):
        return format_timestamp(parse_timestamp(occurred_at_utc))

    occurred_at = event.get("occurred_at")
    return format_timestamp(parse_timestamp(occurred_at))


def sort_events_for_replay(events: list[dict]) -> list[dict]:
    sortable_events = []
    for input_index, event in enumerate(events):
        event_copy = dict(event)
        event_copy["input_index"] = input_index
        event_copy["occurred_at_utc"] = normalize_event_timestamp(event_copy)
        sortable_events.append(event_copy)

    return sorted(
        sortable_events,
        key=lambda event: (
            event["occurred_at_utc"],
            str(event.get("event_id", "")),
            event["input_index"],
        ),
    )


def filter_replayable_events(events: list[dict]) -> tuple[list[dict], list[dict]]:
    replayable = []
    excluded = []

    for event in events:
        quality_flags = event.get("quality_flags")
        if not isinstance(quality_flags, dict):
            quality_flags = {}

        if quality_flags.get("requires_review") is True:
            excluded.append(
                {
                    "event_id": event.get("event_id"),
                    "input_index": event.get("input_index"),
                    "reason": "quarantine",
                }
            )
            continue

        if quality_flags.get("valid_event") is False:
            excluded.append(
                {
                    "event_id": event.get("event_id"),
                    "input_index": event.get("input_index"),
                    "reason": "invalid",
                }
            )
            continue

        replayable.append(event)

    return replayable, excluded


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def round4(value: float) -> float:
    return round(float(value), 4)


def create_empty_node_record(learner_id: str, node_id: str, node_type: str) -> dict:
    return {
        "learner_id": learner_id,
        "node_id": node_id,
        "node_type": node_type,
        "exposure": {
            "count": 0,
            "first_seen_at": None,
            "last_seen_at": None,
            "source_types": [],
            "passive_count": 0,
            "active_count": 0,
        },
        "practice": {
            "attempt_count": 0,
            "first_try_correct_count": 0,
            "retry_count": 0,
            "hint_count": 0,
            "correct_count": 0,
            "incorrect_count": 0,
            "response_time_total_ms": 0,
            "average_response_time_ms": None,
            "latest_practice_at": None,
            "success_rate": None,
        },
        "assessment": {
            "attempt_count": 0,
            "score_total": 0.0,
            "max_score_total": 0.0,
            "success_rate": None,
            "latest_assessment_at": None,
            "retention_check_pass_count": 0,
            "retention_check_fail_count": 0,
        },
        "reinforcement": {
            "hint_count": 0,
            "retry_count": 0,
            "incorrect_count": 0,
            "weak_node_signal_count": 0,
            "reinforcement_need_score": 0.0,
        },
        "engagement": {
            "practice_started_count": 0,
            "practice_completed_count": 0,
            "content_completed_count": 0,
        },
        "mastery_projection": {
            "raw_score": 0.0,
            "band": "unknown",
            "confidence": "low",
        },
        "_latest_mastery_check_failed": False,
        "_latest_mastery_check_at": None,
    }


def update_first_last_seen(exposure: dict, occurred_at_utc: str) -> None:
    if exposure["first_seen_at"] is None or occurred_at_utc < exposure["first_seen_at"]:
        exposure["first_seen_at"] = occurred_at_utc
    if exposure["last_seen_at"] is None or occurred_at_utc > exposure["last_seen_at"]:
        exposure["last_seen_at"] = occurred_at_utc


def update_latest_value(container: dict, key: str, value: str) -> None:
    if container[key] is None or value > container[key]:
        container[key] = value


def update_practice_metrics(record: dict, event: dict) -> None:
    if event.get("event_type") not in {"answer_submitted", "retry_attempt", "hint_used"}:
        return

    attempt = event.get("attempt")
    if not isinstance(attempt, dict):
        return

    practice = record["practice"]
    occurred_at_utc = event["occurred_at_utc"]
    update_latest_value(practice, "latest_practice_at", occurred_at_utc)

    attempt_number = attempt.get("attempt_number")
    is_correct = attempt.get("is_correct")
    used_hint = attempt.get("used_hint") is True
    response_time_ms = attempt.get("response_time_ms")

    if event.get("event_type") == "hint_used":
        if used_hint:
            practice["hint_count"] += 1
        return

    practice["attempt_count"] += 1

    if attempt_number == 1 and is_correct is True and not used_hint:
        practice["first_try_correct_count"] += 1

    if event.get("event_type") == "retry_attempt" or (isinstance(attempt_number, int) and attempt_number > 1):
        practice["retry_count"] += 1

    if used_hint:
        practice["hint_count"] += 1

    if is_correct is True:
        practice["correct_count"] += 1
    elif is_correct is False:
        practice["incorrect_count"] += 1

    if isinstance(response_time_ms, int) and response_time_ms >= 0:
        practice["response_time_total_ms"] += response_time_ms

    if practice["attempt_count"] > 0:
        practice["average_response_time_ms"] = round4(
            practice["response_time_total_ms"] / practice["attempt_count"]
        )

    scored_attempts = practice["correct_count"] + practice["incorrect_count"]
    if scored_attempts > 0:
        practice["success_rate"] = round4(practice["correct_count"] / scored_attempts)


def update_assessment_metrics(record: dict, event: dict) -> None:
    if event.get("event_type") not in {"assessment_attempt", "mastery_check"}:
        return

    attempt = event.get("attempt")
    if not isinstance(attempt, dict):
        return

    score = attempt.get("score")
    max_score = attempt.get("max_score")
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        return
    if not isinstance(max_score, (int, float)) or isinstance(max_score, bool) or max_score <= 0:
        return

    assessment = record["assessment"]
    occurred_at_utc = event["occurred_at_utc"]
    assessment["attempt_count"] += 1
    assessment["score_total"] = round4(assessment["score_total"] + float(score))
    assessment["max_score_total"] = round4(assessment["max_score_total"] + float(max_score))
    update_latest_value(assessment, "latest_assessment_at", occurred_at_utc)
    assessment["success_rate"] = round4(assessment["score_total"] / assessment["max_score_total"])

    ratio = float(score) / float(max_score)
    if event.get("event_type") == "mastery_check":
        if ratio >= 0.7:
            assessment["retention_check_pass_count"] += 1
        else:
            assessment["retention_check_fail_count"] += 1
        record["_latest_mastery_check_at"] = occurred_at_utc
        record["_latest_mastery_check_failed"] = ratio < 0.7


def update_reinforcement_metrics(record: dict, event: dict) -> None:
    attempt = event.get("attempt")
    if not isinstance(attempt, dict):
        attempt = {}

    hint_signal = event.get("event_type") == "hint_used" or attempt.get("used_hint") is True
    retry_signal = event.get("event_type") == "retry_attempt" or (
        isinstance(attempt.get("attempt_number"), int) and attempt.get("attempt_number") > 1
    )
    incorrect_signal = event.get("event_type") == "answer_submitted" and attempt.get("is_correct") is False

    score = attempt.get("score")
    max_score = attempt.get("max_score")
    weak_assessment_signal = False
    if (
        event.get("event_type") in {"assessment_attempt", "mastery_check"}
        and isinstance(score, (int, float))
        and not isinstance(score, bool)
        and isinstance(max_score, (int, float))
        and not isinstance(max_score, bool)
        and max_score > 0
    ):
        weak_assessment_signal = (float(score) / float(max_score)) < 0.7

    reinforcement = record["reinforcement"]
    weak_signal = False

    if hint_signal:
        reinforcement["hint_count"] += 1
        weak_signal = True
    if retry_signal:
        reinforcement["retry_count"] += 1
        weak_signal = True
    if incorrect_signal or weak_assessment_signal:
        reinforcement["incorrect_count"] += 1
        weak_signal = True
    if weak_signal:
        reinforcement["weak_node_signal_count"] += 1

    reinforcement["reinforcement_need_score"] = round4(
        clamp(
            (reinforcement["hint_count"] * 0.2)
            + (reinforcement["retry_count"] * 0.15)
            + (reinforcement["incorrect_count"] * 0.25),
            0.0,
            1.0,
        )
    )


def update_engagement_metrics(record: dict, event: dict) -> None:
    engagement = record["engagement"]
    event_type = event.get("event_type")

    if event_type == "practice_started":
        engagement["practice_started_count"] += 1
    elif event_type == "practice_completed":
        engagement["practice_completed_count"] += 1
    elif event_type == "content_completed":
        engagement["content_completed_count"] += 1


def project_event_to_nodes(event: dict, state: dict) -> None:
    learner_id = event.get("learner_id")
    target_nodes = event.get("target_nodes")
    if not isinstance(target_nodes, dict):
        return

    exposure_flag = False
    evidence_flags = event.get("evidence_flags")
    if isinstance(evidence_flags, dict):
        exposure_flag = evidence_flags.get("counts_as_exposure") is True

    for node_group in SUPPORTED_NODE_GROUPS:
        node_ids = target_nodes.get(node_group)
        if not isinstance(node_ids, list):
            continue

        for node_id in node_ids:
            if not isinstance(node_id, str):
                continue

            key = (learner_id, node_group, node_id)
            if key not in state["node_map"]:
                state["node_map"][key] = create_empty_node_record(learner_id, node_id, node_group)

            record = state["node_map"][key]

            if exposure_flag:
                exposure = record["exposure"]
                exposure["count"] += 1
                update_first_last_seen(exposure, event["occurred_at_utc"])
                source_type = event.get("source_type")
                if isinstance(source_type, str) and source_type not in exposure["source_types"]:
                    exposure["source_types"].append(source_type)
                    exposure["source_types"].sort()
                if event.get("event_type") == "exposure_seen":
                    exposure["passive_count"] += 1
                else:
                    exposure["active_count"] += 1

            update_practice_metrics(record, event)
            update_assessment_metrics(record, event)
            update_reinforcement_metrics(record, event)
            update_engagement_metrics(record, event)
            state["learner_ids"].add(learner_id)


def compute_confidence(record: dict) -> str:
    assessment_attempts = record["assessment"]["attempt_count"]
    practice_attempts = record["practice"]["attempt_count"]
    exposure_count = record["exposure"]["count"]

    if assessment_attempts >= 2 or practice_attempts >= 4:
        return "high"
    if assessment_attempts >= 1 or practice_attempts >= 2 or exposure_count >= 3:
        return "medium"
    return "low"


def derive_mastery_projection(node_record: dict) -> dict:
    exposure = node_record["exposure"]
    practice = node_record["practice"]
    assessment = node_record["assessment"]
    reinforcement = node_record["reinforcement"]

    if node_record["node_type"] == "theme":
        band = "seen" if exposure["count"] > 0 else "unknown"
        return {
            "raw_score": 0.0,
            "band": band,
            "confidence": compute_confidence(node_record),
        }

    practice_success = practice["success_rate"] or 0.0
    assessment_success = assessment["success_rate"] or 0.0
    exposure_signal = (min(exposure["count"], 3) / 3.0) * 0.10
    practice_signal = practice_success * 0.45
    assessment_signal = assessment_success * 0.45
    penalty = min(
        0.4,
        (reinforcement["hint_count"] * 0.05)
        + (reinforcement["retry_count"] * 0.04)
        + (reinforcement["incorrect_count"] * 0.08),
    )
    raw_score = round4(clamp(practice_signal + assessment_signal + exposure_signal - penalty, 0.0, 1.0))

    latest_mastery_check_failed = node_record["_latest_mastery_check_failed"]
    assessment_attempt_count = assessment["attempt_count"]
    assessment_success_rate = assessment["success_rate"] or 0.0

    if latest_mastery_check_failed or reinforcement["reinforcement_need_score"] >= 0.6:
        band = "review_needed"
    elif (
        assessment_attempt_count >= 3
        and assessment_success_rate >= 0.85
        and assessment["retention_check_pass_count"] >= 2
    ):
        band = "automatic"
    elif raw_score >= 0.75 and assessment_attempt_count > 0 and not latest_mastery_check_failed:
        band = "mastered"
    elif raw_score >= 0.55 and assessment_attempt_count == 0:
        band = "functional"
    elif practice["attempt_count"] > 0 or assessment_attempt_count > 0:
        band = "practicing"
    elif exposure["count"] > 0:
        band = "seen"
    else:
        band = "unknown"

    return {
        "raw_score": raw_score,
        "band": band,
        "confidence": compute_confidence(node_record),
    }


def aggregate_node_evidence(events: list[dict]) -> dict:
    state = {
        "node_map": {},
        "learner_ids": set(),
    }
    for event in events:
        project_event_to_nodes(event, state)

    nodes = []
    for key in sorted(state["node_map"], key=lambda item: (item[0], item[1], item[2])):
        record = state["node_map"][key]
        record["mastery_projection"] = derive_mastery_projection(record)
        record.pop("_latest_mastery_check_failed", None)
        record.pop("_latest_mastery_check_at", None)
        nodes.append(record)

    return {
        "learner_ids": sorted(state["learner_ids"]),
        "nodes": nodes,
    }


def build_replay_projection(events: list[dict]) -> dict:
    sorted_events = sort_events_for_replay(events)
    replayable_events, excluded_events = filter_replayable_events(sorted_events)
    aggregate = aggregate_node_evidence(replayable_events)

    node_counts = {f"{group}_nodes": 0 for group in SUPPORTED_NODE_GROUPS}
    for node in aggregate["nodes"]:
        node_counts[f"{node['node_type']}_nodes"] += 1

    excluded_quarantine = sum(1 for event in excluded_events if event["reason"] == "quarantine")
    excluded_invalid = sum(1 for event in excluded_events if event["reason"] == "invalid")

    learner_state_projection = {
        "status": "PROTOTYPE",
        "prototype_warning": "This is not canonical learner_state.json.",
        "reducer_version": DEFAULT_REDUCER_VERSION,
        "learner_ids": aggregate["learner_ids"],
        "node_count": len(aggregate["nodes"]),
        "nodes": aggregate["nodes"],
    }

    mastery_graph_projection = {
        "status": "PROTOTYPE",
        "prototype_warning": "This is not canonical mastery_graph.json.",
        "reducer_version": DEFAULT_REDUCER_VERSION,
        "edges": [],
        "nodes": [
            {
                "learner_id": node["learner_id"],
                "node_id": node["node_id"],
                "node_type": node["node_type"],
                "mastery_projection": node["mastery_projection"],
            }
            for node in aggregate["nodes"]
        ],
    }

    summary = {
        "status": "PASS",
        "reducer_version": DEFAULT_REDUCER_VERSION,
        "input_summary": {
            "events_received": len(events),
            "events_replayed": len(replayable_events),
            "events_excluded_quarantine": excluded_quarantine,
            "events_excluded_invalid": excluded_invalid,
        },
        "node_projection_summary": {
            "total_nodes": len(aggregate["nodes"]),
            **node_counts,
        },
        "policy_summary": {
            "deterministic_replay_order": True,
            "complete_idempotency_claimed": False,
            "quarantine_excluded": True,
            "theme_only_mastery_blocked": True,
            "exposure_only_mastery_blocked": True,
            "canonical_learner_state_modified": False,
        },
        "excluded_events": excluded_events,
    }

    return {
        "learner_state_projection": learner_state_projection,
        "mastery_graph_projection": mastery_graph_projection,
        "summary": summary,
    }


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True, sort_keys=False)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def write_outputs(projection: dict, output_dir: Path, report_path: Path) -> None:
    learner_state_path = output_dir / "learner_state_projection_prototype.json"
    mastery_graph_path = output_dir / "mastery_graph_projection_prototype.json"

    write_json_atomic(learner_state_path, projection["learner_state_projection"])
    write_json_atomic(mastery_graph_path, projection["mastery_graph_projection"])
    write_json_atomic(report_path, projection["summary"])


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build ULGA learner state replay prototype outputs.")
    parser.add_argument("--input", required=True, help="Path to validated learner event collection JSON")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Prototype output directory")
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH), help="Prototype summary report path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    report_path = Path(args.report)

    if not input_path.exists():
        print(f"Replay prototype build: FAIL - input file does not exist: {input_path}")
        return 1

    try:
        events = load_events(input_path)
        projection = build_replay_projection(events)
        write_outputs(projection, output_dir, report_path)
    except Exception as exc:
        print(f"Replay prototype build: FAIL - {exc}")
        return 1

    learner_state_path = output_dir / "learner_state_projection_prototype.json"
    mastery_graph_path = output_dir / "mastery_graph_projection_prototype.json"
    print("Replay prototype build: PASS")
    print(
        "Deterministic replay order only; complete process-restart-safe idempotency still depends on "
        "duplicate event_id protection, stable event indexing, and append safety."
    )
    print(f"Built {learner_state_path}")
    print(f"Built {mastery_graph_path}")
    print(f"Built {report_path}")
    print(f"Events replayed: {projection['summary']['input_summary']['events_replayed']}")
    print(f"Projected nodes: {projection['learner_state_projection']['node_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
