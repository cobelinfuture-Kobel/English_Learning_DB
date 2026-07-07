# R7-M76A Batch 01 RAZ Usage Evidence Quality Filter Readback

## Task

```text
R7-M76A_Batch01RAZUsageEvidenceQualityFilterReadback
```

## Filter result

R7-M75A produced a valid filtered Batch 01 RAZ usage-evidence candidate packet.

```text
validation_status = PASS
raw_candidate_count = 150
filtered_candidate_count = 88
removed_candidate_count = 62
target_count = 5
targets_without_candidates = 0
operator_review_required = true
```

## Removed candidate reasons

```text
clothing_phrasal_put_on = 8
counting_phrase_in_all = 3
duplicate_sentence_match = 22
question_not_affirmative_declarative = 1
question_not_primary_usage_candidate = 1
title_only_candidate = 19
transport_medium_not_place_location = 8
```

## Filtered candidate counts

```text
B01-01 GRAMMAR_ARTICLES_BASIC = 22
B01-02 GRAMMAR_BASIC_PREPOSITIONS_PLACE = 8
B01-03 GRAMMAR_BE_VERB_BASIC = 27
B01-04 GRAMMAR_CAN_STATEMENT = 8
B01-05 GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC = 23
```

## Readback by node

### B01-01 GRAMMAR_ARTICLES_BASIC

Filtered RAZ usage examples include:

```text
The dogs go in.
The cats go in.
This is a kitten.
This is a puppy.
The bird goes over the tree.
```

Interpretation: RAZ usage evidence supports basic article use in early-reader sentence contexts. This does not replace EGP authority evidence.

### B01-02 GRAMMAR_BASIC_PREPOSITIONS_PLACE

Filtered RAZ usage examples include:

```text
You float on the water.
You fish in the water.
You swim in the water.
You play in the water.
```

Interpretation: filtered candidates are narrower than the first broad scan. They support place/prepositional usage as RAZ reading examples, but final operator review is still required.

### B01-03 GRAMMAR_BE_VERB_BASIC

Filtered RAZ usage examples include:

```text
This is a kitten.
Here is my room.
Here are my books.
My hair is short.
This is my eye.
```

Interpretation: RAZ usage evidence strongly supports basic be-verb sentence patterns in early-reader content.

### B01-04 GRAMMAR_CAN_STATEMENT

Filtered RAZ semantic usage examples include:

```text
I can run.
I can jump.
I can hop.
I can ride.
I can climb.
I can play.
We can make sounds.
```

Interpretation: these examples support can-as-ability style usage better than the generic EGP modal-declarative row alone. EGP remains form authority; RAZ remains semantic usage evidence.

### B01-05 GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC

Filtered RAZ usage examples include:

```text
My dog can jump.
My dog can run.
Here is my room.
Here is my bed.
Here are my books.
```

Interpretation: RAZ usage evidence supports possessive determiner + noun in early-reader sentence contexts.

## Safety boundary

```text
authority_write_allowed = false
evidence_refs_write_allowed = false
coverage_increase_allowed = false
practicebank_generation = false
learner_state_write = false
runtime_change = false
```

## Decision implication

The RAZ layer can now help Batch 01 decisions, especially B01-04. However, final evidence selection is still a human source/evidence decision.

The next step would select which filtered RAZ examples to attach as usage evidence and how to coordinate them with EGP form evidence. That requires operator choice.

## Status

```text
R7_M76A_STATUS = PASS_WITH_OPERATOR_REVIEW_REQUIRED
LAST_COMPLETED_STATUS = R7_M76A_RAZ_USAGE_EVIDENCE_QUALITY_FILTER_READBACK_PASS
STOP_REASON = NEED_HUMAN_SOURCE_REF_EVIDENCE_SELECTION
BLOCKER_TYPE = HUMAN_EVIDENCE_REVIEW_REQUIRED
REQUIRED_OPERATOR_ACTION = Review filtered Batch 01 RAZ usage evidence examples and approve a usage-evidence selection plan.
NEXT_RESUME_TASK = R7-M77A_Batch01FilteredRAZUsageEvidenceOperatorSelectionPlan
```
