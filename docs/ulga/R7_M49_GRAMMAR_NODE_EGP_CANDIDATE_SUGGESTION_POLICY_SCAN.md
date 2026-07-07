# R7-M49 Grammar Node EGP Candidate Suggestion Policy Scan

## Task

```text
R7-M49_GrammarNodeEGPCandidateSuggestionPolicyScan
```

## Predecessor

```text
R7-M48_CIReadbackAndCloseout = PASS_CI_SYNCED
```

## Purpose

Define the policy for generating candidate EGP mapping suggestions for the review queue without promoting candidates to authority.

The goal is to help the operator review 32 unmapped grammar nodes more efficiently while preserving evidence safety.

## Current Review Queue State

```text
review_queue_count = 32
priority_counts = HIGH:22, MEDIUM:10
candidate_generation_allowed = true
candidate_promotion_allowed = false
```

## Policy Decision

Candidate suggestions are allowed only as review aids.

They must not update:

```text
ulga/grammar/grammar_nodes.json
ulga/graph/cefr_egp_alignment_table.json as authority MATCH
learner_state
PracticeBank
ReadingV1 runtime
```

## Candidate Suggestion Inputs

Allowed input sources:

```text
ulga/reports/grammar_node_egp_mapping_review_queue.json
grammar_profile/json/grammar_profile.json
ulga/grammar/grammar_nodes.json
```

Allowed comparison fields:

```text
grammar_id
label
category
system_stage
authority_status
EGP super_category
EGP sub_category
EGP level
EGP guideword
EGP can_do_statement
EGP example
```

## Candidate Suggestion Output

Target artifact:

```text
ulga/reports/grammar_node_egp_candidate_suggestions.json
```

Target summary:

```text
ulga/reports/grammar_node_egp_candidate_suggestions_summary.json
```

Each suggestion record should contain:

```json
{
  "grammar_id": "GRAMMAR_EXAMPLE",
  "review_priority": "HIGH|MEDIUM|LOW",
  "candidate_suggestions": [
    {
      "egp_row_id": "EGP_ROW_ID",
      "egp_level": "A1|A2|B1|B2|C1|C2",
      "super_category": "...",
      "sub_category": "...",
      "guideword": "...",
      "candidate_score": 0.0,
      "candidate_reason": "deterministic keyword/category/stage similarity",
      "promotion_status": "OPERATOR_REVIEW_REQUIRED"
    }
  ],
  "candidate_generation_allowed": true,
  "candidate_promotion_allowed": false,
  "learner_state_write": false,
  "practicebank_generation": false
}
```

## Scoring Policy

The candidate suggestion builder may use deterministic scoring only:

```text
+ exact normalized keyword overlap
+ category / sub_category similarity
+ EGP level compatibility
+ guideword token overlap
+ can-do token overlap
- level mismatch penalty
- empty evidence penalty
```

The score is advisory and must not become `MATCH` automatically.

## Promotion Policy

Forbidden automatic promotion:

```text
candidate_score >= threshold -> MATCH
candidate_score highest -> auto egp_ref
candidate suggestion -> grammar_nodes write
candidate suggestion -> coverage matrix authority update
```

Required future promotion route:

```text
operator selects source_ref / EGP row
operator-approved patch writes egp_evidence_refs
pipeline refresh computes EGP_MAPPED
validator checks counts
CI readback
```

## Safety Gates

```text
NO_RUNTIME_IMPLEMENTATION = true
NO_PRACTICEBANK_GENERATION = true
NO_LEARNER_STATE_WRITE = true
NO_AI_MAPPING_PROMOTION = true
NO_AUTHORITY_WRITE = true
CANDIDATE_PROMOTION_ALLOWED = false
```

## NEXT_SHORT_STEP

```text
NEXT_SHORT_STEP = R7-M50_GrammarNodeEGPCandidateSuggestionBuilderImplementation
```

## Status

```text
R7_M49_STATUS = PASS
STOP_REASON = NONE
```
