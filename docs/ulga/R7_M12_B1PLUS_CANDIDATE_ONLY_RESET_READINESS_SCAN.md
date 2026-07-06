# R7-M12 B1_PLUS Candidate-only Reset Readiness Scan

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M12 B1_PLUS candidate-only reset readiness scan

Branch:
codex/r7-m12-b1plus-reset-scan

Status:
READINESS_SCAN_ONLY
```

R7-M12 scans whether the deferred B1_PLUS line can proceed after the corrected B1 graph was closed as static-candidate-ready.

## 2. Prior State

```text
R7_CORRECTED_B1_GRAPH_LINE = CLOSED_AS_STATIC_CANDIDATE_GRAPH_READY
node_count = 32
edge_count = 40
fail_count = 0
```

Earlier B1_PLUS proposals were not implemented because R7-M5 / R7-M6 showed that the proposed basic B1_PLUS items were actually B1 evidence or A2-backed basics.

## 3. Scope Lock

Allowed in R7-M12:

```text
- review B1_PLUS readiness boundary
- identify why B1_PLUS cannot reuse the old R7-M1 B1_PLUS labels directly
- define the operator choice needed before a B1_PLUS planning surface can be rebuilt
```

Forbidden in R7-M12:

```text
- no grammar_nodes.json modification
- no grammar_edges.json modification
- no derived artifact rebuild
- no validation report refresh
- no CI test change
- no learner-facing practice generation
- no learner state write
- no accepted authority promotion
- no B2 implementation
```

## 4. Readiness Finding

```text
B1_PLUS_IMPLEMENTATION_READINESS = NOT_READY
```

Reason:

```text
B1_PLUS does not currently have a distinct approved staging policy. The previous B1_PLUS labels were corrected down to B1 in R7-M6. Continuing automatically would risk inventing a B1_PLUS surface without a clear authority-stage rule.
```

## 5. Required Operator Choice

Before B1_PLUS planning can continue, the operator must choose one staging mode:

```text
MODE-A: B1_PLUS = deeper B1 consolidation
MODE-B: B1_PLUS = bridge from B1 to B2 preview
MODE-C: B1_PLUS = only EGP B2-backed early-preview items
MODE-D: defer B1_PLUS and begin B2 candidate-only planning scan instead
```

## 6. Stop Decision

```text
R7-M12_STOP_DECISION = HUMAN_STAGE_POLICY_REQUIRED
```

This is not a CI or implementation failure. It is a required source/stage policy decision before B1_PLUS evidence selection can proceed.

## 7. Gate & Distance Update

```text
[PASS] R7-M12 remains readiness-only.
[PASS] Corrected B1 graph remains closed as static-candidate-ready.
[PASS] B1_PLUS is not implemented.
[PASS] No grammar source artifact modified.
[PASS] No derived artifact rebuilt.
[PASS] No CI expectation changed.
[PASS] No learner-facing practice generated.
[PASS] No learner state write path introduced.
[BLOCKED] B1_PLUS requires operator-selected staging policy.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

## 8. Next Resume Task

```text
NEXT_RESUME_TASK:
R7-M13 B1_PLUS staging policy selection

REQUIRED_OPERATOR_ACTION:
Choose MODE-A, MODE-B, MODE-C, or MODE-D.
```
