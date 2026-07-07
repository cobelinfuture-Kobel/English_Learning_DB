# R7-M61 Grammar Node EGP Refinement Gate By Grammar Family

## Task

```text
R7-M61_GrammarNodeEGPRefinementGateByGrammarFamily
```

## Predecessor

```text
R7-M59R_RefinedOperatorReviewBatchReadyStop = PASS
R7-M60_RefinedOperatorReviewBatch01 = operator discussion completed
```

## Problem

Batch 01 review showed that surface token overlap can produce false-positive EGP candidates.

Examples:

```text
PREPOSITION token overlap matched no-article rules instead of prepositions of place.
ARTICLE token overlap matched no-article rules instead of basic a/an/the use.
BE VERB token overlap matched modal or noun-phrase rows.
POSSESSIVE token overlap matched adjective rows instead of possessive determiners.
```

## Design Principle

R7-M61 uses corpus-linguistic rationale to design deterministic grammar-family gates.

This is not a corpus-statistical model. It does not compute type-token ratio, collostructional strength, conditional probability, TF-IDF, or cosine similarity over an external corpus.

## Mapping Modes

```text
grammar = core structural mapping
lexico_grammar = grammar category with lexical-context dependency
collocation_sensitive = grammar mapping that must avoid fixed-phrase or no-article noise
```

## Batch 01 Gate Policy

```text
GRAMMAR_ARTICLES_BASIC
mapping_mode = collocation_sensitive
grammar_family = determiner_articles
allow_super_category = DETERMINERS
allow_sub_category contains articles
guideword_include = ARTICLE, A, AN, THE, DEFINITE, INDEFINITE
guideword_exclude = NO ARTICLE, PREPOSITION + NO ARTICLE

GRAMMAR_BASIC_PREPOSITIONS_PLACE
mapping_mode = lexico_grammar
grammar_family = prepositions_place
allow_super_category = PREPOSITIONS
guideword_include = PLACE, POSITION, LOCATION, IN, ON, AT, UNDER, NEXT TO
guideword_exclude = NO ARTICLE, ARTICLE, ADJECTIVE + NOUN

GRAMMAR_BE_VERB_BASIC
mapping_mode = grammar
grammar_family = be_verb_core
guideword_include = BE, AM, IS, ARE
guideword_exclude = MODAL, LIKE, INFINITIVE, NOUN PHRASE

GRAMMAR_CAN_STATEMENT
mapping_mode = grammar
grammar_family = modal_can_statement
guideword_include = CAN, MODAL, ABILITY, AFFIRMATIVE DECLARATIVE
guideword_exclude = QUESTION, YES/NO, NOUN PHRASE

GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC
mapping_mode = grammar
grammar_family = possessive_determiners
guideword_include = POSSESSIVE, MY, YOUR, HIS, HER, ITS, OUR, THEIR
guideword_exclude = ARTICLE, ADJECTIVE + PLURAL NOUN, LIKE
```

## Required R7-M62 Artifacts

```text
ulga/reports/grammar_node_egp_family_gated_candidate_suggestions.json
ulga/reports/grammar_node_egp_family_gated_candidate_suggestions_summary.json
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
NEXT_SHORT_STEP = R7-M62_GrammarNodeEGPFamilyGatedCandidateBuilderImplementation
```

## Status

```text
R7_M61_STATUS = PASS
STOP_REASON = NONE
```
