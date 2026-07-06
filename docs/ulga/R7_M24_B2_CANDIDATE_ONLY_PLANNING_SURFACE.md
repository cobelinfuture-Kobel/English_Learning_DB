# R7-M24 B2 Candidate-only Planning Surface

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M24 B2 candidate-only planning surface definition

Branch:
codex/r7-m24-b2-surface

Status:
PLANNING_SURFACE_ONLY
```

R7-M24 defines a capped B2 candidate planning surface after R7-M23 confirmed B2 planning readiness.

This task does not modify `grammar_nodes.json`, `grammar_edges.json`, derived artifacts, validators, CI expectations, learner-facing practice, or learner state.

## 2. Scope Lock

Allowed in R7-M24:

```text
- define B2 planning candidates
- identify B1 / B1_PLUS graph anchors
- keep all proposals planning-only
- produce next evidence-verification step
```

Forbidden in R7-M24:

```text
- no grammar_nodes.json modification
- no grammar_edges.json modification
- no derived artifact rebuild
- no validation report refresh
- no CI test expectation change
- no learner-facing practice generation
- no learner state write
- no accepted authority promotion
```

## 3. B2 Candidate Surface

R7-M24 proposes 8 B2 candidate records. These are proposal records only, not grammar nodes.

| Proposed grammar_id | Planning label | Anchor in closed graph | B2 direction | Planning status |
|---|---|---|---|---|
| `GRAMMAR_MIXED_CONDITIONALS_B2` | mixed conditionals | `GRAMMAR_SECOND_CONDITIONAL_BASIC` | mixed time-reference conditional meaning | PLANNING_ONLY |
| `GRAMMAR_PASSIVE_REPORTING_STRUCTURES_B2` | passive reporting structures | `GRAMMAR_PASSIVE_WITH_MODALS_B1PLUS` | impersonal passive reporting forms | PLANNING_ONLY |
| `GRAMMAR_ADVANCED_MODAL_SPECULATION_B2` | advanced modal speculation | `GRAMMAR_MODAL_DEDUCTION_PAST_B1PLUS` | modal speculation with perfect/continuous aspect | PLANNING_ONLY |
| `GRAMMAR_RELATIVE_CLAUSES_PREPOSITION_WHOSE_B2` | relative clauses with prepositions / whose | `GRAMMAR_RELATIVE_CLAUSES_NONDEFINING_PREVIEW_B1PLUS` | advanced relative clause control | PLANNING_ONLY |
| `GRAMMAR_FUTURE_PERFECT_B2` | future perfect | `GRAMMAR_FUTURE_CONTINUOUS_PREVIEW_B1PLUS` | future completion before a future time | PLANNING_ONLY |
| `GRAMMAR_REPORTED_SPEECH_ADVANCED_B2` | advanced reported speech | `GRAMMAR_REPORTED_QUESTIONS_REQUESTS_B1PLUS` | wider tense/modal/reporting pattern control | PLANNING_ONLY |
| `GRAMMAR_PERFECT_CONTINUOUS_ADVANCED_CONTRAST_B2` | advanced perfect continuous contrast | `GRAMMAR_PRESENT_PERFECT_SIMPLE_CONTINUOUS_CONTRAST_B1PLUS` | aspect contrast with duration/result/emphasis | PLANNING_ONLY |
| `GRAMMAR_INVERSION_NEGATIVE_ADVERBIALS_B2` | inversion after negative adverbials | `GRAMMAR_WH_QUESTIONS_BE_DO_BASIC` | formal emphasis and word-order control | PLANNING_ONLY |

## 4. Planning Counts

```text
proposed_b2_candidates = 8
implementation_ready = 0
source_ref_verified = 0
```

## 5. Dependency Hypotheses

These are planning hypotheses only. They are not edges.

```text
GRAMMAR_MIXED_CONDITIONALS_B2 likely requires GRAMMAR_SECOND_CONDITIONAL_BASIC.
GRAMMAR_PASSIVE_REPORTING_STRUCTURES_B2 likely requires GRAMMAR_PASSIVE_WITH_MODALS_B1PLUS and GRAMMAR_REPORTED_SPEECH_BASIC.
GRAMMAR_ADVANCED_MODAL_SPECULATION_B2 likely requires GRAMMAR_MODAL_DEDUCTION_PAST_B1PLUS and GRAMMAR_PRESENT_PERFECT_CONTINUOUS_BASIC.
GRAMMAR_RELATIVE_CLAUSES_PREPOSITION_WHOSE_B2 likely requires GRAMMAR_RELATIVE_CLAUSES_NONDEFINING_PREVIEW_B1PLUS.
GRAMMAR_FUTURE_PERFECT_B2 likely requires GRAMMAR_FUTURE_CONTINUOUS_PREVIEW_B1PLUS and GRAMMAR_PRESENT_PERFECT_RESULT_BASIC.
GRAMMAR_REPORTED_SPEECH_ADVANCED_B2 likely requires GRAMMAR_REPORTED_QUESTIONS_REQUESTS_B1PLUS.
GRAMMAR_PERFECT_CONTINUOUS_ADVANCED_CONTRAST_B2 likely requires GRAMMAR_PRESENT_PERFECT_SIMPLE_CONTINUOUS_CONTRAST_B1PLUS.
GRAMMAR_INVERSION_NEGATIVE_ADVERBIALS_B2 likely requires GRAMMAR_WH_QUESTIONS_BE_DO_BASIC.
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
R7-M24_IMPLEMENTATION_DECISION = NOT_READY_SOURCE_REF_VERIFICATION_REQUIRED
```

Reason:

```text
B2 planning surface is defined, but concrete B2 source_ref evidence has not yet been verified.
```

## 8. Gate & Distance Update

```text
[PASS] R7-M24 remains planning-only.
[PASS] 8 B2 candidate proposals defined.
[PASS] All proposals map to closed B1 / B1_PLUS anchors.
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
R7-M25 B2 concrete source-ref verification scan
```

R7-M25 must remain evidence-verification only. It should map the 8 R7-M24 proposals to concrete EGP source_ref candidates where possible, but it must not modify `grammar_nodes.json` or `grammar_edges.json`.
