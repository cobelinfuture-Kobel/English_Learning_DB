# R7-M54 Grammar Node EGP Operator Review Batch Readback

## Task

```text
R7-M54_GrammarNodeEGPOperatorReviewBatchReadback
```

## Predecessor

```text
R7-M53_CIReadbackAndCloseout = PASS_CI_SYNCED
```

## Current Operator Review Packet

Generated artifacts now exist for the operator-review stage:

```text
ulga/reports/grammar_node_egp_operator_review_batches.json
ulga/reports/grammar_node_egp_operator_review_batches_summary.json
```

Current reported values:

```text
batch_count = 7
item_count = 32
batch_size = 5
operator_review_required = true
```

## Allowed Operator Decisions

Each item requires exactly one decision:

```text
ACCEPT_EGP_ROW
REJECT_ALL_CANDIDATES
MARK_NOT_IN_EGP_BUT_SYSTEM_REQUIRED
DEFER
REQUEST_REFINED_CANDIDATES
```

## Meaning

The project has reached the point where automatic continuation would require selecting specific EGP source evidence for grammar nodes.

That is a human evidence-selection step, not a deterministic builder step.

## Forbidden Without Operator Evidence Review

```text
Do not auto-promote highest-scoring candidate.
Do not write egp_evidence_refs automatically.
Do not mark candidate suggestions as MATCH.
Do not increase EGP coverage from suggestions alone.
Do not write learner_state.
Do not generate PracticeBank.
Do not alter ReadingV1 runtime.
```

## Recommended Resume Options

### Option A: Operator Review Batch 01

```text
R7-M55_GrammarNodeEGPMappingOperatorReviewBatch01
```

Use Batch 01 from:

```text
ulga/reports/grammar_node_egp_operator_review_batches.json
```

The operator selects one decision per item.

### Option B: Refined Candidate Generation

```text
R7-M55R_GrammarNodeEGPRefinedCandidateGenerationPolicyScan
```

Use only if the current candidates are too broad or not useful.

## Stop State

```text
R7_M54_STATUS = PASS
STOP_REASON = NEED_HUMAN_SOURCE_REF_EVIDENCE_SELECTION
BLOCKER_TYPE = HUMAN_EVIDENCE_REVIEW_REQUIRED
LAST_COMPLETED_STATUS = R7_M54_OPERATOR_REVIEW_BATCH_READBACK_PASS
REQUIRED_OPERATOR_ACTION = Review Batch 01 or approve refined candidate-generation policy scan.
NEXT_RESUME_TASK = R7-M55_GrammarNodeEGPMappingOperatorReviewBatch01
```
