# R7-M51 Grammar Node EGP Candidate Suggestion Review Readback

## Task

```text
R7-M51_GrammarNodeEGPCandidateSuggestionReviewReadback
```

## Predecessor

```text
R7-M50_CIReadbackAndCloseout = PASS_CI_SYNCED
```

## Current Candidate Suggestion Summary

```text
review_queue_count = 32
suggestion_record_count = 32
total_candidate_count = 160
max_candidates_per_node = 5
review_required = true
```

## Meaning

The system now has deterministic candidate suggestions for all 32 review queue records.

These suggestions are not authority mappings.

They are only review aids for operator selection.

## Required Human Decision Before Mapping Promotion

The next stage would require choosing source evidence for grammar nodes.

That means the operator must decide for each review record whether to:

```text
1. select one EGP row as accepted evidence
2. reject all suggestions and defer
3. mark the node as NOT_IN_EGP_BUT_SYSTEM_REQUIRED with a reason
4. request a refined candidate generation pass
```

## Forbidden Without Human Review

```text
Do not auto-promote highest-scoring suggestion to MATCH.
Do not write egp_evidence_refs automatically.
Do not increase EGP coverage from candidate suggestions alone.
Do not update learner_state.
Do not generate PracticeBank.
Do not alter ReadingV1 runtime.
```

## Recommended Next Task

```text
R7-M52_GrammarNodeEGPMappingOperatorReviewBatchPlan
```

Purpose:

```text
Split the 32 review queue items into small review batches and define the operator decision format.
```

## Stop State

```text
R7_M51_STATUS = PASS
STOP_REASON = NEED_HUMAN_SOURCE_REF_EVIDENCE_SELECTION
BLOCKER_TYPE = HUMAN_EVIDENCE_REVIEW_REQUIRED
LAST_COMPLETED_STATUS = R7_M51_CANDIDATE_SUGGESTION_REVIEW_READBACK_PASS
REQUIRED_OPERATOR_ACTION = Approve R7-M52 batch plan or provide selected EGP row decisions for review queue records.
NEXT_RESUME_TASK = R7-M52_GrammarNodeEGPMappingOperatorReviewBatchPlan
```
