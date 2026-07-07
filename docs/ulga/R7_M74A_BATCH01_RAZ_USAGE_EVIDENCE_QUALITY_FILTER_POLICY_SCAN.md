# R7-M74A Batch 01 RAZ Usage Evidence Quality Filter Policy Scan

## Task

```text
R7-M74A_Batch01RAZUsageEvidenceQualityFilterPolicyScan
```

## Input

```text
ulga/reports/grammar_node_egp_batch01_raz_usage_evidence_candidates.json
ulga/reports/grammar_node_egp_batch01_raz_usage_evidence_candidates_summary.json
```

## Problem

R7-M72A intentionally used broad matching to confirm that RAZ usage evidence exists for all five Batch 01 grammar nodes.

R7-M73A readback found useful candidates, but also deterministic noise:

```text
book-title matches mixed with sentence matches
non-locative on/in phrases
clothing phrasal verb put on
counting phrase in all
transport phrases for on/in that are not place-location targets
article matches from title-case book names
duplicate page-unit candidates
```

## Scope

This stage defines a deterministic quality filter over RAZ usage evidence candidates.

Allowed:

```text
read R7-M72A RAZ candidate artifact
filter duplicate sentence/pattern/source candidates
mark or remove known noisy matches
produce filtered candidate artifact and summary
keep operator_review_required = true
```

Forbidden:

```text
write egp_evidence_refs
write grammar node authority mappings
increase grammar coverage
generate PracticeBank
write learner state
change runtime
select final accepted evidence automatically
```

## Output Contract

```text
ulga/reports/grammar_node_egp_batch01_raz_usage_evidence_candidates_filtered.json
ulga/reports/grammar_node_egp_batch01_raz_usage_evidence_candidates_filtered_summary.json
```

## Quality Rules

### Global rules

```text
G1 remove exact duplicate candidates by grammar_id + normalized sentence_text + matched_text + source_path
G2 require sentence_text to have sentence-like structure unless the source explicitly marks title context
G3 preserve source_path, pattern_id, evidence_role, operator_review_required
G4 keep rejected/noisy candidates only in summary counts, not in filtered candidate list
G5 do not infer authority acceptance
```

### B01-01 Articles

Keep:

```text
sentences containing a/an/the + concrete noun
simple title-like rows only if they are useful as book-title context, not as primary evidence
```

Prefer:

```text
This is a kitten.
This is a puppy.
The dogs go in.
```

Filter:

```text
title-only rows when a sentence-level equivalent exists
partial adjective-only matches such as The Big
```

### B01-02 Place Prepositions

Keep:

```text
in/on/under/behind/between/near/beside + place noun
on the water
in the water
in the box
on the table
under the chair
```

Filter:

```text
put on + clothing
in all
on a plane/train/boat/bike/skateboard/horse when the node target is place-location, not transport medium
ambiguous title-only rows
```

### B01-03 Be Verb

Keep:

```text
This is ...
Here is ...
Here are ...
My hair is ...
```

Filter:

```text
title-only rows when duplicate sentence-level usage exists
questions when target is affirmative declarative basic be unless separately tagged as question context
```

### B01-04 Can Statement

Keep:

```text
I can run.
I can jump.
I can hop.
I can ride.
I can climb.
I can play.
We can make sounds.
```

Filter:

```text
duplicates across page-unit and sentence artifacts
title-only duplicates when sentence-level version exists
can + go transport phrases unless separately tagged as travel/possibility, not ability
```

### B01-05 Possessive Adjectives

Keep:

```text
My dog can jump.
Here is my room.
Here are my books.
My hair is short.
```

Filter:

```text
title-only rows when sentence-level examples exist
question examples unless tagged separately
partial title matches such as My Little when noun head is not isolated cleanly
```

## Filtered Summary Requirements

The summary must report:

```text
raw_candidate_count
filtered_candidate_count
removed_candidate_count
removed_by_reason
candidate_count_by_grammar_id
operator_review_required = true
authority_write_allowed = false
next_short_step
stop_reason
```

## Acceptance Criteria

```text
filtered artifact exists
filtered summary exists
all five Batch 01 grammar nodes remain represented unless genuinely no clean candidate survives
no authority fields are written
validator passes
pytest passes
```

## Next Step

```text
NEXT_SHORT_STEP = R7-M75A_Batch01RAZUsageEvidenceQualityFilterImplementation
```

## Status

```text
R7_M74A_STATUS = PASS
STOP_REASON = NONE
```
