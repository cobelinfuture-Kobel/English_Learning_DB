# R7-M47 Grammar Node EGP Mapping Review Queue Design Scan

## Task

```text
R7-M47_GrammarNodeEGPMappingReviewQueueDesignScan
```

## Predecessor

```text
R7-M46_MainCIReadbackForR7M44A = PASS_CI_SYNCED
```

## Current Evidence Summary

Current generated alignment summary reports:

```text
grammar_node_count = 46
grammar_nodes_source_path = ulga/grammar/grammar_nodes.json
egp_row_count = 1222
mapped_counts_by_level = A1:0, A2:0, B1:8, B2:36, C1:0, C2:0
uncovered_counts_by_level = A1:109, A2:291, B1:330, B2:207, C1:129, C2:112
target_a1_b2_mapped = 44
target_a1_b2_total = 981
target_a1_b2_coverage = 0.04485219164118247
node_status_counts = EGP_MAPPED:14, UNMAPPED:32
unresolved_refs = []
```

## Problem

The pipeline can now read the correct grammar node source and normalize existing `egp_evidence_refs`, but 32 grammar nodes remain `UNMAPPED`.

The next step must not directly convert unmapped nodes to `MATCH`.

A review queue is required before any new node-to-EGP evidence selection is promoted.

## Design Decision

Create a review queue artifact, not an authority mapping artifact.

Target artifact:

```text
ulga/reports/grammar_node_egp_mapping_review_queue.json
```

Target summary:

```text
ulga/reports/grammar_node_egp_mapping_review_queue_summary.json
```

## Review Queue Record Shape

Each review queue item should contain:

```json
{
  "grammar_id": "GRAMMAR_EXAMPLE",
  "label": "human readable label",
  "category": "source node category if present",
  "system_stage": "A1|A1+|A2|A2+|B1|B1+|B2",
  "authority_status": "accepted|candidate|review_required",
  "node_status": "UNMAPPED|EGP_PARTIAL_MATCH|UNRESOLVED_EGP_REFS|CONFLICT_REVIEW_REQUIRED",
  "review_priority": "HIGH|MEDIUM|LOW",
  "review_reason": "why this node needs mapping review",
  "allowed_next_action": "operator_select_egp_ref|mark_not_in_egp_but_system_required|defer",
  "candidate_generation_allowed": true,
  "candidate_promotion_allowed": false,
  "learner_state_write": false
}
```

## Priority Policy

| Condition | Priority |
|---|---|
| A1 or A2 node is unmapped | `HIGH` |
| accepted node is unmapped | `HIGH` |
| B1/B2 candidate node is unmapped | `MEDIUM` |
| unresolved evidence refs exist | `HIGH` |
| system-required outside EGP needs reason | `MEDIUM` |

## Safety Policy

Allowed in R7-M48 implementation:

```text
Create deterministic review queue from current alignment table.
List unmapped grammar nodes.
List unresolved refs.
List candidate-generation eligibility.
```

Forbidden in R7-M48 implementation:

```text
Do not choose new EGP source rows.
Do not mark fuzzy matches as MATCH.
Do not write learner_state.
Do not generate PracticeBank.
Do not alter ReadingV1 runtime.
```

## NEXT_SHORT_STEP

```text
NEXT_SHORT_STEP = R7-M48_GrammarNodeEGPMappingReviewQueueBuilderImplementation
```

## Status

```text
R7_M47_STATUS = PASS
STOP_REASON = NONE
```
