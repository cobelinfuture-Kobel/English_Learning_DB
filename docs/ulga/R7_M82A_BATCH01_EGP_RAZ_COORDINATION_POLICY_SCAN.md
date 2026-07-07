# R7-M82A Batch 01 EGP / RAZ Coordination Policy Scan

## Task

`R7-M82A_Batch01EGPAuthorityAndRAZUsageCoordinationPolicyScan`

## Input state

```text
R7_M80A_STATUS = PASS_CI_SYNCED_AND_CLEAN
R7_M81A_STATUS = PASS
RAZ_USAGE_EXAMPLES_APPROVED = true
APPROVED_RAZ_USAGE_EXAMPLE_COUNT = 29
BATCH01_TARGET_COUNT = 5
```

## Core separation

```text
EGP = authority source for grammar / CEFR mapping
RAZ = usage source for child-readable examples
```

Do not merge these two layers into one field.

## Allowed in this phase

```text
coordinate EGP candidate decisions with approved RAZ usage examples
write planning docs
write review packet artifacts
keep all authority writes disabled
```

## Forbidden in this phase

```text
write grammar_nodes.json
write egp_evidence_refs
increase coverage
create PracticeBank output
write learner_state
change runtime
```

## Batch 01 coordination policy

### B01-01 Articles

```text
EGP role = authority row for articles with nouns
RAZ role = simple article examples
status = ready for coordinated review
```

### B01-02 Place prepositions

```text
EGP role = still unresolved
RAZ role = usage examples for in/on place phrases
status = keep EGP unresolved; RAZ supports usage only
```

### B01-03 Be verb

```text
EGP role = still unresolved or broad
RAZ role = usage examples for basic be-verb sentences
status = keep EGP unresolved; RAZ supports usage only
```

### B01-04 Can statement

```text
EGP role = modal declarative form evidence
RAZ role = semantic usage examples for can-pattern ability style
status = ready for split-layer coordinated review
```

### B01-05 Possessive adjectives

```text
EGP role = authority row for possessives with nouns
RAZ role = simple possessive determiner examples
status = ready for coordinated review
```

## Proposed next artifact

Create a coordination packet that records:

```text
grammar_id
EGP decision recommendation
EGP row id when available
RAZ usage decision status
approved RAZ usage example count
write_allowed flags = false
operator_review_required = true
```

## Status

```text
R7_M82A_STATUS = PASS
LAST_COMPLETED_STATUS = R7_M82A_POLICY_SCAN_PASS
NEXT_SHORT_STEP = R7-M83A_Batch01EGPRAZCoordinationPacketBuilder
STOP_REASON = PLANNING_TO_IMPLEMENTATION_APPROVAL_REQUIRED
```
