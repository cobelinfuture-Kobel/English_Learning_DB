# ULGA-S10F Reinforcement Signal Design Scan

## 1. Scope

S10F defines the design boundary for a future **Reinforcement Signal Authority**.

This scan is design-only. It does not implement builders, validators, schemas, graph outputs, reports, learner-state changes, ranking changes, or planner changes.

S10F scope:

- explain the S10E planner warning:
  - `no eligible opportunity with reinforcement_score > 0`
- define what counts as reinforcement
- distinguish review, reinforcement, and remediation
- define reinforcement targets, signal sources, scoring, state transitions, QA, and risks
- propose a roadmap for `S10G_ReinforcementSignal_Implementation`

S10F out of scope:

- writing `reinforcement_signal.json`
- modifying `learning_opportunities.json`
- modifying `ranked_learning_opportunities.json`
- modifying `antigravity_plan.json`
- modifying learner state
- changing S10C ranking formula
- changing S10E planner behavior

Minimal-change position:

- keep Reinforcement Signal Authority as a derived runtime authority
- do not back-write reinforcement truth into Opportunity, Ranking, Planner, Dependency, Theme Spiral, or Learner State
- let Ranking and Planner consume reinforcement signals only after hard gates are applied

## 2. Inputs Reviewed

Design and closeout documents reviewed:

- `docs/ulga/ULGA_S9A_LEARNER_STATE_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S9F_LEARNER_STATE_BUILDER_QA_AUDIT.md`
- `docs/ulga/ULGA_S9G_LEARNER_STATE_BUILDER_GUARDRAIL_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S9I_LEARNER_STATE_GUARDRAIL_QA_AUDIT.md`
- `docs/ulga/ULGA_S9J_LEARNER_STATE_STABILITY_AUDIT.md`
- `docs/ulga/ULGA_S9L_POST_TIGHTENING_READINESS_AUDIT.md`
- `docs/ulga/ULGA_S10A_CANDIDATE_RANKING_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S10B_LEARNING_OPPORTUNITY_AUTHORITY_IMPLEMENTATION.md`
- `docs/ulga/ULGA_S10C_OPPORTUNITY_RANKING_ENGINE_IMPLEMENTATION.md`
- `docs/ulga/ULGA_S10D_ANTIGRAVITY_PLANNER_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S10E_ANTIGRAVITY_PLANNER_IMPLEMENTATION.md`

Runtime and report artifacts reviewed:

- `ulga/graph/learning_opportunities.json`
- `ulga/graph/ranked_learning_opportunities.json`
- `ulga/graph/antigravity_plan.json`
- `ulga/learner_state/learner_state.json`
- `ulga/schema/learning_signal_policy.json`
- `ulga/graph/dependency_graph.json`
- `ulga/graph/theme_spiral_graph.json`
- `ulga/reports/learning_opportunity_summary.json`
- `ulga/reports/opportunity_ranking_summary.json`
- `ulga/reports/antigravity_plan_summary.json`
- `ulga/reports/dependency_graph_summary.json`
- `ulga/reports/theme_spiral_graph_summary.json`

Key current facts:

- S10E status is `PASS_WITH_WARNINGS`.
- S10E warning is `no eligible opportunity with reinforcement_score > 0; reinforcement block is structural only`.
- S10B emits 1344 learning opportunities.
- S10B summary shows 1337 `ready` opportunities and 7 `unknown` dependency opportunities.
- S10C emits 1344 ranked opportunities.
- S10C ranking has 7 opportunities with `reinforcement_score > 0`.
- All 7 positive-reinforcement opportunities have `dependency.status = unknown`.
- S10E blocks unknown dependency, so eligible reinforcement opportunity count is 0.
- Learner state has weak/due records that could become reinforcement sources later, but S10C V1 does not materialize learner-specific reinforcement signals.

## 3. Reinforcement Definition

S10F must separate three related but different concepts.

### Review

Review means:

```text
Bring previously seen material back into attention.
```

Typical trigger:

- `review_due_at` exists
- material has not been seen recently
- `mastery_band` is `seen` or `practicing`

Review does not require a new target. It can be a short revisit.

### Reinforcement

Reinforcement means:

```text
Strengthen a weak, unstable, recently seen, or dependency-relevant node while teaching or practicing a related opportunity.
```

Typical trigger:

- opportunity shares focus refs with weak learner-state records
- opportunity uses a prerequisite that is weak or due
- opportunity revisits same theme/pattern/vocabulary in a productive context
- opportunity repairs fragile readiness without introducing a hard block

Reinforcement is not simply "any repeated item." It must have an explainable target.

### Remediation

Remediation means:

```text
Repair a known gap or failure.
```

Typical trigger:

- incorrect evidence
- diagnostic signal
- failed assessment
- unmet prerequisite
- repeated confusion pair

Remediation can overlap with reinforcement, but it is more targeted and should normally outrank ordinary review when a learner-specific plan is requested.

Design rule:

```text
Review != Reinforcement != Remediation
```

The planner should not treat one concept as the other.

## 4. Reinforcement Targets

Valid reinforcement targets:

- `Vocabulary`
- `Grammar`
- `Pattern`
- `Chunk`
- `Theme`
- `Opportunity`

### Vocabulary

Use when:

- learner has seen a word but has weak mastery
- word is a prerequisite/focus node in an opportunity
- vocabulary overlaps across reading/dialogue/assessment content

Avoid when:

- vocabulary has no stable authority ref
- word is only a theme hint and not actually practiced

### Grammar

Use when:

- grammar is a prerequisite for current opportunity
- learner has weak or due grammar state
- dependency graph identifies required grammar support

Avoid when:

- grammar is `unknown` dependency and policy disallows it
- grammar relation is soft/contextual only

### Pattern

Use when:

- sentence pattern has weak learner-state evidence
- opportunity uses the same pattern family
- pattern appears in reading/dialogue/assessment content

Avoid when:

- pattern is only superficially similar
- pattern authority ref is missing

### Chunk

Use when:

- chunk is directly practiced or reused
- chunk supports fluency for a target pattern or dialogue

Avoid when:

- chunk is not in the mounted safe authority

### Theme

Use when:

- theme revisit supports retention and context continuity
- Theme Spiral suggests non-gating revisit path
- learner has recent or due theme exposure

Avoid when:

- theme alone is treated as mastery proof
- theme continuity overrules hard dependency readiness

### Opportunity

Use when:

- one opportunity naturally reinforces another opportunity's focus refs
- planner needs a session-level reinforcement slot

Avoid when:

- opportunity has no concrete node-level reinforcement target

## 5. Signal Sources

Potential V1 signal sources:

- `mastery_band`
- `review_due_at`
- `last_seen_at`
- `last_success_at`
- `attempt_count`
- `success_ratio`
- `theme history`
- `dependency graph`

### Sources That Can Be Used Now

Current artifacts expose:

- guarded `mastery_score`
- guarded `mastery_band`
- `review_due_at`
- `last_seen_at`
- `last_success_at`
- `correct_count`
- `incorrect_count`
- `exposure_count`
- dependency `REQUIRES`
- opportunity focus refs
- theme refs
- theme spiral edges

### Sources Not Yet Strong Enough

Current artifacts do not yet provide:

- reliable attempt history beyond sparse sample events
- true retention decay
- graph-aware aggregation
- full theme history by learner
- assessment feedback loop
- learner-session history

V1 should use only conservative signals and emit warnings when signal coverage is sparse.

## 6. Scoring Model

Future `reinforcement_score` should be derived, explainable, and bounded.

Recommended V1 formula:

```text
reinforcement_score =
0.30 * review_due_score
+ 0.25 * mastery_gap_score
+ 0.20 * time_decay_score
+ 0.15 * dependency_importance_score
+ 0.10 * theme_continuity_score
```

### `review_due_score`

Meaning:

- gives priority to nodes whose `review_due_at` is due or soon due

Initial rule:

```text
1.00 if review_due_at <= plan_time
0.70 if review_due_at within 3 days
0.30 if review_due_at exists but not soon
0.00 if no review_due_at
```

### `mastery_gap_score`

Meaning:

- prioritizes weak-but-known material

Initial rule:

```text
seen = 0.90
practicing = 0.80
functional = 0.35
mastered = 0.10
automatic = 0.00
unknown = 0.20 only for introduction, not reinforcement
```

### `time_decay_score`

Meaning:

- approximates stale exposure until true decay exists

Initial rule:

```text
higher when last_seen_at is older
lower when recent success exists
0.00 when no time anchor exists
```

### `dependency_importance_score`

Meaning:

- raises reinforcement for nodes that support reachable opportunities

Initial rule:

```text
1.00 for weak prerequisite of selected/future child opportunity
0.60 for shared grammar/pattern support
0.30 for contextual support
0.00 when no dependency or focus overlap exists
```

### `theme_continuity_score`

Meaning:

- supports thematic revisit without turning theme into a gate

Initial rule:

```text
1.00 same theme due for revisit
0.60 adjacent accepted Theme Spiral step
0.20 related theme only
0.00 no theme relation
```

Important:

- Theme Spiral must remain non-gating.
- Reinforcement score must not override dependency blocks.
- A positive score must carry reason codes.

## 7. State Machine

Recommended reinforcement state machine:

```text
new -> seen -> practicing -> stable -> mastered -> decayed
```

### `new`

No usable learner evidence.

Planner action:

- introduction, not reinforcement

### `seen`

Exposure exists but no stable success.

Planner action:

- review or light reinforcement

### `practicing`

Learner has weak or partial evidence.

Planner action:

- strong reinforcement candidate

### `stable`

Learner is functional but not deeply stable.

Planner action:

- occasional reinforcement, especially before harder child opportunities

### `mastered`

Learner has strong evidence.

Planner action:

- maintenance review only unless decay or transfer failure appears

### `decayed`

Previously stronger evidence is stale or has fallen below threshold.

Planner action:

- high-priority reinforcement or remediation

Transition rules:

- `new -> seen`: first exposure
- `seen -> practicing`: additional exposure or partial success
- `practicing -> stable`: repeated success or direct target evidence
- `stable -> mastered`: strong evidence over time
- `mastered -> decayed`: true decay or failed recent assessment
- `any -> remediation`: diagnostic failure or prerequisite gap

## 8. Opportunity Reinforcement

Node reinforcement must roll up into opportunity reinforcement.

Example:

```text
kitchen
-> There is a kitchen.
-> Home opportunity
```

Node-level signals:

- `vocabulary:kitchen` weak or due
- `pattern:There is ___.` due or weak
- `theme:Home` revisit useful

Opportunity-level result:

```text
Home opportunity reinforces kitchen + there-is pattern + home theme
```

Recommended V1 opportunity aggregation:

```text
opportunity_reinforcement_score =
max(node_reinforcement_scores) * 0.60
+ average(top_3_node_reinforcement_scores) * 0.40
```

Rules:

- require at least one concrete node-level target
- do not use opportunity rank alone as reinforcement evidence
- do not treat "same theme" alone as sufficient
- include `reinforced_node_refs`

## 9. Theme Spiral Integration

Theme Spiral can support reinforcement, but only as a non-gating preference.

Example:

```text
Home -> Family -> Home revisit
```

Valid uses:

- suggest revisit after adjacent spiral movement
- identify same-theme return opportunities
- explain continuity in warm-up or reinforcement block

Invalid uses:

- block a learner
- claim mastery
- override missing prerequisite
- fabricate reinforcement without node overlap or learner-state evidence

Current facts:

- Theme Spiral has 12 accepted `SPIRAL_TO` edges.
- Theme Spiral has 0 gate-eligible edges.
- 8 stage-gap cases remain in review queue.

V1 should cap Theme Spiral contribution at preference level:

```text
theme_continuity_score max contribution = 0.10 of reinforcement_score
```

## 10. Dependency Integration

Dependency graph can identify reinforcement targets when a parent node supports a child opportunity.

Pattern:

```text
Parent node forgotten
-> Child opportunity
```

Valid behavior:

- if child opportunity is eligible and parent is weak/due, reinforce parent through related content
- if parent is missing and gate is hard, block child and recommend prerequisite remediation

Invalid behavior:

- using reinforcement to bypass hard dependency gates
- treating `unknown` dependency as eligible reinforcement

Current root cause:

- the only 7 opportunities with positive S10C `reinforcement_score` are the 7 opportunities with `dependency.status = unknown`
- S10E correctly blocks them under `allow_unknown_dependency = false`
- therefore eligible reinforcement count is 0

Implication:

```text
S10C reinforcement_score is currently coupled to dependency.requires metadata, not to reachable learner-safe reinforcement.
```

S10G must separate:

- `dependency_remediation_candidate`
- `eligible_reinforcement_candidate`

## 11. Planner Integration

Recommended future flow:

```text
Ranking
-> Reinforcement Signal Authority
-> Planner
```

Planner should not simply take Top-N.

Required planner behavior:

- apply hard blocks first
- find eligible reinforcement signals
- assign a reinforcement block only when at least one selected opportunity has a valid reinforcement target
- otherwise emit warning or partial plan

S10E currently does the safer behavior:

```text
preserve session shape
emit warning
do not claim reinforcement evidence
```

Future S10H planner re-audit should measure:

- `planner_usage_rate`
- `reinforcement_block_validity`
- `structural_placeholder_count`
- `eligible_reinforcement_count`

## 12. Session Integration

Session blocks:

- `warm_up`
- `core_learning`
- `reinforcement`
- `assessment`

Recommended reinforcement block policy:

```text
reinforcement block requires:
1. selected opportunity is dependency-ready
2. reading/dialogue/content authority can deliver it
3. at least one concrete reinforced node exists
4. reason_codes include reinforcement reason
```

Valid reason codes:

- `review_due`
- `weak_mastery`
- `dependency_repair`
- `theme_revisit`
- `pattern_reuse`
- `vocabulary_reuse`
- `assessment_feedback`

Invalid reason codes:

- `high_rank` alone
- `same_theme` alone
- `reading_available` alone

If no valid reinforcement exists:

- planner may keep a structural block only if summary warns
- planner must not report a positive reinforcement delivery rate

## 13. Assessment Feedback Loop

Future loop:

```text
Assessment
-> Learner State
-> Reinforcement Signal
-> Planner
```

Assessment should produce evidence events that update learner state.

Reinforcement Signal Authority should then read learner state and identify:

- failed nodes
- weak prerequisites
- decayed nodes
- repeated confusion pairs
- due review targets

Planner should consume these signals to produce sessions.

Important boundary:

- Assessment writes evidence.
- Learner State computes guarded truth.
- Reinforcement Signal derives candidates.
- Planner selects sessions.

Reinforcement Signal must not write learner state directly.

## 14. Reinforcement Authority Schema

Future `reinforcement_signal.json` draft:

```json
{
  "signal_id": "RS_OPP_LO_A1_000001_001",
  "target_type": "opportunity",
  "target_id": "LO_A1_000001",
  "reinforcement_score": 0.0,
  "signal_sources": [
    {
      "source_type": "learner_state",
      "source_ref": "learner:james|vocabulary:VOCAB_NODE_004210"
    }
  ],
  "reinforced_node_refs": [
    "vocabulary:VOCAB_NODE_004210"
  ],
  "reason_codes": [
    "weak_mastery",
    "review_due"
  ],
  "eligibility": {
    "dependency_ready": true,
    "content_available": true,
    "planner_eligible": true
  },
  "generated_at": "2026-06-18T00:00:00Z",
  "source": "REINFORCEMENT_SIGNAL_AUTHORITY"
}
```

Required fields:

- `signal_id`
- `target_type`
- `target_id`
- `reinforcement_score`
- `signal_sources`
- `reinforced_node_refs`
- `reason_codes`
- `eligibility`
- `generated_at`
- `source`

Allowed `target_type`:

- `vocabulary`
- `grammar`
- `pattern`
- `chunk`
- `theme`
- `opportunity`

Validation rules:

- score must be `0.0-1.0`
- reason codes must be non-empty for positive score
- positive planner-eligible signal must pass dependency/content checks
- no signal may promote a hard-blocked opportunity into planner eligibility

## 15. QA / Audit Plan

Required metrics:

- `signal_count`
- `eligible_count`
- `due_count`
- `high_priority_count`
- `planner_usage_rate`
- `assessment_feedback_rate`
- `theme_revisit_rate`
- `dependency_repair_rate`

Additional recommended metrics:

- `blocked_positive_signal_count`
- `empty_learner_state_count`
- `cold_start_signal_count`
- `reason_code_distribution`
- `reinforced_node_type_distribution`
- `eligible_opportunity_reinforcement_count`
- `structural_placeholder_count`
- `false_reinforcement_rate`

Required audits:

- positive reinforcement signals have concrete node targets
- blocked opportunities are not planner-eligible
- theme-only signals are capped
- same learner/input produces deterministic signal ordering
- empty learner state does not fabricate reinforcement
- cold-start learners produce introduction candidates, not reinforcement candidates
- assessment feedback maps to learner-state before reinforcement

## 16. Risks and Mitigations

### Everything becomes reinforcement

Risk:

- any repeated theme or high-ranked opportunity is labeled reinforcement.

Mitigation:

- require concrete node targets and reason codes.

### Theme overfitting

Risk:

- planner repeatedly selects same-theme items and calls it reinforcement.

Mitigation:

- cap theme-only contribution and audit theme distribution.

### Review fatigue

Risk:

- due review signals dominate sessions.

Mitigation:

- enforce session mix and cap review-only opportunities.

### Dependency loops

Risk:

- dependency repair repeatedly points to blocked parent/child cycles.

Mitigation:

- use dependency graph cycle audit and blocked-positive-signal count.

### Planner starvation

Risk:

- hard policy rejects all reinforcement candidates.

Mitigation:

- emit partial plan or structural warning rather than fake reinforcement.

### Cold start

Risk:

- no learner state exists, but planner needs reinforcement slot.

Mitigation:

- cold start produces introduction or diagnostic candidates, not reinforcement.

### Empty learner state

Risk:

- empty state returns artificial high reinforcement.

Mitigation:

- fail closed in learner mode and return zero reinforcement signals unless policy allows generic review.

### API failure / timeout

Risk:

- future assessment or learner-history service fails.

Mitigation:

- use local artifacts first; future services must have timeout and fail-closed behavior.

### Duplicate execution

Risk:

- repeated signal builds duplicate signal ids.

Mitigation:

- stable IDs from target + learner + signal source.

### Process restart

Risk:

- signal order changes after restart.

Mitigation:

- deterministic ordering by score, reason priority, target id.

## 17. Repair Roadmap

### `S10G_ReinforcementSignal_Implementation`

Minimal first pass:

- read learner state, learning opportunities, ranked opportunities, dependency graph, theme spiral graph, reading stubs
- produce `reinforcement_signal.json`
- classify signals into review/reinforcement/remediation
- separate blocked positive signals from planner-eligible signals
- compute opportunity reinforcement score from node-level signals
- emit summary metrics
- add deterministic tests

### `S10H_Planner_ReAudit`

Validate:

- reinforcement block uses real reinforcement signal
- no structural placeholder remains when eligible signals exist
- planner does not select blocked reinforcement candidates
- session summary reports reinforcement validity

### `S10I_LearnerMode_Enablement`

Enable learner-specific planner behavior only after:

- reinforcement signals are available
- learner-state decay risk is explicitly handled or warned
- graph-aware aggregation risk is bounded
- cold-start behavior is explicit

## 18. Final Verdict

S10F is ready to proceed.

Root cause of zero eligible reinforcement:

```text
S10C has 7 opportunities with reinforcement_score > 0,
but all 7 have dependency.status = unknown.
S10E correctly blocks unknown dependency,
so eligible reinforcement opportunity count is 0.
```

Current gap:

```text
There is no Reinforcement Signal Authority that derives learner-safe,
dependency-ready reinforcement candidates from learner state, dependency,
theme, and opportunity overlap.
```

Design conclusion:

- S10E warning is valid.
- Planner should not be fixed by forcing top-ranked items into reinforcement.
- S10G should implement a distinct derived Reinforcement Signal Authority.

```text
S10F_STATUS: DESIGN_READY
```

## Closeout Summary

Files Created:

- `docs/ulga/ULGA_S10F_REINFORCEMENT_SIGNAL_DESIGN_SCAN.md`

Files Modified:

- None

Inputs Reviewed:

- S9A/S9F/S9G/S9I/S9J/S9L docs
- S10A/S10B/S10C/S10D/S10E docs
- `learning_opportunities.json`
- `ranked_learning_opportunities.json`
- `antigravity_plan.json`
- `learner_state.json`
- `learning_signal_policy.json`
- `dependency_graph.json`
- `theme_spiral_graph.json`
- related summary reports

Key Design Decisions:

- Review, reinforcement, and remediation are separate concepts.
- Reinforcement requires concrete node-level target evidence.
- Theme continuity alone is not reinforcement.
- Dependency-blocked positive reinforcement signals must not become planner-eligible.
- S10G should materialize a separate `reinforcement_signal.json`.

Root Cause of Zero Reinforcement:

- existing positive S10C reinforcement scores are tied to unknown dependency records
- S10E blocks those records
- no learner-safe reinforcement signal authority exists yet

Reinforcement Model Chosen:

- weighted score from review due, mastery gap, time decay, dependency importance, and theme continuity
- opportunity-level score aggregates node-level signals
- positive signals require reason codes and eligibility checks

Risks Found:

- everything becomes reinforcement
- theme overfitting
- review fatigue
- dependency loops
- planner starvation
- cold start
- empty learner state

Final Verdict:

```text
S10F_STATUS: DESIGN_READY
```

Recommended Next Task:

```text
ULGA-S10G_ReinforcementSignal_Implementation
```
