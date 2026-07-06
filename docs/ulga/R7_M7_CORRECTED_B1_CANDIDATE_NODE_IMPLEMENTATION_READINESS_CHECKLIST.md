# R7-M7 Corrected B1 Candidate-node Implementation Readiness Checklist

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M7 corrected B1 candidate-node implementation readiness checklist

Branch:
codex/r7-m7-corrected-b1-readiness-checklist

Status:
CHECKLIST_ONLY
```

R7-M7 verifies whether the corrected B1-only surface from R7-M6 is ready for a later capped candidate-node implementation batch. This task does not modify `grammar_nodes.json`, `grammar_edges.json`, derived artifacts, validators, CI tests, learner-facing practice, or learner state.

## 2. Prior Gate From R7-M6

R7-M6 corrected the future implementation surface to B1-only:

```text
B1 corrected candidate proposals = 10
B1_PLUS corrected candidate proposals = 0
B2 proposals = 0
R7-M6_IMPLEMENTATION_DECISION = READY_FOR_B1_ONLY_READINESS_CHECK
```

R7-M6 explicitly stated this is not implementation approval. R7-M7 remains checklist-only.

## 3. Scope Lock

Allowed in R7-M7:

```text
- verify corrected B1 proposal completeness
- verify source_ref coverage
- verify candidate-only safety requirements
- decide whether a later implementation batch can be proposed
- produce a stop / resume handoff if implementation is the next step
```

Forbidden in R7-M7:

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

## 4. Corrected B1 Proposal Readiness Matrix

| # | Corrected grammar_id | Final stage | Final category | Concrete source_ref status | Candidate-only safety | Readiness |
|---:|---|---:|---|---|---|---|
| 1 | `GRAMMAR_PRESENT_PERFECT_UNIQUE_EXPERIENCE_B1` | B1 | `perfect_aspect` | `EGP_SOURCE_XLSX::Data!A935:H935::id=1741163713111x811420585366934300` | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 2 | `GRAMMAR_PRESENT_PERFECT_RESULT_BASIC` | B1 | `perfect_aspect` | `EGP_SOURCE_XLSX::Data!A930:H930::id=1741163713101x869805445646449900` | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 3 | `GRAMMAR_PAST_CONTINUOUS_REASON_REPEATED_B1` | B1 | `past_continuous` | `EGP_SOURCE_XLSX::Data!A851:H851::id=1741163712321x656261946310561000`; `EGP_SOURCE_XLSX::Data!A855:H855::id=1741163712327x699835533298048600` | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 4 | `GRAMMAR_FIRST_CONDITIONAL_BASIC` | B1 | `conditional` | `EGP_SOURCE_XLSX::Data!A261:H261::id=1741163715620x555336911205332160` | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 5 | `GRAMMAR_RELATIVE_CLAUSES_PLACE_TIME_OBJECT_B1` | B1 | `relative_clause` | `EGP_SOURCE_XLSX::Data!A230:H230::id=1741163708565x251895365489699360`; `EGP_SOURCE_XLSX::Data!A231:H231::id=1741163708565x386440393591908900`; `EGP_SOURCE_XLSX::Data!A236:H236::id=1741163708565x862760497502034200` | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 6 | `GRAMMAR_PASSIVE_PRESENT_PAST_EXPANDED_SUBJECTS_B1` | B1 | `passive` | `EGP_SOURCE_XLSX::Data!A809:H809::id=1741163712048x136041892375174060`; `EGP_SOURCE_XLSX::Data!A810:H810::id=1741163712048x581247857975133000` | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 7 | `GRAMMAR_REPORTED_SPEECH_BASIC` | B1 | `reported_speech` | `EGP_SOURCE_XLSX::Data!A1149:H1149::id=1741163715817x889153733096531600` | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 8 | `GRAMMAR_SECOND_CONDITIONAL_BASIC` | B1 | `conditional` | `EGP_SOURCE_XLSX::Data!A265:H265::id=1741163715621x282870273772287460` | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 9 | `GRAMMAR_MODAL_DEDUCTION_BASIC` | B1 | `modal` | `EGP_SOURCE_XLSX::Data!A590:H590::id=1741163710845x798749370290314700` | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |
| 10 | `GRAMMAR_PRESENT_PERFECT_CONTINUOUS_BASIC` | B1 | `perfect_aspect` | `EGP_SOURCE_XLSX::Data!A910:H910::id=1741163712744x249654248066045100`; `EGP_SOURCE_XLSX::Data!A911:H911::id=1741163712744x517808240803915500`; `EGP_SOURCE_XLSX::Data!A919:H919::id=1741163712747x851758421234194700` | candidate / no learner state | READY_FOR_IMPLEMENTATION_PROPOSAL |

## 5. Readiness Summary

```text
corrected_b1_proposals = 10
final_stage_b1 = 10
concrete_source_ref_present = 10
candidate_only_safety_present = 10
implementation_proposal_ready = 10
b1_plus_ready = 0
b2_ready = 0
```

## 6. Implementation Readiness Decision

```text
R7-M7_IMPLEMENTATION_READINESS = READY_FOR_OPERATOR_APPROVED_B1_CANDIDATE_NODE_BATCH
```

This means the corrected B1-only surface is ready for a later implementation task proposal.

It does not authorize immediate implementation inside R7-M7.

## 7. Required Implementation Guardrails

A future implementation task may only proceed if explicitly approved as a candidate-node implementation batch.

Required guardrails for that future task:

```text
- modify grammar_nodes.json only
- add exactly the 10 corrected B1 candidate nodes, unless the implementation task explicitly narrows the count
- authority_status = candidate
- confidence = operator_review_required
- traceability.generated_content=false
- traceability.learner_state_write=false
- no grammar_edges.json modifications in the same node batch
- no derived artifact rebuild in the same node batch unless separately scoped
- no accepted authority promotion
- no learner-facing generation
```

## 8. Gate & Distance Update

```text
[PASS] R7-M7 remains checklist-only.
[PASS] Corrected B1 proposal count is 10.
[PASS] All 10 corrected B1 proposals have concrete source_ref values.
[PASS] All 10 corrected B1 proposals remain candidate-only.
[PASS] B1_PLUS implementation remains deferred.
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

Because the next logical task crosses from planning/checklist into source-artifact implementation, automatic progression must stop after R7-M7 merge unless the operator explicitly approves candidate-node implementation.

```text
NEXT_SHORT_STEP:
R7-M8 corrected B1 candidate-node implementation batch

REQUIRED_OPERATOR_APPROVAL:
Approve R7-M8 as a candidate-node implementation batch that may modify grammar_nodes.json only.
```
