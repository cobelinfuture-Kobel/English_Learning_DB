# R7-M23 B2 Candidate-only Planning Readiness Scan

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M23 B2 candidate-only planning readiness scan

Branch:
codex/r7-m23-b2-readiness

Status:
READINESS_SCAN_ONLY
```

R7-M23 scans whether the B2 candidate-only line can start after the corrected B1 graph and the B1_PLUS Mode-B Package-A graph were closed as static-candidate-ready.

## 2. Prior Closed Lines

```text
R7_CORRECTED_B1_GRAPH_LINE = CLOSED_AS_STATIC_CANDIDATE_GRAPH_READY
R7_B1PLUS_MODE_B_PACKAGE_A_GRAPH_LINE = CLOSED_AS_STATIC_CANDIDATE_GRAPH_READY
node_count = 39
edge_count = 52
fail_count = 0
```

## 3. Scope Lock

Allowed in R7-M23:

```text
- check whether B2 candidate-only planning can begin
- define B2 planning boundaries
- preserve candidate-only / source-ref-first policy
- produce next planning-surface step
```

Forbidden in R7-M23:

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

## 4. Readiness Finding

```text
B2_CANDIDATE_ONLY_PLANNING_READINESS = READY_FOR_PLANNING_SURFACE
```

Reason:

```text
B1 and B1_PLUS static candidate graph lines are closed and CI-synced. B2 may now start as a separate candidate-only planning line, provided it remains source-ref-first and does not promote authority or generate learner-facing practice.
```

## 5. B2 Planning Boundary

B2 candidate planning must satisfy:

```text
- introduced_stage = B2 in future implementation, not during this scan
- authority_status = candidate in future implementation
- source evidence must be concrete EGP or normalized authority reference
- no automatic promotion from B1_PLUS
- no learner-facing generation
- no learner state write
- no accepted authority promotion
```

## 6. Recommended Next Planning Surface

R7-M24 should define a capped B2 candidate surface. It should prefer high-signal B2 grammar constructs that extend the now-closed B1 / B1_PLUS graph:

```text
- advanced passive / passive reporting
- mixed or advanced conditionals
- complex relative clause control
- advanced modal speculation
- discourse-oriented inversion / emphasis where supported
- future perfect / future continuous contrast where supported
- advanced reported speech forms
- complex aspect contrasts
```

## 7. Implementation Decision

```text
R7-M23_IMPLEMENTATION_DECISION = NOT_READY_PLANNING_SURFACE_REQUIRED
```

Reason:

```text
B2 planning can begin, but no capped B2 candidate surface has been defined yet.
```

## 8. Gate & Distance Update

```text
[PASS] R7-M23 remains readiness-only.
[PASS] B1 static candidate graph is closed.
[PASS] B1_PLUS Package-A static candidate graph is closed.
[PASS] B2 candidate-only planning may begin.
[PASS] No grammar source artifact modified.
[PASS] No derived artifact rebuilt.
[PASS] No CI expectation changed.
[PASS] No learner-facing practice generated.
[PASS] No learner state write path introduced.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

## 9. Next Shortest Step

```text
NEXT_SHORT_STEP:
R7-M24 B2 candidate-only planning surface definition
```

R7-M24 must remain planning-only. It should propose a capped B2 candidate surface and must not modify `grammar_nodes.json` or `grammar_edges.json`.
