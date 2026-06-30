# ULGA-S9ZB Replay To Canonical Mapping Design Scan

## 1. Scope

S9ZB defines the mapping between S9Z6 prototype replay output and the S9ZA canonical learner_state contract.

S9ZB does not implement mapping.
S9ZB does not generate canonical learner_state.
S9ZB does not promote prototype output.
S9ZB does not connect to S10A.
S9ZB defines the field-level mapping plan required before future implementation.

## 2. Input and Target Artifacts

### Source Artifact

Prototype output from S9Z6:

- `ulga/learner_state/prototype/learner_state_projection_prototype.json`
- `ulga/learner_state/prototype/mastery_graph_projection_prototype.json`
- `ulga/reports/learner_state_replay_prototype_summary.json`

### Target Contract

Canonical learner_state contract from S9ZA:

- `schema_version`
- `state_id`
- `learner_id`
- `generated_at`
- `source`
- `reducer`
- `learner_summary`
- `node_mastery`
- `theme_summary`
- `review_queue_signals`
- `promotion_metadata`
- `audit`

Clarification:

S9ZB maps source fields to target contract.
S9ZB does not create the target file.

## 3. Mapping Principles

1. Mapping must preserve replay traceability.
2. Canonical learner_state must remain derived, not manually authored.
3. Prototype-only fields must not leak into production unless explicitly mapped.
4. Missing canonical fields must be marked as missing, pending, or future-derived.
5. S10A-readable fields must be stable and read-only.
6. Promotion metadata must default to `promotion_allowed=false`.
7. Audit metadata must identify the replay and QA lineage.
8. Theme direct mastery remains blocked.
9. Exposure-only ceiling remains enforced.
10. Mapping must not claim full idempotency unless event store safety exists.

## 4. Top-Level Mapping Matrix

| Canonical Field | Prototype Source Field | Mapping Type | Current Status | Transformation Required | Risk | Notes |
|---|---|---|---|---|---|---|
| `schema_version` | none | constant | missing | set to `learner_state.v1` | low | requires future canonical schema implementation |
| `state_id` | none | derived | missing | compose from learner_id + generated_at | medium | requires canonical timestamp and single-state identity rule |
| `learner_id` | `learner_ids[0]`, `nodes[].learner_id` | derived | partial | validate single vs multi learner semantics | medium | multi-learner support must be explicit |
| `generated_at` | none | future | missing | require builder output timestamp or reducer metadata | medium | prototype does not persist generated_at |
| `source` | prototype summary `input_summary` | derived | partial | normalize counts and add missing hash/window fields | high | replay provenance incomplete today |
| `reducer` | `reducer_version` | direct/derived | partial | expand to config and policy metadata | high | reducer metadata incomplete blocks promotion |
| `learner_summary` | `learner_ids`, `node_count`, `nodes[]` | derived | partial | aggregate node bands and activity timestamps | medium | overall readiness band should remain future-derived |
| `node_mastery` | `nodes[]` | direct/derived | partial | flatten nested evidence buckets into canonical node records | medium | requires field normalization and missing-field policy |
| `theme_summary` | theme nodes + child node grouping | derived/future | partial | derive coverage and readiness | high | child-theme linkage is incomplete |
| `review_queue_signals` | `nodes[].reinforcement`, `mastery_projection.band` | derived | partial | canonicalize reasons, priority, and event refs | high | event refs are currently missing |
| `promotion_metadata` | none | constant/blocked | blocked | set default not-promoted state | low | must remain blocked |
| `audit` | S9Z7, S9Z8, S9Z9 artifacts | derived | partial | persist latest audit lineage and readiness state | medium | future implementation needs stable audit timestamp/id fields |

## 5. Source Metadata Mapping

Canonical source fields:

- `source.source_type`
- `source.event_log_hash`
- `source.event_count_total`
- `source.event_count_replayed`
- `source.event_count_excluded`
- `source.quarantine_count`
- `source.invalid_count`
- `source.input_window_start`
- `source.input_window_end`

Mapping decisions:

| Canonical Source Field | Prototype Source | Status | Mapping Decision |
|---|---|---|---|
| `source_type` | implied by S9Z6 replay builder | derivable | set to `event_replay` |
| `event_log_hash` | none | missing | must be future-derived from validated event log input |
| `event_count_total` | `summary.input_summary.events_received` | direct | carry forward as integer |
| `event_count_replayed` | `summary.input_summary.events_replayed` | direct | carry forward as integer |
| `event_count_excluded` | derive from quarantine + invalid counts | derivable | sum excluded counts |
| `quarantine_count` | `summary.input_summary.events_excluded_quarantine` | direct | carry forward as integer |
| `invalid_count` | `summary.input_summary.events_excluded_invalid` | direct | carry forward as integer |
| `input_window_start` | replayed node timestamps only | partial | future reducer should derive from preserved replay event lineage |
| `input_window_end` | replayed node timestamps only | partial | future reducer should derive from preserved replay event lineage |

Important decisions:

- `event_log_hash` is currently missing and must be future-derived
- `input_window_start` and `input_window_end` can be derived from replayed event timestamps only if event lineage is preserved
- `quarantine_count` and `invalid_count` can map from prototype summary today

## 6. Reducer Metadata Mapping

Canonical reducer fields:

- `reducer.reducer_version`
- `reducer.config_version`
- `reducer.config_hash`
- `reducer.scoring_policy_version`
- `reducer.decay_policy_version`
- `reducer.dependency_policy_version`
- `reducer.promotion_policy_version`

Mapping status:

- `reducer_version` = available from prototype output
- `config_version` = missing
- `config_hash` = missing
- `scoring_policy_version` = missing or prototype-only
- `decay_policy_version` = missing / pending
- `dependency_policy_version` = missing / pending
- `promotion_policy_version` = missing / S9Z8-derived

Mapping table:

| Canonical Reducer Field | Prototype Source | Status | Notes |
|---|---|---|---|
| `reducer_version` | `learner_state_projection.reducer_version` | direct | current value is `ULGA-S9Z6-prototype` |
| `config_version` | none | missing | future reducer config artifact needed |
| `config_hash` | none | missing | future config hash support needed |
| `scoring_policy_version` | none | partial | may initially label prototype scoring policy, but production version must differ |
| `decay_policy_version` | none | missing | must exist even if decay equals raw score temporarily |
| `dependency_policy_version` | none | missing | required before `blocked` band can be authoritative |
| `promotion_policy_version` | S9Z8 governance only | future | should reference future promotion governance artifact |

Required rule:

Canonical learner_state is not promotion-ready until reducer metadata is complete.

## 7. Learner Summary Mapping

Canonical learner summary fields:

- `level_scope`
- `active_levels`
- `total_nodes_tracked`
- `nodes_by_band`
- `last_activity_at`
- `latest_replay_at`
- `overall_readiness_band`

Possible sources:

- `prototype.learner_ids`
- `prototype.node_count`
- `prototype.nodes[].metadata` or future node level resolution
- `prototype.nodes[].mastery_projection.band`
- `prototype.nodes[].exposure.last_seen_at`
- `prototype.nodes[].practice.latest_practice_at`
- `prototype.nodes[].assessment.latest_assessment_at`

Mapping rules:

- `total_nodes_tracked` from prototype `node_count`
- `nodes_by_band` from grouped node mastery bands
- `last_activity_at` from max of `last_seen_at`, `latest_practice_at`, or `latest_assessment_at`
- `latest_replay_at` from output generated timestamp if available; otherwise future reducer metadata
- `overall_readiness_band` is future-derived and should not be guessed in S9ZB

Field mapping status:

| Learner Summary Field | Source | Status | Notes |
|---|---|---|---|
| `level_scope` | none reliable today | missing | needs node-level or graph-derived CEFR linkage |
| `active_levels` | none reliable today | missing | depends on level derivation |
| `total_nodes_tracked` | `node_count` | direct | available |
| `nodes_by_band` | `nodes[].mastery_projection.band` | direct/derived | available with grouping |
| `last_activity_at` | node timestamp maxima | derivable | available from per-node evidence timestamps |
| `latest_replay_at` | none persisted today | missing | future builder must persist generation timestamp |
| `overall_readiness_band` | none | future | must not be improvised from prototype scores |

## 8. Node Mastery Mapping

Prototype source node shape includes:

- `node.learner_id`
- `node.node_id`
- `node.node_type`
- `node.exposure`
- `node.practice`
- `node.assessment`
- `node.reinforcement`
- `node.engagement`
- `node.mastery_projection`

Canonical target shape includes:

- `node_id`
- `node_type`
- `level`
- `band`
- `raw_score`
- `decay_adjusted_score`
- `confidence`
- `last_seen_at`
- `last_success_at`
- `latest_assessment_at`
- `evidence`
- `signals`
- `policy_trace`

Node field mapping:

| Canonical Field | Prototype Source Field | Mapping Type | Status | Notes |
|---|---|---|---|---|
| `node_id` | `node.node_id` | direct | ready | stable |
| `node_type` | `node.node_type` | direct | ready | stable |
| `level` | none reliable today | missing | partial | requires graph lookup or future node metadata |
| `band` | `node.mastery_projection.band` | direct | ready | stable for prototype contract |
| `raw_score` | `node.mastery_projection.raw_score` | direct | ready | remains prototype-scored until policy changes |
| `decay_adjusted_score` | none explicit today | derived/constant | partial | may equal raw score temporarily |
| `confidence` | `node.mastery_projection.confidence` | direct | ready | stable string confidence |
| `last_seen_at` | `node.exposure.last_seen_at` | direct | ready | available |
| `last_success_at` | none explicit today | derived | partial | could derive from future replay event references; not preserved today |
| `latest_assessment_at` | `node.assessment.latest_assessment_at` | direct | ready | available |
| `evidence.exposure_count` | `node.exposure.count` | direct | ready | available |
| `evidence.practice_attempt_count` | `node.practice.attempt_count` | direct | ready | available |
| `evidence.assessment_attempt_count` | `node.assessment.attempt_count` | direct | ready | available |
| `evidence.hint_count` | `node.practice.hint_count` or `node.reinforcement.hint_count` | derived | partial | canonical source of truth should be defined once |
| `evidence.retry_count` | `node.practice.retry_count` or `node.reinforcement.retry_count` | derived | partial | duplication must be normalized |
| `evidence.incorrect_count` | `node.practice.incorrect_count` or `node.reinforcement.incorrect_count` | derived | partial | duplication must be normalized |
| `evidence.first_try_correct_count` | `node.practice.first_try_correct_count` | direct | ready | available |
| `evidence.retention_check_pass_count` | `node.assessment.retention_check_pass_count` | direct | ready | available |
| `evidence.retention_check_fail_count` | `node.assessment.retention_check_fail_count` | direct | ready | available |
| `signals.needs_reinforcement` | `node.reinforcement.reinforcement_need_score` | derived | partial | threshold must remain non-final until policy version exists |
| `signals.stale_mastery` | none | missing | future | requires decay policy |
| `signals.dependency_blocked` | none | missing | future | requires dependency lock integration |
| `signals.theme_only_mastery_blocked` | derive from `node_type == theme` | derived | partial | can be policy-derived |
| `signals.exposure_only_ceiling_applied` | derive from band/evidence combination | derived | partial | requires explicit canonical flagging |
| `policy_trace.scoring_policy_version` | none | missing | future | must be explicit in reducer metadata |
| `policy_trace.decay_policy_version` | none | missing | future | pending |
| `policy_trace.dependency_policy_version` | none | missing | future | pending |

Important mapping decisions:

- `decay_adjusted_score` may equal `raw_score` temporarily only if `decay_policy_version` marks decay as pending
- `level` is currently partial or missing unless derived from node metadata or graph lookup
- `last_success_at` is partial and needs explicit reducer support
- `dependency_blocked` is false or pending until dependency lock integration exists
- `stale_mastery` is pending until decay policy exists

## 9. Theme Summary Mapping

Important rule:

Theme summary is derived from child node coverage and evidence distribution.
Theme direct mastery from event score remains blocked.

Mapping sources:

- prototype nodes where `node_type == theme`
- child node records grouped by theme if theme references are available
- engagement evidence from `content_completed` events

Canonical theme fields:

- `theme_id`
- `level`
- `coverage.child_nodes_total`
- `coverage.child_nodes_seen`
- `coverage.child_nodes_functional_or_above`
- `coverage.child_nodes_review_needed`
- `readiness.theme_readiness_band`
- `readiness.recommended_action`
- `evidence_summary.exposure_count`
- `evidence_summary.content_completed_count`
- `direct_mastery_blocked`

Mapping status:

| Canonical Theme Field | Source | Status | Notes |
|---|---|---|---|
| `theme_id` | theme node `node_id` | direct | ready | available |
| `level` | none reliable today | missing | future | requires graph or theme metadata |
| `coverage.child_nodes_total` | none reliable today | missing | future | requires theme-child mapping |
| `coverage.child_nodes_seen` | future child-node grouping | future | requires theme-child mapping |
| `coverage.child_nodes_functional_or_above` | future child-node grouping | future | requires theme-child mapping |
| `coverage.child_nodes_review_needed` | future child-node grouping | future | requires theme-child mapping |
| `readiness.theme_readiness_band` | none | future | must be derived, not copied from theme node band |
| `readiness.recommended_action` | none | future | depends on future policy |
| `evidence_summary.exposure_count` | theme node `exposure.count` | direct | ready | available |
| `evidence_summary.content_completed_count` | theme node `engagement.content_completed_count` | direct | ready | available |
| `direct_mastery_blocked` | policy constant | constant | ready | always true |

## 10. Review Queue Signals Mapping

Potential sources:

- `node.mastery_projection.band == review_needed`
- `node.reinforcement.reinforcement_need_score`
- `node.reinforcement.hint_count`
- `node.reinforcement.retry_count`
- `node.reinforcement.incorrect_count`
- `node.assessment.retention_check_fail_count`

Canonical fields:

- `node_id`
- `node_type`
- `reason_codes`
- `priority`
- `last_triggered_at`
- `evidence_refs`

Mapping rules:

- failed mastery check maps to `failed_mastery_check`
- high hint count maps to `hint_pressure`
- high retry count maps to `retry_pressure`
- incorrect count maps to `incorrect_pressure`
- `priority` is future policy-derived; S9ZB may propose prototype thresholds but must mark them non-final
- `evidence_refs` are currently missing unless reducer preserves event IDs per node

Suggested provisional derivation:

| Canonical Review Field | Source | Status | Notes |
|---|---|---|---|
| `node_id` | `node.node_id` | direct | ready |
| `node_type` | `node.node_type` | direct | ready |
| `reason_codes` | reinforcement and assessment patterns | derived | partial |
| `priority` | reinforcement pressure + failed assessment heuristics | future | non-final policy only |
| `last_triggered_at` | max of failed assessment / latest practice / last seen | derived | partial |
| `evidence_refs` | none | missing | requires event reference preservation |

Required conclusion:

review_queue_signals are partially derivable but require event reference preservation for production quality.

## 11. Promotion Metadata Mapping

Canonical promotion metadata must remain blocked.

Map:

```json
{
  "promotion_status": "not_promoted",
  "promotion_allowed": false,
  "promotion_task_id": null,
  "promotion_approved_by": null,
  "promotion_approved_at": null,
  "backup_path": null,
  "rollback_plan_id": null,
  "post_promotion_audit_id": null
}
```

Required rule:

S9ZB must not recommend setting `promotion_allowed=true`.

## 12. Audit Metadata Mapping

Canonical audit fields:

- `audit_status`
- `last_audit_id`
- `last_audit_at`
- `qa_status`
- `warnings`
- `failures`
- `readiness_status`

Possible sources:

- S9Z7 QA audit report
- S9Z9 promotion readiness audit report
- S9Z8 readiness JSON
- S9Z6 summary report

Mapping decisions:

- `audit_status` may map from latest S9Z9 audit status
- `readiness_status` maps from S9Z8 readiness JSON status, expected `NOT_READY`
- `warnings` and `failures` map from latest audit summary
- `last_audit_id` and `last_audit_at` need stable audit metadata in future implementation

Suggested mapping:

| Canonical Audit Field | Source | Status | Notes |
|---|---|---|---|
| `audit_status` | S9Z9 audit `status` | direct | ready |
| `last_audit_id` | S9Z9 audit name/version | derived | partial |
| `last_audit_at` | none persisted today | missing | future audit timestamp support needed |
| `qa_status` | S9Z7 report status | direct | ready |
| `warnings` | latest audit summary warnings | derived | ready |
| `failures` | latest audit summary failures | derived | ready |
| `readiness_status` | S9Z8 readiness JSON `status` | direct | ready |

## 13. S10A Read Contract Mapping

Allowed future S10A fields:

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

Mapping status for S10A:

| S10A Read Field | Mapping Status | Notes |
|---|---|---|
| `learner_id` | partial | stable only after single-state identity rules are finalized |
| `schema_version` | future | requires canonical schema implementation |
| `node_mastery.node_id` | ready | available from prototype node records |
| `node_mastery.node_type` | ready | available from prototype node records |
| `node_mastery.level` | missing | requires graph or metadata derivation |
| `node_mastery.band` | ready | available from prototype mastery projection |
| `node_mastery.raw_score` | ready | available but still prototype-scored |
| `node_mastery.decay_adjusted_score` | partial | depends on pending decay policy |
| `node_mastery.confidence` | ready | available |
| `node_mastery.last_seen_at` | ready | available |
| `node_mastery.last_success_at` | partial | incomplete today |
| `node_mastery.signals.needs_reinforcement` | partial | threshold policy not finalized |
| `node_mastery.signals.dependency_blocked` | missing | dependency lock missing |
| `review_queue_signals` | partial | event refs and priority policy incomplete |
| `theme_summary.readiness` | future | requires theme-child coverage derivation |

Required rules:

- S10A must not read prototype output
- S10A must not read raw events directly
- S10A must not mutate learner_state
- S10A must not ignore `promotion_allowed=false`
- S10A remains blocked after S9ZB

## 14. Mapping Gap Register

| Gap | Severity | Blocker Category | Current Mitigation | Future Task Or Phase |
|---|---|---|---|---|
| `event_log_hash_missing` | High | provenance | promotion blocked | future canonical mapping implementation |
| `config_hash_missing` | High | reducer traceability | promotion blocked | future reducer metadata implementation |
| `scoring_policy_version_missing` | High | policy trace | prototype remains non-canonical | future canonical mapping implementation |
| `decay_policy_missing` | High | scoring lifecycle | decay-adjusted score remains provisional | future decay policy design/implementation |
| `dependency_policy_missing` | High | unlock safety | `blocked` band remains unavailable | future dependency lock design/implementation |
| `promotion_policy_missing` | Medium | governance | promotion metadata defaults blocked | future promotion implementation |
| `level_derivation_incomplete` | Medium | downstream contract | S10A remains blocked | future graph-linked mapping work |
| `last_success_at_incomplete` | Medium | node evidence quality | partial mapping only | future reducer event lineage support |
| `event_refs_missing_for_review_queue` | High | review traceability | review signals remain partial | future reducer event reference preservation |
| `theme_child_coverage_missing` | High | theme derivation | theme_summary remains partial | future theme-child mapping source |
| `dependency_blocked_missing` | High | gate safety | downstream integration remains blocked | future dependency policy implementation |
| `stale_mastery_missing` | Medium | recency/decay | promotion blocked | future decay implementation |
| `canonical_schema_not_implemented` | High | contract enforcement | design-only status | future schema implementation task |
| `promotion_still_blocked` | Expected | governance | intentional | future dedicated promotion path only |
| `s10a_still_blocked` | Expected | downstream gate | intentional | future post-promotion integration work only |

## 15. Mapping Readiness Classification

Expected classification:

- `source` = PARTIAL
- `reducer` = PARTIAL / MISSING
- `learner_summary` = PARTIAL
- `node_mastery` = PARTIAL
- `theme_summary` = PARTIAL
- `review_queue_signals` = PARTIAL
- `promotion_metadata` = BLOCKED
- `audit` = PARTIAL
- `s10a_read_contract` = FUTURE / BLOCKED

Applied classification:

| Canonical Section | Classification | Reason |
|---|---|---|
| `source` | PARTIAL | counts exist, hash and input window do not |
| `reducer` | PARTIAL | reducer_version exists, policy/config metadata does not |
| `learner_summary` | PARTIAL | counts and band grouping are derivable, level scope and readiness band are not |
| `node_mastery` | PARTIAL | core mastery fields exist, policy trace and some timestamps do not |
| `theme_summary` | PARTIAL | theme evidence exists, child coverage and readiness derivation do not |
| `review_queue_signals` | PARTIAL | signal derivation is possible, event refs and stable priority are missing |
| `promotion_metadata` | BLOCKED | must remain not-promoted |
| `audit` | PARTIAL | status lineage exists, stable audit timestamp/id persistence does not |
| `s10a_read_contract` | FUTURE / BLOCKED | only a subset is stable and promotion remains blocked |

## 16. Future Implementation Preconditions

Required preconditions before implementing replay-to-canonical mapping:

- canonical learner_state schema implementation
- stable reducer metadata fields
- event log hash support
- config hash support
- scoring policy version
- decay policy version
- dependency policy version
- event reference preservation
- theme-child mapping source
- rollback and backup policy
- promotion approval metadata

## 17. Explicit Non-Goals

S9ZB does not:

- implement mapping
- create canonical learner_state
- implement canonical JSON Schema
- promote prototype output
- implement scoring calibration
- implement decay
- implement dependency lock
- implement rollback
- connect S10A
- connect planner
- modify existing S9Z files

## 18. Acceptance Criteria

S9ZB passes if:

- mapping design scan markdown is created
- prototype-to-canonical field mapping is defined
- top-level mapping matrix exists
- source metadata mapping is defined
- reducer metadata mapping is defined
- learner summary mapping is defined
- node mastery mapping is defined
- theme summary mapping is defined
- review queue signal mapping is defined
- promotion metadata remains blocked
- audit metadata mapping is defined
- S10A read mapping is defined but remains blocked
- mapping gaps are listed
- future implementation preconditions are listed
- no canonical learner_state is modified
- no runtime, graph, ranking, or planner files are modified

## 19. Recommended Next Task

`ULGA-S9ZC_S9Z_Closeout`

S9ZC should close the S9Z line.

Do not recommend implementation.
Do not recommend canonical promotion.
Do not recommend S10A integration.
Do not recommend planner integration.

## Closeout Summary

### Files Created

- `docs/ulga/ULGA_S9ZB_REPLAY_TO_CANONICAL_MAPPING_DESIGN_SCAN.md`
- `ulga/reports/replay_to_canonical_mapping_design_summary.json`

### Files Modified

- None

### Boundary Confirmation

- Canonical learner state was not modified.
- Canonical mastery graph was not modified.
- Runtime code was not modified.
- Candidate ranking files were not modified.
- Planner logic was not modified.
- Replay prototype output was not promoted.
