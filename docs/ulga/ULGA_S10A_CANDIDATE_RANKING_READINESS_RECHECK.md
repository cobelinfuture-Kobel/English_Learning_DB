# ULGA-S10A Candidate Ranking Readiness Recheck

## 1. Scope

S10A readiness recheck does not implement candidate ranking.
S10A readiness recheck does not connect to learner_state.
S10A readiness recheck does not connect to planner.
S10A readiness recheck decides the safe next path.

This is a read-only readiness recheck after S9Z closeout.

## 2. Current S10A Position

S10A sits in the authority stack as:

```text
Authority Layer
-> ULGA Graph / Dependency / Spiral / Reinforcement Inputs
-> Candidate Ranking
-> Planner / Content Selection
```

But production adaptive candidate ranking is blocked until the canonical learner_state read contract is ready.

Therefore S10A may only proceed in restricted modes:

- `static_candidate_readiness_mode`
- `offline_candidate_query_mode`
- `content_authority_preparation_mode`
- `design_only_mode`

Important recheck decision:

The older `ULGA-S10A_CANDIDATE_RANKING_DESIGN_SCAN` concluded that S10A was ready to proceed with guarded learner-state inputs. That conclusion is no longer sufficient after S9ZC, because S9ZC explicitly preserves:

- `promotion_allowed = false`
- `s10a_integration_allowed = false`
- `planner_integration_allowed = false`

So S10A must now be split into:

- static / offline candidate readiness
- future adaptive learner-specific ranking

Only the first path is eligible now.

## 3. Inputs to Inspect

### Static Authority Inputs

| Input Group | Status | Evidence | Notes |
|---|---|---|---|
| vocabulary authority | `AVAILABLE` | `ulga/reports/vocabulary_authority_qa_audit.json` | 15,696 mounted vocabulary nodes; frequency fields populated |
| grammar authority | `AVAILABLE` | mounted through existing grammar/design line and dependency inputs | grammar is usable as authority input, though not all opportunities carry grammar refs |
| chunk authority | `AVAILABLE` | existing S6 authority/design artifacts | available as mounted authority layer |
| pattern authority | `AVAILABLE` | `ulga/graph/pattern_vocabulary_candidate_query_contract.json`, `ulga/reports/pattern_vocabulary_constraint_summary.json` | 1,344 active candidate constraints |
| theme authority | `PARTIAL` | `ulga/reports/vocabulary_authority_qa_audit.json`, `ulga/reports/learning_opportunity_summary.json` | static theme refs exist for opportunities, but vocabulary theme coverage is mostly derived later |
| frequency authority | `PARTIAL` | `ulga/reports/vocabulary_authority_qa_audit.json` | frequency fields are populated, but no separate frequency authority contract exists |
| dependency authority | `AVAILABLE` | `ulga/reports/dependency_graph_summary.json` | 84 accepted hard prerequisite edges, all gate-eligible |
| spiral authority | `AVAILABLE` | `ulga/reports/theme_spiral_graph_summary.json` | 12 accepted `SPIRAL_TO` edges, explicitly non-gating |
| reinforcement authority | `PARTIAL` | `ulga/reports/reinforcement_signal_summary.json` | authority exists, but current signals are sparse and planner-ineligible |

### Candidate / Query Inputs

| Input Group | Status | Evidence | Notes |
|---|---|---|---|
| pattern_vocabulary_candidate_query_contract | `AVAILABLE` | `ulga/graph/pattern_vocabulary_candidate_query_contract.json`, `ulga/reports/pattern_vocabulary_constraint_summary.json` | stable query seed for static ranking inputs |
| pattern_vocabulary_constraints | `AVAILABLE` | `ulga/graph/pattern_vocabulary_constraints.json`, `ulga/reports/pattern_vocabulary_constraint_summary.json` | 1,932 slot constraints |
| reinforcement_candidate_expansion | `PARTIAL` | existing S10I/S10J artifacts in repo | not required for static readiness recheck, but available as later enrichment |
| exposure_mapping_bridge | `AVAILABLE` | `ulga/reports/exposure_mapping_bridge_summary.json` | bridge exists, but only 3 mappings |
| learner_exposure_evidence | `PARTIAL` | `ulga/reports/learner_exposure_evidence_summary.json` | evidence exists but coverage is only 0.2232% |
| theme_spiral_graph | `AVAILABLE` | `ulga/reports/theme_spiral_graph_summary.json` | safe continuity input only |
| theme_vocab_mapping | `PARTIAL` | `ulga/reports/learning_opportunity_summary.json` | usable through opportunity artifacts, but mostly vocabulary-derived |

### Learner-State Inputs

| Input Group | Status | Evidence | Notes |
|---|---|---|---|
| canonical learner_state | `BLOCKED` | S9ZC closeout, S9ZA summary, S9Z8 readiness JSON | not promoted for S10A use |
| mastery_graph | `BLOCKED` | S9ZC closeout boundary | not available for production adaptive ranking |
| S9Z6 prototype learner_state projection | `BLOCKED` | S9ZC closeout, S9ZB design summary | exists physically, forbidden for S10A consumption |
| S9ZA canonical learner_state contract | `AVAILABLE` | `ulga/reports/learner_state_canonical_schema_design_summary.json` | design-only, not implemented |
| S9ZB replay-to-canonical mapping design | `AVAILABLE` | `ulga/reports/replay_to_canonical_mapping_design_summary.json` | mapping design exists, still blocked |
| S9ZC closeout summary | `AVAILABLE` | `ulga/reports/s9z_closeout_summary.json` | authoritative boundary source |

### Content-System Inputs

| Input Group | Status | Evidence | Notes |
|---|---|---|---|
| Reading Authority readiness | `AVAILABLE` | `docs/ulga/ULGA_S11A_READING_AUTHORITY_DESIGN_SCAN.md`, `ulga/reports/reading_stub_summary.json` | design plus stub authority surface exists |
| Writing Authority readiness | `MISSING` | no matching docs found in `docs/ulga` | can start in parallel |
| Speaking Authority readiness | `MISSING` | no matching docs found in `docs/ulga` | can start in parallel |
| Dialogue Authority readiness | `MISSING` | no matching docs found in `docs/ulga` | can start in parallel |
| Assessment Authority readiness | `MISSING` | no matching docs found in `docs/ulga` | can start in parallel |
| Worksheet Authority readiness | `MISSING` | no matching docs found in `docs/ulga` | not required now |

## 4. Hard Gating Rules

S10A must be blocked from production integration if any of these are true:

- canonical learner_state is missing or not promoted
- `promotion_allowed = false`
- `s10a_integration_allowed = false`
- `planner_integration_allowed = false`
- S10A would need to read prototype learner_state
- S10A would need to read raw event logs directly
- S10A would need to mutate learner_state
- S10A would need production decay / dependency scoring

These gates are all currently true enough to block adaptive production S10A.

However, S10A may proceed in restricted mode if:

- it uses static graph / authority inputs only
- it produces no planner-consumed output
- it does not claim learner-specific adaptation
- it labels output as static / offline / query-readiness only
- it records learner_state blockers as future work

## 5. Static Candidate Ranking Readiness

Static S10A means ranking candidate targets using only:

- CEFR level
- theme
- grammar
- vocabulary
- pattern
- chunk
- dependency status already available in static artifacts
- spiral / reinforcement inputs only as static signals
- content availability and query constraints

Current evidence supports static readiness:

- `ulga/reports/learning_opportunity_summary.json` reports 1,344 opportunities and `requires_learner_state = 0`
- `ulga/reports/opportunity_ranking_summary.json` reports 1,344 ranked opportunities with no warnings
- `ulga/reports/dependency_graph_summary.json` provides 84 accepted hard prerequisite edges
- `ulga/reports/theme_spiral_graph_summary.json` provides non-gating continuity context
- `ulga/reports/pattern_vocabulary_constraint_summary.json` provides active constraint and query-limit behavior

Allowed static outputs:

- static candidate readiness report
- candidate query design
- candidate ranking feature matrix
- candidate input availability matrix
- candidate ranking non-learner mode design

Forbidden outputs:

- personalized learner ranking
- planner schedule
- adaptive lesson sequence
- canonical candidate ranking graph
- production candidate API

Conclusion:

Static S10A can proceed, but only as offline / non-learner-specific candidate readiness and ranking design work.

## 6. Learner-State Dependent Readiness

| Learner-State Item | Current Status | Blocks Production S10A | Blocks Static S10A | Blocks Planner Integration | Can Be Deferred |
|---|---|---|---|---|---|
| canonical learner_state implementation | missing | Yes | No | Yes | No |
| event_log_hash | missing | Yes | No | Partial | Yes |
| config_hash | missing | Yes | No | Partial | Yes |
| scoring_policy_version | missing/prototype-only | Yes | No | Yes | Partial |
| decay_policy_version | missing | Yes | No | Partial | Yes |
| dependency_policy_version | missing | Yes | No | Yes | Partial |
| level_derivation | incomplete | Yes | Partial | Yes | Partial |
| event_refs_for_review_queue | missing | Partial | No | Partial | Yes |
| theme_child_coverage | incomplete | Partial | No | Partial | Yes |
| promotion workflow | missing | Yes | No | Yes | No |
| S10A read contract implementation | missing | Yes | No | Yes | No |

Expected result is confirmed:

- most learner_state blockers do not block static S10A readiness
- most learner_state blockers do block production adaptive S10A

Important safety note:

`level_derivation` is the one blocker that can partially affect static ranking quality, because some future candidate-level reasoning may want stronger CEFR normalization. It does not justify waiting for full learner_state productionization now.

## 7. Content-System Dependency Check

S10A can rank targets, but content systems decide how to teach them.

| Content System | Classification | Evidence | Notes |
|---|---|---|---|
| Reading Authority | `can_start_in_parallel` | S11A design scan, `ulga/reports/reading_stub_summary.json` | strongest current content authority path |
| Writing Practice Authority | `can_start_in_parallel` | missing design artifacts | static S10A should not wait |
| Speaking Practice Authority | `can_start_in_parallel` | missing design artifacts | static S10A should not wait |
| Dialogue Authority | `can_start_in_parallel` | missing design artifacts | optional later consumer path |
| Assessment Authority | `needed_for_adaptive_ranking` | missing design artifacts | needed later for learner evidence loops |
| Worksheet Authority | `needed_for_product_output` | missing design artifacts | not required for static ranking readiness |

Important decision:

If S10A can rank targets but there are no content artifacts to attach, Reading / Writing / Speaking / Assessment may need to begin before full S10A implementation.

Current repository state supports that conclusion:

- Reading has already reached design plus stub-authority readiness.
- Writing, Speaking, Dialogue, Assessment, and Worksheet remain absent as explicit authority lines.
- Therefore content authority work should start in parallel, not as a hard blocker against static S10A.

## 8. Recommended Mode Decision

Final mode:

`MODE_3_PARALLEL_STATIC_S10A_AND_CONTENT_AUTHORITY`

Reason:

S9Z learner_state integration remains blocked, but static candidate readiness and content-system planning can proceed without production learner_state.

Why not the other modes:

- not `MODE_1_STATIC_S10A_CAN_PROCEED` because content authority coverage is still uneven and would leave ranking with weak delivery attachment
- not `MODE_2_CONTENT_AUTHORITY_FIRST` because static candidate inputs are already strong enough to justify parallel ranking-readiness work
- not `MODE_4_WAIT_FOR_LEARNER_STATE_PRODUCTIONIZATION` because most learner_state blockers do not block static/offline S10A

## 9. Allowed Next Tasks

Safe next tasks under the selected mode:

- `ULGA-S10B_StaticCandidateRanking_DesignScan`
- `ULGA-AssessmentAuthority_S1_DesignScan`
- `ULGA-WritingPracticeAuthority_S1_DesignScan`
- `ULGA-SpeakingPracticeAuthority_S1_DesignScan`

Why these are safe:

- they do not require learner_state promotion
- they do not require planner integration
- they do not require prototype learner_state consumption
- they preserve static/offline boundaries

Do not recommend:

- S10A production integration
- S10A learner_state integration
- planner integration
- canonical promotion
- production decay implementation
- production scoring calibration

## 10. Readiness Matrix

| Area | Status | Evidence | Blocks Static S10A? | Blocks Adaptive S10A? | Recommendation |
|---|---|---|---|---|---|
| Static Authority Inputs | `AVAILABLE` | vocabulary, dependency, theme spiral, pattern/query artifacts present | No | No | use now in static mode |
| Candidate Query Contract | `AVAILABLE` | pattern-vocabulary query contract and constraint summary | No | No | reuse as seed contract |
| Dependency / Prerequisite Inputs | `AVAILABLE` | dependency graph summary with 84 accepted edges | No | No | hard-block and eligibility input |
| Theme / Spiral Inputs | `PARTIAL` | spiral summary available, theme sourcing still uneven | No | No | use only as non-gating continuity |
| Reinforcement Inputs | `PARTIAL` | reinforcement summary has 0 planner-eligible items | No | Partial | keep signal low-weight and non-authoritative |
| Canonical Learner State | `BLOCKED` | S9ZC / S9ZA / S9Z8 boundaries | No | Yes | keep blocked |
| S9Z Prototype Learner State | `BLOCKED` | exists but forbidden for S10A use | No | Yes | do not consume |
| S10A Read Contract | `BLOCKED` | design gap remains open in S9ZA/S9ZB | No | Yes | defer until learner_state productionization |
| Planner Integration | `BLOCKED` | S9ZC says planner integration not allowed | No | Yes | keep blocked |
| Reading Authority | `AVAILABLE` | S11A design + S11B stub summary | No | No | continue in parallel |
| Writing Practice Authority | `MISSING` | no explicit artifacts found | No | Partial | start design in parallel |
| Speaking Practice Authority | `MISSING` | no explicit artifacts found | No | Partial | start design in parallel |
| Assessment Authority | `MISSING` | no explicit artifacts found | No | Yes | start design in parallel |

## 11. Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| static ranking may not reflect individual learner needs | ranking may look globally reasonable but personally wrong | label mode as static/offline only |
| lack of canonical learner_state prevents true personalization | adaptive mastery-gap ranking cannot be trusted | do not consume prototype learner_state |
| lack of content authority means ranking has no teachable output | ranked targets may not map to usable learning content | start content authority design in parallel |
| dependency data may be incomplete | some opportunities may look ready when they are only partially grounded | keep hard dependency gating and expose `unknown` states |
| theme-child coverage remains partial | theme continuity may overstate readiness | record learner_state blockers for later incremental work |
| review queue signals lack event refs | reinforcement evidence is weak for future adaptive use | keep static mode non-learner-specific and defer evidence-backed reinforcement |
| prototype score must not leak into ranking | false personalization and unstable adaptive behavior | keep learner_state integration blocked |
| planner integration remains premature | ranked output could be mistaken for session planning | keep planner blocked |

## 12. Acceptance Criteria

This task passes because:

- readiness markdown is created
- optional summary JSON is created
- no runtime / graph / learner_state / ranking / planner files are modified
- S10A production integration remains blocked
- planner integration remains blocked
- prototype learner_state remains unused
- readiness mode is explicitly chosen
- safe next task options are listed
- S9Z deferred blockers are preserved
- content-system parallel path is evaluated

## 13. Optional JSON Summary Contract

Optional metadata summary may exist at:

`ulga/reports/s10a_candidate_ranking_readiness_recheck.json`

It is summary metadata only.
It must not be consumed by runtime code.
It must not be treated as a ranking output.

## 14. Closeout Required

### Files Created

- `docs/ulga/ULGA_S10A_CANDIDATE_RANKING_READINESS_RECHECK.md`
- `ulga/reports/s10a_candidate_ranking_readiness_recheck.json`

### Files Modified

- None

### Final Readiness Mode

- `MODE_3_PARALLEL_STATIC_S10A_AND_CONTENT_AUTHORITY`

### Static S10A Decision

- `ALLOWED` in static / offline / non-learner-specific mode only

### Adaptive S10A Decision

- `NOT ALLOWED`

### Planner Decision

- `NOT ALLOWED`

### Learner-State Decision

- `integration not allowed`
- canonical learner_state remains blocked
- prototype learner_state remains forbidden

### Recommended Next Task

- primary: `ULGA-S10B_StaticCandidateRanking_DesignScan`
- parallel content option: `ULGA-AssessmentAuthority_S1_DesignScan`

## Closeout Summary

### Boundary Confirmation

- No graph JSON files were modified.
- No learner_state files were modified.
- No mastery graph files were modified.
- No event log files were modified.
- No runtime code was modified.
- No S9Z files were modified.
- No S10A ranking code was modified.
- No planner logic was modified.
- No validators, builders, schemas, or tests were modified.

### Final Statement

Production adaptive S10A remains blocked after this recheck.
Static/offline S10A may proceed.
Content authority work should proceed in parallel.
This makes `MODE_3_PARALLEL_STATIC_S10A_AND_CONTENT_AUTHORITY` the safest next path.
