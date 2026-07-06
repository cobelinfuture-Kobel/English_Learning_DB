# R7-M4 B1 / B1_PLUS Proposal-level Source Evidence Attachment Plan

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M4 B1 / B1_PLUS proposal-level source evidence attachment plan

Branch:
codex/r7-m4-b1-b1plus-evidence-attachment-plan

Status:
EVIDENCE_ATTACHMENT_PLAN_ONLY
```

R7-M4 defines the proposal-level evidence attachment table for the 10 R7-M1 B1 / B1_PLUS planning proposals. This task does not modify `grammar_nodes.json`, `grammar_edges.json`, derived artifacts, validators, CI tests, learner-facing practice, or learner state.

## 2. Prior Inputs

R7-M3 marked candidate implementation as not ready because proposal-level source evidence had not been attached.

```text
R7-M3_IMPLEMENTATION_DECISION = NOT_READY
```

R7-M3 also required the next evidence artifact to include:

```text
- proposed grammar_id
- selected source class
- source_id
- source_role
- source_ref
- CEFR level evidence
- allowed_use values
- blocked_use values
- confidence
- implementation_readiness flag
```

R7-M2 defines the allowed evidence classes:

```text
CLASS-A: External authority source
CLASS-B: Project-normalized authority artifact
CLASS-C: Operator planning document
CLASS-D: Learner-facing source
```

## 3. Scope Lock

Allowed in R7-M4:

```text
- create proposal-level evidence attachment table
- assign planned source class per proposal
- assign planned source_id / source_role placeholders
- define concrete fields required before implementation
- preserve NOT_READY status until actual source_ref evidence is reviewed
- produce a resumable next task
```

Forbidden in R7-M4:

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

## 4. Current Baseline To Protect

Current static grammar artifact baseline remains unchanged:

```text
status = PASS
node_count = 22
edge_count = 22
order_row_count = 22
coverage_node_count = 22
query_node_count = 22
check_count = 22
fail_count = 0
```

Current authority split remains unchanged:

```text
accepted = 5
candidate = 17
```

## 5. Evidence Attachment Table

This table is an attachment plan only. `source_ref` remains `TBD_AUTHORITY_ROW_OR_KEY` until a later task maps each proposal to concrete authority evidence.

| Proposed grammar_id | Stage | Selected source class | Planned source_id | Planned source_role | Planned source_ref | CEFR evidence | allowed_use | blocked_use | confidence | implementation_readiness |
|---|---:|---|---|---|---|---|---|---|---|---|
| `GRAMMAR_PRESENT_PERFECT_EXPERIENCE_BASIC` | B1 | CLASS-A or CLASS-B | `EGP_SOURCE_XLSX` or normalized artifact id | `authority_source` or `normalized_authority_artifact` | `TBD_AUTHORITY_ROW_OR_KEY` | B1 evidence required | `level_alignment`, `grammar_construct_reference` | `learner_state_write`, `automatic_promotion` | `operator_review_required` | NOT_READY |
| `GRAMMAR_PRESENT_PERFECT_RESULT_BASIC` | B1 | CLASS-A or CLASS-B | `EGP_SOURCE_XLSX` or normalized artifact id | `authority_source` or `normalized_authority_artifact` | `TBD_AUTHORITY_ROW_OR_KEY` | B1 evidence required | `level_alignment`, `grammar_construct_reference` | `learner_state_write`, `automatic_promotion` | `operator_review_required` | NOT_READY |
| `GRAMMAR_PAST_CONTINUOUS_BASIC` | B1 | CLASS-A or CLASS-B | `EGP_SOURCE_XLSX` or normalized artifact id | `authority_source` or `normalized_authority_artifact` | `TBD_AUTHORITY_ROW_OR_KEY` | B1 evidence required | `level_alignment`, `grammar_construct_reference` | `learner_state_write`, `automatic_promotion` | `operator_review_required` | NOT_READY |
| `GRAMMAR_FIRST_CONDITIONAL_BASIC` | B1 | CLASS-A or CLASS-B | `EGP_SOURCE_XLSX` or normalized artifact id | `authority_source` or `normalized_authority_artifact` | `TBD_AUTHORITY_ROW_OR_KEY` | B1 evidence required | `level_alignment`, `grammar_construct_reference` | `learner_state_write`, `automatic_promotion` | `operator_review_required` | NOT_READY |
| `GRAMMAR_RELATIVE_CLAUSES_BASIC` | B1 | CLASS-A or CLASS-B | `EGP_SOURCE_XLSX` or normalized artifact id | `authority_source` or `normalized_authority_artifact` | `TBD_AUTHORITY_ROW_OR_KEY` | B1 evidence required | `level_alignment`, `grammar_construct_reference` | `learner_state_write`, `automatic_promotion` | `operator_review_required` | NOT_READY |
| `GRAMMAR_PASSIVE_PRESENT_PAST_BASIC` | B1 | CLASS-A or CLASS-B | `EGP_SOURCE_XLSX` or normalized artifact id | `authority_source` or `normalized_authority_artifact` | `TBD_AUTHORITY_ROW_OR_KEY` | B1 evidence required | `level_alignment`, `grammar_construct_reference` | `learner_state_write`, `automatic_promotion` | `operator_review_required` | NOT_READY |
| `GRAMMAR_REPORTED_SPEECH_BASIC` | B1_PLUS | CLASS-A or CLASS-B | `EGP_SOURCE_XLSX` or normalized artifact id | `authority_source` or `normalized_authority_artifact` | `TBD_AUTHORITY_ROW_OR_KEY` | B1_PLUS evidence required | `level_alignment`, `grammar_construct_reference` | `learner_state_write`, `automatic_promotion` | `operator_review_required` | NOT_READY |
| `GRAMMAR_SECOND_CONDITIONAL_BASIC` | B1_PLUS | CLASS-A or CLASS-B | `EGP_SOURCE_XLSX` or normalized artifact id | `authority_source` or `normalized_authority_artifact` | `TBD_AUTHORITY_ROW_OR_KEY` | B1_PLUS evidence required | `level_alignment`, `grammar_construct_reference` | `learner_state_write`, `automatic_promotion` | `operator_review_required` | NOT_READY |
| `GRAMMAR_MODAL_DEDUCTION_BASIC` | B1_PLUS | CLASS-A or CLASS-B | `EGP_SOURCE_XLSX` or normalized artifact id | `authority_source` or `normalized_authority_artifact` | `TBD_AUTHORITY_ROW_OR_KEY` | B1_PLUS evidence required | `level_alignment`, `grammar_construct_reference` | `learner_state_write`, `automatic_promotion` | `operator_review_required` | NOT_READY |
| `GRAMMAR_PRESENT_PERFECT_CONTINUOUS_BASIC` | B1_PLUS | CLASS-A or CLASS-B | `EGP_SOURCE_XLSX` or normalized artifact id | `authority_source` or `normalized_authority_artifact` | `TBD_AUTHORITY_ROW_OR_KEY` | B1_PLUS evidence required | `level_alignment`, `grammar_construct_reference` | `learner_state_write`, `automatic_promotion` | `operator_review_required` | NOT_READY |

## 6. Evidence Attachment Status

```text
proposal_count = 10
planned_attachment_rows = 10
concrete_source_ref_attached = 0
implementation_ready_rows = 0
```

R7-M4 intentionally does not claim that source evidence is attached. It only defines the attachment plan and field requirements.

## 7. Required Next Verification Before Implementation

A later task must replace each `TBD_AUTHORITY_ROW_OR_KEY` with a concrete source reference.

Required concrete verification:

```text
[ ] source_id resolves to a registered source or normalized artifact.
[ ] source_role is schema-compatible.
[ ] source_ref points to a concrete row, key, section, or artifact record.
[ ] CEFR level evidence matches the tentative stage.
[ ] allowed_use includes level_alignment.
[ ] allowed_use includes grammar_construct_reference.
[ ] blocked_use includes learner_state_write.
[ ] blocked_use includes automatic_promotion.
[ ] confidence remains operator_review_required unless evidence is normalized and reviewed.
```

## 8. Implementation Decision

```text
R7-M4_IMPLEMENTATION_DECISION = NOT_READY
```

Reason:

```text
The attachment table is defined, but concrete proposal-level source_ref values are not attached yet. Candidate node implementation remains blocked until concrete evidence verification passes.
```

## 9. Future Candidate Node Batch Boundary

After concrete source evidence is verified, a future implementation batch may add candidate nodes only.

Allowed future batch after verification:

```text
- add up to the 10 R7-M1 B1 / B1_PLUS candidate nodes
- authority_status must remain candidate
- confidence must remain operator_review_required unless normalized authority evidence is reviewed
- traceability.generated_content=false
- traceability.learner_state_write=false
```

Still forbidden:

```text
- accepted authority promotion
- learner-facing practice generation
- learner state write
- B2 implementation
- edge implementation before candidate nodes exist
```

## 10. Risk Register

```text
RISK-1: Placeholder evidence mistaken as attached evidence
Status: OPEN
Impact: High
Control: all rows explicitly remain NOT_READY until concrete source_ref is attached.

RISK-2: EGP row/key mismatch
Status: OPEN
Impact: Medium
Control: next task must verify each row/key against actual authority evidence.

RISK-3: normalized artifact absence
Status: OPEN
Impact: Medium
Control: CLASS-A external authority may be used initially; CLASS-B preferred after normalization.

RISK-4: premature node implementation
Status: OPEN
Impact: High
Control: R7-M4 keeps implementation blocked.
```

## 11. Gate & Distance Update

```text
[PASS] R7-M4 remains evidence-planning only.
[PASS] 10 proposal-level evidence attachment rows defined.
[PASS] No grammar_nodes.json changes.
[PASS] No grammar_edges.json changes.
[PASS] No derived artifact rebuild.
[PASS] No validation report refresh.
[PASS] No CI test change.
[PASS] No learner-facing practice generated.
[PASS] No learner state write path introduced.
[BLOCKED] Candidate node implementation remains not ready because concrete source_ref values are not attached.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

## 12. Next Shortest Step

```text
NEXT_SHORT_STEP:
R7-M5 B1 / B1_PLUS concrete source-ref verification scan
```

R7-M5 must remain evidence-verification only. It should map each R7-M4 row to concrete source_ref values where possible, but it must not modify `grammar_nodes.json` or `grammar_edges.json`.
