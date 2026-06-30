import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

def load_schema(schema_path: Path) -> dict:
    """Loads the single-event schema from the given path."""
    with schema_path.open("r", encoding="utf-8") as f:
        return json.load(f)

def validate_event_schema(event: dict, schema: dict) -> list[dict]:
    """Validates a single event against the JSON schema, returning a list of error dicts."""
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = []
    
    # We validate only if event is a dictionary
    if not isinstance(event, dict):
        return []
        
    for error in validator.iter_errors(event):
        path = ".".join(map(str, error.absolute_path))
        errors.append({
            "severity": "error",
            "code": "schema_validation_failed",
            "message": error.message,
            "path": path
        })
    return errors

def normalize_timestamp_to_utc(value: str) -> str | None:
    """Parses an ISO timestamp (allowing Z and timezone offsets) and normalizes it to UTC."""
    if not isinstance(value, str):
        return None
    try:
        val_to_parse = value
        if val_to_parse.endswith('Z'):
            val_to_parse = val_to_parse[:-1] + '+00:00'
        
        dt = datetime.fromisoformat(val_to_parse)
        if dt.tzinfo is None:
            return None
            
        dt_utc = dt.astimezone(timezone.utc)
        return dt_utc.isoformat().replace('+00:00', 'Z')
    except Exception:
        return None

def load_existing_index(path: Path) -> set[str]:
    """Loads a set of existing event IDs from a JSON file."""
    if not path.exists():
        return set()
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return set(data)
        elif isinstance(data, dict):
            ids = data.get("event_ids")
            if isinstance(ids, list):
                return set(ids)
    except Exception:
        pass
    return set()

def validate_event_collection(events: list[dict], schema: dict, existing_event_ids: set[str] | None = None) -> dict:
    """Validates a collection of learner events.
    
    Returns a report dict with status, summary, normalized_events, errors, warnings, and quarantine.
    """
    errors = []
    warnings = []
    quarantine = []
    normalized_events = []
    
    seen_event_ids = set()
    duplicate_event_ids = set()
    parsed_timestamps = []
    
    invalid_event_indices = set()
    quarantined_event_indices = set()
    valid_event_indices = set()
    
    total_events = len(events)
    
    for idx, event in enumerate(events):
        event_has_error = False
        
        # 1. Type check
        if not isinstance(event, dict):
            event_has_error = True
            invalid_event_indices.add(idx)
            errors.append({
                "event_index": idx,
                "event_id": None,
                "severity": "error",
                "code": "schema_validation_failed",
                "message": f"Event index {idx} is not a JSON object",
                "path": ""
            })
            continue
            
        event_id = event.get("event_id")
        occurred_at = event.get("occurred_at")
        
        # 2. Schema validation
        schema_errs = validate_event_schema(event, schema)
        if schema_errs:
            event_has_error = True
            for err in schema_errs:
                err["event_index"] = idx
                err["event_id"] = event_id if isinstance(event_id, str) else None
                errors.append(err)
                
        # 3. Duplicate event_id inside collection detection
        if isinstance(event_id, str):
            if event_id in seen_event_ids:
                event_has_error = True
                duplicate_event_ids.add(event_id)
                errors.append({
                    "event_index": idx,
                    "event_id": event_id,
                    "severity": "error",
                    "code": "duplicate_event_id",
                    "message": f"Duplicate event_id found in the collection: {event_id}",
                    "path": "event_id",
                    "duplicate_event_id": event_id
                })
            else:
                seen_event_ids.add(event_id)
                
            # 4. Existing index check
            if existing_event_ids and event_id in existing_event_ids:
                event_has_error = True
                errors.append({
                    "event_index": idx,
                    "event_id": event_id,
                    "severity": "error",
                    "code": "event_id_already_exists",
                    "message": f"Event ID already exists in the existing index: {event_id}",
                    "path": "event_id"
                })
                
        # 5. Timestamp parseability and normalization
        normalized_dt_str = None
        if isinstance(occurred_at, str):
            normalized_dt_str = normalize_timestamp_to_utc(occurred_at)
            if normalized_dt_str is None:
                event_has_error = True
                errors.append({
                    "event_index": idx,
                    "event_id": event_id if isinstance(event_id, str) else None,
                    "severity": "error",
                    "code": "invalid_timestamp",
                    "message": f"Timestamp occurred_at is invalid or cannot be parsed: {occurred_at}",
                    "path": "occurred_at"
                })
            else:
                try:
                    dt_obj = datetime.fromisoformat(normalized_dt_str.replace('Z', '+00:00'))
                    parsed_timestamps.append((idx, dt_obj))
                except Exception:
                    pass
                    
        # 6. Semantic guardrails beyond schema
        event_type = event.get("event_type")
        
        # 6.1 exposure_seen
        if event_type == "exposure_seen":
            evidence_flags = event.get("evidence_flags", {})
            if isinstance(evidence_flags, dict):
                counts_as_mastery = evidence_flags.get("counts_as_mastery_update")
                counts_as_assessment = evidence_flags.get("counts_as_assessment")
                if counts_as_mastery is True or counts_as_assessment is True:
                    event_has_error = True
                    errors.append({
                        "event_index": idx,
                        "event_id": event_id if isinstance(event_id, str) else None,
                        "severity": "error",
                        "code": "exposure_seen_invalid_evidence_flags",
                        "message": "exposure_seen events must not count as mastery update or assessment",
                        "path": "evidence_flags"
                    })
                    
        # 6.2 hint_used
        if event_type == "hint_used":
            attempt = event.get("attempt", {})
            if isinstance(attempt, dict):
                used_hint = attempt.get("used_hint")
                if used_hint is not True:
                    event_has_error = True
                    errors.append({
                        "event_index": idx,
                        "event_id": event_id if isinstance(event_id, str) else None,
                        "severity": "error",
                        "code": "hint_used_without_used_hint",
                        "message": "hint_used events must have attempt.used_hint set to true",
                        "path": "attempt.used_hint"
                    })
                    
        # 6.3 assessment_attempt / mastery_check
        if event_type in ("assessment_attempt", "mastery_check"):
            evidence_flags = event.get("evidence_flags", {})
            counts_as_assessment = evidence_flags.get("counts_as_assessment") if isinstance(evidence_flags, dict) else None
            attempt = event.get("attempt", {})
            score = attempt.get("score") if isinstance(attempt, dict) else None
            max_score = attempt.get("max_score") if isinstance(attempt, dict) else None
            
            is_score_numeric = isinstance(score, (int, float)) and not isinstance(score, bool)
            is_max_score_numeric = isinstance(max_score, (int, float)) and not isinstance(max_score, bool)
            
            if counts_as_assessment is not True or not is_score_numeric or not is_max_score_numeric:
                event_has_error = True
                errors.append({
                    "event_index": idx,
                    "event_id": event_id if isinstance(event_id, str) else None,
                    "severity": "error",
                    "code": "assessment_event_missing_score",
                    "message": "assessment_attempt or mastery_check events must count as assessment and have numeric score and max_score",
                    "path": "attempt"
                })
                
        # 6.4 Mastery update target nodes
        evidence_flags = event.get("evidence_flags", {})
        if isinstance(evidence_flags, dict) and evidence_flags.get("counts_as_mastery_update") is True:
            target_nodes = event.get("target_nodes", {})
            if isinstance(target_nodes, dict):
                vocab = target_nodes.get("vocabulary", [])
                grammar = target_nodes.get("grammar", [])
                pattern = target_nodes.get("pattern", [])
                chunk = target_nodes.get("chunk", [])
                
                vocab_len = len(vocab) if isinstance(vocab, list) else 0
                grammar_len = len(grammar) if isinstance(grammar, list) else 0
                pattern_len = len(pattern) if isinstance(pattern, list) else 0
                chunk_len = len(chunk) if isinstance(chunk, list) else 0
                
                if vocab_len == 0 and grammar_len == 0 and pattern_len == 0 and chunk_len == 0:
                    event_has_error = True
                    errors.append({
                        "event_index": idx,
                        "event_id": event_id if isinstance(event_id, str) else None,
                        "severity": "error",
                        "code": "mastery_update_without_target_nodes",
                        "message": "mastery_update events must have at least one non-empty target node array (vocabulary, grammar, pattern, chunk)",
                        "path": "target_nodes"
                    })
                    
        # 6.5 quality_flags.valid_event
        quality_flags = event.get("quality_flags", {})
        if isinstance(quality_flags, dict):
            valid_event = quality_flags.get("valid_event")
            if valid_event is False:
                warnings.append({
                    "event_index": idx,
                    "event_id": event_id if isinstance(event_id, str) else None,
                    "severity": "warning",
                    "code": "producer_marked_event_invalid",
                    "message": "Producer marked this event as invalid",
                    "path": "quality_flags.valid_event"
                })
                
            # 6.6 quality_flags.requires_review
            requires_review = quality_flags.get("requires_review")
            if requires_review is True:
                warnings.append({
                    "event_index": idx,
                    "event_id": event_id if isinstance(event_id, str) else None,
                    "severity": "warning",
                    "code": "requires_review",
                    "message": "Event requires manual review",
                    "path": "quality_flags.requires_review"
                })
                
        # 7. Categorize and build normalized representation if valid/quarantined
        if event_has_error:
            invalid_event_indices.add(idx)
        else:
            if isinstance(quality_flags, dict) and quality_flags.get("requires_review") is True:
                quarantined_event_indices.add(idx)
                quarantine.append({
                    "event_index": idx,
                    "event_id": event_id,
                    "code": "requires_review",
                    "message": "Event requires manual review"
                })
            else:
                valid_event_indices.add(idx)
                
            normalized_events.append({
                "event_id": event_id,
                "occurred_at_utc": normalized_dt_str
            })

    # 8. Timestamp ordering warning
    out_of_order_indexes = []
    max_dt = None
    for idx, dt in parsed_timestamps:
        if max_dt is not None and dt < max_dt:
            out_of_order_indexes.append(idx)
        else:
            max_dt = dt
            
    if out_of_order_indexes:
        warnings.append({
            "event_index": out_of_order_indexes[0],
            "event_id": None,
            "severity": "warning",
            "code": "non_chronological_order",
            "message": "Event timestamps are not in non-decreasing order.",
            "path": "occurred_at",
            "out_of_order_indexes": out_of_order_indexes
        })
        
    # 9. Compute Status
    if len(errors) > 0:
        status = "FAIL"
    elif len(quarantine) > 0:
        status = "PASS_WITH_QUARANTINE"
    elif len(warnings) > 0:
        status = "PASS_WITH_WARNINGS"
    else:
        status = "PASS"
        
    # 10. Construct Report
    return {
        "status": status,
        "summary": {
            "total_events": total_events,
            "valid_events": len(valid_event_indices),
            "invalid_events": len(invalid_event_indices),
            "quarantined_events": len(quarantined_event_indices),
            "error_count": len(errors),
            "warning_count": len(warnings),
            "duplicate_event_ids": sorted(list(duplicate_event_ids))
        },
        "normalized_events": normalized_events,
        "errors": errors,
        "warnings": warnings,
        "quarantine": quarantine
    }

def main() -> int:
    parser = argparse.ArgumentParser(description="ULGA Learner Event Log Collection Validator")
    parser.add_argument("--input", required=True, help="Path to input JSON file containing event collection")
    parser.add_argument("--schema", help="Path to the learner event log schema JSON file")
    parser.add_argument("--existing-index", help="Path to the existing event ID index file")
    parser.add_argument("--report", help="Path to write the validation report JSON")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input file {input_path} does not exist.", file=sys.stderr)
        return 1
        
    # Schema path setup
    if args.schema:
        schema_path = Path(args.schema)
    else:
        # Default to script parent's schemas directory
        script_dir = Path(__file__).resolve().parent
        schema_path = script_dir.parent / "schemas" / "learner_event_log_schema.json"
        
    if not schema_path.exists():
        print(f"Error: schema file {schema_path} does not exist.", file=sys.stderr)
        return 1
        
    try:
        schema = load_schema(schema_path)
    except Exception as e:
        print(f"Error: failed to load schema: {e}", file=sys.stderr)
        return 1
        
    # Existing index setup
    existing_ids = set()
    if args.existing_index:
        index_path = Path(args.existing_index)
        existing_ids = load_existing_index(index_path)
        
    # Load input events
    try:
        with input_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error: failed to parse input JSON: {e}", file=sys.stderr)
        return 1
        
    if isinstance(data, dict):
        if "events" in data and isinstance(data["events"], list):
            events = data["events"]
        else:
            print("Error: Wrapper object must contain an 'events' list.", file=sys.stderr)
            return 1
    elif isinstance(data, list):
        events = data
    else:
        print("Error: Input JSON must be a list of events or a wrapper object with 'events' list.", file=sys.stderr)
        return 1
        
    report = validate_event_collection(events, schema, existing_event_ids=existing_ids)
    
    # Write report if requested
    if args.report:
        report_path = Path(args.report)
        try:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with report_path.open("w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            print(f"Validation report written to {report_path}")
        except Exception as e:
            print(f"Error: failed to write report to {report_path}: {e}", file=sys.stderr)
            return 1
            
    # Print summary to stdout
    print(f"Validation Status: {report['status']}")
    print(f"Total events: {report['summary']['total_events']}")
    print(f"  Valid: {report['summary']['valid_events']}")
    print(f"  Invalid: {report['summary']['invalid_events']}")
    print(f"  Quarantined: {report['summary']['quarantined_events']}")
    print(f"Errors: {report['summary']['error_count']}")
    print(f"Warnings: {report['summary']['warning_count']}")
    
    if report["status"] == "FAIL":
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
