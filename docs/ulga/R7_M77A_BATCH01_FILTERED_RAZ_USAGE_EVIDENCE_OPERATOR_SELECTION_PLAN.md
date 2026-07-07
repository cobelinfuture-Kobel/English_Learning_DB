# R7-M77A Batch 01 Filtered RAZ Usage Evidence Operator Selection Plan

## Task

```text
R7-M77A_Batch01FilteredRAZUsageEvidenceOperatorSelectionPlan
```

## Operator approval

The operator approved progressing from R7-M76A to a usage-evidence selection plan.

## Input artifact

```text
ulga/reports/grammar_node_egp_batch01_raz_usage_evidence_candidates_filtered.json
ulga/reports/grammar_node_egp_batch01_raz_usage_evidence_candidates_filtered_summary.json
```

## Purpose

Create a deterministic proposed selection packet from filtered RAZ usage evidence.

This packet is not final authority acceptance. It is an operator review aid for choosing usage examples that can be attached later as RAZ usage evidence.

## Evidence model

```text
EGP = grammar authority / level authority
RAZ = reading usage evidence / semantic usage example evidence
```

RAZ usage examples may support practice-generation context later, but they must not replace EGP authority rows.

## Scope

Allowed:

```text
read filtered RAZ usage candidates
select a small representative subset per Batch 01 grammar node
preserve source_path, sentence_text, matched_text, pattern_id, evidence_role
mark proposed usage evidence as operator_review_required = true
produce selection-plan artifact and summary
```

Forbidden:

```text
write egp_evidence_refs
write grammar authority mappings
increase EGP coverage
promote any RAZ example to authority evidence
generate PracticeBank
write learner state
change runtime
```

## Proposed selection size

```text
B01-01 GRAMMAR_ARTICLES_BASIC: up to 5 representative examples
B01-02 GRAMMAR_BASIC_PREPOSITIONS_PLACE: up to 5 representative examples
B01-03 GRAMMAR_BE_VERB_BASIC: up to 6 representative examples
B01-04 GRAMMAR_CAN_STATEMENT: up to 7 representative examples
B01-05 GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC: up to 6 representative examples
```

## Selection priorities

### B01-01 Articles

Prioritize sentence-level examples using:

```text
This is a + noun.
The + plural noun + simple verb.
The + noun + simple verb + place phrase.
```

### B01-02 Place prepositions

Prioritize concrete locative readings:

```text
on the water
in the water
```

Transport medium, clothing, and counting phrases remain excluded.

### B01-03 Be verb

Prioritize representative forms:

```text
This is ...
Here is ...
Here are ...
My hair is ...
```

### B01-04 Can statement

Prioritize ability-style examples:

```text
I can run.
I can jump.
I can hop.
I can ride.
I can climb.
I can play.
We can make sounds.
```

### B01-05 Possessive adjectives

Prioritize possessive determiner + noun contexts:

```text
My dog ...
Here is my ...
Here are my ...
My hair ...
```

## Output Contract

```text
ulga/reports/grammar_node_egp_batch01_raz_usage_evidence_selection_plan.json
ulga/reports/grammar_node_egp_batch01_raz_usage_evidence_selection_plan_summary.json
```

## Summary Requirements

```text
source_filtered_candidate_count
selected_candidate_count
selection_count_by_grammar_id
unselected_candidate_count
operator_review_required = true
authority_write_allowed = false
evidence_refs_write_allowed = false
coverage_increase_allowed = false
next_short_step
stop_reason
```

## Acceptance Criteria

```text
selection plan artifact exists
selection summary exists
all five Batch 01 grammar nodes are represented
all selected examples come from filtered RAZ usage candidates
no authority or EGP evidence fields are written
validator passes
pytest passes
```

## Next Step

```text
NEXT_SHORT_STEP = R7-M78A_Batch01RAZUsageEvidenceSelectionPlanArtifactBuilder
```

## Status

```text
R7_M77A_STATUS = PASS
STOP_REASON = NONE
```
