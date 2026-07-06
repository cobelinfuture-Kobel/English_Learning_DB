# R7-M0 B1 / B2 Candidate-only Planning Readiness Scan

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M0 B1 / B2 candidate-only planning readiness scan

Branch:
codex/r7-m0-b1-b2-candidate-planning-scan

Status:
PLANNING_READINESS_SCAN_ONLY
```

R7-M0 starts the next controlled planning line after R6-M11. This task defines the B1 / B1_PLUS / B2 planning boundary, evidence requirements, batch caps, and promotion rules. It does not add B1 / B2 grammar nodes or edges.

## 2. Prior Gate From R6-M11

R6-M11 closed the current A1 / A1_PLUS and A2 / A2_PLUS line as a static candidate graph and explicitly blocked direct B1 / B2 source-artifact expansion.

```text
R6_A1_A2_EXPANSION_LINE = CLOSED_AS_STATIC_CANDIDATE_GRAPH_READY
R6_B1_B2_EXPANSION = NOT_STARTED
R6_B1_B2_NEXT_ALLOWED_MODE = CANDIDATE_ONLY_PLANNING
```

R7-M0 therefore inherits the following constraints:

```text
B1 / B1_PLUS / B2 direct source-artifact expansion: NOT_ALLOWED
B1 / B1_PLUS / B2 bulk implementation: NOT_ALLOWED
B1 / B1_PLUS / B2 candidate-only planning scan: ALLOWED
B1 / B1_PLUS / B2 source-evidence selection policy: ALLOWED
B1 / B1_PLUS / B2 implementation batch: requires separate approved policy and cap
```

## 3. Scope Lock

Allowed in R7-M0:

```text
- define B1 / B1_PLUS / B2 planning boundary
- define evidence requirements
- define batch caps for future candidate batches
- define promotion rules
- identify risks and blockers
- produce a resumable next task
```

Forbidden in R7-M0:

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

## 4. Current Baseline To Protect

Current static grammar artifact baseline remains:

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

Current authority split remains:

```text
accepted = 5
candidate = 17
```

R7-M0 must not disturb this baseline.

## 5. B1 / B2 Candidate Planning Boundary

B1 / B1_PLUS / B2 can be planned as future candidate records only.

```text
Allowed future record status:
- candidate

Disallowed future record status without separate promotion audit:
- accepted
- deprecated
- blocked as a substitute for evidence review
```

Candidate planning can define likely grammar surfaces, but cannot write them into `grammar_nodes.json` or `grammar_edges.json` until a later approved implementation batch.

## 6. Evidence Requirements For Future B1 / B2 Candidate Records

Every future B1 / B2 candidate node must have:

```text
- grammar_id proposal
- label proposal
- category proposal
- CEFR / EGP or normalized-authority evidence pointer
- proposed introduced_stage
- proposed stage_roles for A1 through B2
- source_evidence with non-empty source_ref
- confidence = operator_review_required unless normalized authority evidence is explicit
- traceability.generated_content = false
- traceability.learner_state_write = false
```

Every future B1 / B2 candidate edge must have:

```text
- edge_id proposal
- source grammar_id
- target grammar_id
- relation proposal
- direction proposal
- rationale
- source_evidence with non-empty source_ref
- confidence = operator_review_required unless normalized authority evidence is explicit
- traceability.generated_content = false
- traceability.learner_state_write = false
```

## 7. Future Batch Caps

R7-M0 recommends small future planning batches only:

```text
B1 candidate planning surface: 5 to 10 proposed nodes
B1_PLUS candidate planning surface: 5 to 10 proposed nodes
B2 candidate planning surface: 5 to 10 proposed nodes
Single implementation batch cap after approval: 5 to 12 nodes
Single edge batch cap after approval: enough edges to connect each new node, recommended cap 20
```

Bulk A1-B2 completion remains forbidden.

## 8. Promotion Rules

B1 / B2 candidate records may not become accepted authority unless a later promotion task proves:

```text
- source evidence is authority_source or normalized_authority_artifact
- candidate record has no unresolved schema conflict
- dependency edges resolve
- stage role is consistent with R6/R7 ordering policy
- validation report passes after rebuild
- CI-safe pytest passes
- no learner-facing practice uses the record before promotion
```

Promotion task must be separate from candidate planning and separate from source-artifact implementation.

## 9. Risk Register

```text
RISK-1: B1/B2 breadth explosion
Status: OPEN
Impact: High
Control: planning-only first; batch caps required before implementation.

RISK-2: candidate authority confusion
Status: OPEN
Impact: Medium
Control: candidate records cannot be treated as accepted authority.

RISK-3: compact derived artifacts
Status: OPEN
Impact: Low / Medium
Control: define query-index consumer contract before learner-facing use.

RISK-4: premature learner-facing generation
Status: OPEN
Impact: High
Control: no practice generation until candidate/authority and consumer contracts are explicitly approved.
```

## 10. Gate & Distance Update

```text
[PASS] R7-M0 stays planning-only.
[PASS] No B1 / B2 nodes are added.
[PASS] No B1 / B2 edges are added.
[PASS] Current 22-node / 22-edge baseline is protected.
[PASS] Future B1 / B2 work is restricted to candidate-only planning first.
[PASS] Batch caps are defined.
[PASS] Promotion rules are separated from planning and implementation.
[PASS] learner_state_write=false remains required.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

## 11. Next Shortest Step

```text
NEXT_SHORT_STEP:
R7-M1 B1 / B1_PLUS candidate planning surface definition
```

R7-M1 must remain planning-only. It may propose a small B1 / B1_PLUS candidate surface, but it must not modify `grammar_nodes.json` or `grammar_edges.json`.
