# VOCAB_DB_S0A Level POS Analysis

## Scope

Read-only audit of `vocabulary/source/English Vocabulary Profile Online.xlsx`, canonical sheet `total(15696)`.

No JSON conversion, vocabulary generation, dialogue/question/image/audio generation, C# project creation, or source modification was performed.

## CEFR Level x Part-of-Speech Matrix

| Level | adjective | adverb | auxiliary verb | determiner | exclamation | modal verb | noun | phrasal verb | phrase | preposition | pronoun | verb | Missing POS | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A1 | 93 | 45 | 1 | 39 | 18 | 6 | 322 | 4 | 59 | 37 | 23 | 107 | 30 | 784 |
| A2 | 209 | 120 | 3 | 18 | 11 | 11 | 666 | 27 | 204 | 67 | 36 | 190 | 32 | 1594 |
| B1 | 447 | 166 | 1 | 12 | 3 | 15 | 1112 | 134 | 454 | 61 | 17 | 482 | 33 | 2937 |
| B2 | 679 | 268 | 1 | 14 | 1 | 5 | 1411 | 278 | 773 | 42 | 21 | 661 | 10 | 4164 |
| C1 | 428 | 118 | 0 | 2 | 0 | 0 | 714 | 99 | 668 | 15 | 2 | 362 | 2 | 2410 |
| C2 | 564 | 84 | 0 | 0 | 0 | 0 | 942 | 186 | 1498 | 11 | 2 | 516 | 4 | 3807 |

## POS Distribution by Level

### A1

| POS | Count |
| --- | ---: |
| noun | 322 |
| verb | 107 |
| adjective | 93 |
| phrase | 59 |
| adverb | 45 |
| determiner | 39 |
| preposition | 37 |
| pronoun | 23 |
| exclamation | 18 |
| modal verb | 6 |
| phrasal verb | 4 |
| auxiliary verb | 1 |
| missing | 30 |

### A2

| POS | Count |
| --- | ---: |
| noun | 666 |
| adjective | 209 |
| phrase | 204 |
| verb | 190 |
| adverb | 120 |
| preposition | 67 |
| pronoun | 36 |
| phrasal verb | 27 |
| determiner | 18 |
| exclamation | 11 |
| modal verb | 11 |
| auxiliary verb | 3 |
| missing | 32 |

### B1

| POS | Count |
| --- | ---: |
| noun | 1112 |
| verb | 482 |
| phrase | 454 |
| adjective | 447 |
| adverb | 166 |
| phrasal verb | 134 |
| preposition | 61 |
| pronoun | 17 |
| modal verb | 15 |
| determiner | 12 |
| exclamation | 3 |
| auxiliary verb | 1 |
| missing | 33 |

### B2

| POS | Count |
| --- | ---: |
| noun | 1411 |
| phrase | 773 |
| adjective | 679 |
| verb | 661 |
| phrasal verb | 278 |
| adverb | 268 |
| preposition | 42 |
| pronoun | 21 |
| determiner | 14 |
| modal verb | 5 |
| auxiliary verb | 1 |
| exclamation | 1 |
| missing | 10 |

### C1

| POS | Count |
| --- | ---: |
| noun | 714 |
| phrase | 668 |
| adjective | 428 |
| verb | 362 |
| adverb | 118 |
| phrasal verb | 99 |
| preposition | 15 |
| determiner | 2 |
| pronoun | 2 |
| missing | 2 |

### C2

| POS | Count |
| --- | ---: |
| phrase | 1498 |
| noun | 942 |
| adjective | 564 |
| verb | 516 |
| phrasal verb | 186 |
| adverb | 84 |
| preposition | 11 |
| pronoun | 2 |
| missing | 4 |

## Dominance Findings

- Noun-dominated levels: `A1`, `A2`, `B1`, `B2`, `C1`.
- Phrase-dominated level: `C2`.
- Verb is never the top POS for any CEFR level, but it is the second-largest POS at `A1` and `B1`.
- Phrase share grows strongly from `B2` onward, especially `C1` and `C2`.

## Import Implications

- Active A1-A2 vocabulary pools should prioritize nouns, verbs, adjectives, and high-confidence phrases.
- B2-C1 pools require explicit phrase handling; downstream systems must not assume entries are single words.
- Missing POS rows should be imported with warnings and blocked from active generation until recovered or explicitly allowed.
