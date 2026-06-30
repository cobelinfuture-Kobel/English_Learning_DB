# ULGA-S9Z5 Learner Event Reducer Design Scan

## 1. Scope
This design scan outlines the architecture of the Event Reducer layer within the ULGA learner state subsystem. The reducer is a deterministic projection engine that reads validated learner event sequences and projects them into derived learner states and mastery graph overlays.

To prevent architecture coupling, the definitions are established as:
```text
learner_event_log = immutable raw evidence
validated_event_collection = safe input stream
event_reducer = deterministic projection engine
learner_state = derived rebuildable output
mastery_graph = derived overlay
candidate_ranking = downstream consumer
planner = downstream decision layer
```
This document establishes the reducer's boundaries, ordering contracts, evidence containers, node-level aggregation logic, decay expectations, and replay rules without introducing python files or raw database modifications.

---

## 2. Roadmap Position
The Event Reducer acts as the transition layer between the historical audit trail and runtime adaptation:
* **Upstream:** Bridges **S9Z2 Learner Event Log Design**, **S9Z3 Learner Event Log Schema**, and **S9Z4 Learner Event Log Validator**.
* **Prototype Layer:** Details the exact replay mechanics to be implemented by **S9Z6 Learner State Replay Prototype**.
* **Downstream:** Outputs the derived `learner_state` which is directly consumed by **S10A Candidate Ranking** and the **Antigravity Planner**.

```text
S9Z5 designs how replay should work.
S9Z6 will prototype the replay builder.
S10A consumes the derived state, not raw events directly.
```

---

## 3. Reducer Input Contract
The Event Reducer processes a sanitized stream of raw events. Its input must strictly contain:
* A **validated learner event collection** passing schema validation.
* **Normalized UTC timestamps** (`occurred_at_utc`) resolved by the validator.
* **Quarantine-excluded valid events**: Any event flagged with `quality_flags.requires_review: true` is excluded from scoring by default unless an explicit review override is logged.
* **Optional reducer configuration**: Weighting parameters and default decay intervals.
* **Optional current graph snapshot metadata**: Information mapping target IDs to active CEFR graph structures.

---

## 4. Event Ordering Policy
Offline clients can upload events out of chronological order. To guarantee that replaying the log produces an identical, deterministic state projection, the reducer must sort all events prior to state reduction:

```text
primary sort: occurred_at_utc
secondary sort: event_id
tertiary sort: input_index
```

This ordering policy guarantees deterministic replay order. Process-restart-safe idempotency additionally depends on duplicate event_id protection, stable event indexing, and append safety. No matter the network arrival order, a rebuild of the learner state from the event log will always yield identical results.

---

## 5. Event-to-Evidence Projection
Raw events are processed and projected into five specialized evidence containers.

### Exposure Evidence
* **Source Event Types:** Any event containing `counts_as_exposure: true` (e.g., `exposure_seen`, `practice_started`, `answer_submitted`, `assessment_attempt`).
* **Required Fields:** `occurred_at`, `source_type`, `target_nodes`.
* **Derived Metrics:**
  * `exposure_count`: Cumulative exposures.
  * `first_seen_at`: ISO timestamp of the earliest exposure.
  * `last_seen_at`: ISO timestamp of the latest exposure.
  * `exposure_source_types`: Unique sources representing where the exposure occurred (e.g. `reading`, `dialogue`).
  * `passive_vs_active_exposure_count`: Count of pure passive reads (`exposure_seen`) vs active challenges.
* **Rules:**
  * `exposure_seen` events update exposure metrics only.
  * Exposure alone must not increase the mastery score.
  * Exposure is used to calculate initial readiness or candidate familiarity.

### Practice Evidence
* **Source Event Types:** `answer_submitted`, `practice_started`, `practice_completed`, `retry_attempt`, and optionally `hint_used`.
* **Required Fields:** `attempt.is_correct`, `attempt.score`, `attempt.response_time_ms`, `attempt.used_hint`.
* **Derived Metrics:**
  * `practice_attempt_count`: Total attempts.
  * `first_try_correct_count`: Count of correct answers on `attempt_number == 1`.
  * `corrected_after_retry_count`: Successes on retry attempts after an initial incorrect submission.
  * `average_response_time_ms`: Sum of response times divided by total attempts.
  * `latest_practice_at`: UTC timestamp of the latest practice interaction.
  * `practice_success_rate`: Percentage of correct attempts.
* **Rules:**
  * First attempts and retries must be evaluated separately in metrics.
  * Successes aided by hints (`used_hint == true`) must not count as full independent practice successes.
  * Practice evidence can increase functional mastery scoring but must not affect formal assessment confidence metrics.

### Assessment Evidence
* **Source Event Types:** `assessment_attempt`, `mastery_check`.
* **Required Fields:** `attempt.score`, `attempt.max_score`, `evidence_flags.counts_as_assessment`.
* **Derived Metrics:**
  * `assessment_attempt_count`: Total assessments taken.
  * `assessment_success_rate`: Cumulative score ratio over maximum potential score.
  * `latest_assessment_at`: Timestamp of the latest assessment.
  * `retention_check_pass_count`: Count of successful retention checks.
  * `retention_check_fail_count`: Count of failed retention checks.
  * `assessment_confidence`: High/Medium/Low confidence status based on sample size and age.
* **Rules:**
  * Every assessment event requires numeric `score` and `max_score` metrics.
  * Assessment events are weighted higher in confidence calculations than practice events.
  * A failed `mastery_check` triggers a downgrade in the mastery band or flags the item for the review queue.

### Reinforcement Evidence
* **Source Event Types:** `hint_used`, `retry_attempt`, incorrect `answer_submitted`, low-score assessment attempt, or repeated exposure without subsequent practice.
* **Required Fields:** `attempt.used_hint`, `attempt.is_correct`, `evidence_flags.counts_as_reinforcement`.
* **Derived Metrics:**
  * `hint_count`: Total hints requested.
  * `retry_count`: Total retries executed.
  * `incorrect_count`: Count of failed attempts.
  * `weak_node_signal_count`: Number of times an associated node triggers a reinforcement requirement.
  * `reinforcement_need_score`: Value representing target weakness.
* **Rules:**
  * Reinforcement evidence represents learning support, not just failures.
  * These metrics are used by the candidate ranker to identify targeted review and retry opportunities.

### Engagement Evidence
* **Source Event Types:** `practice_started`, `practice_completed`, `content_completed`.
* **Required Fields:** `session_id`, `attempt.response_time_ms` (or session duration metadata).
* **Derived Metrics:**
  * `session_started_count`: Count of started learning sessions.
  * `session_completed_count`: Count of clean session exits.
  * `content_completed_count`: Units, stories, or assessment blocks completed.
  * `dropout_signal`: Incomplete sessions indicating potential dropout risks.
  * `time_on_task_proxy`: Cumulative response times serving as active learning duration proxy.
* **Rules:**
  * Engagement metrics do not influence node mastery scores.
  * These values are consumed by the planner to modulate pacing (e.g. accelerating or deceleration material).

---

## 6. Node-Level Aggregation Model
The reducer aggregates evidence at the individual CEFR node level, mapping events to:
* **Vocabulary Nodes** (`vocab:...`)
* **Grammar Nodes** (`grammar:...`)
* **Sentence Pattern Nodes** (`pattern:...`)
* **Chunk Nodes** (`chunk:...`)
* **Theme Nodes** (`theme:...`)

### Theme Mastery Rule
```text
theme can receive exposure and engagement projection,
but theme-only mastery updates are not allowed.
```
* **Rationale:** Themes are broad context folders. Mastery exists in the concrete vocabulary, grammar, chunk, and sentence pattern nodes that form that theme. Direct event scoring must not raise a theme's mastery level; theme-level mastery should instead be derived by aggregating the coverage and scores of its child nodes.

### Target Node Projection Record Example
For each node with matching event evidence, the reducer maintains a projection record:

```json
{
  "learner_id": "learner:usr_001",
  "node_id": "vocab:banana",
  "node_type": "vocabulary",
  "exposure": {
    "count": 3,
    "first_seen_at": "2026-06-18T11:10:52Z",
    "last_seen_at": "2026-06-18T11:20:52Z"
  },
  "practice": {
    "attempt_count": 2,
    "first_try_correct_count": 1,
    "retry_count": 1,
    "hint_count": 0,
    "success_rate": 0.5
  },
  "assessment": {
    "attempt_count": 1,
    "success_rate": 1.0,
    "latest_assessment_at": "2026-06-18T11:30:52Z"
  },
  "mastery_projection": {
    "raw_score": 0.72,
    "decay_adjusted_score": 0.68,
    "band": "functional",
    "confidence": "medium"
  }
}
```

---

## 7. Mastery Projection Principles
The reducer maps signals to a single numerical score ranging from `0.0` to `1.0`. The scoring algorithm evaluates:
* `exposure_count`
* `practice_success_rate`
* `first_try_success_rate`
* `assessment_success_rate`
* `hint_penalty`
* `retry_penalty`
* `recency` (decay over time)
* `retention_check_result`
* Node prerequisite status (blocked state checking)
* Confidence levels (number of samples collected)

### Conceptual Scoring Formula
```text
mastery_projection_score =
    weighted_practice_signal
    + weighted_assessment_signal
    + retention_signal
    + exposure_familiarity_signal
    - hint_penalty
    - retry_penalty
    - decay_penalty
```

```text
Exact weights are deferred to S9Z6 or later calibration.
S9Z5 only defines architecture and signal categories.
```

---

## 8. Mastery Band Transition Model
Nodes are classified into discrete mastery bands:
1. **`unknown`**: No exposure record.
2. **`seen`**: Exposure recorded, but no active practice.
3. **`practicing`**: Initial incorrect/correct practices, score unstable.
4. **`functional`**: Solid practice success rate, but no formal assessment.
5. **`mastered`**: Successful assessment or mastery check.
6. **`automatic`**: Repeated, spaced successful assessments over time.
7. **`review_needed`**: Significant decay or failed assessment check.
8. **`blocked`**: Unlocked prerequisites prevent mastery progression.

### Transitions Flow
```text
unknown -> seen
seen -> practicing
practicing -> functional
functional -> mastered
mastered -> automatic
mastered -> review_needed
review_needed -> practicing
blocked -> seen/practicing only after prerequisites improve
```

### Transition Guardrails
* Exposure alone can only transition a node from `unknown -> seen`.
* Practice success transitions nodes from `seen -> practicing -> functional`.
* Assessment success transitions nodes from `functional -> mastered`.
* Spaced repetitions transition nodes from `mastered -> automatic`.
* Assessment failures or mastery check drops transition nodes to `review_needed`.
* Unmet prerequisite conditions constrain nodes to the `blocked` band.

---

## 9. Decay and Retention Design
Mastery decay reflects the biological reality of forgetting. The reducer calculates decay metrics using:
* `last_seen_at` and `last_success_at`: Measures elapsed time since active recall.
* `latest_assessment_at`: Serves as the anchor for formal memory retention.
* Spaced repetition intervals: Scales decay rates depending on the frequency of successful spacing.
* Retention check outcomes: Directly confirms memory status.
* `decay-adjusted_score`: Applies a time-based decay function (e.g., exponential decay) to the raw score.
* Stale mastery detection: Flags nodes that have had no exposure within a critical CEFR level threshold (e.g., 90 days for A1/A2, 180 days for B1/B2).

```text
S9Z5 should define what data is needed for decay,
but not implement a decay formula.
```

---

## 10. Quarantine and Review Policy
Events flagged by the validator are processed as follows:
* **Invalid events** are rejected outright and not replayed.
* **Quarantined events** (`quality_flags.requires_review: true`) are excluded from mastery calculations to avoid contaminating learner states with noisy or incorrect telemetry.
* **Auditability**: Quarantined events remain in raw reports for investigation.
* **Review Overrides**: If a quarantined event is approved, it can be replayed during a rebuild if an authorized override is provided in the configuration.
* Overrides must be recorded in the reducer execution log.

---

## 11. Idempotency and Replay Policy
Because derived states must be deterministic projections, rebuilding the state from the log must follow strict rules:
* The reducer does not mutate raw event logs.
* Outputs must be completely rebuildable from the raw logs.
* Replaying the same logs under the same reducer version and configuration yields identical output states.
* Reducer execution reports must document the `reducer_version` and a hash of the configuration parameters used.

```text
event log = source of truth
learner_state = derived cache
mastery_graph = derived overlay
```

---

## 12. Reducer Output Design
Future reduction runs will produce three output targets:
1. `ulga/learner_state/learner_state.json`: Summary metadata of the learner.
2. `ulga/learner_state/mastery_graph.json`: Graph overlay detailing individual node bands and scores.
3. `ulga/reports/learner_event_reducer_summary.json`: Summary execution report.

### Proposed Reducer Summary Report Structure
```json
{
  "status": "DESIGN_ONLY",
  "reducer_version": "S9Z5-design",
  "input_summary": {
    "events_received": 0,
    "events_reduced": 0,
    "events_excluded": 0
  },
  "node_projection_summary": {
    "vocabulary_nodes": 0,
    "grammar_nodes": 0,
    "pattern_nodes": 0,
    "chunk_nodes": 0,
    "theme_nodes": 0
  },
  "policy_summary": {
    "quarantine_excluded": true,
    "theme_only_mastery_blocked": true,
    "exposure_only_mastery_blocked": true
  }
}
```

---

## 13. Integration Risks
* **Over-weighting Exposure:** Confusing familiarity with active capability, leading to premature content unlocking.
* **Practice Inflation:** Inflating mastery scores by ignoring retry penalties or spacing.
* **Hint Exploitation:** Boosting mastery scores via hints.
* **Response Time Noise:** Response time anomalies caused by client-side interruptions.
* **Assessment Overfitting:** Pushing mastery scores high based on repeated similar assessments.
* **Ordering Anomalies:** Timezone normalization bugs skewing chronology.
* **Event Schema Drift:** Validator/schema shifts causing processing errors on historical logs.
* **Theme-Only Contamination:** Accidentally modifying target vocab mastery when checking theme-level metrics.
* **Cache Out-of-Sync:** Stale `learner_state` cache files leading to incorrect candidate rankings.

---

## 14. Acceptance Criteria
S9Z5 is complete if this design scan:
1. Defines the reducer's boundaries separating log, validator, reducer, learner state, ranking, and planner.
2. Formulates deterministic sorting and replay logic.
3. Outlines event-to-evidence metrics mapping.
4. Describes node aggregation and theme restrictions.
5. Models mastery score elements and transition bands.
6. Details quarantine, override, and idempotency designs.
7. Confirms zero modification of graphs, validator code, or state cache files.

---

## 15. Recommended Next Task
The next task is **ULGA-S9Z6_LearnerStateReplay_Prototype**.

S9Z6 will build a working prototype that:
* Reads a validated learner event collection.
* Sorts the collection deterministically by occurred timestamp.
* Aggregates exposure, practice, assessment, and reinforcement metrics.
* Outputs a prototype `learner_state` JSON.
* Retains isolated prototyping targets separated from production data folders until validation passes.
