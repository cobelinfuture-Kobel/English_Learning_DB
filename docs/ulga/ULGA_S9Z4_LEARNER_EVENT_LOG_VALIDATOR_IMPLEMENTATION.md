# ULGA S9Z4 Learner Event Log Validator Implementation

## 1. Scope
This implementation completes **ULGA-S9Z4_LearnerEventLog_Validator** by introducing a Python-based collection validator and corresponding CLI. It builds on top of the canonical single-event schema (`ulga/schemas/learner_event_log_schema.json`) to validate collections of learner events, checking for duplicates, out-of-order timestamps, formatting errors, and semantic logic constraints.

## 2. Files Created
* [validate_learner_event_log.py](file:///G:/HomeWork/English_Learning_DB/ulga/validators/validate_learner_event_log.py): The collection-level validator and CLI.
* [test_validate_learner_event_log.py](file:///G:/HomeWork/English_Learning_DB/tests/ulga/test_validate_learner_event_log.py): Pytest unit tests for the validator covering all requirements.
* [learner_event_log_valid_collection.json](file:///G:/HomeWork/English_Learning_DB/tests/fixtures/ulga/learner_event_log_valid_collection.json): A fixture containing valid event data.
* [learner_event_log_invalid_collection.json](file:///G:/HomeWork/English_Learning_DB/tests/fixtures/ulga/learner_event_log_invalid_collection.json): A fixture containing event data that fails validation.
* [ULGA_S9Z4_LEARNER_EVENT_LOG_VALIDATOR_IMPLEMENTATION.md](file:///G:/HomeWork/English_Learning_DB/docs/ulga/ULGA_S9Z4_LEARNER_EVENT_LOG_VALIDATOR_IMPLEMENTATION.md): This documentation.

## 3. Files Modified
* None.

## 4. Boundary Confirmation
* **No modifications** were made to existing JSON graphs, runtime code, learner state JSONs, planners, reducers, or mastery scoring engines.
* **No real learner data** was generated.
* **No personal names** (e.g. Cyndi or James) were hardcoded.
* All test user IDs are anonymized using formats such as `learner:usr_001`.

## 5. Validator Responsibilities
The collection validator verifies:
1. **JSON Wrapper or Array Structure**: Standard lists `[...]` or wrapper objects `{ "events": [...] }` are parsed correctly.
2. **Schema Compliance**: Calls `jsonschema` for each event inside the collection.
3. **Internal Duplication**: Detects and reports duplicate `event_id` occurrences within the same collection.
4. **Idempotency Check**: Uses an optional existing index `--existing-index` of previously validated `event_id` values to prevent processing duplicates.
5. **Timestamp Normalization**: Parses and normalizes timezones (`Z` and offsets like `+08:00`) to UTC ISO format.
6. **Timestamp Chronology Warning**: Flags out-of-order events using a non-fatal warning without failing the entire collection validation.
7. **Semantic Guardrails**:
   * `exposure_seen` events must not count as mastery updates or assessment.
   * `hint_used` events must have `attempt.used_hint` set to `true`.
   * `assessment_attempt` and `mastery_check` events must count as assessment and have numeric `attempt.score` and `attempt.max_score`.
   * `counts_as_mastery_update` events must target at least one node array in `target_nodes` (vocabulary, grammar, pattern, chunk).
   * Warnings are emitted if the producer marked an event as invalid (`quality_flags.valid_event` is `false`).
   * Events requiring review (`quality_flags.requires_review` is `true`) are quarantined but keep their valid status (unless other errors exist).

## 6. Validation Report Contract
The return value of `validate_event_collection` contains the following structured format:

```json
{
  "status": "PASS | PASS_WITH_WARNINGS | PASS_WITH_QUARANTINE | FAIL",
  "summary": {
    "total_events": 0,
    "valid_events": 0,
    "invalid_events": 0,
    "quarantined_events": 0,
    "error_count": 0,
    "warning_count": 0,
    "duplicate_event_ids": []
  },
  "normalized_events": [
    {
      "event_id": "evt_001",
      "occurred_at_utc": "2026-06-18T11:10:52Z"
    }
  ],
  "errors": [
    {
      "event_index": 0,
      "event_id": "evt_001",
      "severity": "error",
      "code": "schema_validation_failed",
      "message": "...",
      "path": "..."
    }
  ],
  "warnings": [
    {
      "event_index": 0,
      "event_id": "evt_001",
      "severity": "warning",
      "code": "producer_marked_event_invalid",
      "message": "...",
      "path": "..."
    }
  ],
  "quarantine": [
    {
      "event_index": 0,
      "event_id": "evt_001",
      "code": "requires_review",
      "message": "..."
    }
  ]
}
```

## 7. Error / Warning / Quarantine Policy
* **`FAIL`**: Triggered by any error (schema error, duplicate ID, invalid timestamp parser error, semantic guardrail error).
* **`PASS_WITH_QUARANTINE`**: Triggered if no errors are found, but at least one event needs review (`requires_review`). Quarantined events are considered valid and included in `normalized_events` but flagged for human review.
* **`PASS_WITH_WARNINGS`**: Triggered if warnings exist (out of order timestamps or producer-marked invalid events) but there are no errors and no quarantined events.
* **`PASS`**: Triggered only if all events are fully clean, chronological, and valid.

## 8. Test Coverage
The validator tests cover 15 distinct functional scenarios:
1. Valid collection passes.
2. Wrapper object with `events` key passes.
3. Invalid single event schema is collected as an error.
4. Duplicate `event_id` inside input collection fails.
5. Existing index duplicate fails.
6. Timezone offset is normalized to UTC.
7. Non-chronological event order produces warning but not failure.
8. `quality_flags.requires_review: true` produces quarantine and non-failing status.
9. `quality_flags.valid_event: false` produces warning.
10. `exposure_seen` with invalid mastery flag fails.
11. `hint_used` with `used_hint: false` fails.
12. Assessment event missing score fails.
13. Mastery update without target nodes fails.
14. CLI writes report file.
15. CLI returns exit code 1 on fail.

## 9. Commands Executed
* Run validator tests:
  ```bash
  python -m pytest tests/ulga/test_validate_learner_event_log.py -q
  ```
* Run existing S9Z3 schema tests:
  ```bash
  python -m pytest tests/ulga/test_learner_event_log_schema.py -q
  ```
* Run all ULGA tests:
  ```bash
  python -m pytest tests/ulga/ -q
  ```

## 10. Recommended Next Task
The next logical task is **ULGA-S9Z5_LearnerEventReducer_DesignScan**, which will outline how canonical events inside this validated log should be reduced into learner state updates.
