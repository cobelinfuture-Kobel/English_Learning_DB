# VOCAB_DB_S0A Missing Topic Analysis

## Scope

Read-only audit of rows where `Topic` is empty in canonical sheet `total(15696)`.

## Missing Topic Count by Level

| Level | Total rows | Missing topic | Missing topic % |
| --- | ---: | ---: | ---: |
| A1 | 784 | 306 | 39.0% |
| A2 | 1594 | 625 | 39.2% |
| B1 | 2937 | 1274 | 43.4% |
| B2 | 4164 | 1907 | 45.8% |
| C1 | 2410 | 1772 | 73.5% |
| C2 | 3807 | 2910 | 76.4% |
| Total | 15696 | 8794 | 56.0% |

## Top Guidewords Affected

| Guideword | Missing topic rows |
| --- | ---: |
| `<empty guideword>` | 4733 |
| IDIOM | 449 |
| TIME | 40 |
| PERSON | 25 |
| PLACE | 24 |
| MONEY | 21 |
| SITUATION | 18 |
| DIRECTION | 16 |
| IDEA | 15 |
| GROUP | 15 |
| AMOUNT | 15 |
| DIFFERENT | 15 |
| CHANGE | 14 |
| MOVEMENT | 13 |
| GRAMMAR | 13 |

## Top Parts of Speech Affected

| POS | Missing topic rows |
| --- | ---: |
| phrase | 2653 |
| noun | 2377 |
| verb | 1245 |
| adjective | 1219 |
| adverb | 519 |
| phrasal verb | 371 |
| preposition | 140 |
| pronoun | 87 |
| `<missing pos>` | 86 |
| determiner | 60 |
| modal verb | 28 |
| auxiliary verb | 5 |
| exclamation | 4 |

## Findings

- Missing topic is the largest import risk: 8794 rows, or 56.0% of the canonical sheet.
- Advanced levels are especially sparse: C1 and C2 have topic missing rates above 70%.
- The missing-topic population is heavily phrase/noun/verb/adjective dominated.
- Empty guideword rows account for more than half of missing-topic rows, reducing confidence in automatic topic recovery.

## Recommendations

### Import With Warning

Import missing-topic rows with warning metadata to preserve source completeness and row traceability.

Recommended warning:

```text
missing Topic
```

### Import as `unmapped`

Normalize missing topic to a controlled value only in a separate normalized field, for example:

```json
{
  "topic": "",
  "topic_status": "unmapped"
}
```

Do not overwrite the raw source value.

### Block From Active Generation

Rows with `topic_status: unmapped` should be blocked from active generation until manually mapped or recovered with a validated strategy.

### Candidate Automatic Mapping Strategies

1. Sheet reconciliation: if the same composite key appears on a topic sheet, use that sheet topic as a candidate mapping.
2. Word-level majority vote: if a word has one dominant topic across other rows, propose it as a candidate only when confidence is high.
3. Guideword heuristics: map high-signal guidewords such as `MONEY`, `PERSON`, or `PLACE` to candidate topics, but keep them as review-required.
4. POS-aware fallback: avoid mapping idioms and phrases automatically unless the phrase appears in a topic sheet.
5. Manual review queue: prioritize A1-C1 active rows before C2, since C2 is imported-only for now.

## Validation Policy

- Missing topic should not fail raw import.
- Missing topic should fail active-pool eligibility.
- Reports should include missing-topic counts by level, POS, and guideword.
