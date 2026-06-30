# ULGA-S9G Learner State Builder Guardrail Design Scan

## Executive Summary

Learner-state guardrails are needed because S9F proved that the S9E V1 scoring model can assign high mastery bands from single low-authority signals. This creates a real risk that downstream consumers will overestimate learner readiness, especially for derived or indirect node types.

S9G is not a builder fix. This task is a read-only design scan that defines future scoring caps and dampening rules for S9H implementation.

The goal of S9G is to design guardrails that:

- reduce mastery overstatement from weak evidence
- preserve deterministic rebuild behavior
- remain compatible with the existing S9C schema
- keep Candidate Ranking and Planner dependent on guarded learner-state outputs rather than inflated raw ratios

## S9F Findings Review

S9F QA returned `PASS_WITH_WARNINGS`, not `BLOCKER`, because contract validity and summary integrity were correct while scoring behavior remained risky.

Key S9F warning groups:

- role high-band low-authority warnings
  - `assessment:SHORT_WRITING_CHECK_A2_001` reached `functional` from `review_signal`
  - `morphology:word_family_read` reached `functional` from `diagnostic_signal`
  - `sentence_pattern:PATTERN_NODE_000014` reached `mastered` from `supporting_context`
  - `theme:a1_daily_life_and_routines` reached `mastered` from `coverage_signal`
- ratio overstatement warnings
  - 6 records were flagged with `WARN_RATIO_OVERSTATEMENT_RISK`
- single-event derived-node mastery warnings
  - 5 records were flagged with `WARN_SINGLE_EVENT_DERIVED_NODE_MASTERY`
- decay-not-modeled warning
  - `decay_adjusted_score == mastery_score` for all records
- empty-log limitation
  - zero-event global cold start is still not naturally supported because S9C collections are non-empty

These warnings establish that S9H guardrails are necessary before S9E-style output should influence future Candidate Ranking.

## Problem Definition

The S9E ratio formula is:

```text
mastery_score =
weighted_success_sum / weighted_exposure_sum
```

Because both numerator and denominator are scaled by the same effective strength, the score ratio is preserved even when the underlying evidence is low-authority.

Example:

```text
weighted_success = score * effective_strength
weighted_exposure = effective_strength
ratio = score
```

If a low-authority event is the only evidence for a learner-node pair, it can still produce a high `mastery_score` so long as the raw event score is high. This is why:

- `coverage_signal` can produce `mastered`
- `supporting_context` can produce `mastered`
- `diagnostic_signal` can produce `functional`
- `review_signal` can produce `functional`

The formula is internally consistent but behaviorally unsafe without post-aggregation guardrails.

## Guardrail Design Principles

Recommended principles:

- `primary_target` evidence can support direct mastery progression.
- `supporting_context` can support exposure and readiness, but should have explicit band ceilings.
- `prerequisite` evidence can support readiness, not full mastery.
- `coverage_signal` should not create mastery by itself.
- `diagnostic_signal` should route remediation and reduce confidence uncertainty, not raise mastery strongly.
- `review_signal` should shape `review_due_at` and confidence more than mastery.
- derived node types need stricter ceilings than direct mastery targets.
- stable high bands should require multiple evidence events.
- productive evidence should eventually be stronger than recognition-only evidence, even when raw scores are similar.
- guardrails must run before output so S9C band-score alignment is preserved.

## Role-Based Band Caps

Proposed V1 role caps for S9H:

### `primary_target`

- `max_band = automatic`
- no cap by role alone
- still subject to single-event and node-type guardrails

### `supporting_context`

- `max_band = functional`
- if `exposure_count == 1`, recommended `max_band = practicing` for derived node types
- for direct node types, `functional` can remain possible only after dampening and high-confidence evidence

### `prerequisite`

- `max_band = functional`
- if `exposure_count == 1`, `max_band = practicing`
- should mainly inform readiness and dependency support, not mastery completion

### `coverage_signal`

- `max_band = seen` by default
- optionally `practicing` only when multiple distinct events exist and additional supporting evidence is present
- should never reach `functional`, `mastered`, or `automatic` by itself

### `diagnostic_signal`

- `max_band = practicing`
- should primarily affect confidence, review urgency, and future remediation flags

### `review_signal`

- `max_band = seen` by default
- optionally `practicing` with repeated corroborating evidence
- should schedule review rather than prove mastery

## Node-Type Guardrails

Recommended node-type groups:

### Direct mastery targets

- `grammar`
- `vocabulary`
- `chunk`
- `sentence_pattern`

These can support higher mastery bands when evidence is direct and repeated. `sentence_pattern` should still be guarded when evidence is only contextual.

### Derived / aggregate / future targets

- `theme`
- `morphology`
- `skill`
- `assessment`
- `reading`
- `dialogue`
- `exercise_type`

Recommended caps:

- `theme`
  - requires multi-node or multi-event evidence before `functional+`
  - should remain `practicing` or below when only `coverage_signal` evidence exists
- `morphology`
  - requires multiple vocabulary-family evidence refs before `functional+`
  - one diagnostic family hint should not imply stable family mastery
- `skill`
  - should not become `functional+` from one `supporting_context`
- `assessment`
  - should usually be evidence source, not mastery target
  - allow `functional+` only when explicitly `primary_target`
- `dialogue`
  - should require direct task completion or `primary_target` role before stable `functional+`
- `reading`
  - should require direct reading-task targeting or repeated evidence before `functional+`
- `exercise_type`
  - should not be treated as a mastery target in V1
  - recommended cap: `seen`

## Single-Event Guardrails

Recommended V1 single-event rules:

- single event + non-primary role cannot exceed `practicing`
- single event + `primary_target` may reach `functional` or `mastered` depending on score and confidence
- `automatic` requires repeated successful evidence across at least 3 events
- `mastered` requires either:
  - at least 2 successful evidence events, or
  - one high-confidence `primary_target` productive event in a future evidence taxonomy
- `theme`, `morphology`, `skill`, `assessment`, and `dialogue` should require at least 2 events or explicit aggregation logic before `functional+`

This directly addresses the S9F pattern where one low-authority event created a stable high band.

## Score Dampening vs Band Cap

Two approaches were evaluated:

### A. Dampening `mastery_score`

- modifies the score before band mapping
- preserves S9C score-band alignment
- better for downstream ranking because guarded score and guarded band stay coherent
- may hide raw evidence strength unless separately logged

### B. Keep raw `mastery_score` but cap `mastery_band`

- preserves raw score auditability
- creates score-band mismatch under the current S9C validator
- would require schema evolution or exceptions that weaken contract clarity

### Recommendation for V1

Recommend dampening before S9C band mapping.

Rationale:

- S9C requires `mastery_band` to match `mastery_score`
- guardrails can be implemented without schema changes
- raw vs guarded values can be stored in future builder summary or QA reports instead of `learner_state.json`

## Proposed Guardrail Formula

Future S9H baseline:

```text
base_mastery_score = existing S9E formula
```

Candidate guardrail forms:

```text
guardrail_multiplier =
role_cap_multiplier
* node_type_multiplier
* single_event_multiplier
* evidence_diversity_multiplier

guarded_mastery_score =
base_mastery_score * guardrail_multiplier
```

Alternative hard-ceiling form:

```text
guarded_mastery_score =
min(base_mastery_score, guardrail_score_ceiling)
```

Recommended hybrid:

- use score ceiling for hard safety cases such as `coverage_signal`, `review_signal`, `diagnostic_signal`, and `exercise_type`
- use dampening multipliers for softer cases such as `supporting_context`, `prerequisite`, and derived node types with some meaningful evidence
- remap `mastery_band` from `guarded_mastery_score`

This hybrid is preferred because some cases are categorically unsafe while others are merely too optimistic.

## Recommended V1 Guardrail Table

### Role ceilings

| Role | Recommended ceiling | Notes |
|---|---:|---|
| `primary_target` | `1.00` | No role-only ceiling. |
| `supporting_context` | `0.69` | Cap at `functional`; lower with single-event rules. |
| `prerequisite` | `0.69` | Cap at `functional`; single-event rule can reduce to `0.49`. |
| `coverage_signal` | `0.24` | Default hard cap at `seen`; optional `0.49` only with repeated corroboration. |
| `diagnostic_signal` | `0.49` | Cap at `practicing`. |
| `review_signal` | `0.24` | Default cap at `seen`; optional `0.49` only with repeated corroboration. |

### Node-type ceilings

| Node type | Recommended ceiling | Notes |
|---|---:|---|
| `theme` | `0.49` | Unless at least 2 distinct `evidence_refs` and at least 2 contributing node types. |
| `morphology` | `0.49` | Unless at least 2 related vocabulary-family evidence refs exist. |
| `skill` | `0.49` | Unless `primary_target`. |
| `assessment` | `0.49` | Unless `primary_target`. |
| `dialogue` | `0.69` | Unless `primary_target`. |
| `reading` | `0.69` | Unless `primary_target`. |
| `exercise_type` | `0.24` | Cap at `seen` in V1. |

### Automatic threshold

`automatic` should require:

- at least 3 successful evidence events
- at least one `primary_target` event
- confidence average `>= 0.85`

### Mastered threshold

`mastered` should require:

- at least 2 successful evidence events, or
- one high-confidence `primary_target` productive event in a later richer evidence model

## Impact Simulation on Current S9E Output

Without modifying files, the expected effect on current S9E output is:

- `theme:a1_daily_life_and_routines`
  - current: `mastered` from single `coverage_signal`
  - expected guarded outcome: `seen` or `practicing`
- `sentence_pattern:PATTERN_NODE_000014`
  - current: `mastered` from single `supporting_context`
  - expected guarded outcome: `functional` or `practicing`
- `assessment:SHORT_WRITING_CHECK_A2_001`
  - current: `functional` from `review_signal`
  - expected guarded outcome: `seen` or `practicing`
- `morphology:word_family_read`
  - current: `functional` from `diagnostic_signal`
  - expected guarded outcome: `practicing`
- `grammar:GRAMMAR_NODE_000123`
  - current: `mastered` from `primary_target`
  - expected guarded outcome: likely remains `mastered`
- `chunk:SAFE_CHUNK_000321`
  - current: `functional` from `primary_target`
  - expected guarded outcome: may remain `functional` or fall to `practicing` depending on future success-threshold and retry-sensitive policy

The key point is that S9G should lower inflated indirect records without collapsing legitimate direct records.

## Interaction with Review Due

Guardrail lowering changes `mastery_band`, which changes `review_due_at`.

Recommended interpretation:

- lower guarded mastery should pull review closer
- `review_signal` should influence earlier `review_due_at` even when it does not increase mastery
- `diagnostic_signal` should create a future remediation flag or confidence note, not mastery inflation
- review policy should consume guarded state, not raw pre-guardrail ratios

This keeps review scheduling aligned with safer learner-state estimates.

## Interaction with Candidate Ranking

Guardrails must run before future Candidate Ranking.

Implications:

- ranking should consume guarded `mastery_score` and guarded `mastery_band`
- raw pre-guardrail score, if retained at all, should live only in summary/audit artifacts
- `learner_mastery_gap` must not be computed from inflated derived-node mastery
- theme spiral and prerequisite readiness should not inherit false confidence from low-authority single-event records

Current S9E-style output should not feed future Candidate Ranking unchanged.

## Compatibility with S9C Schema

S9C requires `mastery_band` to match `mastery_score` ranges.

Therefore:

- guardrails must adjust `mastery_score` before output
- do not add `raw_mastery_score` to `learner_state.json` unless the schema evolves
- raw vs guarded comparisons can be kept in future builder summary or QA output
- no schema change is required for S9H if guarded score is the emitted score

This is the main reason score dampening is preferred over band-only caps.

## Risks and Open Questions

- Over-dampening may slow progression and understate real learner readiness.
- Under-dampening may continue to mislead future ranking and planning.
- Theme and morphology guardrails will remain approximate until a graph-aware resolver exists.
- Productive evidence and recognition evidence should be separated more explicitly later.
- Zero-event cold start remains a separate contract issue and is not solved by guardrails.
- True decay remains unresolved; guardrails are not a replacement for retention modeling.
- Teacher-reviewed evidence may deserve richer exception logic later, but V1 should default conservative rather than permissive.

## PASS / WARN / BLOCKER Assessment

Overall assessment: `PASS_WITH_WARNINGS`.

### PASS

- S9F proved guardrails are necessary with concrete examples, not hypothetical concerns.
- S9H implementation is feasible without schema changes if guarded score is emitted before S9C band mapping.
- The role/node-type/single-event risk classes are clear enough to implement deterministic V1 guardrails.

### WARN

- Guardrail thresholds proposed here are still heuristic and will need QA after implementation.
- Some direct targets such as `sentence_pattern` will need nuanced handling because the node type is direct but the observed role may still be indirect.
- Theme and morphology ceilings are intentionally conservative because their true aggregation logic is not yet graph-aware.
- Decay and empty-log limitations remain open after S9G.

### BLOCKER

- Current S9E output should not feed future Candidate Ranking without guardrails.

## Recommended Next Task

`ULGA-S9H_LearnerStateBuilder_Guardrail_Implementation`
