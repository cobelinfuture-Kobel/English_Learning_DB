# R7-M6 B1 / B1_PLUS Stage-alignment Correction Proposal

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M6 B1 / B1_PLUS stage-alignment correction proposal

Branch:
codex/r7-m6-b1-b1plus-stage-alignment-correction

Status:
STAGE_ALIGNMENT_PROPOSAL_ONLY
```

R7-M6 resolves the R7-M5 stage-drift finding at proposal level only. This task does not modify `grammar_nodes.json`, `grammar_edges.json`, derived artifacts, validators, CI tests, learner-facing practice, or learner state.

## 2. Prior Gate From R7-M5

R7-M5 found concrete EGP source references for all 10 R7-M1 proposals, but 8 of 10 proposal rows had stage drift.

```text
proposal_count = 10
concrete_source_ref_found = 10
exact_stage_match = 2
stage_drift = 8
implementation_ready_rows = 0
R7-M5_IMPLEMENTATION_DECISION = NOT_READY_STAGE_ALIGNMENT_REQUIRED
```

R7-M5 allowed four correction modes:

```text
MODE-A: adjust tentative stage to match EGP evidence
MODE-B: keep R7-M1 stage but attach a narrower B1/B1_PLUS supporting EGP row
MODE-C: split proposal into basic and expanded variants
MODE-D: defer proposal from implementation batch
```

## 3. Scope Lock

Allowed in R7-M6:

```text
- propose stage-alignment correction per drifted proposal
- preserve candidate-only boundary
- define corrected future implementation surface
- keep implementation blocked until a later readiness check
- produce a resumable next task
```

Forbidden in R7-M6:

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

## 4. Correction Decision Matrix

| Original proposal | R7-M1 stage | R7-M5 EGP level | Correction mode | Corrected implementation proposal | Corrected stage | Implementation note |
|---|---:|---:|---|---|---:|---|
| `GRAMMAR_PRESENT_PERFECT_EXPERIENCE_BASIC` | B1 | A2 | MODE-C | split: defer `BASIC_EXPERIENCE` to future A2 backfill; add `GRAMMAR_PRESENT_PERFECT_UNIQUE_EXPERIENCE_B1` using EGP row 935 | B1 | implement B1 expanded variant only |
| `GRAMMAR_PRESENT_PERFECT_RESULT_BASIC` | B1 | B1 | MATCH | keep `GRAMMAR_PRESENT_PERFECT_RESULT_BASIC` | B1 | eligible for later B1 readiness check |
| `GRAMMAR_PAST_CONTINUOUS_BASIC` | B1 | A2 | MODE-C | split: defer A2 affirmative basic; add `GRAMMAR_PAST_CONTINUOUS_REASON_REPEATED_B1` using EGP rows 851 / 855 | B1 | implement B1 use-focused variant only |
| `GRAMMAR_FIRST_CONDITIONAL_BASIC` | B1 | B1 | MATCH | keep `GRAMMAR_FIRST_CONDITIONAL_BASIC` | B1 | eligible for later B1 readiness check |
| `GRAMMAR_RELATIVE_CLAUSES_BASIC` | B1 | A2 | MODE-C | split: defer A2 defining relative basics; add `GRAMMAR_RELATIVE_CLAUSES_PLACE_TIME_OBJECT_B1` using EGP rows 230 / 231 / 236 | B1 | implement B1 expanded relative-clause variant only |
| `GRAMMAR_PASSIVE_PRESENT_PAST_BASIC` | B1 | A2 | MODE-C | split: defer A2 singular present/past passive; add `GRAMMAR_PASSIVE_PRESENT_PAST_EXPANDED_SUBJECTS_B1` using EGP rows 809 / 810 | B1 | implement B1 expanded subject-range variant only |
| `GRAMMAR_REPORTED_SPEECH_BASIC` | B1_PLUS | B1 | MODE-A | adjust `GRAMMAR_REPORTED_SPEECH_BASIC` to B1 | B1 | B1_PLUS label was too high for basic reported speech |
| `GRAMMAR_SECOND_CONDITIONAL_BASIC` | B1_PLUS | B1 | MODE-A | adjust `GRAMMAR_SECOND_CONDITIONAL_BASIC` to B1 | B1 | B1_PLUS label was too high for basic second conditional |
| `GRAMMAR_MODAL_DEDUCTION_BASIC` | B1_PLUS | B1 | MODE-A | adjust `GRAMMAR_MODAL_DEDUCTION_BASIC` to B1 | B1 | B1_PLUS label was too high for basic modal deduction with `must` |
| `GRAMMAR_PRESENT_PERFECT_CONTINUOUS_BASIC` | B1_PLUS | B1 | MODE-A | adjust `GRAMMAR_PRESENT_PERFECT_CONTINUOUS_BASIC` to B1 | B1 | B1_PLUS label was too high for basic present perfect continuous |

## 5. Corrected Future B1 Implementation Surface

R7-M6 proposes that the next candidate-node implementation surface be B1-only, capped at 10 nodes.

```text
B1 corrected candidate proposals = 10
B1_PLUS corrected candidate proposals = 0
B2 proposals = 0
```

Corrected B1-only proposal IDs:

```text
1. GRAMMAR_PRESENT_PERFECT_UNIQUE_EXPERIENCE_B1
2. GRAMMAR_PRESENT_PERFECT_RESULT_BASIC
3. GRAMMAR_PAST_CONTINUOUS_REASON_REPEATED_B1
4. GRAMMAR_FIRST_CONDITIONAL_BASIC
5. GRAMMAR_RELATIVE_CLAUSES_PLACE_TIME_OBJECT_B1
6. GRAMMAR_PASSIVE_PRESENT_PAST_EXPANDED_SUBJECTS_B1
7. GRAMMAR_REPORTED_SPEECH_BASIC
8. GRAMMAR_SECOND_CONDITIONAL_BASIC
9. GRAMMAR_MODAL_DEDUCTION_BASIC
10. GRAMMAR_PRESENT_PERFECT_CONTINUOUS_BASIC
```

## 6. Deferred Items

The following basic A2-backed constructs must not be implemented inside the B1 / B1_PLUS batch:

```text
- GRAMMAR_PRESENT_PERFECT_EXPERIENCE_BASIC as A2 basic experience
- GRAMMAR_PAST_CONTINUOUS_BASIC as A2 affirmative basic
- GRAMMAR_RELATIVE_CLAUSES_BASIC as A2 defining relative basics
- GRAMMAR_PASSIVE_PRESENT_PAST_BASIC as A2 singular present/past passive
```

These can be handled later as an A2 backfill or separate stage-normalization task. They must not be inserted into R7 B1 implementation as if they were B1 evidence.

## 7. Implementation Decision

```text
R7-M6_IMPLEMENTATION_DECISION = READY_FOR_B1_ONLY_READINESS_CHECK
```

This is not implementation approval. It only means the corrected B1-only surface is coherent enough for a later readiness checklist.

Still blocked:

```text
candidate node implementation = NOT_STARTED
candidate edge implementation = NOT_STARTED
accepted authority promotion = NOT_ALLOWED
learner-facing practice = NOT_ALLOWED
learner_state_write = NOT_ALLOWED
```

## 8. Required Next Check Before Implementation

Before any `grammar_nodes.json` write, a later task must verify that each corrected B1 proposal has:

```text
[ ] final grammar_id
[ ] final label
[ ] final category
[ ] final introduced_stage = B1
[ ] concrete source_ref from R7-M5 or R7-M6 corrected source row
[ ] authority_status = candidate
[ ] confidence = operator_review_required
[ ] traceability.generated_content=false
[ ] traceability.learner_state_write=false
```

## 9. Gate & Distance Update

```text
[PASS] R7-M6 remains proposal-only.
[PASS] Stage drift is resolved at proposal level.
[PASS] Future implementation surface is corrected to B1-only.
[PASS] B1_PLUS implementation is deferred, not forced.
[PASS] A2-backed basics are not smuggled into B1 implementation.
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

## 10. Next Shortest Step

```text
NEXT_SHORT_STEP:
R7-M7 corrected B1 candidate-node implementation readiness checklist
```

R7-M7 must remain checklist-only. It should verify whether the corrected B1-only surface is ready for a later capped candidate-node implementation batch. It must not modify `grammar_nodes.json` or `grammar_edges.json`.
