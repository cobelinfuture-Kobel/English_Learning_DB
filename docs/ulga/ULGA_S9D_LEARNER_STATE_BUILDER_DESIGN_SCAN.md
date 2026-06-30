# ULGA-S9D Learner State Builder Design Scan

## Executive Summary

LearnerStateBuilder is the future ULGA authority component that converts validated S9B evidence events into canonical S9C learner-state records.

- Input: `ulga/learner_state/evidence_event_schema.json` and evidence payloads shaped like `sample_evidence_events.json`
- Output: `ulga/learner_state/learner_state_schema.json` and runtime payloads shaped like `sample_learner_state.json`

LearnerStateBuilder must remain separate from Candidate Ranking and Planner.

- Builder owns deterministic learner-state computation.
- Candidate Ranking owns what to recommend next.
- Planner owns pacing, bundle selection, scheduling, and intervention flow.

If builder logic leaks into ranking or planner code, repeated execution, process restart, and future scoring-rule changes will create inconsistent learner truth across Dashboard, API, Scheduler, Orchestrator, and Strategy consumers.

## Input Contract Review

Reviewed:

- `ulga/learner_state/evidence_event_schema.json`
- `ulga/learner_state/sample_evidence_events.json`

### `event_id`

- Stable event identity for replay safety.
- Must be unique across the full event log.
- Builder V1 should reject duplicates before aggregation begins.

### `learner_id`

- Required partition key for multi-learner isolation.
- All aggregation must be scoped by `learner_id` first, then `node_id`.
- This is mandatory to prevent James and Cyndi state leakage.

### `event_type`

- Encodes evidence provenance and expected reliability.
- Should influence update strength through a deterministic multiplier table.
- Must not directly determine mastery band without score, role, and confidence context.

### `node_refs`

- One event can affect multiple nodes with different roles and weights.
- Builder must flatten `node_refs` into per-node weighted evidence entries.
- `primary_target` should carry stronger update authority than `supporting_context`.
- `coverage_signal` and `review_signal` must not behave like direct mastery proof.

### `score`

- Normalized numeric evidence quality input in the range `0..1`.
- Should be a major driver of raw mastery contribution.
- Must not be trusted in isolation because event type, role, and confidence all matter.

### `attempt_count`

- Indicates whether an event reflects first-pass performance or retry-assisted success.
- Can reduce confidence or update strength for high-retry evidence.
- Should not directly increase `exposure_count` beyond one event in V1 if raw event count semantics are chosen.

### `response_time`

- Optional fluency signal.
- More useful for distinguishing `mastered` from `automatic` than for basic pass/fail.
- V1 should use this conservatively or not at all in the core mastery formula to avoid brittle timing assumptions across event types.

### `error_type`

- Diagnostic metadata, not just a negative score tag.
- Useful for future dashboards, remediation routing, and confidence notes.
- V1 builder may preserve it only indirectly through confidence notes or future summaries rather than in the canonical learner-state schema.

### `confidence`

- Required reliability estimate from the event producer.
- `confidence.value` should scale update strength.
- Manual and auto-scored events can share score ranges while still contributing differently because confidence differs.

### `source`

- Provides provenance such as `producer`, `channel`, and `derivation`.
- Important for auditability when API failure, malformed upstream responses, or manual review corrections occur.
- Builder should not rewrite source provenance from evidence events, but may summarize derivation method inside output `source`.

### `processing_idempotency_key`

- Required replay-safety field beyond `event_id`.
- Protects against duplicate ingestion when the same logical event is emitted with transport retries or process restarts.
- Builder V1 should reject duplicate keys before producing output.

## Output Contract Review

Reviewed:

- `ulga/learner_state/learner_state_schema.json`
- `ulga/learner_state/sample_learner_state.json`

### `learner_id + node_id` uniqueness

- Canonical learner-state identity.
- Builder must emit at most one record per pair.
- Duplicate pairs in final output should be treated as builder failure, not merged implicitly after emission.

### `mastery_score`

- Raw pre-decay mastery estimate in the range `0..1`.
- Must be deterministic from the same input event log and weighting policy.
- V1 should derive this only from evidence aggregation, not from planner heuristics.

### `mastery_band`

- Must match S9C score ranges exactly:
  - `unknown`: `0.00 <= score < 0.10`
  - `seen`: `0.10 <= score < 0.25`
  - `practicing`: `0.25 <= score < 0.50`
  - `functional`: `0.50 <= score < 0.70`
  - `mastered`: `0.70 <= score < 0.90`
  - `automatic`: `0.90 <= score <= 1.00`
- Builder must not invent custom bands.

### `exposure_count`

- Requires an explicit semantics decision for V1.
- Strongly affects downstream interpretation of confidence, review due, and dashboard display.
- See Count Semantics Decision below.

### `correct_count` / `incorrect_count`

- S9C requires integers and enforces `correct_count + incorrect_count <= exposure_count`.
- Builder therefore needs deterministic integer thresholding even if mastery uses weighted fractional evidence internally.
- V1 should count an event as correct when normalized effective score passes a chosen threshold and incorrect otherwise.

### `evidence_refs`

- Must preserve traceability from learner-state records back to source events.
- Should contain deduplicated `event_id` values in deterministic order.
- Important for audit, replay inspection, and future dashboard drill-down.

### `decay_adjusted_score`

- Required by S9C even before full spaced repetition exists.
- V1 can keep it equal to `mastery_score` or apply a minimal age penalty policy, but the choice must be explicit and rebuildable.

### `review_due_at`

- Required output scheduling hint owned by learner-state authority, not planner.
- V1 should use a simple band-based interval policy anchored to `last_success_at`.
- `unknown` should keep `review_due_at = null`.

### `state_updated_at`

- Must reflect when the builder produced this record, not when the source event occurred.
- For deterministic rebuilds, V1 should use the builder run timestamp consistently across all emitted records.

### `processing_idempotency_key`

- Output-level idempotency key should represent the state build version for that learner-node pair.
- V1 can derive it from learner id, node id, and build timestamp or build digest.
- It must be unique across emitted records in one build.

## Builder Responsibilities

LearnerStateBuilder should:

- load evidence events from a canonical event collection
- validate evidence events before aggregation
- reject duplicate `event_id` values
- reject duplicate `processing_idempotency_key` values
- flatten `node_refs` into weighted node-level evidence entries
- group evidence by `learner_id + node_id`
- apply event type, role, node-ref, score, and confidence weights
- update `exposure_count`
- update integer `correct_count` and `incorrect_count`
- compute raw `mastery_score`
- assign `mastery_band` using S9C ranges
- compute output `confidence`
- compute V1 placeholder `decay_adjusted_score`
- compute V1 placeholder `review_due_at`
- emit canonical `learner_state_records`
- validate final output against the S9C learner-state validator

## Non-Responsibilities

LearnerStateBuilder must not:

- rank candidates
- recommend lessons
- mutate static ULGA graph files
- decide learning path
- alter S9B or S9C schema contracts
- infer mounted graph existence unless a later graph resolver is added
- perform UI or Dashboard logic
- own Scheduler, Orchestrator, or Strategy policy
- perform partial in-place runtime mutation in V1

## Proposed Builder Algorithm

Deterministic first-pass algorithm:

1. Read the full evidence-event collection.
2. Validate the payload against the S9B validator.
3. Reject duplicate `event_id`.
4. Reject duplicate `processing_idempotency_key`.
5. Sort events deterministically by `timestamp`, then `event_id`.
6. Flatten each event into weighted evidence entries, one per `node_ref`.
7. Compute per-entry effective strength:

```text
effective_strength =
node_ref.weight
* role_multiplier
* event_type_multiplier
* confidence.value
```

8. Compute per-entry effective score:

```text
effective_score =
score
* effective_strength
```

9. Aggregate by `(learner_id, node_id)` only.
10. Track:
    - latest seen timestamp
    - latest success timestamp
    - deduplicated evidence refs
    - weighted exposure sum
    - weighted success sum
    - raw event exposure count
    - integer success/failure counts
11. Compute `mastery_score` from aggregated weighted values.
12. Map `mastery_score` to S9C `mastery_band`.
13. Compute record-level `confidence`.
14. Compute V1 `decay_adjusted_score`.
15. Compute V1 `review_due_at`.
16. Emit one record per `(learner_id, node_id)`.
17. Sort output deterministically by `learner_id`, then `node_type`, then `node_id`.
18. Validate the emitted collection against the S9C validator before writing.

### Success / Failure Threshold Proposal

Recommended V1 event-level classification:

- effective normalized score `>= 0.60` counts as success
- effective normalized score `< 0.60` counts as incorrect

Where:

```text
effective_normalized_score =
score * event_type_multiplier * confidence.value
```

Rationale:

- Keeps integer counts simple enough for S9C.
- Avoids tying correctness to `node_ref.weight`, which is about routing strength rather than whether the event itself was successful.
- Makes retry-heavy low-confidence events less likely to count as strong success.

## Evidence Weighting Policy

Suggested V1 event type multipliers:

| Event type | Multiplier | Rationale |
|---|---:|---|
| `worksheet` | 0.90 | Useful structured evidence, but can overstate recognition. |
| `quiz` | 1.00 | Good direct evidence without over-privileging tests. |
| `reading` | 0.65 | Stronger for exposure than production mastery. |
| `dialogue` | 1.05 | Better contextual retrieval evidence. |
| `speaking` | 1.10 | Strong production evidence when confidence is good. |
| `writing` | 1.10 | Strong production evidence when scoring is reliable. |
| `listening` | 0.70 | Useful for comprehension, weaker for production mastery. |
| `manual_parent_input` | 0.45 | Must remain conservative. |
| `manual_teacher_input` | 0.95 | Valuable, but still not automatically authoritative above all else. |

Suggested V1 role multipliers:

| Role | Multiplier | Rationale |
|---|---:|---|
| `primary_target` | 1.00 | Direct mastery target. |
| `supporting_context` | 0.50 | Context matters, but impact should be lower. |
| `prerequisite` | 0.40 | Useful readiness hint, weak direct mastery proof. |
| `diagnostic_signal` | 0.35 | Good for confidence shaping, not strong mastery proof. |
| `review_signal` | 0.30 | Shows revisit need, not direct proficiency. |
| `coverage_signal` | 0.20 | Must not create strong mastery on its own. |

Suggested combined evidence rule:

```text
weighted_success =
score
* node_ref.weight
* confidence.value
* event_type_multiplier
* role_multiplier
```

Warnings:

- `coverage_signal` must not create mastery by itself.
- `supporting_context` should have lower impact than `primary_target`.
- `manual_parent_input` should remain conservative even when reported score is high.
- speaking and writing evidence should scale with `confidence.value`; low-confidence ASR or weak rubric quality should reduce update strength.

## Count Semantics Decision

Two options:

### Option A. `exposure_count` as raw event count

- Count one exposure when a learner-node pair is touched by an event.
- Integer semantics stay intuitive.
- Easier to explain in Dashboard and API.
- Naturally compatible with S9C integer count rules.

### Option B. `exposure_count` as weighted rounded count

- Attempts to encode evidence strength directly inside count.
- Harder to explain and debug.
- More likely to drift under replay or weighting-policy changes.
- Can create confusing cases where a node has evidence refs but zero rounded exposures.

### Recommendation for V1

Recommend Option A: `exposure_count` as raw event count per learner-node pair.

Rationale:

- Minimal-change fit for S9C integer contract.
- More stable under repeated full rebuild.
- Easier to reason about when debugging abnormal API responses or duplicate ingestion.
- Keeps weighting inside mastery computation rather than mixing two meanings into one field.

## Mastery Formula Proposal

Recommended V1 formula:

```text
weighted_success_sum =
sum(score * node_ref.weight * confidence.value * event_type_multiplier * role_multiplier)

weighted_exposure_sum =
sum(node_ref.weight * confidence.value * event_type_multiplier * role_multiplier)

mastery_score =
clamp(weighted_success_sum / weighted_exposure_sum, 0, 1)
```

Recommended guard:

```text
if weighted_exposure_sum == 0:
    mastery_score = 0
```

Rationale:

- Deterministic
- Replay-safe
- Keeps evidence score normalized
- Allows node role and provenance to influence impact without schema changes
- Works for James and Cyndi independently because aggregation key includes `learner_id`

Limitations:

- Does not yet model streaks, forgetting curves, or spaced repetition.
- Can under-represent time ordering because all weighted evidence is summarized into one ratio.
- Theme or morphology aggregation may need additional guardrails later because these are not always direct practice targets.

## Decay / Review Due Design

This section is design only.

### V1 `decay_adjusted_score`

Recommended placeholder:

- default `decay_adjusted_score = mastery_score`
- optional simple age penalty only when `last_success_at` exists and evidence is stale

Example optional simple penalty:

```text
days_since_last_success = max(0, floor((build_time - last_success_at) / 1 day))
simple_penalty = min(0.20, days_since_last_success * 0.005)
decay_adjusted_score = clamp(mastery_score - simple_penalty, 0, 1)
```

Recommendation for V1:

- use `decay_adjusted_score = mastery_score`

Rationale:

- Simplest deterministic baseline
- Avoids premature spaced-repetition assumptions
- Keeps S9D implementation surface small

### V1 `review_due_at`

Recommended placeholder policy:

- `unknown` -> `null`
- `seen` -> `last_seen_at + 2 days`
- `practicing` -> `last_success_at or last_seen_at + 3 days`
- `functional` -> `last_success_at + 7 days`
- `mastered` -> `last_success_at + 14 days`
- `automatic` -> `last_success_at + 30 days`

Rules:

- If both `last_success_at` and `last_seen_at` are `null`, `review_due_at = null`
- If `last_success_at` is `null`, fall back to `last_seen_at`
- Builder should not emit a past-due timestamp caused by partial failed writes; compute all records in memory first, then write once

## Idempotency and Replay Safety

Builder V1 should prioritize deterministic full rebuild over incremental mutation.

- reject duplicate `event_id`
- reject duplicate `processing_idempotency_key`
- rebuild the full learner-state collection from the full event log each run
- do not patch existing learner-state records in place during V1
- sort input and output deterministically so the same event log yields the same learner-state content except for deliberate build timestamp fields

Why full rebuild is preferred for V1:

- safer under process restart
- easier to debug after timeout or abnormal upstream response
- avoids silent drift from partial incremental mutations
- reduces coupling to Scheduler and Orchestrator retry behavior

## Multi-Learner Support

Builder must explicitly support:

- `learner:james`
- `learner:cyndi`

Rules:

- aggregate by `learner_id + node_id`, never by `node_id` alone
- keep learner-scoped evidence refs separate
- never let one learner's success alter another learner's `mastery_score`, `confidence`, or `review_due_at`
- avoid module-level global mutable state for accumulators because process reuse can leak learner data between runs

## Error Handling

Builder design must handle:

- invalid evidence event
  - reject before aggregation
- missing required fields
  - fail validation with explicit field path
- unknown `node_type`
  - fail validation; do not coerce
- invalid `score`
  - fail validation; do not clamp silently
- empty events
  - either fail input validation or emit a documented empty-state path only if contract changes later
- duplicate ids
  - reject duplicate `event_id` and duplicate `processing_idempotency_key`
- malformed timestamp
  - fail validation; do not guess timezone
- future mounted graph mismatch
  - warn or quarantine in a later resolver stage, but V1 builder should not infer graph existence
- partial write prevention
  - compute full output in memory, validate, then write once atomically

Real environment risks to keep explicit:

- API failure can produce incomplete or repeated event batches.
- Timeout can leave half-built output unless write is atomic.
- Empty data must still support future cold-start handling, but current S9C collection contract is non-empty.
- Repeated execution must not inflate counts.
- Process restart must not depend on in-memory incremental state.
- Exchange-style abnormal upstream responses are analogous to malformed runtime producer payloads here: null fields, duplicate logical events, or inconsistent timestamps must be rejected, not tolerated silently.

## Proposed Future Files for S9E

Recommended future files:

- `ulga/builders/build_learner_state.py`
- `ulga/learner_state/learner_state.json`
- `ulga/reports/learner_state_builder_summary.json`
- `ulga/validators/validate_learner_state_builder_output.py`
- `tests/ulga/test_learner_state_builder.py`
- `docs/ulga/ULGA_S9E_LEARNER_STATE_BUILDER_IMPLEMENTATION.md`

## PASS / WARN / BLOCKER

### PASS

- S9B evidence event contract is sufficient for a deterministic first-pass builder.
- S9C learner-state contract is sufficient for canonical builder output.
- Duplicate protection fields exist at both event and record levels.
- Multi-learner separation is contractually supported through required `learner_id`.

### WARN

- S9C currently requires non-empty learner-state collections, so true zero-event cold-start output is not yet naturally representable without a seed strategy or contract revision.
- S9B/S9C validators do not currently enforce mounted graph existence, so future graph mismatch handling must be added carefully without breaking schema-only boundaries.
- Theme, morphology, assessment, skill, and dialogue records may receive evidence before a fully mounted graph-resolver layer exists; builder must not over-interpret those signals.
- `response_time` is present but not yet standardized enough to drive automaticity strongly in V1.

### BLOCKER

- No runtime event-log storage, atomic output-write path, or builder summary artifact exists yet.
- No current implementation contract defines how empty global event logs should seed non-empty S9C collections.
- If future orchestrators require incremental updates instead of full rebuild, additional idempotent state-transition rules will be needed beyond this V1 design.

## Recommended Next Task

`ULGA-S9E_LearnerStateBuilder_Implementation`

## Final Assessment

Overall assessment: `PASS WITH WARNINGS`.

Builder implementation is feasible with the current S9B and S9C contracts if V1 stays deterministic, replay-safe, and full-rebuild oriented. The main risks are not formula complexity but boundary leakage, duplicate ingestion, empty-log behavior, and accidental coupling to ranking or planner logic.
