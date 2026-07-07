# R7-M66 Batch 01 Decision Readback and Next Refinement Plan

## Task

```text
R7-M66_Batch01DecisionReadbackAndNextRefinementPlan
```

## Predecessor

```text
R7-M65_Batch01OperatorDecisionArtifact = PASS
```

## Operator Decision Outcome

```text
REQUEST_REFINED_CANDIDATES = 4
DEFER = 1
ACCEPT_EGP_ROW = 0
```

## Planning Scope

This plan is for targeted second-pass refinement only.

It does not write `egp_evidence_refs`, update grammar authority, generate PracticeBank, write learner state, or alter ReadingV1 runtime.

## Second-Pass Refinement Targets

### 1. GRAMMAR_ARTICLES_BASIC

Required target:

```text
Find EGP rows for broad basic article presence rules: a/an/the with nouns.
```

Refinement gates:

```text
allow_super_category = DETERMINERS
allow_sub_category = articles
include = WITH NOUNS, INDEFINITE, DEFINITE, A + NOUN, AN + NOUN, THE + NOUN
exclude = NO ARTICLE, PREPOSITION + NO ARTICLE, VERY + ADJECTIVES, only peripheral adjective frames
```

### 2. GRAMMAR_BASIC_PREPOSITIONS_PLACE

Required target:

```text
Find EGP rows for locative/place prepositions.
```

Refinement gates:

```text
allow_super_category = PREPOSITIONS or CLAUSES with locative prepositional phrase evidence
include = PLACE, LOCATION, POSITION, IN, ON, UNDER, NEXT TO, BEHIND, BETWEEN, IN FRONT OF
exclude = NO ARTICLE, ARTICLE-only rows, noun phrase-only rows
```

### 3. GRAMMAR_BE_VERB_BASIC

Required target:

```text
Find direct EGP evidence for am/is/are basic be-verb forms.
```

Refinement gates:

```text
allow_super_category = VERBS or CLAUSES
include = BE, AM, IS, ARE, AFFIRMATIVE WITH BE, NEGATIVE WITH BE, QUESTIONS WITH BE
exclude = MODAL, LIKE, INFINITIVE, lexical verb-only rows
```

### 4. GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC

Required target:

```text
Find EGP rows for possessive adjectives/determiners before nouns.
```

Refinement gates:

```text
allow_super_category = DETERMINERS
include = POSSESSIVE, MY, YOUR, HIS, HER, ITS, OUR, THEIR, + NOUN
exclude = ARTICLE-only rows, adjective-only rows, noun phrase rows without possessive determiners
```

## Deferred Source Audit Target

### GRAMMAR_CAN_STATEMENT

Deferred row:

```text
1741163708329x931125497510935300
```

Audit requirement:

```text
Inspect source row example/can-do statement to determine whether the row supports can + base verb for ability statements, not merely generic modal auxiliary declaratives.
```

Possible outcomes after audit:

```text
ACCEPT_EGP_ROW if examples explicitly support can-for-ability statements.
REQUEST_REFINED_CANDIDATES if examples are generic modal only.
DEFER if source row examples are insufficient or ambiguous.
```

## Required R7-M67 Artifacts

```text
ulga/reports/grammar_node_egp_batch01_second_refinement_plan.json
ulga/reports/grammar_node_egp_batch01_second_refinement_plan_summary.json
```

## NEXT_SHORT_STEP

```text
R7-M67_Batch01SecondRefinementPlanArtifactBuilder
```

## Status

```text
R7_M66_STATUS = PASS
STOP_REASON = NONE
NEXT_SHORT_STEP = R7-M67_Batch01SecondRefinementPlanArtifactBuilder
```
