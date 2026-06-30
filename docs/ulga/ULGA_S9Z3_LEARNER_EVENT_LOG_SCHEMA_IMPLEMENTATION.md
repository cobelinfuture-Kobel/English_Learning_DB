# ULGA-S9Z3 Learner Event Log Schema Implementation

## Scope

This task implements the formal JSON Schema contract for one canonical ULGA Learner Event Log event and adds schema validation tests.

Boundaries preserved:

- No runtime Python files were modified.
- No graph JSON files were modified.
- No `learner_state.json` files were modified.
- No candidate ranking, planner, reducer, or mastery scoring logic was changed.
- No real learner data was created.

## Files

Created:

- `ulga/schemas/learner_event_log_schema.json`
- `tests/ulga/test_learner_event_log_schema.py`
- `docs/ulga/ULGA_S9Z3_LEARNER_EVENT_LOG_SCHEMA_IMPLEMENTATION.md`

Modified:

- None

## Key Schema Decisions

1. The schema is self-contained and validates a single event object, not a collection wrapper. This keeps S9Z3 focused on the canonical record contract and avoids coupling to future storage layout decisions.
2. `additionalProperties: false` is applied at every object layer to reduce integration drift between content producers, validators, and downstream reducers.
3. Recommended ID prefixes for `event_id` and `session_id` are documented but not enforced. This keeps the contract compatible with alternate ID generation strategies while still validating non-empty IDs.
4. `occurred_at` uses JSON Schema `date-time` format so valid UTC `Z` timestamps and offset timestamps such as `+08:00` are accepted by standards-compliant validators.
5. Assessment and mastery-update guardrails are encoded with conditional schema rules:
   - assessment evidence requires numeric `attempt.score` and `attempt.max_score`
   - mastery updates require at least one node in `vocabulary`, `grammar`, `pattern`, or `chunk`
   - `exposure_seen` blocks assessment and mastery-update routing
   - `hint_used` requires `attempt.used_hint: true`
   - `assessment_attempt` and `mastery_check` force `counts_as_assessment: true`

## Risk Review

- Risk level: Low
- Live trading impact: None
- Restart required: No

Potential real-environment limitations intentionally deferred to S9Z4 validator work:

- duplicate `event_id` detection across repeated runs
- append/write idempotency after process restart
- malformed upstream API payload handling
- timeout/retry policy for external event producers
- quarantine flows for partial or delayed event delivery

These are runtime and operational concerns, not schema-only concerns.

## Test Coverage

The test suite covers:

1. valid `answer_submitted`
2. valid `exposure_seen` with nullable attempt fields
3. valid `assessment_attempt`
4. invalid unknown `event_type`
5. invalid `learner_id`
6. invalid timestamp
7. assessment without score
8. mastery update without required target nodes
9. exposure event incorrectly marked as mastery update
10. `hint_used` with `used_hint: false`

## Integration Notes

- The schema does not depend on graph files, learner state files, or planner artifacts.
- The schema path follows the task requirement: `ulga/schemas/learner_event_log_schema.json`.
- Existing runtime validators were not altered, reducing regression risk for current ULGA pipelines.

## Recommended Next Task

- `ULGA-S9Z4_LearnerEventLog_Validator`: implement a dedicated validator for collection-level checks, timestamp normalization behavior, duplicate event protection, and process-restart-safe idempotency handling.
