# R7-M18 B1_PLUS Mode-B Package-A Candidate-node Readiness Checklist

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M18 B1_PLUS Mode-B Package-A candidate-node readiness checklist

Branch:
codex/r7-m18-b1plus-readiness-checklist

Status:
CHECKLIST_ONLY
```

R7-M18 verifies whether the 7 Package-A accepted B1_PLUS Mode-B candidates are ready for a later operator-approved candidate-node implementation batch. This task does not modify `grammar_nodes.json`, `grammar_edges.json`, derived artifacts, validators, CI tests, learner-facing practice, or learner state.

## 2. Prior Gate From R7-M17

```text
SELECTED_PACKAGE = PACKAGE-A
accepted_for_readiness_review = 7
deferred = 1
R7-M17_IMPLEMENTATION_DECISION = NOT_READY_READINESS_CHECK_REQUIRED
```

Deferred proposal:

```text
GRAMMAR_SECOND_CONDITIONAL_EXPANDED_B1PLUS
```

## 3. Scope Lock

Allowed in R7-M18:

```text
- verify the 7 accepted B1_PLUS candidates against implementation prerequisites
- preserve Package-A deferral for second conditional expanded
- decide whether an operator-approved candidate-node implementation batch can be proposed
- produce a stop / resume handoff if implementation is the next step
```

Forbidden in R7-M18:

```text
- no grammar_nodes.json modification
- no grammar_edges.json modification
- no derived artifact rebuild
- no validation report refresh
- no CI test expectation change
- no learner-facing practice generation
- no learner state write
- no accepted authority promotion
- no B2 implementation
```

## 4. Candidate Readiness Matrix

| # | Proposed grammar_id | Final stage | Bridge role | Concrete source_ref status | Candidate-only safety | Readiness |
|---:|---|---:|---|---|---|---|
| 1 | `GRAMMAR_REPORTED_QUESTIONS_REQUESTS_B1PLUS` | B1_PLUS | clause complexity extension | present from R7-M15 | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 2 | `GRAMMAR_MODAL_DEDUCTION_PAST_B1PLUS` | B1_PLUS | B2 preview use | present from R7-M15 | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 3 | `GRAMMAR_PASSIVE_WITH_MODALS_B1PLUS` | B1_PLUS | B2 preview form | present from R7-M15 | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 4 | `GRAMMAR_RELATIVE_CLAUSES_NONDEFINING_PREVIEW_B1PLUS` | B1_PLUS | B2 preview form | present from R7-M15 | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 5 | `GRAMMAR_CONDITIONALS_UNLESS_AS_LONG_AS_B1PLUS` | B1_PLUS | advanced B1 control | present from R7-M15 | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 6 | `GRAMMAR_PRESENT_PERFECT_SIMPLE_CONTINUOUS_CONTRAST_B1PLUS` | B1_PLUS | advanced B1 control | present from R7-M15 | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 7 | `GRAMMAR_FUTURE_CONTINUOUS_PREVIEW_B1PLUS` | B1_PLUS | B2 preview form | present from R7-M15 | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |

## 5. Deferred Item Confirmation

```text
GRAMMAR_SECOND_CONDITIONAL_EXPANDED_B1PLUS = DEFERRED_BY_PACKAGE_A
```

This item must not be added to the next B1_PLUS node batch.

## 6. Readiness Summary

```text
accepted_package_a_candidates = 7
final_stage_b1plus = 7
concrete_source_ref_present = 7
candidate_only_safety_present = 7
implementation_proposal_ready = 7
deferred_by_package_a = 1
```

## 7. Implementation Readiness Decision

```text
R7-M18_IMPLEMENTATION_READINESS = READY_FOR_OPERATOR_APPROVED_B1PLUS_CANDIDATE_NODE_BATCH
```

This means the Package-A B1_PLUS surface is ready for a later implementation task proposal.

It does not authorize immediate implementation inside R7-M18.

## 8. Required Implementation Guardrails

A future implementation task may only proceed if explicitly approved as a candidate-node implementation batch.

Required guardrails for that future task:

```text
- modify grammar_nodes.json only, unless derived sync is explicitly approved in the same task
- add exactly the 7 Package-A B1_PLUS candidate nodes, unless the implementation task explicitly narrows the count
- do not add GRAMMAR_SECOND_CONDITIONAL_EXPANDED_B1PLUS
- authority_status = candidate
- introduced_stage = B1_PLUS
- confidence = operator_review_required
- traceability.generated_content=false
- traceability.learner_state_write=false
- no grammar_edges.json modifications in the same node batch unless separately scoped
- no accepted authority promotion
- no learner-facing generation
```

## 9. Gate & Distance Update

```text
[PASS] R7-M18 remains checklist-only.
[PASS] 7 Package-A B1_PLUS candidates are implementation-proposal ready.
[PASS] 1 weak-stage proposal remains deferred.
[PASS] No grammar_nodes.json changes.
[PASS] No grammar_edges.json changes.
[PASS] No derived artifact rebuild.
[PASS] No validation report refresh.
[PASS] No CI test change.
[PASS] No learner-facing practice generated.
[PASS] No learner state write path introduced.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

## 10. Stop / Resume Handoff

Because the next logical task crosses from checklist into source-artifact implementation, automatic progression must stop after R7-M18 merge unless the operator explicitly approves candidate-node implementation.

```text
NEXT_SHORT_STEP:
R7-M19 B1_PLUS Mode-B Package-A candidate-node implementation batch

REQUIRED_OPERATOR_APPROVAL:
Approve R7-M19 as a candidate-node implementation batch that may modify grammar_nodes.json and, if needed for CI, sync derived artifacts / validation / CI expectations.
```
