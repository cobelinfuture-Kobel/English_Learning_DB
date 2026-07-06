# R7-M28 B2 Package-A Candidate-node Readiness Checklist

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M28 B2 Package-A candidate-node readiness checklist

Branch:
codex/r7-m28-b2-readiness

Status:
CHECKLIST_ONLY
```

R7-M28 verifies whether the 7 Package-A accepted B2 candidates are ready for a later operator-approved candidate-node implementation batch. This task does not modify `grammar_nodes.json`, `grammar_edges.json`, derived artifacts, validators, CI tests, learner-facing practice, or learner state.

## 2. Prior Gate From R7-M27

```text
SELECTED_PACKAGE = PACKAGE-A
accepted_for_readiness_review = 7
deferred = 1
R7-M27_IMPLEMENTATION_DECISION = NOT_READY_READINESS_CHECK_REQUIRED
```

Deferred proposal:

```text
GRAMMAR_MIXED_CONDITIONALS_B2
```

## 3. Scope Lock

Allowed in R7-M28:

```text
- verify the 7 accepted B2 candidates against implementation prerequisites
- preserve Package-A deferral for mixed conditionals
- decide whether an operator-approved candidate-node implementation batch can be proposed
- produce a stop / resume handoff if implementation is the next step
```

Forbidden in R7-M28:

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

## 4. Candidate Readiness Matrix

| # | Proposed grammar_id | Final stage | Concrete source_ref status | Candidate-only safety | Readiness |
|---:|---|---:|---|---|---|
| 1 | `GRAMMAR_PASSIVE_REPORTING_STRUCTURES_B2` | B2 | present from R7-M25 | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 2 | `GRAMMAR_ADVANCED_MODAL_SPECULATION_B2` | B2 | present from R7-M25 | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 3 | `GRAMMAR_RELATIVE_CLAUSES_PREPOSITION_WHOSE_B2` | B2 | present from R7-M25 | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 4 | `GRAMMAR_FUTURE_PERFECT_B2` | B2 | present from R7-M25 | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 5 | `GRAMMAR_REPORTED_SPEECH_ADVANCED_B2` | B2 | present from R7-M25 | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 6 | `GRAMMAR_PERFECT_CONTINUOUS_ADVANCED_CONTRAST_B2` | B2 | present from R7-M25 | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 7 | `GRAMMAR_INVERSION_NEGATIVE_ADVERBIALS_B2` | B2 | present from R7-M25 | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |

## 5. Deferred Item Confirmation

```text
GRAMMAR_MIXED_CONDITIONALS_B2 = DEFERRED_BY_PACKAGE_A
```

This item must not be added to the next B2 node batch.

## 6. Readiness Summary

```text
accepted_package_a_candidates = 7
final_stage_b2 = 7
concrete_source_ref_present = 7
candidate_only_safety_present = 7
implementation_proposal_ready = 7
deferred_by_package_a = 1
```

## 7. Implementation Readiness Decision

```text
R7-M28_IMPLEMENTATION_READINESS = READY_FOR_OPERATOR_APPROVED_B2_CANDIDATE_NODE_BATCH
```

This means the Package-A B2 surface is ready for a later implementation task proposal.

It does not authorize immediate implementation inside R7-M28.

## 8. Required Implementation Guardrails

A future implementation task may only proceed if explicitly approved as a candidate-node implementation batch.

Required guardrails for that future task:

```text
- modify grammar_nodes.json only, unless derived sync is explicitly approved in the same task
- add exactly the 7 Package-A B2 candidate nodes, unless the implementation task explicitly narrows the count
- do not add GRAMMAR_MIXED_CONDITIONALS_B2
- authority_status = candidate
- introduced_stage = B2
- confidence = operator_review_required
- traceability.generated_content=false
- traceability.learner_state_write=false
- no grammar_edges.json modifications in the same node batch unless separately scoped
- no accepted authority promotion
- no learner-facing generation
```

## 9. Gate & Distance Update

```text
[PASS] R7-M28 remains checklist-only.
[PASS] 7 Package-A B2 candidates are implementation-proposal ready.
[PASS] 1 weak/indirect proposal remains deferred.
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

Because the next logical task crosses from checklist into source-artifact implementation, automatic progression must stop after R7-M28 merge unless the operator explicitly approves candidate-node implementation.

```text
NEXT_SHORT_STEP:
R7-M29 B2 Package-A candidate-node implementation batch

REQUIRED_OPERATOR_APPROVAL:
Approve R7-M29 as a candidate-node implementation batch that may modify grammar_nodes.json and, if needed for CI, sync derived artifacts / validation / CI expectations.
```
