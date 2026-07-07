# R7-M55R Grammar Node EGP Refined Candidate Generation Policy Scan

## Task

```text
R7-M55R_GrammarNodeEGPRefinedCandidateGenerationPolicyScan
```

## Predecessor

```text
R7-M54_GrammarNodeEGPOperatorReviewBatchReadback = PASS
```

## Purpose

Improve the usefulness of the existing candidate suggestions before operator evidence review begins.

The current review packet contains 32 items and 160 candidate suggestions. This is usable, but still broad. R7-M55R defines a stricter refinement layer so the operator sees fewer, higher-signal candidates.

## Scope

R7-M55R is still a review-support task only.

It does not choose evidence and does not write accepted mappings.

## Refinement Rules

The refined candidate pass must apply all rules below:

```text
1. Keep only stage-compatible EGP levels.
2. Require either meaningful token overlap or a stronger existing candidate score.
3. Limit each grammar node to at most 3 refined candidates.
4. Add confidence_band = HIGH / MEDIUM / LOW.
5. Preserve review_required = true.
6. Preserve learner_state_write = false.
7. Preserve practicebank_generation = false.
```

## Stage Compatibility

```text
A1  -> A1
A1+ -> A1, A2
A2  -> A2
A2+ -> A2, B1
B1  -> B1
B1+ -> B1, B2
B2  -> B2
```

## Confidence Policy

```text
HIGH   = candidate_score >= 0.40
MEDIUM = candidate_score >= 0.30 and < 0.40
LOW    = candidate_score >= 0.22 and < 0.30
```

Any candidate below `0.22` must be removed unless a future operator-approved rule says otherwise.

## Required Artifacts for R7-M56R

```text
ulga/reports/grammar_node_egp_refined_candidate_suggestions.json
ulga/reports/grammar_node_egp_refined_candidate_suggestions_summary.json
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

## NEXT_SHORT_STEP

```text
NEXT_SHORT_STEP = R7-M56R_GrammarNodeEGPRefinedCandidateBuilderImplementation
```

## Status

```text
R7_M55R_STATUS = PASS
STOP_REASON = NONE
```
