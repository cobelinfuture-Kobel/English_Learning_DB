# R7-M64 Family-Gated Operator Review Batch 01

## Task

```text
R7-M64_FamilyGatedOperatorReviewBatch01
```

## Scope

This document prepares Batch 01 for human operator decisions.

It does not select an EGP row, write `egp_evidence_refs`, increase coverage, generate PracticeBank, or write learner state.

## Batch 01 Items

```text
GRAMMAR_ARTICLES_BASIC = 4 family-gated candidates
GRAMMAR_BASIC_PREPOSITIONS_PLACE = 0 family-gated candidates
GRAMMAR_BE_VERB_BASIC = 2 family-gated candidates
GRAMMAR_CAN_STATEMENT = 4 family-gated candidates
GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC = 0 family-gated candidates
```

## Decision Options

```text
ACCEPT_EGP_ROW
REJECT_ALL_CANDIDATES
MARK_NOT_IN_EGP_BUT_SYSTEM_REQUIRED
DEFER
REQUEST_REFINED_CANDIDATES
```

## Review Worksheet

### B01-01 GRAMMAR_ARTICLES_BASIC

```text
mapping_mode = collocation_sensitive
grammar_family = determiner_articles
candidate_count = 4
```

Candidates:

```text
1. 1741163708789x105964971324936210
   A1 / DETERMINERS / articles
   FORM: WITH NOUNS
   score = 0.805128 / HIGH

2. 1741163708789x344483096716751800
   A1 / DETERMINERS / articles
   FORM: 'A' + ADJECTIVES
   score = 0.803704 / HIGH

3. 1741163708789x174288205596050180
   A1 / DETERMINERS / articles
   FORM: 'A' + 'VERY' + ADJECTIVES
   score = 0.761111 / HIGH

4. 1741163708789x819248395543273500
   A1 / DETERMINERS / articles
   FORM: PREPOSITION + 'THE' + NOUN
   score = 0.645 / MEDIUM
```

Review note:

```text
Candidate set is materially improved versus the earlier no-article noise. Candidate 1 is the broadest match for basic articles with nouns, but the operator must confirm source-row examples before ACCEPT_EGP_ROW.
```

### B01-02 GRAMMAR_BASIC_PREPOSITIONS_PLACE

```text
mapping_mode = lexico_grammar
grammar_family = prepositions_place
candidate_count = 0
```

Review note:

```text
No candidate survived the place-preposition family gate. This item should normally be REQUEST_REFINED_CANDIDATES or DEFER until better source-row discovery for locative/place prepositions exists.
```

### B01-03 GRAMMAR_BE_VERB_BASIC

```text
mapping_mode = grammar
grammar_family = be_verb_core
candidate_count = 2
```

Candidates:

```text
1. 1741163708329x286701804737242940
   A1 / CLAUSES / declarative
   FORM: AFFIRMATIVE DECLARATIVE
   score = 0.53 / MEDIUM

2. 1741163708329x778951051617750700
   A1 / CLAUSES / declarative
   FORM: NEGATIVE DECLARATIVE WITH 'BE'
   score = 0.53 / MEDIUM
```

Review note:

```text
Both candidates are plausible be-verb core rows, but broad. The operator must confirm examples/source text before accepting one or both as evidence.
```

### B01-04 GRAMMAR_CAN_STATEMENT

```text
mapping_mode = grammar
grammar_family = modal_can_statement
candidate_count = 4
```

Candidates:

```text
1. 1741163708329x931125497510935300
   A1 / CLAUSES / declarative
   FORM: AFFIRMATIVE DECLARATIVE, MODAL AUXILIARY VERBS
   score = 0.762121 / HIGH

2. 1741163708329x286701804737242940
   A1 / CLAUSES / declarative
   FORM: AFFIRMATIVE DECLARATIVE
   score = 0.643846 / MEDIUM

3. 1741163708329x894844343465365000
   A1 / CLAUSES / declarative
   FORM: NEGATIVE DECLARATIVE, LEXICAL VERBS
   score = 0.565882 / MEDIUM

4. 1741163708329x778951051617750700
   A1 / CLAUSES / declarative
   FORM: NEGATIVE DECLARATIVE WITH 'BE'
   score = 0.565 / MEDIUM
```

Review note:

```text
Candidate 1 is the strongest structural match for can statements because it targets modal auxiliary declaratives. It still needs operator confirmation that the source row supports can for ability, not only general modal form.
```

### B01-05 GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC

```text
mapping_mode = grammar
grammar_family = possessive_determiners
candidate_count = 0
```

Review note:

```text
No candidate survived the possessive determiner family gate. This item should normally be REQUEST_REFINED_CANDIDATES or DEFER until better source-row discovery for my/your/his/her/its/our/their before nouns exists.
```

## Operator Decision Template

```text
B01-01 GRAMMAR_ARTICLES_BASIC = <decision>
selected_egp_row_id = <id or null>
reason = <operator reason>

B01-02 GRAMMAR_BASIC_PREPOSITIONS_PLACE = <decision>
selected_egp_row_id = <id or null>
reason = <operator reason>

B01-03 GRAMMAR_BE_VERB_BASIC = <decision>
selected_egp_row_id = <id or null>
reason = <operator reason>

B01-04 GRAMMAR_CAN_STATEMENT = <decision>
selected_egp_row_id = <id or null>
reason = <operator reason>

B01-05 GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC = <decision>
selected_egp_row_id = <id or null>
reason = <operator reason>
```

## Stop State

```text
R7_M64_STATUS = OPERATOR_REVIEW_WORKSHEET_READY
STOP_REASON = NEED_HUMAN_SOURCE_REF_EVIDENCE_SELECTION
BLOCKER_TYPE = HUMAN_EVIDENCE_REVIEW_REQUIRED
LAST_COMPLETED_STATUS = R7_M64_FAMILY_GATED_OPERATOR_REVIEW_BATCH01_WORKSHEET_READY
REQUIRED_OPERATOR_ACTION = Fill the Batch 01 operator decision template.
NEXT_RESUME_TASK = R7-M65_Batch01OperatorDecisionArtifact
```
