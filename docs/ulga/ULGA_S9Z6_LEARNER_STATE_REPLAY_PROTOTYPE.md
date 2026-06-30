# ULGA-S9Z6 Learner State Replay Prototype

## Scope

This task implements a prototype-only learner state replay builder that reads validated learner event collections, sorts replayable events deterministically, aggregates node-level evidence, and emits isolated prototype projection outputs.

This prototype does not overwrite canonical learner state artifacts and does not integrate with ranking, planner, runtime APIs, or production reducer logic.

## S9Z5 Errata Alignment Performed

The required S9Z5 wording errata were applied before implementation:

1. The idempotency statement now claims deterministic replay order only, with explicit note that process-restart-safe idempotency also requires duplicate protection, stable indexing, and append safety.
2. The deterministic projection wording now correctly states that derived states must be deterministic projections.

## Files Created

- `ulga/builders/build_learner_state_replay_prototype.py`
- `tests/ulga/test_learner_state_replay_prototype.py`
- `tests/fixtures/ulga/learner_event_replay_prototype_events.json`
- `docs/ulga/ULGA_S9Z6_LEARNER_STATE_REPLAY_PROTOTYPE.md`
- `ulga/learner_state/prototype/learner_state_projection_prototype.json`
- `ulga/learner_state/prototype/mastery_graph_projection_prototype.json`
- `ulga/reports/learner_state_replay_prototype_summary.json`

## Files Modified

- `docs/ulga/ULGA_S9Z5_LEARNER_EVENT_REDUCER_DESIGN_SCAN.md`

No other existing project files were modified.

## Boundary Confirmation

- Canonical graph JSON files were not modified.
- Canonical `ulga/learner_state/learner_state.json` was not modified.
- Candidate ranking files were not modified.
- Planner logic was not modified.
- Runtime API code was not modified.
- Production reducer logic was not modified.
- No real learner data was created.

## Prototype Replay Policy

- Supported input forms:
  - raw list of events
  - wrapper object with `events`
- Replay sort order:
  - primary: `occurred_at_utc`
  - secondary: `event_id`
  - tertiary: `input_index`
- Missing `occurred_at_utc` is derived from `occurred_at`
- Quarantined events are excluded when `quality_flags.requires_review == true`
- Producer-marked invalid events are excluded when `quality_flags.valid_event == false`

Deterministic ordering guarantee used by the prototype:

```text
This ordering guarantees deterministic replay order, not complete process-restart-safe idempotency.
Complete idempotency requires duplicate event_id protection, stable event indexing, and append safety.
```

## Evidence Aggregation Logic

Supported node groups:

- `vocabulary`
- `grammar`
- `pattern`
- `chunk`
- `theme`

Per replayed event, evidence is projected to every listed node in the supported target groups.

Evidence buckets implemented:

- exposure
- practice
- assessment
- reinforcement
- engagement

Key prototype rules:

- exposure-only evidence can move a node to `seen` only
- practice updates attempt, retry, correctness, hint, and response-time metrics
- assessment updates totals, success rate, and mastery-check pass/fail counters
- reinforcement accumulates hint, retry, incorrect, and weak-signal counts
- engagement updates counts only and does not directly raise mastery
- theme nodes may collect exposure and engagement evidence, but direct mastery scoring remains blocked

## Mastery Projection Disclaimer

The scoring weights in S9Z6 are prototype-only and are not calibrated production mastery weights.

Prototype score:

```text
practice_signal = practice.success_rate * 0.45
assessment_signal = assessment.success_rate * 0.45
exposure_signal = min(exposure.count, 3) / 3 * 0.10
penalty = min(0.4, hint_count * 0.05 + retry_count * 0.04 + incorrect_count * 0.08)
raw_score = clamp(practice_signal + assessment_signal + exposure_signal - penalty, 0.0, 1.0)
```

Band priority order:

- `review_needed`
- `automatic`
- `mastered`
- `functional`
- `practicing`
- `seen`
- `unknown`

`blocked` is intentionally not implemented in this prototype.

## Output Artifact Locations

- `ulga/learner_state/prototype/learner_state_projection_prototype.json`
- `ulga/learner_state/prototype/mastery_graph_projection_prototype.json`
- `ulga/reports/learner_state_replay_prototype_summary.json`

All outputs are isolated under prototype paths or report paths and do not overwrite canonical learner state.

## Test Coverage

The test suite covers:

1. list input loading
2. wrapper input loading
3. deterministic sorting
4. quarantined event exclusion
5. producer-marked invalid event exclusion
6. exposure-only `seen` ceiling
7. correct practice aggregation
8. retry aggregation and reinforcement
9. hint aggregation and reinforcement
10. assessment aggregation
11. failed mastery check to `review_needed`
12. theme direct mastery block
13. prototype-only output writing
14. canonical learner state non-modification
15. summary idempotency claim flag

## Commands Executed

Executed for implementation verification:

- `python -m pytest tests/ulga/test_learner_state_replay_prototype.py -q`
- `python -m pytest tests/ulga/test_validate_learner_event_log.py -q`
- `python -m pytest tests/ulga/test_learner_event_log_schema.py -q`
- `python ulga/builders/build_learner_state_replay_prototype.py --input tests/fixtures/ulga/learner_event_replay_prototype_events.json`

Observed results:

- `tests/ulga/test_learner_state_replay_prototype.py`: `15 passed`
- `tests/ulga/test_validate_learner_event_log.py`: `15 passed`
- `tests/ulga/test_learner_event_log_schema.py`: `10 passed`
- replay prototype build: `PASS`

## Real-Environment Risks

- prototype weights are not calibrated
- no dependency lock or prerequisite graph integration yet
- no decay formula implemented yet
- no canonical learner state overwrite path by design
- no candidate ranking integration
- no planner integration
- idempotency is not fully guaranteed by sorting alone
- event store append safety remains future work
- schema migration policy remains future work
- upstream malformed event streams can still fail the builder if timestamp fields are unusable

## Recommended Next Task

- `ULGA-S9Z7_LearnerStateReplay_QA_Audit`

S9Z7 should audit prototype outputs before any promotion toward canonical learner state or any future S10A integration.
