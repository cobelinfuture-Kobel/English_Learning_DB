# R7-M29 B2 Package-A Candidate-node Implementation Batch

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M29 B2 Package-A candidate-node implementation batch

Status:
IMPLEMENTATION_BATCH_WITH_VALIDATION_SYNC
```

R7-M29 implements the operator-approved Package-A B2 candidate-node batch from the R7-M28 readiness checklist and keeps all records candidate-only.

## 2. Implemented Candidate Nodes

R7-M29 adds these 7 B2 Package-A candidate nodes:

```text
1. GRAMMAR_PASSIVE_REPORTING_STRUCTURES_B2
2. GRAMMAR_ADVANCED_MODAL_SPECULATION_B2
3. GRAMMAR_RELATIVE_CLAUSES_PREPOSITION_WHOSE_B2
4. GRAMMAR_FUTURE_PERFECT_B2
5. GRAMMAR_REPORTED_SPEECH_ADVANCED_B2
6. GRAMMAR_PERFECT_CONTINUOUS_ADVANCED_CONTRAST_B2
7. GRAMMAR_INVERSION_NEGATIVE_ADVERBIALS_B2
```

All 7 nodes use:

```text
authority_status = candidate
introduced_stage = B2
traceability.generated_content = false
traceability.learner_state_write = false
```

Deferred item preserved:

```text
GRAMMAR_MIXED_CONDITIONALS_B2
```

## 3. Scope Control

```text
No grammar_edges.json modification.
No accepted authority promotion.
No learner-facing practice generation.
No learner state write.
No learner-facing practice write path.
```

## 4. Synced Static Artifact Counts

```text
node_count = 46
edge_count = 52
order_row_count = 46
coverage_node_count = 46
query_node_count = 46
EXPECTED_NODE_COUNT = 46
EXPECTED_EDGE_COUNT = 52
```

Coverage / query sync:

```text
grammar_coverage_matrix.summary.authority_status_counts.accepted = 5
grammar_coverage_matrix.summary.authority_status_counts.candidate = 41
grammar_coverage_matrix.stage_matrix[B2].role_counts.focus = 7
grammar_coverage_matrix.stage_matrix[B2].role_counts.maintenance = 39
grammar_query_index.summary.category_count = 25
grammar_query_index.summary.authority_status_count = 2
```

## 5. Gate & Distance Update

```text
[PASS] 7 B2 Package-A candidate nodes added.
[PASS] All new nodes remain candidate-only.
[PASS] GRAMMAR_MIXED_CONDITIONALS_B2 remains deferred.
[PASS] No grammar_edges.json modification.
[PASS] No accepted authority promotion.
[PASS] No learner-facing practice generated.
[PASS] No learner state write introduced.
[PASS] Validation report synced to 46 nodes / 52 edges.
[PASS] CI-safe test expectations synced to 46 / 52.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

## 6. Next Shortest Step

```text
NEXT_SHORT_STEP:
R7-M30 B2 Package-A candidate-edge planning scan
```

R7-M30 must remain planning-only. It should inspect prerequisite / sequencing edges for the 7 new B2 candidate nodes, but it must not modify `grammar_edges.json` until explicitly approved.
