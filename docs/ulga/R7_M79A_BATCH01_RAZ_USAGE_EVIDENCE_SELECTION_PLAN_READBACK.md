# R7-M79A Batch 01 RAZ Usage Evidence Selection Plan Readback

## Task

```text
R7-M79A_Batch01RAZUsageEvidenceSelectionPlanReadback
```

## Selection plan result

R7-M78A produced a valid proposed RAZ usage-evidence selection packet.

```text
validation_status = PASS
source_filtered_candidate_count = 88
selected_candidate_count = 29
unselected_candidate_count = 59
target_count = 5
targets_without_selected_candidates = 0
operator_review_required = true
```

## Selection counts

```text
B01-01 GRAMMAR_ARTICLES_BASIC = 5
B01-02 GRAMMAR_BASIC_PREPOSITIONS_PLACE = 5
B01-03 GRAMMAR_BE_VERB_BASIC = 6
B01-04 GRAMMAR_CAN_STATEMENT = 7
B01-05 GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC = 6
```

## Proposed selections by node

### B01-01 GRAMMAR_ARTICLES_BASIC

Proposed RAZ usage examples:

```text
This is a cub.
This is a kid.
This is a calf.
This is a foal.
This is a lamb.
```

Interpretation: clean `a + noun` early-reader examples; useful as RAZ usage evidence for basic article usage.

### B01-02 GRAMMAR_BASIC_PREPOSITIONS_PLACE

Proposed RAZ usage examples:

```text
You sail on the water.
You float on the water.
You paddle on the water.
You dive in the water.
You fish in the water.
```

Interpretation: clean `on the water` / `in the water` examples; useful as RAZ usage evidence for locative preposition usage, but not a complete preposition-of-place inventory.

### B01-03 GRAMMAR_BE_VERB_BASIC

Proposed RAZ usage examples:

```text
This is a cub.
This is a kid.
This is a calf.
This is a foal.
This is a lamb.
This is my ear.
```

Interpretation: clean `This is ...` early-reader examples; useful as RAZ usage evidence for basic be-verb patterns.

### B01-04 GRAMMAR_CAN_STATEMENT

Proposed RAZ semantic usage examples:

```text
I can run.
I can jump.
I can hop.
I can ride.
I can climb.
I can play.
We can make sounds.
```

Interpretation: this is the strongest Batch 01 RAZ semantic usage result. It directly supports can-as-ability style examples in early-reader material. EGP remains the form authority layer.

### B01-05 GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC

Proposed RAZ usage examples:

```text
My dog can dig.
My dog can hug.
My dog can run.
My dog can sit.
My dog can jump.
My dog can swim.
```

Interpretation: clean `my + noun` examples; useful as RAZ usage evidence for possessive determiner + noun.

## Architecture interpretation

```text
EGP evidence = grammar authority / level authority
RAZ selected examples = usage evidence / semantic usage examples
```

The proposed selection packet can inform Batch 01 operator decisions, especially B01-04, but it does not itself authorize:

```text
authority write
evidence_refs write
coverage increase
PracticeBank generation
learner_state write
runtime change
```

## Decision implication

A later authority patch, if approved, should keep EGP and RAZ layers separate:

```text
B01-04 EGP row 1741163708329x931125497510935300 = can/modal declarative form evidence
B01-04 RAZ examples I can run / I can jump / I can play = semantic usage evidence
```

## Status

```text
R7_M79A_STATUS = PASS_WITH_OPERATOR_REVIEW_REQUIRED
LAST_COMPLETED_STATUS = R7_M79A_SELECTION_PLAN_READBACK_PASS
STOP_REASON = NEED_HUMAN_SOURCE_REF_EVIDENCE_SELECTION
BLOCKER_TYPE = HUMAN_EVIDENCE_REVIEW_REQUIRED
REQUIRED_OPERATOR_ACTION = Approve or edit the proposed RAZ usage evidence selections before any usage-evidence attachment or Batch 01 decision artifact is created.
NEXT_RESUME_TASK = R7-M80A_Batch01RAZUsageEvidenceSelectionOperatorDecisionArtifact
```
