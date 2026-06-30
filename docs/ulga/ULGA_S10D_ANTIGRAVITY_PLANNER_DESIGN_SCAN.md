# ULGA-S10D Antigravity Planner Design Scan

## 1. Scope

S10D defines the design boundary for the future **Antigravity Planner**.

This scan is design-only. It does not implement planner code, does not create planner JSON artifacts, and does not mutate any graph, learner-state, schema, report, validator, builder, or test file.

The Antigravity Planner sits after the S10B Learning Opportunity Authority and S10C Opportunity Ranking Engine. Its job is to assemble ranked opportunities into learner-safe plans and learning sessions.

S10D scope:

- define why Planner is not another ranking layer
- define planner modes: `global`, `learner`, and `session`
- draft input and output contracts
- define learning-session structure
- define planner policy and selection strategy
- define hard blocks, explainability, QA, and risks
- define integration boundary with future Reading, Dialogue, Assessment, and Worksheet authorities

S10D out of scope:

- implementation under `ulga/builders`, `ulga/validators`, or `ulga/schema`
- writing `antigravity_plan.json`
- modifying `ranked_learning_opportunities.json`
- modifying learner state
- generating reading, dialogue, worksheet, or assessment content
- changing ranking formula, opportunity construction, dependency graph, or theme spiral graph

Minimal-change position:

- reuse `ulga/graph/ranked_learning_opportunities.json` as the ranked candidate input
- treat S10C score order as advisory, not as a final learning plan
- keep Planner as a read-only derived runtime authority
- make learner/session modes fail closed when required learner context is unavailable
- defer all content generation to future content authorities

## 2. Current Inputs Reviewed

Design and closeout documents reviewed:

- `docs/ulga/ULGA_S10A_CANDIDATE_RANKING_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S10B_LEARNING_OPPORTUNITY_AUTHORITY_IMPLEMENTATION.md`
- `docs/ulga/ULGA_S10B1_LEARNING_OPPORTUNITY_THEME_SPECIFICITY_FIX.md`
- `docs/ulga/ULGA_S10C_OPPORTUNITY_RANKING_ENGINE_IMPLEMENTATION.md`

Runtime and authority artifacts reviewed:

- `ulga/graph/learning_opportunities.json`
- `ulga/graph/ranked_learning_opportunities.json`
- `ulga/graph/dependency_graph.json`
- `ulga/graph/theme_spiral_graph.json`
- `ulga/graph/theme_nodes.json`
- `ulga/graph/vocabulary_nodes.json`
- `ulga/graph/sentence_patterns.json`
- `ulga/schema/learning_signal_policy.json`
- `ulga/learner_state/learner_state.json`

Report artifacts reviewed:

- `ulga/reports/learning_opportunity_summary.json`
- `ulga/reports/opportunity_ranking_summary.json`
- `ulga/reports/theme_spiral_graph_summary.json`
- `ulga/reports/learner_state_builder_summary.json`
- `ulga/reports/learner_state_guardrail_summary.json`

Key current facts:

- S10B currently emits 1344 learning opportunities and passes validation.
- S10B1 removed `General` theme fallback from current opportunity output; all 1344 opportunities have specific theme refs.
- Theme source remains concentrated: 1327 opportunities use `vocabulary_theme`; 17 use `pattern_theme_ref`.
- Dependency status is mostly ready: 1337 `ready`, 7 `unknown`.
- S10C ranks all 1344 opportunities and passes validation.
- S10C is currently global ranking; learner-state missing data defaults to `0.5` in the global mastery-gap hook.
- S10C top-10 is split across B1/B2 but is theme-concentrated and has `reinforcement_score: 0.0` in the documented examples.
- Theme Spiral remains non-gating: 12 `SPIRAL_TO` edges, 0 gate-eligible edges, and 8 stage-gap review cases.
- Learner state is small but guarded: 9 records across 2 learners, with guardrails modifying 7 records.
- No reviewed report contains `Missing Optional Inputs`.

## 3. Why Planner Is Not Ranking

The Opportunity Ranking Engine answers:

```text
Which learning opportunities are strongest candidates, in deterministic order?
```

The Antigravity Planner answers:

```text
Which opportunities should be assembled into a learner-safe plan or session now?
```

Planner must not degenerate into:

```text
take top N ranked opportunities
return them as a plan
```

Reasons:

- ranking does not enforce session structure
- ranking does not enforce recent repetition windows
- ranking does not enforce reinforcement quotas
- ranking does not enforce new-content caps
- ranking does not allocate warm-up, core learning, reinforcement, and assessment blocks
- global ranking may ignore learner fatigue, recent themes, learner-specific gaps, and current session context
- top-ranked opportunities can be theme-concentrated even when individually valid

Planner should consume ranking output, but it must apply plan-level constraints and explain both selected and rejected candidates.

## 4. Planner Architecture

Recommended authority position:

```text
Learning Opportunity Authority
+ Opportunity Ranking Engine
+ Learner State Authority
+ Dependency Authority
+ Theme Spiral Authority
+ Reinforcement Policy
+ Antigravity Planner
+ Future Reading / Dialogue / Assessment / Worksheet Authorities
```

Planner responsibilities:

- read ranked opportunities
- read learner context when required by mode
- apply hard blocks before final selection
- enforce level, dependency, repetition, diversity, and reinforcement policy
- allocate selected opportunities into learning-session blocks
- preserve explainability for selected and rejected candidates
- produce a plan artifact suitable for content authorities

Planner non-responsibilities:

- compute global ranking scores from scratch
- define dependency truth
- write or repair learner state
- generate final reading/dialogue/assessment content
- promote Theme Spiral edges into hard gates
- silently repair missing authority refs

## 5. Planner Input Contract

Draft request shape:

```json
{
  "planner_mode": "global | learner | session",
  "learner_context": {
    "learner_id": "James",
    "current_level": "A1",
    "target_level": "A2",
    "recent_theme_refs": [],
    "recent_opportunity_ids": [],
    "mastery_snapshot_ref": "ulga/learner_state/learner_state.json"
  },
  "ranking_input": {
    "ranked_opportunities_ref": "ulga/graph/ranked_learning_opportunities.json",
    "learning_opportunities_ref": "ulga/graph/learning_opportunities.json"
  },
  "policy_input": {
    "planner_policy_ref": "future planner_policy.json"
  }
}
```

Contract rules:

- `planner_mode` is required.
- `ranked_opportunities_ref` is required in all modes.
- `learning_opportunities_ref` is required so the planner can recover themes, levels, focus nodes, dependencies, and policy flags not present in the ranked file.
- `learner_context` is optional only in `global` mode.
- `learner_context.mastery_snapshot_ref` is required in `learner` and `session` modes.
- `recent_theme_refs` and `recent_opportunity_ids` are required in `session` mode, even if empty arrays.
- Missing, unreadable, or schema-invalid required refs must produce `S10D_STATUS: BLOCKED` for that run, not a silent fallback.

## 6. Planner Modes

### Global Mode

Purpose:

- produce general recommended opportunities without learner-specific state
- support dashboard previews, curriculum exploration, and smoke tests

Allowed inputs:

- ranked opportunities
- learning opportunities
- dependency and theme metadata
- global planner policy

Global mode rules:

- may use S10C ordering as the main candidate order
- must still apply diversity and session allocation if it emits sessions
- must label learner-state usage as `not_used`
- must not claim personalization

Output:

```text
general recommended opportunities
```

### Learner Mode

Purpose:

- produce a learner-specific plan using guarded learner state and learner target level

Required inputs:

- learner id
- current and target level
- guarded learner-state snapshot
- ranked opportunities
- learning opportunities

Learner mode rules:

- must use guarded learner-state values only
- must not use raw pre-guardrail mastery
- must hard block if learner state is unavailable or no records exist for the requested learner
- must explain mastery-gap and reinforcement decisions when learner-state evidence exists
- must not mutate learner state

Output:

```text
learner-specific opportunity plan
```

### Session Mode

Purpose:

- produce 10-20 minute learning sessions with block allocation, fatigue guardrails, repetition avoidance, and assessment hooks

Required additional inputs:

- recent 7-day and/or 30-day opportunity history
- recent theme history
- reinforcement history when available
- assessment result refs when available

Session mode rules:

- must enforce recent repetition guard
- must cap same-theme concentration
- must reserve space for reinforcement
- must limit new content
- must allocate selected opportunities into session blocks
- must return an empty or partial session with reasons rather than fill gaps with unsafe candidates

Output:

```text
learning sessions ready for future content authorities
```

## 7. Learning Session Model

A `Learning Session` is not a flat list of opportunities. It is a bounded plan segment with instructional roles.

Recommended block order:

1. `warm_up`
2. `core_learning`
3. `reinforcement`
4. `assessment`
5. `optional_extension`

Draft session shape:

```json
{
  "session_id": "SESSION_A1_HOME_0001",
  "learner_id": "James",
  "target_level": "A1",
  "session_blocks": [
    {
      "block_type": "warm_up",
      "opportunity_ids": []
    },
    {
      "block_type": "core_learning",
      "opportunity_ids": []
    },
    {
      "block_type": "reinforcement",
      "opportunity_ids": []
    },
    {
      "block_type": "assessment",
      "opportunity_ids": []
    }
  ]
}
```

Block semantics:

- `warm_up`: familiar or low-risk opportunities, ideally connected to recent themes or known nodes
- `core_learning`: limited new content selected after dependency and level gates
- `reinforcement`: due or weak related nodes, not filler
- `assessment`: checkable opportunity or assessment authority hook
- `optional_extension`: only when core and reinforcement quotas are already satisfied

## 8. Planner Policy Draft

Future `planner_policy.json` draft:

```json
{
  "daily_target_opportunity_count": 3,
  "max_new_content_ratio": 0.3,
  "min_reinforcement_ratio": 0.5,
  "max_same_theme_ratio": 0.7,
  "max_level_jump": 1,
  "allow_unknown_dependency": false,
  "prefer_theme_continuity": true,
  "prefer_spiral_progression": true,
  "avoid_recent_repetition_days": 7
}
```

Policy notes:

- `daily_target_opportunity_count` controls plan size, not ranking input size.
- `max_new_content_ratio` prevents a session from becoming all new material.
- `min_reinforcement_ratio` compensates for current S10C outputs where reinforcement evidence can be sparse or zero.
- `max_same_theme_ratio` prevents top-ranked theme clusters from dominating a session.
- `max_level_jump` should compare learner current level to opportunity level.
- `allow_unknown_dependency: false` is the safe V1 default because 7 current opportunities have `dependency.status = unknown`.
- `avoid_recent_repetition_days` is mandatory in session mode.

## 9. Selection Strategy

Planner selection should run after ranked opportunities are loaded and joined to full opportunity metadata.

Recommended order:

1. input validation
2. ranked-opportunity to opportunity-metadata join
3. hard block checks
4. dependency gate
5. level gate
6. learner-state gate when mode requires it
7. recent repetition guard
8. new-content and reinforcement quota balancing
9. theme continuity and theme diversity balancing
10. session block allocation
11. deterministic tie-break
12. explanation and rejected-candidate reporting

Selection principles:

- Ranking order is a preference source, not the final selection algorithm.
- Hard blocks always beat score.
- Learner/session policy can skip a high-ranked opportunity for a lower-ranked but better-balanced one.
- Empty eligible pools are valid and must be reported.
- Selection must be deterministic for identical inputs.

Suggested deterministic tie-break after policy filters:

1. lower hard-block count
2. higher S10C `candidate_score`
3. higher dependency readiness
4. stronger learner-state relevance when mode is learner/session
5. lower level jump
6. lower recent repetition count
7. stable `opportunity_id`

## 10. Hard Block Policy

Planner hard blocks:

- `missing_prerequisite`
- `blocked_dependency`
- `level_jump_too_large`
- `unsafe_opportunity`
- `missing_required_authority_refs`
- `already_mastered_and_no_reinforcement_need`
- `recently_repeated`
- `learner_state_unavailable_in_learner_mode`
- `learner_state_unavailable_in_session_mode`
- `unknown_dependency_when_policy_disallows`
- `unsupported_planner_mode`
- `ranked_opportunity_missing_metadata`

Current-input implications:

- The 7 opportunities with `dependency.status = unknown` should be blocked when `allow_unknown_dependency` is false.
- Learner-specific output cannot rely on S10C's global `mastery_gap_score = 0.5` fallback.
- Current top-ranked examples have `reinforcement_score = 0.0`; session mode must not treat them as reinforcement blocks unless future evidence supports that role.

Theme Spiral hard-block rule:

- Theme Spiral is non-gating and must not hard block by itself.
- Stage-gap warnings may cap preference but cannot independently reject an opportunity.

## 11. Output Contract Draft

Future `antigravity_plan.json` draft:

```json
{
  "plan_id": "PLAN_000001",
  "planner_mode": "learner",
  "learner_id": "James",
  "generated_from": {
    "ranked_opportunities": "ulga/graph/ranked_learning_opportunities.json",
    "learning_opportunities": "ulga/graph/learning_opportunities.json",
    "learner_state": "ulga/learner_state/learner_state.json"
  },
  "recommended_sessions": [],
  "rejected_candidates": [],
  "plan_summary": {
    "total_opportunities": 0,
    "new_content_ratio": 0.0,
    "reinforcement_ratio": 0.0,
    "theme_distribution": {},
    "level_distribution": {}
  },
  "explanations": []
}
```

Recommended `rejected_candidates` item shape:

```json
{
  "opportunity_id": "LO_B1_000184",
  "rank": 1,
  "candidate_score": 0.657846,
  "rejection_reasons": [
    "same_theme_ratio_exceeded"
  ],
  "hard_block": false,
  "authority_refs": {
    "ranking": "ulga/graph/ranked_learning_opportunities.json",
    "opportunity": "ulga/graph/learning_opportunities.json"
  }
}
```

Recommended selected opportunity item shape:

```json
{
  "opportunity_id": "LO_A1_000001",
  "assigned_block": "core_learning",
  "selection_reasons": [
    "dependency_ready",
    "level_within_policy",
    "theme_continuity"
  ],
  "source_rank": 42,
  "source_candidate_score": 0.61
}
```

## 12. Explainability Strategy

Planner explainability must cover both:

- why an opportunity was selected
- why a higher-ranked opportunity was skipped or blocked

Recommended reason codes:

- `dependency_ready`
- `mastery_gap`
- `theme_continuity`
- `theme_spiral_progression`
- `reinforcement_needed`
- `high_frequency`
- `pattern_high_utility`
- `recent_repetition_blocked`
- `level_jump_blocked`
- `dependency_blocked`
- `unknown_dependency_blocked`
- `same_theme_ratio_exceeded`
- `new_content_ratio_exceeded`
- `reinforcement_quota_required`
- `learner_state_required_missing`
- `metadata_join_failed`
- `session_block_capacity_reached`

Explainability rules:

- every selected opportunity needs at least one positive reason
- every rejected candidate needs at least one rejection reason
- hard blocks must be distinguishable from soft policy skips
- reason codes should map back to authority refs or policy fields
- explanations should be stable under repeated execution

## 13. Reading / Dialogue / Assessment Integration

S10D should prepare for, but not implement, future authorities:

- `S11 Reading Authority`
- `S12 Dialogue Authority`
- `S13 Assessment Authority`
- `S14 Worksheet Authority`

Boundary:

- Planner emits a Learning Session / Opportunity Plan.
- Reading Authority turns selected opportunities into reading material.
- Dialogue Authority turns selected opportunities into dialogue practice.
- Assessment Authority produces checks and writes future evidence events.
- Learner State Authority consumes future evidence events and updates learner state.

Planner must not:

- generate final reading passages
- generate dialogue scripts
- generate answer keys
- write assessment results
- write learner-state updates

Recommended integration fields for future use:

- `assigned_block`
- `target_level`
- `theme_refs`
- `focus_nodes`
- `selection_reasons`
- `assessment_hint`
- `content_authority_hint`

## 14. QA / Audit Plan

Required planner audit metrics:

- `plan_count`
- `session_count`
- `selected_opportunity_count`
- `rejected_candidate_count`
- `dependency_block_count`
- `level_jump_block_count`
- `recent_repetition_block_count`
- `unknown_dependency_block_count`
- `theme_distribution`
- `level_distribution`
- `new_content_ratio`
- `reinforcement_ratio`
- `same_theme_max_ratio`
- `explainability_coverage`
- `learner_state_usage_coverage`
- `determinism_check`

Additional recommended audits:

- empty ranked input returns controlled empty plan
- malformed ranked input returns blocked status
- missing opportunity metadata reports join failure
- learner mode without matching learner records blocks
- session mode with recent repeated opportunities blocks or skips repeats
- repeated execution with identical inputs produces byte-stable selected IDs and reason codes
- process restart does not alter ordering or block decisions
- unknown dependency is blocked when policy disallows it

QA status rules:

- `PASS`: all required inputs valid, plan satisfies policy, explainability coverage is complete
- `PASS_WITH_WARNINGS`: plan is valid but constrained by sparse learner state, sparse reinforcement evidence, or partial optional inputs
- `BLOCKED`: required authority refs missing/invalid, learner state unavailable in learner/session mode, or no safe plan can be produced under hard policy

## 15. Risks and Mitigations

### Planner degenerates into Top-N wrapper

Risk:

- session output mirrors S10C rank order without policy-level balancing

Mitigation:

- require block allocation, quotas, diversity caps, and rejected-candidate explanations

### Planner ignores learner state

Risk:

- learner/session mode becomes a mislabeled global plan

Mitigation:

- hard block missing learner-state refs and measure `learner_state_usage_coverage`

### Planner overuses one theme

Risk:

- current ranking can surface theme-concentrated top results

Mitigation:

- enforce `max_same_theme_ratio` and report theme distribution

### Planner underuses reinforcement

Risk:

- current examples show top-ranked opportunities with `reinforcement_score = 0.0`

Mitigation:

- enforce `min_reinforcement_ratio`; if reinforcement evidence is unavailable, emit warning or partial plan rather than mislabel new content as reinforcement

### Planner recommends isolated opportunities

Risk:

- a selected opportunity may be valid but hard to teach or assess

Mitigation:

- prefer opportunities with pattern/theme/focus-node support and pass content-authority hints forward

### Planner cannot explain rejection

Risk:

- dashboard, QA, and future orchestration cannot tell why higher-ranked candidates were skipped

Mitigation:

- require `rejected_candidates` with hard/soft reason codes

### Planner depends on future content authorities too early

Risk:

- S10D/S10E becomes blocked waiting for Reading/Dialogue/Assessment implementations

Mitigation:

- emit content-authority hints only; defer material generation

### Planner mutates learner state

Risk:

- duplicate execution or process restart corrupts learner progress

Mitigation:

- keep Planner read-only; future assessment evidence should flow through Learner State Authority

### Planner overfits global ranking

Risk:

- high S10C scores dominate even when learner/session policy says to skip them

Mitigation:

- treat rank as an input preference after hard blocks, not as final plan truth

### Real environment risks

`API failure / timeout`

- Planner may depend on future service calls for learner history or content-authority previews.
- Mitigation: V1 should use local artifacts only; future service calls must have timeout, retry, and fail-closed behavior.

`empty data`

- Ranked input or eligible pool may be empty.
- Mitigation: return empty plan with `BLOCKED` or `PASS_WITH_WARNINGS`, depending on mode and policy.

`duplicate execution`

- Running the planner twice must not duplicate learner records or change output order.
- Mitigation: no learner-state writes; deterministic tie-breaks.

`process restart`

- Restarted runtime must reproduce the same plan from the same inputs.
- Mitigation: no hidden in-memory counters; stable IDs derived from request/run id plus deterministic sequence.

`abnormal authority response`

- Missing opportunity metadata, null levels, malformed theme refs, or invalid learner records can corrupt planning.
- Mitigation: schema validation, metadata join checks, and explicit hard blocks.

## 16. Recommended Next Tasks

1. `ULGA-S10E_AntigravityPlanner_Implementation`

   Minimal first pass:

   - implement global mode only
   - read `ranked_learning_opportunities.json` and `learning_opportunities.json`
   - join ranked records to opportunity metadata
   - apply dependency unknown block when policy disallows it
   - enforce simple theme diversity and level distribution metrics
   - emit selected and rejected candidates with reason codes
   - add deterministic tests

2. `ULGA-S10F_AntigravityPlanner_QA_Audit`

   Validate hard blocks, empty input handling, metadata join failures, deterministic repeat-run behavior, explainability coverage, and plan-summary metrics.

3. Later learner/session expansion:

   Add learner and session modes only after planner V1 can safely produce global plans and after learner-state/history contracts are explicit enough to avoid silent fallback.

Alternative next track:

- `S11A_ReadingAuthority_DesignScan`

Use this if the priority is to define content-authority boundaries before implementing Planner.

## 17. Final Verdict

S10D is ready to proceed to implementation with a conservative boundary.

Reasons:

- S10B and S10C provide stable opportunity and ranking inputs.
- Current reports show no missing optional inputs in the reviewed S10B/S10C artifacts.
- Dependency and theme authorities have clear gating boundaries.
- Learner state exists and is guarded, but is still small enough that learner/session modes should fail closed rather than degrade silently.
- Planner can be implemented as a read-only derived authority without graph mutation.

Controlled warnings:

- S10C is global ranking, so S10D/S10E must not claim learner personalization until learner mode is explicitly implemented.
- Theme assignments are specific but mostly sourced from vocabulary theme authority, so session diversity remains necessary.
- Reinforcement evidence is currently sparse in top-ranked examples, so Planner must not fake reinforcement coverage.
- Theme Spiral remains non-gating and should only influence preference.

```text
S10D_STATUS: DESIGN_READY
```
