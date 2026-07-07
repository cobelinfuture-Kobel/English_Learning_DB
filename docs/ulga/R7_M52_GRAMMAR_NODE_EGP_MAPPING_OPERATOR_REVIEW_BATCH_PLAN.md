# R7-M52 Grammar Node EGP Mapping Operator Review Batch Plan

## Task

```text
R7-M52_GrammarNodeEGPMappingOperatorReviewBatchPlan
```

## Predecessor

```text
R7-M51_GrammarNodeEGPCandidateSuggestionReviewReadback = PASS
```

## Current State

The current review queue and candidate suggestion artifacts report:

```text
review_queue_count = 32
suggestion_record_count = 32
total_candidate_count = 160
max_candidates_per_node = 5
review_required = true
```

## Purpose

Split the 32 grammar-node EGP review items into small operator-review batches.

This task does not select EGP evidence and does not write `egp_evidence_refs`.

## Batch Policy

```text
batch_size = 5
sort_order = review_priority, system_stage, grammar_id
expected_batch_count = 7
```

Expected split:

```text
Batch 01 = 5 items
Batch 02 = 5 items
Batch 03 = 5 items
Batch 04 = 5 items
Batch 05 = 5 items
Batch 06 = 5 items
Batch 07 = 2 items
```

## Operator Decision Format

Each item must receive exactly one decision:

```text
ACCEPT_EGP_ROW
REJECT_ALL_CANDIDATES
MARK_NOT_IN_EGP_BUT_SYSTEM_REQUIRED
DEFER
REQUEST_REFINED_CANDIDATES
```

### ACCEPT_EGP_ROW Required Fields

```json
{
  "decision": "ACCEPT_EGP_ROW",
  "grammar_id": "...",
  "selected_egp_row_id": "...",
  "operator_reason": "..."
}
```

### REJECT_ALL_CANDIDATES Required Fields

```json
{
  "decision": "REJECT_ALL_CANDIDATES",
  "grammar_id": "...",
  "operator_reason": "..."
}
```

### MARK_NOT_IN_EGP_BUT_SYSTEM_REQUIRED Required Fields

```json
{
  "decision": "MARK_NOT_IN_EGP_BUT_SYSTEM_REQUIRED",
  "grammar_id": "...",
  "operator_reason": "..."
}
```

### DEFER Required Fields

```json
{
  "decision": "DEFER",
  "grammar_id": "...",
  "operator_reason": "..."
}
```

### REQUEST_REFINED_CANDIDATES Required Fields

```json
{
  "decision": "REQUEST_REFINED_CANDIDATES",
  "grammar_id": "...",
  "operator_reason": "...",
  "refinement_hint": "..."
}
```

## Safety Constraints

```text
NO_RUNTIME_IMPLEMENTATION = true
NO_PRACTICEBANK_GENERATION = true
NO_LEARNER_STATE_WRITE = true
NO_AUTO_EGP_ROW_SELECTION = true
NO_AUTHORITY_WRITE = true
NO_COVERAGE_INCREASE_FROM_CANDIDATES = true
```

## Required Artifacts for R7-M53

```text
ulga/reports/grammar_node_egp_operator_review_batches.json
ulga/reports/grammar_node_egp_operator_review_batches_summary.json
```

## NEXT_SHORT_STEP

```text
NEXT_SHORT_STEP = R7-M53_GrammarNodeEGPOperatorReviewBatchBuilderImplementation
```

## Status

```text
R7_M52_STATUS = PASS
STOP_REASON = NONE
```
