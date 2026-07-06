# R7-M8 Corrected B1 Candidate-node Implementation Batch

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M8 corrected B1 candidate-node implementation batch

Branch:
codex/r7-m8-corrected-b1-candidate-node-batch

Status:
IMPLEMENTATION_BATCH_WITH_DERIVED_SYNC
```

R7-M8 implements the operator-approved corrected B1 candidate-node batch from R7-M7 and keeps all records candidate-only.

## 2. Operator Approval

The operator approved the expanded R7-M8 route so the implementation can pass CI:

```text
Allowed files:
- ulga/grammar/grammar_nodes.json
- ulga/grammar/grammar_order_table.json
- ulga/grammar/grammar_coverage_matrix.json
- ulga/grammar/grammar_query_index.json
- ulga/reports/grammar_artifact_validation_report.json
- tests/ci/test_static_grammar_artifacts.py
```

## 3. Implemented Candidate Nodes

R7-M8 adds 10 corrected B1 candidate nodes:

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

All 10 nodes use:

```text
authority_status = candidate
introduced_stage = B1
confidence = operator_review_required
traceability.generated_content = false
traceability.learner_state_write = false
```

## 4. Out of Scope

```text
No grammar_edges.json modification.
No accepted authority promotion.
No learner-facing practice generation.
No learner state write.
No B1_PLUS implementation.
No B2 implementation.
```

## 5. Synced Static Artifact Counts

```text
node_count = 32
edge_count = 22
order_row_count = 32
coverage_node_count = 32
query_node_count = 32
fail_count = 0
```

CI expectations are updated to:

```text
EXPECTED_NODE_COUNT = 32
EXPECTED_EDGE_COUNT = 22
```

## 6. Gate & Distance Update

```text
[PASS] 10 corrected B1 candidate nodes added.
[PASS] All new nodes remain candidate-only.
[PASS] No learner-facing practice generated.
[PASS] No learner state write introduced.
[PASS] No grammar_edges.json modification.
[PASS] Static derived artifacts synced to 32 nodes / 22 edges.
[PASS] CI-safe test expectations synced to 32 / 22.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

## 7. Next Shortest Step

```text
NEXT_SHORT_STEP:
R7-M9 corrected B1 candidate-edge planning scan
```

R7-M9 must remain edge-planning only. It should propose matching B1 candidate edges for the 10 R7-M8 nodes, but it must not modify `grammar_edges.json` until explicitly approved.
