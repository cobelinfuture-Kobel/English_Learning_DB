# R7-M73A Batch 01 RAZ Usage Evidence Candidate Readback

## Task

```text
R7-M73A_Batch01RAZUsageEvidenceCandidateReadback
```

## Source summary

R7-M72A produced a valid Batch 01 RAZ usage-evidence candidate packet.

```text
validation_status = PASS
source_roots_found = raz_output_jsons
source_file_count = 2252
scanned_text_unit_count = 2294069
scanned_sentence_count = 1510664
target_count = 5
total_raz_usage_candidate_count = 150
targets_without_candidates = 0
operator_review_required = true
```

## Target coverage

All Batch 01 grammar nodes now have RAZ usage candidates.

```text
B01-01 GRAMMAR_ARTICLES_BASIC = candidates found
B01-02 GRAMMAR_BASIC_PREPOSITIONS_PLACE = candidates found
B01-03 GRAMMAR_BE_VERB_BASIC = candidates found
B01-04 GRAMMAR_CAN_STATEMENT = candidates found
B01-05 GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC = candidates found
```

## Notable usage evidence examples

### B01-01 Articles

Examples include:

```text
This is a kitten.
This is a puppy.
The dogs go in.
The bird goes over the tree.
```

These support article usage as RAZ reading examples only.

### B01-02 Place prepositions

Examples include:

```text
You float on the water.
You fish in the water.
You swim in the water.
```

The packet also contains noisy matches such as transport phrases, clothing phrasal verb usage, and non-place phrases. These must be filtered before operator acceptance.

### B01-03 Be verb

Examples include:

```text
This is a kitten.
Here is my room.
Here are my books.
My hair is short.
```

These are useful early-reader usage examples for basic be-verb patterns.

### B01-04 Can statement

Examples include:

```text
I can run.
I can jump.
I can hop.
I can ride.
I can climb.
I can play.
We can make sounds.
```

These are stronger semantic usage examples for can-as-ability than the generic EGP modal declarative row alone.

### B01-05 Possessive adjectives

Examples include:

```text
My dog can jump.
Here is my room.
Here are my books.
My hair is short.
What is your hair like?
```

These support possessive determiner usage in child-readable context.

## Architecture interpretation

```text
EGP row evidence remains grammar authority.
RAZ sentence evidence is usage/example evidence.
RAZ evidence does not update EGP authority coverage.
RAZ evidence does not write egp_evidence_refs.
```

## Quality issue found

The first RAZ candidate scan is intentionally broad. It finds useful candidates, but also includes noisy matches:

```text
book titles mixed with sentences
non-locative on/in phrases
clothing phrasal verb put on
in all counting phrases
article matches inside titles
repeated page-unit duplicates
```

Therefore, the next step should add a deterministic quality filter before presenting candidates for final operator selection.

## Status

```text
R7_M73A_STATUS = PASS_WITH_ACTIONABLE_WARNINGS
LAST_COMPLETED_STATUS = R7_M73A_RAZ_USAGE_EVIDENCE_CANDIDATE_READBACK_PASS_WITH_ACTIONABLE_WARNINGS
NEXT_SHORT_STEP = R7-M74A_Batch01RAZUsageEvidenceQualityFilterPolicyScan
STOP_REASON = NONE
```
