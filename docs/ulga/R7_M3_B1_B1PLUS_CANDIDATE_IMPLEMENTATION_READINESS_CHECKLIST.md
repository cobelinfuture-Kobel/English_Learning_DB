# R7-M3 B1 / B1_PLUS Candidate Implementation Readiness Checklist

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M3 B1 / B1_PLUS candidate implementation readiness checklist

Branch:
codex/r7-m3-b1-b1plus-implementation-readiness

Status:
CHECKLIST_ONLY
```

R7-M3 checks whether the R7-M1 planning proposals plus R7-M2 evidence policy are sufficient to permit a later capped B1 / B1_PLUS candidate node implementation batch. This task does not modify `grammar_nodes.json`, `grammar_edges.json`, derived artifacts, validators, CI tests, learner-facing practice, or learner state.

## 2. Prior Inputs

R7-M1 proposed a planning-only surface:

```text
B1 proposed nodes = 6
B1_PLUS proposed nodes = 4
Total proposed planning surface = 10
```

R7-M2 defined the source-evidence policy and blocked implementation until evidence is attached.

## 3. Scope Lock

Allowed in R7-M3:

```text
- check whether R7-M1 proposals are implementation-ready
- check whether R7-M2 evidence policy is sufficient
- define a go / no-go decision for a future candidate node batch
- identify missing evidence and blockers
- produce a resumable next task
```

Forbidden in R7-M3:

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

## 5. Proposal Readiness Checklist

R7-M3 evaluates each R7-M1 proposal against the R7-M2 readiness gate.

Required before implementation:

```text
[ ] source_id exists
[ ] source_ref is non-empty
[ ] CEFR level evidence exists
[ ] source_role is schema-compatible
[ ] allowed_use includes level_alignment
[ ] allowed_use includes grammar_construct_reference
[ ] blocked_use includes learner_state_write
[ ] blocked_use includes automatic_promotion
[ ] authority_status will remain candidate
[ ] confidence remains operator_review_required unless normalized authority evidence is reviewed
[ ] traceability.generated_content=false
[ ] traceability.learner_state_write=false
```

## 6. Proposal-level Readiness Matrix

| Proposed grammar_id | Stage | Planning proposal exists | Evidence policy exists | Source evidence attached | Implementation decision |
|---|---:|---:|---:|---:|---|
| `GRAMMAR_PRESENT_PERFECT_EXPERIENCE_BASIC` | B1 | yes | yes | no | NOT_READY |
| `GRAMMAR_PRESENT_PERFECT_RESULT_BASIC` | B1 | yes | yes | no | NOT_READY |
| `GRAMMAR_PAST_CONTINUOUS_BASIC` | B1 | yes | yes | no | NOT_READY |
| `GRAMMAR_FIRST_CONDITIONAL_BASIC` | B1 | yes | yes | no | NOT_READY |
| `GRAMMAR_RELATIVE_CLAUSES_BASIC` | B1 | yes | yes | no | NOT_READY |
| `GRAMMAR_PASSIVE_PRESENT_PAST_BASIC` | B1 | yes | yes | no | NOT_READY |
| `GRAMMAR_REPORTED_SPEECH_BASIC` | B1_PLUS | yes | yes | no | NOT_READY |
| `GRAMMAR_SECOND_CONDITIONAL_BASIC` | B1_PLUS | yes | yes | no | NOT_READY |
| `GRAMMAR_MODAL_DEDUCTION_BASIC` | B1_PLUS | yes | yes | no | NOT_READY |
| `GRAMMAR_PRESENT_PERFECT_CONTINUOUS_BASIC` | B1_PLUS | yes | yes | no | NOT_READY |

## 7. Implementation Decision

```text
R7-M3_IMPLEMENTATION_DECISION = NOT_READY
```

Reason:

```text
R7-M1 provides a capped planning surface.
R7-M2 provides a source-evidence policy.
However, no proposal-level evidence attachment exists yet.
Therefore a source-artifact implementation batch is still blocked.
```

## 8. Minimum Work Needed Before Implementation

A later task must attach evidence to each proposed node before implementation can start.

Minimum next evidence artifact should include:

```text
- proposed grammar_id
- selected source class: CLASS-A or CLASS-B, with CLASS-C as secondary support
- source_id
- source_role
- source_ref
- CEFR level evidence
- allowed_use values
- blocked_use values
- confidence
- implementation_readiness flag
```

## 9. Candidate Batch Cap For Later Implementation

R7-M3 preserves the R7-M0 / R7-M1 cap:

```text
Single future implementation batch cap: 5 to 12 nodes
Current R7-M1 planning proposals: 10 nodes
Allowed future implementation mode: candidate-only node batch after evidence attachment
Forbidden future implementation mode: accepted authority promotion or learner-facing generation
```

## 10. Edge Planning Boundary

No B1 / B1_PLUS edge implementation is allowed before candidate node evidence is attached.

Future sequence must be:

```text
1. attach source evidence to R7-M1 proposals
2. approve capped candidate node implementation batch
3. add candidate nodes only
4. add matching candidate edges only
5. rebuild derived artifacts
6. refresh validation report and CI-safe tests
7. run CI
8. keep all records candidate until separate promotion audit
```

## 11. Risk Register

```text
RISK-1: Implementation before evidence attachment
Status: OPEN
Impact: High
Control: R7-M3 explicitly marks implementation as NOT_READY.

RISK-2: B1_PLUS undercoverage
Status: OPEN
Impact: Low / Medium
Control: implementation can start with the capped 10 proposals only after evidence; later extension remains separate.

RISK-3: Candidate / accepted confusion
Status: OPEN
Impact: Medium
Control: implementation must keep authority_status=candidate.

RISK-4: edge dependency mismatch
Status: OPEN
Impact: Medium
Control: edges must be planned after node evidence and must resolve against existing grammar IDs.
```

## 12. Gate & Distance Update

```text
[PASS] R7-M3 remains checklist-only.
[PASS] No grammar_nodes.json changes.
[PASS] No grammar_edges.json changes.
[PASS] No derived artifact rebuild.
[PASS] No validation report refresh.
[PASS] No CI test change.
[PASS] No learner-facing practice generated.
[PASS] No learner state write path introduced.
[PASS] R7-M1 proposals are confirmed planning-only.
[PASS] R7-M2 evidence policy is sufficient as a policy layer.
[BLOCKED] Candidate node implementation is not ready because proposal-level evidence is not attached.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

## 13. Next Shortest Step

```text
NEXT_SHORT_STEP:
R7-M4 B1 / B1_PLUS proposal-level source evidence attachment plan
```

R7-M4 must remain evidence-planning only. It should define the evidence attachment table for the 10 R7-M1 proposals, but it must not modify `grammar_nodes.json` or `grammar_edges.json`.
