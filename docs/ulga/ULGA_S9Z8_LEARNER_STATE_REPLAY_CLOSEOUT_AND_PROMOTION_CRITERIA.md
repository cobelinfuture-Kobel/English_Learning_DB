# ULGA-S9Z8 Learner State Replay Closeout And Promotion Criteria

## 1. Scope

S9Z8 closes out the S9Z learner event replay prototype sequence and defines the promotion criteria required before any future movement from prototype learner state projection toward canonical learner state integration.

S9Z8 does not promote prototype learner_state.
S9Z8 does not modify canonical learner_state.
S9Z8 does not connect to S10A Candidate Ranking.
S9Z8 defines the rules required before those actions are allowed.

## 2. S9Z Sequence Closeout Summary

### S9Z2 = Event Log Architecture

- Purpose: defined immutable learner event log boundaries, event taxonomy, and replay-first architecture.
- Created artifacts: `docs/ulga/ULGA_S9Z2_LEARNER_EVENT_LOG_DESIGN_SCAN.md`
- Current status: complete
- Production-ready or prototype-only: architectural foundation only

### S9Z3 = Single Event Schema

- Purpose: created the canonical single learner event JSON Schema.
- Created artifacts: `ulga/schemas/learner_event_log_schema.json`, `tests/ulga/test_learner_event_log_schema.py`, `docs/ulga/ULGA_S9Z3_LEARNER_EVENT_LOG_SCHEMA_IMPLEMENTATION.md`
- Current status: complete
- Production-ready or prototype-only: foundation ready for validation use, not sufficient alone for production replay

### S9Z4 = Event Collection Validator

- Purpose: implemented collection-level validation, duplicate detection, timezone normalization, and quarantine handling.
- Created artifacts: `ulga/validators/validate_learner_event_log.py`, `tests/ulga/test_validate_learner_event_log.py`, implementation documentation and fixtures
- Current status: complete
- Production-ready or prototype-only: validation layer implemented, downstream promotion still blocked

### S9Z5 = Reducer Design

- Purpose: defined deterministic replay ordering, evidence buckets, node aggregation principles, quarantine policy, and future reducer requirements.
- Created artifacts: `docs/ulga/ULGA_S9Z5_LEARNER_EVENT_REDUCER_DESIGN_SCAN.md`
- Current status: complete with approved errata alignment
- Production-ready or prototype-only: design authority only

### S9Z6 = Replay Prototype

- Purpose: implemented a prototype replay builder and isolated prototype learner state / mastery graph outputs.
- Created artifacts: `ulga/builders/build_learner_state_replay_prototype.py`, `tests/ulga/test_learner_state_replay_prototype.py`, fixture, prototype outputs, and documentation
- Current status: complete
- Production-ready or prototype-only: prototype only

### S9Z7 = Read-Only QA Audit

- Purpose: audited S9Z6 for determinism, isolation, errata alignment, exclusion behavior, and output shape.
- Created artifacts: `ulga/audits/audit_learner_state_replay_prototype.py`, `ulga/reports/learner_state_replay_prototype_qa_audit.json`, `docs/ulga/ULGA_S9Z7_LEARNER_STATE_REPLAY_QA_AUDIT.md`
- Current status: complete, audit returned `PASS`
- Production-ready or prototype-only: prototype QA only

### S9Z8 = Promotion Criteria / Closeout

- Purpose: closes the S9Z sequence and defines strict rules for any future promotion toward canonical learner state.
- Created artifacts: this document, plus optional readiness metadata
- Current status: complete after S9Z8 delivery
- Production-ready or prototype-only: governance and readiness criteria only

## 3. Current System State

- event schema = implemented
- event validator = implemented
- replay prototype = implemented
- prototype QA = passed
- canonical learner_state promotion = not allowed yet
- S10A integration = not allowed yet
- planner integration = not allowed yet

The system has a validated prototype replay path, not a production learner state pipeline.

## 4. Promotion Decision

Promotion to canonical learner_state: NOT ALLOWED IN S9Z8

Reason:

- prototype weights are not calibrated
- no decay formula
- no dependency lock integration
- no canonical learner_state schema migration plan
- no event store append safety
- no full idempotency guarantee
- no rollback plan implemented
- no S10A integration contract

## 5. Promotion Blockers

### 1. Scoring Calibration Blocker

- S9Z6 uses prototype-only weights.
- Production scoring must define calibrated weighting or externally approved heuristic policy.

### 2. Decay Policy Blocker

- No formal decay formula exists.
- Production learner state requires explicit recency, retention, and stale mastery handling.

### 3. Dependency Lock Blocker

- No prerequisite dependency integration exists.
- `blocked` mastery band is not implemented in S9Z6.

### 4. Canonical Schema Blocker

- Prototype output shape has not been aligned with canonical `learner_state.json` schema.
- A canonical learner state schema migration plan is needed.

### 5. Event Store Idempotency Blocker

- Deterministic replay order exists.
- Complete process-restart-safe idempotency is not yet guaranteed.
- Promotion requires append safety, stable event index, and duplicate replay protection.

### 6. Rollback / Backup Blocker

- No backup or restore process exists for canonical learner state promotion.
- Promotion must be reversible.

### 7. S10A Contract Blocker

- Candidate Ranking must consume a stable derived learner state contract.
- S10A must not consume raw event logs directly.

### 8. QA Coverage Blocker

- Multi-fixture replay QA is still missing.
- Additional edge-case coverage is required for:
  - multiple learners
  - multiple sessions
  - mixed CEFR levels
  - empty event collection
  - all-quarantine input
  - all-invalid input
  - same timestamp tie-breaking
  - timezone offset mixture
  - long replay sequence

## 6. Promotion Prerequisites

Promotion may only be considered after these follow-on tasks or equivalent scope have been completed:

- `ULGA-S9Z9_LearnerStateReplay_PromotionReadiness_Audit`
- `ULGA-S9ZA_LearnerStateCanonicalSchema_DesignScan`
- `ULGA-S9ZB_LearnerStateReplay_CalibrationPolicy_DesignScan`
- `ULGA-S9ZC_LearnerStateReplay_DependencyLock_DesignScan`
- `ULGA-S9ZD_LearnerStateReplay_EventStoreSafety_DesignScan`

Task names may be adjusted later, but the underlying concerns must be resolved before canonical promotion.

## 7. Promotion Readiness Checklist

| Area | Requirement | Current Status | Promotion Ready? |
|---|---|---|---|
| Schema | Event schema exists | PASS | Yes |
| Validator | Collection validator exists | PASS | Yes |
| Replay | Prototype replay exists | PASS | Prototype only |
| QA | S9Z7 QA passed | PASS | Prototype QA only |
| Scoring | Calibrated scoring exists | Missing | No |
| Decay | Formal decay policy exists | Missing | No |
| Dependency lock | `blocked` band integrated | Missing | No |
| Canonical schema | canonical learner_state contract aligned | Missing | No |
| Idempotency | append safety + stable index exists | Missing | No |
| Rollback | backup/restore promotion process exists | Missing | No |
| S10A contract | stable read contract exists | Missing | No |

## 8. Allowed Future Promotion Flow

Safe future promotion flow:

```text
prototype replay
-> promotion readiness audit
-> canonical learner_state schema alignment
-> calibration / decay / dependency policy
-> shadow canonical learner_state generation
-> read-only comparison with prototype output
-> backup / rollback plan
-> manual promotion approval
-> canonical learner_state write
-> post-promotion QA
-> S10A read-only integration
```

Promotion must happen through a dedicated promotion task.
Promotion must not happen accidentally inside QA, audit, or ranking work.

## 9. Explicitly Forbidden Actions

After S9Z8, these actions remain forbidden:

- overwrite `ulga/learner_state/learner_state.json`
- overwrite canonical mastery graph
- connect S9Z6 output directly to S10A
- connect S9Z6 output directly to planner
- treat prototype weights as production scores
- treat exposure-only nodes as mastered
- treat theme nodes as directly mastered
- remove quarantine exclusion
- claim full idempotency without event store safety
- bypass manual promotion approval

## 10. Canonical Learner State Promotion Requirements

A future canonical learner state promotion must include:

- canonical schema contract
- versioned reducer configuration
- reducer version
- input event log hash
- event count
- excluded event count
- quarantine count
- invalid count
- generated_at
- backup path
- rollback instructions
- promotion approval metadata
- post-promotion QA result
- downstream compatibility report

## 11. S10A Candidate Ranking Integration Gate

S10A may only consume learner state when:

- canonical learner_state schema is stable
- promotion QA passed
- derived state includes `node_id`, `node_type`, `band`, `raw_score`, `confidence`, `last_seen_at`, and reinforcement indicators
- candidate ranking reads learner_state as read-only input
- candidate ranking does not mutate learner_state
- candidate ranking does not read raw events directly unless explicitly designed as audit mode

Until then:

S10A integration remains blocked.

## 12. Risk Register

| Risk | Severity | Current Mitigation | Required Future Task |
|---|---|---|---|
| Prototype score overfitting | High | Prototype outputs remain non-canonical | `ULGA-S9ZB_LearnerStateReplay_CalibrationPolicy_DesignScan` |
| False mastery from insufficient attempts | High | Exposure-only ceiling and review-needed priority exist in prototype | `ULGA-S9Z9_LearnerStateReplay_PromotionReadiness_Audit` |
| Lack of decay formula | High | Promotion blocked | `ULGA-S9ZA` or dedicated decay design task |
| Dependency lock absence | High | Promotion blocked and `blocked` band deferred | `ULGA-S9ZC_LearnerStateReplay_DependencyLock_DesignScan` |
| Event store duplicate replay | High | Validator detects duplicates, but append safety is missing | `ULGA-S9ZD_LearnerStateReplay_EventStoreSafety_DesignScan` |
| Schema migration mismatch | High | Prototype remains isolated from canonical learner state | `ULGA-S9ZA_LearnerStateCanonicalSchema_DesignScan` |
| learner_state cache staleness | Medium | No canonical promotion path exists yet | future canonical promotion / rollback task |
| Candidate ranking reading unstable fields | High | S10A integration explicitly blocked | future S10A contract task |
| Planner acting on prototype output | High | Planner integration explicitly blocked | future planner gate / integration design task |
| Rollback failure | High | No promotion allowed before rollback plan exists | future promotion implementation task |

## 13. Readiness JSON Contract

An optional machine-readable readiness artifact may be maintained at:

`ulga/reports/learner_state_replay_promotion_readiness.json`

It must remain metadata-only and must not contain actual learner state promotion output.

## 14. Acceptance Criteria

S9Z8 is complete if:

- closeout markdown is created
- promotion remains explicitly disallowed
- S9Z sequence status is summarized
- promotion blockers are listed
- future promotion prerequisites are defined
- S10A integration remains blocked
- forbidden actions are explicit
- rollback and versioning requirements are documented
- no canonical learner state files are modified
- no graph, runtime, ranking, or planner files are modified

## 15. Recommended Next Task

`ULGA-S9Z9_LearnerStateReplay_PromotionReadiness_Audit`

S9Z9 should remain read-only and verify whether any blocker has been resolved.

Do not recommend direct S10A integration after S9Z8.
Do not recommend canonical learner_state promotion after S9Z8.

## Closeout Summary

### Files Created

- `docs/ulga/ULGA_S9Z8_LEARNER_STATE_REPLAY_CLOSEOUT_AND_PROMOTION_CRITERIA.md`
- `ulga/reports/learner_state_replay_promotion_readiness.json`

### Files Modified

- None

### Boundary Confirmation

- Canonical learner state was not modified.
- Canonical mastery graph was not modified.
- Runtime code was not modified.
- Candidate ranking files were not modified.
- Planner logic was not modified.

### Final Decision

- Promotion to canonical learner_state remains blocked after S9Z8.
- S10A Candidate Ranking integration remains blocked after S9Z8.
- The replay pipeline has completed prototype implementation and prototype QA, but not promotion readiness.
