# ULGA-S9ZA Learner State Canonical Schema Design Scan

## 1. Scope

S9ZA defines the target canonical learner state contract that future replay promotion must map into.

S9ZA does not implement canonical learner_state.
S9ZA does not promote prototype output.
S9ZA does not connect to S10A.
S9ZA defines the target contract for future mapping and promotion.

## 2. Why Canonical Learner State Is Needed

The current S9Z6 replay output is a prototype replay projection. It is useful for replay testing, prototype scoring checks, and QA validation, but it is not a stable production contract.

The future canonical `learner_state.json` serves a different role:

- prototype projection is for replay testing and QA
- canonical learner_state is the stable derived cache used by future downstream systems
- S10A Candidate Ranking must consume canonical learner_state, not raw event logs and not prototype output
- canonical learner_state must be versioned, auditable, and rebuildable

The main gap is that S9Z6 emphasizes replay evidence visibility, while a canonical contract must emphasize stable downstream consumption, provenance, policy traceability, and promotion safety.

## 3. Design Principles

1. learner_state is derived, not manually authored
2. event log remains source of truth
3. canonical learner_state must be rebuildable
4. canonical learner_state must be read-only for ranking and planner
5. scoring fields must be explicitly versioned
6. prototype-only fields must not leak into production
7. theme mastery must be derived, not directly scored
8. exposure-only cannot imply mastery
9. quarantine and invalid event exclusions must be traceable
10. promotion must be reversible

## 4. Canonical Learner State Top-Level Shape

Proposed top-level design:

```json
{
  "schema_version": "learner_state.v1",
  "state_id": "learner_state:learner:usr_001:20260618T120000Z",
  "learner_id": "learner:usr_001",
  "generated_at": "2026-06-18T12:00:00Z",
  "source": {
    "source_type": "event_replay",
    "event_log_hash": "sha256:...",
    "event_count_total": 0,
    "event_count_replayed": 0,
    "event_count_excluded": 0,
    "quarantine_count": 0,
    "invalid_count": 0
  },
  "reducer": {
    "reducer_version": "ULGA-S9Zx",
    "config_version": "reducer_config.v1",
    "config_hash": "sha256:...",
    "scoring_policy_version": "scoring_policy.v1",
    "decay_policy_version": "decay_policy.v1"
  },
  "learner_summary": {},
  "node_mastery": [],
  "theme_summary": [],
  "review_queue_signals": [],
  "promotion_metadata": {},
  "audit": {}
}
```

This is a design proposal only. It is not a generated file and not a schema implementation.

## 5. Required Top-Level Fields

| Field | Purpose | Required | Type | Downstream Consumer | S10A May Read | Planner May Read Later | Internal Only |
|---|---|---|---|---|---|---|---|
| `schema_version` | identifies canonical contract version | Yes | string | all future readers | Yes | Yes | No |
| `state_id` | unique state snapshot identity | Yes | string | audit, promotion tooling | Yes | Yes | No |
| `learner_id` | identifies the learner | Yes | string | all downstream readers | Yes | Yes | No |
| `generated_at` | records snapshot generation time | Yes | string timestamp | audit, freshness checks | Yes | Yes | No |
| `source` | captures replay provenance and event coverage | Yes | object | audit, rollback, freshness checks | Limited | Limited | No |
| `reducer` | captures reducer and policy versions | Yes | object | audit, compatibility gates | Limited | Limited | No |
| `learner_summary` | learner-level aggregate overview | Yes | object | broad filtering | Yes | Yes | No |
| `node_mastery` | canonical node-level mastery records | Yes | array | S10A and future planner | Yes | Yes | No |
| `theme_summary` | derived theme readiness view | Yes | array | future ranking / reporting | Yes | Yes | No |
| `review_queue_signals` | canonical reinforcement and review triggers | Yes | array | future ranking and review flows | Yes | Yes | No |
| `promotion_metadata` | records promotion state and approvals | Yes | object | promotion workflow | No | No | Mostly |
| `audit` | records QA and readiness state | Yes | object | safety gates | Limited | Limited | Mostly |

## 6. Source Metadata Contract

Required source fields:

- `source_type`
- `event_log_hash`
- `event_count_total`
- `event_count_replayed`
- `event_count_excluded`
- `quarantine_count`
- `invalid_count`
- `input_window_start`
- `input_window_end`

Purpose:

- prove learner_state is derived from event log
- enable replay audit
- prevent stale or untraceable state
- support rollback and rebuild comparison

Design notes:

- `source_type` should default to `event_replay`
- `event_log_hash` must identify the exact replay input basis
- excluded counts must remain explicit so downstream systems can reject partial or opaque state
- `input_window_start` and `input_window_end` must capture the actual replay evidence horizon, not planner runtime time

## 7. Reducer Metadata Contract

Required reducer fields:

- `reducer_version`
- `config_version`
- `config_hash`
- `scoring_policy_version`
- `decay_policy_version`
- `dependency_policy_version`
- `promotion_policy_version`

Rules:

- scoring version must be explicit
- decay version must be explicit even if decay policy is pending
- dependency policy version must exist even if dependency lock is not yet implemented
- S10A must not consume learner_state if reducer metadata is missing

Design implication:

S9Z6 currently exposes only `reducer_version`. The canonical contract must expand this to full policy traceability so downstream readers can reject incompatible state.

## 8. Learner Summary Contract

Suggested learner-level summary:

```json
{
  "level_scope": ["A1"],
  "active_levels": ["A1"],
  "total_nodes_tracked": 0,
  "nodes_by_band": {
    "unknown": 0,
    "seen": 0,
    "practicing": 0,
    "functional": 0,
    "mastered": 0,
    "automatic": 0,
    "review_needed": 0,
    "blocked": 0
  },
  "last_activity_at": null,
  "latest_replay_at": null,
  "overall_readiness_band": "early"
}
```

Clarifications:

- this is summary only
- S10A may use it for broad filtering
- node-level decisions must use `node_mastery`

Recommended semantics:

- `level_scope` = levels represented in current state snapshot
- `active_levels` = levels with meaningful replayed learner activity
- `overall_readiness_band` = coarse planning signal only, never a substitute for node-level mastery

## 9. Node Mastery Contract

Canonical node-level record proposal:

```json
{
  "node_id": "vocab:banana",
  "node_type": "vocabulary",
  "level": "A1",
  "band": "review_needed",
  "raw_score": 0.62,
  "decay_adjusted_score": 0.58,
  "confidence": "medium",
  "last_seen_at": "2026-06-18T10:07:00Z",
  "last_success_at": "2026-06-18T10:06:00Z",
  "latest_assessment_at": "2026-06-18T10:07:00Z",
  "evidence": {
    "exposure_count": 5,
    "practice_attempt_count": 2,
    "assessment_attempt_count": 3,
    "hint_count": 1,
    "retry_count": 1,
    "incorrect_count": 2,
    "first_try_correct_count": 1,
    "retention_check_pass_count": 1,
    "retention_check_fail_count": 1
  },
  "signals": {
    "needs_reinforcement": true,
    "stale_mastery": false,
    "dependency_blocked": false,
    "theme_only_mastery_blocked": false,
    "exposure_only_ceiling_applied": false
  },
  "policy_trace": {
    "scoring_policy_version": "scoring_policy.v1",
    "decay_policy_version": "decay_policy.v1",
    "dependency_policy_version": "dependency_policy.v1"
  }
}
```

Required design decisions:

- `node_id`, `node_type`, `band`, `raw_score`, and `confidence` are required
- `decay_adjusted_score` should be required, but may equal `raw_score` until decay is implemented
- `theme` node direct mastery must be blocked or derived only
- `blocked` band must be reserved even if not implemented yet
- `review_needed` must be a first-class band
- S10A may read `node_id`, `node_type`, `band`, score, confidence, and reinforcement signals
- S10A must not mutate `node_mastery`

Additional design guidance:

- Required node types in scope: `vocabulary`, `grammar`, `pattern`, `chunk`, `theme`
- Canonical `level` should be explicit at node level even if later derived from graph metadata
- `policy_trace` belongs with each node record so partial snapshots remain auditable

## 10. Mastery Band Contract

Canonical bands:

- `unknown`
- `seen`
- `practicing`
- `functional`
- `mastered`
- `automatic`
- `review_needed`
- `blocked`

| Band | Meaning | Allowed Transition Source | S10A May Recommend New Learning | S10A Should Recommend Reinforcement | Planner Stability Later |
|---|---|---|---|---|---|
| `unknown` | no meaningful evidence yet | initial state | Yes, cautiously | No | unstable |
| `seen` | exposure exists but no active mastery evidence | `unknown` | Yes | Usually no | unstable |
| `practicing` | active attempts exist but mastery is still unstable | `seen`, `review_needed` | Yes | Often yes | unstable |
| `functional` | learner performs adequately in practice but lacks stronger confirmation | `practicing` | Yes | Sometimes | moderately stable |
| `mastered` | strong direct evidence supports reliable command | `functional` | Maybe, depending on dependencies | Low | stable |
| `automatic` | repeated spaced evidence supports durable mastery | `mastered` | Yes | Rarely | highly stable |
| `review_needed` | recent evidence or decay indicates remediation is needed | any evidence-backed band | No for forward unlock | Yes | unstable |
| `blocked` | prerequisites or policy prevent downstream unlock | any band where dependency gate applies | No | Possibly prerequisite repair only | blocked |

Required guardrails:

- exposure-only can only reach `seen`
- theme-only direct mastery is blocked
- failed `mastery_check` can force `review_needed`
- `blocked` prevents downstream unlock
- `automatic` requires repeated spaced evidence

## 11. Theme Summary Contract

Theme state should be represented separately from raw node mastery scoring.

Important rule:

Themes are not directly mastered from single events.
Theme readiness is derived from child node coverage and mastery distribution.

Suggested structure:

```json
{
  "theme_id": "theme:a1_food_and_drink",
  "level": "A1",
  "coverage": {
    "child_nodes_total": 0,
    "child_nodes_seen": 0,
    "child_nodes_functional_or_above": 0,
    "child_nodes_review_needed": 0
  },
  "readiness": {
    "theme_readiness_band": "partial",
    "recommended_action": "reinforce"
  },
  "evidence_summary": {
    "exposure_count": 0,
    "content_completed_count": 0
  },
  "direct_mastery_blocked": true
}
```

Design rationale:

- `theme_summary` is the production replacement for implicit theme interpretation from prototype output
- a theme node may still exist in `node_mastery`, but its direct score must remain policy-limited
- downstream systems should prefer `theme_summary.readiness` over direct theme-node score

## 12. Review Queue Signals Contract

Suggested review signal shape:

```json
{
  "node_id": "vocab:banana",
  "node_type": "vocabulary",
  "reason_codes": [
    "failed_mastery_check",
    "retry_pressure",
    "hint_pressure"
  ],
  "priority": "high",
  "last_triggered_at": "2026-06-18T10:07:00Z",
  "evidence_refs": ["evt_007"]
}
```

Purpose:

- canonicalize review / reinforcement triggers
- decouple review routing from raw prototype metrics
- create a stable input for future reinforcement ranking

S10A may later use this for reinforcement candidate ranking.

But in S9ZA:

No S10A integration is allowed.

## 13. Promotion Metadata Contract

Required promotion metadata fields:

- `promotion_status`
- `promotion_allowed`
- `promotion_task_id`
- `promotion_approved_by`
- `promotion_approved_at`
- `backup_path`
- `rollback_plan_id`
- `post_promotion_audit_id`

Current default state:

```json
{
  "promotion_status": "not_promoted",
  "promotion_allowed": false
}
```

Design intent:

- canonical learner state must record whether it is only generated, shadow-generated, or manually promoted
- promotion metadata must exist even before promotion so readers can reject unapproved state

## 14. Audit Contract

Required audit fields:

- `audit_status`
- `last_audit_id`
- `last_audit_at`
- `qa_status`
- `warnings`
- `failures`
- `readiness_status`

Purpose:

- prove that learner_state was generated through approved pipeline
- allow S10A to reject unsafe learner_state
- allow future rollback and diagnosis

Recommended example:

```json
{
  "audit_status": "passed",
  "last_audit_id": "ULGA-S9Z9",
  "last_audit_at": "2026-06-18T12:00:00Z",
  "qa_status": "prototype_qa_passed",
  "warnings": [],
  "failures": [],
  "readiness_status": "not_ready_for_promotion"
}
```

## 15. S10A Read Contract

Stable read-only fields S10A may eventually consume:

- `learner_id`
- `schema_version`
- `node_mastery.node_id`
- `node_mastery.node_type`
- `node_mastery.level`
- `node_mastery.band`
- `node_mastery.raw_score`
- `node_mastery.decay_adjusted_score`
- `node_mastery.confidence`
- `node_mastery.last_seen_at`
- `node_mastery.last_success_at`
- `node_mastery.signals.needs_reinforcement`
- `node_mastery.signals.dependency_blocked`
- `review_queue_signals`
- `theme_summary.readiness`

Forbidden:

- S10A must not consume raw event logs directly
- S10A must not mutate learner_state
- S10A must not consume prototype output
- S10A must not ignore `promotion_allowed=false`

## 16. Prototype-to-Canonical Gap Analysis

Key gaps between S9Z6 prototype projection and proposed canonical schema:

- missing source metadata
- missing reducer config hash
- missing scoring, decay, and dependency policy versions
- missing promotion metadata
- missing audit metadata
- missing canonical S10A read contract
- prototype mastery score not calibrated
- `blocked` band not implemented
- `decay_adjusted_score` not real yet
- `theme_summary` not fully derived
- `review_queue_signals` not canonicalized

Additional observations from current artifacts:

- S9Z6 stores rich nested evidence buckets, but not canonical provenance metadata
- S9C record-style schema predates S9Z replay needs and lacks explicit replay source counters, promotion metadata, and audit contract
- S9Z6 theme handling is policy-correct for prototype QA, but canonical output needs separate `theme_summary` semantics to avoid overloading direct theme node state

This gap analysis is the direct setup for S9ZB.

## 17. Explicit Non-Goals

S9ZA does not:

- implement schema JSON
- modify learner_state
- promote prototype output
- implement scoring calibration
- implement decay formula
- implement dependency lock
- implement rollback system
- implement S10A integration
- implement planner integration

## 18. Acceptance Criteria

S9ZA passes if:

- markdown design scan is created
- canonical learner_state top-level structure is defined
- node mastery contract is defined
- mastery band contract is defined
- theme summary contract is defined
- review queue signal contract is defined
- promotion metadata contract is defined
- audit metadata contract is defined
- S10A read contract is defined
- prototype-to-canonical gaps are listed
- promotion remains blocked
- no canonical learner_state is modified
- no runtime, graph, ranking, or planner files are modified

## 19. Recommended Next Task

`ULGA-S9ZB_ReplayToCanonicalMapping_DesignScan`

S9ZB should define how S9Z6 prototype projection fields map into the proposed canonical learner_state contract.

Do not recommend implementation yet.
Do not recommend S10A integration yet.
Do not recommend promotion yet.

## Closeout Summary

### Files Created

- `docs/ulga/ULGA_S9ZA_LEARNER_STATE_CANONICAL_SCHEMA_DESIGN_SCAN.md`
- `ulga/reports/learner_state_canonical_schema_design_summary.json`

### Files Modified

- None

### Boundary Confirmation

- Canonical learner state was not modified.
- Canonical mastery graph was not modified.
- Runtime code was not modified.
- Candidate ranking files were not modified.
- Planner logic was not modified.
- Replay prototype output was not promoted.
