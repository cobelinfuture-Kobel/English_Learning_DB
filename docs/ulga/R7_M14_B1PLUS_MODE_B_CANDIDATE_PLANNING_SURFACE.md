# R7-M14 B1_PLUS Mode-B Candidate Planning Surface

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M14 B1_PLUS Mode-B candidate planning surface definition

Branch:
codex/r7-m14-b1plus-planning-surface

Status:
PLANNING_SURFACE_ONLY
```

R7-M14 defines a capped B1_PLUS candidate planning surface under the R7-M13 Mode-B policy:

```text
B1_PLUS = bridge from B1 to B2 preview
```

This task does not modify `grammar_nodes.json`, `grammar_edges.json`, derived artifacts, validators, CI expectations, learner-facing practice, or learner state.

## 2. Scope Lock

Allowed in R7-M14:

```text
- define B1_PLUS Mode-B planning candidates
- mark candidate bridge role
- identify dependency hypotheses against the closed B1 graph
- keep all proposals planning-only
- produce next evidence-verification step
```

Forbidden in R7-M14:

```text
- no grammar_nodes.json modification
- no grammar_edges.json modification
- no derived artifact rebuild
- no validation report refresh
- no CI test change
- no learner-facing practice generation
- no learner state write
- no accepted authority promotion
- no B2 implementation
```

## 3. Mode-B Candidate Surface

R7-M14 proposes 8 B1_PLUS bridge candidates. These are proposal records only, not grammar nodes.

| Proposed grammar_id | Bridge role | Planning label | B1 anchor | B2 preview direction | Planning status |
|---|---|---|---|---|---|
| `GRAMMAR_REPORTED_QUESTIONS_REQUESTS_B1PLUS` | `BRIDGE_ROLE_CLAUSE_COMPLEXITY_EXTENSION` | reported questions and requests | `GRAMMAR_REPORTED_SPEECH_BASIC` | indirect question/request control | PLANNING_ONLY |
| `GRAMMAR_MODAL_DEDUCTION_PAST_B1PLUS` | `BRIDGE_ROLE_B2_PREVIEW_USE` | modal deduction about the past | `GRAMMAR_MODAL_DEDUCTION_BASIC` | `must have` / `might have` preview | PLANNING_ONLY |
| `GRAMMAR_PASSIVE_WITH_MODALS_B1PLUS` | `BRIDGE_ROLE_B2_PREVIEW_FORM` | passive with modal verbs | `GRAMMAR_PASSIVE_PRESENT_PAST_EXPANDED_SUBJECTS_B1` | modal + passive combined form | PLANNING_ONLY |
| `GRAMMAR_RELATIVE_CLAUSES_NONDEFINING_PREVIEW_B1PLUS` | `BRIDGE_ROLE_B2_PREVIEW_FORM` | non-defining relative clause preview | `GRAMMAR_RELATIVE_CLAUSES_PLACE_TIME_OBJECT_B1` | comma-marked extra information | PLANNING_ONLY |
| `GRAMMAR_CONDITIONALS_UNLESS_AS_LONG_AS_B1PLUS` | `BRIDGE_ROLE_ADVANCED_B1_CONTROL` | conditional linkers beyond if | `GRAMMAR_FIRST_CONDITIONAL_BASIC` | conditional meaning variation | PLANNING_ONLY |
| `GRAMMAR_SECOND_CONDITIONAL_EXPANDED_B1PLUS` | `BRIDGE_ROLE_CLAUSE_COMPLEXITY_EXTENSION` | expanded second conditional control | `GRAMMAR_SECOND_CONDITIONAL_BASIC` | richer hypothetical clauses | PLANNING_ONLY |
| `GRAMMAR_PRESENT_PERFECT_SIMPLE_CONTINUOUS_CONTRAST_B1PLUS` | `BRIDGE_ROLE_ADVANCED_B1_CONTROL` | present perfect simple vs continuous contrast | `GRAMMAR_PRESENT_PERFECT_CONTINUOUS_BASIC` | aspect-choice control | PLANNING_ONLY |
| `GRAMMAR_FUTURE_CONTINUOUS_PREVIEW_B1PLUS` | `BRIDGE_ROLE_B2_PREVIEW_FORM` | future continuous preview | `GRAMMAR_FUTURE_GOING_TO_BASIC` | future form expansion | PLANNING_ONLY |

## 4. Planning Counts

```text
proposed_b1plus_candidates = 8
bridge_role_advanced_b1_control = 2
bridge_role_b2_preview_form = 3
bridge_role_b2_preview_use = 1
bridge_role_clause_complexity_extension = 2
implementation_ready = 0
```

## 5. Dependency Hypotheses

These are planning hypotheses only. They are not edges.

```text
GRAMMAR_REPORTED_QUESTIONS_REQUESTS_B1PLUS likely requires GRAMMAR_REPORTED_SPEECH_BASIC and GRAMMAR_WH_QUESTIONS_BE_DO_BASIC.
GRAMMAR_MODAL_DEDUCTION_PAST_B1PLUS likely requires GRAMMAR_MODAL_DEDUCTION_BASIC and GRAMMAR_PRESENT_PERFECT_UNIQUE_EXPERIENCE_B1.
GRAMMAR_PASSIVE_WITH_MODALS_B1PLUS likely requires GRAMMAR_PASSIVE_PRESENT_PAST_EXPANDED_SUBJECTS_B1 and GRAMMAR_CAN_STATEMENT.
GRAMMAR_RELATIVE_CLAUSES_NONDEFINING_PREVIEW_B1PLUS likely requires GRAMMAR_RELATIVE_CLAUSES_PLACE_TIME_OBJECT_B1.
GRAMMAR_CONDITIONALS_UNLESS_AS_LONG_AS_B1PLUS likely requires GRAMMAR_FIRST_CONDITIONAL_BASIC.
GRAMMAR_SECOND_CONDITIONAL_EXPANDED_B1PLUS likely requires GRAMMAR_SECOND_CONDITIONAL_BASIC.
GRAMMAR_PRESENT_PERFECT_SIMPLE_CONTINUOUS_CONTRAST_B1PLUS likely requires GRAMMAR_PRESENT_PERFECT_CONTINUOUS_BASIC and GRAMMAR_PRESENT_PERFECT_RESULT_BASIC.
GRAMMAR_FUTURE_CONTINUOUS_PREVIEW_B1PLUS likely requires GRAMMAR_FUTURE_GOING_TO_BASIC and GRAMMAR_PRESENT_CONTINUOUS_BASIC.
```

## 6. Evidence Requirement

Before any implementation, each candidate must receive concrete source evidence:

```text
- source_id
- concrete source_ref
- CEFR / EGP row or normalized authority reference
- source_role = authority_source or normalized_authority_artifact
- allowed_use includes level_alignment and grammar_construct_reference
- blocked_use includes learner_state_write and automatic_promotion
- confidence = operator_review_required unless normalized reviewed
```

## 7. Implementation Decision

```text
R7-M14_IMPLEMENTATION_DECISION = NOT_READY_SOURCE_REF_VERIFICATION_REQUIRED
```

Reason:

```text
Mode-B planning surface is defined, but concrete B1_PLUS source_ref evidence has not yet been verified.
```

## 8. Gate & Distance Update

```text
[PASS] R7-M14 remains planning-only.
[PASS] 8 B1_PLUS Mode-B candidate proposals defined.
[PASS] All proposals map to B1 anchors and B2 preview directions.
[PASS] No grammar_nodes.json changes.
[PASS] No grammar_edges.json changes.
[PASS] No derived artifact rebuild.
[PASS] No validation report refresh.
[PASS] No CI test change.
[PASS] No learner-facing practice generated.
[PASS] No learner state write path introduced.
[BLOCKED] Implementation remains not ready until source_ref verification.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

## 9. Next Shortest Step

```text
NEXT_SHORT_STEP:
R7-M15 B1_PLUS Mode-B concrete source-ref verification scan
```

R7-M15 must remain evidence-verification only. It should map the 8 R7-M14 proposals to concrete EGP source_ref candidates where possible, but it must not modify `grammar_nodes.json` or `grammar_edges.json`.
