# R7-M17 B1_PLUS Mode-B Implementation Readiness Checklist

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M17 B1_PLUS Mode-B implementation readiness checklist

Branch:
codex/r7-m17-b1p-readiness

Status:
CHECKLIST_ONLY
```

R7-M17 verifies whether the corrected 8-row B1_PLUS Mode-B surface from R7-M16 is ready for a later operator-approved candidate-node implementation batch.

## 2. Prior Gate From R7-M16

```text
corrected_b1plus_candidates = 8
ready_for_readiness_check = 8
implementation_ready = 0
```

R7-M16 explicitly did not approve implementation.

## 3. Scope Lock

Allowed in R7-M17:

```text
- verify corrected B1_PLUS proposal completeness
- verify source_ref coverage
- verify Mode-B bridge policy compliance
- verify candidate-only safety requirements
- decide whether a later implementation batch can be proposed
```

Forbidden in R7-M17:

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

## 4. Corrected B1_PLUS Readiness Matrix

| # | Corrected grammar_id | introduced_stage | source_ref present | Mode-B compliance | candidate-only safety | Readiness |
|---:|---|---:|---|---|---|---|
| 1 | `GRAMMAR_REPORTED_QUESTIONS_B1PLUS` | B1_PLUS | yes | pass | pass | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 2 | `GRAMMAR_REPORTED_REQUESTS_COMMANDS_B1PLUS` | B1_PLUS | yes | pass with preview guard | pass | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 3 | `GRAMMAR_CONDITIONAL_VARIATION_B1PLUS` | B1_PLUS | yes | pass | pass | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 4 | `GRAMMAR_THIRD_CONDITIONAL_PREVIEW_B1PLUS` | B1_PLUS | yes | pass with preview guard | pass | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 5 | `GRAMMAR_PASSIVE_RELATIVE_BY_PHRASE_B1PLUS` | B1_PLUS | yes | pass | pass | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 6 | `GRAMMAR_RELATIVE_CLAUSES_OBJECT_WHOSE_B1PLUS` | B1_PLUS | yes | pass with preview guard | pass | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 7 | `GRAMMAR_MODAL_CERTAINTY_POSSIBILITY_B1PLUS` | B1_PLUS | yes | pass with preview guard | pass | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 8 | `GRAMMAR_PERFECT_ASPECT_CONTRAST_B1PLUS` | B1_PLUS | yes | pass | pass | READY_FOR_IMPLEMENTATION_PROPOSAL |

## 5. Readiness Summary

```text
corrected_b1plus_proposals = 8
source_ref_present = 8
mode_b_compliant = 8
candidate_only_safety_present = 8
implementation_proposal_ready = 8
b2_implementation_ready = 0
```

## 6. Implementation Readiness Decision

```text
R7-M17_IMPLEMENTATION_READINESS = READY_FOR_OPERATOR_APPROVED_B1PLUS_CANDIDATE_NODE_BATCH
```

This means the corrected B1_PLUS Mode-B surface is ready for a later implementation task proposal.

It does not authorize immediate implementation inside R7-M17.

## 7. Required Implementation Guardrails

A future implementation task may only proceed if explicitly approved as a candidate-node implementation batch.

Required guardrails:

```text
- modify grammar_nodes.json only, unless derived sync is separately approved in the same implementation route
- add exactly the 8 corrected B1_PLUS candidate nodes, unless the implementation task explicitly narrows the count
- introduced_stage = B1_PLUS
- authority_status = candidate
- confidence = operator_review_required
- traceability.generated_content = false
- traceability.learner_state_write = false
- no grammar_edges.json modifications in the same node batch unless separately approved
- no accepted authority promotion
- no learner-facing generation
- B2 evidence may be preview support only, not B2 mastery
```

## 8. Gate & Distance Update

```text
[PASS] R7-M17 remains checklist-only.
[PASS] Corrected B1_PLUS proposal count is 8.
[PASS] All 8 corrected B1_PLUS proposals have source_ref evidence.
[PASS] All 8 corrected B1_PLUS proposals comply with Mode-B bridge policy.
[PASS] All 8 corrected B1_PLUS proposals remain candidate-only.
[PASS] B2 implementation remains out of scope.
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

## 9. Stop / Resume Handoff

Because the next logical task crosses from planning/checklist into source-artifact implementation, automatic progression must stop after R7-M17 merge unless the operator explicitly approves candidate-node implementation.

```text
NEXT_SHORT_STEP:
R7-M18 B1_PLUS Mode-B candidate-node implementation batch

REQUIRED_OPERATOR_APPROVAL:
Approve R7-M18 as a candidate-node implementation batch that may modify grammar_nodes.json and, if CI requires it, sync derived artifacts / validation / CI expectations.
```
