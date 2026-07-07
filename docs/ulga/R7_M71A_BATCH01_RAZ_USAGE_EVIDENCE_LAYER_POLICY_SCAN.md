# R7-M71A Batch 01 RAZ Usage Evidence Layer Policy Scan

## Task

```text
R7-M71A_Batch01RAZUsageEvidenceLayerPolicyScan
```

## Background

R7-M70 stopped because Batch 01 still needs human source/evidence decisions before any authority mapping can be written.

The operator asked whether Batch 01 can first use RAZ-related sentences or passages. The answer is yes, but only as usage evidence.

## Evidence Layer Separation

```text
EGP = grammar authority and level authority
RAZ = reading usage evidence and child-readable sentence evidence
```

RAZ evidence must not replace EGP rows. RAZ examples can support how a structure appears in early-reader reading content.

## Scope

This stage may build a candidate index of RAZ sentence or passage snippets related to Batch 01 grammar nodes.

It must not:

```text
write egp_evidence_refs
promote authority mappings
increase grammar coverage
generate PracticeBank
write learner state
change ReadingV1 runtime
```

## Target Grammar Nodes

```text
B01-01 GRAMMAR_ARTICLES_BASIC
B01-02 GRAMMAR_BASIC_PREPOSITIONS_PLACE
B01-03 GRAMMAR_BE_VERB_BASIC
B01-04 GRAMMAR_CAN_STATEMENT
B01-05 GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC
```

## RAZ Usage Evidence Roles

```text
RAZ_USAGE_EVIDENCE = sentence or passage evidence from RAZ-like reading source
RAZ_SEMANTIC_USAGE_EVIDENCE = usage evidence that supports a semantic function such as ability
RAZ_PASSAGE_CONTEXT = passage-level context supporting a sentence pattern
```

## Matching Intent

```text
GRAMMAR_ARTICLES_BASIC
Find a/an/the + noun usage in early-reader sentences.

GRAMMAR_BASIC_PREPOSITIONS_PLACE
Find locative preposition usage such as in/on/under/next to/behind/between.

GRAMMAR_BE_VERB_BASIC
Find basic be-verb sentences using am/is/are.

GRAMMAR_CAN_STATEMENT
Find can + base verb ability-style sentences such as can jump, can run, can swim, can fly, can read.

GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC
Find possessive determiner usage such as my/your/his/her/its/our/their + noun.
```

## Output Contract

```text
ulga/reports/grammar_node_egp_batch01_raz_usage_evidence_candidates.json
ulga/reports/grammar_node_egp_batch01_raz_usage_evidence_candidates_summary.json
```

## Candidate Status

All output candidates must remain review aids only.

```text
operator_review_required = true
authority_write_allowed = false
evidence_refs_write_allowed = false
```

## Next Step

```text
NEXT_SHORT_STEP = R7-M72A_Batch01RAZUsageEvidenceCandidateBuilderImplementation
```

## Status

```text
R7_M71A_STATUS = PASS
STOP_REASON = NONE
```
